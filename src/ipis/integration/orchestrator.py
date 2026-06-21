"""Synchronous closed-loop orchestrator (decision A1) for IPIS integration.

Drives one deterministic clock over the unified debutanizer, wiring the plant and
the three module services in the order that makes the composed-coverage timing
argument hold by construction (``docs/module4/formalization-spike.md`` §4, open
item O1):

    setpoints u_k  (computed at the end of cycle k-1)
      -> apply to plant -> realize cycle-k truth and signals   [u_k fixed BEFORE eps_k]
      -> M1 soft sensor:  features(plant) -> estimate + interval
      -> M2 PdM:          pump features    -> health + RUL lower bound
      -> assemble OperationalState fields
      -> M3 RTO:          backoff = M1 half-width, hold = M1 drift -> u_{k+1}
      -> delayed label of the true quality back to M1 (drives ACI)

Because ``u_k`` is computed from cycle-(k-1) information and applied before the
cycle-k measurement noise is realized, ``u_k`` is independent of ``eps_k`` given
the regime, so the conformal selection penalty vanishes (Delta_sel = 0) and the
per-cycle SCC composition applies. The orchestrator merely *enforces* that order.

The module services and the M1 feature transform are injected as Protocols: the
real ``SoftSensorService``, ``solve_rto`` and ``PdMService`` (plus M1's physics
feature transform) are wired by thin adapters on the repo, while the loop logic
here is exercised in the sandbox with stubs. The per-cycle ψ-budget is *logged*
when a :class:`~ipis.integration.psi.PsiConfig` is supplied, but not yet
enforced -- enforcement is the D1 NLP change in Module 3.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import numpy.typing as npt

from ipis.integration.plant import DebutanizerPlant, PlantOutput, PumpDegradation
from ipis.integration.psi import (
    BudgetReport,
    OperatingPoint,
    PsiConfig,
    evaluate_budget,
    pump_load,
)

# --- Reading types (adapters map real service outputs into these) --------------


@dataclass(frozen=True)
class SoftSensorReading:
    """Module 1 output: point estimate, interval half-width, drift flag."""

    estimate: float
    half_width: float
    drift: bool = False


@dataclass(frozen=True)
class RTOReading:
    """Module 3 output: recommended setpoints and binding constraints."""

    reflux_ratio: float
    distillate_kmol_h: float
    active_constraints: tuple[str, ...] = ()


@dataclass(frozen=True)
class PdMReading:
    """Module 2 output: health, flag, and the RUL lower bound (None pre-onset)."""

    health_score: float
    flag: str
    rul_hours: float | None


# --- Injected service interfaces -----------------------------------------------


class FeatureTransform(Protocol):
    """Map a plant output to Module 1's physics-feature vector (P-GP: from the
    sensor-stage temperature and regime). Wired to M1's real transform."""

    def __call__(self, plant_out: PlantOutput) -> npt.NDArray[np.float64]: ...


class SoftSensor(Protocol):
    """Adapter over ``SoftSensorService`` (predict + delayed label)."""

    def predict(self, features: npt.NDArray[np.float64], sample_id: str) -> SoftSensorReading: ...

    def label(self, sample_id: str, y_true: float) -> None: ...


class RTOSolver(Protocol):
    """Adapter over ``solve_rto`` (returns None on a drift hold)."""

    def solve(self, *, backoff: float, rto_hold: bool, feed_z: float) -> RTOReading | None: ...


class PdM(Protocol):
    """Adapter over ``PdMService.observe``."""

    def observe(self, equipment_id: str, features: npt.NDArray[np.float64]) -> PdMReading: ...


# --- Ground-truth RUL (for coverage checking of the RUL half of S_k) ------------


def true_rul_hours(deg: PumpDegradation, reflux_flow: float) -> float:
    """Forward-looking ground-truth RUL [h] at the current load.

    Mirrors the :class:`~ipis.integration.plant.PumpDegradation` damage model:
    at load ``L`` the damage accrues at ``base_rate * L**exp`` per hour, so the
    remaining life is the remaining damage divided by that rate. Used by the
    coverage harness to evaluate ``rho_k >= rho_min``; returns ``inf`` at zero
    load.
    """
    load = pump_load(reflux_flow, deg.ref_reflux_flow)
    rate = deg.base_rate * load**deg.load_exponent
    remaining = max(0.0, deg.damage_at_failure * (1.0 - deg.severity))
    if rate <= 0.0:
        return float("inf")
    return remaining / rate * deg.dt


# --- Per-cycle record -----------------------------------------------------------


@dataclass(frozen=True)
class CycleRecord:
    """Everything the coverage harness needs from one closed-loop cycle."""

    sequence_id: int
    applied_reflux: float
    applied_distillate: float
    sensor_temp_c: float
    xb_true: float
    quality_estimate: float
    quality_half_width: float
    health_score: float
    health_flag: str
    rul_lower_hours: float | None
    true_rul_hours: float
    severity: float
    active_constraints: tuple[str, ...]
    held: bool
    operating_point: OperatingPoint
    budget: BudgetReport | None
    state_fields: dict


# --- The orchestrator -----------------------------------------------------------


@dataclass
class ClosedLoopOrchestrator:
    """Deterministic synchronous closed loop over the unified debutanizer."""

    plant: DebutanizerPlant
    feature_fn: FeatureTransform
    soft_sensor: SoftSensor
    rto_solver: RTOSolver
    pdm: PdM
    equipment_id: str = "reflux_pump_P101"
    quality_key: str = "C4_bottom"
    seed_setpoints: tuple[float, float] = (2.5, 49.0)
    label_delay: int = 0
    # optional ψ-budget logging (pre-D1: diagnostic, not enforced)
    psi_config: PsiConfig | None = None
    eps: float = 0.05
    alpha1: float = 0.10
    alpha2: float = 0.10
    # internal state
    _next: tuple[float, float] = field(init=False)
    _seq: int = field(default=0, init=False)
    _labels: deque[tuple[str, float]] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        self._next = self.seed_setpoints

    def run_cycle(self, rng: np.random.Generator | None = None) -> CycleRecord:
        """Advance one cycle under causal timing; return its record."""
        reflux, distillate = self._next  # u_k, computed at end of cycle k-1
        out = self.plant.step(reflux, distillate, rng=rng)  # cycle-k truth AFTER u_k
        sid = str(self._seq)

        m1 = self.soft_sensor.predict(self.feature_fn(out), sid)
        m2 = self.pdm.observe(self.equipment_id, out.pump_features)

        # u_{k+1} from cycle-k information (affects k+1, whose noise is independent of eps_k)
        rto = self.rto_solver.solve(
            backoff=m1.half_width, rto_hold=m1.drift, feed_z=self.plant.feed_z
        )
        held = rto is None
        if rto is None:
            active: tuple[str, ...] = ("rto_hold",)
        else:
            self._next = (rto.reflux_ratio, rto.distillate_kmol_h)
            active = tuple(rto.active_constraints)

        # delayed label feedback drives M1's ACI update
        self._labels.append((sid, out.xb_true))
        if len(self._labels) > self.label_delay:
            old_id, y_true = self._labels.popleft()
            self.soft_sensor.label(old_id, y_true)

        budget = (
            evaluate_budget(
                out.operating_point, self.psi_config, self.eps, self.alpha1, self.alpha2
            )
            if self.psi_config is not None
            else None
        )
        rul_true = true_rul_hours(self.plant.degradation, out.operating_point.reflux_flow)
        state_fields = self._assemble_state(reflux, distillate, out, m1, m2, rto, active)

        record = CycleRecord(
            sequence_id=self._seq,
            applied_reflux=reflux,
            applied_distillate=distillate,
            sensor_temp_c=out.sensor_temp_c,
            xb_true=out.xb_true,
            quality_estimate=m1.estimate,
            quality_half_width=m1.half_width,
            health_score=m2.health_score,
            health_flag=m2.flag,
            rul_lower_hours=m2.rul_hours,
            true_rul_hours=rul_true,
            severity=out.severity,
            active_constraints=active,
            held=held,
            operating_point=out.operating_point,
            budget=budget,
            state_fields=state_fields,
        )
        self._seq += 1
        return record

    def run(self, n_cycles: int, rng: np.random.Generator | None = None) -> list[CycleRecord]:
        """Run ``n_cycles`` closed-loop cycles."""
        return [self.run_cycle(rng=rng) for _ in range(n_cycles)]

    def _assemble_state(
        self,
        reflux: float,
        distillate: float,
        out: PlantOutput,
        m1: SoftSensorReading,
        m2: PdMReading,
        rto: RTOReading | None,
        active: tuple[str, ...],
    ) -> dict:
        """Build the OperationalState field dict (constructed into the pydantic
        model by the serving layer: ``OperationalState(**state_fields)``)."""
        rul = {self.equipment_id: m2.rul_hours} if m2.rul_hours is not None else {}
        setpoints = (
            {}
            if rto is None
            else {
                "reflux_ratio": rto.reflux_ratio,
                "distillate_kmol_h": rto.distillate_kmol_h,
            }
        )
        return {
            "sequence_id": self._seq,
            "process_conditions": {
                "reflux_ratio": reflux,
                "distillate_kmol_h": distillate,
                "tray6_T_C": out.sensor_temp_c,
            },
            "quality_estimate": {self.quality_key: m1.estimate},
            "quality_confidence": {self.quality_key: m1.half_width},
            "equipment_health": {self.equipment_id: m2.health_score},
            "health_flags": {self.equipment_id: m2.flag},
            "remaining_useful_life": rul,
            "setpoint_recommendations": setpoints,
            "active_constraints": list(active),
            "module_status": {},
        }
