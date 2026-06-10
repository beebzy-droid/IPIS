"""F4 — Held-out residual trace, raw vs bias-corrected (Debutanizer).

Evidence: bias_trace_debutanizer.json from `scripts/bias_update_eval.py --json`:
{"y": [...], "raw_pred": [...], "corrected_pred": [...], "lam":, "theta":}
"""

from __future__ import annotations

import numpy as np

from ipis.shared.evidence import load_evidence

from .style import DOUBLE_COL, PALETTE, apply_style, save_figure


def render(in_dir=None, out_dir=None) -> list:
    import matplotlib.pyplot as plt

    apply_style()
    ev = load_evidence("bias_trace_debutanizer", in_dir)
    y = np.asarray(ev["y"], float)
    raw = y - np.asarray(ev["raw_pred"], float)
    cor = y - np.asarray(ev["corrected_pred"], float)
    t = np.arange(len(y))

    fig, ax = plt.subplots(figsize=(DOUBLE_COL, 2.2))
    ax.plot(t, raw, color=PALETTE["raw"], alpha=0.85, label=f"raw residual (sd {np.std(raw):.3f})")
    ax.plot(
        t,
        cor,
        color=PALETTE["corrected"],
        alpha=0.85,
        label=f"corrected residual (sd {np.std(cor):.3f}, λ={ev['lam']:g}, θ={ev['theta']})",
    )
    ax.axhline(0.0, color="k", lw=0.6)
    ax.set_xlabel("held-out test sample")
    ax.set_ylabel("residual")
    ax.legend(frameon=False, ncols=2, loc="upper right")
    return save_figure(fig, "F4_bias_trace", out_dir)


if __name__ == "__main__":
    for p in render():
        print(p)
