"""Safe deterministic JSON model artifacts with payload hashes and version checks."""
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
from .parameters import HMMFit

MODEL_SCHEMA = "task3-hmm-model-v1"
ENGINE_VERSION = "task3-hmm-engine-v1"
SOURCE_VERSION = "1c-emhmm-c46541e9ab8611330489a920c46cdb00342931d5"

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


def _dependencies():
    return {"python": platform.python_version(), "numpy": version("numpy"),
            "scipy": version("scipy"), "scikit-learn": version("scikit-learn")}


def _validate_dependencies(dependencies: Mapping[str, str]):
    values = dict(dependencies)
    required = {"python", "numpy", "scipy", "scikit-learn"}
    if (not required.issubset(values) or any(not isinstance(key, str) or not isinstance(value, str) or not value
                                             for key, value in values.items())):
        raise ValueError("dependencies must contain nonempty python/numpy/scipy/scikit-learn versions")
    return values


def save_model(path, model, spec, config, training_start, training_end, *, dependencies=None, state_ids=None):
    """Write one deterministic JSON artifact in exclusive-create mode."""
    if (not isinstance(model, HMMFit) or not np.isfinite(model.loglik) or model.n_iter < 1 or
            len(model.history) != model.n_iter):
        raise ValueError("serialization requires a fitted model with finite likelihood and complete history")
    if (config.n_states != spec.state_count or config.seed != spec.seed or
            config.emission != spec.emission or config.covariance_type != spec.covariance_type or
            model.n_states != spec.state_count or model.n_features != len(spec.feature_names)):
        raise ValueError("model, config, and ModelSpec dimensions/configuration disagree")
    start = pd.Timestamp(training_start)
    end = pd.Timestamp(training_end)
    if start.tzinfo is not None or end.tzinfo is not None or start != start.normalize() or end != end.normalize() or end < start:
        raise ValueError("training dates must be ordered timezone-naive session dates")
    ids = tuple(state_ids) if state_ids is not None else tuple(f"state_{i}" for i in range(spec.state_count))
    if (len(ids) != spec.state_count or len(set(ids)) != len(ids) or
            any(not isinstance(item, str) or not item for item in ids)):
        raise ValueError("state_ids must be nonempty unique strings and match state_count")
    payload = {
        "model_spec": asdict(spec), "numerical_settings": asdict(config), "parameters": model.parameter_dict(),
        "training": {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")},
        "state_ids": list(ids),
        "convergence": {"log_likelihood": model.loglik, "iterations": model.n_iter,
                        "converged": model.converged, "history": list(model.history),
                        "regularization_events": model.regularization_events,
                        "criterion": "abs(history[-1]-history[-2]) < tol * max(1, abs(history[-1]))"},
        "dependencies": _validate_dependencies(dependencies if dependencies is not None else _dependencies())}
    digest = sha256_bytes(canonical_json_bytes(payload))
    artifact = {"schema_version": MODEL_SCHEMA, "engine_version": ENGINE_VERSION,
                "source_version": SOURCE_VERSION, "payload_sha256": digest, "payload": payload}
    with Path(path).open("xb") as handle:
        handle.write(canonical_json_bytes(artifact))
    return digest


def load_model(path, *, expected_engine_version=ENGINE_VERSION):
    """Load only validated JSON data; never deserialize executable objects."""
    try:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid HMM JSON artifact") from exc
    required = {"schema_version", "engine_version", "source_version", "payload_sha256", "payload"}
    if not isinstance(artifact, dict) or not required.issubset(artifact):
        raise ValueError("HMM artifact is missing required version/payload metadata")
    if artifact["schema_version"] != MODEL_SCHEMA:
        raise ValueError(f"unsupported HMM artifact schema: {artifact['schema_version']}")
    if artifact["engine_version"] != expected_engine_version:
        raise ValueError(f"HMM engine version mismatch: {artifact['engine_version']}")
    if artifact["source_version"] != SOURCE_VERSION:
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
        required_convergence = {"log_likelihood", "iterations", "converged", "history", "regularization_events", "criterion"}
        if not isinstance(convergence, dict) or not required_convergence.issubset(convergence):
            raise ValueError("incomplete convergence diagnostics")
        if type(convergence["converged"]) is not bool:
            raise ValueError("converged must be a JSON boolean")
        for key in ("iterations", "regularization_events"):
            if type(convergence[key]) is not int or convergence[key] < 0:
                raise ValueError(f"{key} must be a nonnegative JSON integer")
        if type(convergence["log_likelihood"]) not in {int, float} or not np.isfinite(convergence["log_likelihood"]):
            raise ValueError("serialized log_likelihood must be finite and numeric")
        if (not isinstance(convergence["history"], list) or convergence["iterations"] < 1 or
                len(convergence["history"]) != convergence["iterations"]):
            raise ValueError("serialized iteration/history metadata disagree")
        _validate_dependencies(payload["dependencies"])
        spec_data = dict(payload["model_spec"])
        spec_data["feature_names"] = tuple(spec_data["feature_names"])
        spec = ModelSpec(**spec_data)
        config = EMConfig(**payload["numerical_settings"])
        parameters = payload["parameters"]
        model = HMMFit(startprob=np.asarray(parameters["startprob"], dtype=float),
                       transmat=np.asarray(parameters["transmat"], dtype=float),
                       means=np.asarray(parameters["means"], dtype=float),
                       covars=np.asarray(parameters["covars"], dtype=float),
                       covariance_type=parameters["covariance_type"], emission=parameters["emission"],
                       dof=parameters["dof"], loglik=float(convergence["log_likelihood"]),
                       n_iter=int(convergence["iterations"]), converged=bool(convergence["converged"]),
                       history=list(convergence["history"]), seed=spec.seed,
                       regularization_events=int(convergence["regularization_events"]))
        training = payload["training"]
        start = pd.Timestamp(training["start"])
        end = pd.Timestamp(training["end"])
        ids = tuple(payload["state_ids"])
        dependencies = dict(payload["dependencies"])
    except ValueError:
        raise
    except (KeyError, TypeError) as exc:
        raise ValueError("invalid HMM model metadata or parameters") from exc
    if (model.n_states != spec.state_count or model.n_features != len(spec.feature_names) or
            config.n_states != spec.state_count or config.seed != spec.seed or
            config.emission != spec.emission or config.covariance_type != spec.covariance_type):
        raise ValueError("serialized model/config/spec dimensions disagree")
    if (len(ids) != spec.state_count or len(set(ids)) != len(ids) or
            any(not isinstance(item, str) or not item for item in ids) or end < start or
            start.tzinfo is not None or end.tzinfo is not None or
            start != start.normalize() or end != end.normalize()):
        raise ValueError("invalid serialized state IDs or training boundary")
    return LoadedModel(model, spec, config, start, end, ids, dependencies, actual)
