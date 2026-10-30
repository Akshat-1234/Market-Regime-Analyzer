import numpy as np
import pytest

from regime_backtester.config import load_config
from regime_backtester.data import synthetic_prices
from regime_backtester.features import build_features
from regime_backtester.hmm import fit_regime, forward_filter


class FakeHMM:
    n_components = 2
    startprob_ = np.array([0.75, 0.25])
    transmat_ = np.array([[0.9, 0.1], [0.2, 0.8]])

    def _compute_log_likelihood(self, x):
        return -0.5 * np.column_stack([(x[:, 0] - 0) ** 2, (x[:, 0] - 2) ** 2])


def test_forward_filter_manual_recursion_and_chunk_boundary():
    model = FakeHMM()
    x = np.array([[0.0], [2.0], [1.5], [0.5]])
    p, final = forward_filter(model, x)
    expected0 = model.startprob_ * np.exp(model._compute_log_likelihood(x)[0])
    expected0 /= expected0.sum()
    expected1 = (expected0 @ model.transmat_) * np.exp(model._compute_log_likelihood(x)[1])
    expected1 /= expected1.sum()
    np.testing.assert_allclose(p[0], expected0)
    np.testing.assert_allclose(p[1], expected1)
    np.testing.assert_allclose(p.sum(axis=1), 1)
    first, alpha = forward_filter(model, x[:2])
    second, split_final = forward_filter(model, x[2:], alpha)
    np.testing.assert_allclose(np.vstack([first, second]), p)
    np.testing.assert_allclose(split_final, final)
    changed = x.copy()
    changed[2:] = 200
    np.testing.assert_allclose(forward_filter(model, changed)[0][:2], p[:2])


def test_fit_scaler_pca_and_filter_are_train_only():
    prices = synthetic_prices(760)
    f = build_features(prices).dropna(subset=["daily_return", "volatility_20", "drawdown_252"])
    spec = {"name": "test", "n_states": 2, "features": ["daily_return", "volatility_20", "drawdown_252"],
            "pca_components": 2}
    cfg = load_config(overrides={"hmm": {"seeds": [42], "n_iter": 250, "tol": 0.1,
                                          "min_state_fraction": 0.0,
                                          "models": [spec], "primary_model": "test"}})
    train = f.iloc[:350]
    test = f.iloc[350:430]
    model = fit_regime(train[spec["features"]].to_numpy(), train.daily_return.to_numpy(), spec, cfg)
    np.testing.assert_allclose(model.scaler.mean_, train[spec["features"]].mean().to_numpy())
    assert model.pca is not None and model.pca.n_components_ == 2
    assert np.all(np.diff(model.state_vols) >= 0)
    assert np.all(np.diff(model.exposures) <= 1e-12)
    all_p = model.filter_new(test[spec["features"]].to_numpy())
    prefix = model.filter_new(test[spec["features"]].iloc[:20].to_numpy())
    np.testing.assert_allclose(all_p[:20], prefix, rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(all_p.sum(axis=1), 1)


def test_no_accepted_fit_fails_closed():
    prices = synthetic_prices(250)
    f = build_features(prices).dropna(subset=["daily_return", "volatility_20"])
    spec = {"name": "test", "n_states": 2, "features": ["daily_return", "volatility_20"]}
    cfg = load_config(overrides={"hmm": {"seeds": [42], "n_iter": 2, "tol": 1e-15,
                                          "models": [spec], "primary_model": "test"}})
    with pytest.raises(RuntimeError, match="All fits rejected"):
        fit_regime(f[spec["features"]].to_numpy(), f.daily_return.to_numpy(), spec, cfg)
