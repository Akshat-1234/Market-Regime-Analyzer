"""Canonical NIFTY input and parsed-data identity contracts.

The raw-byte hash is authoritative for the preserved CSV.  The parsed-record
fingerprint is a separate logical-data identity and never replaces it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from ._validation import canonical_json_bytes, require_sha256, sha256_bytes

CANONICAL_DATA_SHA256 = "ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4"
CANONICAL_COLUMNS = ("Date", "Close", "High", "Low", "Open")
OHLC_COLUMNS = CANONICAL_COLUMNS[1:]
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class DatasetProvenance:
    raw_sha256: str
    parsed_sha256: str
    rows: int
    start_date: str
    end_date: str
    columns: tuple[str, ...]
    newline_style: str

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["columns"] = list(self.columns)
        return result


@dataclass(frozen=True)
class CanonicalDataset:
    frame: pd.DataFrame
    provenance: DatasetProvenance


def validate_ohlc_frame(frame: pd.DataFrame, *, canonical_order: bool = False) -> pd.DataFrame:
    """Return a defensive, date-indexed copy after structural OHLC validation.

    Structural validity is not vendor, corporate-action, calendar-completeness,
    total-return, or licensing verification.
    """
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("market data must be a pandas DataFrame")
    columns = tuple(str(column) for column in frame.columns)
    if len(columns) != len(set(columns)) or set(columns) != set(CANONICAL_COLUMNS):
        raise ValueError(f"required columns are exactly {CANONICAL_COLUMNS}")
    if canonical_order and columns != CANONICAL_COLUMNS:
        raise ValueError(f"canonical CSV column order must be {CANONICAL_COLUMNS}")
    if len(frame) == 0:
        raise ValueError("market data must contain observations")

    output = frame.copy(deep=True)
    if pd.api.types.is_datetime64_any_dtype(output["Date"]):
        dates = pd.DatetimeIndex(output["Date"])
        if dates.tz is not None or (dates != dates.normalize()).any():
            raise ValueError("Date must contain timezone-naive session dates only")
    else:
        raw_dates = output["Date"]
        if raw_dates.isna().any() or not raw_dates.map(
                lambda value: isinstance(value, str) and bool(_DATE_ONLY.fullmatch(value))).all():
            raise ValueError("Date text must use strict YYYY-MM-DD session dates")
        try:
            dates = pd.DatetimeIndex(pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="raise"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Date contains an invalid calendar session") from exc
    if dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("Date must be strictly increasing and unique")
    output["Date"] = dates

    for column in OHLC_COLUMNS:
        try:
            output[column] = pd.to_numeric(output[column], errors="raise").astype(float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{column} must be numeric") from exc
    values = output.loc[:, OHLC_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("OHLC values must be present and finite")
    if (values <= 0).any():
        raise ValueError("OHLC values must be strictly positive")

    close = output["Close"].to_numpy()
    high = output["High"].to_numpy()
    low = output["Low"].to_numpy()
    open_ = output["Open"].to_numpy()
    if (high < np.maximum.reduce([open_, close, low])).any():
        raise ValueError("High must be at least Open, Close, and Low")
    if (low > np.minimum.reduce([open_, close, high])).any():
        raise ValueError("Low must be at most Open, Close, and High")

    output = output.set_index("Date")
    output.index.name = "Date"
    return output.loc[:, OHLC_COLUMNS]


def parsed_records_sha256(frame: pd.DataFrame) -> str:
    """Hash logical rows independently of CSV line endings and insignificant spacing."""
    source = frame
    if isinstance(frame, pd.DataFrame) and "Date" not in frame.columns and frame.index.name == "Date":
        source = frame.reset_index()
    clean = validate_ohlc_frame(source)
    records = [[index.strftime("%Y-%m-%d"),
                *[format(float(value), ".17g") for value in row]]
               for index, row in zip(clean.index, clean.to_numpy())]
    return sha256_bytes(canonical_json_bytes({"columns": list(clean.columns), "rows": records}))


def read_canonical_csv(path: str | Path,
                       expected_sha256: str = CANONICAL_DATA_SHA256) -> CanonicalDataset:
    """Read without altering bytes and verify both raw and parsed identities."""
    require_sha256(expected_sha256, "expected_sha256")
    raw = Path(path).read_bytes()
    raw_hash = sha256_bytes(raw)
    if raw_hash != expected_sha256:
        raise ValueError(f"canonical raw SHA-256 mismatch: expected {expected_sha256}, got {raw_hash}")
    try:
        parsed = pd.read_csv(BytesIO(raw), dtype=str)
    except Exception as exc:
        raise ValueError("canonical CSV could not be parsed") from exc
    clean = validate_ohlc_frame(parsed, canonical_order=True)
    logical = parsed_records_sha256(clean)
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n")
    newline = "CRLF" if lf > 0 and crlf == lf else "LF" if lf > 0 and crlf == 0 else "mixed"
    provenance = DatasetProvenance(
        raw_sha256=raw_hash,
        parsed_sha256=logical,
        rows=len(clean),
        start_date=clean.index[0].strftime("%Y-%m-%d"),
        end_date=clean.index[-1].strftime("%Y-%m-%d"),
        columns=CANONICAL_COLUMNS,
        newline_style=newline,
    )
    return CanonicalDataset(clean, provenance)
