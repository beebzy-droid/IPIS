"""F7 — Real-TEP coverage by regime × method × θ vs the 0.90 target.

Evidence: coverage_tep.json from `scripts/conformal_eval.py --json`:
{"target": 0.9, "regimes": {"mode1": {"2": {"split": {"cov":..,"width":..},
"aci": {...}, "enbpi": {...}}, "5": {...}}, ...}}
"""

from __future__ import annotations

import numpy as np

from ipis.shared.evidence import load_evidence

from .style import DOUBLE_COL, PALETTE, apply_style, save_figure

METHODS = ("split", "aci", "enbpi")


def render(in_dir=None, out_dir=None) -> list:
    import matplotlib.pyplot as plt

    apply_style()
    ev = load_evidence("coverage_tep", in_dir)
    target = float(ev.get("target", 0.90))
    regimes = ev["regimes"]
    thetas = sorted({t for r in regimes.values() for t in r}, key=int)

    fig, axes = plt.subplots(1, len(thetas), figsize=(DOUBLE_COL, 2.4), sharey=True, squeeze=False)
    all_covs = [
        regimes[r][t][m]["cov"]
        for r in regimes
        for t in regimes[r]
        for m in METHODS
        if m in regimes[r][t]
    ]
    y_lo = min(0.75, max(0.0, min(all_covs) - 0.05))
    width = 0.8 / len(METHODS)
    for j, theta in enumerate(thetas):
        ax = axes[0][j]
        names = sorted(regimes)
        x = np.arange(len(names))
        for k, m in enumerate(METHODS):
            covs = [regimes[r][theta][m]["cov"] for r in names if m in regimes[r][theta]]
            if len(covs) != len(names):
                continue  # method absent for this regime set
            ax.bar(
                x + (k - 1) * width,
                covs,
                width,
                label=m.upper() if j == 0 else None,
                color=PALETTE[m],
            )
        ax.axhline(target, color="k", lw=0.8, ls="--")
        ax.set_xticks(x, names)
        ax.set_title(f"θ = {theta}")
        ax.set_ylim(y_lo, 1.0)
        if j == 0:
            ax.set_ylabel("empirical coverage")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(
        handles, labels, frameon=False, ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.10)
    )
    return save_figure(fig, "F7_tep_coverage", out_dir)


if __name__ == "__main__":
    for p in render():
        print(p)
