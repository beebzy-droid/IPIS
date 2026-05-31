"""Diagnose why held-out test performance collapses while train/val hold.

Pure data analysis -- no modeling, no commit needed. Run from project root:

    python scripts/diagnose_split_shift.py
    python scripts/diagnose_split_shift.py --ref-lag 15 --max-lag 25

Compares the three time-ordered splits along the axes that distinguish the
candidate causes of a train~=val >> test collapse:

  1. TARGET/INPUT DISTRIBUTION SHIFT
     Per-split mean/std/min/max of y and each input. If test y sits at a
     different level/scale than train, a train-calibrated model predicts in
     the wrong range -> R^2 collapses. (Level shift.)

  2. TRANSPORT-DELAY DRIFT  (-> Wang DTDE, adaptive window)
     Best lag for u5 within each split. If train/val peak at ~15 but test
     peaks elsewhere, a fixed-lag model is mis-aligned on test.

  3. RELATIONSHIP / CONCEPT DRIFT  (-> Phase 1B drift detection)
     Correlation of u5(t - ref_lag) with y(t) within each split. If the
     core lagged relationship is strong in train/val but weak in test, the
     input-output mapping itself changed.

Read: a level shift points to target non-stationarity; a lag shift points to
DTDE; a relationship collapse points to concept drift. They can co-occur.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")
INPUT_COLS = ["u1", "u2", "u3", "u4", "u5", "u6", "u7"]
Y_COL = "y"


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _best_lag(u: np.ndarray, y: np.ndarray, max_lag: int) -> tuple[int, float]:
    best_k, best_r = 0, 0.0
    for k in range(max_lag + 1):
        uu = u[: len(u) - k] if k else u
        yy = y[k:] if k else y
        if len(uu) < 10:
            break
        r = _pearson(uu, yy)
        if abs(r) > abs(best_r):
            best_k, best_r = k, r
    return best_k, best_r


def _lagged_corr(u: np.ndarray, y: np.ndarray, lag: int) -> float:
    if lag <= 0:
        return _pearson(u, y)
    if len(u) <= lag + 10:
        return float("nan")
    return _pearson(u[: len(u) - lag], y[lag:])


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnose train/val/test distribution shift.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--ref-lag", type=int, default=15, help="Global best lag for u5.")
    ap.add_argument("--max-lag", type=int, default=25)
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
    segments = {"train": split.train, "val": split.val, "test": split.test}

    print("=" * 64)
    print("1) TARGET distribution per split  (level/scale shift?)")
    print("=" * 64)
    print(f"  {'split':6s}{'n':>6s}{'y_mean':>10s}{'y_std':>9s}{'y_min':>8s}{'y_max':>8s}")
    for name, seg in segments.items():
        y = seg[Y_COL].to_numpy(float)
        print(
            f"  {name:6s}{len(y):>6d}{y.mean():>10.4f}{y.std():>9.4f}{y.min():>8.4f}{y.max():>8.4f}"
        )

    print("-" * 64)
    print("   u5 distribution per split  (input shift?)")
    print(f"  {'split':6s}{'u5_mean':>10s}{'u5_std':>9s}{'u5_min':>8s}{'u5_max':>8s}")
    for name, seg in segments.items():
        u = seg["u5"].to_numpy(float)
        print(f"  {name:6s}{u.mean():>10.4f}{u.std():>9.4f}{u.min():>8.4f}{u.max():>8.4f}")

    print("=" * 64)
    print(f"2) TRANSPORT-DELAY drift  (best lag for u5 in [0,{args.max_lag}])")
    print("=" * 64)
    print(f"  {'split':6s}{'best_k':>8s}{'r':>10s}{'r^2':>10s}")
    for name, seg in segments.items():
        u = seg["u5"].to_numpy(float)
        y = seg[Y_COL].to_numpy(float)
        k, r = _best_lag(u, y, args.max_lag)
        print(f"  {name:6s}{k:>8d}{r:>10.4f}{r * r:>10.4f}")

    print("=" * 64)
    print(f"3) RELATIONSHIP drift  (corr of u5(t-{args.ref_lag}) with y(t))")
    print("=" * 64)
    print(f"  {'split':6s}{'r':>10s}{'r^2':>10s}")
    for name, seg in segments.items():
        u = seg["u5"].to_numpy(float)
        y = seg[Y_COL].to_numpy(float)
        r = _lagged_corr(u, y, args.ref_lag)
        r2 = r * r if np.isfinite(r) else float("nan")
        print(f"  {name:6s}{r:>10.4f}{r2:>10.4f}")
    print("-" * 64)
    print("Read: test y level far from train -> level shift; test best_k far")
    print("from train -> delay drift (DTDE); test r^2 << train r^2 at ref_lag")
    print("-> concept drift. These can co-occur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
