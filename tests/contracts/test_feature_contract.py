from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.contracts.features import (build_contract_features, complete_feature_rows,
                                         feature_manifest)

ROOT = Path(__file__).resolve().parents[2]


def prices(count: int = 300) -> pd.DataFrame:
    close = 100 * np.exp(np.linspace(0, 0.4, count) + 0.02 * np.sin(np.arange(count)))
    return pd.DataFrame({
        "Date": pd.date_range("2020-01-01", periods=count, freq="B").strftime("%Y-%m-%d"),
        "Close": close,
        "Open": close * 0.999,
        "High": close * 1.01,
        "Low": close * 0.99,
    })


def test_daily_return_and_sample_volatility_match_hand_calculation():
    frame = prices(25)
    features, manifest = build_contract_features(frame, "rv")
    close = frame["Close"].to_numpy()
    returns = close[1:] / close[:-1] - 1
    assert np.isnan(features["daily_return"].iloc[0])
    np.testing.assert_allclose(features["daily_return"].iloc[1:], returns)
    expected_position20 = np.std(returns[:20], ddof=1) * math.sqrt(252)
    assert features["volatility_20"].iloc[:20].isna().all()
    assert features["volatility_20"].iloc[20] == pytest.approx(expected_position20)
    assert manifest["volatility_ddof"] == 1
    assert manifest["return_type"] == "simple_close_to_close"
    assert manifest["imputation"] is False


def test_contract_features_match_actual_f10_formulas_for_rv_and_rvd():
    path = ROOT / "research/legacy/src/regime_backtester/features.py"
    spec = importlib.util.spec_from_file_location("_f10_features_reference", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    frame = prices()
    reference = module.build_features(frame)
    reference.index = pd.DatetimeIndex(frame["Date"])
    reference.index.name = "Date"
    for family, columns in (("rv", ["daily_return", "volatility_20"]),
                            ("rvd", ["daily_return", "volatility_20", "drawdown_252"])):
        actual, _ = build_contract_features(frame, family)
        pd.testing.assert_frame_equal(actual[columns], reference[columns], check_exact=True)


def test_rvd_drawdown_warmup_and_hand_calculation():
    frame = prices(255)
    features, manifest = build_contract_features(frame, "rvd")
    close = frame["Close"].to_numpy()
    assert features["drawdown_252"].iloc[:251].isna().all()
    expected = close[251] / np.max(close[:252]) - 1
    assert features["drawdown_252"].iloc[251] == pytest.approx(expected)
    specs = {entry["name"]: entry for entry in manifest["specs"]}
    assert specs["daily_return"]["first_valid_position"] == 1
    assert specs["volatility_20"]["lookback_sessions"] == 20
    assert specs["drawdown_252"]["first_valid_position"] == 251


def test_feature_prefix_is_invariant_to_future_close_mutation():
    original = prices(80)
    mutated = original.copy()
    cut = 50
    mutated.loc[mutated.index > cut, "Close"] *= 8
    # Preserve a valid OHLC envelope; only Close is relevant to the contract.
    for column in ("Open", "High", "Low"):
        mutated.loc[mutated.index > cut, column] *= 8
    left, _ = build_contract_features(original, "rvd")
    right, _ = build_contract_features(mutated, "rvd")
    pd.testing.assert_frame_equal(left.iloc[:cut + 1], right.iloc[:cut + 1])
    assert not left.iloc[cut + 1:].equals(right.iloc[cut + 1:])


def test_feature_gaps_are_not_imputed_and_internal_gap_is_rejected():
    frame = prices(40)
    features, _ = build_contract_features(frame, "rv")
    features.iloc[25, features.columns.get_loc("daily_return")] = np.nan
    features.iloc[25, features.columns.get_loc("volatility_20")] = np.nan
    with pytest.raises(ValueError, match="internal gap"):
        complete_feature_rows(features)
    assert features.iloc[25].isna().all()


def test_complete_feature_rows_trims_only_leading_warmup():
    features, _ = build_contract_features(prices(30), "rv")
    trimmed = complete_feature_rows(features)
    assert len(trimmed) == len(features) - 20
    assert trimmed.index[0] == features.index[20]
    pd.testing.assert_frame_equal(trimmed, features.iloc[20:])


def test_feature_manifest_is_versioned_and_rejects_new_family():
    manifest = feature_manifest("rv")
    assert manifest["schema"] == "f10-close-features-v1"
    assert manifest["columns"] == ["daily_return", "volatility_20"]
    assert manifest["warmup_policy"].startswith("retain missing")
    assert manifest["internal_gap_policy"] == "reject"
    with pytest.raises(ValueError, match="family"):
        feature_manifest("rvd_mom")
