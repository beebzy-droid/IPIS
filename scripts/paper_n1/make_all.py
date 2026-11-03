"""Render every figure and table of the N1 paper from the Phase 1 evidence.

Run from the repository root (Windows cmd):
    set PYTHONPATH=src
    python -m scripts.paper_n1.make_all

Reads docs/paper/evidence/phase1_*.json (commit bd6454d and later); writes PDF, PNG and a CSV of
the plotted numbers for each figure, and a LaTeX body and a CSV for each table, to
docs/paper/figures/n1/. Nothing is computed that the evidence does not hold, except means and
t intervals over runs, ratios and rolling coverage, which the modules state.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import (
    fig_debutanizer,
    fig_diagnosis,
    fig_persistence,
    fig_speed_chart,
    fig_stability,
    tables,
)
from .style import REPO_ROOT

PARTS = {
    "stability": fig_stability.render,
    "diagnosis": fig_diagnosis.render,
    "speed_chart": fig_speed_chart.render,
    "persistence": fig_persistence.render,
    "debutanizer": fig_debutanizer.render,
    "tables": tables.render,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="N1 paper figures and tables")
    ap.add_argument("--only", nargs="+", choices=list(PARTS), default=list(PARTS))
    ap.add_argument("--evidence", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    for name in args.only:
        for p in PARTS[name](args.evidence, args.out):
            p = Path(p).resolve()
            shown = p.relative_to(REPO_ROOT) if p.is_relative_to(REPO_ROOT) else p
            print(f"  {name}: {shown.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
