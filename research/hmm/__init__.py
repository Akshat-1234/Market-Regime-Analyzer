"""Selectively migrated 1c Gaussian/Student-t HMM engine.

The package is independent of the historical application. It does not perform
discovery, forecasting, allocation, or strategy selection.
"""
from .config import EMConfig
from .parameters import HMMFit, HMMParameters, HMMNumericalError, StateOccupancyError
from .emissions import emission_logprob
from .forward_backward import EStep, e_step, filter_causal
from .em import fit_hmm, fit_config, initialize_parameters, m_step
from .inference import smooth
from .adapter import FitAdapterResult, fit_model

ENGINE_VERSION = "task3-hmm-engine-v1"
SOURCE_COMMIT = "c46541e9ab8611330489a920c46cdb00342931d5"
SOURCE_EMHMM_SHA256 = "181d251fb8b3b78c907c6518a1714898041dbcb048275f82bd5dd308c2d1f6c9"

__all__ = [
    "EMConfig", "EStep", "FitAdapterResult", "HMMFit", "HMMParameters",
    "HMMNumericalError", "StateOccupancyError", "e_step", "emission_logprob",
    "filter_causal", "fit_config", "fit_hmm", "fit_model", "initialize_parameters",
    "m_step", "smooth", "ENGINE_VERSION", "SOURCE_COMMIT", "SOURCE_EMHMM_SHA256",
]
