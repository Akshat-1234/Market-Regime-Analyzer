"""Machine-checkable matching diagnostics; no allocation policy is implemented."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._validation import finite_number


@dataclass(frozen=True)
class ControlMatchDiagnostics:
    exposure_ks_distances: tuple[float, ...]
    causal: bool
    mean_exposure_difference: float
    annualized_turnover_difference: float
    annualized_volatility_difference: float

    def __post_init__(self) -> None:
        distances = tuple(finite_number(value, "exposure KS distance")
                          for value in self.exposure_ks_distances)
        if not distances or any(value < 0 or value > 1 for value in distances):
            raise ValueError("exposure KS distances must be non-empty values in [0, 1]")
        if not isinstance(self.causal, bool):
            raise ValueError("causal must be explicit")
        object.__setattr__(self, "exposure_ks_distances", distances)
        for name in ("mean_exposure_difference", "annualized_turnover_difference",
                     "annualized_volatility_difference"):
            value = abs(finite_number(getattr(self, name), name))
            object.__setattr__(self, name, value)

    def summary(self) -> dict[str, float | int | bool]:
        # Keep mean and median separate; the historical 1c key conflated them.
        return {
            "control_count": len(self.exposure_ks_distances),
            "mean_exposure_ks": float(np.mean(self.exposure_ks_distances)),
            "median_exposure_ks": float(np.median(self.exposure_ks_distances)),
            "causal": self.causal,
            "mean_exposure_difference": self.mean_exposure_difference,
            "annualized_turnover_difference": self.annualized_turnover_difference,
            "annualized_volatility_difference": self.annualized_volatility_difference,
        }


@dataclass(frozen=True)
class ControlMatchThresholds:
    exposure_ks: float
    ks_statistic: str
    mean_exposure_difference: float
    annualized_turnover_difference: float
    annualized_volatility_difference: float

    def __post_init__(self) -> None:
        if self.ks_statistic not in {"mean", "median"}:
            raise ValueError("ks_statistic must be 'mean' or 'median'")
        for name in ("exposure_ks", "mean_exposure_difference",
                     "annualized_turnover_difference", "annualized_volatility_difference"):
            value = finite_number(getattr(self, name), name)
            if value < 0:
                raise ValueError(f"{name} threshold must be nonnegative")
            object.__setattr__(self, name, value)


def assert_control_matching(diagnostics: ControlMatchDiagnostics,
                            thresholds: ControlMatchThresholds) -> None:
    """Fail closed on noncausal controls or any unsupported matching claim."""
    if not diagnostics.causal:
        raise ValueError("noncausal controls cannot support a matched-control claim")
    summary = diagnostics.summary()
    observed = summary[f"{thresholds.ks_statistic}_exposure_ks"]
    checks = (
        (observed, thresholds.exposure_ks, f"{thresholds.ks_statistic} exposure KS"),
        (diagnostics.mean_exposure_difference, thresholds.mean_exposure_difference,
         "mean exposure difference"),
        (diagnostics.annualized_turnover_difference, thresholds.annualized_turnover_difference,
         "annualized turnover difference"),
        (diagnostics.annualized_volatility_difference, thresholds.annualized_volatility_difference,
         "annualized volatility difference"),
    )
    failures = [f"{name} {observed_value} exceeds {limit}"
                for observed_value, limit, name in checks if observed_value > limit]
    if failures:
        raise ValueError("control matching failed: " + "; ".join(failures))
