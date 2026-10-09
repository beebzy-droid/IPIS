# ADR-011 — Phase 1D.2: production serving architecture

**Status:** Accepted
**Date:** 2026-06-05
**Decision owner:** Bien Busico
**Module:** 1 (soft sensor) — production serving stack
**Extends:** ADR-007 (physics-anchored model), ADR-008 (drift + bias-update),
ADR-010 (conformal uncertainty)

## Context

The soft sensor must be *served*, not just benchmarked. The defining constraint is that
its labels are **delayed and infrequent**: predictions are produced every sample, but the
ground-truth assay arrives later and sparsely. Both the bias-update (ADR-008) and ACI
(ADR-010) are *stateful online updaters* that consume those delayed labels. So the server
is not the usual stateless request→response model host — it is **two asynchronous flows
over mutable state**:

- `predict` (high-frequency, reads state): features → raw → corrected = raw + b_t →
  ACI interval. Microsecond compute (linear + EWMA + quantile lookup).
- `label` (low-frequency, mutates state): a delayed assay updates b_t, α_t, and the
  drift detector.

That statefulness — not raw throughput — is the engineering problem, and it drives every
decision below.

## Decision

A framework-agnostic stateful core wrapped by a thin async HTTP layer, fed by a frozen
model bundle, shipped in a lean container with CI.

- **Core — `serving/service.py::SoftSensorService`.** Sync, no web/async/MLflow
  coupling. Composes the linear model + ADR-008 bias-update + ADR-010 ACI + an injected
  drift detector + a `sample_id`→prediction ring buffer + a pickle snapshot.
- **State (D1): in-process + periodic disk snapshot, single-instance; Redis deferred.**
  State is tiny (b_t, α_t, a bounded score window, a bounded prediction buffer). The
  snapshot pickles only **mutable** state (b_t, the ACI object, the river detector, the
  buffer, counters); the **immutable** model reloads from the registry and is never
  pickled into the snapshot.
- **API (D2): async FastAPI** — `POST /predict` (batch-first), `POST /label`,
  `GET /health` (lock-free liveness), `GET /metrics`, `GET /state`. An `asyncio.Lock`
  guards mutations.
- **Delayed-label pairing (D3): server-side `sample_id`→prediction ring buffer.** The
  client posts `{sample_id, y_true}`; the server pairs it with the stored prediction.
- **MLflow (D4): registry + tracking only; joblib fallback.** A joblib `ModelBundle`
  (frozen sklearn pipeline + calibration residuals + params) is the interchange format.
  MLflow logs params/metrics/the registered model/the bundle artifact; serving loads the
  bundle from MLflow **or** a local file, defaulting to a committed synthetic fixture so
  it runs offline / in CI. MLflow does **not** serve the model; it is an optional import.
- **Container/CI (D5): lean image + GitHub Actions.** The image installs only
  `requirements-serving.txt` (the empirically-confirmed serving import set — no
  torch/mlflow/streamlit) and regenerates the fixture in-image. CI = unit tests
  (`PYTHONPATH=src`, pinned black/ruff on `src tests`) + container smoke (`/health`,
  `/predict`). Real-data coverage stays the local `conformal_eval.py` (gitignored data is
  not in CI).

### Key correctness invariant (delayed labels)
The ACI coverage indicator for a label is computed against the interval **stored when
that sample was predicted**, not the service's current interval — by the time a delayed
assay arrives, α_t and the score window have advanced. `ACIConformal.update` assumes
immediate feedback and is therefore *not* used; the service drives `aci_step` + the score
window directly, against the stored `(raw, corrected, lower, upper)`. The bias recursion
is bit-faithful to `apply_bias_update` (ADR-008) when labels arrive in order, `delay`
samples late — so the 1D.1b coverage result transfers to the live path.

## Rationale

- **Single-instance + snapshot, not Redis.** State is ~kilobytes; a restart-safe pickle
  snapshot is sufficient and honest for a portfolio deployment. Redis is the documented
  horizontal-scale answer, not a present need — building it now would be over-engineering.
- **MLflow as registry, FastAPI owns state.** MLflow cannot host a stateful online
  updater; forcing the model through MLflow serving would not solve the actual problem.
  The joblib bundle keeps serving and CI dependency-light and offline-capable.
- **Lean container.** The full project dependency set (torch, xgboost, mlflow, streamlit,
  coolprop, gekko, …) is irrelevant to an inference API that is linear + EWMA + a quantile
  lookup. Installing only the confirmed import set keeps the image small and the build
  fast; the served model is microsecond-cheap, so the latency budget is I/O-bound.
- **Lock as an explicit boundary.** Async handlers calling a synchronous, non-awaiting
  service method are already serialised by the event loop; the `asyncio.Lock` documents
  the mutation boundary and stays correct if a call is ever offloaded to a threadpool.

## Consequences

### Positive
- A real, restart-safe, online soft-sensor service with the soft-sensor-specific
  `/label` endpoint most model servers lack; 49 unit tests; CI green; local Docker
  build+run verified.
- The stateful core is framework-agnostic and reusable (1D.3 Streamlit, OT-sim in 1D.4).

### Negative
- **Single instance.** Horizontal scale requires externalising state (Redis) — deferred,
  documented.
- The snapshot pickles a river detector; pickle is version-sensitive (mitigated: it is a
  local, single-writer snapshot, and the model is excluded from it).
- CI does not run the data-dependent tests (gitignored benchmark data); they run locally.

### Neutral
- Feature engineering is upstream of the API (it consumes feature rows, with
  `feature_names` carried in the bundle); a raw-tag-ingesting variant that buffers history
  for lagged features is a future option.

## Revisit triggers
- Multi-replica / HA need → externalise state to Redis (D1).
- A heavier point model (1D.5 nonlinear source) → revisit the "compute is µs" assumption
  and whether the service call should move off the event loop (the lock then becomes
  load-bearing).
- Raw-tag ingestion → add a feature-builder wrapper that buffers raw history.

## References
- ADR-007 (model), ADR-008 (drift/bias-update), ADR-010 (conformal).
- `src/ipis/module1_soft_sensor/serving/{service,api,loader,main}.py`,
  `scripts/register_model.py`, `Dockerfile`, `requirements-serving.txt`,
  `.github/workflows/ci.yml`.
- Tests: `tests/unit/{test_service,test_api,test_loader}.py`.
