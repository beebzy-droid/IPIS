#!/usr/bin/env python3
"""Evidence for the TEP random-number defect and its replacement (pre-registration Sec. 3D).

Three checks, written to one record:
1. The original generator. TESUB7 in teprob.f computes G <- DMOD(G * 9228907, 2**32) in double
   precision. For the source's own seed and the 57 seeds listed in SUBROUTINE TEINIT, the
   emulation (``generate_tep_modes.legacy_cycle``) gives the settled form G = 2**k m and the period
   2**(30 - k) draws. For a multiplier of 3 mod 8, the odd m split into two cycles, m = 1 or 3
   mod 8 and m = 5 or 7 mod 8; seeds on the same (k, cycle) share one stream at different phases.
2. Draws per simulated hour: a build that counts TESUB7 calls, mode1, the source's own seed,
   10 h. This turns periods in draws into hours.
3. The replacement. The Fortran MRG32k3a that ``generate_tep_modes`` writes in place of TESUB7 is
   compiled with a small driver and compared, draw by draw, with the Python reference
   ``mrg_uniforms`` (200 000 draws of stream 7, alternating the [0, 1) and [-1, 1) forms). Its
   first two outputs from the RngStreams seed (12345, ..., 12345) are recorded as well.

Run next to generate_tep_modes.py, temain_mod.f and teprob.f (for example in WSL):
    python3 tep_rng_check.py --json tep_rng_check.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import generate_tep_modes as g

DEFAULT_SEED = 4651207995


def listed_seeds() -> list[int]:
    """Seed values in the comment lines of teprob.f (e.g. 'C  d03_tr: G=1731738903.D0')."""
    text = (g.HERE / "teprob.f").read_text()
    return sorted({int(m) for m in re.findall(r"(?m)^C.*\bG=(\d+)\.D[0O]", text)})


def settled_state(seed: int, burn: int = 5000) -> int:
    x = float(seed)
    for _ in range(burn):
        x = math.fmod(x * 9228907.0, 4294967296.0)
    return int(x)


def legacy_table() -> list[dict]:
    rows = []
    for seed in [DEFAULT_SEED, *listed_seeds()]:
        k, period = g.legacy_cycle(seed)
        m = settled_state(seed) >> k
        rows.append(
            {"seed": seed, "k": k, "period_draws": period, "cycle": "A" if m % 8 in (1, 3) else "B"}
        )
    return rows


def draws_per_hour(hours: int = 10) -> float:
    """Count TESUB7 calls in a mode1 run with the source's own seed."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        drv = g._driver_source("mode1", *g.MODES["mode1"], src_dir=g.HERE, hours=hours, record_s=60)
        drv = drv.replace("\tCLOSE(UNIT=50)\n", "\tCLOSE(UNIT=50)\n\tPRINT *, 'NCALL', NCALL\n", 1)
        anchor = "      DOUBLE PRECISION XMEAS, XMV"
        drv = drv.replace(anchor, "      INTEGER*8 NCALL\n      COMMON/RCOUNT/NCALL\n" + anchor, 1)
        plant = (g.HERE / "teprob.f").read_text()
        head = "      COMMON/RANDSD/G\n      G=DMOD(G*9228907.D0,4294967296.D0)\n"
        if plant.count(head) != 1:
            raise RuntimeError("expected the original TESUB7 in teprob.f")
        count = "      INTEGER*8 NCALL\n      COMMON/RCOUNT/NCALL\n      NCALL=NCALL+1\n"
        plant = plant.replace(head, "      COMMON/RANDSD/G\n" + count + head.split("\n", 1)[1])
        (tmp_dir / "d.f").write_text(drv)
        (tmp_dir / "p.f").write_text(plant)
        subprocess.run(
            ["gfortran", "-std=legacy", "-w", "d.f", "p.f", "-o", "c"], cwd=tmp, check=True
        )
        out = subprocess.run(["./c"], cwd=tmp, capture_output=True, text=True, check=True).stdout
    calls = int(next(line for line in out.splitlines() if "NCALL" in line).split()[-1])
    return calls / hours


def fortran_draws(state: tuple, n: int, alternate: bool = True) -> list[float]:
    """Compile the Fortran MRG32k3a at ``state`` and return its first ``n`` draws: alternating the
    [-1, 1) form (odd draws) and the [0, 1) form (even draws), or all in the [0, 1) form."""
    odd = "-1" if alternate else "1"
    main = (
        "      PROGRAM T\n      INTEGER J\n      DOUBLE PRECISION TESUB7, X\n"
        f"      DO 10 J = 1, {n}\n        IF (MOD(J,2).EQ.0) THEN\n          X = TESUB7(1)\n"
        f"        ELSE\n          X = TESUB7({odd})\n        ENDIF\n"
        "        WRITE(*,'(ES26.17E3)') X\n 10   CONTINUE\n      END\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "t.f").write_text(main + g._mrg_tesub7(state))
        subprocess.run(["gfortran", "-std=legacy", "-w", "t.f", "-o", "t"], cwd=tmp, check=True)
        out = subprocess.run(["./t"], cwd=tmp, capture_output=True, text=True, check=True).stdout
    return [float(x) for x in out.split()]


def replacement_check(stream: int = 7, n: int = 200_000) -> dict:
    """Compare the compiled Fortran MRG32k3a with the Python reference, draw by draw, and take its
    first output from the RngStreams seed (12345, ..., 12345)."""
    state = g.mrg_stream_state(stream)
    u, _ = g.mrg_uniforms(state, n)
    ref = [x if j % 2 == 0 else 2.0 * x - 1.0 for j, x in zip(range(1, n + 1), u, strict=True)]
    fortran = fortran_draws(state, n)
    mismatches = sum(a != b for a, b in zip(fortran, ref, strict=True))
    return {
        "stream": stream,
        "draws": n,
        "mismatches": mismatches,
        "fortran_first_outputs_seed_12345": fortran_draws(g.MRG_DEFAULT, 2, alternate=False),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="TEP random-number check (pre-registration Sec. 3D)")
    ap.add_argument("--json", default=None, help="write the record to this path")
    args = ap.parse_args()
    table = legacy_table()
    rate = draws_per_hour()
    by_k = Counter(r["k"] for r in table)
    by_cycle = Counter(f"k={r['k']}, cycle {r['cycle']}" for r in table)
    periods_h = {str(k): 2 ** (30 - k) / rate for k in sorted(by_k)}
    check = replacement_check()
    print("draws per simulated hour:", round(rate))
    print(
        "seeds by k:",
        dict(sorted(by_k.items())),
        "| periods (h):",
        {k: round(v, 1) for k, v in periods_h.items()},
    )
    print("seeds by (k, cycle):", dict(sorted(by_cycle.items())))
    print("MRG32k3a Fortran vs Python:", check)
    if args.json:
        stamp = datetime.now(timezone.utc)  # noqa: UP017 (WSL Python may be 3.10)
        version = subprocess.run(["gfortran", "--version"], capture_output=True, text=True)
        doc = {
            "_meta": {
                "generated_utc": stamp.isoformat(timespec="seconds"),
                "python": platform.python_version(),
                "gfortran": version.stdout.splitlines()[0] if version.stdout else None,
                "sha256": {
                    name: hashlib.sha256((g.HERE / name).read_bytes()).hexdigest()
                    for name in ("teprob.f", "temain_mod.f", "generate_tep_modes.py")
                }
                | {
                    "tep_rng_check.py": hashlib.sha256(
                        Path(__file__).resolve().read_bytes()
                    ).hexdigest()
                },
            },
            "draws_per_hour": rate,
            "legacy_period_hours_by_k": periods_h,
            "legacy_seeds_by_k": {str(k): v for k, v in sorted(by_k.items())},
            "legacy_seeds_by_k_and_cycle": dict(sorted(by_cycle.items())),
            "legacy_seeds": table,
            "mrg32k3a_replacement": check,
        }
        Path(args.json).write_text(json.dumps(doc, indent=2))
    return 0 if check["mismatches"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
