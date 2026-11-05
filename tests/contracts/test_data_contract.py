from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from research.contracts.data import (CANONICAL_COLUMNS, CANONICAL_DATA_SHA256,
                                     parsed_records_sha256, read_canonical_csv,
                                     validate_ohlc_frame)

ROOT = Path(__file__).resolve().parents[2]


def sample_frame(rows: int = 6) -> pd.DataFrame:
    close = [100 + index for index in range(rows)]
    return pd.DataFrame({
        "Date": pd.date_range("2024-01-01", periods=rows, freq="B").strftime("%Y-%m-%d"),
        "Close": close,
        "High": [value + 2 for value in close],
        "Low": [value - 2 for value in close],
        "Open": [value + 0.5 for value in close],
    })


def test_canonical_nifty_raw_identity_schema_and_dates():
    dataset = read_canonical_csv(ROOT / "research/data/nifty_index.csv")
    assert dataset.provenance.raw_sha256 == CANONICAL_DATA_SHA256
    assert len(dataset.provenance.parsed_sha256) == 64
    assert dataset.provenance.rows == 4684
    assert dataset.provenance.start_date == "2007-09-17"
    assert dataset.provenance.end_date == "2026-10-22"
    assert dataset.provenance.columns == CANONICAL_COLUMNS
    assert dataset.provenance.newline_style == "CRLF"


def test_line_ending_changes_raw_identity_but_not_parsed_identity(tmp_path):
    frame = sample_frame()
    crlf = frame.to_csv(index=False, lineterminator="\r\n").encode()
    lf = crlf.replace(b"\r\n", b"\n")
    assert hashlib.sha256(crlf).digest() != hashlib.sha256(lf).digest()
    crlf_path = tmp_path / "crlf.csv"
    lf_path = tmp_path / "lf.csv"
    crlf_path.write_bytes(crlf)
    lf_path.write_bytes(lf)
    left = read_canonical_csv(crlf_path, hashlib.sha256(crlf).hexdigest())
    right = read_canonical_csv(lf_path, hashlib.sha256(lf).hexdigest())
    assert left.provenance.raw_sha256 != right.provenance.raw_sha256
    assert left.provenance.parsed_sha256 == right.provenance.parsed_sha256
    pd.testing.assert_frame_equal(left.frame, right.frame)


def test_synthetic_ohlc_validator_returns_defensive_date_indexed_copy():
    source = sample_frame()
    clean = validate_ohlc_frame(source)
    source.iloc[0, source.columns.get_loc("Close")] = -100
    assert clean.index.name == "Date"
    assert clean.iloc[0]["Close"] == 100
    assert list(clean.columns) == ["Close", "High", "Low", "Open"]
    assert parsed_records_sha256(clean) == parsed_records_sha256(validate_ohlc_frame(sample_frame()))


@pytest.mark.parametrize("column", ["Close", "High", "Low", "Open"])
def test_synthetic_missing_or_nonnumeric_ohlc_is_rejected(column):
    frame = sample_frame().astype({name: object for name in ("Close", "High", "Low", "Open")})
    frame.loc[2, column] = "missing"
    with pytest.raises(ValueError, match="numeric"):
        validate_ohlc_frame(frame)


def test_synthetic_duplicate_or_unsorted_dates_are_rejected():
    duplicated = sample_frame()
    duplicated.loc[1, "Date"] = duplicated.loc[0, "Date"]
    with pytest.raises(ValueError, match="strictly increasing and unique"):
        validate_ohlc_frame(duplicated)
    unsorted = sample_frame().iloc[::-1]
    with pytest.raises(ValueError, match="strictly increasing and unique"):
        validate_ohlc_frame(unsorted)


def test_synthetic_invalid_ohlc_envelope_is_rejected():
    high = sample_frame()
    high.loc[1, "High"] = high.loc[1, "Close"] - 1
    with pytest.raises(ValueError, match="High"):
        validate_ohlc_frame(high)
    low = sample_frame()
    low.loc[1, "Low"] = low.loc[1, "Close"] + 1
    with pytest.raises(ValueError, match="Low"):
        validate_ohlc_frame(low)


def test_synthetic_nonpositive_or_infinite_prices_are_rejected():
    for value, match in ((0, "strictly positive"), (float("inf"), "finite")):
        frame = sample_frame().astype({"Close": float})
        frame.loc[0, "Close"] = value
        with pytest.raises(ValueError, match=match):
            validate_ohlc_frame(frame)


def test_canonical_order_and_raw_hash_mismatch_are_rejected(tmp_path):
    reordered = sample_frame()[["Date", "Open", "High", "Low", "Close"]]
    with pytest.raises(ValueError, match="column order"):
        validate_ohlc_frame(reordered, canonical_order=True)
    path = tmp_path / "data.csv"
    path.write_bytes(sample_frame().to_csv(index=False).encode())
    with pytest.raises(ValueError, match="raw SHA-256 mismatch"):
        read_canonical_csv(path, CANONICAL_DATA_SHA256)


def test_invalid_calendar_date_and_missing_column_are_rejected():
    invalid = sample_frame()
    invalid.loc[0, "Date"] = "2024-02-30"
    with pytest.raises(ValueError, match="calendar"):
        validate_ohlc_frame(invalid)
    with pytest.raises(ValueError, match="required columns"):
        validate_ohlc_frame(sample_frame().drop(columns=["Open"]))
