from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.contracts.temporal import eligible_training_labels, forward_return_labels


def panel_for_maturity():
    count = 54
    dates = pd.date_range("2020-01-01", periods=count, freq="B")
    positions = np.arange(count, dtype=float)
    close = pd.Series(100 + positions + 0.2 * np.sin(positions), index=dates)
    horizon = 3
    target = close.shift(-horizon) / close - 1
    target.iloc[-horizon:] = [0.01, 0.012, 0.014]  # finite synthetic tail for the legacy routine
    panel = pd.DataFrame({
        "fwd_return_3": target,
        "trend_20": np.sin(positions / 4),
        "return_20": np.cos(positions / 5),
        "volatility_20": 0.15 + 0.02 * np.sin(positions / 7),
        "drawdown_252": -0.1 + 0.02 * np.cos(positions / 6),
        "p_low_vol": 0.4 + 0.1 * np.sin(positions / 3),
        "p_high_vol": 0.4 - 0.1 * np.sin(positions / 3),
        "entropy": 0.5 + 0.05 * np.cos(positions / 4),
        "expected_state_return": 0.001 * np.sin(positions / 2),
    }, index=dates)
    return close, panel


def test_exact_1c_expanding_oos_uses_immature_boundary_target(historical_1c):
    predictive = historical_1c.module("predictive")
    close, panel = panel_for_maturity()
    min_train = 4
    first_test_date = panel.index[min_train]
    baseline = predictive.expanding_oos(panel, "fwd_return_3", min_train=min_train,
                                        refit_every=2, return_forecasts=True)["forecasts"]
    mutated = panel.copy()
    # Decision at row 3 is inside train=slice(0, 4), but its outcome ends at row
    # 6, after the first test begins at row 4.  This is the raw-label mutation
    # that the historical test (which mutated only later materialized labels) missed.
    mutated.iloc[3, mutated.columns.get_loc("fwd_return_3")] += 25
    changed = predictive.expanding_oos(mutated, "fwd_return_3", min_train=min_train,
                                       refit_every=2, return_forecasts=True)["forecasts"]
    before = baseline.loc[first_test_date, "observable_only"]
    after = changed.loc[first_test_date, "observable_only"]
    assert np.isfinite(before) and np.isfinite(after)
    assert before != pytest.approx(after)

    labels = forward_return_labels(close, 3)
    crossing = next(label for label in labels if label.decision_date == close.index[3])
    assert crossing.outcome_end_date == close.index[6]
    assert crossing not in eligible_training_labels(labels, first_test_date)
    assert all(label.outcome_end_date < first_test_date
               for label in eligible_training_labels(labels, first_test_date))


def test_maturity_guard_keeps_only_labels_unchanged_by_raw_future_mutation():
    close, panel = panel_for_maturity()
    cutoff = close.index[10]
    original = forward_return_labels(close, 3)
    changed_close = close.copy()
    changed_close.loc[changed_close.index >= cutoff] *= 6
    changed = forward_return_labels(changed_close, 3)
    assert eligible_training_labels(original, cutoff) == eligible_training_labels(changed, cutoff)
    assert any(label.outcome_end_date >= cutoff and label.decision_date < cutoff for label in original)
