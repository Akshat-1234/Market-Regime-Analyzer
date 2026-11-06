from __future__ import annotations
import numpy as np
from research.discovery.alignment import StateProfiles, align_state_profiles, initial_alignment


def profiles(fold, ids, values):
    return StateProfiles(fold, tuple(ids),
                         {state: {"daily_return": float(value[0]), "volatility_20": float(value[1])}
                          for state, value in zip(ids, values)},
                         np.array([1.0, 1.0]), "2007-10-16", "2011-12-30" if fold == "reference" else "2012-12-31")


def test_profile_alignment_is_permutation_invariant():
    reference = profiles("reference", ["r0", "r1"], [[0.0, 0.0], [3.0, 3.0]])
    aligned = {"r0": "structure_A", "r1": "structure_B"}
    current = profiles("current", ["c0", "c1"], [[3.1, 3.1], [0.1, 0.1]])
    permuted = profiles("current", ["x0", "x1"], [[0.1, 0.1], [3.1, 3.1]])
    first = align_state_profiles(reference, current, aligned)
    second = align_state_profiles(reference, permuted, aligned)
    assert first.current_to_aligned["c0"] == second.current_to_aligned["x1"] == "structure_B"
    assert first.current_to_aligned["c1"] == second.current_to_aligned["x0"] == "structure_A"
    assert first.agreement == second.agreement == 1.0


def test_rectangular_alignment_preserves_unmatched_state_explicitly():
    reference = profiles("reference", ["r0", "r1"], [[0.0, 0.0], [3.0, 3.0]])
    current = profiles("current", ["c0", "c1", "c2"], [[0.0, 0.1], [3.1, 3.0], [20.0, 20.0]])
    result = align_state_profiles(reference, current, {"r0": "A", "r1": "B"})
    assert result.current_to_aligned["c0"] == "A" and result.current_to_aligned["c1"] == "B"
    extra = next(record for record in result.records if record["status"] == "new_unmatched")
    assert extra["aligned_state_id"].startswith("structure_current_")
    assert result.unmatched_frequency > 0


def test_ambiguous_alignment_is_not_forced():
    reference = profiles("reference", ["r0", "r1"], [[0.0, 0.0], [1.0, 1.0]])
    current = profiles("current", ["c0", "c1"], [[0.5, 0.5], [20.0, 20.0]])
    result = align_state_profiles(reference, current, {"r0": "A", "r1": "B"})
    ambiguous = next(record for record in result.records if record["local_state_id"] == "c0")
    assert ambiguous["status"] == "ambiguous" and ambiguous["aligned_state_id"] is None
    assert ambiguous["margin"] == 0.0


def test_distant_states_are_new_not_semantically_relabelled():
    reference = profiles("reference", ["r0", "r1"], [[0.0, 0.0], [1.0, 1.0]])
    current = profiles("current", ["c0", "c1"], [[10.0, 10.0], [20.0, 20.0]])
    result = align_state_profiles(reference, current, {"r0": "A", "r1": "B"})
    assert all(record["status"] == "new_unmatched" for record in result.records)
    assert all(value.startswith("structure_current_") for value in result.current_to_aligned.values())


def test_initial_alignment_preserves_local_ids_and_needs_no_outer_data():
    current = profiles("current", ["local_0", "local_1"], [[0.0, 0.0], [1.0, 1.0]])
    result = initial_alignment(current)
    assert result.reference_fold_id is None and result.agreement is None
    assert set(result.current_to_aligned) == {"local_0", "local_1"}
    assert all(record["status"] == "initial_unaligned" for record in result.records)
    assert not result.as_dict()["outer_test_used"]
