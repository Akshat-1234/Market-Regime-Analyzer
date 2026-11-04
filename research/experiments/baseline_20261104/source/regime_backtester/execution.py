"""Self-financing close-to-close simulation for long/cash targets."""
from __future__ import annotations

import numpy as np
import pandas as pd


def simulate(signal: pd.Series, market_returns: pd.Series, *, initial_capital: float,
             annual_risk_free_rate: float, trading_days_per_year: int,
             transaction_cost_bps: float, execution_delay_sessions: int = 0,
             risk_free_annual_by_date: pd.Series | None = None) -> pd.DataFrame:
    """Trade at the decision close or after a configurable extra delay,
    and then earn the following close-to-close return.

    We solve the proportional cost/rebalance equation exactly. Between trades,
    actual risky weight drifts as risky and cash assets earn different returns.
    The last signal has no next observed return and is never executed.
    """
    if not isinstance(execution_delay_sessions, int) or execution_delay_sessions < 0:
        raise ValueError("execution_delay_sessions must be a non-negative integer")
    if len(signal) < execution_delay_sessions + 2 or not signal.index.is_unique or not signal.index.is_monotonic_increasing:
        raise ValueError("Not enough unique, chronologically sorted signal dates for the delay")
    if not signal.index.isin(market_returns.index).all():
        raise ValueError("Market returns are missing a signal date")
    s = signal.astype(float).to_numpy()
    r = market_returns.reindex(signal.index).astype(float).to_numpy()
    if not np.isfinite(s).all() or (s < 0).any() or (s > 1).any():
        raise ValueError("Long/cash targets must be finite and within [0, 1]")
    if not np.isfinite(r[1:]).all() or (r[1:] <= -1).any():
        raise ValueError("Next-day market returns must be finite and above -100%")
    if initial_capital <= 0 or trading_days_per_year <= 0 or annual_risk_free_rate <= -1:
        raise ValueError("Invalid capital, annualization, or risk-free rate")
    c = transaction_cost_bps / 10000.0
    if not 0 <= c < 1:
        raise ValueError("Transaction cost must be in [0, 10000) bps")
    rf = (1 + annual_risk_free_rate) ** (1 / trading_days_per_year) - 1
    dynamic_rf = None
    if risk_free_annual_by_date is not None:
        if not risk_free_annual_by_date.index.is_unique:
            raise ValueError("Dynamic cash-rate dates must be unique")
        annual_rates = risk_free_annual_by_date.reindex(signal.index).to_numpy(dtype=float)
        if not np.isfinite(annual_rates).all() or (annual_rates <= -1).any():
            raise ValueError("Dynamic cash rates must be finite, > -1 and cover every signal date")
        dynamic_rf = (1 + annual_rates) ** (1 / trading_days_per_year) - 1
    wealth = float(initial_capital)
    risky = 0.0
    peak = wealth
    rows = []
    for i in range(execution_delay_sessions, len(s) - 1):
        target = s[i - execution_delay_sessions]
        before = wealth
        prior_weight = risky / before
        numerator = target * before - risky
        # delta = target * (before - c*abs(delta)) - risky.
        delta = numerator / (1 + target * c) if numerator >= 0 else numerator / (1 - target * c)
        cost = c * abs(delta)
        invested = risky + delta
        cash = before - cost - invested
        if invested < -1e-7 or cash < -1e-7:
            raise AssertionError("Rebalance is not self-financing")
        invested = max(invested, 0.0)
        cash = max(cash, 0.0)
        risky = invested * (1 + r[i + 1])
        # The known rate at execution close, not the next day's later rate.
        cash_rf = rf if dynamic_rf is None else dynamic_rf[i]
        wealth = risky + cash * (1 + cash_rf)
        if not np.isfinite(wealth) or wealth <= 0:
            raise ValueError("Portfolio value became non-positive or non-finite")
        peak = max(peak, wealth)
        rows.append({"Date": signal.index[i + 1], "decision_date": signal.index[i - execution_delay_sessions],
                     "execution_date": signal.index[i],
                     "market_return": r[i + 1], "target_exposure": target,
                     "pre_trade_exposure": prior_weight, "turnover": abs(delta) / before,
                     "cost_fraction": cost / before, "strategy_return": wealth / before - 1,
                     "equity": wealth, "drawdown": wealth / peak - 1})
    return pd.DataFrame(rows).set_index("Date")
