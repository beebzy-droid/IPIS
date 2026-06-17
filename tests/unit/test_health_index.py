"""Tests for the Hotelling T^2 health index (Option C).

Math tests use synthetic feature matrices; one integration test fits on healthy
signals and asserts a fault signal escalates health_score down and the flag to
ALARM, using the real combined feature vector.
"""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module2_pdm.features.vibration_features import FEATURE_VECTOR_NAMES, feature_vector
from ipis.module2_pdm.health.health_index import HealthIndexModel
from ipis.module2_pdm.physics.bearing_frequencies import DefectFrequencies
from ipis.shared.state_bus import HealthFlag

NAMES4 = ("a", "b", "c", "d")


def _healthy_matrix(n=200, dim=4, seed=0):
    rng = np.random.RandomState(seed)
    return rng.multivariate_normal(np.zeros(dim), np.eye(dim), size=n)


def test_limits_ordered_and_positive():
    m = HealthIndexModel.fit(_healthy_matrix(), NAMES4)
    assert 0 < m.warn_t2 < m.alarm_t2
    assert m.n_features == 4


def test_healthy_sample_is_ok_and_high_health():
    m = HealthIndexModel.fit(_healthy_matrix(), NAMES4)
    x = np.zeros(4)  # at the baseline mean -> T^2 ~ 0
    assert m.t2(x) < m.warn_t2
    assert m.flag(x) == HealthFlag.OK
    assert m.health_score(x) == pytest.approx(1.0, abs=1e-9)


def test_far_sample_alarms_and_low_health():
    m = HealthIndexModel.fit(_healthy_matrix(), NAMES4)
    x = np.array([8.0, 8.0, 8.0, 8.0])  # far in Mahalanobis terms
    assert m.t2(x) >= m.alarm_t2
    assert m.flag(x) == HealthFlag.ALARM
    assert m.health_score(x) < 0.2


def test_health_monotone_decreasing_with_distance():
    m = HealthIndexModel.fit(_healthy_matrix(), NAMES4)
    scores = [m.health_score(np.full(4, r)) for r in (0.0, 1.0, 2.0, 4.0, 8.0)]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
    assert scores[0] == pytest.approx(1.0)


def test_flag_escalates_through_warn_to_alarm():
    m = HealthIndexModel.fit(_healthy_matrix(), NAMES4)
    # find a radius that lands between warn and alarm
    seen = set()
    for r in np.linspace(0, 6, 200):
        seen.add(m.flag(np.full(4, r)))
    assert {HealthFlag.OK, HealthFlag.WARN, HealthFlag.ALARM} <= seen


def test_fit_rejects_too_few_samples():
    with pytest.raises(ValueError):
        HealthIndexModel.fit(np.zeros((1, 4)), NAMES4)


def test_fit_rejects_dim_mismatch():
    with pytest.raises(ValueError):
        HealthIndexModel.fit(_healthy_matrix(dim=4), ("a", "b", "c"))


def test_assess_returns_all_outputs():
    m = HealthIndexModel.fit(_healthy_matrix(), NAMES4)
    out = m.assess(np.zeros(4))
    assert set(out) == {"t2", "health_score", "flag"}
    assert out["flag"] == HealthFlag.OK


# ---- integration: real feature vector, healthy signals vs a fault signal ----


def _noise(fs=12000, dur=1.0, level=1.0, seed=0):
    return np.random.RandomState(seed).randn(int(fs * dur)) * level


def _fault(fs=12000, dur=1.0, f_fault=120.0, seed=0):
    rng = np.random.RandomState(seed)
    n = int(fs * dur)
    t = np.arange(n) / fs
    x = np.zeros(n)
    period = 1.0 / f_fault
    k = 1
    while k * period < dur:
        i0 = int(k * period * fs)
        tt = t[i0:] - k * period
        x[i0:] += np.exp(-800 * tt) * np.sin(2 * np.pi * 3000 * tt)
        k += 1
    return x + 0.05 * rng.randn(n)


def test_integration_fault_signal_drops_health_and_alarms():
    fs = 12000
    defects = DefectFrequencies(bpfo=107.0, bpfi=162.0, ftf=12.0, bsf=70.0)
    band = (2000.0, 4500.0)
    healthy = np.vstack(
        [feature_vector(_noise(fs=fs, seed=s), fs, defects, band=band) for s in range(40)]
    )
    model = HealthIndexModel.fit(healthy, FEATURE_VECTOR_NAMES)

    # a held-out healthy sample stays OK with high health
    xh = feature_vector(_noise(fs=fs, seed=999), fs, defects, band=band)
    assert model.flag(xh) == HealthFlag.OK
    assert model.health_score(xh) > 0.8

    # an inner-race fault (modulating BPFI) drops health and alarms
    xf = feature_vector(_fault(fs=fs, f_fault=162.0, seed=7), fs, defects, band=band)
    assert model.flag(xf) == HealthFlag.ALARM
    assert model.health_score(xf) < model.health_score(xh)
