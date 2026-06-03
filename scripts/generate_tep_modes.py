#!/usr/bin/env python3
"""Reproducible generator for the IPIS Phase-1C TEP multimode dataset.

Provenance of record for the TEP data. Compiles the canonical closed-loop
Tennessee Eastman simulator of Russell, Chiang & Braatz (the FORTRAN behind the
classic d00-d21 datasets) and generates three operating-point regimes for the
within-TEP migration study (Option C).

WHY THIS SIMULATOR. COSTEP (Simulink) was abandoned after a non-reproducible
reactor-pressure startup trip we could not fix without interactive access. The
Russell/Braatz closed-loop code is more cited for TEP data generation, is stable
out of the box, and compiles/runs headless under gfortran -- so the data is fully
reproducible on any Linux/WSL box with a Fortran compiler.

REQUIREMENTS
  - gfortran (e.g. `sudo apt-get install gfortran`; Windows: via WSL or MinGW)
  - the Russell/Braatz sources `temain_mod.f` and `teprob.f` in the same dir
    (git clone https://github.com/camaramm/tennessee-eastman-profBraatz)
  - numpy

WHAT IT PRODUCES
  tep_mode1.csv, tep_mode2.csv, tep_mode3.csv
  Each: 2000 rows (100 h at the 3-min TEP measurement cadence), 54 columns:
        time(h), XMEAS_1..41, XMV_1..12   (no header)

REGIME DESIGN (validated; see stats printed at the end of a run)
  The G/H split is set by the reactor-feed composition controllers:
    SETPT(14) -> reactor-feed D mol% (XMEAS 26), D -> product G
    SETPT(15) -> reactor-feed E mol% (XMEAS 27), E -> product H
  Three regimes on the HIGH-G side (which lowers reactor pressure -> safe margin;
  low-G setpoints pin the 3000 kPa pressure trip and were rejected):
    mode1 (base)   SETPT14=6.882 SETPT15=18.776  -> G ~ 53.8 mol%
    mode2 (mid-G)  SETPT14=7.600 SETPT15=17.600  -> G ~ 58.2 mol%
    mode3 (high-G) SETPT14=8.500 SETPT15=16.500  -> G ~ 63.4 mol%
  Gaps ~4-5 mol% vs within-mode std ~1.3 => distinct operating points needing
  migration, all stable, all soft-sensor-learnable (multivar R^2 0.57-0.71).

EXCITATION. IDV 8 (A,B,C feed composition), IDV 10 (C feed temperature) and
IDV 13 (reaction-kinetics slow drift), enabled from t=0. IDV 13 is what makes G
move as a learnable function of the inputs without loading reactor pressure; the
cooling-water disturbances (IDV 11/12) were rejected because they pin pressure.

NOTE ON FRAMING. These are feed-ratio-induced operating-point regimes, NOT the
canonical Downs & Vogel Mode 1/2/3 G/H ratios (those need mode-specific retuned
controllers). They are a clean, honest substrate for the Option-C claim:
"SBC migrates a soft sensor across operating regimes with <30% of retrain data."
"""

from __future__ import annotations

import pathlib
import subprocess

import numpy as np
from numpy.linalg import lstsq

HERE = pathlib.Path(__file__).resolve().parent
NPTS = 360000  # 100 h at DELTAT = 1 s
EXCITATION_IDVS = (8, 10, 13)
MODES = {  # tag: (SETPT14 reactor-feed D mol%, SETPT15 reactor-feed E mol%)
    "mode1": (6.882, 18.776),
    "mode2": (7.600, 17.600),
    "mode3": (8.500, 16.500),
}


def _driver_source(tag: str, sp14: float, sp15: float) -> str:
    """Patch the Russell/Braatz main driver for one regime + single-CSV output."""
    s = (HERE / "temain_mod.f").read_text()
    s = s.replace("      NPTS = 172800", f"      NPTS = {NPTS}")
    # excitation: switch on chosen IDVs after the main-program zeroing loop
    anchor = "      DO 100 I = 1, 20\n          IDV(I) = 0\n 100  CONTINUE"
    if s.count(anchor) != 1:
        raise RuntimeError("expected exactly one IDV-zeroing loop in temain_mod.f")
    s = s.replace(
        anchor,
        anchor + "\n" + "\n".join(f"      IDV({k}) = 1" for k in EXCITATION_IDVS),
        1,
    )
    # neutralise the built-in IDV(12) step at steady-state
    s = s.replace(
        "         IF (I.GE.SSPTS) THEN\n                 IDV(12)=1\n          ENDIF",
        "C        (excitation IDVs set from t=0)",
    )
    # regime setpoints
    s = s.replace("      SETPT(14)=6.8820", f"      SETPT(14)={sp14:.4f}")
    s = s.replace("      SETPT(15)=18.776", f"      SETPT(15)={sp15:.4f}")
    # single-CSV output: replace the 15-file OPEN block
    o0 = s.index("\tOPEN(UNIT=111,FILE=")
    o1 = s.index("\n", s.index("OPEN(UNIT=2121,")) + 1
    s = s[:o0] + f"\tOPEN(UNIT=50,FILE='tep_{tag}.csv',STATUS='replace')\n" + s[o1:]
    # write a CSV row every 180 s
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


def _learnability_r2(d: np.ndarray) -> float:
    g = d[:, 40]
    x = np.column_stack(
        [d[:, 2] / d[:, 3], d[:, 3], d[:, 8], d[:, 7], d[:, 1], d[:, 4], np.ones(len(g))]
    )
    beta, *_ = lstsq(x, g, rcond=None)
    pred = x @ beta
    return 1.0 - ((g - pred) ** 2).sum() / ((g - g.mean()) ** 2).sum()


def main() -> None:
    for need in ("temain_mod.f", "teprob.f"):
        if not (HERE / need).exists():
            raise SystemExit(f"missing {need}: clone tennessee-eastman-profBraatz here first")
    for tag, (sp14, sp15) in MODES.items():
        src = HERE / f"te_{tag}.f"
        src.write_text(_driver_source(tag, sp14, sp15))
        subprocess.run(
            [
                "gfortran",
                "-std=legacy",
                "-w",
                str(src),
                str(HERE / "teprob.f"),
                "-o",
                str(HERE / f"te_{tag}"),
            ],
            check=True,
        )
        subprocess.run([str(HERE / f"te_{tag}")], cwd=HERE, check=True)
        d = np.loadtxt(HERE / f"tep_{tag}.csv", delimiter=",")
        g, pr = d[:, 40], d[:, 7]
        print(
            f"{tag}: rows {d.shape[0]} | G {g.mean():.2f}+/-{g.std():.2f} "
            f"[{g.min():.1f},{g.max():.1f}] | Pr max {pr.max():.0f} "
            f"%pin {(pr >= 2999).mean() * 100:.0f}% | multivar R2 {_learnability_r2(d):.3f}"
        )


if __name__ == "__main__":
    main()
