"""Diagnose generalization vs model complexity (PLS components).

Pure diagnostic -- NOT a model-selection tool. Run from project root:

    python scripts/diagnose_complexity.py
    python scripts/diagnose_complexity.py --max-lag 17 --max-components 20

Reports train/val/test R^2 for each n_components from 1 upward. The purpose
is to UNDERSTAND generalization under the test-period regime shift, after the
finding that the dominant physical feature (u5 at lag-15) predicts test well
(r^2=0.62) while the full 126-feature PLS scored test R^2=0.04.

Expected signature if the kitchen-sink model overfits to the train+val regime:
    - val R^2 rises with components (val shares train's regime -> rewards them).
    - test R^2 peaks at LOW complexity (1-3) then degrades or stays low.

HONESTY GUARDRAIL: do not select n_components by test R^2 -- that is
test-set leakage in model selection. This curve is for diagnosis only. The
legitimate responses are parsimony/regularization, regime-aware validation,
and physics-grounding for robustness.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.features.lagged import make_lagged_features

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def main() -> int:
    ap = argparse.ArgumentParser(description="PLS generalization vs complexity (diagnostic).")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--max-lag", type=int, default=17)
    ap.add_argument("--max-components", type=int, default=20)
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
    X_tr, y_tr = make_lagged_features(split.train, args.max_lag)
    X_va, y_va = make_lagged_features(split.val, args.max_lag)
    X_te, y_te = make_lagged_features(split.test, args.max_lag)
    x_scaler = StandardScaler().fit(X_tr)
    Xtr, Xva, Xte = (x_scaler.transform(X) for X in (X_tr, X_va, X_te))

    print("=" * 56)
    print("PLS generalization vs complexity  (DIAGNOSTIC ONLY)")
    print("=" * 56)
    print(f"  max_lag={args.max_lag}  features={X_tr.shape[1]}")
    print(f"  {'k':>3s}{'train_R2':>11s}{'val_R2':>10s}{'test_R2':>10s}")
    max_k = min(args.max_components, X_tr.shape[1])
    best_val_k, best_val = 1, -1e9
    for k in range(1, max_k + 1):
        m = PLSRegression(n_components=k).fit(Xtr, y_tr)
        tr = r2_score(y_tr, m.predict(Xtr).ravel())
        va = r2_score(y_va, m.predict(Xva).ravel())
        te = r2_score(y_te, m.predict(Xte).ravel())
        if va > best_val:
            best_val_k, best_val = k, va
        print(f"  {k:>3d}{tr:>11.4f}{va:>10.4f}{te:>10.4f}")
    print("-" * 56)
    print(f"  val-selected k = {best_val_k} (the honest choice; do NOT pick by test).")
    print("  If test_R2 peaks at low k and val_R2 keeps rising, the model is")
    print("  overfitting to the train+val regime -> parsimony / physics-grounding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
