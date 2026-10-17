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

WHAT IT PRODUCES (default call, unchanged since Phase 1C)
  tep_mode1.csv, tep_mode2.csv, tep_mode3.csv
  Each: 2000 rows (100 h at the 3-min TEP measurement cadence), 54 columns:
        time(h), XMEAS_1..41, XMV_1..12   (no header)

N1 PHASE 1 REPLICATIONS (pre-registration D-P1.8)
  --streams, --hours and --record-s give independent runs, other run lengths and finer recording:
    python generate_tep_modes.py --modes mode1 --streams 1 4 --hours 100 --record-s 60
  writes tep_mode1_stream1_100h_60s.csv and so on. Each regime's streams come from
  tep_seed_qualification.py ("chosen" in its record). Without --streams or --seeds the source is
  compiled unchanged, which reproduces the Phase-1C files byte for byte. After each run the
  summary flags a shutdown.

RANDOM NUMBERS. teprob.f draws every disturbance and noise term from TESUB7, a multiplicative
  congruential generator G <- 9228907 G mod 2**32 evaluated in double precision. The product
  exceeds 2**53, so it is rounded; the state gains trailing zero bits until G = 2**k m with k >= 3,
  after which the recursion is exact with period 2**(30 - k) draws. The plant uses about 952,000
  draws per simulated hour, so the stream repeats every 141 h (k = 3), 70 h (k = 4), 35 h (k = 5)
  and down to 0.55 h (k = 11): within 100 h for 41 of the 58 seeds in the source. Different seeds
  with the same k share one of two cycles (``legacy_cycle``; tep_rng_check.py).
  Replicated runs therefore use ``--streams``: TESUB7 is replaced by MRG32k3a (L'Ecuyer 1999),
  and run j starts at stream j, j * 2**127 draws from the RngStreams default seed, so no two runs
  share a random number. ``--seeds`` keeps the original generator and only replaces G (the
  classic data sets used the values listed in teprob.f SUBROUTINE TEINIT); it is kept for
  comparison only.

SHUTDOWNS. The simulator does not stop at a shutdown. Any violated limit (Downs and Vogel 1993,
  Table 6; teprob.f tests the noise-free states) sets every derivative to zero, the plant freezes,
  and rows keep being written with XMEAS 1-22 exactly constant and without measurement noise.
  ``shutdown_time`` detects that freeze, which catches every limit, including the levels. A test
  on the written pressure is not reliable, for two reasons. The written value carries measurement
  noise, so it can cross 3000 kPa a row before the shutdown, or without one. And a pressure trip
  can be written as exactly 0.3000000E+04, which a strict ">" misses. ``limit_time`` reports that
  test as a diagnostic only.
  The program writes only the CSV: the per-variable files of the original driver (Fortran units
  1111-2121) are not written.

REGIME DESIGN (validated; see stats printed at the end of a run)
  The G/H split is set by the reactor-feed composition controllers:
    SETPT(14) -> reactor-feed D mol% (XMEAS 26), D -> product G
    SETPT(15) -> reactor-feed E mol% (XMEAS 27), E -> product H
  Three regimes on the HIGH-G side (which lowers reactor pressure; low-G setpoints pin the
  3000 kPa pressure trip and were rejected). With the source's own seed all three stay below the
  limit for 100 h; with other seeds or streams many runs trip (40 of 76 streams in
  tep_seed_qualification.py):
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

import argparse
import math
import pathlib
import subprocess

import numpy as np
from numpy.linalg import lstsq

HERE = pathlib.Path(__file__).resolve().parent
NPTS = 360000  # 100 h at DELTAT = 1 s (the Phase-1C default)
EXCITATION_IDVS = (8, 10, 13)
MODES = {  # tag: (SETPT14 reactor-feed D mol%, SETPT15 reactor-feed E mol%)
    "mode1": (6.882, 18.776),
    "mode2": (7.600, 17.600),
    "mode3": (8.500, 16.500),
}
SEED_LINE = "       G=4651207995.D0"
TESUB7_SOURCE = """      DOUBLE PRECISION FUNCTION TESUB7(I)
      INTEGER I
      DOUBLE PRECISION G,DMOD
      COMMON/RANDSD/G
      G=DMOD(G*9228907.D0,4294967296.D0)
      IF(I.GE.0)TESUB7=G/4294967296.D0
      IF(I.LT.0)TESUB7=2.D0*G/4294967296.D0-1.D0
      RETURN
      END
"""

# MRG32k3a (L'Ecuyer 1999); state (s10, s11, s12, s20, s21, s22), newest last in each component.
MRG_M1, MRG_M2 = 4294967087, 4294944443
MRG_NORM = 2.328306549295727688e-10
MRG_A1 = ((0, 1, 0), (0, 0, 1), (-810728, 1403580, 0))
MRG_A2 = ((0, 1, 0), (0, 0, 1), (-1370589, 0, 527612))
MRG_DEFAULT = (12345, 12345, 12345, 12345, 12345, 12345)  # the RngStreams default seed
STREAM_JUMP = 2**127  # draws between consecutive streams, as in RngStreams


def _matmul(a: tuple, b: tuple, m: int) -> tuple:
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) % m for j in range(3)) for i in range(3)
    )


def _matpow(a: tuple, e: int, m: int) -> tuple:
    out = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    while e:
        if e & 1:
            out = _matmul(a, out, m)
        a, e = _matmul(a, a, m), e >> 1
    return out


def mrg_advance(state: tuple, steps: int) -> tuple[int, ...]:
    """MRG32k3a state after ``steps`` draws (exact, by matrix powers)."""
    out = []
    for a, m, v in ((MRG_A1, MRG_M1, state[:3]), (MRG_A2, MRG_M2, state[3:])):
        p = _matpow(a, steps, m)
        out += [sum(p[i][k] * v[k] for k in range(3)) % m for i in range(3)]
    return tuple(out)


def mrg_stream_state(stream: int) -> tuple[int, ...]:
    """Start state of stream ``stream`` (>= 1): stream * 2**127 draws from the default seed."""
    if stream < 1:
        raise ValueError("streams are numbered from 1")
    return mrg_advance(MRG_DEFAULT, stream * STREAM_JUMP)


def mrg_uniforms(state: tuple, n: int) -> tuple[list[float], tuple[int, ...]]:
    """Reference MRG32k3a: the next ``n`` uniforms in (0, 1), with the double arithmetic that the
    Fortran replacement of TESUB7 uses, and the final state."""
    s10, s11, s12, s20, s21, s22 = state
    out = []
    for _ in range(n):
        p1 = (1403580 * s11 - 810728 * s10) % MRG_M1
        p2 = (527612 * s22 - 1370589 * s20) % MRG_M2
        s10, s11, s12, s20, s21, s22 = s11, s12, p1, s21, s22, p2
        out.append(float(p1 - p2 + (MRG_M1 if p1 <= p2 else 0)) * MRG_NORM)
    return out, (s10, s11, s12, s20, s21, s22)


def _mrg_tesub7(state: tuple) -> str:
    """Fortran 77 MRG32k3a in place of TESUB7; exact in double precision by construction."""
    s = [f"{v}.D0" for v in state]
    return f"""      DOUBLE PRECISION FUNCTION TESUB7(I)
C     MRG32k3a (L'Ecuyer 1999) replaces the original generator, which
C     loses precision in double arithmetic and repeats within 0.55-141 h
C     (IPIS N1 Phase 1; scripts/generate_tep_modes.py).
      INTEGER I,K
      DOUBLE PRECISION S10,S11,S12,S20,S21,S22,P1,P2,U
      SAVE S10,S11,S12,S20,S21,S22
      DATA S10,S11,S12/{s[0]},{s[1]},{s[2]}/
      DATA S20,S21,S22/{s[3]},{s[4]},{s[5]}/
      P1=1403580.D0*S11-810728.D0*S10
      K=INT(P1/4294967087.D0)
      P1=P1-DBLE(K)*4294967087.D0
      IF(P1.LT.0.D0)P1=P1+4294967087.D0
      S10=S11
      S11=S12
      S12=P1
      P2=527612.D0*S22-1370589.D0*S20
      K=INT(P2/4294944443.D0)
      P2=P2-DBLE(K)*4294944443.D0
      IF(P2.LT.0.D0)P2=P2+4294944443.D0
      S20=S21
      S21=S22
      S22=P2
      IF(P1.LE.P2)THEN
        U=(P1-P2+4294967087.D0)*2.328306549295727688D-10
      ELSE
        U=(P1-P2)*2.328306549295727688D-10
      ENDIF
      IF(I.GE.0)TESUB7=U
      IF(I.LT.0)TESUB7=2.D0*U-1.D0
      RETURN
      END
"""


def legacy_cycle(seed: int, burn: int = 5000) -> tuple[int, int]:
    """Original TESUB7 from ``seed``: (k, period in draws) once the state has settled to 2**k m.

    Emulates G <- DMOD(G * 9228907, 2**32) in IEEE double precision (Python floats).
    """
    g = float(seed)
    for _ in range(burn):
        g = math.fmod(g * 9228907.0, 4294967296.0)
    n = int(g)
    k = (n & -n).bit_length() - 1
    return k, 2 ** (30 - k)


def output_name(
    tag: str, seed: int | None, hours: int, record_s: int, stream: int | None = None
) -> str:
    """Phase-1C name for the default run; stream or seed, duration and cadence spelled out
    otherwise."""
    if stream is not None:
        return f"tep_{tag}_stream{stream}_{hours}h_{record_s}s.csv"
    if seed is None and hours == 100 and record_s == 180:
        return f"tep_{tag}.csv"
    return f"tep_{tag}_seed{seed if seed is not None else 'src'}_{hours}h_{record_s}s.csv"


def _driver_source(
    tag: str,
    sp14: float,
    sp15: float,
    *,
    src_dir: pathlib.Path = HERE,
    hours: int = 100,
    record_s: int = 180,
    out_name: str = "tepout.csv",
) -> str:
    """Patch the Russell/Braatz main driver for one regime + single-CSV output.

    The CSV name stays short because fixed-form Fortran ignores everything past column 72;
    ``generate`` renames the file afterwards.
    """
    if hours < 1 or record_s < 1:
        raise ValueError("hours and record_s must be positive")
    s = (src_dir / "temain_mod.f").read_text()
    if s.count("      NPTS = 172800") != 1:
        raise RuntimeError("expected exactly one NPTS assignment in temain_mod.f")
    s = s.replace("      NPTS = 172800", f"      NPTS = {hours * 3600}")
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
    if len(out_name) > 16:
        raise ValueError("out_name must be at most 16 characters (fixed-form column limit)")
    o0 = s.index("\tOPEN(UNIT=111,FILE=")
    o1 = s.index("\n", s.index("OPEN(UNIT=2121,")) + 1
    s = s[:o0] + f"\tOPEN(UNIT=50,FILE='{out_name}',STATUS='replace')\n" + s[o1:]
    # write a CSV row every record_s seconds
    block = (
        " \tTEST4=MOD(I,180)\t\n\tIF (TEST4.EQ.0) THEN\n\t\tCALL OUTPUT\n"
        "      \t\tWRITE(111,111) I\n 111  \t\tFORMAT(1X,I6)\n     \tENDIF"
    )
    if s.count(block) != 1:
        raise RuntimeError("expected exactly one output block in temain_mod.f")
    s = s.replace(  # CALL OUTPUT dropped: it only wrote the per-variable files (units 1111-2121)
        block,
        f" \tTEST4=MOD(I,{record_s})\n\tIF (TEST4.EQ.0) THEN\n"
        "\t\tWRITE(50,500) TIME,(XMEAS(J),J=1,41),(XMV(J),J=1,12)\n"
        " 500  \t\tFORMAT(F12.5,53(',',E15.7))\n     \tENDIF",
    )
    c0 = s.index(" \tCLOSE(UNIT=111)")
    c1 = s.index("\n", s.index("CLOSE(UNIT=2121)")) + 1
    s = s[:c0] + "\tCLOSE(UNIT=50)\n" + s[c1:]
    return s


def _plant_source(
    seed: int | None, *, stream: int | None = None, src_dir: pathlib.Path = HERE
) -> str:
    """teprob.f; with ``stream``, TESUB7 becomes MRG32k3a at that stream; with ``seed``, only the
    original generator's G is replaced."""
    s = (src_dir / "teprob.f").read_text()
    if seed is not None and stream is not None:
        raise ValueError("give a seed or a stream, not both")
    if stream is not None:
        if s.count(TESUB7_SOURCE) != 1:
            raise RuntimeError("expected exactly one original TESUB7 in teprob.f")
        return s.replace(TESUB7_SOURCE, _mrg_tesub7(mrg_stream_state(stream)))
    if seed is None:
        return s
    if not 0 < seed < 2**53:  # G is a DOUBLE PRECISION constant; below 2**53 it is exact
        raise ValueError("seed must be an integer in (0, 2**53)")
    if s.count(SEED_LINE) != 1:
        raise RuntimeError("expected exactly one seed assignment G=4651207995.D0 in teprob.f")
    return s.replace(SEED_LINE, f"       G={seed}.D0")


def _learnability_r2(d: np.ndarray) -> float:
    g = d[:, 40]
    x = np.column_stack(
        [d[:, 2] / d[:, 3], d[:, 3], d[:, 8], d[:, 7], d[:, 1], d[:, 4], np.ones(len(g))]
    )
    beta, *_ = lstsq(x, g, rcond=None)
    pred = x @ beta
    return 1.0 - ((g - pred) ** 2).sum() / ((g - g.mean()) ** 2).sum()


def shutdown_time(d: np.ndarray, still: int = 3) -> float | None:
    """Time (h) of the first frozen row, or None if the plant never shuts down.

    A shutdown freezes the plant: from then on XMEAS 1-22 are written unchanged row after row.
    Measurement noise makes ``still`` consecutive unchanged rows impossible in normal operation. A
    freeze that begins in the last ``still`` rows and lasts to the end also counts.
    """
    frozen = np.all(np.diff(d[:, 1:23], axis=0) == 0.0, axis=1)
    run = np.convolve(frozen.astype(int), np.ones(still, dtype=int), mode="valid") == still
    if run.any():
        return float(d[int(np.argmax(run)), 0])
    if frozen.size and frozen[-1]:  # a freeze that began in the last ``still`` rows
        k = frozen.size - 1
        while k > 0 and frozen[k - 1]:
            k -= 1
        return float(d[k, 0])
    return None


def limit_time(d: np.ndarray) -> float | None:
    """Diagnostic only: time (h) of the first written reactor pressure >= 3000 kPa or
    temperature >= 175 C. Written values carry measurement noise (see the module docstring)."""
    limit = (d[:, 7] >= 3000.0) | (d[:, 9] >= 175.0)
    return float(d[int(np.argmax(limit)), 0]) if limit.any() else None


def generate(
    tag: str,
    *,
    seed: int | None = None,
    stream: int | None = None,
    hours: int = 100,
    record_s: int = 180,
    src_dir: pathlib.Path = HERE,
) -> pathlib.Path:
    """Compile and run one regime; return the CSV path (written in ``src_dir``)."""
    sp14, sp15 = MODES[tag]
    name = output_name(tag, seed, hours, record_s, stream)
    stem = name.removesuffix(".csv")
    driver = src_dir / f"te_{stem}.f"
    patched = seed is not None or stream is not None
    plant = src_dir / (f"teprob_{stem}.f" if patched else "teprob.f")
    driver.write_text(
        _driver_source(tag, sp14, sp15, src_dir=src_dir, hours=hours, record_s=record_s)
    )
    if patched:
        plant.write_text(_plant_source(seed, stream=stream, src_dir=src_dir))
    exe = src_dir / f"te_{stem}"
    subprocess.run(
        ["gfortran", "-std=legacy", "-w", str(driver), str(plant), "-o", str(exe)], check=True
    )
    subprocess.run([str(exe)], cwd=src_dir, check=True, stdout=subprocess.DEVNULL)
    return (src_dir / "tepout.csv").replace(src_dir / name)


def main() -> None:
    ap = argparse.ArgumentParser(description="TEP multimode generator (Phase 1C; N1 Phase 1)")
    ap.add_argument("--modes", nargs="+", default=list(MODES), choices=list(MODES))
    group = ap.add_mutually_exclusive_group()
    group.add_argument(
        "--streams", nargs="+", type=int, default=None, help="MRG32k3a streams (one run each)"
    )
    group.add_argument(
        "--seeds", nargs="+", type=int, default=None, help="original generator, seed G (legacy)"
    )
    ap.add_argument("--hours", type=int, default=100)
    ap.add_argument("--record-s", type=int, default=180, help="seconds between CSV rows")
    args = ap.parse_args()
    for need in ("temain_mod.f", "teprob.f"):
        if not (HERE / need).exists():
            raise SystemExit(f"missing {need}: clone tennessee-eastman-profBraatz here first")
    expected = args.hours * 3600 // args.record_s
    runs: list[dict] = (
        [{"stream": j} for j in args.streams]
        if args.streams
        else [{"seed": s} for s in (args.seeds or [None])]
    )
    for tag in args.modes:
        for run in runs:
            path = generate(tag, **run, hours=args.hours, record_s=args.record_s)
            d = np.loadtxt(path, delimiter=",")
            g, pr = d[:, 40], d[:, 7]
            trip = shutdown_time(d)
            status = "no shutdown" if trip is None else f"SHUTDOWN at {trip:.2f} h"
            lim = limit_time(d)
            if lim is not None:
                status += f" (written limit first reached at {lim:.2f} h)"
            print(
                f"{path.name}: rows {d.shape[0]}/{expected} | G {g.mean():.2f}+/-{g.std():.2f} "
                f"[{g.min():.1f},{g.max():.1f}] | Pr max {pr.max():.0f} "
                f"%pin {(pr >= 2999).mean() * 100:.0f}% | multivar R2 {_learnability_r2(d):.3f}"
                f" | {status}"
            )


if __name__ == "__main__":
    main()
