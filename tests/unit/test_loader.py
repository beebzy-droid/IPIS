"""Tests for the serving loader + entrypoint (Phase 1D.2c).

Bundle save/load round-trip, ``load_service`` building a working service, the ASGI
entrypoint resolving a bundle from the environment, and a real MLflow artifact
round-trip (skipped if MLflow is not installed).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.serving import api as api_mod
from ipis.module1_soft_sensor.serving.loader import (
    ModelBundle,
    load_bundle,
    load_service,
    save_bundle,
)


def _fixture_bundle(seed: int = 7) -> ModelBundle:
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, (600, 3))
    coef = np.array([3.0, -1.5, 0.75])
    y = x @ coef + rng.normal(0, 1.0, 600)
    model = Pipeline([("scaler", StandardScaler()), ("lr", LinearRegression())]).fit(
        x[:450], y[:450]
    )
    resid = y[450:] - model.predict(x[450:])
    return ModelBundle(
        model=model,
        feature_names=["f0", "f1", "f2"],
        calibration_residuals=resid.astype(float),
        params={
            "lam": 0.3,
            "delay": 0,
            "alpha": 0.10,
            "gamma": 0.05,
            "window": 200,
            "drift_on": "corrected",
        },
        metadata={"kind": "test"},
    )


# --------------------------------------------------------------------------- #
# bundle round-trip                                                           #
# --------------------------------------------------------------------------- #
def test_bundle_save_load_roundtrip(tmp_path):
    b = _fixture_bundle()
    p = save_bundle(b, tmp_path / "b.joblib")
    assert p.exists()
    got = load_bundle(p)
    assert got.feature_names == b.feature_names
    assert got.params == b.params
    np.testing.assert_allclose(got.calibration_residuals, b.calibration_residuals)
    x = np.array([[1.0, 0.0, 0.0]])
    np.testing.assert_allclose(got.model.predict(x), b.model.predict(x))


def test_load_bundle_rejects_non_bundle(tmp_path):
    import joblib

    p = tmp_path / "bad.joblib"
    joblib.dump({"not": "a bundle"}, p)
    with pytest.raises(TypeError, match="not a ModelBundle"):
        load_bundle(p)


# --------------------------------------------------------------------------- #
# load_service                                                                #
# --------------------------------------------------------------------------- #
def test_load_service_builds_working_service(tmp_path):
    p = save_bundle(_fixture_bundle(), tmp_path / "b.joblib")
    svc = load_service(bundle_path=p)
    out = svc.predict(np.array([[1.0, 0.0, 0.0]]))
    row = out[0]
    assert row["lower"] <= row["y_pred"] <= row["upper"]
    assert svc.detector is not None  # ADWIN attached by default
    assert svc.aci.target_alpha == pytest.approx(0.10)


def test_load_service_can_disable_drift(tmp_path):
    p = save_bundle(_fixture_bundle(), tmp_path / "b.joblib")
    svc = load_service(bundle_path=p, enable_drift=False)
    assert svc.detector is None


def test_load_service_env_resolution(tmp_path, monkeypatch):
    p = save_bundle(_fixture_bundle(), tmp_path / "b.joblib")
    monkeypatch.setenv("IPIS_MODEL_BUNDLE", str(p))
    svc = load_service()  # no explicit path -> resolves from env
    assert svc.n_predict == 0 and svc.detector is not None


def test_load_service_missing_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("IPIS_MODEL_BUNDLE", raising=False)
    monkeypatch.delenv("IPIS_MLFLOW_MODEL", raising=False)
    monkeypatch.chdir(tmp_path)  # no models/ here
    with pytest.raises(FileNotFoundError, match="No model bundle"):
        load_service()


# --------------------------------------------------------------------------- #
# entrypoint                                                                  #
# --------------------------------------------------------------------------- #
def test_entrypoint_app_serves_from_env_bundle(tmp_path, monkeypatch):
    p = save_bundle(_fixture_bundle(), tmp_path / "b.joblib")
    monkeypatch.setenv("IPIS_MODEL_BUNDLE", str(p))
    main_mod = importlib.import_module("ipis.module1_soft_sensor.serving.main")
    importlib.reload(main_mod)  # rebuild module-level app under the env bundle
    with TestClient(main_mod.app) as c:
        assert c.get("/health").json()["status"] == "ok"
        r = c.post("/predict", json={"instances": [[1.0, 0.0, 0.0]]})
        assert r.status_code == 200
        assert r.json()["predictions"][0]["lower"] <= r.json()["predictions"][0]["upper"]


# --------------------------------------------------------------------------- #
# MLflow round-trip (optional)                                                #
# --------------------------------------------------------------------------- #
def test_mlflow_artifact_roundtrip(tmp_path, monkeypatch):
    mlflow = pytest.importorskip("mlflow")
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")  # mlflow>=3 file-store opt-out
    monkeypatch.setenv("MLFLOW_TRACKING_URI", (tmp_path / "mlruns").as_uri())
    bundle = _fixture_bundle()
    with mlflow.start_run() as run:
        mlflow.log_params(bundle.params)
        local = tmp_path / "soft_sensor_bundle.joblib"
        save_bundle(bundle, local)
        mlflow.log_artifact(str(local), artifact_path="bundle")
        uri = f"runs:/{run.info.run_id}/bundle/soft_sensor_bundle.joblib"
    svc = load_service(mlflow_model=uri)
    out = svc.predict(np.array([[1.0, 0.0, 0.0]]))[0]
    assert out["lower"] <= out["y_pred"] <= out["upper"]


# keep api_mod referenced (import side: ensures the serving package imports cleanly)
def test_api_module_importable():
    assert hasattr(api_mod, "create_app")


def test_default_committed_fixture_loads(monkeypatch):
    """The committed models/soft_sensor_fixture.joblib must load via default resolution."""
    from ipis.module1_soft_sensor.serving.loader import DEFAULT_BUNDLE

    monkeypatch.delenv("IPIS_MODEL_BUNDLE", raising=False)
    monkeypatch.delenv("IPIS_MLFLOW_MODEL", raising=False)
    if not Path(DEFAULT_BUNDLE).exists():
        pytest.skip("committed fixture absent; run scripts/register_model.py --fixture")
    svc = load_service()
    out = svc.predict(np.array([[1.0, 0.0, 0.0]]))[0]
    assert out["lower"] <= out["y_pred"] <= out["upper"]
