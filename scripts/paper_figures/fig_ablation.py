"""F2 — Debutanizer feature ablation: CV robustness by feature philosophy.

Evidence: ablation_debutanizer.json from `scripts/run_ablation_debutanizer.py --json`.
"""

from __future__ import annotations

import numpy as np

from ipis.shared.evidence import load_evidence

from .style import PALETTE, SINGLE_COL, apply_style, save_figure

ORDER = ["u5_only", "physics_only", "physics_plus_u5", "lagged_raw"]
LABELS = {
    "u5_only": "u5 only",
    "physics_only": "physics",
    "physics_plus_u5": "physics+u5",
    "lagged_raw": "lagged raw",
}


def render(in_dir=None, out_dir=None) -> list:
    import matplotlib.pyplot as plt

    apply_style()
    ev = load_evidence("ablation_debutanizer", in_dir)
    arms = ev["arms"]
    names = [n for n in ORDER if n in arms] + [n for n in arms if n not in ORDER]

    x = np.arange(len(names))
    cv = [arms[n]["cv_mean"] for n in names]
    se = [arms[n]["cv_se"] for n in names]
    worst = [arms[n]["worst_fold"] for n in names]
    k = [arms[n]["n_features"] for n in names]

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.6))
    ax.bar(x, cv, 0.55, yerr=se, capsize=3, color=PALETTE["corrected"], label="CV mean ± SE")
    ax.scatter(x, worst, color=PALETTE["raw"], marker="_", s=220, lw=1.6, label="worst fold")
    ax.axhline(0.0, color="k", lw=0.6)
    ax.set_xticks(x, [f"{LABELS.get(n, n)}\n(k={kk})" for n, kk in zip(names, k, strict=True)])
    ax.set_ylabel("blocked-CV R²")
    ax.legend(frameon=False, loc="lower left")
    return save_figure(fig, "F2_feature_ablation", out_dir)


if __name__ == "__main__":
    for p in render():
        print(p)
