"""Explicit numerical configuration for the migrated 1c EM engine."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

COVARIANCE_TYPES = ("diag", "full")
EMISSION_TYPES = ("gaussian", "student_t")

@dataclass(frozen=True)
class EMConfig:
    n_states: int
    covariance_type: str = "diag"
    emission: str = "gaussian"
    dof: float | None = None
    n_iter: int = 200
    tol: float = 1e-5
    min_covar: float = 1e-4
    sticky: float = 0.0
    seed: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.n_states, bool) or not isinstance(self.n_states, int) or self.n_states < 2:
            raise ValueError("n_states must be an integer >= 2")
        if self.covariance_type not in COVARIANCE_TYPES:
            raise ValueError(f"covariance_type must be one of {COVARIANCE_TYPES}")
        if self.emission not in EMISSION_TYPES:
            raise ValueError(f"emission must be one of {EMISSION_TYPES}")
        if self.emission == "student_t":
            if self.covariance_type != "diag":
                raise ValueError("Student-t emissions support diag scale only")
            if self.dof is None or not np.isfinite(self.dof) or self.dof <= 2:
                raise ValueError("Student-t emissions need finite dof > 2")
        if isinstance(self.n_iter, bool) or not isinstance(self.n_iter, int) or self.n_iter < 1:
            raise ValueError("n_iter must be a positive integer")
        for name in ("tol", "min_covar", "sticky"):
            value = getattr(self, name)
            if isinstance(value, bool) or not np.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.tol < 0:
            raise ValueError("tol must be nonnegative")
        if self.min_covar <= 0:
            raise ValueError("min_covar must be positive")
        if self.sticky < 0:
            raise ValueError("sticky must be nonnegative")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
