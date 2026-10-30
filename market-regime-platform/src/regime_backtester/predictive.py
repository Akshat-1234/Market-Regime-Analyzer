"""Does causal regime information predict anything beyond observable indicators?

Three questions, kept separate:
  1. Do discovered states differ in their contemporaneous characteristics?
     (descriptive; see :mod:`regime_backtester.diagnostics`)
  2. Do causal filtered probabilities carry information about FUTURE returns,
     volatility or drawdown after controlling for conventional observables?
  3. Does using that information improve portfolio decisions?  (allocation.py)

Nothing here is trained on future observations: regressions are reported both
in-sample with HAC (Newey-West) errors and out-of-sample with an expanding
re-estimation schedule.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .significance import stationary_bootstrap_indices


def newey_west_ols(y: np.ndarray, X: np.ndarray, *, lags: int) -> dict:
    """OLS with Newey-West (Bartlett) covariance."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    n, k = X.shape
    if n <= k + lags + 2:
        raise ValueError("Not enough observations for the HAC regression")
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    scores = X * resid[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1)
        gamma = scores[lag:].T @ scores[:-lag]
        meat += weight * (gamma + gamma.T)
    covariance = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(covariance), 1e-30))
    t = beta / se
    p = 2 * (1 - norm.cdf(np.abs(t)))
    total = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float((resid ** 2).sum()) / total if total > 0 else np.nan
    return {"beta": beta, "se": se, "t": t, "p": p, "r2": r2, "n": n, "k": k,
            "residuals": resid, "covariance": covariance}


def wald_zero(beta: np.ndarray, covariance: np.ndarray, indices: list[int]) -> dict:
    """Joint Wald test that a block of coefficients is zero."""
    idx = np.asarray(indices, dtype=int)
    b = beta[idx]
    V = covariance[np.ix_(idx, idx)]
    try:
        statistic = float(b @ np.linalg.pinv(V) @ b)
    except np.linalg.LinAlgError:
        return {"statistic": float("nan"), "p_value": float("nan"), "df": len(idx)}
    from scipy.stats import chi2

    return {"statistic": statistic, "p_value": float(1 - chi2.cdf(statistic, len(idx))),
            "df": len(idx)}


def forward_targets(prices: pd.DataFrame, horizon: int = 20) -> pd.DataFrame:
    """Targets known only after the horizon; used solely for evaluation."""
    close = prices["Close"].astype(float)
    r = close.pct_change(fill_method=None)
    fwd_return = close.shift(-horizon) / close - 1
    fwd_vol = r.shift(-1).rolling(horizon).std().shift(-(horizon - 1)) * np.sqrt(252)
    rolling_max = close.shift(-1).rolling(horizon).max().shift(-(horizon - 1))
    rolling_min = close.shift(-1).rolling(horizon).min().shift(-(horizon - 1))
    fwd_drawdown = rolling_min / close - 1
    return pd.DataFrame({"fwd_return": fwd_return, "fwd_vol": fwd_vol,
                         "fwd_drawdown": fwd_drawdown, "fwd_min": rolling_min,
                         "fwd_max": rolling_max})


def regime_regressors(signals: pd.DataFrame) -> pd.DataFrame:
    """Comparable, rank-based regime variables (state IDs are not comparable)."""
    pcols = sorted([c for c in signals.columns if c.startswith("p_rank_")],
                   key=lambda c: int(c.rsplit("_", 1)[1]))
    if not pcols:
        raise ValueError("signals must contain p_rank_* columns")
    probs = signals[pcols].to_numpy(dtype=float)
    out = pd.DataFrame(index=signals.index)
    out["p_low_vol"] = probs[:, 0]
    out["p_high_vol"] = probs[:, -1]
    out["entropy"] = signals["entropy_normalized"].to_numpy()
    out["expected_state_vol"] = signals["expected_vol"].to_numpy()
    out["expected_next_vol"] = signals["expected_next_vol"].to_numpy()
    out["expected_state_return"] = signals["expected_return"].to_numpy()
    return out


def build_panel(prices: pd.DataFrame, signals: pd.DataFrame, features: pd.DataFrame,
                horizons: tuple[int, ...] = (1, 5, 20)) -> pd.DataFrame:
    """Evaluation panel: causal regressors at t, future targets at t+h."""
    panel = regime_regressors(signals)
    observable = ["trend_20", "return_20", "volatility_20", "drawdown_252",
                  "risk_adj_trend_20"]
    panel = panel.join(features[observable].reindex(panel.index))
    for horizon in horizons:
        targets = forward_targets(prices, horizon).reindex(panel.index)
        panel[f"fwd_return_{horizon}"] = targets["fwd_return"]
        if horizon == 20:
            panel["fwd_vol_20"] = targets["fwd_vol"]
            panel["fwd_drawdown_20"] = targets["fwd_drawdown"]
    return panel


BASE_REGRESSORS = ["trend_20", "return_20", "volatility_20", "drawdown_252"]
REGIME_REGRESSORS = ["p_low_vol", "p_high_vol", "entropy", "expected_state_return"]
#: The out-of-sample design is kept small and well conditioned.  It excludes the
#: training-fold state *mean return* (piecewise-constant across folds) and
#: ``p_low_vol`` (nearly ``1 - p_high_vol`` for these models, which makes the
#: expanding-window design ill-conditioned and produces exploding forecasts).
#: The in-sample HAC tests keep the full block as descriptive regressors.
REGIME_REGRESSORS_OOS = ["p_high_vol", "entropy"]


def _design(frame: pd.DataFrame, columns: list[str], standardise: bool = True) -> np.ndarray:
    x = frame[columns].to_numpy(dtype=float)
    if standardise:
        sd = x.std(axis=0)
        sd = np.where(sd > 1e-12, sd, 1.0)
        x = (x - x.mean(axis=0)) / sd
    return np.column_stack([np.ones(len(x)), x])


def in_sample_tests(panel: pd.DataFrame, target: str, *, lags: int = 10) -> list[dict]:
    """Nested HAC regressions: observables only vs observables + regime block."""
    frame = panel[[target] + BASE_REGRESSORS + REGIME_REGRESSORS].dropna()
    if len(frame) < 250:
        raise ValueError(f"Too few observations for {target}")
    rows = []
    for label, columns in (("observable_only", BASE_REGRESSORS),
                           ("regime_only", REGIME_REGRESSORS),
                           ("observable_plus_regime", BASE_REGRESSORS + REGIME_REGRESSORS)):
        X = _design(frame, columns)
        fit = newey_west_ols(frame[target].to_numpy(), X, lags=lags)
        regime_idx = [1 + columns.index(c) for c in REGIME_REGRESSORS if c in columns]
        wald = wald_zero(fit["beta"], fit["covariance"], regime_idx) if regime_idx else {
            "statistic": np.nan, "p_value": np.nan, "df": 0}
        rows.append({"target": target, "model": label, "n": fit["n"], "r2": fit["r2"],
                     "wald_statistic": wald["statistic"], "wald_p_value": wald["p_value"],
                     **{f"coef_{c}": float(b) for c, b in zip(columns, fit["beta"][1:])},
                     **{f"t_{c}": float(t) for c, t in zip(columns, fit["t"][1:])}})
    return rows


def _ridge_fit(design: np.ndarray, y: np.ndarray, penalty: float) -> np.ndarray:
    """Ridge with an unpenalised intercept.

    Near-degenerate regime probabilities (the fitted posteriors are 0/1 on ~87%
    of days) can otherwise produce exploding forecasts from a handful of
    training observations.  The penalty is applied identically to both competing
    models, so it does not favour either.
    """
    k = design.shape[1]
    penalty_matrix = np.eye(k) * penalty
    penalty_matrix[0, 0] = 0.0
    return np.linalg.solve(design.T @ design + penalty_matrix, design.T @ y)


def _window_standardise(train: np.ndarray, test: np.ndarray,
                        dispersion_ratio: float = 0.10
                        ) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Centre/scale a training window; refuse slopes the window cannot identify.

    Scaling uses the *estimation window only*, so no future information enters.
    Two safeguards against extrapolation artefacts:

    * ``dead`` columns - a column whose estimation-window standard deviation is
      below ``dispersion_ratio`` times its own estimation-window range is a
      spike, not a regressor: it is 0 on nearly every observation with a
      vanishing handful of non-zero values.  Its slope would be set by those few
      points and then applied to the whole of a new regime.  Such a column is
      neutralised (standardised values exactly zero, so the ridge coefficient is
      pinned at zero) for that window.
    * ``clipped`` - standardised test values are clipped to the estimation
      window's own standardised range, i.e. no linear extrapolation beyond the
      support that was observed when the model was estimated.

    Example of why this matters: the fuzzy high-volatility state is essentially
    never occupied before March 2020 (max filtered probability 0.012 in
    2012-2020), so pre-2020 windows cannot identify its coefficient.  Applying
    that unidentified coefficient to a sustained probability of 1.0 in March
    2020 produced forecasts 300 standard deviations outside the target's range.
    That is an estimator failure, not evidence about regime information.
    """
    centre = train.mean(axis=0)
    scale = train.std(axis=0)
    span = train.max(axis=0) - train.min(axis=0)
    dead = (scale <= 0) | (scale < dispersion_ratio * span)
    safe = np.where(dead, 1.0, scale)
    train_z = (train - centre) / safe
    test_z = (test - centre) / safe
    train_z[:, dead] = 0.0
    test_z[:, dead] = 0.0
    live = ~dead
    if live.any():
        upper = train_z[:, live].max(axis=0)
        lower = train_z[:, live].min(axis=0)
        clipped = int(((test_z[:, live] > upper) | (test_z[:, live] < lower)).sum())
        test_z[:, live] = np.clip(test_z[:, live], lower, upper)
    else:
        clipped = 0
    return train_z, test_z, int(dead.sum()), clipped


def expanding_oos(panel: pd.DataFrame, target: str, *, min_train: int = 500,
                  refit_every: int = 21, ridge_penalty: float = 1.0,
                  return_forecasts: bool = False
                  ) -> dict | tuple[dict, pd.DataFrame]:
    """Expanding re-estimation comparison of observable-only vs +regime models.

    Every forecast at t uses observations strictly before t: the estimation
    window is standardised on its own moments, then applied unchanged to the
    forecast block.  The OOS R^2 is measured against the observable-only model
    (positive = regime information adds accuracy).
    """
    frame = panel[[target] + BASE_REGRESSORS + REGIME_REGRESSORS].dropna()
    if len(frame) < min_train + 50:
        raise ValueError(f"Too few observations for an expanding evaluation of {target}")
    y = frame[target].to_numpy(dtype=float)
    raw_b = frame[BASE_REGRESSORS].to_numpy(dtype=float)
    raw_r = frame[BASE_REGRESSORS + REGIME_REGRESSORS_OOS].to_numpy(dtype=float)
    y_hat_b = np.full(len(frame), np.nan)
    y_hat_r = np.full(len(frame), np.nan)
    start = min_train
    dead_windows = 0
    clipped_values = 0
    for begin in range(start, len(frame), refit_every):
        end = min(begin + refit_every, len(frame))
        train = slice(0, begin)
        for raw, output in ((raw_b, y_hat_b), (raw_r, y_hat_r)):
            train_z, test_z, n_dead, n_clipped = _window_standardise(raw[train], raw[begin:end])
            dead_windows += n_dead
            clipped_values += n_clipped
            design_train = np.column_stack([np.ones(begin), train_z])
            design_test = np.column_stack([np.ones(end - begin), test_z])
            beta = _ridge_fit(design_train, y[train], ridge_penalty)
            output[begin:end] = design_test @ beta
    mask = np.isfinite(y_hat_b) & np.isfinite(y_hat_r)
    loss_b = (y[mask] - y_hat_b[mask]) ** 2
    loss_r = (y[mask] - y_hat_r[mask]) ** 2
    oos_r2_vs_base = 1 - loss_r.sum() / loss_b.sum() if loss_b.sum() > 0 else np.nan
    dm = None
    if len(loss_b) > 20:
        from .significance import diebold_mariano

        dm = diebold_mariano(pd.Series(loss_r), pd.Series(loss_b), lags=10)
    # Sanity diagnostics: a forecast far outside the target's own history means
    # the estimator failed, and this must never be read as evidence about the
    # hypothesis.
    target_sd = float(y[:start].std())
    result = {"target": target, "observations": int(mask.sum()),
            "ridge_penalty": ridge_penalty,
            "mse_observable_only": float(loss_b.mean()),
            "mse_observable_plus_regime": float(loss_r.mean()),
            "oos_r2_vs_observable": float(oos_r2_vs_base),
            "dm_statistic": None if dm is None else dm["statistic"],
            "dm_p_value": None if dm is None else dm["p_value"],
            "forecast_sd_observable_only": float(np.nanstd(y_hat_b)),
            "forecast_sd_observable_plus_regime": float(np.nanstd(y_hat_r)),
            "max_abs_forecast_in_training_sd": float(np.nanmax(np.abs(y_hat_r)) / target_sd)
            if target_sd > 0 else np.nan,
            "columns_without_training_variation": dead_windows,
            "forecast_values_clipped_to_training_support": clipped_values}
    if return_forecasts:
        result["forecasts"] = pd.DataFrame({"actual": y, "observable_only": y_hat_b,
                                            "observable_plus_regime": y_hat_r},
                                           index=frame.index)
    return result


def entropy_conditioning(panel: pd.DataFrame, target: str, *, bins: int = 5,
                         samples: int = 1000, seed: int = 1701) -> pd.DataFrame:
    """Quantile-of-entropy buckets with stationary-bootstrap intervals."""
    frame = panel[[target, "entropy"]].dropna()
    if len(frame) < bins * 50:
        raise ValueError("Too few observations for entropy conditioning")
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.quantile(frame["entropy"], quantiles)
    edges[0], edges[-1] = -np.inf, np.inf
    labels = pd.cut(frame["entropy"], edges, labels=False, include_lowest=True)
    values = frame[target].to_numpy(dtype=float)
    indices = stationary_bootstrap_indices(len(values), samples=samples, mean_block=20, seed=seed)
    rows = []
    for bucket in range(bins):
        mask = (labels == bucket).to_numpy()
        if mask.sum() < 10:
            continue
        boot = []
        for i in range(min(samples, 400)):
            resampled = indices[i]
            selected = resampled[mask[resampled]]
            if len(selected):
                boot.append(values[selected].mean())
        boot = np.asarray(boot)
        rows.append({"target": target, "bucket": bucket + 1,
                     "entropy_low": float(edges[bucket]), "entropy_high": float(edges[bucket + 1]),
                     "observations": int(mask.sum()),
                     "mean": float(values[mask].mean()),
                     "median": float(np.median(values[mask])),
                     "boot_lower": float(np.quantile(boot, 0.025)),
                     "boot_upper": float(np.quantile(boot, 0.975)),
                     "positive_fraction": float((values[mask] > 0).mean())})
    return pd.DataFrame(rows)
