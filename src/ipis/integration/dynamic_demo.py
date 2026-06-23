"""Reusable in-sandbox dynamic demo loop for the Module 5 horizon experiments.

This is the dynamic analogue of ``ipis.integration.coverage.build_demo_orchestrator``
(which wires a real static loop with cheap services). It supplies the three pieces the
horizon sweeps need, factored out of the unit-test stubs so the experiments and the tests
share one construction:

  * ``DelayedACISoftSensor`` -- an affine physics-anchored soft sensor wrapping M1's
    ``ACIConformal`` with CORRECT delayed-label feedback (per-sample stored half-width).
  * ``CappedBackoffRTO`` -- a cheap stand-in for the chance-constrained NLP: it meets the
    spec via the conformal back-off, is pulled toward an economic reflux target, and is
    clipped by a psi-budget reflux cap. The cap is the only knob separating the two arms:
    uncapped (health-blind) the RTO over-refluxes for product value and burns RUL; capped
    (health-constrained) it holds near the spec-minimum and preserves RUL. The real GEKKO
    solve remains the repo path.
  * ``build_dynamic_demo_orchestrator`` -- wires them onto the dynamic plant.

Both arms are scored against the SAME certified floor ``1 - (alpha1 + alpha2) - eps``;
the cap (not ``eps``) selects the arm, so ``eps`` stays the certificate parameter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ipis.integration.dynamic_orchestrator import DynamicClosedLoopOrchestrator
from ipis.integration.dynamic_plant import DynamicDebutanizerPlant
from ipis.integration.orchestrator import PdMReading, RTOReading, SoftSensorReading
from ipis.integration.plant import FeatureSynthesizer, FeedSpec, PumpDegradation
from ipis.module1_soft_sensor.evaluation.conformal import ACIConformal, aci_step

# Demo surface + thermo (monotone xb in R), shared with the unit tests' expectations.
_AFFINE_A, _AFFINE_B = -0.2064, 0.00226  # soft sensor linearized at R~5, temp~98


def demo_xb_surface(R: float, D: float, z: float) -> float:
    """True bottoms C4, monotone decreasing in reflux ratio R."""
    return 0.05 * float(np.exp(-0.3 * (R - 1.0)))


def demo_tray_temp(R: float, D: float) -> float:
    return 108.0 - 2.0 * R


class _DemoProps:
    def relative_volatility(self, temp_c: float) -> float:
        return 6.0

    def liquid_viscosity_cp(self, temp_c: float) -> float:
        return 0.12

    def k_value_hk(self, temp_c: float) -> float:
        return 0.8


def dynamic_feature_fn(out) -> np.ndarray:
    return np.array([out.sensor_temp_c], dtype=float)


def reflux_ratio_for_spec(spec: float, backoff: float, D: float, z: float, r_bounds) -> float:
    """Smallest reflux ratio meeting ``xb(R, D, z) + backoff <= spec`` (xb decreasing in R)."""
    target = spec - backoff
    lo, hi = r_bounds
    if demo_xb_surface(hi, D, z) > target:
        return hi
    if demo_xb_surface(lo, D, z) <= target:
        return lo
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if demo_xb_surface(mid, D, z) <= target:
            hi = mid
        else:
            lo = mid
    return hi


@dataclass
class DelayedACISoftSensor:
    """Affine soft sensor + ACI with correct delayed-label feedback."""

    init_residuals: np.ndarray
    alpha: float = 0.10
    gamma: float = 0.02
    noise_sd: float = 5e-4
    window: int | None = 200
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(0))
    _aci: ACIConformal = field(init=False)
    _pending: dict = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._aci = ACIConformal(
            self.init_residuals, alpha=self.alpha, gamma=self.gamma, window=self.window
        )

    @property
    def alpha_t(self) -> float:
        return float(self._aci.alpha_t)

    def predict(self, features, sample_id) -> SoftSensorReading:
        temp = float(features[0])
        noise = self.rng.normal(0.0, self.noise_sd) if self.noise_sd > 0 else 0.0
        est = _AFFINE_A + _AFFINE_B * temp + noise
        self._aci.interval(np.array(est, dtype=float))
        hw = float(self._aci._last_halfwidth)
        self._pending[sample_id] = (est, hw)
        return SoftSensorReading(estimate=est, half_width=hw, drift=False)

    def label(self, sample_id, y_true) -> None:
        y_pred, hw = self._pending.pop(sample_id)
        score = abs(float(y_true) - y_pred)
        covered = score <= hw
        self._aci.alpha_t = aci_step(
            self._aci.alpha_t, covered, self._aci.gamma, self._aci.target_alpha
        )
        self._aci.scores.append(score)


@dataclass
class CappedBackoffRTO:
    """Conformal back-off RTO with an economic reflux pull and a psi-budget cap.

    Per cycle: meet ``xb + backoff <= spec`` at the smallest reflux (``R_spec``), then pull
    toward the economic target ``econ_ratio`` (over-purify for product value), then clip to
    the cap. ``cap_ratio = inf`` is the health-blind arm; a finite cap is the constrained
    arm. ``active_constraints`` reports ``psi_budget`` when the cap binds (so the coverage
    harness counts it) and ``quality`` otherwise.
    """

    spec: float
    D: float
    econ_ratio: float
    cap_ratio: float = math.inf
    r_bounds: tuple[float, float] = (2.0, 9.0)

    def solve(self, *, backoff, rto_hold, feed_z, operating_point) -> RTOReading | None:
        if rto_hold:
            return None
        r_spec = reflux_ratio_for_spec(self.spec, float(backoff), self.D, feed_z, self.r_bounds)
        cap = max(self.cap_ratio, r_spec)  # never clip below the spec-feasible reflux
        r = min(max(r_spec, self.econ_ratio), cap)
        if cap < self.econ_ratio and r == cap:
            active: tuple[str, ...] = ("psi_budget",)
        else:
            active = ("quality",)
        return RTOReading(reflux_ratio=r, distillate_kmol_h=self.D, active_constraints=active)


class HealthyPdM:
    def observe(self, equipment_id, features) -> PdMReading:
        return PdMReading(health_score=0.95, flag="OK", rul_hours=None)


def build_dynamic_demo_orchestrator(
    seed: int,
    cfg,
    *,
    econ_ratio: float = 7.8,
    cap_ratio: float = math.inf,
    gamma: float = 0.02,
    label_delay_cycles: int = 2,
    base_rate: float = 3.0e-5,
    load_exponent: float = 3.0,
    steps_per_cycle: int = 60,
    noise_sd: float = 5e-4,
    deadtime_h: float = 0.083,
    d_hold: float = 35.0,
) -> DynamicClosedLoopOrchestrator:
    """Wire the dynamic demo loop. ``cap_ratio = inf`` -> health-blind; finite -> constrained.

    ``cfg`` is an ``ipis.integration.coverage.CoverageConfig`` (uses ``spec_xb_c4``,
    ``alpha1``, ``alpha2``, ``eps``, ``rul_min_hours``). The reference reflux is the nominal
    spec-minimum, so the constrained arm sits near affinity-load 1 and the blind arm's
    economic over-reflux drives the load (and the wear) up by the cube law.
    """
    r_nominal = reflux_ratio_for_spec(cfg.spec_xb_c4, 3.0e-3, d_hold, 0.35, (2.0, 9.0))
    ref_reflux = r_nominal * d_hold
    plant = DynamicDebutanizerPlant(
        xb_truth=demo_xb_surface,
        tray_temp=demo_tray_temp,
        properties=_DemoProps(),
        feed=FeedSpec(F=100.0, z_lk=0.35, q=1.0),
        feed_z=0.35,
        degradation=PumpDegradation(
            ref_reflux_flow=ref_reflux, base_rate=base_rate, load_exponent=load_exponent
        ),
        synthesizer=FeatureSynthesizer(
            feature_names=("rms", "kurtosis"), baseline=np.zeros(2), growth=np.ones(2)
        ),
        dt=0.0167,
        tau_act=0.0167,
        tau_proc=0.5,
        tau_temp=0.25,
        deadtime_h=deadtime_h,
        R0=r_nominal,
        D0=d_hold,
    )
    soft_sensor = DelayedACISoftSensor(
        init_residuals=np.full(60, 0.002),
        alpha=cfg.alpha1,
        gamma=gamma,
        noise_sd=noise_sd,
        rng=np.random.default_rng(1000 + seed),
    )
    return DynamicClosedLoopOrchestrator(
        plant=plant,
        feature_fn=dynamic_feature_fn,
        soft_sensor=soft_sensor,
        rto_solver=CappedBackoffRTO(cfg.spec_xb_c4, d_hold, econ_ratio, cap_ratio),
        pdm=HealthyPdM(),
        steps_per_cycle=steps_per_cycle,
        seed_setpoints=(r_nominal, d_hold),
        label_delay_cycles=label_delay_cycles,
        eps=cfg.eps,
        alpha1=cfg.alpha1,
        alpha2=cfg.alpha2,
        spec_xb_c4=cfg.spec_xb_c4,
        rul_min_hours=cfg.rul_min_hours,
    )
