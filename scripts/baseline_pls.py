"""PLS baseline for the Debutanizer soft sensor (Phase 1A).

The first ML baseline. PLS is chosen because the lagged features are highly
collinear (each input copied at 0..max_lag), and PLS handles collinearity by
projecting onto latent components -- a natural fit and a strong, simple
linear baseline.

Honest-evaluation guarantees:
    - Time-ordered split (no shuffle) via data.preprocessing.time_ordered_split.
    - Lagged features built WITHIN each split segment (no cross-boundary leak).
    - StandardScaler fit on TRAIN ONLY, applied to val/test.
    - n_components tuned on VALIDATION; test reported once, untouched during tuning.

Reference target: the in-sample linear ceiling with lags 1..17 was R^2 = 0.79
(signal diagnosis). The held-out PLS R^2 should land somewhat below that;
the gap is the honest cost of out-of-sample generalization.

Run locally from the project root:

    python scripts/baseline_pls.py
    python scripts/baseline_pls.py --max-lag 17 --max-components 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.features.lagged import make_lagged_features

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def main() -> int:
    ap = argparse.ArgumentParser(description="PLS baseline for the Debutanizer soft sensor.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--max-lag", type=int, default=17)
    ap.add_argument("--max-components", type=int, default=30)
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

    # 1) Time-ordered split FIRST (no shuffle).
    split = time_ordered_split(df)  # 0.70 / 0.15 / 0.15
    # 2) Lagged features WITHIN each segment (no cross-boundary leakage).
    X_tr, y_tr = make_lagged_features(split.train, args.max_lag)
    X_va, y_va = make_lagged_features(split.val, args.max_lag)
    X_te, y_te = make_lagged_features(split.test, args.max_lag)

    # 3) Scale on TRAIN ONLY.
    x_scaler = StandardScaler().fit(X_tr)
    Xtr, Xva, Xte = (x_scaler.transform(X) for X in (X_tr, X_va, X_te))

    print("=" * 60)
    print("PLS baseline -- leakage-safe lagged features")
    print("=" * 60)
    print(f"  max_lag              : {args.max_lag}")
    print(f"  features             : {X_tr.shape[1]}")
    print(f"  rows train/val/test  : {len(y_tr)}/{len(y_va)}/{len(y_te)}")
    print("-" * 60)

    # 4) Tune n_components on VALIDATION.
    max_k = min(args.max_components, X_tr.shape[1])
    best_k, best_va_r2 = 1, -np.inf
    for k in range(1, max_k + 1):
        model = PLSRegression(n_components=k)
        model.fit(Xtr, y_tr)
        va_r2 = r2_score(y_va, model.predict(Xva).ravel())
        if va_r2 > best_va_r2:
            best_k, best_va_r2 = k, va_r2

    # 5) Refit at best_k; report train/val/test once.
    model = PLSRegression(n_components=best_k)
    model.fit(Xtr, y_tr)
    tr_p = model.predict(Xtr).ravel()
    va_p = model.predict(Xva).ravel()
    te_p = model.predict(Xte).ravel()

    print(f"  best n_components    : {best_k}  (selected on validation)")
    print(f"  {'split':6s}{'R^2':>10s}{'RMSE':>12s}")
    for name, yt, yp in (
        ("train", y_tr, tr_p),
        ("val", y_va, va_p),
        ("test", y_te, te_p),
    ):
        print(f"  {name:6s}{r2_score(yt, yp):>10.4f}{root_mean_squared_error(yt, yp):>12.4f}")
    print("-" * 60)
    print("  Reference: in-sample linear ceiling (lags 1..17) was R^2 = 0.79.")
    print("  Held-out test R^2 below that is the honest generalization cost.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
