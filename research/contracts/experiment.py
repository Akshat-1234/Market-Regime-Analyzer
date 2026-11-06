"""Immutable experiment directories and machine-verifiable provenance manifests."""
from __future__ import annotations

from copy import deepcopy
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import pandas as pd

from ._validation import as_timestamp, canonical_json_bytes, require_sha256, sha256_bytes
from .model import FitStatus

EXPERIMENT_SCHEMA_VERSION = "task2-experiment-manifest-v1"
_REQUIRED = {"schema_version", "experiment_id", "source", "dataset", "feature_spec",
             "model_spec", "folds", "seeds", "dependencies", "execution", "artifacts",
             "warnings", "fit_records", "status"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _utc_text(value: Any, field: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO UTC timestamp")
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO UTC timestamp") from exc
    if pd.isna(stamp) or stamp.tzinfo is None or stamp.utcoffset() != pd.Timedelta(0):
        raise ValueError(f"{field} must be an explicit UTC timestamp")


def _safe_artifact_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("artifact paths must be nonempty POSIX-relative strings")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError("artifact paths cannot be absolute, noncanonical, or traverse directories")
    return path.as_posix()


def validate_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a defensive manifest copy without mutating the input."""
    _mapping(manifest, "manifest")
    missing = sorted(_REQUIRED - set(manifest))
    if missing:
        raise ValueError("manifest missing required fields: " + ", ".join(missing))
    if manifest["schema_version"] != EXPERIMENT_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {EXPERIMENT_SCHEMA_VERSION}")
    experiment_id = manifest["experiment_id"]
    if not isinstance(experiment_id, str) or not _ID.fullmatch(experiment_id) or experiment_id == "LATEST":
        raise ValueError("experiment_id must be an immutable safe identifier, not LATEST")

    source = _mapping(manifest["source"], "source")
    commit = source.get("commit")
    inventory = source.get("source_inventory_sha256")
    if commit is None and inventory is None:
        raise ValueError("source requires a full commit or source_inventory_sha256")
    if commit is not None and (not isinstance(commit, str) or not _COMMIT.fullmatch(commit)):
        raise ValueError("source.commit must be a full lowercase Git commit")
    if inventory is not None:
        require_sha256(inventory, "source.source_inventory_sha256")

    dataset = _mapping(manifest["dataset"], "dataset")
    require_sha256(dataset.get("raw_sha256"), "dataset.raw_sha256")
    require_sha256(dataset.get("parsed_sha256"), "dataset.parsed_sha256")
    if not isinstance(dataset.get("rows"), int) or dataset["rows"] < 1:
        raise ValueError("dataset.rows must be a positive integer")

    feature = _mapping(manifest["feature_spec"], "feature_spec")
    if not feature.get("family") or not feature.get("version"):
        raise ValueError("feature_spec requires family and version")
    columns = feature.get("columns")
    if (not isinstance(columns, list) or not columns or
            any(not isinstance(column, str) or not column for column in columns) or
            len(set(columns)) != len(columns)):
        raise ValueError("feature_spec.columns must be a nonempty ordered unique list")

    model = _mapping(manifest["model_spec"], "model_spec")
    for field in ("name", "model_version", "emission", "covariance_type", "transformation"):
        if not isinstance(model.get(field), str) or not model[field]:
            raise ValueError(f"model_spec.{field} must be nonempty")
    if model.get("feature_version") != feature["version"]:
        raise ValueError("model_spec.feature_version must match feature_spec.version")
    if model.get("feature_names") != columns:
        raise ValueError("model_spec.feature_names must exactly match ordered feature_spec.columns")
    if isinstance(model.get("state_count"), bool) or not isinstance(model.get("state_count"), int) or model["state_count"] < 2:
        raise ValueError("model_spec.state_count must be an integer >= 2")
    if isinstance(model.get("seed"), bool) or not isinstance(model.get("seed"), int) or model["seed"] < 0:
        raise ValueError("model_spec.seed must be a nonnegative integer")

    folds = manifest["folds"]
    if not isinstance(folds, list) or not folds:
        raise ValueError("folds must be a nonempty list")
    fold_ids = set()
    previous_test_end = None
    for position, fold_value in enumerate(folds):
        fold = _mapping(fold_value, f"folds[{position}]")
        fold_id = fold.get("fold_id")
        if not isinstance(fold_id, str) or not fold_id or fold_id in fold_ids:
            raise ValueError("fold IDs must be nonempty and unique")
        fold_ids.add(fold_id)
        stamps = {name: as_timestamp(fold.get(name), f"folds[{position}].{name}")
                  for name in ("train_start", "train_end", "test_start", "test_end")}
        if not stamps["train_start"] <= stamps["train_end"] < stamps["test_start"] <= stamps["test_end"]:
            raise ValueError("fold dates violate train_end < test_start")
        if previous_test_end is not None and stamps["test_start"] <= previous_test_end:
            raise ValueError("fold test windows must be chronological and nonoverlapping")
        previous_test_end = stamps["test_end"]

    seeds = manifest["seeds"]
    if (not isinstance(seeds, list) or not seeds or
            any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds) or
            model["seed"] not in seeds):
        raise ValueError("seeds must be nonnegative integers and include model_spec.seed")
    dependencies = _mapping(manifest["dependencies"], "dependencies")
    if not dependencies or any(not isinstance(name, str) or not isinstance(version, str) or not version
                               for name, version in dependencies.items()):
        raise ValueError("dependencies must map package names to explicit versions")

    execution = _mapping(manifest["execution"], "execution")
    if not execution.get("command") or not execution.get("python"):
        raise ValueError("execution requires command and python")
    _utc_text(execution.get("started_utc"), "execution.started_utc")
    status = manifest["status"]
    if status not in {"running", "completed", "partial", "failed"}:
        raise ValueError("status must be running, completed, partial, or failed")
    _utc_text(execution.get("finished_utc"), "execution.finished_utc", optional=True)
    if status == "completed" and execution.get("finished_utc") is None:
        raise ValueError("completed experiments require finished_utc")

    artifacts = _mapping(manifest["artifacts"], "artifacts")
    for name, digest in artifacts.items():
        _safe_artifact_path(name)
        require_sha256(digest, f"artifacts[{name!r}]")
    if status == "completed" and not artifacts:
        raise ValueError("completed experiments require at least one declared artifact")

    warnings = manifest["warnings"]
    if not isinstance(warnings, list) or any(not isinstance(warning, str) for warning in warnings):
        raise ValueError("warnings must be a list of strings")
    fit_records = manifest["fit_records"]
    if not isinstance(fit_records, list):
        raise ValueError("fit_records must be a list")
    unsuccessful = False
    for position, record_value in enumerate(fit_records):
        record = _mapping(record_value, f"fit_records[{position}]")
        if not record.get("fit_id") or record.get("fold_id") not in fold_ids:
            raise ValueError("fit records require fit_id and a declared fold_id")
        try:
            fit_status = FitStatus(record.get("status"))
        except ValueError as exc:
            raise ValueError("fit record has invalid status") from exc
        if fit_status is FitStatus.ACCEPTED and record.get("converged") is not True:
            raise ValueError("accepted fit records require converged=true")
        if fit_status is not FitStatus.ACCEPTED:
            unsuccessful = True
            if not record.get("reason"):
                raise ValueError("unsuccessful fit records require an explicit reason")
    if status == "failed" and not warnings:
        raise ValueError("failed experiments require a recorded warning/failure")
    if unsuccessful and status == "completed" and not warnings:
        raise ValueError("completed experiments with rejected/failed fits require warnings")
    return deepcopy(dict(manifest))


def create_experiment(base_dir: str | Path, manifest: Mapping[str, Any],
                      artifacts: Mapping[str, bytes]) -> Path:
    """Create one immutable run directory; never overwrite or update LATEST."""
    clean = validate_manifest(manifest)
    declared = clean["artifacts"]
    if set(declared) != set(artifacts):
        raise ValueError("artifact payload names must exactly match manifest declarations")
    for name, payload in artifacts.items():
        if not isinstance(payload, bytes):
            raise ValueError("artifact payloads must be bytes")
        if sha256_bytes(payload) != declared[name]:
            raise ValueError(f"artifact hash mismatch before writing: {name}")
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    run_dir = base / clean["experiment_id"]
    run_dir.mkdir(exist_ok=False)  # collision protection: no exist_ok overwrite
    for name, payload in artifacts.items():
        destination = run_dir.joinpath(*PurePosixPath(name).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write(payload)
    with (run_dir / "manifest.json").open("xb") as handle:
        handle.write(canonical_json_bytes(clean))
    return run_dir


def verify_experiment(run_dir: str | Path) -> dict[str, Any]:
    """Verify schema, declared hashes, missing files, and unrecorded regular files."""
    import json

    root = Path(run_dir)
    with (root / "manifest.json").open("r", encoding="utf-8") as handle:
        manifest = validate_manifest(json.load(handle))
    actual_files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    declared_files = set(manifest["artifacts"]) | {"manifest.json"}
    if actual_files != declared_files:
        raise ValueError(f"experiment file set mismatch: actual={sorted(actual_files)}, declared={sorted(declared_files)}")
    for name, digest in manifest["artifacts"].items():
        path = root.joinpath(*PurePosixPath(name).parts)
        if not path.is_file() or sha256_bytes(path.read_bytes()) != digest:
            raise ValueError(f"missing or hash-mismatched artifact: {name}")
    return manifest


def record_failure(manifest: Mapping[str, Any], message: str, finished_utc: str) -> dict[str, Any]:
    """Return a failed manifest copy; failures never become silent successes."""
    clean = validate_manifest(manifest)
    if not message:
        raise ValueError("failure message must be nonempty")
    _utc_text(finished_utc, "finished_utc")
    clean["status"] = "failed"
    clean["execution"]["finished_utc"] = finished_utc
    clean["warnings"] = [*clean["warnings"], f"failure: {message}"]
    return validate_manifest(clean)
