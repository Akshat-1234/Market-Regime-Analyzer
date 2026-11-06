"""Write a reproducible run directory, readable report and static plots."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from .pipeline import PipelineResult


def _fmt(value, fmt: str = ".3f") -> str:
    if value is None or pd.isna(value):
        return "—"
    if isinstance(value, str):
        return value.replace("|", "\\|")
    return format(value, fmt)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join(lines)


def _plot(result: PipelineResult, directory: Path) -> None:
    figs = directory / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"axes.grid": True, "grid.alpha": 0.22, "axes.spines.top": False,
                         "axes.spines.right": False, "font.size": 10})
    trend = f"Trend {result.config['backtest']['trend_window']}"
    names = ["Buy & Hold", trend, "Vol Target", "HMM + Trend"]
    colors = ["#475569", "#d97706", "#0284c7", "#0f766e"]
    label = "SYNTHETIC — " if result.metadata["data_source"].get("kind") == "synthetic" else ""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.5, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    for name, color in zip(names, colors):
        df = result.runs[name]
        ax1.plot(df.index, df["equity"], label=name, color=color, linewidth=1.35)
        ax2.plot(df.index, 100 * df["drawdown"], label=name, color=color, linewidth=1.0)
    ax1.set_title(label + "Walk-forward portfolio value, after costs")
    ax1.set_ylabel("Portfolio value")
    ax1.legend(ncol=2, frameon=False)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Return date")
    fig.tight_layout()
    fig.savefig(figs / "equity_drawdown.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(12.5, 3.8))
    pcols = [c for c in result.walkforward.signals.columns if c.startswith("p_state_")]
    for col in pcols:
        ax.plot(result.walkforward.signals.index, result.walkforward.signals[col], label=col, linewidth=.9)
    ax.set_title(label + "Primary HMM filtered probabilities at decision close")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Probability")
    ax.legend(frameon=False, ncol=max(1, len(pcols)))
    fig.tight_layout()
    fig.savefig(figs / "regime_probabilities.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _report(result: PipelineResult) -> str:
    m, c = result.metadata, result.config
    b, wf, h = c["backtest"], c["walkforward"], c["hmm"]
    kind = m["data_source"].get("kind", "unknown")
    warning = (
        "**SYNTHETIC DATA: these figures do not describe NIFTY or any real market.**\n\n"
        if kind == "synthetic" else ""
    )
    perf_rows = []
    for name, row in result.performance.iterrows():
        perf_rows.append([name, _fmt(row["cagr"], ".2%"), _fmt(row["annual_volatility"], ".2%"),
                          _fmt(row["sharpe"], ".2f"), _fmt(row["sortino"], ".2f"),
                          _fmt(row["max_drawdown"], ".2%"), _fmt(row["calmar"], ".2f"),
                          _fmt(row["mean_exposure"], ".1%"), _fmt(row["turnover_per_year"], ".2f")])
    perf = _table(["Strategy", "CAGR", "Volatility", "Sharpe", "Sortino", "Max DD",
                   "Calmar", "Exposure", "Turnover/yr"], perf_rows)
    state_rows = []
    for _, row in result.regime_summary.iterrows():
        state_rows.append([str(int(row["state_by_train_vol"])), str(int(row["days"])),
                           _fmt(row["occupancy"], ".1%"), _fmt(row["avg_run_length"], ".1f"),
                           _fmt(row["mean_held_interval_market_return"], ".3%"),
                           _fmt(row["held_interval_volatility_annualized"], ".1%")])
    states = _table(["Volatility rank", "Days", "Occupancy", "Mean run", "Held-interval mean", "Held-interval vol/yr"], state_rows)
    ci_rows = []
    for _, row in result.bootstrap.iterrows():
        ci_rows.append([row["control"], _fmt(row["observed_sharpe_difference"], "+.3f"),
                        f"[{_fmt(row['lower'], '+.3f')}, {_fmt(row['upper'], '+.3f')}]",
                        _fmt(row["fraction_le_zero"], ".1%"), str(int(row["valid_samples"]))])
    intervals = _table(["Control", "Observed Δ Sharpe", "Block-bootstrap interval", "Fraction Δ ≤ 0", "Samples"], ci_rows)
    sparse = result.regime_summary.loc[result.regime_summary["days"] < 30, "state_by_train_vol"].tolist()
    sparse_note = f" States {sparse} have fewer than 30 observations; their conditional statistics are especially unstable." if sparse else ""
    window_type = "Expanding" if wf["max_train_days"] is None else "Rolling"
    timing = ("Same-close fill is assumed after observing that close; this is optimistic and may not be practically executable. "
              "Rerun with `--execution-delay 1` for a more conservative next-close sensitivity test."
              if b["execution_delay_sessions"] == 0 else
              f"An extra {b['execution_delay_sessions']} session(s) elapse between decision close and execution close.")
    return f"""# Walk-forward regime backtest

{warning}Research only; not investment advice. This is a reconstruction, not an exact rerun of the unavailable earlier 14-model implementation.

## Data and setup

- Source: `{kind}`; path: `{m['data_source'].get('path')}`; SHA-256: `{m['data_source'].get('sha256')}`.
- Source URL, if provided: {m['data_source'].get('url', 'not recorded')}.
- Data used: {m['data_start']} to {m['data_end']} ({m['data_rows_analyzed']} rows).
- OOS signal dates: {m['first_signal_date']} to {m['last_signal_date']}; realized return dates: {m['first_return_date']} to {m['last_return_date']} ({m['return_observations']} observations).
- {window_type} training window, annual refits, at least {wf['min_train_days']} feature-valid days; rolling maximum: {wf['max_train_days']}.
- Primary model: `{h['primary_model']}`; {len(h['models'])} pre-specified model(s); state ordering is by **training weighted next-day volatility**.
- Target vol: {h['target_volatility']:.1%}; HMM/trend blend: {1-b['trend_weight_in_blend']:.0%}/{b['trend_weight_in_blend']:.0%}.
- Cash earns {b['annual_risk_free_rate']:.2%} annualized; {b['transaction_cost_bps']:g} bps per one-way traded notional; {b['trading_days_per_year']} trading days/year.
- **Execution:** {timing}

## Input quality

`data_quality.csv` lists yearly close-return volatility and, if Open is available, its coverage, OHLC out-of-range observations, overnight/intraday volatility and the fraction of opens essentially equal to the previous close. These checks flag investigation candidates; they do not certify data quality. Early Open quotes can be unreliable. The default models use Close only.

## Performance

{perf}

Max DD is a positive magnitude; turnover is one-way traded notional divided by portfolio value, annualized. Fractional targets rebalance daily and their turnover includes weight drift. Initial entry costs are included; no artificial terminal liquidation. Sharpe uses daily excess returns over the cash rate; CAGR is annualized by trading observations. Index price returns omit dividends unless the input is a total-return series.

![Equity and drawdowns](figures/equity_drawdown.png)

## H1 — descriptive regimes

Labels use the primary model's probability at each **decision close**; outcomes below are the market returns over the interval held after execution. Run lengths and occupancy describe the observed rank labels, not evidence that a distinct underlying economic regime exists. The effective number of occupied states is {m['oos_effective_regime_count']:.2f}; the largest rank covers {m['oos_largest_regime_fraction']:.1%} of intervals. Ranks are recalibrated at every refit and can change meaning across years.{sparse_note}

{states}

`train_transition_matrices.csv` contains the fitted matrices per refit; `empirical_transitions.csv` summarizes adjacent OOS rank labels, including boundaries between refits.

![Primary filtered probabilities](figures/regime_probabilities.png)

## H2 — conditional strategy results

See `regime_strategy_sharpe.csv` for post-cost Sharpe and sample size by decision-time regime. These are descriptive, conditional ex-post comparisons, not a significance test or an investable per-regime policy. The strategies have shared market exposure; small states can be highly unstable.

## H3 — paired Sharpe difference: HMM + Trend minus control

Circular moving-block percentile bootstrap, {c['bootstrap']['block_length']}-day blocks, {c['bootstrap']['confidence']:.0%} intervals, seed {c['bootstrap']['seed']}. The same dates are sampled jointly for both strategies.

{intervals}

The fraction at or below zero is a bootstrap proportion, **not** a p-value. An interval containing zero does not prove equality or equivalence. Intervals do not correct for the many strategies tried in the previous conversation, hyperparameter choice, nonstationarity or data snooping.

## Important limitations

1. This rebuild uses a documented four-model volatility-target ensemble; the prior 14-model ensemble's code and configuration were not supplied. Do not compare these figures as an exact reproduction.
2. The prior discussion tested many variants and examined 2023–2026, so that period is not an untouched holdout. Freeze the design and evaluate on genuinely unseen data and other markets.
3. Yahoo or other index quotes can contain inaccurate historical OHLC, revisions, missing dates or corporate-action issues. Validate against the provider, and use an investable total-return proxy, realistic fees/taxes/slippage and an appropriate cash/funding rate.
4. A Gaussian HMM can overfit, has arbitrary labels, and filtered probabilities are model-dependent—not guarantees. Failed or poorly occupied fits are rejected; see `fits.csv`.
5. A drawdown reduction or historical Sharpe does not establish future alpha. No leverage, shorting, market impact, taxes, dividends, intraday execution or India VIX/FII features are modelled by default.
"""


def write_results(result: PipelineResult, directory: str | Path) -> Path:
    out = Path(directory).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    result.performance.to_csv(out / "performance.csv", index_label="strategy")
    result.data_quality.to_csv(out / "data_quality.csv", index=False)
    result.walkforward.signals.to_csv(out / "signals.csv", index_label="decision_date")
    result.walkforward.fits.to_csv(out / "fits.csv", index=False)
    result.walkforward.state_calibrations.to_csv(out / "train_state_calibration.csv", index=False)
    result.walkforward.transition_matrices.to_csv(out / "train_transition_matrices.csv", index=False)
    result.regime_summary.to_csv(out / "regime_summary.csv", index=False)
    result.regime_strategy.to_csv(out / "regime_strategy_sharpe.csv", index=False)
    result.empirical_transitions.to_csv(out / "empirical_transitions.csv", index_label="from_state")
    result.bootstrap.to_csv(out / "bootstrap.csv", index=False)
    long = pd.concat([df.assign(strategy=name).reset_index() for name, df in result.runs.items()], ignore_index=True)
    long.to_csv(out / "daily_backtests.csv", index=False)
    pd.DataFrame({k: v["equity"] for k, v in result.runs.items()}).to_csv(out / "equity_curves.csv", index_label="Date")
    pd.DataFrame({k: v["strategy_return"] for k, v in result.runs.items()}).to_csv(out / "daily_returns.csv", index_label="Date")
    (out / "metadata.json").write_text(json.dumps(result.metadata, indent=2) + "\n", encoding="utf-8")
    (out / "run_config.yaml").write_text(yaml.safe_dump(result.config, sort_keys=False), encoding="utf-8")
    _plot(result, out)
    (out / "report.md").write_text(_report(result), encoding="utf-8")
    return out.resolve()
