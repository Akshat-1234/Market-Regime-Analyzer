"""Validated HMM parameters and fit diagnostics; no semantic state ordering."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np
from .config import COVARIANCE_TYPES, EMISSION_TYPES

class HMMNumericalError(ValueError):
    """Numerical failure during valid HMM evaluation or fitting."""

class StateOccupancyError(ValueError):
    """A state has no usable posterior mass during EM."""

@dataclass
class HMMParameters:
    startprob: np.ndarray
    transmat: np.ndarray
    means: np.ndarray
    covars: np.ndarray
    covariance_type: str
    emission: str = "gaussian"
    dof: float | None = None

    def __post_init__(self) -> None:
        self.startprob = np.asarray(self.startprob, dtype=float)
        self.transmat = np.asarray(self.transmat, dtype=float)
        self.means = np.asarray(self.means, dtype=float)
        self.covars = np.asarray(self.covars, dtype=float)
        if self.covariance_type == "diag" and self.covars.ndim == 3:
            self.covars = np.einsum("kii->ki", self.covars)
        if self.covariance_type not in COVARIANCE_TYPES:
            raise ValueError(f"Unknown covariance_type {self.covariance_type!r}")
        if self.emission not in EMISSION_TYPES:
            raise ValueError(f"Unknown emission {self.emission!r}")
        if self.startprob.ndim != 1 or len(self.startprob) < 2:
            raise ValueError("startprob must contain at least two states")
        k = len(self.startprob)
        if self.means.ndim != 2 or self.means.shape[0] != k or self.means.shape[1] < 1:
            raise ValueError("means must have shape (n_states, n_features)")
        d = self.means.shape[1]
        if self.transmat.shape != (k, k):
            raise ValueError("transmat must be square and match n_states")
        for name, array in (("startprob", self.startprob), ("transmat", self.transmat),
                            ("means", self.means), ("covars", self.covars)):
            if not np.isfinite(array).all():
                raise ValueError(f"{name} must be finite")
        if (self.startprob < 0).any() or not np.isclose(self.startprob.sum(), 1.0, atol=1e-10, rtol=0):
            raise ValueError("startprob must be nonnegative and sum to one")
        if (self.transmat < 0).any() or not np.allclose(self.transmat.sum(axis=1), 1.0, atol=1e-10, rtol=0):
            raise ValueError("transmat rows must be nonnegative and sum to one")
        if self.covariance_type == "diag":
            if self.covars.shape != (k, d) or (self.covars <= 0).any():
                raise ValueError("Diagonal emission variances must be positive with shape (n_states, n_features)")
        else:
            if self.covars.shape != (k, d, d):
                raise ValueError("Full emission covariances must have shape (n_states, n_features, n_features)")
            for matrix in self.covars:
                if not np.allclose(matrix, matrix.T, atol=1e-10, rtol=1e-10):
                    raise ValueError("Full emission covariances must be symmetric")
                try:
                    np.linalg.cholesky(matrix)
                except np.linalg.LinAlgError as exc:
                    raise ValueError("Full emission covariances must be positive definite") from exc
        if self.emission == "student_t":
            if self.covariance_type != "diag":
                raise ValueError("Student-t emissions support diag scale only")
            if self.dof is None or not np.isfinite(self.dof) or self.dof <= 2:
                raise ValueError("Student-t emissions need finite dof > 2")
        elif self.dof is not None and not np.isfinite(self.dof):
            raise ValueError("dof must be finite when supplied")

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

    def parameter_dict(self) -> dict[str, Any]:
        return {"startprob": self.startprob.tolist(), "transmat": self.transmat.tolist(),
                "means": self.means.tolist(), "covars": self.covars.tolist(),
                "covariance_type": self.covariance_type, "emission": self.emission, "dof": self.dof}

    def emission_logprob(self, x: np.ndarray) -> np.ndarray:
        from .emissions import emission_logprob
        return emission_logprob(x, self.means, self.covars, self.covariance_type, self.emission, self.dof)

    def filter(self, x: np.ndarray, previous_log_alpha: np.ndarray | None = None):
        from .forward_backward import filter_causal
        return filter_causal(self.means, self.covars, self.covariance_type, self.emission,
                             self.dof, self.startprob, self.transmat, x, previous_log_alpha)

    def predictive_loglik(self, x: np.ndarray, previous_log_alpha: np.ndarray | None = None):
        _, log_pred, final_alpha = self.filter(x, previous_log_alpha)
        return float(log_pred.sum()), final_alpha

@dataclass(frozen=True)
class RegularizationDiagnostics:
    """Precise covariance-operation counters; none is an instability score.

    ``regularization_applications`` is the legacy-compatible sum of diagonal
    variance floor hits, full-covariance floor applications, and clipped
    eigenvalues. Full covariance matrices always receive the configured
    diagonal floor, whether or not eigenvalue clipping is subsequently needed.
    """
    regularization_applications: int = 0
    diagonal_variance_floor_hits: int = 0
    eigenvalue_clipping_events: int = 0
    full_covariance_floor_applications: int = 0

    def __post_init__(self) -> None:
        for name in ("regularization_applications", "diagonal_variance_floor_hits",
                     "eigenvalue_clipping_events", "full_covariance_floor_applications"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        expected = (self.diagonal_variance_floor_hits + self.eigenvalue_clipping_events
                    + self.full_covariance_floor_applications)
        if self.regularization_applications != expected:
            raise ValueError("regularization_applications must equal the sum of detailed counters")

    @property
    def legacy_events(self) -> int:
        return self.regularization_applications

    def as_dict(self) -> dict[str, int]:
        return {name: getattr(self, name) for name in (
            "regularization_applications", "diagonal_variance_floor_hits",
            "eigenvalue_clipping_events", "full_covariance_floor_applications")}

    def __add__(self, other: "RegularizationDiagnostics") -> "RegularizationDiagnostics":
        if not isinstance(other, RegularizationDiagnostics):
            return NotImplemented
        return RegularizationDiagnostics(**{
            name: getattr(self, name) + getattr(other, name) for name in self.as_dict()})


@dataclass
class HMMFit(HMMParameters):
    """Fitted parameters plus original-compatible convergence diagnostics."""
    loglik: float = float("nan")
    n_iter: int = 0
    converged: bool = False
    history: list[float] = field(default_factory=list)
    seed: int = 0
    regularization_events: int = 0
    regularization_applications: int = 0
    diagonal_variance_floor_hits: int = 0
    eigenvalue_clipping_events: int = 0
    full_covariance_floor_applications: int = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.n_iter, bool) or not isinstance(self.n_iter, int) or self.n_iter < 0:
            raise ValueError("n_iter must be a nonnegative integer")
        if not isinstance(self.converged, bool):
            raise ValueError("converged must be explicit")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if (isinstance(self.regularization_events, bool) or
                not isinstance(self.regularization_events, int) or self.regularization_events < 0):
            raise ValueError("regularization_events must be a nonnegative integer")
        for name in ("regularization_applications", "diagonal_variance_floor_hits",
                     "eigenvalue_clipping_events", "full_covariance_floor_applications"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if (isinstance(self.loglik, (bool, np.bool_)) or
                not isinstance(self.loglik, (int, float, np.integer, np.floating))):
            raise ValueError("loglik must be numeric or NaN for an unfitted model")
        self.loglik = float(self.loglik)
        if np.isinf(self.loglik):
            raise ValueError("loglik must be finite or NaN for an unfitted model")
        self.history = [float(value) for value in self.history]
        if not np.isfinite(self.history).all():
            raise ValueError("fit history must be finite")
