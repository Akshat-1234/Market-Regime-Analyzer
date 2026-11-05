from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.contracts.temporal import (ExecutionTiming, TargetLabel, annual_expanding_folds,
                                         eligible_training_labels, forward_return_labels,
                                         require_mature_labels)


def test_forward_labels_have_explicit_outcome_end_and_hand_value():
    dates = pd.date_range("2024-01-01", periods=7, freq="B")
    close = pd.Series([100, 101, 103, 102, 105, 107, 110], index=dates)
    labels = forward_return_labels(close, 2)
    assert len(labels) == 5
    assert labels[0].decision_date == dates[0]
    assert labels[0].outcome_end_date == dates[2]
    assert labels[0].value == pytest.approx(0.03)
    assert labels[-1].decision_date == dates[4]
    assert labels[-1].outcome_end_date == dates[6]


def test_maturity_is_strict_for_decision_and_outcome_end():
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    mature = TargetLabel(dates[0], dates[1], 1, 0.01)
    outcome_on_cutoff = TargetLabel(dates[0], dates[2], 2, 0.02)
    decision_on_cutoff = TargetLabel(dates[2], dates[3], 1, 0.01)
    eligible = eligible_training_labels([mature, outcome_on_cutoff, decision_on_cutoff], dates[2])
    assert eligible == (mature,)
    require_mature_labels(eligible, dates[2])
    with pytest.raises(ValueError, match="strictly before"):
        require_mature_labels([outcome_on_cutoff], dates[2])


def test_future_price_mutation_cannot_change_matured_prefix_labels():
    dates = pd.date_range("2024-01-01", periods=12, freq="B")
    close = pd.Series(np.linspace(100, 122, 12), index=dates)
    mutated = close.copy()
    cutoff = dates[6]
    mutated.loc[mutated.index >= cutoff] *= 4
    original_labels = forward_return_labels(close, 2)
    mutated_labels = forward_return_labels(mutated, 2)
    original = eligible_training_labels(original_labels, cutoff)
    changed = eligible_training_labels(mutated_labels, cutoff)
    assert original == changed
    assert len(original) < len(original_labels)
    # The raw full label set can change; the maturity guard protects training.
    assert any(left.value != right.value for left, right in zip(original_labels, mutated_labels))


def test_boundary_crossing_label_is_excluded_even_when_decision_is_in_training():
    dates = pd.date_range("2024-01-01", periods=8, freq="B")
    close = pd.Series(np.arange(100, 108), index=dates)
    labels = forward_return_labels(close, 3)
    cutoff = dates[4]
    crossing = next(label for label in labels if label.decision_date == dates[3])
    assert crossing.outcome_end_date == dates[6]
    assert crossing not in eligible_training_labels(labels, cutoff)


def test_fake_recursive_filter_full_and_prefix_agree_under_future_mutation():
    # Deliberately fake deterministic model: validates the contract fixture,
    # not HMM accuracy.  Recursion depends only on past observations.
    def fake_filter(observations):
        transition = np.array([[0.9, 0.1], [0.2, 0.8]])
        probability = np.array([0.5, 0.5])
        output = []
        for observation in observations:
            probability = probability @ transition
            likelihood = np.array([np.exp(-abs(observation)), np.exp(-abs(observation - 2))])
            probability = probability * likelihood
            probability = probability / probability.sum()
            output.append(probability.copy())
        return np.asarray(output)

    observations = np.array([0.2, 0.8, 1.5, 2.1, 1.1, 0.4])
    mutated = observations.copy()
    mutated[4:] = [100, -100]
    np.testing.assert_allclose(fake_filter(observations)[:4], fake_filter(mutated)[:4])
    np.testing.assert_allclose(fake_filter(observations)[:4], fake_filter(observations[:4]))


def test_annual_folds_are_expanding_ordered_and_refit_at_test_start():
    dates = pd.date_range("2019-01-01", "2021-12-31", freq="B")
    folds = annual_expanding_folds(dates, min_train=250, start_date="2020-01-01")
    assert len(folds) == 2
    assert folds[0].train_start == dates[0]
    assert folds[0].test_start >= pd.Timestamp("2020-01-01")
    assert folds[0].train_end < folds[0].test_start
    assert folds[1].train_end == folds[0].test_end
    assert folds[1].train_end < folds[1].test_start
    assert len(dates[dates <= folds[1].train_end]) > len(dates[dates <= folds[0].train_end])


def test_execution_timing_preserves_delayed_first_return_gap():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    timing = ExecutionTiming(dates[0], dates[1], dates[2])
    assert timing.first_return_date == dates[2]
    with pytest.raises(ValueError, match="decision < execution < first"):
        ExecutionTiming(dates[0], dates[0], dates[1])
    with pytest.raises(ValueError, match="decision < execution < first"):
        ExecutionTiming(dates[0], dates[1], dates[1])


def test_invalid_label_or_empty_fold_schedule_is_rejected():
    dates = pd.date_range("2024-01-01", periods=4, freq="B")
    with pytest.raises(ValueError, match="outcome_end"):
        TargetLabel(dates[1], dates[1], 1, 0.01)
    with pytest.raises(ValueError, match="empty"):
        annual_expanding_folds(dates, min_train=10)
