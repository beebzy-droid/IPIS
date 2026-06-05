"""Tests for the FastAPI serving layer (Phase 1D.2b).

Sync TestClient for the request/response contract + error mapping + lifespan
snapshot; async httpx client for the concurrency / lock behaviour (no lost updates
under concurrent /label).
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from ipis.module1_soft_sensor.evaluation.drift import make_adwin
from ipis.module1_soft_sensor.serving.api import create_app
from ipis.module1_soft_sensor.serving.service import SoftSensorService


def _model(coef: float = 3.0, intercept: float = 0.0):
    def predict(x: np.ndarray) -> np.ndarray:
        x = np.atleast_2d(np.asarray(x, float))
        return intercept + coef * x[:, 0]

    return predict


def _service(seed: int = 0, **kw) -> SoftSensorService:
    rng = np.random.default_rng(seed)
    return SoftSensorService(_model(), init_residuals=rng.normal(0, 1.0, 300), alpha=0.10, **kw)


def _client(svc: SoftSensorService) -> TestClient:
    return TestClient(create_app(svc))


# --------------------------------------------------------------------------- #
# contract                                                                    #
# --------------------------------------------------------------------------- #
def test_health_ok():
    with _client(_service()) as c:
        r = c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok" and body["model_loaded"] is True


def test_predict_batch_intervals_well_formed():
    with _client(_service()) as c:
        r = c.post("/predict", json={"instances": [[1.0], [2.0], [3.0]]})
        assert r.status_code == 200
        preds = r.json()["predictions"]
        assert len(preds) == 3
        for p in preds:
            assert p["lower"] <= p["y_pred"] <= p["upper"]
        assert preds[1]["y_pred_raw"] == pytest.approx(6.0)


def test_predict_with_client_ids():
    with _client(_service()) as c:
        r = c.post("/predict", json={"instances": [[1.0]], "sample_ids": ["abc"]})
        assert r.json()["predictions"][0]["sample_id"] == "abc"


def test_predict_id_length_mismatch_is_422():
    with _client(_service()) as c:
        r = c.post("/predict", json={"instances": [[1.0], [2.0]], "sample_ids": ["only-one"]})
        assert r.status_code == 422


def test_empty_instances_is_422():
    with _client(_service()) as c:
        assert c.post("/predict", json={"instances": []}).status_code == 422


def test_label_mutates_bias_and_alpha():
    with _client(_service()) as c:
        c.post("/predict", json={"instances": [[1.0]], "sample_ids": ["s0"]})
        before = c.get("/metrics").json()
        # truth far above the raw prediction -> bias must move up
        r = c.post("/label", json={"sample_id": "s0", "y_true": 50.0})
        assert r.status_code == 200
        after = c.get("/metrics").json()
        assert after["bias"] > before["bias"]
        assert after["n_label"] == before["n_label"] + 1
        assert "covered" in r.json()


def test_label_unknown_id_is_404():
    with _client(_service()) as c:
        r = c.post("/label", json={"sample_id": "ghost", "y_true": 1.0})
        assert r.status_code == 404


def test_state_lists_pending_sample_ids():
    with _client(_service()) as c:
        c.post("/predict", json={"instances": [[1.0], [2.0]], "sample_ids": ["p0", "p1"]})
        st = c.get("/state").json()
        assert set(st["pending_sample_ids"]) == {"p0", "p1"}
        assert st["pending_labels"] == 2


def test_drift_flag_surfaces_through_api():
    svc = _service(drift_detector=make_adwin(delta=0.002), drift_on="raw", lam=1.0)
    with _client(svc) as c:
        seen = False
        for k in range(600):
            sid = f"d{k}"
            c.post("/predict", json={"instances": [[1.0]], "sample_ids": [sid]})
            shift = 0.0 if k < 300 else 8.0
            r = c.post("/label", json={"sample_id": sid, "y_true": 3.0 + shift})
            seen = seen or r.json()["drift_flag"]
        assert seen


# --------------------------------------------------------------------------- #
# lifespan snapshot through the app                                           #
# --------------------------------------------------------------------------- #
def test_shutdown_writes_snapshot_and_restart_restores(tmp_path):
    snap = tmp_path / "state.pkl"
    svc = _service(snapshot_path=snap, lam=0.3)
    with _client(svc) as c:
        for k in range(40):
            sid = f"s{k}"
            c.post("/predict", json={"instances": [[1.0]], "sample_ids": [sid]})
            c.post("/label", json={"sample_id": sid, "y_true": 8.0})
        m_before = c.get("/metrics").json()
    assert snap.exists()  # written on shutdown (lifespan exit)

    svc2 = _service(snapshot_path=snap, lam=0.3)
    with _client(svc2) as c:  # startup restores
        m_after = c.get("/metrics").json()
        assert m_after["bias"] == pytest.approx(m_before["bias"])
        assert m_after["n_label"] == m_before["n_label"]
        assert m_after["alpha_t"] == pytest.approx(m_before["alpha_t"])


# --------------------------------------------------------------------------- #
# concurrency / lock                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_concurrent_labels_no_lost_updates():
    # Fire many concurrent /label for distinct, already-predicted ids. The lock must
    # leave the counters exact and the buffer fully drained (no lost increments / no
    # double-pop) regardless of interleaving.
    svc = _service(lam=0.3, buffer_size=256)
    transport = ASGITransport(app=create_app(svc))
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        n = 200
        await asyncio.gather(
            *[
                c.post("/predict", json={"instances": [[1.0]], "sample_ids": [f"c{k}"]})
                for k in range(n)
            ]
        )
        results = await asyncio.gather(
            *[c.post("/label", json={"sample_id": f"c{k}", "y_true": 5.0}) for k in range(n)]
        )
        assert all(r.status_code == 200 for r in results)
        m = (await c.get("/metrics")).json()
        assert m["n_label"] == n
        assert m["pending_labels"] == 0
