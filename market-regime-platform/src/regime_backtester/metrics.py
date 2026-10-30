"""Performance, descriptive regime diagnostics and paired bootstrap."""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_rf(annual: float, periods: int) -> float:
    return (1 + annual) ** (1 / periods) - 1


def annual_sharpe(returns: np.ndarray, annual_rf: float, periods: int) -> float:
    r = np.asarray(returns, dtype=float)
    if len(r) < 2 or not np.isfinite(r).all():
        return float("nan")
    excess = r - daily_rf(annual_rf, periods)
    sd = float(np.std(excess, ddof=1))
    return float(np.sqrt(periods) * excess.mean() / sd) if sd > 1e-12 else float("nan")


def performance_table(runs: dict[str, pd.DataFrame], config: dict) -> pd.DataFrame:
    b = config["backtest"]
    periods, rf, initial = b["trading_days_per_year"], b["annual_risk_free_rate"], b["initial_capital"]
    result = []
    for name, run in runs.items():
        r = run["strategy_return"].to_numpy(dtype=float)
        n = len(r)
        final = float(run["equity"].iloc[-1])
        years = n / periods
        cagr = float((final / initial) ** (1 / years) - 1)
        vol = float(np.std(r, ddof=1) * np.sqrt(periods)) if n > 1 else float("nan")
        sharpe = annual_sharpe(r, rf, periods)
        excess = r - daily_rf(rf, periods)
        downside = float(np.sqrt(np.mean(np.minimum(excess, 0) ** 2)))
        sortino = float(np.sqrt(periods) * np.mean(excess) / downside) if downside > 1e-12 else float("nan")
        max_dd = -float(run["drawdown"].min())
        result.append({"strategy": name, "observations": n, "final_value": final,
                       "total_return": final / initial - 1, "cagr": cagr,
                       "annual_volatility": vol, "sharpe": sharpe, "sortino": sortino,
                       "max_drawdown": max_dd, "calmar": cagr / max_dd if max_dd > 1e-12 else np.nan,
                       "mean_exposure": float(run["target_exposure"].mean()),
                       "turnover_per_year": float(run["turnover"].sum() / years),
                       "total_cost_fraction_sum": float(run["cost_fraction"].sum())})
    return pd.DataFrame(result).set_index("strategy")


def regime_tables(signals: pd.DataFrame, runs: dict[str, pd.DataFrame], config: dict
                  ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """H1/H2: decision-time label, outcomes from the subsequent held interval."""
    reference = next(iter(runs.values()))
    decisions = pd.DatetimeIndex(reference["decision_date"])
    labels = signals.loc[decisions, "primary_regime"].astype(int).to_numpy()
    probabilities = signals.loc[decisions, [c for c in signals.columns if c.startswith("p_state_")]]
    confidence = probabilities.max(axis=1).to_numpy()
    market = reference["market_return"].to_numpy()
    k = probabilities.shape[1]
    annual = config["backtest"]["trading_days_per_year"]
    rf = config["backtest"]["annual_risk_free_rate"]
    # Descriptive lengths of consecutive ranked-label runs, including year boundaries.
    runs_by_state: dict[int, list[int]] = {s: [] for s in range(k)}
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            runs_by_state[int(labels[start])].append(i - start)
            start = i
    h1, h2 = [], []
    for state in range(k):
        mask = labels == state
        y = market[mask]
        n = int(mask.sum())
        h1.append({"state_by_train_vol": state, "days": n, "occupancy": n / len(labels),
                   "avg_run_length": float(np.mean(runs_by_state[state])) if runs_by_state[state] else np.nan,
                   "mean_confidence": float(confidence[mask].mean()) if n else np.nan,
                   "mean_held_interval_market_return": float(y.mean()) if n else np.nan,
                   "held_interval_volatility_annualized": float(y.std(ddof=1) * np.sqrt(annual)) if n > 1 else np.nan,
                   "positive_held_interval_fraction": float((y > 0).mean()) if n else np.nan})
        for name, df in runs.items():
            if not df.index.equals(reference.index):
                raise ValueError("Strategy return calendars differ")
            sub = df["strategy_return"].to_numpy()[mask]
            h2.append({"state_by_train_vol": state, "strategy": name, "days": n,
                       "sharpe": annual_sharpe(sub, rf, annual),
                       "mean_exposure": float(df["target_exposure"].to_numpy()[mask].mean()) if n else np.nan})
    counts = np.zeros((k, k), dtype=int)
    for left, right in zip(labels[:-1], labels[1:]):
        counts[left, right] += 1
    denom = counts.sum(axis=1, keepdims=True)
    transition = np.divide(counts, denom, out=np.full((k, k), np.nan), where=denom != 0)
    transitions = pd.DataFrame(transition, index=[f"state_{i}" for i in range(k)],
                               columns=[f"state_{i}" for i in range(k)])
    return pd.DataFrame(h1), pd.DataFrame(h2), transitions


def paired_block_bootstrap(runs: dict[str, pd.DataFrame], candidate: str,
                           controls: list[str], config: dict) -> pd.DataFrame:
    """Circular moving-block percentile intervals for candidate minus control.

    Dates are resampled in identical blocks across strategies. The fraction of
    differences <= 0 is descriptive, NOT an unadjusted hypothesis-test p-value.
    """
    b, boot = config["backtest"], config["bootstrap"]
    base = runs[candidate]["strategy_return"]
    for control in controls:
        if not base.index.equals(runs[control].index):
            raise ValueError("Bootstrap requires identical return calendars")
    n = len(base)
    if n < 2:
        raise ValueError("Need at least two return observations for bootstrap")
    rng = np.random.default_rng(boot["seed"])
    length = boot["block_length"]
    count = int(np.ceil(n / length))
    starts = rng.integers(0, n, size=(boot["samples"], count))
    indices = ((starts[:, :, None] + np.arange(length)) % n).reshape(boot["samples"], -1)[:, :n]
    periods, rf = b["trading_days_per_year"], b["annual_risk_free_rate"]
    drf = daily_rf(rf, periods)

    def bootstrap_sharpes(series: pd.Series) -> np.ndarray:
        values = series.to_numpy()[indices] - drf
        sd = values.std(axis=1, ddof=1)
        return np.divide(np.sqrt(periods) * values.mean(axis=1), sd,
                         out=np.full(boot["samples"], np.nan), where=sd > 1e-12)

    candidate_sharpes = bootstrap_sharpes(base)
    observed = annual_sharpe(base.to_numpy(), rf, periods)
    alpha = (1 - boot["confidence"]) / 2
    rows = []
    for control in controls:
        c = runs[control]["strategy_return"]
        diff = candidate_sharpes - bootstrap_sharpes(c)
        valid = diff[np.isfinite(diff)]
        if not len(valid):
            raise ValueError(f"No finite bootstrap Sharpe comparisons for {control}")
        rows.append({"candidate": candidate, "control": control,
                     "observed_sharpe_difference": observed - annual_sharpe(c.to_numpy(), rf, periods),
                     "lower": float(np.quantile(valid, alpha)),
                     "upper": float(np.quantile(valid, 1 - alpha)),
                     "fraction_le_zero": float((valid <= 0).mean()),
                     "valid_samples": len(valid), "block_length": length,
                     "confidence": boot["confidence"]})
    return pd.DataFrame(rows)
