"""Tests for the physics-to-data bridge.

DIPPR-101 numeric targets are transcribed from Perry's 9th ed., Table 2-8 and
verified against the page (Tmin/Tmax check values + known normal boiling
points). The bubble-point method is cross-verified against Smith 9th ed.
Eq. 13.20. The affine-SBC fit is tested on a synthetic affine relationship
with known scale/bias (the real-data fit lives in the validation script,
since the benchmark data is gitignored).
"""

from __future__ import annotations

import math

import pytest

from ipis.module1_soft_sensor.physics_bridge.bridge import (
    AffineSBC,
    BridgeConfig,
    denormalize,
    physics_estimate,
)
from ipis.physics.bubble_point_inversion import light_key_fraction
from ipis.physics.dippr101 import N_BUTANE, N_HEXANE, N_PENTANE, dippr101_psat


class TestDIPPR101:
    """Vapor pressure vs Perry's Table 2-8 check values (P in Pa, T in K)."""

    def test_butane_tmin(self) -> None:
        assert dippr101_psat(134.86, N_BUTANE) == pytest.approx(0.674, rel=0.02)

    def test_butane_tmax(self) -> None:
        assert dippr101_psat(425.12, N_BUTANE) == pytest.approx(3.770e6, rel=0.01)

    def test_pentane_tmin(self) -> None:
        assert dippr101_psat(143.42, N_PENTANE) == pytest.approx(0.0686, rel=0.02)

    def test_hexane_tmax(self) -> None:
        assert dippr101_psat(507.6, N_HEXANE) == pytest.approx(3.045e6, rel=0.01)

    def test_butane_normal_boiling_point(self) -> None:
        # n-butane NBP ~ -0.5 C = 272.65 K, where Psat = 101325 Pa.
        assert dippr101_psat(272.65, N_BUTANE) == pytest.approx(101325, rel=0.03)

    def test_supercritical_raises(self) -> None:
        # Above n-butane t_max (425.12 K) the species is supercritical.
        with pytest.raises(ValueError, match="supercritical"):
            dippr101_psat(450.0, N_BUTANE)


class TestBubblePointInversion:
    """Light-key fraction by ideal-binary bubble-point inversion."""

    def test_fraction_in_unit_interval(self) -> None:
        # Tray-6 conditions: 106 C, 5 bar -> physical C4 fraction in [0, 1].
        x = light_key_fraction(106 + 273.15, 5e5)
        assert 0.0 <= x <= 1.0

    def test_monotonic_decreasing_in_temperature(self) -> None:
        # Hotter -> less C4 retained in the liquid (higher Psat_heavy).
        p = 5e5
        x_cool = light_key_fraction(104 + 273.15, p)
        x_hot = light_key_fraction(110 + 273.15, p)
        assert x_cool > x_hot

    def test_matches_closed_form(self) -> None:
        # Verify against the explicit modified-Raoult formula (gamma=1).
        T, P = 106 + 273.15, 5e5
        p4 = dippr101_psat(T, N_BUTANE)
        p6 = dippr101_psat(T, N_HEXANE)
        expected = (P - p6) / (p4 - p6)
        assert light_key_fraction(T, P, clip=False) == pytest.approx(expected, rel=1e-9)

    def test_light_key_supercritical_raises(self) -> None:
        with pytest.raises(ValueError, match="supercritical"):
            light_key_fraction(160 + 273.15, 5e5)  # 160 C > butane Tc (152 C)


class TestDenormalize:
    def test_endpoints(self) -> None:
        assert denormalize(0.0, 100.0, 112.0) == pytest.approx(100.0)
        assert denormalize(1.0, 100.0, 112.0) == pytest.approx(112.0)

    def test_midpoint(self) -> None:
        assert denormalize(0.5, 4.5, 5.5) == pytest.approx(5.0)


class TestPhysicsEstimate:
    def test_returns_unit_interval(self) -> None:
        # Normalized mid-range T and P should give a physical fraction.
        x = physics_estimate(0.5, 0.5, BridgeConfig())
        assert 0.0 <= x <= 1.0

    def test_lower_temp_gives_more_c4(self) -> None:
        # Lower normalized T (cooler tray) -> more C4 retained.
        assert physics_estimate(0.1, 0.5) > physics_estimate(0.9, 0.5)


class TestAffineSBC:
    """Affine output-SBC fit on a synthetic known relationship."""

    def test_recovers_known_scale_bias(self) -> None:
        # y = 2.5 * x + 0.1 exactly -> fit must recover scale=2.5, bias=0.1, R2=1.
        xs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
        ys = [2.5 * x + 0.1 for x in xs]
        sbc = AffineSBC().fit(xs, ys)
        assert sbc.scale == pytest.approx(2.5, rel=1e-9)
        assert sbc.bias == pytest.approx(0.1, rel=1e-9)
        assert sbc.r_squared == pytest.approx(1.0, abs=1e-9)
        assert sbc.n == 6

    def test_predict(self) -> None:
        sbc = AffineSBC().fit([0.0, 1.0], [1.0, 3.0])  # scale=2, bias=1
        assert sbc.predict(2.0) == pytest.approx(5.0)

    def test_partial_fit_r2(self) -> None:
        # Noisy-but-correlated data -> 0 < R2 < 1.
        xs = [0.0, 0.1, 0.2, 0.3, 0.4]
        ys = [0.02, 0.05, 0.03, 0.08, 0.10]  # roughly increasing
        sbc = AffineSBC().fit(xs, ys)
        assert 0.0 < sbc.r_squared <= 1.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            AffineSBC().fit([0.1, 0.2], [1.0])

    def test_zero_variance_raises(self) -> None:
        with pytest.raises(ValueError, match="zero variance"):
            AffineSBC().fit([0.3, 0.3, 0.3], [1.0, 2.0, 3.0])

    def test_too_few_points_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            AffineSBC().fit([0.5], [1.0])


def test_method_is_finite_and_sane() -> None:
    """End-to-end smoke: physics estimate feeds a sane affine fit."""
    t_norms = [i / 10 for i in range(11)]
    xs = [physics_estimate(t, 0.5) for t in t_norms]
    ys = [0.6 * x + 0.05 for x in xs]  # synthetic affine target
    sbc = AffineSBC().fit(xs, ys)
    assert math.isfinite(sbc.scale) and math.isfinite(sbc.bias)
    assert sbc.r_squared == pytest.approx(1.0, abs=1e-9)
