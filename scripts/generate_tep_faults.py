#!/usr/bin/env python3
"""Generate the canonical TEP fault-detection dataset (d00-d20) for IPIS Phase 2C.

Compiles the Russell/Chiang/Braatz closed-loop Tennessee Eastman FORTRAN (the code
behind the classic d00-d21 datasets) and runs each of the 20 Downs & Vogel process
disturbances (IDV 1-20) as its own 48 h scenario with the fault injected at 8 h
(sample 160 on the 3-min measurement grid), plus a fault-free run (d00). This is
the standard FDD benchmark layout: 960 samples/run, fault onset at sample 160.

WHY THIS SIMULATOR (same provenance as generate_tep_modes.py). The Russell/Braatz
closed-loop code is the most-cited source for TEP fault data, compiles/runs headless
under gfortran, and is fully reproducible. This version exposes IDV(1..20) (the
canonical Downs & Vogel disturbances); IDV-21 (valve stiction) is not present.

REQUIREMENTS
  - gfortran (`sudo apt-get install gfortran`; Windows: WSL or MinGW)
  - numpy
  - temain_mod.f and teprob.f in THIS directory
    (git clone https://github.com/camaramm/tennessee-eastman-profBraatz)

OUTPUT  data/raw/tep/fdd/d00.csv .. d20.csv
  Each: 960 rows, 54 columns: time(h), XMEAS_1..41, XMV_1..12 (no header).
  d00 = fault-free baseline; d{ff} = IDV ff active from sample 160 onward.
  IDV-3 / 9 / 15 are the known near-undetectable faults (no clear shift in the
  measurements) -- expected to score ~0% detection for ANY detector.

    cd scripts && git clone https://github.com/camaramm/tennessee-eastman-profBraatz tmp \\
        && cp tmp/temain_mod.f tmp/teprob.f . && rm -rf tmp
    cd .. && python scripts/generate_tep_faults.py
"""

from __future__ import annotations

import pathlib
import subprocess

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "raw" / "tep" / "fdd"  # repo: scripts/ -> ../data/raw/tep/fdd
NPTS = 172800  # 48 h at DELTAT = 1 s -> 960 samples at the 180 s output grid
FAULT_START = 28800  # 8 h -> fault onset at sample 160
N_IDV = 20


def _driver_source(fault: int) -> str:
    """Patch the Russell/Braatz driver: inject IDV `fault` at 8 h + single-CSV output."""
    s = (HERE / "temain_mod.f").read_text()
    s = s.replace("      NPTS = 172800", f"      NPTS = {NPTS}")
    block = "         IF (I.GE.SSPTS) THEN\n                 IDV(12)=1\n          ENDIF"
    if s.count(block) != 1:
        raise RuntimeError("expected exactly one IDV(12) step block in temain_mod.f")
    inject = (
        "C        d00: fault-free"
        if fault == 0
        else f"         IF (I.GE.{FAULT_START}) THEN\n                 IDV({fault})=1\n          ENDIF"
    )
    s = s.replace(block, inject, 1)
    # single-CSV output (short filename keeps the OPEN within Fortran's column 72)
    o0 = s.index("\tOPEN(UNIT=111,FILE=")
    o1 = s.index("\n", s.index("OPEN(UNIT=2121,")) + 1
    s = s[:o0] + f"\tOPEN(UNIT=50,FILE='d{fault:02d}.csv',STATUS='unknown')\n" + s[o1:]
    s = s.replace(
        " \tTEST4=MOD(I,180)\t\n\tIF (TEST4.EQ.0) THEN\n\t\tCALL OUTPUT\n"
        "      \t\tWRITE(111,111) I\n 111  \t\tFORMAT(1X,I6)\n     \tENDIF",
        " \tTEST4=MOD(I,180)\n\tIF (TEST4.EQ.0) THEN\n\t\tCALL OUTPUT\n"
        "\t\tWRITE(50,500) TIME,(XMEAS(J),J=1,41),(XMV(J),J=1,12)\n"
        " 500  \t\tFORMAT(F12.5,53(',',E15.7))\n     \tENDIF",
    )
    c0 = s.index(" \tCLOSE(UNIT=111)")
    c1 = s.index("\n", s.index("CLOSE(UNIT=2121)")) + 1
    s = s[:c0] + "\tCLOSE(UNIT=50)\n" + s[c1:]
    return s


def main() -> None:
    for need in ("temain_mod.f", "teprob.f"):
        if not (HERE / need).exists():
            raise SystemExit(f"missing {need}: clone tennessee-eastman-profBraatz into {HERE}")
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Generating d00-d{N_IDV:02d} -> {OUT}")
    for f in range(N_IDV + 1):
        src = HERE / f"te_fault_{f:02d}.f"
        src.write_text(_driver_source(f))
        subprocess.run(
            [
                "gfortran",
                "-std=legacy",
                "-w",
                str(src),
                str(HERE / "teprob.f"),
                "-o",
                str(HERE / f"te_fault_{f:02d}"),
            ],
            check=True,
        )
        subprocess.run([str(HERE / f"te_fault_{f:02d}")], cwd=HERE, check=True)
        (HERE / f"d{f:02d}.csv").replace(OUT / f"d{f:02d}.csv")
        d = np.loadtxt(OUT / f"d{f:02d}.csv", delimiter=",")
        pre, post = d[:160, 1:23], d[160:, 1:23]
        z = np.abs(post.mean(0) - pre.mean(0)) / (pre.std(0) + 1e-9)
        tag = "fault-free" if f == 0 else f"IDV {f}"
        print(
            f"  d{f:02d} {tag:<12}: rows {d.shape[0]} cols {d.shape[1]} | "
            f"max z-shift {z.max():4.1f}  #vars|z|>3 {(z > 3).sum():2d}"
        )
    for p in list(HERE.glob("te_fault_*")):
        p.unlink()
    print("done.")


if __name__ == "__main__":
    main()
