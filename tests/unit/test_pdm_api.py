"""Tests for the Phase-2D PdM FastAPI surface (ipis.module2_pdm.serving.api)."""

from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from ipis.module2_pdm.serving.api import create_app
from ipis.module2_pdm.serving.service import PdMService

from .test_pdm_service import N_FEAT, build_artifact


def _client() -> TestClient:
    return TestClient(create_app(PdMService(build_artifact())))


def test_health_endpoint():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json()["module"] == "m2"


def test_assess_healthy_sample():
    client = _client()
    r = client.post("/assess", json={"equipment_id": "pump", "features": [0.0] * N_FEAT})
    assert r.status_code == 200
    body = r.json()
    assert body["equipment_id"] == "pump"
    assert body["flag"] == "ok"
    assert body["rul_hours"] is None  # healthy: no RUL yet


def test_assess_escalates_and_state_endpoint():
    client = _client()
    rng = np.random.default_rng(1)
    # plateau then ramp, posting each sample
    for _ in range(30):
        client.post(
            "/assess",
            json={"equipment_id": "pump", "features": rng.standard_normal(N_FEAT).tolist()},
        )
    last = None
    for i in range(90):
        feats = (rng.standard_normal(N_FEAT) + 0.12 * i).tolist()
        last = client.post("/assess", json={"equipment_id": "pump", "features": feats}).json()
    assert last["flag"] == "alarm"
    assert last["rul_hours"] is not None and last["rul_hours"] >= 0.0

    r = client.get("/state")
    assert r.status_code == 200
    state = r.json()
    assert state["health_flags"]["pump"] == "alarm"
    assert "pump" in state["remaining_useful_life"]


def test_assess_wrong_feature_count_is_error():
    client = _client()
    r = client.post("/assess", json={"equipment_id": "pump", "features": [1.0, 2.0]})
    assert r.status_code == 422  # ValueError from the service -> mapped to 422
