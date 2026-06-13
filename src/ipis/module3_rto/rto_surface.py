"""Surface-agnostic RTO solver for 3B.

The 3A solver (`rto_nlp.solve_rto`) embeds the quadratic coefficients in a
GEKKO NLP. 3B's surface is a GP (a kernel sum, not a polynomial) and its
back-off is operating-point-dependent (the conformal half-width varies with
the sensor input), so a GEKKO embedding is awkward. The decision box is 2-D
and bounded, so a dense grid + local refine is robust, derivative-free, and
handles an arbitrary back-off callable — the same solver serves 3B.1
(constant back-off, GPR surface) and 3B.2/3B.3 (interval-driven back-off).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ipis.module3_rto.economics import (
    DHVAP_C6_KJ_PER_KMOL,
    EconomicsAnchor,
)
from ipis.module3_rto.rto_nlp import D_BOUNDS, DEFAULT_SPEC_XB_C4, R_BOUNDS

XbSurface = Callable[[float, float], float]
BackoffFn = Callable[[float, float], float]


@dataclass(frozen=True)
class SurfaceRTOResult:
    """RTO optimum on a generic surface."""

    reflux_ratio: float
    distillate_kmol_h: float
    x_bottoms_lk: float
    backoff_at_opt: float
    reboiler_duty_kw: float
    profit_usd_per_h: float
    feasible_found: bool
    active_constraints: list[str] = field(default_factory=list)


def solve_rto_surface(
    xb_surface: XbSurface,
    economics: EconomicsAnchor | None = None,
    spec_xb_c4: float = DEFAULT_SPEC_XB_C4,
    backoff: float | BackoffFn = 0.0,
    feed_kmol_h: float = 100.0,
    z_lk: float = 0.35,
    r_bounds: tuple[float, float] = R_BOUNDS,
    d_bounds: tuple[float, float] = D_BOUNDS,
    n_grid: int = 241,
) -> SurfaceRTOResult | None:
    """Maximize two-stream profit s.t. xB + backoff <= spec on a grid.

    Args:
        xb_surface: Callable (R, D) -> x_B (e.g. GPRSurface.predict).
        economics: Price anchor (literature defaults if None).
        spec_xb_c4: Bottoms C4 spec.
        backoff: Constant margin, or a callable (R, D) -> margin (the
            interval-driven chance-constraint back-off in 3B.2/3B.3).
        feed_kmol_h, z_lk: Feed basis (match the surface's twin).
        r_bounds, d_bounds: Decision box (the surface trust region).
        n_grid: Grid points per axis.

    Returns:
        The feasible max-profit point, or None if the box has no feasible point.
    """
    econ = economics or EconomicsAnchor()
    bo_fn: BackoffFn = backoff if callable(backoff) else (lambda r, d: float(backoff))

    rs = np.linspace(*r_bounds, n_grid)
    ds = np.linspace(*d_bounds, n_grid)
    best: SurfaceRTOResult | None = None
    for r in rs:
        for d in ds:
            xb = float(xb_surface(float(r), float(d)))
            if not np.isfinite(xb) or xb <= 0.0:
                continue
            bo = bo_fn(float(r), float(d))
            if xb + bo > spec_xb_c4:
                continue  # infeasible under the (possibly adaptive) back-off
            bottoms = feed_kmol_h - d
            b_lk = xb * bottoms
            b_hk = bottoms - b_lk
            d_lk = feed_kmol_h * z_lk - b_lk
            d_hk = d - d_lk
            if d_lk < 0 or d_hk < 0 or b_hk < 0:
                continue
            duty = (r + 1.0) * d * DHVAP_C6_KJ_PER_KMOL / 3600.0
            profit = econ.profit_usd_per_h(d_lk, d_hk, b_lk, b_hk, duty)
            if best is None or profit > best.profit_usd_per_h:
                active = []
                if abs(xb + bo - spec_xb_c4) < 5e-4:
                    active.append("c4_spec_backoff")
                best = SurfaceRTOResult(
                    reflux_ratio=float(r),
                    distillate_kmol_h=float(d),
                    x_bottoms_lk=xb,
                    backoff_at_opt=float(bo),
                    reboiler_duty_kw=float(duty),
                    profit_usd_per_h=float(profit),
                    feasible_found=True,
                    active_constraints=active,
                )
    return best
