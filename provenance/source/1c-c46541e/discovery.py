"""Causal walk-forward discovery experiments.

This module is deliberately separate from :mod:`regime_backtester.walkforward`:
the original engine and its four fixed configurations stay untouched, so the
verified baseline remains reproducible.  Here a *specification* (features, state
count, emission, covariance, stickiness) is a first-class object, every fold is
fit on strictly earlier observations, and the comparison criteria are
probabilistic (held-out predictive likelihood, AIC, BIC) rather than backtest
Sharpe.

Selection protocol (recorded in the experiment register)
-------------------------------------------------------
1. Choose the state count and emission family by the mean *inner* held-out
   predictive log-density across expanding annual folds.  The inner split is the
   first 80% of each fold's training window; the last 20% is never used to fit
   that candidate.
2. AIC/BIC and downstream Sharpe are reported, never used to select.
3. Downstream allocation uses the single selected specification for every fold;
   no per-fold or per-year model choice is made.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from hmmlearn.hmm import GaussianHMM

from .emhmm import HMMFit, fit_hmm


# ---------------------------------------------------------------- specifications

@dataclass(frozen=True)
class Spec:
    name: str
    features: tuple[str, ...]
    n_states: int
    covariance_type: str = "diag"
    emission: str = "gaussian"
    dof: float | None = None
    sticky: float = 0.0

    def as_dict(self) -> dict:
        return {"name": self.name, "features": list(self.features),
                "n_states": self.n_states, "covariance_type": self.covariance_type,
                "emission": self.emission, "dof": self.dof, "sticky": self.sticky}


#: Feature families.  Each addition is a research hypothesis, not decoration.
FEATURE_SETS: dict[str, tuple[str, ...]] = {
    # Baseline families: returns + a single volatility horizon (+ drawdown).
    "rv2": ("daily_return", "volatility_20"),
    "rvd3": ("daily_return", "volatility_20", "drawdown_252"),
    # Hypothesis: trend/momentum contains information not in vol or drawdown.
    "rvd_mom": ("daily_return", "volatility_20", "drawdown_252", "risk_adj_trend_20"),
    # Hypothesis: downside risk is distinct from total volatility.
    "rvd_down": ("daily_return", "volatility_20", "drawdown_252", "downside_vol_20"),
    # Hypothesis: range-based volatility is a less noisy risk estimate.
    "rvd_range": ("daily_return", "volatility_20", "drawdown_252", "parkinson_vol_20"),
    # Hypothesis: instability of volatility is a distinct state dimension.
    "rvd_volvol": ("daily_return", "volatility_20", "drawdown_252", "vol_of_vol_60"),
    # Hypothesis-free accumulation, deliberately included as a negative control.
    "accumulation": ("daily_return", "volatility_20", "drawdown_252",
                     "risk_adj_trend_20", "downside_vol_20", "parkinson_vol_20",
                     "vol_of_vol_60"),
}

DEFAULT_SEEDS = (2, 42, 7)


def fold_schedule(dates: pd.DatetimeIndex, min_train_days: int = 504,
                  start_date: str | None = "2012-01-01") -> list[tuple[int, int, int, int]]:
    """Expanding annual folds replicating the baseline engine's refit calendar.

    Returns ``(train_start, train_end_exclusive, test_start, test_end_exclusive)``
    positions into ``dates``.  Training always ends strictly before the first
    signal date of the fold.
    """
    n = len(dates)
    if n < min_train_days + 2:
        raise ValueError("Not enough observations for the requested minimum training window")
    first = int(min_train_days)
    if start_date:
        first = max(first, int(dates.searchsorted(pd.Timestamp(start_date), side="left")))
    folds: list[tuple[int, int, int, int]] = []
    pos = first
    while pos < n:
        first_signal = dates[pos]
        next_year = pd.Timestamp(year=first_signal.year + 1, month=1, day=1)
        end = min(int(dates.searchsorted(next_year, side="left")), n)
        folds.append((0, pos, pos, end))
        pos = end
    if not folds:
        raise ValueError("The fold schedule is empty")
    return folds


# ---------------------------------------------------------------- fitting

@dataclass
class FoldFit:
    """One specification fitted on one chronological fold."""

    spec: Spec
    train_index: pd.DatetimeIndex
    test_index: pd.DatetimeIndex
    model: HMMFit                 # states re-ordered by training volatility rank
    order: np.ndarray
    probs_train: np.ndarray       # filtered, train only, volatility-ranked
    probs_test: np.ndarray        # causal filtered, seeded from train end
    state_means: np.ndarray
    state_vols: np.ndarray
    state_exposures: np.ndarray
    transition: np.ndarray
    occupancy: np.ndarray
    scaler: StandardScaler
    train_loglik: float
    test_predictive_loglik_per_obs: float
    diagnostics: dict = field(default_factory=dict)

    def exposures_at(self, probs: np.ndarray) -> np.ndarray:
        return probs @ self.state_exposures


def fit_spec_fold(train_x: np.ndarray, train_r: np.ndarray, test_x: np.ndarray,
                  spec: Spec, *, seeds: Iterable[int] = DEFAULT_SEEDS,
                  n_iter: int = 200, tol: float = 1e-5, min_covar: float = 1e-4,
                  min_state_fraction: float = 0.02, target_volatility: float = 0.12,
                  volatility_floor: float = 0.03, annualization: int = 252) -> FoldFit:
    """Fit one spec on a training block and filter the following block causally."""
    x = np.asarray(train_x, dtype=float)
    r = np.asarray(train_r, dtype=float)
    xt = np.asarray(test_x, dtype=float)
    if not (len(x) == len(r) and len(x) > spec.n_states * 5):
        raise ValueError("Training arrays must align and be long enough")
    if (np.std(x, axis=0) < 1e-12).any():
        raise ValueError(f"{spec.name}: a training feature is constant")

    scaler = StandardScaler().fit(x)
    scaled = scaler.transform(x)
    scaled_test = scaler.transform(xt)

    accepted: list[tuple[float, HMMFit, np.ndarray, np.ndarray]] = []
    fallback: list[tuple[float, HMMFit, np.ndarray, np.ndarray]] = []
    failures: list[str] = []
    for seed in seeds:
        try:
            model = fit_engine(scaled, spec, seed=seed, n_iter=n_iter, tol=tol,
                               min_covar=min_covar)
            probs, _, final_alpha = model.filter(scaled)
            labels = probs.argmax(axis=1)
            occupancy = np.bincount(labels, minlength=spec.n_states) / len(labels)
            if (occupancy < min_state_fraction).any():
                failures.append(f"seed {seed}: occupancy below {min_state_fraction}")
                continue
            if not model.converged:
                failures.append(f"seed {seed}: no convergence")
                fallback.append((model.loglik, model, probs, final_alpha))
                continue
            accepted.append((model.loglik, model, probs, final_alpha))
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
            failures.append(f"seed {seed}: {exc}")
    # A non-converged but finite, occupied fit is used only when nothing converged,
    # and the fact is recorded.  It is never silently treated as converged.
    used_fallback = False
    if not accepted:
        if not fallback:
            raise RuntimeError(f"All fits rejected for {spec.name}: {'; '.join(failures)}")
        accepted = fallback
        used_fallback = True
    loglik, model, probs_train, final_alpha = max(accepted, key=lambda item: item[0])
    probs_test, log_pred, _ = model.filter(scaled_test, previous_log_alpha=final_alpha)

    # Calibrate state return distribution from training-only filtered
    # probabilities against the *next* training return (no OOS outcome).
    means, vols = [], []
    for state in range(spec.n_states):
        w = probs_train[:-1, state]
        y = r[1:]
        total = w.sum()
        if total <= 1e-10:
            raise RuntimeError(f"{spec.name}: state {state} has no calibration weight")
        mean = float(np.dot(w, y) / total)
        var = float(np.dot(w, (y - mean) ** 2) / total)
        means.append(mean)
        vols.append(float(np.sqrt(max(0.0, var) * annualization)))
    order = np.argsort(vols, kind="stable")
    state_vols = np.asarray(vols)[order]
    state_means = np.asarray(means)[order]
    exposures = np.clip(target_volatility / np.maximum(state_vols, volatility_floor), 0, 1)
    sorted_model = _permute_model(model, order)
    probs_train = probs_train[:, order]
    probs_test = probs_test[:, order]
    transition = model.transmat[np.ix_(order, order)]

    occupancy = np.bincount(probs_train.argmax(axis=1), minlength=spec.n_states) / len(probs_train)
    diagnostics = {
        "seed": model.seed, "iterations": model.n_iter, "converged": model.converged,
        "n_seeds_accepted": len(accepted), "rejected_seeds": "; ".join(failures),
        "used_nonconverged_fallback": used_fallback,
        "dof": model.dof, "n_parameters": model.n_parameters(),
        "aic": -2 * loglik + 2 * model.n_parameters(),
        "bic": -2 * loglik + model.n_parameters() * np.log(len(x)),
        "min_train_occupancy": float(occupancy.min()),
        "max_train_occupancy": float(occupancy.max()),
        "effective_states": float(1.0 / np.sum(occupancy ** 2)),
        "mean_diagonal": float(np.mean(np.diag(transition))),
        "implied_mean_duration": float(np.mean(1.0 / np.maximum(1.0 - np.diag(transition), 1e-6))),
    }
    return FoldFit(spec=spec,
                   train_index=pd.DatetimeIndex([]), test_index=pd.DatetimeIndex([]),
                   model=sorted_model, order=order, probs_train=probs_train,
                   probs_test=probs_test, state_means=state_means, state_vols=state_vols,
                   state_exposures=exposures, transition=transition, occupancy=occupancy[order],
                   scaler=scaler, train_loglik=loglik,
                   test_predictive_loglik_per_obs=float(log_pred.mean()) / 1.0,
                   diagnostics=diagnostics)


def fit_engine(x: np.ndarray, spec: Spec, *, seed: int, n_iter: int, tol: float,
               min_covar: float) -> HMMFit:
    """Fit one candidate with the appropriate optimizer.

    Gaussian, non-sticky models use ``hmmlearn`` (fast, well tested).  Heavy-tailed
    and duration-prior models use this project's EM, which is validated against
    ``hmmlearn`` for the Gaussian case.  Every reported likelihood is computed by
    the same log-space filter, so cross-engine comparisons are like-for-like.
    """
    use_hmmlearn = spec.emission == "gaussian" and spec.sticky == 0.0
    if not use_hmmlearn:
        return fit_hmm(x, spec.n_states, covariance_type=spec.covariance_type,
                       emission=spec.emission, dof=spec.dof, n_iter=n_iter, tol=tol,
                       min_covar=min_covar, sticky=spec.sticky, seed=seed)
    import logging

    # hmmlearn logs every max-iteration warning; the converged flag below records
    # it explicitly instead, and a rejected fit is reported per seed.
    logging.getLogger("hmmlearn").setLevel(logging.ERROR)
    tuned_tol = min(float(tol), 1e-4)
    model = GaussianHMM(n_components=spec.n_states, covariance_type=spec.covariance_type,
                        n_iter=max(n_iter, 300), tol=tuned_tol, min_covar=min_covar,
                        random_state=seed, implementation="log")
    model.fit(x)
    history = list(np.asarray(model.monitor_.history, dtype=float))
    change = history[-1] - history[-2] if len(history) >= 2 else np.inf
    fitted = HMMFit(startprob=model.startprob_, transmat=model.transmat_,
                    means=model.means_, covars=model.covars_,
                    covariance_type=spec.covariance_type, emission="gaussian",
                    dof=None, loglik=float(model.score(x)), n_iter=int(model.monitor_.iter),
                    converged=bool(len(history) >= 2 and -1e-6 <= change < tuned_tol),
                    history=history, seed=seed)
    return fitted


def emission_parameters_raw(fit: FoldFit, n_states: int | None = None) -> pd.DataFrame:
    """Emission location/scale in the original feature units, volatility-ranked."""
    k = fit.spec.n_states if n_states is None else n_states
    scale = fit.scaler.scale_
    centre = fit.scaler.mean_
    means = fit.model.means * scale + centre
    covars = fit.model.covars
    if fit.model.covariance_type == "diag":
        variances = covars * scale ** 2
    else:
        variances = np.einsum("kii->ki", covars) * scale ** 2
    return pd.DataFrame({"rank": np.arange(k),
                         **{f"mean_{c}": means[:, j] for j, c in enumerate(fit.spec.features)},
                         **{f"sd_{c}": np.sqrt(variances[:, j]) for j, c in enumerate(fit.spec.features)}})


def align_states(previous: FoldFit, current: FoldFit) -> dict:
    """Hungarian match of adjacent-fold emissions in original units.

    State identifiers are arbitrary; comparing numerical IDs across refits would
    be meaningless.  Matching is on standardised emission location and scale.
    """
    from scipy.optimize import linear_sum_assignment

    a = emission_parameters_raw(previous)
    b = emission_parameters_raw(current)
    if len(a) != len(b):
        raise ValueError("Alignment requires the same number of states")
    columns = [c for c in a.columns if c != "rank"]
    A = a[columns].to_numpy(dtype=float)
    B = b[columns].to_numpy(dtype=float)
    pooled = np.vstack([A, B])
    sd = pooled.std(axis=0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    cost = ((A[:, None, :] - B[None, :, :]) / sd) ** 2
    cost = cost.sum(axis=2)
    rows, cols = linear_sum_assignment(cost)
    return {"refit_date": current.diagnostics.get("refit_date"),
            "previous_refit_date": previous.diagnostics.get("refit_date"),
            "match_cost": float(cost[rows, cols].sum()),
            "mean_match_distance": float(np.sqrt(cost[rows, cols]).mean()),
            "identity_mapping": bool(np.all(rows == cols)),
            "mapping": ",".join(f"{int(r)}->{int(c)}" for r, c in zip(rows, cols)),
            "n_states": len(a)}


def _permute_model(model: HMMFit, order: np.ndarray) -> HMMFit:
    return HMMFit(startprob=model.startprob[order],
                  transmat=model.transmat[np.ix_(order, order)],
                  means=model.means[order], covars=model.covars[order],
                  covariance_type=model.covariance_type, emission=model.emission,
                  dof=model.dof, loglik=model.loglik, n_iter=model.n_iter,
                  converged=model.converged, history=list(model.history), seed=model.seed)


def inner_predictive_loglik(train_x: np.ndarray, train_r: np.ndarray, spec: Spec, *,
                            fraction: float = 0.8, seeds: Iterable[int] = (2, 42),
                            n_iter: int = 200, tol: float = 1e-5,
                            min_covar: float = 1e-4) -> float:
    """Held-out one-step predictive log-density inside a fold's training window.

    The last ``1 - fraction`` of the training window is never used to fit the
    candidate, so heavier models cannot win by memorising the data they are
    scored on.  The scaler is also fitted on the inner training part only.
    """
    x = np.asarray(train_x, dtype=float)
    r = np.asarray(train_r, dtype=float)
    split = max(int(len(x) * fraction), spec.n_states * 10)
    if len(x) - split < 10:
        raise ValueError("Inner validation block is too short")
    inner_x, val_x = x[:split], x[split:]
    scaler = StandardScaler().fit(inner_x)
    scaled_inner = scaler.transform(inner_x)
    scaled_val = scaler.transform(val_x)
    best: tuple[float, HMMFit, np.ndarray] | None = None
    for seed in seeds:
        model = fit_engine(scaled_inner, spec, seed=seed, n_iter=n_iter, tol=tol,
                           min_covar=min_covar)
        if best is None or model.loglik > best[0]:
            best = (model.loglik, model, model.filter(scaled_inner)[2])
    assert best is not None
    loglik, model, alpha = best
    _, log_pred, _ = model.filter(scaled_val, previous_log_alpha=alpha)
    return float(log_pred.mean())


def run_spec(prices: pd.DataFrame, features: pd.DataFrame, spec: Spec, config: dict,
             *, seeds: Iterable[int] = DEFAULT_SEEDS, n_iter: int = 200,
             tol: float = 1e-5, min_covar: float = 1e-4,
             min_state_fraction: float = 0.02, target_volatility: float = 0.12,
             volatility_floor: float = 0.03, inner_fraction: float = 0.8,
             inner_seeds: Iterable[int] = (2, 42),
             progress=None) -> list[FoldFit]:
    """Walk-forward fit of one specification. No future observation is touched."""
    unknown = [c for c in spec.features if c not in features]
    if unknown:
        raise ValueError(f"Unknown features {unknown}")
    panel = features[list(spec.features)]
    valid = panel.notna().all(axis=1)
    if not valid.any():
        raise ValueError("No complete feature rows")
    start = int(np.flatnonzero(valid.to_numpy())[0])
    panel = panel.iloc[start:]
    if panel.isna().any(axis=None):
        raise ValueError("Feature panel has an internal gap")
    dates = panel.index
    returns = prices["Close"].pct_change(fill_method=None).reindex(dates)
    wf = config["walkforward"]
    folds = fold_schedule(dates, int(wf["min_train_days"]), wf.get("start_date"))
    fits: list[FoldFit] = []
    for k, (train_start, train_end, test_start, test_end) in enumerate(folds, 1):
        if wf.get("max_train_days"):
            train_start = max(train_start, train_end - int(wf["max_train_days"]))
        train = panel.iloc[train_start:train_end]
        test = panel.iloc[test_start:test_end]
        train_returns = returns.loc[train.index].to_numpy()
        if np.isnan(train_returns).any():
            raise ValueError("Training returns contain missing values")
        fold = fit_spec_fold(train.to_numpy(), train_returns, test.to_numpy(), spec,
                             seeds=seeds, n_iter=n_iter, tol=tol, min_covar=min_covar,
                             min_state_fraction=min_state_fraction,
                             target_volatility=target_volatility,
                             volatility_floor=volatility_floor,
                             annualization=config["backtest"]["trading_days_per_year"])
        fold.train_index = train.index
        fold.test_index = test.index
        fold.diagnostics.update({
            "fold": k, "refit_date": dates[test_start],
            "train_start": train.index[0], "train_end": train.index[-1],
            "signal_start": test.index[0], "signal_end": test.index[-1],
            "train_observations": len(train), "signal_observations": len(test),
            "train_loglik_per_obs": fold.train_loglik / len(train),
        })
        try:
            fold.diagnostics["inner_predictive_loglik_per_obs"] = inner_predictive_loglik(
                train.to_numpy(), train_returns, spec, fraction=inner_fraction,
                seeds=inner_seeds, n_iter=n_iter, tol=tol, min_covar=min_covar)
        except (RuntimeError, ValueError) as exc:
            fold.diagnostics["inner_predictive_loglik_per_obs"] = float("nan")
            fold.diagnostics["inner_error"] = str(exc)
        fits.append(fold)
        if progress:
            progress(f"  {spec.name} fold {k}/{len(folds)} "
                     f"({spec.n_states} states, {len(train)} train, {len(test)} test)")
    return fits


def concatenate_signals(fits: list[FoldFit]) -> pd.DataFrame:
    """Per-date filtered probabilities, state statistics and exposures."""
    blocks = []
    for fit in fits:
        probs = np.asarray(fit.probs_test, dtype=float)
        frame = pd.DataFrame(probs, index=fit.test_index,
                             columns=[f"p_rank_{j}" for j in range(fit.spec.n_states)])
        frame["expected_vol"] = probs @ fit.state_vols
        frame["expected_return"] = probs @ fit.state_means
        frame["state_exposure"] = probs @ fit.state_exposures
        frame["expected_next_vol"] = (probs @ fit.transition.T) @ fit.state_vols
        frame["state_mean_return"] = float(np.mean(fit.state_means))
        frame["state_return_dispersion"] = float(np.std(fit.state_means))
        frame["state_vol_mean"] = float(np.mean(fit.state_vols))
        train_high = np.clip(np.asarray(fit.probs_train, dtype=float), 1e-12, 1.0)[:, -1]
        frame["p_high_train_p80"] = float(np.quantile(train_high, 0.8))
        p = np.clip(probs, 1e-12, 1.0)
        entropy = -(p * np.log(p)).sum(axis=1) / np.log(p.shape[1])
        frame["entropy_normalized"] = entropy
        frame["max_probability"] = p.max(axis=1)
        frame["argmax_rank"] = frame.filter(like="p_rank_").to_numpy().argmax(axis=1)
        blocks.append(frame)
    return pd.concat(blocks).sort_index()


def summarise_spec(spec: Spec, fits: list[FoldFit]) -> dict:
    diag = pd.DataFrame([f.diagnostics for f in fits])
    return {
        "spec": spec.name, "features": ",".join(spec.features),
        "n_states": spec.n_states, "covariance_type": spec.covariance_type,
        "emission": spec.emission, "sticky": spec.sticky,
        "folds": len(fits),
        "mean_inner_predictive_loglik_per_obs": float(diag["inner_predictive_loglik_per_obs"].mean()),
        "mean_test_predictive_loglik_per_obs": float(np.mean([f.test_predictive_loglik_per_obs for f in fits])),
        "total_aic": float(diag["aic"].sum()), "total_bic": float(diag["bic"].sum()),
        "mean_train_loglik_per_obs": float(diag["train_loglik_per_obs"].mean()),
        "min_occupancy": float(diag["min_train_occupancy"].min()),
        "mean_effective_states": float(diag["effective_states"].mean()),
        "mean_implied_duration": float(diag["implied_mean_duration"].mean()),
        "mean_dof": float(diag["dof"].dropna().mean()) if diag["dof"].notna().any() else np.nan,
        "failed_folds": int(diag["inner_error"].notna().sum()) if "inner_error" in diag else 0,
    }
