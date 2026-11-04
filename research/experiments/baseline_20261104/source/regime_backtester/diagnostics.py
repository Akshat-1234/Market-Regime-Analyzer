"""Auditable data-quality, feature and fitted-state diagnostics."""
from __future__ import annotations
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy.optimize import linear_sum_assignment
from .data import annual_quality_table
from .features import build_features

PCA_FEATURES = ["daily_return", "sign_persistence", "volatility_20", "trend_20", "return_5",
                "return_20", "return_60", "volatility_5", "volatility_60", "volatility_change",
                "ma_distance_50", "ma_distance_200", "high_low_range", "intraday_return",
                "overnight_gap", "return_skewness"]


def data_diagnostics(raw: pd.DataFrame, prices: pd.DataFrame, first_signal_date: pd.Timestamp) -> dict:
    """Return diagnostics; missing weekdays are candidates, not certified gaps."""
    d = raw.copy()
    d.columns = [str(c).strip() for c in d.columns]
    if "Date" not in d:
        raise ValueError("Raw quality diagnostics require a Date column")
    parsed = pd.to_datetime(d.Date, errors="coerce")
    duplicate_dates = int(parsed.duplicated().sum())
    r = prices.Close.pct_change(fill_method=None)
    prev = prices.Close.shift(1)
    gap = prices.Open / prev - 1 if "Open" in prices else pd.Series(np.nan, index=prices.index)
    intraday = prices.Close / prices.Open - 1 if "Open" in prices else pd.Series(np.nan, index=prices.index)
    issue = pd.DataFrame({"Date": prices.index, "close": prices.Close.to_numpy(),
                          "close_return": r.to_numpy(), "overnight_gap": gap.to_numpy(),
                          "intraday_return": intraday.to_numpy()})
    issue["extreme_return"] = issue.close_return.abs() > 0.05
    issue["zero_close_return"] = issue.close_return == 0
    issue["near_prev_close_open"] = issue.overnight_gap.abs() < 0.0001 # 1 basis point
    issue["near_open_and_large_intraday"] = issue.near_prev_close_open & (issue.intraday_return.abs() > .01)
    candidates = pd.bdate_range(prices.index.min(), prices.index.max()).difference(prices.index)
    missing = pd.DataFrame({"weekday_without_row": candidates, "status": "Unverified: may be exchange holiday or data gap"})
    annual = annual_quality_table(prices)
    agg = issue.groupby(issue.Date.dt.year).agg(
        near_previous_close_within_1bp=("near_prev_close_open", "mean"),
        near_open_large_intraday_count=("near_open_and_large_intraday", "sum"),
        extreme_return_count=("extreme_return", "sum"), zero_return_count=("zero_close_return", "sum"))
    annual = annual.merge(agg, left_on="year", right_index=True, how="left")
    bad_ohlc = None
    if {"Open", "High", "Low", "Close"}.issubset(prices):
        bad_ohlc = int(((prices.High < prices.Low) | (prices.Open > prices.High) | (prices.Open < prices.Low) |
                        (prices.Close > prices.High) | (prices.Close < prices.Low)).sum())
    summary = {"rows": len(prices), "start": str(prices.index[0].date()), "end": str(prices.index[-1].date()),
               "raw_duplicate_dates": duplicate_dates, "invalid_raw_dates": int(parsed.isna().sum()),
               "missing_values_by_column": {str(k): int(v) for k,v in d.isna().sum().items()},
               "invalid_ohlc_rows": bad_ohlc,
               "weekday_candidates_without_rows": len(candidates),
               "weekday_gap_caveat": "Weekdays include exchange holidays; not a verified missing-session count.",
               "extreme_return_threshold_abs": .05, "extreme_return_days": int(issue.extreme_return.sum()),
               "zero_return_days": int(issue.zero_close_return.sum()),
               "open_within_1bp_of_previous_close_days": int(issue.near_prev_close_open.sum()) if "Open" in prices else None,
               "open_within_1bp_and_intraday_move_gt_1pct_days": int(issue.near_open_and_large_intraday.sum()) if "Open" in prices else None,
               "pca_training_end": str((prices.index[prices.index < first_signal_date])[-1].date()),
               "pca_caveat": "Exploratory, train-only PCA on 16 features; it is not used in the default HMM."}
    features = build_features(prices)
    train_all = features.loc[features.index < first_signal_date, PCA_FEATURES]
    available = [c for c in PCA_FEATURES if train_all[c].notna().any()]
    train = train_all[available].dropna()
    if available == PCA_FEATURES and len(train) >= len(PCA_FEATURES) + 1:
        scaled = StandardScaler().fit_transform(train)
        pca = PCA(svd_solver="full").fit(scaled)
        variance = pd.DataFrame({"component": [f"PC{i+1}" for i in range(len(PCA_FEATURES))],
                                 "eigenvalue": pca.explained_variance_, "explained_variance": pca.explained_variance_ratio_,
                                 "cumulative_variance": np.cumsum(pca.explained_variance_ratio_)})
        loadings = pd.DataFrame(pca.components_.T, index=PCA_FEATURES, columns=variance.component).reset_index(names="feature")
        summary["pca_status"] = "available, fitted before first OOS signal"
    else:
        variance = pd.DataFrame(columns=["component","eigenvalue","explained_variance","cumulative_variance"])
        loadings = pd.DataFrame(columns=["feature"])
        summary["pca_status"] = "unavailable: insufficient complete pre-OOS 16-feature OHLC observations"
    corr = train.corr().reset_index(names="feature") if available else pd.DataFrame(columns=["feature"])
    distributions = pd.DataFrame({"feature": train.columns, "observations": train.notna().sum().to_numpy(),
                                  "mean": train.mean().to_numpy(), "std": train.std().to_numpy(),
                                  "p05": train.quantile(.05).to_numpy(), "median": train.median().to_numpy(),
                                  "p95": train.quantile(.95).to_numpy()})
    flagged = issue[issue.extreme_return | issue.zero_close_return | issue.near_open_and_large_intraday].copy()
    return {"summary": summary, "annual": annual, "flags": flagged, "weekday_candidates": missing,
            "pca_variance": variance, "pca_loadings": loadings, "feature_correlations": corr,
            "feature_distributions": distributions}


def model_diagnostics(result) -> dict[str, pd.DataFrame]:
    calibrations = result.walkforward.state_calibrations
    signals = result.walkforward.signals
    fits = result.walkforward.fits
    rows = []
    for (refit, model), group in calibrations.groupby(["refit_date", "model"], sort=True):
        weights = group.target_exposure.to_numpy()
        rounded = np.round(weights, 6)
        pairs = [(i, j) for i in range(len(weights)) for j in range(i+1, len(weights))]
        identical = sum(abs(weights[i] - weights[j]) < 1e-6 for i,j in pairs)
        rows.append({"refit_date": refit, "model": model, "state_count": len(weights),
                     "unique_state_exposures_1e6": len(np.unique(rounded)), "state_pairs": len(pairs),
                     "identical_state_pairs": identical,
                     "identical_pair_fraction": identical / len(pairs) if pairs else np.nan,
                     "min_train_occupancy": float(group.train_occupancy.min()),
                     "max_train_occupancy": float(group.train_occupancy.max()),
                     "exposure_min": float(weights.min()), "exposure_max": float(weights.max())})
    model_summary = []
    occupancy_rows = []
    for spec in result.config["hmm"]["models"]:
        name = spec["name"]
        exposure = signals[f"model_exposure_{name}"]
        label_col = f"model_regime__{name}"
        labels = signals[label_col] if label_col in signals else signals["primary_regime"] if name == result.config["hmm"]["primary_model"] else None
        model_summary.append({"model": name, "signal_days": len(exposure), "unique_daily_exposures_1e6": exposure.round(6).nunique(),
                              "fraction_near_full_exposure": float((exposure >= 0.999999).mean()),
                              "mean_exposure": float(exposure.mean()), "p10_exposure": float(exposure.quantile(.1)),
                              "p50_exposure": float(exposure.quantile(.5)), "p90_exposure": float(exposure.quantile(.9)),
                              "rejected_seed_fits": int(fits.loc[fits.model == name, "rejected_seeds"].fillna("").ne("").sum())})
        if labels is not None:
            for k in range(spec["n_states"]):
                count = int((labels == k).sum())
                occupancy_rows.append({"model": name, "local_volatility_rank": k, "days": count,
                                       "occupancy": count / len(labels), "rare_below_5pct": count / len(labels) < .05})
    # Volatility-based Hungarian matching is a descriptive heuristic, not an
    # assumption that arbitrary state IDs are identical or proof of persistence.
    stability, cross = [], []
    for name, g in calibrations.groupby("model"):
        dates = sorted(g.refit_date.unique())
        for before, after in zip(dates[:-1], dates[1:]):
            left = g[g.refit_date == before].sort_values("state_by_train_vol")
            right = g[g.refit_date == after].sort_values("state_by_train_vol")
            va = left.weighted_next_day_vol_annualized.to_numpy()
            vb = right.weighted_next_day_vol_annualized.to_numpy()
            cost = np.abs(np.log(np.maximum(va[:,None],1e-8) / np.maximum(vb[None,:],1e-8)))
            ii,jj=linear_sum_assignment(cost)
            for i,j in zip(ii,jj):
                stability.append({"model":name,"previous_refit":before,"refit_date":after,
                                  "previous_local_rank":int(left.iloc[i].state_by_train_vol),
                                  "current_local_rank":int(right.iloc[j].state_by_train_vol),
                                  "previous_training_vol":va[i],"current_training_vol":vb[j],
                                  "absolute_vol_change":abs(va[i]-vb[j]),"matching_cost":cost[i,j],
                                  "method":"Hungarian on log training-vol difference; heuristic"})
    for refit,g in calibrations.groupby("refit_date"):
        names=sorted(g.model.unique())
        for ia,a in enumerate(names):
            for b in names[ia+1:]:
                left=g[g.model==a].sort_values("state_by_train_vol")
                right=g[g.model==b].sort_values("state_by_train_vol")
                va=left.weighted_next_day_vol_annualized.to_numpy()
                vb=right.weighted_next_day_vol_annualized.to_numpy()
                cost=np.abs(np.log(np.maximum(va[:,None],1e-8)/np.maximum(vb[None,:],1e-8)))
                ii,jj=linear_sum_assignment(cost)
                for i,j in zip(ii,jj):
                    cross.append({"refit_date":refit,"model_a":a,"model_b":b,
                                  "rank_a":int(left.iloc[i].state_by_train_vol),
                                  "rank_b":int(right.iloc[j].state_by_train_vol),
                                  "vol_a":va[i],"vol_b":vb[j],"matching_cost":cost[i,j],
                                  "method":"Hungarian on log training-vol difference; unmatched states omitted"})
    return {"state_allocation_diagnostics": pd.DataFrame(rows), "model_diagnostics": pd.DataFrame(model_summary),
            "model_occupancy": pd.DataFrame(occupancy_rows), "state_stability":pd.DataFrame(stability),
            "state_cross_model_matching":pd.DataFrame(cross)}
