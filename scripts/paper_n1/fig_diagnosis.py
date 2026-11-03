"""The diagnosis: uninformative intervals rise with the dead time while coverage reads nominal.

Sequential loop, stored pairing, three step-size policies (delay-blind, the white-noise rule,
replay to eps / 2), uncompensated and compensated, at every theta of T1 (3-min updates) and T2
(1-min updates). Mean over the 15 TEP runs with its 95 % t interval (stage B summaries).
The two panels of an arm share their y scale; the arms do not (their theta grids differ).
Evidence: phase1_stageB_{T1,T2}.json, `summary.cells`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .style import (
    DOUBLE_COL,
    INK,
    MARKERS,
    SERIES,
    apply_style,
    header_above,
    legend_below,
    load,
    save_csv,
    save_figure,
)

ARMS = (("T1", "T1: 3-min updates"), ("T2", "T2: 1-min updates"))
COMPS = (("raw", "uncompensated"), ("comp", "compensated"))
POLICIES = (
    ("aware_half", r"replay to $\varepsilon/2$", SERIES[0]),
    ("blind", "delay-blind", SERIES[1]),
    ("design", "white-noise rule", SERIES[2]),
)
METRICS = (("u", 100.0, "uninformative intervals U (%)"), ("coverage", 1.0, "coverage"))
BUDGET = 0.02
NOMINAL = 0.90
DX = {"aware_half": -0.14, "blind": 0.0, "design": 0.14}


def cells(in_dir: Path | None = None) -> list[tuple[str, int, str, str, str, float, float, float]]:
    """(arm, theta, comp, policy, metric, mean, lo, hi) for U and coverage."""
    out = []
    for arm, _ in ARMS:
        b = load(f"phase1_stageB_{arm}", in_dir)
        for th in b["thetas"]:
            for comp, _ in COMPS:
                for pol, _, _ in POLICIES:
                    c = b["summary"]["cells"][f"theta={th}|{comp}|sequential|{pol}|stored"]
                    for metric, _, _ in METRICS:
                        m = c[metric]
                        out.append((arm, int(th), comp, pol, metric, m["mean"], m["lo"], m["hi"]))
    return out


def render(in_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    apply_style()
    rows = cells(in_dir)
    fig = plt.figure(figsize=(DOUBLE_COL, 3.3))
    gs = fig.add_gridspec(2, 5, width_ratios=[1, 1, 0.22, 1, 1], wspace=0.12, hspace=0.18)
    panel = 0
    groups = []
    for a, (arm, header) in enumerate(ARMS):
        thetas = sorted({r[1] for r in rows if r[0] == arm})
        pos = {t: i for i, t in enumerate(thetas)}
        group = []
        for c, (comp, comp_label) in enumerate(COMPS):
            col = 3 * a + c
            for row, (metric, scale, ylabel) in enumerate(METRICS):
                ax = fig.add_subplot(gs[row, col])
                for (pol, _label, colour), marker in zip(POLICIES, MARKERS, strict=True):
                    pts = sorted(
                        (t, m, lo, hi)
                        for ar, t, cp, p, mm, m, lo, hi in rows
                        if ar == arm and cp == comp and p == pol and mm == metric
                    )
                    x = np.array([pos[t] for t, *_ in pts]) + DX[pol]
                    y = np.array([m for _, m, _, _ in pts]) * scale
                    err = np.array([[m - lo, hi - m] for _, m, lo, hi in pts]).T * scale
                    ax.errorbar(
                        x,
                        y,
                        yerr=err,
                        color=colour,
                        marker=marker,
                        lw=1.1,
                        capsize=1.5,
                        elinewidth=0.7,
                        markeredgecolor="white",
                        markeredgewidth=0.5,
                    )
                ref = 100 * BUDGET if metric == "u" else NOMINAL
                ax.axhline(ref, color=INK["muted"], lw=0.8, zorder=1)
                ax.set_xlim(-0.45, len(thetas) - 0.55)
                ax.set_xticks(range(len(thetas)), [str(t) for t in thetas])
                if row == 0:
                    ax.set_title(f"({'abcd'[panel]}) {comp_label}", loc="left")
                    ax.tick_params(labelbottom=False)
                    panel += 1
                    group.append(ax)
                else:
                    ax.set_xlabel(r"dead time $\theta$")
                if col == 0:
                    ax.set_ylabel(ylabel)
        groups.append((group, header))
    axes = np.array(fig.axes).reshape(4, 2).T  # rows U, coverage; columns in panel order
    for row in range(2):
        for a in range(2):
            left, right = axes[row, 2 * a], axes[row, 2 * a + 1]
            if row == 0:
                hi = max(left.get_ylim()[1], right.get_ylim()[1])
                lim = (min(left.get_ylim()[0], right.get_ylim()[0]), hi)
            else:
                lim = (0.85, 0.95)
            left.set_ylim(*lim)
            right.set_ylim(*lim)
            right.tick_params(labelleft=False)
    fig.align_ylabels(axes[:, 0])
    for group, header in groups:
        header_above(fig, group, header)
    handles = [
        Line2D([], [], color=colour, marker=marker, mec="white", mew=0.5, label=label)
        for (_, label, colour), marker in zip(POLICIES, MARKERS, strict=True)
    ]
    handles.append(
        Line2D([], [], color=INK["muted"], lw=0.8, label="U budget (2 %), nominal coverage (0.90)")
    )
    legend_below(fig, handles, ncol=4, handletextpad=0.4, columnspacing=1.4)
    paths = save_figure(fig, "n1_diagnosis", out_dir)
    paths.append(
        save_csv(
            rows,
            ["arm", "theta", "comp", "policy", "metric", "mean", "lo95", "hi95"],
            "n1_diagnosis",
            out_dir,
        )
    )
    return paths


if __name__ == "__main__":
    for p in render():
        print(p)
