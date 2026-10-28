"""How much does D-P1.11's Gaussian coverage scaling depend on the tails? (pre-registration A.1
and A.9, 2026-10-28; reads the dry-run evidence, run from the repository root.)

D-P1.11 scales each run's baseline run-median width to the compensated loop's coverage in that
run by z((1 + c_loop) / 2) / z((1 + c_baseline) / 2). This script repeats the coverage-matched
comparison of the dry run (docs/paper/evidence/baseline_dryrun_phi05.json and _phi09.json,
conformal PID at its D-P1.11 selection, and SPCI) with the same factor computed from t5, t3 and
Laplace quantiles. Under heavier tails the Gaussian factor under-corrects in both directions, so
it favours whichever method covers less.

Run:
    set PYTHONPATH=src
    python scripts\\pilots\\coverage_scaling_tails.py
It prints a table and writes docs/paper/evidence/coverage_scaling_tails.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scipy import stats

EVIDENCE = Path("docs/paper/evidence")
DISTS = {"gaussian": stats.norm(), "t5": stats.t(5), "t3": stats.t(3), "laplace": stats.laplace()}
METHODS = {
    "pid_qr": "d_p1_11",
    "pid_theta": "d_p1_11",
    "pid_matched": "d_p1_11",
    "spci": None,
}


def compare(loop: list[dict], runs: list[dict]) -> dict:
    lw = [r["median_width"] for r in loop]
    lc = [r["coverage"] for r in loop]
    bw = [r["median_width"] for r in runs]
    bc = [r["coverage"] for r in runs]
    out = {
        "coverage": sum(bc) / len(bc),
        "loop_coverage": sum(lc) / len(lc),
        "unscaled_change": sum(bw) / sum(lw) - 1.0,
    }
    for name, dist in DISTS.items():
        scaled = [
            w * dist.ppf((1 + cl) / 2) / dist.ppf((1 + cb) / 2)
            for w, cb, cl in zip(bw, bc, lc, strict=True)
        ]
        out[name] = {
            "change": sum(scaled) / sum(lw) - 1.0,
            "narrower_runs": int(sum(s < w for s, w in zip(scaled, lw, strict=True))),
        }
    return out


def main() -> int:
    result: dict = {}
    for tag in ("phi05", "phi09"):
        d = json.loads((EVIDENCE / f"baseline_dryrun_{tag}.json").read_text())
        row = {}
        for key, sel in METHODS.items():
            runs = d[key][sel]["runs"] if sel else d[key]["runs"]
            row[key] = compare(d["loop"]["runs"], runs)
            r = row[key]
            cells = "; ".join(
                f"{n} {100 * r[n]['change']:+.1f} % ({r[n]['narrower_runs']}/5)" for n in DISTS
            )
            print(
                f"phi {d['phi']} {key:11s} coverage {r['coverage']:.3f} (loop "
                f"{r['loop_coverage']:.3f}), unscaled {100 * r['unscaled_change']:+.1f} % | {cells}"
            )
        result[str(d["phi"])] = row
    if "--no-json" not in sys.argv:
        from ipis.shared.evidence import dump_evidence

        print("evidence ->", dump_evidence("coverage_scaling_tails", result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
