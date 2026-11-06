from __future__ import annotations
import numpy as np
import pytest
from research.contracts.model import FitStatus, InferenceKind, require_usable_oos
from research.hmm.adapter import fit_model
from research.hmm.config import EMConfig


def test_accepted_adapter_has_separate_contract_blocks(make_spec, train_test_data):
    train, train_dates, test, test_dates = train_test_data
    result = fit_model(train, train_dates, make_spec(), test_x=test, test_dates=test_dates,
                       settings=EMConfig(2, seed=7, n_iter=5, tol=1e6), include_smoothed=True)
    assert result.record.status is FitStatus.ACCEPTED and result.record.converged
    assert result.record.training_filtered.kind is InferenceKind.TRAINING_FILTERED
    assert result.record.smoothed.kind is InferenceKind.SMOOTHED
    assert result.record.oos_filtered.kind is InferenceKind.OOS_FILTERED
    assert result.record.oos_filtered.dates.equals(test_dates)
    assert result.training_density.transformation_jacobian_included and result.oos_density.space == "raw"
    require_usable_oos(result.record)


def test_nonconverged_fit_fails_closed_without_oos(make_spec, train_test_data):
    train, train_dates, test, test_dates = train_test_data
    result = fit_model(train, train_dates, make_spec(), test_x=test, test_dates=test_dates,
                       settings=EMConfig(2, seed=7, n_iter=1, tol=0.0))
    assert result.record.status is FitStatus.NONCONVERGED
    assert not result.record.converged and not result.record.fallback_used
    assert result.record.oos_filtered is None and result.oos_density is None and result.record.training_filtered is not None
    with pytest.raises(ValueError, match="only an accepted converged fit"):
        require_usable_oos(result.record)


def test_occupancy_rejection_has_diagnostics_and_no_oos(make_spec, train_test_data):
    train, train_dates, test, test_dates = train_test_data
    result = fit_model(train, train_dates, make_spec(), test_x=test, test_dates=test_dates,
                       settings=EMConfig(2, seed=7, n_iter=5, tol=1e6), min_state_fraction=1.0)
    assert result.record.status is FitStatus.REJECTED and result.record.rejection_reason
    assert "occupancy" in result.record.rejection_reason and result.record.oos_filtered is None and result.oos_density is None


def test_failed_fit_preserves_failure_reason(make_spec, train_test_data):
    train, train_dates, test, test_dates = train_test_data
    train = train.copy()
    train[3, 1] = np.nan
    result = fit_model(train, train_dates, make_spec(), test_x=test, test_dates=test_dates)
    assert result.record.status is FitStatus.FAILED and result.record.failure_reason and "finite" in result.record.failure_reason
    assert result.record.oos_filtered is None and result.model is None


def test_variable_state_count_and_state_id_boundaries(make_spec, train_test_data):
    train, train_dates, test, test_dates = train_test_data
    ids = ("a", "b", "c", "d")
    result = fit_model(train, train_dates, make_spec(states=4), test_x=test, test_dates=test_dates,
                       settings=EMConfig(4, seed=7, n_iter=5, tol=1e6), state_ids=ids)
    assert result.record.status is FitStatus.ACCEPTED and result.record.oos_filtered.state_ids == ids
    assert result.record.oos_filtered.probabilities.shape == (30, 4)


def test_filtering_is_causal_when_future_oos_is_mutated(make_spec, train_test_data):
    train, train_dates, test, test_dates = train_test_data
    result = fit_model(train, train_dates, make_spec(), test_x=test, test_dates=test_dates,
                       settings=EMConfig(2, seed=7, n_iter=5, tol=1e6))
    changed = test.copy()
    changed[15:] += 10000
    first, first_density, _ = result.model.filter(test, result.final_log_alpha)
    second, second_density, _ = result.model.filter(changed, result.final_log_alpha)
    np.testing.assert_allclose(first[:15], second[:15], atol=1e-15)
    np.testing.assert_allclose(first_density[:15], second_density[:15], atol=1e-14)


def test_scaled_density_is_explicitly_not_identity_jacobian(make_spec, train_test_data):
    train, train_dates, *_ = train_test_data
    result = fit_model(train, train_dates, make_spec(), space="scaled", settings=EMConfig(2, seed=7, n_iter=5, tol=1e6))
    assert result.training_density.space == "scaled" and not result.training_density.transformation_jacobian_included
    assert result.diagnostics["space"] == "scaled"


def test_oos_boundary_before_training_end_is_rejected(make_spec, train_test_data):
    train, train_dates, test, _ = train_test_data
    with pytest.raises(ValueError, match="oos_filtered dates must begin after train_end"):
        fit_model(train, train_dates, make_spec(), test_x=test[:2], test_dates=train_dates[-2:],
                  settings=EMConfig(2, seed=7, n_iter=5, tol=1e6))

@pytest.mark.parametrize("kwargs,match", [
    ({"settings": EMConfig(3, seed=7)}, "must match ModelSpec"),
    ({"state_ids": ("same", "same")}, "unique"), ({"space": "other"}, "space"),
    ({"test_x": np.zeros((2, 2))}, "supplied together")])
def test_invalid_adapter_boundaries_are_rejected(kwargs, match, make_spec, train_test_data):
    train, train_dates, *_ = train_test_data
    with pytest.raises(ValueError, match=match):
        fit_model(train, train_dates, make_spec(), **kwargs)


def test_feature_date_alignment_is_enforced(make_spec, train_test_data):
    train, train_dates, *_ = train_test_data
    with pytest.raises(ValueError, match="align"):
        fit_model(train[:-1], train_dates, make_spec())
    with pytest.raises(ValueError, match="timezone-naive"):
        fit_model(train, train_dates.tz_localize("UTC"), make_spec())
