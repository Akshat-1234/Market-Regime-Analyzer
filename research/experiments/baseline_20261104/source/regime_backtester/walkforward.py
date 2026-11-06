"""Calendar-year walk-forward training, filtering and signal generation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .features import build_features, common_model_features
from .hmm import fit_regime
from .strategies import fixed_signals


@dataclass
class WalkForwardResult:
    signals: pd.DataFrame
    fits: pd.DataFrame
    state_calibrations: pd.DataFrame
    transition_matrices: pd.DataFrame


def walk_forward(prices: pd.DataFrame, config: dict,
                 progress: Callable[[str], None] | None = None) -> WalkForwardResult:
    """At each first signal of a new year, refit using strictly earlier data.

    All HMM variants share an observation calendar. Every signal is known at
    that date's close; the execution engine handles the next-interval lag.
    """
    wf, h, b = config["walkforward"], config["hmm"], config["backtest"]
    if wf["end_date"]:
        prices = prices.loc[:wf["end_date"]].copy()
    if len(prices) < 2:
        raise ValueError("No usable prices before end_date")
    all_features = build_features(prices, b["trading_days_per_year"])
    features = common_model_features(all_features, h["models"])
    dates = features.index
    # Ensure the fixed controls have finished their own warm-up as well.
    baseline_warmup = max(b["trend_window"], b["momentum_window"],
                          b["mean_reversion_window"] - 1, 50, 20, 14)
    if len(prices) <= baseline_warmup:
        raise ValueError("Not enough rows for baseline indicator warm-up")
    first = max(wf["min_train_days"],
                int(dates.searchsorted(prices.index[baseline_warmup], side="left")))
    if wf["start_date"]:
        first = max(first, int(dates.searchsorted(pd.Timestamp(wf["start_date"]), side="left")))
    if len(features) - first < 2:
        raise ValueError(
            f"Not enough feature-valid rows: have {len(features)}, require at least "
            f"{first + 2} for training plus two OOS signal dates."
        )
    returns = prices["Close"].pct_change(fill_method=None).reindex(dates)
    base = fixed_signals(prices, config).reindex(dates)
    signal_blocks = []
    fits = []
    calibrations = []
    matrices = []
    pos = first
    while pos < len(features):
        first_signal = dates[pos]
        next_year = pd.Timestamp(year=first_signal.year + 1, month=1, day=1)
        end = int(dates.searchsorted(next_year, side="left"))
        end = min(end, len(features))
        train_from = 0 if wf["max_train_days"] is None else max(0, pos - wf["max_train_days"])
        train = features.iloc[train_from:pos]
        test = features.iloc[pos:end]
        if train.index.max() >= test.index.min():
            raise AssertionError("Training must end strictly before first signal")
        if progress:
            progress(f"Refit {first_signal.date()}: {len(train)} train rows, {len(test)} signal dates")
        block = base.loc[test.index].copy()
        overlays = []
        primary = None
        for spec in h["models"]:
            fitted = fit_regime(train[spec["features"]].to_numpy(),
                                returns.loc[train.index].to_numpy(), spec, config,
                                b["trading_days_per_year"])
            p = fitted.filter_new(test[spec["features"]].to_numpy())
            exposure = p @ fitted.exposures
            overlays.append(exposure)
            block[f"model_exposure_{spec['name']}"] = exposure
            # Preserve every model's local, train-volatility-ranked posterior.
            # Ranks across folds/models are not identical economic states.
            for j in range(spec["n_states"]):
                block[f"model_probability__{spec['name']}__{j}"] = p[:, j]
            block[f"model_regime__{spec['name']}"] = p.argmax(axis=1)
            if spec["name"] == h["primary_model"]:
                primary = p
            record = {"refit_date": first_signal, "model": spec["name"], "states": spec["n_states"],
                      "train_start": train.index[0], "train_end": train.index[-1],
                      "signal_start": test.index[0], "signal_end": test.index[-1],
                      "train_observations": len(train), "signal_observations": len(test),
                      "features": ",".join(spec["features"]), "pca_components": spec.get("pca_components"),
                      **fitted.diagnostics}
            fits.append(record)
            trans = fitted.sorted_transition
            for state in range(spec["n_states"]):
                calibrations.append({"refit_date": first_signal, "model": spec["name"],
                                     "state_by_train_vol": state, "train_occupancy": fitted.occupancy[state],
                                     "weighted_next_day_mean": fitted.state_means[state],
                                     "weighted_next_day_vol_annualized": fitted.state_vols[state],
                                     "target_exposure": fitted.exposures[state]})
                for to in range(spec["n_states"]):
                    matrices.append({"refit_date": first_signal, "model": spec["name"],
                                     "from_state": state, "to_state": to, "probability": trans[state, to]})
        if primary is None:
            raise AssertionError("Primary model not fitted")
        block["HMM Ensemble"] = np.mean(overlays, axis=0)
        trend_name = f"Trend {b['trend_window']}"
        trend_weight = b["trend_weight_in_blend"]
        block["HMM + Trend"] = (1 - trend_weight) * block["HMM Ensemble"] + trend_weight * block[trend_name]
        for j in range(primary.shape[1]):
            block[f"p_state_{j}"] = primary[:, j]
        block["primary_regime"] = primary.argmax(axis=1)
        signal_blocks.append(block)
        pos = end
    signals = pd.concat(signal_blocks)
    if not signals.index.is_unique or not signals.index.is_monotonic_increasing:
        raise AssertionError("Walk-forward signal dates must be unique and ordered")
    return WalkForwardResult(signals, pd.DataFrame(fits), pd.DataFrame(calibrations), pd.DataFrame(matrices))
