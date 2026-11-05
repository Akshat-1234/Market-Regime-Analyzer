"""Exclusive-cutoff target maturity, expanding folds, and execution timing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from ._validation import as_timestamp, finite_number, validate_date_index


@dataclass(frozen=True)
class TargetLabel:
    decision_date: pd.Timestamp
    outcome_end_date: pd.Timestamp
    horizon_sessions: int
    value: float

    def __post_init__(self) -> None:
        decision = as_timestamp(self.decision_date, "decision_date")
        end = as_timestamp(self.outcome_end_date, "outcome_end_date")
        if end <= decision:
            raise ValueError("target outcome_end_date must follow decision_date")
        if isinstance(self.horizon_sessions, bool) or self.horizon_sessions < 1:
            raise ValueError("horizon_sessions must be a positive integer")
        object.__setattr__(self, "decision_date", decision)
        object.__setattr__(self, "outcome_end_date", end)
        object.__setattr__(self, "value", finite_number(self.value, "target value"))

    def mature_before(self, test_start: pd.Timestamp) -> bool:
        cutoff = as_timestamp(test_start, "test_start")
        return self.decision_date < cutoff and self.outcome_end_date < cutoff


@dataclass(frozen=True)
class FoldBoundary:
    fold_id: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp

    def __post_init__(self) -> None:
        if not self.fold_id:
            raise ValueError("fold_id must be non-empty")
        values = {name: as_timestamp(getattr(self, name), name)
                  for name in ("train_start", "train_end", "test_start", "test_end")}
        if not values["train_start"] <= values["train_end"] < values["test_start"] <= values["test_end"]:
            raise ValueError("fold requires train_start <= train_end < test_start <= test_end")
        for name, value in values.items():
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class ExecutionTiming:
    decision_date: pd.Timestamp
    execution_date: pd.Timestamp
    first_return_date: pd.Timestamp

    def __post_init__(self) -> None:
        decision = as_timestamp(self.decision_date, "decision_date")
        execution = as_timestamp(self.execution_date, "execution_date")
        first_return = as_timestamp(self.first_return_date, "first_return_date")
        if not decision < execution < first_return:
            raise ValueError("timing requires decision < execution < first measured return")
        object.__setattr__(self, "decision_date", decision)
        object.__setattr__(self, "execution_date", execution)
        object.__setattr__(self, "first_return_date", first_return)


def forward_return_labels(close: pd.Series, horizon_sessions: int) -> tuple[TargetLabel, ...]:
    """Construct explicit decision/outcome-end labels; never claim trailing outcomes exist."""
    if isinstance(horizon_sessions, bool) or not isinstance(horizon_sessions, int) or horizon_sessions < 1:
        raise ValueError("horizon_sessions must be a positive integer")
    if not isinstance(close, pd.Series):
        raise ValueError("close must be a Series")
    dates = validate_date_index(close.index, len(close))
    values = close.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("close values must be finite and positive")
    labels = []
    for position in range(0, len(close) - horizon_sessions):
        end = position + horizon_sessions
        labels.append(TargetLabel(dates[position], dates[end], horizon_sessions,
                                  float(values[end] / values[position] - 1.0)))
    return tuple(labels)


def eligible_training_labels(labels: Iterable[TargetLabel], test_start: pd.Timestamp) -> tuple[TargetLabel, ...]:
    """f10 purge: decision date and complete target outcome both precede test start."""
    cutoff = as_timestamp(test_start, "test_start")
    result = []
    for label in labels:
        if not isinstance(label, TargetLabel):
            raise ValueError("labels must be TargetLabel instances")
        if label.mature_before(cutoff):
            result.append(label)
    return tuple(result)


def require_mature_labels(labels: Iterable[TargetLabel], test_start: pd.Timestamp) -> None:
    cutoff = as_timestamp(test_start, "test_start")
    for label in labels:
        if not isinstance(label, TargetLabel) or not label.mature_before(cutoff):
            raise ValueError("training label decision/outcome dates must both be strictly before test_start")


def annual_expanding_folds(dates: pd.DatetimeIndex, *, min_train: int,
                           start_date: str | None = None) -> tuple[FoldBoundary, ...]:
    """Build chronological annual test folds with an expanding historical prefix."""
    index = validate_date_index(dates)
    if isinstance(min_train, bool) or not isinstance(min_train, int) or min_train < 1:
        raise ValueError("min_train must be a positive integer")
    first = min_train
    if start_date is not None:
        first = max(first, int(index.searchsorted(as_timestamp(start_date, "start_date"), side="left")))
    folds = []
    position = first
    while position < len(index):
        first_signal = index[position]
        next_year = pd.Timestamp(year=first_signal.year + 1, month=1, day=1)
        end = min(int(index.searchsorted(next_year, side="left")), len(index))
        if end <= position:
            raise ValueError("fold calendar did not advance")
        folds.append(FoldBoundary(f"fold_{len(folds) + 1:03d}", index[0], index[position - 1],
                                  index[position], index[end - 1]))
        position = end
    if not folds:
        raise ValueError("fold schedule is empty")
    return tuple(folds)
