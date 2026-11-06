"""Training-only state profiles and rectangular Hungarian alignment."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from research.contracts.model import InferenceKind, ProbabilityBlock
from research.contracts.state import posterior_weighted_characteristics
from .protocol import ALIGNMENT_MAX_DISTANCE, ALIGNMENT_MIN_MARGIN, FEATURE_NAMES


@dataclass(frozen=True)
class StateProfiles:
    fold_id: str
    local_state_ids: tuple[str, ...]
    profiles: dict[str, dict[str, float]]
    feature_variance: np.ndarray
    train_start: str
    train_end: str

    def matrix(self):
        return np.asarray([[self.profiles[state][name] for name in FEATURE_NAMES]
                           for state in self.local_state_ids], dtype=float)


def build_state_profiles(fold_id: str, train_frame: pd.DataFrame,
                         training_block: ProbabilityBlock) -> StateProfiles:
    if training_block.kind is not InferenceKind.TRAINING_FILTERED or not training_block.dates.equals(train_frame.index):
        raise ValueError("profiles require aligned training-filtered probabilities")
    raw = posterior_weighted_characteristics(
        training_block.probabilities,
        {name: train_frame[name].to_numpy(dtype=float) for name in FEATURE_NAMES},
        training_block.state_ids)
    if any(raw[state][name] is None for state in raw for name in FEATURE_NAMES):
        raise ValueError("state profile has no posterior mass")
    return StateProfiles(fold_id, training_block.state_ids, raw,
                         train_frame.loc[:, FEATURE_NAMES].to_numpy(dtype=float).var(axis=0, ddof=0),
                         train_frame.index[0].strftime("%Y-%m-%d"), train_frame.index[-1].strftime("%Y-%m-%d"))


@dataclass(frozen=True)
class AlignmentResult:
    reference_fold_id: str | None
    current_fold_id: str
    records: tuple[dict, ...]
    current_to_aligned: dict[str, str | None]
    agreement: float | None
    unmatched_frequency: float
    distance_matrix: list[list[float]] | None

    def as_dict(self):
        return {"schema": "task4-state-alignment-v1", "method": "training-posterior-profile-hungarian-v1",
                "reference_fold_id": self.reference_fold_id, "current_fold_id": self.current_fold_id,
                "records": list(self.records), "current_to_aligned": self.current_to_aligned,
                "agreement": self.agreement, "unmatched_frequency": self.unmatched_frequency,
                "distance_matrix": self.distance_matrix, "outer_test_used": False,
                "maximum_accepted_distance": ALIGNMENT_MAX_DISTANCE, "minimum_margin": ALIGNMENT_MIN_MARGIN}


def initial_alignment(profiles: StateProfiles) -> AlignmentResult:
    records = []
    mapping = {}
    for local in profiles.local_state_ids:
        aligned = f"structure_{profiles.fold_id}_{local}"
        mapping[local] = aligned
        records.append({"local_state_id": local, "aligned_state_id": aligned, "status": "initial_unaligned",
                        "proposed_reference_local_id": None, "distance": None, "margin": None, "confidence": None})
    return AlignmentResult(None, profiles.fold_id, tuple(records), mapping, None, 0.0, None)


def _margin(distances, row, column):
    alternatives = []
    if distances.shape[1] > 1:
        alternatives.append(np.min(np.delete(distances[row], column)) - distances[row, column])
    if distances.shape[0] > 1:
        alternatives.append(np.min(np.delete(distances[:, column], row)) - distances[row, column])
    return float(min(alternatives)) if alternatives else None


def align_state_profiles(reference: StateProfiles, current: StateProfiles,
                         reference_aligned_ids: Mapping[str, str | None]) -> AlignmentResult:
    """Align only from adjacent training profiles; never from outer-test outcomes."""
    if reference.train_end >= current.train_start and reference.fold_id == current.fold_id:
        raise ValueError("alignment folds must be distinct")
    ref_matrix = reference.matrix()
    current_matrix = current.matrix()
    if not np.isfinite(ref_matrix).all() or not np.isfinite(current_matrix).all():
        raise ValueError("state profiles must be finite")
    scale = np.sqrt((reference.feature_variance + current.feature_variance) / 2.0)
    if not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("alignment feature scale is degenerate")
    distances = np.sqrt((((current_matrix[:, None, :] - ref_matrix[None, :, :]) / scale) ** 2).sum(axis=2))
    rows, columns = linear_sum_assignment(distances)
    proposed = {int(row): int(column) for row, column in zip(rows, columns)}
    records = []
    mapping: dict[str, str | None] = {}
    accepted = 0
    for current_index, local in enumerate(current.local_state_ids):
        reference_index = proposed.get(current_index)
        reference_local = reference.local_state_ids[reference_index] if reference_index is not None else None
        distance = float(distances[current_index, reference_index]) if reference_index is not None else None
        margin = _margin(distances, current_index, reference_index) if reference_index is not None else None
        inheritable = reference_aligned_ids.get(reference_local) if reference_local is not None else None
        is_accepted = bool(reference_index is not None and distance <= ALIGNMENT_MAX_DISTANCE
                           and margin is not None and margin >= ALIGNMENT_MIN_MARGIN and inheritable)
        if is_accepted:
            status = "accepted"
            aligned = inheritable
            accepted += 1
        elif reference_index is not None and distance <= ALIGNMENT_MAX_DISTANCE and margin is not None and margin < ALIGNMENT_MIN_MARGIN:
            status = "ambiguous"
            aligned = None
        else:
            status = "new_unmatched"
            aligned = f"structure_{current.fold_id}_{local}"
        mapping[local] = aligned
        records.append({"local_state_id": local, "aligned_state_id": aligned, "status": status,
                        "proposed_reference_local_id": reference_local,
                        "proposed_reference_aligned_id": inheritable,
                        "distance": distance, "margin": margin,
                        "confidence": None if distance is None else float(1.0 / (1.0 + distance))})
    possible = min(len(reference.local_state_ids), len(current.local_state_ids))
    agreement = float(accepted / possible) if possible else None
    unmatched = sum(record["status"] != "accepted" for record in records) / len(records)
    return AlignmentResult(reference.fold_id, current.fold_id, tuple(records), mapping, agreement,
                           float(unmatched), distances.tolist())
