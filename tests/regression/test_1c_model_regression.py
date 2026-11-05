from __future__ import annotations

import ast

import numpy as np
import pytest

from research.contracts.model import FitRecord, FitStatus, ModelSpec, require_usable_oos


def test_exact_1c_nonconverged_fallback_is_used_when_no_fit_converged(historical_1c, monkeypatch):
    discovery = historical_1c.module("discovery")
    emhmm = historical_1c.module("emhmm")
    fixture_model = emhmm.HMMFit(
        startprob=np.array([0.5, 0.5]),
        transmat=np.array([[0.9, 0.1], [0.2, 0.8]]),
        means=np.array([[-1.0, 0.0], [1.0, 0.5]]),
        covars=np.array([[0.5, 0.4], [0.7, 0.6]]),
        covariance_type="diag", emission="gaussian", loglik=-10.0,
        n_iter=3, converged=False, history=[-12.0, -11.0, -10.0], seed=17,
    )
    monkeypatch.setattr(discovery, "fit_engine", lambda *args, **kwargs: fixture_model)
    positions = np.arange(24, dtype=float)
    train_x = np.column_stack([np.sin(positions), np.cos(positions / 3) + positions / 100])
    train_r = 0.01 * np.sin(positions / 2)
    test_x = np.column_stack([np.sin(positions[:5] + 0.1), np.cos(positions[:5] / 3)])
    spec = discovery.Spec("synthetic_nonconvergence", ("x0", "x1"), 2)
    fit = discovery.fit_spec_fold(train_x, train_r, test_x, spec, seeds=(17,),
                                  n_iter=3, min_state_fraction=0.0)
    assert fit.diagnostics["used_nonconverged_fallback"] is True
    assert fit.diagnostics["converged"] is False
    assert fit.model.converged is False

    contract_fit = FitRecord(
        spec=ModelSpec("synthetic", "fixture-v1", "rv", "f10-close-features-v1",
                       ("daily_return", "volatility_20"), 2, "gaussian", "diag", "zscore", 17),
        status=FitStatus.NONCONVERGED, converged=False, train_start="2020-01-01",
        train_end="2020-02-01", rejection_reason="maximum iterations", fallback_used=True,
        parameters={"historical_fixture": True},
    )
    assert not contract_fit.usable_for_inference
    with pytest.raises(ValueError, match="only an accepted"):
        require_usable_oos(contract_fit)


def test_exact_1c_double_permuted_occupancy_reproduction(historical_1c):
    source = historical_1c.source("market-regime-platform/src/regime_backtester/discovery.py").decode()
    reorder = "probs_train = probs_train[:, order]"
    occupancy = "occupancy=occupancy[order]"
    assert reorder in source and occupancy in source
    assert source.index(reorder) < source.index(occupancy)

    probabilities = np.array([[.9, .1, 0], [.8, .2, 0], [.1, .8, .1], [.1, .7, .2]])
    order = np.array([2, 0, 1])
    correct_after = np.bincount(probabilities[:, order].argmax(axis=1), minlength=3) / len(probabilities)
    # The source recomputes occupancy after column reordering, then indexes that
    # already-reordered vector by order a second time for FoldFit.
    historical_returned = correct_after[order]
    assert not np.allclose(historical_returned, correct_after)
    # Reviewed min/max and effective-state aggregates are permutation-invariant;
    # this test does not claim those summary rankings changed.
    assert historical_returned.min() == correct_after.min()
    assert historical_returned.max() == correct_after.max()
    assert np.sum(historical_returned ** 2) == pytest.approx(np.sum(correct_after ** 2))


def test_exact_1c_selection_is_global_after_all_folds_not_joint_nested(historical_1c):
    discovery_source = historical_1c.source(
        "market-regime-platform/src/regime_backtester/discovery.py").decode()
    study_source = historical_1c.source("market-regime-platform/src/regime_backtester/study.py").decode()
    tree = ast.parse(study_source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "study_discovery")
    sweep_loop = next(node for node in function.body if isinstance(node, ast.For))
    best = next(node for node in ast.walk(function) if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "best_k" for target in node.targets))
    assert best.lineno > sweep_loop.end_lineno
    assert 'valid.sort_values("mean_inner_predictive_loglik_per_obs"' in study_source
    run_all = study_source[study_source.index("def run_all"):]
    assert run_all.index("n_states = selection[\"selected_n_states\"]") < run_all.index("study_features(")
    # This confirms the implementation/dataflow defect; numerical downstream
    # impact is not claimed or repaired by this regression.


def test_exact_1c_scaled_density_is_compared_across_different_dimensions(historical_1c):
    discovery = historical_1c.module("discovery")
    source = historical_1c.source("market-regime-platform/src/regime_backtester/discovery.py").decode()
    study = historical_1c.source("market-regime-platform/src/regime_backtester/study.py").decode()
    dimensions = {name: len(features) for name, features in discovery.FEATURE_SETS.items()}
    assert dimensions["rv2"] == 2 and dimensions["rvd3"] == 3
    assert "StandardScaler().fit(inner_x)" in source
    assert "scaled_val = scaler.transform(val_x)" in source
    assert "return float(log_pred.mean())" in source
    assert "jacobian" not in source[source.index("def inner_predictive_loglik"):
                                      source.index("def run_spec")].lower()
    assert "for name, columns in FEATURE_SETS.items()" in study
    assert "valid.sort_values(\"mean_inner_predictive_loglik_per_obs\"" in study
    # A log-density over R^2 and one over R^3 are not rankings on a common
    # measure, even if each is internally causal.  Contract rejection is tested
    # separately; this test confirms the historical source path.
