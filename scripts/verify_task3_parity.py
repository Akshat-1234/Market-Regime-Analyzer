#!/usr/bin/env python3
"""Generate measured exact-1c and independent-reference HMM parity evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from hmmlearn.hmm import GaussianHMM
import numpy as np
from research.contracts._validation import canonical_json_bytes
from research.hmm.em import fit_hmm
from research.hmm.emissions import emission_logprob
from research.hmm.forward_backward import e_step
from research.hmm.parameters import HMMFit

COMMIT = "c46541e9ab8611330489a920c46cdb00342931d5"
SOURCE = "market-regime-platform/src/regime_backtester/emhmm.py"


def load_original(root):
    payload = subprocess.check_output(["git", "show", f"{COMMIT}:{SOURCE}"], cwd=root)
    expected = None
    with (root / "provenance/inventory/1c-c46541e-tracked-blobs.jsonl").open() as handle:
        for line in handle:
            row = json.loads(line)
            if row["path"] == SOURCE:
                expected = row["sha256"]
    actual = hashlib.sha256(payload).hexdigest()
    if expected is None or actual != expected:
        raise RuntimeError("original HMM source is not inventory-identical")
    name = "_task3_parity_original"
    module = types.ModuleType(name)
    module.__file__ = f"{COMMIT}:{SOURCE}"
    sys.modules[name] = module
    exec(compile(payload, module.__file__, "exec"), module.__dict__)
    return module, actual


def array_metrics(actual, expected):
    a = np.asarray(actual, dtype=float)
    b = np.asarray(expected, dtype=float)
    return {"bitwise_equal": bool(np.array_equal(a, b)),
            "max_absolute_difference": float(np.max(np.abs(a - b))) if a.size else 0.0,
            "shape": list(a.shape)}


def original_smoothing(old, parameters, x):
    emit = old.emission_logprob(x, parameters["means"], parameters["covars"],
                                parameters["covariance_type"], parameters["emission"], parameters["dof"])
    alpha, pred, likelihood = old._log_forward(emit, parameters["startprob"], parameters["transmat"], None)
    beta = np.zeros_like(emit)
    log_trans = np.log(parameters["transmat"])
    for t in range(len(x) - 2, -1, -1):
        beta[t] = old._lse(emit[t + 1] + beta[t + 1] + log_trans, axis=1)
    log_gamma = alpha + beta
    log_gamma -= old._lse(log_gamma, axis=1)[:, None]
    gamma = np.exp(log_gamma)
    gamma /= gamma.sum(axis=1, keepdims=True)
    return alpha, pred, beta, gamma, likelihood


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="provenance/task3_parity.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    old, source_hash = load_original(root)
    rng = np.random.default_rng(123)
    x = np.concatenate([rng.normal(-1, 0.4, (80, 2)), rng.normal(1, 0.7, (80, 2))])
    cases = []
    for emission, covariance, dof in [("gaussian", "diag", None), ("gaussian", "full", None), ("student_t", "diag", 6.0)]:
        kwargs = dict(n_states=2, covariance_type=covariance, emission=emission, dof=dof,
                      n_iter=7, tol=0.0, sticky=2.0, seed=7, min_covar=1e-4)
        original = old.fit_hmm(x, **kwargs)
        migrated = fit_hmm(x, **kwargs)
        parameters = {name: np.asarray(getattr(original, name), dtype=float)
                      for name in ("startprob", "transmat", "means", "covars")}
        parameters.update(covariance_type=covariance, emission=emission, dof=original.dof)
        emit_grid = np.concatenate([x[:10], np.array([[1e6, -1e6], [-1e6, 1e6]])])
        old_emit = old.emission_logprob(emit_grid, parameters["means"], parameters["covars"], covariance, emission, parameters["dof"])
        new_emit = emission_logprob(emit_grid, parameters["means"], parameters["covars"], covariance, emission, parameters["dof"])
        old_filter = old.filter_causal(parameters["means"], parameters["covars"], covariance, emission, parameters["dof"],
                                       parameters["startprob"], parameters["transmat"], x[:60])
        new_filter = migrated.filter(x[:60])
        old_oos = old.filter_causal(parameters["means"], parameters["covars"], covariance, emission, parameters["dof"],
                                    parameters["startprob"], parameters["transmat"], x[60:], old_filter[2])
        new_oos = migrated.filter(x[60:], new_filter[2])
        old_smooth = original_smoothing(old, parameters, x)
        new_smooth = e_step(migrated.emission_logprob(x), migrated.startprob, migrated.transmat)
        case = {
            "id": f"{emission}-{covariance}", "configuration": kwargs,
            "fit": {name: array_metrics(getattr(migrated, name), getattr(original, name))
                    for name in ("startprob", "transmat", "means", "covars", "history")},
            "final_log_likelihood_absolute_difference": abs(migrated.loglik - original.loglik),
            "iterations_equal": migrated.n_iter == original.n_iter,
            "convergence_equal": migrated.converged == original.converged,
            "dof_equal": migrated.dof == original.dof,
            "regularization_events_new_diagnostic": migrated.regularization_events,
            "emissions": array_metrics(new_emit, old_emit),
            "filtered_probabilities": array_metrics(new_filter[0], old_filter[0]),
            "filtered_predictive_log_density": array_metrics(new_filter[1], old_filter[1]),
            "final_log_alpha": array_metrics(new_filter[2], old_filter[2]),
            "oos_filtered_probabilities": array_metrics(new_oos[0], old_oos[0]),
            "oos_predictive_log_density": array_metrics(new_oos[1], old_oos[1]),
            "smoothed_probabilities": array_metrics(new_smooth.gamma, old_smooth[3]),
            "backward_log_beta": array_metrics(new_smooth.log_beta, old_smooth[2])}
        booleans = [value["bitwise_equal"] for value in case["fit"].values()]
        booleans += [case[name]["bitwise_equal"] for name in (
            "emissions", "filtered_probabilities", "filtered_predictive_log_density", "final_log_alpha",
            "oos_filtered_probabilities", "oos_predictive_log_density", "smoothed_probabilities", "backward_log_beta")]
        case["all_original_comparisons_bitwise_equal"] = all(booleans)
        cases.append(case)
    fixed = HMMFit(np.array([0.6, 0.4]), np.array([[0.9, 0.1], [0.2, 0.8]]),
                   np.array([[-1.0, 0.0], [1.0, 1.0]]),
                   np.array([[[0.5, 0.1], [0.1, 0.8]], [[0.7, -0.2], [-0.2, 1.1]]]), "full")
    independent_x = np.random.default_rng(912).normal(size=(40, 2))
    reference = GaussianHMM(n_components=2, covariance_type="full", implementation="log")
    reference.startprob_ = fixed.startprob
    reference.transmat_ = fixed.transmat
    reference.means_ = fixed.means
    reference.covars_ = fixed.covars
    reference_likelihood, reference_gamma = reference.score_samples(independent_x)
    actual = e_step(fixed.emission_logprob(independent_x), fixed.startprob, fixed.transmat)
    hmmlearn_result = {
        "library": "hmmlearn", "model": "GaussianHMM-full-log-implementation",
        "log_likelihood_absolute_difference": abs(actual.loglik - reference_likelihood),
        "log_likelihood_atol": 1e-9, "log_likelihood_rtol": 1e-11,
        "log_likelihood_within_tolerance": bool(np.isclose(actual.loglik, reference_likelihood, rtol=1e-11, atol=1e-9)),
        "smoothed_probabilities": array_metrics(actual.gamma, reference_gamma),
        "smoothed_probability_atol": 1e-10, "smoothed_probability_rtol": 1e-10,
        "smoothed_probabilities_within_tolerance": bool(np.allclose(actual.gamma, reference_gamma, rtol=1e-10, atol=1e-10))}
    evidence = {
        "schema": "task3-hmm-parity-v1", "source": {"commit": COMMIT, "path": SOURCE, "sha256": source_hash},
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "original_valid_input_tolerance": {"rtol": 0.0, "atol": 0.0, "requirement": "bitwise equality"},
        "cases": cases, "independent_hmmlearn_reference": hmmlearn_result,
        "excluded_family": "Student-t full covariance was unsupported by exact 1c and remains rejected",
        "divergences": [],
        "correctness_hardening_separate_from_parity": [
            "reject NaN/inf and invalid covariance/probability inputs",
            "reject invalid covariance rather than silently repairing it outside original EM regularization",
            "count covariance regularization events in diagnostics", "no nonconverged-to-accepted fallback"],
        "scope": "numerical equivalence and independent mathematics only; no predictive or economic claim"}
    all_original = all(case["all_original_comparisons_bitwise_equal"] for case in cases)
    independent = hmmlearn_result["log_likelihood_within_tolerance"] and hmmlearn_result["smoothed_probabilities_within_tolerance"]
    evidence["result"] = {"all_original_cases_bitwise_equal": all_original,
                          "independent_reference_within_predeclared_tolerance": independent}
    with (root / args.output).open("xb") as handle:
        handle.write(canonical_json_bytes(evidence))
    print(json.dumps(evidence["result"], indent=2))
    if not all_original or not independent:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
