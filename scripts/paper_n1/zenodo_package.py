"""The Zenodo deposit of the N1 paper's evidence: two archives, a README and checksums.

Run from the repository root, on the machine that holds the 15 TEP runs (Windows cmd):
    set PYTHONPATH=src
    python -m scripts.paper_n1.zenodo_package --tag n1-jpc-submission

Writes to dist/zenodo/ (gitignored):
- IPIS-<tag>.zip: `git archive` of the tagged commit: code, pre-registration, runner records,
  evidence, figure and table generators, figures and the supplementary tables;
- tep_phase1_runs.zip: the 15 Tennessee Eastman runs of the study, each checked first against
  the SHA-256 in docs/paper/evidence/tep_seed_qualification.json (``phase1.data.tep_files``);
- README.md: what the deposit holds and how to reproduce the study;
- SHA256SUMS.txt: the digests of the three files above.
The debutanizer data are not redistributed: README.md gives their source and the SHA-256 of the
file the study read. Nothing in the working tree is changed, and the evidence is not read beyond
the recorded digests.
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

README = """# Evidence, code and pre-registration for "{title}"

Bien Don Busico, University of the Philippines Diliman, Quezon City, Philippines
(ORCID 0009-0006-7755-2470; bienbusico@gmail.com)

This deposit archives what the article's pre-registered study used and produced, as of tag
`{tag}` (commit {commit}) of the IPIS repository, https://github.com/beebzy-droid/IPIS.

## Files

| File | Content |
|---|---|
| `IPIS-{tag}.zip` | The repository at the tag (`git archive`). The protocol: `docs/module1/PHASE1_PREREGISTRATION.md`, frozen at tag `n1-phase1-freeze` (29 October 2026). The runner and its map to the protocol: `scripts/phase1_run.py`, `src/ipis/module1_soft_sensor/phase1/`, `docs/module1/PHASE1_RUNNER.md`. The records of the run: `docs/paper/evidence/phase1_*.json` (stage A at commit 133b0f3, stage B and the verdicts at bd6454d) and `docs/module1/PHASE1_RESULTS.md`. Figures, tables and supplementary tables: `scripts/paper_n1/`, written to `docs/paper/figures/n1/` |
| `tep_phase1_runs.zip` | The 15 Tennessee Eastman runs of the study (100 h, one row every 60 s; columns: time in h, XMEAS 1-41, XMV 1-12), named `tep_<operating point>_stream<j>_100h_60s.csv`, with `SHA256SUMS.txt` |
| `SHA256SUMS.txt` | Digests of the two archives and of `README.md` |

## Data not included

The debutanizer data are those of Fortuna, Graziani, Rizzo and Xibilia, Soft Sensors for
Monitoring and Control of Industrial Processes (Springer, 2007). They are not redistributed here.
The study read the file `data/raw/debutanizer/debutanizer_data.txt`, SHA-256
`{debut_sha}`; compare a copy with this digest before using it. The stage A records hold the
digest of every input, and stage B refuses inputs whose digests differ from them.

## Reproducing the study

1. Unpack `IPIS-{tag}.zip`, create the environment (Python 3.11; `pyproject.toml`), and put the
   15 runs in `data/raw/tep/phase1/` and the debutanizer file in `data/raw/debutanizer/`.
2. `docs/module1/PHASE1_RUNNER.md`, Section 1, gives the run commands and what each stage checks
   (`scripts/phase1_run.py --stage A`, `--stage B` and `--verdicts`, with `PYTHONPATH=src`).
3. `python -m scripts.paper_n1.make_all` writes the figures and tables from the records.

The runs can also be regenerated from the simulator (`scripts/generate_tep_modes.py` and
`scripts/tep_phase1_runs.py`; sources of Russell, Chiang and Braatz at
https://github.com/camaramm/tennessee-eastman-profBraatz, commit 0643318), which checks each
file byte for byte against the recorded digest. The simulator's own random-number generator is
replaced by MRG32k3a streams; the article's supplementary material explains why.

## Licences

Code and documents in `IPIS-{tag}.zip`: MIT (the repository's `LICENSE`). The simulated runs in
`tep_phase1_runs.zip`: CC BY 4.0.
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Zenodo deposit of the N1 evidence")
    ap.add_argument("--tag", required=True, help="the repository tag to archive")
    ap.add_argument("--tep-dir", type=Path, default=REPO_ROOT / dt.TEP_DIR)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args()

    commit = git("rev-parse", "--verify", f"{args.tag}^{{commit}}")
    runs = dt.tep_files(args.tep_dir, REPO_ROOT / dt.TEP_RECORD)  # each checked against the record
    args.out.mkdir(parents=True, exist_ok=True)

    repo_zip = args.out / f"IPIS-{args.tag}.zip"
    prefix = f"IPIS-{args.tag}/"
    git("archive", "--format=zip", f"--prefix={prefix}", "-o", str(repo_zip), args.tag)

    runs_zip = args.out / "tep_phase1_runs.zip"
    sums = "".join(f"{r.sha256}  {r.path.name}\n" for r in runs)
    with zipfile.ZipFile(runs_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for r in runs:
            z.write(r.path, arcname=f"tep_phase1_runs/{r.path.name}")
        z.writestr("tep_phase1_runs/SHA256SUMS.txt", sums)

    readme = args.out / "README.md"
    text = README.format(title=TITLE, tag=args.tag, commit=commit[:7], debut_sha=DEBUT_SHA256)
    readme.write_text(text, encoding="utf-8", newline="\n")

    files = (repo_zip, runs_zip, readme)
    lines = "".join(f"{sha256(p)}  {p.name}\n" for p in files)
    (args.out / "SHA256SUMS.txt").write_text(lines, encoding="utf-8", newline="\n")
    for p in (*files, args.out / "SHA256SUMS.txt"):
        print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")
    print(f"  tag {args.tag} = {commit[:7]}; {len(runs)} runs checked against the record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
