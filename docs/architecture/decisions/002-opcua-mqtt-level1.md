# ADR 002 — OPC-UA/MQTT Infrastructure at Level 1 Scope

**Status:** Accepted
**Date:** 2026-05-28
**Decision owner:** Bien Busico

## Context

OPC-UA and MQTT are the data transport protocols that connect ML models to real plant systems. The question was at what level of fidelity to implement them in Module 1:

- **Level 1** — Simulated OPC-UA server replays benchmark data; MQTT carries predictions to dashboard. Read-only.
- **Level 2** — Add bidirectional control: model writes setpoints back via OPC-UA write-tags. Requires RTO module.
- **Level 3** — Add edge deployment: inference runs on a Raspberry Pi or edge container subscribing via MQTT.

## Decision

**Implement Level 1 in Module 1. Level 2 in Module 3. Level 3 in integration phase (optional).**

## Rationale

### Why Level 1 is enough for Module 1

- The soft sensor is read-only by nature — it estimates a value, does not act on the plant
- Closed-loop control without an RTO module is meaningless
- Level 1 demonstrates the full OT/IT data flow (PLC → OPC-UA → preprocessing → ML → MQTT → dashboard) without taking on control complexity

### Why this is non-trivial value

- 87% of industrial AI projects fail at deployment. The gap is operational infrastructure, not algorithms.
- Demonstrating OPC-UA + MQTT + InfluxDB + dashboard end-to-end separates this project from "Jupyter notebook with good metrics" projects
- The infrastructure is reused across all four IPIS modules — built once, paid forward

### Why not start higher

- Level 2/3 add scope to a module that's already ambitious (hybrid model + drift + transfer + three datasets)
- Closed-loop control has safety implications even in simulation (RTO recommends a setpoint that violates a constraint that the soft sensor missed) — solve when RTO module exists

## Consequences

### Positive

- Module 1 demonstrates real OT/IT integration, not just ML
- Infrastructure code (OPC-UA server, MQTT broker, InfluxDB) is reusable across Modules 2–3
- Production-readiness narrative becomes credible

### Negative

- No closed-loop demonstration in Module 1 (Module 1 alone is "advisory mode")
- Some OT/IT capabilities (e.g., OPC-UA write-tags, edge deployment) deferred to later modules

### Neutral

- The OPC-UA simulator can be swapped for a real OPC-UA endpoint (real plant data, e.g., Coca-Cola partner data) with configuration changes only, not redesign

## Implementation notes

- OPC-UA server: `asyncua` Python library. Existing examples in the asyncua repo as starting point.
- MQTT broker: Mosquitto in Docker. Configuration in `docker/mosquitto.conf`.
- InfluxDB 2.x in Docker. Bucket name: `process_data`.
- Topic schema:
  - `/ipis/m1/prediction` — soft sensor output
  - `/ipis/m1/confidence` — conformal interval
  - `/ipis/m1/drift` — drift detector status
  - `/ipis/m1/health` — module health (latency, errors)

## Revisit triggers

This decision will be revisited if:

- A real industrial partner provides live OPC-UA data and asks for closed-loop control (Module 3 priority bumped up)
- Performance testing shows MQTT or OPC-UA latency dominates inference time
- Module 3 requires a different communication pattern than expected

## References

- ISA-95 standard for OT/IT integration
- OPC-UA specification (IEC 62541)
- Eclipse Mosquitto MQTT broker
- asyncua Python library
