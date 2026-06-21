"""Driver: integrated IPIS coverage sweep -> the Paper-4 headline figure.

Runs the fully-wired closed loop (real M1/M2/M3) over seeds x cycles, TWICE --
health-blind (psi-budget effectively off) vs conformal health-constrained -- and
reports empirical coverage of S_k = {x<=spec} & {rho>=rho_min} against the
certified floor 1 - (alpha1+alpha2) - eps.

This is a scaffold: fill the TODOs (your loaded services + the three calibrated
constants), then run on the repo:

    python scripts/run_integrated_coverage.py

CRITICAL: every Monte-Carlo seed gets a FRESH orchestrator (fresh pump
degradation, fresh M1/M2 online state). Reusing one instance carries damage and
adaptation across seeds and invalidates the coverage estimate -- which is why the
factory below reconstructs everything per call rather than closing over a single
pre-built orchestrator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

from ipis.integration.coverage import CoverageConfig, run_coverage, summarize
from ipis.integration.plant import FeatureSynthesizer, FeedSpec, PumpDegradation
from ipis.integration.psi import CoordinateScales, OperatingPoint, PsiConfig
from ipis.integration.wiring import (
    build_integrated_orchestrator,
    econ_params_from_anchor,
)

# ---------------------------------------------------------------------------
# Calibrated constants -- fill these in (sources in the table I gave you).
# ---------------------------------------------------------------------------
L1: float = 0.0  # TODO: from lipschitz.l1_from_regime_data (O2)
L2: float = 0.0  # TODO: from Paper 3's SCC Lipschitz estimate
FEMTO_REF_FLOW: float = 66.5  # TODO: reflux flow R*D at the bearing's characterization condition
DEGRADATION_RATE: float = 1.0e-3  # TODO: base_rate so true RUL maps to plant-realistic hours
SYNTH_GROWTH: Any = None  # TODO: per-feature slope so severity=1 reaches M2's failure-region features

SPEC_XB_C4: float = 0.02
ALPHA1: float = 0.10
ALPHA2: float = 0.10
RHO_MIN_HOURS: float = 200.0  # the pump RUL floor that defines the safety event
BUDGET_EPS: float = 0.05  # ψ-budget for the constrained arm; floor = 1 - (a1+a2) - eps
N_SEEDS: int = 30
N_CYCLES: int = 200

# The M1 calibration anchor (Fortuna regime) in (R, D, alpha, R_min, S) coordinates.
FORTUNA_OP = OperatingPoint(
    R=1.9, D=35.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=FEMTO_REF_FLOW
)


@dataclass
class LoadedServices:
    """Everything the driver needs from your loaders.

    The two *factories* must return a PRISTINE service each call (reload, or
    deep-copy a freshly-loaded instance) so each seed is independent.
    """

    soft_sensor_factory: Callable[[], Any]  # () -> fresh SoftSensorService
    pdm_factory: Callable[[], Any]  # () -> fresh PdMService
    ln_xb_surface: Any  # fitted LnXbSurface (.coef quadratic)
    economics_anchor: Any  # EconomicsAnchor
    gpr_ln_xb: Any  # GP twin: .predict(R, D) -> ln(xB)   (the plant/truth)
    gpr_tray_t: Any  # GP twin: .predict(R, D) -> tray-6 T
    thermo: Any  # PropertyEvaluator: relative_volatility / liquid_viscosity_cp / k_value_hk
    health_model: Any  # M2 HealthIndexModel (.feature_names, .mean)


def load_services() -> LoadedServices:
    """TODO: construct LoadedServices from your repo loaders (1D.2c for M1, the
    M2 PdMArtifact, the M3 fitted surface + economics + GP twin)."""
    raise NotImplementedError("wire your loaders here")


def main() -> None:
    svc = load_services()
    econ = econ_params_from_anchor(svc.economics_anchor)
    psi_cfg = PsiConfig(
        L1=L1,
        L2=L2,
        fortuna_op=FORTUNA_OP,
        femto_ref_reflux_flow=FEMTO_REF_FLOW,
        scales=CoordinateScales(),
    )

    def make_orchestrator(seed: int, cfg: CoverageConfig, *, eps: float):
        # Fresh, independent loop per seed.
        return build_integrated_orchestrator(
            soft_sensor=svc.soft_sensor_factory(),
            pdm=svc.pdm_factory(),
            ln_xb_surface=svc.ln_xb_surface,
            econ=econ,
            xb_truth=lambda R, D, z: math.exp(svc.gpr_ln_xb.predict(R, D)),
            tray_temp=svc.gpr_tray_t.predict,
            properties=svc.thermo,
            degradation=PumpDegradation(
                ref_reflux_flow=FEMTO_REF_FLOW, base_rate=DEGRADATION_RATE
            ),
            feature_synthesizer=FeatureSynthesizer(
                feature_names=svc.health_model.feature_names,
                baseline=svc.health_model.mean,
                growth=SYNTH_GROWTH,
            ),
            psi_cfg=psi_cfg,
            feed=FeedSpec(F=100.0, z_lk=0.35),
            spec_xb_c4=SPEC_XB_C4,
            eps=eps,
        )

    for tag, eps in (("health-blind", 1.0e6), ("health-constrained", BUDGET_EPS)):
        cfg = CoverageConfig(
            spec_xb_c4=SPEC_XB_C4,
            rul_min_hours=RHO_MIN_HOURS,
            alpha1=ALPHA1,
            alpha2=ALPHA2,
            eps=eps,
            n_seeds=N_SEEDS,
            n_cycles=N_CYCLES,
        )
        # e=eps default-arg pins the value per iteration (avoids late-binding).
        result = run_coverage(lambda s, c, e=eps: make_orchestrator(s, c, eps=e), cfg)
        print(f"\n=== {tag} (eps={eps:g}) ===")
        print(summarize(result))


if __name__ == "__main__":
    main()
