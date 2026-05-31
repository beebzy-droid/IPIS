"""Compare physics-anchored vs statistical models under blocked CV (Path B).

The core Module 1 experiment. Three models, identical forward-chaining CV and
identical held-out test, with PER-FOLD R^2 shown (the visibility the earlier
selection script lacked):

    1. u5-only         : raw u5 at the transport lag (1 feature) -- backbone.
    2. physics-anchored: bubble-point C4 + stripping factor (alpha*reflux) +
                         u5, all at the transport lag (~4 features).
    3. kitchen-sink PLS: 126 lagged features (7 inputs x lags 0..max_lag).

The question is NOT only "which wins held-out R^2" but whether physics-grounding
REDUCES cross-regime CV variance (less negative folds, smaller SE) -- the
instability that wrecked the kitchen-sink model. Run from project root:

    python scripts/compare_physics_pls.py
    python scripts/compare_physics_pls.py --transport-lag 15 --max-lag 17 --n-splits 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.evaluation.blocked_cv import blocked_cv_r2, mean_se
from ipis.module1_soft_sensor.features.lagged import make_lagged_features
from ipis.module1_soft_sensor.features.physics_features import (
    make_physics_anchored_features,
    make_u5_only_features,
)

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def _held_out_test(builder, make_estimator, pool: pd.DataFrame, test: pd.DataFrame) -> tuple:
    """Fit on full pool, evaluate once on held-out test. Returns (R2, RMSE)."""
    X_pool, y_pool = builder(pool)
    X_te, y_te = builder(test)
    scaler = StandardScaler().fit(X_pool)
    model = make_estimator().fit(scaler.transform(X_pool), y_pool)
    pred = np.asarray(model.predict(scaler.transform(X_te))).ravel()
    return r2_score(y_te, pred), root_mean_squared_error(y_te, pred)


def main() -> int:
    ap = argparse.ArgumentParser(description="Physics-anchored vs statistical comparison.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--transport-lag", type=int, default=15)
    ap.add_argument("--max-lag", type=int, default=17)
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--pls-components", type=int, default=1)
    args = ap.parse_args()

    try:
        from ipis.module1_soft_sensor.data.loaders import DebutanizerLoader
    except Exception as exc:  # noqa: BLE001
        print(f"Could not import DebutanizerLoader: {exc}")
        return 1
    try:
        df = DebutanizerLoader().load(args.path)
    except FileNotFoundError as exc:
        print(f"Data file not found: {exc}")
        return 1

    split = time_ordered_split(df)
    pool = pd.concat([split.train, split.val], ignore_index=True)
    test = split.test.reset_index(drop=True)

    tlag = args.transport_lag
    models = {
        "u5-only (1 feat)": {
            "builder": lambda seg: make_u5_only_features(seg, tlag),
            "make": lambda: LinearRegression(),
            "guard_lag": tlag,
        },
        "physics-anchored": {
            "builder": lambda seg: make_physics_anchored_features(seg, tlag, include_raw_u5=True),
            "make": lambda: LinearRegression(),
            "guard_lag": tlag,
        },
        "kitchen-sink PLS": {
            "builder": lambda seg: make_lagged_features(seg, args.max_lag),
            "make": lambda: PLSRegression(n_components=args.pls_components),
            "guard_lag": args.max_lag,
        },
    }

    print("=" * 72)
    print("Path B comparison -- blocked CV (per-fold) + held-out test")
    print("=" * 72)
    print(f"  pool rows={len(pool)}  test rows={len(test)}  n_splits={args.n_splits}")
    print(f"  transport_lag={tlag}  max_lag(kitchen-sink)={args.max_lag}")
    print("-" * 72)

    for name, spec in models.items():
        folds = blocked_cv_r2(
            pool,
            make_estimator=spec["make"],
            max_lag=spec["guard_lag"],
            n_splits=args.n_splits,
            feature_builder=spec["builder"],
        )
        m, se = mean_se(folds)
        te_r2, te_rmse = _held_out_test(spec["builder"], spec["make"], pool, test)
        fold_str = " ".join(f"{f:+.2f}" for f in folds)
        print(f"  {name}")
        print(f"    per-fold R^2 : [{fold_str}]")
        print(f"    CV mean+/-SE : {m:+.3f} +/- {se:.3f}")
        print(f"    held-out test: R^2={te_r2:+.4f}  RMSE={te_rmse:.4f}")
        print("-" * 72)

    print("  Read: physics-anchored WINS if its CV folds are less negative and")
    print("  its SE smaller than kitchen-sink (robustness under regime shift),")
    print("  at comparable or better held-out R^2. Held-out alone is not the")
    print("  verdict -- cross-regime STABILITY is the Module 1 result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
