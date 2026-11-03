"""Claim 2' (F8): compensation makes the miss process less persistent and admits a larger step.

(a) The integrated autocorrelation time (IACT) of the open-loop miss indicator at T1, theta = 4,
uncompensated and compensated, one line per run, with the mean and its 95 % t interval.
(b) The sequential loop's step size tuned by replay to eps / 2, per TEP regime.
Evidence: phase1_stageB_T1.json (`open_loop`), phase1_stageA_T1.json (`tuning`),
phase1_verdicts.json (F8).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.phase1 import rules

from .style import DOUBLE_COL, INK, SERIES, apply_style, load, save_csv, save_figure

THETA = "4"


def num(x: float, d: int = 2) -> str:
    """A number with a typographic minus sign."""
    return f"{x:.{d}f}".replace("-", "\N{MINUS SIGN}")


COMPS = (("raw", "uncompensated", SERIES[1]), ("comp", "compensated", SERIES[0]))


def render(in_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    import matplotlib.pyplot as plt

    apply_style()
    b = load("phase1_stageB_T1", in_dir)
    a = load("phase1_stageA_T1", in_dir)
    v = load("phase1_verdicts", in_dir)
    runs = list(b["streams"])
    iact = {c: np.array([b["open_loop"][THETA][c][k]["iact"] for k in runs]) for c, _, _ in COMPS}
    f8 = v["decided"]["F8"]
    diff = iact["comp"] - iact["raw"]
    if not np.allclose(diff, f8["iact_diff_per_run"], rtol=0, atol=1e-9):
        raise ValueError("the open-loop IACT does not match the F8 record")

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(DOUBLE_COL, 2.5), gridspec_kw={"width_ratios": [1.0, 1.15]}
    )
    for i in range(len(runs)):
        ax_a.plot([0, 1], [iact["raw"][i], iact["comp"][i]], color=INK["grid"], lw=0.9, zorder=1)
    for x, (c, _label, colour) in enumerate(COMPS):
        m = rules.t_interval(iact[c], 0.95)
        ax_a.errorbar(
            [x],
            [m["mean"]],
            yerr=[[m["mean"] - m["lo"]], [m["hi"] - m["mean"]]],
            color=colour,
            marker="o",
            ms=6,
            mec="white",
            mew=0.8,
            capsize=3,
            elinewidth=1.0,
            zorder=3,
        )
        ax_a.scatter(
            np.full(len(runs), x),
            iact[c],
            s=10,
            color=colour,
            alpha=0.55,
            edgecolors="none",
            zorder=2,
        )
    ci = f8["ci95"]
    ax_a.annotate(
        f"difference {num(ci['mean'])}\n95 % CI [{num(ci['lo'])}, {num(ci['hi'])}]",
        (0.98, 0.98),
        xycoords="axes fraction",
        ha="right",
        va="top",
        fontsize=7,
        color=INK["secondary"],
    )
    ax_a.set_xticks([0, 1], [label for _, label, _ in COMPS])
    ax_a.set_xlim(-0.35, 1.35)
    ax_a.set_ylabel("IACT of the open-loop misses")
    ax_a.set_title(r"(a) T1, $\theta$ = 4, 15 runs", loc="left", color=INK["primary"])
    ax_a.grid(axis="x", visible=False)

    plants = list(a["tuning"])
    steps = {
        c: [a["tuning"][p][THETA][c]["sequential"]["aware_half"]["gamma"] for p in plants]
        for c, _, _ in COMPS
    }
    y = np.arange(len(plants))[::-1]
    for i in range(len(plants)):
        ax_b.plot(
            [steps["raw"][i], steps["comp"][i]], [y[i], y[i]], color=INK["grid"], lw=2.0, zorder=1
        )
    # where the two step sizes are equal, the marks are offset vertically so both stay visible
    equal = np.isclose(steps["raw"], steps["comp"], rtol=0.0, atol=1e-12)
    dy = {"raw": 0.1, "comp": -0.1}
    for c, label, colour in COMPS:
        ax_b.scatter(
            steps[c],
            y + np.where(equal, dy[c], 0.0),
            s=36,
            color=colour,
            edgecolors="white",
            linewidths=0.8,
            zorder=3,
            label=label,
        )
    ax_b.set_yticks(y, [p.replace("mode", "mode ") for p in plants])
    ax_b.set_xlim(0.0, 0.01)
    ax_b.set_xlabel(r"step size $\gamma$, replay to $\varepsilon/2$")
    ax_b.set_title("(b) tuned step size by regime", loc="left", color=INK["primary"])
    ax_b.legend(loc="lower left")
    ax_b.grid(axis="y", visible=False)
    paths = save_figure(fig, "n1_persistence", out_dir)
    table = [[k, iact["raw"][i], iact["comp"][i]] for i, k in enumerate(runs)]
    table += [[p, steps["raw"][i], steps["comp"][i]] for i, p in enumerate(plants)]
    paths.append(
        save_csv(
            table, ["run_or_regime", "uncompensated", "compensated"], "n1_persistence", out_dir
        )
    )
    return paths


if __name__ == "__main__":
    for p in render():
        print(p)
