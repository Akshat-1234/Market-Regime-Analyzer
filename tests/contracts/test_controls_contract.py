from __future__ import annotations

import pytest

from research.contracts.controls import (ControlMatchDiagnostics, ControlMatchThresholds,
                                         assert_control_matching)


def diagnostics(**changes):
    values = dict(exposure_ks_distances=(0.01, 0.02, 0.90), causal=True,
                  mean_exposure_difference=0.01, annualized_turnover_difference=0.02,
                  annualized_volatility_difference=0.01)
    values.update(changes)
    return ControlMatchDiagnostics(**values)


def thresholds(**changes):
    values = dict(exposure_ks=0.05, ks_statistic="median", mean_exposure_difference=0.05,
                  annualized_turnover_difference=0.05, annualized_volatility_difference=0.05)
    values.update(changes)
    return ControlMatchThresholds(**values)


def test_exposure_ks_mean_and_median_are_not_conflated():
    summary = diagnostics().summary()
    assert summary["mean_exposure_ks"] == pytest.approx(0.31)
    assert summary["median_exposure_ks"] == pytest.approx(0.02)
    assert summary["mean_exposure_ks"] != summary["median_exposure_ks"]


def test_matching_claim_uses_named_statistic_and_all_dimensions():
    assert_control_matching(diagnostics(), thresholds())
    with pytest.raises(ValueError, match="mean exposure KS"):
        assert_control_matching(diagnostics(), thresholds(ks_statistic="mean"))
    with pytest.raises(ValueError, match="turnover"):
        assert_control_matching(diagnostics(annualized_turnover_difference=0.2), thresholds())
    with pytest.raises(ValueError, match="volatility"):
        assert_control_matching(diagnostics(annualized_volatility_difference=0.2), thresholds())


def test_noncausal_control_fails_closed_even_when_distribution_matches():
    with pytest.raises(ValueError, match="noncausal"):
        assert_control_matching(diagnostics(causal=False), thresholds())
