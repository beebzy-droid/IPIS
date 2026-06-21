"""Closed-loop plant emulator for IPIS integration (P-GP substrate).

The column substrate is Module 3's *validated* GP surfaces -- ``TruthSurface3D``
for the true bottoms quality x_B(R, D, z) and the ``(R, D) -> tray-6 T`` surface
-- injected as callables so this module hard-imports neither Module 3 nor
CoolProp and stays unit-testable with stubs. Around that substrate this module
owns the Perry's-verified thermo/flow quantities the economic surrogate does not
expose, and the load-driven pump degradation that feeds Module 2's real
HI -> RUL pipeline (decision C1).

Per cycle, :meth:`DebutanizerPlant.step` returns:

  * ``sensor_temp_c``  -- tray-6 temperature (Module 1's feature input under P-GP)
  * ``xb_true``        -- true C4-in-bottoms (coverage ground truth)
  * ``pump_features``  -- synthetic vibration feature vector for ``PdMService``
  * ``operating_point``-- the :class:`~ipis.integration.psi.OperatingPoint` for
                          the ψ-budget penalty
  * ``oconnell_efficiency`` and ``severity`` diagnostics

Perry's Chemical Engineers' Handbook, 9th ed. (verified
``docs/module4/perry-verification.md``):

  * Underwood minimum reflux, common-root form  (Eq. 13-37 / 13-38)
  * stripping factor S = K_HK * V' / L'           (Eq. 13-44)
  * O'Connell overall efficiency                  (Eq. 14-138)
  * pump affinity laws                            (Table 10-13, via ``psi``)

Honest scope notes:
  * Under P-GP the GP surfaces ARE the twin, so O'Connell is a *diagnostic*
    (a consistency check against the twin's embedded efficiency), not a re-pin
    of the plant -- see open item O3.
  * K_HK for the stripping factor is evaluated at the sensor-stage temperature
    (the designated M1/M3 reference stage), a documented approximation.
  * The synthetic feature growth direction must be CALIBRATED on the repo
    against Module 2's fitted ``HealthIndexModel`` so that T^2 crosses the
    WARN/ALARM limits at the intended severity; the default here is an
    uncalibrated monotone drift suitable for testing the mechanics only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import numpy.typing as npt

from ipis.integration.psi import OperatingPoint, pump_load

# --- Injected substrate interfaces ---------------------------------------------


class XbTruth(Protocol):
    """True bottoms quality x_B as a function of (R, D, feed z)."""

    def __call__(self, R: float, D: float, z: float) -> float: ...


class TrayTempSurface(Protocol):
    """Sensor-stage (tray-6) temperature [degC] as a function of (R, D)."""

    def __call__(self, R: float, D: float) -> float: ...


class PropertyEvaluator(Protocol):
    """Thermophysical properties at a temperature [degC]. Production wires a
    CoolProp-backed implementation for the twin's component pair; tests inject a
    stub. Required (no fabricated default) -- verify-before-load-bearing."""

    def relative_volatility(self, temp_c: float) -> float: ...

    def liquid_viscosity_cp(self, temp_c: float) -> float: ...

    def k_value_hk(self, temp_c: float) -> float: ...


# --- Feed and flows -------------------------------------------------------------


@dataclass(frozen=True)
class FeedSpec:
    """Column feed: molar rate, light-key mole fraction, and thermal quality q."""

    F: float  # feed molar rate
    z_lk: float  # feed light-key mole fraction
    q: float = 1.0  # 1.0 = saturated liquid feed

    def __post_init__(self) -> None:
        if self.F <= 0:
            raise ValueError("feed rate F must be strictly positive")
        if not 0.0 < self.z_lk < 1.0:
            raise ValueError("feed light-key fraction z_lk must be in (0, 1)")


@dataclass(frozen=True)
class ColumnFlows:
    """Internal molar flows from a constant-molar-overflow balance."""

    B: float
    L_rect: float
    V_rect: float
    L_strip: float
    V_strip: float
    reflux_flow: float  # rectifying liquid = reflux pump duty


def column_flows(R: float, D: float, feed: FeedSpec) -> ColumnFlows:
    """Constant-molar-overflow flows for the two sections."""
    if D <= 0 or D >= feed.F:
        raise ValueError("distillate D must satisfy 0 < D < F")
    B = feed.F - D
    L_rect = R * D
    V_rect = (R + 1.0) * D
    L_strip = L_rect + feed.q * feed.F
    V_strip = L_strip - B
    return ColumnFlows(
        B=B,
        L_rect=L_rect,
        V_rect=V_rect,
        L_strip=L_strip,
        V_strip=V_strip,
        reflux_flow=L_rect,
    )


# --- Perry's-verified regime quantities ----------------------------------------


def underwood_rmin_binary(
    alpha: float, z_lk: float, x_d_lk: float, q: float, *, tol: float = 1e-12
) -> float:
    """Underwood minimum reflux for a binary key split (Eq. 13-37 / 13-38).

    Solves Eq. 13-38 for the common root theta in (1, alpha) (relative
    volatilities alpha_LK = alpha, alpha_HK = 1) by bisection, then evaluates
    Eq. 13-37 for ``R_min``. ``q`` is the feed thermal quality.
    """
    if alpha <= 1.0:
        raise ValueError("alpha must exceed 1 for a finite minimum reflux")
    if not (0.0 < z_lk < 1.0 and 0.0 < x_d_lk < 1.0):
        raise ValueError("z_lk and x_d_lk must be in (0, 1)")

    def eq38(theta: float) -> float:
        return alpha * z_lk / (alpha - theta) + (1.0 - z_lk) / (1.0 - theta) - (1.0 - q)

    lo, hi = 1.0 + tol, alpha - tol
    # eq38 -> -inf at theta->1+, +inf at theta->alpha-; monotone increasing between.
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        val = eq38(mid)
        if abs(val) < tol or (hi - lo) < tol:
            lo = hi = mid
            break
        if val < 0.0:
            lo = mid
        else:
            hi = mid
    theta = 0.5 * (lo + hi)
    rmin_plus_one = alpha * x_d_lk / (alpha - theta) + (1.0 - x_d_lk) / (1.0 - theta)
    return rmin_plus_one - 1.0


def stripping_factor(k_hk: float, v_strip: float, l_strip: float) -> float:
    """Stripping factor S = K_HK * V' / L' (Eq. 13-44; S = 1/A, A = L/(K V))."""
    if l_strip <= 0:
        raise ValueError("stripping-section liquid L' must be strictly positive")
    return k_hk * v_strip / l_strip


def oconnell_efficiency(alpha: float, mu_l_cp: float) -> float:
    """O'Connell overall column efficiency E_OC = 0.492 (alpha * mu_L)^-0.245.

    ``mu_l_cp`` is the liquid viscosity in centipoise (Perry Eq. 14-138 /
    Fig. 14-47). Verified against Perry Example 14-12: alpha=1.3, mu=0.25 -> 0.65.
    """
    if alpha <= 0 or mu_l_cp <= 0:
        raise ValueError("alpha and viscosity must be strictly positive")
    return 0.492 * (alpha * mu_l_cp) ** -0.245


# --- C1: load-driven pump degradation and synthetic vibration -------------------


@dataclass
class PumpDegradation:
    """Stateful bearing-degradation accumulator driven by affinity-law load.

    Damage accrues as ``base_rate * load**load_exponent * dt`` where ``load`` is
    the affinity-law pump load (BHP ratio) from :func:`psi.pump_load`; severity
    is the fraction of accumulated damage to ``damage_at_failure`` clamped to
    [0, 1]. Coefficients are configurable and must be calibrated to the FEMTO
    degradation timescale before the served RUL is load-bearing.
    """

    ref_reflux_flow: float
    base_rate: float = 1.0e-3
    load_exponent: float = 1.0
    damage_at_failure: float = 1.0
    dt: float = 1.0
    _damage: float = field(default=0.0, init=False)

    def step(self, reflux_flow: float) -> float:
        """Advance one cycle at the given reflux flow; return current severity."""
        load = pump_load(reflux_flow, self.ref_reflux_flow)
        self._damage += self.base_rate * load**self.load_exponent * self.dt
        return self.severity

    @property
    def severity(self) -> float:
        return float(min(1.0, self._damage / self.damage_at_failure))

    def reset(self) -> None:
        self._damage = 0.0


@dataclass
class FeatureSynthesizer:
    """Map degradation severity to a Module-2-compatible feature vector.

    At ``severity == 0`` the vector equals ``baseline`` (healthy); it drifts
    along ``growth`` with severity. CALIBRATE on the repo: set ``baseline`` to
    ``health_model.mean`` and ``growth`` so the Hotelling T^2 crosses the
    WARN/ALARM limits at the intended severity. The defaults are an uncalibrated
    monotone drift that exercises the mechanics only.
    """

    feature_names: tuple[str, ...]
    baseline: npt.NDArray[np.float64]
    growth: npt.NDArray[np.float64]
    noise_sd: float = 0.0

    def __post_init__(self) -> None:
        n = len(self.feature_names)
        if self.baseline.shape != (n,) or self.growth.shape != (n,):
            raise ValueError("baseline and growth must have length len(feature_names)")

    def synthesize(
        self, severity: float, rng: np.random.Generator | None = None
    ) -> npt.NDArray[np.float64]:
        x = self.baseline + severity * self.growth
        if rng is not None and self.noise_sd > 0.0:
            x = x + rng.normal(0.0, self.noise_sd, size=x.shape)
        return np.asarray(x, dtype=np.float64)


# --- Plant assembly -------------------------------------------------------------


class PlantOutput(Protocol):  # documentation alias; concrete type is _PlantOutput
    sensor_temp_c: float
    xb_true: float
    pump_features: npt.NDArray[np.float64]
    operating_point: OperatingPoint
    oconnell_efficiency: float
    severity: float


@dataclass(frozen=True)
class _PlantOutput:
    sensor_temp_c: float
    xb_true: float
    pump_features: npt.NDArray[np.float64]
    operating_point: OperatingPoint
    oconnell_efficiency: float
    severity: float


@dataclass
class DebutanizerPlant:
    """P-GP plant: injected GP surfaces + thermo + C1 pump degradation."""

    xb_truth: XbTruth
    tray_temp: TrayTempSurface
    properties: PropertyEvaluator
    feed: FeedSpec
    degradation: PumpDegradation
    synthesizer: FeatureSynthesizer
    feed_z: float = field(default=0.5)  # current feed light-key fraction (disturbance)

    def step(self, R: float, D: float, rng: np.random.Generator | None = None) -> _PlantOutput:
        """One closed-loop cycle: apply (R, D), realize plant truth and signals."""
        flows = column_flows(R, D, self.feed)
        sensor_t = float(self.tray_temp(R, D))
        xb = float(self.xb_truth(R, D, self.feed_z))

        alpha = self.properties.relative_volatility(sensor_t)
        mu_l = self.properties.liquid_viscosity_cp(sensor_t)
        k_hk = self.properties.k_value_hk(sensor_t)

        # Distillate light-key purity by overall LK mass balance: F z = D x_D + B x_B.
        x_d_lk = (self.feed.F * self.feed.z_lk - flows.B * xb) / D
        x_d_lk = float(np.clip(x_d_lk, 1e-6, 1.0 - 1e-6))

        r_min = underwood_rmin_binary(alpha, self.feed.z_lk, x_d_lk, self.feed.q)
        strip = stripping_factor(k_hk, flows.V_strip, flows.L_strip)
        eta = oconnell_efficiency(alpha, mu_l)

        severity = self.degradation.step(flows.reflux_flow)
        features = self.synthesizer.synthesize(severity, rng=rng)

        op = OperatingPoint(
            R=R,
            D=D,
            alpha=alpha,
            R_min=r_min,
            strip_factor=strip,
            reflux_flow=flows.reflux_flow,
        )
        return _PlantOutput(
            sensor_temp_c=sensor_t,
            xb_true=xb,
            pump_features=features,
            operating_point=op,
            oconnell_efficiency=eta,
            severity=severity,
        )
