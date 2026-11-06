"""Self-contained EM / filtering for Gaussian and Student-t hidden Markov models.

Why this module exists
----------------------
``hmmlearn`` supports Gaussian emissions and an unconstrained transition matrix
only.  The research questions in this project require (a) heavy-tailed emissions
and (b) a duration/sticky prior, because financial daily returns are strongly
leptokurtic (excess kurtosis ~16 on the supplied NIFTY series).  Rewriting the
estimator keeps every assumption explicit and testable.

Guarantees
----------
* All recursions run in log space; no silent underflow is converted into a
  confident posterior.
* Only the forward recursion is exposed for decisions.  ``filter`` returns the
  *predictive* log-density of each observation given the past, which is exactly
  what an out-of-sample predictive-likelihood comparison needs.
* The Gaussian path is validated against ``hmmlearn`` (same parameters -> same
  log-likelihood and same filtered probabilities).

Not a general-purpose HMM library.  Long/cash research only; no smoothing is
used for trading decisions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.special import gammaln


def _lse(a: np.ndarray, axis: int | None = None) -> np.ndarray:
    """Fast log-sum-exp (scipy's wrapper is ~200 us per call here)."""
    a = np.asarray(a, dtype=float)
    if axis is None:
        m = np.max(a)
        if not np.isfinite(m):
            return m
        return m + np.log(np.exp(a - m).sum()).item()
    m = np.max(a, axis=axis, keepdims=True)
    m_safe = np.where(np.isfinite(m), m, 0.0)
    total = np.exp(a - m_safe).sum(axis=axis, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.log(total) + m_safe
    return np.squeeze(out, axis=axis)

COVARIANCE_TYPES = ("diag", "full")
EMISSION_TYPES = ("gaussian", "student_t")


def _log_gaussian(x: np.ndarray, means: np.ndarray, covars: np.ndarray,
                  covariance_type: str) -> np.ndarray:
    """(n, d) observations -> (n, k) log densities."""
    n, d = x.shape
    k = len(means)
    out = np.empty((n, k), dtype=float)
    if covariance_type == "diag":
        log_norm = -0.5 * (d * np.log(2 * np.pi) + np.log(covars).sum(axis=1))
        precision = 1.0 / covars
        for j in range(k):
            maha = ((x - means[j]) ** 2 * precision[j]).sum(axis=1)
            out[:, j] = log_norm[j] - 0.5 * maha
        return out
    if covariance_type != "full":
        raise ValueError(f"Unknown covariance_type {covariance_type!r}")
    for j in range(k):
        chol = np.linalg.cholesky(covars[j])
        diff = x - means[j]
        # Solve L z = diff^T; maha = |z|^2.
        z = np.linalg.solve(chol, diff.T)
        log_det = 2.0 * np.log(np.diag(chol)).sum()
        out[:, j] = -0.5 * (d * np.log(2 * np.pi) + log_det + (z ** 2).sum(axis=0))
    return out


def _mahalanobis_sq(x: np.ndarray, means: np.ndarray, covars: np.ndarray,
                    covariance_type: str) -> np.ndarray:
    n, d = x.shape
    k = len(means)
    out = np.empty((n, k), dtype=float)
    if covariance_type == "diag":
        precision = 1.0 / covars
        for j in range(k):
            out[:, j] = ((x - means[j]) ** 2 * precision[j]).sum(axis=1)
        return out
    for j in range(k):
        chol = np.linalg.cholesky(covars[j])
        z = np.linalg.solve(chol, (x - means[j]).T)
        out[:, j] = (z ** 2).sum(axis=0)
    return out


def _log_student_t(x: np.ndarray, means: np.ndarray, covars: np.ndarray,
                   dof: float) -> np.ndarray:
    """Multivariate Student-t with diagonal *scale* matrix (var = dof/(dof-2)*scale)."""
    if dof <= 2:
        raise ValueError("Student-t dof must exceed 2 for a finite variance")
    n, d = x.shape
    maha = _mahalanobis_sq(x, means, covars, "diag")
    log_norm = (gammaln((dof + d) / 2) - gammaln(dof / 2) - 0.5 * d * np.log(dof * np.pi)
                - 0.5 * np.log(covars).sum(axis=1))
    return log_norm - 0.5 * (dof + d) * np.log1p(maha / dof)


def emission_logprob(x, means, covars, covariance_type: str, emission: str,
                     dof: float | None) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim != 2:
        raise ValueError("Observations must be 2D")
    if emission == "gaussian":
        return _log_gaussian(x, means, covars, covariance_type)
    if emission == "student_t":
        if covariance_type != "diag":
            raise ValueError("Student-t emissions currently support diag scale only")
        if dof is None:
            raise ValueError("Student-t emissions require a dof")
        return _log_student_t(x, means, covars, float(dof))
    raise ValueError(f"Unknown emission {emission!r}")


def _log_forward(log_emit: np.ndarray, startprob: np.ndarray, transmat: np.ndarray,
                 previous_log_alpha: np.ndarray | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Log forward recursion. Returns (log_alpha, log_predictive, loglik)."""
    n, k = log_emit.shape
    with np.errstate(divide="ignore"):
        log_trans = np.log(transmat)
        log_start = np.log(startprob)
    log_alpha = np.empty((n, k), dtype=float)
    log_pred = np.empty(n, dtype=float)
    if previous_log_alpha is None:
        alpha = log_start + log_emit[0]
    else:
        prev = np.asarray(previous_log_alpha, dtype=float)
        if prev.shape != (k,) or not np.isfinite(_lse(prev)):
            raise ValueError("previous_log_alpha is invalid")
        alpha = _lse(prev[:, None] + log_trans, axis=0) + log_emit[0]
    loglik = _lse(alpha)
    if not np.isfinite(loglik):
        raise ValueError("HMM filtering produced no finite posterior")
    log_pred[0] = loglik
    log_alpha[0] = alpha - loglik
    for t in range(1, n):
        alpha = _lse(log_alpha[t - 1][:, None] + log_trans, axis=0) + log_emit[t]
        loglik = _lse(alpha)
        if not np.isfinite(loglik):
            raise ValueError("HMM filtering produced no finite posterior")
        log_pred[t] = loglik
        log_alpha[t] = alpha - loglik
    return log_alpha, log_pred, float(log_pred.sum())


def filter_causal(means, covars, covariance_type, emission, dof, startprob, transmat,
                  x: np.ndarray, previous_log_alpha: np.ndarray | None = None
                  ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Filtered posteriors, predictive log-densities and the final log alpha."""
    log_emit = emission_logprob(x, means, covars, covariance_type, emission, dof)
    log_alpha, log_pred, loglik = _log_forward(log_emit, startprob, transmat, previous_log_alpha)
    return np.exp(log_alpha), log_pred, log_alpha[-1]


@dataclass
class HMMFit:
    """Fitted parameters plus provenance of the optimisation."""

    startprob: np.ndarray
    transmat: np.ndarray
    means: np.ndarray
    covars: np.ndarray
    covariance_type: str
    emission: str = "gaussian"
    dof: float | None = None
    loglik: float = float("nan")
    n_iter: int = 0
    converged: bool = False
    history: list[float] = field(default_factory=list)
    seed: int = 0

    def __post_init__(self) -> None:
        # hmmlearn returns (k, d, d) covars even for diag; normalise that shape.
        self.covars = np.asarray(self.covars, dtype=float)
        if self.covariance_type == "diag" and self.covars.ndim == 3:
            self.covars = np.einsum("kii->ki", self.covars)
        if self.covariance_type == "diag":
            if self.covars.ndim != 2 or (self.covars <= 0).any():
                raise ValueError("Diagonal emission variances must be positive and 2D")
        else:
            if self.covars.ndim != 3:
                raise ValueError("Full emission covariances must be 3D")
            for matrix in self.covars:
                np.linalg.cholesky(matrix)

    @property
    def n_states(self) -> int:
        return len(self.startprob)

    @property
    def n_features(self) -> int:
        return self.means.shape[1]

    def n_parameters(self) -> int:
        k, d = self.n_states, self.n_features
        p = (k - 1) + k * (k - 1) + k * d
        p += k * d if self.covariance_type == "diag" else k * d * (d + 1) // 2
        if self.emission == "student_t":
            p += 1
        return int(p)

    def emission_logprob(self, x: np.ndarray) -> np.ndarray:
        return emission_logprob(x, self.means, self.covars, self.covariance_type,
                                self.emission, self.dof)

    def filter(self, x: np.ndarray, previous_log_alpha: np.ndarray | None = None
               ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return filter_causal(self.means, self.covars, self.covariance_type, self.emission,
                             self.dof, self.startprob, self.transmat, x, previous_log_alpha)

    def predictive_loglik(self, x: np.ndarray, previous_log_alpha: np.ndarray | None = None
                          ) -> tuple[float, np.ndarray]:
        _, log_pred, final_alpha = self.filter(x, previous_log_alpha)
        return float(log_pred.sum()), final_alpha


def fit_hmm(x: np.ndarray, n_states: int, *, covariance_type: str = "diag",
            emission: str = "gaussian", dof: float | None = None,
            n_iter: int = 200, tol: float = 1e-5, min_covar: float = 1e-4,
            sticky: float = 0.0, seed: int = 0) -> HMMFit:
    """EM for a Gaussian or Student-t HMM.

    ``sticky`` adds ``sticky`` pseudo-observations to each diagonal transition
    count (a Dirichlet prior centred on staying). It is the duration control:
    ``sticky=0`` is the ordinary maximum-likelihood HMM.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or len(x) < n_states * 2 or not np.isfinite(x).all():
        raise ValueError("Training observations must be a finite non-empty 2D array")
    if covariance_type not in COVARIANCE_TYPES:
        raise ValueError(f"covariance_type must be one of {COVARIANCE_TYPES}")
    if emission not in EMISSION_TYPES:
        raise ValueError(f"emission must be one of {EMISSION_TYPES}")
    if emission == "student_t" and covariance_type != "diag":
        raise ValueError("Student-t emissions support diag scale only")
    if emission == "student_t" and (dof is None or dof <= 2):
        raise ValueError("Student-t emissions need dof > 2")

    n, d = x.shape
    if n_iter < 1:
        raise ValueError("n_iter must be positive")
    from sklearn.cluster import KMeans

    hard = KMeans(n_clusters=n_states, n_init=4, random_state=seed).fit_predict(x)
    startprob = np.full(n_states, 1.0 / n_states)
    transmat = np.full((n_states, n_states), 0.1 / max(n_states - 1, 1))
    np.fill_diagonal(transmat, 0.9)
    means = np.empty((n_states, d))
    covars = np.empty((n_states, d) if covariance_type == "diag" else (n_states, d, d))
    global_cov = np.atleast_2d(np.cov(x.T, bias=True))
    for j in range(n_states):
        mask = hard == j
        if mask.sum() < d + 1:
            means[j] = x.mean(axis=0)
            covars[j] = np.diag(global_cov) * 1.5 if covariance_type == "diag" else global_cov * 1.5
        else:
            means[j] = x[mask].mean(axis=0)
            cov = np.atleast_2d(np.cov(x[mask].T, bias=True)) + np.eye(d) * 1e-3
            covars[j] = np.diag(cov) if covariance_type == "diag" else cov

    history: list[float] = []
    converged = False
    previous = -np.inf
    for iteration in range(1, n_iter + 1):
        log_emit = emission_logprob(x, means, covars, covariance_type, emission, dof)
        log_alpha, log_pred, loglik = _log_forward(log_emit, startprob, transmat, None)
        # Backward recursion (diagnostics/EM only, never a trading signal).
        log_beta = np.zeros_like(log_alpha)
        with np.errstate(divide="ignore"):
            log_trans_diag_free = np.log(transmat)
        for t in range(n - 2, -1, -1):
            log_beta[t] = _lse(log_emit[t + 1] + log_beta[t + 1] + log_trans_diag_free, axis=1)
        if not np.isfinite(log_beta).any():
            raise ValueError("Backward recursion produced no finite values")
        log_gamma = log_alpha + log_beta
        log_gamma -= _lse(log_gamma, axis=1)[:, None]
        gamma = np.exp(log_gamma)
        gamma /= gamma.sum(axis=1, keepdims=True)

        if emission == "student_t":
            maha = _mahalanobis_sq(x, means, covars, "diag")
            u = (dof + d) / (dof + maha)
        else:
            u = np.ones_like(gamma)

        # Transition expected counts.  With normalised alpha,
        #   xi_t(i,j) = gamma_t(i) A_ij b_j(x_{t+1}) beta_{t+1}(j) / S_t,
        # where S_t is the (i,j) normaliser, i.e. p(x_{t+1..T} | x_<=t).  Dividing
        # only by c_{t+1} would leave xi rows that do not equal state occupancy.
        with np.errstate(divide="ignore"):
            log_trans = np.log(transmat)
        num = (log_alpha[:-1][:, :, None] + log_trans[None, :, :]
               + (log_emit[1:] + log_beta[1:])[:, None, :])
        num -= _lse(num.reshape(len(num), -1), axis=1)[:, None, None]
        xi_counts = np.exp(num).sum(axis=0)

        startprob = np.maximum(gamma[0], 1e-12)
        startprob = startprob / startprob.sum()
        # A tiny floor keeps the chain irreducible; a structural zero would make
        # log(0) infinite and silently destroy the backward recursion.
        transmat = xi_counts + sticky * np.eye(n_states) + 1e-10
        transmat /= transmat.sum(axis=1, keepdims=True)

        for j in range(n_states):
            w = gamma[:, j] * u[:, j]
            total = w.sum()
            if total <= 1e-10:
                raise ValueError("A state received no posterior mass during EM")
            means[j] = (w[:, None] * x).sum(axis=0) / total
            diff = x - means[j]
            if covariance_type == "diag":
                covars[j] = np.maximum((w[:, None] * diff ** 2).sum(axis=0) / total, min_covar)
            else:
                covars[j] = ((w[:, None, None] * (diff[:, :, None] * diff[:, None, :])).sum(axis=0)
                             / total)
                covars[j] += np.eye(d) * min_covar
                covars[j] = _nearest_positive_definite(covars[j])

        if emission == "student_t":
            dof = _update_dof(x, means, covars, gamma, dof)

        history.append(float(loglik))
        if np.isfinite(previous) and abs(loglik - previous) < tol * max(1.0, abs(loglik)):
            converged = True
            break
        previous = loglik

    final_fit = HMMFit(startprob=np.asarray(startprob, dtype=float),
                       transmat=np.asarray(transmat, dtype=float),
                       means=np.asarray(means, dtype=float),
                       covars=np.asarray(covars, dtype=float),
                       covariance_type=covariance_type, emission=emission,
                       dof=None if dof is None else float(dof), loglik=float(history[-1]),
                       n_iter=iteration, converged=converged, history=history, seed=seed)
    # Recompute the likelihood of the returned parameters, not of the E-step.
    final_fit.loglik = final_fit.predictive_loglik(x)[0]
    return final_fit


def _nearest_positive_definite(matrix: np.ndarray, epsilon: float = 1e-8) -> np.ndarray:
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2)
    values = np.maximum(values, epsilon)
    return vectors @ np.diag(values) @ vectors.T


def _update_dof(x: np.ndarray, means: np.ndarray, covars: np.ndarray,
                gamma: np.ndarray, current: float) -> float:
    """Shared Student-t dof by a deterministic profile-likelihood grid."""
    grid = np.array([3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0])
    maha = _mahalanobis_sq(x, means, covars, "diag")
    n, d = x.shape
    scores = []
    for nu in grid:
        log_norm = gammaln((nu + d) / 2) - gammaln(nu / 2) - 0.5 * d * np.log(nu * np.pi)
        log_kernel = -0.5 * (nu + d) * np.log1p(maha / nu)
        scores.append(float((gamma * (log_norm + log_kernel)).sum()))
    return float(grid[int(np.argmax(scores))]) if max(scores) > -np.inf else current
