from __future__ import annotations
import numpy as np
import pytest
from scipy.special import gammaln
from scipy.stats import multivariate_normal, norm, t as student_t
from research.hmm.emissions import emission_logprob
from research.hmm.parameters import HMMFit


def test_gaussian_diag_matches_scipy_independent_reference(diag_fit):
    x = np.array([[-1.2, 0.1], [0.0, 0.5], [2.0, -1.0], [1e4, -1e4]])
    actual = diag_fit.emission_logprob(x)
    expected = np.column_stack([multivariate_normal.logpdf(x, mean=diag_fit.means[j], cov=np.diag(diag_fit.covars[j]))
                                for j in range(diag_fit.n_states)])
    np.testing.assert_allclose(actual, expected, rtol=2e-13, atol=2e-13)
    assert actual.shape == (4, 2) and np.isfinite(actual).all()


def test_gaussian_full_matches_scipy_independent_reference(full_fit):
    x = np.array([[-1.2, 0.1], [0.0, 0.5], [2.0, -1.0], [1e4, -1e4]])
    actual = full_fit.emission_logprob(x)
    expected = np.column_stack([multivariate_normal.logpdf(x, mean=full_fit.means[j], cov=full_fit.covars[j])
                                for j in range(full_fit.n_states)])
    np.testing.assert_allclose(actual, expected, rtol=2e-13, atol=2e-13)


def test_one_dimensional_gaussian_multiple_states_matches_norm():
    x = np.array([[-2.0], [0.0], [3.0]])
    means = np.array([[-1.0], [0.5], [2.0]])
    covars = np.array([[0.4], [1.2], [2.0]])
    actual = emission_logprob(x, means, covars, "diag", "gaussian", None)
    expected = np.column_stack([norm.logpdf(x[:, 0], loc=means[j, 0], scale=np.sqrt(covars[j, 0])) for j in range(3)])
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-14)


def test_student_t_diag_matches_independent_multivariate_formula(student_fit):
    x = np.array([[-1.2, 0.1], [0.0, 0.5], [2.0, -1.0], [1e4, -1e4]])
    actual = student_fit.emission_logprob(x)
    dof = student_fit.dof
    d = x.shape[1]
    expected = np.empty_like(actual)
    for j in range(student_fit.n_states):
        diff = x - student_fit.means[j]
        maha = (diff ** 2 / student_fit.covars[j]).sum(axis=1)
        log_norm = (gammaln((dof + d) / 2) - gammaln(dof / 2) - 0.5 * d * np.log(dof * np.pi)
                    - 0.5 * np.log(student_fit.covars[j]).sum())
        expected[:, j] = log_norm - 0.5 * (dof + d) * np.log1p(maha / dof)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-13)


def test_one_dimensional_student_t_matches_scipy():
    x = np.array([[-3.0], [0.0], [4.0]])
    means = np.array([[0.0], [1.0]])
    covars = np.array([[1.5], [0.7]])
    actual = emission_logprob(x, means, covars, "diag", "student_t", 5.0)
    expected = np.column_stack([student_t.logpdf(x[:, 0], 5.0, loc=means[j, 0], scale=np.sqrt(covars[j, 0])) for j in range(2)])
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-13)


def test_extreme_valid_observations_and_nearly_singular_pd_remain_finite(diag_fit, full_fit):
    extreme = np.array([[1e100, -1e100]])
    assert np.isfinite(diag_fit.emission_logprob(extreme)).all()
    covars = np.array([[[1.0, 1.0 - 1e-12], [1.0 - 1e-12, 1.0]]])
    actual = emission_logprob([[0.0, 0.0]], np.zeros((1, 2)), covars, "full", "gaussian", None)
    assert actual.shape == (1, 1) and np.isfinite(actual).all()
    assert np.isfinite(full_fit.emission_logprob(extreme)).all()

@pytest.mark.parametrize("covars,match", [
    (np.array([[-1.0, 0.5]]), "positive"), (np.array([[np.nan, 0.5]]), "finite"),
    (np.array([[[1.0, 2.0], [2.0, 1.0]]]), "positive definite"),
    (np.array([[[1.0, 0.2], [0.1, 1.0]]]), "symmetric")])
def test_invalid_covariance_is_rejected_not_regularized(covars, match):
    covariance = "diag" if covars.ndim == 2 else "full"
    with pytest.raises(ValueError, match=match):
        emission_logprob([[0.0, 0.0]], np.zeros((1, 2)), covars, covariance, "gaussian", None)


def test_singular_and_invalid_covariance_shapes_are_rejected():
    with pytest.raises(ValueError, match="positive definite"):
        emission_logprob([[0.0, 0.0]], np.zeros((1, 2)), np.array([[[1.0, 1.0], [1.0, 1.0]]]), "full", "gaussian", None)
    with pytest.raises(ValueError, match="match means"):
        emission_logprob([[0.0, 0.0]], np.zeros((1, 2)), np.ones((2, 2)), "diag", "gaussian", None)


def test_nonfinite_and_wrong_dimensional_observations_are_rejected(diag_fit):
    for x in ([1.0, 2.0], [[np.nan, 0.0]], [[np.inf, 0.0]], []):
        with pytest.raises(ValueError, match="Observations"):
            diag_fit.emission_logprob(np.asarray(x))


def test_student_t_full_covariance_is_deliberately_rejected(full_fit):
    from research.hmm.config import EMConfig
    with pytest.raises(ValueError, match="diag scale only"):
        emission_logprob([[0.0, 0.0]], full_fit.means, full_fit.covars, "full", "student_t", 6.0)
    with pytest.raises(ValueError, match="diag scale only"):
        EMConfig(2, covariance_type="full", emission="student_t", dof=6.0)
    with pytest.raises(ValueError, match="diag scale only"):
        HMMFit(full_fit.startprob, full_fit.transmat, full_fit.means, full_fit.covars, "full", "student_t", 6.0)

@pytest.mark.parametrize("dof", [None, 2.0, -1.0, np.nan, np.inf])
def test_invalid_student_t_dof_is_rejected(diag_fit, dof):
    with pytest.raises(ValueError, match="dof"):
        emission_logprob([[0.0, 0.0]], diag_fit.means, diag_fit.covars, "diag", "student_t", dof)


def test_hmmfit_diag_matrix_conversion_and_full_validation(diag_fit):
    matrices = np.array([np.diag(row) for row in diag_fit.covars])
    converted = HMMFit(diag_fit.startprob, diag_fit.transmat, diag_fit.means, matrices, "diag")
    np.testing.assert_array_equal(converted.covars, diag_fit.covars)
    with pytest.raises(ValueError, match="positive definite"):
        HMMFit([1.0, 0.0], [[1.0, 0.0], [0.0, 1.0]], np.zeros((2, 2)),
               np.array([[[1.0, 1.0], [1.0, 1.0]], np.eye(2)]), "full")
