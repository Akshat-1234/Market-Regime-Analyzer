"""Causal, out-of-sample HMM incremental-value controls.

All controls use only HMM exposures observable by the decision date. Full-period
permutations would leak future exposure distribution into earlier decisions;
we intentionally use prior-only resampling, not a hindsight permutation.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from .execution import simulate
from .metrics import annual_sharpe, paired_block_bootstrap
from .research_metrics import evaluate_window
from .stress_testing import STRESS_PERIODS

CONTROL_NAMES = ("Past-only shuffled", "Past-only block shuffled", "Exposure/turnover-matched random")


def _refresh_probabilities(values: np.ndarray, seed: int = 1097, history_window: int | None = 63) -> np.ndarray:
    """Past-only rolling estimate of HMM variation / independent redraw variation."""
    x = np.asarray(values, dtype=float)
    n = len(x)
    q = np.ones(n)
    if n < 3:
        return q
    if history_window is not None and history_window < 2:
        raise ValueError("history_window must be at least two sessions, or None")
    rng = np.random.default_rng(seed)
    u = rng.random(n)
    changes = np.abs(np.diff(x, prepend=x[0]))
    pairs = np.zeros(n)
    for i in range(1, n):
        lo = max(0, i - history_window) if history_window else 0
        pairs[i] = abs(x[i] - x[lo + int(u[i] * (i - lo))])
    # Prefix sums let q[t] use only entries through t-1, in a rolling window.
    csum = np.r_[0.0, np.cumsum(changes)]
    psum = np.r_[0.0, np.cumsum(pairs)]
    for t in range(2, n):
        lo = max(1, t - history_window) if history_window else 1
        denom = psum[t] - psum[lo]
        q[t] = min(1.0, (csum[t] - csum[lo]) / denom) if denom > 1e-12 else 0.0
    return q


def causal_control(values: np.ndarray, kind: str, seed: int, block_length: int = 20,
                   refresh: np.ndarray | None = None, history_window: int | None = 63) -> np.ndarray:
    """Generate controls from prior-only exposures, defaulting to a rolling quarter.

    First observation uses the current real HMM exposure as initialization.
    No subsequent draw can use the current or a future observation. A historical
    block must be complete before it is drawn. Window selection is documented.
    """
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) == 0 or not np.isfinite(x).all() or (x < 0).any() or (x > 1).any():
        raise ValueError("HMM exposure must be a finite one-dimensional [0,1] array")
    if block_length < 1:
        raise ValueError("block_length must be positive")
    if history_window is not None and history_window < 2:
        raise ValueError("history_window must be at least two sessions, or None")
    rng = np.random.default_rng(seed)
    out = np.empty_like(x)
    out[0] = x[0]
    n = len(x)
    if kind == CONTROL_NAMES[0]:
        u = rng.random(n)
        t = np.arange(n)
        lo = np.maximum(0, t-history_window) if history_window else np.zeros(n, dtype=int)
        indices = lo + np.floor(u * (t - lo)).astype(int)
        indices[0] = 0
        out[:] = x[indices]
    elif kind == CONTROL_NAMES[1]:
        t = 1
        while t < n:
            lo = max(0, t-history_window) if history_window else 0
            length = min(block_length, t-lo)  # independent of future sample length
            start = int(rng.integers(lo, t-length+1))
            take = min(length, n-t)
            out[t:t+take] = x[start:start+take]
            t += length
    elif kind == CONTROL_NAMES[2]:
        q = _refresh_probabilities(x, history_window=history_window) if refresh is None else refresh
        if len(q) != n:
            raise ValueError("refresh vector must match exposure length")
        draw = rng.random((n, 2))  # fixed draws per day preserve prefix reproducibility
        for t in range(1, n):
            lo = max(0, t-history_window) if history_window else 0
            out[t] = x[lo + int(draw[t, 1] * (t-lo))] if draw[t, 0] < q[t] else out[t-1]
    else:
        raise ValueError(f"Unknown control type: {kind}")
    return out


@dataclass
class AttributionResult:
    metrics: pd.DataFrame
    simulations: pd.DataFrame
    bootstrap: pd.DataFrame
    periods: pd.DataFrame
    control_daily: pd.DataFrame


def run_attribution(result, prices: pd.DataFrame, simulations: int = 200,
                    seed: int = 1701, block_length: int = 20,
                    history_window: int | None = 63) -> AttributionResult:
    if simulations < 2 or block_length < 1:
        raise ValueError("Need at least two simulations and a positive block length")
    b = result.config["backtest"]
    signals = result.walkforward.signals
    trend_name = f"Trend {b['trend_window']}"
    real = result.runs["HMM + Trend"]
    trend = result.runs[trend_name]
    if not real.index.equals(trend.index):
        raise ValueError("Real and trend returns are not aligned")
    rf, periods, cost = b["annual_risk_free_rate"], b["trading_days_per_year"], b["transaction_cost_bps"]
    raw_hmm = signals["HMM Ensemble"].to_numpy()
    trend_target = signals[trend_name].to_numpy()
    blend = b["trend_weight_in_blend"]
    market = prices.Close.pct_change(fill_method=None)
    kwargs = dict(initial_capital=b["initial_capital"], annual_risk_free_rate=rf,
                  trading_days_per_year=periods, execution_delay_sessions=b["execution_delay_sessions"])
    real_metrics = evaluate_window(real, rf, periods)
    real_gross = simulate(signals["HMM + Trend"], market, transaction_cost_bps=0, **kwargs)
    # Common realized turnover fee schedule: diagnostic counterfactual only.
    fee_schedule = (cost / 10000.0) * real.turnover.to_numpy()
    real_same_cost = (1 + real_gross.strategy_return.to_numpy()) * (1 - fee_schedule) - 1
    real_same_cost_sharpe = annual_sharpe(real_same_cost, rf, periods)
    q = _refresh_probabilities(raw_hmm, history_window=history_window)
    simulation_rows = []
    daily_control = {}
    period_values: dict[tuple[str, str], list[float]] = {}
    base_seed_seq = np.random.SeedSequence(seed)
    seeds = base_seed_seq.generate_state(simulations * len(CONTROL_NAMES), dtype=np.uint32)
    for ki, kind in enumerate(CONTROL_NAMES):
        daily = []
        for j in range(simulations):
            rng_seed = int(seeds[ki * simulations + j])
            control_hmm = causal_control(raw_hmm, kind, rng_seed, block_length, q, history_window)
            exposure = pd.Series((1 - blend) * control_hmm + blend * trend_target, index=signals.index)
            trade = simulate(exposure, market, transaction_cost_bps=cost, **kwargs)
            gross = simulate(exposure, market, transaction_cost_bps=0, **kwargs)
            if not trade.index.equals(real.index):
                raise AssertionError("Control must use the identical realized return calendar")
            stats = evaluate_window(trade, rf, periods)
            adjusted = (1 + gross.strategy_return.to_numpy()) * (1 - fee_schedule) - 1
            cash_adj_sharpe = annual_sharpe(adjusted, rf, periods)
            # Match checks are ex-post diagnostics, never inputs to controls.
            decisions = pd.DatetimeIndex(trade.decision_date)
            used_hmm = pd.Series(control_hmm, index=signals.index).loc[decisions].to_numpy()
            real_hmm = signals.loc[decisions, "HMM Ensemble"].to_numpy()
            row = {"control": kind, "simulation": j, "seed": rng_seed, **stats,
                   "real_minus_control_sharpe": real_metrics["sharpe"] - stats["sharpe"],
                   "real_minus_control_max_drawdown": real_metrics["max_drawdown"] - stats["max_drawdown"],
                   "mean_hmm_exposure": float(used_hmm.mean()),
                   "real_mean_hmm_exposure": float(real_hmm.mean()),
                   "hmm_exposure_ks_distance": float(ks_2samp(used_hmm, real_hmm).statistic),
                   "hmm_exposure_p10": float(np.quantile(used_hmm, .1)),
                   "hmm_exposure_p50": float(np.quantile(used_hmm, .5)),
                   "hmm_exposure_p90": float(np.quantile(used_hmm, .9)),
                   "common_fee_schedule_sharpe": cash_adj_sharpe,
                   "real_minus_control_common_fee_sharpe": real_same_cost_sharpe - cash_adj_sharpe}
            simulation_rows.append(row)
            arr = trade.strategy_return.to_numpy()
            daily.append(arr)
            for label, (start, end) in STRESS_PERIODS.items():
                mask = (trade.index >= start) & (trade.index <= end)
                if mask.sum() > 1:
                    period_values.setdefault((label, kind), []).append(annual_sharpe(arr[mask], rf, periods))
        daily_control[kind] = np.mean(np.vstack(daily), axis=0)
    sim = pd.DataFrame(simulation_rows)
    summary = []
    for name, frame in [("Trend alone", trend), ("Trend + real HMM", real)]:
        stat = evaluate_window(frame, rf, periods)
        summary.append({"control": name, "n_simulations": 1, **stat,
                        "sharpe_p05": stat["sharpe"], "sharpe_p95": stat["sharpe"],
                        "max_drawdown_p05": stat["max_drawdown"], "max_drawdown_p95": stat["max_drawdown"],
                        "fraction_real_sharpe_above_control": np.nan,
                        "median_hmm_exposure_ks": 0.0 if name.endswith("real HMM") else np.nan,
                        "median_real_minus_control_common_fee_sharpe": np.nan})
    for kind, group in sim.groupby("control", sort=False):
        row = {"control": f"Trend + {kind}", "n_simulations": len(group)}
        for col in ("cagr", "annual_volatility", "sharpe", "sortino", "max_drawdown", "calmar",
                    "mean_exposure", "turnover_per_year", "total_cost_fraction_sum", "cost_fraction_per_year"):
            row[col] = float(group[col].median())
        row.update({"observations": len(real), "sharpe_p05": float(group.sharpe.quantile(.05)),
                    "sharpe_p95": float(group.sharpe.quantile(.95)),
                    "max_drawdown_p05": float(group.max_drawdown.quantile(.05)),
                    "max_drawdown_p95": float(group.max_drawdown.quantile(.95)),
                    "fraction_real_sharpe_above_control": float((group.real_minus_control_sharpe > 0).mean()),
                    "median_hmm_exposure_ks": float(group.hmm_exposure_ks_distance.median()),
                    "median_real_minus_control_common_fee_sharpe": float(group.real_minus_control_common_fee_sharpe.median())})
        summary.append(row)
    boot_runs = {"HMM + Trend": real, "Trend": trend}
    for kind, values in daily_control.items():
        boot_runs[f"Mean control: {kind}"] = pd.DataFrame({"strategy_return": values}, index=real.index)
    bootstrap = paired_block_bootstrap(boot_runs, "HMM + Trend", [k for k in boot_runs if k != "HMM + Trend"], result.config)
    bootstrap["interpretation"] = "Paired bootstrap vs daily mean control portfolio"  # not individual-control null p-value
    period_rows = []
    for label, (start, end) in STRESS_PERIODS.items():
        rsub, tsub = real.loc[start:end], trend.loc[start:end]
        if len(rsub) < 2:
            continue
        rs = annual_sharpe(rsub.strategy_return.to_numpy(), rf, periods)
        ts = annual_sharpe(tsub.strategy_return.to_numpy(), rf, periods)
        for kind in CONTROL_NAMES:
            sample = np.asarray(period_values.get((label, kind), []), dtype=float)
            sample = sample[np.isfinite(sample)]
            period_rows.append({"period": label, "start": start, "end": end, "observations": len(rsub),
                                "control": kind, "real_sharpe": rs, "trend_sharpe": ts,
                                "control_sharpe_median": float(np.median(sample)) if len(sample) else np.nan,
                                "fraction_real_above_control": float(np.mean(rs > sample)) if len(sample) else np.nan})
    daily_frame = pd.DataFrame(daily_control, index=real.index)
    daily_frame.index.name = "Date"
    return AttributionResult(pd.DataFrame(summary), sim, bootstrap, pd.DataFrame(period_rows), daily_frame)
