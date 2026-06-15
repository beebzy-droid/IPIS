"""Paper-2 figures rendered from the frozen regime-map evidence.

Reads docs/module3/paper/evidence/regime_map.json (produced by
run_3b3_regime_map.py --save-json on the committed twin data) and renders the
disturbance-swept figures:

  F3  realized violation vs sigma_z, four methods   (the headline / selection effect)
  F5  operating profit vs sigma_z, four methods     (safety not profit)
  F7  a-posteriori inflation kappa vs sigma_z        (data-starvation diagnostic)

Data-rendered figures that need the raw twin (F4 back-off heatmaps, F6 surrogate
validation) and the schematics (F1, F2) are produced by separate scripts.

Usage:
  python scripts/paper2_figures/make_swept_figures.py \
    [--json docs/module3/paper/evidence/regime_map.json] [--outdir docs/module3/paper/figures]
"""

from __future__ import annotations

import argparse
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# colour-blind-safe, consistent across all paper-2 figures
STYLE = {
    "oracle": {
        "color": "#000000",
        "marker": "o",
        "ls": "--",
        "label": "oracle (truth conditional quantile)",
    },
    "cqr+apost": {
        "color": "#0072B2",
        "marker": "s",
        "ls": "-",
        "label": "CQR + a-posteriori (proposed)",
    },
    "naive-fixed": {"color": "#E69F00", "marker": "^", "ls": ":", "label": "naive fixed margin"},
    "naive-adapt": {
        "color": "#D55E00",
        "marker": "v",
        "ls": ":",
        "label": "naive adaptive (normalized)",
    },
}
ORDER = ["oracle", "cqr+apost", "naive-fixed", "naive-adapt"]


def _load(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def _series(data: dict, method: str, key: str):
    """(sigma, value) pairs where the method is feasible; infeasible -> gap."""
    xs, ys = [], []
    for s in sorted(data["regime"], key=float):
        cell = data["regime"][s][method]
        if cell["feasible"] and cell[key] is not None:
            xs.append(float(s))
            ys.append(cell[key])
    return xs, ys


def _infeasible_sigmas(data: dict, method: str):
    return [
        float(s)
        for s in sorted(data["regime"], key=float)
        if not data["regime"][s][method]["feasible"]
    ]


def fig_violation(data: dict, outpath: str) -> None:
    alpha = data["metadata"]["alpha"]
    band = data["metadata"]["violation_mc_band"]
    realistic = data["metadata"]["realistic_sigma_z"]
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for m in ORDER:
        xs, ys = _series(data, m, "realized_violation")
        ax.plot(
            xs,
            ys,
            color=STYLE[m]["color"],
            marker=STYLE[m]["marker"],
            ls=STYLE[m]["ls"],
            label=STYLE[m]["label"],
            lw=1.8,
            ms=5,
        )
        # MC band around each feasible point
        ax.fill_between(
            xs,
            [y - band for y in ys],
            [y + band for y in ys],
            color=STYLE[m]["color"],
            alpha=0.08,
            lw=0,
        )
        for s in _infeasible_sigmas(data, m):
            ax.plot(s, alpha, marker="x", color=STYLE[m]["color"], ms=8, mew=2)
    ax.axhline(alpha, color="0.4", lw=1.0, ls="-")
    ax.text(
        ax.get_xlim()[1],
        alpha,
        f" target $\\alpha={alpha:.2f}$",
        va="center",
        ha="left",
        fontsize=8,
        color="0.3",
    )
    ax.axvline(realistic, color="0.7", lw=0.8, ls="--")
    ax.text(
        realistic,
        ax.get_ylim()[1],
        " realistic",
        rotation=90,
        va="top",
        ha="left",
        fontsize=8,
        color="0.5",
    )
    ax.set_xlabel(r"feed-composition disturbance magnitude $\sigma_z$")
    ax.set_ylabel(r"realized constraint-violation rate $\hat v(u^\star)$")
    ax.set_title(
        "Marginal back-offs are exploited by the RTO; conditional calibration tracks the oracle",
        fontsize=9,
    )
    ax.set_ylim(0, 0.56)
    ax.legend(fontsize=7.5, framealpha=0.9, loc="center left")
    ax.annotate(
        "infeasible (×)",
        xy=(0.98, 0.02),
        xycoords="axes fraction",
        ha="right",
        va="bottom",
        fontsize=7,
        color="0.4",
    )
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def fig_profit(data: dict, outpath: str) -> None:
    realistic = data["metadata"]["realistic_sigma_z"]
    det = data["metadata"].get("deterministic_optimum_profit_usd_per_h")
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for m in ORDER:
        xs, ys = _series(data, m, "profit_usd_per_h")
        ax.plot(
            xs,
            ys,
            color=STYLE[m]["color"],
            marker=STYLE[m]["marker"],
            ls=STYLE[m]["ls"],
            label=STYLE[m]["label"],
            lw=1.8,
            ms=5,
        )
    if det:
        ax.axhline(det, color="0.4", lw=1.0, ls="-")
        ax.text(
            ax.get_xlim()[1],
            det,
            f" deterministic ${det:.0f}",
            va="center",
            ha="left",
            fontsize=8,
            color="0.3",
        )
    ax.axvline(realistic, color="0.7", lw=0.8, ls="--")
    ax.set_xlabel(r"feed-composition disturbance magnitude $\sigma_z$")
    ax.set_ylabel(r"operating profit at $u^\star$ (USD h$^{-1}$)")
    ax.set_title(
        "Profit is muted at realistic disturbance: the contribution is safety, not profit",
        fontsize=9,
    )
    ax.legend(fontsize=7.5, framealpha=0.9, loc="lower left")
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def fig_kappa(data: dict, outpath: str) -> None:
    realistic = data["metadata"]["realistic_sigma_z"]
    xs, ys = _series(data, "cqr+apost", "kappa")
    infeas = _infeasible_sigmas(data, "cqr+apost")
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(
        xs,
        ys,
        color=STYLE["cqr+apost"]["color"],
        marker="s",
        lw=1.8,
        ms=5,
        label="CQR + a-posteriori",
    )
    ax.axhline(1.0, color="0.6", lw=0.8, ls="--")
    ax.text(
        xs[0], 1.0, " no tightening ($\\kappa=1$)", va="bottom", ha="left", fontsize=8, color="0.4"
    )
    for s in infeas:
        ax.plot(
            s, max(ys) if ys else 1.0, marker="x", color=STYLE["cqr+apost"]["color"], ms=9, mew=2
        )
        ax.annotate(
            "infeasible",
            xy=(s, max(ys) if ys else 1.0),
            fontsize=7.5,
            color="0.4",
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
        )
    ax.axvline(realistic, color="0.7", lw=0.8, ls="--")
    ax.set_xlabel(r"feed-composition disturbance magnitude $\sigma_z$")
    ax.set_ylabel(r"a-posteriori inflation $\kappa^\star$")
    ax.set_title(
        "The safety margin is stretched before it breaks: $\\kappa$ as a data-adequacy signal",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/module3/paper/evidence/regime_map.json")
    ap.add_argument("--outdir", default="docs/module3/paper/figures")
    args = ap.parse_args()
    data = _load(args.json)
    os.makedirs(args.outdir, exist_ok=True)
    fig_violation(data, os.path.join(args.outdir, "F3_violation_vs_sigma.png"))
    fig_profit(data, os.path.join(args.outdir, "F5_profit_vs_sigma.png"))
    fig_kappa(data, os.path.join(args.outdir, "F7_kappa_vs_sigma.png"))
    print(f"wrote F3, F5, F7 to {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
