"""Phase 1C migration -- data-fraction sweep (Lu OSBC; Yan/Luo added incrementally).

Run from the project root (gitignored data; not CI):

    python scripts/tep_migration.py
    python scripts/tep_migration.py --data-dir data/raw/tep --source mode1 --targets mode2,mode3

Trains the source soft sensor on the source mode, then for each target mode runs
the data-fraction sweep: migrated (source + Lu OSBC) vs from-scratch (same class)
vs from-scratch (generic 112-feature lagged), all on a held-out target test block.
The headline metric is the crossover -- the smallest target-data fraction at
which the migrated model matches a from-scratch model trained on 100% of the
target pool.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.data.tep_loader import TEPLoader
from ipis.module1_soft_sensor.features.lagged import make_lagged_features
from ipis.module1_soft_sensor.features.tep_physics_features import (
    diagnose_transport_lag,
    make_tep_physics_features,
)
from ipis.module1_soft_sensor.migration.sbc import LuOSBC
from ipis.module1_soft_sensor.migration.sweep import data_fraction_sweep

TEP_FAST_INPUTS = [f"XMEAS_{i}" for i in range(1, 23)]
MIGRATORS = {"osbc": LuOSBC}  # yan, luo added as implemented


def main() -> int:
    ap = argparse.ArgumentParser(description="TEP regime migration data-fraction sweep.")
    ap.add_argument("--data-dir", type=Path, default=Path("data/raw/tep"))
    ap.add_argument("--source", default="mode1")
    ap.add_argument("--targets", default="mode2,mode3")
    ap.add_argument("--method", default="osbc", choices=sorted(MIGRATORS))
    ap.add_argument("--transport-lag", type=int, default=-1)
    ap.add_argument("--generic-lag", type=int, default=3)
    ap.add_argument("--fractions", default="0.05,0.1,0.2,0.3,0.5,1.0")
    args = ap.parse_args()
    fractions = [float(x) for x in args.fractions.split(",")]

    loader = TEPLoader()
    try:
        src = loader.load(args.data_dir / f"tep_{args.source}.csv")
    except FileNotFoundError as exc:
        print(f"Data file not found: {exc}")
        return 1

    lag = diagnose_transport_lag(src) if args.transport_lag < 0 else args.transport_lag

    def phys(df: pd.DataFrame):
        return make_tep_physics_features(df, transport_lag=lag)

    def generic(df: pd.DataFrame):
        return make_lagged_features(
            df, max_lag=args.generic_lag, input_cols=TEP_FAST_INPUTS, target_col="y"
        )

    # source model on ALL source-mode data
    X_src, y_src = phys(src)
    scaler = StandardScaler().fit(X_src)
    src_model = LinearRegression().fit(scaler.transform(X_src), np.asarray(y_src).ravel())

    def source_predict(df: pd.DataFrame) -> np.ndarray:
        X, _ = phys(df)
        return src_model.predict(scaler.transform(X))

    migrator = MIGRATORS[args.method]
    print("=" * 78)
    print(f"Phase 1C migration sweep -- method={args.method}  source={args.source}  lag={lag}")
    print("=" * 78)

    for tgt in [t for t in args.targets.split(",") if t]:
        try:
            dft = loader.load(args.data_dir / f"tep_{tgt}.csv")
        except FileNotFoundError:
            print(f"\n{tgt}: (file not found, skipped)")
            continue
        sp = time_ordered_split(dft)
        pool = pd.concat([sp.train, sp.val], ignore_index=True)
        test = sp.test.reset_index(drop=True)
        res = data_fraction_sweep(
            pool,
            test,
            source_predict,
            phys,
            migrator,
            fractions,
            same_class_factory=LinearRegression,
            generic_builder=generic,
            generic_factory=LinearRegression,
        )
        print(f"\n=== TARGET {tgt} ===")
        print(res.summary())

    print("\n" + "-" * 78)
    print("  migrated >= from-scratch-100% at f<30% would confirm the <30%-data claim.")
    print("  OSBC is the floor; Yan functional SBC + Luo matrix SBC handle the")
    print("  input-dependent regime differences OSBC cannot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
