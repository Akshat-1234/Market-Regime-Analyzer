"""Walk-forward fold metrics, holdout boundaries and cash-rate sensitivity."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from .execution import simulate
from .experiment_tracking import frozen_config, config_sha256
from .research_metrics import evaluate_window


def fold_metrics(result) -> tuple[pd.DataFrame, pd.DataFrame]:
    fits = result.walkforward.fits
    primary = fits[fits.model == result.config["hmm"]["primary_model"]].sort_values("signal_start")
    b = result.config["backtest"]
    records = []
    for i, fit in enumerate(primary.itertuples(), 1):
        for name, run in result.runs.items():
            decision = pd.to_datetime(run["decision_date"])
            sub = run.loc[(decision >= fit.signal_start) & (decision <= fit.signal_end)]
            if sub.empty:
                continue
            records.append({"fold_id": i, "strategy": name, "train_start": fit.train_start,
                            "train_end": fit.train_end, "test_signal_start": fit.signal_start,
                            "test_signal_end": fit.signal_end, "test_return_start": sub.index[0],
                            "test_return_end": sub.index[-1], "train_observations": fit.train_observations,
                            **evaluate_window(sub, b["annual_risk_free_rate"], b["trading_days_per_year"])})
    # Aggregate recomputed from full aligned OOS daily returns, never fold averages.
    aggregate = pd.DataFrame([{"strategy": n, **evaluate_window(r, b["annual_risk_free_rate"], b["trading_days_per_year"])}
                              for n, r in result.runs.items()])
    return pd.DataFrame(records), aggregate


def retrospective_holdout(runs: dict[str, pd.DataFrame], config: dict, start: str = "2023-01-01",
                          end: str = "2026-10-22") -> pd.DataFrame:
    b = config["backtest"]
    return pd.DataFrame([{"strategy": n, "label": "RETROSPECTIVE — PREVIOUSLY EXAMINED",
                          "start": r.loc[start:end].index[0], "end": r.loc[start:end].index[-1],
                          **evaluate_window(r.loc[start:end], b["annual_risk_free_rate"], b["trading_days_per_year"])}
                         for n, r in runs.items() if not r.loc[start:end].empty])


def freeze_manifest(config: dict, data_hash: str, last_data_date: str, source_hash: str,
                    freeze_time: datetime | None = None) -> dict:
    now = freeze_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("freeze_time must include a timezone")
    local_date = now.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    boundary = max(local_date, str(last_data_date))
    frozen = frozen_config(config)
    config_hash = config_sha256(config)
    return {"status": "PENDING — no post-freeze data evaluated", "frozen_at_utc": now.astimezone(timezone.utc).isoformat(),
            "frozen_at_exchange_date": local_date, "last_original_data_date": last_data_date,
            "evaluation_decision_date_strictly_after": boundary, "baseline_data_sha256": data_hash,
            "source_code_sha256": source_hash, "frozen_config_sha256": config_hash,
            "frozen_config": frozen,
            "rules": "Fixed specs, hyperparameters, lag and costs; scheduled annual refits may use only prior observations. Decisions must be after both freeze day and original data end.",
            "warning": "Frozen after extensive historical examination. 2023–2026 is retrospective, not untouched."}


def validate_prospective_extension(original: pd.DataFrame, extension: pd.DataFrame, manifest: dict) -> None:
    """Reject revisions to the original prefix and require a post-freeze row."""
    if not set(original.columns).issubset(extension.columns):
        raise ValueError("Extension lacks original columns")
    prefix = extension.reindex(original.index)
    if len(prefix) != len(original) or prefix[original.columns].isna().any(axis=None):
        raise ValueError("Extension is missing original observations")
    if not np.allclose(prefix[original.columns].to_numpy(dtype=float), original.to_numpy(dtype=float), rtol=1e-12, atol=1e-12):
        raise ValueError("Extension revises original historical prices; start a new study")
    boundary = pd.Timestamp(manifest["evaluation_decision_date_strictly_after"])
    if not (extension.index > boundary).any():
        raise ValueError("No observations strictly after freeze boundary; prospective holdout remains pending")


def cash_sensitivity(result, prices: pd.DataFrame, dynamic_rates: pd.Series | None = None) -> pd.DataFrame:
    """Replay identical signals under cash assumptions; trading timing unchanged."""
    b = result.config["backtest"]
    market = prices.Close.pct_change(fill_method=None)
    scenarios = [("constant_0pct", 0.0, None), ("constant_6_5pct", .065, None)]
    if dynamic_rates is not None:
        scenarios.append(("rbi_91d_lagged_proxy", .065, dynamic_rates))
    rows = []
    for scenario, annual, dynamic in scenarios:
        for name in result.runs:
            simulated = simulate(result.walkforward.signals[name], market,
                initial_capital=b["initial_capital"], annual_risk_free_rate=annual,
                trading_days_per_year=b["trading_days_per_year"], transaction_cost_bps=b["transaction_cost_bps"],
                execution_delay_sessions=b["execution_delay_sessions"], risk_free_annual_by_date=dynamic)
            drf = None
            if dynamic is not None:
                known = dynamic.reindex(pd.DatetimeIndex(simulated.execution_date)).to_numpy()
                drf = (1 + known) ** (1 / b["trading_days_per_year"]) - 1
            rows.append({"cash_scenario": scenario, "strategy": name,
                         **evaluate_window(simulated, annual, b["trading_days_per_year"], drf)})
    return pd.DataFrame(rows)
