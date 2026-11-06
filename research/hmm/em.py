"""Original 1c EM updates refactored into testable initialization/E/M steps."""
from __future__ import annotations
import numpy as np
from scipy.special import gammaln
from .config import EMConfig
from .emissions import emission_logprob, _mahalanobis_sq
from .forward_backward import e_step, EStep
from .parameters import HMMFit, HMMParameters, StateOccupancyError

NEAREST_PD_EPSILON = 1e-8
TRANSITION_FLOOR = 1e-10
INITIAL_COVARIANCE_JITTER = 1e-3


def _training_array(x, n_states):
    values = np.asarray(x, dtype=float)
    if values.ndim != 2 or len(values) < n_states * 2 or not np.isfinite(values).all():
        raise ValueError("Training observations must be a finite non-empty 2D array")
    return values


def initialize_parameters(x, config):
    """Exact KMeans/biased-covariance initialization from 1c."""
    values = _training_array(x, config.n_states)
    from sklearn.cluster import KMeans
    n, d = values.shape
    k = config.n_states
    hard = KMeans(n_clusters=k, n_init=4, random_state=config.seed).fit_predict(values)
    startprob = np.full(k, 1.0 / k)
    transmat = np.full((k, k), 0.1 / max(k - 1, 1))
    np.fill_diagonal(transmat, 0.9)
    means = np.empty((k, d))
    covars = np.empty((k, d) if config.covariance_type == "diag" else (k, d, d))
    global_cov = np.atleast_2d(np.cov(values.T, bias=True))
    for j in range(k):
        mask = hard == j
        if mask.sum() < d + 1:
            means[j] = values.mean(axis=0)
            covars[j] = np.diag(global_cov) * 1.5 if config.covariance_type == "diag" else global_cov * 1.5
        else:
            means[j] = values[mask].mean(axis=0)
            cov = np.atleast_2d(np.cov(values[mask].T, bias=True)) + np.eye(d) * INITIAL_COVARIANCE_JITTER
            covars[j] = np.diag(cov) if config.covariance_type == "diag" else cov
    return HMMParameters(startprob, transmat, means, covars, config.covariance_type, config.emission, config.dof)


def _nearest_positive_definite(matrix, epsilon=NEAREST_PD_EPSILON):
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2)
    values = np.maximum(values, epsilon)
    return vectors @ np.diag(values) @ vectors.T


def _update_dof(x, means, covars, gamma, current):
    """Original shared-dof deterministic profile-likelihood grid."""
    grid = np.array([3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0])
    maha = _mahalanobis_sq(x, means, covars, "diag")
    n, d = x.shape
    scores = []
    for nu in grid:
        log_norm = gammaln((nu + d) / 2) - gammaln(nu / 2) - 0.5 * d * np.log(nu * np.pi)
        log_kernel = -0.5 * (nu + d) * np.log1p(maha / nu)
        scores.append(float((gamma * (log_norm + log_kernel)).sum()))
    return float(grid[int(np.argmax(scores))]) if max(scores) > -np.inf else current


def m_step(x, step, parameters, config):
    """Apply one original EM update and count actual covariance-floor events."""
    values = _training_array(x, config.n_states)
    n, d = values.shape
    k = config.n_states
    if parameters.emission == "student_t":
        maha = _mahalanobis_sq(values, parameters.means, parameters.covars, "diag")
        u = (parameters.dof + d) / (parameters.dof + maha)
    else:
        u = np.ones_like(step.gamma)
    startprob = np.maximum(step.gamma[0], 1e-12)
    startprob = startprob / startprob.sum()
    transmat = step.xi_counts + config.sticky * np.eye(k) + TRANSITION_FLOOR
    transmat /= transmat.sum(axis=1, keepdims=True)
    means = np.empty((k, d))
    covars = np.empty((k, d) if config.covariance_type == "diag" else (k, d, d))
    regularization_events = 0
    for j in range(k):
        w = step.gamma[:, j] * u[:, j]
        total = w.sum()
        if total <= 1e-10:
            raise StateOccupancyError("A state received no posterior mass during EM")
        means[j] = (w[:, None] * values).sum(axis=0) / total
        diff = values - means[j]
        if config.covariance_type == "diag":
            raw = (w[:, None] * diff ** 2).sum(axis=0) / total
            regularization_events += int((raw < config.min_covar).sum())
            covars[j] = np.maximum(raw, config.min_covar)
        else:
            covars[j] = ((w[:, None, None] * (diff[:, :, None] * diff[:, None, :])).sum(axis=0) / total)
            covars[j] += np.eye(d) * config.min_covar
            regularization_events += 1
            eigenvalues = np.linalg.eigvalsh((covars[j] + covars[j].T) / 2)
            regularization_events += int((eigenvalues < NEAREST_PD_EPSILON).sum())
            covars[j] = _nearest_positive_definite(covars[j])
    dof = parameters.dof
    if parameters.emission == "student_t":
        dof = _update_dof(values, means, covars, step.gamma, parameters.dof)
    return HMMParameters(startprob, transmat, means, covars, config.covariance_type,
                         config.emission, dof), regularization_events


def fit_config(x, config):
    """Fit using the original convergence criterion and no implicit fallback."""
    values = _training_array(x, config.n_states)
    parameters = initialize_parameters(values, config)
    history = []
    converged = False
    previous = -np.inf
    regularization_events = 0
    for iteration in range(1, config.n_iter + 1):
        log_emit = emission_logprob(values, parameters.means, parameters.covars,
                                    parameters.covariance_type, parameters.emission, parameters.dof)
        step = e_step(log_emit, parameters.startprob, parameters.transmat)
        loglik = step.loglik
        parameters, events = m_step(values, step, parameters, config)
        regularization_events += events
        history.append(float(loglik))
        if np.isfinite(previous) and abs(loglik - previous) < config.tol * max(1.0, abs(loglik)):
            converged = True
            break
        previous = loglik
    final_fit = HMMFit(startprob=np.asarray(parameters.startprob, dtype=float),
                       transmat=np.asarray(parameters.transmat, dtype=float),
                       means=np.asarray(parameters.means, dtype=float),
                       covars=np.asarray(parameters.covars, dtype=float),
                       covariance_type=config.covariance_type, emission=config.emission,
                       dof=None if parameters.dof is None else float(parameters.dof),
                       loglik=float(history[-1]), n_iter=iteration, converged=converged,
                       history=history, seed=config.seed, regularization_events=regularization_events)
    final_fit.loglik = final_fit.predictive_loglik(values)[0]
    return final_fit


def fit_hmm(x, n_states, *, covariance_type="diag", emission="gaussian", dof=None,
            n_iter=200, tol=1e-5, min_covar=1e-4, sticky=0.0, seed=0):
    """Original-compatible public signature."""
    return fit_config(x, EMConfig(n_states=n_states, covariance_type=covariance_type,
                                  emission=emission, dof=dof, n_iter=n_iter, tol=tol,
                                  min_covar=min_covar, sticky=sticky, seed=seed))
