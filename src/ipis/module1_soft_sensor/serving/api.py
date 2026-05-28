"""FastAPI inference endpoint for Module 1 soft sensor.

Provides:
- POST /predict — single-sample inference with conformal prediction interval
- GET /health — health/readiness check
- GET /metrics — Prometheus-compatible metrics
- GET /version — model version and metadata

Production target: < 200 ms p95 latency on a single sample.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="IPIS Module 1 — Soft Sensor",
    description="Hybrid soft sensor inference endpoint",
    version="0.1.0",
)


class PredictionRequest(BaseModel):
    """Request payload for /predict."""

    features: dict[str, float] = Field(..., description="Process measurement values")


class PredictionResponse(BaseModel):
    """Response payload for /predict."""

    prediction: float
    lower_bound: float
    upper_bound: float
    confidence: float
    drift_flag: bool
    latency_ms: float
    model_version: str


@app.get("/health")
async def health() -> dict[str, str]:
    """Health/readiness probe."""
    return {"status": "ok"}


@app.get("/version")
async def version() -> dict[str, str]:
    """Model and service version info."""
    return {
        "service_version": "0.1.0",
        "model_version": "not_loaded",
        "status": "placeholder",
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest) -> PredictionResponse:
    """Soft sensor prediction with conformal prediction interval.

    Args:
        request: PredictionRequest with process features.

    Returns:
        PredictionResponse with prediction, 95% interval, and metadata.

    Raises:
        NotImplementedError: Placeholder until Phase 1D.
    """
    raise NotImplementedError("Implement in Phase 1D. See docs/module1/spec.md")
