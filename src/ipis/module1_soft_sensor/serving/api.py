"""FastAPI serving layer for the Module-1 soft sensor (Phase 1D.2b).

Wraps the framework-agnostic :class:`SoftSensorService` (1D.2a) in an async HTTP API:

  POST /predict   single or batch -> point estimate + conformal interval (reads state)
  POST /label     fold a delayed assay into the bias-update + ACI + drift (mutates)
  GET  /health    liveness (lock-free)
  GET  /metrics   current b_t, alpha_t, rolling coverage, counters (consistent read)
  GET  /state     /metrics plus the pending (awaiting-label) sample_ids

Concurrency. Handlers are ``async`` and the service call is synchronous and does not
await inside the critical section, so under the event loop mutations are already
serialised. The ``asyncio.Lock`` in ``app.state.lock`` makes the mutation boundary
explicit and stays correct if a service call is ever offloaded to a threadpool/executor
(e.g. behind a heavier model). ``/health`` is intentionally lock-free so a liveness
probe never blocks behind a mutation.

State + restart. The app is built from an already-constructed service (model loaded by
the caller / 1D.2c loader). On startup it restores a snapshot if one exists; on shutdown
it writes one — so a restart resumes b_t / alpha_t / the score window unchanged.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from ipis.module1_soft_sensor.serving.service import SoftSensorService


# --------------------------------------------------------------------------- #
# Schemas                                                                     #
# --------------------------------------------------------------------------- #
class PredictRequest(BaseModel):
    """Batch-first predict contract; a single prediction is a list of one row."""

    instances: list[list[float]] = Field(..., min_length=1, description="rows of features")
    sample_ids: list[str] | None = Field(None, description="optional client ids, len == instances")


class PredictionRow(BaseModel):
    sample_id: str
    y_pred_raw: float
    y_pred: float
    lower: float
    upper: float
    bias: float
    alpha_t: float
    drift_flag: bool


class PredictResponse(BaseModel):
    predictions: list[PredictionRow]


class LabelRequest(BaseModel):
    sample_id: str
    y_true: float


class LabelResponse(BaseModel):
    sample_id: str
    y_true: float
    residual_raw: float
    residual_corrected: float
    covered: bool
    bias: float
    alpha_t: float
    drift_flag: bool
    rolling_coverage: float
    n_label: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    n_predict: int
    n_label: int


# --------------------------------------------------------------------------- #
# App factory                                                                 #
# --------------------------------------------------------------------------- #
def create_app(service: SoftSensorService) -> FastAPI:
    """Build the FastAPI app around an already-constructed service."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        svc: SoftSensorService = app.state.service
        if svc.snapshot_path is not None and svc.snapshot_path.exists():
            svc.load_snapshot()
        yield
        if svc.snapshot_path is not None:
            svc.save_snapshot()

    app = FastAPI(title="IPIS soft sensor", version="1.0", lifespan=lifespan)
    app.state.service = service
    app.state.lock = asyncio.Lock()

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:  # lock-free liveness
        svc: SoftSensorService = request.app.state.service
        return HealthResponse(
            status="ok",
            model_loaded=svc.point_predict is not None,
            n_predict=svc.n_predict,
            n_label=svc.n_label,
        )

    @app.post("/predict", response_model=PredictResponse)
    async def predict(req: PredictRequest, request: Request) -> PredictResponse:
        svc: SoftSensorService = request.app.state.service
        x = np.asarray(req.instances, dtype=float)
        async with request.app.state.lock:
            try:
                rows = svc.predict(x, sample_id=req.sample_ids)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        rows = rows if isinstance(rows, list) else [rows]
        return PredictResponse(predictions=[PredictionRow(**r) for r in rows])

    @app.post("/label", response_model=LabelResponse)
    async def label(req: LabelRequest, request: Request) -> LabelResponse:
        svc: SoftSensorService = request.app.state.service
        async with request.app.state.lock:
            try:
                result = svc.label(req.sample_id, req.y_true)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        return LabelResponse(**result)

    @app.get("/metrics")
    async def metrics(request: Request) -> dict:
        svc: SoftSensorService = request.app.state.service
        async with request.app.state.lock:
            return svc.metrics()

    @app.get("/state")
    async def state(request: Request) -> dict:
        svc: SoftSensorService = request.app.state.service
        async with request.app.state.lock:
            out = svc.metrics()
            out["pending_sample_ids"] = list(svc.buffer.keys())[:50]
            return out

    return app
