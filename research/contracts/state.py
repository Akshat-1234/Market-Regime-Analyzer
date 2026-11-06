"""Arbitrary-label occupancy, training-based alignment, and descriptions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from ._validation import finite_number, validate_probability_matrix
from .model import InferenceKind, ProbabilityBlock

ALIGNMENT_METHOD = "training-hard-contingency-hungarian-v1"


@dataclass(frozen=True)
class StateOccupancy:
    state_id: str
    hard_count: int
    hard_fraction: float
    posterior_weight: float
    rare: bool


@dataclass(frozen=True)
class StateAlignment:
    reference_ids: tuple[str, ...]
    current_ids: tuple[str, ...]
    current_to_reference: Mapping[str, str]
    training_start: pd.Timestamp
    training_end: pd.Timestamp
    agreement: float
    contingency: np.ndarray
    method: str = ALIGNMENT_METHOD


def summarize_occupancy(probabilities: np.ndarray, state_ids: tuple[str, ...] | None = None,
                        *, rare_min_count: int = 100, rare_min_fraction: float = 0.05
                        ) -> tuple[StateOccupancy, ...]:
    """Summarize the supplied column order exactly once; never permute twice."""
    matrix = validate_probability_matrix(probabilities)
    ids = tuple(state_ids) if state_ids is not None else tuple(f"state_{i}" for i in range(matrix.shape[1]))
    if len(ids) != matrix.shape[1] or len(set(ids)) != len(ids):
        raise ValueError("state_ids must be unique and match probability columns")
    if isinstance(rare_min_count, bool) or not isinstance(rare_min_count, int) or rare_min_count < 0:
        raise ValueError("rare_min_count must be a nonnegative integer")
    if not 0 <= rare_min_fraction <= 1:
        raise ValueError("rare_min_fraction must be between zero and one")
    hard = matrix.argmax(axis=1)
    counts = np.bincount(hard, minlength=matrix.shape[1])
    fractions = counts / len(matrix)
    weights = matrix.mean(axis=0)
    return tuple(StateOccupancy(str(ids[index]), int(counts[index]), float(fractions[index]),
                                float(weights[index]),
                                bool(counts[index] < rare_min_count or fractions[index] < rare_min_fraction))
                 for index in range(matrix.shape[1]))


def align_training_states(reference: ProbabilityBlock, current: ProbabilityBlock) -> StateAlignment:
    """Align arbitrary current labels to reference labels using training overlap only."""
    for name, block in (("reference", reference), ("current", current)):
        if not isinstance(block, ProbabilityBlock) or block.kind is not InferenceKind.TRAINING_FILTERED:
            raise ValueError(f"{name} alignment input must be training-filtered probabilities")
    if reference.probabilities.shape[1] != current.probabilities.shape[1]:
        raise ValueError("one-to-one alignment requires the same state count")
    overlap = reference.dates.intersection(current.dates)
    if overlap.empty:
        raise ValueError("state alignment requires overlapping training dates")
    reference_rows = reference.dates.get_indexer(overlap)
    current_rows = current.dates.get_indexer(overlap)
    reference_hard = reference.probabilities[reference_rows].argmax(axis=1)
    current_hard = current.probabilities[current_rows].argmax(axis=1)
    size = reference.probabilities.shape[1]
    contingency = np.zeros((size, size), dtype=np.int64)
    np.add.at(contingency, (reference_hard, current_hard), 1)
    rows, columns = linear_sum_assignment(-contingency)
    mapping = {current.state_ids[column]: reference.state_ids[row]
               for row, column in zip(rows, columns)}
    agreement = float(contingency[rows, columns].sum() / len(overlap))
    return StateAlignment(reference.state_ids, current.state_ids, mapping,
                          overlap[0], overlap[-1], agreement, contingency)


def apply_alignment(current: ProbabilityBlock, alignment: StateAlignment) -> np.ndarray:
    """Return probabilities in reference-column order using the explicit mapping."""
    if current.state_ids != alignment.current_ids:
        raise ValueError("alignment current IDs do not match the probability block")
    aligned = np.empty_like(current.probabilities)
    for reference_position, reference_id in enumerate(alignment.reference_ids):
        sources = [index for index, current_id in enumerate(current.state_ids)
                   if alignment.current_to_reference.get(current_id) == reference_id]
        if len(sources) != 1:
            raise ValueError("alignment must be a one-to-one complete mapping")
        aligned[:, reference_position] = current.probabilities[:, sources[0]]
    return aligned


def posterior_weighted_characteristics(probabilities: np.ndarray,
                                       measurements: Mapping[str, np.ndarray],
                                       state_ids: tuple[str, ...] | None = None
                                       ) -> dict[str, dict[str, float | None]]:
    """Describe measured contemporaneous variables, with explicit empty-state nulls.

    Forward outcomes are a separate temporal contract and are not an alignment
    input.  Rare-state means remain descriptive and are never inferential claims.
    """
    matrix = validate_probability_matrix(probabilities)
    ids = tuple(state_ids) if state_ids is not None else tuple(f"state_{i}" for i in range(matrix.shape[1]))
    if len(ids) != matrix.shape[1] or len(set(ids)) != len(ids):
        raise ValueError("state_ids must be unique and match probability columns")
    clean_measurements = {}
    for name, values in measurements.items():
        array = np.asarray(values, dtype=float)
        if array.ndim != 1 or len(array) != len(matrix):
            raise ValueError(f"measurement {name} must align with probability rows")
        clean_measurements[name] = array
    result: dict[str, dict[str, float | None]] = {}
    for state_position, state_id in enumerate(ids):
        row: dict[str, float | None] = {}
        for name, values in clean_measurements.items():
            valid = np.isfinite(values)
            weight = float(matrix[valid, state_position].sum())
            row[name] = (float(np.dot(matrix[valid, state_position], values[valid]) / weight)
                         if weight > 1e-12 else None)
        result[str(state_id)] = row
    return result
