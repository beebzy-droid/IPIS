"""Tests for the Module 2 bearing fault-frequency physics layer.

The headline test is `test_cwru_6205_self_consistency`: the verify-before-load-
bearing gate. It asserts the 6205 geometry reproduces Smith & Randall (2015)
Table 2's published multipliers to <1%. If this fails, the geometry is wrong and
nothing downstream is trustworthy.
"""

from __future__ import annotations

import math

import pytest

from ipis.module2_pdm.physics.bearing_frequencies import (
    CWRU_DE_6205,
    SELF_CONSISTENCY_TOL,
    BearingGeometry,
    DefectMultipliers,
    frequencies_from_geometry,
    multipliers_from_geometry,
    self_consistency_residual,
)


def test_cwru_6205_self_consistency():
    """Geometry reproduces Smith & Randall 2015 Table 2 multipliers to <1%."""
    residual = self_consistency_residual(CWRU_DE_6205.geometry, CWRU_DE_6205.published)
    assert residual < SELF_CONSISTENCY_TOL, f"6205 geometry residual {residual:.4f} exceeds tol"


def test_cwru_6205_multipliers_match_table2():
    """Each derived multiplier matches the published value to 3 decimals."""
    m = multipliers_from_geometry(CWRU_DE_6205.geometry)
    pub = CWRU_DE_6205.published
    assert m.bpfo == pytest.approx(pub.bpfo, abs=1e-3)
    assert m.bpfi == pytest.approx(pub.bpfi, abs=1e-3)
    assert m.ftf == pytest.approx(pub.ftf, abs=1e-3)
    assert m.bsf == pytest.approx(pub.bsf, abs=1e-3)


def test_bpfi_plus_bpfo_equals_n_times_fr():
    """Kinematic identity: BPFI + BPFO = n * f_r (the (1-g)+(1+g) cancellation)."""
    m = multipliers_from_geometry(CWRU_DE_6205.geometry)
    assert m.bpfo + m.bpfi == pytest.approx(CWRU_DE_6205.geometry.n_rolling_elements, abs=1e-9)


def test_ftf_is_half_of_bpfo_over_n():
    """FTF = BPFO / n (cage passes one element-spacing slower)."""
    geom = CWRU_DE_6205.geometry
    m = multipliers_from_geometry(geom)
    assert m.ftf == pytest.approx(m.bpfo / geom.n_rolling_elements, abs=1e-9)


def test_at_shaft_hz_scales_linearly():
    """Hz = multiplier * shaft_hz; CWRU ~1772 rpm = 29.53 Hz example."""
    shaft_hz = 1772.0 / 60.0
    m = multipliers_from_geometry(CWRU_DE_6205.geometry)
    f = frequencies_from_geometry(CWRU_DE_6205.geometry, shaft_hz)
    assert f.bpfo == pytest.approx(m.bpfo * shaft_hz, rel=1e-9)
    assert f.bpfi == pytest.approx(m.bpfi * shaft_hz, rel=1e-9)
    # sanity: BPFI for a ~29.5 Hz shaft lands in the expected ~160 Hz band
    assert 150.0 < f.bpfi < 170.0


def test_zero_shaft_hz_gives_zero():
    f = frequencies_from_geometry(CWRU_DE_6205.geometry, 0.0)
    assert (f.bpfo, f.bpfi, f.ftf, f.bsf) == (0.0, 0.0, 0.0, 0.0)


def test_contact_angle_reduces_spread():
    """Non-zero contact angle shrinks gamma, pulling BPFO/BPFI toward n/2."""
    base = BearingGeometry(9, 0.3126, 1.537, contact_angle_rad=0.0)
    angled = BearingGeometry(9, 0.3126, 1.537, contact_angle_rad=math.radians(30))
    mb, ma = multipliers_from_geometry(base), multipliers_from_geometry(angled)
    assert ma.bpfi < mb.bpfi
    assert ma.bpfo > mb.bpfo


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_rolling_elements": 0, "ball_diameter": 1.0, "pitch_diameter": 5.0},
        {"n_rolling_elements": 9, "ball_diameter": 5.0, "pitch_diameter": 1.0},
        {"n_rolling_elements": 9, "ball_diameter": 0.0, "pitch_diameter": 5.0},
    ],
)
def test_invalid_geometry_rejected(kwargs):
    with pytest.raises(ValueError):
        BearingGeometry(**kwargs)


def test_negative_shaft_hz_rejected():
    with pytest.raises(ValueError):
        DefectMultipliers(1, 2, 3, 4).at_shaft_hz(-1.0)
