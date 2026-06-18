"""Build a FEMTO degradation health-index trend for one run-to-failure bearing.

Fits the Hotelling T^2 health index on the bearing's early life (assumed healthy),
then rolls it forward over the whole run to produce a rising T^2 / falling
health_score trend with OK/WARN/ALARM flags, alongside the RUL ground truth. The
output CSV (index, elapsed_s, rul_s, t2, health_score, flag) is the (HI, RUL)
table that the Phase 2B RUL model + one-sided conformal bound consume.

Run from repo root after placing FEMTO data in data/raw/femto/:

    set PYTHONPATH=src
    python scripts/build_femto_hi_trend.py Learning_set/Bearing1_1
    python scripts/build_femto_hi_trend.py Full_Test_Set/Bearing1_3 --healthy-frac 0.2

Uses the horizontal channel (standard for FEMTO RUL) and the time-domain feature
vector (FEMTO has no verified defect frequencies; see femto_loader docstring).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from ipis.module2_pdm.data.femto_loader import load_femto_bearing
from ipis.module2_pdm.features.vibration_features import (
    TIME_FEATURE_NAMES,
    time_feature_vector,
)
from ipis.module2_pdm.health.health_index import HealthIndexModel
from ipis.module2_pdm.rul.degradation import (
    robust_baseline_window,
    robust_first_prediction_time,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bearing", help="path under data/raw/femto/, e.g. Learning_set/Bearing1_1")
    ap.add_argument(
        "--healthy-frac",
        type=float,
        default=None,
        help="force legacy first-fraction baseline (default: robust quietest-window)",
    )
    ap.add_argument("--channel", choices=["horizontal", "vertical"], default="horizontal")
    ap.add_argument(
        "--persist",
        type=int,
        default=3,
        help="consecutive WARN/ALARM snapshots required to call an onset",
    )
    ap.add_argument("--out", default=None, help="output CSV path")
    args = ap.parse_args()

    bdir = Path("data/raw/femto") / args.bearing
    if not bdir.is_dir():
        print(f"[ERROR] not found: {bdir}")
        return 1

    bearing = load_femto_bearing(bdir)
    n = bearing.n_snapshots
    print(
        f"Bearing       : {bearing.name}  (condition {bearing.condition}, "
        f"{bearing.rpm} rpm / {bearing.load_n} N)"
    )
    print(
        f"Snapshots     : {n}  (~{bearing.elapsed_s(n - 1) / 60:.1f} min run, "
        f"{bearing.interval_s:.0f}s cadence)"
    )

    # Feature matrix over the whole run (horizontal or vertical channel).
    ch = 0 if args.channel == "horizontal" else 1
    feats = np.vstack([time_feature_vector(bearing.snapshot(i)[ch]) for i in range(n)])

    # Robust healthy baseline: the quietest adequately-sized early window (auto-skips
    # run-in transients and degradation onset). --healthy-frac forces the legacy
    # first-fraction window for comparison.
    if args.healthy_frac is not None:
        bstart, bw = 0, max(2, int(args.healthy_frac * n))
        baseline_desc = f"first {bw} (frac {args.healthy_frac})"
    else:
        bstart, bw = robust_baseline_window(feats)
        baseline_desc = f"snapshots {bstart}-{bstart + bw} (quietest window)"
    model = HealthIndexModel.fit(feats[bstart : bstart + bw], TIME_FEATURE_NAMES)
    print(
        f"Healthy fit   : {baseline_desc}; "
        f"WARN T2={model.warn_t2:.1f}  ALARM T2={model.alarm_t2:.1f}"
    )
    if bw < 10 * feats.shape[1]:
        print(
            f"[WARN] baseline ({bw}) < 10x features ({feats.shape[1]}); "
            f"covariance may be under-determined -> noisy T2."
        )

    t2 = np.array([model.t2(feats[i]) for i in range(n)])
    fpt = robust_first_prediction_time(
        t2, baseline_end=bstart + bw, warn_limit=model.warn_t2, persist=args.persist
    )
    fpt_val = -1 if fpt is None else fpt

    rows = [
        {
            "index": i,
            "elapsed_s": f"{bearing.elapsed_s(i):.1f}",
            "rul_s": f"{bearing.time_to_failure_s(i):.1f}",
            "t2": f"{t2[i]:.4f}",
            "health_score": f"{model.health_score(feats[i]):.4f}",
            "flag": model.flag(feats[i]).value,
            "fpt": fpt_val,
        }
        for i in range(n)
    ]

    out = Path(args.out) if args.out else Path("data/processed") / f"femto_hi_{bearing.name}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def lead(idx):
        return (
            "n/a"
            if idx is None
            else f"snapshot {idx} (RUL {bearing.time_to_failure_s(idx) / 60:.1f} min)"
        )

    print(f"FPT (onset)   : {lead(fpt)}  (after baseline, >= {args.persist} consecutive)")
    print(f"End T2        : {t2[-1]:.1f}  (healthy fit median ~ {feats.shape[1]})")
    print(f"Wrote         : {out}  ({n} rows incl. fpt col)  -> feeds Phase 2B RUL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
