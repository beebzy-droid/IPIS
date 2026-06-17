"""F2 evidence — Debutanizer feature-ablation under the identical 1A protocol.

Four arms, same folds, same estimator (plain linear regression), same blocked
time-series CV (claim C2: thermodynamically grounded features beat raw-signal models
in robustness, and complexity-by-physics beats complexity-by-validation):

  u5_only          raw u5 at the transport lag (single-feature backbone)
  physics_only     bubble-point estimate, alpha(T), stripping factor (no raw u5)
  physics_plus_u5  the deployed 1A set (physics + raw u5)
  lagged_raw       the kitchen sink: every input at lags 0..max-lag
                   (complexity set by validation -- the lottery source)

Run (cmd, env ipis, repo root; data gitignored):
    set PYTHONPATH=src
    python scripts\\run_ablation_debutanizer.py --json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.loaders import DebutanizerLoader
from ipis.module1_soft_sensor.evaluation.blocked_cv import blocked_cv_r2, mean_se
from ipis.module1_soft_sensor.features.lagged import make_lagged_features
from ipis.module1_soft_sensor.features.physics_features import (
    make_physics_anchored_features,
    make_u5_only_features,
)

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def _arms(tlag: int, kitchen_max_lag: int) -> dict:
    """name -> feature_builder(segment) -> (X, y). Builders trim their own lags."""

    def to_xy(builder):
        def f(seg: pd.DataFrame):
            x, y = builder(seg)
            return np.asarray(x, float), np.asarray(y, float).ravel()

        return f

    return {
        "u5_only": to_xy(lambda s: make_u5_only_features(s, transport_lag=tlag)),
        "physics_only": to_xy(
            lambda s: make_physics_anchored_features(s, transport_lag=tlag, include_raw_u5=False)
        ),
        "physics_plus_u5": to_xy(
            lambda s: make_physics_anchored_features(s, transport_lag=tlag, include_raw_u5=True)
        ),
        "lagged_raw": to_xy(lambda s: make_lagged_features(s, max_lag=kitchen_max_lag)),
    }


def run(
    path: Path, tlag: int = 15, kitchen_max_lag: int = 17, n_splits: int = 5, test_n: int = 360
) -> dict:
    df = DebutanizerLoader().load(path)
    pool, test = df.iloc[:-test_n].reset_index(drop=True), df.iloc[-test_n:].reset_index(drop=True)
    print(f"pool={len(pool)} test={len(test)} tlag={tlag} kitchen_max_lag={kitchen_max_lag}")

    out: dict = {"transport_lag": tlag, "n_splits": n_splits, "arms": {}}
    for name, builder in _arms(tlag, kitchen_max_lag).items():
        scores = blocked_cv_r2(
            pool, LinearRegression, max_lag=tlag, n_splits=n_splits, feature_builder=builder
        )
        m, se = mean_se(scores)
        # held-out test under the same composition (scaler fit on pool)
        x_tr, y_tr = builder(pool)
        x_te, y_te = builder(test)
        scaler = StandardScaler().fit(x_tr)
        model = LinearRegression().fit(scaler.transform(x_tr), y_tr)
        test_r2 = float(r2_score(y_te, model.predict(scaler.transform(x_te))))
        out["arms"][name] = {
            "cv_mean": float(m),
            "cv_se": float(se),
            "fold_r2": [float(v) for v in scores],
            "worst_fold": float(min(scores)),
            "n_features": int(x_tr.shape[1]),
            "test_r2": test_r2,
        }
        print(
            f"  {name:<16} k={x_tr.shape[1]:>3}  CV {m:+.3f} ± {se:.3f}  "
            f"worst {min(scores):+.3f}  test {test_r2:+.3f}"
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Debutanizer feature ablation (F2 evidence)")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--transport-lag", type=int, default=15)
    ap.add_argument("--kitchen-max-lag", type=int, default=17)
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--json", action="store_true", help="dump to docs/paper/evidence/")
    args = ap.parse_args()
    out = run(args.path, args.transport_lag, args.kitchen_max_lag, args.n_splits)
    if args.json:
        from ipis.shared.evidence import dump_evidence

        print("evidence ->", dump_evidence("ablation_debutanizer", out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
