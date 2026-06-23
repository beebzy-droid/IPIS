"""Dynamic closed-loop orchestrator for IPIS Module 5 (horizon coverage).

The Module 4 orchestrator (``ipis.integration.orchestrator.ClosedLoopOrchestrator``)
runs one quasi-static cycle per ``plant.step``. Module 5 replaces the plant with the
dynamic plant (``ipis.integration.dynamic_plant.DynamicDebutanizerPlant``) and keeps the
same causal-timing contract, lifting the per-cycle composed certificate to a *long-run /
horizon* guarantee under feedback-induced dependence and DELAYED labels (ACI; Gibbs &
Candes 2021).

Two timescales:

  * the plant integration step ``dt`` (a plant property, ~1 min);
  * the RTO / decision interval ``steps_per_cycle * dt`` (~30-60 min). One *cycle* k is
    one decision ``u_k`` held across ``steps_per_cycle`` integration steps; the realized
    end-of-cycle state is the last sampled output.

Causal timing (O1), preserved from M4 and re-examined under deadtime in
``docs/module5/o1-deadtime-timing.md``:

    u_k computed from cycle-(k-1) info
      -> held across the interval -> realize cycle-k truth   [u_k fixed BEFORE eps_k]
      -> M1 predict (interval from current ACI alpha_t) ; M2 observe
      -> M3 solve u_{k+1} from cycle-k info
      -> the cycle-(k - D_a) label is released to M1, driving the ACI update

``label_delay_cycles`` (``D_a``) is the lab/analyzer delay expressed in DECISION cycles
(``D_a = ceil(analyzer_delay / RTO_interval)``); it is the cycle-level delay that makes
ACI run on *stale* residuals. The plant's own sub-``dt`` analyzer deadtime (``xb_measured``)
is the finer within-cycle effect and is carried through to the recorder/viewer. Because
the cycle-k interval is formed from residuals no newer than cycle ``k - D_a - 1``, it never
references cycle-k's own outcome, so the selection penalty stays ``Delta_sel = 0``; deadtime
moves into the ACI coverage *rate*, not its validity (see the doc).

Records are ``CycleRecord``-compatible (they carry ``xb_true``, ``true_rul_hours``,
``active_constraints``, ``held``, ``severity``, ...), so the proven
``ipis.integration.coverage.run_coverage`` harness measures the horizon coverage of the
joint event ``S_k = {x_k <= x_spec} and {rho_k >= rho_min}`` with its Wilson interval and
the certified floor. The orchestrator also populates a ``CampaignRecorder`` (the V1
visualization + analysis substrate).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np

from ipis.integration.dynamic_plant import DynamicDebutanizerPlant, DynamicPlantOutput
from ipis.integration.orchestrator import (
    FeatureTransform,
    PdM,
    RTOSolver,
    SoftSensor,
    true_rul_hours,
)
from ipis.integration.psi import (
    BudgetReport,
    OperatingPoint,
    PsiConfig,
    certified_coverage,
    evaluate_budget,
)
from ipis.integration.recorder import CampaignRecorder


@dataclass(frozen=True)
class DynamicCycleRecord:
    """One decision cycle of the dynamic loop.

    The leading fields match ``ipis.integration.orchestrator.CycleRecord`` (minus the
    state-bus ``state_fields``), so ``run_coverage`` consumes a list of these unchanged.
    The trailing fields expose the dynamic story: realized vs commanded decisions, the
    elapsed time, the joint-event outcome, and the certified floor.
    """

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
    # --- dynamic extras ---
    realized_reflux: float
    realized_distillate: float
    time_h: float
    s_event: bool | None
    certified_floor: float | None


@dataclass
class DynamicClosedLoopOrchestrator:
    """Deterministic dynamic closed loop; one decision held across many plant steps."""

    plant: DynamicDebutanizerPlant
    feature_fn: FeatureTransform
    soft_sensor: SoftSensor
    rto_solver: RTOSolver
    pdm: PdM
    steps_per_cycle: int = 60  # plant dt-steps per RTO decision interval
    equipment_id: str = "reflux_pump_P101"
    seed_setpoints: tuple[float, float] = (2.5, 49.0)
    label_delay_cycles: int = 2  # D_a: lab/analyzer delay in DECISION cycles
    # ψ-budget logging (pre-D1: diagnostic) and certificate parameters
    psi_config: PsiConfig | None = None
    eps: float = 0.05
    alpha1: float = 0.10
    alpha2: float = 0.10
    # optional safety-event thresholds (for the recorder's s_event/floor)
    spec_xb_c4: float | None = None
    rul_min_hours: float | None = None
    # internal state
    recorder: CampaignRecorder = field(default_factory=CampaignRecorder, init=False)
    _next: tuple[float, float] = field(init=False)
    _seq: int = field(default=0, init=False)
    _labels: deque[tuple[str, float]] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        if self.steps_per_cycle < 1:
            raise ValueError("steps_per_cycle must be >= 1")
        if self.label_delay_cycles < 0:
            raise ValueError("label_delay_cycles (D_a) must be non-negative")
        self._next = self.seed_setpoints
        # start the plant at the seed operating point so cycle 0 is consistent
        self.plant.seed_steady(*self.seed_setpoints)

    def _advance(self, R: float, D: float, rng: np.random.Generator | None) -> DynamicPlantOutput:
        out: DynamicPlantOutput | None = None
        for _ in range(self.steps_per_cycle):
            out = self.plant.step(R, D, rng=rng)
        assert out is not None  # steps_per_cycle >= 1
        return out

    def run_cycle(self, rng: np.random.Generator | None = None) -> DynamicCycleRecord:
        """Advance one decision cycle under the causal-timing contract."""
        reflux, distillate = self._next  # u_k, from cycle k-1
        out = self._advance(reflux, distillate, rng)  # realize cycle-k truth AFTER u_k
        sid = str(self._seq)

        m1 = self.soft_sensor.predict(self.feature_fn(out), sid)
        m2 = self.pdm.observe(self.equipment_id, out.pump_features)

        # u_{k+1} from cycle-k information
        rto = self.rto_solver.solve(
            backoff=m1.half_width,
            rto_hold=m1.drift,
            feed_z=self.plant.feed_z,
            operating_point=out.operating_point,
        )
        held = rto is None
        if rto is None:
            active: tuple[str, ...] = ("rto_hold",)
        else:
            self._next = (rto.reflux_ratio, rto.distillate_kmol_h)
            active = tuple(rto.active_constraints)

        # release the cycle-(k - D_a) label to M1, driving the ACI update on stale residuals
        self._labels.append((sid, out.xb_true))
        if len(self._labels) > self.label_delay_cycles:
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

        s_event: bool | None = None
        floor: float | None = None
        if self.spec_xb_c4 is not None and self.rul_min_hours is not None:
            s_event = bool(out.xb_true <= self.spec_xb_c4 and rul_true >= self.rul_min_hours)
            floor = certified_coverage(self.alpha1, self.alpha2, self.eps)

        record = DynamicCycleRecord(
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
            realized_reflux=out.realized_reflux,
            realized_distillate=out.realized_distillate,
            time_h=out.time_h,
            s_event=s_event,
            certified_floor=floor,
        )
        self.recorder.record(
            out,
            cycle=self._seq,
            quality_estimate=m1.estimate,
            quality_half_width=m1.half_width,
            rul_lower_hours=m2.rul_hours,
            true_rul_hours=rul_true,
            health_flag=m2.flag,
            aci_quantile=getattr(self.soft_sensor, "alpha_t", None),
            s_event=s_event,
            coverage_floor=floor,
        )
        self._seq += 1
        return record

    def run(
        self, n_cycles: int, rng: np.random.Generator | None = None
    ) -> list[DynamicCycleRecord]:
        """Run ``n_cycles`` decision cycles; returns the per-cycle records."""
        return [self.run_cycle(rng=rng) for _ in range(n_cycles)]
