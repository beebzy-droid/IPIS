"""F3 — SECOM elastic-net CV path: the p~n selection lottery and the one-SE rescue.

Evidence: secom_cv_path.json from `scripts/secom_baseline.py --json`.
"""

from __future__ import annotations

import numpy as np

from ipis.shared.evidence import load_evidence

from .style import PALETTE, SINGLE_COL, apply_style, save_figure


def render(in_dir=None, out_dir=None) -> list:
    import matplotlib.pyplot as plt

    apply_style()
    ev = load_evidence("secom_cv_path", in_dir)
    alphas = np.asarray(ev["alphas"], float)
    mean = np.asarray(ev["cv_mean"], float)
    se = np.asarray(ev["cv_se"], float)
    i_star = int(ev["one_se_index"])
    i_best = int(ev["best_index"])

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.4))
    # negative R2 spanning orders of magnitude: plot -R2 on log y
    y = -mean
    ax.errorbar(alphas, y, yerr=se, color=PALETTE["neutral"], marker="o", ms=3, capsize=2)
    ax.scatter(
        [alphas[i_star]],
        [y[i_star]],
        color=PALETTE["aci"],
        zorder=5,
        label=f"one-SE pick (α={alphas[i_star]:g})",
    )
    ax.scatter(
        [alphas[i_best]],
        [y[i_best]],
        color=PALETTE["split"],
        zorder=5,
        marker="s",
        label="best CV mean",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.invert_xaxis()  # left -> right = weaker shrinkage = more complex
    ax.set_xlabel("elastic-net α (shrinkage; complexity increases →)")
    ax.set_ylabel("−(CV R²)  (lower is better)")
    ax.legend(frameon=False, loc="upper left")
    return save_figure(fig, "F3_secom_cv_path", out_dir)


if __name__ == "__main__":
    for p in render():
        print(p)
