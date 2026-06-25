# IPIS — Integrated Process Intelligence System

> A hybrid digital-twin-backed framework integrating soft sensors, predictive maintenance, and real-time optimization for chemical process manufacturing.

[![CI](https://github.com/beebzy-droid/IPIS/actions/workflows/ci.yml/badge.svg)](https://github.com/beebzy-droid/IPIS/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What this is

IPIS is an open-source process intelligence framework that integrates three capability modules into a closed-loop decision system, unified by a fourth integration layer:

1. **Soft Sensor** — real-time prediction of hard-to-measure quality variables
2. **Predictive Maintenance** — anomaly detection and remaining useful life estimation
3. **Real-Time Optimization (RTO)** — constrained setpoint recommendations

All three modules sit on top of a **digital twin layer** (first-principles physics models) that provides baselines, constraints, and surrogate training data.

A fourth layer (**Module 4**) composes the three into a single **closed-loop coverage certificate**: a distribution-free, per-cycle guarantee on the joint safety event that the product stays in specification *and* the equipment survives to its next maintenance window. This is the integration that turns three calibrated components into one certified system.

## Why it exists

Three documented gaps in industrial AI for process manufacturing:

- **Cross-process generalization** — published models don't transfer between plants with different topologies
- **Grade-transition robustness** — models degrade during operating regime shifts
- **Proof-of-concept to production gap** — 87% of industrial AI projects fail at deployment

IPIS addresses all three with one architecture, validated across heterogeneous benchmark datasets.

## Architecture (high level)

```
        DIGITAL TWIN LAYER (DWSIM + GEKKO + CoolProp)
                            │
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
   Soft Sensor    Predictive Maintenance      RTO
   (Module 1)        (Module 2)         (Module 3)
        │                   │                   │
        └───────────────────┴───────────────────┘
                            ↓
                OPERATIONAL STATE BUS
                (MQTT + InfluxDB)
                            ↓
              OPERATOR DASHBOARD + API
              (Streamlit + FastAPI)
```

## Project status

| Module | Status | Notes |
|---|---|---|
| Module 1 — Soft Sensor | ✅ Complete | Paper under review (CACE-D-26-00944) |
| Module 2 — Predictive Maintenance | ✅ Complete | Feature-complete (2A–2D); SCC paper under review (JRESS-D-26-04509) |
| Module 3 — Real-Time Optimization | ✅ Complete | Paper under review (CACE-D-26-01040) |
| Module 4 — Integration (composed certificate) | ✅ Complete | Closed-loop coverage certificate validated on the debutanizer twin; IECR manuscript submission-ready (`paper4/`) |
| Module 5 — Dynamic / horizon realization | ⏳ Next | Dynamic plant + adaptive-conformal horizon guarantee; the bridge to plantwide |

## Publications

Listed by module. Submission directories `paperN/` are numbered by authoring order, which
differs from the module numbering for Modules 2 and 3; the module mapping below is authoritative.

- **Module 1 — Soft Sensor:** *A physics-informed, drift-adaptive soft-sensor framework with
  calibrated uncertainty under delayed labels.* Under review, *Computers & Chemical Engineering*
  (CACE-D-26-00944). Source: `paper/`.
- **Module 2 — Predictive Maintenance (Similarity-Calibrated Conformal):** *Similarity-Calibrated
  Conformal Prediction: a physics-derived, a-priori coverage certificate for prognostics under
  operating-regime transfer.* Under review, *Reliability Engineering & System Safety*
  (JRESS-D-26-04509). Source: `paper3/`.
- **Module 3 — Real-Time Optimization:** *Conditionally calibrated conformal back-offs for chance-constrained real-time optimisation under unmeasured disturbances.* Under
  review, *Computers & Chemical Engineering* (CACE-D-26-01040). Source: `paper2/`.
- **Module 4 — Integration (composed coverage certificate):** *A composed coverage certificate for
  closed-loop process operation: unifying conformal soft sensing, calibrated prognostics, and
  health-constrained real-time optimization.* In preparation (submission-ready), *Industrial &
  Engineering Chemistry Research* (ACS). Source: `paper4/`.

## Project lifecycle and roadmap

**The through-line.** IPIS is building toward a single idea: *certified process intelligence* — a
plant in which every data-driven decision carries a distribution-free safety guarantee. Each module
is not only a method but a capability the field did not previously have, and the modules are designed
to **compose**. Read in sequence they move from trustworthy components, to a certified closed loop,
to a certified plant.

**What each module opens.**

| Module | The contribution | The door it opens |
|---|---|---|
| **M1 — Soft Sensor** | Calibrated uncertainty that survives delayed labels, drift, and regime shift, with a hostile negative control isolating where the performance comes from | Inferential sensing you can *trust in production*, not only on a benchmark |
| **M2 — Predictive Maintenance (SCC)** | An a-priori, physics-derived coverage certificate for remaining-life bounds under operating-regime transfer | Prognostics whose guarantee *holds when the regime changes* |
| **M3 — Real-Time Optimization** | Naming and fixing the conformal selection effect: why marginally valid back-offs over-violate, and how conditional calibration restores safety | Economic optimization that stays *provably safe under uncertainty* |
| **M4 — Integration (composed certificate)** | The first derived, enforceable coverage certificate for the *joint* closed-loop safety event (in-spec product **and** surviving equipment), with the feedback objection resolved by causal timing | Certified closed-loop autonomy: a plant that optimizes itself against a *provable safety floor* |
| **M5 — Dynamic / horizon (next)** | The certificate as a runtime monitor over a real-time horizon, via adaptive conformal inference | Certified autonomy *in real time*, off the quasi-static twin |

**The lifecycle, in phases.**

- **Phase A — the three pillars (DONE).** Calibrated sensing (M1), transferable prognostics (M2),
  safe optimization (M3). Three standalone papers, each a documented gap closed.
- **Phase B — composition (DONE).** The closed-loop coverage certificate that turns the three
  guarantees into one joint guarantee (M4). The headline result of the project so far: on a
  calibrated debutanizer twin, a certified safety floor of 0.75 is met at 0.988 coverage under the
  budget and collapses to 0.000 without it.
- **Phase C — realization (NEXT, Module 5).** Move to a dynamic, physically realistic loop and lift
  the per-cycle certificate to a horizon guarantee. The bridge to plantwide.
- **Phase D — scale (mid-term).** Plantwide / multi-unit operation with one coverage budget allocated
  across units, a certificate for an *integrated plant* rather than a single column. The
  highest-leverage step. In parallel, tighten the composition with a dependence-aware joint-failure
  model.
- **Phase E — generalize, harden, validate (long-term).** New dimensionless groups per unit type
  (turning the universality claim into a theorem); active fault management (the certificate as a
  fault-tolerant-control monitor); and validation on an operating LPG / petrochemical column with
  real DCS data, the credibility capstone.

**The endgame.** A unified theory and an open-source reference implementation of certified process
intelligence for manufacturing: a framework in which soft sensing, prognostics, and optimization are
not three tools bolted together but one system carrying a single, enforceable, distribution-free
safety guarantee from the sensor, to the setpoint, to the plant. The intended capstone is a book that
documents the whole arc as a coherent sub-discipline of process systems engineering, each module a
chapter and a door opened toward autonomous, *certified* manufacturing.

## Quick start

```bash
# Clone
git clone https://github.com/beebzy-droid/IPIS.git
cd IPIS

# Create environment (Python 3.11+)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
pytest tests/unit -v

# Download datasets
python scripts/download_datasets.py --all
```

## Documentation

- [Project structure map](PROJECT_STRUCTURE.md)
- [Continuity / handoff doc](docs/HANDOFF.md)
- [System architecture](docs/architecture/system-overview.md)
- [Architecture Decision Records (ADRs)](docs/architecture/decisions/)
- [Module 1 specification](docs/module1/spec.md) — Soft Sensor
- [Module 2 specification](docs/module2/spec.md) — Predictive Maintenance
- [Module 3 specification](docs/module3/spec.md) — Real-Time Optimization
- [Module 4 theory note](docs/module4/formalization-spike.md) — Composed coverage certificate (integration)

## Tech stack

- **ML:** PyTorch, scikit-learn, XGBoost, River (online learning), MAPIE (conformal)
- **Physics:** DWSIM, CoolProp, GEKKO
- **Infrastructure:** OPC-UA (asyncua), MQTT (Mosquitto), InfluxDB, FastAPI, Streamlit
- **MLOps:** MLflow, Hydra, Docker, GitHub Actions, pytest

## Citation

If you use this work in research, please cite:

```bibtex
@software{busico_ipis_2026,
  author = {Busico, Bien},
  title = {IPIS: Integrated Process Intelligence System},
  year = {2026},
  url = {https://github.com/beebzy-droid/IPIS}
}
```

## License

MIT — see [LICENSE](LICENSE).

## Author

**Bien Busico** — Process Engineer | Chemical Engineering × AI/ML × Industry 4.0
