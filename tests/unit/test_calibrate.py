"""Tests for plant calibration (``ipis.integration.calibrate``)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import chi2

from ipis.integration.calibrate import (
    CalibrationReport,
    degradation_rate_for_rul,
    synth_growth,
    verify_calibration,
)
from ipis.integration.plant import FeatureSynthesizer

# --- synthetic M2 ---------------------------------------------------------------


class _HealthModel:
    def __init__(self, n: int = 3) -> None:
        self.mean = np.zeros(n)
        self.precision = np.eye(n)
        self.n_features = n
        self.warn_t2 = float(chi2.ppf(0.95, n))
        self.alarm_t2 = float(chi2.ppf(0.99, n))

    def t2(self, x):
        d = np.asarray(x, dtype=float).ravel() - self.mean
        return float(d @ self.precision @ d)

    def flag(self, x):
        t = self.t2(x)
        return "ALARM" if t >= self.alarm_t2 else ("WARN" if t >= self.warn_t2 else "OK")

    def health_score(self, x):
        ex = max(0.0, self.t2(x) - self.n_features)
        return 1.0 / (1.0 + ex / self.n_features)


class _PdM:
    def __init__(self, hm: _HealthModel, rul_scale: float = 80.0) -> None:
        self.hm = hm
        self.rul_scale = rul_scale

    def observe(self, equipment_id, features):
        h = self.hm.health_score(features)
        flag = self.hm.flag(features)
        # RUL only once past onset (not OK); a calibrated lower bound on true RUL.
        rul = None if flag == "OK" else self.rul_scale * h
        return {"health_score": h, "flag": flag, "rul_hours": rul, "t2": self.hm.t2(features)}


# --- degradation rate -----------------------------------------------------------


def test_rate_gives_target_rul() -> None:
    rate = degradation_rate_for_rul(2000.0)
    assert rate == pytest.approx(1.0 / 2000.0)
    # fresh RUL at load 1 = damage_at_failure*dt/base_rate
    assert 1.0 / rate == pytest.approx(2000.0)


def test_rate_rejects_nonpositive() -> None:
    with pytest.raises(ValueError):
        degradation_rate_for_rul(0.0)


# --- synth growth ---------------------------------------------------------------


def test_growth_places_severity_one_at_target_t2() -> None:
    hm = _HealthModel(n=3)
    failure = np.array([3.0, 2.0, 1.0])
    g = synth_growth(hm, failure, target_t2_mult=2.0)
    # severity == 1 -> features = mean + g -> T^2 should equal 2 * alarm_t2
    assert hm.t2(hm.mean + g) == pytest.approx(2.0 * hm.alarm_t2, rel=1e-9)
    # growth points along the failure direction
    assert np.all(np.sign(g) == np.sign(failure - hm.mean))


def test_growth_alarm_fires_below_one() -> None:
    hm = _HealthModel(n=4)
    g = synth_growth(hm, np.array([2.0, 2.0, 1.0, 1.0]), target_t2_mult=2.0)
    # ALARM at severity ~ 1/sqrt(2) ~ 0.707; check 0.71 alarms, 0.70 does not.
    assert hm.t2(hm.mean + 0.71 * g) >= hm.alarm_t2
    assert hm.t2(hm.mean + 0.70 * g) < hm.alarm_t2


def test_growth_rejects_failure_at_mean() -> None:
    hm = _HealthModel()
    with pytest.raises(ValueError):
        synth_growth(hm, hm.mean)


# --- verification harness -------------------------------------------------------


def test_verify_calibration_behaves() -> None:
    hm = _HealthModel(n=3)
    failure = np.array([3.0, 2.0, 1.0])
    growth = synth_growth(hm, failure, target_t2_mult=2.0)
    synth = FeatureSynthesizer(
        feature_names=("rms", "kurt", "crest"),
        baseline=hm.mean.copy(),
        growth=growth,
    )
    rate = degradation_rate_for_rul(100.0)  # fast clock so 60 cycles reach EoL
    rep = verify_calibration(_PdM(hm), synth, ref_flow=66.5, base_rate=rate, load=1.5, n_cycles=60)
    assert isinstance(rep, CalibrationReport)
    assert rep.reached_alarm is True
    assert rep.alarm_severity is not None and 0.6 < rep.alarm_severity < 0.85
    assert rep.health_monotone is True


def test_verify_flags_rul_scale_mismatch() -> None:
    # An M2 whose RUL scale far exceeds the plant's true RUL -> lower bound invalid.
    hm = _HealthModel(n=3)
    growth = synth_growth(hm, np.array([3.0, 2.0, 1.0]))
    synth = FeatureSynthesizer(
        feature_names=("a", "b", "c"), baseline=hm.mean.copy(), growth=growth
    )
    rate = degradation_rate_for_rul(100.0)
    rep = verify_calibration(
        _PdM(hm, rul_scale=1.0e6), synth, ref_flow=66.5, base_rate=rate, n_cycles=60
    )
    assert rep.rul_lower_bound_valid is False
