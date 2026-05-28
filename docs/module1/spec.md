# Module 1 — Soft Sensor

This directory holds Module 1 documentation.

## Files

- **spec.md** — Technical specification (see Word document in project archive: `IPIS_Module1_Technical_Specification.docx`)
- **results.md** — Populated after each phase completes with metrics, plots, and observations
- **lessons-learned.md** — Honest postmortem per phase: what worked, what didn't, what would be done differently

## Status

| Phase | Status | Completion target |
|---|---|---|
| 1A — Hybrid model on Debutanizer | Not started | Weeks 1–4 |
| 1B — Drift detection | Not started | Weeks 5–7 |
| 1C — Cross-process transfer | Not started | Weeks 8–12 |
| 1D — Production-ready deployment stack | Not started | Weeks 13–16 |
| 1E — SECOM stress test | Not started | Weeks 17–18 |
| 1F — Writing & submission | Not started | Weeks 19–20 |

## Architecture summary (locked)

- **Model:** Path B residual hybrid (first-principles baseline + PINN-regularized residual ML), with standard ML residual learner as documented fallback
- **Datasets:** Debutanizer (primary), Tennessee Eastman (transfer), SECOM (stress test)
- **Infrastructure:** Simulated OPC-UA server (asyncua), MQTT broker (Mosquitto), InfluxDB historian
- **Serving:** FastAPI inference endpoint, Streamlit dashboard, MLflow versioning
- **Drift handling:** ADWIN/Page-Hinkley + JITL retraining
- **Uncertainty:** Conformal prediction (MAPIE)

See `docs/architecture/decisions/` for the reasoning behind each decision.
