"""head_to_head.py — 3B.3: interval-driven vs fixed-margin RTO.

The decision (scoping D4): compare profit at EQUAL constraint-violation rate,
not raw profit. Both methods choose a setpoint by maximizing profit on the
nominal (z=0.35) surrogate under a back-off; the difference is the back-off.

  - fixed margin b: constant; sweep b -> a (violation, profit) frontier.
  - interval-driven: heteroscedastic conformal half-width C+(operating point);
    sweep alpha -> its own frontier (its violation rate ~ alpha by coverage).

A setpoint's violation rate is the fraction of feed-z draws for which the TRUE
xB (the 3-D truth surface) exceeds spec; its profit is the mean profit over the
same draws. The headline is the profit gap at the matched violation rate the
90% guarantee delivers.

Open-loop (scoping D6): one RTO setpoint per back-off level, evaluated over the
feed ensemble; no closed-loop integrator (that is 3C).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ipis.module3_rto.economics import (
    DHVAP_C6_KJ_PER_KMOL,
    EconomicsAnchor,
)
from ipis.module3_rto.rto_nlp import DEFAULT_SPEC_XB_C4
from ipis.module3_rto.rto_surface import solve_rto_surface
from ipis.module3_rto.surrogate import TruthSurface3D


@dataclass(frozen=True)
class FrontierPoint:
    """One (violation rate, profit) point and the setpoint that produced it."""

    knob: float  # b (fixed) or alpha (interval-driven)
    reflux_ratio: float
    distillate_kmol_h: float
    violation_rate: float
    mean_profit_usd_per_h: float
    feasible: bool


def _evaluate_setpoint(
    r: float,
    d: float,
    truth: TruthSurface3D,
    z_samples: np.ndarray,
    econ: EconomicsAnchor,
    spec_xb: float,
    feed_kmol_h: float,
) -> tuple[float, float]:
    """Violation rate and mean profit at (R, D) over the feed-z ensemble."""
    xb_z = np.array([truth.predict(r, d, float(z)) for z in z_samples])
    violation = float(np.mean(xb_z > spec_xb))
    bottoms = feed_kmol_h - d
    duty = (r + 1.0) * d * DHVAP_C6_KJ_PER_KMOL / 3600.0
    profits = []
    for z, xb in zip(z_samples, xb_z, strict=True):
        b_lk = xb * bottoms
        b_hk = bottoms - b_lk
        d_lk = feed_kmol_h * float(z) - b_lk
        d_hk = d - d_lk
        if d_lk < 0 or d_hk < 0 or b_hk < 0:
            continue
        profits.append(econ.profit_usd_per_h(d_lk, d_hk, b_lk, b_hk, duty))
    mean_profit = float(np.mean(profits)) if profits else float("nan")
    return violation, mean_profit


def fixed_margin_frontier(
    nominal_xb_surface: Callable[[float, float], float],
    truth: TruthSurface3D,
    z_samples: np.ndarray,
    b_grid: np.ndarray,
    economics: EconomicsAnchor | None = None,
    spec_xb: float = DEFAULT_SPEC_XB_C4,
    feed_kmol_h: float = 100.0,
) -> list[FrontierPoint]:
    """Sweep a constant back-off b -> the fixed-margin frontier."""
    econ = economics or EconomicsAnchor()
    out: list[FrontierPoint] = []
    for b in b_grid:
        opt = solve_rto_surface(
            nominal_xb_surface, econ, spec_xb, backoff=float(b), feed_kmol_h=feed_kmol_h
        )
        if opt is None:
            out.append(
                FrontierPoint(
                    float(b), float("nan"), float("nan"), float("nan"), float("nan"), False
                )
            )
            continue
        v, p = _evaluate_setpoint(
            opt.reflux_ratio, opt.distillate_kmol_h, truth, z_samples, econ, spec_xb, feed_kmol_h
        )
        out.append(FrontierPoint(float(b), opt.reflux_ratio, opt.distillate_kmol_h, v, p, True))
    return out


def interval_driven_frontier(
    nominal_xb_surface: Callable[[float, float], float],
    tray_t_surface: Callable[[float, float], float],
    sensor,
    truth: TruthSurface3D,
    z_samples: np.ndarray,
    alpha_grid: np.ndarray,
    economics: EconomicsAnchor | None = None,
    spec_xb: float = DEFAULT_SPEC_XB_C4,
    feed_kmol_h: float = 100.0,
) -> list[FrontierPoint]:
    """Sweep alpha -> the interval-driven frontier (heteroscedastic back-off)."""
    econ = economics or EconomicsAnchor()
    out: list[FrontierPoint] = []
    for a in alpha_grid:
        bo = sensor.backoff_callable_at_alpha(tray_t_surface, float(a))
        opt = solve_rto_surface(
            nominal_xb_surface, econ, spec_xb, backoff=bo, feed_kmol_h=feed_kmol_h
        )
        if opt is None:
            out.append(
                FrontierPoint(
                    float(a), float("nan"), float("nan"), float("nan"), float("nan"), False
                )
            )
            continue
        v, p = _evaluate_setpoint(
            opt.reflux_ratio, opt.distillate_kmol_h, truth, z_samples, econ, spec_xb, feed_kmol_h
        )
        out.append(FrontierPoint(float(a), opt.reflux_ratio, opt.distillate_kmol_h, v, p, True))
    return out


def _interp_profit_at_violation(frontier: list[FrontierPoint], target_v: float) -> float:
    """Profit on a frontier at a target violation rate (linear interp in violation)."""
    pts = sorted(
        [
            (p.violation_rate, p.mean_profit_usd_per_h)
            for p in frontier
            if p.feasible and np.isfinite(p.violation_rate)
        ]
    )
    if not pts:
        return float("nan")
    vs = np.array([v for v, _ in pts])
    ps = np.array([pr for _, pr in pts])
    if target_v <= vs[0]:
        return float(ps[0])
    if target_v >= vs[-1]:
        return float(ps[-1])
    return float(np.interp(target_v, vs, ps))


def profit_delta_at_matched_violation(
    frontier_fixed: list[FrontierPoint],
    frontier_interval: list[FrontierPoint],
    target_violation: float,
) -> dict[str, float]:
    """Headline: interval-driven minus fixed-margin profit at a matched violation rate."""
    p_fixed = _interp_profit_at_violation(frontier_fixed, target_violation)
    p_iv = _interp_profit_at_violation(frontier_interval, target_violation)
    return {
        "target_violation": float(target_violation),
        "profit_fixed": p_fixed,
        "profit_interval": p_iv,
        "delta_usd_per_h": p_iv - p_fixed,
        "delta_usd_per_yr": (p_iv - p_fixed) * 8760.0,
    }
