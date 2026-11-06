"""Explicit retrospective smoothing, separate from causal filtering."""
from __future__ import annotations
import numpy as np
from .forward_backward import EStep, e_step
from .parameters import HMMParameters


def smooth(model: HMMParameters, x: np.ndarray) -> EStep:
    """Return filtered and smoothed quantities using the whole observation block.

    ``EStep.gamma`` is retrospective/noncausal. ``EStep.log_alpha`` and
    ``EStep.log_pred`` retain forward-only quantities for the same block.
    """
    return e_step(model.emission_logprob(x), model.startprob, model.transmat)
