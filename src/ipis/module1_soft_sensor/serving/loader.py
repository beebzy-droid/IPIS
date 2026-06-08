"""Model bundle + service loader for the soft-sensor serving layer (Phase 1D.2c).

The serving layer needs a frozen point model plus the metadata to rebuild the stateful
service: the calibration residuals that seed ACI and the ADR-008/ADR-010
hyper-parameters. We standardise on one joblib **bundle** as the interchange format.
MLflow (optional) is used for registry + tracking and stores the same bundle as a run
artifact, so :func:`load_service` always ends up with a :class:`ModelBundle` whether
the bytes came from a local file or an MLflow-logged artifact. With no MLflow installed,
serving and CI run entirely from the local joblib bundle (decision D4).

Resolution order for the bundle (first hit wins):
    1. explicit ``bundle_path`` arg
    2. ``IPIS_MODEL_BUNDLE`` env var (a joblib path)
    3. ``mlflow_model`` arg / ``IPIS_MLFLOW_MODEL`` env (an MLflow artifact URI of the
       bundle, e.g. ``runs:/<run_id>/bundle/soft_sensor_bundle.joblib``)
    4. the committed fixture at ``models/soft_sensor_fixture.joblib``
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
from numpy.typing import NDArray

from ipis.module1_soft_sensor.evaluation.drift import make_adwin
from ipis.module1_soft_sensor.serving.service import SoftSensorService

FloatArray = NDArray[np.float64]
DEFAULT_BUNDLE = "models/soft_sensor_fixture.joblib"
BUNDLE_ARTIFACT = "bundle/soft_sensor_bundle.joblib"  # path used inside an MLflow run


@dataclass
class ModelBundle:
    """Everything needed to (re)build a SoftSensorService except live mutable state."""

    model: object  # fitted sklearn estimator; predict(2-D features) -> 1-D raw y
    feature_names: list[str]
    calibration_residuals: FloatArray  # held-out residuals; seed the ACI score window
    params: dict  # lam, delay, alpha, gamma, window, drift_on
    metadata: dict = field(default_factory=dict)  # e.g. 1D.1b coverage, data hash


def save_bundle(bundle: ModelBundle, path: str | Path) -> Path:
    """Persist a bundle as joblib (the interchange format)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, p)
    return p


def load_bundle(path: str | Path) -> ModelBundle:
    """Load a joblib bundle, validating its shape."""
    obj = joblib.load(Path(path))
    if not isinstance(obj, ModelBundle):
        raise TypeError(f"{path} is not a ModelBundle (got {type(obj).__name__})")
    obj.calibration_residuals = np.asarray(obj.calibration_residuals, dtype=float)
    return obj


def _load_bundle_from_mlflow(artifact_uri: str) -> ModelBundle:
    """Download a bundle artifact from MLflow and load it. MLflow imported lazily."""
    import mlflow  # optional dependency; only needed on this path

    local = mlflow.artifacts.download_artifacts(artifact_uri=artifact_uri)
    return load_bundle(local)


def _resolve_bundle(bundle_path: str | Path | None, mlflow_model: str | None) -> ModelBundle:
    bundle_path = bundle_path or os.environ.get("IPIS_MODEL_BUNDLE")
    mlflow_model = mlflow_model or os.environ.get("IPIS_MLFLOW_MODEL")
    if bundle_path:
        return load_bundle(bundle_path)
    if mlflow_model:
        return _load_bundle_from_mlflow(mlflow_model)
    if Path(DEFAULT_BUNDLE).exists():
        return load_bundle(DEFAULT_BUNDLE)
    raise FileNotFoundError(
        "No model bundle found. Set IPIS_MODEL_BUNDLE (joblib path) or IPIS_MLFLOW_MODEL "
        f"(MLflow artifact URI), or provide {DEFAULT_BUNDLE}."
    )


def load_service(
    bundle_path: str | Path | None = None,
    *,
    mlflow_model: str | None = None,
    snapshot_path: str | Path | None = None,
    enable_drift: bool = True,
    drift_delta: float = 0.002,
) -> SoftSensorService:
    """Build a ready SoftSensorService from a model bundle.

    The frozen point model + hyper-parameters come from the bundle; the live drift
    detector is constructed here (ADWIN by default) and the mutable state is empty
    until a snapshot is restored (the FastAPI lifespan does that, 1D.2b).
    """
    bundle = _resolve_bundle(bundle_path, mlflow_model)
    model = bundle.model

    def point_predict(x: FloatArray) -> FloatArray:
        x = np.atleast_2d(np.asarray(x, dtype=float))
        return np.asarray(model.predict(x), dtype=float).ravel()

    detector = make_adwin(delta=drift_delta) if enable_drift else None
    return SoftSensorService(
        point_predict,
        init_residuals=bundle.calibration_residuals,
        drift_detector=detector,
        snapshot_path=snapshot_path,
        **bundle.params,
    )
