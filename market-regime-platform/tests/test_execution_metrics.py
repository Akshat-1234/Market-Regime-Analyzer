import numpy as np
import pandas as pd
import pytest

from regime_backtester.config import load_config
from regime_backtester.execution import simulate
from regime_backtester.metrics import annual_sharpe, paired_block_bootstrap, performance_table


DATES = pd.bdate_range("2024-01-01", periods=4)


def run(signal, returns, cost=0, rf=0, delay=0):
    return simulate(pd.Series(signal, index=DATES), pd.Series(returns, index=DATES),
                    initial_capital=1000, annual_risk_free_rate=rf,
                    trading_days_per_year=252, transaction_cost_bps=cost,
                    execution_delay_sessions=delay)


def test_signal_earns_next_return_and_not_same_day_return():
    result = run([0, 1, 0, 1], [np.nan, 0.1, -0.1, 0.1])
    np.testing.assert_allclose(result.target_exposure, [0, 1, 0])
    np.testing.assert_allclose(result.strategy_return, [0, -0.1, 0], atol=1e-12)
    assert result.decision_date.iloc[1] == DATES[1]
    assert result.index[1] == DATES[2]
    assert result.equity.iloc[-1] == pytest.approx(900)


def test_extra_execution_delay():
    result = run([0, 1, 0, 1], [np.nan, 0.1, -0.1, 0.1], delay=1)
    np.testing.assert_allclose(result.target_exposure, [0, 1])
    np.testing.assert_allclose(result.strategy_return, [0, 0.1], atol=1e-12)
    assert result.decision_date.iloc[1] == DATES[1]
    assert result.execution_date.iloc[1] == DATES[2]
    assert result.index[1] == DATES[3]


def test_exact_self_financing_entry_fee_and_no_terminal_sale():
    result = run([1, 1, 1, 0], [np.nan, 0, 0, 0], cost=10)
    expected = 1000 / 1.001
    assert result.equity.iloc[0] == pytest.approx(expected)
    assert result.equity.iloc[-1] == pytest.approx(expected)
    assert result.turnover.iloc[0] == pytest.approx(1 / 1.001)
    assert result.turnover.iloc[1] == pytest.approx(0)
    assert result.turnover.iloc[2] == pytest.approx(0)


def test_costs_apply_to_sell_and_fractional_weights_rebalance_after_drift():
    drift = run([0.5, 0.5, 0, 0], [np.nan, 0.1, 0, 0], cost=10)
    assert drift.pre_trade_exposure.iloc[1] > 0.5
    assert drift.turnover.iloc[1] > 0  # target unchanged; actual weight drifted
    assert drift.turnover.iloc[2] > 0
    assert (drift.cost_fraction > 0).all()


def test_cash_earns_rf_and_sharpe_is_undefined_for_constant_excess():
    result = run([0, 0, 0, 0], [np.nan, 0.2, -0.3, 0.1], rf=0.065)
    rf = 1.065 ** (1 / 252) - 1
    np.testing.assert_allclose(result.strategy_return, rf, atol=1e-12)
    assert np.isnan(annual_sharpe(result.strategy_return.to_numpy(), 0.065, 252))
    cfg = load_config()
    stats = performance_table({"Cash": result}, cfg).loc["Cash"]
    assert stats.cagr == pytest.approx(.065, rel=1e-10)


def test_bootstrap_uses_paired_dates_and_is_seeded():
    rng = np.random.default_rng(9)
    idx = pd.bdate_range("2020-01-01", periods=80)
    rets = rng.normal(0.0004, 0.01, len(idx))
    frame = pd.DataFrame({"strategy_return": rets}, index=idx)
    runs = {"same1": frame, "same2": frame.copy()}
    cfg = load_config(overrides={"bootstrap": {"samples": 40}})
    a = paired_block_bootstrap(runs, "same1", ["same2"], cfg)
    b = paired_block_bootstrap(runs, "same1", ["same2"], cfg)
    pd.testing.assert_frame_equal(a, b)
    np.testing.assert_allclose(a[["observed_sharpe_difference", "lower", "upper"]], 0)


def test_rejects_bad_weights_or_returns():
    with pytest.raises(ValueError, match="targets"):
        run([0, 1.1, 0, 0], [np.nan, 0, 0, 0])
    with pytest.raises(ValueError, match="Next-day"):
        run([0, 1, 0, 0], [np.nan, 0, -1.0, 0])
