# IPIS — Integrated Process Intelligence System

> A hybrid digital-twin-backed framework integrating soft sensors, predictive maintenance, and real-time optimization for chemical process manufacturing.

[![CI](https://github.com/beebzy-droid/IPIS/actions/workflows/ci.yml/badge.svg)](https://github.com/beebzy-droid/IPIS/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What this is

IPIS is an open-source process intelligence framework that integrates three modules into a closed-loop decision system:

1. **Soft Sensor** — real-time prediction of hard-to-measure quality variables
2. **Predictive Maintenance** — anomaly detection and remaining useful life estimation
3. **Real-Time Optimization (RTO)** — constrained setpoint recommendations

All three modules sit on top of a **digital twin layer** (first-principles physics models) that provides baselines, constraints, and surrogate training data.

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

| Module | Status | Target |
|---|---|---|
| Module 1 — Soft Sensor | ✅ Complete; paper under review (CACE-D-26-00944) |
| Module 2 — Predictive Maintenance | ⏳ Planned | After Module 3 |
| Module 3 — RTO | ✅ Complete; paper under review (JPROCONT-D-26-00565) |
| Integration (full IPIS) | ⏳ Planned | After Module 2 |

## Publications

- **Paper 1 (soft sensor):** under review, *Computers & Chemical Engineering* (CACE-D-26-00944). Source in `paper/`.
- **Paper 2 (RTO):** "The conformal selection effect in real-time optimisation…" — under review, *Journal of Process Control* (JPROCONT-D-26-00565). Source in `paper2/`

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
- [Module 3 specification](docs/module3/spec.md) — Real-Time Optimization

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
