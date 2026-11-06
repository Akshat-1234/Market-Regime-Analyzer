from __future__ import annotations
import json
import numpy as np
from research.contracts.experiment import verify_experiment
from research.discovery.alignment import build_state_profiles, initial_alignment
from research.discovery.data import load_feature_data
from research.discovery.diagnostics import block_metrics, transition_metrics
from research.discovery.experiment import _fold_artifacts, _utc, fit_attempt
from research.discovery.protocol import candidate_grid
from research.hmm.serialization import load_model


def test_fold_artifact_manifest_integrity_and_reproducible_rerun(tmp_path, synthetic_features, synthetic_outer, fast_numerics):
    candidate = candidate_grid()[0]
    train = synthetic_features.loc[synthetic_outer.train_start:synthetic_outer.train_end]
    test = synthetic_features.loc[synthetic_outer.test_start:synthetic_outer.test_end]
    record, _, payload = fit_attempt(candidate, 2, train, test, synthetic_outer, role="outer_refit")
    assert record["status"] == "accepted" and record["numerical_settings"]["n_iter"] == 5
    result, transform, raw = payload
    selection = {"schema": "task4-inner-selection-v1", "fold_id": synthetic_outer.fold_id, "status": "selected",
                 "selected_candidate_id": candidate.candidate_id, "state_count": 2, "emission": "gaussian",
                 "covariance_type": "diag", "selected_seed": 2, "mean_inner_raw_log_density_per_observation": 0.0,
                 "validation_fold_ids": ["synthetic_inner"], "eligible_candidates": [candidate.candidate_id],
                 "candidate_scores": {candidate.candidate_id: 0.0}, "seed_scores": {candidate.candidate_id: {"2": 0.0}},
                 "selected_candidate_seed_scores": {"2": 0.0}, "outer_test_used": False}
    profiles = build_state_profiles(synthetic_outer.fold_id, train, result.record.training_filtered)
    alignment = initial_alignment(profiles).as_dict()
    train_metrics = block_metrics(result.record.training_filtered, train)
    outer_metrics = block_metrics(result.record.oos_filtered, test)
    transitions = transition_metrics(result.model, result.record.training_assignments)
    data_manifest = load_feature_data()[1]
    diagnostics, _ = _fold_artifacts(tmp_path / "first", synthetic_outer, selection, result, transform, raw,
                                     alignment, data_manifest, "3f9d7a49745044b5ba270a4b2a886cf292f944e1", _utc(),
                                     train, test, candidate, train_metrics, outer_metrics, transitions)
    fold_dir = tmp_path / "first/folds" / synthetic_outer.fold_id
    manifest = verify_experiment(fold_dir)
    assert manifest["source"]["commit"] == "3f9d7a49745044b5ba270a4b2a886cf292f944e1"
    assert manifest["dataset"]["raw_sha256"] == data_manifest["dataset"]["raw_sha256"]
    assert len(manifest["artifacts"]) == 7 and diagnostics["outer_density"]["jacobian_included"]
    loaded = load_model(fold_dir / "selected_model.json")
    x = transform.apply(test)
    np.testing.assert_array_equal(loaded.model.filter(x, result.final_log_alpha)[0],
                                  result.record.oos_filtered.probabilities)
    _fold_artifacts(tmp_path / "second", synthetic_outer, selection, result, transform, raw,
                    alignment, data_manifest, "3f9d7a49745044b5ba270a4b2a886cf292f944e1", _utc(),
                    train, test, candidate, train_metrics, outer_metrics, transitions)
    second_dir = tmp_path / "second/folds" / synthetic_outer.fold_id
    verify_experiment(second_dir)
    for name in ("selected_model.json", "diagnostics.json", "inner_selection.json", "state_alignment.json",
                 "transform.json", "outer_filtered.csv", "outer_density.csv"):
        assert (fold_dir / name).read_bytes() == (second_dir / name).read_bytes()
    original = (fold_dir / "diagnostics.json").read_bytes()
    (fold_dir / "diagnostics.json").write_bytes(original + b" ")
    try:
        verify_experiment(fold_dir)
    except ValueError as exc:
        assert "hash" in str(exc)
    else:
        raise AssertionError("artifact tampering was not detected")


def test_protocol_manifest_has_no_outer_results_and_declares_nonclaims():
    from research.discovery.protocol import protocol_dict
    protocol = protocol_dict()
    assert protocol["selection"]["outer_test_used"] is False
    assert protocol["alignment"]["outer_test_used"] is False
    assert len(protocol["candidate_grid"]) == 12 and protocol["seeds"] == [2, 42, 7]
    assert protocol["inner_folds"]["validation_rows"] == 126
    assert "outer_results" not in protocol and protocol["boundary_sensitivity"]
    json.dumps(protocol, allow_nan=False)
