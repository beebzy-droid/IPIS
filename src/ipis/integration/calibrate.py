"""Plant calibration: the two constants the integrated run must fit to Module 2.

``build_integrated_orchestrator`` takes two values that cannot be loaded -- they
must be fitted so the synthetic pump is consistent with the real M2:

  * ``PumpDegradation.base_rate``  -- sets the plant's true-RUL clock.
  * ``FeatureSynthesizer.growth``  -- sets where severity lands in M2's T^2.

Both are closed-form here. ``base_rate`` follows directly from the damage model;
``growth`` is the displacement from M2's healthy mean to its failure region,
scaled so severity reaches a chosen Hotelling-T^2 along the real failure
direction. :func:`verify_calibration` then runs a degradation trajectory through
the real ``PdMService`` and checks the synthesized features drive sensible
health/RUL behaviour (ALARM fires before end-of-life, health decreases, and M2's
RUL is a valid lower bound on the plant's true RUL).

The fitting functions are pure (duck-typed against M2's ``HealthIndexModel``) and
tested in the sandbox with a synthetic model; run them with your loaded M2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt


class HealthModel(Protocol):
    """The bits of M2's ``HealthIndexModel`` the calibration needs."""

    mean: npt.NDArray[np.float64]
    precision: npt.NDArray[np.float64]
    alarm_t2: float

    def t2(self, x: npt.NDArray[np.float64]) -> float: ...


def degradation_rate_for_rul(
    fresh_nominal_rul_hours: float,
    *,
    damage_at_failure: float = 1.0,
    dt: float = 1.0,
) -> float:
    """``PumpDegradation.base_rate`` so a fresh pump at the FEMTO reference load
    (load = 1) has true RUL = ``fresh_nominal_rul_hours``.

    Damage accrues at ``base_rate * load**exp * dt``; at load 1 a fresh pump
    (remaining = ``damage_at_failure``) survives ``damage_at_failure*dt/base_rate``
    hours, so ``base_rate = damage_at_failure*dt / fresh_nominal_rul_hours``. Set
    ``fresh_nominal_rul_hours`` to the characteristic length of M2's training
    degradation trajectories so the plant's true RUL and M2's similarity-RUL share
    a clock.
    """
    if fresh_nominal_rul_hours <= 0.0:
        raise ValueError("fresh_nominal_rul_hours must be positive")
    return damage_at_failure * dt / fresh_nominal_rul_hours


def synth_growth(
    health_model: HealthModel,
    failure_features: npt.ArrayLike,
    *,
    target_t2_mult: float = 2.0,
) -> npt.NDArray[np.float64]:
    """``FeatureSynthesizer.growth``: the healthy-mean -> failure-region
    displacement, scaled so severity = 1 reaches ``target_t2_mult * alarm_t2`` in
    M2's Hotelling T^2 along the real failure direction.

    With ``baseline = health_model.mean`` and this growth, ``t2(severity) =
    severity**2 * target_t2_mult * alarm_t2``, so ALARM (T^2 >= alarm_t2) fires at
    severity ``1/sqrt(target_t2_mult)`` -- e.g. ~0.71 for the default 2.0, leaving
    head-room before end-of-life. ``failure_features`` is the feature vector at
    end-of-life in M2's training data (its high-severity centroid).
    """
    if target_t2_mult <= 0.0:
        raise ValueError("target_t2_mult must be positive")
    mean = np.asarray(health_model.mean, dtype=float).ravel()
    delta = np.asarray(failure_features, dtype=float).ravel() - mean
    precision = np.asarray(health_model.precision, dtype=float)
    denom = float(delta @ precision @ delta)
    if denom <= 0.0:
        raise ValueError("failure_features coincide with the healthy mean")
    c = float(np.sqrt(target_t2_mult * float(health_model.alarm_t2) / denom))
    return c * delta


@dataclass(frozen=True)
class CalibrationReport:
    """Diagnostics from a verification degradation run."""

    reached_alarm: bool
    alarm_severity: float | None
    health_monotone: bool
    rul_lower_bound_valid: bool
    severities: tuple[float, ...]
    flags: tuple[str, ...]
    health_scores: tuple[float, ...]
    rul_hours: tuple[float | None, ...]
    true_rul_hours: tuple[float, ...]


def _is_alarm(flag: Any) -> bool:
    return "ALARM" in str(flag).upper()


def verify_calibration(
    pdm: Any,
    synthesizer: Any,
    *,
    ref_flow: float,
    base_rate: float,
    equipment_id: str = "reflux_pump_P101",
    load: float = 1.5,
    n_cycles: int = 60,
    damage_at_failure: float = 1.0,
    dt: float = 1.0,
    load_exponent: float = 1.0,
    lb_valid_frac: float = 0.9,
) -> CalibrationReport:
    """Run a constant-load degradation trajectory through the real M2 and report
    whether the synthesized features behave.

    ``load`` is the affinity load relative to the FEMTO reference (1.5 = 50%
    above nominal); the trajectory should drive severity high enough to trip
    ALARM. ``lb_valid_frac`` is the fraction of post-onset cycles for which M2's
    RUL must be a lower bound on the plant's true RUL.
    """
    from ipis.integration.orchestrator import true_rul_hours
    from ipis.integration.plant import PumpDegradation

    deg = PumpDegradation(
        ref_reflux_flow=ref_flow,
        base_rate=base_rate,
        load_exponent=load_exponent,
        damage_at_failure=damage_at_failure,
        dt=dt,
    )
    reflux = load * ref_flow
    sev: list[float] = []
    flags: list[str] = []
    health: list[float] = []
    ruls: list[float | None] = []
    trues: list[float] = []
    alarm_sev: float | None = None

    for _ in range(n_cycles):
        s = deg.step(reflux)
        x = synthesizer.synthesize(s)
        r = pdm.observe(equipment_id, x)
        flag = r["flag"]
        sev.append(s)
        flags.append(str(flag))
        health.append(float(r["health_score"]))
        rul = r.get("rul_hours")
        ruls.append(None if rul is None else float(rul))
        trues.append(true_rul_hours(deg, reflux))
        if alarm_sev is None and _is_alarm(flag):
            alarm_sev = s

    # health should be (weakly) non-increasing as damage accrues
    h = np.asarray(health)
    health_monotone = bool(np.all(np.diff(h) <= 1e-9))

    # where M2 reports a RUL, it should lower-bound the plant's true RUL
    paired = [(lo, tr) for lo, tr in zip(ruls, trues, strict=True) if lo is not None]
    if paired:
        valid = sum(lo <= tr + 1e-9 for lo, tr in paired) / len(paired)
        rul_lb_valid = valid >= lb_valid_frac
    else:
        rul_lb_valid = False

    return CalibrationReport(
        reached_alarm=alarm_sev is not None,
        alarm_severity=alarm_sev,
        health_monotone=health_monotone,
        rul_lower_bound_valid=rul_lb_valid,
        severities=tuple(sev),
        flags=tuple(flags),
        health_scores=tuple(health),
        rul_hours=tuple(ruls),
        true_rul_hours=tuple(trues),
    )
