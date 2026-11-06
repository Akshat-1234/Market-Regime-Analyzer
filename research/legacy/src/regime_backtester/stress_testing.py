"""Predeclared calendar stress windows; no tuning to realized outcomes."""
from __future__ import annotations
import pandas as pd
from .research_metrics import evaluate_window

STRESS_PERIODS = {
    "2013": ("2013-01-01", "2013-12-31"),
    "2015–2016": ("2015-01-01", "2016-12-31"),
    "2020 COVID + recovery": ("2020-01-01", "2020-12-31"),
    "2022": ("2022-01-01", "2022-12-31"),
}


def stress_analysis(runs: dict[str, pd.DataFrame], config: dict) -> pd.DataFrame:
    b = config["backtest"]
    output = []
    for label, (start, end) in STRESS_PERIODS.items():
        benchmark = runs["Buy & Hold"].loc[start:end]
        if benchmark.empty:
            continue
        benchmark_total = evaluate_window(benchmark, b["annual_risk_free_rate"], b["trading_days_per_year"])["total_return"]
        for strategy, run in runs.items():
            window = run.loc[start:end]
            if not window.index.equals(benchmark.index):
                raise ValueError(f"Mismatched stress return dates for {strategy} / {label}")
            metrics = evaluate_window(window, b["annual_risk_free_rate"], b["trading_days_per_year"])
            output.append({"period": label, "period_start": start, "period_end": end,
                           "actual_start": window.index[0], "actual_end": window.index[-1],
                           "strategy": strategy, **metrics,
                           "return_difference_vs_buy_hold": metrics["total_return"] - benchmark_total})
    return pd.DataFrame(output)
