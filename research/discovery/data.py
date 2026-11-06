"""Canonical Task 2 data/feature loading and measured provenance."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
from research.contracts._validation import canonical_json_bytes
from research.contracts.data import read_canonical_csv
from research.contracts.features import FEATURE_CONTRACT_VERSION, build_contract_features, complete_feature_rows
from .protocol import DATA_SHA256, FEATURE_NAMES


def load_feature_data(path="research/data/nifty_index.csv"):
    source = Path(path)
    dataset = read_canonical_csv(source, DATA_SHA256)
    prices = dataset.frame.reset_index()
    features, feature_manifest = build_contract_features(prices, "rv")
    feature_manifest = dict(feature_manifest)
    complete = complete_feature_rows(features)
    if tuple(complete.columns) != FEATURE_NAMES:
        raise ValueError("Task 4 feature order differs from the frozen protocol")
    feature_hash = hashlib.sha256(
        np.ascontiguousarray(complete.to_numpy(dtype=float)).tobytes()
        + "|".join(date.strftime("%Y-%m-%d") for date in complete.index).encode("ascii")).hexdigest()
    manifest = {
        "schema": "task4-data-feature-provenance-v1", "dataset": dataset.provenance.as_dict(),
        "canonical_path": str(source), "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "feature_manifest": feature_manifest, "feature_manifest_sha256": hashlib.sha256(
            canonical_json_bytes(feature_manifest)).hexdigest(),
        "ordered_feature_names": list(FEATURE_NAMES), "complete_rows": len(complete),
        "complete_start": complete.index[0].strftime("%Y-%m-%d"),
        "complete_end": complete.index[-1].strftime("%Y-%m-%d"),
        "complete_feature_sha256": feature_hash, "internal_gap_imputation": False,
        "limitations": ["hash identity is not vendor verification", "not total-return data",
                        "calendar completeness/corporate actions/licensing unverified"]}
    return complete, manifest
