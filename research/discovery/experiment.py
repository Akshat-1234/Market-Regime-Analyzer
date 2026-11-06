"""Execute and verify the frozen nested temporal discovery protocol."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import pandas as pd
from research.contracts._validation import canonical_json_bytes, sha256_bytes
from research.contracts.experiment import create_experiment, verify_experiment
from research.hmm.adapter import fit_model
from research.hmm.serialization import save_model
from .alignment import (AlignmentResult, align_state_profiles, build_state_profiles, initial_alignment)
from .data import load_feature_data
from .diagnostics import aggregate_results, block_metrics, transition_metrics
from .protocol import (FEATURE_NAMES, MIN_STATE_FRACTION, NUMERICAL_SETTINGS, PROTOCOL_VERSION, SEEDS,
                       candidate_grid, inner_folds, outer_folds, protocol_dict)
from .temporal import (AttemptScore, TrainingTransform, raw_density_from_scaled,
                       select_using_inner_evidence)
from research.contracts.model import SelectionScore
from research.hmm.version import ENGINE_VERSION


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _json_line(record):
    return (json.dumps(record, sort_keys=True, ensure_ascii=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("ascii")


def _json_lines(records):
    return b"".join(_json_line(record) for record in records)


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def _append(path, payload):
    with path.open("ab") as handle:
        handle.write(payload)


def _regularization(model):
    if model is None:
        return None
    return {"regularization_events": model.regularization_events,
            "regularization_applications": model.regularization_applications,
            "diagonal_variance_floor_hits": model.diagonal_variance_floor_hits,
            "eigenvalue_clipping_events": model.eigenvalue_clipping_events,
            "full_covariance_floor_applications": model.full_covariance_floor_applications}


def fit_attempt(candidate, seed, train_frame, evaluation_frame, outer, *, inner=None, role="inner"):
    """Fit one declared attempt and return its record, optional score, and adapter result."""
    transform = TrainingTransform.fit(train_frame)
    train = transform.apply(train_frame)
    evaluation = transform.apply(evaluation_frame)
    spec = candidate.model_spec(seed)
    config = candidate.config(seed)
    inner_id = inner.inner_fold_id if inner is not None else None
    fit_id = f"{outer.fold_id}_{inner_id or 'outer_refit'}_{candidate.candidate_id}_seed_{seed}"
    evaluation_start = evaluation_frame.index[0]
    evaluation_limit = pd.Timestamp(outer.train_end if inner is not None else outer.test_end)
    if train_frame.index[-1] >= evaluation_start or evaluation_frame.index[-1] > evaluation_limit:
        raise ValueError("fit/evaluation dates violate the declared temporal boundary")
    try:
        result = fit_model(train, train_frame.index, spec, test_x=evaluation, test_dates=evaluation_frame.index,
                           settings=config, min_state_fraction=MIN_STATE_FRACTION, space="scaled",
                           state_ids=tuple(f"local_{i}" for i in range(candidate.state_count)))
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        record = {"fit_id": fit_id, "fold_id": outer.fold_id, "inner_fold_id": inner_id, "role": role,
                  "candidate_id": candidate.candidate_id, "state_count": candidate.state_count,
                  "emission": candidate.emission, "covariance_type": candidate.covariance_type, "seed": seed,
                  "status": "failed", "converged": False, "failure_reason": f"{type(exc).__name__}: {exc}",
                  "rejection_reason": None, "transform": transform.as_dict(), "numerical_settings": asdict(config),
                  "outer_test_used_for_selection": False}
        return record, None, None
    record = {"fit_id": fit_id, "fold_id": outer.fold_id, "inner_fold_id": inner_id, "role": role,
              "candidate_id": candidate.candidate_id, "state_count": candidate.state_count,
              "emission": candidate.emission, "covariance_type": candidate.covariance_type, "seed": seed,
              "status": result.record.status.value, "converged": result.record.converged,
              "iterations": None if result.model is None else result.model.n_iter,
              "training_scaled_log_likelihood": None if result.model is None else result.model.loglik,
              "rejection_reason": result.record.rejection_reason, "failure_reason": result.record.failure_reason,
              "regularization": _regularization(result.model), "transform": transform.as_dict(),
              "numerical_settings": asdict(config),
              "train_start": transform.train_start, "train_end": transform.train_end,
              "evaluation_start": evaluation_frame.index[0].strftime("%Y-%m-%d"),
              "evaluation_end": evaluation_frame.index[-1].strftime("%Y-%m-%d"),
              "outer_test_used_for_selection": False}
    score = None
    if result.record.status.value == "accepted":
        raw = raw_density_from_scaled(evaluation_frame.index, result.oos_density.values, transform)
        scaled_values = result.oos_density.values
        record.update({"evaluation_scaled_log_density_sum": float(scaled_values.sum()),
                       "evaluation_scaled_log_density_mean": float(scaled_values.mean()),
                       "evaluation_raw_log_density_sum": float(raw.values.sum()),
                       "evaluation_raw_log_density_mean": float(raw.values.mean()),
                       "raw_density_comparison_key": list(raw.comparison_key[:-1]) + [raw.comparison_key[-1]]})
        if inner is not None:
            score = AttemptScore(candidate.candidate_id, seed, inner.inner_fold_id,
                                 SelectionScore(outer.fold_id, candidate.candidate_id, inner.inner_fold_id,
                                                evaluation_frame.index[-1], pd.Timestamp(outer.test_start),
                                                float(raw.values.mean())))
    return record, score, (result, transform, raw if result.record.status.value == "accepted" else None)


def _selection_record(selection, outer):
    candidate = next(item for item in candidate_grid() if item.candidate_id == selection.decision.selected_candidate_id)
    return {"schema": "task4-inner-selection-v1", "fold_id": outer.fold_id, "status": "selected",
            "selected_candidate_id": selection.decision.selected_candidate_id,
            "state_count": candidate.state_count, "emission": candidate.emission,
            "covariance_type": candidate.covariance_type,
            "selected_seed": selection.selected_seed,
            "mean_inner_raw_log_density_per_observation": selection.decision.mean_inner_log_density,
            "validation_fold_ids": list(selection.decision.validation_fold_ids),
            "eligible_candidates": list(selection.eligible_candidates), "candidate_scores": selection.candidate_scores,
            "seed_scores": selection.seed_scores,
            "selected_candidate_seed_scores": selection.seed_scores[selection.decision.selected_candidate_id],
            "outer_test_used": False}


def _expected_duration(matrix, index):
    value = float(matrix[index, index])
    return None if value >= 1 else 1.0 / (1.0 - value)


def _add_stability(alignment: AlignmentResult, reference, current):
    if reference is None:
        return alignment.as_dict()
    ref_model, ref_train_metrics = reference["model"], reference["training_state_metrics"]
    current_model, current_metrics = current["model"], current["training_state_metrics"]
    records = []
    for item in alignment.records:
        row = dict(item)
        if item["status"] == "accepted":
            ref_index = int(item["proposed_reference_local_id"].rsplit("_", 1)[1])
            current_index = int(item["local_state_id"].rsplit("_", 1)[1])
            ref_state = ref_train_metrics["states"][ref_index]
            current_state = current_metrics["states"][current_index]
            ref_duration = _expected_duration(ref_model.transmat, ref_index)
            current_duration = _expected_duration(current_model.transmat, current_index)
            ref_episode = reference["transition_metrics"]["empirical_episode_durations"][f"local_{ref_index}"]["mean"]
            current_episode = current["transition_metrics"]["empirical_episode_durations"][f"local_{current_index}"]["mean"]
            row["stability"] = {
                "training_profile_distance": item["distance"],
                "self_transition_abs_difference": abs(float(ref_model.transmat[ref_index, ref_index])
                                                               - float(current_model.transmat[current_index, current_index])),
                "expected_duration_abs_difference": (None if ref_duration is None or current_duration is None
                                                      else abs(ref_duration - current_duration)),
                "training_posterior_occupancy_abs_difference": abs(ref_state["posterior_weight"]
                                                                          - current_state["posterior_weight"]),
                "training_episode_mean_duration_abs_difference": (None if ref_episode is None or current_episode is None
                                                                    else abs(ref_episode - current_episode))}
        records.append(row)
    result = alignment.as_dict()
    result["records"] = records
    return result


def _outer_csv(result, aligned_ids):
    block = result.record.oos_filtered
    frame = pd.DataFrame(block.probabilities, columns=block.state_ids)
    frame.insert(0, "Date", block.dates.strftime("%Y-%m-%d"))
    hard = block.probabilities.argmax(axis=1)
    local = [block.state_ids[index] for index in hard]
    frame["hard_local_state_id"] = local
    frame["hard_aligned_state_id"] = [aligned_ids.get(state) or "" for state in local]
    return frame.to_csv(index=False, lineterminator="\n").encode("ascii")


def _density_csv(result, raw):
    return pd.DataFrame({"Date": result.record.oos_filtered.dates.strftime("%Y-%m-%d"),
                         "scaled_log_density": result.oos_density.values,
                         "raw_log_density": raw.values}).to_csv(index=False, lineterminator="\n").encode("ascii")


def _fold_artifacts(run_dir, outer, selection_record, result, transform, raw, alignment_record,
                    data_manifest, source_commit, started, train_frame, test_frame, candidate,
                    train_metrics, outer_metrics, transitions):
    model = result.model
    diagnostics = {"schema": "task4-fold-diagnostics-v1", "fold_id": outer.fold_id, "status": "accepted",
                   "boundaries": outer.as_dict(), "selection": selection_record,
                   "fit": {"status": result.record.status.value, "converged": result.record.converged,
                           "iterations": model.n_iter, "training_scaled_log_likelihood": model.loglik,
                           "regularization": _regularization(model),
                           "rejection_reason": result.record.rejection_reason, "failure_reason": result.record.failure_reason},
                   "training_state_metrics": train_metrics, "outer_state_metrics": outer_metrics,
                   "transition_metrics": transitions,
                   "outer_density": {"raw_sum": float(raw.values.sum()), "raw_mean_per_observation": float(raw.values.mean()),
                                     "scaled_sum": float(result.oos_density.values.sum()),
                                     "scaled_mean_per_observation": float(result.oos_density.values.mean()),
                                     "units": "nats_per_observation", "jacobian_included": True},
                   "alignment": alignment_record, "smoothed_probabilities_used": False}
    current_for_stability = {"model": model, "training_state_metrics": train_metrics, "transition_metrics": transitions}
    with tempfile.TemporaryDirectory(prefix="task4-model-") as temporary:
        model_path = Path(temporary) / "model.json"
        save_model(model_path, model, result.record.spec, candidate.config(selection_record["selected_seed"]),
                   outer.train_start, outer.train_end, state_ids=result.record.training_filtered.state_ids)
        model_bytes = model_path.read_bytes()
    artifacts = {"selected_model.json": model_bytes,
                 "diagnostics.json": canonical_json_bytes(diagnostics),
                 "inner_selection.json": canonical_json_bytes(selection_record),
                 "state_alignment.json": canonical_json_bytes(alignment_record),
                 "transform.json": canonical_json_bytes(transform.as_dict()),
                 "outer_filtered.csv": _outer_csv(result, alignment_record["current_to_aligned"]),
                 "outer_density.csv": _density_csv(result, raw)}
    spec_payload = asdict(result.record.spec)
    spec_payload["feature_names"] = list(result.record.spec.feature_names)
    fold_manifest = {"schema_version": "task2-experiment-manifest-v1", "experiment_id": outer.fold_id,
                     "source": {"commit": source_commit, "source_inventory_sha256": protocol_dict()["engine_freeze_sha256"]},
                     "dataset": data_manifest["dataset"],
                     "feature_spec": {"family": "rv", "version": data_manifest["feature_contract_version"],
                                      "columns": list(FEATURE_NAMES)},
                     "model_spec": spec_payload, "folds": [outer.as_dict()], "seeds": list(SEEDS),
                     "dependencies": {"python": __import__("platform").python_version(), "numpy": np.__version__,
                                      "pandas": pd.__version__, "scipy": __import__("scipy").__version__,
                                      "scikit-learn": __import__("sklearn").__version__, "hmmlearn": __import__("hmmlearn").__version__},
                     "execution": {"command": "python -m research.discovery.experiment --run",
                                   "python": __import__("sys").executable, "started_utc": started, "finished_utc": _utc()},
                     "artifacts": {name: sha256_bytes(payload) for name, payload in artifacts.items()},
                     "warnings": ["All unsuccessful candidate attempts are retained at the parent run level."],
                     "fit_records": [{"fit_id": f"{outer.fold_id}_selected", "fold_id": outer.fold_id,
                                      "status": "accepted", "converged": True}], "status": "completed"}
    create_experiment(run_dir / "folds", fold_manifest, artifacts)
    return diagnostics, current_for_stability


def verify_run(run_dir):
    root = Path(run_dir)
    manifest = json.loads((root / "run_manifest.json").read_text())
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    expected = set(manifest["artifacts"]) | {"run_manifest.json", "SHA256SUMS"}
    if actual != expected:
        raise ValueError("Task 4 run file set differs from its inventory")
    for name, digest in manifest["artifacts"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Task 4 artifact hash mismatch: {name}")
    checksum_lines = (root / "SHA256SUMS").read_text().splitlines()
    checksums = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in checksum_lines}
    if set(checksums) != actual - {"SHA256SUMS"}:
        raise ValueError("SHA256SUMS file set mismatch")
    for name, digest in checksums.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"SHA256SUMS mismatch: {name}")
    for fold_manifest in (root / "folds").glob("*/manifest.json"):
        verify_experiment(fold_manifest.parent)
    return manifest


def evaluate_inner_fold(outer_fold, features, *, grid=None, seeds=SEEDS):
    """Execute only inner-train/validation slices; outer observations are never read."""
    train = features.loc[outer_fold.train_start:outer_fold.train_end]
    attempts, scores = [], []
    for inner in inner_folds(outer_fold, train.index):
        inner_train = features.loc[inner.train_start:inner.train_end]
        validation = features.loc[inner.validation_start:inner.validation_end]
        density_reference = None
        for candidate in grid or candidate_grid():
            for seed in seeds:
                record, score, payload = fit_attempt(candidate, seed, inner_train, validation, outer_fold, inner=inner)
                attempts.append(record)
                if score is not None:
                    from .temporal import assert_same_density_contract
                    raw = payload[2]
                    if density_reference is None:
                        density_reference = raw
                    else:
                        assert_same_density_contract(density_reference, raw)
                    scores.append(score)
    return attempts, scores


def run_experiment(output_dir, source_commit):
    if len(source_commit) != 40 or source_commit != source_commit.lower():
        raise ValueError("experiment source must be a full lowercase Git commit")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    started = _utc()
    features, data_manifest = load_feature_data()
    outer = outer_folds(features.index)
    inner_manifest = {fold.fold_id: [item.as_dict() for item in inner_folds(
        fold, features.loc[:fold.train_end].index)] for fold in outer}
    _write(output / "protocol_manifest.json", canonical_json_bytes(protocol_dict()))
    _write(output / "data_feature_provenance.json", canonical_json_bytes(data_manifest))
    _write(output / "outer_fold_manifest.json", canonical_json_bytes(
        {"schema": "task4-outer-fold-manifest-v1", "folds": [fold.as_dict() for fold in outer], "inner_folds": inner_manifest}))
    for name in ("candidate_fits.jsonl", "inner_selection_records.jsonl",
                 "fold_diagnostics.jsonl", "state_alignments.jsonl"):
        _write(output / name, b"")
    attempts, selections, fold_records, alignment_records = [], [], [], []
    previous = None
    grid = candidate_grid()
    for outer_fold in outer:
        train = features.loc[outer_fold.train_start:outer_fold.train_end]
        test = features.loc[outer_fold.test_start:outer_fold.test_end]
        inner_attempts, scores = evaluate_inner_fold(outer_fold, features, grid=grid)
        attempts.extend(inner_attempts)
        _append(output / "candidate_fits.jsonl", _json_lines(inner_attempts))
        try:
            selection = select_using_inner_evidence(scores, outer_fold.fold_id)
            selection_record = _selection_record(selection, outer_fold)
        except ValueError as exc:
            selection_record = {"schema": "task4-inner-selection-v1", "fold_id": outer_fold.fold_id,
                                "status": "inconclusive", "reason": str(exc), "outer_test_used": False}
            selections.append(selection_record)
            _append(output / "inner_selection_records.jsonl", _json_line(selection_record))
            inconclusive = {"schema": "task4-fold-diagnostics-v1", "fold_id": outer_fold.fold_id,
                            "status": "inconclusive", "reason": str(exc), "boundaries": outer_fold.as_dict()}
            fold_records.append(inconclusive)
            _append(output / "fold_diagnostics.jsonl", _json_line(inconclusive))
            previous = None
            continue
        selections.append(selection_record)
        _append(output / "inner_selection_records.jsonl", _json_line(selection_record))
        candidate = next(item for item in grid if item.candidate_id == selection_record["selected_candidate_id"])
        seed = selection_record["selected_seed"]
        record, _score, payload = fit_attempt(candidate, seed, train, test, outer_fold, role="outer_refit")
        attempts.append(record)
        _append(output / "candidate_fits.jsonl", _json_line(record))
        if payload is None or record["status"] != "accepted":
            inconclusive = {"schema": "task4-fold-diagnostics-v1", "fold_id": outer_fold.fold_id,
                            "status": "inconclusive", "reason": "selected outer refit was not accepted",
                            "selection": selection_record, "outer_refit": record, "boundaries": outer_fold.as_dict()}
            fold_records.append(inconclusive)
            _append(output / "fold_diagnostics.jsonl", _json_line(inconclusive))
            previous = None
            continue
        result, transform, raw = payload
        profiles = build_state_profiles(outer_fold.fold_id, train, result.record.training_filtered)
        if previous is None:
            alignment = initial_alignment(profiles)
            reference_for_stability = None
        else:
            alignment = align_state_profiles(previous["profiles"], profiles, previous["alignment"]["current_to_aligned"])
            reference_for_stability = previous
        train_metrics = block_metrics(result.record.training_filtered, train)
        outer_metrics = block_metrics(result.record.oos_filtered, test)
        transitions = transition_metrics(result.model, result.record.training_assignments)
        current_metrics = {"model": result.model, "training_state_metrics": train_metrics,
                           "transition_metrics": transitions}
        preliminary = _add_stability(alignment, reference_for_stability, current_metrics)
        diagnostics, current = _fold_artifacts(output, outer_fold, selection_record, result, transform, raw,
                                               preliminary, data_manifest, source_commit, started,
                                               train, test, candidate, train_metrics, outer_metrics, transitions)
        fold_records.append(diagnostics)
        alignment_records.append(preliminary)
        _append(output / "fold_diagnostics.jsonl", _json_line(diagnostics))
        _append(output / "state_alignments.jsonl", _json_line(preliminary))
        previous = {"profiles": profiles, "alignment": preliminary, **current}
    aggregate = aggregate_results(fold_records, attempts, selections, alignment_records)
    _write(output / "aggregate_results.json", canonical_json_bytes(aggregate))
    artifacts = {path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in output.rglob("*") if path.is_file()}
    run_manifest = {"schema": "task4-discovery-run-v1", "protocol_version": PROTOCOL_VERSION,
                    "source_commit": source_commit, "engine_version": ENGINE_VERSION,
                    "engine_freeze_sha256": protocol_dict()["engine_freeze_sha256"],
                    "dataset_sha256": data_manifest["dataset"]["raw_sha256"],
                    "feature_sha256": data_manifest["complete_feature_sha256"],
                    "execution": {"command": "python -m research.discovery.experiment --run",
                                  "started_utc": started, "finished_utc": _utc()},
                    "candidate_attempts": len(attempts), "folds": len(outer), "status": "completed",
                    "artifacts": artifacts,
                    "warnings": ["Descriptive research only; no predictive/economic/prospective claim.",
                                 "Inconclusive and rejected fits are retained rather than discarded."]}
    _write(output / "run_manifest.json", canonical_json_bytes(run_manifest))
    all_checksums = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            all_checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}\n")
    _write(output / "SHA256SUMS", "".join(all_checksums).encode("ascii"))
    return verify_run(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--verify", metavar="RUN_DIR")
    parser.add_argument("--output-dir", default="research/experiments/task4_v1_0_0")
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    if args.verify:
        manifest = verify_run(args.verify)
        print(json.dumps({"verified": True, "run": args.verify, "attempts": manifest["candidate_attempts"]}, indent=2))
        return
    if not args.run:
        parser.error("specify --run or --verify")
    commit = args.source_commit or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    manifest = run_experiment(args.output_dir, commit)
    print(json.dumps({"status": manifest["status"], "attempts": manifest["candidate_attempts"],
                      "folds": manifest["folds"], "output": args.output_dir}, indent=2))


if __name__ == "__main__":
    main()
