from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
import numpy as np
import pandas as pd
import pytest
from research.contracts.model import ModelSpec
from research.hmm.parameters import HMMFit

ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "c46541e9ab8611330489a920c46cdb00342931d5"
SOURCE_PATH = "market-regime-platform/src/regime_backtester/emhmm.py"

@pytest.fixture(scope="session")
def original_emhmm():
    payload = subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{SOURCE_PATH}"], cwd=ROOT)
    inventory = {}
    with (ROOT / "provenance/inventory/1c-c46541e-tracked-blobs.jsonl").open() as handle:
        for line in handle:
            record = json.loads(line)
            inventory[record["path"]] = record["sha256"]
    assert hashlib.sha256(payload).hexdigest() == inventory[SOURCE_PATH]
    name = "_task3_immutable_1c_emhmm"
    module = types.ModuleType(name)
    module.__file__ = f"{SOURCE_COMMIT}:{SOURCE_PATH}"
    sys.modules[name] = module
    exec(compile(payload, module.__file__, "exec"), module.__dict__)
    return module

@pytest.fixture
def diag_fit():
    return HMMFit(startprob=np.array([0.6, 0.4]), transmat=np.array([[0.9, 0.1], [0.2, 0.8]]),
                  means=np.array([[-1.0, 0.0], [1.0, 1.0]]), covars=np.array([[0.5, 0.8], [0.7, 1.2]]),
                  covariance_type="diag", loglik=-123.25, n_iter=2, converged=True,
                  history=[-123.250001, -123.25], seed=7)

@pytest.fixture
def full_fit():
    return HMMFit(startprob=np.array([0.6, 0.4]), transmat=np.array([[0.9, 0.1], [0.2, 0.8]]),
                  means=np.array([[-1.0, 0.0], [1.0, 1.0]]),
                  covars=np.array([[[0.5, 0.1], [0.1, 0.8]], [[0.7, -0.2], [-0.2, 1.1]]]),
                  covariance_type="full", seed=3)

@pytest.fixture
def student_fit(diag_fit):
    from dataclasses import replace
    return replace(diag_fit, emission="student_t", dof=6.0)

@pytest.fixture
def make_spec():
    def factory(states=2, emission="gaussian", covariance="diag", seed=7):
        return ModelSpec("task3-synthetic", "task3-hmm-engine-v1.1", "rv", "f10-close-features-v1",
                         ("daily_return", "volatility_20"), states, emission, covariance, "identity", seed)
    return factory

@pytest.fixture
def train_test_data():
    rng = np.random.default_rng(12345)
    train = np.concatenate([rng.normal([-0.01, 0.12], [0.004, 0.025], (60, 2)),
                            rng.normal([0.015, 0.28], [0.006, 0.04], (60, 2))])
    test = np.concatenate([rng.normal([-0.008, 0.13], [0.004, 0.025], (15, 2)),
                           rng.normal([0.014, 0.27], [0.006, 0.04], (15, 2))])
    dates = pd.date_range("2020-01-01", periods=150, freq="B")
    return train, dates[:120], test, dates[120:]
