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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bearing", help="path under data/raw/femto/, e.g. Learning_set/Bearing1_1")
    ap.add_argument(
        "--healthy-frac",
        type=float,
        default=0.2,
        help="fraction of early snapshots used as the healthy baseline",
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

    n_healthy = max(2, int(args.healthy_frac * n))
    model = HealthIndexModel.fit(feats[:n_healthy], TIME_FEATURE_NAMES)
    print(
        f"Healthy fit   : first {n_healthy} snapshots; "
        f"WARN T2={model.warn_t2:.1f}  ALARM T2={model.alarm_t2:.1f}"
    )
    if n_healthy < 10 * feats.shape[1]:
        print(
            f"[WARN] healthy baseline ({n_healthy}) < 10x features ({feats.shape[1]}); "
            f"covariance may be under-determined -> noisy T2. Real FEMTO bearings have "
            f"ample snapshots; for short runs raise --healthy-frac."
        )

    rows = []
    flags = []
    for i in range(n):
        t2 = model.t2(feats[i])
        flag = model.flag(feats[i]).value
        flags.append(flag)
        rows.append(
            {
                "index": i,
                "elapsed_s": f"{bearing.elapsed_s(i):.1f}",
                "rul_s": f"{bearing.time_to_failure_s(i):.1f}",
                "t2": f"{t2:.4f}",
                "health_score": f"{model.health_score(feats[i]):.4f}",
                "flag": flag,
            }
        )

    out = Path(args.out) if args.out else Path("data/processed") / f"femto_hi_{bearing.name}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def first_persistent(levels: set[str]) -> int | None:
        """First index where `flag` stays in `levels` for `args.persist` snapshots."""
        run = 0
        for i, fl in enumerate(flags):
            run = run + 1 if fl in levels else 0
            if run >= args.persist:
                return i - args.persist + 1
        return None

    def lead(idx):
        return (
            "n/a"
            if idx is None
            else f"snapshot {idx} (RUL {bearing.time_to_failure_s(idx) / 60:.1f} min)"
        )

    warn_onset = first_persistent({"warn", "alarm"})
    alarm_onset = first_persistent({"alarm"})
    print(f"WARN onset    : {lead(warn_onset)}  (>= {args.persist} consecutive)")
    print(f"ALARM onset   : {lead(alarm_onset)}  (>= {args.persist} consecutive)")
    print(f"End T2        : {float(rows[-1]['t2']):.1f}  (healthy fit median ~ {feats.shape[1]})")
    print(f"Wrote         : {out}  ({n} rows; raw per-snapshot flags)  -> feeds Phase 2B RUL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
