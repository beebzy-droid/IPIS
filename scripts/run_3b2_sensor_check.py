"""run_3b2_sensor_check.py — 3B.2 gate: conformal soft sensor on the twin.

Two inputs:
  --nominal : the z=0.35 sweep (G2 output) -> 3B.1 GPR (R,D)->xB and ->tray-6 T
  --zvaried : the feed-z campaign (R x D x several z) -> sensor calibration data
              (the disturbance that gives the single-feature sensor its scatter)

Pass criteria (scoping D3):
  - one-sided coverage on a held-out test split reaches ~0.90 (finite-sample band)
  - the conformal width is heteroscedastic (CV > 0) — else it is just a fixed
    margin and cannot beat 3A
  - the interval-driven chance-constraint solve is feasible
  - PREVIEW: interval-driven back-off < fixed margin at the optimum (the 3B.3 win)

Run:
  python scripts/run_3b2_sensor_check.py --nominal data/raw/dwsim/twin_runs.csv \
      --zvaried data/raw/dwsim/twin_runs_zvaried.csv
"""

from __future__ import annotations

import argparse
import sys
import warnings

import numpy as np
import pandas as pd

from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile
from ipis.module3_rto.rto_surface import solve_rto_surface
from ipis.module3_rto.soft_sensor import TwinSoftSensor
from ipis.module3_rto.surrogate import fit_gpr_from_csv

_SEED = 20260613


def main(argv: list[str] | None = None) -> int:
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nominal", required=True, help="z=0.35 sweep CSV (surfaces)")
    ap.add_argument("--zvaried", required=True, help="feed-z campaign CSV (sensor calib)")
    ap.add_argument("--alpha", type=float, default=0.10)
    args = ap.parse_args(argv)

    # surfaces from the nominal sweep (3B.1)
    gpr_xb, gpr_tt = fit_gpr_from_csv(args.nominal)

    # sensor from the z-varied campaign: split into train / calib / test
    df = pd.read_csv(args.zvaried)
    t = df["tray6_T_C"].to_numpy()
    xb = df["xb_c4"].to_numpy()
    rng = np.random.default_rng(_SEED)
    idx = rng.permutation(len(df))
    n = len(df)
    tr, ca, te = idx[: n // 2], idx[n // 2 : 3 * n // 4], idx[3 * n // 4 :]

    sensor = TwinSoftSensor(alpha=args.alpha)
    sensor.fit(t[tr], xb[tr], t[ca], xb[ca])
    rep = sensor.validate_coverage(t[te], xb[te])

    # interval-driven vs fixed margin (sized to the one-sided split quantile)
    e_ca = xb[ca] - sensor._mu.predict(sensor._z(t[ca]))
    fixed = float(conformal_quantile(e_ca, 1.0 - args.alpha))
    bo = sensor.backoff_callable(gpr_tt.predict)
    opt_iv = solve_rto_surface(gpr_xb.predict, backoff=bo)
    opt_fx = solve_rto_surface(gpr_xb.predict, backoff=fixed)

    print("=== 3B.2 conformal soft-sensor gate ===")
    print(
        f"  one-sided coverage: target {rep.target:.2f}  empirical {rep.empirical:.3f}  (n_test={rep.n_test})"
    )
    print(f"  mean C+ = {rep.mean_halfwidth:.5f}   width CV = {rep.halfwidth_cv:.2f}")
    print(f"  fixed one-sided margin = {fixed:.5f}")
    if opt_iv and opt_fx:
        print(
            f"  interval-driven optimum: R*={opt_iv.reflux_ratio:.3f} D*={opt_iv.distillate_kmol_h:.3f} "
            f"xB={opt_iv.x_bottoms_lk:.4f} C+={opt_iv.backoff_at_opt:.5f} profit={opt_iv.profit_usd_per_h:.1f}"
        )
        print(
            f"  fixed-margin   optimum: R*={opt_fx.reflux_ratio:.3f} D*={opt_fx.distillate_kmol_h:.3f} "
            f"xB={opt_fx.x_bottoms_lk:.4f} C+={opt_fx.backoff_at_opt:.5f} profit={opt_fx.profit_usd_per_h:.1f}"
        )
        print(
            f"  PREVIEW profit delta (interval - fixed) = {opt_iv.profit_usd_per_h - opt_fx.profit_usd_per_h:.1f} USD/h"
        )

    checks = {
        "coverage reaches ~0.90 (>= target-0.05)": rep.empirical >= rep.target - 0.05,
        "width heteroscedastic (CV > 0.05)": rep.halfwidth_cv > 0.05,
        "interval-driven solve feasible": opt_iv is not None and opt_iv.feasible_found,
    }
    print("\n  -- gate (3B.2: sensor is calibrated + adaptive) --")
    ok = True
    for label, passed in checks.items():
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
    # The profit win is a 3B.3 outcome (measured at equal violation rate), shown
    # here only as a directional preview — it is NOT a 3B.2 pass/fail criterion.
    if opt_iv is not None:
        below = opt_iv.backoff_at_opt < fixed
        print(
            f"  [3B.3 preview] back-off at optimum {'<' if below else '>='} fixed margin "
            f"-> profit delta {opt_iv.profit_usd_per_h - opt_fx.profit_usd_per_h:+.1f} USD/h"
        )
    print(f"\n3B.2 {'PASS' if ok else 'FAIL'}  (real magnitude needs the DWSIM z-campaign)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
