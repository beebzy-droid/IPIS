# IPIS System Architecture

## Purpose

Define the overall IPIS architecture: layers, modules, data flow, and the contracts between components.

This document is the high-level reference. Module-specific specs (e.g., `docs/module1/spec.md`) detail the internals of each module.

---

## Architecture layers

IPIS is organized into four layers, in dependency order:

### Level 1 — Digital Twin (Physics Foundation)

First-principles process models that provide:

- Baseline predictions for hybrid soft sensors
- Hard constraints for RTO
- Surrogate training data when real data is sparse
- Anomaly references for predictive maintenance

**Tools:** DWSIM (free, transitions to Aspen later), GEKKO (dynamic optimization), CoolProp (thermophysical properties), MATLAB (optional for dynamic models).

### Level 2 — Intelligence (Soft Sensor + PdM)

ML modules that correct and monitor the digital twin layer.

- **Module 1 (Soft Sensor):** real-time quality estimation via hybrid residual learning
- **Module 2 (PdM):** equipment health monitoring as deviation from DT-predicted behavior

**Tools:** PyTorch, scikit-learn, XGBoost, River.

### Level 3 — Decision (RTO)

Constrained optimization using DT physics + ML state estimates.

- **Module 3 (RTO):** maximizes economic objective subject to mass/energy balance, quality, and equipment health constraints

**Tools:** Pyomo, GEKKO, scipy.optimize.

### Level 4 — Interface (Operator Dashboard + API)

Makes the system usable.

**Tools:** Streamlit (dashboard), FastAPI (REST API), MQTT (real-time messaging).

---

## Data flow

```
┌───────────────────────────────────────────────────────────────┐
│  DIGITAL TWIN LAYER                                           │
│  First-Principles Model (DWSIM, GEKKO, CoolProp)              │
│  Outputs: physics baseline, hard constraints, surrogate data  │
└────────────────────┬──────────────────────────────┬───────────┘
                     ↓                              ↓
            Physics baseline               Hard constraints
                     ↓                              ↓
┌────────────────────┐  ┌────────────────┐  ┌─────────────────┐
│   SOFT SENSOR      │  │      PdM       │  │      RTO        │
│   Module 1         │  │   Module 2     │  │   Module 3      │
│   ML residual      │  │   Deviation    │  │   DT-trained    │
│   correction       │  │   from DT      │  │   surrogate     │
└─────────┬──────────┘  └───────┬────────┘  └────────┬────────┘
          │                     │                    │
          └─────────────────────┴────────────────────┘
                                ↓
                   OPERATIONAL STATE BUS
                   S(t) = {ŷ_quality, H_equipment,
                           process_conditions, confidence}
                                ↓
                   OPERATOR INTERFACE / API
                   Streamlit dashboard + FastAPI
                   Setpoint recommendations + health flags
```

---

## The operational state bus

The state bus is the single contract that all modules read from and write to.

### State schema

```python
from pydantic import BaseModel
from datetime import datetime

class OperationalState(BaseModel):
    timestamp: datetime
    process_conditions: dict[str, float]       # raw measurements
    quality_estimate: dict[str, float]         # soft sensor output
    quality_confidence: dict[str, float]       # 95% PI half-widths
    equipment_health: dict[str, float]         # 0..1 health scores
    health_flags: dict[str, str]               # "ok" | "warn" | "alarm"
    drift_status: dict[str, bool]              # per-module drift flag
    active_constraints: list[str]              # which constraints are binding
```

### Why this design

A shared state schema means modules can be developed independently as long as they read and write to the contract. This is critical for the build sequence:

- Module 1 produces `quality_estimate`, `quality_confidence`, `drift_status["m1"]`
- Module 2 produces `equipment_health`, `health_flags`, `drift_status["m2"]`
- Module 3 consumes all of the above, produces `active_constraints` and setpoint recommendations

---

## Transport protocols

- **OPC-UA** — primary protocol for reading from PLCs/DCS and writing setpoints. In Module 1 we use a simulated OPC-UA server (asyncua) that replays benchmark data.
- **MQTT** — message bus between modules. Topics namespaced as `/ipis/{module}/{signal}`.
- **InfluxDB** — historian layer. Subscribes to MQTT and stores all signals as time series.

---

## Module dependency graph

```
            ┌──────────────┐
            │  Digital     │
            │  Twin Layer  │
            └──────┬───────┘
                   │
        ┌──────────┴──────────┐
        ↓                     ↓
   ┌─────────┐          ┌─────────┐
   │ Mod 1   │          │ Mod 2   │
   │ Soft    │          │ PdM     │
   │ Sensor  │          │         │
   └────┬────┘          └────┬────┘
        │                    │
        └────────┬───────────┘
                 ↓
            ┌─────────┐
            │ Mod 3   │
            │ RTO     │
            └─────────┘
```

Module 3 depends on Modules 1 and 2 via the state bus, but Modules 1 and 2 are independent of each other.

---

## Build order (locked)

1. **Shared infrastructure first** — state bus, OPC-UA/MQTT skeleton, data router
2. **Module 1 — Soft Sensor** (Phase 1A–1F, 16–20 weeks)
3. **Module 2 — Predictive Maintenance**
4. **Module 3 — RTO**
5. **Integration** — closed-loop full IPIS demonstration

See ADRs in `docs/architecture/decisions/` for the reasoning behind each major decision.
