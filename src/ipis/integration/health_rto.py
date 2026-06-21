"""Conformal health-constrained RTO (decision D1) -- the §6 actionable corollary.

This is a NEW integration module, not an edit to Module 3's submitted
``rto_nlp.py`` (Paper 2, JPROCONT-D-26-00565). It rebuilds the same economic NLP
from *injected* parameters -- the fitted ``LnXbSurface`` coefficients and an
``EconomicsAnchor``-equivalent price set -- so Paper 2's code stays frozen, and
adds the similitude-departure (ψ-budget) constraint of
``docs/module4/formalization-spike.md`` §6:

    max  profit(R, D)
    s.t. ln-surface(R, D) <= ln(spec - backoff)                 (quality, Paper 2)
         2 (L1 ||psi1(u) - psi1*|| + L2 ||psi2(u) - psi2*||) <= eps   (§6, NEW)
         R, D in the surface trust box

Enforcing the second constraint certifies, per §5, ``P(S_k) >= 1 - (a1+a2) - eps``:
the RTO maximises profit subject to staying inside the similitude-departure
budget that keeps its own soft sensor calibrated and its own RUL bound valid.
When that constraint binds, the optimum is being traded away from the
health-blind economic optimum -- the money shot.

The economic objective mirrors ``rto_nlp.solve_rto`` exactly; the repo-only
consistency test (``pytest.importorskip('gekko')``) asserts that with a slack
``eps`` the health-constrained optimum reproduces the unconstrained Paper-2
optimum, guarding against drift. The ψ-budget value is the same quantity as
:func:`ipis.integration.psi.budget_penalty`, unit-tested here without GEKKO.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from ipis.integration.psi import (
    OperatingPoint,
    PsiConfig,
    budget_penalty,
    psi1,
)

_SQRT_EPS = 1e-12  # keeps the norm sqrt differentiable at the anchor
DEFAULT_SPEC_XB_C4 = 0.02
R_BOUNDS: tuple[float, float] = (0.8, 3.0)
D_BOUNDS: tuple[float, float] = (33.0, 37.0)


@dataclass(frozen=True)
class EconomicParams:
    """Scalar economics for building the GEKKO objective symbolically.

    Map from Module 3 on the repo::

        EconomicParams(
            c4_value_usd_per_kg=econ.c4_value_usd_per_kg,
            gasoline_value_usd_per_kg=econ.gasoline_value_usd_per_kg,
            energy_cost_usd_per_gj=econ.energy_cost_usd_per_gj,
            dhvap_kj_per_kmol=DHVAP_C6_KJ_PER_KMOL,
            m_lk_kg_per_kmol=M_C4_KG_PER_KMOL,
            m_hk_kg_per_kmol=M_C6_KG_PER_KMOL,
        )
    """

    c4_value_usd_per_kg: float
    gasoline_value_usd_per_kg: float
    energy_cost_usd_per_gj: float
    dhvap_kj_per_kmol: float
    m_lk_kg_per_kmol: float
    m_hk_kg_per_kmol: float


@dataclass(frozen=True)
class HealthRTOResult:
    """Solved health-constrained recommendation (mirrors ``RTOResult`` + budget)."""

    reflux_ratio: float
    distillate_kmol_h: float
    x_bottoms_lk: float
    reboiler_duty_kw: float
    profit_usd_per_h: float
    backoff: float
    eps: float
    budget_at_opt: float
    active_constraints: list[str] = field(default_factory=list)

    def to_state_bus_fields(self) -> dict[str, object]:
        return {
            "setpoint_recommendations": {
                "reflux_ratio": self.reflux_ratio,
                "distillate_kmol_h": self.distillate_kmol_h,
            },
            "active_constraints": list(self.active_constraints),
        }


def psi_budget_value(
    R: float,
    D: float,
    alpha: float,
    R_min: float,
    strip_factor: float,
    cfg: PsiConfig,
) -> float:
    """ψ-budget B(u) at a numeric operating point -- equals
    :func:`ipis.integration.psi.budget_penalty`. The pure-Python twin of the
    symbolic constraint built inside :func:`solve_health_constrained_rto`."""
    op = OperatingPoint(
        R=R,
        D=D,
        alpha=alpha,
        R_min=R_min,
        strip_factor=strip_factor,
        reflux_flow=R * D,
    )
    return budget_penalty(op, cfg)


def solve_health_constrained_rto(
    surface_coef: Sequence[float],
    econ: EconomicParams,
    *,
    alpha: float,
    R_min: float,
    strip_factor: float,
    cfg: PsiConfig,
    eps: float,
    spec_xb_c4: float = DEFAULT_SPEC_XB_C4,
    backoff: float = 0.0,
    feed_kmol_h: float = 100.0,
    z_lk: float = 0.35,
    r_bounds: tuple[float, float] = R_BOUNDS,
    d_bounds: tuple[float, float] = D_BOUNDS,
    rto_hold: bool = False,
) -> HealthRTOResult | None:
    """Solve the §6 health-constrained economic NLP with GEKKO/IPOPT.

    The regime ``(alpha, R_min, strip_factor)`` is the current-cycle
    linearisation point (from the plant's ``OperatingPoint``); within the solve
    these are constants and only ``R, D`` vary. Returns ``None`` on a drift hold.
    """
    if rto_hold:
        return None
    eff_spec = spec_xb_c4 - backoff
    if eff_spec <= 0.0:
        raise ValueError(f"backoff {backoff} consumes the whole spec {spec_xb_c4}.")
    if eps < 0.0:
        raise ValueError("eps (coverage budget) must be non-negative")

    from gekko import GEKKO  # lazy: keeps the module importable without gekko

    # Constant pieces of ||psi1 - psi1*|| (alpha, strip vary only across cycles).
    psi1_star = psi1(cfg.fortuna_op, cfg.scales)
    c_alpha = alpha / cfg.scales.alpha_scale - psi1_star[0]
    c_strip = strip_factor / cfg.scales.strip_scale - psi1_star[2]
    gill_star = psi1_star[1]
    gill_scale = cfg.scales.gilliland_scale
    ref = cfg.femto_ref_reflux_flow
    pscale = cfg.scales.pump_load_scale

    g = GEKKO(remote=False)
    # Warm start near quality feasibility: a tight (spec - backoff) is a narrow
    # corner of the box that IPOPT can miss from a mid-box start. Estimate the R
    # that meets the surface spec at mid-D (linear-in-R approximation) and start
    # there; this does not change the optimum, only the initial iterate.
    d_mid = sum(d_bounds) / 2.0
    lin_slope = surface_coef[1] + surface_coef[5] * d_mid
    if abs(lin_slope) > 1e-9:
        r_feas = (
            float(np.log(eff_spec))
            - surface_coef[0]
            - surface_coef[2] * d_mid
            - surface_coef[4] * d_mid * d_mid
        ) / lin_slope
        r0 = min(max(r_feas, r_bounds[0]), r_bounds[1])
    else:
        r0 = sum(r_bounds) / 2.0
    r = g.Var(value=r0, lb=r_bounds[0], ub=r_bounds[1])
    d = g.Var(value=sum(d_bounds) / 2, lb=d_bounds[0], ub=d_bounds[1])

    b = surface_coef
    ln_xb = b[0] + b[1] * r + b[2] * d + b[3] * r * r + b[4] * d * d + b[5] * r * d
    xb = g.exp(ln_xb)
    bottoms = feed_kmol_h - d
    b_lk = xb * bottoms
    b_hk = bottoms - b_lk
    d_lk = feed_kmol_h * z_lk - b_lk
    d_hk = d - d_lk
    duty_kw = (r + 1.0) * d * econ.dhvap_kj_per_kmol / 3600.0
    overhead_kg = d_lk * econ.m_lk_kg_per_kmol + d_hk * econ.m_hk_kg_per_kmol
    bottoms_kg = b_lk * econ.m_lk_kg_per_kmol + b_hk * econ.m_hk_kg_per_kmol
    profit = (
        overhead_kg * econ.c4_value_usd_per_kg
        + bottoms_kg * econ.gasoline_value_usd_per_kg
        - econ.energy_cost_usd_per_gj * duty_kw * 3600.0 / 1.0e6
    )

    # Quality constraint (Paper 2).
    g.Equation(ln_xb <= float(np.log(eff_spec)))

    # ψ-budget constraint (§6, NEW). gill term is the only R-dependent part of d1.
    gill = (r - R_min) / (r + 1.0)
    gill_term = gill / gill_scale - gill_star
    d1 = (c_alpha**2 + c_strip**2 + gill_term**2 + _SQRT_EPS) ** 0.5
    load = ((r * d) / ref) ** 3.0
    d2 = (((load - 1.0) / pscale) ** 2 + _SQRT_EPS) ** 0.5
    budget = 2.0 * (cfg.L1 * d1 + cfg.L2 * d2)
    g.Equation(budget <= eps)

    g.Maximize(profit)
    g.options.SOLVER = 3  # IPOPT
    try:
        g.solve(disp=False)
    except Exception:
        # An unsolvable joint quality+ψ-budget set means no setpoint can be
        # certified for S_k at this regime -> hold (no recommendation), the same
        # operational response as a drift hold. Re-run with disp=True to inspect.
        return None

    r_opt, d_opt = float(r.value[0]), float(d.value[0])
    ln_opt = (
        b[0]
        + b[1] * r_opt
        + b[2] * d_opt
        + b[3] * r_opt**2
        + b[4] * d_opt**2
        + b[5] * r_opt * d_opt
    )
    xb_opt = float(np.exp(ln_opt))
    duty_opt = (r_opt + 1.0) * d_opt * econ.dhvap_kj_per_kmol / 3600.0
    bottoms_o = feed_kmol_h - d_opt
    b_lk_o = xb_opt * bottoms_o
    profit_opt = (
        (b_lk_o * econ.m_lk_kg_per_kmol + (bottoms_o - b_lk_o) * econ.m_hk_kg_per_kmol)
        * econ.gasoline_value_usd_per_kg
        + (
            (feed_kmol_h * z_lk - b_lk_o) * econ.m_lk_kg_per_kmol
            + (d_opt - (feed_kmol_h * z_lk - b_lk_o)) * econ.m_hk_kg_per_kmol
        )
        * econ.c4_value_usd_per_kg
        - econ.energy_cost_usd_per_gj * duty_opt * 3600.0 / 1.0e6
    )

    budget_opt = psi_budget_value(r_opt, d_opt, alpha, R_min, strip_factor, cfg)
    tol = 1e-3
    active: list[str] = []
    if abs(ln_opt - float(np.log(eff_spec))) < tol:
        active.append("c4_spec_backoff")
    if abs(budget_opt - eps) < max(tol, 1e-3 * eps):
        active.append("psi_budget")
    if abs(r_opt - r_bounds[0]) < tol or abs(r_opt - r_bounds[1]) < tol:
        active.append("reflux_bound")
    if abs(d_opt - d_bounds[0]) < tol or abs(d_opt - d_bounds[1]) < tol:
        active.append("distillate_bound")

    return HealthRTOResult(
        reflux_ratio=r_opt,
        distillate_kmol_h=d_opt,
        x_bottoms_lk=xb_opt,
        reboiler_duty_kw=duty_opt,
        profit_usd_per_h=profit_opt,
        backoff=backoff,
        eps=eps,
        budget_at_opt=budget_opt,
        active_constraints=active,
    )
