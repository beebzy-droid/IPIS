"""3A economic RTO: response surface + GEKKO NLP (fixed-margin baseline).

Architecture (scoping D1-C, D3, D5-3A):
    ColumnModel (shortcut now, DWSIM/GPR surrogate at 3B)
        -> grid evaluation -> quadratic surface on ln(x_bottoms_LK)
        -> GEKKO NLP: max profit s.t. x_B,C4 <= spec - backoff
        -> RTOResult -> state_bus fields (D4)

Only ln(x_B) needs a fitted surface: reboiler duty is exactly linear in the
decision variables, Q_kW = (R + 1) * D * dHvap / 3600, and the binary mass
balance makes all four stream flows analytic given x_B:
    b_lk = x_B (F - D);  b_hk = (F - D) - b_lk
    d_lk = F z - b_lk;   d_hk = D - d_lk
Revenue is the two-stream mass-based structure of EconomicsAnchor (overhead
at the C4 price, bottoms at the gasoline price), which makes the bottoms C4
spec ACTIVE at the economic optimum — the structure 3B's back-off needs.

The back-off parameter is the 3B hook: here a fixed margin; at 3B it is
mapped from Module 1's calibrated conformal interval width (the paper-2
contribution). The NLP layer does not change between the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ipis.module3_rto.column_model import (
    DHVAP_C6_KJ_PER_KMOL,
    ColumnModel,
    ShortcutColumnModel,
)
from ipis.module3_rto.economics import (
    M_C4_KG_PER_KMOL,
    M_C6_KG_PER_KMOL,
    EconomicsAnchor,
)

# Decision-variable box (the region the surface is fitted and trusted on).
R_BOUNDS: tuple[float, float] = (0.8, 3.0)
D_BOUNDS: tuple[float, float] = (33.0, 37.0)
DEFAULT_SPEC_XB_C4: float = 0.02  # 2 mol% C4 in stabilized gasoline


@dataclass(frozen=True)
class LnXbSurface:
    """Quadratic surface ln(x_B) ~ b0 + b1 R + b2 D + b3 R^2 + b4 D^2 + b5 R D.

    Attributes:
        coef: The six coefficients (b0..b5).
        r_squared: Fit quality on the training grid.
        max_abs_resid: Worst-case |ln residual| on the grid (a multiplicative
            model-error band: exp(max_abs_resid) on x_B).
    """

    coef: tuple[float, float, float, float, float, float]
    r_squared: float
    max_abs_resid: float

    def predict_ln(self, r: float, d: float) -> float:
        """ln(x_B) at (R, D) — plain-float path for verification."""
        b = self.coef
        return b[0] + b[1] * r + b[2] * d + b[3] * r * r + b[4] * d * d + b[5] * r * d


def fit_ln_xb_surface(
    model: ColumnModel,
    r_bounds: tuple[float, float] = R_BOUNDS,
    d_bounds: tuple[float, float] = D_BOUNDS,
    n_grid: int = 9,
) -> LnXbSurface:
    """Fit the quadratic ln(x_B) surface on an n_grid x n_grid evaluation grid.

    Infeasible grid points (model raises ValueError) are skipped; the fit
    requires at least 12 feasible points (2x the parameter count).

    Args:
        model: Any ColumnModel (shortcut at 3A, DWSIM/GPR surrogate at 3B).
        r_bounds: Reflux-ratio box.
        d_bounds: Distillate-rate box.
        n_grid: Grid points per axis.

    Returns:
        The fitted surface with fit diagnostics.

    Raises:
        ValueError: If fewer than 12 grid points are feasible.
    """
    rows: list[tuple[float, float, float]] = []
    for r in np.linspace(*r_bounds, n_grid):
        for d in np.linspace(*d_bounds, n_grid):
            try:
                resp = model.evaluate(float(r), float(d))
            except ValueError:
                continue
            if resp.x_bottoms_lk > 0.0:
                rows.append((float(r), float(d), float(np.log(resp.x_bottoms_lk))))
    if len(rows) < 12:
        raise ValueError(f"Only {len(rows)} feasible grid points; need >= 12.")
    arr = np.asarray(rows)
    r, d, y = arr[:, 0], arr[:, 1], arr[:, 2]
    x_mat = np.column_stack([np.ones_like(r), r, d, r * r, d * d, r * d])
    coef, *_ = np.linalg.lstsq(x_mat, y, rcond=None)
    resid = y - x_mat @ coef
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return LnXbSurface(
        coef=tuple(float(c) for c in coef),
        r_squared=1.0 - ss_res / ss_tot,
        max_abs_resid=float(np.abs(resid).max()),
    )


@dataclass(frozen=True)
class RTOResult:
    """Solved RTO recommendation.

    Attributes:
        reflux_ratio: Recommended reflux-ratio setpoint.
        distillate_kmol_h: Recommended distillate-rate setpoint.
        x_bottoms_lk: Surface-predicted bottoms C4 at the optimum.
        reboiler_duty_kw: Reboiler duty at the optimum.
        profit_usd_per_h: Objective value.
        backoff: The constraint back-off applied (3B: from M1 intervals).
        active_constraints: Names of constraints binding at the optimum.
    """

    reflux_ratio: float
    distillate_kmol_h: float
    x_bottoms_lk: float
    reboiler_duty_kw: float
    profit_usd_per_h: float
    backoff: float
    active_constraints: list[str] = field(default_factory=list)

    def to_state_bus_fields(self) -> dict[str, object]:
        """Map to OperationalState fields (scoping D4, interface B)."""
        return {
            "setpoint_recommendations": {
                "reflux_ratio": self.reflux_ratio,
                "distillate_kmol_h": self.distillate_kmol_h,
            },
            "active_constraints": list(self.active_constraints),
        }


def solve_rto(
    surface: LnXbSurface,
    economics: EconomicsAnchor | None = None,
    spec_xb_c4: float = DEFAULT_SPEC_XB_C4,
    backoff: float = 0.0,
    feed_kmol_h: float = 100.0,
    z_lk: float = 0.35,
    r_bounds: tuple[float, float] = R_BOUNDS,
    d_bounds: tuple[float, float] = D_BOUNDS,
    rto_hold: bool = False,
) -> RTOResult | None:
    """Solve the constrained economic NLP with GEKKO/IPOPT.

        max  revenue(d_lk, d_hk, b_lk, b_hk) - c_GJ * (R+1) D dHvap / 1e6
        s.t. ln-surface(R, D) <= ln(spec - backoff)
             R, D in bounds

    Args:
        surface: Fitted ln(x_B) surface.
        economics: Price anchor (literature defaults if None).
        spec_xb_c4: Hard quality spec on bottoms C4 mole fraction.
        backoff: Constraint margin. 0 = no back-off; fixed value = the 3A
            baseline; M1-interval-driven value = the 3B contribution.
        feed_kmol_h: Feed rate (must match the surface's model).
        z_lk: Feed C4 fraction (must match the surface's model).
        r_bounds: Reflux box (surface trust region).
        d_bounds: Distillate box (surface trust region).
        rto_hold: D4 drift-alarm hold — if True, return None (no
            recommendation is published while Module 1 reports drift).

    Returns:
        RTOResult, or None when held.

    Raises:
        ValueError: If backoff leaves no feasible spec headroom.
        RuntimeError: If IPOPT fails to converge.
    """
    if rto_hold:
        return None
    eff_spec = spec_xb_c4 - backoff
    if eff_spec <= 0.0:
        raise ValueError(f"backoff {backoff} consumes the whole spec {spec_xb_c4}.")
    econ = economics or EconomicsAnchor()

    from gekko import GEKKO  # lazy: keeps module importable without gekko

    g = GEKKO(remote=False)
    r = g.Var(value=sum(r_bounds) / 2, lb=r_bounds[0], ub=r_bounds[1])
    d = g.Var(value=sum(d_bounds) / 2, lb=d_bounds[0], ub=d_bounds[1])
    b = surface.coef
    ln_xb = b[0] + b[1] * r + b[2] * d + b[3] * r * r + b[4] * d * d + b[5] * r * d
    xb = g.exp(ln_xb)
    bottoms = feed_kmol_h - d
    b_lk = xb * bottoms
    b_hk = bottoms - b_lk
    d_lk = feed_kmol_h * z_lk - b_lk
    d_hk = d - d_lk
    duty_kw = (r + 1.0) * d * DHVAP_C6_KJ_PER_KMOL / 3600.0
    overhead_kg = d_lk * M_C4_KG_PER_KMOL + d_hk * M_C6_KG_PER_KMOL
    bottoms_kg = b_lk * M_C4_KG_PER_KMOL + b_hk * M_C6_KG_PER_KMOL
    profit = (
        overhead_kg * econ.c4_value_usd_per_kg
        + bottoms_kg * econ.gasoline_value_usd_per_kg
        - econ.energy_cost_usd_per_gj * duty_kw * 3600.0 / 1.0e6
    )
    g.Equation(ln_xb <= float(np.log(eff_spec)))
    g.Maximize(profit)
    g.options.SOLVER = 3  # IPOPT
    try:
        g.solve(disp=False)
    except Exception as exc:  # gekko raises bare Exception on solver failure
        raise RuntimeError(f"IPOPT failed: {exc}") from exc

    r_opt, d_opt = float(r.value[0]), float(d.value[0])
    ln_opt = surface.predict_ln(r_opt, d_opt)
    xb_opt = float(np.exp(ln_opt))
    duty_opt = (r_opt + 1.0) * d_opt * DHVAP_C6_KJ_PER_KMOL / 3600.0
    bottoms_o = feed_kmol_h - d_opt
    b_lk_o = xb_opt * bottoms_o
    profit_opt = econ.profit_usd_per_h(
        feed_kmol_h * z_lk - b_lk_o,
        d_opt - (feed_kmol_h * z_lk - b_lk_o),
        b_lk_o,
        bottoms_o - b_lk_o,
        duty_opt,
    )

    tol = 1e-3
    active: list[str] = []
    if abs(ln_opt - float(np.log(eff_spec))) < tol:
        active.append("c4_spec_backoff")
    if abs(r_opt - r_bounds[0]) < tol or abs(r_opt - r_bounds[1]) < tol:
        active.append("reflux_bound")
    if abs(d_opt - d_bounds[0]) < tol or abs(d_opt - d_bounds[1]) < tol:
        active.append("distillate_bound")

    return RTOResult(
        reflux_ratio=r_opt,
        distillate_kmol_h=d_opt,
        x_bottoms_lk=xb_opt,
        reboiler_duty_kw=duty_opt,
        profit_usd_per_h=profit_opt,
        backoff=backoff,
        active_constraints=active,
    )


def run_case_study(backoffs: tuple[float, ...] = (0.0, 0.005)) -> list[RTOResult]:
    """The 3A closeout case study: solve at each back-off on the shortcut model."""
    surface = fit_ln_xb_surface(ShortcutColumnModel())
    results = []
    for bo in backoffs:
        res = solve_rto(surface, backoff=bo)
        if res is not None:
            results.append(res)
    return results
