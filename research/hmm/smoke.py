"""One bounded canonical close-only RV train/subsequent-OOS integration smoke."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from research.contracts._validation import canonical_json_bytes
from research.contracts.features import FEATURE_CONTRACT_VERSION, build_contract_features, complete_feature_rows
from research.contracts.model import FitStatus, ModelSpec
from .adapter import fit_model
from .config import EMConfig
from .serialization import save_model
from .version import ENGINE_VERSION

CANONICAL_DATA_SHA256 = "ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4"
TRAIN_ROWS = 756
OOS_ROWS = 126


def run_smoke(data_path, output_dir):
    source = Path(data_path)
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CANONICAL_DATA_SHA256:
        raise ValueError("canonical CSV hash mismatch")
    prices = pd.read_csv(source, parse_dates=["Date"])
    features, _feature_manifest = build_contract_features(prices, "rv")
    complete = complete_feature_rows(features)
    if list(complete.columns) != ["daily_return", "volatility_20"] or len(complete) < TRAIN_ROWS + OOS_ROWS:
        raise ValueError("canonical RV feature shape is not as declared")
    selected = complete.iloc[:TRAIN_ROWS + OOS_ROWS]
    train_frame = selected.iloc[:TRAIN_ROWS]
    oos_frame = selected.iloc[TRAIN_ROWS:]
    mean = train_frame.to_numpy(dtype=float).mean(axis=0)
    scale = train_frame.to_numpy(dtype=float).std(axis=0, ddof=0)
    if not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("training-only feature scale is degenerate")
    train = (train_frame.to_numpy(dtype=float) - mean) / scale
    oos = (oos_frame.to_numpy(dtype=float) - mean) / scale
    spec = ModelSpec("canonical-rv-task3-smoke", ENGINE_VERSION, "rv", FEATURE_CONTRACT_VERSION,
                     ("daily_return", "volatility_20"), 3, "gaussian", "diag",
                     "training-only-zscore-ddof0-v1", 42)
    config = EMConfig(n_states=3, covariance_type="diag", emission="gaussian",
                      n_iter=200, tol=1e-5, min_covar=1e-4, sticky=0.0, seed=42)
    result = fit_model(train, train_frame.index, spec, test_x=oos, test_dates=oos_frame.index,
                       settings=config, space="scaled", include_smoothed=True,
                       state_ids=("local_0", "local_1", "local_2"))
    causal_prefix_verified = None
    if result.record.status is FitStatus.ACCEPTED:
        original_probabilities, original_density, _ = result.model.filter(oos, result.final_log_alpha)
        mutated = oos.copy()
        mutated[len(mutated) // 2:] += 1000.0
        mutated_probabilities, mutated_density, _ = result.model.filter(mutated, result.final_log_alpha)
        split = len(oos) // 2
        causal_prefix_verified = bool(
            np.allclose(original_probabilities[:split], mutated_probabilities[:split], rtol=0, atol=1e-15)
            and np.allclose(original_density[:split], mutated_density[:split], rtol=0, atol=1e-14))
        np.testing.assert_array_equal(original_probabilities, result.record.oos_filtered.probabilities)
    feature_hash = hashlib.sha256(
        np.ascontiguousarray(complete.to_numpy(dtype=float)).tobytes()
        + "|".join(date.strftime("%Y-%m-%d") for date in complete.index).encode("ascii")).hexdigest()
    summary = {
        "schema": "task3-canonical-smoke-v1",
        "data": {"path": str(source), "raw_sha256": digest, "raw_rows": len(prices),
                 "raw_start": prices["Date"].iloc[0].strftime("%Y-%m-%d"),
                 "raw_end": prices["Date"].iloc[-1].strftime("%Y-%m-%d"),
                 "feature_contract": FEATURE_CONTRACT_VERSION, "complete_feature_rows": len(complete),
                 "complete_feature_sha256": feature_hash, "close_only": True, "imputation": False},
        "split": {"feature_valid_train_rows": TRAIN_ROWS, "subsequent_oos_rows": OOS_ROWS,
                  "train_start": train_frame.index[0].strftime("%Y-%m-%d"),
                  "train_end": train_frame.index[-1].strftime("%Y-%m-%d"),
                  "oos_start": oos_frame.index[0].strftime("%Y-%m-%d"),
                  "oos_end": oos_frame.index[-1].strftime("%Y-%m-%d"),
                  "training_mean": mean.tolist(), "training_scale_ddof0": scale.tolist()},
        "fixed_configuration": asdict(config),
        "fit": {"status": result.record.status.value, "converged": result.record.converged,
                "fallback_used": result.record.fallback_used,
                "iterations": None if result.model is None else result.model.n_iter,
                "training_log_likelihood_scaled": None if result.model is None else result.model.loglik,
                "regularization_events": None if result.model is None else result.model.regularization_events,
                "regularization_applications": None if result.model is None else result.model.regularization_applications,
                "diagonal_variance_floor_hits": None if result.model is None else result.model.diagonal_variance_floor_hits,
                "eigenvalue_clipping_events": None if result.model is None else result.model.eigenvalue_clipping_events,
                "full_covariance_floor_applications": None if result.model is None else result.model.full_covariance_floor_applications,
                "rejection_reason": result.record.rejection_reason, "failure_reason": result.record.failure_reason,
                "state_occupancy": [asdict(item) for item in result.occupancy],
                "oos_block_present": result.record.oos_filtered is not None,
                "oos_scaled_log_density_sum": None if result.oos_density is None else float(result.oos_density.values.sum())},
        "causal_prefix_verified": causal_prefix_verified,
        "scope": "single bounded integration smoke; no tuning, inference, allocation, or performance claim"}
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    if result.record.status is FitStatus.ACCEPTED:
        model_path = destination / "model.json"
        payload_hash = save_model(model_path, result.model, spec, config,
                                  train_frame.index[0], train_frame.index[-1],
                                  state_ids=("local_0", "local_1", "local_2"))
        summary["model_artifact"] = {"path": str(model_path), "payload_sha256": payload_hash,
                                     "file_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest()}
    with (destination / "summary.json").open("xb") as handle:
        handle.write(canonical_json_bytes(summary))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="research/data/nifty_index.csv")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary = run_smoke(args.data, args.output_dir)
    print(json.dumps({"status": summary["fit"]["status"], "converged": summary["fit"]["converged"],
                      "iterations": summary["fit"]["iterations"],
                      "causal_prefix_verified": summary["causal_prefix_verified"],
                      "output": str(Path(args.output_dir) / "summary.json")}, indent=2))
    if summary["fit"]["status"] != FitStatus.ACCEPTED.value or not summary["causal_prefix_verified"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
