"""Reusable slice metrics without averaging fold-level statistics."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .metrics import daily_rf


def recovery_details(returns: np.ndarray) -> dict:
    r = np.asarray(returns, dtype=float)
    wealth = np.r_[1.0, np.cumprod(1 + r)]
    peak = np.maximum.accumulate(wealth)
    drawdown = wealth / peak - 1
    trough = int(np.argmin(drawdown))
    if trough == 0 or drawdown[trough] >= -1e-12:
        return {"max_drawdown": 0.0, "peak_offset": None, "trough_offset": None,
                "recovery_offset": None, "sessions_to_recover": None,
                "sessions_from_trough_to_recover": None, "recovery_status": "no_drawdown"}
    peak_value = peak[trough]
    peak_indices = np.flatnonzero(np.isclose(wealth[:trough + 1], peak_value, rtol=1e-12, atol=1e-12))
    peak_index = int(peak_indices[-1])
    recovery = np.flatnonzero(wealth[trough + 1:] >= peak_value * (1 - 1e-12))
    recovery_index = int(trough + 1 + recovery[0]) if len(recovery) else None
    return {"max_drawdown": float(-drawdown[trough]), "peak_offset": peak_index,
            "trough_offset": trough, "recovery_offset": recovery_index,
            "sessions_to_recover": recovery_index - peak_index if recovery_index is not None else None,
            "sessions_from_trough_to_recover": recovery_index - trough if recovery_index is not None else None,
            "recovery_status": "recovered_in_window" if recovery_index is not None else "not_recovered_by_window_end"}


def evaluate_window(run: pd.DataFrame, annual_rf: float, periods: int,
                    daily_cash_rates: np.ndarray | pd.Series | None = None) -> dict:
    """Evaluate actual returns in one contiguous slice, rebased to wealth 1.

    Holdings and fees at the slice boundary remain those of the original run;
    there is no artificial close/reopen. If cash rate is time-varying, its daily
    values must already be aligned to each return's execution date.
    """
    if len(run) == 0:
        raise ValueError("Cannot evaluate an empty return window")
    r = run["strategy_return"].to_numpy(dtype=float)
    if not np.isfinite(r).all() or (r <= -1).any():
        raise ValueError("Return window contains invalid returns")
    n = len(r)
    rf = np.full(n, daily_rf(annual_rf, periods)) if daily_cash_rates is None else np.asarray(daily_cash_rates, dtype=float)
    if len(rf) != n or not np.isfinite(rf).all():
        raise ValueError("Cash rates must be finite and aligned with returns")
    excess = r - rf
    sd = float(np.std(r, ddof=1)) if n > 1 else np.nan
    excess_sd = float(np.std(excess, ddof=1)) if n > 1 else np.nan
    downside = float(np.sqrt(np.mean(np.minimum(excess, 0) ** 2)))
    total = float(np.prod(1 + r) - 1)
    cagr = float((1 + total) ** (periods / n) - 1)
    dd = recovery_details(r)
    max_dd = dd["max_drawdown"]
    return {"observations": n, "total_return": total, "cagr": cagr,
            "annual_volatility": sd * np.sqrt(periods) if n > 1 else np.nan,
            "sharpe": float(np.sqrt(periods) * excess.mean() / excess_sd) if n > 1 and excess_sd > 1e-12 else np.nan,
            # Mean over ALL days, with positive excess contributing zero.
            "sortino": float(np.sqrt(periods) * excess.mean() / downside) if downside > 1e-12 else np.nan,
            "max_drawdown": max_dd, "calmar": cagr / max_dd if max_dd > 1e-12 else np.nan,
            "mean_exposure": float(run["target_exposure"].mean()) if "target_exposure" in run else np.nan,
            "turnover_per_year": float(run["turnover"].sum() * periods / n) if "turnover" in run else np.nan,
            "total_cost_fraction_sum": float(run["cost_fraction"].sum()) if "cost_fraction" in run else np.nan,
            "cost_fraction_per_year": float(run["cost_fraction"].sum() * periods / n) if "cost_fraction" in run else np.nan,
            "sessions_to_recover": dd["sessions_to_recover"],
            "sessions_from_trough_to_recover": dd["sessions_from_trough_to_recover"],
            "recovery_status": dd["recovery_status"]}
