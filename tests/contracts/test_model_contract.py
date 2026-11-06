from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.contracts.model import (FitRecord, FitStatus, InferenceKind, ModelSpec,
                                      PredictiveDensity, ProbabilityBlock, SelectionScore,
                                      assert_comparable_density, require_usable_oos,
                                      select_candidate_for_fold)


def spec(states: int = 3) -> ModelSpec:
    return ModelSpec("synthetic", "fixture-model-v1", "rv", "f10-close-features-v1",
                     ("daily_return", "volatility_20"), states, "gaussian", "diag",
                     "training-zscore-with-raw-jacobian", 42)


def block(kind=InferenceKind.OOS_FILTERED, states: int = 3, start="2024-01-01"):
    dates = pd.date_range(start, periods=4, freq="B")
    probabilities = np.full((4, states), 1 / states)
    return ProbabilityBlock(dates, probabilities, tuple(f"s{i}" for i in range(states)), kind)


def accepted_fit(**changes):
    values = dict(spec=spec(), status=FitStatus.ACCEPTED, converged=True,
                  train_start="2023-01-02", train_end="2023-12-29",
                  parameters={"fixture": True}, oos_filtered=block())
    values.update(changes)
    return FitRecord(**values)


def test_probability_block_distinguishes_inference_kinds_for_variable_k():
    assert block(states=4).probabilities.shape == (4, 4)
    assert block(InferenceKind.TRAINING_FILTERED).causal
    assert block(InferenceKind.FILTERED).causal
    assert block(InferenceKind.OOS_FILTERED).causal
    assert not block(InferenceKind.SMOOTHED).causal


@pytest.mark.parametrize("probabilities,match", [
    ([[0.8, 0.3]], "sum to one"),
    ([[-0.1, 1.1]], "nonnegative"),
    ([[np.nan, 1.0]], "finite"),
    ([0.5, 0.5], "N x K"),
    ([[1.0]], "K >= 2"),
])
def test_invalid_probability_shapes_and_values_are_rejected(probabilities, match):
    with pytest.raises(ValueError, match=match):
        ProbabilityBlock(pd.date_range("2024-01-01", periods=1), probabilities, ("a", "b"),
                         InferenceKind.FILTERED)


def test_probability_dates_and_state_ids_must_align():
    with pytest.raises(ValueError, match="equal lengths"):
        ProbabilityBlock(pd.date_range("2024-01-01", periods=2), [[0.5, 0.5]], ("a", "b"),
                         InferenceKind.FILTERED)
    with pytest.raises(ValueError, match="state_ids"):
        ProbabilityBlock(pd.date_range("2024-01-01", periods=1), [[0.5, 0.5]], ("a", "a"),
                         InferenceKind.FILTERED)
    with pytest.raises(ValueError, match="strictly increasing"):
        ProbabilityBlock(pd.DatetimeIndex(["2024-01-02", "2024-01-02"]), [[0.5, 0.5]] * 2,
                         ("a", "b"), InferenceKind.FILTERED)


def test_accepted_fit_requires_convergence_parameters_and_no_fallback():
    fit = accepted_fit()
    assert fit.usable_for_inference
    assert require_usable_oos(fit).kind is InferenceKind.OOS_FILTERED
    with pytest.raises(ValueError, match="accepted fits require"):
        accepted_fit(converged=False)
    with pytest.raises(ValueError, match="accepted fits require"):
        accepted_fit(parameters=None)
    with pytest.raises(ValueError, match="accepted fits require"):
        accepted_fit(fallback_used=True)


def test_nonconverged_fallback_is_explicit_but_never_usable():
    fit = accepted_fit(status=FitStatus.NONCONVERGED, converged=False,
                       rejection_reason="maximum iterations", fallback_used=True)
    assert fit.fallback_used
    assert not fit.usable_for_inference
    with pytest.raises(ValueError, match="only an accepted"):
        require_usable_oos(fit)


def test_rejected_and_failed_fits_require_reasons_and_cannot_supply_oos():
    rejected = accepted_fit(status=FitStatus.REJECTED, rejection_reason="zero occupancy",
                            parameters=None, oos_filtered=None)
    failed = accepted_fit(status=FitStatus.FAILED, failure_reason="singular covariance",
                          parameters=None, oos_filtered=None)
    assert rejected.status is FitStatus.REJECTED
    assert failed.status is FitStatus.FAILED
    with pytest.raises(ValueError, match="rejection_reason"):
        accepted_fit(status=FitStatus.REJECTED, parameters=None, oos_filtered=None)
    with pytest.raises(ValueError, match="failure_reason"):
        accepted_fit(status=FitStatus.FAILED, parameters=None, oos_filtered=None)


def test_training_assignments_and_block_dates_are_explicit():
    training = ProbabilityBlock(pd.date_range("2023-01-02", periods=4, freq="B"),
                                [[0.9, 0.1, 0], [0.8, 0.2, 0], [0.1, 0.8, 0.1], [0.2, 0.7, 0.1]],
                                ("s0", "s1", "s2"), InferenceKind.TRAINING_FILTERED)
    fit = accepted_fit(train_start=training.dates[0], train_end=training.dates[-1],
                       training_filtered=training, training_assignments=np.array([0, 0, 1, 1]))
    assert fit.training_filtered.kind is InferenceKind.TRAINING_FILTERED
    np.testing.assert_array_equal(fit.training_assignments, [0, 0, 1, 1])
    with pytest.raises(ValueError, match="must align"):
        accepted_fit(train_start=training.dates[0], train_end=training.dates[-1],
                     training_filtered=training, training_assignments=np.array([0, 1]))
    with pytest.raises(ValueError, match="kind"):
        accepted_fit(smoothed=block(InferenceKind.OOS_FILTERED))


def test_density_comparison_requires_identical_raw_features_dates_and_jacobian():
    dates = pd.date_range("2024-01-01", periods=3, freq="B")
    left = PredictiveDensity(dates, [-1, -2, -3], ("daily_return", "volatility_20"),
                             "raw", transformation_jacobian_included=True)
    right = PredictiveDensity(dates, [-1.1, -2.1, -3.1], ("daily_return", "volatility_20"),
                              "raw", transformation_jacobian_included=True)
    assert_comparable_density(left, right)
    different_dimension = PredictiveDensity(
        dates, [-1, -2, -3], ("daily_return", "volatility_20", "drawdown_252"),
        "raw", transformation_jacobian_included=True)
    with pytest.raises(ValueError, match="same ordered raw feature vector"):
        assert_comparable_density(left, different_dimension)
    scaled = PredictiveDensity(dates, [-1, -2, -3], left.feature_names, "scaled")
    with pytest.raises(ValueError, match="only raw-space"):
        assert_comparable_density(left, scaled)
    no_jacobian = PredictiveDensity(dates, [-1, -2, -3], left.feature_names, "raw")
    with pytest.raises(ValueError, match="Jacobian"):
        assert_comparable_density(left, no_jacobian)
    other_dates = PredictiveDensity(pd.date_range("2024-02-01", periods=3, freq="B"),
                                    [-1, -2, -3], left.feature_names, "raw",
                                    transformation_jacobian_included=True)
    with pytest.raises(ValueError, match="observation dates"):
        assert_comparable_density(left, other_dates)


def test_inner_selection_uses_only_pre_outer_validation_and_deterministic_ties():
    scores = [
        SelectionScore("outer_2021", "k2", "inner_a", "2020-06-30", "2021-01-01", -2.0),
        SelectionScore("outer_2021", "k2", "inner_b", "2020-12-30", "2021-01-01", -1.0),
        SelectionScore("outer_2021", "k3", "inner_a", "2020-06-30", "2021-01-01", -2.0),
        SelectionScore("outer_2021", "k3", "inner_b", "2020-12-30", "2021-01-01", -2.0),
    ]
    decision = select_candidate_for_fold(scores, "outer_2021")
    assert decision.selected_candidate_id == "k2"
    assert decision.mean_inner_log_density == pytest.approx(-1.5)
    assert decision.validation_fold_ids == ("inner_a", "inner_b")


def test_future_fold_or_global_selection_evidence_is_rejected():
    causal = SelectionScore("outer_2020", "k2", "inner_2019", "2019-12-31", "2020-01-01", -1)
    with pytest.raises(ValueError, match="strictly before"):
        select_candidate_for_fold([
            causal,
            SelectionScore("outer_2020", "k3", "outer_2021", "2021-12-31", "2020-01-01", 100),
        ], "outer_2020")
    decision = select_candidate_for_fold([causal], "outer_2020")
    later = SelectionScore("outer_2021", "k3", "inner_2020", "2020-12-31", "2021-01-01", 100)
    assert select_candidate_for_fold([causal, later], "outer_2020") == decision


def test_fit_probability_state_count_and_oos_boundary_match_model_and_training():
    with pytest.raises(ValueError, match="state count must match"):
        accepted_fit(oos_filtered=block(states=4))
    with pytest.raises(ValueError, match="begin after train_end"):
        accepted_fit(train_end="2024-01-03")


def test_model_spec_rejects_single_state_and_unversioned_configuration():
    with pytest.raises(ValueError, match="state_count"):
        spec(1)
    values = spec().__dict__.copy()
    values["model_version"] = ""
    with pytest.raises(ValueError, match="model_version"):
        ModelSpec(**values)
