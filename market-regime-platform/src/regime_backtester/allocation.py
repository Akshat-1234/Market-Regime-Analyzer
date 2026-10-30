"""Regime-conditioned allocation rules and strong matched controls.

The original platform maps a state to ``min(1, target_vol / state_vol)`` and
averages four models.  That is a volatility-targeting rule implemented through a
latent state, so its information channel is essentially realised volatility.  The
rules here separate three questions that the original design conflated:

* ``vol_state``/``vol_expected``/``vol_transition``: risk-only mappings that differ
  in whether they use the current state volatility, the probability-weighted
  expectation, or the one-step-ahead transition expectation.
* ``return_tilt``: uses the *training* expected return of each state, shrunk
  towards the cross-state mean, on top of the risk mapping.
* ``entropy``/``high_vol_gate``: uses posterior uncertainty or a training-quantile
  risk gate.

Every parameter is estimated inside the training window of the fold that produced
the probabilities.  No rule is tuned on the evaluation period.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .execution import simulate
from .features import build_features
from .strategies import fixed_signals


def _clip01(x: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(x, dtype=float), 0.0, 1.0)


def policy_exposures(signals: pd.DataFrame, features: pd.DataFrame, prices: pd.DataFrame,
                     config: dict, *, tilt_lambda: float = 0.5) -> pd.DataFrame:
    """All research allocation policies, aligned to the signal calendar."""
    b = config["backtest"]
    target = float(b["vol_target"])
    floor = float(config["hmm"]["volatility_floor"])
    out = pd.DataFrame(index=signals.index)
    base = _clip01(signals["state_exposure"].to_numpy())
    out["vol_state"] = base
    out["vol_expected"] = _clip01(target / np.maximum(signals["expected_vol"].to_numpy(), floor))
    out["vol_transition"] = _clip01(target / np.maximum(signals["expected_next_vol"].to_numpy(), floor))
    # Posterior uncertainty: scale the risk mapping by one minus normalised entropy.
    entropy = signals["entropy_normalized"].to_numpy()
    out["entropy_scaled"] = _clip01(base * (1.0 - entropy))
    # Return-aware tilt, standardised by the cross-state dispersion of training means.
    spread = np.maximum(signals["state_return_dispersion"].to_numpy(), 1e-8)
    z = (signals["expected_return"].to_numpy() - signals["state_mean_return"].to_numpy()) / spread
    out["return_tilt"] = _clip01(base * (1.0 + tilt_lambda * np.clip(z, -2, 2)))
    # Trend policies for identical comparison.
    trend_name = f"Trend {b['trend_window']}"
    trend = fixed_signals(prices, config)[trend_name].reindex(signals.index).to_numpy(dtype=float)
    vol20 = features["volatility_20"].reindex(signals.index).to_numpy(dtype=float)
    out["trend"] = trend
    out["trend_vol"] = _clip01(trend * (target / np.maximum(vol20, floor)))
    # Training-quantile risk gate on trend exposure (no evaluation-period tuning).
    high = np.clip(signals["p_high_train_p80"].to_numpy(), 0, 1)
    p_high = signals[[c for c in signals.columns if c.startswith("p_rank_")]].to_numpy()[:, -1]
    in_high = (p_high >= high).astype(float)
    out["trend_risk_gate"] = _clip01(trend * (1.0 - 0.5 * in_high))
    # The original blend, reproduced for continuity (not a gate).
    blend = float(b["trend_weight_in_blend"])
    out["hmm_trend_blend"] = (1 - blend) * base + blend * trend
    out["volstate_trend_blend"] = (1 - blend) * out["vol_state"] + blend * trend
    if not np.isfinite(out.to_numpy()).all():
        raise ValueError("Allocation policies produced non-finite exposures")
    return out


def simulate_exposure(exposure: pd.Series, prices: pd.DataFrame, config: dict,
                      *, risk_free: float | None = None) -> pd.DataFrame:
    b = config["backtest"]
    returns = prices["Close"].pct_change(fill_method=None)
    return simulate(exposure, returns, initial_capital=b["initial_capital"],
                    annual_risk_free_rate=b["annual_risk_free_rate"] if risk_free is None else risk_free,
                    trading_days_per_year=b["trading_days_per_year"],
                    transaction_cost_bps=b["transaction_cost_bps"],
                    execution_delay_sessions=b["execution_delay_sessions"])


def vol_matched_exposure(signals: pd.DataFrame, features: pd.DataFrame,
                         *, refit_every: int = 21, min_history: int = 250,
                         target_column: str = "state_exposure",
                         rng: np.random.Generator | None = None,
                         block: int = 20) -> pd.Series:
    """Observable-volatility analogue of the regime mapping, causal throughout.

    An isotonic regression ``volatility_20 -> exposure`` is refit on past data
    only (every ``refit_every`` sessions).  It reproduces the shape of the regime
    mapping while using no latent state, so it is the direct test of whether the
    HMM adds anything beyond a smooth function of observed volatility.

    The deterministic mapping is a single path, so on its own it yields a single
    Sharpe ratio and no reference distribution - which is not a usable matched
    control.  When ``rng`` is supplied each refit uses a stationary block
    bootstrap of the *past* (volatility, exposure) pairs, giving a family of
    equally matched controls whose spread reflects estimation uncertainty in the
    mapping itself.  The bootstrap resamples only observations available at the
    refit date, so the control stays causal.
    """
    from sklearn.isotonic import IsotonicRegression

    vol = features["volatility_20"].reindex(signals.index).to_numpy(dtype=float)
    exposure = signals[target_column].to_numpy(dtype=float)
    n = len(vol)
    if n < min_history + 30:
        raise ValueError("Not enough history for a vol-matched control")
    output = np.full(n, np.nan)
    for start in range(min_history, n, refit_every):
        end = min(start + refit_every, n)
        # Fit on observations strictly before ``start``; -vol makes the map increasing.
        history = slice(max(0, start - 1000), start)
        mask = np.isfinite(vol[history]) & np.isfinite(exposure[history])
        if mask.sum() < 100:
            output[start:end] = exposure[start - 1]
            continue
        x, y = -vol[history][mask], exposure[history][mask]
        if rng is not None:
            idx = _block_bootstrap_index(len(x), block, rng)
            x, y = x[idx], y[idx]
        iso = IsotonicRegression(increasing=True, out_of_bounds="clip")
        iso.fit(x, y)
        output[start:end] = iso.predict(-vol[start:end])
    output[:min_history] = exposure[:min_history]
    return pd.Series(_clip01(output), index=signals.index)


def _block_bootstrap_index(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """Circular block bootstrap index over ``[0, n)`` (past-only by construction)."""
    block = max(1, min(int(block), n))
    count = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=count)
    index = np.concatenate([(start + np.arange(block)) % n for start in starts])[:n]
    return index


def phase_shift(exposure: np.ndarray, offset: int) -> np.ndarray:
    """Circular shift: preserves the path's exact marginal and autocorrelation,
    destroys its alignment with returns.  Fold boundaries become irrelevant
    because only the target path is shifted."""
    x = np.asarray(exposure, dtype=float)
    if x.ndim != 1 or len(x) < 3:
        raise ValueError("exposure must be a 1-D array with at least three entries")
    return np.roll(x, int(offset) % len(x))


def markov_path_exposure(transition: np.ndarray, state_exposure: np.ndarray, n: int,
                         rng: np.random.Generator) -> np.ndarray:
    """Simulate a state path from the fitted transition matrix and map to exposure.

    This null keeps the persistence and the marginal exposure distribution implied
    by the fitted chain but removes any information from the observed data.
    """
    transition = np.asarray(transition, dtype=float)
    if transition.ndim != 2 or transition.shape[0] != transition.shape[1]:
        raise ValueError("transition must be square")
    if len(state_exposure) != transition.shape[0]:
        raise ValueError("state_exposure must match the number of states")
    values, vectors = np.linalg.eig(transition.T)
    stationary = np.real(vectors[:, np.argmin(np.abs(values - 1.0))])
    if not np.isfinite(stationary).all() or np.abs(stationary).sum() <= 1e-12:
        stationary = np.full(transition.shape[0], 1.0 / transition.shape[0])
    stationary = np.abs(stationary) / np.abs(stationary).sum()
    states = np.empty(n, dtype=int)
    states[0] = rng.choice(len(stationary), p=stationary)
    cumulative = transition.cumsum(axis=1)
    draws = rng.random(n)
    for t in range(1, n):
        states[t] = np.searchsorted(cumulative[states[t - 1]], draws[t], side="right")
        states[t] = min(states[t], len(cumulative) - 1)
    return np.asarray(state_exposure, dtype=float)[states]


def dynamic_vol_target_exposure(prices: pd.DataFrame, config: dict,
                                *, window: int = 20) -> pd.Series:
    """Plain observable volatility targeting (no HMM), for a like-for-like control."""
    b = config["backtest"]
    r = prices["Close"].pct_change(fill_method=None)
    vol = r.rolling(window).std() * np.sqrt(b["trading_days_per_year"])
    return (b["vol_target"] / vol.replace(0, np.nan)).clip(0, 1).fillna(0.0)


def benchmark_exposures(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Fixed conventional benchmarks on the same calendar."""
    return fixed_signals(prices, config)
