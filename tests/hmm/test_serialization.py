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


def rehash_artifact(path):
    """Give a semantically invalid payload a valid canonical integrity hash."""
    from research.contracts._validation import canonical_json_bytes, sha256_bytes
    artifact = json.loads(path.read_text())
    artifact["payload_sha256"] = sha256_bytes(canonical_json_bytes(artifact["payload"]))
    path.write_bytes(canonical_json_bytes(artifact))
    return artifact


@pytest.mark.parametrize("attribute,value", [("emission", "student_t"), ("covariance_type", "full"), ("seed", 8)])
def test_save_rejects_model_spec_config_mismatch(attribute, value, tmp_path, diag_fit, make_spec):
    from copy import deepcopy
    model = deepcopy(diag_fit)
    setattr(model, attribute, value)
    with pytest.raises(ValueError):
        save_model(tmp_path / "mismatch.json", model, make_spec(), EMConfig(2, seed=7), "2020-01-01", "2020-02-01")


def test_save_rejects_spec_and_config_contradictions(tmp_path, diag_fit, make_spec):
    with pytest.raises(ValueError, match="emissions disagree"):
        save_model(tmp_path / "spec.json", diag_fit, make_spec(emission="student_t"),
                   EMConfig(2, seed=7), "2020-01-01", "2020-02-01")
    with pytest.raises(ValueError, match="covariance types disagree"):
        save_model(tmp_path / "config.json", diag_fit, make_spec(),
                   EMConfig(2, covariance_type="full", seed=7), "2020-01-01", "2020-02-01")


def save_student_fixture(tmp_path, student_fit, make_spec, initial_dof=6.0, name="student.json"):
    path = tmp_path / name
    save_model(path, student_fit, make_spec(emission="student_t"),
               EMConfig(2, emission="student_t", dof=initial_dof, seed=7), "2020-01-01", "2020-02-01")
    return path


def test_student_t_initial_and_profiled_final_dof_may_differ(tmp_path, student_fit, make_spec):
    path = save_student_fixture(tmp_path, student_fit, make_spec, initial_dof=8.0)
    loaded = load_model(path)
    assert loaded.config.dof == 8.0 and loaded.model.dof == 6.0
    assert loaded.model.converged


def test_valid_hash_student_t_dof_metadata_mismatch_is_rejected(tmp_path, student_fit, make_spec):
    path = save_student_fixture(tmp_path, student_fit, make_spec)
    artifact = json.loads(path.read_text())
    artifact["payload"]["convergence"]["degrees_of_freedom"]["fitted"] = 9.0
    path.write_text(json.dumps(artifact))
    rehash_artifact(path)
    with pytest.raises(ValueError, match="dof metadata disagree"):
        load_model(path)


def test_gaussian_student_t_metadata_is_rejected_on_save_and_load(tmp_path, diag_fit, make_spec):
    from copy import deepcopy
    model = deepcopy(diag_fit)
    model.dof = 6.0
    with pytest.raises(ValueError, match="Gaussian artifacts"):
        save_model(tmp_path / "gaussian-dof.json", model, make_spec(),
                   EMConfig(2, dof=6.0, seed=7), "2020-01-01", "2020-02-01")
    path, _ = save_fixture(tmp_path, diag_fit, make_spec)
    artifact = json.loads(path.read_text())
    artifact["payload"]["parameters"]["dof"] = 6.0
    artifact["payload"]["numerical_settings"]["dof"] = 6.0
    artifact["payload"]["convergence"]["degrees_of_freedom"].update(initial=6.0, fitted=6.0)
    path.write_text(json.dumps(artifact))
    rehash_artifact(path)
    with pytest.raises(ValueError, match="Gaussian artifacts"):
        load_model(path)


def test_valid_hash_semantic_parameter_and_identifier_defects_are_rejected(tmp_path, diag_fit, make_spec):
    cases = [
        ("invalid-covariance", lambda p: p["parameters"].update(covars=[[0.5]])),
        ("invalid-transition", lambda p: p["parameters"].update(transmat=[[0.9, 0.2], [0.2, 0.8]])),
        ("invalid-start", lambda p: p["parameters"].update(startprob=[0.7, 0.4])),
        ("nonfinite-means", lambda p: p["parameters"]["means"][0].__setitem__(0, "NaN")),
        ("invalid-state-ids", lambda p: p.update(state_ids=["same", "same"])),
        ("model-emission", lambda p: p["parameters"].update(emission="student_t", dof=6.0)),
        ("model-seed", lambda p: p["convergence"].update(fitted_seed=8)),
        ("spec-count", lambda p: p["model_spec"].update(state_count=3)),
        ("config-emission", lambda p: p["numerical_settings"].update(emission="student_t", dof=6.0)),
    ]
    for name, mutate in cases:
        path, _ = save_fixture(tmp_path, diag_fit, make_spec, name + ".json")
        artifact = json.loads(path.read_text())
        mutate(artifact["payload"])
        path.write_text(json.dumps(artifact))
        rehash_artifact(path)
        with pytest.raises(ValueError):
            load_model(path)


def test_valid_hash_invalid_convergence_and_regularization_are_rejected(tmp_path, diag_fit, make_spec):
    path, _ = save_fixture(tmp_path, diag_fit, make_spec, "convergence.json")
    artifact = json.loads(path.read_text())
    artifact["payload"]["convergence"]["converged"] = False
    path.write_text(json.dumps(artifact))
    rehash_artifact(path)
    with pytest.raises(ValueError, match="nonconverged metadata"):
        load_model(path)
    path, _ = save_fixture(tmp_path, diag_fit, make_spec, "regularization.json")
    artifact = json.loads(path.read_text())
    artifact["payload"]["convergence"]["regularization_applications"] = 1
    path.write_text(json.dumps(artifact))
    rehash_artifact(path)
    with pytest.raises(ValueError, match="regularization_applications"):
        load_model(path)


def test_legacy_v1_round_trip_is_strict_and_numerically_identical(tmp_path, diag_fit, make_spec):
    path, _ = save_fixture(tmp_path, diag_fit, make_spec, "legacy.json")
    artifact = json.loads(path.read_text())
    artifact["schema_version"] = "task3-hmm-model-v1"
    artifact["engine_version"] = "task3-hmm-engine-v1"
    artifact["payload"]["model_spec"]["model_version"] = "task3-hmm-engine-v1"
    convergence = artifact["payload"]["convergence"]
    for key in ("regularization_applications", "diagonal_variance_floor_hits",
                "eigenvalue_clipping_events", "full_covariance_floor_applications",
                "fitted_seed", "degrees_of_freedom"):
        del convergence[key]
    path.write_text(json.dumps(artifact))
    rehash_artifact(path)
    loaded = load_model(path)
    assert loaded.artifact_schema == "task3-hmm-model-v1" and loaded.engine_version == "task3-hmm-engine-v1"
    x = np.random.default_rng(14).normal(size=(8, 2))
    np.testing.assert_array_equal(loaded.model.filter(x)[0], diag_fit.filter(x)[0])


def test_full_covariance_detailed_diagnostics_round_trip(tmp_path, full_fit, make_spec):
    from dataclasses import replace
    model = replace(full_fit, loglik=-10.0, n_iter=1, converged=False, history=[-10.0],
                    regularization_events=2, regularization_applications=2,
                    full_covariance_floor_applications=2)
    path = tmp_path / "full.json"
    save_model(path, model, make_spec(covariance="full", seed=3),
               EMConfig(2, covariance_type="full", n_iter=1, seed=3), "2020-01-01", "2020-02-01")
    loaded = load_model(path)
    assert loaded.model.full_covariance_floor_applications == 2
    assert loaded.model.eigenvalue_clipping_events == 0
    assert loaded.model.regularization_events == 2
