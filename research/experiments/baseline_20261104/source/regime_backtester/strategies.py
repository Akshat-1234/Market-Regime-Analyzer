"""Fixed close-of-day benchmarks. Exposure is a target for the NEXT interval."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _latching(entry: pd.Series, exit_: pd.Series) -> pd.Series:
    if not entry.index.equals(exit_.index):
        raise ValueError("Entry and exit dates do not match")
    holding = False
    output = []
    for buy, sell in zip(entry.fillna(False), exit_.fillna(False)):
        if holding and bool(sell):
            holding = False
        elif not holding and bool(buy):
            holding = True
        output.append(float(holding))
    return pd.Series(output, index=entry.index)


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Simple rolling RSI; explicitly handle all-gain/all-loss/flat windows."""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    ratio = gain / loss.replace(0, np.nan)
    result = 100 - 100 / (1 + ratio)
    result = result.mask((loss == 0) & (gain > 0), 100.0)
    result = result.mask((gain == 0) & (loss > 0), 0.0)
    return result.mask((gain == 0) & (loss == 0), 50.0)


def fixed_signals(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
    c = prices["Close"].astype(float)
    r = c.pct_change(fill_method=None)
    b = config["backtest"]
    periods = b["trading_days_per_year"]
    out = pd.DataFrame(index=prices.index)
    out["Buy & Hold"] = 1.0
    # t-stat > 0 is exactly mean(return) > 0 for positive standard deviation.
    out[f"Trend {b['trend_window']}"] = (r.rolling(b["trend_window"]).mean() > 0).astype(float)
    out[f"Momentum {b['momentum_window']}"] = (c.pct_change(b["momentum_window"], fill_method=None) > 0).astype(float)
    ma = c.rolling(b["mean_reversion_window"]).mean()
    out["MA Reversion"] = _latching(c < ma * (1 - b["mean_reversion_entry_band"]), c >= ma)
    rs = rsi(c)
    out["RSI Reversion"] = _latching(rs < 30, rs >= 50)
    upper = c.shift(1).rolling(50).max()
    lower = c.shift(1).rolling(20).min()
    out["Donchian"] = _latching(c > upper, c < lower)
    vol = r.rolling(20).std() * np.sqrt(periods)
    out["Vol Target"] = (b["vol_target"] / vol.replace(0, np.nan)).clip(0, 1)
    out["Vol Target"] = out["Vol Target"].mask(vol == 0, 1.0).fillna(0.0)
    return out
