"""End-to-end orchestration, independent of the command line and output files."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from importlib import metadata as package_metadata
import platform
from typing import Callable

import pandas as pd

from . import __version__
from .data import annual_quality_table
from .execution import simulate
from .metrics import paired_block_bootstrap, performance_table, regime_tables
from .strategies import fixed_signals
from .walkforward import WalkForwardResult, walk_forward


@dataclass
class PipelineResult:
    walkforward: WalkForwardResult
    runs: dict[str, pd.DataFrame]
    performance: pd.DataFrame
    data_quality: pd.DataFrame
    regime_summary: pd.DataFrame
    regime_strategy: pd.DataFrame
    empirical_transitions: pd.DataFrame
    bootstrap: pd.DataFrame
    metadata: dict
    config: dict


def run_pipeline(prices: pd.DataFrame, config: dict, source: dict | None = None,
                 progress: Callable[[str], None] | None = None) -> PipelineResult:
    if config["walkforward"]["end_date"]:
        prices = prices.loc[:config["walkforward"]["end_date"]].copy()
    wf = walk_forward(prices, config, progress)
    b = config["backtest"]
    returns = prices["Close"].pct_change(fill_method=None)
    strategy_names = list(fixed_signals(prices, config).columns) + ["HMM Ensemble", "HMM + Trend"]
    runs = {}
    for name in strategy_names:
        runs[name] = simulate(wf.signals[name], returns,
                              initial_capital=b["initial_capital"],
                              annual_risk_free_rate=b["annual_risk_free_rate"],
                              trading_days_per_year=b["trading_days_per_year"],
                              transaction_cost_bps=b["transaction_cost_bps"],
                              execution_delay_sessions=b["execution_delay_sessions"])
    perf = performance_table(runs, config)
    h1, h2, trans = regime_tables(wf.signals, runs, config)
    controls = ["Buy & Hold", f"Trend {b['trend_window']}", "Vol Target"]
    ci = paired_block_bootstrap(runs, "HMM + Trend", controls, config)
    # Fingerprint the implementation independently of the input-data hash.
    code_hasher = hashlib.sha256()
    for module_path in sorted(Path(__file__).resolve().parent.glob("*.py")):
        code_hasher.update(module_path.name.encode("utf-8") + b"\0")
        code_hasher.update(module_path.read_bytes())
    versions = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn", "hmmlearn", "matplotlib", "PyYAML", "threadpoolctl", "yfinance"):
        try:
            versions[package] = package_metadata.version(package)
        except package_metadata.PackageNotFoundError:
            versions[package] = None
    first_run = next(iter(runs.values()))
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(),
            "data_source": source or {"kind": "in-memory", "path": None, "sha256": None},
            "data_rows_analyzed": len(prices), "data_start": str(prices.index[0].date()),
            "data_end": str(prices.index[-1].date()),
            "first_signal_date": str(wf.signals.index[0].date()),
            "last_signal_date": str(wf.signals.index[-1].date()),
            "first_return_date": str(first_run.index[0].date()),
            "last_return_date": str(first_run.index[-1].date()),
            "return_observations": len(first_run),
            "primary_model": config["hmm"]["primary_model"],
            "oos_effective_regime_count": float(1 / (h1["occupancy"] ** 2).sum()),
            "oos_largest_regime_fraction": float(h1["occupancy"].max()),
            "project_version": __version__, "core_source_sha256": code_hasher.hexdigest(),
            "python": platform.python_version(), "packages": versions}
    quality = annual_quality_table(prices, b["trading_days_per_year"])
    return PipelineResult(wf, runs, perf, quality, h1, h2, trans, ci, meta, config)
