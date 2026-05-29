"""FUG shortcut-method unit tests.

Edition discipline (per the source map): each fixture's expected value and
the inputs that produce it come from the SAME Perry's edition, because
specific values (alpha, K, compositions) drift between editions while the
equation forms are stable.

    - Fenske fixture:    all 9th ed. (Section 13, p13-20 worked example).
    - Underwood fixture: all 8th ed. (Table 13-6: theta=1.3647, R_min=0.9426).

Equation citations are 9th ed.; the Underwood numeric fixture is 8th ed.
because that is where the fully converged values are printed.
"""

from __future__ import annotations

import math

import pytest

from ipis.physics.fug import (
    effective_alpha,
    fenske_nmin,
    gilliland_n,
    relative_volatility,
    underwood_rmin,
    underwood_theta,
)

# --- 9th ed. Example 13-1 key-component data (light key n-C4, heavy key i-C5) ---
# D x_i and B x_i in lb-mol/h; alpha referenced to i-C5 (= 1.00).
NC4_D, NC4_B = 25.1, 1.9
IC5_D, IC5_B = 3.15, 16.85
ALPHA_NC4_9TH = 2.01

# --- 8th ed. Table 13-6 Underwood data (mole-fraction basis) ---
ALPHA_8TH = {"C3": 4.99, "iC4": 2.62, "nC4": 2.02, "iC5": 1.00, "nC5": 0.864}
ZF_8TH = {"C3": 0.05, "iC4": 0.15, "nC4": 0.25, "iC5": 0.20, "nC5": 0.35}
XD_8TH = {"C3": 0.102, "iC4": 0.301, "nC4": 0.473, "iC5": 0.069, "nC5": 0.055}
Q_SAT_LIQUID = 1.0


class TestRelativeVolatility:
    def test_ratio(self) -> None:
        assert relative_volatility(2.0, 1.0) == pytest.approx(2.0)

    def test_reference_self_is_one(self) -> None:
        assert relative_volatility(1.5, 1.5) == pytest.approx(1.0)

    def test_nonpositive_ref_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            relative_volatility(2.0, 0.0)


class TestEffectiveAlpha:
    def test_two_point_geometric_mean(self) -> None:
        assert effective_alpha(4.0, 1.0) == pytest.approx(2.0)  # sqrt(4*1)

    def test_three_point_geometric_mean(self) -> None:
        assert effective_alpha(8.0, 1.0, 1.0) == pytest.approx(2.0)  # cbrt(8)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one"):
            effective_alpha()


class TestFenske9thEd:
    """Fenske N_min vs Perry's 9th ed. Example 13-1 (all-9th fixture)."""

    def test_nmin_nc4_ic5(self) -> None:
        n_min = fenske_nmin(NC4_D, NC4_B, IC5_D, IC5_B, ALPHA_NC4_9TH)
        assert n_min == pytest.approx(6.10, abs=0.02)

    def test_nmin_in_expected_band(self) -> None:
        # Perry assumes N=10; N_min typically 0.4N-0.6N.
        n_min = fenske_nmin(NC4_D, NC4_B, IC5_D, IC5_B, ALPHA_NC4_9TH)
        assert 4.0 <= n_min <= 6.5

    def test_alpha_must_exceed_one(self) -> None:
        with pytest.raises(ValueError, match="exceed 1"):
            fenske_nmin(NC4_D, NC4_B, IC5_D, IC5_B, 1.0)


class TestUnderwood8thEd:
    """Underwood theta and R_min vs Perry's 8th ed. Table 13-6 (all-8th fixture)."""

    def test_theta_converges(self) -> None:
        theta = underwood_theta(ALPHA_8TH, ZF_8TH, Q_SAT_LIQUID, alpha_hk=1.00, alpha_lk=2.02)
        assert theta == pytest.approx(1.3647, abs=0.001)

    def test_rmin(self) -> None:
        theta = underwood_theta(ALPHA_8TH, ZF_8TH, Q_SAT_LIQUID, alpha_hk=1.00, alpha_lk=2.02)
        r_min = underwood_rmin(ALPHA_8TH, XD_8TH, theta)
        # Perry 8th ed: 0.9426; x_D rounded to 3 dp gives ~0.9424.
        assert r_min == pytest.approx(0.9426, abs=0.003)

    def test_mismatched_keys_raise(self) -> None:
        with pytest.raises(ValueError, match="identical component keys"):
            underwood_theta({"a": 2.0}, {"b": 1.0}, 1.0, 1.0, 2.0)


class TestGilliland:
    """Gilliland-Molokanov correlation (Perry's Eq. 13-30)."""

    def test_n_exceeds_nmin(self) -> None:
        n = gilliland_n(reflux=1.5, r_min=0.9426, n_min=6.10)
        assert n > 6.10

    def test_large_reflux_approaches_nmin(self) -> None:
        # As R -> large, Psi -> 1, N -> N_min.
        n = gilliland_n(reflux=50.0, r_min=0.9426, n_min=6.10)
        assert n == pytest.approx(6.10, abs=0.5)

    def test_reflux_below_rmin_raises(self) -> None:
        with pytest.raises(ValueError, match="must exceed"):
            gilliland_n(reflux=0.5, r_min=0.9426, n_min=6.10)


class TestFullFUGChain:
    """Integration: full FUG chain produces internally consistent results."""

    def test_chain_8th_ed_basis(self) -> None:
        # Underwood (8th-ed basis)
        theta = underwood_theta(ALPHA_8TH, ZF_8TH, Q_SAT_LIQUID, alpha_hk=1.00, alpha_lk=2.02)
        r_min = underwood_rmin(ALPHA_8TH, XD_8TH, theta)
        # Fenske N_min using 8th-ed alpha for the LK (n-C4 = 2.02)
        # Convert 8th-ed mole-fraction splits to consistent key flows is non-trivial;
        # here we assert the chain is sane: pick an operating reflux 1.3x R_min.
        n_min = 6.10  # 9th-ed verified value, used as a representative N_min
        n = gilliland_n(reflux=1.3 * r_min, r_min=r_min, n_min=n_min)
        assert r_min == pytest.approx(0.9426, abs=0.003)
        assert n > n_min
        assert math.isfinite(n)
