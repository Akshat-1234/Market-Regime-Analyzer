"""CSV ingestion, data integrity checks and explicitly synthetic data."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_prices(frame: pd.DataFrame, date_column: str = "Date", price_column: str = "Close") -> pd.DataFrame:
    """Return sorted daily data with a timezone-naive *local calendar* Date index.

    Close is required. Open/High/Low/Volume are optional; missing optional data
    cannot be used by a model that requires it. Duplicate dates are errors.
    """
    if frame.empty:
        raise ValueError("Price data is empty")
    labels = [str(col).strip() for col in frame.columns]
    lowered = [x.casefold() for x in labels]
    if len(set(lowered)) != len(lowered):
        raise ValueError("CSV column names are ambiguous after case/whitespace normalization")
    names = dict(zip(lowered, frame.columns))
    needed = (date_column.casefold(), price_column.casefold())
    if any(name not in names for name in needed):
        raise ValueError(f"CSV needs {date_column!r} and {price_column!r}; found {labels}")
    if names[needed[0]] == names[needed[1]]:
        raise ValueError("Date and price columns must be different")
    d = pd.DataFrame()
    try:
        # Localize-none preserves an exchange's calendar date instead of shifting
        # e.g. midnight Asia/Kolkata to the previous UTC day.
        def local_day(value):
            x = pd.Timestamp(value)
            if pd.isna(x):
                return pd.NaT
            return x.tz_localize(None).normalize() if x.tzinfo is not None else x.normalize()
        d["Date"] = frame[names[needed[0]]].map(local_day)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Date column contains an invalid date") from exc
    if d["Date"].isna().any():
        raise ValueError("Date column contains missing dates")
    d["Close"] = pd.to_numeric(frame[names[needed[1]]], errors="coerce")
    close_values = d["Close"].to_numpy(dtype=float)
    if not np.isfinite(close_values).all() or (close_values <= 0).any():
        raise ValueError("Every Close must be finite and strictly positive")
    for canonical in ("Open", "High", "Low", "Volume"):
        key = canonical.casefold()
        if key in names and names[key] not in (names[needed[0]], names[needed[1]]):
            raw = frame[names[key]]
            values = pd.to_numeric(raw, errors="coerce")
            if (raw.notna() & values.isna()).any():
                raise ValueError(f"{canonical} contains a non-numeric value")
            valid = values.dropna().to_numpy(dtype=float)
            if not np.isfinite(valid).all() or (valid < 0 if canonical == "Volume" else valid <= 0).any():
                raise ValueError(f"{canonical} contains invalid values")
            d[canonical] = values
    if d["Date"].duplicated().any():
        duplicate = d.loc[d["Date"].duplicated(), "Date"].iloc[0].date()
        raise ValueError(f"Duplicate trading date {duplicate}; resolve it in the input CSV")
    d = d.sort_values("Date").set_index("Date")
    if len(d) < 2:
        raise ValueError("At least two observations are required")
    if "High" in d and "Low" in d:
        bad = d["High"].notna() & d["Low"].notna() & (d["High"] < d["Low"])
        if bad.any():
            raise ValueError(f"High is below Low on {d.index[bad][0].date()}")
    return d


def load_price_csv(path: str | Path, date_column: str = "Date", price_column: str = "Close") -> tuple[pd.DataFrame, dict]:
    path = Path(path).expanduser()
    if not path.exists():
        raise FileNotFoundError(
            f"Price CSV not found: {path}. Put your CSV in data/raw/, use --csv PATH, "
            "or run --synthetic for a demo."
        )
    content = path.read_bytes()
    try:
        raw = pd.read_csv(io.BytesIO(content))
    except (pd.errors.ParserError, UnicodeDecodeError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f"Cannot read CSV {path}: {exc}") from exc
    data = validate_prices(raw, date_column, price_column)
    marker = next((col for col in raw.columns if str(col).strip().casefold() == "data_source"), None)
    is_synthetic = marker is not None and raw[marker].astype(str).str.strip().str.upper().eq("SYNTHETIC").all()
    return data, {"kind": "synthetic" if is_synthetic else "csv", "path": str(path.resolve()), "sha256": sha256_bytes(content)}


def synthetic_prices(n: int = 2200, seed: int = 314159) -> pd.DataFrame:
    """Generate a reproducible fake series with two volatility regimes."""
    if n < 2:
        raise ValueError("n must be at least 2")
    rng = np.random.default_rng(seed)
    state = np.zeros(n, dtype=int)
    for i in range(1, n):
        flip = rng.random() < (0.025 if state[i - 1] == 0 else 0.045)
        state[i] = 1 - state[i - 1] if flip else state[i - 1]
    returns = rng.normal(np.where(state == 0, 0.00055, -0.00015), np.where(state == 0, 0.007, 0.021))
    close = 10000 * np.cumprod(1 + returns)
    previous = np.r_[close[0], close[:-1]]
    open_ = previous * (1 + rng.normal(0, 0.0025, n))
    spread = np.abs(rng.normal(0.003, 0.002, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    raw = pd.DataFrame({"Date": pd.bdate_range("2008-01-01", periods=n), "Open": open_,
                        "High": high, "Low": low, "Close": close})
    return validate_prices(raw)


def download_yahoo(ticker: str, start: str, end: str | None, output: str | Path) -> Path:
    """Download a Yahoo daily snapshot; Yahoo's end date is exclusive."""
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Install the download extra: pip install -e '.[download]'") from exc
    if not ticker.strip():
        raise ValueError("Ticker cannot be empty")
    raw = yf.download(ticker, start=start, end=end, auto_adjust=False,
                      interval="1d", progress=False, threads=False, actions=False)
    if raw.empty:
        raise RuntimeError("Yahoo returned no rows (possibly rate-limited). Supply a CSV instead.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw = raw.reset_index()
    data = validate_prices(raw)
    out = Path(output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(out, index_label="Date")
    return out


def annual_quality_table(prices: pd.DataFrame, annualization: int = 252) -> pd.DataFrame:
    """Descriptive checks, not a certification of vendor data correctness."""
    c = prices["Close"]
    result = pd.DataFrame(index=prices.index)
    result["close_return"] = c.pct_change(fill_method=None)
    if "Open" in prices:
        result["overnight_gap"] = prices["Open"] / c.shift(1) - 1
        result["intraday_return"] = c / prices["Open"] - 1
    rows = []
    for year, group in result.groupby(result.index.year):
        gap = group["overnight_gap"].dropna() if "overnight_gap" in group else pd.Series(dtype=float)
        intraday = group["intraday_return"].dropna() if "intraday_return" in group else pd.Series(dtype=float)
        correlation = np.nan
        if "intraday_return" in group:
            pair = group[["close_return", "intraday_return"]].dropna()
            if len(pair) > 1 and pair["close_return"].std() > 1e-12 and pair["intraday_return"].std() > 1e-12:
                correlation = pair["close_return"].corr(pair["intraday_return"])
        original = prices.loc[group.index]
        open_available = original["Open"].notna().mean() if "Open" in original else np.nan
        outside_range = np.nan
        if {"Open", "High", "Low", "Close"}.issubset(original.columns):
            complete = original[["Open", "High", "Low", "Close"]].dropna()
            if len(complete):
                outside_range = ((complete["Open"] > complete["High"]) | (complete["Open"] < complete["Low"]) |
                                 (complete["Close"] > complete["High"]) | (complete["Close"] < complete["Low"])).mean()
        rows.append({"year": int(year), "observations": len(group),
                     "open_available_fraction": open_available,
                     "ohlc_out_of_range_fraction": outside_range,
                     "close_return_vol_annualized": group["close_return"].std() * np.sqrt(annualization),
                     "overnight_gap_vol_daily": gap.std() if len(gap) > 1 else np.nan,
                     "intraday_vol_daily": intraday.std() if len(intraday) > 1 else np.nan,
                     "open_near_previous_close_fraction": (gap.abs() < 1e-5).mean() if len(gap) else np.nan,
                     "close_intraday_return_correlation": correlation})
    return pd.DataFrame(rows)
