from __future__ import annotations
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from research.contracts.model import InferenceKind, ProbabilityBlock
from research.discovery.diagnostics import (aggregate_results, block_metrics, episode_metrics,
                                             summarize_values, transition_metrics)


def test_descriptive_distribution_and_episode_durations():
    summary = summarize_values([1.0, 2.0, 3.0])
    assert summary == {"n": 3, "mean": 2.0, "median": 2.0, "std": 1.0, "min": 1.0, "max": 3.0}
    assert summarize_values([])["n"] == 0
    episodes = episode_metrics([0, 0, 1, 1, 1, 0], ("local_0", "local_1"))
    assert episodes["local_0"]["mean"] == 1.5 and episodes["local_0"]["episodes"] == 2
    assert episodes["local_1"]["mean"] == 3.0 and episodes["local_1"]["episodes"] == 1


def test_transition_implied_duration_is_not_episode_duration():
    model = SimpleNamespace(n_states=2, transmat=np.array([[0.75, 0.25], [0.2, 0.8]]))
    result = transition_metrics(model, np.array([0, 0, 1, 1, 1, 0]))
    assert result["expected_duration_sessions"]["local_0"] == 4.0
    assert result["expected_duration_sessions"]["local_1"] == pytest.approx(5.0)
    assert result["empirical_episode_durations"]["local_0"]["mean"] == 1.5
    assert "not empirical persistence" in result["duration_note"]


def test_occupancy_effective_size_entropy_and_rare_states():
    probabilities = np.array([[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]])
    dates = pd.date_range("2020-01-01", periods=4, freq="B")
    block = ProbabilityBlock(dates, probabilities, ("local_0", "local_1"), InferenceKind.TRAINING_FILTERED)
    frame = pd.DataFrame({"daily_return": [-0.01, -0.005, 0.01, 0.02],
                          "volatility_20": [0.1, 0.12, 0.3, 0.35]}, index=dates)
    result = block_metrics(block, frame)
    assert result["states"][0]["hard_count"] == 2 and result["states"][1]["hard_count"] == 2
    assert result["states"][0]["effective_sample_size"] > 0
    assert result["rare_state_fraction"] == 1.0  # Task 2 count<100 rule on this tiny fixture
    assert result["mean_posterior_entropy_nats"] > 0
    assert result["states"][0]["raw_feature_profile"]["daily_return"] < 0


def test_aggregate_preserves_inconclusive_folds_and_status_counts():
    folds = [{"status": "accepted", "selection": {"mean_inner_raw_log_density_per_observation": 1.0},
              "outer_density": {"raw_mean_per_observation": 0.5},
              "training_state_metrics": {"mean_posterior_entropy_nats": 0.2, "rare_state_fraction": 0.0,
                                         "mean_max_posterior_confidence": 0.9},
              "outer_state_metrics": {"mean_posterior_entropy_nats": 0.3, "rare_state_fraction": 0.5,
                                      "mean_max_posterior_confidence": 0.8}},
             {"status": "inconclusive"}]
    attempts = [{"candidate_id": "a", "status": "accepted"}, {"candidate_id": "a", "status": "failed"}]
    selections = [{"status": "selected", "candidate_id": "a", "state_count": 2, "emission": "gaussian",
                   "covariance_type": "diag", "selected_seed": 2, "selected_candidate_seed_scores": {"2": 1.0}}]
    result = aggregate_results(folds, attempts, selections, [])
    assert result["fold_counts"] == {"total": 2, "accepted": 1, "rejected_or_inconclusive": 1}
    assert result["candidate_fit_status_counts"] == {"accepted": 1, "failed": 1}
    assert result["distributions"]["outer_test_raw_log_density_per_observation"]["n"] == 1
    assert result["no_significance_or_economic_claim"]
