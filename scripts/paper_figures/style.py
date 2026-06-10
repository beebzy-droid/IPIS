"""Shared matplotlib style for CACE figures (elsarticle column widths)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SINGLE_COL = 3.5  # inches (elsarticle single column)
DOUBLE_COL = 7.16
FIGURE_DIR = Path("docs/paper/figures")

PALETTE = {
    "aci": "#4C78A8",
    "split": "#E45756",
    "enbpi": "#72B7B2",
    "migrated": "#4C78A8",
    "scratch": "#E45756",
    "generic": "#B279A2",
    "raw": "#E45756",
    "corrected": "#4C78A8",
    "neutral": "#54585A",
}


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "lines.linewidth": 1.2,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 200,
            "savefig.bbox": "tight",
        }
    )


def save_figure(fig, name: str, out_dir: str | Path | None = None) -> list[Path]:
    """Save PNG (review/draft) + PDF (submission) and return both paths."""
    d = Path(out_dir) if out_dir else FIGURE_DIR
    d.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("png", "pdf"):
        p = d / f"{name}.{ext}"
        fig.savefig(p)
        paths.append(p)
    return paths
