"""Build degradation HI trends for every FEMTO bearing found on disk, then point at
the RUL evaluation.

Auto-discovers data/raw/femto/<set>/Bearing*/ across Learning_set, Test_set and
Full_Test_Set, runs build_femto_hi_trend.py for each (robust baseline + fpt column),
and prints a one-line FPT/arc summary table so early-degrading or non-monotone
bearings are easy to spot before the eval. Then run scripts/run_femto_rul.py.

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


def main() -> int:
    dirs = sorted(d for d in glob.glob(str(ROOT / "*" / "Bearing*")) if Path(d).is_dir())
    if not dirs:
        print(f"[ERROR] no bearings found under {ROOT}/<set>/Bearing*")
        return 1
    print(f"Found {len(dirs)} bearing folders under {ROOT}\n")
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
