"""Paper-2 schematics (vector, no data dependency).

  F1  the chance-constrained RTO loop: nominal model + conformal back-off feed the
      optimiser, which sets (R,D) on the twin; the constrained x_B is unmeasured, and a
      grey dashed path marks the closed-loop soft-sensor feedback left to future work.
  F2  the debutaniser twin: nine-stage binary column with the feed-z disturbance, the
      distillate (light key) and the constrained bottoms composition.

Usage:
  python scripts/paper2_figures/make_schematics.py [--outdir docs/module3/paper/figures]
"""

from __future__ import annotations

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

BLUE, ORANGE, GREY, INK = "#0072B2", "#D55E00", "#9aa0a6", "#222222"


def _box(ax, xy, w, h, text, *, fc="white", ec=INK, fs=9, lw=1.4, z=2):
    x, y = xy
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2, y - h / 2),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            fc=fc,
            ec=ec,
            lw=lw,
            zorder=z,
        )
    )
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=z + 1, color=INK)


def _arrow(ax, p0, p1, *, color=INK, ls="-", lw=1.6, z=1, rad=None):
    cs = f"arc3,rad={rad}" if rad is not None else "arc3,rad=0"
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle="-|>",
            connectionstyle=cs,
            mutation_scale=14,
            lw=lw,
            color=color,
            linestyle=ls,
            shrinkA=2,
            shrinkB=2,
            zorder=z,
        )
    )


def fig_rto_loop(outpath: str) -> None:
    fig, ax = plt.subplots(figsize=(10.2, 5.4))
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 7.5)
    ax.axis("off")

    _box(ax, (1.9, 5.4), 3.2, 0.9, r"Nominal model  $\hat{g}(u)$")
    _box(
        ax,
        (1.9, 2.8),
        3.2,
        1.1,
        "Conformal back-off  $C(u)$\n(fixed / normalised / CQR)",
        ec=BLUE,
    )
    ax.text(
        1.9,
        2.0,
        r"$\uparrow$ calibration data $\{(u_i,z_i,g_i)\}$",
        ha="center",
        va="top",
        fontsize=7.5,
        color=GREY,
    )

    _box(
        ax,
        (5.7, 4.1),
        3.0,
        1.9,
        "RTO optimiser\n\n" r"$\max_u\ \pi(u)$" "\n" r"s.t. $\hat{g}(u){+}C(u)\leq\bar{g}$",
        lw=1.8,
    )
    _box(
        ax,
        (9.4, 4.1),
        3.3,
        1.9,
        "Debutaniser twin\n(DWSIM, Peng-Robinson)\n9 stages, binary nC4/nC6",
        ec=INK,
        fs=8.2,
    )
    _box(ax, (12.4, 4.1), 1.5, 1.0, "spec\n" r"$x_B\leq\bar{g}$", ec=BLUE)

    _arrow(ax, (3.5, 5.4), (4.2, 4.6))
    _arrow(ax, (3.5, 2.9), (4.2, 3.6), color=BLUE)
    _arrow(ax, (7.2, 4.1), (7.75, 4.1))
    ax.text(7.47, 4.5, r"$u^\star=(R,D)$", ha="center", va="bottom", fontsize=8.5)

    _arrow(ax, (9.4, 6.7), (9.4, 5.05), color=ORANGE)
    ax.text(
        9.4,
        6.85,
        r"$z\sim\mathcal{F}_\sigma$  (unmeasured feed composition)",
        ha="center",
        va="bottom",
        fontsize=8.5,
        color=ORANGE,
    )

    _arrow(ax, (11.05, 4.1), (11.65, 4.1), color=GREY, ls=(0, (4, 2)))
    ax.text(
        11.35,
        3.45,
        "realised $x_B$\n(unmeasured)",
        ha="center",
        va="top",
        fontsize=7.5,
        color=GREY,
    )

    _arrow(ax, (12.4, 3.55), (5.7, 3.1), color=GREY, ls=(0, (5, 3)), lw=1.3, z=0, rad=-0.5)
    ax.text(
        8.9,
        1.45,
        "online soft-sensor feedback:  closed-loop (future work)",
        ha="center",
        va="center",
        fontsize=8,
        color=GREY,
        style="italic",
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5},
        zorder=2,
    )

    ax.set_title(
        "F1  Chance-constrained RTO with a conformal constraint back-off",
        fontsize=10,
        loc="left",
    )
    fig.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_column(outpath: str) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 7.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11)
    ax.axis("off")

    # process-conditions note in the empty upper-left
    ax.text(
        0.2,
        9.2,
        "binary n-butane / n-hexane\nPeng-Robinson EOS\ntop 4.7 bar,  $\\Delta P$ 0.4 bar",
        ha="left",
        va="top",
        fontsize=8.5,
        color=GREY,
    )

    cx, half = 5.2, 0.95
    top, bot = 9.3, 2.0
    ax.add_patch(
        Rectangle((cx - half, bot), 2 * half, top - bot, fill=False, ec=INK, lw=1.8, zorder=2)
    )
    n = 9
    ys = [top - (i + 0.5) * (top - bot) / n for i in range(n)]
    feed_stage = 4
    for i, y in enumerate(ys):
        ax.plot([cx - half + 0.12, cx + half - 0.12], [y, y], color=INK, lw=0.7, zorder=2)
        if i in (0, feed_stage, 8):
            ax.text(cx + half + 0.18, y, f"stage {i}", va="center", fontsize=7, color=GREY)

    # condenser + distillate + reflux
    ax.add_patch(Circle((cx, top + 0.95), 0.42, fill=False, ec=INK, lw=1.5, zorder=3))
    ax.text(cx, top + 0.95, "cond.", ha="center", va="center", fontsize=6.5)
    _arrow(ax, (cx, top), (cx, top + 0.5))
    _arrow(ax, (cx + 0.42, top + 1.2), (cx + 2.3, top + 1.2), color=BLUE)
    ax.text(
        cx + 2.4,
        top + 1.2,
        "Distillate  $D$\n(LPG, light key)",
        va="center",
        fontsize=8.5,
        color=BLUE,
    )
    ax.add_patch(
        FancyArrowPatch(
            (cx + 0.42, top + 0.7),
            (cx - 0.3, top - 0.15),
            connectionstyle="arc3,rad=-0.4",
            arrowstyle="-|>",
            mutation_scale=12,
            lw=1.4,
            color=INK,
            zorder=3,
        )
    )
    ax.text(cx - 1.2, top + 0.4, "reflux $R$", va="center", fontsize=8, color=INK)

    # reboiler + bottoms
    ax.add_patch(Circle((cx, bot - 0.95), 0.42, fill=False, ec=INK, lw=1.5, zorder=3))
    ax.text(cx, bot - 0.95, "reb.", ha="center", va="center", fontsize=6.5)
    _arrow(ax, (cx, bot), (cx, bot - 0.5))
    _arrow(ax, (cx + 0.42, bot - 0.95), (cx + 2.3, bot - 0.95), color=ORANGE)
    ax.text(
        cx + 2.4,
        bot - 0.95,
        "Bottoms  $B$\n$x_B$ = bottoms nC4\n(constrained, $\\leq\\bar{g}$)",
        va="center",
        fontsize=8.5,
        color=ORANGE,
    )
    ax.add_patch(
        FancyArrowPatch(
            (cx - 0.42, bot - 0.7),
            (cx + 0.3, bot + 0.15),
            connectionstyle="arc3,rad=-0.4",
            arrowstyle="-|>",
            mutation_scale=12,
            lw=1.4,
            color=INK,
            zorder=3,
        )
    )

    # feed (disturbance) into the feed stage
    _arrow(ax, (cx - half - 2.4, ys[feed_stage]), (cx - half, ys[feed_stage]), color=ORANGE)
    ax.text(
        cx - half - 2.5,
        ys[feed_stage],
        "Feed  100 kmol h$^{-1}$\n$z=x_{nC4}$  (disturbance)",
        ha="right",
        va="center",
        fontsize=8.5,
        color=ORANGE,
    )

    ax.set_title(
        "F2  Debutaniser twin: feed disturbance and the constrained bottoms",
        fontsize=10,
        loc="left",
    )
    fig.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="docs/module3/paper/figures")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    fig_rto_loop(os.path.join(args.outdir, "F1_rto_loop.png"))
    fig_column(os.path.join(args.outdir, "F2_column.png"))
    print(f"wrote F1, F2 to {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
