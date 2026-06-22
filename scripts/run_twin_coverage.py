"""Module 4 -- composed coverage certificate, closed-loop demonstration on the twin.

Demonstrates the Paper-4 thesis end to end: the per-cycle *composed* coverage
certificate

    P(S_k | dpsi) >= 1 - (alpha1 + alpha2) - 2(L1||dpsi1|| + L2||dpsi2||) - Delta_sel,k

with S_k = {x_k <= x_spec} AND {rho_k >= rho_min}, holds empirically when the
RTO honours the psi-budget constraint and fails when it does not. Causal
discrete-cycle timing makes Delta_sel = 0, so the operative floor is

    certified_floor = 1 - (alpha1 + alpha2) - eps.

REAL component code, demonstration-grade data (no proprietary CSVs):
  * M1 -- the real physics-anchored soft sensor (add_physics_features + ACI,
    SoftSensorService) trained on twin-generated samples. Empirical conformal
    coverage ~0.90 on held-out twin data; its half-width drives the RTO backoff.
  * M2 -- the real predictive-maintenance stack (Hotelling T^2 HealthIndexModel +
    trajectory-similarity RUL), built from the canonical test recipe.
  * M3 -- the real FUG ShortcutColumnModel surface (fit_ln_xb_surface) and the
    Module-4 health-constrained economic NLP (psi-budget) over it.

The plant is a calibrated FUG twin: x_bottoms from ShortcutColumnModel is the
truth; tray-6 temperature is a physically-motivated inferential measurement the
soft sensor refines; a stateful affinity-law PumpDegradation drives a Module-2
feature synthesiser. Component *accuracy* is validated on operational data in the
Module-1/2 papers; this script demonstrates how the three coverage *guarantees
compose* -- which is what the certificate is about -- and is fully reproducible
from the repo. Physical deployment (DWSIM dynamic / DCS) is Module-5 future work.

Two arms, identical everything except the psi-budget:
  health-blind        eps -> inf   psi-budget inactive; RTO optimises economics
                                    freely, over-refluxes for the tight spec,
                                    accumulates pump damage -> RUL floor fails.
  health-constrained  eps = 0.05   psi-budget binds; RTO held on the certified
                                    reference -> quality AND RUL preserved.

Degradation calibration: damage accrues as base_rate * pump_load^load_exponent,
pump_load being the affinity BHP ratio (Q/Qref)^3. load_exponent = 2 follows from
rolling-element bearing fatigue (L10 ~ load^-3) with hydraulic radial load ~ Q^2
(affinity head), i.e. damage ~ Q^6; base_rate is set to a ~1000 h fresh-nominal
RUL. These coefficients are calibrated to the bearing-degradation timescale, per
the PumpDegradation contract.

Run (cmd, env ipis, from repo root):
    python scripts\\run_twin_coverage.py
    python scripts\\run_twin_coverage.py --fig docs\\module4\\twin_coverage.png
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ipis.integration.calibrate import degradation_rate_for_rul, synth_growth
from ipis.integration.coverage import CoverageConfig, CoverageResult, run_coverage, summarize
from ipis.integration.plant import (
    DebutanizerPlant,
    FeatureSynthesizer,
    FeedSpec,
    PumpDegradation,
)
from ipis.integration.psi import CoordinateScales, OperatingPoint, PsiConfig
from ipis.integration.wiring import build_integrated_orchestrator, econ_params_from_anchor
from ipis.module1_soft_sensor.features.physics_features import (
    PHYSICS_FEATURE_COLS,
    _psat_vec,
    add_physics_features,
)
from ipis.module1_soft_sensor.serving.service import SoftSensorService
from ipis.module2_pdm.health.health_index import HealthIndexModel
from ipis.module2_pdm.rul.similarity import SimilarityRUL
from ipis.module2_pdm.serving.loader import PdMArtifact
from ipis.module2_pdm.serving.service import PdMService
from ipis.module3_rto.column_model import ShortcutColumnModel
from ipis.module3_rto.economics import EconomicsAnchor
from ipis.module3_rto.rto_nlp import fit_ln_xb_surface
from ipis.physics.dippr101 import N_BUTANE, N_HEXANE

# --------------------------------------------------------------------------- #
# Twin geometry and the M1 feature-normalisation contract (must match the      #
# in-loop M1FeatureTransform: BridgeConfig T in [100,112] C, P in [4.5,5.5]    #
# bar, reflux-flow R*D in [26,111], column pressure 5.0 bar).                   #
# --------------------------------------------------------------------------- #
COL = ShortcutColumnModel()
P_NOM_BAR = 5.0
T_MIN_C, T_MAX_C = 100.0, 112.0
P_MIN_BAR, P_MAX_BAR = 4.5, 5.5
RF_MIN, RF_MAX = 26.0, 111.0
R_NOM, D_NOM = 2.037, 33.49  # validated RTO optimum (spec 0.02 anchor)
SIG_T, SIG_XB = 0.25, 0.0010  # tray-6 sensor noise (C); bottoms process noise


def xb_truth(reflux_ratio: float, distillate: float, z: float | None = None) -> float:
    """Plant truth: bottoms light-key (C4) fraction from the FUG column."""
    return COL.evaluate(reflux_ratio, distillate).x_bottoms_lk


def tray6_temp(reflux_ratio: float, distillate: float) -> float:
    """Inferential tray-6 temperature [C]: cooler as reflux sharpens the split."""
    t = 106.0 - 3.4 * (reflux_ratio - R_NOM) + 0.9 * (distillate - D_NOM)
    return float(np.clip(t, 100.5, 111.5))


class TwinProperties:
    """DIPPR-101 relative volatility / HK K-value; representative liquid viscosity."""

    def relative_volatility(self, temp_c: float) -> float:
        tk = np.array([temp_c + 273.15])
        return float(_psat_vec(tk, N_BUTANE)[0] / _psat_vec(tk, N_HEXANE)[0])

    def liquid_viscosity_cp(self, temp_c: float) -> float:
        return float(0.15 * np.exp(-0.004 * (temp_c - 100.0)))

    def k_value_hk(self, temp_c: float) -> float:
        tk = np.array([temp_c + 273.15])
        return float(_psat_vec(tk, N_HEXANE)[0] / (P_NOM_BAR * 1.0e5))


PROPS = TwinProperties()
FEED = FeedSpec(F=100.0, z_lk=0.35, q=1.0)
REF_FLOW = R_NOM * D_NOM  # reference reflux flow for psi-budget and pump load


# --------------------------------------------------------------------------- #
# Module 1: real physics-anchored soft sensor trained on the twin.             #
# Feature order matches M1FeatureTransform(include_raw_u5=True):               #
# [bubble_point_c4, rel_volatility, stripping_factor, u5].                      #
# --------------------------------------------------------------------------- #
def _features(reflux_ratio: float, distillate: float, temp_c: float) -> np.ndarray:
    u5 = (temp_c - T_MIN_C) / (T_MAX_C - T_MIN_C)
    u2 = (P_NOM_BAR - P_MIN_BAR) / (P_MAX_BAR - P_MIN_BAR)
    u3 = (reflux_ratio * distillate - RF_MIN) / (RF_MAX - RF_MIN)
    feat = add_physics_features(pd.DataFrame({"u5": [u5], "u2": [u2], "u3": [u3]}))
    cols = list(PHYSICS_FEATURE_COLS) + ["u5"]
    return feat[cols].to_numpy(float)[0]


def _sample_box(n: int, rng: np.random.Generator) -> list[tuple[float, float, float, float]]:
    out: list[tuple[float, float, float, float]] = []
    while len(out) < n:
        r, d = rng.uniform(1.0, 3.0), rng.uniform(33.0, 37.0)
        try:
            xb = xb_truth(r, d)
        except ValueError:
            continue
        out.append((r, d, xb, tray6_temp(r, d)))
    return out


def train_soft_sensor(seed: int = 7) -> tuple[object, np.ndarray]:
    """Fit the point model on twin samples; return (model, calibration residuals)."""
    rng = np.random.default_rng(seed)
    samp = _sample_box(700, rng)
    feats, ys = [], []
    for r, d, xb, t in samp:
        feats.append(_features(r, d, t + rng.normal(0, SIG_T)))
        ys.append(xb + rng.normal(0, SIG_XB))
    feats_arr, ys_arr = np.asarray(feats), np.asarray(ys)
    n_fit = 450
    model = make_pipeline(StandardScaler(), Ridge(alpha=1e-3))
    model.fit(feats_arr[:n_fit], ys_arr[:n_fit])
    resid = ys_arr[n_fit:] - model.predict(feats_arr[n_fit:])
    return model, resid


# --------------------------------------------------------------------------- #
# Module 2: real PdM stack from the canonical test recipe.                      #
# --------------------------------------------------------------------------- #
INTERVAL, N_FEAT = 10.0, 5


def build_pdm_artifact(seed: int = 0) -> PdMArtifact:
    rng = np.random.default_rng(seed)
    healthy = rng.standard_normal((200, N_FEAT))
    hm = HealthIndexModel.fit(
        healthy, tuple(f"v{i}" for i in range(N_FEAT)), warn_q=0.95, alarm_q=0.99
    )
    library = []
    for k in range(3):
        n = 180 + 20 * k
        di = np.exp(np.linspace(np.log(5.0), np.log(500.0 + 100.0 * k), n))
        hi = np.log1p(np.maximum.accumulate(di))
        library.append((hi, np.linspace(n * INTERVAL, 0.0, n)))
    sim = SimilarityRUL(library=library, interval=INTERVAL, mode="phase")
    return PdMArtifact(health_model=hm, similarity=sim, conformal_delta_hours=0.2, ema_alpha=0.3)


_ART = build_pdm_artifact(0)
_HM = _ART.health_model
_GROWTH = synth_growth(_HM, np.asarray(_HM.mean, float) + np.ones(N_FEAT), target_t2_mult=2.0)


def make_synth() -> FeatureSynthesizer:
    return FeatureSynthesizer(
        feature_names=tuple(_HM.feature_names),
        baseline=np.asarray(_HM.mean, float),
        growth=_GROWTH,
        noise_sd=0.0,
    )


# affinity BHP x bearing fatigue -> damage ~ Q^6 (load_exponent = 2); ~1000 h fresh RUL
BASE_RATE = degradation_rate_for_rul(fresh_nominal_rul_hours=1000.0)
LOAD_EXPONENT = 2.0


def make_degradation() -> PumpDegradation:
    return PumpDegradation(
        ref_reflux_flow=REF_FLOW,
        base_rate=BASE_RATE,
        load_exponent=LOAD_EXPONENT,
        damage_at_failure=1.0,
        dt=1.0,
    )


# --------------------------------------------------------------------------- #
# Module 3 surface + economics + psi-config (reference u* from a nominal step). #
# --------------------------------------------------------------------------- #
SURFACE = fit_ln_xb_surface(COL)
ECON = econ_params_from_anchor(EconomicsAnchor())
L1, L2 = 0.15, 0.15
SCALES = CoordinateScales(
    alpha_scale=1.0, gilliland_scale=1.0, strip_scale=1.0, pump_load_scale=1.0
)


def _fortuna_op() -> OperatingPoint:
    plant = DebutanizerPlant(
        xb_truth=xb_truth,
        tray_temp=tray6_temp,
        properties=PROPS,
        feed=FEED,
        degradation=make_degradation(),
        synthesizer=make_synth(),
        feed_z=FEED.z_lk,
    )
    return plant.step(R_NOM, D_NOM, rng=np.random.default_rng(0)).operating_point


FORTUNA = _fortuna_op()


def psi_cfg() -> PsiConfig:
    return PsiConfig(
        L1=L1, L2=L2, fortuna_op=FORTUNA, femto_ref_reflux_flow=REF_FLOW, scales=SCALES
    )


# --------------------------------------------------------------------------- #
# Factory (fresh per-seed state) + two-arm sweep.                              #
# --------------------------------------------------------------------------- #
def make_factory(model: object, resid: np.ndarray, eps: float):
    def factory(seed: int, cfg: CoverageConfig):
        svc = SoftSensorService(
            point_predict=lambda x: model.predict(x),
            init_residuals=resid,
            lam=0.3,
            delay=0,
            alpha=cfg.alpha1,
            gamma=0.05,
            window=200,
            drift_on="corrected",
        )
        pdm = PdMService(build_pdm_artifact(0))
        return build_integrated_orchestrator(
            soft_sensor=svc,
            pdm=pdm,
            ln_xb_surface=SURFACE,
            econ=ECON,
            xb_truth=xb_truth,
            tray_temp=tray6_temp,
            properties=PROPS,
            degradation=make_degradation(),
            feature_synthesizer=make_synth(),
            psi_cfg=psi_cfg(),
            feed=FEED,
            spec_xb_c4=cfg.spec_xb_c4,
            eps=eps,
            seed_setpoints=(R_NOM, D_NOM),
            col_pressure_bar=P_NOM_BAR,
            transport_lag=1,
            include_raw_u5=True,
            alpha1=cfg.alpha1,
            alpha2=cfg.alpha2,
        )

    return factory


def make_figure(
    model: object,
    resid: np.ndarray,
    cfg: CoverageConfig,
    blind: CoverageResult,
    constr: CoverageResult,
    path: str,
) -> None:
    """Headline figure: coverage bars + per-cycle RUL and severity trajectories."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # one representative seed for the trajectories
    def trajectory(eps: float) -> tuple[np.ndarray, np.ndarray]:
        orch = make_factory(model, resid, eps)(0, cfg)
        recs = orch.run(cfg.n_cycles, rng=np.random.default_rng(0))
        rul = np.array([r.true_rul_hours for r in recs])
        sev = np.array([r.severity for r in recs])
        return rul, sev

    rul_b, sev_b = trajectory(1e6)
    rul_c, sev_c = trajectory(cfg.eps)
    cyc = np.arange(cfg.n_cycles)
    blue, red = "#1f77b4", "#d62728"

    fig, ax = plt.subplots(1, 3, figsize=(15.0, 4.4))

    # (a) coverage decomposition + certified floor
    groups = ["S_k\n(joint)", "Quality\nx<=spec", "RUL\nrho>=rho_min"]
    bvals = [blind.s_coverage, blind.quality_coverage, blind.rul_coverage]
    cvals = [constr.s_coverage, constr.quality_coverage, constr.rul_coverage]
    x = np.arange(len(groups))
    ax[0].bar(x - 0.19, bvals, 0.36, label="health-blind", color=red, alpha=0.85)
    ax[0].bar(x + 0.19, cvals, 0.36, label="health-constrained", color=blue, alpha=0.85)
    ax[0].axhline(
        constr.certified_floor,
        ls="--",
        color="black",
        lw=1.3,
        label=f"certified floor {constr.certified_floor:.2f}",
    )
    for xi, (bv, cv) in enumerate(zip(bvals, cvals)):
        ax[0].text(xi - 0.19, bv + 0.02, f"{bv:.2f}", ha="center", fontsize=8)
        ax[0].text(xi + 0.19, cv + 0.02, f"{cv:.2f}", ha="center", fontsize=8)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(groups)
    ax[0].set_ylim(0, 1.08)
    ax[0].set_ylabel("empirical coverage")
    ax[0].set_title("(a) Composed coverage vs certified floor")
    ax[0].legend(loc="center left", fontsize=8)

    # (b) true RUL trajectory + rho_min
    ax[1].plot(cyc, rul_b, color=red, lw=1.8, label="health-blind")
    ax[1].plot(cyc, rul_c, color=blue, lw=1.8, label="health-constrained")
    ax[1].axhline(
        cfg.rul_min_hours,
        ls="--",
        color="black",
        lw=1.3,
        label=f"rho_min = {cfg.rul_min_hours:.0f} h",
    )
    ax[1].set_xlabel("control cycle k")
    ax[1].set_ylabel("true RUL [h]")
    ax[1].set_title("(b) Pump RUL trajectory")
    ax[1].legend(loc="upper right", fontsize=8)

    # (c) severity trajectory
    ax[2].plot(cyc, sev_b, color=red, lw=1.8, label="health-blind")
    ax[2].plot(cyc, sev_c, color=blue, lw=1.8, label="health-constrained")
    ax[2].set_xlabel("control cycle k")
    ax[2].set_ylabel("degradation severity")
    ax[2].set_ylim(0, 1.02)
    ax[2].set_title("(c) Pump degradation severity")
    ax[2].legend(loc="upper left", fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(f"[figure] wrote {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=float, default=0.008, help="bottoms C4 spec x_spec")
    ap.add_argument("--rho-min", type=float, default=200.0, help="RUL floor [h]")
    ap.add_argument("--eps", type=float, default=0.05, help="psi-budget for constrained arm")
    ap.add_argument("--alpha1", type=float, default=0.10, help="M1 conformal miscoverage")
    ap.add_argument("--alpha2", type=float, default=0.10, help="M2/M3 health miscoverage")
    ap.add_argument("--seeds", type=int, default=8, help="Monte-Carlo seeds")
    ap.add_argument("--cycles", type=int, default=80, help="cycles per seed")
    ap.add_argument("--fig", type=str, default="twin_coverage.png", help="figure output path")
    args = ap.parse_args()

    model, resid = train_soft_sensor()
    rmse = float(np.sqrt(np.mean(resid**2)))
    print(f"[M1] physics-anchored soft sensor trained on twin -- calib RMSE={rmse:.6f}")
    print(f"[M2] alarm_t2={_HM.alarm_t2:.2f}  ref_flow={REF_FLOW:.2f}  base_rate={BASE_RATE:.5f}")
    print(f"[M3] ln-xb surface r2={SURFACE.r_squared:.4f}")
    print(
        f"[psi] u* alpha={FORTUNA.alpha:.3f} R_min={FORTUNA.R_min:.3f} "
        f"strip={FORTUNA.strip_factor:.3f} reflux_flow={FORTUNA.reflux_flow:.2f}"
    )

    cfg = CoverageConfig(
        spec_xb_c4=args.spec,
        rul_min_hours=args.rho_min,
        alpha1=args.alpha1,
        alpha2=args.alpha2,
        eps=args.eps,
        n_seeds=args.seeds,
        n_cycles=args.cycles,
    )

    print("\n=== HEALTH-BLIND (psi-budget inactive, eps -> inf) ===")
    blind = run_coverage(make_factory(model, resid, 1e6), cfg)
    print(summarize(blind))

    print("\n=== HEALTH-CONSTRAINED (psi-budget eps={:.3g}) ===".format(args.eps))
    constr = run_coverage(make_factory(model, resid, args.eps), cfg)
    print(summarize(constr))

    verdict = "VALIDATES" if constr.meets_floor and not blind.meets_floor else "INCONCLUSIVE"
    print(
        f"\n[certificate] constrained S={constr.s_coverage:.3f} "
        f"(floor {constr.certified_floor:.3f}) vs blind S={blind.s_coverage:.3f} -> {verdict}"
    )

    make_figure(model, resid, cfg, blind, constr, args.fig)


if __name__ == "__main__":
    main()
