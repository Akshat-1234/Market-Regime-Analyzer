"""Causal nested temporal regime discovery using the frozen Task 3.1 engine."""
from .protocol import PROTOCOL_VERSION, candidate_grid, inner_folds, outer_folds, protocol_dict
from .temporal import TrainingTransform, raw_density_from_scaled, select_using_inner_evidence
from .alignment import StateProfiles, align_state_profiles, build_state_profiles, initial_alignment

__all__ = ["PROTOCOL_VERSION", "StateProfiles", "TrainingTransform", "align_state_profiles",
           "build_state_profiles", "candidate_grid", "initial_alignment", "inner_folds", "outer_folds",
           "protocol_dict", "raw_density_from_scaled", "select_using_inner_evidence"]
