"""Unit tests for the closed-loop orchestrator (``ipis.integration.orchestrator``)."""

from __future__ import annotations

import numpy as np

from ipis.integration.orchestrator import (
    ClosedLoopOrchestrator,
    PdMReading,
    RTOReading,
    SoftSensorReading,
    true_rul_hours,
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
)

# --- stubs ----------------------------------------------------------------------


def _xb_stub(R: float, D: float, z: float) -> float:
    return 0.04 * float(np.exp(-0.3 * (R - 1.0)))


def _tray_stub(R: float, D: float) -> float:
    return 104.0 - 2.0 * (R - 2.0)


class _PropStub:
    def relative_volatility(self, temp_c: float) -> float:
        return 6.0

    def liquid_viscosity_cp(self, temp_c: float) -> float:
        return 0.12

    def k_value_hk(self, temp_c: float) -> float:
        return 0.8


def _feature_fn(out) -> np.ndarray:
    return np.array([out.sensor_temp_c, out.operating_point.alpha], dtype=float)


class _SoftSensorStub:
    def __init__(self, half_width: float = 0.002, drift: bool = False) -> None:
        self.half_width = half_width
        self.drift = drift
        self.labelled: list[tuple[str, float]] = []

    def predict(self, features, sample_id) -> SoftSensorReading:
        return SoftSensorReading(estimate=0.03, half_width=self.half_width, drift=self.drift)

    def label(self, sample_id: str, y_true: float) -> None:
        self.labelled.append((sample_id, y_true))


class _RTOStub:
    """Records the backoff it receives; returns a fixed recommendation."""

    def __init__(self, hold: bool = False) -> None:
        self.hold = hold
        self.backoffs: list[float] = []
        self.recommendation = (3.0, 48.0)

    def solve(self, *, backoff: float, rto_hold: bool, feed_z: float):
        self.backoffs.append(backoff)
        if self.hold or rto_hold:
            return None
        return RTOReading(
            reflux_ratio=self.recommendation[0],
            distillate_kmol_h=self.recommendation[1],
            active_constraints=("c4_spec_backoff",),
        )


class _PdMStub:
    def __init__(self, rul: float | None = 500.0) -> None:
        self.rul = rul

    def observe(self, equipment_id, features) -> PdMReading:
        return PdMReading(health_score=0.9, flag="OK", rul_hours=self.rul)


def _plant(rate: float = 1e-3) -> DebutanizerPlant:
    return DebutanizerPlant(
        xb_truth=_xb_stub,
        tray_temp=_tray_stub,
        properties=_PropStub(),
        feed=FeedSpec(F=100.0, z_lk=0.35, q=1.0),
        degradation=PumpDegradation(ref_reflux_flow=125.0, base_rate=rate),
        synthesizer=FeatureSynthesizer(
            feature_names=("rms", "kurtosis"),
            baseline=np.zeros(2),
            growth=np.ones(2),
        ),
        feed_z=0.35,
    )


def _orch(soft=None, rto=None, pdm=None, **kw) -> ClosedLoopOrchestrator:
    return ClosedLoopOrchestrator(
        plant=_plant(kw.pop("rate", 1e-3)),
        feature_fn=_feature_fn,
        soft_sensor=soft or _SoftSensorStub(),
        rto_solver=rto or _RTOStub(),
        pdm=pdm or _PdMStub(),
        **kw,
    )


# --- tests ----------------------------------------------------------------------


def test_first_cycle_applies_seed() -> None:
    orch = _orch(seed_setpoints=(2.5, 49.0))
    rec = orch.run_cycle()
    assert rec.sequence_id == 0
    assert rec.applied_reflux == 2.5
    assert rec.applied_distillate == 49.0


def test_causal_timing_next_cycle_applies_recommendation() -> None:
    # Cycle k+1 must apply exactly the recommendation computed in cycle k.
    rto = _RTOStub()
    rto.recommendation = (3.3, 47.5)
    orch = _orch(rto=rto, seed_setpoints=(2.5, 49.0))
    recs = orch.run(2)
    assert (recs[0].applied_reflux, recs[0].applied_distillate) == (2.5, 49.0)
    assert (recs[1].applied_reflux, recs[1].applied_distillate) == (3.3, 47.5)


def test_backoff_equals_m1_half_width() -> None:
    soft = _SoftSensorStub(half_width=0.0031)
    rto = _RTOStub()
    orch = _orch(soft=soft, rto=rto)
    orch.run_cycle()
    assert rto.backoffs[-1] == 0.0031


def test_drift_triggers_hold_and_setpoints_frozen() -> None:
    soft = _SoftSensorStub(drift=True)
    orch = _orch(soft=soft, seed_setpoints=(2.5, 49.0))
    recs = orch.run(2)
    assert recs[0].held is True
    assert recs[0].active_constraints == ("rto_hold",)
    assert recs[0].state_fields["setpoint_recommendations"] == {}
    # held -> setpoints unchanged on the next cycle
    assert (recs[1].applied_reflux, recs[1].applied_distillate) == (2.5, 49.0)


def test_delayed_label_feedback() -> None:
    soft = _SoftSensorStub()
    orch = _orch(soft=soft, label_delay=2)
    recs = orch.run(3)
    # With delay 2, after 3 cycles only cycle-0's label has been delivered.
    assert len(soft.labelled) == 1
    assert soft.labelled[0][0] == "0"
    assert soft.labelled[0][1] == recs[0].xb_true


def test_state_fields_match_bus_schema() -> None:
    orch = _orch()
    sf = orch.run_cycle().state_fields
    for key in (
        "sequence_id",
        "process_conditions",
        "quality_estimate",
        "quality_confidence",
        "equipment_health",
        "health_flags",
        "remaining_useful_life",
        "setpoint_recommendations",
        "active_constraints",
        "module_status",
    ):
        assert key in sf
    assert orch.quality_key in sf["quality_estimate"]
    assert orch.equipment_id in sf["equipment_health"]


def test_rul_omitted_before_onset() -> None:
    orch = _orch(pdm=_PdMStub(rul=None))
    sf = orch.run_cycle().state_fields
    assert sf["remaining_useful_life"] == {}


def test_budget_logged_only_with_config() -> None:
    cfg = PsiConfig(
        L1=0.1,
        L2=0.2,
        fortuna_op=OperatingPoint(
            R=2.5, D=49.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=122.5
        ),
        femto_ref_reflux_flow=125.0,
        scales=CoordinateScales(),
    )
    with_cfg = _orch(psi_config=cfg).run_cycle()
    without = _orch().run_cycle()
    assert with_cfg.budget is not None
    assert without.budget is None


def test_true_rul_positive_and_decreasing() -> None:
    orch = _orch(rate=1e-2)
    first = orch.run_cycle()
    for _ in range(15):
        last = orch.run_cycle()
    assert np.isfinite(first.true_rul_hours)
    assert first.true_rul_hours > 0.0
    assert last.true_rul_hours < first.true_rul_hours


def test_true_rul_helper_infinite_at_zero_rate() -> None:
    deg = PumpDegradation(ref_reflux_flow=125.0, base_rate=0.0)
    assert true_rul_hours(deg, 125.0) == float("inf")


def test_sequence_ids_increment() -> None:
    recs = _orch().run(4)
    assert [r.sequence_id for r in recs] == [0, 1, 2, 3]
