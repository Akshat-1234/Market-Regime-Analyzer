from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from hmmlearn.hmm import GaussianHMM
import sklearn.cluster
from research.contracts.model import InferenceKind, ProbabilityBlock
from research.contracts.state import align_training_states, apply_alignment
from research.hmm.em import fit_hmm, initialize_parameters
from research.hmm.config import EMConfig
from research.hmm.emissions import emission_logprob
from research.hmm.forward_backward import e_step


def observations():
    rng = np.random.default_rng(123)
    return np.concatenate([rng.normal(-1, 0.4, (80, 2)), rng.normal(1, 0.7, (80, 2))])


def assert_fit_parity(original, migrated):
    for name in ("startprob", "transmat", "means", "covars"):
        np.testing.assert_array_equal(getattr(migrated, name), getattr(original, name))
    assert migrated.covariance_type == original.covariance_type and migrated.emission == original.emission
    assert migrated.dof == original.dof and migrated.loglik == original.loglik
    assert migrated.n_iter == original.n_iter and migrated.converged == original.converged
    np.testing.assert_array_equal(migrated.history, original.history)
    assert migrated.seed == original.seed


def test_original_kmeans_initialization_is_identical(original_emhmm, monkeypatch):
    x = observations()
    captured = []
    parent = sklearn.cluster.KMeans
    class CapturingKMeans(parent):
        def fit_predict(self, *args, **kwargs):
            result = super().fit_predict(*args, **kwargs)
            captured.append(self)
            return result
    with monkeypatch.context() as patch:
        patch.setattr(sklearn.cluster, "KMeans", CapturingKMeans)
        original_emhmm.fit_hmm(x, 2, n_iter=1, tol=0.0, sticky=2.0, seed=7)
    assert len(captured) == 1
    kmeans = captured[0]
    assert kmeans.n_init == 4 and kmeans.random_state == 7
    migrated = initialize_parameters(x, EMConfig(2, sticky=2.0, seed=7))
    for j, mask in enumerate((kmeans.labels_ == 0, kmeans.labels_ == 1)):
        np.testing.assert_array_equal(migrated.means[j], x[mask].mean(axis=0))

@pytest.mark.parametrize("emission,covariance,dof", [("gaussian", "diag", None), ("gaussian", "full", None), ("student_t", "diag", 6.0)])
def test_emissions_are_bitwise_identical_to_original(original_emhmm, emission, covariance, dof):
    rng = np.random.default_rng(991)
    x = np.concatenate([rng.normal(size=(8, 2)), np.array([[1e6, -1e6], [-1e6, 1e6]])])
    means = np.array([[-1.0, 0.0], [1.0, 1.0]])
    covars = (np.array([[0.5, 0.8], [0.7, 1.2]]) if covariance == "diag" else
              np.array([[[0.5, 0.1], [0.1, 0.8]], [[0.7, -0.2], [-0.2, 1.1]]]))
    old = original_emhmm.emission_logprob(x, means, covars, covariance, emission, dof)
    new = emission_logprob(x, means, covars, covariance, emission, dof)
    np.testing.assert_array_equal(new, old)

@pytest.mark.parametrize("emission,covariance,dof", [("gaussian", "diag", None), ("gaussian", "full", None), ("student_t", "diag", 6.0)])
def test_fit_parity_is_bitwise_identical_with_sticky_prior(original_emhmm, emission, covariance, dof):
    x = observations()
    kwargs = dict(n_states=2, covariance_type=covariance, emission=emission, dof=dof,
                  n_iter=7, tol=0.0, sticky=2.0, seed=7, min_covar=1e-4)
    assert_fit_parity(original_emhmm.fit_hmm(x, **kwargs), fit_hmm(x, **kwargs))


def test_forward_filter_and_chunked_oos_are_bitwise_identical(original_emhmm, diag_fit):
    x = observations()[:50]
    parameters = diag_fit.parameter_dict()
    for name in ("means", "covars", "startprob", "transmat"):
        parameters[name] = np.asarray(parameters[name], dtype=float)
    original = original_emhmm.filter_causal(parameters["means"], parameters["covars"], "diag", "gaussian", None,
                                            parameters["startprob"], parameters["transmat"], x[:20])
    migrated = diag_fit.filter(x[:20])
    for new, old in zip(migrated, original):
        np.testing.assert_array_equal(new, old)
    old_oos = original_emhmm.filter_causal(parameters["means"], parameters["covars"], "diag", "gaussian", None,
                                           parameters["startprob"], parameters["transmat"], x[20:], original[2])
    new_oos = diag_fit.filter(x[20:], migrated[2])
    for new, old in zip(new_oos, old_oos):
        np.testing.assert_array_equal(new, old)


def test_smoothing_is_bitwise_identical_to_original_internal_backward_math(original_emhmm, diag_fit):
    x = observations()[:30]
    parameters = diag_fit.parameter_dict()
    for name in ("means", "covars", "startprob", "transmat"):
        parameters[name] = np.asarray(parameters[name], dtype=float)
    emit = original_emhmm.emission_logprob(x, parameters["means"], parameters["covars"], "diag", "gaussian", None)
    old_alpha, old_pred, old_likelihood = original_emhmm._log_forward(emit, parameters["startprob"], parameters["transmat"], None)
    old_beta = np.zeros_like(emit)
    log_trans = np.log(parameters["transmat"])
    for t in range(len(x) - 2, -1, -1):
        old_beta[t] = original_emhmm._lse(emit[t + 1] + old_beta[t + 1] + log_trans, axis=1)
    old_log_gamma = old_alpha + old_beta
    old_log_gamma -= original_emhmm._lse(old_log_gamma, axis=1)[:, None]
    old_gamma = np.exp(old_log_gamma)
    old_gamma /= old_gamma.sum(axis=1, keepdims=True)
    new = e_step(diag_fit.emission_logprob(x), diag_fit.startprob, diag_fit.transmat)
    np.testing.assert_array_equal(new.log_alpha, old_alpha)
    np.testing.assert_array_equal(new.log_pred, old_pred)
    np.testing.assert_array_equal(new.log_beta, old_beta)
    np.testing.assert_array_equal(new.gamma, old_gamma)
    assert new.loglik == old_likelihood


def test_state_label_alignment_handles_permutation_without_changing_values(original_emhmm):
    x = observations()
    old = original_emhmm.fit_hmm(x, 2, n_iter=5, tol=0.0, seed=7)
    new = fit_hmm(x, 2, n_iter=5, tol=0.0, seed=7)
    reference_probs = old.filter(x)[0]
    migrated_probs = new.filter(x)[0]
    np.testing.assert_array_equal(reference_probs, migrated_probs)
    dates = pd.date_range("2020-01-01", periods=len(x), freq="B")
    reference = ProbabilityBlock(dates, reference_probs, ("ref_0", "ref_1"), InferenceKind.TRAINING_FILTERED)
    current = ProbabilityBlock(dates, migrated_probs[:, [1, 0]], ("new_0", "new_1"), InferenceKind.TRAINING_FILTERED)
    alignment = align_training_states(reference, current)
    aligned = apply_alignment(current, alignment)
    assert alignment.agreement == 1.0
    np.testing.assert_array_equal(aligned, reference_probs)


def test_hmmlearn_independently_checks_likelihood_and_smoothing(full_fit):
    x = np.random.default_rng(912).normal(size=(40, 2))
    reference = GaussianHMM(n_components=2, covariance_type="full", implementation="log")
    reference.startprob_ = full_fit.startprob
    reference.transmat_ = full_fit.transmat
    reference.means_ = full_fit.means
    reference.covars_ = full_fit.covars
    old_likelihood, old_gamma = reference.score_samples(x)
    new = e_step(full_fit.emission_logprob(x), full_fit.startprob, full_fit.transmat)
    assert new.loglik == pytest.approx(old_likelihood, rel=1e-11, abs=1e-9)
    np.testing.assert_allclose(new.gamma, old_gamma, rtol=1e-10, atol=1e-10)
