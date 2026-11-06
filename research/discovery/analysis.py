"""Verify a completed Task 4 run and derive descriptive, non-selective reports."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd

from research.contracts._validation import canonical_json_bytes, sha256_bytes
from .diagnostics import aggregate_results, summarize_values
from .experiment import verify_run
from .protocol import PROTOCOL_VERSION, SEEDS, candidate_grid

CORE_FOLD_ARTIFACTS = (
    "selected_model.json", "diagnostics.json", "inner_selection.json", "state_alignment.json",
    "transform.json", "outer_filtered.csv", "outer_density.csv",
)


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _jsonl(path):
    lines = Path(path).read_bytes().splitlines()
    if any(not line for line in lines):
        raise ValueError(f"blank JSONL record in {path}")
    return [json.loads(line) for line in lines]


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def _csv(frame):
    return frame.to_csv(index=False, lineterminator="\n").encode("ascii")


def _candidate_key(record):
    return (record["fold_id"], record.get("inner_fold_id"), record["candidate_id"], record["seed"])


def verify_coverage(root):
    """Check complete rectangular inner evidence and one recorded selected outer refit."""
    outer_manifest = json.loads((root / "outer_fold_manifest.json").read_text())
    protocol = json.loads((root / "protocol_manifest.json").read_text())
    attempts = _jsonl(root / "candidate_fits.jsonl")
    selections = _jsonl(root / "inner_selection_records.jsonl")
    diagnostics = _jsonl(root / "fold_diagnostics.jsonl")
    alignments = _jsonl(root / "state_alignments.jsonl")
    folds = outer_manifest["folds"]
    fold_by_id = {fold["fold_id"]: fold for fold in folds}
    inner_by_outer = outer_manifest["inner_folds"]
    expected_inner = {
        (outer["fold_id"], inner["inner_fold_id"], candidate["candidate_id"], seed): (outer, inner)
        for outer in folds for inner in inner_by_outer[outer["fold_id"]]
        for candidate in protocol["candidate_grid"] for seed in protocol["seeds"]
    }
    actual_inner = {_candidate_key(record): record for record in attempts if record["role"] == "inner"}
    errors = []
    if len(actual_inner) != sum(record["role"] == "inner" for record in attempts):
        errors.append("duplicate inner fit identifiers")
    missing = sorted(set(expected_inner) - set(actual_inner))
    unexpected = sorted(set(actual_inner) - set(expected_inner))
    if missing:
        errors.append(f"missing {len(missing)} declared inner attempts")
    if unexpected:
        errors.append(f"found {len(unexpected)} undeclared inner attempts")
    selected_by_fold = {record["fold_id"]: record for record in selections}
    if len(selected_by_fold) != len(selections) or set(selected_by_fold) != set(fold_by_id):
        errors.append("selection records are not unique and complete")
    outer_attempts = [record for record in attempts if record["role"] == "outer_refit"]
    expected_outer = {fold_id for fold_id, record in selected_by_fold.items() if record["status"] == "selected"}
    actual_outer = {record["fold_id"] for record in outer_attempts}
    if len(outer_attempts) != len(actual_outer) or actual_outer != expected_outer:
        errors.append("outer-refit records do not match selected folds")
    for key, record in actual_inner.items():
        if key not in expected_inner:
            continue
        outer, inner = expected_inner[key]
        transform = record["transform"]
        if not (transform["train_end"] == inner["train_end"] < inner["validation_start"]
                and inner["validation_end"] <= outer["train_end"]):
            errors.append(f"inner chronology violation: {record['fit_id']}")
        if "evaluation_start" in record and (record["evaluation_start"], record["evaluation_end"]) != (
                inner["validation_start"], inner["validation_end"]):
            errors.append(f"inner evaluation boundary mismatch: {record['fit_id']}")
        if record["status"] == "accepted" and "evaluation_start" not in record:
            errors.append(f"accepted inner attempt lacks evaluation boundaries: {record['fit_id']}")
        if record["outer_test_used_for_selection"] is not False:
            errors.append(f"outer-test flag violation: {record['fit_id']}")
    for record in outer_attempts:
        outer = fold_by_id[record["fold_id"]]
        selection = selected_by_fold[record["fold_id"]]
        if (record["candidate_id"], record["seed"]) != (selection["selected_candidate_id"], selection["selected_seed"]):
            errors.append(f"outer refit differs from inner decision: {record['fit_id']}")
        if record["transform"]["train_end"] != outer["train_end"]:
            errors.append(f"outer training boundary violation: {record['fit_id']}")
        if "evaluation_start" in record and (record["evaluation_start"], record["evaluation_end"]) != (
                outer["test_start"], outer["test_end"]):
            errors.append(f"outer chronology violation: {record['fit_id']}")
        if record["status"] == "accepted" and "evaluation_start" not in record:
            errors.append(f"accepted outer attempt lacks evaluation boundaries: {record['fit_id']}")
    if len({record["fit_id"] for record in attempts}) != len(attempts):
        errors.append("duplicate fit identifiers")
    density_keys = {}
    for record in attempts:
        if record["role"] == "inner" and record["status"] == "accepted":
            density_keys.setdefault((record["fold_id"], record["inner_fold_id"]), set()).add(
                json.dumps(record["raw_density_comparison_key"], sort_keys=True))
    if any(len(keys) != 1 for keys in density_keys.values()):
        errors.append("incompatible raw-density comparison keys within an inner fold")
    accepted_diagnostics = [record for record in diagnostics if record["status"] == "accepted"]
    if len(diagnostics) != len(folds) or len(alignments) != len(accepted_diagnostics):
        errors.append("fold diagnostic/alignment coverage mismatch")
    expected_attempts = len(expected_inner) + len(expected_outer)
    if len(attempts) != expected_attempts:
        errors.append(f"expected {expected_attempts} attempts, found {len(attempts)}")
    if errors:
        raise ValueError("Task 4 coverage verification failed: " + "; ".join(errors[:12]))
    status_counts = Counter(record["status"] for record in attempts)
    convergence_counts = Counter(str(record["converged"]) for record in attempts)
    rejection_counts = Counter(record["rejection_reason"] for record in attempts if record["rejection_reason"])
    failure_counts = Counter(record["failure_reason"] for record in attempts if record["failure_reason"])
    return {
        "schema": "task4-coverage-verification-v1", "verified": True,
        "expected_attempts": expected_attempts, "actual_attempts": len(attempts),
        "expected_inner_attempts": len(expected_inner), "actual_inner_attempts": len(actual_inner),
        "expected_outer_refit_attempts": len(expected_outer), "actual_outer_refit_attempts": len(outer_attempts),
        "outer_folds": len(folds), "accepted_fold_diagnostics": len(accepted_diagnostics),
        "selection_records": len(selections), "alignment_records": len(alignments),
        "candidate_fit_status_counts": dict(status_counts), "converged_counts": dict(convergence_counts),
        "rejection_reason_counts": {str(key): value for key, value in rejection_counts.items()},
        "failure_reason_counts": {str(key): value for key, value in failure_counts.items()},
        "all_inner_attempts_have_three_complete_temporal_blocks": True,
        "raw_density_contracts_compatible_within_each_inner_fold": True,
        "outer_test_used_for_selection": False,
        "failed_rejected_and_nonconverged_records_retained": True,
        "unique_fit_ids": len({record["fit_id"] for record in attempts}) == len(attempts),
    }


def model_path_and_seed_sensitivity(selections):
    ordered = sorted((record for record in selections if record["status"] == "selected"), key=lambda row: row["fold_id"])
    path, seed_rows = [], []
    previous = None
    for record in ordered:
        candidate = record["selected_candidate_id"]
        seed = record["selected_seed"]
        path.append({
            "fold_id": record["fold_id"], "selected_candidate_id": candidate, "selected_seed": seed,
            "previous_candidate_id": previous["selected_candidate_id"] if previous else "",
            "previous_seed": previous["selected_seed"] if previous else "",
            "candidate_changed": bool(previous and candidate != previous["selected_candidate_id"]),
            "seed_changed": bool(previous and seed != previous["selected_seed"]),
            "mean_inner_raw_log_density_per_observation": record["mean_inner_raw_log_density_per_observation"],
        })
        winners = {}
        for declared_seed in SEEDS:
            scores = {candidate_id: values[str(declared_seed)] for candidate_id, values in record["seed_scores"].items()
                      if str(declared_seed) in values}
            winner = min(scores, key=lambda item: (-scores[item], item))
            winners[declared_seed] = winner
            seed_rows.append({
                "fold_id": record["fold_id"], "seed": declared_seed, "counterfactual_single_seed_winner": winner,
                "winner_mean_inner_raw_log_density_per_observation": scores[winner],
                "matches_multi_seed_selected_candidate": winner == candidate,
                "is_protocol_selected_seed": declared_seed == seed,
            })
        path[-1]["single_seed_winners_all_agree"] = len(set(winners.values())) == 1
        previous = record
    episodes = []
    for row in path:
        if not episodes or episodes[-1]["selected_candidate_id"] != row["selected_candidate_id"]:
            episodes.append({"selected_candidate_id": row["selected_candidate_id"], "start_fold_id": row["fold_id"],
                             "end_fold_id": row["fold_id"], "folds": 1})
        else:
            episodes[-1]["end_fold_id"] = row["fold_id"]
            episodes[-1]["folds"] += 1
    lengths = [episode["folds"] for episode in episodes]
    summary = {
        "selected_folds": len(path), "candidate_changes": sum(row["candidate_changed"] for row in path),
        "candidate_change_fraction_of_adjacent_pairs": (sum(row["candidate_changed"] for row in path) / (len(path) - 1)
                                                        if len(path) > 1 else None),
        "seed_changes": sum(row["seed_changed"] for row in path), "candidate_persistence_episodes": episodes,
        "candidate_persistence_fold_lengths": summarize_values(lengths),
        "folds_where_all_single_seed_winners_agree": sum(row["single_seed_winners_all_agree"] for row in path),
        "single_seed_winner_match_count": sum(row["matches_multi_seed_selected_candidate"] for row in seed_rows),
        "single_seed_winner_match_denominator": len(seed_rows),
        "counterfactual_note": "Single-seed winners are descriptive reuse of inner scores, not alternate outer refits or protocol changes.",
    }
    return path, seed_rows, summary


def candidate_rankings(selections):
    rows = []
    for selection in sorted(selections, key=lambda row: row["fold_id"]):
        if selection["status"] != "selected":
            continue
        ranked = sorted(selection["candidate_scores"], key=lambda item: (-selection["candidate_scores"][item], item))
        for rank, candidate in enumerate(ranked, 1):
            rows.append({"fold_id": selection["fold_id"], "candidate_id": candidate, "rank": rank,
                         "mean_inner_raw_log_density_per_observation": selection["candidate_scores"][candidate],
                         "selected": candidate == selection["selected_candidate_id"]})
    return rows


def occupancy_and_episodes(root, diagnostics):
    occupancy, episodes = [], []
    diagnostic_by_fold = {record["fold_id"]: record for record in diagnostics if record["status"] == "accepted"}
    for fold_id, record in sorted(diagnostic_by_fold.items()):
        selection = record["selection"]
        alignment = record["alignment"]["current_to_aligned"]
        for sample, key in (("training", "training_state_metrics"), ("outer_test", "outer_state_metrics")):
            for state in record[key]["states"]:
                local = state["local_state_id"]
                occupancy.append({"fold_id": fold_id, "sample": sample, "candidate_id": selection["selected_candidate_id"],
                                  "selected_seed": selection["selected_seed"], "local_state_id": local,
                                  "aligned_state_id": alignment.get(local) or "", "hard_count": state["hard_count"],
                                  "hard_fraction": state["hard_fraction"], "posterior_weight": state["posterior_weight"],
                                  "effective_sample_size": state["effective_sample_size"], "rare": state["rare"]})
        filtered = pd.read_csv(root / "folds" / fold_id / "outer_filtered.csv", dtype={"hard_aligned_state_id": str})
        filtered["hard_aligned_state_id"] = filtered["hard_aligned_state_id"].fillna("")
        start = 0
        for index in range(1, len(filtered) + 1):
            changed = index == len(filtered)
            if not changed:
                changed = (filtered.at[index, "hard_local_state_id"] != filtered.at[start, "hard_local_state_id"]
                           or filtered.at[index, "hard_aligned_state_id"] != filtered.at[start, "hard_aligned_state_id"])
            if changed:
                episodes.append({"fold_id": fold_id, "candidate_id": selection["selected_candidate_id"],
                                 "local_state_id": filtered.at[start, "hard_local_state_id"],
                                 "aligned_state_id": filtered.at[start, "hard_aligned_state_id"],
                                 "start_date": filtered.at[start, "Date"], "end_date": filtered.at[index - 1, "Date"],
                                 "duration_sessions": index - start})
                start = index
    return occupancy, episodes


def alignment_summary(alignments):
    subsequent = [record for record in alignments if record["reference_fold_id"] is not None]
    states = [item for record in alignments for item in record["records"]]
    subsequent_states = [item for record in subsequent for item in record["records"]]
    return {
        "initial_folds": len(alignments) - len(subsequent), "subsequent_fold_pairs": len(subsequent),
        "all_state_status_counts": dict(Counter(item["status"] for item in states)),
        "subsequent_state_status_counts": dict(Counter(item["status"] for item in subsequent_states)),
        "agreement_distribution": summarize_values(record["agreement"] for record in subsequent),
        "unmatched_frequency_distribution": summarize_values(record["unmatched_frequency"] for record in subsequent),
        "accepted_state_distance_distribution": summarize_values(
            item["distance"] for item in subsequent_states if item["status"] == "accepted"),
        "ambiguous_states_not_forced": all(item["aligned_state_id"] is None for item in subsequent_states
                                           if item["status"] == "ambiguous"),
        "outer_test_used_for_alignment": False,
        "label_note": "Aligned IDs are structural references, not semantic regime names; unmatched/ambiguous states remain distinct or blank.",
    }


def compare_with_preserved_run(root, preserved):
    comparisons = []
    root_folds = {path.name for path in (root / "folds").iterdir() if path.is_dir()}
    preserved_folds = {path.name for path in (preserved / "folds").iterdir() if path.is_dir()}
    for fold_id in sorted(root_folds | preserved_folds):
        for name in CORE_FOLD_ARTIFACTS:
            current_path = root / "folds" / fold_id / name
            preserved_path = preserved / "folds" / fold_id / name
            current = current_path.read_bytes() if current_path.is_file() else None
            previous = preserved_path.read_bytes() if preserved_path.is_file() else None
            comparisons.append({"fold_id": fold_id, "artifact": name, "current_present": current is not None,
                                "preserved_present": previous is not None, "byte_identical": current == previous,
                                "current_sha256": hashlib.sha256(current).hexdigest() if current is not None else None,
                                "preserved_sha256": hashlib.sha256(previous).hexdigest() if previous is not None else None})
    selections = {record["fold_id"]: record for record in _jsonl(root / "inner_selection_records.jsonl")}
    diagnostics = {record["fold_id"]: record for record in _jsonl(root / "fold_diagnostics.jsonl")}
    alignments = {record["fold_id"]: record for record in _jsonl(root / "state_alignments.jsonl")}
    object_checks = []
    for fold_id in sorted(root_folds & preserved_folds):
        for name, current in (("inner_selection.json", selections.get(fold_id)),
                              ("diagnostics.json", diagnostics.get(fold_id)),
                              ("state_alignment.json", alignments.get(fold_id))):
            previous = json.loads((preserved / "folds" / fold_id / name).read_text())
            object_checks.append({"fold_id": fold_id, "artifact": name, "object_identical": current == previous})
    return {
        "schema": "task4-reproducibility-comparison-v1", "recovery_run": str(root), "preserved_run": str(preserved),
        "comparison_type": "independent executions of unchanged numerical protocol; engineering-only persistence fix between runs",
        "fold_sets_identical": root_folds == preserved_folds, "core_artifact_comparisons": comparisons,
        "global_fold_object_comparisons": object_checks,
        "all_core_artifacts_byte_identical": all(item["byte_identical"] for item in comparisons),
        "all_global_fold_objects_identical": all(item["object_identical"] for item in object_checks),
        "candidate_attempt_comparison_available": False,
        "candidate_attempt_comparison_note": "The initial process lost in-memory global attempt records during final aggregation; recovery coverage is checked independently.",
        "manifest_exceptions": ["source.commit", "execution timestamps"],
        "initial_run_status": "failed_after_fold_artifacts_not_a_completed_experiment",
    }


def analyze_run(run_dir, output_dir, comparison_run=None):
    root = Path(run_dir).resolve()
    run_manifest = verify_run(root)
    if run_manifest["status"] != "completed" or run_manifest["protocol_version"] != PROTOCOL_VERSION:
        raise ValueError("analysis requires a completed run of the frozen protocol")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = _utc()
    coverage = verify_coverage(root)
    attempts = _jsonl(root / "candidate_fits.jsonl")
    selections = _jsonl(root / "inner_selection_records.jsonl")
    diagnostics = _jsonl(root / "fold_diagnostics.jsonl")
    alignments = _jsonl(root / "state_alignments.jsonl")
    aggregate = aggregate_results(diagnostics, attempts, selections, alignments)
    if aggregate != json.loads((root / "aggregate_results.json").read_text()):
        raise ValueError("stored aggregate results do not reproduce from persisted records")
    path, seed_rows, path_summary = model_path_and_seed_sensitivity(selections)
    rankings = candidate_rankings(selections)
    occupancy, episodes = occupancy_and_episodes(root, diagnostics)
    outer_occupancy = [row for row in occupancy if row["sample"] == "outer_test"]
    lengths = [row["duration_sessions"] for row in episodes]
    by_candidate = {}
    for candidate in sorted({row["candidate_id"] for row in episodes}):
        values = [row["duration_sessions"] for row in episodes if row["candidate_id"] == candidate]
        by_candidate[candidate] = summarize_values(values)
    stability = {
        "schema": "task4-stability-analysis-v1", "model_path": path_summary,
        "alignment": alignment_summary(alignments),
        "outer_occupancy": {
            "fold_state_rows": len(outer_occupancy), "rare_fold_state_rows": sum(row["rare"] for row in outer_occupancy),
            "zero_hard_assignment_fold_state_rows": sum(row["hard_count"] == 0 for row in outer_occupancy),
            "rare_fold_state_row_fraction": (sum(row["rare"] for row in outer_occupancy) / len(outer_occupancy)
                                               if outer_occupancy else None),
            "rare_rule": "Task 2 hard_count < 100 and hard_fraction < 0.05; descriptive, not a new selection rule",
        },
        "outer_hard_state_durations": {
            "all_episodes": summarize_values(lengths),
            "one_session_episode_fraction": (sum(value == 1 for value in lengths) / len(lengths) if lengths else None),
            "by_candidate": by_candidate,
            "boundary_note": "Episodes are computed within each annual outer test only; local state IDs are never joined naively across fold boundaries.",
        },
        "statistical_scope": aggregate["interpretation"], "no_significance_or_economic_claim": True,
    }
    payloads = {
        "coverage_verification.json": canonical_json_bytes(coverage),
        "selected_model_path.csv": _csv(pd.DataFrame(path)),
        "candidate_rankings.csv": _csv(pd.DataFrame(rankings)),
        "seed_sensitivity.csv": _csv(pd.DataFrame(seed_rows)),
        "state_occupancy.csv": _csv(pd.DataFrame(occupancy)),
        "state_episodes.csv": _csv(pd.DataFrame(episodes)),
        "stability_analysis.json": canonical_json_bytes(stability),
    }
    if comparison_run is not None:
        comparison = compare_with_preserved_run(root, Path(comparison_run).resolve())
        payloads["reproducibility_comparison.json"] = canonical_json_bytes(comparison)
    for name, payload in payloads.items():
        _write(output / name, payload)
    artifacts = {name: sha256_bytes(payload) for name, payload in payloads.items()}
    manifest = {
        "schema": "task4-analysis-manifest-v1", "protocol_version": PROTOCOL_VERSION,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_run": str(root), "source_run_manifest_sha256": hashlib.sha256((root / "run_manifest.json").read_bytes()).hexdigest(),
        "comparison_run": str(Path(comparison_run).resolve()) if comparison_run is not None else None,
        "execution": {"command": "python -m research.discovery.analysis", "started_utc": started, "finished_utc": _utc()},
        "artifacts": artifacts, "status": "completed",
        "warnings": ["Derived descriptive reports only; no candidate was reselected and no protocol threshold was changed."],
    }
    _write(output / "analysis_manifest.json", canonical_json_bytes(manifest))
    checksums = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                        for path in sorted(output.iterdir()) if path.is_file())
    _write(output / "SHA256SUMS", checksums.encode("ascii"))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--comparison-run")
    args = parser.parse_args()
    manifest = analyze_run(args.run, args.output_dir, args.comparison_run)
    print(json.dumps({"status": manifest["status"], "output": args.output_dir,
                      "artifacts": len(manifest["artifacts"])}, indent=2))


if __name__ == "__main__":
    main()
