"""The analyzer-speed chart (P3): width ratio, compensated over uncompensated, against label age.

Predicted in stage A from each run's calibration autocorrelation, before any evaluation row;
measured in stage B as the ratio of the static 90 % quantiles of the evaluation scores. TEP:
mean over the 15 runs with the 95 % t interval of the measured mean, label age in minutes,
(theta + 1) times the update interval. Debutanizer: one stream, label age in samples (the
file's sampling interval is documented as 6 or 12 min; pre-registration Section 2).
Where two arms share a label age (15 min: T1 at theta = 4, T2 at 14, T3 at 0), their marks are
offset by 0.45 min so that each stays visible; the CSV holds the true ages.
Evidence: phase1_stageA_*.json (`predictions`) and phase1_stageB_*.json (`measured_ratio`).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.phase1 import rules

from .style import DOUBLE_COL, INK, MARKERS, SERIES, apply_style, load, save_csv, save_figure

TEP_ARMS = (
    ("T1", "T1: 3-min updates", 3.0),
    ("T2", "T2: 1-min updates", 1.0),
    ("T3", "T3: one update per analyzer value", 15.0),
)
ARM_DX = {"T1": -0.45, "T2": 0.0, "T3": 0.45}  # minutes; applied only where the arms' ages coincide


def ratios(unit: str, in_dir: Path | None = None) -> list[tuple[int, float, float, float, float]]:
    """(theta, predicted mean, measured mean, measured lo95, measured hi95) over the unit's runs."""
    a = load(f"phase1_stageA_{unit}", in_dir)
    b = load(f"phase1_stageB_{unit}", in_dir)
    out = []
    for th in b["thetas"]:
        pred = a["predictions"][str(th)]["per_stream"]
        meas = b["measured_ratio"][str(th)]
        keys = list(pred)
        m = rules.t_interval([meas[k] for k in keys], 0.95)
        out.append((int(th), float(np.mean([pred[k] for k in keys])), m["mean"], m["lo"], m["hi"]))
    return out


def render(in_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    apply_style()
    fig, (ax_t, ax_d) = plt.subplots(
        1, 2, figsize=(DOUBLE_COL, 2.7), gridspec_kw={"width_ratios": [1.35, 1.0]}
    )
    table = []
    tep = {unit: ratios(unit, in_dir) for unit, _, _ in TEP_ARMS}
    ages = [(th + 1) * du for unit, _, du in TEP_ARMS for th, *_ in tep[unit]]
    shared = {x for x in ages if ages.count(x) > 1}
    for (unit, label, du), colour, marker in zip(TEP_ARMS, SERIES, MARKERS, strict=True):
        r = tep[unit]
        age = np.array(
            [(th + 1) * du + (ARM_DX[unit] if (th + 1) * du in shared else 0.0) for th, *_ in r]
        )
        pred = np.array([p for _, p, _, _, _ in r])
        meas = np.array([m for _, _, m, _, _ in r])
        err = np.array([[m - lo, hi - m] for _, _, m, lo, hi in r]).T
        ax_t.plot(
            age,
            pred,
            color=colour,
            lw=1.0,
            marker=marker,
            mfc="white",
            mec=colour,
            mew=1.0,
            label=label,
        )
        ax_t.errorbar(
            age,
            meas,
            yerr=err,
            color=colour,
            ls="",
            marker=marker,
            mec="white",
            mew=0.5,
            capsize=2,
            elinewidth=0.8,
        )
        table += [[unit, th, (th + 1) * du, p, m, lo, hi] for th, p, m, lo, hi in r]
    ax_t.set_xlabel("label age (min)")
    ax_t.set_ylabel("width ratio, compensated / uncompensated")
    ax_t.set_title("TEP, 15 runs", loc="left", color=INK["primary"])
    ax_t.set_xticks([1, 3, 5, 9, 15])
    r = ratios("debutanizer", in_dir)
    age = np.array([th + 1 for th, *_ in r])
    ax_d.plot(
        age,
        [p for _, p, *_ in r],
        color=SERIES[0],
        lw=1.0,
        marker="o",
        mfc="white",
        mec=SERIES[0],
        mew=1.0,
    )
    ax_d.plot(
        age, [m for _, _, m, _, _ in r], color=SERIES[0], ls="", marker="o", mec="white", mew=0.5
    )
    table += [["debutanizer", th, th + 1, p, m, "", ""] for th, p, m, _, _ in r]  # one stream
    ax_d.set_xlabel("label age (samples)")
    ax_d.set_title("Debutanizer, one stream", loc="left", color=INK["primary"])
    ax_d.set_xticks(list(age))
    for ax in (ax_t, ax_d):
        ax.set_ylim(0.0, 1.05)
        ax.axhline(1.0, color=INK["muted"], lw=0.8, zorder=1)
    handles, labels = ax_t.get_legend_handles_labels()
    handles += [
        Line2D([], [], ls="-", marker="o", color=INK["muted"], mfc="white", label="predicted (P3)"),
        Line2D([], [], ls="", marker="o", color=INK["muted"], label="measured"),
    ]
    ax_t.legend(handles=handles, loc="lower right", handletextpad=0.4)
    paths = save_figure(fig, "n1_speed_chart", out_dir)
    paths.append(
        save_csv(
            table,
            [
                "unit",
                "theta",
                "label_age",
                "predicted_mean",
                "measured_mean",
                "measured_lo95",
                "measured_hi95",
            ],
            "n1_speed_chart",
            out_dir,
        )
    )
    return paths


if __name__ == "__main__":
    for p in render():
        print(p)
