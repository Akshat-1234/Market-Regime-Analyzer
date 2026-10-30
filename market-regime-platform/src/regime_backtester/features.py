"""Causal, close-of-day features. No fitting or future observations here."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_features(prices: pd.DataFrame, annualization: int = 252) -> pd.DataFrame:
    c = prices["Close"].astype(float)
    r = c.pct_change(fill_method=None)
    f = pd.DataFrame(index=prices.index)
    f["daily_return"] = r
    f["sign_persistence"] = np.sign(r).rolling(5).mean()
    f["volatility_20"] = r.rolling(20).std() * np.sqrt(annualization)
    f["trend_20"] = c / c.rolling(20).mean() - 1
    f["return_5"] = c.pct_change(5, fill_method=None)
    f["return_20"] = c.pct_change(20, fill_method=None)
    f["return_60"] = c.pct_change(60, fill_method=None)
    f["volatility_5"] = r.rolling(5).std() * np.sqrt(annualization)
    f["volatility_60"] = r.rolling(60).std() * np.sqrt(annualization)
    f["volatility_change"] = f["volatility_20"] - f["volatility_20"].shift(5)
    f["ma_distance_50"] = c / c.rolling(50).mean() - 1
    f["ma_distance_200"] = c / c.rolling(200).mean() - 1
    if {"High", "Low"}.issubset(prices.columns):
        f["high_low_range"] = (prices["High"] - prices["Low"]) / c
    else:
        f["high_low_range"] = np.nan
    if "Open" in prices.columns:
        f["intraday_return"] = c / prices["Open"] - 1
        f["overnight_gap"] = prices["Open"] / c.shift(1) - 1
    else:
        f["intraday_return"] = np.nan
        f["overnight_gap"] = np.nan
    f["return_skewness"] = r.rolling(20).skew()
    # A trailing high, not the maximum over the complete future-containing sample.
    f["drawdown_252"] = c / c.rolling(252).max() - 1
    # --- Research feature library (added 2026-10-30) -------------------------
    # Each column is a candidate, not a default. They are only used by an
    # explicit experiment specification; the baseline models select by name and
    # are therefore numerically unchanged.
    # Downside semivariance: asymmetric risk that total volatility hides.
    f["downside_vol_20"] = (np.sqrt((r.clip(upper=0.0) ** 2).rolling(20).mean())
                            * np.sqrt(annualization))
    # Parkinson range volatility: uses the intraday range and is less noisy than
    # close-to-close volatility. Requires High/Low only (never Open).
    if {"High", "Low"}.issubset(prices.columns):
        log_range_sq = np.log(prices["High"].astype(float) / prices["Low"].astype(float)) ** 2
        f["parkinson_vol_20"] = (np.sqrt(log_range_sq.rolling(20).mean() / (4 * np.log(2)))
                                 * np.sqrt(annualization))
    else:
        f["parkinson_vol_20"] = np.nan
    # Volatility of volatility: instability of the risk environment itself.
    f["vol_of_vol_60"] = f["volatility_20"].rolling(60).std()
    # Risk-adjusted 20-day trend (a t-statistic in annualised units).
    f["risk_adj_trend_20"] = f["return_20"] / (
        f["volatility_20"] * np.sqrt(20 / annualization))
    # Tail-event frequency: share of the past 60 sessions beyond two sigma.
    f["tail_freq_60"] = (r.abs() > 2 * r.rolling(60).std()).rolling(60).mean()
    return f.replace([np.inf, -np.inf], np.nan)


def common_model_features(features: pd.DataFrame, models: list[dict]) -> pd.DataFrame:
    """Align models to one contiguous, fully observed sample, without imputation."""
    columns = list(dict.fromkeys(col for m in models for col in m["features"]))
    unknown = [col for col in columns if col not in features]
    if unknown:
        raise ValueError(f"Unknown model features: {unknown}")
    selected = features[columns]
    valid = selected.notna().all(axis=1)
    if not valid.any():
        bad = selected.columns[selected.notna().sum() == 0].tolist()
        raise ValueError(f"No complete feature rows. Missing or unusable columns: {bad}; check OHLC requirements")
    start = np.flatnonzero(valid.to_numpy())[0]
    tail = selected.iloc[start:]
    if tail.isna().any(axis=None):
        first_bad = tail.index[tail.isna().any(axis=1)][0].date()
        badcols = tail.columns[tail.loc[pd.Timestamp(first_bad)].isna()].tolist()
        raise ValueError(f"Feature data has an internal gap on {first_bad}: {badcols}; repair input before fitting")
    return tail
