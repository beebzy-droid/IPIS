"""Dynamic / transport-lag plant for IPIS Module 5 (horizon-coverage substrate).

Module 4's plant (``ipis.integration.plant.DebutanizerPlant``) is *quasi-static*:
``step(R, D)`` returns the steady-state truth instantly. Its column truth is the
Module 3 GP surface ``xb_truth(R, D, z)`` (a DWSIM-fit ``TruthSurface3D``); the Perry
thermo (Underwood, O'Connell) are consistency diagnostics, not governing equations.

Module 5 needs a *dynamic* plant so the per-cycle composed certificate (M4 Theorem 1)
can be lifted to a long-run / horizon guarantee under feedback-induced dependence
(ACI; Gibbs & Candes 2021). Rather than introduce a from-scratch mechanistic stage
model -- which would disagree with both the GP twin and DWSIM and force a full re-pin
of the M4 certificate calibration -- this module keeps the *validated GP steady-state
surface as the static gain* and wraps it in dynamics:

    nonlinear-static (GP surface)  +  linear-dynamic (transport)  block.

This is a standard Hammerstein-class dynamic-plant representation. By construction its
steady state reproduces the M4 twin exactly (asserted in ``test_dynamic_plant``), so
the certificate machinery transfers with at most a tray-efficiency re-pin (open O3).

Transport elements made first-class (each a documented default to be pinned to the
specific column at draft time -- verify-before-load-bearing):

  * actuator first-order lag on the decisions ``(R, D)`` -- the commanded setpoint is
    not realized instantly (control valve + flow loop), so the similitude coordinate
    ``psi`` evolves over the *realized* path, not the commanded step;
  * process first-order lag on the composition and sensor-temperature response (column
    holdup / throughput) toward the GP steady state at the *realized* (R, D);
  * analyzer deadtime on the *measured* quality (gas-chromatograph cycle), so the label
    that drives M1's ACI arrives delayed -- the dependence/delay ACI absorbs (the
    O1-under-deadtime timing analysis is increment 2).

Time constants are in HOURS; defaults are illustrative orders of magnitude:
  * ``tau_act``    ~ 1 min   valve stroke + flow loop
  * ``tau_proc``   ~ 30 min  overhead composition settling
  * ``tau_temp``   ~ 15 min  sensor-stage temperature
  * ``deadtime_h`` ~ 5 min   GC analyzer cycle

The integration timestep ``dt`` is a fixed plant property; one ``step`` advances the
continuous dynamics by ``dt`` and accrues exactly ``dt`` of pump degradation (the plant
aligns ``PumpDegradation.dt`` to its own clock). The RTO/decision interval is many
``dt`` steps and is the caller's concern (the dynamic orchestrator, increment 2).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from ipis.integration.plant import (
    FeatureSynthesizer,
    FeedSpec,
    PropertyEvaluator,
    PumpDegradation,
    TrayTempSurface,
    XbTruth,
    column_flows,
    oconnell_efficiency,
    stripping_factor,
    underwood_rmin_binary,
)
from ipis.integration.psi import OperatingPoint

_EPS = 1e-6


def first_order_step(x: float, target: float, tau_h: float, dt_h: float) -> float:
    """Exact zero-order-hold update of ``dx/dt = (target - x)/tau`` over ``dt``.

    ``tau_h <= 0`` collapses to an instantaneous response (returns ``target``).
    Unconditionally stable for any ``dt_h >= 0`` with a held target.
    """
    if tau_h <= 0.0:
        return float(target)
    decay = math.exp(-dt_h / tau_h)
    return float(target + (x - target) * decay)


@dataclass(frozen=True)
class DynamicPlantOutput:
    """One sampled cycle of the dynamic plant.

    The first six fields match ``ipis.integration.plant._PlantOutput`` and so satisfy
    the ``PlantOutput`` protocol structurally -- the Module 4 orchestrator, feature
    transform and coverage harness consume this object unchanged. The remaining fields
    expose the dynamic story increment 2 needs: realized vs commanded decisions, the
    elapsed time, and the deadtime-delayed analyzer reading (the delayed ACI label).
    """

    sensor_temp_c: float
    xb_true: float  # current dynamic bottoms C4 -- coverage ground truth NOW
    pump_features: npt.NDArray[np.float64]
    operating_point: OperatingPoint
    oconnell_efficiency: float
    severity: float
    time_h: float
    applied_reflux: float  # commanded R (setpoint)
    applied_distillate: float  # commanded D (setpoint)
    realized_reflux: float  # R after actuator lag (drives psi and the pump)
    realized_distillate: float
    xb_measured: float  # analyzer reading = xb_true delayed by deadtime (+ noise)


@dataclass
class DynamicDebutanizerPlant:
    """GP-gain + transport-dynamics plant for the horizon-coverage loop."""

    xb_truth: XbTruth
    tray_temp: TrayTempSurface
    properties: PropertyEvaluator
    feed: FeedSpec
    degradation: PumpDegradation
    synthesizer: FeatureSynthesizer
    feed_z: float = 0.5

    # transport dynamics (hours) -- pin to the column (see module docstring)
    dt: float = 0.0167  # fixed integration timestep ~1 min
    tau_act: float = 0.0167  # actuator / flow-loop lag ~1 min
    tau_proc: float = 0.5  # composition settling ~30 min
    tau_temp: float = 0.25  # sensor-stage temperature ~15 min
    deadtime_h: float = 0.083  # analyzer (GC) deadtime ~5 min
    meas_noise_sd: float = 0.0  # analyzer measurement noise (sd, xb units)

    # initial operating point (seeds realized + process states at steady state)
    R0: float = 3.0
    D0: float = 50.0

    # --- state (not init) ---
    _R_real: float = field(default=0.0, init=False)
    _D_real: float = field(default=0.0, init=False)
    _xb: float = field(default=0.0, init=False)
    _temp: float = field(default=0.0, init=False)
    _t: float = field(default=0.0, init=False)
    _buf: deque[float] = field(default=None, init=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.dt <= 0.0:
            raise ValueError("integration timestep dt must be strictly positive")
        for name in ("tau_act", "tau_proc", "tau_temp", "deadtime_h", "meas_noise_sd"):
            if getattr(self, name) < 0.0:
                raise ValueError(f"{name} must be non-negative")
        # align the degradation clock to the plant clock (one step == dt hours)
        self.degradation.dt = self.dt
        self.seed_steady(self.R0, self.D0)

    # --- helpers ----------------------------------------------------------------
    def _steady(self, R: float, D: float) -> tuple[float, float]:
        return float(self.xb_truth(R, D, self.feed_z)), float(self.tray_temp(R, D))

    def deadtime_steps(self) -> int:
        """Number of samples of analyzer delay (``round(deadtime_h / dt)``)."""
        return int(round(self.deadtime_h / self.dt))

    def seed_steady(self, R: float, D: float) -> None:
        """Reset realized + process states to the steady state at (R, D)."""
        R = max(R, _EPS)
        D = float(np.clip(D, _EPS, self.feed.F - _EPS))
        self._R_real = R
        self._D_real = D
        xb_ss, t_ss = self._steady(R, D)
        self._xb = xb_ss
        self._temp = t_ss
        self._t = 0.0
        length = self.deadtime_steps() + 1
        self._buf = deque([xb_ss] * length, maxlen=length)

    def _operating_point(self, R: float, D: float, temp: float, xb: float) -> OperatingPoint:
        flows = column_flows(R, D, self.feed)
        alpha = self.properties.relative_volatility(temp)
        k_hk = self.properties.k_value_hk(temp)
        x_d_lk = (self.feed.F * self.feed.z_lk - flows.B * xb) / D
        x_d_lk = float(np.clip(x_d_lk, _EPS, 1.0 - _EPS))
        r_min = underwood_rmin_binary(alpha, self.feed.z_lk, x_d_lk, self.feed.q)
        strip = stripping_factor(k_hk, flows.V_strip, flows.L_strip)
        return OperatingPoint(
            R=R,
            D=D,
            alpha=alpha,
            R_min=r_min,
            strip_factor=strip,
            reflux_flow=flows.reflux_flow,
        )

    # --- the loop ---------------------------------------------------------------
    def step(
        self, R_cmd: float, D_cmd: float, rng: np.random.Generator | None = None
    ) -> DynamicPlantOutput:
        """Advance the continuous dynamics by one ``dt`` under held commands."""
        # 1) actuator lag: commanded -> realized
        self._R_real = max(first_order_step(self._R_real, R_cmd, self.tau_act, self.dt), _EPS)
        self._D_real = float(
            np.clip(
                first_order_step(self._D_real, D_cmd, self.tau_act, self.dt),
                _EPS,
                self.feed.F - _EPS,
            )
        )
        # 2) GP steady-state targets at the realized operating point (the static gain)
        xb_ss, t_ss = self._steady(self._R_real, self._D_real)
        # 3) process lag toward the targets
        self._temp = first_order_step(self._temp, t_ss, self.tau_temp, self.dt)
        self._xb = first_order_step(self._xb, xb_ss, self.tau_proc, self.dt)
        # 4) pump degradation driven by the REALIZED reflux flow (one dt)
        flows = column_flows(self._R_real, self._D_real, self.feed)
        severity = self.degradation.step(flows.reflux_flow)
        features = self.synthesizer.synthesize(severity, rng=rng)
        eta = oconnell_efficiency(
            self.properties.relative_volatility(self._temp),
            self.properties.liquid_viscosity_cp(self._temp),
        )
        # 5) analyzer deadtime FIFO on the true xb, plus optional measurement noise
        self._buf.append(self._xb)
        measured = self._buf[0]
        if rng is not None and self.meas_noise_sd > 0.0:
            measured = float(measured + rng.normal(0.0, self.meas_noise_sd))
        # 6) operating point from the realized path (psi evolves continuously)
        op = self._operating_point(self._R_real, self._D_real, self._temp, self._xb)
        self._t += self.dt
        return DynamicPlantOutput(
            sensor_temp_c=self._temp,
            xb_true=self._xb,
            pump_features=features,
            operating_point=op,
            oconnell_efficiency=eta,
            severity=severity,
            time_h=self._t,
            applied_reflux=R_cmd,
            applied_distillate=D_cmd,
            realized_reflux=self._R_real,
            realized_distillate=self._D_real,
            xb_measured=measured,
        )

    def run_hold(
        self, R_cmd: float, D_cmd: float, n_steps: int, rng: np.random.Generator | None = None
    ) -> list[DynamicPlantOutput]:
        """Convenience: hold a command for ``n_steps`` and return the trajectory."""
        return [self.step(R_cmd, D_cmd, rng=rng) for _ in range(n_steps)]
