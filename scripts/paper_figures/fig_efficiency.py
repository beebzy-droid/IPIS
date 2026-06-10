"""F5 — Regime-migration data-efficiency curves (TEP mode→mode).

Evidence: efficiency_tep.json from `scripts/tep_migration.py --json`:
{"method": "yan", "targets": {"mode2": {<SweepResult asdict>}, ...}}
"""

from __future__ import annotations

import numpy as np

from ipis.shared.evidence import load_evidence

from .style import DOUBLE_COL, PALETTE, apply_style, save_figure


def render(in_dir=None, out_dir=None) -> list:
    import matplotlib.pyplot as plt

    apply_style()
    ev = load_evidence("efficiency_tep", in_dir)
    methods = ev["methods"]
    method = "yan" if "yan" in methods else sorted(methods)[0]
    run = methods[method]
    targets = run["targets"]

    fig, axes = plt.subplots(1, len(targets), figsize=(DOUBLE_COL, 2.4), sharey=True, squeeze=False)
    for j, (name, r) in enumerate(sorted(targets.items())):
        ax = axes[0][j]
        f = np.asarray(r["fractions"], float)
        mig = np.asarray(r["migrated_r2"], float)
        fs = np.asarray(r["from_scratch_same_r2"], float)
        if r.get("migrated_r2_std"):
            ax.errorbar(
                f,
                mig,
                yerr=r["migrated_r2_std"],
                color=PALETTE["migrated"],
                marker="o",
                ms=3,
                capsize=2,
                label="migrated",
            )
        else:
            ax.plot(f, mig, color=PALETTE["migrated"], marker="o", ms=3, label="migrated")
        ax.plot(f, fs, color=PALETTE["scratch"], marker="s", ms=3, label="from scratch")
        bar = float(r.get("bar_same_r2", np.nan))
        if np.isfinite(bar):
            ax.axhline(
                r.get("target_level", 0.9) * bar,
                color="k",
                lw=0.8,
                ls="--",
                label="90% of ceiling" if j == 0 else None,
            )
        de = r.get("data_efficiency")
        title = f"{method} → {name}"
        if de:
            title += f"  (efficiency {de:.1f}×)"
        ax.set_title(title)
        ax.set_xlabel("target-data fraction")
        if j == 0:
            ax.set_ylabel("held-out R²")
    axes[0][0].legend(frameon=False, loc="lower right")
    return save_figure(fig, "F5_data_efficiency", out_dir)


if __name__ == "__main__":
    for p in render():
        print(p)
