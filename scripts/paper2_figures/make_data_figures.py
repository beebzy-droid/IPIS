"""Paper-2 data-rendered figures (require the twin CSVs).

  F4  back-off fields C(R,D) for the naive-adaptive vs CQR+a-posteriori methods at
      the realistic disturbance, with each method's selected optimum and the TRUE
      feasibility boundary overlaid -- the "why" picture for the selection effect.
  F6  surrogate leave-one-feed-composition-out validation: predicted vs actual x_B
      on the held-out z=0.375 slice, and the monotone x_B(R,D,z) response.

Usage:
  python scripts/paper2_figures/make_data_figures.py \
    --nominal data/raw/dwsim/twin_runs.csv --zvaried data/raw/dwsim/twin_runs_zvaried.csv \
    [--outdir docs/module3/paper/figures]
"""

from __future__ import annotations

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ipis.module3_rto import chance_rto as crto  # noqa: E402
from ipis.module3_rto.economics import EconomicsAnchor  # noqa: E402
from ipis.module3_rto.surrogate import (  # noqa: E402
    _fit,
    fit_gpr_from_csv,
    fit_truth_surface_3d,
)

SPEC, ALPHA, SEED, REALISTIC = 0.02, 0.10, 20260614, 0.006


def _surfaces(nominal_csv: str, zvaried_csv: str):
    econ = EconomicsAnchor()
    xb_nom, _ = fit_gpr_from_csv(nominal_csv)
    dfn = pd.read_csv(nominal_csv)
    xd_nom = _fit(dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["xd_c4"], log_target=False)
    q_nom = _fit(
        dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["reboiler_duty_kW"], log_target=False
    )
    truth = fit_truth_surface_3d(zvaried_csv)
    grid = crto.build_decision_grid(xb_nom, xd_nom, q_nom, econ)
    return xb_nom, truth, grid


def _axes(grid):
    gr = np.unique(grid.r)
    gd = np.unique(grid.d)
    return gr, gd, len(gd), len(gr)


def fig_backoff_fields(xb_nom, truth, grid, outpath: str) -> None:
    gr, gd, nd, nr = _axes(grid)
    dist = crto.DisturbanceModel(sigma=REALISTIC)
    rng = np.random.default_rng(SEED)
    cal = crto.sample_calibration(xb_nom, truth, dist, rng, n=1500)

    C_nrm = crto.normalized_backoff(cal, grid, ALPHA)
    C_cqr = crto.cqr_backoff(cal, grid, ALPHA)

    # selected optima (CQR after a-posteriori inflation -> use kappa for its field)
    res_nrm = crto.solve_chance_rto(grid, C_nrm, SPEC, truth, dist, rng, method="naive-adapt")
    res_cqr = crto.aposteriori_tighten(grid, C_cqr, SPEC, truth, dist, ALPHA, rng)
    res_orc = crto.solve_chance_rto(
        grid, crto.oracle_backoff(truth, grid, dist, ALPHA), SPEC, truth, dist, rng, method="oracle"
    )
    kappa = res_cqr.kappa

    # true (1-alpha) conditional quantile of x_B over z, via the monotone-z shortcut
    z_hi = dist.quantile(1.0 - ALPHA)
    true_q = np.clip(crto._grid3d(truth, grid.r, grid.d, np.full(grid.n, z_hi)), 0.0, 1.0)

    panels = [
        ("naive adaptive (normalized)", C_nrm, res_nrm, "#D55E00"),
        (f"CQR + a-posteriori ($\\kappa={kappa:.2f}$)", kappa * C_cqr, res_cqr, "#0072B2"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    vmax = float(np.percentile(np.concatenate([C_nrm, kappa * C_cqr]), 98))
    for ax, (title, field, res, col) in zip(axes, panels, strict=False):
        F = field.reshape(nd, nr)
        pc = ax.pcolormesh(gr, gd, F, cmap="viridis", vmin=0, vmax=vmax, shading="auto")
        # TRUE feasibility boundary: true_q == spec (the oracle's safe/unsafe divide)
        cs = ax.contour(
            gr, gd, true_q.reshape(nd, nr), levels=[SPEC], colors="white", linewidths=2.4
        )
        ax.clabel(cs, fmt={SPEC: "true boundary"}, fontsize=7.5, inline=True)
        if res.feasible_found:
            ax.plot(
                res.reflux_ratio,
                res.distillate_kmol_h,
                marker="*",
                ms=18,
                color=col,
                mec="white",
                mew=1.2,
                label="selected optimum",
                zorder=5,
            )
        if res_orc.feasible_found:
            ax.plot(
                res_orc.reflux_ratio,
                res_orc.distillate_kmol_h,
                marker="P",
                ms=11,
                color="white",
                mec="black",
                mew=1.2,
                label="oracle optimum",
                zorder=5,
            )
        ax.set_title(title, fontsize=9.5)
        ax.set_xlabel("reflux ratio $R$")
        ax.legend(fontsize=7.5, loc="upper right", framealpha=0.9)
    axes[0].set_ylabel(r"distillate flow $D$ (kmol h$^{-1}$)")
    cbar = fig.colorbar(pc, ax=axes, fraction=0.046, pad=0.02)
    cbar.set_label(r"back-off $C(R,D)$ in $x_B$", fontsize=9)
    fig.suptitle(
        "Back-off field $C(R,D)$; white = true safe/unsafe boundary. The adaptive margin "
        "stays small in the low-$D$ corner, so its optimum (\u2605) lands on the unsafe side; "
        "CQR's margin grows there, keeping its optimum safe.",
        fontsize=8.5,
        y=1.02,
    )
    fig.savefig(outpath, dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_surrogate_validation(zvaried_csv: str, outpath: str, held_z: float = 0.375) -> None:
    df = pd.read_csv(zvaried_csv)
    train = df[np.abs(df["z_c4"] - held_z) > 1e-9]
    test = df[np.abs(df["z_c4"] - held_z) <= 1e-9].copy()
    import tempfile

    tmp = os.path.join(tempfile.gettempdir(), "_ipis_f6_train.csv")
    train.to_csv(tmp, index=False)
    try:
        surf = fit_truth_surface_3d(tmp)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    pred = np.array(
        [
            surf.predict(r, d, z)
            for r, d, z in test[["reflux_ratio", "distillate_kmol_h", "z_c4"]].to_numpy()
        ]
    )
    act = test["xb_c4"].to_numpy()
    ss_res = float(((act - pred) ** 2).sum())
    ss_tot = float(((act - act.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    mae = float(np.mean(np.abs(act - pred)))

    # full-fit truth for the monotone response panel
    full = fit_truth_surface_3d(zvaried_csv)
    zs = np.linspace(0.30, 0.40, 40)
    traces = [(1.5, 34.5), (2.2, 35.0), (3.0, 36.0)]

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.0, 4.2))
    lo = min(act.min(), pred.min()) * 0.9
    hi = max(act.max(), pred.max()) * 1.1
    axA.plot([lo, hi], [lo, hi], color="0.5", ls="--", lw=1.0)
    axA.scatter(act, pred, s=40, color="#0072B2", edgecolor="white", zorder=3)
    axA.set_xlabel(r"actual $x_B$ (DWSIM, held-out $z=0.375$)")
    axA.set_ylabel(r"predicted $x_B$ (GP, trained on $z\neq0.375$)")
    axA.set_title(
        f"Leave-one-$z$-out: $R^2={r2:.3f}$, MAE$={mae:.4f}$ ($n={len(act)}$)", fontsize=9
    )
    axA.set_xlim(lo, hi)
    axA.set_ylim(lo, hi)

    for r, d in traces:
        xb = np.array([full.predict(r, d, z) for z in zs])
        axB.plot(zs, xb, lw=1.8, label=f"$R={r}$, $D={d}$")
    axB.axhline(SPEC, color="0.4", lw=1.0)
    axB.text(0.30, SPEC, f" spec $\\bar g={SPEC}$", va="bottom", ha="left", fontsize=8, color="0.3")
    axB.axvline(0.35, color="0.7", lw=0.8, ls="--")
    axB.set_xlabel(r"feed light-key fraction $z$")
    axB.set_ylabel(r"bottoms composition $x_B$")
    axB.set_title("Monotone $x_B$ response justifies the $z$-quantile oracle", fontsize=9)
    axB.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nominal", required=True)
    ap.add_argument("--zvaried", required=True)
    ap.add_argument("--outdir", default="docs/module3/paper/figures")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    xb_nom, truth, grid = _surfaces(args.nominal, args.zvaried)
    fig_backoff_fields(xb_nom, truth, grid, os.path.join(args.outdir, "F4_backoff_fields.png"))
    fig_surrogate_validation(args.zvaried, os.path.join(args.outdir, "F6_surrogate_validation.png"))
    print(f"wrote F4, F6 to {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
