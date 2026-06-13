"""run_3b1_gpr_check.py — 3B.1 gate: GPR surrogate reproduces the 3A twin.

Fits the GP surrogate (ADR-006) on the twin sweep CSV and checks it against the
3A quadratic surface and optimum. Pass criteria:
  - GP interpolates the training points (R^2 ~ 1, max|GP-true| small)
  - GP surface is monotone (xB falls with R and with D) — faithful, not oscillating
  - RTO optimum on the GP surface matches 3A (same binding spec, profit within
    a few USD/h, sensor-T in the M1 envelope)

Run:  python scripts/run_3b1_gpr_check.py data/raw/dwsim/twin_runs.csv
"""

from __future__ import annotations

import argparse
import sys
import warnings

import numpy as np
import pandas as pd

from ipis.module3_rto.rto_nlp import fit_ln_xb_surface_from_csv, solve_rto
from ipis.module3_rto.rto_surface import solve_rto_surface
from ipis.module3_rto.surrogate import fit_gpr_from_csv

ENVELOPE = (100.0, 112.0)


def main(argv: list[str] | None = None) -> int:
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="twin sweep CSV (G2 output)")
    args = ap.parse_args(argv)

    gpr_xb, gpr_tt = fit_gpr_from_csv(args.csv)
    quad = fit_ln_xb_surface_from_csv(args.csv)
    df = pd.read_csv(args.csv)

    gp_pts = np.array(
        [gpr_xb.predict(r, d) for r, d in zip(df.reflux_ratio, df.distillate_kmol_h, strict=False)]
    )
    err = np.abs(gp_pts - df.xb_c4.to_numpy()).max()

    rs = np.linspace(0.8, 3.0, 23)
    ds = np.linspace(33.0, 37.0, 21)
    mono_r = all(
        gpr_xb.predict(rs[i], d) >= gpr_xb.predict(rs[i + 1], d) - 1e-6
        for d in ds
        for i in range(len(rs) - 1)
    )
    mono_d = all(
        gpr_xb.predict(r, ds[j]) >= gpr_xb.predict(r, ds[j + 1]) - 1e-6
        for r in rs
        for j in range(len(ds) - 1)
    )

    gpr_opt = solve_rto_surface(gpr_xb.predict, backoff=0.0)
    quad_opt = solve_rto(quad, backoff=0.0)
    t_opt = gpr_tt.predict(gpr_opt.reflux_ratio, gpr_opt.distillate_kmol_h)

    print("=== 3B.1 GPR surrogate gate ===")
    print(f"  GP ln(xB) R^2={gpr_xb.r_squared:.5f}  tray-T R^2={gpr_tt.r_squared:.5f}")
    print(f"  max|GP - true xB| on points = {err:.5f}  (quadratic was ~0.0039)")
    print(f"  monotone: xB falls with R={mono_r}, falls with D={mono_d}")
    print(
        f"  3A quadratic optimum: R*={quad_opt.reflux_ratio:.3f} D*={quad_opt.distillate_kmol_h:.3f} "
        f"xB={quad_opt.x_bottoms_lk:.4f} profit={quad_opt.profit_usd_per_h:.1f}"
    )
    print(
        f"  3B.1 GPR  optimum   : R*={gpr_opt.reflux_ratio:.3f} D*={gpr_opt.distillate_kmol_h:.3f} "
        f"xB={gpr_opt.x_bottoms_lk:.4f} profit={gpr_opt.profit_usd_per_h:.1f}"
    )
    print(
        f"  sensor T at GPR optimum = {t_opt:.1f} C [{'IN' if ENVELOPE[0] <= t_opt <= ENVELOPE[1] else 'OUT'}]"
    )

    checks = {
        "GP interpolates points (err < 1e-3)": err < 1e-3,
        "monotone in R and D": mono_r and mono_d,
        "optimum profit within 5 USD/h of 3A": abs(
            gpr_opt.profit_usd_per_h - quad_opt.profit_usd_per_h
        )
        < 5.0,
        "optimum D* within 0.5 of 3A": abs(gpr_opt.distillate_kmol_h - quad_opt.distillate_kmol_h)
        < 0.5,
        "spec active at optimum": "c4_spec_backoff" in gpr_opt.active_constraints,
        "optimum sensor-T in M1 envelope": ENVELOPE[0] <= t_opt <= ENVELOPE[1],
    }
    print("\n  -- gate --")
    ok = True
    for label, passed in checks.items():
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
    print(f"\n3B.1 {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
