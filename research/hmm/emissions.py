"""Gaussian and Student-t log densities with exact valid-input 1c arithmetic."""
from __future__ import annotations
import numpy as np
from scipy.special import gammaln


def _log_gaussian(x, means, covars, covariance_type):
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
        z = np.linalg.solve(chol, diff.T)
        log_det = 2.0 * np.log(np.diag(chol)).sum()
        out[:, j] = -0.5 * (d * np.log(2 * np.pi) + log_det + (z ** 2).sum(axis=0))
    return out


def _mahalanobis_sq(x, means, covars, covariance_type):
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


def _log_student_t(x, means, covars, dof):
    """Multivariate Student-t with diagonal scale, not full covariance."""
    if dof <= 2:
        raise ValueError("Student-t dof must exceed 2 for a finite variance")
    n, d = x.shape
    maha = _mahalanobis_sq(x, means, covars, "diag")
    log_norm = (gammaln((dof + d) / 2) - gammaln(dof / 2) - 0.5 * d * np.log(dof * np.pi)
                - 0.5 * np.log(covars).sum(axis=1))
    return log_norm - 0.5 * (dof + d) * np.log1p(maha / dof)


def _validate(x, means, covars, covariance_type, emission, dof):
    x = np.asarray(x, dtype=float)
    means = np.asarray(means, dtype=float)
    covars = np.asarray(covars, dtype=float)
    if x.ndim != 2 or len(x) == 0 or x.shape[1] < 1 or not np.isfinite(x).all():
        raise ValueError("Observations must be a nonempty finite 2D array")
    if means.ndim != 2 or len(means) == 0 or not np.isfinite(means).all():
        raise ValueError("means must be a nonempty finite 2D array")
    n, d = x.shape
    k = len(means)
    if means.shape[1] != d:
        raise ValueError("Observation and mean feature dimensions must match")
    if covariance_type == "diag" and covars.ndim == 3:
        covars = np.einsum("kii->ki", covars)
    if covariance_type == "diag":
        if covars.shape != (k, d) or not np.isfinite(covars).all() or (covars <= 0).any():
            raise ValueError("Diagonal covariance must be finite, positive, and match means")
    elif covariance_type == "full":
        if covars.shape != (k, d, d) or not np.isfinite(covars).all():
            raise ValueError("Full covariance must be finite and match means")
        for matrix in covars:
            if not np.allclose(matrix, matrix.T, atol=1e-10, rtol=1e-10):
                raise ValueError("Full covariance must be symmetric")
            try:
                np.linalg.cholesky(matrix)
            except np.linalg.LinAlgError as exc:
                raise ValueError("Full emission covariances must be positive definite") from exc
    else:
        raise ValueError(f"Unknown covariance_type {covariance_type!r}")
    if emission == "student_t":
        if covariance_type != "diag":
            raise ValueError("Student-t emissions currently support diag scale only")
        if dof is None or not np.isfinite(dof) or dof <= 2:
            raise ValueError("Student-t emissions require finite dof > 2")
    elif emission != "gaussian":
        raise ValueError(f"Unknown emission {emission!r}")
    return x, means, covars


def emission_logprob(x, means, covars, covariance_type: str, emission: str, dof: float | None) -> np.ndarray:
    x, means, covars = _validate(x, means, covars, covariance_type, emission, dof)
    if emission == "gaussian":
        return _log_gaussian(x, means, covars, covariance_type)
    return _log_student_t(x, means, covars, float(dof))
