"""Past-only alignment of a cited 91-day auction-yield cash proxy."""
from __future__ import annotations
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd


def align_auction_yields(auction_csv: str | Path, calendar: pd.DatetimeIndex, max_age_days: int = 31) -> tuple[pd.Series, pd.DataFrame]:
    """Annual rate available at each close: latest auction strictly before date.

    Cut-off yields are a proxy, not realized T-bill P&L. This avoids using an
    auction-day value whose intraday publication time is unknown. No backward
    fill; missing or stale observations fail rather than silently fabricate.
    """
    if not calendar.is_unique or not calendar.is_monotonic_increasing:
        raise ValueError("Calendar must be unique and sorted")
    if max_age_days < 1:
        raise ValueError("max_age_days must be positive")
    a = pd.read_csv(auction_csv, parse_dates=["auction_date"])
    if not {"auction_date", "cutoff_yield_percent"}.issubset(a.columns):
        raise ValueError("Auction CSV must have auction_date and cutoff_yield_percent")
    a["cutoff_yield_percent"] = pd.to_numeric(a["cutoff_yield_percent"], errors="coerce")
    if a.auction_date.isna().any() or a.auction_date.duplicated().any() or not np.isfinite(a.cutoff_yield_percent).all():
        raise ValueError("Invalid or duplicated auction-yield values")
    a = a.sort_values("auction_date")
    d = pd.DataFrame({"Date": calendar})
    aligned = pd.merge_asof(d, a, left_on="Date", right_on="auction_date", direction="backward", allow_exact_matches=False)
    aligned["age_days"] = (aligned.Date - aligned.auction_date).dt.days
    if aligned.auction_date.isna().any() or (aligned.age_days > max_age_days).any():
        raise ValueError(f"Auction rate absent or older than {max_age_days} calendar days")
    aligned["annual_rate"] = aligned.cutoff_yield_percent / 100.0
    if (aligned.annual_rate <= -1).any():
        raise ValueError("Auction-derived rate must exceed -100%")
    rates = pd.Series(aligned.annual_rate.to_numpy(), index=calendar, name="annual_rate")
    return rates, aligned


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
