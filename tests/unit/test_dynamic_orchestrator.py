"""Unit tests for the Module 5 dynamic orchestrator (``dynamic_orchestrator``).

Covers the causal-timing / delayed-label contract (the O1 substrate), CycleRecord
compatibility with the M4 ``run_coverage`` harness, recorder population, and the headline
demonstration: over a long campaign with delayed labels the M1 ACI interval holds its
coverage and the joint event S_k meets its certified floor.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from ipis.integration.coverage import CoverageConfig, run_coverage
from ipis.integration.dynamic_orchestrator import (
    DynamicClosedLoopOrchestrator,
    DynamicCycleRecord,
)
from ipis.integration.dynamic_plant import DynamicDebutanizerPlant
from ipis.integration.orchestrator import PdMReading, RTOReading, SoftSensorReading
from ipis.integration.plant import FeatureSynthesizer, FeedSpec, PumpDegradation
from ipis.module1_soft_sensor.evaluation.conformal import ACIConformal, aci_step

# --- plant/thermo stubs --------------------------------------------------------

_D_HOLD = 35.0
_A, _B = -0.2064, 0.00226  # local affine soft sensor (linearized at R~5, temp~98)


def _xb_stub(R: float, D: float, z: float) -> float:
    return 0.05 * float(np.exp(-0.3 * (R - 1.0)))  # monotone decreasing in R


def _tray_stub(R: float, D: float) -> float:
    return 108.0 - 2.0 * R


class _PropStub:
    def relative_volatility(self, temp_c: float) -> float:
        return 6.0

    def liquid_viscosity_cp(self, temp_c: float) -> float:
        return 0.12

    def k_value_hk(self, temp_c: float) -> float:
        return 0.8


def _feature_fn(out) -> np.ndarray:
    return np.array([out.sensor_temp_c], dtype=float)


# --- service stubs -------------------------------------------------------------


class _DelayedACISoftSensor:
    """Affine soft sensor + ACI, with CORRECT delayed-label feedback.

    Stores the half-width used to FORM each cycle's interval and, when that cycle's label
    arrives later, applies the ACI step against the stored half-width (not the most recent
    one). This is the delayed-feedback semantics the loop needs; ``ACIConformal.update``
    alone couples to the last ``interval`` call and would be wrong under delay.
    """

    def __init__(self, init_residuals, alpha, gamma, rng, noise_sd=5e-4, window=200):
        self.aci = ACIConformal(init_residuals, alpha=alpha, gamma=gamma, window=window)
        self.rng = rng
        self.noise_sd = noise_sd
        self._pending: dict[str, tuple[float, float]] = {}
        self.label_log: list[str] = []

    @property
    def alpha_t(self) -> float:
        return float(self.aci.alpha_t)

    def predict(self, features, sample_id) -> SoftSensorReading:
        temp = float(features[0])
        noise = self.rng.normal(0.0, self.noise_sd) if self.noise_sd > 0 else 0.0
        est = _A + _B * temp + noise
        self.aci.interval(np.array(est, dtype=float))  # sets _last_halfwidth
        hw = float(self.aci._last_halfwidth)
        self._pending[sample_id] = (est, hw)
        return SoftSensorReading(estimate=est, half_width=hw, drift=False)

    def label(self, sample_id, y_true) -> None:
        y_pred, hw = self._pending.pop(sample_id)
        score = abs(float(y_true) - y_pred)
        covered = score <= hw
        self.aci.alpha_t = aci_step(
            self.aci.alpha_t, covered, self.aci.gamma, self.aci.target_alpha
        )
        self.aci.scores.append(score)
        self.label_log.append(sample_id)


class _BackoffRTO:
    """Conformal back-off RTO stub: smallest R meeting ``xb + backoff <= spec`` at fixed D.

    Uses the (idealized) true surface and picks the smallest reflux achieving the
    chance-constrained upper bound, sparing the pump. Mirrors the real chance-constrained
    NLP's behavior cheaply (the GEKKO solve is the repo path)."""

    def __init__(self, spec, D=_D_HOLD, r_bounds=(2.0, 8.0)):
        self.spec = float(spec)
        self.D = float(D)
        self.r_lo, self.r_hi = r_bounds

    def solve(self, *, backoff, rto_hold, feed_z, operating_point) -> RTOReading | None:
        if rto_hold:
            return None
        target = self.spec - float(backoff)
        lo, hi = self.r_lo, self.r_hi
        if _xb_stub(hi, self.D, feed_z) > target:
            return RTOReading(
                reflux_ratio=hi, distillate_kmol_h=self.D, active_constraints=("quality",)
            )
        if _xb_stub(lo, self.D, feed_z) <= target:
            return RTOReading(reflux_ratio=lo, distillate_kmol_h=self.D, active_constraints=())
        for _ in range(40):  # bisection: xb is decreasing in R
            mid = 0.5 * (lo + hi)
            if _xb_stub(mid, self.D, feed_z) <= target:
                hi = mid
            else:
                lo = mid
        return RTOReading(
            reflux_ratio=hi, distillate_kmol_h=self.D, active_constraints=("quality",)
        )


class _OkPdM:
    def observe(self, equipment_id, features) -> PdMReading:
        return PdMReading(health_score=0.95, flag="OK", rul_hours=None)


# --- factory (run_coverage-compatible) -----------------------------------------


def _build(seed: int, cfg: CoverageConfig) -> DynamicClosedLoopOrchestrator:
    ref = 5.0 * _D_HOLD  # nominal reflux at R=5 -> affinity load ~ 1 near the operating point
    plant = DynamicDebutanizerPlant(
        xb_truth=_xb_stub,
        tray_temp=_tray_stub,
        properties=_PropStub(),
        feed=FeedSpec(F=100.0, z_lk=0.35, q=1.0),
        feed_z=0.35,
        degradation=PumpDegradation(ref_reflux_flow=ref, base_rate=1e-5, load_exponent=3.0),
        synthesizer=FeatureSynthesizer(
            feature_names=("rms", "kurtosis"), baseline=np.zeros(2), growth=np.ones(2)
        ),
        dt=0.0167,
        tau_act=0.0167,
        tau_proc=0.5,
        tau_temp=0.25,
        deadtime_h=0.083,
        R0=5.0,
        D0=_D_HOLD,
    )
    soft_sensor = _DelayedACISoftSensor(
        init_residuals=np.full(60, 0.002),
        alpha=cfg.alpha1,
        gamma=0.02,
        rng=np.random.default_rng(1000 + seed),
    )
    return DynamicClosedLoopOrchestrator(
        plant=plant,
        feature_fn=_feature_fn,
        soft_sensor=soft_sensor,
        rto_solver=_BackoffRTO(cfg.spec_xb_c4),
        pdm=_OkPdM(),
        steps_per_cycle=60,
        seed_setpoints=(5.0, _D_HOLD),
        label_delay_cycles=2,
        eps=cfg.eps,
        alpha1=cfg.alpha1,
        alpha2=cfg.alpha2,
        spec_xb_c4=cfg.spec_xb_c4,
        rul_min_hours=cfg.rul_min_hours,
    )


_CFG = CoverageConfig(spec_xb_c4=0.02, rul_min_hours=200.0, alpha1=0.10, alpha2=0.10, eps=0.05)


# --- tests ---------------------------------------------------------------------


def test_runs_and_records() -> None:
    orch = _build(0, _CFG)
    recs = orch.run(10, rng=np.random.default_rng(0))
    assert len(recs) == 10
    assert isinstance(recs[0], DynamicCycleRecord)
    assert len(orch.recorder) == 10
    # the RTO moves the setpoint off the seed, and the actuator settles within the cycle
    # (tau_act << RTO interval), so end-of-cycle realized R has caught up to commanded.
    assert recs[1].applied_reflux != recs[0].applied_reflux
    assert recs[1].realized_reflux == pytest.approx(recs[1].applied_reflux, rel=1e-3)


def test_delayed_label_reaches_aci_with_exact_cycle_lag() -> None:
    orch = _build(0, _CFG)
    n, da = 12, orch.label_delay_cycles
    orch.run(n, rng=np.random.default_rng(0))
    ss = orch.soft_sensor
    # labels are released in order, lagging by exactly D_a cycles.
    assert ss.label_log == [str(i) for i in range(n - da)]
    # ACI alpha_t cannot move until the first label arrives (cycles 0..D_a-1 untouched).
    arr = orch.recorder.to_arrays()
    alpha_trace = arr["aci_quantile"]
    assert np.allclose(alpha_trace[:da], _CFG.alpha1)


def test_record_is_run_coverage_compatible() -> None:
    rec = _build(0, _CFG).run(1, rng=np.random.default_rng(0))[0]
    for fld in ("xb_true", "true_rul_hours", "active_constraints", "held", "severity"):
        assert hasattr(rec, fld)
    assert rec.s_event in (True, False)
    assert rec.certified_floor == pytest.approx(1.0 - (0.10 + 0.10) - 0.05)


def test_recorder_is_json_serializable_with_intel() -> None:
    orch = _build(0, _CFG)
    orch.run(5, rng=np.random.default_rng(0))
    rows = orch.recorder.to_records()
    json.dumps(rows)  # must not raise
    assert rows[0]["coverage_floor"] == pytest.approx(0.75)
    assert rows[-1]["aci_quantile"] is not None


def test_horizon_interval_coverage_holds_under_delay() -> None:
    # Single long campaign: the M1 ACI interval covers xb_true near 1 - alpha1 despite the
    # 2-cycle label delay and the feedback-induced dependence.
    orch = _build(7, _CFG)
    orch.run(400, rng=np.random.default_rng(7))
    a = orch.recorder.to_arrays()
    covered = np.abs(a["xb_true"] - a["quality_estimate"]) <= a["quality_half_width"]
    cov = float(np.mean(covered))
    assert (
        abs(cov - (1.0 - _CFG.alpha1)) <= 0.05
    ), f"horizon interval coverage off target: {cov:.3f}"
    # alpha_t stays bounded (ACI adapts but does not diverge under delayed feedback).
    assert np.all(a["aci_quantile"] > 0.0) and np.all(a["aci_quantile"] < 0.60)


def test_horizon_sk_meets_certified_floor() -> None:
    # The joint safety event S_k = {x<=spec} and {rho>=rho_min} holds at >= the certified
    # floor over the campaign, measured by the same Wilson harness M4 uses.
    result = run_coverage(
        _build, CoverageConfig(**{**_CFG.__dict__, "n_seeds": 3, "n_cycles": 120})
    )
    assert result.certified_floor == pytest.approx(0.75)
    assert result.meets_floor, (
        f"S_k coverage {result.s_coverage:.3f} CI {result.s_coverage_ci} "
        f"below floor {result.certified_floor:.3f}"
    )
    assert result.quality_coverage >= 0.90
