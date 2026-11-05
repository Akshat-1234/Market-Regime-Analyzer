"""f10-compatible close-only RV and RVD feature contracts.

No feature family is introduced here.  Warm-up and internal missing rows remain
missing; this module never forward-fills them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .data import validate_ohlc_frame

FEATURE_CONTRACT_VERSION = "f10-close-features-v1"


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    version: str
    inputs: tuple[str, ...]
    lookback_sessions: int
    first_valid_position: int
    availability: str
    formula: str
    missing_value_policy: str


DAILY_RETURN = FeatureSpec(
    "daily_return", "daily-return-f10-v1", ("Close",), 1, 1,
    "known after Close[t]",
    "Close[t] / Close[t-1] - 1",
    "first row missing; no imputation",
)
REALIZED_VOLATILITY = FeatureSpec(
    "volatility_20", "realized-vol20-f10-v1", ("daily_return",), 20, 20,
    "known after Close[t] using returns through t",
    "sample_std(daily_return[t-19:t+1], ddof=1) * sqrt(252)",
    "20 nonmissing returns required; no imputation",
)
DRAWDOWN = FeatureSpec(
    "drawdown_252", "drawdown252-f10-v1", ("Close",), 252, 251,
    "known after Close[t] using closes through t",
    "Close[t] / max(Close[t-251:t+1]) - 1",
    "252 nonmissing closes required; no imputation",
)

FAMILY_SPECS = {
    "rv": (DAILY_RETURN, REALIZED_VOLATILITY),
    "rvd": (DAILY_RETURN, REALIZED_VOLATILITY, DRAWDOWN),
}


def feature_manifest(family: str) -> dict[str, Any]:
    if family not in FAMILY_SPECS:
        raise ValueError("family must be 'rv' or 'rvd'")
    specs = FAMILY_SPECS[family]
    return {
        "schema": FEATURE_CONTRACT_VERSION,
        "family": family,
        "columns": [spec.name for spec in specs],
        "annualization_sessions": 252,
        "return_type": "simple_close_to_close",
        "volatility_ddof": 1,
        "warmup_policy": "retain missing rows; trim only common leading warm-up for fitting",
        "internal_gap_policy": "reject",
        "imputation": False,
        "specs": [{**asdict(spec), "inputs": list(spec.inputs)} for spec in specs],
    }


def build_contract_features(prices: pd.DataFrame, family: str = "rv") -> tuple[pd.DataFrame, dict[str, Any]]:
    """Materialize the preserved f10 formulas with versioned metadata."""
    manifest = feature_manifest(family)
    clean = validate_ohlc_frame(prices)
    close = clean["Close"].astype(float)
    returns = close.pct_change(fill_method=None)
    output = pd.DataFrame(index=clean.index)
    output["daily_return"] = returns
    output["volatility_20"] = returns.rolling(20).std() * np.sqrt(252)
    if family == "rvd":
        output["drawdown_252"] = close / close.rolling(252).max() - 1
    output.index.name = "Date"
    return output, manifest


def complete_feature_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove only common leading warm-up rows and reject every internal gap."""
    if not isinstance(frame, pd.DataFrame) or frame.shape[1] == 0 or len(frame) == 0:
        raise ValueError("feature frame must be non-empty")
    if not np.isfinite(frame.to_numpy(dtype=float)[frame.notna().to_numpy()]).all():
        raise ValueError("present feature values must be finite")
    valid = frame.notna().all(axis=1).to_numpy()
    if not valid.any():
        raise ValueError("feature frame has no complete rows")
    first = int(np.flatnonzero(valid)[0])
    trimmed = frame.iloc[first:].copy()
    if trimmed.isna().any(axis=None):
        raise ValueError("feature frame contains an internal gap; imputation is forbidden")
    if not np.isfinite(trimmed.to_numpy(dtype=float)).all():
        raise ValueError("complete feature rows must be finite")
    return trimmed
