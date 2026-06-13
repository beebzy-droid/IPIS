"""run_g2_analysis.py — G2/3A closeout analysis on the DWSIM twin sweep.

Consumes the twin sweep CSV (produced by the DWSIM.Automation sweep,
scripts/run_g2_sweep.py) and produces the 3A deliverables:

  1. ln(x_B) surface fit on REAL Peng-Robinson x_B (R^2 + residual band)
  2. V1-V3 validation (envelope / mass balance / monotonicity) via validate_twin
  3. RTO back-off sweep on the twin surface (the head-to-head 3A baseline):
     constraint-active check + profit gradient per 0.001 back-off
  4. feasibility map: which grid points actually meet xB <= 0.02

This runs in the ipis env (pandas + numpy + gekko); no DWSIM needed — the
DWSIM half already happened in the sweep. Sandbox-testable.

Run:  python scripts/run_g2_analysis.py data/raw/dwsim/twin_runs.csv
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from ipis.module3_rto.economics import EconomicsAnchor
from ipis.module3_rto.rto_nlp import (
    DEFAULT_SPEC_XB_C4,
    fit_ln_xb_surface_from_csv,
    solve_rto,
)

SPEC_XB = DEFAULT_SPEC_XB_C4  # 0.02 bottoms C4


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="twin sweep CSV (G2 output)")
    ap.add_argument(
        "--backoffs",
        default="0.0,0.0025,0.005,0.010",
        help="comma-separated back-off values",
    )
    args = ap.parse_args(argv)

    df = pd.read_csv(args.csv)
    print(f"=== twin sweep: {len(df)} rows from {args.csv} ===")
    print(
        df[["reflux_ratio", "distillate_kmol_h", "xb_c4", "reboiler_duty_kW"]].to_string(
            index=False
        )
    )

    # 1. surface fit on real PR x_B
    surf = fit_ln_xb_surface_from_csv(args.csv)
    import math

    band = math.exp(surf.max_abs_resid)
    print(
        f"\n=== ln(xB) surface (real PR) ===\n"
        f"  R^2 = {surf.r_squared:.5f}   max|ln resid| = {surf.max_abs_resid:.3f} "
        f"(x{band:.2f} band on xB)"
    )

    # 2. feasibility map vs the 0.02 spec
    feas = df[df["xb_c4"] <= SPEC_XB]
    print(f"\n=== feasibility (xB <= {SPEC_XB}) ===")
    print(f"  {len(feas)}/{len(df)} grid points meet spec")
    if len(feas):
        print(
            "  feasible R range: "
            f"[{feas['reflux_ratio'].min()}, {feas['reflux_ratio'].max()}]; "
            f"D range: [{feas['distillate_kmol_h'].min()}, {feas['distillate_kmol_h'].max()}]"
        )

    # 3. RTO back-off sweep on the twin surface
    print("\n=== RTO on twin surface (back-off sweep) ===")
    econ = EconomicsAnchor()
    backoffs = [float(x) for x in args.backoffs.split(",")]
    prev = None
    print(
        f"  {'backoff':>8}  {'R*':>6}  {'D*':>7}  {'xB':>7}  {'Q_kW':>7}  {'profit$/h':>10}  active"
    )
    for bo in backoffs:
        res = solve_rto(surf, economics=econ, backoff=bo)
        if res is None:
            print(f"  {bo:8.4f}  (held)")
            continue
        print(
            f"  {bo:8.4f}  {res.reflux_ratio:6.3f}  {res.distillate_kmol_h:7.3f}  "
            f"{res.x_bottoms_lk:7.4f}  {res.reboiler_duty_kw:7.1f}  "
            f"{res.profit_usd_per_h:10.2f}  {res.active_constraints}"
        )
        if prev is not None:
            d_bo = bo - prev[0]
            if d_bo > 0:
                grad = (prev[1] - res.profit_usd_per_h) / (d_bo / 0.001)
                print(f"           -> profit gradient {grad:6.2f} USD/h per 0.001 back-off")
        prev = (bo, res.profit_usd_per_h)

    print("\nNote: V1-V3 validation is run separately via scripts/validate_twin.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
