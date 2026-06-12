"""F1 — Framework + serving architecture diagram (scripted; no evidence needed).

Panel (a): the offline/online framework pipeline. Panel (b): the two-flow stateful
serving core with the delayed-label/stored-interval invariant.
"""

from __future__ import annotations

from .style import DOUBLE_COL, PALETTE, apply_style, save_figure

BLUE, RED, TEAL, GREY = (
    PALETTE["corrected"],
    PALETTE["raw"],
    PALETTE["enbpi"],
    PALETTE["neutral"],
)


def _box(ax, x, y, w, h, text, color, fs=6.5):
    from matplotlib.patches import FancyBboxPatch

    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012",
            facecolor=color,
            edgecolor="none",
            alpha=0.18,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.012", facecolor="none", edgecolor=color, lw=1.0
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def _arrow(ax, x0, y0, x1, y1, color=GREY, ls="-"):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops={"arrowstyle": "->", "color": color, "lw": 1.0, "linestyle": ls},
    )


def render(out_dir=None) -> list:
    import matplotlib.pyplot as plt

    apply_style()
    fig, (a, b) = plt.subplots(1, 2, figsize=(DOUBLE_COL, 2.7))
    for ax in (a, b):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    # ---------------- panel (a): framework pipeline ----------------
    a.set_title("(a) framework", fontsize=8)
    _box(a, 0.02, 0.72, 0.27, 0.18, "process data\n+ transport-lag\ndiagnosis", GREY)
    _box(a, 0.36, 0.72, 0.27, 0.18, "physics features\n(bubble point,\nα(T), stripping)", BLUE)
    _box(a, 0.70, 0.72, 0.28, 0.18, "blocked CV\n+ one-SE\nselection", BLUE)
    _box(a, 0.70, 0.40, 0.28, 0.18, "linear sensor\n(frozen bundle)", GREY)
    _box(a, 0.36, 0.40, 0.27, 0.18, "bias-update\n(EWMA, delay θ)", RED)
    _box(a, 0.02, 0.40, 0.27, 0.18, "ACI conformal\ninterval", TEAL)
    _box(a, 0.36, 0.08, 0.27, 0.18, "drift detector\n(on corrected)", RED)
    _box(a, 0.70, 0.08, 0.28, 0.18, "migration\n(Yan GP, offline)", GREY)
    _arrow(a, 0.29, 0.81, 0.36, 0.81)
    _arrow(a, 0.63, 0.81, 0.70, 0.81)
    _arrow(a, 0.84, 0.72, 0.84, 0.58)
    _arrow(a, 0.70, 0.49, 0.63, 0.49)
    _arrow(a, 0.36, 0.49, 0.29, 0.49)
    _arrow(a, 0.495, 0.40, 0.495, 0.26)
    _arrow(a, 0.84, 0.26, 0.84, 0.40, ls="--")

    # ---------------- panel (b): serving two flows ----------------
    b.set_title("(b) online implementation (estimation + reconciliation)", fontsize=8)
    _box(b, 0.02, 0.66, 0.22, 0.2, "process inputs\n(scan rate)", GREY)
    _box(b, 0.02, 0.12, 0.22, 0.2, "laboratory result\n(delay \u03b8)", GREY)
    _box(b, 0.36, 0.39, 0.28, 0.3, "calibration state\nb_t, α_t,\nresidual window", RED)
    _box(b, 0.74, 0.66, 0.24, 0.2, "estimate + interval\nissued and\nrecorded", TEAL)
    _box(b, 0.74, 0.12, 0.24, 0.2, "state persisted\n(restart-safe)", GREY)
    _arrow(b, 0.24, 0.76, 0.36, 0.62)  # predict reads state
    _arrow(b, 0.64, 0.62, 0.74, 0.74)  # store interval
    _arrow(b, 0.24, 0.22, 0.36, 0.45, color=RED)  # label mutates state
    _arrow(b, 0.74, 0.74, 0.50, 0.39, color=TEAL, ls="--")  # coverage vs STORED interval
    _arrow(b, 0.64, 0.45, 0.74, 0.24, ls="--")  # snapshot
    b.text(
        0.49,
        0.02,
        "coverage scored against the interval recorded at estimation time (dashed)",
        ha="center",
        fontsize=6,
        color=GREY,
    )

    return save_figure(fig, "F1_architecture", out_dir)


if __name__ == "__main__":
    for p in render():
        print(p)
