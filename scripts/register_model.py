"""Build and register the soft-sensor model bundle (Phase 1D.2c).

Two modes:

  --fixture   Build a small SYNTHETIC bundle (no data needed) and write it to
              models/soft_sensor_fixture.joblib. Deterministic; committed for CI and
              as the default served model when nothing else is configured.

  (default)   Build the REAL bundle from the TEP data (mirrors scripts/tep_baseline.py
              + scripts/conformal_eval.py): fit the physics-anchored linear pipeline on
              train, take calibration residuals on val, and bundle the ADR-008/ADR-010
              params. With --mlflow, also log params + 1D.1b-style metrics + the bundle
              artifact to MLflow (registry + tracking) and register the sklearn model.
              Needs the gitignored data, so this path is NOT exercised in CI.

Run (cmd, env ipis, repo root):
    set PYTHONPATH=src
    python scripts\\register_model.py --fixture
    python scripts\\register_model.py --data-dir data\\raw\\tep --mode mode1 --mlflow
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.serving.loader import (
    BUNDLE_ARTIFACT,
    DEFAULT_BUNDLE,
    ModelBundle,
    save_bundle,
)

DEFAULT_PARAMS = {
    "lam": 0.3,
    "delay": 0,
    "alpha": 0.10,
    "gamma": 0.05,
    "window": 200,
    "drift_on": "corrected",
}


def build_fixture_bundle(seed: int = 1234) -> ModelBundle:
    """Deterministic synthetic bundle: a 3-feature standardised linear pipeline."""
    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(seed)
    n, p = 1000, 3
    x = rng.normal(0, 1, (n, p))
    coef = np.array([3.0, -1.5, 0.75])
    y = x @ coef + rng.normal(0, 1.0, n)
    x_tr, y_tr, x_va, y_va = x[:800], y[:800], x[800:], y[800:]

    model = Pipeline([("scaler", StandardScaler()), ("lr", LinearRegression())]).fit(x_tr, y_tr)
    resid = y_va - model.predict(x_va)  # held-out residuals seed the ACI window
    return ModelBundle(
        model=model,
        feature_names=[f"f{i}" for i in range(p)],
        calibration_residuals=resid.astype(float),
        params=dict(DEFAULT_PARAMS),
        metadata={"kind": "fixture", "seed": seed, "n_train": 800, "n_calib": int(resid.size)},
    )


def build_tep_bundle(
    data_dir: Path, mode: str, lam: float, theta: int, transport_lag: int
) -> tuple[ModelBundle, dict]:
    """Real bundle from one TEP regime; returns (bundle, tracking_metrics)."""
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
    from ipis.module1_soft_sensor.data.tep_loader import TEPLoader
    from ipis.module1_soft_sensor.evaluation.bias_update import apply_bias_update
    from ipis.module1_soft_sensor.features.tep_physics_features import (
        diagnose_transport_lag,
        make_tep_physics_features,
    )

    df = TEPLoader().load(Path(data_dir) / f"tep_{mode}.csv")
    lag = diagnose_transport_lag(df) if transport_lag < 0 else transport_lag
    split = time_ordered_split(df)
    x_tr, y_tr = make_tep_physics_features(split.train, transport_lag=lag)
    x_va, y_va = make_tep_physics_features(split.val, transport_lag=lag)
    feature_names = list(
        getattr(x_tr, "columns", [f"f{i}" for i in range(np.asarray(x_tr).shape[1])])
    )
    x_tr, y_tr = np.asarray(x_tr, float), np.asarray(y_tr, float).ravel()
    x_va, y_va = np.asarray(x_va, float), np.asarray(y_va, float).ravel()

    model = Pipeline([("scaler", StandardScaler()), ("lr", LinearRegression())]).fit(x_tr, y_tr)
    raw_va = model.predict(x_va)
    resid = y_va - raw_va  # seed for ACI (cold-start b=0 -> corrected==raw)
    cor_va, _ = apply_bias_update(y_va, raw_va, lam=lam, delay=theta)

    params = dict(DEFAULT_PARAMS) | {"lam": lam, "delay": theta}
    metrics = {
        "val_r2_raw": float(r2_score(y_va, raw_va)),
        "val_r2_corrected": float(r2_score(y_va, cor_va)),
        "transport_lag": float(lag),
    }
    bundle = ModelBundle(
        model=model,
        feature_names=feature_names,
        calibration_residuals=resid.astype(float),
        params=params,
        metadata={"kind": "tep", "mode": mode, **metrics},
    )
    return bundle, metrics


def log_to_mlflow(bundle: ModelBundle, metrics: dict, run_name: str, model_name: str) -> str:
    """Log params + metrics + the bundle artifact + the sklearn model; register it.

    Returns the bundle artifact URI to set as IPIS_MLFLOW_MODEL for serving.
    """
    import tempfile

    import mlflow
    import mlflow.sklearn

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(bundle.params)
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(bundle.model, name="model", registered_model_name=model_name)
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "soft_sensor_bundle.joblib"
            save_bundle(bundle, local)
            mlflow.log_artifact(str(local), artifact_path="bundle")
        uri = f"runs:/{run.info.run_id}/{BUNDLE_ARTIFACT}"
    return uri


def main() -> int:
    ap = argparse.ArgumentParser(description="Build/register the soft-sensor bundle.")
    ap.add_argument("--fixture", action="store_true", help="build the synthetic CI fixture")
    ap.add_argument("--out", type=Path, default=None, help="output joblib path")
    ap.add_argument("--data-dir", type=Path, default=Path("data/raw/tep"))
    ap.add_argument("--mode", default="mode1")
    ap.add_argument("--lam", type=float, default=0.3)
    ap.add_argument("--theta", type=int, default=2)
    ap.add_argument("--transport-lag", type=int, default=-1)
    ap.add_argument("--mlflow", action="store_true", help="log + register to MLflow (real path)")
    ap.add_argument("--model-name", default="ipis_soft_sensor")
    args = ap.parse_args()

    if args.fixture:
        bundle = build_fixture_bundle()
        out = args.out or Path(DEFAULT_BUNDLE)
        save_bundle(bundle, out)
        print(
            f"fixture bundle -> {out}  (features={bundle.feature_names}, "
            f"n_calib={bundle.calibration_residuals.size})"
        )
        return 0

    bundle, metrics = build_tep_bundle(
        args.data_dir, args.mode, args.lam, args.theta, args.transport_lag
    )
    out = args.out or Path(f"models/soft_sensor_{args.mode}.joblib")
    save_bundle(bundle, out)
    print(f"TEP bundle ({args.mode}) -> {out}  metrics={metrics}")
    if args.mlflow:
        uri = log_to_mlflow(
            bundle, metrics, run_name=f"soft_sensor_{args.mode}", model_name=args.model_name
        )
        print(f"logged to MLflow; serve with  set IPIS_MLFLOW_MODEL={uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
