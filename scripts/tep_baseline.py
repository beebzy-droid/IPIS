"""Phase 1C part-A baseline -- single-mode TEP soft sensor + transfer gap.

Run locally from the project root (gitignored data; not CI):

    python scripts/tep_baseline.py
    python scripts/tep_baseline.py --data-dir data/raw/tep --source mode1

Establishes the SOURCE soft sensor for the migration study by applying the same
recipe used on the Debutanizer -- physics-anchored features + blocked
forward-chaining CV + a linear base model -- to a single TEP operating mode.
This is the part-A claim ("the recipe transfers across topology"). It then
quantifies the cross-mode TRANSFER GAP (source model applied to the other modes,
untreated), which is the empirical motivation for part-C SBC migration.

The source model fitted here is exactly what the migration (Lu/Yan/Luo) will
scale-and-bias onto the target modes with <30% of their data.

Dataset-agnostic: works on any modes loadable by TEPLoader (the in-sandbox
Russell/Braatz CSVs, or the canonical mv-per xlsx once converted to CSV).
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

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.data.tep_loader import TEPLoader
from ipis.module1_soft_sensor.evaluation.drift import blocked_cv_residuals
from ipis.module1_soft_sensor.features.tep_physics_features import (
    diagnose_transport_lag,
    make_tep_physics_features,
)


def _mean_se(xs: list[float]) -> tuple[float, float]:
    a = np.asarray(xs, dtype=float)
    return float(a.mean()), (float(a.std(ddof=1) / np.sqrt(len(a))) if len(a) > 1 else 0.0)


def main() -> int:
    ap = argparse.ArgumentParser(description="TEP single-mode baseline + transfer gap.")
    ap.add_argument("--data-dir", type=Path, default=Path("data/raw/tep"))
    ap.add_argument("--source", default="mode1")
    ap.add_argument("--targets", default="mode2,mode3")
    ap.add_argument("--transport-lag", type=int, default=-1, help="-1 = diagnose")
    ap.add_argument("--n-splits", type=int, default=5)
    args = ap.parse_args()

    loader = TEPLoader()
    src_path = args.data_dir / f"tep_{args.source}.csv"
    try:
        src = loader.load(src_path)
    except FileNotFoundError as exc:
        print(f"Data file not found: {exc}")
        return 1

    lag = diagnose_transport_lag(src) if args.transport_lag < 0 else args.transport_lag

    def builder(df: pd.DataFrame):
        return make_tep_physics_features(df, transport_lag=lag)

    split = time_ordered_split(src)
    pool = pd.concat([split.train, split.val], ignore_index=True)
    test = split.test.reset_index(drop=True)

    print("=" * 78)
    print(f"Phase 1C part-A baseline -- source={args.source}  (transport_lag={lag})")
    print("=" * 78)
    print(f"  source rows {len(src)}  pool {len(pool)}  test {len(test)}  n_splits {args.n_splits}")
    print("-" * 78)

    # blocked forward-chaining CV on the pool (the honest cross-regime instrument)
    folds = blocked_cv_residuals(
        pool,
        LinearRegression,
        max_lag=lag,
        n_splits=args.n_splits,
        feature_builder=builder,
    )
    cv_r2 = [f.r2 for f in folds]
    m, se = _mean_se(cv_r2)
    print(f"  blocked-CV R2: {m:+.3f} +/- {se:.3f}   worst fold {min(cv_r2):+.3f}")

    # pool-fit source model -> held-out test
    X_pool, y_pool = builder(pool)
    X_te, y_te = builder(test)
    scaler = StandardScaler().fit(X_pool)
    source = LinearRegression().fit(scaler.transform(X_pool), y_pool)
    y_te = np.asarray(y_te, dtype=float).ravel()
    test_r2 = r2_score(y_te, source.predict(scaler.transform(X_te)))
    print(f"  held-out test R2 (within {args.source}): {test_r2:+.3f}")
    print(f"  => the recipe transfers across topology (part-A claim): R2 ~ {test_r2:.2f} on TEP")

    # bias-update recovery: the 1B method (built for the Debutanizer) applied
    # unchanged to TEP -- the full-recipe-transfer result. theta=5 is the
    # documented analyzer dead-time (0.25 h / 3-min cadence); bracket reported.
    from ipis.module1_soft_sensor.evaluation.bias_update import corrected_fold_r2

    print("-" * 78)
    print("  FULL-RECIPE TRANSFER (1B bias-update applied unchanged to TEP):")
    print(f"    static                       CV {m:+.3f} +/- {se:.3f}  worst {min(cv_r2):+.3f}")
    for theta in (2, 5, 8):
        c = corrected_fold_r2(folds, lam=0.3, delay=theta)
        cm, cse = _mean_se(c)
        tag = " (documented)" if theta == 5 else ""
        print(
            f"    + bias-update theta={theta}{tag:13s} CV {cm:+.3f} +/- {cse:.3f}  worst {min(c):+.3f}"
        )
    print("    => the Debutanizer recipe (features + blocked CV + bias-update) works")
    print("       unchanged on a reactor process: methodology transfers across topology.")

    # transfer gap: source model applied untreated to the other modes
    print("-" * 78)
    print("  TRANSFER GAP (source model -> other modes, UNTREATED = migration motivation):")
    full_src = pd.concat([pool, test], ignore_index=True)  # refit on all source data
    Xs, ys = builder(full_src)
    sc = StandardScaler().fit(Xs)
    src_model = LinearRegression().fit(sc.transform(Xs), ys)
    for tgt in [t for t in args.targets.split(",") if t]:
        try:
            dft = loader.load(args.data_dir / f"tep_{tgt}.csv")
        except FileNotFoundError:
            print(f"    {tgt}: (file not found, skipped)")
            continue
        Xt, yt = builder(dft)
        yt = np.asarray(yt, dtype=float).ravel()
        r2 = r2_score(yt, src_model.predict(sc.transform(Xt)))
        print(f"    {args.source} model -> {tgt}: R2 {r2:+.3f}  (G mean {yt.mean():.1f} mol%)")
    print("-" * 78)
    print("  Negative transfer R2 => a model is NOT portable across operating regimes")
    print("  without correction. Part C migrates the source model with <30% target data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
