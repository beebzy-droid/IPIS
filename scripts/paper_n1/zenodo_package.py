"""The Zenodo deposit of the N1 paper's evidence: two archives, a README and checksums.

Run from the repository root, on the machine that holds the 15 TEP runs, after committing this
script (Windows cmd):
    set PYTHONPATH=src
    python -m scripts.paper_n1.zenodo_package --tag n1-jpc-submission

Writes to dist/zenodo/ (gitignored):
- IPIS-<tag>.zip: `git archive` of the tagged commit, limited to the files of the N1 study
  (N1_PATHS): its code and tests, the protocol and the records of the run, the evidence that the
  runner, the pilots and the figures read or wrote, the figure and table generators, the figures
  and the supplementary tables. The repository's other modules and papers are not part of the
  study and are not archived;
- tep_phase1_runs.zip: the 15 Tennessee Eastman runs of the study, each checked first against
  the SHA-256 in docs/paper/evidence/tep_seed_qualification.json (``phase1.data.tep_files``);
- README.md: what the deposit holds, how to reproduce the study, and the archived paths;
- SHA256SUMS.txt: the digests of the three files above.
The debutanizer data are not redistributed: README.md gives their source and the SHA-256 of the
file the study read. Nothing in the working tree is changed, and the evidence is not read beyond
the recorded digests.

History: the version at tag n1-jpc-submission archived the whole repository. The record
published on 2026-11-25 held that archive; its files were replaced with this version's within
Zenodo's period for editing a published record's files, so the DOI did not change
(docs/module1/ZENODO_N1.md, Section 5).
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

from ipis.module1_soft_sensor.phase1 import data as dt

from .style import REPO_ROOT

OUT_DIR = REPO_ROOT / "dist" / "zenodo"
DEBUT_SHA256 = "03ce599a6bac1239558cb475f6e81a26e431981ac7ece3c1825c7bdaf53471d8"
TITLE = (
    "When the laboratory is late: dead-time analysis and compensation of conformal "
    "soft-sensor intervals"
)

# The files of the N1 study at the tag (git pathspecs; a directory stands for all its files).
# Code: everything the study's scripts and tests import. Checked on 2026-11-25 by unpacking the
# archive alone: the 159 tests listed here pass, and make_all rewrites the 31 figure and table
# files from the records. Documents: the protocol and the decisions that led to it, the runner's
# map, the results, the literature sweep. Evidence: the records that the runner, the pilots and
# the figures read or wrote, and two earlier records that the protocol documents cite.
N1_PATHS = (
    "LICENSE",
    "pyproject.toml",
    "data/raw/debutanizer/.gitkeep",
    "data/raw/tep/.gitkeep",
    # Protocol, decisions, runner map, results, literature sweep
    "docs/module1/M1_NARROWING_PROPOSAL.md",
    "docs/module1/PHASE1_PREREGISTRATION.md",
    "docs/module1/PHASE1_RUNNER.md",
    "docs/module1/PHASE1_RESULTS.md",
    "docs/module1/LITERATURE_SWEEP_N1.md",
    "docs/module1/sweep",
    # Evidence
    "docs/paper/evidence/baseline_dryrun_phi05.json",
    "docs/paper/evidence/baseline_dryrun_phi09.json",
    "docs/paper/evidence/baseline_reproduction.json",
    "docs/paper/evidence/coverage_scaling_tails.json",
    "docs/paper/evidence/coverage_tep.json",
    "docs/paper/evidence/debutanizer_lag_scan.json",
    "docs/paper/evidence/f8_estimand_check.json",
    "docs/paper/evidence/f8_persistence_power.json",
    "docs/paper/evidence/f8_persistence_power_held20.json",
    "docs/paper/evidence/f8_persistence_power_held50.json",
    "docs/paper/evidence/f8_persistence_power_sweep.json",
    "docs/paper/evidence/phase1_power.json",
    "docs/paper/evidence/phase1_precheck.json",
    "docs/paper/evidence/phase1_stageA_T1.json",
    "docs/paper/evidence/phase1_stageA_T1_gb.json",
    "docs/paper/evidence/phase1_stageA_T2.json",
    "docs/paper/evidence/phase1_stageA_T3.json",
    "docs/paper/evidence/phase1_stageA_debutanizer.json",
    "docs/paper/evidence/phase1_stageB_T1.json",
    "docs/paper/evidence/phase1_stageB_T1_gb.json",
    "docs/paper/evidence/phase1_stageB_T2.json",
    "docs/paper/evidence/phase1_stageB_T3.json",
    "docs/paper/evidence/phase1_stageB_debutanizer.json",
    "docs/paper/evidence/phase1_stageB_debutanizer_steps.json",
    "docs/paper/evidence/phase1_verdicts.json",
    "docs/paper/evidence/tep_lag_compare.json",
    "docs/paper/evidence/tep_rng_check.json",
    "docs/paper/evidence/tep_seed_qualification.json",
    "docs/paper/evidence/tep_seed_verify_owner_2026-10-22.txt",
    # Figures, tables and supplementary tables
    "docs/paper/figures/n1",
    # Scripts
    "scripts/baselines",
    "scripts/diagnose_debutanizer_lag.py",
    "scripts/generate_tep_modes.py",
    "scripts/paper_n1/__init__.py",
    "scripts/paper_n1/fig_debutanizer.py",
    "scripts/paper_n1/fig_diagnosis.py",
    "scripts/paper_n1/fig_persistence.py",
    "scripts/paper_n1/fig_speed_chart.py",
    "scripts/paper_n1/fig_stability.py",
    "scripts/paper_n1/make_all.py",
    "scripts/paper_n1/style.py",
    "scripts/paper_n1/supplement.py",
    "scripts/paper_n1/tables.py",
    "scripts/phase1_power.py",
    "scripts/phase1_precheck.py",
    "scripts/phase1_run.py",
    "scripts/pilots",
    "scripts/sweep/n1_screening.py",
    "scripts/tep_phase1_runs.py",
    "scripts/tep_rng_check.py",
    "scripts/tep_seed_qualification.py",
    # Library
    "src/ipis/__init__.py",
    "src/ipis/shared/__init__.py",
    "src/ipis/shared/evidence.py",
    "src/ipis/shared/state_bus.py",
    "src/ipis/module1_soft_sensor/__init__.py",
    "src/ipis/module1_soft_sensor/data/__init__.py",
    "src/ipis/module1_soft_sensor/data/loaders.py",
    "src/ipis/module1_soft_sensor/data/preprocessing.py",
    "src/ipis/module1_soft_sensor/data/tep_loader.py",
    "src/ipis/module1_soft_sensor/evaluation/__init__.py",
    "src/ipis/module1_soft_sensor/evaluation/baselines.py",
    "src/ipis/module1_soft_sensor/evaluation/baselines_pid.py",
    "src/ipis/module1_soft_sensor/evaluation/baselines_spci.py",
    "src/ipis/module1_soft_sensor/evaluation/conformal.py",
    "src/ipis/module1_soft_sensor/evaluation/delay_compensation.py",
    "src/ipis/module1_soft_sensor/evaluation/delayed_aci.py",
    "src/ipis/module1_soft_sensor/evaluation/inference.py",
    "src/ipis/module1_soft_sensor/phase1",
    # Tests
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/fixtures/tep_mode2_stream3000_2h_60s.csv",
    "tests/unit/__init__.py",
    "tests/unit/test_baselines.py",
    "tests/unit/test_conformal.py",
    "tests/unit/test_delay_compensation.py",
    "tests/unit/test_delayed_aci.py",
    "tests/unit/test_inference.py",
    "tests/unit/test_paper_n1.py",
    "tests/unit/test_phase1_precheck.py",
    "tests/unit/test_phase1_runner.py",
    "tests/unit/test_state_bus.py",
    "tests/unit/test_tep_generator.py",
)

README = """# Evidence, code and pre-registration for "{title}"

Bien Don Busico, University of the Philippines Diliman, Quezon City, Philippines
(ORCID 0009-0006-7755-2470; bienbusico@gmail.com)

This deposit archives what the article's pre-registered study used and produced, as of tag
`{tag}` (commit {commit}) of the IPIS repository, https://github.com/beebzy-droid/IPIS. The
repository also holds other modules and papers of the IPIS project; they are not part of the
study and are not archived here.

## Files

| File | Content |
|---|---|
| `IPIS-{tag}.zip` | The study's {n_files} files at the tag (`git archive` of the paths listed at the end of this file). The protocol: `docs/module1/PHASE1_PREREGISTRATION.md`, frozen at tag `n1-phase1-freeze` (29 October 2026), and the decisions that led to it, `docs/module1/M1_NARROWING_PROPOSAL.md`. The runner and its map to the protocol: `scripts/phase1_run.py`, `src/ipis/module1_soft_sensor/phase1/`, `docs/module1/PHASE1_RUNNER.md`. The records of the run: `docs/paper/evidence/phase1_*.json` (stage A at commit 133b0f3, stage B and the verdicts at bd6454d) and `docs/module1/PHASE1_RESULTS.md`. The pilots and the baseline reproduction check: `scripts/pilots/`, `scripts/baselines/`. The literature sweep: `docs/module1/LITERATURE_SWEEP_N1.md` and `docs/module1/sweep/` (titles, identifiers and digests only). Figures, tables and supplementary tables: `scripts/paper_n1/`, written to `docs/paper/figures/n1/`. The study's tests: `tests/unit/` |
| `tep_phase1_runs.zip` | The 15 Tennessee Eastman runs of the study (100 h, one row every 60 s; columns: time in h, XMEAS 1-41, XMV 1-12), named `tep_<operating point>_stream<j>_100h_60s.csv`, with `SHA256SUMS.txt` |
| `SHA256SUMS.txt` | Digests of the two archives and of `README.md` |

## Data not included

The debutanizer data are those of Fortuna, Graziani, Rizzo and Xibilia, Soft Sensors for
Monitoring and Control of Industrial Processes (Springer, 2007). They are not redistributed here.
The study read the file `data/raw/debutanizer/debutanizer_data.txt`, SHA-256
`{debut_sha}`; compare a copy with this digest before using it. The stage A records hold the
digest of every input, and stage B refuses inputs whose digests differ from them.

## Reproducing the study

1. Unpack `IPIS-{tag}.zip` and work in its folder with `PYTHONPATH=src`. The study needs Python
   with numpy, scipy, pandas, scikit-learn, statsmodels, matplotlib and pydantic, and pytest with
   pytest-cov for the tests (`python -m pytest tests/unit`). The records of the run
   (`phase1_stage*.json`, `phase1_verdicts.json`) were made with Python 3.11.15 on Windows and
   list the package versions they used; each other record names the Python version that wrote
   it. The tests and the figure and table generators were also checked with Python 3.13 and
   numpy 2.5 on Linux.
   `pyproject.toml` is included for its test and lint settings; its dependency list is that of
   the whole IPIS project.
2. Put the 15 runs in `data/raw/tep/phase1/` and the debutanizer file in `data/raw/debutanizer/`.
3. `docs/module1/PHASE1_RUNNER.md`, Section 1, gives the run commands and what each stage checks
   (`scripts/phase1_run.py --stage A`, `--stage B` and `--verdicts`).
4. `python -m scripts.paper_n1.make_all` writes the figures and tables from the records to
   `docs/paper/figures/n1/`. On another platform a value can differ in its last digits.

The runs can also be regenerated from the simulator (`scripts/generate_tep_modes.py` and
`scripts/tep_phase1_runs.py`; sources of Russell, Chiang and Braatz at
https://github.com/camaramm/tennessee-eastman-profBraatz, commit 0643318), which checks each
file byte for byte against the recorded digest. The simulator's own random-number generator is
replaced by MRG32k3a streams; the article's supplementary material explains why.

`scripts/baselines/README.md` gives the separate environment and the pinned sources of the
baseline reproduction check. Two records that the protocol documents cite,
`docs/paper/evidence/coverage_tep.json` and `docs/paper/evidence/tep_lag_compare.json`, come from
the repository's earlier Module 1 pipeline; the code that wrote them is in the repository at the
tag, not in this archive.

## Licences

Code and documents in `IPIS-{tag}.zip`: MIT (the repository's `LICENSE`). The simulated runs in
`tep_phase1_runs.zip`: CC BY 4.0.

## Archived paths

`scripts/paper_n1/zenodo_package.py` at commit {head} of the repository wrote this deposit. The
archive is

    git archive --format=zip --prefix=IPIS-{tag}/ -o IPIS-{tag}.zip {tag} -- PATHS

with PATHS, in this order:

{paths}
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    return out.stdout.strip()


def tag_files(tag: str) -> list[str]:
    """The files that N1_PATHS select at the tag; stops if a path selects none."""
    files: list[str] = []
    for p in N1_PATHS:
        got = git("ls-tree", "-r", "--name-only", tag, "--", p).splitlines()
        if not got:
            raise SystemExit(f"{p}: not in {tag}")
        files.extend(got)
    if len(set(files)) != len(files):
        raise SystemExit("N1_PATHS select a file twice")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Zenodo deposit of the N1 evidence")
    ap.add_argument("--tag", required=True, help="the repository tag to archive")
    ap.add_argument("--tep-dir", type=Path, default=REPO_ROOT / dt.TEP_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    me = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()
    if git("status", "--porcelain", "--", me):
        raise SystemExit(
            f"{me} has uncommitted changes: commit it first (README.md names its commit)"
        )
    head = git("rev-parse", "--short=7", "HEAD")
    commit = git("rev-parse", "--verify", f"{args.tag}^{{commit}}")
    files = tag_files(args.tag)
    runs = dt.tep_files(args.tep_dir, REPO_ROOT / dt.TEP_RECORD)  # each checked against the record
    args.out.mkdir(parents=True, exist_ok=True)

    repo_zip = args.out / f"IPIS-{args.tag}.zip"
    prefix = f"IPIS-{args.tag}/"
    git(
        "archive",
        "--format=zip",
        f"--prefix={prefix}",
        "-o",
        str(repo_zip),
        args.tag,
        "--",
        *N1_PATHS,
    )
    with zipfile.ZipFile(repo_zip) as z:
        held = sorted(n[len(prefix) :] for n in z.namelist() if not n.endswith("/"))
    if held != sorted(files):
        raise SystemExit(f"{repo_zip.name} does not hold exactly the files that N1_PATHS select")

    runs_zip = args.out / "tep_phase1_runs.zip"
    sums = "".join(f"{r.sha256}  {r.path.name}\n" for r in runs)
    with zipfile.ZipFile(runs_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for r in runs:
            z.write(r.path, arcname=f"tep_phase1_runs/{r.path.name}")
        z.writestr("tep_phase1_runs/SHA256SUMS.txt", sums)

    readme = args.out / "README.md"
    text = README.format(
        title=TITLE,
        tag=args.tag,
        commit=commit[:7],
        head=head,
        n_files=len(files),
        debut_sha=DEBUT_SHA256,
        paths="\n".join(f"    {p}" for p in N1_PATHS),
    )
    readme.write_text(text, encoding="utf-8", newline="\n")

    deposit = (repo_zip, runs_zip, readme)
    lines = "".join(f"{sha256(p)}  {p.name}\n" for p in deposit)
    (args.out / "SHA256SUMS.txt").write_text(lines, encoding="utf-8", newline="\n")
    for p in (*deposit, args.out / "SHA256SUMS.txt"):
        print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")
    print(f"  tag {args.tag} = {commit[:7]}: {len(files)} files of the N1 study archived")
    print(f"  {len(runs)} runs checked against the record; packaged at commit {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
