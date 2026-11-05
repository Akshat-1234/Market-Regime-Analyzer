from __future__ import annotations

import json

import numpy as np
import pytest

from research.contracts.controls import ControlMatchDiagnostics
from research.contracts.experiment import validate_manifest


def test_exact_1c_reference_manifest_fails_new_provenance_contract(historical_1c):
    path = "market-regime-platform/research_outputs/study_20261030T111521Z/manifest.json"
    historical = json.loads(historical_1c.source(path))
    assert "stages" in historical  # historical diagnostic/status register
    with pytest.raises(ValueError, match="missing required fields") as error:
        validate_manifest(historical)
    message = str(error.value)
    assert "schema_version" in message
    assert "source" in message
    assert "artifacts" in message
    # The old manifest is read only and remains unchanged in Git.


def test_exact_1c_median_exposure_key_computes_mean(historical_1c):
    source = historical_1c.source("market-regime-platform/src/regime_backtester/study.py").decode()
    assert 'ks = float(np.mean([ks_2samp' in source
    assert '"median_exposure_ks": ks' in source
    distances = (0.01, 0.02, 0.90)
    summary = ControlMatchDiagnostics(distances, True, 0.01, 0.01, 0.01).summary()
    assert float(np.mean(distances)) == pytest.approx(summary["mean_exposure_ks"])
    assert summary["median_exposure_ks"] == pytest.approx(0.02)
    assert summary["mean_exposure_ks"] != summary["median_exposure_ks"]


def test_exact_1c_phase_shift_wraps_future_into_past(historical_1c):
    allocation = historical_1c.module("allocation")
    exposure = np.arange(1.0, 9.0)
    shifted = allocation.phase_shift(exposure, 3)
    np.testing.assert_array_equal(shifted[:3], exposure[-3:])
    np.testing.assert_array_equal(shifted, np.roll(exposure, 3))
    # Circular shift preserves marginals by construction but is not a causal
    # transformation: late exposures enter early positions.  No allocation
    # matching claim can be supported by that property alone.
