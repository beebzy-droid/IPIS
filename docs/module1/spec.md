# Module 1 — Soft Sensor

This directory holds Module 1 documentation. **Status: complete; paper under review
(CACE-D-26-00944).**

## Files

- **spec.md** — This technical specification (as-built).
- **results.md** — Per-phase metrics, plots, and observations (1A–1F).
- **lessons-learned.md** — Honest postmortem per phase: what worked, what didn't, what would be done differently.

## Status

| Phase | Status | Completion target |
|---|---|---|
| 1A — Hybrid model on Debutanizer | **✅ Complete** (ADR-007) | Weeks 1–4 |
| 1B — Drift detection + bias-update | **✅ Complete** (ADR-008) | Weeks 5–7 |
| 1C — Cross-process transfer (→ TEP) | **✅ Complete** (ADR-009) | Weeks 8–12 |
| 1D — Production-ready deployment stack | **✅ Complete** (ADR-010 conformal, ADR-011 serving) | Weeks 13–16 |
| 1E — SECOM stress test | **✅ Complete** (ADR-012) | Weeks 17–18 |
| 1F — Writing & submission | **✅ Complete** — submitted to *Computers & Chemical Engineering*, CACE-D-26-00944 | Weeks 19–20 |

## Architecture summary (as-built; supersedes the original locked plan where noted)

- **Model:** Dynamic, physics-*anchored* linear model evaluated under blocked CV (**ADR-007**). Pivoted from the original ADR-001 Path-B PINN/residual-hybrid plan after Phase 1A findings (static physics R²=0.018; covariate shift; cross-regime calibration drift). PINN (Path A) retained as private future work, not externally promised.
- **Datasets:** Debutanizer (primary), Tennessee Eastman (transfer), SECOM (stress test).
- **Drift handling:** ADWIN (primary) / Page-Hinkley / CUSUM residual detection + **Shardt open-loop bias-update** (**ADR-008**), benchmarked head-to-head against JITL and dominating on this calibration-drift problem (CV +0.648±0.046 vs JITL +0.405±0.215; held-out test 0.857 vs static 0.476; zero local fits vs 1,620). JITL retained as the reported baseline.
- **Cross-process transfer (1C, ADR-009):** methodology transfer + within-TEP regime migration via scale-and-bias correction. **Yan functional migration ~10× data efficiency** (reaches 90% of the from-scratch ceiling at ~5% target data) with calibrated 95% GP intervals; OSBC ~3.3×; Luo ≡ from-scratch for a linear source (verified analytically). Literal Debutanizer→TEP parameter migration is mathematically inapplicable (disjoint input spaces) — framed honestly as methodology + within-process migration.
- **Uncertainty:** Distribution-free conformal prediction, implemented **from-primary** (**ADR-010**): **ACI** (Gibbs & Candès 2021) as the online primary, **EnbPI** (Xu & Xie 2021) comparator, split conformal as the deliberately-weak exchangeability baseline. Validated on the real TEP regimes: corrected+ACI **0.90 ± 0.003** across modes and label delays (regime-uniform), where raw static split swings 0.847–0.957. MAPIE retained as an optional cross-check, not a runtime dependency.
- **Serving (1D, ADR-011):** `SoftSensorService` (delayed-label / stored-interval invariant) + FastAPI (`/predict`, `/label`, `/health`, `/metrics`, `/state`) + `ModelBundle` loader (joblib, MLflow optional) + Streamlit monitoring dashboard + lean Dockerfile + GitHub Actions CI. p50 latency ~1.2 ms.
- **Stress test (1E, ADR-012):** SECOM (semiconductor, 590 features) as a hostile negative control — validity-without-accuracy: ACI holds ~0.91 coverage on a failed point model at 37% narrower intervals than static split; one-SE selection beats the p≈n lottery.

## Publication

Module 1 is reported in **Paper 1**: "A physics-informed, drift-adaptive soft-sensor framework
with calibrated uncertainty under delayed labels: from benchmark validation to a negative
control and real-time implementation," under review at *Computers & Chemical Engineering*
(**CACE-D-26-00944**). LaTeX source in `paper/`; markdown working copy, figures, and frozen
evidence in `docs/paper/`.

See `docs/architecture/decisions/` for the reasoning behind each decision, and `docs/HANDOFF.md`
for the full build history.
