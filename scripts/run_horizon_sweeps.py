"""Run the Module 5 horizon sweeps; emit the three paper figures and frozen evidence.

Usage (from repo root, conda env ipis):
    python scripts/run_horizon_sweeps.py

Writes:
    docs/module5/figures/fig1_two_arm.png
    docs/module5/figures/fig2_deadtime.png
    docs/module5/figures/fig3_gamma_union.png
    docs/paper/evidence/module5_horizon_sweeps.json   (stamped)

matplotlib is configured for the sandbox: Agg backend, DejaVu Sans, Unicode text labels
(no mathtext / TeX).
"""

from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.unicode_minus": False, "figure.dpi": 130})

from ipis.integration.coverage import CoverageConfig  # noqa: E402
from ipis.integration.horizon_experiments import (  # noqa: E402
    deadtime_sweep,
    gamma_sweep,
    two_arm_contrast,
)

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "docs" / "module5" / "figures"
EVID = ROOT / "docs" / "paper" / "evidence" / "module5_horizon_sweeps.json"
FIG_DIR.mkdir(parents=True, exist_ok=True)
EVID.parent.mkdir(parents=True, exist_ok=True)

BLUE, CORAL, GRAY = "#185FA5", "#D85A30", "#5F5E5A"


def fig_two_arm(t) -> None:
    metrics = ["S_k coverage", "quality coverage", "RUL coverage"]
    blind = [t.blind.s_coverage, t.blind.quality_coverage, t.blind.rul_coverage]
    cons = [t.constrained.s_coverage, t.constrained.quality_coverage, t.constrained.rul_coverage]
    x = range(len(metrics))
    w = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.bar([i - w / 2 for i in x], blind, w, label="health-blind", color=CORAL)
    ax.bar([i + w / 2 for i in x], cons, w, label="health-constrained", color=BLUE)
    ax.axhline(t.floor, ls="--", color=GRAY, lw=1)
    ax.text(
        2.45, t.floor + 0.012, f"certified floor {t.floor:.2f}", ha="right", color=GRAY, fontsize=9
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("coverage over campaign")
    ax.set_title("Two-arm contrast: blind meets spec but burns RUL, so S\u2096 collapses")
    ax.legend(loc="center right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_two_arm.png")
    plt.close(fig)


def fig_deadtime(d) -> None:
    da = [p.d_a for p in d.points]
    sk = [p.s_coverage for p in d.points]
    iv = [p.interval_coverage for p in d.points]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(da, sk, "o-", color=BLUE, label="S\u2096 coverage")
    ax.plot(da, iv, "s-", color=CORAL, label="M1 interval coverage")
    ax.axhline(d.floor, ls="--", color=GRAY, lw=1)
    ax.text(max(da), d.floor + 0.006, f"floor {d.floor:.2f}", ha="right", color=GRAY, fontsize=9)
    ax.axhline(d.target_interval_coverage, ls=":", color=CORAL, lw=1)
    ax.text(
        max(da),
        d.target_interval_coverage + 0.006,
        f"target {d.target_interval_coverage:.2f}",
        ha="right",
        color=CORAL,
        fontsize=9,
    )
    ax.set_xlabel("label delay D\u2090 (decision cycles)")
    ax.set_ylabel("coverage")
    ax.set_ylim(0.70, 1.03)
    ax.set_title("Validity invariant to deadtime: S\u2096 holds the floor for every D\u2090")
    ax.legend(loc="center right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_deadtime.png")
    plt.close(fig)


def fig_gamma_union(g) -> None:
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.4, 4.0))

    # (a) coverage vs adaptivity; finite-width gammas only for the width line
    gs = [p.gamma for p in g.points]
    cov = [p.interval_coverage for p in g.points]
    fin = [(p.gamma, p.mean_half_width) for p in g.points if p.mean_half_width != float("inf")]
    axA.plot(gs, cov, "o-", color=BLUE, label="interval coverage")
    axA.axhline(g.target_interval_coverage, ls=":", color=GRAY, lw=1)
    axA.text(
        gs[-1],
        g.target_interval_coverage + 0.004,
        f"target {g.target_interval_coverage:.2f}",
        ha="right",
        color=GRAY,
        fontsize=9,
    )
    axA.set_xscale("log")
    axA.set_xlabel("ACI learning rate \u03b3")
    axA.set_ylabel("interval coverage", color=BLUE)
    axA.set_ylim(0.85, 0.97)
    axt = axA.twinx()
    if fin:
        axt.plot([f[0] for f in fin], [f[1] for f in fin], "s--", color=CORAL)
    axt.set_ylabel("mean half-width", color=CORAL)
    axA.set_title("(a) coverage vs adaptivity")

    # (b) naive Bonferroni half-width vs horizon K (inf = vacuous), ACI line for reference
    ks = [u.horizon_k for u in g.union_bound]
    finite = [
        (u.horizon_k, u.bonferroni_half_width)
        for u in g.union_bound
        if u.bonferroni_half_width != float("inf")
    ]
    vac = [u.horizon_k for u in g.union_bound if u.bonferroni_half_width == float("inf")]
    cap = (
        max([f[1] for f in finite] + [g.aci_mean_half_width]) * 1.5
        if finite
        else g.aci_mean_half_width * 3
    )
    if finite:
        axB.plot(
            [f[0] for f in finite], [f[1] for f in finite], "o-", color=CORAL, label="Bonferroni"
        )
    for k in vac:
        axB.scatter([k], [cap], marker="^", color=CORAL, zorder=5)
        axB.annotate(
            "vacuous (\u221e)",
            (k, cap),
            textcoords="offset points",
            xytext=(0, -14),
            ha="center",
            color=CORAL,
            fontsize=8,
        )
    axB.axhline(g.aci_mean_half_width, ls="--", color=BLUE, lw=1, label="ACI mean half-width")
    axB.set_xscale("log")
    axB.set_xlabel("joint horizon K (cycles)")
    axB.set_ylabel("half-width")
    axB.set_ylim(0, cap * 1.15)
    axB.set_title("(b) ACI finite where Bonferroni is vacuous")
    axB.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_gamma_union.png")
    plt.close(fig)


def main() -> None:
    cfg = CoverageConfig(
        spec_xb_c4=0.02,
        rul_min_hours=200.0,
        alpha1=0.10,
        alpha2=0.10,
        eps=0.05,
        n_seeds=4,
        n_cycles=120,
    )
    da_values = [0, 1, 2, 4, 8]
    gamma_values = [0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128]
    union_horizons = [1, 10, 50, 200, 1000]

    print("running two-arm contrast ...")
    t = two_arm_contrast(cfg)
    print("running deadtime sweep ...")
    d = deadtime_sweep(cfg, da_values, campaign_cycles=400)
    print("running gamma sweep ...")
    g = gamma_sweep(cfg, gamma_values, campaign_cycles=400, union_horizons=union_horizons)

    fig_two_arm(t)
    fig_deadtime(d)
    fig_gamma_union(g)

    evidence = {
        "stamp": {
            "script": "scripts/run_horizon_sweeps.py",
            "argv": sys.argv,
            "utc": datetime.now(timezone.utc).isoformat(),
            "config": dataclasses.asdict(cfg),
            "da_values": da_values,
            "gamma_values": gamma_values,
            "union_horizons": union_horizons,
        },
        "figure1_two_arm": dataclasses.asdict(t),
        "figure2_deadtime": dataclasses.asdict(d),
        "figure3_gamma_union": dataclasses.asdict(g),
    }

    def _clean(o):
        if isinstance(o, float) and o == float("inf"):
            return "inf"
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_clean(v) for v in o]
        return o

    EVID.write_text(json.dumps(_clean(evidence), indent=2))
    print(f"\nwrote figures to {FIG_DIR}")
    print(f"wrote evidence to {EVID}")
    print(
        f"\ntwo-arm: blind S_k={t.blind.s_coverage:.3f} (meets={t.blind.meets_floor}) | "
        f"constrained S_k={t.constrained.s_coverage:.3f} (meets={t.constrained.meets_floor}) | floor={t.floor:.2f}"
    )


if __name__ == "__main__":
    main()
