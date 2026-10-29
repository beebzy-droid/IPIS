#!/usr/bin/env python3
"""Generate the 15 TEP runs of N1 Phase 1 and check each one byte for byte (pre-registration
Section 5.2 and Section 9, step 5).

The runs are the ones the qualification chose (``tep_seed_qualification.py``, record
``docs/paper/evidence/tep_seed_qualification.json``): five MRG32k3a streams per regime, 100 h,
recorded every 60 s. For each one this script
- checks first that the Fortran sources and ``generate_tep_modes.py`` are the files the record
  names (its ``_meta.sha256``), and stops before generating anything if they are not;
- generates the run with ``generate_tep_modes.generate(..., stream=j)`` in a private work folder;
- compares the SHA-256 of the CSV with the one the record holds for that run;
- moves a matching file into ``--out`` under the generator's name, for example
  ``tep_mode1_stream19_100h_60s.csv``, and deletes a file that differs.

It reads nothing in the data and prints no statistic of it: only the file name and whether its
hash matches. The Phase 1 runner checks the same hashes again when it loads the files. The exit
status is 1 if any run differs.

Run next to generate_tep_modes.py, temain_mod.f and teprob.f, with the record copied beside them
(for example in WSL):
    python3 tep_phase1_runs.py --record tep_seed_qualification.json --out OUT_DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import generate_tep_modes as g

SOURCES = ("temain_mod.f", "teprob.f", "generate_tep_modes.py")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sources(record: dict, here: Path) -> list[str]:
    """Names of the source files whose SHA-256 differs from the record (empty if all match)."""
    want = record["_meta"]["sha256"]
    return [name for name in SOURCES if sha256(here / name) != want[name]]


def expected_hashes(record: dict) -> dict[tuple[str, int], str]:
    """(regime, stream) -> SHA-256 of the run's CSV, for every chosen run of the record."""
    rows = {row["stream"]: row for row in record["log"]}
    return {
        (tag, stream): rows[stream][tag]["csv_sha256"]
        for tag, streams in record["chosen"].items()
        for stream in streams
    }


def make_run(
    tag: str, stream: int, want: str, hours: int, record_s: int, work: Path, out: Path
) -> bool:
    """Generate one run in ``work``; keep it in ``out`` if its hash is ``want``. Build files and a
    differing CSV are deleted."""
    stem = g.output_name(tag, None, hours, record_s, stream).removesuffix(".csv")
    build = [work / name for name in (f"te_{stem}.f", f"teprob_{stem}.f", f"te_{stem}")]
    try:
        path = g.generate(tag, stream=stream, hours=hours, record_s=record_s, src_dir=work)
        same = sha256(path) == want
        if same:
            shutil.move(str(path), str(out / path.name))
        else:
            path.unlink(missing_ok=True)
        print(path.name, "same as the record" if same else "DIFFERENT from the record")
        return same
    finally:
        for p in (*build, work / "tepout.csv"):
            p.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate and check the N1 Phase 1 TEP runs")
    ap.add_argument("--record", required=True, help="tep_seed_qualification.json")
    ap.add_argument("--out", required=True, help="folder for the 15 CSV files")
    args = ap.parse_args()
    record = json.loads(Path(args.record).read_text())
    here = g.HERE
    bad_sources = check_sources(record, here)
    if bad_sources:
        print("these files differ from the record, so nothing was generated:", bad_sources)
        return 1
    hours, record_s = record["_meta"]["hours"], record["_meta"]["record_s"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = here / ".phase1_runs"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir()
    for name in ("temain_mod.f", "teprob.f"):
        shutil.copyfile(here / name, work / name)
    bad = 0
    try:
        for (tag, stream), want in expected_hashes(record).items():
            bad += not make_run(tag, stream, want, hours, record_s, work, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    n = len(expected_hashes(record))
    print(f"{n - bad} of {n} runs match the record" + ("" if not bad else "; see above"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
