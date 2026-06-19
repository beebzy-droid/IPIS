"""FastAPI surface for the Module 2 PdM service (Phase 2D).

`create_app(service)` factory mirroring M1's serving/api split: the framework-
agnostic PdMService lives in `app.state`, endpoints read it lock-free via the
request. Endpoints:

  GET  /health  -> liveness
  POST /assess  -> ingest one feature vector, return the equipment assessment
  GET  /state   -> the current OperationalState M2 fields (health / flags / RUL)
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ipis.module2_pdm.serving.service import PdMService
from ipis.shared.state_bus import HealthFlag


class AssessRequest(BaseModel):
    equipment_id: str
    features: list[float] = Field(..., description="One feature vector for the equipment")


class AssessResponse(BaseModel):
    equipment_id: str
    t2: float
    health_score: float
    flag: HealthFlag
    fpt: int | None
    rul_hours: float | None


class StateResponse(BaseModel):
    equipment_health: dict[str, float]
    health_flags: dict[str, HealthFlag]
    remaining_useful_life: dict[str, float]


def create_app(service: PdMService) -> FastAPI:
    """Build the PdM FastAPI app around a constructed service."""
    app = FastAPI(title="IPIS Module 2 — Predictive Maintenance", version="2.0")
    app.state.service = service

    @app.exception_handler(ValueError)
    async def _value_error(request: Request, exc: ValueError) -> JSONResponse:
        # bad input (e.g. wrong feature count) -> client error, not 500
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/health")
    async def health() -> dict:  # lock-free liveness
        return {"status": "ok", "module": "m2"}

    @app.post("/assess", response_model=AssessResponse)
    async def assess(req: AssessRequest, request: Request) -> dict:
        svc: PdMService = request.app.state.service
        return svc.observe(req.equipment_id, req.features)

    @app.get("/state", response_model=StateResponse)
    async def state(request: Request) -> dict:
        svc: PdMService = request.app.state.service
        return svc.operational_state_fields()

    return app
