# Module 1 — Soft Sensor

This directory holds Module 1 documentation.

## Files

- **spec.md** — Technical specification (see Word document in project archive: `IPIS_Module1_Technical_Specification.docx`)
- **results.md** — Populated after each phase completes with metrics, plots, and observations
- **lessons-learned.md** — Honest postmortem per phase: what worked, what didn't, what would be done differently

## Status

| Phase | Status | Completion target |
|---|---|---|
| 1A — Hybrid model on Debutanizer | **Complete** (ADR-007) | Weeks 1–4 |
| 1B — Drift detection | **Complete** (ADR-008) | Weeks 5–7 |
| 1C — Cross-process transfer | Not started | Weeks 8–12 |
| 1D — Production-ready deployment stack | Not started | Weeks 13–16 |
| 1E — SECOM stress test | Not started | Weeks 17–18 |
| 1F — Writing & submission | Not started | Weeks 19–20 |

## Architecture summary (as-built; supersedes the original locked plan where noted)

- **Model:** Dynamic, physics-*anchored* linear model evaluated under blocked CV (**ADR-007**). Pivoted from the original ADR-001 Path-B PINN/residual-hybrid plan after Phase 1A findings (static physics R²=0.018; covariate shift; cross-regime calibration drift). PINN (Path A) retained as private future work, not externally promised.
- **Datasets:** Debutanizer (primary), Tennessee Eastman (transfer), SECOM (stress test)
- **Infrastructure:** Simulated OPC-UA server (asyncua), MQTT broker (Mosquitto), InfluxDB historian
- **Serving:** FastAPI inference endpoint, Streamlit dashboard, MLflow versioning
- **Drift handling:** ADWIN (primary) / Page-Hinkley / CUSUM residual detection + **Shardt open-loop bias-update** (**ADR-008**). The bias-update supersedes the originally-planned JITL retraining for this calibration-drift failure mode.
- **Uncertainty:** Conformal prediction (MAPIE) — *planned; not yet implemented as of 1B. Owed before 1F (candidate: 1D or a 1A/1B addendum).*

See `docs/architecture/decisions/` for the reasoning behind each decision.
