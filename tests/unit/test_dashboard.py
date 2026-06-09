"""Tests for the dashboard's pure pieces (Phase 1D.3).

The Streamlit UI (`render`) is exercised by running it, not pytest. Here we cover the
two testable units: the synthetic stream generator and `ServiceClient` (against the real
FastAPI app via an httpx ASGITransport, so it's a genuine client<->API round-trip with no
network). We also assert the module imports without pulling in Streamlit.
"""

from __future__ import annotations

import sys

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.serving.api import create_app
from ipis.module1_soft_sensor.serving.dashboard import (
    DEFAULT_COEF,
    ServiceClient,
    make_synthetic_sample,
)
from ipis.module1_soft_sensor.serving.service import SoftSensorService


# --------------------------------------------------------------------------- #
# synthetic stream                                                            #
# --------------------------------------------------------------------------- #
def test_make_synthetic_sample_shape_and_type():
    x, y = make_synthetic_sample(np.random.default_rng(0))
    assert x.shape == (len(DEFAULT_COEF),)
    assert isinstance(y, float)


def test_noise_scale_inflates_residual_variance():
    coef = np.asarray(DEFAULT_COEF)
    rng = np.random.default_rng(1)
    res_lo = [make_synthetic_sample(rng, noise_scale=1.0) for _ in range(4000)]
    res_hi = [make_synthetic_sample(rng, noise_scale=4.0) for _ in range(4000)]
    v_lo = np.var([y - x @ coef for x, y in res_lo])
    v_hi = np.var([y - x @ coef for x, y in res_hi])
    assert v_hi > 4 * v_lo  # ~16x vs ~1x


def test_mean_shift_offsets_residual_mean():
    coef = np.asarray(DEFAULT_COEF)
    rng = np.random.default_rng(2)
    samples = [make_synthetic_sample(rng, mean_shift=5.0) for _ in range(4000)]
    mean_res = np.mean([y - x @ coef for x, y in samples])
    assert abs(mean_res - 5.0) < 0.2


# --------------------------------------------------------------------------- #
# ServiceClient against the real app (ASGI transport)                         #
# --------------------------------------------------------------------------- #
def _service() -> SoftSensorService:
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, (300, 3))
    coef = np.array([3.0, -1.5, 0.75])
    y = x @ coef + rng.normal(0, 1, 300)
    model = Pipeline([("s", StandardScaler()), ("lr", LinearRegression())]).fit(x, y)
    resid = y - model.predict(x)

    def point_predict(arr):
        return np.asarray(model.predict(np.atleast_2d(arr)), dtype=float).ravel()

    return SoftSensorService(point_predict, init_residuals=resid, lam=0.3, delay=0, alpha=0.10)


@pytest.fixture
def client() -> ServiceClient:
    # TestClient is a sync httpx.Client that drives the ASGI app synchronously,
    # so it stands in for the dashboard's real httpx client against a live server.
    app = create_app(_service())
    return ServiceClient(client=TestClient(app))


def test_client_health(client):
    assert client.health() is True


def test_client_predict_returns_valid_interval(client):
    rows = client.predict([[1.0, 0.0, 0.0]], ["s0"])
    row = rows[0]
    assert row["sample_id"] == "s0"
    assert row["lower"] <= row["y_pred"] <= row["upper"]


def test_client_label_round_trip(client):
    rows = client.predict([[1.0, 0.0, 0.0]], ["s0"])
    res = client.label("s0", float(rows[0]["y_pred"]))
    assert isinstance(res["covered"], bool)
    assert res["n_label"] == 1


def test_client_metrics_exposes_state(client):
    m = client.metrics()
    for key in ("bias", "alpha_t", "target_coverage", "rolling_coverage"):
        assert key in m
    assert m["target_coverage"] == pytest.approx(0.90)


def test_prelabel_rolling_coverage_is_none_over_the_wire(client):
    # Server-side it's math.nan until the first label, but JSON has no NaN — it
    # arrives as null/None. The dashboard's metric formatting must tolerate this
    # (regression: f"{None:.3f}" TypeError in the metrics strip).
    m = client.metrics()
    assert m["n_label"] == 0
    assert m["rolling_coverage"] is None


# --------------------------------------------------------------------------- #
# import hygiene                                                              #
# --------------------------------------------------------------------------- #
def test_module_imports_without_streamlit():
    # render() imports streamlit lazily, so importing the module must not require it.
    assert "streamlit" not in sys.modules
