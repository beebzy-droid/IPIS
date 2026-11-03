"""Shared style and I/O for the N1 paper's figures and tables (elsarticle, two columns).

Colours: the first three slots of the reference categorical palette (blue, orange, aqua), which
pass every colour-vision check on a white surface for all pairs; aqua is below 3:1 contrast on
white, so every series also carries its own marker and a legend entry, and no figure relies on
colour alone. Ink, gridlines and axes are neutral greys. Text is never set in a series colour.
matplotlib is optional at import (Agg is selected when it is installed), so the tables need
numpy alone.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ipis.module1_soft_sensor.phase1 import record as rc

try:  # the non-interactive backend, set before any module imports pyplot
    import matplotlib

    matplotlib.use("Agg")
except ImportError:  # the tables need no matplotlib
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "docs" / "paper" / "evidence"
FIGURE_DIR = REPO_ROOT / "docs" / "paper" / "figures" / "n1"
SINGLE_COL = 3.5  # inches (elsarticle single column)
DOUBLE_COL = 7.16

SERIES = ("#2a78d6", "#eb6834", "#1baf7a")  # blue, orange, aqua: categorical slots 1 to 3
MARKERS = ("o", "s", "D")
INK = {
    "primary": "#0b0b0b",
    "secondary": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
}


def apply_style() -> None:
    import matplotlib

    matplotlib.rcParams.update(
        {
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "legend.title_fontsize": 7,
            "lines.linewidth": 1.2,
            "lines.markersize": 4.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": INK["axis"],
            "axes.linewidth": 0.8,
            "axes.labelcolor": INK["primary"],
            "axes.grid": True,
            "grid.color": INK["grid"],
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "xtick.color": INK["secondary"],
            "ytick.color": INK["secondary"],
            "text.color": INK["primary"],
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
        }
    )


def _points(fig: Any, pt: float) -> float:
    """A length in points as a fraction of the figure's height."""
    return pt / (72.0 * fig.get_figheight())


def legend_below(
    fig: Any, handles: Sequence[Any], ncol: int, gap_pt: float = 4.0, **kw: Any
) -> Any:
    """A figure legend centred under the axes, below their tick and axis labels.

    The figure is drawn first, so the legend's place follows the fonts actually used.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    bottom = min(ax.get_tightbbox(renderer).transformed(inv).y0 for ax in fig.axes)
    x0 = min(ax.get_position().x0 for ax in fig.axes)
    x1 = max(ax.get_position().x1 for ax in fig.axes)
    return fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5 * (x0 + x1), bottom - _points(fig, gap_pt)),
        ncol=ncol,
        **kw,
    )


def header_above(fig: Any, axes: Sequence[Any], text: str, gap_pt: float = 3.0) -> Any:
    """A header centred over a group of axes, above their titles."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    top = max(ax.get_tightbbox(renderer).transformed(inv).y1 for ax in axes)  # incl. titles
    x0 = min(ax.get_position().x0 for ax in axes)
    x1 = max(ax.get_position().x1 for ax in axes)
    return fig.text(
        0.5 * (x0 + x1),
        top + _points(fig, gap_pt),
        text,
        ha="center",
        va="bottom",
        fontsize=8,
        color=INK["primary"],
    )


def load(name: str, in_dir: Path | None = None) -> dict[str, Any]:
    """A Phase 1 evidence file, with non-finite numbers restored (``record.read_evidence``)."""
    return rc.read_evidence((in_dir or EVIDENCE_DIR) / f"{name}.json")


def save_figure(fig: Any, name: str, out_dir: Path | None = None) -> list[Path]:
    """PDF (for the manuscript) and PNG (for review). The PDF carries no creation date, so the
    bytes repeat for a given matplotlib version."""
    import matplotlib.pyplot as plt

    d = out_dir or FIGURE_DIR
    d.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext, meta in (("pdf", {"CreationDate": None}), ("png", {})):
        p = d / f"{name}.{ext}"
        fig.savefig(p, metadata=meta)
        paths.append(p)
    plt.close(fig)
    return paths


def save_csv(
    rows: Sequence[Sequence[Any]], header: Sequence[str], name: str, out_dir: Path | None = None
) -> Path:
    """The numbers a figure shows, as a table beside it."""
    d = out_dir or FIGURE_DIR
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    return p
