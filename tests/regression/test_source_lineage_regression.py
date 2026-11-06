from __future__ import annotations

import hashlib
from io import BytesIO

import pandas as pd

from research.contracts.data import (CANONICAL_DATA_SHA256, parsed_records_sha256,
                                     read_canonical_csv, validate_ohlc_frame)


def test_1c_csv_is_lf_raw_distinct_but_parsed_equivalent(historical_1c, tmp_path):
    canonical_path = tmp_path / "canonical.csv"
    # Copy bytes only to a temporary fixture so the real canonical file is never written.
    import pathlib
    source_path = pathlib.Path(__file__).resolve().parents[2] / "research/data/nifty_index.csv"
    canonical_path.write_bytes(source_path.read_bytes())
    canonical = read_canonical_csv(canonical_path)
    raw_1c = historical_1c.source("nifty_index.csv")
    assert hashlib.sha256(raw_1c).hexdigest() == "cf384a63c9137ec9b7f73d398c7ec5fc55ccdcccf89a514b824ad5341f409e59"
    assert canonical_path.read_bytes().replace(b"\r\n", b"\n") == raw_1c
    assert hashlib.sha256(raw_1c).hexdigest() != CANONICAL_DATA_SHA256
    other = validate_ohlc_frame(pd.read_csv(BytesIO(raw_1c), dtype=str), canonical_order=True)
    assert parsed_records_sha256(other) == canonical.provenance.parsed_sha256
    pd.testing.assert_frame_equal(other, canonical.frame)
