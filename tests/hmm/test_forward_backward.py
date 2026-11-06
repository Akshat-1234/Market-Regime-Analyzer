from __future__ import annotations
import itertools
import numpy as np
import pytest
from research.hmm.forward_backward import _log_forward, e_step


def fixture_chain():
    return (np.array([0.6, 0.4]), np.array([[0.9, 0.1], [0.2, 0.8]]),
            np.log(np.array([[0.8, 0.5], [0.4, 0.9], [0.7, 0.3]])))


def manual_forward(start, trans, emit):
    probabilities, predictive, previous = [], [], None
    for row in emit:
        unnormalized = (start if previous is None else previous @ trans) * row
        total = unnormalized.sum()
        previous = unnormalized / total
        probabilities.append(previous.copy())
        predictive.append(total)
    return np.asarray(probabilities), np.asarray(predictive)


def test_forward_matches_plain_probability_recursion():
    start, trans, log_emit = fixture_chain()
    log_alpha, log_pred, total = _log_forward(log_emit, start, trans, None)
    expected_probs, expected_predictive = manual_forward(start, trans, np.exp(log_emit))
    np.testing.assert_allclose(np.exp(log_alpha), expected_probs, rtol=0, atol=1e-15)
    np.testing.assert_allclose(np.exp(log_pred), expected_predictive, rtol=0, atol=1e-15)
    assert total == pytest.approx(np.log(expected_predictive).sum(), abs=1e-15)
    np.testing.assert_allclose(np.exp(log_alpha).sum(axis=1), 1.0, atol=1e-15)


def test_smoothing_matches_exhaustive_state_path_enumeration():
    start, trans, log_emit = fixture_chain()
    emit = np.exp(log_emit)
    n, k = emit.shape
    joint = np.zeros((n, k))
    pair_counts = np.zeros((n - 1, k, k))
    for path in itertools.product(range(k), repeat=n):
        probability = start[path[0]] * emit[0, path[0]]
        for t in range(1, n):
            probability *= trans[path[t - 1], path[t]] * emit[t, path[t]]
        for t, state in enumerate(path):
            joint[t, state] += probability
        for t in range(n - 1):
            pair_counts[t, path[t], path[t + 1]] += probability
    posterior = joint / joint.sum(axis=1, keepdims=True)
    step = e_step(log_emit, start, trans)
    np.testing.assert_allclose(step.gamma, posterior, rtol=0, atol=2e-15)
    np.testing.assert_allclose(step.xi_counts, pair_counts.sum(axis=0) / joint[0].sum(), rtol=0, atol=2e-15)
    assert joint[0].sum() == pytest.approx(np.exp(step.loglik), abs=1e-15)
    np.testing.assert_allclose(step.gamma.sum(axis=1), 1.0, atol=1e-15)


def test_pairwise_counts_are_consistent_with_smoothed_occupancy():
    start, trans, log_emit = fixture_chain()
    step = e_step(log_emit, start, trans)
    np.testing.assert_allclose(step.xi_counts.sum(), len(log_emit) - 1, atol=1e-14)
    num = step.log_alpha[:-1][:, :, None] + np.log(trans)[None, :, :] + (log_emit[1:] + step.log_beta[1:])[:, None, :]
    xi = np.exp(num - step.log_pred[1:, None, None])
    np.testing.assert_allclose(xi.sum(axis=2), np.exp(step.log_alpha[:-1] + step.log_beta[:-1] - step.log_pred[1:, None]), atol=1e-12)


def test_one_observation_filter_and_smoothing_edge_case():
    start, trans, log_emit = fixture_chain()
    step = e_step(log_emit[:1], start, trans)
    np.testing.assert_allclose(step.gamma, np.exp(step.log_alpha), atol=1e-15)
    np.testing.assert_array_equal(step.xi_counts, np.zeros((2, 2)))
    np.testing.assert_allclose(step.log_beta, np.zeros((1, 2)))


def test_extreme_transition_probabilities_are_log_space_stable():
    log_emit = np.log(np.array([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]]))
    step = e_step(log_emit, np.array([1.0, 0.0]), np.eye(2))
    np.testing.assert_allclose(step.gamma, [[1.0, 0.0]] * 3)
    assert np.isfinite(step.loglik)


def test_long_sequence_has_finite_normalized_probabilities():
    n = 10000
    start, trans, _ = fixture_chain()
    log_emit = np.tile(np.array([-1000.0, -1000.5]), (n, 1))
    log_alpha, log_pred, total = _log_forward(log_emit, start, trans, None)
    probabilities = np.exp(log_alpha)
    assert len(probabilities) == n and np.isfinite(total) and np.isfinite(log_pred).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1.0, atol=1e-14)


def test_prefix_invariance_and_chunk_continuation(diag_fit):
    x = np.random.default_rng(8).normal(size=(80, 2))
    full, full_log_pred, final = diag_fit.filter(x)
    prefix, prefix_pred, alpha = diag_fit.filter(x[:31])
    continuation, continuation_pred, continued_final = diag_fit.filter(x[31:], alpha)
    np.testing.assert_allclose(full[:31], prefix, rtol=0, atol=1e-15)
    np.testing.assert_allclose(full[31:], continuation, rtol=0, atol=1e-15)
    np.testing.assert_allclose(full_log_pred, np.concatenate([prefix_pred, continuation_pred]), atol=1e-14)
    np.testing.assert_allclose(final, continued_final, atol=1e-15)


def test_future_mutation_changes_smoothed_but_not_filtered_prefix(diag_fit):
    from research.hmm.inference import smooth
    x = np.random.default_rng(19).normal(size=(30, 2))
    changed = x.copy()
    changed[20:] = 1000
    first = smooth(diag_fit, x)
    second = smooth(diag_fit, changed)
    np.testing.assert_allclose(np.exp(first.log_alpha[:20]), np.exp(second.log_alpha[:20]), atol=1e-15)
    assert not np.allclose(first.gamma[:20], second.gamma[:20])
    np.testing.assert_allclose(first.gamma.sum(axis=1), 1.0, atol=1e-14)


def test_invalid_chain_and_previous_alpha_fail_closed(diag_fit):
    with pytest.raises(ValueError, match="previous_log_alpha is invalid"):
        diag_fit.filter([[0.0, 0.0]], np.array([np.nan, np.nan]))
    from research.hmm.forward_backward import filter_causal
    values = diag_fit.parameter_dict()
    with pytest.raises(ValueError, match="startprob"):
        filter_causal(values["means"], values["covars"], "diag", "gaussian", None,
                      [0.2, 0.2], values["transmat"], [[0.0, 0.0]])
