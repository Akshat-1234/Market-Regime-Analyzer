"""Descriptive state/fold diagnostics; no independence or significance claims."""
from __future__ import annotations
from collections import Counter
import numpy as np
from research.contracts.model import ProbabilityBlock
from research.contracts.state import posterior_weighted_characteristics, summarize_occupancy
from .protocol import FEATURE_NAMES


def summarize_values(values):
    clean = np.asarray([value for value in values if value is not None and np.isfinite(value)], dtype=float)
    if not len(clean):
        return {"n": 0, "mean": None, "median": None, "std": None, "min": None, "max": None}
    return {"n": int(len(clean)), "mean": float(clean.mean()), "median": float(np.median(clean)),
            "std": float(clean.std(ddof=1)) if len(clean) > 1 else None,
            "min": float(clean.min()), "max": float(clean.max())}


def episode_metrics(assignments, state_ids):
    hard = np.asarray(assignments, dtype=int)
    episodes = {state: [] for state in range(len(state_ids))}
    if len(hard):
        start = 0
        for index in range(1, len(hard) + 1):
            if index == len(hard) or hard[index] != hard[start]:
                episodes[int(hard[start])].append(index - start)
                start = index
    result = {}
    for index, state in enumerate(state_ids):
        durations = np.asarray(episodes[index], dtype=float)
        result[state] = {"episodes": int(len(durations)),
                         "mean": float(durations.mean()) if len(durations) else None,
                         "median": float(np.median(durations)) if len(durations) else None,
                         "std": float(durations.std(ddof=1)) if len(durations) > 1 else None,
                         "min": float(durations.min()) if len(durations) else None,
                         "max": float(durations.max()) if len(durations) else None}
    return result


def block_metrics(block: ProbabilityBlock, raw_frame):
    probabilities = block.probabilities
    ids = block.state_ids
    occupancy = summarize_occupancy(probabilities, ids)
    profiles = posterior_weighted_characteristics(
        probabilities, {name: raw_frame[name].to_numpy(dtype=float) for name in FEATURE_NAMES}, ids)
    entropy = -np.sum(probabilities * np.log(np.clip(probabilities, 1e-300, 1.0)), axis=1)
    confidence = probabilities.max(axis=1)
    hard = probabilities.argmax(axis=1)
    states = []
    for index, state in enumerate(ids):
        weights = probabilities[:, index]
        total = float(weights.sum())
        effective = float(total ** 2 / np.dot(weights, weights)) if np.dot(weights, weights) > 0 else 0.0
        mask = hard == index
        states.append({"local_state_id": state,
                       "hard_count": occupancy[index].hard_count, "hard_fraction": occupancy[index].hard_fraction,
                       "posterior_weight": occupancy[index].posterior_weight, "rare": occupancy[index].rare,
                       "effective_sample_size": effective,
                       "raw_feature_profile": profiles[state],
                       "mean_posterior_entropy_nats_on_hard_rows": float(entropy[mask].mean()) if mask.any() else None,
                       "mean_max_posterior_confidence_on_hard_rows": float(confidence[mask].mean()) if mask.any() else None})
    return {"kind": block.kind.value, "dates": {"start": block.dates[0].strftime("%Y-%m-%d"),
                                               "end": block.dates[-1].strftime("%Y-%m-%d"), "rows": len(block.dates)},
            "states": states, "rare_state_fraction": float(np.mean([state["rare"] for state in states])),
            "mean_posterior_entropy_nats": float(entropy.mean()), "mean_max_posterior_confidence": float(confidence.mean())}


def transition_metrics(model, training_assignments):
    expected = {}
    for index in range(model.n_states):
        diagonal = float(model.transmat[index, index])
        expected[f"local_{index}"] = None if diagonal >= 1.0 else float(1.0 / (1.0 - diagonal))
    return {"transition_matrix": model.transmat.tolist(), "expected_duration_sessions": expected,
            "empirical_episode_durations": episode_metrics(training_assignments, tuple(f"local_{i}" for i in range(model.n_states))),
            "duration_note": "Implied geometric duration is not empirical persistence; hard episodes are descriptive and label-local."}


def _nested(record, path):
    value = record
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def aggregate_results(fold_records, candidate_attempts, selection_records, alignment_records):
    accepted = [record for record in fold_records if record["status"] == "accepted"]
    selections = [record for record in selection_records if record["status"] == "selected"]
    metric_paths = {
        "inner_validation_raw_log_density_per_observation": "selection.mean_inner_raw_log_density_per_observation",
        "outer_test_raw_log_density_per_observation": "outer_density.raw_mean_per_observation",
        "training_mean_posterior_entropy_nats": "training_state_metrics.mean_posterior_entropy_nats",
        "outer_mean_posterior_entropy_nats": "outer_state_metrics.mean_posterior_entropy_nats",
        "training_rare_state_fraction": "training_state_metrics.rare_state_fraction",
        "outer_rare_state_fraction": "outer_state_metrics.rare_state_fraction",
        "training_mean_confidence": "training_state_metrics.mean_max_posterior_confidence",
        "outer_mean_confidence": "outer_state_metrics.mean_max_posterior_confidence"}
    distributions = {name: summarize_values([_nested(record, path) for record in accepted])
                     for name, path in metric_paths.items()}
    distributions["alignment_agreement"] = summarize_values([record["agreement"] for record in alignment_records])
    distributions["alignment_unmatched_frequency"] = summarize_values([record["unmatched_frequency"] for record in alignment_records])
    stability_records = [item for record in alignment_records for item in record["records"]
                         if item["status"] == "accepted" and item.get("stability")]
    for name in ("training_profile_distance", "self_transition_abs_difference", "expected_duration_abs_difference",
                 "training_posterior_occupancy_abs_difference", "training_episode_mean_duration_abs_difference"):
        distributions[name] = summarize_values([item["stability"].get(name) for item in stability_records])
    candidate_counts = Counter(record["selected_candidate_id"] for record in selections)
    state_counts = Counter(str(record["state_count"]) for record in selections)
    emission_counts = Counter(record["emission"] for record in selections)
    covariance_counts = Counter(record["covariance_type"] for record in selections)
    seed_counts = Counter(str(record["selected_seed"]) for record in selections)
    status_counts = Counter(record["status"] for record in candidate_attempts)
    by_candidate = {}
    for record in candidate_attempts:
        row = by_candidate.setdefault(record["candidate_id"], Counter())
        row[record["status"]] += 1
    seed_spreads = []
    for record in selections:
        values = list(record["selected_candidate_seed_scores"].values())
        if values:
            seed_spreads.append(max(values) - min(values))
    return {
        "schema": "task4-aggregate-results-v1",
        "fold_counts": {"total": len(fold_records), "accepted": len(accepted),
                        "rejected_or_inconclusive": len(fold_records) - len(accepted)},
        "candidate_fit_status_counts": dict(status_counts),
        "candidate_fit_status_by_candidate": {key: dict(value) for key, value in sorted(by_candidate.items())},
        "selected_candidate_frequency": dict(candidate_counts), "selected_state_count_frequency": dict(state_counts),
        "selected_emission_frequency": dict(emission_counts), "selected_covariance_frequency": dict(covariance_counts),
        "selected_seed_frequency": dict(seed_counts),
        "selected_candidate_inner_seed_score_spread": summarize_values(seed_spreads),
        "distributions": distributions,
        "interpretation": "Descriptive annual-fold evidence only; overlapping daily rows and repeated candidates are not independent samples.",
        "no_significance_or_economic_claim": True}
