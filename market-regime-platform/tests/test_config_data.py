from pathlib import Path
import sys
import types

import numpy as np
import pandas as pd
import pytest

from regime_backtester.config import DEFAULTS, load_config
from regime_backtester.data import download_yahoo, load_price_csv, synthetic_prices, validate_prices
from regime_backtester.features import build_features, common_model_features


def test_default_yaml_and_code_are_in_sync():
    assert load_config(Path(__file__).resolve().parents[1] / "config/default.yaml") == DEFAULTS


def test_partial_config_and_validation(tmp_path):
    config_file = tmp_path / "conf.yaml"
    config_file.write_text("backtest:\n  transaction_cost_bps: 17\n")
    assert load_config(config_file)["backtest"]["transaction_cost_bps"] == 17
    config_file.write_text("backtest:\n  surprise: 1\n")
    with pytest.raises(ValueError, match="Unknown configuration key"):
        load_config(config_file)
    with pytest.raises(ValueError, match="max_train_days"):
        load_config(overrides={"walkforward": {"min_train_days": 500, "max_train_days": 300}})
    with pytest.raises(ValueError, match="duplicate|unique"):
        load_config(overrides={"hmm": {"seeds": [42, 42]}})
    with pytest.raises(ValueError, match="before end_date"):
        load_config(overrides={"walkforward": {"start_date": "2023-01-02", "end_date": "2022-12-31"}})


def test_price_validation_and_local_date_handling():
    frame = pd.DataFrame({" Date ": ["2024-01-02 00:00:00+05:30", "2024-01-01 00:00:00+05:30"],
                          " CLOSE ": [101, 100]})
    p = validate_prices(frame)
    assert p.index.tolist() == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]
    assert p.Close.tolist() == [100, 101]
    with pytest.raises(ValueError, match="Duplicate"):
        validate_prices(pd.DataFrame({"Date": ["2024-01-01", "2024-01-01"], "Close": [1, 2]}))
    with pytest.raises(ValueError, match="strictly positive"):
        validate_prices(pd.DataFrame({"Date": ["2024-01-01", "2024-01-02"], "Close": [1, 0]}))
    with pytest.raises(ValueError, match="High is below Low"):
        validate_prices(pd.DataFrame({"Date": ["2024-01-01", "2024-01-02"], "Close": [1, 2],
                                      "High": [1, 1], "Low": [0.5, 1.5]}))


def test_synthetic_csv_carries_provenance(tmp_path):
    sample = synthetic_prices(30)
    sample["Data_Source"] = "SYNTHETIC"
    path = tmp_path / "sample.csv"
    sample.to_csv(path, index_label="Date")
    loaded, source = load_price_csv(path)
    assert len(loaded) == 30 and source["kind"] == "synthetic"
    assert len(source["sha256"]) == 64


def test_downloader_normalizes_yahoo_multiindex(monkeypatch, tmp_path):
    data = synthetic_prices(30)
    data.columns = pd.MultiIndex.from_product([data.columns, ["^NSEI"]])
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=lambda *a, **kw: data))
    path = download_yahoo("^NSEI", "2020-01-01", None, tmp_path / "raw.csv")
    loaded, source = load_price_csv(path)
    assert len(loaded) == 30 and "Close" in loaded and source["kind"] == "csv"


def test_features_are_causal_when_future_is_removed_or_changed():
    prices = synthetic_prices(600)
    cutoff = prices.index[440]
    full = build_features(prices)
    short = build_features(prices.loc[:cutoff])
    pd.testing.assert_frame_equal(full.loc[:cutoff], short)
    changed = prices.copy()
    changed.loc[changed.index > cutoff, ["Open", "High", "Low", "Close"]] *= 3
    pd.testing.assert_frame_equal(full.loc[:cutoff], build_features(changed).loc[:cutoff])


def test_common_features_reject_missing_ohlc_and_internal_gap():
    prices = synthetic_prices(320)[["Close"]]
    features = build_features(prices)
    with pytest.raises(ValueError, match="Missing or unusable"):
        common_model_features(features, [{"features": ["overnight_gap"]}])
    features.loc[features.index[260], "daily_return"] = np.nan
    with pytest.raises(ValueError, match="internal gap"):
        common_model_features(features, [{"features": ["daily_return", "volatility_20"]}])


def test_quality_table_handles_constant_intraday_series():
    from regime_backtester.data import annual_quality_table
    p = synthetic_prices(60)
    p["Open"] = p["Close"]
    table = annual_quality_table(p)
    assert np.isnan(table.close_intraday_return_correlation.iloc[0])
    assert table.overnight_gap_vol_daily.iloc[0] > 0
