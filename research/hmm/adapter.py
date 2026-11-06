"""Fail-closed adapter from the independent HMM engine to Task 2 contracts."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping
import numpy as np
import pandas as pd
from research.contracts._validation import validate_date_index
from research.contracts.model import FitRecord, FitStatus, InferenceKind, ModelSpec, PredictiveDensity, ProbabilityBlock
from research.contracts.state import StateOccupancy, summarize_occupancy
from .config import EMConfig
from .em import fit_config
from .inference import smooth
from .parameters import HMMFit, StateOccupancyError

@dataclass
class FitAdapterResult:
    record: FitRecord
    model: HMMFit | None = None
    training_density: PredictiveDensity | None = None
    oos_density: PredictiveDensity | None = None
    final_log_alpha: np.ndarray | None = None
    occupancy: tuple[StateOccupancy, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _density(dates, values, spec, space):
    return PredictiveDensity(dates=dates, values=values, feature_names=spec.feature_names,
                             space=space, units="nats_per_observation",
                             transformation_jacobian_included=(space == "raw"))


def _settings_for(spec, settings):
    if settings is None:
        return EMConfig(spec.state_count, spec.covariance_type, spec.emission, seed=spec.seed)
    if not (settings.n_states == spec.state_count and settings.covariance_type == spec.covariance_type
            and settings.emission == spec.emission and settings.seed == spec.seed):
        raise ValueError("EMConfig must match ModelSpec state/covariance/emission/seed")
    return settings


def fit_model(train_x, train_dates, spec: ModelSpec, *, test_x=None, test_dates=None,
              settings=None, min_state_fraction=0.0, include_smoothed=False,
              space="raw", state_ids=None) -> FitAdapterResult:
    """Fit training data only and conditionally attach accepted OOS filtering."""
    config = _settings_for(spec, settings)
    dates = validate_date_index(train_dates)
    values = np.asarray(train_x, dtype=float)
    if values.ndim != 2 or len(values) != len(dates) or values.shape[1] != len(spec.feature_names):
        raise ValueError("training observations, dates, and ordered feature names must align")
    if (test_x is None) != (test_dates is None):
        raise ValueError("test_x and test_dates must be supplied together")
    oos_values = None if test_x is None else np.asarray(test_x, dtype=float)
    oos_dates = None if test_dates is None else validate_date_index(test_dates, len(oos_values))
    if oos_values is not None and (oos_values.ndim != 2 or oos_values.shape[1] != values.shape[1]):
        raise ValueError("OOS observations must have the same feature dimension")
    if not 0 <= min_state_fraction <= 1:
        raise ValueError("min_state_fraction must be between zero and one")
    if space not in {"raw", "scaled"}:
        raise ValueError("space must be 'raw' or 'scaled'")
    ids = tuple(state_ids) if state_ids is not None else tuple(f"state_{i}" for i in range(spec.state_count))
    if len(ids) != spec.state_count or len(set(ids)) != len(ids):
        raise ValueError("state_ids must be unique and match ModelSpec.state_count")
    try:
        model = fit_config(values, config)
        training_probabilities, training_log_pred, final_alpha = model.filter(values)
    except StateOccupancyError as exc:
        record = FitRecord(spec, FitStatus.REJECTED, False, dates[0], dates[-1], rejection_reason=str(exc))
        return FitAdapterResult(record, diagnostics={"error_type": type(exc).__name__})
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
        record = FitRecord(spec, FitStatus.FAILED, False, dates[0], dates[-1],
                           failure_reason=f"{type(exc).__name__}: {exc}")
        return FitAdapterResult(record, diagnostics={"error_type": type(exc).__name__})
    training_block = ProbabilityBlock(dates, training_probabilities, ids, InferenceKind.TRAINING_FILTERED)
    occupancy = summarize_occupancy(training_probabilities, ids)
    training_density = _density(dates, training_log_pred, spec, space)
    smoothed_block = None
    if include_smoothed:
        smoothed_block = ProbabilityBlock(dates, smooth(model, values).gamma, ids, InferenceKind.SMOOTHED)
    parameters: Mapping[str, Any] = model.parameter_dict()
    diagnostics = {"engine_version": "task3-hmm-engine-v1", "config": asdict(config),
                   "space": space, "regularization_events": model.regularization_events,
                   "history": list(model.history), "returned_log_likelihood": model.loglik,
                   "min_state_fraction": min_state_fraction}
    below = [item.state_id for item in occupancy if item.hard_fraction < min_state_fraction]
    if below:
        reason = f"states below hard training occupancy {min_state_fraction}: {','.join(below)}"
        record = FitRecord(spec, FitStatus.REJECTED, model.converged, dates[0], dates[-1],
                           rejection_reason=reason, parameters=parameters,
                           training_assignments=training_probabilities.argmax(axis=1),
                           training_filtered=training_block, smoothed=smoothed_block)
        return FitAdapterResult(record, model, training_density, None, final_alpha,
                                occupancy, {**diagnostics, "rejection_reason": reason})
    if not model.converged:
        reason = f"maximum iterations ({config.n_iter}) without meeting relative likelihood tolerance {config.tol}"
        record = FitRecord(spec, FitStatus.NONCONVERGED, False, dates[0], dates[-1],
                           rejection_reason=reason, fallback_used=False, parameters=parameters,
                           training_assignments=training_probabilities.argmax(axis=1),
                           training_filtered=training_block, smoothed=smoothed_block)
        return FitAdapterResult(record, model, training_density, None, final_alpha,
                                occupancy, {**diagnostics, "rejection_reason": reason})
    oos_block = None
    oos_density = None
    if oos_values is not None:
        oos_probabilities, oos_log_pred, _ = model.filter(oos_values, final_alpha)
        oos_block = ProbabilityBlock(oos_dates, oos_probabilities, ids, InferenceKind.OOS_FILTERED)
        oos_density = _density(oos_dates, oos_log_pred, spec, space)
    record = FitRecord(spec, FitStatus.ACCEPTED, True, dates[0], dates[-1], parameters=parameters,
                       training_assignments=training_probabilities.argmax(axis=1),
                       training_filtered=training_block, smoothed=smoothed_block, oos_filtered=oos_block)
    return FitAdapterResult(record, model, training_density, oos_density, final_alpha, occupancy, diagnostics)
