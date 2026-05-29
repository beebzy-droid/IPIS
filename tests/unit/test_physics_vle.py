"""Physics-engine unit tests, validated against Perry's worked examples.

All numerical targets are transcribed directly from Perry's Chemical
Engineers' Handbook, 9th ed., and verified against the source page (not
from any secondary summary).

Verified source values (Perry's Example 4-11, acetone(1)/n-hexane(2)):
    Antoine (natural-log form, kPa, K):
        acetone:  A=14.3145, B=2756.22, C=-45.090
        n-hexane: A=13.8193, B=2696.04, C=-48.833
    At T = 325.15 K:  P1_sat = 87.616 kPa, P2_sat = 58.105 kPa
    Wilson params: V=(74.05, 131.61) cm3/mol, a=(985.05, 453.57) cal/mol
    At x1 = 0.40:  gamma1 = 1.8053, gamma2 = 1.2869
    BUBL P:        P = 108.134 kPa, y1 = 0.5851
"""

from __future__ import annotations

import pytest

from ipis.physics.activity import IdealSolution, WilsonBinary
from ipis.physics.antoine import AntoineParams, antoine_psat
from ipis.physics.vle import bubble_pressure

# Perry's Example 4-11 component definitions
ACETONE = AntoineParams(A=14.3145, B=2756.22, C=-45.090, name="acetone")
N_HEXANE = AntoineParams(A=13.8193, B=2696.04, C=-48.833, name="n-hexane")
WILSON = WilsonBinary(V=(74.05, 131.61), a=(985.05, 453.57))
T_EX = 325.15  # K


class TestAntoine:
    """Antoine vapor pressure vs. Perry's Example 4-11 values."""

    def test_acetone_psat(self) -> None:
        assert antoine_psat(T_EX, ACETONE) == pytest.approx(87.616, abs=0.01)

    def test_hexane_psat(self) -> None:
        assert antoine_psat(T_EX, N_HEXANE) == pytest.approx(58.105, abs=0.01)

    def test_natural_log_form_not_base10(self) -> None:
        """Guard against the base-10 error: base-10 would give ~29714 kPa."""
        assert antoine_psat(T_EX, ACETONE) < 200  # sane kPa, not tens of thousands

    def test_invalid_temperature_raises(self) -> None:
        with pytest.raises(ValueError, match="out of valid range"):
            antoine_psat(40.0, ACETONE)  # T + C < 0


class TestWilson:
    """Wilson activity coefficients vs. Perry's Example 4-11 values."""

    def test_gammas_at_x1_040(self) -> None:
        g1, g2 = WILSON.gamma([0.40, 0.60], T_EX)
        assert g1 == pytest.approx(1.8053, abs=0.001)
        assert g2 == pytest.approx(1.2869, abs=0.001)

    def test_binary_only(self) -> None:
        with pytest.raises(ValueError, match="binary"):
            WILSON.gamma([0.3, 0.3, 0.4], T_EX)


class TestIdealSolution:
    """Ideal model returns unity activity coefficients."""

    def test_all_unity(self) -> None:
        assert IdealSolution().gamma([0.4, 0.6], T_EX) == [1.0, 1.0]


class TestBubblePressureNonIdeal:
    """Full bubble-point vs. Perry's Example 4-11 (Wilson), the key fixture."""

    def test_bubble_pressure_and_vapor(self) -> None:
        P, y = bubble_pressure([0.40, 0.60], T_EX, [ACETONE, N_HEXANE], WILSON)
        assert P == pytest.approx(108.134, abs=0.05)
        assert y[0] == pytest.approx(0.5851, abs=0.001)


class TestBubblePressureIdeal:
    """Ideal-solution path (Debutanizer-relevant) is internally consistent."""

    def test_ideal_is_raoult(self) -> None:
        # With gamma=1, P must equal x1*P1sat + x2*P2sat exactly.
        P, _ = bubble_pressure([0.40, 0.60], T_EX, [ACETONE, N_HEXANE], IdealSolution())
        p1 = antoine_psat(T_EX, ACETONE)
        p2 = antoine_psat(T_EX, N_HEXANE)
        assert P == pytest.approx(0.40 * p1 + 0.60 * p2, rel=1e-12)

    def test_mole_fractions_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError, match="sum to 1"):
            bubble_pressure([0.4, 0.4], T_EX, [ACETONE, N_HEXANE], IdealSolution())
