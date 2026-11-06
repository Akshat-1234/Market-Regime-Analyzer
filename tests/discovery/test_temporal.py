from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from research.contracts.model import SelectionScore, assert_comparable_density
from research.discovery.experiment import evaluate_inner_fold, fit_attempt
from research.discovery.protocol import (INNER_FOLD_COUNT, MIN_INNER_TRAIN_ROWS, NUMERICAL_SETTINGS,
                                         candidate_grid, inner_folds, outer_folds)
from research.discovery.temporal import (AttemptScore, TrainingTransform, raw_density_from_scaled,
                                         select_using_inner_evidence)


def test_actual_outer_and_inner_boundaries_are_chronological():
    from research.discovery.data import load_feature_data
    features, manifest = load_feature_data()
    folds = outer_folds(features.index)
    assert len(folds) == 14 and folds[0].fold_id == "outer_2012" and folds[-1].fold_id == "outer_2025"
    assert folds[0].train_start == "2007-10-16" and folds[0].test_start.startswith("2012-")
    assert manifest["complete_rows"] == 4664 and manifest["dataset"]["rows"] == 4684
    for fold in folds:
        train = features.loc[fold.train_start:fold.train_end].index
        test = features.loc[fold.test_start:fold.test_end].index
        assert len(train) == fold.train_rows and len(test) == fold.test_rows
        assert train[-1] < test[0] and test[-1].year == int(fold.fold_id[-4:])
        inners = inner_folds(fold, train)
        assert len(inners) == INNER_FOLD_COUNT
        for inner in inners:
            inner_train = features.loc[inner.train_start:inner.train_end].index
            validation = features.loc[inner.validation_start:inner.validation_end].index
            assert len(inner_train) >= MIN_INNER_TRAIN_ROWS and len(validation) == 126
            assert inner_train[-1] < validation[0] and validation[-1] <= train[-1] < test[0]


def test_candidate_grid_is_bounded_and_complete():
    grid = candidate_grid()
    assert len(grid) == 12 and {candidate.state_count for candidate in grid} == {2, 3, 4, 5}
    assert sum(candidate.emission == "student_t" for candidate in grid) == 4
    assert all(candidate.covariance_type == "diag" for candidate in grid if candidate.emission == "student_t")
    assert sum(candidate.covariance_type == "full" for candidate in grid) == 4


def test_training_transform_ignores_validation_and_applies_jacobian(synthetic_features):
    train = synthetic_features.iloc[:504]
    validation = synthetic_features.iloc[504:630]
    transform = TrainingTransform.fit(train)
    np.testing.assert_array_equal(transform.mean, train.to_numpy().mean(axis=0))
    np.testing.assert_array_equal(transform.scale, train.to_numpy().std(axis=0, ddof=0))
    changed = validation.copy()
    changed.iloc[:] = 1e6
    np.testing.assert_array_equal(transform.mean, TrainingTransform.fit(train).mean)
    scaled = transform.apply(validation)
    np.testing.assert_allclose(scaled, (validation.to_numpy() - transform.mean) / transform.scale)
    zeros = np.zeros(len(validation))
    raw = raw_density_from_scaled(validation.index, zeros, transform)
    np.testing.assert_allclose(raw.values, -transform.log_jacobian)
    other = raw_density_from_scaled(validation.index, zeros, transform)
    assert_comparable_density(raw, other)
    assert raw.space == "raw" and raw.transformation_jacobian_included


def _score(outer, candidate, seed, fold, value):
    return AttemptScore(candidate, seed, fold,
                        SelectionScore(outer, candidate, fold, pd.Timestamp("2011-12-30"),
                                       pd.Timestamp("2012-01-03"), value))


def test_selection_requires_complete_seeds_and_is_deterministic():
    attempts = []
    for candidate in ("k2_gaussian_diag", "k3_gaussian_diag"):
        for seed in (2, 42, 7):
            for fold in range(3):
                value = 1.0 if candidate.startswith("k2") else 2.0
                if candidate.startswith("k3") and seed != 2 and fold == 2:
                    continue
                attempts.append(_score("outer_2012", candidate, seed, f"inner_{fold}", value))
    selection = select_using_inner_evidence(attempts, "outer_2012")
    assert selection.decision.selected_candidate_id == "k2_gaussian_diag"
    assert selection.selected_seed == 2 and selection.eligible_candidates == ("k2_gaussian_diag",)
    repeated = select_using_inner_evidence(list(reversed(attempts)), "outer_2012")
    assert repeated.decision == selection.decision and repeated.selected_seed == selection.selected_seed


def test_selection_uses_highest_complete_seed_mean_with_smallest_tie_break():
    attempts = []
    for seed, value in ((2, 1.0), (42, 2.0), (7, 2.0)):
        for fold in range(3):
            attempts.append(_score("outer_2012", "k2_gaussian_diag", seed, f"inner_{fold}", value + fold * 0.01))
    selection = select_using_inner_evidence(attempts, "outer_2012")
    assert selection.selected_seed == 7


def test_no_usable_inner_evidence_is_inconclusive():
    with pytest.raises(ValueError, match="no candidate"):
        select_using_inner_evidence([], "outer_2012")


def test_fit_attempt_reproducibility_validation_isolation_and_continuation(synthetic_features, synthetic_outer, fast_numerics):
    inner = inner_folds(synthetic_outer, synthetic_features.loc[:synthetic_outer.train_end].index)[0]
    train = synthetic_features.loc[inner.train_start:inner.train_end]
    validation = synthetic_features.loc[inner.validation_start:inner.validation_end]
    candidate = candidate_grid()[0]
    first, score, payload = fit_attempt(candidate, 2, train, validation, synthetic_outer, inner=inner)
    second, _, second_payload = fit_attempt(candidate, 2, train, validation, synthetic_outer, inner=inner)
    assert first["status"] == "accepted" and score is not None
    assert first == second
    result, transform, raw = payload
    for name in ("startprob", "transmat", "means", "covars"):
        np.testing.assert_array_equal(getattr(result.model, name), getattr(second_payload[0].model, name))
    expected, density, _ = result.model.filter(transform.apply(validation), result.final_log_alpha)
    np.testing.assert_array_equal(expected, result.record.oos_filtered.probabilities)
    np.testing.assert_array_equal(density, result.oos_density.values)
    changed = validation.copy()
    changed.iloc[:] = 1000
    changed_record, _, changed_payload = fit_attempt(candidate, 2, train, changed, synthetic_outer, inner=inner)
    for name in ("startprob", "transmat", "means", "covars"):
        np.testing.assert_array_equal(getattr(result.model, name), getattr(changed_payload[0].model, name))
    assert changed_record["evaluation_raw_log_density_mean"] != first["evaluation_raw_log_density_mean"]


def test_future_mutation_does_not_change_filtered_prefix(synthetic_features, synthetic_outer, fast_numerics):
    inner = inner_folds(synthetic_outer, synthetic_features.loc[:synthetic_outer.train_end].index)[0]
    train = synthetic_features.loc[inner.train_start:inner.train_end]
    validation = synthetic_features.loc[inner.validation_start:inner.validation_end]
    _, _, payload = fit_attempt(candidate_grid()[0], 2, train, validation, synthetic_outer, inner=inner)
    result, transform, _ = payload
    scaled = transform.apply(validation)
    changed = scaled.copy()
    changed[60:] += 1000
    first, first_density, _ = result.model.filter(scaled, result.final_log_alpha)
    second, second_density, _ = result.model.filter(changed, result.final_log_alpha)
    np.testing.assert_allclose(first[:60], second[:60], atol=1e-15)
    np.testing.assert_allclose(first_density[:60], second_density[:60], atol=1e-14)


def test_nonconvergence_is_retained_without_selection_score(synthetic_features, synthetic_outer, monkeypatch):
    monkeypatch.setitem(NUMERICAL_SETTINGS, "n_iter", 1)
    monkeypatch.setitem(NUMERICAL_SETTINGS, "tol", 0.0)
    inner = inner_folds(synthetic_outer, synthetic_features.loc[:synthetic_outer.train_end].index)[0]
    record, score, payload = fit_attempt(candidate_grid()[0], 2,
                                        synthetic_features.loc[inner.train_start:inner.train_end],
                                        synthetic_features.loc[inner.validation_start:inner.validation_end],
                                        synthetic_outer, inner=inner)
    assert record["status"] == "nonconverged" and score is None and payload[2] is None
    assert record["rejection_reason"]


def test_outer_test_mutation_cannot_change_inner_fit_or_selection(synthetic_features, synthetic_outer, fast_numerics):
    grid = (candidate_grid()[0],)
    first_attempts, first_scores = evaluate_inner_fold(synthetic_outer, synthetic_features, grid=grid, seeds=(2, 42))
    changed = synthetic_features.copy()
    changed.loc[synthetic_outer.test_start:synthetic_outer.test_end] = 1e6
    second_attempts, second_scores = evaluate_inner_fold(synthetic_outer, changed, grid=grid, seeds=(2, 42))
    assert first_attempts == second_attempts
    assert [item.score for item in first_scores] == [item.score for item in second_scores]
    first = select_using_inner_evidence(first_scores, synthetic_outer.fold_id)
    second = select_using_inner_evidence(second_scores, synthetic_outer.fold_id)
    assert first.decision == second.decision and first.selected_seed == second.selected_seed
