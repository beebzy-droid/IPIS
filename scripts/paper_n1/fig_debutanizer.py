"""Debutanizer (descriptive): coverage over trailing windows of 100 evaluation rows, theta = 3.

Split conformal (loop off) against the delayed sequential loop tuned by replay to eps / 2,
without and with compensation, from the per-step flags of stage B. The legend gives the coverage
over all evaluation rows.
Evidence: phase1_stageB_debutanizer_steps.json; phase1_stageB_debutanizer.json for the
worst rolling coverage each panel reports.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.phase1 import metrics as mt

from .style import DOUBLE_COL, INK, SERIES, apply_style, load, save_csv, save_figure

THETA = 3
NOMINAL = 0.90
PANELS = (("raw", "(a) uncompensated"), ("comp", "(b) compensated"))
LOOPS = (
    ("sequential|aware_half", "delayed loop", SERIES[0]),
    ("none|-", "split conformal", SERIES[1]),
)


def flags(steps: dict, key: str) -> np.ndarray:
    return np.array([c == "1" for c in steps[key]["cov"]], dtype=bool)


def render(in_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    import matplotlib.pyplot as plt

    apply_style()
    steps = load("phase1_stageB_debutanizer_steps", in_dir)["steps"]
    b = load("phase1_stageB_debutanizer", in_dir)
    stream = b["streams"][0]
    fig, axes = plt.subplots(1, 2, figsize=(DOUBLE_COL, 2.4), sharey=True)
    table: dict[str, np.ndarray] = {}
    for ax, (comp, title) in zip(axes, PANELS, strict=True):
        for loop, label, colour in LOOPS:
            key = f"theta={THETA}|{comp}|{loop}|stored"
            cov = flags(steps, key)
            roll = mt.rolling(cov)
            cell = b["cells"][key][stream]
            if not np.isclose(roll.min(), cell["local_cov_min"], atol=1e-12):
                raise ValueError(f"{key}: rolling coverage does not match the stage B record")
            x = np.arange(mt.LOCAL, cov.size + 1)
            ax.plot(x, roll, color=colour, lw=1.1, label=f"{label}: {cell['coverage']:.3f}")
            table[f"{comp}|{loop}"] = roll
        ax.axhline(NOMINAL, color=INK["muted"], lw=0.8, zorder=1, label=f"nominal: {NOMINAL:.3f}")
        ax.set_title(title, loc="left", color=INK["primary"])
        ax.set_xlabel("evaluation row (end of the 100-row window)")
        ax.set_ylim(0.0, 1.02)
        ax.legend(loc="lower left", title="coverage, all rows")
    axes[0].set_ylabel("coverage over the last 100 rows")
    paths = save_figure(fig, "n1_debutanizer", out_dir)
    keys = list(table)
    rows = [
        [int(i + mt.LOCAL), *[round(float(table[k][i]), 4) for k in keys]]
        for i in range(len(table[keys[0]]))
    ]  # multiples of 1/100, rounded for stable text
    paths.append(save_csv(rows, ["window_end_row", *keys], "n1_debutanizer", out_dir))
    return paths


if __name__ == "__main__":
    for p in render():
        print(p)
