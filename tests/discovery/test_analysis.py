from __future__ import annotations

import json

import pandas as pd
import pytest

from research.discovery.analysis import (candidate_rankings, compare_with_preserved_run, model_path_and_seed_sensitivity,
                                         occupancy_and_episodes, verify_coverage, CORE_FOLD_ARTIFACTS)
from research.discovery.protocol import SEEDS, candidate_grid, protocol_dict


def _selection(fold, candidate="k2_gaussian_diag", seed=2):
    other = "k3_student_t_diag" if candidate == "k2_gaussian_diag" else "k2_gaussian_diag"
    return {"fold_id": fold, "status": "selected", "selected_candidate_id": candidate, "selected_seed": seed,
            "mean_inner_raw_log_density_per_observation": 2.0, "candidate_scores": {candidate: 2.0, other: 1.0},
            "seed_scores": {candidate: {str(value): 2.0 + value / 100 for value in SEEDS},
                            other: {str(value): 1.0 + value / 100 for value in SEEDS}}}


def test_model_path_and_counterfactual_seed_summary():
    selections = [_selection("outer_2020"), _selection("outer_2021"),
                  _selection("outer_2022", "k3_student_t_diag", 42)]
    path, seed_rows, summary = model_path_and_seed_sensitivity(selections)
    assert [row["candidate_changed"] for row in path] == [False, False, True]
    assert summary["candidate_changes"] == 1 and summary["seed_changes"] == 1
    assert summary["candidate_persistence_episodes"][0]["folds"] == 2
    assert summary["single_seed_winner_match_count"] == len(seed_rows)
    assert summary["folds_where_all_single_seed_winners_agree"] == 3
    assert candidate_rankings(selections)[0]["rank"] == 1


def test_occupancy_and_fold_local_episode_durations(tmp_path):
    fold = tmp_path / "folds" / "outer_2020"
    fold.mkdir(parents=True)
    pd.DataFrame({"Date": pd.date_range("2020-01-01", periods=5).strftime("%Y-%m-%d"),
                  "hard_local_state_id": ["local_0", "local_0", "local_1", "local_1", "local_1"],
                  "hard_aligned_state_id": ["a", "a", "b", "", ""]}).to_csv(fold / "outer_filtered.csv", index=False)
    states = [{"local_state_id": "local_0", "hard_count": 2, "hard_fraction": 0.4,
               "posterior_weight": 0.4, "effective_sample_size": 2.0, "rare": True},
              {"local_state_id": "local_1", "hard_count": 3, "hard_fraction": 0.6,
               "posterior_weight": 0.6, "effective_sample_size": 3.0, "rare": False}]
    diagnostic = {"fold_id": "outer_2020", "status": "accepted",
                  "selection": {"selected_candidate_id": "k2_gaussian_diag", "selected_seed": 2},
                  "alignment": {"current_to_aligned": {"local_0": "a", "local_1": None}},
                  "training_state_metrics": {"states": states}, "outer_state_metrics": {"states": states}}
    occupancy, episodes = occupancy_and_episodes(tmp_path, [diagnostic])
    assert len(occupancy) == 4
    assert [row["duration_sessions"] for row in episodes] == [2, 1, 2]
    assert episodes[-1]["aligned_state_id"] == ""


def test_rectangular_coverage_and_temporal_contracts(tmp_path):
    outer = {"fold_id": "outer_2020", "train_start": "2018-01-01", "train_end": "2019-12-31",
             "test_start": "2020-01-01", "test_end": "2020-12-31", "train_rows": 500, "test_rows": 200}
    inners = []
    for index in range(3):
        inners.append({"inner_fold_id": f"inner_{index}", "train_start": "2018-01-01",
                       "train_end": f"2019-0{index + 1}-01", "validation_start": f"2019-0{index + 1}-02",
                       "validation_end": f"2019-0{index + 1}-03"})
    (tmp_path / "outer_fold_manifest.json").write_text(json.dumps(
        {"folds": [outer], "inner_folds": {"outer_2020": inners}}))
    (tmp_path / "protocol_manifest.json").write_text(json.dumps(protocol_dict()))
    attempts = []
    for inner in inners:
        for candidate in candidate_grid():
            for seed in SEEDS:
                attempts.append({"fit_id": f"{inner['inner_fold_id']}-{candidate.candidate_id}-{seed}",
                                 "fold_id": "outer_2020", "inner_fold_id": inner["inner_fold_id"], "role": "inner",
                                 "candidate_id": candidate.candidate_id, "seed": seed, "status": "accepted",
                                 "converged": True, "rejection_reason": None, "failure_reason": None,
                                 "transform": {"train_end": inner["train_end"]},
                                 "evaluation_start": inner["validation_start"], "evaluation_end": inner["validation_end"],
                                 "outer_test_used_for_selection": False, "raw_density_comparison_key": ["raw", "jacobian"]})
    attempts.append({"fit_id": "outer", "fold_id": "outer_2020", "inner_fold_id": None, "role": "outer_refit",
                     "candidate_id": "k2_gaussian_diag", "seed": 2, "status": "accepted", "converged": True,
                     "rejection_reason": None, "failure_reason": None, "transform": {"train_end": outer["train_end"]},
                     "evaluation_start": outer["test_start"], "evaluation_end": outer["test_end"],
                     "outer_test_used_for_selection": False})
    for name, records in (("candidate_fits.jsonl", attempts),
                          ("inner_selection_records.jsonl", [_selection("outer_2020")]),
                          ("fold_diagnostics.jsonl", [{"fold_id": "outer_2020", "status": "accepted"}]),
                          ("state_alignments.jsonl", [{"fold_id": "outer_2020", "status": "accepted"}])):
        (tmp_path / name).write_text("".join(json.dumps(record) + "\n" for record in records))
    result = verify_coverage(tmp_path)
    assert result["verified"] and result["actual_attempts"] == 109
    assert result["expected_inner_attempts"] == 108


def test_preserved_run_comparison_is_byte_exact(tmp_path):
    current = tmp_path / "current"
    preserved = tmp_path / "preserved"
    for root in (current, preserved):
        fold = root / "folds" / "outer_2020"
        fold.mkdir(parents=True)
        for name in CORE_FOLD_ARTIFACTS:
            payload = json.dumps({"fold_id": "outer_2020"}) if name.endswith(".json") else name
            (fold / name).write_text(payload)
        for name in ("inner_selection_records.jsonl", "fold_diagnostics.jsonl", "state_alignments.jsonl"):
            (root / name).write_text(json.dumps({"fold_id": "outer_2020"}) + "\n")
    result = compare_with_preserved_run(current, preserved)
    assert result["fold_sets_identical"]
    assert result["all_core_artifacts_byte_identical"]
    assert len(result["core_artifact_comparisons"]) == len(CORE_FOLD_ARTIFACTS)
    assert not result["candidate_attempt_comparison_available"]
