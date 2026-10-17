#!/usr/bin/env python3
"""TEP run qualification for N1 Phase 1 (pre-registration D-P1.8).

Rule:
- Every run uses its own MRG32k3a stream (``generate_tep_modes.py --streams``). The original
  TEP generator settles into cycles of 0.55 to 141 h that different seeds share, so seeds of it
  cannot give independent 100-h runs (see generate_tep_modes.py, RANDOM NUMBERS). Streams are
  2**127 draws apart; a 100-h run uses about 1e8.
- The candidates are streams 1, 2, 3, ..., dealt to mode1, mode2 and mode3 in rotation (candidate
  k goes to regime k mod 3) before any run, so no stream serves two regimes.
- A candidate qualifies for its regime if its 100-h run at 60-s rows has no shutdown
  (``generate_tep_modes.shutdown_time``, the plant freeze that any violated limit causes). Each
  regime takes its first five qualifiers. Candidates are examined until every regime has five; the
  record ends at the candidate that completes the selection, whatever the number of workers.
- Each candidate is run in its own regime; ``--matrix`` also runs it in the other two, for a
  complete trip matrix that does not affect the selection.
- Only the trip status is read: the shutdown time, the written reactor pressure and temperature at
  the first frozen row, and, as a diagnostic, the first row where the written pressure or
  temperature reaches its limit. The SHA-256 of each data file is recorded, so that a run can be
  checked byte for byte on another machine without this procedure. Each data file and its build
  files are deleted at once.
- The record's _meta holds the SHA-256 of the Fortran sources, the generator and this script.

Run next to generate_tep_modes.py, temain_mod.f and teprob.f (for example in WSL):
    python3 tep_seed_qualification.py --json tep_seed_qualification.json --workers 2
The exit status is 1 if the candidates run out before every regime has five qualifiers.
To check another machine, regenerate the chosen runs and compare their SHA-256 with the record
(each file is deleted after hashing):
    python3 tep_seed_qualification.py --verify tep_seed_qualification.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import generate_tep_modes as g
import numpy as np

REGIMES = tuple(g.MODES)
SOURCES = ("temain_mod.f", "teprob.f")


def assigned_regime(k: int) -> str:
    """Regime of the k-th candidate (0-based): dealt in rotation, before any run."""
    return REGIMES[k % len(REGIMES)]


def select(log: list[dict], per_regime: int) -> dict[str, list[int]]:
    """Each regime's first ``per_regime`` candidates whose run in that regime did not shut down."""
    chosen: dict[str, list[int]] = {tag: [] for tag in REGIMES}
    for k, row in enumerate(log):
        tag = assigned_regime(k)
        if row[tag]["shutdown_h"] is None and len(chosen[tag]) < per_regime:
            chosen[tag].append(row["stream"])
    picked = [s for tag in REGIMES for s in chosen[tag]]
    assert len(picked) == len(set(picked)), "a stream was selected for two regimes"
    return chosen


def complete(chosen: dict[str, list[int]], per_regime: int) -> bool:
    return all(len(chosen[tag]) >= per_regime for tag in REGIMES)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_status(
    tag: str, stream: int, hours: int, record_s: int, work_dir: Path | None = None
) -> dict:
    """Trip status of one run. Data and build files are deleted, also if the run fails."""
    work = work_dir or g.HERE
    stem = g.output_name(tag, None, hours, record_s, stream).removesuffix(".csv")
    files = [work / f"{stem}.csv"] + [
        work / name for name in (f"te_{stem}.f", f"teprob_{stem}.f", f"te_{stem}", "tepout.csv")
    ]
    try:
        path = g.generate(tag, stream=stream, hours=hours, record_s=record_s, src_dir=work)
        d = np.loadtxt(path, delimiter=",")
        t, lim = g.shutdown_time(d), g.limit_time(d)
        out: dict = {"shutdown_h": t, "limit_h": lim, "csv_sha256": sha256(path)}
        if t is not None:
            i = int(np.flatnonzero(d[:, 0] == t)[0])
            out.update(pressure_kpa=float(d[i, 7]), temperature_c=float(d[i, 9]))
        return out
    finally:
        for p in files:
            p.unlink(missing_ok=True)


def _work_dir() -> Path:
    """A fresh private directory per process (the simulator always writes tepout.csv in its cwd),
    with fresh copies of the sources."""
    work = g.HERE / f".qualify_{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    for name in SOURCES:
        shutil.copyfile(g.HERE / name, work / name)
    return work


_WORK: Path | None = None  # this process's directory, made on its first candidate


def _candidate(job: tuple[int, int, int, bool]) -> dict:
    global _WORK
    k, hours, record_s, matrix = job
    stream, tag = k + 1, assigned_regime(k)
    if _WORK is None:
        _WORK = _work_dir()
    work = _WORK
    row: dict = {"stream": stream, "assigned": tag}
    for t in REGIMES if matrix else (tag,):
        row[t] = run_status(t, stream, hours, record_s, work)
    return row


def extend(log: list[dict], rows: list[dict], per_regime: int) -> list[dict]:
    """Append ``rows`` (in candidate order) until the selection is complete; return the rows
    appended. Rows after the completing candidate are dropped, so the record does not depend on
    the number of workers."""
    added = []
    for row in rows:
        if complete(select(log, per_regime), per_regime):
            break
        log.append(row)
        added.append(row)
    return added


def verify(record: dict) -> int:
    """Regenerate every chosen run and compare its SHA-256 with the record; files are deleted."""
    hours, record_s = record["_meta"]["hours"], record["_meta"]["record_s"]
    rows = {row["stream"]: row for row in record["log"]}
    work, bad = _work_dir(), 0
    try:
        for tag in REGIMES:
            for stream in record["chosen"][tag]:
                got = run_status(tag, stream, hours, record_s, work)["csv_sha256"]
                same = got == rows[stream][tag]["csv_sha256"]
                bad += not same
                print(tag, stream, "same" if same else "DIFFERENT")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("all chosen runs reproduce byte for byte" if not bad else f"{bad} runs differ")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Qualify TEP runs by trip status (D-P1.8)")
    ap.add_argument("--per-regime", type=int, default=5)
    ap.add_argument("--hours", type=int, default=100)
    ap.add_argument("--record-s", type=int, default=60)
    ap.add_argument("--max-streams", type=int, default=600)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--matrix", action="store_true", help="also run every candidate elsewhere")
    ap.add_argument("--json", default=None, help="write the record to this path")
    ap.add_argument("--verify", default=None, help="check the chosen runs of this record instead")
    args = ap.parse_args()
    if args.verify:
        return verify(json.loads(Path(args.verify).read_text()))
    log: list[dict] = []
    try:
        with Pool(args.workers) as pool:
            for start in range(0, args.max_streams, args.workers):
                jobs = [
                    (k, args.hours, args.record_s, args.matrix)
                    for k in range(start, min(start + args.workers, args.max_streams))
                ]
                for row in extend(log, pool.map(_candidate, jobs), args.per_regime):
                    tag = row["assigned"]
                    print(row["stream"], tag, row[tag]["shutdown_h"], flush=True)
                if complete(select(log, args.per_regime), args.per_regime):
                    break
    finally:
        for work in g.HERE.glob(".qualify_*"):
            shutil.rmtree(work, ignore_errors=True)
    chosen = select(log, args.per_regime)
    done = complete(chosen, args.per_regime)
    print("chosen:", chosen, "" if done else "INCOMPLETE: the candidates ran out")
    if args.json:
        version = subprocess.run(["gfortran", "--version"], capture_output=True, text=True)
        stamp = datetime.now(timezone.utc)  # noqa: UP017 (WSL Python may be 3.10)
        doc = {
            "_meta": {
                "generated_utc": stamp.isoformat(timespec="seconds"),
                "python": platform.python_version(),
                "gfortran": version.stdout.splitlines()[0] if version.stdout else None,
                "hours": args.hours,
                "record_s": args.record_s,
                "per_regime": args.per_regime,
                "matrix": args.matrix,
                "rng": "MRG32k3a (L'Ecuyer 1999) in place of TESUB7; stream j starts j * 2**127 "
                "draws from the seed (12345, 12345, 12345, 12345, 12345, 12345)",
                "rule": "streams 1, 2, ... dealt to mode1, mode2, mode3 in rotation; each regime "
                "takes its first per_regime candidates without a shutdown",
                "sha256": {
                    name: sha256(g.HERE / name) for name in (*SOURCES, "generate_tep_modes.py")
                }
                | {"tep_seed_qualification.py": sha256(Path(__file__).resolve())},
            },
            "complete": done,
            "chosen": chosen,
            "stream_states": {
                str(s): list(g.mrg_stream_state(s)) for tag in REGIMES for s in chosen[tag]
            },
            "log": log,
        }
        with open(args.json, "w") as f:
            json.dump(doc, f, indent=2)
    return 0 if done else 1


if __name__ == "__main__":
    raise SystemExit(main())
