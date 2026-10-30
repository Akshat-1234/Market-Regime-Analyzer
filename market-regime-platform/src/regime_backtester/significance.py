"""Dependence-aware inference for strategy and state comparisons.

Everything here treats time-series observations as dependent.  Percentile
intervals from a stationary (Politis-Romano) bootstrap and White/Hansen style
reality checks are reported; none of them repairs prior model search, and every
output is labelled as exploratory unless the caller pre-registered the test.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def stationary_bootstrap_indices(n: int, *, samples: int = 1000, mean_block: float = 20.0,
                                 seed: int = 1701) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix (samples, n)."""
    if n < 2 or samples < 2 or mean_block < 1:
        raise ValueError("Need n>=2, samples>=2 and mean_block>=1")
    rng = np.random.default_rng(seed)
    p = min(1.0, 1.0 / mean_block)
    starts = rng.integers(0, n, size=samples)
    uniform = rng.random((samples, n))
    new_block = uniform < p
    indices = np.empty((samples, n), dtype=np.int64)
    indices[:, 0] = starts
    for t in range(1, n):
        indices[:, t] = np.where(new_block[:, t],
                                 rng.integers(0, n, size=samples),
                                 (indices[:, t - 1] + 1) % n)
    return indices


def sharpe_from_values(values: np.ndarray, periods: int) -> np.ndarray:
    """Annualised Sharpe for every row of a (samples, n) excess-return matrix."""
    sd = values.std(axis=1, ddof=1)
    return np.divide(np.sqrt(periods) * values.mean(axis=1), sd,
                     out=np.full(len(values), np.nan), where=sd > 1e-12)


def paired_sharpe_interval(candidate: pd.Series, control: pd.Series, *, periods: int,
                           daily_rf: float, samples: int = 1000, mean_block: float = 20.0,
                           seed: int = 1701, confidence: float = 0.95) -> dict:
    """Stationary-bootstrap percentile interval for a Sharpe difference.

    Returns the observed difference, the interval and the bootstrap fraction of
    non-positive differences.  The fraction is *not* a conventional p-value.
    """
    if not candidate.index.equals(control.index):
        raise ValueError("Candidate and control must share a calendar")
    c = candidate.to_numpy(dtype=float) - daily_rf
    b = control.to_numpy(dtype=float) - daily_rf
    idx = stationary_bootstrap_indices(len(c), samples=samples, mean_block=mean_block, seed=seed)
    diff = sharpe_from_values(c[idx], periods) - sharpe_from_values(b[idx], periods)
    valid = diff[np.isfinite(diff)]
    if not len(valid):
        raise ValueError("No finite bootstrap differences")
    alpha = (1 - confidence) / 2
    observed = (float(sharpe_from_values(c[None, :], periods)[0])
                - float(sharpe_from_values(b[None, :], periods)[0]))
    return {"observed_difference": observed,
            "lower": float(np.quantile(valid, alpha)),
            "upper": float(np.quantile(valid, 1 - alpha)),
            "fraction_le_zero": float((valid <= 0).mean()),
            "samples": int(len(valid)), "mean_block": mean_block,
            "confidence": confidence}


def reality_check(returns: pd.DataFrame, benchmark: str, *, periods: int, daily_rf: float,
                  samples: int = 1000, mean_block: float = 20.0, seed: int = 1701) -> dict:
    """Hansen-style studentised reality check / SPA over a family of strategies.

    H0: no strategy in ``returns`` has positive expected excess return over the
    benchmark.  The bootstrap null is recentred with
    ``max(0, mean(d_k))`` per strategy, which is the SPA consistent recentring and
    is more conservative than White's original recentring.  A small p-value means
    the family's best member is unlikely under the null *for this family*; it does
    not establish that the winning strategy is the one with real information.
    """
    if benchmark not in returns:
        raise ValueError(f"Benchmark {benchmark!r} is not in the return table")
    candidates = [c for c in returns.columns if c != benchmark]
    if not candidates:
        raise ValueError("No candidate strategies")
    # Absolute excess returns differ only by a common cash rate, so the
    # benchmark difference is invariant to it; ``periods`` is kept for API parity.
    d = returns[candidates].sub(returns[benchmark], axis=0).to_numpy(dtype=float)
    n = len(d)
    mean = d.mean(axis=0)
    sd = d.std(axis=0, ddof=1)
    sd = np.where(sd > 1e-12, sd, np.nan)
    observed = np.nanmax(np.sqrt(n) * mean / sd)
    idx = stationary_bootstrap_indices(n, samples=samples, mean_block=mean_block, seed=seed)
    boot = d[idx]  # (samples, n, k)
    boot_mean = boot.mean(axis=1)
    recentre = np.maximum(0.0, mean)
    null = boot_mean - recentre
    null_sd = boot.std(axis=1, ddof=1)
    null_sd = np.where(null_sd > 1e-12, null_sd, np.nan)
    statistics = np.sqrt(n) * null / null_sd
    with np.errstate(invalid="ignore"):
        best = np.nanmax(statistics, axis=1)
    valid = best[np.isfinite(best)]
    p_value = float((valid >= observed).mean()) if len(valid) else float("nan")
    ranking = pd.DataFrame({"strategy": candidates,
                            "mean_excess_vs_benchmark": mean,
                            "t_statistic": np.sqrt(n) * mean / sd}).sort_values(
        "t_statistic", ascending=False)
    return {"observed_statistic": float(observed), "p_value": p_value,
            "samples": int(len(valid)), "mean_block": mean_block,
            "benchmark": benchmark, "ranking": ranking}


def diebold_mariano(loss_a: pd.Series, loss_b: pd.Series, *, lags: int = 10) -> dict:
    """Diebold-Mariano test for equal predictive loss (HAC variance)."""
    if not loss_a.index.equals(loss_b.index):
        raise ValueError("Loss series must share a calendar")
    d = (loss_a - loss_b).to_numpy(dtype=float)
    n = len(d)
    if n < 10:
        raise ValueError("Too few observations for a DM test")
    mean = d.mean()
    gamma0 = np.dot(d, d) / n
    variance = gamma0
    for lag in range(1, min(lags, n - 1) + 1):
        gamma = np.dot(d[lag:], d[:-lag]) / n
        variance += 2 * (1 - lag / (lags + 1)) * gamma
    if variance <= 0:
        return {"statistic": float("nan"), "p_value": float("nan"), "mean_difference": float(mean)}
    statistic = mean / np.sqrt(variance / n)
    from scipy.stats import norm

    return {"statistic": float(statistic), "p_value": float(2 * (1 - norm.cdf(abs(statistic)))),
            "mean_difference": float(mean), "lags": lags}
