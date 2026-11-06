"""Load, merge and validate a small, explicit YAML configuration."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "data": {"csv": "data/raw/nifty_index.csv", "date_column": "Date", "price_column": "Close"},
    "walkforward": {"min_train_days": 504, "max_train_days": None, "start_date": None, "end_date": None},
    "hmm": {
        "primary_model": "rvd_3", "covariance_type": "diag", "n_iter": 250,
        "tol": 0.05, "min_covar": 0.001, "min_state_fraction": 0.02,
        "seeds": [2, 42], "target_volatility": 0.12, "volatility_floor": 0.03,
        "models": [
            {"name": "rv_2", "n_states": 2, "features": ["daily_return", "volatility_20"]},
            {"name": "rv_3", "n_states": 3, "features": ["daily_return", "volatility_20"]},
            {"name": "rvd_2", "n_states": 2, "features": ["daily_return", "volatility_20", "drawdown_252"]},
            {"name": "rvd_3", "n_states": 3, "features": ["daily_return", "volatility_20", "drawdown_252"]},
        ],
    },
    "backtest": {
        "initial_capital": 1000.0, "annual_risk_free_rate": 0.065,
        "trading_days_per_year": 252, "transaction_cost_bps": 10.0, "execution_delay_sessions": 0,
        "trend_weight_in_blend": 0.5, "trend_window": 50,
        "momentum_window": 20, "mean_reversion_window": 20,
        "mean_reversion_entry_band": 0.02, "vol_target": 0.12,
    },
    "bootstrap": {"samples": 1000, "block_length": 20, "seed": 42, "confidence": 0.95},
    "output": {"directory": "results/run"},
}


def _merge(base: dict, update: dict, path: str = "") -> None:
    for key, value in update.items():
        if key not in base:
            raise ValueError(f"Unknown configuration key: {path}{key}")
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"{path}{key} must be a mapping")
            _merge(base[key], value, f"{path}{key}.")
        else:
            base[key] = deepcopy(value)


def _number(value: Any, name: str, lower: float | None = None,
            upper: float | None = None, *, integer: bool = False,
            lower_open: bool = False, upper_open: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be {'an integer' if integer else 'a number'}")
    if integer and (not isinstance(value, int)):
        raise ValueError(f"{name} must be an integer")
    import math
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if lower is not None and (value < lower or (lower_open and value == lower)):
        raise ValueError(f"{name} is below its allowed range")
    if upper is not None and (value > upper or (upper_open and value == upper)):
        raise ValueError(f"{name} is above its allowed range")


def validate_config(c: dict) -> dict:
    for key in ("csv", "date_column", "price_column"):
        if not isinstance(c["data"][key], str) or not c["data"][key].strip():
            raise ValueError(f"data.{key} must be a non-empty string")
    wf = c["walkforward"]
    _number(wf["min_train_days"], "walkforward.min_train_days", 30, integer=True)
    if wf["max_train_days"] is not None:
        _number(wf["max_train_days"], "walkforward.max_train_days", wf["min_train_days"], integer=True)
    for key in ("start_date", "end_date"):
        if wf[key] is not None:
            try:
                wf[key] = date.fromisoformat(str(wf[key])).isoformat()
            except ValueError as exc:
                raise ValueError(f"walkforward.{key} must be YYYY-MM-DD") from exc
    if wf["start_date"] and wf["end_date"] and wf["start_date"] >= wf["end_date"]:
        raise ValueError("start_date must be before end_date")

    h = c["hmm"]
    if h["covariance_type"] not in ("diag", "full"):
        raise ValueError("hmm.covariance_type must be diag or full")
    _number(h["n_iter"], "hmm.n_iter", 2, integer=True)
    for key in ("tol", "min_covar", "target_volatility", "volatility_floor"):
        _number(h[key], f"hmm.{key}", 0, lower_open=True)
    _number(h["min_state_fraction"], "hmm.min_state_fraction", 0, 0.5, upper_open=True)
    if not isinstance(h["seeds"], list) or not h["seeds"]:
        raise ValueError("hmm.seeds must be a non-empty list")
    for seed in h["seeds"]:
        _number(seed, "hmm seed", 0, 2**32 - 1, integer=True)
    if len(set(h["seeds"])) != len(h["seeds"]):
        raise ValueError("hmm.seeds must be unique")
    if not isinstance(h["models"], list) or not h["models"]:
        raise ValueError("hmm.models must be a non-empty list")
    names = []
    for m in h["models"]:
        if not isinstance(m, dict) or set(m) - {"name", "n_states", "features", "pca_components"}:
            raise ValueError("Each model needs name, n_states, features and optional pca_components")
        if not {"name", "n_states", "features"}.issubset(m):
            raise ValueError("Each HMM model requires name, n_states and features")
        if not isinstance(m["name"], str) or not m["name"].strip():
            raise ValueError("Each model needs a non-empty name")
        names.append(m["name"])
        _number(m["n_states"], f"{m['name']}.n_states", 2, 10, integer=True)
        if h["min_state_fraction"] * m["n_states"] >= 1:
            raise ValueError("min_state_fraction is too high for the state count")
        cols = m["features"]
        if not isinstance(cols, list) or not cols or not all(isinstance(x, str) and x for x in cols):
            raise ValueError(f"{m['name']}.features must be a non-empty list of names")
        if len(cols) != len(set(cols)):
            raise ValueError(f"{m['name']}.features contains duplicates")
        if m.get("pca_components") is not None:
            _number(m["pca_components"], f"{m['name']}.pca_components", 1, len(cols), integer=True)
    if len(names) != len(set(names)) or h["primary_model"] not in names:
        raise ValueError("Model names must be unique and include hmm.primary_model")

    b = c["backtest"]
    _number(b["initial_capital"], "backtest.initial_capital", 0, lower_open=True)
    _number(b["annual_risk_free_rate"], "backtest.annual_risk_free_rate", -1, lower_open=True)
    _number(b["trading_days_per_year"], "backtest.trading_days_per_year", 1, integer=True)
    _number(b["transaction_cost_bps"], "backtest.transaction_cost_bps", 0, 10000, upper_open=True)
    _number(b["execution_delay_sessions"], "backtest.execution_delay_sessions", 0, 20, integer=True)
    _number(b["trend_weight_in_blend"], "backtest.trend_weight_in_blend", 0, 1)
    for key in ("trend_window", "momentum_window", "mean_reversion_window"):
        _number(b[key], f"backtest.{key}", 2, integer=True)
    _number(b["mean_reversion_entry_band"], "backtest.mean_reversion_entry_band", 0, 1, upper_open=True)
    _number(b["vol_target"], "backtest.vol_target", 0, lower_open=True)
    boot = c["bootstrap"]
    _number(boot["samples"], "bootstrap.samples", 1, integer=True)
    _number(boot["block_length"], "bootstrap.block_length", 1, integer=True)
    _number(boot["seed"], "bootstrap.seed", 0, 2**32 - 1, integer=True)
    _number(boot["confidence"], "bootstrap.confidence", 0, 1, lower_open=True, upper_open=True)
    if not isinstance(c["output"]["directory"], str) or not c["output"]["directory"].strip():
        raise ValueError("output.directory must be non-empty")
    return c


def load_config(path: str | Path | None = None, overrides: dict | None = None) -> dict:
    config = deepcopy(DEFAULTS)
    if path is not None:
        with Path(path).open(encoding="utf-8") as f:
            patch = yaml.safe_load(f) or {}
        if not isinstance(patch, dict):
            raise ValueError("Configuration root must be a mapping")
        _merge(config, patch)
    if overrides:
        _merge(config, overrides)
    return validate_config(config)
