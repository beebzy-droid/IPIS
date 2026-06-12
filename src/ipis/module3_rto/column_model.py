"""Rating-mode column model for the 3A debutanizer RTO skeleton.

The RTO needs a column in RATING mode: the column exists (N fixed), the
decision variables are reflux ratio R and distillate rate D, and the model
returns the resulting bottoms C4 slippage and reboiler duty. The repo's FUG
module (Perry's 9th ed., Sec. 13; ADR-004) runs in DESIGN mode (split in,
N out), so this module inverts it: for fixed N, solve the 1-D root problem
"which LK recovery makes Gilliland return exactly N_column?" via brentq.

This shortcut model is the 3A STAND-IN for the DWSIM twin. Both sit behind
the same ``ColumnModel`` protocol; at 3B the GPR-over-DWSIM surrogate
(ADR-006) drops into the same slot with zero changes to the NLP layer.

Binary system: n-butane (LK) / n-hexane (HK proxy for stabilized gasoline),
consistent with the Module 1 physics bridge (tray-6 T in [100, 112] C,
column P in [4.5, 5.5] bar). Constants verified via CoolProp at
mid-envelope conditions:
    alpha(nC4/nC6) = 5.97 at 106 C (sat-pressure ratio)
    dHvap(nC6, 110 C) = 25.93 kJ/mol  (boilup is hexane-rich; nC4 is near
    its 152 C critical point, so the nC4 latent heat is NOT the right basis)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from scipy.optimize import brentq

from ipis.module3_rto.economics import DHVAP_C6_KJ_PER_KMOL
from ipis.physics.fug import fenske_nmin, gilliland_n, underwood_rmin, underwood_theta

# --- 3A nominal column (twin spec, docs/module3/twin-spec-3a.md) ---
ALPHA_LK: float = 5.97  # nC4 vs nC6 at 106 C, 4.9 bar (CoolProp)
N_STAGES: float = 8.0  # theoretical, incl. reboiler (see twin-spec-3a.md, decision T3)
FEED_KMOL_H: float = 100.0
Z_LK: float = 0.35  # C4 fraction in a representative stabilizer feed
Q_FEED: float = 1.0  # saturated liquid


@dataclass(frozen=True)
class ColumnResponse:
    """Steady-state column response at one (R, D) operating point."""

    reflux_ratio: float
    distillate_kmol_h: float
    x_bottoms_lk: float
    x_distillate_lk: float
    reboiler_duty_kw: float
    c4_product_kmol_h: float


class ColumnModel(Protocol):
    """The slot the 3B DWSIM/GPR surrogate fills (ADR-006)."""

    def evaluate(self, reflux_ratio: float, distillate_kmol_h: float) -> ColumnResponse:
        """Steady-state response at the given operating point."""
        ...


@dataclass(frozen=True)
class ShortcutColumnModel:
    """Fixed-N FUG rating model (binary LK/HK).

    For a candidate LK recovery r (fraction of feed LK leaving overhead),
    the binary mass balance with fixed D gives all four key flows; Fenske
    gives N_min, Underwood gives R_min, and Gilliland maps (R, R_min, N_min)
    to an implied stage count. The recovery the column actually delivers is
    the root of N_implied(r) - N_column = 0.

    Attributes:
        alpha_lk: LK relative volatility (HK reference).
        n_stages: Fixed theoretical stage count (incl. reboiler).
        feed_kmol_h: Feed rate.
        z_lk: LK feed mole fraction.
        q_feed: Feed thermal condition (1.0 = saturated liquid).
    """

    alpha_lk: float = ALPHA_LK
    n_stages: float = N_STAGES
    feed_kmol_h: float = FEED_KMOL_H
    z_lk: float = Z_LK
    q_feed: float = Q_FEED

    def _flows(self, recovery: float, distillate: float) -> tuple[float, float, float, float]:
        """Key-component flows (d_lk, b_lk, d_hk, b_hk) for an LK recovery."""
        f_lk = self.feed_kmol_h * self.z_lk
        f_hk = self.feed_kmol_h * (1.0 - self.z_lk)
        d_lk = f_lk * recovery
        b_lk = f_lk - d_lk
        d_hk = distillate - d_lk
        b_hk = f_hk - d_hk
        return d_lk, b_lk, d_hk, b_hk

    def _implied_stages(self, recovery: float, reflux: float, distillate: float) -> float:
        """Gilliland stage count implied by a candidate recovery."""
        d_lk, b_lk, d_hk, b_hk = self._flows(recovery, distillate)
        n_min = fenske_nmin(d_lk, b_lk, d_hk, b_hk, self.alpha_lk)
        alphas = {"lk": self.alpha_lk, "hk": 1.0}
        z = {"lk": self.z_lk, "hk": 1.0 - self.z_lk}
        theta = underwood_theta(alphas, z, self.q_feed, 1.0, self.alpha_lk)
        x_d = {"lk": d_lk / distillate, "hk": d_hk / distillate}
        r_min = underwood_rmin(alphas, x_d, theta)
        if reflux <= r_min:
            return math.inf  # infeasible reflux: pushes the root to lower recovery
        return gilliland_n(reflux, r_min, n_min)

    def evaluate(self, reflux_ratio: float, distillate_kmol_h: float) -> ColumnResponse:
        """Steady-state response at (R, D) for the fixed-N column.

        Args:
            reflux_ratio: Operating reflux ratio R (> 0).
            distillate_kmol_h: Distillate rate D; must leave all four key
                flows positive (0 < D, D > tiny LK overhead, D < total feed
                of either bound).

        Returns:
            ColumnResponse with compositions, duty, and C4 product rate.

        Raises:
            ValueError: If (R, D) admits no physical binary split.
        """
        f_lk = self.feed_kmol_h * self.z_lk
        # Recovery bounds keeping all four key flows strictly positive.
        eps = 1e-6
        lo = max(eps, (distillate_kmol_h - (self.feed_kmol_h - f_lk)) / f_lk + eps)
        hi = min(1.0 - eps, distillate_kmol_h / f_lk - eps)
        if not lo < hi:
            raise ValueError(
                f"No physical split at D={distillate_kmol_h} (recovery bounds [{lo}, {hi}])."
            )

        def residual(r: float) -> float:
            n = self._implied_stages(r, reflux_ratio, distillate_kmol_h)
            return self.n_stages - n if math.isfinite(n) else -1.0

        # residual > 0 where the column has spare stages (low recovery),
        # < 0 where the demanded split exceeds the column. Root = delivered split.
        if residual(hi) >= 0.0:
            r_star = hi  # column can do better than the mass-balance ceiling
        elif residual(lo) <= 0.0:
            raise ValueError(
                f"Column infeasible at R={reflux_ratio}, D={distillate_kmol_h}: "
                "even the loosest split needs more than N stages."
            )
        else:
            r_star = brentq(residual, lo, hi, xtol=1e-10)

        d_lk, b_lk, d_hk, b_hk = self._flows(r_star, distillate_kmol_h)
        bottoms = b_lk + b_hk
        vapor_kmol_h = (reflux_ratio + 1.0) * distillate_kmol_h
        duty_kw = vapor_kmol_h * DHVAP_C6_KJ_PER_KMOL / 3600.0
        return ColumnResponse(
            reflux_ratio=reflux_ratio,
            distillate_kmol_h=distillate_kmol_h,
            x_bottoms_lk=b_lk / bottoms,
            x_distillate_lk=d_lk / distillate_kmol_h,
            reboiler_duty_kw=duty_kw,
            c4_product_kmol_h=d_lk,
        )
