"""Typed model outputs, fit disposition, comparable density, and selection."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from ._validation import (as_timestamp, finite_number, validate_date_index,
                          validate_probability_matrix)


class InferenceKind(str, Enum):
    TRAINING_FILTERED = "training_filtered"
    FILTERED = "filtered"
    OOS_FILTERED = "oos_filtered"
    SMOOTHED = "smoothed"


class FitStatus(str, Enum):
    ACCEPTED = "accepted"
    NONCONVERGED = "nonconverged"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    model_version: str
    feature_family: str
    feature_version: str
    feature_names: tuple[str, ...]
    state_count: int
    emission: str
    covariance_type: str
    transformation: str
    seed: int

    def __post_init__(self) -> None:
        for field in ("name", "model_version", "feature_family", "feature_version",
                      "emission", "covariance_type", "transformation"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field).strip():
                raise ValueError(f"{field} must be a non-empty version/configuration value")
        object.__setattr__(self, "feature_names", tuple(self.feature_names))
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("feature_names must be non-empty, ordered, and unique")
        if isinstance(self.state_count, bool) or not isinstance(self.state_count, int) or self.state_count < 2:
            raise ValueError("state_count must be an integer >= 2")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")


@dataclass(frozen=True)
class ProbabilityBlock:
    dates: pd.DatetimeIndex
    probabilities: np.ndarray
    state_ids: tuple[str, ...]
    kind: InferenceKind

    def __post_init__(self) -> None:
        matrix = validate_probability_matrix(self.probabilities)
        dates = validate_date_index(self.dates, len(matrix))
        ids = tuple(self.state_ids)
        if len(ids) != matrix.shape[1] or len(set(ids)) != len(ids):
            raise ValueError("state_ids must be unique and match probability columns")
        if any(not isinstance(state_id, str) or not state_id for state_id in ids):
            raise ValueError("state_ids must be non-empty strings")
        object.__setattr__(self, "probabilities", matrix)
        object.__setattr__(self, "dates", dates)
        object.__setattr__(self, "state_ids", ids)
        object.__setattr__(self, "kind", InferenceKind(self.kind))

    @property
    def causal(self) -> bool:
        return self.kind is not InferenceKind.SMOOTHED


@dataclass(frozen=True)
class FitRecord:
    spec: ModelSpec
    status: FitStatus
    converged: bool
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    rejection_reason: str | None = None
    failure_reason: str | None = None
    fallback_used: bool = False
    parameters: Mapping[str, Any] | None = None
    training_assignments: np.ndarray | None = None
    training_filtered: ProbabilityBlock | None = None
    filtered: ProbabilityBlock | None = None
    smoothed: ProbabilityBlock | None = None
    oos_filtered: ProbabilityBlock | None = None

    def __post_init__(self) -> None:
        status = FitStatus(self.status)
        object.__setattr__(self, "status", status)
        start = as_timestamp(self.train_start, "train_start")
        end = as_timestamp(self.train_end, "train_end")
        if end < start:
            raise ValueError("train_end must not precede train_start")
        object.__setattr__(self, "train_start", start)
        object.__setattr__(self, "train_end", end)
        if not isinstance(self.converged, bool) or not isinstance(self.fallback_used, bool):
            raise ValueError("converged and fallback_used must be explicit booleans")
        if status is FitStatus.ACCEPTED:
            if not self.converged or self.parameters is None or self.fallback_used:
                raise ValueError("accepted fits require convergence, parameters, and no fallback")
            if self.rejection_reason or self.failure_reason:
                raise ValueError("accepted fits cannot carry rejection/failure reasons")
        elif status is FitStatus.NONCONVERGED:
            if self.converged or not self.rejection_reason:
                raise ValueError("nonconverged fits require converged=False and a rejection reason")
        elif status is FitStatus.REJECTED:
            if not self.rejection_reason:
                raise ValueError("rejected fits require a rejection_reason")
        elif status is FitStatus.FAILED and not self.failure_reason:
            raise ValueError("failed fits require a failure_reason")

        for name, expected in (("training_filtered", InferenceKind.TRAINING_FILTERED),
                               ("filtered", InferenceKind.FILTERED),
                               ("smoothed", InferenceKind.SMOOTHED),
                               ("oos_filtered", InferenceKind.OOS_FILTERED)):
            block = getattr(self, name)
            if block is not None and (not isinstance(block, ProbabilityBlock) or block.kind is not expected):
                raise ValueError(f"{name} must be a ProbabilityBlock of kind {expected.value}")
            if block is not None and block.probabilities.shape[1] != self.spec.state_count:
                raise ValueError(f"{name} state count must match ModelSpec.state_count")
            if block is not None and name == "oos_filtered" and block.dates[0] <= end:
                raise ValueError("oos_filtered dates must begin after train_end")
        if self.training_filtered is not None:
            block = self.training_filtered
            if block.dates[0] != start or block.dates[-1] != end:
                raise ValueError("training_filtered dates must match the declared training boundary")
            if self.oos_filtered is not None and block.state_ids != self.oos_filtered.state_ids:
                raise ValueError("training and OOS state_ids must agree within one fit")
        if self.training_assignments is not None:
            assignments = np.asarray(self.training_assignments)
            if assignments.ndim != 1 or not len(assignments):
                raise ValueError("training_assignments must be a non-empty one-dimensional array")
            if self.training_filtered is not None and len(assignments) != len(self.training_filtered.dates):
                raise ValueError("training assignments and training probabilities must align")
            if len(assignments) and ((assignments < 0).any() or (assignments >= self.spec.state_count).any()):
                raise ValueError("training assignments contain an invalid local state index")
            object.__setattr__(self, "training_assignments", assignments)

    @property
    def usable_for_inference(self) -> bool:
        return self.status is FitStatus.ACCEPTED and self.oos_filtered is not None


def require_usable_oos(fit: FitRecord) -> ProbabilityBlock:
    if not isinstance(fit, FitRecord) or not fit.usable_for_inference:
        raise ValueError("only an accepted converged fit with OOS filtered probabilities is usable")
    assert fit.oos_filtered is not None
    return fit.oos_filtered


@dataclass(frozen=True)
class PredictiveDensity:
    dates: pd.DatetimeIndex
    values: np.ndarray
    feature_names: tuple[str, ...]
    space: str
    units: str = "nats_per_observation"
    transformation_jacobian_included: bool = False

    def __post_init__(self) -> None:
        values = np.asarray(self.values, dtype=float)
        if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
            raise ValueError("density values must be a non-empty finite vector")
        dates = validate_date_index(self.dates, len(values))
        names = tuple(self.feature_names)
        if not names or len(set(names)) != len(names):
            raise ValueError("density feature_names must be non-empty, ordered, and unique")
        if self.space not in {"raw", "scaled"}:
            raise ValueError("density space must be 'raw' or 'scaled'")
        if self.units != "nats_per_observation":
            raise ValueError("density units must be nats_per_observation")
        if not isinstance(self.transformation_jacobian_included, bool):
            raise ValueError("transformation_jacobian_included must be explicit")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "dates", dates)
        object.__setattr__(self, "feature_names", names)

    @property
    def raw_dimension(self) -> int:
        return len(self.feature_names)

    @property
    def comparison_key(self) -> tuple[Any, ...]:
        date_fingerprint = hashlib.sha256(
            "\n".join(stamp.strftime("%Y-%m-%d") for stamp in self.dates).encode("ascii")
        ).hexdigest()
        return (self.feature_names, self.raw_dimension, self.space, self.units,
                self.transformation_jacobian_included, len(self.dates), date_fingerprint)


def assert_comparable_density(left: PredictiveDensity, right: PredictiveDensity) -> None:
    """Reject cross-dimensional or scaled/raw likelihood comparisons.

    In particular, multiplying values or adding a Jacobian cannot turn a density
    over one feature vector into a density over a different feature vector.
    """
    if left.space != "raw" or right.space != "raw":
        raise ValueError("only raw-space predictive densities are comparable")
    if not left.transformation_jacobian_included or not right.transformation_jacobian_included:
        raise ValueError("raw-space densities must include any fitted transformation Jacobian")
    if left.feature_names != right.feature_names or left.raw_dimension != right.raw_dimension:
        raise ValueError("predictive densities require the same ordered raw feature vector")
    if left.units != right.units or not left.dates.equals(right.dates):
        raise ValueError("predictive densities require identical observation dates and units")


@dataclass(frozen=True)
class SelectionScore:
    outer_fold_id: str
    candidate_id: str
    validation_fold_id: str
    validation_end: pd.Timestamp
    outer_test_start: pd.Timestamp
    predictive_log_density: float

    def __post_init__(self) -> None:
        if not self.outer_fold_id or not self.candidate_id or not self.validation_fold_id:
            raise ValueError("selection and validation identifiers must be non-empty")
        end = as_timestamp(self.validation_end, "validation_end")
        start = as_timestamp(self.outer_test_start, "outer_test_start")
        object.__setattr__(self, "validation_end", end)
        object.__setattr__(self, "outer_test_start", start)
        object.__setattr__(self, "predictive_log_density",
                           finite_number(self.predictive_log_density, "predictive_log_density"))


@dataclass(frozen=True)
class SelectionDecision:
    outer_fold_id: str
    selected_candidate_id: str
    mean_inner_log_density: float
    validation_fold_ids: tuple[str, ...]


def select_candidate_for_fold(scores: Sequence[SelectionScore], outer_fold_id: str) -> SelectionDecision:
    """Select only from inner validation ending strictly before the outer test."""
    relevant = [score for score in scores if score.outer_fold_id == outer_fold_id]
    if not relevant:
        raise ValueError(f"no inner selection scores for {outer_fold_id}")
    starts = {score.outer_test_start for score in relevant}
    if len(starts) != 1:
        raise ValueError("outer fold scores disagree about outer_test_start")
    outer_start = next(iter(starts))
    for score in relevant:
        if score.validation_end >= outer_start:
            raise ValueError("selection evidence must end strictly before outer_test_start")
    by_candidate: dict[str, list[SelectionScore]] = {}
    for score in relevant:
        by_candidate.setdefault(score.candidate_id, []).append(score)
    means = {candidate: float(np.mean([score.predictive_log_density for score in group]))
             for candidate, group in by_candidate.items()}
    # Deterministic candidate-ID tie break; never use outer-fold outcomes.
    selected = sorted(by_candidate, key=lambda candidate: (-means[candidate], candidate))[0]
    return SelectionDecision(
        outer_fold_id=outer_fold_id,
        selected_candidate_id=selected,
        mean_inner_log_density=means[selected],
        validation_fold_ids=tuple(score.validation_fold_id for score in by_candidate[selected]),
    )
