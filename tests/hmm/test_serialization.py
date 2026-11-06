from __future__ import annotations
import json
import numpy as np
import pandas as pd
import pytest
from research.hmm.config import EMConfig
from research.hmm.serialization import ENGINE_VERSION, load_model, save_model


def save_fixture(tmp_path, diag_fit, make_spec, name="model.json"):
    path = tmp_path / name
    digest = save_model(path, diag_fit, make_spec(), EMConfig(2, seed=7), "2020-01-01", "2020-02-01")
    return path, digest


def test_round_trip_preserves_parameters_configuration_and_inference(tmp_path, diag_fit, make_spec):
    path, digest = save_fixture(tmp_path, diag_fit, make_spec)
    loaded = load_model(path)
    assert loaded.payload_sha256 == digest and loaded.spec == make_spec() and loaded.config.seed == 7
    assert loaded.training_start == pd.Timestamp("2020-01-01") and loaded.training_end == pd.Timestamp("2020-02-01")
    for name in ("startprob", "transmat", "means", "covars"):
        np.testing.assert_array_equal(getattr(loaded.model, name), getattr(diag_fit, name))
    x = np.random.default_rng(1).normal(size=(10, 2))
    np.testing.assert_array_equal(loaded.model.filter(x)[0], diag_fit.filter(x)[0])
    np.testing.assert_array_equal(loaded.model.predictive_loglik(x)[1], diag_fit.predictive_loglik(x)[1])


def test_serialization_is_deterministic(tmp_path, diag_fit, make_spec):
    first, first_hash = save_fixture(tmp_path, diag_fit, make_spec, "first.json")
    second, second_hash = save_fixture(tmp_path, diag_fit, make_spec, "second.json")
    assert first_hash == second_hash and first.read_bytes() == second.read_bytes()


def test_payload_corruption_fails_hash_verification(tmp_path, diag_fit, make_spec):
    path, _ = save_fixture(tmp_path, diag_fit, make_spec)
    artifact = json.loads(path.read_text())
    artifact["payload"]["parameters"]["means"][0][0] += 1
    path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match="payload hash mismatch"):
        load_model(path)


def test_invalid_json_and_missing_metadata_fail_closed(tmp_path, diag_fit, make_spec):
    path, _ = save_fixture(tmp_path, diag_fit, make_spec)
    path.write_text("not json")
    with pytest.raises(ValueError, match="invalid HMM JSON"):
        load_model(path)
    path, _ = save_fixture(tmp_path, diag_fit, make_spec, "missing.json")
    artifact = json.loads(path.read_text())
    del artifact["payload"]["numerical_settings"]
    artifact["payload_sha256"] = "0" * 64
    path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match="payload hash mismatch"):
        load_model(path)


def test_engine_schema_and_source_version_mismatches_are_rejected(tmp_path, diag_fit, make_spec):
    for index, (field, value) in enumerate([("engine_version", "other"), ("schema_version", "other"), ("source_version", "other")]):
        path, _ = save_fixture(tmp_path, diag_fit, make_spec, f"version-{index}.json")
        artifact = json.loads(path.read_text())
        artifact[field] = value
        path.write_text(json.dumps(artifact))
        with pytest.raises(ValueError, match="mismatch|unsupported"):
            load_model(path)


def test_overwrite_collision_is_rejected(tmp_path, diag_fit, make_spec):
    path, _ = save_fixture(tmp_path, diag_fit, make_spec)
    with pytest.raises(FileExistsError):
        save_model(path, diag_fit, make_spec(), EMConfig(2, seed=7), "2020-01-01", "2020-02-01")


def test_unfitted_or_nonfinite_model_cannot_be_serialized(tmp_path, diag_fit, make_spec):
    from research.hmm.parameters import HMMFit
    values = diag_fit.parameter_dict()
    values.pop("dof")
    unfitted = HMMFit(**values, seed=diag_fit.seed)
    with pytest.raises(ValueError, match="fitted model"):
        save_model(tmp_path / "bad.json", unfitted, make_spec(), EMConfig(2, seed=7), "2020-01-01", "2020-02-01")


def test_valid_hash_but_missing_nested_metadata_is_rejected(tmp_path, diag_fit, make_spec):
    from research.contracts._validation import canonical_json_bytes, sha256_bytes
    path, _ = save_fixture(tmp_path, diag_fit, make_spec)
    artifact = json.loads(path.read_text())
    del artifact["payload"]["dependencies"]
    artifact["payload_sha256"] = sha256_bytes(canonical_json_bytes(artifact["payload"]))
    path.write_bytes(canonical_json_bytes(artifact))
    with pytest.raises(ValueError, match="missing model/training/numerical"):
        load_model(path)


def test_valid_hash_does_not_authorize_scalar_type_coercion(tmp_path, diag_fit, make_spec):
    from research.contracts._validation import canonical_json_bytes, sha256_bytes
    path, _ = save_fixture(tmp_path, diag_fit, make_spec)
    artifact = json.loads(path.read_text())
    artifact["payload"]["convergence"]["converged"] = "false"
    artifact["payload_sha256"] = sha256_bytes(canonical_json_bytes(artifact["payload"]))
    path.write_bytes(canonical_json_bytes(artifact))
    with pytest.raises(ValueError, match="JSON boolean"):
        load_model(path)


def test_loaded_version_compatibility_can_be_explicitly_checked(tmp_path, diag_fit, make_spec):
    path, _ = save_fixture(tmp_path, diag_fit, make_spec)
    with pytest.raises(ValueError, match="version mismatch"):
        load_model(path, expected_engine_version=ENGINE_VERSION + "-next")
