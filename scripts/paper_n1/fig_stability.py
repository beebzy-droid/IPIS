"""The stability limit against the step sizes that hold the budget.

gamma_crit(theta) = 2 sin(pi / (4 theta + 2)) (P1), the replay's cap 0.8 gamma_crit, the
white-noise rule `design_gamma`, and the sequential loop's step sizes tuned by replay to eps / 2 in
stage A, uncompensated and compensated: per TEP regime for T1 and T2, and for the debutanizer.
Evidence: phase1_stageA_{T1,T2,debutanizer}.json.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.evaluation import delayed_aci as d

from .style import (
    INK,
    MARKERS,
    SERIES,
    SINGLE_COL,
    apply_style,
    legend_below,
    load,
    save_csv,
    save_figure,
)

UNITS = (("T1", "T1, 3-min updates"), ("T2", "T2, 1-min updates"), ("debutanizer", "Debutanizer"))
COMPS = (("raw", "uncompensated", SERIES[1]), ("comp", "compensated", SERIES[0]))
UNIT_DX = {"T1": -0.22, "T2": 0.0, "debutanizer": 0.22}
COMP_DX = {"raw": -0.07, "comp": 0.07}


def tuned_steps(in_dir: Path | None = None) -> list[tuple[str, str, int, str, float, bool]]:
    """(unit, plant, theta, comp, gamma, feasible) of the sequential loop tuned to eps / 2."""
    rows = []
    for unit, _ in UNITS:
        a = load(f"phase1_stageA_{unit}", in_dir)
        for plant, by_theta in a["tuning"].items():
            for th, by_comp in by_theta.items():
                for comp, _, _ in COMPS:
                    v = by_comp[comp]["sequential"]["aware_half"]
                    rows.append(
                        (unit, plant, int(th), comp, float(v["gamma"]), bool(v["feasible"]))
                    )
    return rows


def render(in_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    apply_style()
    rows = tuned_steps(in_dir)
    theta = np.arange(0, 15)
    crit = np.array([d.gamma_crit(int(t)) for t in theta])
    design = np.array([d.design_gamma(int(t)) for t in theta])

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.7))
    ax.plot(theta, crit, color=INK["primary"], lw=1.0, zorder=2)
    ax.plot(theta, 0.8 * crit, color=INK["muted"], lw=0.8, zorder=2)
    ax.plot(theta, design, color=SERIES[2], lw=1.0, marker="^", ms=3, zorder=2)
    ax.annotate(
        r"stability limit $\gamma_{crit}$",
        (14, crit[-1]),
        xytext=(-2, 4),
        textcoords="offset points",
        ha="right",
        va="bottom",
        fontsize=7,
        color=INK["primary"],
    )
    ax.annotate(
        r"replay cap $0.8\,\gamma_{crit}$",
        (14, 0.8 * crit[-1]),
        xytext=(-2, -4),
        textcoords="offset points",
        ha="right",
        va="top",
        fontsize=7,
        color=INK["secondary"],
    )
    ax.annotate(
        "white-noise rule",
        (14, design[-1]),
        xytext=(-2, -5),
        textcoords="offset points",
        ha="right",
        va="top",
        fontsize=7,
        color=INK["secondary"],
    )
    for (unit, _), marker in zip(UNITS, MARKERS, strict=True):
        for comp, _, colour in COMPS:
            pts = [(t, g) for u, _, t, c, g, _ in rows if u == unit and c == comp]
            x = np.array([t for t, _ in pts]) + UNIT_DX[unit] + COMP_DX[comp]
            y = np.array([g for _, g in pts])
            ax.scatter(
                x,
                y,
                s=16,
                marker=marker,
                color=colour,
                edgecolors="white",
                linewidths=0.6,
                zorder=3,
            )
    ax.set_yscale("log")
    ax.set_ylim(5e-4, 3.0)
    ax.set_xlim(-0.6, 14.6)
    ax.set_xticks([0, 1, 2, 3, 4, 7, 12, 14])
    ax.set_xlabel(r"dead time $\theta$ (calibrator updates)")
    ax.set_ylabel(r"step size $\gamma$")
    comp_h = [Line2D([], [], ls="", marker="o", color=c, label=lab) for _, lab, c in COMPS]
    unit_h = [
        Line2D([], [], ls="", marker=m, color=INK["muted"], label=lab)
        for (_, lab), m in zip(UNITS, MARKERS, strict=True)
    ]
    blank = Line2D([], [], ls="", label=" ")
    # column-major fill: row 1 the two arms of the comparison, row 2 the three units
    handles = [comp_h[0], unit_h[0], comp_h[1], unit_h[1], blank, unit_h[2]]
    legend_below(fig, handles, ncol=3, handletextpad=0.3, columnspacing=1.0)
    paths = save_figure(fig, "n1_stability", out_dir)
    table = [[u, p, t, c, g, f] for u, p, t, c, g, f in rows]
    table += [
        ["gamma_crit", "", int(t), "", float(v), ""] for t, v in zip(theta, crit, strict=True)
    ]
    table += [
        ["design_gamma", "", int(t), "", float(v), ""] for t, v in zip(theta, design, strict=True)
    ]
    paths.append(
        save_csv(
            table,
            ["series", "plant", "theta", "comp", "gamma", "feasible"],
            "n1_stability",
            out_dir,
        )
    )
    return paths


if __name__ == "__main__":
    for p in render():
        print(p)
