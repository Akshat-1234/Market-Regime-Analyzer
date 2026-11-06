"""Training-only transforms, comparable raw densities, and strict inner selection."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np
import pandas as pd
from research.contracts.model import (PredictiveDensity, SelectionDecision, SelectionScore,
                                      assert_comparable_density, select_candidate_for_fold)
from .protocol import FEATURE_NAMES, INNER_FOLD_COUNT, MIN_COMPLETE_SEEDS


@dataclass(frozen=True)
class TrainingTransform:
    mean: np.ndarray
    scale: np.ndarray
    train_start: str
    train_end: str
    train_rows: int

    @classmethod
    def fit(cls, frame: pd.DataFrame) -> "TrainingTransform":
        if tuple(frame.columns) != FEATURE_NAMES or frame.empty:
            raise ValueError("training frame must contain the ordered Task 4 features")
        values = frame.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("training features must be finite without internal gaps")
        mean = values.mean(axis=0)
        scale = values.std(axis=0, ddof=0)
        if not np.isfinite(scale).all() or (scale <= 0).any():
            raise ValueError("training-only feature scale is degenerate")
        return cls(mean, scale, frame.index[0].strftime("%Y-%m-%d"),
                   frame.index[-1].strftime("%Y-%m-%d"), len(frame))

    def apply(self, frame: pd.DataFrame) -> np.ndarray:
        if tuple(frame.columns) != FEATURE_NAMES or frame.empty:
            raise ValueError("transform input must contain the ordered Task 4 features")
        values = frame.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("transform features must be finite")
        return (values - self.mean) / self.scale

    @property
    def log_jacobian(self) -> float:
        return float(np.log(self.scale).sum())

    def as_dict(self):
        return {"method": "training-only-zscore-ddof0-with-raw-jacobian-v1",
                "train_start": self.train_start, "train_end": self.train_end, "train_rows": self.train_rows,
                "feature_names": list(FEATURE_NAMES), "mean": self.mean.tolist(), "scale_ddof0": self.scale.tolist(),
                "sum_log_scale": self.log_jacobian}


def raw_density_from_scaled(dates, scaled_log_density, transform: TrainingTransform) -> PredictiveDensity:
    """Convert p_z(z) to p_x(x): log p_x = log p_z - sum(log scale)."""
    values = np.asarray(scaled_log_density, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("scaled predictive log density must be a finite vector")
    return PredictiveDensity(pd.DatetimeIndex(dates), values - transform.log_jacobian,
                              FEATURE_NAMES, "raw", "nats_per_observation", True)


def assert_same_density_contract(left: PredictiveDensity, right: PredictiveDensity):
    assert_comparable_density(left, right)


@dataclass(frozen=True)
class AttemptScore:
    candidate_id: str
    seed: int
    inner_fold_id: str
    score: SelectionScore


@dataclass(frozen=True)
class StrictSelection:
    decision: SelectionDecision
    selected_seed: int
    eligible_candidates: tuple[str, ...]
    candidate_scores: dict[str, float]
    seed_scores: dict[str, dict[str, float]]


def select_using_inner_evidence(attempts: Sequence[AttemptScore], outer_fold_id: str) -> StrictSelection:
    """Require complete seed coverage before delegating deterministic selection to Task 2."""
    by_candidate_seed: dict[tuple[str, int], list[AttemptScore]] = {}
    for attempt in attempts:
        if attempt.score.outer_fold_id != outer_fold_id:
            raise ValueError("inner attempt belongs to a different outer fold")
        if attempt.score.validation_end >= attempt.score.outer_test_start:
            raise ValueError("inner validation reaches the outer test")
        key = (attempt.candidate_id, attempt.seed)
        by_candidate_seed.setdefault(key, []).append(attempt)
    complete: dict[str, dict[int, list[AttemptScore]]] = {}
    for (candidate, seed), group in by_candidate_seed.items():
        fold_ids = [item.inner_fold_id for item in group]
        if len(group) == INNER_FOLD_COUNT and len(set(fold_ids)) == INNER_FOLD_COUNT:
            complete.setdefault(candidate, {})[seed] = sorted(group, key=lambda item: item.inner_fold_id)
    eligible = tuple(sorted(candidate for candidate, seeds in complete.items() if len(seeds) >= MIN_COMPLETE_SEEDS))
    if not eligible:
        raise ValueError(f"no candidate has {MIN_COMPLETE_SEEDS} complete seeds for {outer_fold_id}")
    eligible_scores = [item.score for candidate in eligible for seed_group in complete[candidate].values()
                       for item in seed_group]
    decision = select_candidate_for_fold(eligible_scores, outer_fold_id)
    candidate_scores = {}
    seed_scores: dict[str, dict[str, float]] = {}
    for candidate in eligible:
        values = [item.score.predictive_log_density for seed_group in complete[candidate].values() for item in seed_group]
        candidate_scores[candidate] = float(np.mean(values))
        seed_scores[candidate] = {str(seed): float(np.mean([item.score.predictive_log_density for item in group]))
                                  for seed, group in sorted(complete[candidate].items())}
    selected_seed_scores = seed_scores[decision.selected_candidate_id]
    selected_seed = min((int(seed) for seed in selected_seed_scores),
                        key=lambda seed: (-selected_seed_scores[str(seed)], seed))
    return StrictSelection(decision, selected_seed, eligible, candidate_scores, seed_scores)
