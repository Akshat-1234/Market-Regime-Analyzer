from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from research.discovery.protocol import Fold


@pytest.fixture
def synthetic_features():
    rng = np.random.default_rng(2026)
    rows = 1100
    returns = np.concatenate([rng.normal(-0.002, 0.004, rows // 2), rng.normal(0.003, 0.006, rows - rows // 2)])
    volatility = np.concatenate([rng.normal(0.12, 0.015, rows // 2), rng.normal(0.28, 0.025, rows - rows // 2)])
    dates = pd.date_range("2007-10-16", periods=rows, freq="B")
    return pd.DataFrame({"daily_return": returns, "volatility_20": volatility}, index=dates)


@pytest.fixture
def synthetic_outer(synthetic_features):
    index = synthetic_features.index
    return Fold("outer_synthetic", index[0].strftime("%Y-%m-%d"), index[881].strftime("%Y-%m-%d"),
                index[882].strftime("%Y-%m-%d"), index[1007].strftime("%Y-%m-%d"), 882, 126)


@pytest.fixture
def fast_numerics(monkeypatch):
    from research.discovery.protocol import NUMERICAL_SETTINGS
    monkeypatch.setitem(NUMERICAL_SETTINGS, "n_iter", 5)
    monkeypatch.setitem(NUMERICAL_SETTINGS, "tol", 1e6)
