"""Debutanizer transport-lag provenance (M1 audit A9, reviewer R4.5).

Scans r(k) = corr(driver_{t-k}, y_t) for k = 0..max_lag on the TRAINING POOL ONLY
(train + val of ``time_ordered_split``); the 360-sample test block is never read. Emits the
full profile as provenance-stamped evidence, so the lag used downstream is reproducible from
the repository instead of being a hard-coded constant.

    set PYTHONPATH=src
    python scripts\\diagnose_debutanizer_lag.py --json
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def lag_profile(u: np.ndarray, y: np.ndarray, max_lag: int) -> np.ndarray:
    """Pearson r between the driver lagged by k and the target, for k = 0..max_lag."""
    return np.array(
        [
            float(np.corrcoef(u if k == 0 else u[:-k], y if k == 0 else y[k:])[0, 1])
            for k in range(max_lag + 1)
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Debutanizer lag scan on the training pool only")
    ap.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="debutanizer data file (default matches bias_update_eval.py)",
    )
    ap.add_argument("--driver", default="u5")
    ap.add_argument("--target", default="y")
    ap.add_argument("--max-lag", type=int, default=40)
    ap.add_argument("--json", action="store_true", help="dump evidence to docs/paper/evidence/")
    args = ap.parse_args()

    import pandas as pd

    from ipis.module1_soft_sensor.data.loaders import DebutanizerLoader
    from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split

    df = DebutanizerLoader().load(args.path)
    split = time_ordered_split(df)
    pool = pd.concat([split.train, split.val], ignore_index=True)
    r = lag_profile(
        pool[args.driver].to_numpy(float), pool[args.target].to_numpy(float), args.max_lag
    )
    k = int(np.argmax(np.abs(r)))
    print(f"pool n={len(pool)}; test n={len(split.test)} not read")
    for i, v in enumerate(r):
        print(f"  lag {i:2d}  r={v:+.3f}  r2={v * v:.3f}{'  <- max' if i == k else ''}")
    print(
        f"argmax |r| at lag {k}: r={r[k]:+.3f}, r2={r[k] ** 2:.3f}, interior={0 < k < args.max_lag}"
    )
    if args.json:
        from ipis.shared.evidence import dump_evidence

        payload = {
            "driver": args.driver,
            "target": args.target,
            "max_lag": args.max_lag,
            "n_pool": len(pool),
            "n_test_unread": len(split.test),
            "r": r.tolist(),
            "argmax_lag": k,
            "r_at_argmax": float(r[k]),
            "interior": bool(0 < k < args.max_lag),
        }
        print("evidence ->", dump_evidence("debutanizer_lag_scan", payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
