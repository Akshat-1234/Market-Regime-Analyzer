"""Tests for the research extensions: EM engine, discovery, inference, controls.

These tests target the properties that decide whether the research claims are
trustworthy: numerical agreement with an independent implementation, causal
filtering, train/test separation, state-alignment logic, control construction and
the absence of future information in forecasts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler

from regime_backtester.allocation import (markov_path_exposure, phase_shift,
                                          policy_exposures, vol_matched_exposure)
from regime_backtester.config import load_config
from regime_backtester.data import load_price_csv, synthetic_prices
from regime_backtester.discovery import (FEATURE_SETS, Spec, align_states,
                                         concatenate_signals, fit_spec_fold,
                                         fold_schedule, run_spec)
from regime_backtester.emhmm import HMMFit, fit_hmm
from regime_backtester.features import build_features
from regime_backtester.predictive import (_ridge_fit, expanding_oos, forward_targets,
                                          newey_west_ols)
from regime_backtester.significance import (diebold_mariano, reality_check,
                                            stationary_bootstrap_indices)


@pytest.fixture(scope="module")
def synthetic():
    prices = synthetic_prices(n=900, seed=7)
    features = build_features(prices)
    return prices, features


@pytest.fixture(scope="module")
def nifty():
    prices, _ = load_price_csv("data/raw/nifty_index.csv")
    return prices, build_features(prices)


def test_gaussian_em_matches_hmmlearn_likelihood(synthetic, nifty):
    """The same parameters must give the same likelihood in both engines."""
    prices, features = nifty
    x = features[list(FEATURE_SETS["rvd3"])].dropna().iloc[:600].to_numpy()
    x = StandardScaler().fit_transform(x)
    model = GaussianHMM(n_components=3, covariance_type="diag", n_iter=80,
                        random_state=3, implementation="log").fit(x)
    reference = HMMFit(model.startprob_, model.transmat_, model.means_, model.covars_,
                       "diag")
    likelihood, _ = reference.predictive_loglik(x)
    assert likelihood == pytest.approx(model.score(x), rel=1e-10, abs=1e-8)


def test_filtered_posterior_is_causal(nifty):
    """The filtered posterior at t must equal the posterior of the truncated prefix."""
    prices, features = nifty
    x = StandardScaler().fit_transform(
        features[list(FEATURE_SETS["rvd3"])].dropna().iloc[:500].to_numpy())
    model = GaussianHMM(n_components=2, covariance_type="diag", n_iter=50,
                        random_state=1, implementation="log").fit(x)
    fitted = HMMFit(model.startprob_, model.transmat_, model.means_, model.covars_, "diag")
    probs, _, _ = fitted.filter(x)
    for t in (10, 137, 300):
        reference = model.predict_proba(x[:t + 1])[-1]
        assert np.allclose(probs[t], reference, atol=1e-10)


def test_em_monotone_and_student_t_beats_gaussian_on_tails():
    rng = np.random.default_rng(11)
    x = rng.standard_t(4, size=(700, 2)) * np.array([1.0, 2.0]) + np.array([0.1, -0.2])
    fitted = fit_hmm(x, 2, emission="student_t", dof=6.0, seed=1, n_iter=60, tol=0.0)
    changes = np.diff(fitted.history)
    assert changes.min() > -1e-6, "EM likelihood must not decrease"
    gaussian = fit_hmm(x, 2, seed=1, n_iter=60)
    assert fitted.loglik > gaussian.loglik
    new = rng.standard_t(4, size=(300, 2)) * np.array([1.0, 2.0]) + np.array([0.1, -0.2])
    assert fitted.predictive_loglik(new)[0] > gaussian.predictive_loglik(new)[0]


def test_sticky_prior_increases_persistence():
    rng = np.random.default_rng(3)
    x = rng.normal(size=(400, 2))
    plain = fit_hmm(x, 3, seed=2, n_iter=80)
    sticky = fit_hmm(x, 3, seed=2, n_iter=80, sticky=40.0)
    assert np.trace(sticky.transmat) > np.trace(plain.transmat)


def test_fold_schedule_matches_baseline_refit_dates(nifty):
    prices, features = nifty
    dates = features[list(FEATURE_SETS["rvd3"])].dropna().index
    folds = fold_schedule(dates, 504, "2012-01-01")
    baseline = pd.read_csv("runs/run_20261030_080824_12346d/fits.csv",
                           parse_dates=["refit_date"])
    expected = sorted(baseline.refit_date.unique())
    observed = [pd.Timestamp(dates[test_start]) for _, _, test_start, _ in folds]
    assert len(folds) == len(expected) == 15
    assert [str(d.date()) for d in observed] == [str(pd.Timestamp(d).date()) for d in expected]


def test_fold_fit_has_no_future_information(synthetic):
    prices, features = synthetic
    config = load_config(None, {"walkforward": {"min_train_days": 300,
                                               "start_date": str(prices.index[400].date())}})
    spec = Spec("rv2_test", FEATURE_SETS["rv2"], 2)
    panel = features[list(spec.features)].dropna()
    train = panel.iloc[:300]
    test = panel.iloc[300:420]
    returns = prices["Close"].pct_change(fill_method=None).loc[train.index]
    first = fit_spec_fold(train.to_numpy(), returns.to_numpy(), test.to_numpy(), spec,
                          seeds=(2,), n_iter=60)
    mutated = test.copy()
    mutated.iloc[60:] *= 3.0
    second = fit_spec_fold(train.to_numpy(), returns.to_numpy(), mutated.to_numpy(), spec,
                           seeds=(2,), n_iter=60)
    assert np.allclose(first.probs_test[:60], second.probs_test[:60])
    assert not np.allclose(first.probs_test, second.probs_test)


def test_alignment_is_permutation_aware(synthetic):
    prices, features = synthetic
    spec = Spec("rv2_align", FEATURE_SETS["rv2"], 2)
    panel = features[list(spec.features)].dropna()
    returns = prices["Close"].pct_change(fill_method=None).reindex(panel.index)
    a = fit_spec_fold(panel.iloc[:300].to_numpy(), returns.iloc[:300].to_numpy(),
                      panel.iloc[300:400].to_numpy(), spec, seeds=(2,), n_iter=60)
    b = fit_spec_fold(panel.iloc[350:650].to_numpy(), returns.iloc[350:650].to_numpy(),
                      panel.iloc[650:750].to_numpy(), spec, seeds=(2,), n_iter=60)
    result = align_states(a, b)
    assert result["n_states"] == 2
    assert 0 <= result["match_cost"] < np.inf
    pairs = [pair.split("->") for pair in result["mapping"].split(",")]
    assert sorted(int(pair[0]) for pair in pairs) == [0, 1]
    assert sorted(int(pair[1]) for pair in pairs) == [0, 1]


def test_run_spec_is_causal_and_complete(nifty):
    prices, features = nifty
    config = load_config(None, {"walkforward": {"min_train_days": 504,
                                               "start_date": "2012-01-01"}})
    spec = Spec("rv2_k2", FEATURE_SETS["rv2"], 2)
    fits = run_spec(prices, features, spec, config, seeds=(5,))
    assert len(fits) == 15
    for fit in fits:
        assert fit.train_index.max() < fit.test_index.min()
        assert fit.probs_test.shape == (len(fit.test_index), 2)
        assert np.allclose(fit.probs_test.sum(axis=1), 1.0)
        assert np.isfinite(fit.test_predictive_loglik_per_obs)
    signals = concatenate_signals(fits)
    assert signals["state_exposure"].between(0, 1).all()
    assert signals["entropy_normalized"].between(-1e-12, 1 + 1e-12).all()


def test_hac_ols_recovers_slope():
    rng = np.random.default_rng(5)
    n = 500
    x = rng.normal(size=n)
    y = 2.0 + 1.5 * x + rng.normal(scale=0.5, size=n)
    design = np.column_stack([np.ones(n), x])
    fit = newey_west_ols(y, design, lags=5)
    assert fit["beta"][1] == pytest.approx(1.5, abs=0.1)
    assert fit["p"][1] < 1e-6
    assert 0.6 < fit["r2"] < 0.95


def test_forward_targets_have_no_lookahead():
    prices = synthetic_prices(n=60, seed=3)
    targets = forward_targets(prices, horizon=5)
    close = prices["Close"]
    t = 20
    expected = close.iloc[t + 5] / close.iloc[t] - 1
    assert targets["fwd_return"].iloc[t] == pytest.approx(expected)
    assert np.isnan(targets["fwd_return"].iloc[-1])


def test_expanding_forecast_ignores_future_mutation(nifty):
    prices, features = nifty
    config = load_config(None, {"walkforward": {"min_train_days": 504,
                                               "start_date": "2012-01-01"}})
    fits = run_spec(prices, features, Spec("rv2_k2", FEATURE_SETS["rv2"], 2),
                    config, seeds=(5,))
    signals = concatenate_signals(fits)
    from regime_backtester.predictive import build_panel

    panel = build_panel(prices, signals, features)
    base = expanding_oos(panel, "fwd_vol_20", min_train=400, refit_every=21,
                         return_forecasts=True)["forecasts"]
    mutated = panel.copy()
    # Change observations *after* the first forecasts: earlier forecasts must not move.
    cut = mutated.index[700]
    mutated.loc[mutated.index >= cut, "fwd_vol_20"] *= 5.0
    changed = expanding_oos(mutated, "fwd_vol_20", min_train=400, refit_every=21,
                            return_forecasts=True)["forecasts"]
    before = base.loc[:cut].iloc[:-1]
    np.testing.assert_allclose(before["observable_only"].to_numpy(),
                               changed.loc[before.index, "observable_only"].to_numpy())
    np.testing.assert_allclose(before["observable_plus_regime"].to_numpy(),
                               changed.loc[before.index, "observable_plus_regime"].to_numpy())
    assert not np.allclose(base["observable_only"].dropna(), changed["observable_only"].dropna())


def test_controls_preserve_prespecified_properties():
    rng = np.random.default_rng(1)
    exposure = pd.Series(np.linspace(0.2, 0.9, 400))
    shifted = phase_shift(exposure.to_numpy(), 137)
    assert np.allclose(np.sort(shifted), np.sort(exposure.to_numpy()))
    transition = np.array([[0.95, 0.05], [0.10, 0.90]])
    path = markov_path_exposure(transition, np.array([0.9, 0.4]), 500, rng)
    assert set(np.unique(path)) <= {0.9, 0.4}
    assert path.mean() == pytest.approx(0.9 * (0.10 / 0.15) + 0.4 * (0.05 / 0.15), abs=0.06)


def test_vol_matched_control_is_causal(nifty):
    prices, features = nifty
    config = load_config(None, {"walkforward": {"min_train_days": 504,
                                               "start_date": "2012-01-01"}})
    fits = run_spec(prices, features, Spec("rv2_k2", FEATURE_SETS["rv2"], 2),
                    config, seeds=(5,))
    signals = concatenate_signals(fits)
    first = vol_matched_exposure(signals, features, min_history=250, refit_every=21)
    mutated = features.copy()
    cut = signals.index[1200]
    mutated.loc[mutated.index > cut, "volatility_20"] *= 4.0
    mutated_signals = signals.copy()
    mutated_signals.loc[mutated_signals.index > cut, "state_exposure"] = 0.1
    second = vol_matched_exposure(mutated_signals, mutated, min_history=250, refit_every=21)
    assert np.allclose(first.loc[:cut].to_numpy(), second.loc[:cut].to_numpy())


def test_policy_exposures_are_bounded(nifty):
    prices, features = nifty
    config = load_config(None, {"walkforward": {"min_train_days": 504,
                                               "start_date": "2012-01-01"},
                                "backtest": {"execution_delay_sessions": 1}})
    fits = run_spec(prices, features, Spec("rv2_k2", FEATURE_SETS["rv2"], 2),
                    config, seeds=(5,))
    signals = concatenate_signals(fits)
    policies = policy_exposures(signals, features, prices, config)
    assert policies.notna().all(axis=None)
    assert ((policies >= -1e-12) & (policies <= 1 + 1e-12)).all(axis=None)
    assert "trend_vol" in policies


def test_stationary_bootstrap_and_reality_check():
    indices = stationary_bootstrap_indices(200, samples=50, mean_block=10, seed=3)
    assert indices.shape == (50, 200)
    assert indices.min() >= 0 and indices.max() < 200
    rng = np.random.default_rng(2)
    returns = pd.DataFrame(rng.normal(0.0002, 0.01, size=(500, 4)),
                           columns=["bench", "a", "b", "c"])
    result = reality_check(returns, "bench", periods=252, daily_rf=0.0, samples=200,
                           mean_block=10, seed=5)
    assert 0.0 <= result["p_value"] <= 1.0
    assert len(result["ranking"]) == 3
    dm = diebold_mariano(pd.Series(rng.normal(size=100)), pd.Series(rng.normal(size=100)))
    assert np.isfinite(dm["statistic"])


def test_window_standardise_neutralises_spike_regressors():
    """A regressor that is 0 except for a vanishing handful of values carries no
    identifiable slope and must be neutralised rather than extrapolated."""
    from regime_backtester.predictive import _window_standardise

    rng = np.random.default_rng(11)
    spike = np.zeros((500, 1))
    spike[:3, 0] = 0.01                       # 0.6 % of the window, max 1 % of range
    train_z, test_z, dead, clipped = _window_standardise(spike, np.ones((10, 1)))
    assert dead == 1 and clipped == 0
    assert np.allclose(train_z, 0.0) and np.allclose(test_z, 0.0)


def test_window_standardise_clips_extrapolation_to_training_support():
    """Test values outside the estimation window's range are clipped, so an
    unseen regime cannot be extrapolated to an arbitrarily large forecast."""
    from regime_backtester.predictive import _window_standardise

    train = np.linspace(0.0, 1.0, 200)[:, None]
    test = np.array([[50.0], [0.5]])
    _, test_z, dead, clipped = _window_standardise(train, test)
    assert dead == 0 and clipped == 1
    upper = ((train - train.mean()) / train.std()).max()
    assert test_z[0, 0] == pytest.approx(upper)
    assert np.isfinite(test_z).all()


def test_expanding_forecasts_stay_within_a_sane_range(nifty):
    """Regression guard: a state that is unoccupied in the estimation window must
    not produce a forecast hundreds of standard deviations away from the target."""
    prices, features = nifty
    config = load_config(None, {"walkforward": {"min_train_days": 504,
                                                "start_date": "2012-01-01"}})
    fits = run_spec(prices, features, Spec("rv2_k2", FEATURE_SETS["rv2"], 2),
                    config, seeds=(5,))
    from regime_backtester.predictive import build_panel

    panel = build_panel(prices, concatenate_signals(fits), features)
    result = expanding_oos(panel, "fwd_return_1", min_train=400, refit_every=21)
    assert result["max_abs_forecast_in_training_sd"] < 20.0
    assert np.isfinite(result["oos_r2_vs_observable"])


def test_vol_matched_bootstrap_controls_are_causal_and_varied(nifty):
    """The vol-matched control must produce a family of causal paths, not one."""
    prices, features = nifty
    config = load_config(None, {"walkforward": {"min_train_days": 504,
                                                "start_date": "2012-01-01"}})
    fits = run_spec(prices, features, Spec("rv2_k2", FEATURE_SETS["rv2"], 2),
                    config, seeds=(5,))
    signals = concatenate_signals(fits)
    rng = np.random.default_rng(3)
    paths = [vol_matched_exposure(signals, features, min_history=250, refit_every=63,
                                  rng=rng) for _ in range(4)]
    for path in paths:
        assert path.between(0, 1).all()
        assert np.isfinite(path.to_numpy()).all()
    cut = signals.index[1300]
    mutated_features = features.copy()
    mutated_features.loc[mutated_features.index > cut, "volatility_20"] *= 4.0
    rng_a = np.random.default_rng(9)
    rng_b = np.random.default_rng(9)
    first = vol_matched_exposure(signals, features, min_history=250, refit_every=63, rng=rng_a)
    second = vol_matched_exposure(signals, mutated_features, min_history=250, refit_every=63,
                                  rng=rng_b)
    assert np.allclose(first.loc[:cut].to_numpy(), second.loc[:cut].to_numpy())
    assert not np.allclose(np.asarray(paths[0]), np.asarray(paths[1]))


def test_paired_sharpe_interval_uses_a_daily_risk_free_rate():
    """Regression guard: the annual cash rate must be converted before it is used
    as a daily excess-return adjustment.  With an annual rate treated as daily,
    both Sharpes shift by ~6.5 %/day and the *sign* of their difference flips for
    strategies of different volatility."""
    from regime_backtester.metrics import annual_sharpe, daily_rf
    from regime_backtester.significance import paired_sharpe_interval

    rng = np.random.default_rng(21)
    n = 1500
    def standardised(seed):
        z = np.random.default_rng(seed).normal(size=n)
        return (z - z.mean()) / z.std()

    calm = pd.Series(0.00050 + 0.005 * standardised(1))    # Sharpe ~0.79
    wild = pd.Series(0.00045 + 0.012 * standardised(2))    # Sharpe ~0.27
    annual, periods = 0.065, 252
    expected = (annual_sharpe(calm.to_numpy(), annual, periods)
                - annual_sharpe(wild.to_numpy(), annual, periods))
    stats = paired_sharpe_interval(calm, wild, periods=periods,
                                  daily_rf=daily_rf(annual, periods),
                                  samples=200, mean_block=20, seed=1)
    assert stats["observed_difference"] == pytest.approx(expected, abs=1e-9)
    assert stats["observed_difference"] > 0        # the calmer series has the higher Sharpe
    buggy = paired_sharpe_interval(calm, wild, periods=periods, daily_rf=annual,
                                   samples=200, mean_block=20, seed=1)
    assert buggy["observed_difference"] < 0        # documents the old defect
