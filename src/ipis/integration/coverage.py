"""Monte Carlo coverage harness -- the IPIS experimental core (module 5/5).

Runs the closed loop over many seeds x cycles and measures the empirical
coverage of the composed safety event

    S_k = { x_k <= x_spec }  and  { rho_k >= rho_min }

against the certified floor of ``docs/module4/formalization-spike.md`` §5-6,

    P(S_k) >= 1 - (alpha1 + alpha2) - eps,

using the per-cycle ground truth recorded by the orchestrator (``xb_true`` and
``true_rul_hours``). Comparing a health-blind loop (eps -> large, the ψ-budget
never binds) against the conformal health-constrained loop (finite eps) is the
headline result: the health-blind RTO drives the reflux pump harder, consuming
RUL until the ``rho_k >= rho_min`` half of S_k fails more than alpha2 of the
time, while the constrained loop holds its certified floor.

``HealthRTOAdapter`` bridges the orchestrator's ``RTOSolver`` protocol to
:func:`ipis.integration.health_rto.solve_health_constrained_rto`; it is the same
adapter used on the repo with the real ``LnXbSurface`` coefficients and
``EconomicsAnchor``. The harness itself is solver-agnostic -- the GEKKO solve is
exercised only through the adapter, so the harness logic is unit-tested with a
cheap stub RTO and the real-NLP demonstration is gated behind GEKKO.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ipis.integration.health_rto import (
    EconomicParams,
    solve_health_constrained_rto,
)
from ipis.integration.orchestrator import (
    ClosedLoopOrchestrator,
    PdMReading,
    RTOReading,
    SoftSensorReading,
)
from ipis.integration.plant import (
    DebutanizerPlant,
    FeatureSynthesizer,
    FeedSpec,
    PumpDegradation,
)
from ipis.integration.psi import (
    CoordinateScales,
    OperatingPoint,
    PsiConfig,
    certified_coverage,
)

OrchestratorFactory = Callable[[int, "CoverageConfig"], ClosedLoopOrchestrator]


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (robust at the extremes)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


@dataclass(frozen=True)
class CoverageConfig:
    """Sweep + certificate parameters."""

    spec_xb_c4: float = 0.02
    rul_min_hours: float = 200.0
    alpha1: float = 0.10
    alpha2: float = 0.10
    eps: float = 0.05  # ψ-budget; set large (e.g. 1e6) for the health-blind arm
    n_seeds: int = 8
    n_cycles: int = 25


@dataclass(frozen=True)
class CoverageResult:
    """Aggregated coverage of S_k and its certificate comparison."""

    n_total: int
    s_coverage: float
    s_coverage_ci: tuple[float, float]
    quality_coverage: float
    rul_coverage: float
    certified_floor: float
    meets_floor: bool
    mean_profit_usd_per_h: float
    frac_psi_binding: float
    frac_held: float
    final_severity_mean: float


def run_coverage(
    factory: OrchestratorFactory, cfg: CoverageConfig, *, z: float = 1.96
) -> CoverageResult:
    """Run the sweep and aggregate S_k coverage with a Wilson interval."""
    s_hits = q_hits = rul_hits = 0
    n = 0
    psi_binding = held = 0
    profits: list[float] = []
    final_sev: list[float] = []

    for seed in range(cfg.n_seeds):
        orch = factory(seed, cfg)
        rng = np.random.default_rng(seed)
        records = orch.run(cfg.n_cycles, rng=rng)
        for rec in records:
            n += 1
            q_ok = rec.xb_true <= cfg.spec_xb_c4
            rul_ok = rec.true_rul_hours >= cfg.rul_min_hours
            q_hits += int(q_ok)
            rul_hits += int(rul_ok)
            s_hits += int(q_ok and rul_ok)
            if "psi_budget" in rec.active_constraints:
                psi_binding += 1
            if rec.held:
                held += 1
        if records:
            final_sev.append(records[-1].severity)

    s_cov = s_hits / n if n else 0.0
    floor = certified_coverage(cfg.alpha1, cfg.alpha2, cfg.eps)
    ci = wilson_interval(s_hits, n, z=z)
    return CoverageResult(
        n_total=n,
        s_coverage=s_cov,
        s_coverage_ci=ci,
        quality_coverage=q_hits / n if n else 0.0,
        rul_coverage=rul_hits / n if n else 0.0,
        certified_floor=floor,
        meets_floor=ci[0] >= floor,
        mean_profit_usd_per_h=float(np.mean(profits)) if profits else float("nan"),
        frac_psi_binding=psi_binding / n if n else 0.0,
        frac_held=held / n if n else 0.0,
        final_severity_mean=float(np.mean(final_sev)) if final_sev else float("nan"),
    )


def summarize(result: CoverageResult) -> str:
    """One-line-per-metric summary for logs / the paper's results table."""
    lo, hi = result.s_coverage_ci
    verdict = "MEETS" if result.meets_floor else "BELOW"
    return (
        f"S_k coverage = {result.s_coverage:.3f} [{lo:.3f}, {hi:.3f}] "
        f"vs floor {result.certified_floor:.3f}  -> {verdict}\n"
        f"  quality coverage = {result.quality_coverage:.3f}\n"
        f"  RUL-floor coverage = {result.rul_coverage:.3f}\n"
        f"  psi-budget binding = {result.frac_psi_binding:.2f} of cycles\n"
        f"  RTO held (drift) = {result.frac_held:.2f} of cycles\n"
        f"  mean final severity = {result.final_severity_mean:.3f}\n"
        f"  N = {result.n_total}"
    )


# --- Adapter: orchestrator RTOSolver -> health_rto (also the repo adapter) ------


@dataclass
class HealthRTOAdapter:
    """Implements the orchestrator's ``RTOSolver`` via the §6 health-constrained
    NLP. On the repo, construct with the real ``LnXbSurface.coef`` and an
    ``EconomicParams`` mapped from ``EconomicsAnchor``."""

    surface_coef: tuple[float, float, float, float, float, float]
    econ: EconomicParams
    psi_cfg: PsiConfig
    eps: float
    spec_xb_c4: float = 0.02
    r_bounds: tuple[float, float] = (0.8, 3.0)
    d_bounds: tuple[float, float] = (33.0, 37.0)
    feed_kmol_h: float = 100.0

    def solve(
        self,
        *,
        backoff: float,
        rto_hold: bool,
        feed_z: float,
        operating_point: OperatingPoint,
    ) -> RTOReading | None:
        result = solve_health_constrained_rto(
            self.surface_coef,
            self.econ,
            alpha=operating_point.alpha,
            R_min=operating_point.R_min,
            strip_factor=operating_point.strip_factor,
            cfg=self.psi_cfg,
            eps=self.eps,
            spec_xb_c4=self.spec_xb_c4,
            backoff=backoff,
            feed_kmol_h=self.feed_kmol_h,
            z_lk=feed_z,
            r_bounds=self.r_bounds,
            d_bounds=self.d_bounds,
            rto_hold=rto_hold,
        )
        if result is None:
            return None
        return RTOReading(
            reflux_ratio=result.reflux_ratio,
            distillate_kmol_h=result.distillate_kmol_h,
            active_constraints=tuple(result.active_constraints),
        )


# --- Sandbox demonstration wiring (real plant + real health_rto; stub M1/M2) ----


def _demo_surface_coef() -> tuple[float, float, float, float, float, float]:
    # ln(xB) decreasing in R: xB ~0.016 -> 0.007 over the R box. Meeting a tight
    # spec (e.g. 0.008) forces high reflux; a loose spec lets the energy-minimising
    # optimum sit low. This is what makes the health trade-off visible.
    return (-3.84, -0.37, 0.0, 0.0, 0.0, 0.0)


def _demo_econ() -> EconomicParams:
    return EconomicParams(
        c4_value_usd_per_kg=0.62,
        gasoline_value_usd_per_kg=0.55,
        energy_cost_usd_per_gj=6.5,
        dhvap_kj_per_kmol=30000.0,
        m_lk_kg_per_kmol=58.12,
        m_hk_kg_per_kmol=86.18,
    )


def _demo_psi_cfg(femto_ref: float) -> PsiConfig:
    return PsiConfig(
        L1=0.05,
        L2=0.30,
        fortuna_op=OperatingPoint(
            R=1.9, D=35.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=femto_ref
        ),
        femto_ref_reflux_flow=femto_ref,
        scales=CoordinateScales(pump_load_scale=1.0),
    )


class _DemoSoftSensor:
    """Fixed-back-off stub: deterministic plant means the RTO enforces the spec,
    so quality coverage is exercised by the hard constraint (real M1 = Paper 1)."""

    def __init__(self, half_width: float) -> None:
        self.half_width = half_width

    def predict(self, features, sample_id) -> SoftSensorReading:
        return SoftSensorReading(
            estimate=float(features[0]), half_width=self.half_width, drift=False
        )

    def label(self, sample_id: str, y_true: float) -> None:
        return None


class _DemoPdM:
    """Cosmetic health/RUL for the bus; the RTO is gated by the ψ-budget, not by
    this RUL (real M2 supplies the calibrated lower bound)."""

    def observe(self, equipment_id, features) -> PdMReading:
        return PdMReading(health_score=0.9, flag="OK", rul_hours=None)


def _demo_feature_fn(plant_out) -> np.ndarray:
    return np.array([plant_out.xb_true], dtype=float)


def build_demo_orchestrator(
    seed: int,
    cfg: CoverageConfig,
    *,
    femto_ref: float = 66.5,
    degradation_rate: float = 1.2e-2,
) -> ClosedLoopOrchestrator:
    """Wire a real closed loop for the in-sandbox money-shot demonstration.

    ``femto_ref`` is the seed reflux flow (R=1.9, D=35): the bearing was
    characterised at the nominal operating point, so the ψ-budget keeps the loop
    near it. Under a tight spec the health-blind RTO must over-reflux to meet the
    spec (load >> ref, fast wear), while the constrained RTO cannot reach the
    spec within the budget and holds at the nominal point (load = ref, slow wear).
    """

    def xb_truth(R: float, D: float, z: float) -> float:
        c = _demo_surface_coef()
        ln = c[0] + c[1] * R + c[2] * D + c[3] * R * R + c[4] * D * D + c[5] * R * D
        return float(np.exp(ln))

    def tray_temp(R: float, D: float) -> float:
        return 104.0 - 2.0 * (R - 1.9)

    class _Prop:
        def relative_volatility(self, t: float) -> float:
            return 6.0

        def liquid_viscosity_cp(self, t: float) -> float:
            return 0.12

        def k_value_hk(self, t: float) -> float:
            return 0.8

    plant = DebutanizerPlant(
        xb_truth=xb_truth,
        tray_temp=tray_temp,
        properties=_Prop(),
        feed=FeedSpec(F=cfg_feed(cfg), z_lk=0.35, q=1.0),
        degradation=PumpDegradation(
            ref_reflux_flow=femto_ref, base_rate=degradation_rate, load_exponent=1.0
        ),
        synthesizer=FeatureSynthesizer(
            feature_names=("rms", "kurtosis"),
            baseline=np.zeros(2),
            growth=np.ones(2),
        ),
        feed_z=0.35,
    )
    adapter = HealthRTOAdapter(
        surface_coef=_demo_surface_coef(),
        econ=_demo_econ(),
        psi_cfg=_demo_psi_cfg(femto_ref),
        eps=cfg.eps,
        spec_xb_c4=cfg.spec_xb_c4,
        feed_kmol_h=cfg_feed(cfg),
    )
    return ClosedLoopOrchestrator(
        plant=plant,
        feature_fn=_demo_feature_fn,
        soft_sensor=_DemoSoftSensor(half_width=0.0003),
        rto_solver=adapter,
        pdm=_DemoPdM(),
        equipment_id="reflux_pump_P101",
        seed_setpoints=(1.9, 35.0),
        psi_config=_demo_psi_cfg(femto_ref),
        eps=cfg.eps,
        alpha1=cfg.alpha1,
        alpha2=cfg.alpha2,
    )


def cfg_feed(cfg: CoverageConfig) -> float:
    """Feed rate used by the demo (kept consistent across plant and RTO)."""
    return 100.0
