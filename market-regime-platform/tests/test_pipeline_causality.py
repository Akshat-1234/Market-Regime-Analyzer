"""Full-pipeline truncation + mutation tests: no future-dependent signals."""
import numpy as np
import pandas as pd

from regime_backtester.config import load_config
from regime_backtester.data import synthetic_prices
from regime_backtester.pipeline import run_pipeline
from regime_backtester.reporting import write_results


def compact_config():
    spec = {"name": "test_pca", "n_states": 2,
            "features": ["daily_return", "volatility_20", "drawdown_252"], "pca_components": 2}
    return load_config(overrides={"walkforward": {"min_train_days": 220},
                                  "hmm": {"models": [spec], "primary_model": "test_pca",
                                          "seeds": [42], "n_iter": 250, "tol": 0.1,
                                          "min_state_fraction": 0.0},
                                  "bootstrap": {"samples": 25, "block_length": 10}})


def test_full_pipeline_unchanged_by_truncation_and_future_mutation(tmp_path):
    prices = synthetic_prices(900)
    cfg = compact_config()
    cutoff = prices.index[760]
    full = run_pipeline(prices, cfg)
    truncated = run_pipeline(prices.loc[:cutoff], cfg)
    altered_prices = prices.copy()
    future = altered_prices.index > cutoff
    altered_prices.loc[future, ["Open", "High", "Low", "Close"]] *= 1.03
    altered = run_pipeline(altered_prices, cfg)
    for other in (truncated, altered):
        pd.testing.assert_frame_equal(full.walkforward.signals.loc[:cutoff],
                                      other.walkforward.signals.loc[:cutoff], check_exact=False, rtol=1e-9, atol=1e-10)
        for name in full.runs:
            pd.testing.assert_frame_equal(full.runs[name].loc[:cutoff], other.runs[name].loc[:cutoff],
                                          check_exact=False, rtol=1e-9, atol=1e-10)
    fits = full.walkforward.fits
    assert (pd.to_datetime(fits.train_end) < pd.to_datetime(fits.signal_start)).all()
    pcols = [c for c in full.walkforward.signals if c.startswith("p_state_")]
    np.testing.assert_allclose(full.walkforward.signals[pcols].sum(axis=1), 1, atol=1e-10)
    assert full.performance.observations.nunique() == 1
    out = write_results(truncated, tmp_path / "report")
    assert (out / "report.md").exists() and (out / "figures/equity_drawdown.png").exists()
    assert (out / "signals.csv").exists() and (out / "metadata.json").exists()


def test_execution_delay_keeps_common_oos_calendar():
    prices = synthetic_prices(620)
    cfg = compact_config()
    cfg["backtest"]["execution_delay_sessions"] = 1
    result = run_pipeline(prices, cfg)
    ref = result.runs["Buy & Hold"]
    assert ref.index.equals(result.runs["HMM + Trend"].index)
    assert ref.execution_date.iloc[0] > ref.decision_date.iloc[0]
    assert ref.index[0] > ref.execution_date.iloc[0]


def test_start_end_and_rolling_training_boundaries():
    prices = synthetic_prices(950)
    cfg = compact_config()
    cfg["walkforward"].update({"min_train_days": 180, "max_train_days": 220,
                               "start_date": "2010-01-04", "end_date": "2011-01-31"})
    result = run_pipeline(prices, cfg)
    fit = result.walkforward.fits
    assert (fit.train_observations == 220).all()
    assert result.walkforward.signals.index[0] >= pd.Timestamp("2010-01-04")
    assert result.walkforward.signals.index[-1] <= pd.Timestamp("2011-01-31")
    assert (pd.to_datetime(fit.train_end) < pd.to_datetime(fit.signal_start)).all()
