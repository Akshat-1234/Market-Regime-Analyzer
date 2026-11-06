"""Log-space forward/backward recursions and explicit E-step posteriors."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .emissions import emission_logprob
from .parameters import HMMNumericalError


def _lse(a: np.ndarray, axis: int | None = None) -> np.ndarray:
    """Original 1c log-sum-exp operation order for numerical parity."""
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


def _validate_chain(startprob, transmat, k):
    start = np.asarray(startprob, dtype=float)
    trans = np.asarray(transmat, dtype=float)
    if start.shape != (k,) or not np.isfinite(start).all() or (start < 0).any():
        raise ValueError("startprob must be finite, nonnegative, and match emissions")
    if not np.isclose(start.sum(), 1.0, atol=1e-10, rtol=0):
        raise ValueError("startprob must sum to one")
    if trans.shape != (k, k) or not np.isfinite(trans).all() or (trans < 0).any():
        raise ValueError("transmat must be finite, nonnegative, and match emissions")
    if not np.allclose(trans.sum(axis=1), 1.0, atol=1e-10, rtol=0):
        raise ValueError("transmat rows must sum to one")


def _log_forward(log_emit, startprob, transmat, previous_log_alpha):
    """Exact valid-input 1c forward recursion."""
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
        raise HMMNumericalError("HMM filtering produced no finite posterior")
    log_pred[0] = loglik
    log_alpha[0] = alpha - loglik
    for t in range(1, n):
        alpha = _lse(log_alpha[t - 1][:, None] + log_trans, axis=0) + log_emit[t]
        loglik = _lse(alpha)
        if not np.isfinite(loglik):
            raise HMMNumericalError("HMM filtering produced no finite posterior")
        log_pred[t] = loglik
        log_alpha[t] = alpha - loglik
    return log_alpha, log_pred, float(log_pred.sum())


def filter_causal(means, covars, covariance_type, emission, dof, startprob, transmat,
                  x, previous_log_alpha=None):
    """Filtered posteriors, one-step predictive densities, and final log-alpha."""
    log_emit = emission_logprob(x, means, covars, covariance_type, emission, dof)
    _validate_chain(startprob, transmat, log_emit.shape[1])
    log_alpha, log_pred, _ = _log_forward(log_emit, startprob, transmat, previous_log_alpha)
    return np.exp(log_alpha), log_pred, log_alpha[-1]


def backward_log(log_emit, transmat):
    """Unscaled log-beta recursion used by the original EM implementation."""
    values = np.asarray(log_emit, dtype=float)
    if values.ndim != 2 or len(values) == 0 or np.isnan(values).any() or np.isposinf(values).any():
        raise ValueError("log_emit must be a nonempty 2D array without NaN/+inf")
    n, _ = values.shape
    log_beta = np.zeros_like(values)
    with np.errstate(divide="ignore"):
        log_trans = np.log(transmat)
    for t in range(n - 2, -1, -1):
        log_beta[t] = _lse(values[t + 1] + log_beta[t + 1] + log_trans, axis=1)
    if not np.isfinite(log_beta).all():
        raise HMMNumericalError("Backward recursion produced nonfinite values")
    return log_beta

@dataclass
class EStep:
    log_alpha: np.ndarray
    log_pred: np.ndarray
    log_beta: np.ndarray
    gamma: np.ndarray
    xi_counts: np.ndarray
    loglik: float


def e_step(log_emit, startprob, transmat):
    """Return filtered, smoothed and pairwise expected-count quantities."""
    values = np.asarray(log_emit, dtype=float)
    if values.ndim != 2 or len(values) == 0 or np.isnan(values).any() or np.isposinf(values).any():
        raise ValueError("log_emit must be a nonempty 2D array without NaN/+inf")
    _validate_chain(startprob, transmat, values.shape[1])
    log_alpha, log_pred, loglik = _log_forward(values, startprob, transmat, None)
    log_beta = backward_log(values, transmat)
    log_gamma = log_alpha + log_beta
    log_gamma -= _lse(log_gamma, axis=1)[:, None]
    gamma = np.exp(log_gamma)
    gamma /= gamma.sum(axis=1, keepdims=True)
    k = values.shape[1]
    if len(values) == 1:
        xi_counts = np.zeros((k, k), dtype=float)
    else:
        with np.errstate(divide="ignore"):
            log_trans = np.log(transmat)
        num = (log_alpha[:-1][:, :, None] + log_trans[None, :, :]
               + (values[1:] + log_beta[1:])[:, None, :])
        num -= _lse(num.reshape(len(num), -1), axis=1)[:, None, None]
        xi_counts = np.exp(num).sum(axis=0)
    return EStep(log_alpha, log_pred, log_beta, gamma, xi_counts, loglik)
