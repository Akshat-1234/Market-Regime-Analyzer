"""Frozen Task 4 v1 protocol; no outer-outcome-dependent configuration."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
import numpy as np
import pandas as pd
from research.contracts.features import FEATURE_CONTRACT_VERSION
from research.contracts.model import ModelSpec
from research.hmm.config import EMConfig
from research.hmm.version import ENGINE_VERSION

PROTOCOL_VERSION = "task4-rv-nested-v1.0.0"
ENGINE_FREEZE_SHA256 = "53f61c24e75ddda81e374ce4629cb88cf1fb521a5dc8c1d91d1a68ce95cd0ea9"
DATA_SHA256 = "ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4"
FEATURE_NAMES = ("daily_return", "volatility_20")
SEEDS = (2, 42, 7)
OUTER_YEARS = tuple(range(2012, 2026))
MIN_OUTER_TRAIN_ROWS = 756
MIN_INNER_TRAIN_ROWS = 504
INNER_VALIDATION_ROWS = 126
INNER_FOLD_COUNT = 3
MIN_COMPLETE_SEEDS = 2
MIN_STATE_FRACTION = 0.02
ALIGNMENT_MAX_DISTANCE = 2.0
ALIGNMENT_MIN_MARGIN = 0.25
NUMERICAL_SETTINGS = {"n_iter": 200, "tol": 1e-5, "min_covar": 1e-4, "sticky": 0.0, "student_t_initial_dof": 6.0}


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    state_count: int
    emission: str
    covariance_type: str

    def config(self, seed: int) -> EMConfig:
        return EMConfig(n_states=self.state_count, covariance_type=self.covariance_type,
                        emission=self.emission,
                        dof=NUMERICAL_SETTINGS["student_t_initial_dof"] if self.emission == "student_t" else None,
                        n_iter=NUMERICAL_SETTINGS["n_iter"], tol=NUMERICAL_SETTINGS["tol"],
                        min_covar=NUMERICAL_SETTINGS["min_covar"], sticky=NUMERICAL_SETTINGS["sticky"], seed=seed)

    def model_spec(self, seed: int) -> ModelSpec:
        return ModelSpec(self.candidate_id, ENGINE_VERSION, "rv", FEATURE_CONTRACT_VERSION,
                         FEATURE_NAMES, self.state_count, self.emission, self.covariance_type,
                         "training-only-zscore-ddof0-with-raw-jacobian-v1", seed)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fold:
    fold_id: str
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_rows: int
    test_rows: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InnerFold:
    inner_fold_id: str
    outer_fold_id: str
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    train_rows: int
    validation_rows: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def candidate_grid() -> tuple[Candidate, ...]:
    grid = []
    for k in (2, 3, 4, 5):
        for emission, covariance in (("gaussian", "diag"), ("gaussian", "full"), ("student_t", "diag")):
            grid.append(Candidate(f"k{k}_{emission}_{covariance}", k, emission, covariance))
    return tuple(grid)


def _stamp(value) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def outer_folds(feature_dates: pd.DatetimeIndex) -> tuple[Fold, ...]:
    dates = pd.DatetimeIndex(feature_dates)
    folds = []
    for year in OUTER_YEARS:
        test = dates[dates.year == year]
        if not len(test):
            raise ValueError(f"missing outer-test year {year}")
        train = dates[dates < test[0]]
        if len(train) < MIN_OUTER_TRAIN_ROWS:
            raise ValueError(f"insufficient outer training rows for {year}")
        folds.append(Fold(f"outer_{year}", _stamp(train[0]), _stamp(train[-1]), _stamp(test[0]), _stamp(test[-1]),
                          len(train), len(test)))
    for previous, current in zip(folds, folds[1:]):
        if current.test_start <= previous.test_end:
            raise ValueError("outer tests must be chronological and nonoverlapping")
    return tuple(folds)


def inner_folds(outer: Fold, outer_train_dates: pd.DatetimeIndex) -> tuple[InnerFold, ...]:
    dates = pd.DatetimeIndex(outer_train_dates)
    if len(dates) != outer.train_rows or _stamp(dates[0]) != outer.train_start or _stamp(dates[-1]) != outer.train_end:
        raise ValueError("inner construction requires the exact declared outer training dates")
    minimum = MIN_INNER_TRAIN_ROWS + INNER_VALIDATION_ROWS
    if len(dates) < minimum:
        raise ValueError("insufficient rows for chronological inner validation")
    endpoints = np.linspace(minimum, len(dates), INNER_FOLD_COUNT).astype(int)
    if len(set(endpoints)) != INNER_FOLD_COUNT:
        raise ValueError("inner validation endpoints are not unique")
    result = []
    for index, endpoint in enumerate(endpoints, 1):
        validation = dates[endpoint - INNER_VALIDATION_ROWS:endpoint]
        train = dates[:endpoint - INNER_VALIDATION_ROWS]
        if len(validation) != INNER_VALIDATION_ROWS or len(train) < MIN_INNER_TRAIN_ROWS:
            raise ValueError("inner fold violates predeclared sample sizes")
        if train[-1] >= validation[0] or validation[-1] > dates[-1]:
            raise ValueError("inner train/validation chronology is invalid")
        result.append(InnerFold(f"{outer.fold_id}_inner_{index:02d}", outer.fold_id,
                                _stamp(train[0]), _stamp(train[-1]), _stamp(validation[0]), _stamp(validation[-1]),
                                len(train), len(validation)))
    for previous, current in zip(result, result[1:]):
        if current.validation_start <= previous.validation_end:
            raise ValueError("inner validation blocks must not overlap")
    return tuple(result)


def protocol_dict() -> dict[str, Any]:
    return {
        "schema": "task4-discovery-protocol-v1", "protocol_version": PROTOCOL_VERSION,
        "engine_version": ENGINE_VERSION, "engine_freeze_sha256": ENGINE_FREEZE_SHA256,
        "research_question": "Do bounded HMM specifications produce occupied, identifiable and temporally reproducible latent states without outer-test selection leakage?",
        "dataset": {"path": "research/data/nifty_index.csv", "raw_sha256": DATA_SHA256, "rows": 4684,
                    "start": "2007-09-17", "end": "2026-10-22"},
        "features": {"family": "rv", "contract_version": FEATURE_CONTRACT_VERSION, "ordered_names": list(FEATURE_NAMES),
                     "close_only": True, "internal_gap_imputation": False},
        "candidate_grid": [candidate.as_dict() for candidate in candidate_grid()], "seeds": list(SEEDS),
        "numerical_settings": NUMERICAL_SETTINGS,
        "outer_folds": {"years": list(OUTER_YEARS), "construction": "expanding training; subsequent calendar-year nonoverlapping tests",
                        "minimum_training_rows": MIN_OUTER_TRAIN_ROWS, "partial_2026_excluded": True},
        "inner_folds": {"count": INNER_FOLD_COUNT, "minimum_train_rows": MIN_INNER_TRAIN_ROWS,
                        "validation_rows": INNER_VALIDATION_ROWS,
                        "endpoint_rule": "floor(linspace(min_train+validation_rows, outer_train_rows, 3))",
                        "construction": "three nonoverlapping subsequent validation blocks with expanding training"},
        "acceptance": {"minimum_hard_training_state_fraction": MIN_STATE_FRACTION,
                       "complete_inner_folds_per_seed": INNER_FOLD_COUNT,
                       "minimum_complete_seeds_per_candidate": MIN_COMPLETE_SEEDS,
                       "unsuccessful_attempts_retained": True},
        "selection": {"evidence": "inner validation only", "metric": "mean per-observation raw-space predictive log density",
                      "candidate_score": "mean over all eligible seed/fold scores using Task 2 SelectionDecision",
                      "selected_seed": "highest mean inner score among complete seeds; smallest seed tie break",
                      "candidate_tie_break": "Task 2 deterministic candidate-ID tie break",
                      "outer_test_used": False},
        "density": {"fit_space": "training-only-zscore-ddof0", "comparison_space": "raw",
                    "raw_conversion": "scaled_log_density_minus_sum_log_training_scales",
                    "jacobian_included": True, "units": "nats_per_observation"},
        "alignment": {"method": "training-posterior-profile-hungarian-v1",
                      "profiles": "training-filtered posterior-weighted raw daily_return and volatility_20",
                      "scale": "sqrt(mean of adjacent training-only feature variances)",
                      "maximum_accepted_distance": ALIGNMENT_MAX_DISTANCE,
                      "minimum_row_column_margin": ALIGNMENT_MIN_MARGIN,
                      "rectangular_unmatched": True, "ambiguous_mapping_not_forced": True,
                      "outer_test_used": False},
        "rare_state_rule": {"hard_count_less_than": 100, "hard_fraction_less_than": 0.05},
        "statistics": "descriptive fold distributions: n, mean, median, sample std, min, max; no independence/significance claim",
        "nonclaims": ["no forecasting or return prediction", "no allocation/backtest/trading signal",
                      "no economic usefulness claim", "no prospective holdout claim", "no semantic regime labels"],
        "boundary_sensitivity": "annual fold distributions only; no alternate shifted-boundary protocol was predeclared",
    }
