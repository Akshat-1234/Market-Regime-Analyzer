"""Safe deterministic JSON artifacts with semantic and version validation.

Schema v2 records fitted/initial Student-t dof separately and disaggregates
regularization diagnostics. Schema v1 remains loadable through a strict legacy
compatibility path; a payload hash never substitutes for semantic validation.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from importlib.metadata import version
import json
from pathlib import Path
import platform
from typing import Mapping
import numpy as np
import pandas as pd
from research.contracts._validation import canonical_json_bytes, require_sha256, sha256_bytes
from research.contracts.model import ModelSpec
from .config import EMConfig
from .parameters import HMMFit, HMMParameters, RegularizationDiagnostics
from .version import ENGINE_VERSION, LEGACY_ENGINE_VERSION, SOURCE_COMMIT

MODEL_SCHEMA = "task3-hmm-model-v2"
LEGACY_MODEL_SCHEMA = "task3-hmm-model-v1"
SOURCE_VERSION = f"1c-emhmm-{SOURCE_COMMIT}"
CONVERGENCE_CRITERION = "abs(history[-1]-history[-2]) < tol * max(1, abs(history[-1]))"
DOF_SEMANTICS = "config_initial_model_profiled_final"
_COUNTER_NAMES = ("regularization_applications", "diagonal_variance_floor_hits",
                  "eigenvalue_clipping_events", "full_covariance_floor_applications")


@dataclass
class LoadedModel:
    model: HMMFit
    spec: ModelSpec
    config: EMConfig
    training_start: pd.Timestamp
    training_end: pd.Timestamp
    state_ids: tuple[str, ...]
    dependencies: dict[str, str]
    payload_sha256: str
    artifact_schema: str
    engine_version: str


def _dependencies():
    return {"python": platform.python_version(), "numpy": version("numpy"),
            "scipy": version("scipy"), "scikit-learn": version("scikit-learn")}


def _validate_dependencies(dependencies: Mapping[str, str]):
    if not isinstance(dependencies, Mapping):
        raise ValueError("dependencies must be an object")
    values = dict(dependencies)
    required = {"python", "numpy", "scipy", "scikit-learn"}
    if (not required.issubset(values) or any(not isinstance(key, str) or not isinstance(value, str)
                                             or not value.strip() for key, value in values.items())):
        raise ValueError("dependencies must contain nonempty python/numpy/scipy/scikit-learn versions")
    return values


def _strict_int(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _finite_number(value, name):
    if type(value) not in {int, float} or not np.isfinite(value):
        raise ValueError(f"{name} must be finite and numeric")
    return float(value)


def _json_finite_array(value, name):
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    for item in value:
        if isinstance(item, list):
            _json_finite_array(item, name)
        else:
            _finite_number(item, name)


def _validate_state_ids(state_ids, state_count):
    if not isinstance(state_ids, (list, tuple)):
        raise ValueError("state_ids must be an array of nonempty unique strings")
    ids = tuple(state_ids)
    if (len(ids) != state_count or len(set(ids)) != len(ids) or
            any(not isinstance(item, str) or not item.strip() for item in ids)):
        raise ValueError("state_ids must be nonempty unique strings and match state_count")
    return ids


def _training_boundaries(training_start, training_end, *, serialized=False):
    if serialized and (not isinstance(training_start, str) or not isinstance(training_end, str)):
        raise ValueError("serialized training dates must be ISO date strings")
    try:
        start = pd.Timestamp(training_start)
        end = pd.Timestamp(training_end)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid training dates") from exc
    if (start.tzinfo is not None or end.tzinfo is not None or start != start.normalize()
            or end != end.normalize() or end < start):
        raise ValueError("training dates must be ordered timezone-naive session dates")
    if serialized and (start.strftime("%Y-%m-%d") != training_start
                       or end.strftime("%Y-%m-%d") != training_end):
        raise ValueError("serialized training dates must use exact YYYY-MM-DD form")
    return start, end


def _regularization_for_model(model):
    values = {name: getattr(model, name) for name in _COUNTER_NAMES}
    for name, value in values.items():
        _strict_int(value, name)
    diagnostics = RegularizationDiagnostics(**values)
    _strict_int(model.regularization_events, "regularization_events")
    if model.regularization_events != diagnostics.legacy_events:
        raise ValueError("regularization_events must retain the legacy aggregate meaning")
    if model.covariance_type == "diag":
        if diagnostics.full_covariance_floor_applications or diagnostics.eigenvalue_clipping_events:
            raise ValueError("diagonal covariance cannot contain full-covariance diagnostics")
        expected = RegularizationDiagnostics(
            regularization_applications=diagnostics.diagonal_variance_floor_hits,
            diagonal_variance_floor_hits=diagnostics.diagonal_variance_floor_hits)
        if diagnostics != expected:
            raise ValueError("inconsistent diagonal regularization diagnostics")
    else:
        if diagnostics.diagonal_variance_floor_hits:
            raise ValueError("full covariance cannot contain diagonal variance floor hits")
        expected_full = model.n_iter * model.n_states
        if diagnostics.full_covariance_floor_applications != expected_full:
            raise ValueError("full-covariance floor applications must equal iterations times states")
        expected = RegularizationDiagnostics(
            regularization_applications=expected_full + diagnostics.eigenvalue_clipping_events,
            eigenvalue_clipping_events=diagnostics.eigenvalue_clipping_events,
            full_covariance_floor_applications=expected_full)
        if diagnostics != expected:
            raise ValueError("inconsistent full-covariance regularization diagnostics")
    return diagnostics


def _validate_convergence(model, config):
    _strict_int(model.n_iter, "n_iter", 1)
    if model.n_iter > config.n_iter:
        raise ValueError("fitted iterations exceed the declared configuration cap")
    if type(model.converged) is not bool:
        raise ValueError("converged must be an explicit boolean")
    _finite_number(model.loglik, "loglik")
    if not isinstance(model.history, (list, tuple)) or len(model.history) != model.n_iter:
        raise ValueError("fitted iteration/history metadata disagree")
    for value in model.history:
        _finite_number(value, "history")
    criterion_met = False
    if model.n_iter >= 2:
        criterion_met = bool(abs(model.history[-1] - model.history[-2])
                             < config.tol * max(1.0, abs(model.history[-1])))
    if model.converged and (model.n_iter < 2 or not criterion_met):
        raise ValueError("converged metadata does not satisfy the declared history criterion")
    if not model.converged and (model.n_iter != config.n_iter or criterion_met):
        raise ValueError("nonconverged metadata must exhaust the cap without meeting the criterion")


def _validate_semantics(model, spec, config, engine_version):
    """Validate the complete model/config/spec relationship on save and load."""
    if not isinstance(model, HMMFit) or not isinstance(spec, ModelSpec) or not isinstance(config, EMConfig):
        raise ValueError("serialization requires HMMFit, ModelSpec, and EMConfig instances")
    # Reconstructing the base value object revalidates all array dimensions,
    # probabilities, finite values, covariance shapes, and emission constraints.
    HMMParameters(np.asarray(model.startprob), np.asarray(model.transmat), np.asarray(model.means),
                  np.asarray(model.covars), model.covariance_type, model.emission, model.dof)
    _strict_int(model.seed, "model.seed")
    if not (model.n_states == spec.state_count == config.n_states):
        raise ValueError("model, config, and ModelSpec state counts disagree")
    if model.n_features != len(spec.feature_names):
        raise ValueError("model and ModelSpec feature dimensions disagree")
    if not (model.covariance_type == spec.covariance_type == config.covariance_type):
        raise ValueError("model, config, and ModelSpec covariance types disagree")
    if not (model.emission == spec.emission == config.emission):
        raise ValueError("model, config, and ModelSpec emissions disagree")
    if not (model.seed == spec.seed == config.seed):
        raise ValueError("model, config, and ModelSpec seeds disagree")
    if spec.model_version != engine_version:
        raise ValueError("ModelSpec.model_version must match the artifact engine version")
    if model.emission == "student_t":
        if config.dof is None or not np.isfinite(config.dof) or config.dof <= 2:
            raise ValueError("Student-t initial configuration dof must be finite and > 2")
        if model.dof is None or not np.isfinite(model.dof) or model.dof <= 2:
            raise ValueError("Student-t fitted dof must be finite and > 2")
        # Equality is deliberately not required: config.dof is the initial value;
        # the original EM may profile a different final value on its fixed grid.
    elif model.dof is not None or config.dof is not None:
        raise ValueError("Gaussian artifacts cannot contain Student-t dof metadata")
    _validate_convergence(model, config)
    return _regularization_for_model(model)


def save_model(path, model, spec, config, training_start, training_end, *, dependencies=None, state_ids=None):
    """Write one semantically validated deterministic JSON artifact."""
    if isinstance(model, HMMFit) and model.n_iter < 1:
        raise ValueError("serialization requires a fitted model with complete convergence history")
    diagnostics = _validate_semantics(model, spec, config, ENGINE_VERSION)
    start, end = _training_boundaries(training_start, training_end)
    ids = _validate_state_ids(state_ids if state_ids is not None else
                              [f"state_{i}" for i in range(spec.state_count)], spec.state_count)
    convergence = {
        "log_likelihood": model.loglik, "iterations": model.n_iter,
        "converged": model.converged, "history": list(model.history),
        "regularization_events": model.regularization_events,
        **diagnostics.as_dict(), "criterion": CONVERGENCE_CRITERION,
        "fitted_seed": model.seed,
        "degrees_of_freedom": {"initial": config.dof, "fitted": model.dof,
                               "semantics": DOF_SEMANTICS}}
    payload = {
        "model_spec": asdict(spec), "numerical_settings": asdict(config), "parameters": model.parameter_dict(),
        "training": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")},
        "state_ids": list(ids), "convergence": convergence,
        "dependencies": _validate_dependencies(dependencies if dependencies is not None else _dependencies())}
    digest = sha256_bytes(canonical_json_bytes(payload))
    artifact = {"schema_version": MODEL_SCHEMA, "engine_version": ENGINE_VERSION,
                "source_version": SOURCE_VERSION, "payload_sha256": digest, "payload": payload}
    with Path(path).open("xb") as handle:
        handle.write(canonical_json_bytes(artifact))
    return digest


def _legacy_diagnostics(model):
    legacy = model.regularization_events
    if model.covariance_type == "diag":
        return RegularizationDiagnostics(regularization_applications=legacy,
                                         diagonal_variance_floor_hits=legacy)
    full_applications = model.n_iter * model.n_states
    clipped = legacy - full_applications
    if clipped < 0:
        raise ValueError("legacy full-covariance regularization aggregate is inconsistent")
    return RegularizationDiagnostics(regularization_applications=legacy,
                                     eigenvalue_clipping_events=clipped,
                                     full_covariance_floor_applications=full_applications)


def load_model(path, *, expected_engine_version=None):
    """Load v1/v2 JSON data, checking both integrity and complete semantics."""
    try:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid HMM JSON artifact") from exc
    required = {"schema_version", "engine_version", "source_version", "payload_sha256", "payload"}
    if not isinstance(artifact, dict) or not required.issubset(artifact):
        raise ValueError("HMM artifact is missing required version/payload metadata")
    schema = artifact["schema_version"]
    engine = artifact["engine_version"]
    supported = {(MODEL_SCHEMA, ENGINE_VERSION), (LEGACY_MODEL_SCHEMA, LEGACY_ENGINE_VERSION)}
    if (schema, engine) not in supported:
        raise ValueError("unsupported or contradictory HMM schema/engine version")
    if expected_engine_version is not None and engine != expected_engine_version:
        raise ValueError(f"HMM engine version mismatch: {engine}")
    if artifact["source_version"] != SOURCE_VERSION or SOURCE_COMMIT != SOURCE_VERSION.rsplit("-", 1)[-1]:
        raise ValueError("HMM source lineage mismatch")
    require_sha256(artifact["payload_sha256"], "payload_sha256")
    payload = artifact["payload"]
    if not isinstance(payload, dict):
        raise ValueError("HMM payload must be an object")
    actual = sha256_bytes(canonical_json_bytes(payload))
    if actual != artifact["payload_sha256"]:
        raise ValueError("HMM artifact payload hash mismatch")
    needed = {"model_spec", "numerical_settings", "parameters", "training", "state_ids", "convergence", "dependencies"}
    if not needed.issubset(payload):
        raise ValueError("HMM payload is missing model/training/numerical metadata")
    try:
        convergence = payload["convergence"]
        required_convergence = {"log_likelihood", "iterations", "converged", "history",
                                "regularization_events", "criterion"}
        if schema == MODEL_SCHEMA:
            required_convergence |= {*_COUNTER_NAMES, "fitted_seed", "degrees_of_freedom"}
        if not isinstance(convergence, dict) or not required_convergence.issubset(convergence):
            raise ValueError("incomplete convergence diagnostics")
        if type(convergence["converged"]) is not bool:
            raise ValueError("converged must be a JSON boolean")
        _strict_int(convergence["iterations"], "iterations", 1)
        _strict_int(convergence["regularization_events"], "regularization_events")
        _finite_number(convergence["log_likelihood"], "log_likelihood")
        _json_finite_array(convergence["history"], "history")
        if convergence["criterion"] != CONVERGENCE_CRITERION:
            raise ValueError("unsupported convergence criterion")
        for name in _COUNTER_NAMES:
            if schema == MODEL_SCHEMA:
                _strict_int(convergence[name], name)
        dependencies = _validate_dependencies(payload["dependencies"])
        spec_data = dict(payload["model_spec"])
        spec_data["feature_names"] = tuple(spec_data["feature_names"])
        spec = ModelSpec(**spec_data)
        config = EMConfig(**payload["numerical_settings"])
        parameters = payload["parameters"]
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be an object")
        for name in ("startprob", "transmat", "means", "covars"):
            _json_finite_array(parameters[name], name)
        if parameters["dof"] is not None:
            _finite_number(parameters["dof"], "dof")
        fitted_seed = convergence["fitted_seed"] if schema == MODEL_SCHEMA else spec.seed
        _strict_int(fitted_seed, "fitted_seed")
        model = HMMFit(startprob=np.asarray(parameters["startprob"], dtype=float),
                       transmat=np.asarray(parameters["transmat"], dtype=float),
                       means=np.asarray(parameters["means"], dtype=float),
                       covars=np.asarray(parameters["covars"], dtype=float),
                       covariance_type=parameters["covariance_type"], emission=parameters["emission"],
                       dof=parameters["dof"], loglik=float(convergence["log_likelihood"]),
                       n_iter=convergence["iterations"], converged=convergence["converged"],
                       history=list(convergence["history"]), seed=fitted_seed,
                       regularization_events=convergence["regularization_events"],
                       **({name: convergence[name] for name in _COUNTER_NAMES}
                          if schema == MODEL_SCHEMA else {}))
        if schema == LEGACY_MODEL_SCHEMA:
            diagnostics = _legacy_diagnostics(model)
            for name, value in diagnostics.as_dict().items():
                setattr(model, name, value)
        else:
            dof_metadata = convergence["degrees_of_freedom"]
            if (not isinstance(dof_metadata, dict) or dof_metadata.get("semantics") != DOF_SEMANTICS
                    or dof_metadata.get("initial") != config.dof or dof_metadata.get("fitted") != model.dof):
                raise ValueError("initial/fitted Student-t dof metadata disagree with model/config")
            if dof_metadata.get("initial") is not None:
                _finite_number(dof_metadata["initial"], "initial dof")
            if dof_metadata.get("fitted") is not None:
                _finite_number(dof_metadata["fitted"], "fitted dof")
        training = payload["training"]
        start, end = _training_boundaries(training["start"], training["end"], serialized=True)
        ids = _validate_state_ids(payload["state_ids"], spec.state_count)
    except ValueError:
        raise
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("invalid HMM model metadata or parameters") from exc
    _validate_semantics(model, spec, config, engine)
    return LoadedModel(model, spec, config, start, end, ids, dependencies, actual, schema, engine)
