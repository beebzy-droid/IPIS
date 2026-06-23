"""Unit tests for the Module 5 dynamic plant (``ipis.integration.dynamic_plant``).

The load-bearing test is ``test_steady_state_matches_static_twin``: the dynamic plant
must settle to the exact Module 4 (static GP) twin output, so the composed certificate
calibration transfers. The remaining tests pin the transport-lag mechanics.
"""

from __future__ import annotations

import numpy as np
import pytest

from ipis.integration.dynamic_plant import (
    DynamicDebutanizerPlant,
    DynamicPlantOutput,
    first_order_step,
)
from ipis.integration.plant import (
    DebutanizerPlant,
    FeatureSynthesizer,
    FeedSpec,
    PumpDegradation,
)

# --- injected stubs (stand in for the M3 GP surfaces and CoolProp) -------------


def _xb_stub(R: float, D: float, z: float) -> float:
    # More reflux -> purer bottoms -> less C4 in bottoms (monotone decreasing in R).
    return 0.05 * float(np.exp(-0.3 * (R - 1.0)))


def _tray_stub(R: float, D: float) -> float:
    return 104.0 - 2.0 * (R - 2.0)


class _PropStub:
    def relative_volatility(self, temp_c: float) -> float:
        return 6.0 * float(np.exp(-0.01 * (temp_c - 104.0)))

    def liquid_viscosity_cp(self, temp_c: float) -> float:
        return 0.12

    def k_value_hk(self, temp_c: float) -> float:
        return 0.8


def _synth() -> FeatureSynthesizer:
    return FeatureSynthesizer(
        feature_names=("rms", "kurtosis", "bpfo"),
        baseline=np.zeros(3),
        growth=np.ones(3),
    )


def _dynamic(**kw: object) -> DynamicDebutanizerPlant:
    return DynamicDebutanizerPlant(
        xb_truth=_xb_stub,
        tray_temp=_tray_stub,
        properties=_PropStub(),
        feed=FeedSpec(F=100.0, z_lk=0.5, q=1.0),
        degradation=PumpDegradation(ref_reflux_flow=125.0, base_rate=1.0e-3),
        synthesizer=_synth(),
        feed_z=0.5,
        **kw,  # type: ignore[arg-type]
    )


def _static() -> DebutanizerPlant:
    return DebutanizerPlant(
        xb_truth=_xb_stub,
        tray_temp=_tray_stub,
        properties=_PropStub(),
        feed=FeedSpec(F=100.0, z_lk=0.5, q=1.0),
        degradation=PumpDegradation(ref_reflux_flow=125.0, base_rate=1.0e-3),
        synthesizer=_synth(),
        feed_z=0.5,
    )


# --- first-order helper --------------------------------------------------------


def test_first_order_one_tau_is_one_minus_inv_e() -> None:
    # After dt == tau, the response has closed 1 - 1/e ~ 0.632 of the gap.
    out = first_order_step(0.0, 1.0, tau_h=0.5, dt_h=0.5)
    assert out == pytest.approx(1.0 - np.exp(-1.0), abs=1e-9)


def test_first_order_zero_tau_is_instant() -> None:
    assert first_order_step(0.0, 7.0, tau_h=0.0, dt_h=0.1) == 7.0


# --- the load-bearing continuity check -----------------------------------------


def test_steady_state_matches_static_twin() -> None:
    """Settled dynamic truth == M4 static GP twin output (so the certificate transfers)."""
    R, D = 3.5, 55.0
    dyn = _dynamic()
    dyn.seed_steady(2.0, 50.0)  # start somewhere else, then drive to (R, D)
    # settle: > 15 time-constants past the slowest lag, and past the deadtime.
    n = (
        int(15.0 * max(dyn.tau_proc, dyn.tau_temp, dyn.deadtime_h) / dyn.dt)
        + dyn.deadtime_steps()
        + 5
    )
    traj = dyn.run_hold(R, D, n)
    last = traj[-1]

    static_out = _static().step(R, D)
    assert last.xb_true == pytest.approx(static_out.xb_true, rel=1e-6)
    assert last.sensor_temp_c == pytest.approx(static_out.sensor_temp_c, rel=1e-6)
    # once settled and past deadtime, the analyzer reading equals the truth.
    assert last.xb_measured == pytest.approx(last.xb_true, rel=1e-6)
    # realized decisions have caught up to the commanded setpoints.
    assert last.realized_reflux == pytest.approx(R, rel=1e-6)
    assert last.realized_distillate == pytest.approx(D, rel=1e-6)


def test_steady_state_monotonicity_inherited_from_surface() -> None:
    # The GP gain's monotonicity (more R -> lower xb) survives the dynamics.
    lo = _dynamic()
    hi = _dynamic()
    n = 800
    xb_lo = lo.run_hold(2.0, 50.0, n)[-1].xb_true
    xb_hi = hi.run_hold(4.0, 50.0, n)[-1].xb_true
    assert xb_hi < xb_lo


# --- actuator lag --------------------------------------------------------------


def test_actuator_first_order_time_constant() -> None:
    # With dt == tau_act, one step closes 1 - 1/e of the R gap (commanded != realized).
    dyn = _dynamic(dt=0.0167, tau_act=0.0167, tau_proc=0.0, tau_temp=0.0, deadtime_h=0.0)
    dyn.seed_steady(2.0, 50.0)
    out = dyn.step(4.0, 50.0)
    expected = 2.0 + (4.0 - 2.0) * (1.0 - np.exp(-1.0))
    assert out.realized_reflux == pytest.approx(expected, abs=1e-6)
    assert out.applied_reflux == 4.0  # the command is recorded distinctly


def test_psi_uses_realized_not_commanded_path() -> None:
    # Mid-transient, the operating point (psi input) uses the realized R, not commanded.
    dyn = _dynamic(tau_act=0.5)  # slow actuator so the gap is visible after one step
    dyn.seed_steady(2.0, 50.0)
    out = dyn.step(5.0, 50.0)
    assert out.operating_point.R == pytest.approx(out.realized_reflux)
    assert out.operating_point.R < out.applied_reflux


# --- process lag and analyzer deadtime -----------------------------------------


def test_process_lag_delays_composition() -> None:
    # After one short step the true xb has not jumped to the new steady state.
    dyn = _dynamic(dt=0.01, tau_proc=0.5, tau_act=0.0, deadtime_h=0.0)
    xb0 = dyn._xb  # steady at (R0, D0)
    xb_ss_new = _xb_stub(5.0, 50.0, 0.5)
    out = dyn.step(5.0, 50.0)
    assert xb_ss_new < out.xb_true < xb0  # strictly between old state and new target


def test_deadtime_delays_measurement_by_exact_steps() -> None:
    # Isolate deadtime: instant actuator + process, so true xb jumps immediately.
    dyn = _dynamic(dt=0.01, tau_act=0.0, tau_proc=0.0, tau_temp=0.0, deadtime_h=0.05)
    L = dyn.deadtime_steps()
    assert L == 5
    xb_old = dyn._xb
    xb_new = _xb_stub(5.0, 50.0, 0.5)
    outs = dyn.run_hold(5.0, 50.0, L + 2)
    # truth is at the new value immediately (instant lags)
    assert outs[0].xb_true == pytest.approx(xb_new, rel=1e-9)
    # measurement still reads the OLD value until L samples have elapsed
    assert outs[L - 1].xb_measured == pytest.approx(xb_old, rel=1e-9)
    # then the new value reaches the analyzer
    assert outs[L].xb_measured == pytest.approx(xb_new, rel=1e-9)


# --- contract, degradation clock, determinism ----------------------------------


def test_output_satisfies_plant_output_contract() -> None:
    out = _dynamic().step(3.0, 50.0)
    for fld in (
        "sensor_temp_c",
        "xb_true",
        "pump_features",
        "operating_point",
        "oconnell_efficiency",
        "severity",
    ):
        assert hasattr(out, fld), f"missing PlantOutput field {fld}"
    assert isinstance(out, DynamicPlantOutput)


def test_degradation_clock_aligned_to_plant() -> None:
    dyn = _dynamic(dt=0.25)
    assert dyn.degradation.dt == pytest.approx(0.25)
    s0 = dyn.degradation.severity
    dyn.run_hold(3.0, 50.0, 10)
    assert dyn.degradation.severity > s0  # damage accrues


def test_measurement_noise_is_reproducible() -> None:
    a = _dynamic(meas_noise_sd=1e-3)
    b = _dynamic(meas_noise_sd=1e-3)
    ra = a.step(3.0, 50.0, rng=np.random.default_rng(0)).xb_measured
    rb = b.step(3.0, 50.0, rng=np.random.default_rng(0)).xb_measured
    assert ra == rb


def test_rejects_nonpositive_dt() -> None:
    with pytest.raises(ValueError):
        _dynamic(dt=0.0)
