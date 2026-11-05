from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.contracts.model import InferenceKind, ProbabilityBlock
from research.contracts.state import (align_training_states, apply_alignment,
                                      posterior_weighted_characteristics, summarize_occupancy)


def training_block(probabilities, ids=None):
    matrix = np.asarray(probabilities, dtype=float)
    state_ids = tuple(ids) if ids is not None else tuple(f"state_{i}" for i in range(matrix.shape[1]))
    return ProbabilityBlock(pd.date_range("2024-01-01", periods=len(probabilities), freq="B"),
                            matrix, state_ids, InferenceKind.TRAINING_FILTERED)


def test_state_alignment_is_permutation_invariant_and_uses_explicit_mapping():
    reference_probabilities = np.array([
        [.90, .09, .01], [.80, .15, .05], [.10, .80, .10],
        [.05, .85, .10], [.05, .10, .85], [.10, .05, .85],
    ])
    reference = training_block(reference_probabilities)
    permutation = [2, 0, 1]
    current_ids = tuple(reference.state_ids[index] for index in permutation)
    current = training_block(reference_probabilities[:, permutation], current_ids)
    alignment = align_training_states(reference, current)
    assert alignment.current_to_reference == {current_ids[i]: reference.state_ids[permutation[i]]
                                               for i in range(3)}
    assert alignment.agreement == 1.0
    np.testing.assert_allclose(apply_alignment(current, alignment), reference_probabilities)


def test_occupancy_tracks_permuted_columns_exactly_once():
    probabilities = np.array([[.9, .1, 0], [.8, .2, 0], [.1, .8, .1], [.1, .7, .2]])
    order = np.array([2, 0, 1])
    permuted = probabilities[:, order]
    ids = np.array(["a", "b", "c"])[order]
    observed = summarize_occupancy(permuted, tuple(ids), rare_min_count=0, rare_min_fraction=0)
    hard = permuted.argmax(axis=1)
    expected = np.bincount(hard, minlength=3) / len(permuted)
    np.testing.assert_allclose([item.hard_fraction for item in observed], expected)
    # Reapplying the order here would be the historical double-permutation bug.
    assert not np.allclose(expected, expected[order])


def test_rare_and_zero_occupancy_states_are_explicit_for_variable_k():
    probabilities = np.array([[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0],
                              [0, 1, 0, 0], [0, 0, .6, .4]], dtype=float)
    summary = summarize_occupancy(probabilities, ("a", "b", "rare", "zero"),
                                  rare_min_count=2, rare_min_fraction=.10)
    assert len(summary) == 4
    assert summary[0].hard_count == 3
    assert not summary[0].rare
    assert summary[2].hard_count == 1 and summary[2].rare
    assert summary[3].hard_count == 0 and summary[3].hard_fraction == 0
    assert summary[3].rare
    assert summary[3].posterior_weight == pytest.approx(.08)


def test_zero_weight_characteristics_are_null_not_fake_zero():
    probabilities = np.array([[1., 0.], [1., 0.], [0., 1.]])
    descriptions = posterior_weighted_characteristics(
        probabilities, {"measured_volatility": np.array([.1, .2, .4]),
                        "missing_measurement": np.array([np.nan, np.nan, np.nan])}, ("low", "high"))
    assert descriptions["low"]["measured_volatility"] == pytest.approx(.15)
    assert descriptions["high"]["measured_volatility"] == pytest.approx(.4)
    empty = posterior_weighted_characteristics(np.array([[1., 0.], [1., 0.]]),
                                               {"measured": np.array([1., 2.])}, ("used", "empty"))
    assert empty["empty"]["measured"] is None
    assert descriptions["low"]["missing_measurement"] is None


def test_alignment_rejects_smoothed_or_oos_inputs():
    reference = training_block([[.8, .2], [.2, .8]])
    for kind in (InferenceKind.SMOOTHED, InferenceKind.OOS_FILTERED, InferenceKind.FILTERED):
        current = ProbabilityBlock(reference.dates, reference.probabilities, ("x", "y"), kind)
        with pytest.raises(ValueError, match="training-filtered"):
            align_training_states(reference, current)


def test_alignment_uses_only_overlap_of_adjacent_expanding_training_windows():
    reference_probabilities = np.array([[.9, .1], [.8, .2], [.2, .8], [.1, .9]])
    reference = training_block(reference_probabilities, ("calm", "stress"))
    # Current training starts one session later and adds one nonoverlap row.
    current = ProbabilityBlock(pd.date_range("2024-01-02", periods=4, freq="B"),
                               reference_probabilities[[1, 2, 3, 0]][:, [1, 0]],
                               ("stress", "calm"), InferenceKind.TRAINING_FILTERED)
    alignment = align_training_states(reference, current)
    assert alignment.training_start == pd.Timestamp("2024-01-02")
    assert alignment.training_end == pd.Timestamp("2024-01-04")
    assert alignment.agreement == 1.0
    assert alignment.contingency.sum() == 3


def test_alignment_requires_overlapping_dates_and_state_count():
    reference = training_block([[.8, .2], [.2, .8]], ("a", "b"))
    other_dates = ProbabilityBlock(pd.date_range("2025-01-01", periods=2), reference.probabilities,
                                   ("a", "b"), InferenceKind.TRAINING_FILTERED)
    with pytest.raises(ValueError, match="overlapping training dates"):
        align_training_states(reference, other_dates)
    three = training_block([[.7, .2, .1], [.1, .2, .7]], ("a", "b", "c"))
    with pytest.raises(ValueError, match="same state count"):
        align_training_states(reference, three)
