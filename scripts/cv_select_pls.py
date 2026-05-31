"""Select PLS complexity by blocked CV + 1-SE rule, then evaluate ONCE on test.

The honest replacement for single-adjacent-validation selection. Run from the
project root:

    python scripts/cv_select_pls.py
    python scripts/cv_select_pls.py --max-lag 17 --max-components 20 --n-splits 5

Protocol:
    1. Hold out the last 15% as the test set (touched exactly once, at the end).
    2. On the remaining 85% (the CV pool), run forward-chaining blocked CV for
       each n_components; report mean +/- SE per complexity.
    3. Select n_components by the 1-SE rule (simplest within 1 SE of the best
       CV mean) -- parsimony chosen WITHOUT inspecting the test set.
    4. Refit at the selected complexity on the full CV pool; report test R^2 once.

This directly addresses the finding that adjacent validation picks the
regime-overfit model (val peaks where test craters). The CV mean+SE gives an
honest, cross-regime selection; the 1-SE rule encodes the parsimony the data
calls for.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score, root_mean_squared_error
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.evaluation.blocked_cv import (
    blocked_cv_r2,
    mean_se,
    one_se_selection,
)
from ipis.module1_soft_sensor.features.lagged import make_lagged_features

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def main() -> int:
    ap = argparse.ArgumentParser(description="Blocked-CV PLS selection (1-SE rule).")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--max-lag", type=int, default=17)
    ap.add_argument("--max-components", type=int, default=20)
    ap.add_argument("--n-splits", type=int, default=5)
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

    # 1) Pool = train+val (first 85%); test = last 15% (held out, touched once).
    split = time_ordered_split(df)  # 0.70 / 0.15 / 0.15
    pool = pd.concat([split.train, split.val], ignore_index=True)
    test = split.test.reset_index(drop=True)

    # 2) Blocked CV on the pool for each n_components.
    max_k = min(args.max_components, 7 * (args.max_lag + 1))
    ks: list[float] = []
    means: list[float] = []
    ses: list[float] = []
    print("=" * 60)
    print("Blocked time-series CV on the pool (train+val)")
    print("=" * 60)
    print(f"  pool rows={len(pool)}  test rows={len(test)}  n_splits={args.n_splits}")
    print(f"  {'k':>3s}{'cv_mean_R2':>12s}{'cv_se':>9s}")
    for k in range(1, max_k + 1):
        scores = blocked_cv_r2(
            pool,
            make_estimator=lambda k=k: PLSRegression(n_components=k),
            max_lag=args.max_lag,
            n_splits=args.n_splits,
        )
        m, se = mean_se(scores)
        ks.append(k)
        means.append(m)
        ses.append(se)
        print(f"  {k:>3d}{m:>12.4f}{se:>9.4f}")

    # 3) 1-SE parsimony selection (no test inspection).
    selected_k = int(one_se_selection(ks, means, ses))
    best_k = ks[int(max(range(len(means)), key=lambda i: means[i]))]
    print("-" * 60)
    print(f"  best CV mean at k={best_k}; 1-SE rule selects k={selected_k} (parsimony).")

    # 4) Refit on full pool at selected k; evaluate ONCE on held-out test.
    X_pool, y_pool = make_lagged_features(pool, args.max_lag)
    X_te, y_te = make_lagged_features(test, args.max_lag)
    scaler = StandardScaler().fit(X_pool)
    model = PLSRegression(n_components=selected_k).fit(scaler.transform(X_pool), y_pool)
    te_pred = model.predict(scaler.transform(X_te)).ravel()
    print("-" * 60)
    print(f"  HELD-OUT TEST  (k={selected_k}, evaluated once)")
    print(f"    R^2  : {r2_score(y_te, te_pred):.4f}")
    print(f"    RMSE : {root_mean_squared_error(y_te, te_pred):.4f}")
    print("-" * 60)
    print("  Compare to single-adjacent-val PLS (k=6): test R^2 = 0.04.")
    print("  A higher/more stable test R^2 here shows honest selection helps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
