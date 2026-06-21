"""Tests for the coverage harness (``ipis.integration.coverage``)."""

from __future__ import annotations

import numpy as np
import pytest

from ipis.integration.coverage import (
    CoverageConfig,
    build_demo_orchestrator,
    run_coverage,
    summarize,
    wilson_interval,
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

# --- cheap non-GEKKO factory for harness-logic tests ---------------------------


class _ConstRTO:
    def solve(self, *, backoff, rto_hold, feed_z, operating_point):
        if rto_hold:
            return None
        return RTOReading(reflux_ratio=1.9, distillate_kmol_h=35.0, active_constraints=())


class _StubM1:
    def predict(self, features, sample_id) -> SoftSensorReading:
        return SoftSensorReading(estimate=float(features[0]), half_width=0.002)

    def label(self, sample_id, y_true) -> None:
        return None


class _StubM2:
    def observe(self, equipment_id, features) -> PdMReading:
        return PdMReading(health_score=0.9, flag="OK", rul_hours=None)


def _xb(R, D, z):
    return 0.015  # always within a 0.02 spec -> quality coverage 1.0


def _tray(R, D):
    return 104.0


class _Prop:
    def relative_volatility(self, t):
        return 6.0

    def liquid_viscosity_cp(self, t):
        return 0.12

    def k_value_hk(self, t):
        return 0.8


def _const_factory(rate: float):
    def factory(seed: int, cfg: CoverageConfig) -> ClosedLoopOrchestrator:
        plant = DebutanizerPlant(
            xb_truth=_xb,
            tray_temp=_tray,
            properties=_Prop(),
            feed=FeedSpec(F=100.0, z_lk=0.35),
            degradation=PumpDegradation(ref_reflux_flow=66.5, base_rate=rate),
            synthesizer=FeatureSynthesizer(
                feature_names=("a",), baseline=np.zeros(1), growth=np.ones(1)
            ),
            feed_z=0.35,
        )
        return ClosedLoopOrchestrator(
            plant=plant,
            feature_fn=lambda out: np.array([out.xb_true]),
            soft_sensor=_StubM1(),
            rto_solver=_ConstRTO(),
            pdm=_StubM2(),
            seed_setpoints=(1.9, 35.0),
        )

    return factory


# --- Wilson interval -----------------------------------------------------------


def test_wilson_bounds() -> None:
    assert wilson_interval(0, 0) == (0.0, 1.0)
    lo, hi = wilson_interval(10, 10)
    assert hi == pytest.approx(1.0, abs=1e-9)
    assert lo < 1.0
    lo0, hi0 = wilson_interval(0, 10)
    assert lo0 == pytest.approx(0.0, abs=1e-9)
    assert hi0 > 0.0


def test_wilson_contains_point_estimate() -> None:
    lo, hi = wilson_interval(7, 10)
    assert lo <= 0.7 <= hi


# --- harness aggregation -------------------------------------------------------


def test_run_coverage_shapes_and_ranges() -> None:
    cfg = CoverageConfig(n_seeds=4, n_cycles=10, rul_min_hours=1.0)
    res = run_coverage(_const_factory(rate=1e-4), cfg)
    assert res.n_total == 40
    for v in (res.s_coverage, res.quality_coverage, res.rul_coverage):
        assert 0.0 <= v <= 1.0
    assert res.quality_coverage == pytest.approx(1.0)  # xb=0.015 < 0.02 spec
    assert res.s_coverage_ci[0] <= res.s_coverage <= res.s_coverage_ci[1]


def test_meets_floor_logic() -> None:
    # Very low rho_min -> RUL always satisfied -> S coverage high -> meets floor.
    cfg = CoverageConfig(n_seeds=4, n_cycles=10, rul_min_hours=1.0, eps=0.05)
    res = run_coverage(_const_factory(rate=1e-5), cfg)
    assert res.rul_coverage == pytest.approx(1.0)
    assert res.meets_floor is True


def test_rul_coverage_drops_with_faster_degradation() -> None:
    cfg = CoverageConfig(n_seeds=3, n_cycles=30, rul_min_hours=300.0)
    slow = run_coverage(_const_factory(rate=1e-4), cfg)
    fast = run_coverage(_const_factory(rate=5e-3), cfg)
    assert fast.rul_coverage <= slow.rul_coverage


def test_summarize_is_stringy() -> None:
    cfg = CoverageConfig(n_seeds=2, n_cycles=5, rul_min_hours=1.0)
    text = summarize(run_coverage(_const_factory(rate=1e-4), cfg))
    assert "S_k coverage" in text
    assert "RUL-floor coverage" in text


# --- the money shot: real plant + real health_rto (GEKKO) ----------------------


def test_money_shot_health_aware_preserves_rul() -> None:
    pytest.importorskip("gekko")
    # Tight spec (0.008): meeting it forces high reflux. The health-blind RTO
    # over-refluxes and burns the pump; the health-constrained RTO refuses
    # (the ψ-budget makes the spec unreachable) and holds at the nominal point.
    base = {
        "spec_xb_c4": 0.008,
        "rul_min_hours": 30.0,
        "n_seeds": 2,
        "n_cycles": 18,
        "alpha1": 0.1,
        "alpha2": 0.1,
    }
    blind = run_coverage(build_demo_orchestrator, CoverageConfig(eps=1.0e6, **base))
    cons = run_coverage(build_demo_orchestrator, CoverageConfig(eps=0.05, **base))

    # Core: the constrained loop preserves RUL where the blind loop consumes it.
    assert cons.rul_coverage > blind.rul_coverage
    assert cons.final_severity_mean < blind.final_severity_mean
    # The trade-off: the blind loop chases the spec, the constrained loop holds.
    assert blind.quality_coverage > cons.quality_coverage
    assert cons.frac_held > blind.frac_held
