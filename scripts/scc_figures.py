"""Regenerate the paper3 figures from the committed evidence scripts.

Before this script the four figures in `paper3/figures/` had no generator in the repo: they were
produced ad hoc in an earlier session, so the standing rule (no number enters the manuscript unless
a committed script reproduces it) did not hold for anything printed on an axis.

  fig1_coverage     (a) testbed coverage at eta = 0 by calibrate -> deploy pair, naive vs SCC vs
                        discrete-mode conformal with no target history
                    (b) C-MAPSS coverage over all 30 ordered regime pairs, FD002 and FD004
  fig2_departure    SCC coverage gap and interval back-off vs the departure eta, with the
                    actionability bands of Section 4.3 shaded
  fig3_certificate  held-out measured coverage gap vs the physical departure, with the a-priori
                    bound, annotated with the mean margin

fig4_diagnostic is NOT regenerated here: its three cases (n = 40 similitude, n = 40 violated,
n = 6 FEMTO-like) are not reproduced by any committed evidence script, so regenerating it would
mean inventing parameters. That is recorded as debt in the revision log.

Panel (a) needs the C-MAPSS files; see the data note in `scripts/cmapss_loader.py`.

Run:  PYTHONPATH=src python3 scripts/scc_figures.py --out paper3/figures
"""

from __future__ import annotations

import argparse
import itertools
import json
import pathlib

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from cmapss_loader import load  # noqa: E402
from r15b_certificate import certificate, collect  # noqa: E402
from r21_cmapss import ALPHA as CM_ALPHA  # noqa: E402
from r21_cmapss import (  # noqa: E402
    SENSORS,
    attach_referred,
    fit_predictor,
    one_snapshot_per,
)
from r23_discrete_mode import ALPHA as TB_ALPHA  # noqa: E402
from r23_discrete_mode import SEEDS as TB_SEEDS  # noqa: E402
from r23_discrete_mode import TEMPS  # noqa: E402
from r23_discrete_mode import unit_scores as testbed_scores  # noqa: E402

from ipis.module2_pdm.scc.conformal import one_sided_quantile  # noqa: E402

NAIVE, SCC, DISCRETE = "#b5473f", "#3c62a8", "#8c8c8c"
TARGET = 0.90
# Canvases match the elsarticle review text width (about 5.3 in), so \includegraphics at
# \linewidth does not rescale them and the label sizes below are the sizes on the page.
SINGLE, WIDE = (5.3, 2.6), (5.3, 2.7)


def style(base: int) -> None:
    plt.rcParams.update(
        {
            "font.size": base,
            "axes.labelsize": base,
            "axes.titlesize": base,
            "xtick.labelsize": base - 1,
            "ytick.labelsize": base - 1,
            "legend.fontsize": base - 1,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 600,
        }
    )


# --------------------------------------------------------------------------- panel data


def testbed_pairs(evidence: pathlib.Path) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Naive and SCC coverage per ordered pair at eta = 0, from scripts/r15c_directional.py."""
    ev = json.loads((evidence / "directional.json").read_text())
    keys = [k for k in ev if k.startswith("0.0|")]
    labels = [k.split("|")[1] for k in keys]
    naive = np.array([ev[k]["naive_cov"] for k in keys])
    scc = np.array([ev[k]["scc_cov"] for k in keys])
    order = np.argsort(naive)
    return [labels[i] for i in order], naive[order], scc[order]


def discrete_fallback() -> dict[float, float]:
    """Coverage of discrete-mode conformal at a target regime with no failure history.

    With no calibration set for that mode the method falls back to the nearest available mode,
    exactly as in `scripts/r23_discrete_mode.py`, so the value depends on the deployment
    condition alone.
    """
    out: dict[float, float] = {}
    per_target: dict[float, list[float]] = {t: [] for t in TEMPS}
    for seed in range(TB_SEEDS):
        rng = np.random.default_rng(seed * 977 + 11)
        sc = {t: testbed_scores(t, 0.0, seed * 17 + i, rng) for i, t in enumerate(TEMPS)}
        for target in TEMPS:
            sources = [t for t in TEMPS if t != target]
            nearest = min(sources, key=lambda s: abs(s - target))
            q = one_sided_quantile(sc[nearest][0], TB_ALPHA)
            per_target[target].append(float(np.mean(sc[target][0] <= q)))
    for t, v in per_target.items():
        out[t] = float(np.mean(v))
    return out


def cmapss_pairs(ds: str, seeds: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Per ordered regime pair, naive and SCC coverage, averaged over seeds.

    Same protocol as `scripts/r21_cmapss.py` (engine-disjoint thirds, one snapshot per engine per
    regime, ridge fitted on the source regime); that script stores clipped gaps, and a coverage
    axis needs the unclipped values.
    """
    df = attach_referred(load(ds))
    regimes = sorted(df.regime.unique())
    units = np.array(sorted(df.unit.unique()))
    raw_feats, ref_feats = SENSORS, [f"d_{s}" for s in SENSORS]

    acc: dict[tuple, list[list[float]]] = {}
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        perm = rng.permutation(units)
        n_tr = len(perm) // 3
        tr_u, cal_u, te_u = perm[:n_tr], perm[n_tr : 2 * n_tr], perm[2 * n_tr :]
        snaps_tr = {r: df[(df.regime == r) & (df.unit.isin(tr_u))] for r in regimes}
        cal = {r: one_snapshot_per(df, cal_u, r, rng) for r in regimes}
        te = {r: one_snapshot_per(df, te_u, r, rng) for r in regimes}
        models = {
            (r, kind): fit_predictor(snaps_tr[r], feats, "ridge")
            for r in regimes
            for kind, feats in (("raw", raw_feats), ("ref", ref_feats))
        }

        def scored(frame, model, feats):
            return model.predict(frame[feats].to_numpy()) - frame["rul_cap"].to_numpy()

        for a, b in itertools.permutations(regimes, 2):
            s_raw = scored(cal[a], models[(a, "raw")], raw_feats)
            s_ref = scored(cal[a], models[(a, "ref")], ref_feats)
            t_raw = scored(te[b], models[(a, "raw")], raw_feats)
            t_ref = scored(te[b], models[(a, "ref")], ref_feats)
            qn = one_sided_quantile(s_raw, CM_ALPHA)
            qs = one_sided_quantile(s_ref, CM_ALPHA)
            acc.setdefault((a, b), []).append(
                [float(np.mean(t_raw <= qn)), float(np.mean(t_ref <= qs))]
            )
    means = np.array([np.mean(v, axis=0) for v in acc.values()])
    return means[:, 0], means[:, 1]


def crossing(etas: np.ndarray, values: np.ndarray, level: float) -> float | None:
    """Linear interpolation of the eta at which values first reach a level."""
    above = np.where(values >= level)[0]
    if len(above) == 0 or above[0] == 0:
        return None
    i = above[0]
    x0, x1, y0, y1 = etas[i - 1], etas[i], values[i - 1], values[i]
    return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0))


# --------------------------------------------------------------------------- figures


def fig1(evidence: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    style(9)
    labels, naive, scc = testbed_pairs(evidence)
    fallback = discrete_fallback()
    disc = np.array([fallback[float(lbl.split("->")[1])] for lbl in labels])

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=WIDE, sharey=True, gridspec_kw={"width_ratios": [1.45, 1], "wspace": 0.12}
    )

    x = np.arange(len(labels))
    w = 0.27
    ax_a.bar(x - w, naive, w, color=NAIVE, label="naive")
    ax_a.bar(x, disc, w, color=DISCRETE, label="discrete-mode")
    ax_a.bar(x + w, scc, w, color=SCC, label="SCC")
    ax_a.axhline(TARGET, color="k", lw=0.9, ls="--", zorder=3)
    ax_a.set_xticks(x, [lbl.replace("->", "\u2192") for lbl in labels], rotation=30, ha="right")
    ax_a.set_ylabel("empirical coverage")
    ax_a.set_xlabel("calibrate $\\to$ deploy (K)")
    ax_a.set_ylim(0, 1.04)
    ax_a.set_title("(a) catalyst testbed, $\\eta=0$", loc="left", pad=6)

    rng = np.random.default_rng(0)
    for k, ds in enumerate(("FD002", "FD004")):
        for j, (values, colour) in enumerate(zip(cmapss_pairs(ds), (NAIVE, SCC), strict=True)):
            pos = 1 + 2 * k + (j - 0.5) * 0.62
            ax_b.scatter(
                pos + rng.uniform(-0.13, 0.13, len(values)),
                values,
                s=7,
                color=colour,
                alpha=0.7,
                linewidths=0,
                zorder=3,
            )
            ax_b.hlines(values.mean(), pos - 0.22, pos + 0.22, color=colour, lw=2.0, zorder=4)
    ax_b.axhline(TARGET, color="k", lw=0.9, ls="--", zorder=1)
    ax_b.set_xticks([1, 3], ["FD002", "FD004"])
    ax_b.set_ylim(0, 1.04)
    ax_b.set_xlim(0.3, 3.7)
    ax_b.set_xlabel("ordered regime pairs")
    ax_b.set_title("(b) C-MAPSS turbofan fleet", loc="left", pad=6)

    handles, names = ax_a.get_legend_handles_labels()
    fig.legend(
        handles, names, frameon=False, ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.09)
    )
    path = out / "fig1_coverage.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def fig2(evidence: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    style(9)
    ev = json.loads((evidence / "r24_actionability.json").read_text())
    etas = np.array(sorted(float(k) for k in ev if k.replace(".", "").isdigit()))
    gaps = np.array([ev[str(e)]["gap"] for e in etas])
    backs = np.array([ev[str(e)]["backoff"] for e in etas])
    e_act = crossing(etas, backs, 0.5)
    e_deg = crossing(etas, backs, 1.0)

    fig, ax = plt.subplots(figsize=SINGLE)
    ax.axvspan(etas[0], e_act, color="#2e7d32", alpha=0.07)
    ax.axvspan(e_act, e_deg, color="#f9a825", alpha=0.10)
    ax.axvspan(e_deg, etas[-1], color="#b5473f", alpha=0.10)
    for edge in (e_act, e_deg):
        ax.axvline(edge, color="0.35", lw=0.8, ls=":")
    ax.text(
        e_act,
        1.02,
        f"$\\eta={e_act:.2f}$",
        ha="center",
        va="bottom",
        transform=ax.get_xaxis_transform(),
        fontsize=7,
    )
    ax.text(
        e_deg,
        1.02,
        f"$\\eta={e_deg:.2f}$",
        ha="center",
        va="bottom",
        transform=ax.get_xaxis_transform(),
        fontsize=7,
    )

    ax.plot(etas, gaps, "o-", color=SCC, ms=3.5, lw=1.4, label="SCC coverage gap")
    ax.set_xlabel("unmodelled physics weight $\\eta$")
    ax.set_ylabel("SCC coverage gap", color=SCC)
    ax.tick_params(axis="y", colors=SCC)
    ax.set_ylim(0, max(gaps) * 1.25)
    ax.set_xlim(etas[0], etas[-1])

    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.plot(etas, backs, "s--", color="#6b8e23", ms=3.5, lw=1.4, label="interval back-off $b$")
    ax2.axhline(1.0, color="#6b8e23", lw=0.7, ls="-", alpha=0.35)
    ax2.set_ylabel("interval back-off $b=q_T/\\overline{\\mathrm{RUL}}_T$", color="#6b8e23")
    ax2.tick_params(axis="y", colors="#6b8e23")
    ax2.set_ylim(0, max(backs) * 1.1)

    path = out / "fig2_departure.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def fig3(out: pathlib.Path) -> pathlib.Path:
    style(9)
    rows = collect(400, 5)
    cert = certificate(rows, seed=1)
    delta, gap = rows[:, 0], rows[:, 1]
    idx = np.random.default_rng(1).permutation(len(rows))
    te = idx[int(0.6 * len(idx)) :]

    grid = np.linspace(0, delta.max() * 1.05, 100)
    bound = 2 * (cert["a"] + cert["L"] * grid)

    fig, ax = plt.subplots(figsize=SINGLE)
    ax.fill_between(grid, 0, bound, color=NAIVE, alpha=0.07)
    ax.plot(grid, bound, color=NAIVE, lw=1.3, label="a-priori bound $2(a+L\\delta)$")
    ax.scatter(delta[te], gap[te], s=16, color=SCC, zorder=3, label="measured gap (held-out)")
    ax.set_xlabel("physical departure $\\delta=\\eta\\,|h(S)-h(T)|$")
    ax.set_ylabel("coverage gap")
    ax.set_xlim(0, grid[-1])
    ax.set_ylim(0, bound.max() * 1.08)
    ax.annotate(
        f"mean margin {cert['margin_mean']:.3f}",
        xy=(grid[-1] * 0.45, bound.max() * 0.45),
        fontsize=7.5,
        color="0.3",
    )
    ax.legend(frameon=False, loc="upper left", fontsize=7.5)
    path = out / "fig3_certificate.pdf"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="paper3/figures", help="output directory")
    parser.add_argument("--evidence", default="out", help="directory holding the evidence JSONs")
    parser.add_argument("--only", choices=["fig1", "fig2", "fig3"], help="render one figure")
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    evidence = pathlib.Path(args.evidence)

    jobs = {
        "fig1": lambda: fig1(evidence, out),
        "fig2": lambda: fig2(evidence, out),
        "fig3": lambda: fig3(out),
    }
    for name, job in jobs.items():
        if args.only in (None, name):
            print(f"wrote {job()}")


if __name__ == "__main__":
    main()
