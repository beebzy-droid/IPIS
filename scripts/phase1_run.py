"""N1 Phase 1 runner (pre-registration Section 9, steps 6 and 7; docs/module1/PHASE1_RUNNER.md).

Stage A reads calibration rows only: the debutanizer's training split and the TEP rows up to
70 h. It writes, per unit, everything the protocol fixes from them, the P3 predictions among
them (docs/paper/evidence/phase1_stageA_<unit>.json). Commit and push that evidence before stage
B: the commit records that the predictions were written before any evaluation row was read
(Section 3F). Commit the runner itself before stage A: stage A refuses to run from sources that
differ from the last commit, stage B refuses to run until the stage A files are committed,
pushed and unchanged, or if the sources or the Python packages differ from stage A's, and stage
A refuses to run again once a unit has a stage B file.

Stage B reads every row, checks that it reproduces stage A's calibration quantities, and runs
every cell with stage A's settings (phase1_stageB_<unit>.json, and the debutanizer's per-step
flags in phase1_stageB_debutanizer_steps.json). --verdicts then applies the rules of Section 6
(phase1_verdicts.json).

The 15 TEP runs must be in data\\raw\\tep\\phase1 (or give --tep-dir). Run from the repository root,
in the ipis environment (Windows cmd):
    set PYTHONPATH=src
    python scripts\\phase1_run.py --stage A --workers 6
    (commit and push docs\\paper\\evidence\\phase1_stageA_*.json)
    python scripts\\phase1_run.py --stage B --workers 6
    python scripts\\phase1_run.py --verdicts

Every BLAS library runs on one thread, set here before numpy loads, so that a result does not
depend on the thread count, and MKL, if numpy uses it, runs its reproducible code path
(MKL_CBWR); the work is spread over --workers processes instead. Results do not depend on the
number of workers.
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = "1"
os.environ["MKL_CBWR"] = "COMPATIBLE"

import argparse  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

from ipis.module1_soft_sensor.phase1 import data as dat  # noqa: E402
from ipis.module1_soft_sensor.phase1 import record as rc  # noqa: E402
from ipis.module1_soft_sensor.phase1 import stages as st  # noqa: E402
from ipis.module1_soft_sensor.phase1.verdicts import verdicts  # noqa: E402

EVIDENCE = Path("docs/paper/evidence")
PRECHECK = EVIDENCE / "phase1_precheck.json"


def stage_a_path(ev: Path, unit: str) -> Path:
    return ev / f"phase1_stageA_{unit}.json"


def stage_b_path(ev: Path, unit: str) -> Path:
    return ev / f"phase1_stageB_{unit}.json"


def steps_path(ev: Path) -> Path:
    return ev / "phase1_stageB_debutanizer_steps.json"


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def committed(path: Path) -> str | None:
    """None if ``path`` is tracked by git and unchanged against HEAD; else the reason."""
    try:
        if git("ls-files", "--error-unmatch", path.as_posix()).returncode != 0:
            return "not committed"
        if git("diff", "--quiet", "HEAD", "--", path.as_posix()).returncode != 0:
            return "changed since the last commit"
        return None
    except OSError as exc:
        return f"git is not available ({exc})"


def pushed(path: Path) -> tuple[str | None, str | None]:
    """The commit that last changed ``path``, with None if that commit is on the branch's
    upstream (the remote-tracking branch, which git updates at each push), else the reason."""
    try:
        last = git("log", "-1", "--format=%H", "--", path.as_posix())
        sha = last.stdout.strip() if last.returncode == 0 else ""
        if not sha:
            return "no commit has it", None
        up = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        ref = up.stdout.strip() if up.returncode == 0 and up.stdout.strip() else "origin/main"
        check = git("merge-base", "--is-ancestor", sha, ref).returncode
        if check == 1:
            return f"its commit {sha[:12]} is not on {ref} (not pushed)", sha
        if check != 0:
            return f"cannot check its commit {sha[:12]} against {ref}", sha
        return None, sha
    except OSError as exc:
        return f"git is not available ({exc})", None


def provenance() -> dict[str, Any]:
    """Source hashes and packages, and the git commit the code was run from (best effort)."""
    out = rc.provenance(st.SOURCES)
    try:
        head = git("rev-parse", "HEAD")
        dirty = git("status", "--porcelain", "--", *st.SOURCES)
        out["git_head"] = head.stdout.strip() if head.returncode == 0 else None
        out["sources_uncommitted"] = [line[3:] for line in dirty.stdout.splitlines()]
    except OSError:
        out["git_head"] = None
    return out


def load_units(args: argparse.Namespace, stage: str, pmap: st.Mapper) -> list[st.Unit]:
    units = []
    if "debutanizer" in args.units:
        pre = rc.read_evidence(args.precheck)
        units.append(st.debutanizer_unit(args.debutanizer, stage, pre))
    tep = [u for u in st.TEP_UNITS if u in args.units]
    if tep:
        units += st.tep_units(args.tep_dir, args.record, stage, tep, pmap)
    return units


def run_stage_a(args: argparse.Namespace) -> None:
    for unit in args.units:
        if stage_b_path(args.evidence_dir, unit).exists():
            sys.exit(f"{unit} has a stage B record: stage A cannot run again")
    sources = provenance()
    if (sources.get("git_head") is None or sources.get("sources_uncommitted")) and not (
        args.allow_uncommitted
    ):
        sys.exit(
            "the runner's sources differ from the last commit (or git is not available): "
            f"{sources.get('sources_uncommitted')}. Commit the runner first."
        )
    with st.mapper(args.workers) as pmap:
        for unit in load_units(args, "A", pmap):
            t0 = time.time()
            rec = st.stage_a(unit, pmap) | {"provenance": sources}
            path = stage_a_path(args.evidence_dir, unit.name)
            sha = rc.write_evidence(path, rec)
            flagged = sum(
                not v["feasible"]
                for plant in rec["tuning"].values()
                for th in plant.values()
                for comp in th.values()
                for loop in comp.values()
                for v in loop.values()
            )
            pid = ""
            if "pid" in rec:
                flags = [
                    v["flag"]
                    for p in rec["pid"]["tuning"].values()
                    for t in p.values()
                    for v in t.values()
                ]
                pid = f"; conformal PID tunings not 'valid': {sum(f != 'valid' for f in flags)}"
            print(
                f"stage A {unit.name}: {len(unit.streams)} streams; tunings flagged infeasible: "
                f"{flagged}{pid}; {time.time() - t0:.0f} s\n  {path.as_posix()}  sha256 {sha}",
                flush=True,
            )


def run_stage_b(args: argparse.Namespace) -> None:
    sources = provenance()
    stage_a = {}
    for unit in args.units:
        path = stage_a_path(args.evidence_dir, unit)
        if not path.exists():
            sys.exit(f"{path.as_posix()} is missing: run stage A first")
        reason, commit = committed(path), None
        if reason is None:
            reason, commit = pushed(path)
        if reason is not None and not args.allow_uncommitted:
            sys.exit(f"{path.as_posix()}: {reason}. Commit and push the stage A evidence first.")
        a = rc.read_evidence(path)
        changed = sorted(
            f
            for f, h in sources["sources_sha256"].items()
            if a["provenance"]["sources_sha256"].get(f) != h
        )
        if changed and not args.allow_source_change:
            sys.exit(f"sources changed since stage A ({unit}): {changed}")
        env = {k: a["provenance"][k] for k in ("python", "packages")}
        if env != {k: sources[k] for k in ("python", "packages")} and not args.allow_env_change:
            sys.exit(f"Python or its packages differ from stage A's ({unit}): {env}")
        stage_a[unit] = (a, rc.evidence_sha256(path), commit, changed)
    steps_all: dict[str, Any] = {}
    with st.mapper(args.workers) as pmap:
        for unit in load_units(args, "B", pmap):
            t0 = time.time()
            a, a_sha, a_commit, changed = stage_a[unit.name]
            rec, steps = st.stage_b(unit, a, pmap)
            rec |= {
                "stage_a_sha256": a_sha,
                "stage_a_commit": a_commit,
                "sources_changed_since_stage_a": changed,
                "provenance": sources,
            }
            path = stage_b_path(args.evidence_dir, unit.name)
            sha = rc.write_evidence(path, rec, compact=True)
            close = _close_checks(rec["checks"])
            status = (
                "all exact" if not close else f"{len(close)} within tolerance only: {close[:5]}"
            )
            print(
                f"stage B {unit.name}: {time.time() - t0:.0f} s; checks against stage A: {status}"
                f"\n  {path.as_posix()}  sha256 {sha}",
                flush=True,
            )
            if steps:
                steps_all = {
                    "unit": unit.name,
                    "stage_a_sha256": a_sha,
                    "steps": st.steps_record(steps),
                    "provenance": sources,
                }
    if steps_all:
        path = steps_path(args.evidence_dir)
        sha = rc.write_evidence(path, steps_all, compact=True)
        print(f"  {path.as_posix()}  sha256 {sha}", flush=True)


def _close_checks(node: Any, path: str = "") -> list[str]:
    """The checks that matched within tolerance but not bit for bit."""
    if isinstance(node, dict):
        return [c for k, v in node.items() for c in _close_checks(v, f"{path}/{k}")]
    if isinstance(node, list):
        return [c for i, v in enumerate(node) for c in _close_checks(v, f"{path}/{i}")]
    return [path] if node == "close" else []


def run_verdicts(args: argparse.Namespace) -> None:
    """The verdicts need every unit's records (``allow_partial``, for tests only, skips the
    missing ones)."""
    stage_a, stage_b, inputs = {}, {}, {}
    for unit in st.UNITS:
        pa, pb = stage_a_path(args.evidence_dir, unit), stage_b_path(args.evidence_dir, unit)
        if not (pa.exists() and pb.exists()):
            if getattr(args, "allow_partial", False):
                continue
            missing = pa if not pa.exists() else pb
            sys.exit(f"{missing.as_posix()} is missing: run both stages for every unit first")
        stage_a[unit], stage_b[unit] = rc.read_evidence(pa), rc.read_evidence(pb)
        if stage_b[unit]["stage_a_sha256"] != rc.evidence_sha256(pa):
            sys.exit(f"{pa.as_posix()} is not the stage A record stage B used")
        inputs[pa.as_posix()] = rc.evidence_sha256(pa)
        inputs[pb.as_posix()] = rc.evidence_sha256(pb)
    ps = steps_path(args.evidence_dir)
    if not ps.exists():
        sys.exit(f"{ps.as_posix()} is missing: run stage B for the debutanizer first")
    steps = rc.read_evidence(ps)["steps"]
    inputs[ps.as_posix()] = rc.evidence_sha256(ps)
    out = verdicts(stage_a, stage_b, steps)
    out |= {"inputs_sha256": inputs, "provenance": provenance()}
    path = args.evidence_dir / "phase1_verdicts.json"
    sha = rc.write_evidence(path, out)
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print(f"{path.as_posix()}  sha256 {sha}")


def main() -> None:
    ap = argparse.ArgumentParser(description="N1 Phase 1 runner")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage", choices=("A", "B"))
    mode.add_argument("--verdicts", action="store_true")
    ap.add_argument("--units", nargs="+", default=list(st.UNITS), choices=st.UNITS)
    ap.add_argument("--workers", type=int, default=1, help="worker processes")
    ap.add_argument("--debutanizer", type=Path, default=dat.DEBUT_PATH)
    ap.add_argument("--tep-dir", type=Path, default=dat.TEP_DIR)
    ap.add_argument("--record", type=Path, default=dat.TEP_RECORD)
    ap.add_argument("--precheck", type=Path, default=PRECHECK)
    ap.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    ap.add_argument("--allow-uncommitted", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--allow-source-change", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--allow-env-change", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--allow-partial", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if not Path("src/ipis/module1_soft_sensor/phase1/stages.py").exists():
        sys.exit("run from the repository root")
    if args.verdicts:
        run_verdicts(args)
    elif args.stage == "A":
        run_stage_a(args)
    else:
        run_stage_b(args)


if __name__ == "__main__":
    main()
