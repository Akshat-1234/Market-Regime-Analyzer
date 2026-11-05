from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from research.contracts.experiment import (EXPERIMENT_SCHEMA_VERSION, create_experiment,
                                           record_failure, validate_manifest, verify_experiment)


def payload() -> bytes:
    return b'{"observation":1}\n'


def manifest() -> dict:
    artifact = payload()
    return {
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "experiment_id": "synthetic_20261105T000000Z_deadbeef",
        "source": {"commit": "57ae0c238e497a059ce85f83da398477be705e8a",
                   "source_inventory_sha256": "1" * 64},
        "dataset": {"raw_sha256": "a" * 64, "parsed_sha256": "b" * 64, "rows": 12},
        "feature_spec": {"family": "rv", "version": "f10-close-features-v1",
                         "columns": ["daily_return", "volatility_20"]},
        "model_spec": {"name": "synthetic", "model_version": "fixture-model-v1",
                       "feature_version": "f10-close-features-v1",
                       "feature_names": ["daily_return", "volatility_20"], "state_count": 3,
                       "emission": "gaussian", "covariance_type": "diag",
                       "transformation": "training-zscore-with-raw-jacobian", "seed": 42},
        "folds": [{"fold_id": "fold_001", "train_start": "2020-01-01", "train_end": "2020-12-31",
                   "test_start": "2021-01-01", "test_end": "2021-01-08"}],
        "seeds": [2, 42],
        "dependencies": {"numpy": "2.4.6", "pandas": "2.3.3"},
        "execution": {"command": "pytest synthetic", "python": "3.11.2",
                      "started_utc": "2026-11-05T00:00:00Z", "finished_utc": "2026-11-05T00:00:01Z"},
        "artifacts": {"metrics/result.json": hashlib.sha256(artifact).hexdigest()},
        "warnings": [],
        "fit_records": [{"fit_id": "fit_001", "fold_id": "fold_001", "status": "accepted",
                         "converged": True}],
        "status": "completed",
    }


def test_complete_manifest_creates_immutable_verifiable_directory_without_latest(tmp_path):
    run = create_experiment(tmp_path / "experiments", manifest(), {"metrics/result.json": payload()})
    verified = verify_experiment(run)
    assert verified["experiment_id"] == manifest()["experiment_id"]
    assert not (run.parent / "LATEST").exists()
    assert json.loads((run / "manifest.json").read_text())["schema_version"] == EXPERIMENT_SCHEMA_VERSION


def test_incomplete_source_or_feature_model_identity_is_rejected():
    missing_source = manifest()
    missing_source["source"] = {}
    with pytest.raises(ValueError, match="source requires"):
        validate_manifest(missing_source)
    missing_fields = manifest()
    del missing_fields["dataset"]
    with pytest.raises(ValueError, match="missing required fields: dataset"):
        validate_manifest(missing_fields)
    mismatch = manifest()
    mismatch["model_spec"]["feature_names"] = list(reversed(mismatch["model_spec"]["feature_names"]))
    with pytest.raises(ValueError, match="exactly match"):
        validate_manifest(mismatch)


def test_manifest_hashes_and_fold_order_are_machine_checked():
    bad_hash = manifest()
    bad_hash["dataset"]["raw_sha256"] = "not-a-hash"
    with pytest.raises(ValueError, match="raw_sha256"):
        validate_manifest(bad_hash)
    bad_fold = manifest()
    bad_fold["folds"][0]["train_end"] = "2021-01-02"
    with pytest.raises(ValueError, match="train_end < test_start"):
        validate_manifest(bad_fold)


def test_output_collision_is_never_overwritten(tmp_path):
    base = tmp_path / "experiments"
    run = create_experiment(base, manifest(), {"metrics/result.json": payload()})
    original = (run / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        create_experiment(base, manifest(), {"metrics/result.json": payload()})
    assert (run / "manifest.json").read_bytes() == original


def test_undeclared_missing_or_hash_mismatched_artifacts_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="exactly match"):
        create_experiment(tmp_path / "missing", manifest(), {})
    with pytest.raises(ValueError, match="hash mismatch"):
        create_experiment(tmp_path / "bad", manifest(), {"metrics/result.json": b"changed"})
    run = create_experiment(tmp_path / "verify", manifest(), {"metrics/result.json": payload()})
    (run / "metrics/result.json").unlink()
    with pytest.raises(ValueError, match="file set mismatch"):
        verify_experiment(run)


def test_unrecorded_output_and_modified_artifact_are_detected(tmp_path):
    run = create_experiment(tmp_path / "experiments", manifest(), {"metrics/result.json": payload()})
    (run / "extra.txt").write_text("unrecorded")
    with pytest.raises(ValueError, match="file set mismatch"):
        verify_experiment(run)
    (run / "extra.txt").unlink()
    (run / "metrics/result.json").write_bytes(b"modified")
    with pytest.raises(ValueError, match="hash-mismatched"):
        verify_experiment(run)


def test_path_traversal_and_latest_identity_are_rejected():
    traversal = manifest()
    traversal["artifacts"] = {"../outside": "c" * 64}
    with pytest.raises(ValueError, match="traverse"):
        validate_manifest(traversal)
    latest = manifest()
    latest["experiment_id"] = "LATEST"
    with pytest.raises(ValueError, match="not LATEST"):
        validate_manifest(latest)


def test_failure_recording_does_not_become_success():
    failed = record_failure(manifest(), "synthetic optimizer error", "2026-11-05T00:01:00Z")
    assert failed["status"] == "failed"
    assert failed["warnings"][-1] == "failure: synthetic optimizer error"
    assert failed["experiment_id"] == manifest()["experiment_id"]
    bad_fit = manifest()
    bad_fit["fit_records"] = [{"fit_id": "fit_bad", "fold_id": "fold_001",
                               "status": "accepted", "converged": False}]
    with pytest.raises(ValueError, match="converged=true"):
        validate_manifest(bad_fit)


def test_rejected_fit_is_explicit_and_completed_run_carries_warning():
    value = manifest()
    value["fit_records"] = [{"fit_id": "fit_rejected", "fold_id": "fold_001",
                             "status": "rejected", "converged": False, "reason": "zero occupancy"}]
    value["warnings"] = ["one synthetic candidate rejected"]
    validated = validate_manifest(value)
    assert validated["fit_records"][0]["status"] == "rejected"
    value["warnings"] = []
    with pytest.raises(ValueError, match="require warnings"):
        validate_manifest(value)
