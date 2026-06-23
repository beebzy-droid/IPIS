"""Module 5 horizon experiments (Paper 5 figures).

Three sweeps over the dynamic loop (`ipis.integration.dynamic_demo`):

  1. ``two_arm_contrast`` -- health-blind vs conformal health-constrained, both scored
     against the same certified floor. The headline: the blind RTO meets the quality spec
     but over-refluxes and drives projected RUL below the floor, so S_k collapses; the
     constrained loop holds its floor. (Figure 1.)
  2. ``deadtime_sweep`` -- horizon coverage and its finite-horizon transient vs the label
     delay D_a. Validity is invariant (S_k holds); the early-window coverage deviation is
     the transient that grows with D_a and washes out by the late window. (Figure 2.)
  3. ``gamma_sweep`` -- ACI learning-rate sweep (coverage vs interval width), plus the
     contrast against a naive K-cycle Bonferroni interval that goes vacuous as K grows,
     where ACI stays finite and adaptive. (Figure 3.)

All numeric outputs are plain dataclasses so a caller can serialize them as frozen evidence
or feed them to a plotter without re-running the loop.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import partial

import numpy as np

from ipis.integration.coverage import CoverageConfig, run_coverage
from ipis.integration.dynamic_demo import build_dynamic_demo_orchestrator
from ipis.integration.psi import certified_coverage
from ipis.module1_soft_sensor.evaluation.conformal import (
    conformal_quantile,
    select_gamma,
    split_conformal_halfwidth,
)

_DEFAULT_CONSTRAINED_CAP = 4.85
_DEFAULT_ECON = 7.8


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _campaign_arrays(cfg: CoverageConfig, seed: int, n_cycles: int, **builder_kw) -> dict:
    """Run one constrained-arm campaign and return the recorder columns."""
    orch = build_dynamic_demo_orchestrator(seed, cfg, **builder_kw)
    orch.run(n_cycles, rng=np.random.default_rng(seed))
    return orch.recorder.to_arrays()


def _interval_coverage(a: dict, lo: int = 0, hi: int | None = None) -> float:
    sl = slice(lo, hi)
    covered = np.abs(a["xb_true"][sl] - a["quality_estimate"][sl]) <= a["quality_half_width"][sl]
    return float(np.mean(covered)) if covered.size else float("nan")


# --------------------------------------------------------------------------- #
# 1. two-arm contrast (Figure 1)                                              #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ArmResult:
    label: str
    s_coverage: float
    s_ci: tuple[float, float]
    quality_coverage: float
    rul_coverage: float
    meets_floor: bool
    final_severity_mean: float
    frac_psi_binding: float


@dataclass(frozen=True)
class TwoArmResult:
    floor: float
    blind: ArmResult
    constrained: ArmResult


def two_arm_contrast(
    cfg: CoverageConfig,
    *,
    econ_ratio: float = _DEFAULT_ECON,
    constrained_cap: float = _DEFAULT_CONSTRAINED_CAP,
) -> TwoArmResult:
    """Run both arms against the same floor (the cap selects the arm, not ``eps``)."""

    def _arm(label: str, cap: float) -> ArmResult:
        r = run_coverage(
            partial(build_dynamic_demo_orchestrator, econ_ratio=econ_ratio, cap_ratio=cap), cfg
        )
        return ArmResult(
            label=label,
            s_coverage=r.s_coverage,
            s_ci=r.s_coverage_ci,
            quality_coverage=r.quality_coverage,
            rul_coverage=r.rul_coverage,
            meets_floor=r.meets_floor,
            final_severity_mean=r.final_severity_mean,
            frac_psi_binding=r.frac_psi_binding,
        )

    blind = _arm("health-blind", math.inf)
    constrained = _arm("health-constrained", constrained_cap)
    floor = certified_coverage(cfg.alpha1, cfg.alpha2, cfg.eps)
    return TwoArmResult(floor=floor, blind=blind, constrained=constrained)


# --------------------------------------------------------------------------- #
# 2. deadtime sweep (Figure 2)                                                #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DeadtimePoint:
    d_a: int
    s_coverage: float
    s_ci_lo: float
    interval_coverage: float
    interval_coverage_early: float
    interval_coverage_late: float


@dataclass(frozen=True)
class DeadtimeSweepResult:
    floor: float
    target_interval_coverage: float
    early_window: int
    points: list[DeadtimePoint] = field(default_factory=list)


def deadtime_sweep(
    cfg: CoverageConfig,
    d_a_values: list[int],
    *,
    constrained_cap: float = _DEFAULT_CONSTRAINED_CAP,
    campaign_cycles: int = 400,
    campaign_seed: int = 7,
    early_window: int = 60,
) -> DeadtimeSweepResult:
    """Constrained arm: S_k coverage (validity) and the interval-coverage transient vs D_a."""
    points: list[DeadtimePoint] = []
    floor = 0.0
    for d_a in d_a_values:
        r = run_coverage(
            partial(
                build_dynamic_demo_orchestrator, cap_ratio=constrained_cap, label_delay_cycles=d_a
            ),
            cfg,
        )
        floor = r.certified_floor
        a = _campaign_arrays(
            cfg, campaign_seed, campaign_cycles, cap_ratio=constrained_cap, label_delay_cycles=d_a
        )
        points.append(
            DeadtimePoint(
                d_a=d_a,
                s_coverage=r.s_coverage,
                s_ci_lo=r.s_coverage_ci[0],
                interval_coverage=_interval_coverage(a),
                interval_coverage_early=_interval_coverage(a, 0, early_window),
                interval_coverage_late=_interval_coverage(a, early_window),
            )
        )
    return DeadtimeSweepResult(
        floor=floor,
        target_interval_coverage=1.0 - cfg.alpha1,
        early_window=early_window,
        points=points,
    )


# --------------------------------------------------------------------------- #
# 3. gamma sweep + naive union-bound contrast (Figure 3)                      #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GammaPoint:
    gamma: float
    interval_coverage: float
    mean_half_width: float


@dataclass(frozen=True)
class UnionBoundPoint:
    horizon_k: int
    bonferroni_half_width: float  # +inf where the level exceeds the calibration resolution


@dataclass(frozen=True)
class GammaSweepResult:
    target_interval_coverage: float
    selected_gamma: float
    aci_mean_half_width: float
    points: list[GammaPoint] = field(default_factory=list)
    union_bound: list[UnionBoundPoint] = field(default_factory=list)


def gamma_sweep(
    cfg: CoverageConfig,
    gamma_values: list[float],
    *,
    constrained_cap: float = _DEFAULT_CONSTRAINED_CAP,
    campaign_cycles: int = 400,
    campaign_seed: int = 7,
    union_horizons: list[int] | None = None,
) -> GammaSweepResult:
    """Coverage vs adaptivity over gamma, with the naive K-cycle Bonferroni contrast.

    The naive baseline guarantees joint coverage over K cycles by Bonferroni: each cycle at
    level ``1 - alpha/K``, i.e. the ``1 - alpha/K`` conformal quantile of the residuals. As K
    grows this level exceeds what the finite calibration set can resolve and the half-width
    diverges (``+inf``) -- vacuous intervals -- whereas ACI keeps a finite adaptive width.
    """
    points: list[GammaPoint] = []
    for g in gamma_values:
        a = _campaign_arrays(
            cfg, campaign_seed, campaign_cycles, cap_ratio=constrained_cap, gamma=g
        )
        points.append(
            GammaPoint(
                gamma=g,
                interval_coverage=_interval_coverage(a),
                mean_half_width=float(np.nanmean(a["quality_half_width"])),
            )
        )

    # residual stream from the constrained campaign at a mid gamma, for selection + baseline
    a_mid = _campaign_arrays(cfg, campaign_seed, campaign_cycles, cap_ratio=constrained_cap)
    resid = np.abs(a_mid["xb_true"] - a_mid["quality_estimate"])
    est = a_mid["quality_estimate"]
    sel = select_gamma(est, a_mid["xb_true"], np.full(60, 0.002), alpha=cfg.alpha1)
    aci_mean_hw = float(np.nanmean(a_mid["quality_half_width"]))

    horizons = union_horizons or [1, 10, 50, 200, 1000]
    union: list[UnionBoundPoint] = []
    for k in horizons:
        # Bonferroni per-cycle miscoverage alpha/k -> conformal quantile at level 1 - alpha/k
        hw = split_conformal_halfwidth(resid, cfg.alpha1 / k)
        union.append(UnionBoundPoint(horizon_k=k, bonferroni_half_width=hw))
    # sanity: the level-1 (no correction) split half-width, for reference
    _ = conformal_quantile(resid, 1.0 - cfg.alpha1)

    return GammaSweepResult(
        target_interval_coverage=1.0 - cfg.alpha1,
        selected_gamma=float(sel),
        aci_mean_half_width=aci_mean_hw,
        points=points,
        union_bound=union,
    )
