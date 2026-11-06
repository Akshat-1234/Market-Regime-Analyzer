from __future__ import annotations
import numpy as np
import pytest
from sklearn.cluster import KMeans
from research.hmm.config import EMConfig
from research.hmm.em import fit_hmm, initialize_parameters, m_step
from research.hmm.forward_backward import EStep, e_step
from research.hmm.parameters import StateOccupancyError


def synthetic(states=2, n=80):
    rng = np.random.default_rng(222)
    return np.concatenate([rng.normal([j * 2.0, -j], [0.4 + j * 0.05, 0.6], (n // states, 2)) for j in range(states)])


def test_initialization_is_deterministic_and_matches_independent_kmeans():
    x = synthetic()
    config = EMConfig(2, seed=11)
    first = initialize_parameters(x, config)
    second = initialize_parameters(x, config)
    np.testing.assert_array_equal(first.means, second.means)
    labels = KMeans(n_clusters=2, n_init=4, random_state=11).fit_predict(x)
    for j in range(2):
        expected_mean = x[labels == j].mean(axis=0)
        expected_cov = np.diag(np.atleast_2d(np.cov(x[labels == j].T, bias=True)) + np.eye(2) * 1e-3)
        np.testing.assert_array_equal(first.means[j], expected_mean)
        np.testing.assert_array_equal(first.covars[j], expected_cov)
    np.testing.assert_array_equal(first.startprob, [0.5, 0.5])
    np.testing.assert_array_equal(first.transmat, [[0.9, 0.1], [0.1, 0.9]])


def test_one_gaussian_m_step_matches_manual_weighted_update():
    x = synthetic()
    config = EMConfig(2, seed=2, sticky=3.0, min_covar=1e-3)
    initial = initialize_parameters(x, config)
    step = e_step(initial.emission_logprob(x), initial.startprob, initial.transmat)
    updated, events = m_step(x, step, initial, config)
    gamma = step.gamma
    np.testing.assert_allclose(updated.startprob, gamma[0] / gamma[0].sum(), atol=1e-15)
    expected_trans = step.xi_counts + 3.0 * np.eye(2) + 1e-10
    expected_trans /= expected_trans.sum(axis=1, keepdims=True)
    np.testing.assert_array_equal(updated.transmat, expected_trans)
    for j in range(2):
        weight = gamma[:, j]
        mean = (weight[:, None] * x).sum(axis=0) / weight.sum()
        diff = x - mean
        cov = (weight[:, None] * diff ** 2).sum(axis=0) / weight.sum()
        np.testing.assert_array_equal(updated.means[j], mean)
        np.testing.assert_array_equal(updated.covars[j], np.maximum(cov, config.min_covar))
    assert events == 0

@pytest.mark.parametrize("covariance", ["diag", "full"])
def test_gaussian_training_log_likelihood_is_monotonic(covariance):
    fit = fit_hmm(synthetic(), 2, covariance_type=covariance, n_iter=12, tol=0.0, sticky=1.0, seed=7)
    assert np.all(np.diff(fit.history) >= -1e-8)
    assert fit.regularization_events >= (1 if covariance == "full" else 0)
    assert fit.loglik == fit.predictive_loglik(synthetic())[0]


def test_final_likelihood_is_recomputed_after_last_m_step():
    x = synthetic()
    fit = fit_hmm(x, 2, n_iter=1, tol=0.0, seed=7)
    assert fit.n_iter == 1 and not fit.converged and fit.loglik != fit.history[-1]
    assert fit.loglik == fit.predictive_loglik(x)[0]


def test_convergence_uses_original_relative_history_criterion():
    fit = fit_hmm(synthetic(), 2, n_iter=20, tol=1e6, seed=3)
    assert fit.converged and fit.n_iter == 2
    assert abs(fit.history[-1] - fit.history[-2]) < 1e6 * max(1.0, abs(fit.history[-1]))


def test_maximum_iteration_cap_is_explicit_nonconvergence():
    fit = fit_hmm(synthetic(), 2, n_iter=1, tol=0.0, seed=3)
    assert fit.n_iter == 1 and not fit.converged


def test_same_seed_reproduces_every_fit_array_and_history():
    x = synthetic()
    first = fit_hmm(x, 2, n_iter=5, seed=42, sticky=0.5)
    second = fit_hmm(x, 2, n_iter=5, seed=42, sticky=0.5)
    for name in ("startprob", "transmat", "means", "covars"):
        np.testing.assert_array_equal(getattr(first, name), getattr(second, name))
    np.testing.assert_array_equal(first.history, second.history)
    assert first.loglik == second.loglik


def test_sticky_prior_increases_persistence_in_one_update():
    x = synthetic()
    base_config = EMConfig(2, seed=2, sticky=0.0)
    initial = initialize_parameters(x, base_config)
    step = e_step(initial.emission_logprob(x), initial.startprob, initial.transmat)
    plain, _ = m_step(x, step, initial, base_config)
    sticky, _ = m_step(x, step, initial, EMConfig(2, seed=2, sticky=20.0))
    assert np.trace(sticky.transmat) > np.trace(plain.transmat)
    np.testing.assert_array_equal(sticky.means, plain.means)


def test_student_t_dof_stays_on_valid_grid_and_likelihood_is_monotonic():
    fit = fit_hmm(synthetic(), 2, emission="student_t", dof=6.0, n_iter=10, tol=0.0, seed=7, sticky=1.0)
    grid = {3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0}
    assert fit.dof in grid and np.all(np.diff(fit.history) >= -1e-7)


def synthetic_estep(x, gamma):
    k = gamma.shape[1]
    xi = np.full((k, k), max(len(x) - 1, 0) / (k * k))
    return EStep(np.zeros((len(x), k)), np.zeros(len(x)), np.zeros((len(x), k)), gamma, xi, 0.0)


def test_empty_posterior_component_is_rejected():
    x = np.zeros((6, 2))
    gamma = np.column_stack([np.ones(6), np.zeros(6)])
    config = EMConfig(2)
    initial = initialize_parameters(synthetic(), config)
    with pytest.raises(StateOccupancyError, match="no posterior mass"):
        m_step(x, synthetic_estep(x, gamma), initial, config)

@pytest.mark.parametrize("covariance", ["diag", "full"])
def test_covariance_regularization_is_explicit_and_returns_positive_covariance(covariance):
    x = np.zeros((6, 2))
    gamma = np.full((6, 2), 0.5)
    config = EMConfig(2, covariance_type=covariance, min_covar=1e-12)
    initial = initialize_parameters(synthetic(), config)
    updated, events = m_step(x, synthetic_estep(x, gamma), initial, config)
    assert events > 0
    if covariance == "diag":
        assert np.all(updated.covars >= config.min_covar)
    else:
        assert np.all(np.linalg.eigvalsh(updated.covars) >= 1e-8 - 1e-12)

@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_nonfinite_training_data_is_rejected(bad):
    x = synthetic()
    x[0, 0] = bad
    with pytest.raises(ValueError, match="finite"):
        fit_hmm(x, 2)


def test_low_sample_fit_is_rejected():
    with pytest.raises(ValueError, match="Training observations"):
        fit_hmm(np.zeros((3, 2)), 2)


def test_diagonal_diagnostics_count_only_actual_variance_floor_hits():
    x = synthetic()
    config = EMConfig(2, seed=2, min_covar=1e-12)
    initial = initialize_parameters(x, config)
    step = e_step(initial.emission_logprob(x), initial.startprob, initial.transmat)
    _, clean = m_step(x, step, initial, config, return_diagnostics=True)
    assert clean.as_dict() == {"regularization_applications": 0, "diagonal_variance_floor_hits": 0,
                               "eigenvalue_clipping_events": 0, "full_covariance_floor_applications": 0}
    zero = np.zeros((6, 2))
    gamma = np.full((6, 2), 0.5)
    updated, hits = m_step(zero, synthetic_estep(zero, gamma), initial, config, return_diagnostics=True)
    assert hits.as_dict() == {"regularization_applications": 4, "diagonal_variance_floor_hits": 4,
                              "eigenvalue_clipping_events": 0, "full_covariance_floor_applications": 0}
    _, legacy = m_step(zero, synthetic_estep(zero, gamma), initial, config)
    assert legacy == 4


def test_full_covariance_floor_is_not_eigenvalue_clipping():
    x = synthetic()
    config = EMConfig(2, covariance_type="full", seed=2, min_covar=1e-12)
    initial = initialize_parameters(x, config)
    step = e_step(initial.emission_logprob(x), initial.startprob, initial.transmat)
    _, diagnostics = m_step(x, step, initial, config, return_diagnostics=True)
    assert diagnostics.full_covariance_floor_applications == 2
    assert diagnostics.eigenvalue_clipping_events == 0
    assert diagnostics.diagonal_variance_floor_hits == 0
    assert diagnostics.regularization_applications == 2


def test_full_covariance_eigenvalue_clipping_is_counted_separately():
    x = np.zeros((6, 2))
    gamma = np.full((6, 2), 0.5)
    config = EMConfig(2, covariance_type="full", min_covar=1e-12)
    initial = initialize_parameters(synthetic(), config)
    updated, diagnostics = m_step(x, synthetic_estep(x, gamma), initial, config, return_diagnostics=True)
    assert diagnostics.full_covariance_floor_applications == 2
    assert diagnostics.eigenvalue_clipping_events == 4
    assert diagnostics.regularization_applications == 6
    _, legacy = m_step(x, synthetic_estep(x, gamma), initial, config)
    assert legacy == 6
    assert np.all(np.linalg.eigvalsh(updated.covars) >= 1e-8 - 1e-12)


def test_fit_preserves_legacy_aggregate_and_detailed_counter_sum():
    fit = fit_hmm(synthetic(), 2, covariance_type="full", n_iter=3, tol=0.0, seed=7)
    assert fit.full_covariance_floor_applications == fit.n_iter * fit.n_states
    assert fit.regularization_events == fit.regularization_applications
    assert fit.regularization_applications == (fit.diagonal_variance_floor_hits
                                                + fit.eigenvalue_clipping_events
                                                + fit.full_covariance_floor_applications)
