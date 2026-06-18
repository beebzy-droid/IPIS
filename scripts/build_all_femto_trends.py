"""Build degradation HI trends for every run-to-failure FEMTO bearing on disk.

Auto-discovers data/raw/femto/<set>/Bearing*/ but ONLY for the run-to-failure sets
(Learning_set, Full_Test_Set). Test_set is deliberately skipped: its bearings are
TRUNCATED (the PHM-2012 challenge cuts them before failure and withholds the true
RUL), so last-snapshot != failure and the RUL ground truth our pipeline assumes is
invalid for them. They also share bearing names with Full_Test_Set, which would
overwrite the correct CSVs (keyed by bearing name).

Runs build_femto_hi_trend.py for each (robust baseline + fpt column) and prints a
one-line FPT/arc summary so early-degrading / non-monotone bearings are easy to
spot before the eval. Then run scripts/run_femto_rul.py.

    set PYTHONPATH=src
    python scripts/build_all_femto_trends.py
    python scripts/run_femto_rul.py
"""

from __future__ import annotations

import glob
import subprocess
import sys
from pathlib import Path

ROOT = Path("data/raw/femto")
# run-to-failure sets only; Test_set is truncated (no valid failure-time ground truth)
RUN_TO_FAILURE_SETS = {"Learning_set", "Full_Test_Set"}


def main() -> int:
    dirs = sorted(
        d
        for d in glob.glob(str(ROOT / "*" / "Bearing*"))
        if Path(d).is_dir() and Path(d).parts[-2] in RUN_TO_FAILURE_SETS
    )
    if not dirs:
        print(
            f"[ERROR] no run-to-failure bearings under {ROOT}/{{Learning_set,Full_Test_Set}}/Bearing*"
        )
        return 1
    skipped = sorted(
        Path(d).parts[-2]
        for d in glob.glob(str(ROOT / "*" / "Bearing*"))
        if Path(d).is_dir() and Path(d).parts[-2] not in RUN_TO_FAILURE_SETS
    )
    print(f"Found {len(dirs)} run-to-failure bearing folders under {ROOT}")
    if skipped:
        print(f"Skipped {len(skipped)} truncated Test_set bearings (no valid RUL ground truth)\n")
    ok, failed = 0, []
    for d in dirs:
        sub = "/".join(Path(d).parts[-2:])  # e.g. Learning_set/Bearing1_1
        r = subprocess.run(
            [sys.executable, "scripts/build_femto_hi_trend.py", sub],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            ok += 1
            fpt_line = next((ln for ln in r.stdout.splitlines() if ln.startswith("FPT")), "")
            print(f"[ok]  {sub:<26} {fpt_line.strip()}")
        else:
            failed.append(sub)
            print(
                f"[FAIL] {sub}: {r.stderr.strip().splitlines()[-1] if r.stderr else 'see output'}"
            )
    print(
        f"\nBuilt {ok}/{len(dirs)} trends -> data/processed/. "
        f"{'Failures: ' + ', '.join(failed) if failed else 'No failures.'}"
    )
    print(
        "Next: python scripts/run_femto_rul.py  "
        "(exclude near-0 / non-monotone bearings via EXCLUDE in that script)."
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
