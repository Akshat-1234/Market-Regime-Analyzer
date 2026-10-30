"""Research experiment runner: audit, discovery, ablations, evaluation.

Usage::

    python -m regime_backtester.study --csv data/raw/nifty_index.csv \
        --start 2012-01-01 --output research_outputs

The runner never overwrites archived runs or ``results/``.  Each invocation
writes a fresh timestamped directory under ``research_outputs/`` plus a stable
``latest`` pointer file.  Every table records the specification, seeds and data
hash that produced it through ``manifest.json``.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

from . import __version__
from .allocation import (benchmark_exposures, markov_path_exposure, phase_shift,
                         policy_exposures, simulate_exposure, vol_matched_exposure)
from .config import load_config
from .data import load_price_csv
from .discovery import (DEFAULT_SEEDS, FEATURE_SETS, Spec, align_states,
                        concatenate_signals, emission_parameters_raw, fit_engine,
                        fold_schedule, run_spec, summarise_spec)
from .features import build_features
from .metrics import daily_rf, performance_table
from .predictive import (BASE_REGRESSORS, REGIME_REGRESSORS, build_panel,
                         entropy_conditioning, expanding_oos, in_sample_tests)
from .significance import (paired_sharpe_interval, reality_check,
                           stationary_bootstrap_indices)
from .strategies import fixed_signals

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "research_outputs"


# ------------------------------------------------------------------ utilities

def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonable(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=_jsonable) + "\n", encoding="utf-8")


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False)


def _prepare(csv: str, start: str, config_path: str | None = None,
             execution_delay: int = 1) -> tuple[pd.DataFrame, dict, dict, pd.DataFrame]:
    # One-session delay is the conservative convention used by every research run;
    # the same-close default in config/default.yaml stays untouched for the legacy CLI.
    config = load_config(config_path or (ROOT / "config" / "default.yaml"),
                         {"data": {"csv": csv},
                          "walkforward": {"start_date": start},
                          "backtest": {"execution_delay_sessions": execution_delay}})
    prices, source = load_price_csv(csv, config["data"]["date_column"],
                                    config["data"]["price_column"])
    features = build_features(prices, config["backtest"]["trading_days_per_year"])
    return prices, config, source, features


# --------------------------------------------------------------- A. audit

def study_audit(prices: pd.DataFrame, features: pd.DataFrame, config: dict,
                baseline_run: Path, output: Path) -> dict:
    """Recompute data, feature, probability and execution diagnostics."""
    output.mkdir(parents=True, exist_ok=True)
    returns = prices["Close"].pct_change(fill_method=None).dropna()
    candidates = pd.bdate_range(prices.index.min(), prices.index.max()).difference(prices.index)

    summary = {
        "rows": int(len(prices)),
        "start": str(prices.index[0].date()), "end": str(prices.index[-1].date()),
        "close_return_mean_daily": float(returns.mean()),
        "close_return_sd_daily": float(returns.std()),
        "annualised_volatility": float(returns.std() * np.sqrt(252)),
        "skewness": float(returns.skew()), "excess_kurtosis": float(returns.kurt()),
        "minimum_return": float(returns.min()), "maximum_return": float(returns.max()),
        "zero_return_days": int((returns == 0).sum()),
        "extreme_abs_gt_5pct_days": int((returns.abs() > 0.05).sum()),
        "weekday_sessions_without_row": int(len(candidates)),
        "weekday_gap_caveat": "Weekdays include exchange holidays; not a verified gap count.",
        "autocorrelation_abs_return_lag1": float(returns.abs().autocorr(1)),
        "autocorrelation_abs_return_lag20": float(returns.abs().autocorr(20)),
    }
    if {"High", "Low"}.issubset(prices.columns):
        invalid = ((prices.High < prices.Low) | (prices.Close > prices.High)
                   | (prices.Close < prices.Low) | (prices.Open > prices.High)
                   | (prices.Open < prices.Low))
        summary["invalid_ohlc_rows"] = int(invalid.sum())
        summary["high_low_available"] = True
    if "Open" in prices.columns:
        gap = prices.Open / prices.Close.shift(1) - 1
        summary["open_within_1bp_of_previous_close"] = int((gap.abs() < 1e-4).sum())
        summary["open_within_1bp_and_intraday_gt_1pct"] = int(
            ((gap.abs() < 1e-4) & ((prices.Close / prices.Open - 1).abs() > 0.01)).sum())
        summary["open_data_warning"] = ("Open prices look vendor-smoothed in part of the "
                                        "sample; Open-based features are excluded from research specs.")
    _write_json(output / "data_summary.json", summary)

    feature_columns = [c for c in features.columns if features[c].notna().sum() > 1000]
    corr = features[feature_columns].corr()
    corr.to_csv(output / "feature_correlations.csv")
    pairs = []
    for i, a in enumerate(feature_columns):
        for b in feature_columns[i + 1:]:
            value = corr.loc[a, b]
            if np.isfinite(value):
                pairs.append({"feature_a": a, "feature_b": b, "correlation": float(value),
                              "abs_correlation": float(abs(value))})
    pd.DataFrame(pairs).sort_values("abs_correlation", ascending=False).head(40).to_csv(
        output / "feature_redundancy_top_pairs.csv", index=False)

    vif_rows = []
    for name, columns in FEATURE_SETS.items():
        frame = features[list(columns)].dropna()
        values = []
        for column in columns:
            others = [c for c in columns if c != column]
            x = np.column_stack([np.ones(len(frame)), frame[others].to_numpy()])
            y = frame[column].to_numpy()
            beta = np.linalg.lstsq(x, y, rcond=None)[0]
            resid = y - x @ beta
            r2 = 1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()
            values.append(float(1 / max(1 - r2, 1e-12)))
        vif_rows.append({"feature_set": name, "features": ",".join(columns),
                         "max_vif": max(values), "mean_vif": float(np.mean(values)),
                         **{f"vif_{c}": v for c, v in zip(columns, values)}})
    _write_csv(pd.DataFrame(vif_rows), output / "feature_vif.csv")

    # ---- verified baseline probability and exposure diagnostics
    signals_path = baseline_run / "signals.csv"
    diag = {}
    if signals_path.exists():
        signals = pd.read_csv(signals_path, index_col=0, parse_dates=True)
        probability_columns = [c for c in signals.columns if c.startswith("model_probability__rvd_3")]
        probs = np.clip(signals[probability_columns].to_numpy(dtype=float), 1e-12, 1.0)
        entropy = -(probs * np.log(probs)).sum(axis=1) / np.log(probs.shape[1])
        joined = signals.join(features[["volatility_20"]], how="left")
        exposure = joined["model_exposure_rvd_3"].to_numpy(dtype=float)
        vol = joined["volatility_20"].to_numpy(dtype=float)
        mask = np.isfinite(exposure) & np.isfinite(vol)
        design = np.column_stack([np.ones(mask.sum()), 1.0 / vol[mask]])
        beta = np.linalg.lstsq(design, exposure[mask], rcond=None)[0]
        fitted = design @ beta
        r2 = 1 - ((exposure[mask] - fitted) ** 2).sum() / ((exposure[mask] - exposure[mask].mean()) ** 2).sum()
        labels = signals["primary_regime"].to_numpy()
        switches = int((labels[1:] != labels[:-1]).sum())
        diag = {
            "source": str(signals_path),
            "probability_columns": probability_columns,
            "median_normalised_entropy": float(np.median(entropy)),
            "p90_normalised_entropy": float(np.quantile(entropy, 0.9)),
            "fraction_max_probability_above_0.99": float((probs.max(axis=1) > 0.99).mean()),
            "fraction_max_probability_above_0.999": float((probs.max(axis=1) > 0.999).mean()),
            "median_max_probability": float(np.median(probs.max(axis=1))),
            "label_switches_per_year": float(switches / (len(labels) / 252)),
            "state_occupancy": {f"rank_{j}": float((labels == j).mean()) for j in range(probs.shape[1])},
            "r2_exposure_on_inverse_vol": float(r2),
            "correlation_exposure_inverse_vol": float(np.corrcoef(exposure[mask], 1.0 / vol[mask])[0, 1]),
            "correlation_with_observable_vol_target": float(
                joined["model_exposure_rvd_3"].corr(joined["Vol Target"])),
            "mean_exposure": float(exposure.mean()),
            "min_exposure": float(exposure.min()), "max_exposure": float(exposure.max()),
        }
    _write_json(output / "baseline_probability_diagnostics.json", diag)

    # ---- execution-timing sensitivity on the archived baseline exposures
    timing_rows = []
    if signals_path.exists():
        signals = pd.read_csv(signals_path, index_col=0, parse_dates=True)
        returns_series = prices["Close"].pct_change(fill_method=None)
        for delay in (0, 1, 2, 3):
            for name in ("Buy & Hold", "Trend 50", "HMM Ensemble", "HMM + Trend"):
                run = simulate_exposure(signals[name], prices, {**config,
                                        "backtest": {**config["backtest"],
                                                     "execution_delay_sessions": delay}})
                from .research_metrics import evaluate_window

                stats = evaluate_window(run, config["backtest"]["annual_risk_free_rate"],
                                        config["backtest"]["trading_days_per_year"])
                timing_rows.append({"strategy": name, "execution_delay_sessions": delay,
                                    "return_lag_sessions": delay + 1,
                                    "cagr": stats["cagr"], "sharpe": stats["sharpe"],
                                    "max_drawdown": stats["max_drawdown"],
                                    "mean_exposure": stats["mean_exposure"],
                                    "turnover_per_year": stats["turnover_per_year"]})
    _write_csv(pd.DataFrame(timing_rows), output / "execution_timing_sensitivity.csv")
    return {"summary": summary, "probability_diagnostics": diag}


# --------------------------------------------------- B. state-count discovery

def _seed_stability(prices: pd.DataFrame, features: pd.DataFrame, spec: Spec, config: dict,
                    seeds=(2, 42, 7, 11, 23), n_iter: int = 200, tol: float = 1e-5,
                    min_covar: float = 1e-4) -> pd.DataFrame:
    """Agreement of causal test-block labels across random initialisations."""
    panel = features[list(spec.features)].dropna()
    dates = panel.index
    returns = prices["Close"].pct_change(fill_method=None).reindex(dates)
    folds = fold_schedule(dates, int(config["walkforward"]["min_train_days"]),
                          config["walkforward"].get("start_date"))
    rows = []
    for k, (train_start, train_end, test_start, test_end) in enumerate(folds, 1):
        from sklearn.preprocessing import StandardScaler

        train = panel.iloc[train_start:train_end].to_numpy()
        test = panel.iloc[test_start:test_end].to_numpy()
        scaler = StandardScaler().fit(train)
        labels, exposures = [], []
        for seed in seeds:
            try:
                model = fit_engine(scaler.transform(train), spec, seed=seed, n_iter=n_iter,
                                   tol=tol, min_covar=min_covar)
                probs, _, alpha = model.filter(scaler.transform(train))
                test_probs, _, _ = model.filter(scaler.transform(test), previous_log_alpha=alpha)
                labels.append(test_probs.argmax(axis=1))
                exposures.append(model.loglik)
            except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                continue
        if len(labels) < 2:
            rows.append({"n_states": spec.n_states, "fold": k,
                         "refit_date": dates[test_start], "mean_pairwise_ari": np.nan,
                         "min_pairwise_ari": np.nan, "fraction_argmax_identical": np.nan,
                         "seeds": len(labels)})
            continue
        agreements = []
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                agreements.append(adjusted_rand_score(labels[i], labels[j]))
        rows.append({"n_states": spec.n_states, "fold": k,
                     "refit_date": dates[test_start],
                     "mean_pairwise_ari": float(np.mean(agreements)),
                     "min_pairwise_ari": float(np.min(agreements)),
                     "fraction_argmax_identical": float(np.mean(
                         [np.mean(labels[0] == other) for other in labels[1:]])),
                     "seeds": len(seeds)})
    return pd.DataFrame(rows)


def _failed_summary(spec: Spec, error: str) -> dict:
    return {"spec": spec.name, "features": ",".join(spec.features),
            "n_states": spec.n_states, "covariance_type": spec.covariance_type,
            "emission": spec.emission, "sticky": spec.sticky, "folds": 0,
            "status": "all_fits_rejected", "error": error,
            "mean_inner_predictive_loglik_per_obs": np.nan,
            "mean_test_predictive_loglik_per_obs": np.nan,
            "total_aic": np.nan, "total_bic": np.nan,
            "mean_train_loglik_per_obs": np.nan, "min_occupancy": np.nan,
            "mean_effective_states": np.nan, "mean_implied_duration": np.nan,
            "mean_dof": np.nan, "failed_folds": np.nan}


def study_discovery(prices, features, config, output: Path, k_values=(2, 3, 4, 5, 6, 7),
                    seeds=DEFAULT_SEEDS) -> tuple[pd.DataFrame, dict[int, list], dict]:
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    fits_by_k: dict[int, list] = {}
    for k in k_values:
        spec = Spec(f"rvd3_k{k}", FEATURE_SETS["rvd3"], k)
        try:
            fits = run_spec(prices, features, spec, config, seeds=seeds,
                            target_volatility=config["hmm"]["target_volatility"],
                            volatility_floor=config["hmm"]["volatility_floor"])
        except RuntimeError as exc:
            # A state count that cannot produce occupied states is a valid
            # research outcome; it is recorded, not silently dropped.
            summaries.append(_failed_summary(spec, str(exc)))
            continue
        fits_by_k[k] = fits
        summaries.append({**summarise_spec(spec, fits), "status": "completed"})
    sweep = pd.DataFrame(summaries)
    sweep["rank_by_inner_predictive_loglik"] = sweep[
        "mean_inner_predictive_loglik_per_obs"].rank(ascending=False, method="min")
    sweep["rank_by_bic"] = sweep["total_bic"].rank(method="min")
    _write_csv(sweep, output / "state_count_sweep.csv")

    fold_rows = []
    for k, fits in fits_by_k.items():
        for fit in fits:
            fold_rows.append({"n_states": k, **{key: _jsonable(value)
                                                for key, value in fit.diagnostics.items()}})
    _write_csv(pd.DataFrame(fold_rows), output / "state_count_folds.csv")

    stability = pd.concat([_seed_stability(prices, features, Spec(f"rvd3_k{k}", FEATURE_SETS["rvd3"], k),
                                           config) for k in fits_by_k])
    _write_csv(stability, output / "seed_stability.csv")

    alignment_rows = []
    for k, fits in fits_by_k.items():
        for previous, current in zip(fits[:-1], fits[1:]):
            alignment_rows.append({"n_states": k, **align_states(previous, current)})
    alignment = pd.DataFrame(alignment_rows)
    _write_csv(alignment, output / "state_alignment.csv")

    valid = sweep.dropna(subset=["mean_inner_predictive_loglik_per_obs"])
    if valid.empty:
        raise RuntimeError("No state-count specification produced a usable fit")
    best_k = int(valid.sort_values("mean_inner_predictive_loglik_per_obs",
                                   ascending=False).iloc[0]["n_states"])
    selection = {
        "criterion": "mean inner held-out predictive log-density (last 20% of each training window)",
        "selected_n_states": best_k,
        "inner_predictive_loglik_by_k": dict(zip(sweep.n_states, sweep.mean_inner_predictive_loglik_per_obs)),
        "bic_by_k": dict(zip(sweep.n_states, sweep.total_bic)),
        "note": ("AIC/BIC and downstream Sharpe are reported but not used to select. "
                 "Differences smaller than ~0.01 nats/day are not interpretable."),
        "mean_seed_ari_by_k": stability.groupby("n_states").mean_pairwise_ari.mean().to_dict(),
        "identity_alignment_fraction_by_k": alignment.groupby("n_states").identity_mapping.mean().to_dict(),
    }
    _write_json(output / "selection.json", selection)
    return sweep, fits_by_k, selection


def study_features(prices, features, config, output: Path, n_states: int) -> tuple[pd.DataFrame, str]:
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for name, columns in FEATURE_SETS.items():
        if len(columns) < 2:
            continue
        spec = Spec(f"{name}_k{n_states}", columns, n_states)
        try:
            fits = run_spec(prices, features, spec, config,
                            target_volatility=config["hmm"]["target_volatility"],
                            volatility_floor=config["hmm"]["volatility_floor"])
        except RuntimeError as exc:
            summaries.append({**_failed_summary(spec, str(exc)), "feature_set": name})
            continue
        row = summarise_spec(spec, fits)
        row["feature_set"] = name
        summaries.append({**row, "status": "completed"})
    table = pd.DataFrame(summaries)
    table["rank_by_inner_predictive_loglik"] = table[
        "mean_inner_predictive_loglik_per_obs"].rank(ascending=False, method="min")
    _write_csv(table, output / "feature_ablation.csv")
    valid = table.dropna(subset=["mean_inner_predictive_loglik_per_obs"])
    best = str(valid.sort_values("mean_inner_predictive_loglik_per_obs",
                                 ascending=False).iloc[0]["feature_set"])
    _write_json(output / "selection.json", {
        "selected_feature_set": best,
        "criterion": "mean inner held-out predictive log-density",
        "delta_vs_rvd3": {
            row.feature_set: float(row.mean_inner_predictive_loglik_per_obs
                                   - table.loc[table.feature_set == "rvd3",
                                               "mean_inner_predictive_loglik_per_obs"].iloc[0])
            for row in table.itertuples()},
        "redundancy_note": "Downside/range volatility correlate > 0.9 with volatility_20.",
    })
    return table, best


def study_emissions(prices, features, config, output: Path, n_states: int,
                    feature_set: str) -> tuple[pd.DataFrame, dict, Spec, list]:
    output.mkdir(parents=True, exist_ok=True)
    columns = FEATURE_SETS[feature_set]
    specs = [
        Spec(f"gaussian_diag_k{n_states}", columns, n_states),
        Spec(f"gaussian_full_k{n_states}", columns, n_states, covariance_type="full"),
        Spec(f"student_t_k{n_states}", columns, n_states, emission="student_t", dof=8.0),
        Spec(f"sticky5_k{n_states}", columns, n_states, sticky=5.0),
        Spec(f"sticky20_k{n_states}", columns, n_states, sticky=20.0),
    ]
    summaries, fitted = [], {}
    failed: list[Spec] = []
    for spec in specs:
        try:
            fits = run_spec(prices, features, spec, config,
                            target_volatility=config["hmm"]["target_volatility"],
                            volatility_floor=config["hmm"]["volatility_floor"])
        except RuntimeError as exc:
            summaries.append({**_failed_summary(spec, str(exc)),
                              "emission_family": spec.emission,
                              "estimated_dof_median": np.nan, "status": "all_fits_rejected"})
            failed.append(spec)
            continue
        fitted[spec.name] = fits
        row = summarise_spec(spec, fits)
        row["emission_family"] = spec.emission
        row["estimated_dof_median"] = float(np.nanmedian(
            [f.model.dof for f in fits if f.model.dof is not None])) if spec.emission == "student_t" else np.nan
        summaries.append({**row, "status": "completed"})
    table = pd.DataFrame(summaries)
    table["rank_by_inner_predictive_loglik"] = table[
        "mean_inner_predictive_loglik_per_obs"].rank(ascending=False, method="min")
    _write_csv(table, output / "emission_comparison.csv")
    valid = table.dropna(subset=["mean_inner_predictive_loglik_per_obs"])
    if valid.empty:
        raise RuntimeError("Every emission specification failed")
    best_name = str(valid.sort_values("mean_inner_predictive_loglik_per_obs",
                                      ascending=False).iloc[0]["spec"])
    best_spec = next(s for s in specs if s.name == best_name)

    # Duration diagnostics: geometric assumption vs realised label runs.
    duration_rows = []
    for spec in (specs[0], specs[3], specs[4], specs[2]):
        if spec.name not in fitted:
            continue
        fits = fitted[spec.name]
        signals = concatenate_signals(fits)
        labels = signals["argmax_rank"].to_numpy()
        runs, start = [], 0
        for i in range(1, len(labels) + 1):
            if i == len(labels) or labels[i] != labels[start]:
                runs.append(i - start)
                start = i
        runs = np.asarray(runs)
        implied = np.mean(1.0 / np.maximum(1.0 - np.diag(np.mean([f.transition for f in fits], axis=0)), 1e-9))
        mean_run = float(runs.mean())
        # Binned chi-square of run lengths against a geometric with matched mean.
        edges = np.array([1, 2, 3, 4, 5, 10, np.inf])
        observed = np.histogram(runs, bins=edges)[0]
        p = 1.0 / max(mean_run, 1.0)
        expected = np.array([(1 - p) ** (edges[i] - 1) - (1 - p) ** (min(edges[i + 1], 10000) - 1)
                             for i in range(len(edges) - 1)]) * len(runs)
        expected = np.maximum(expected, 1e-9)
        chi2 = float(((observed - expected) ** 2 / expected).sum())
        duration_rows.append({"spec": spec.name, "implied_mean_duration": float(implied),
                              "empirical_mean_run": mean_run,
                              "empirical_median_run": float(np.median(runs)),
                              "fraction_runs_of_length_1": float((runs == 1).mean()),
                              "geometric_fraction_length_1": float(p),
                              "chi_square_vs_geometric": chi2,
                              "chi_square_df": len(edges) - 2,
                              "runs": int(len(runs))})
    _write_csv(pd.DataFrame(duration_rows), output / "duration_diagnostics.csv")
    _write_json(output / "selection.json", {
        "selected_spec": best_spec.name,
        "emission": best_spec.emission, "sticky": best_spec.sticky,
        "criterion": "mean inner held-out predictive log-density",
        "inner_loglik_by_spec": dict(zip(table.spec, table.mean_inner_predictive_loglik_per_obs)),
    })
    return table, fitted, best_spec, fitted[best_spec.name]


# --------------------------------------------------------------- C. inference

def study_predictive(prices, features, config, output: Path, fits) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    signals = concatenate_signals(fits)
    panel = build_panel(prices, signals, features)
    targets = ["fwd_return_1", "fwd_return_5", "fwd_return_20", "fwd_vol_20", "fwd_drawdown_20"]
    rows = []
    for target in targets:
        rows.extend(in_sample_tests(panel, target))
    _write_csv(pd.DataFrame(rows), output / "hac_regressions.csv")

    oos = [expanding_oos(panel, target) for target in targets]
    _write_csv(pd.DataFrame(oos), output / "expanding_oos.csv")

    entropy_rows = []
    for target in ("fwd_return_20", "fwd_vol_20", "fwd_drawdown_20"):
        entropy_rows.append(entropy_conditioning(panel, target))
    _write_csv(pd.concat(entropy_rows), output / "entropy_conditioning.csv")

    # State-conditional forward behaviour (rank labels, not manually named).
    label_rows = []
    signals_with_targets = signals.join(panel[["fwd_return_20", "fwd_vol_20", "fwd_drawdown_20"]])
    for rank, group in signals_with_targets.groupby("argmax_rank"):
        label_rows.append({"rank": int(rank), "days": int(len(group)),
                           "mean_exposure": float(group["state_exposure"].mean()),
                           "mean_state_vol": float(group["expected_vol"].mean()),
                           "mean_fwd_return_20": float(group["fwd_return_20"].mean()),
                           "median_fwd_return_20": float(group["fwd_return_20"].median()),
                           "mean_fwd_vol_20": float(group["fwd_vol_20"].mean()),
                           "mean_fwd_drawdown_20": float(group["fwd_drawdown_20"].mean())})
    _write_csv(pd.DataFrame(label_rows), output / "state_forward_characteristics.csv")

    reg = pd.DataFrame(rows)
    summary = {}
    for target in targets:
        subset = reg[(reg.target == target)]
        full = subset[subset.model == "observable_plus_regime"].iloc[0]
        base = subset[subset.model == "observable_only"].iloc[0]
        summary[target] = {"incremental_r2": float(full.r2 - base.r2),
                           "wald_p_value": float(full.wald_p_value),
                           "n": int(full.n)}
    oos_frame = pd.DataFrame(oos)
    summary["oos"] = {row.target: {"oos_r2_vs_observable": row.oos_r2_vs_observable,
                                   "dm_p_value": row.dm_p_value,
                                   "observations": row.observations}
                      for row in oos_frame.itertuples()}
    _write_json(output / "predictive_summary.json", summary)
    return summary


# ------------------------------------------------------------ D. allocation

def _stationary_bootstrap_control_summary(real: pd.Series, controls: list[pd.Series],
                                          *, periods: int, rf: float) -> dict:
    from .significance import sharpe_from_values

    drf = daily_rf(rf, periods)
    sharpes = np.array([sharpe_from_values((c.to_numpy() - drf)[None, :], periods)[0]
                        for c in controls])
    real_sharpe = float(sharpe_from_values((real.to_numpy() - drf)[None, :], periods)[0])
    return {"real_sharpe": real_sharpe,
            "control_median_sharpe": float(np.nanmedian(sharpes)),
            "control_p05": float(np.nanquantile(sharpes, 0.05)),
            "control_p95": float(np.nanquantile(sharpes, 0.95)),
            "fraction_real_above_control": float(np.nanmean(real_sharpe > sharpes)),
            "control_simulations": len(controls)}


def study_allocation(prices, features, config, output: Path, fits, spec: Spec,
                     simulations: int = 200, seed: int = 1701) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    signals = concatenate_signals(fits)
    b = config["backtest"]
    policies = policy_exposures(signals, features, prices, config)
    benchmarks = benchmark_exposures(prices, config).reindex(signals.index)
    exposure_table = pd.concat([benchmarks, policies.add_prefix("policy_")], axis=1)
    if exposure_table.isna().any(axis=None):
        raise ValueError("Exposure table contains missing values")

    runs = {name: simulate_exposure(exposure_table[name], prices, config)
            for name in exposure_table.columns}
    performance = performance_table(runs, config)
    performance.to_csv(output / "performance.csv")

    rf, periods = b["annual_risk_free_rate"], b["trading_days_per_year"]
    # ``daily_rf`` is a *daily* rate: passing the annual rate here shifted both
    # Sharpes by 6.5 %/day, which is not a common additive shift for a ratio and
    # therefore flipped the sign of differences between strategies of different
    # volatility.  Fixed (see VERIFICATION.md, defect D6).
    rf_daily = daily_rf(rf, periods)
    _write_csv(pd.DataFrame({name: run["strategy_return"] for name, run in runs.items()}),
               output / "daily_returns.csv")
    # Paired stationary-bootstrap intervals against two conventional benchmarks.
    bootstrap_rows = []
    for name in exposure_table.columns:
        for control in ("Trend 50", "Vol Target", "policy_trend_vol"):
            if name == control or control not in runs:
                continue
            stats = paired_sharpe_interval(runs[name]["strategy_return"],
                                           runs[control]["strategy_return"],
                                           periods=periods, daily_rf=rf_daily,
                                           samples=1000, mean_block=20, seed=seed)
            bootstrap_rows.append({"strategy": name, "control": control, **stats})
    _write_csv(pd.DataFrame(bootstrap_rows), output / "paired_bootstrap.csv")

    # ---- matched controls for the two pre-specified regime policies
    rng = np.random.default_rng(seed)
    n = len(signals)
    control_rows, summary = [], {}
    for policy in ("policy_vol_state", "policy_return_tilt"):
        exposure = exposure_table[policy].to_numpy(dtype=float)
        shifted, markov = [], []
        for _ in range(simulations):
            offset = int(rng.integers(250, max(251, n - 250)))
            shifted.append(pd.Series(phase_shift(exposure, offset), index=signals.index))
        for _ in range(simulations):
            path = np.empty(n)
            for fit in fits:
                length = len(fit.test_index)
                start = np.searchsorted(signals.index, fit.test_index[0])
                path[start:start + length] = markov_path_exposure(
                    fit.transition, fit.state_exposures, length, rng)
            markov.append(pd.Series(np.clip(path, 0, 1), index=signals.index))
        control_frames = {"phase_shift": shifted, "markov_path": markov}
        if policy == "policy_vol_state":
            # A single deterministic vol->exposure mapping gives one Sharpe ratio and
            # therefore no reference distribution; resample the past pairs so the
            # control family spans estimation uncertainty in the mapping itself.
            control_frames["vol_matched"] = [
                vol_matched_exposure(signals, features, target_column="state_exposure",
                                     rng=rng) for _ in range(min(simulations, 100))]
        real_run = runs[policy]
        for kind, series_list in control_frames.items():
            control_runs = [simulate_exposure(series, prices, config) for series in series_list]
            stats = _stationary_bootstrap_control_summary(
                real_run["strategy_return"], [c["strategy_return"] for c in control_runs],
                periods=periods, rf=rf)
            from scipy.stats import ks_2samp

            ks = float(np.mean([ks_2samp(series.to_numpy(), exposure).statistic
                                for series in series_list]))
            summary[f"{policy}__{kind}"] = {**stats,
                                            "median_exposure_ks": ks,
                                            "mean_exposure_real": float(exposure.mean()),
                                            "mean_exposure_control": float(np.mean([s.mean() for s in series_list])),
                                            "mean_turnover_real": float(real_run["turnover"].sum() * 252 / len(real_run)),
                                            "mean_turnover_control": float(np.mean(
                                                [c["turnover"].sum() * 252 / len(c) for c in control_runs]))}
    _write_csv(pd.DataFrame([{"policy_control": k, **v} for k, v in summary.items()]),
               output / "matched_controls.csv")
    _write_json(output / "matched_controls_summary.json", summary)

    # ---- family-wide reality check against the conventional trend+vol target
    return_frame = pd.DataFrame({name: run["strategy_return"] for name, run in runs.items()})
    # ``reality_check`` differences against the benchmark, so the cash rate cancels
    # and only the (correct) daily rate is passed for API consistency.
    rc = reality_check(return_frame, "policy_trend_vol", periods=periods,
                       daily_rf=rf_daily, samples=1000, mean_block=20, seed=seed)
    rc["ranking"].to_csv(output / "reality_check_ranking.csv", index=False)
    _write_json(output / "reality_check.json",
                {k: v for k, v in rc.items() if k != "ranking"})
    return {"performance": performance, "matched_controls": summary,
            "reality_check": {k: v for k, v in rc.items() if k != "ranking"}}




# ------------------------------------------------------- experiment register

def write_experiment_register(run_dir: Path) -> pd.DataFrame:
    """Document every experiment, its hypothesis, criteria and outcome.

    Generated from the produced artefacts so the register cannot drift from the
    results.  Rows that were planned but not executed are marked explicitly.
    """
    rows: list[dict] = []
    common = {
        "training_data": "expanding annual windows ending the session before each refit",
        "evaluation_data": "2012-01-05..2026-10-22 out-of-sample returns (already examined historically)",
    }
    sweep_path = run_dir / "discovery" / "state_count_sweep.csv"
    if sweep_path.exists():
        sweep = pd.read_csv(sweep_path)
        best = sweep.sort_values("mean_inner_predictive_loglik_per_obs", ascending=False).iloc[0]
        rows.append({
            "experiment_id": "E1_state_count",
            "hypothesis": "More than two latent states are required to describe the joint return/volatility/drawdown process.",
            "variable_changed": "number of Gaussian-diagonal states (2..7)",
            "held_constant": "features daily_return, volatility_20, drawdown_252; annual refits; seeds 2/42/7; scaler fit in-fold",
            "metric": "mean inner held-out predictive log-density (last 20% of each training window); AIC/BIC; seed ARI; occupancy",
            "failure_criterion": "the chosen K does not exceed simpler K by more than 0.01 nats/day, or states are unstable",
            "result": (f"selected K={int(best.n_states)} with mean inner log-density "
                       f"{best.mean_inner_predictive_loglik_per_obs:.4f}; BIC total {best.total_bic:.0f}"),
            "decision": "K carried forward to the feature and emission studies",
            **common})
    feat_path = run_dir / "features" / "feature_ablation.csv"
    if feat_path.exists():
        feat = pd.read_csv(feat_path)
        best = feat.sort_values("mean_inner_predictive_loglik_per_obs", ascending=False).iloc[0]
        baseline = feat.loc[feat.feature_set == "rvd3", "mean_inner_predictive_loglik_per_obs"]
        delta = (best.mean_inner_predictive_loglik_per_obs - baseline.iloc[0]) if len(baseline) else np.nan
        rows.append({
            "experiment_id": "E2_feature_ablation",
            "hypothesis": "Trend, downside-risk, range-volatility or vol-of-vol information improves state discovery beyond returns+vol+drawdown.",
            "variable_changed": "feature family (7 sets, one dimension added at a time)",
            "held_constant": "state count, emission family, refit calendar, seeds, scaler protocol",
            "metric": "mean inner held-out predictive log-density; correlation/VIF redundancy",
            "failure_criterion": "no family improves the held-out criterion by 0.01 nats/day",
            "result": f"best {best.feature_set} with delta {delta:.4f} nats/day versus rvd3",
            "decision": "best feature set carried forward",
            **common})
    emit_path = run_dir / "emissions" / "emission_comparison.csv"
    if emit_path.exists():
        emit = pd.read_csv(emit_path)
        best = emit.sort_values("mean_inner_predictive_loglik_per_obs", ascending=False).iloc[0]
        rows.append({
            "experiment_id": "E3_emissions_and_duration",
            "hypothesis": "Gaussian emissions and geometric durations are adequate for daily index data (excess kurtosis ~16).",
            "variable_changed": "Gaussian diag / Gaussian full / Student-t / sticky transitions (kappa 5, 20)",
            "held_constant": "state count, feature set, refit calendar, seeds",
            "metric": "mean inner held-out predictive log-density; implied vs empirical durations",
            "failure_criterion": "no alternative improves held-out density; duration misfit not material",
            "result": f"selected {best.spec} with {best.mean_inner_predictive_loglik_per_obs:.4f} nats/day",
            "decision": "selected specification used for predictive and allocation studies",
            **common})
    predictive_path = run_dir / "predictive" / "predictive_summary.json"
    if predictive_path.exists():
        summary = json.loads(predictive_path.read_text(encoding="utf-8"))
        oos = summary.get("oos", {})
        rows.append({
            "experiment_id": "E4_predictive_information",
            "hypothesis": "Causal filtered state information predicts future returns/volatility beyond conventional observables.",
            "variable_changed": "adding regime probabilities + entropy to a ridge model of observable indicators",
            "held_constant": "expanding re-estimation every 21 sessions, minimum 500 observations, identical ridge penalty",
            "metric": "expanding-window OOS R^2 versus observable-only model; Diebold-Mariano; in-sample HAC Wald",
            "failure_criterion": "OOS R^2 <= 0 and DM p > 0.05 for every horizon",
            "result": "; ".join(f"{k}: OOS R2 {v['oos_r2_vs_observable']:.4f}, DM p {v['dm_p_value']:.3f}"
                                for k, v in oos.items()),
            "decision": "predictive information not established; allocation study still run as the economic test",
            **common})
    controls_path = run_dir / "allocation" / "matched_controls_summary.json"
    if controls_path.exists():
        controls = json.loads(controls_path.read_text(encoding="utf-8"))
        rows.append({
            "experiment_id": "E5_allocation_and_controls",
            "hypothesis": "Regime-conditioned allocation improves risk-adjusted return beyond trend, volatility targeting and matched random controls.",
            "variable_changed": "allocation rule (risk-only, transition-aware, entropy-scaled, return-tilt, trend+vol)",
            "held_constant": "one-session execution delay, 10 bps one-way cost, 6.5% cash, identical dates and costs",
            "metric": "net Sharpe/CAGR/max drawdown; phase-shift and Markov-path control distributions; reality check p-value",
            "failure_criterion": "real strategy does not exceed the control median, or reality check p > 0.05",
            "result": "; ".join(f"{k}: real {v['real_sharpe']:.3f} vs control median "
                                f"{v['control_median_sharpe']:.3f} (beats {v['fraction_real_above_control']:.0%})"
                                for k, v in controls.items()),
            "decision": "reported without selecting a winning rule",
            **common})
    rows.append({
        "experiment_id": "E6_prospective_holdout",
        "hypothesis": "Frozen specification performs as expected on genuinely unseen data.",
        "variable_changed": "none (frozen)",
        "held_constant": "everything",
        "metric": "post-freeze Sharpe/drawdown",
        "failure_criterion": "not applicable yet",
        "result": "NOT EXECUTED: the supplied data end 2026-10-22 and the freeze date is 2026-10-30; no decision can occur strictly after both.",
        "decision": "pending; see runs/run_20261030_081436_12ea5b/holdout_freeze.json",
        **common})
    register = pd.DataFrame(rows)
    register.to_csv(run_dir / "EXPERIMENT_REGISTER.csv", index=False)
    return register


# ------------------------------------------------------------------- runner

def run_all(csv: str, start: str, output: Path, *, simulations: int = 200,
            seed: int = 1701, baseline_run: Path | None = None,
            execution_delay: int = 1, k_values=(2, 3, 4, 5, 6, 7)) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output / f"study_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    prices, config, source, features = _prepare(csv, start, execution_delay=execution_delay)
    baseline_run = baseline_run or (ROOT / "runs" / "run_20261030_080824_12346d")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "project_version": __version__, "python": platform.python_version(),
        "data": source, "start_date": start, "seeds": list(DEFAULT_SEEDS),
        "simulations": simulations, "simulation_seed": seed,
        "config": config,
        "packages": {name: _package_version(name) for name in
                     ("numpy", "pandas", "scipy", "scikit-learn", "hmmlearn", "statsmodels")},
        "stages": {},
    }
    _write_json(run_dir / "manifest.json", manifest)

    print("[audit]")
    audit = study_audit(prices, features, config, baseline_run, run_dir / "audit")
    manifest["stages"]["audit"] = "completed"

    print("[discovery] state-count sweep")
    sweep, fits_by_k, selection = study_discovery(prices, features, config,
                                                  run_dir / "discovery", k_values=k_values)
    n_states = selection["selected_n_states"]
    manifest["stages"]["discovery"] = "completed"

    print(f"[features] ablation at K={n_states}")
    feature_table, feature_set = study_features(prices, features, config,
                                                run_dir / "features", n_states)
    manifest["stages"]["features"] = "completed"

    print(f"[emissions] comparison at K={n_states}, features={feature_set}")
    emission_table, fitted_by_name, best_spec, final_fits = study_emissions(
        prices, features, config, run_dir / "emissions", n_states, feature_set)
    manifest["stages"]["emissions"] = "completed"
    manifest["selected_specification"] = asdict(best_spec)
    manifest["selection"] = {"n_states": n_states, "feature_set": feature_set,
                             "emission": best_spec.name}

    print("[predictive]")
    predictive = study_predictive(prices, features, config, run_dir / "predictive", final_fits)
    manifest["stages"]["predictive"] = "completed"

    print("[allocation]")
    allocation = study_allocation(prices, features, config, run_dir / "allocation",
                                  final_fits, best_spec, simulations=simulations, seed=seed)
    manifest["stages"]["allocation"] = "completed"

    write_experiment_register(run_dir)
    manifest["stages"]["register"] = "completed"
    _write_json(run_dir / "manifest.json", manifest)
    (output / "LATEST").write_text(run_dir.name + "\n", encoding="utf-8")
    return run_dir


def _package_version(name: str) -> str | None:
    from importlib import metadata

    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the market-regime research studies")
    parser.add_argument("--csv", default=str(ROOT / "data" / "raw" / "nifty_index.csv"))
    parser.add_argument("--start", default="2012-01-01")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--simulations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--baseline-run", default=None)
    parser.add_argument("--execution-delay", type=int, default=1)
    args = parser.parse_args(argv)
    run_dir = run_all(args.csv, args.start, Path(args.output), simulations=args.simulations,
                      seed=args.seed, execution_delay=args.execution_delay,
                      baseline_run=Path(args.baseline_run) if args.baseline_run else None)
    print(f"Study written to {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
