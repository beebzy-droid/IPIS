"""Convert the canonical mv-per TEP xlsx datasets to the project CSV format.

One-time helper. Reads the mv-per normal-operation xlsx for modes 1/3/4 via
TEPCanonicalLoader (xmv-k -> XMEAS_k, decimated to the 3-min grid) and writes
them as headerless CSVs (time + 41 XMEAS, no XMV) into an output directory, so
all existing code (tep_baseline.py, the migration) runs on the canonical modes
through the normal TEPLoader -- which now accepts XMEAS-only files.

Usage (from project root, after `git lfs pull` of the mv-per repo):

    python scripts/convert_canonical_tep.py \
        --src ..\\tennessee-eastman-dataset\\simulations \
        --out data\\raw\\tep_canonical

Produces: data/raw/tep_canonical/tep_mode1.csv, tep_mode3.csv, tep_mode4.csv
(gitignored, like all data). Canonical modes: 1 = base 50/50, 3 = 90/10 (G-rich),
4 = 50/50 at max rate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ipis.module1_soft_sensor.data.tep_canonical_loader import TEPCanonicalLoader

# mode -> relative xlsx path under the mv-per simulations dir
CANONICAL_FILES = {
    "mode1": Path("mode_1") / "mode1_normal_500.xlsx",
    "mode3": Path("mode_3") / "mode3_normal_50.xlsx",
    "mode4": Path("mode_4") / "mode4_normal_50.xlsx",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert canonical mv-per TEP xlsx -> CSV.")
    ap.add_argument("--src", type=Path, required=True, help="mv-per simulations/ dir")
    ap.add_argument("--out", type=Path, default=Path("data/raw/tep_canonical"))
    ap.add_argument("--decimate", type=int, default=3, help="1-min -> 3-min grid")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    loader = TEPCanonicalLoader(decimate=args.decimate)
    for mode, rel in CANONICAL_FILES.items():
        xlsx = args.src / rel
        if not xlsx.exists():
            print(f"  {mode}: SKIP (not found: {xlsx})")
            continue
        df = loader.load(xlsx)
        cols = ["time"] + [f"XMEAS_{i}" for i in range(1, 42)]
        out_csv = args.out / f"tep_{mode}.csv"
        df[cols].to_csv(out_csv, header=False, index=False)
        g = df["XMEAS_40"]
        print(
            f"  {mode}: {len(df)} rows -> {out_csv}  "
            f"| G mean {g.mean():.2f} std {g.std():.2f} [{g.min():.1f},{g.max():.1f}]"
        )
    print("Done. Point --data-dir at the output dir to run baseline/migration on canonical modes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
