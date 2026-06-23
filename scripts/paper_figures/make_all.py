"""Render every paper figure whose evidence JSON exists; report what's missing.

set PYTHONPATH=src
python -m scripts.paper_figures.make_all
"""

from __future__ import annotations

import sys

from ipis.shared.evidence import EVIDENCE_DIR

from . import (
    fig_ablation,
    fig_architecture,
    fig_bias_trace,
    fig_coverage_tep,
    fig_efficiency,
    fig_secom_cv_path,
    fig_synthetic_stress,
)

REGISTRY = {
    "ablation_debutanizer": (
        "F2",
        fig_ablation.render,
        "scripts/run_ablation_debutanizer.py --json",
    ),
    "secom_cv_path": ("F3", fig_secom_cv_path.render, "scripts/secom_baseline.py --json"),
    "coverage_tep": ("F7", fig_coverage_tep.render, "scripts/conformal_eval.py --json"),
    "synthetic_stress": (
        "F6",
        fig_synthetic_stress.render,
        "scripts/conformal_synthetic_check.py --json",
    ),
    "bias_trace_debutanizer": ("F4", fig_bias_trace.render, "scripts/bias_update_eval.py --json"),
    "efficiency_tep": ("F5", fig_efficiency.render, "scripts/tep_migration.py --json"),
}


def main() -> int:
    missing = []
    for name, (fid, render, producer) in REGISTRY.items():
        if (EVIDENCE_DIR / f"{name}.json").exists():
            for p in render():
                print(f"  {fid}: {p}")
        else:
            missing.append((fid, name, producer))
    for p in fig_architecture.render():  # F1: scripted diagram, no evidence needed
        print(f"  F1: {p}")
    if missing:
        print("\nMissing evidence (run the producer, then re-run make_all):")
        for fid, name, producer in missing:
            print(f"  {fid}: {name}.json  <-  {producer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
