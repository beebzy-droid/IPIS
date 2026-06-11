"""F6 — Rolling coverage under a controlled residual-scale regime shift (synthetic).

Evidence: synthetic_stress.json from `scripts/conformal_synthetic_check.py --json`.
"""

from __future__ import annotations

import numpy as np

from ipis.shared.evidence import load_evidence

from .style import DOUBLE_COL, PALETTE, apply_style, save_figure


def render(in_dir=None, out_dir=None) -> list:
    import matplotlib.pyplot as plt

    apply_style()
    ev = load_evidence("synthetic_stress", in_dir)
    r = ev["rolling"]
    s = ev["summary"]
    target, boundary = float(ev["target"]), int(ev["boundary"])

    fig, ax = plt.subplots(figsize=(DOUBLE_COL, 2.4))
    for key, label in (
        ("split", f"split (static; post {s['split']['post']:.3f})"),
        ("aci", f"ACI (post {s['aci']['post']:.3f}, γ={ev['gamma']:.3f})"),
        ("enbpi", f"EnbPI (post {s['enbpi']['post']:.3f})"),
    ):
        ax.plot(np.asarray(r[key], float), color=PALETTE[key], label=label)
    ax.axhline(target, color="k", ls="--", lw=0.8)
    ax.axvline(boundary, color="grey", ls=":", lw=0.8)
    ax.set_xlabel(f"time step (trailing {ev['window']}-step coverage); shift at t={boundary}")
    ax.set_ylabel("rolling coverage")
    ax.set_ylim(0.35, 1.02)
    ax.legend(frameon=False, loc="lower left", ncols=1)
    return save_figure(fig, "F6_synthetic_stress", out_dir)


if __name__ == "__main__":
    for p in render():
        print(p)
