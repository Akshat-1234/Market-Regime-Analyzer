"""Small validation primitives shared by the Task 2 contracts."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + "\n").encode("utf-8")


def as_timestamp(value: Any, field: str) -> pd.Timestamp:
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not a valid timestamp") from exc
    if pd.isna(stamp) or stamp.tzinfo is not None:
        raise ValueError(f"{field} must be a present, timezone-naive session date")
    if stamp != stamp.normalize():
        raise ValueError(f"{field} must be a session date without a time component")
    return stamp


def iso_date(value: Any, field: str) -> str:
    return as_timestamp(value, field).strftime("%Y-%m-%d")


def validate_probability_matrix(probabilities: Any) -> np.ndarray:
    matrix = np.asarray(probabilities, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0 or matrix.shape[1] < 2:
        raise ValueError("probabilities must be a non-empty N x K matrix with K >= 2")
    if not np.isfinite(matrix).all():
        raise ValueError("probabilities must be finite")
    if (matrix < 0).any():
        raise ValueError("probabilities must be nonnegative")
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=1e-10, rtol=0):
        raise ValueError("each probability row must sum to one")
    return matrix


def validate_date_index(dates: Any, expected_length: int | None = None) -> pd.DatetimeIndex:
    index = pd.DatetimeIndex(dates)
    if index.hasnans or index.tz is not None:
        raise ValueError("dates must be present and timezone-naive")
    if (index != index.normalize()).any():
        raise ValueError("dates must be session dates without time components")
    if not index.is_monotonic_increasing or not index.is_unique:
        raise ValueError("dates must be strictly increasing and unique")
    if expected_length is not None and len(index) != expected_length:
        raise ValueError("dates and observations must have equal lengths")
    return index


def finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not np.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number
