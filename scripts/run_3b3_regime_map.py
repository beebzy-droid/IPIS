"""3B.3 -- chance-constrained RTO regime map (Design B: CPP-style, feed-z).

Sweeps the feed-composition disturbance magnitude sigma_z and, at each, compares
four back-off strategies on the realized constraint-violation rate at the RTO
optimum (primary) and operating profit (secondary):

  oracle        truth conditional (1-alpha) quantile      -- achievable ideal
  cqr+apost     conditional CQR + CPP a-posteriori step    -- the proposed method
  naive-fixed   constant pooled conformal margin           -- baseline
  naive-adapt   normalized/adaptive conformal (marginal)   -- baseline that fails

Demonstrates: marginal back-offs (esp. adaptive) are exploited by the optimizer
(realized violation >> nominal alpha); the conditional + a-posteriori method
restores violation control toward the oracle.

Run:
  python scripts/run_3b3_regime_map.py \
    --nominal data/raw/dwsim/twin_runs.csv \
    --zvaried data/raw/dwsim/twin_runs_zvaried.csv
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from ipis.module3_rto import chance_rto as crto  # noqa: E402
from ipis.module3_rto.economics import EconomicsAnchor  # noqa: E402
from ipis.module3_rto.surrogate import (  # noqa: E402
    _fit,
    fit_gpr_from_csv,
    fit_truth_surface_3d,
)

SPEC = 0.02
ALPHA = 0.10
SEED = 20260614
SIGMAS = (0.004, 0.006, 0.008, 0.010, 0.015, 0.020, 0.025)
REALISTIC = 0.006


def _leave_z_out_r2(zvaried_csv: str, held_z: float = 0.375) -> tuple[float, float, int]:
    """Audit-F: fit the 3-D truth on all z != held_z, predict the held-out slice."""
    df = pd.read_csv(zvaried_csv)
    train = df[np.abs(df["z_c4"] - held_z) > 1e-9]
    test = df[np.abs(df["z_c4"] - held_z) <= 1e-9]
    tmp_train = os.path.join(tempfile.gettempdir(), "_ipis_lzo_train.csv")
    train.to_csv(tmp_train, index=False)
    try:
        surf = fit_truth_surface_3d(tmp_train)
    finally:
        if os.path.exists(tmp_train):
            os.remove(tmp_train)
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
    return r2, float(np.mean(np.abs(act - pred))), int(len(act))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nominal", required=True, help="z=0.35 sweep CSV (nominal surfaces)")
    ap.add_argument("--zvaried", required=True, help="feed-z campaign CSV (truth surface)")
    args = ap.parse_args()

    econ = EconomicsAnchor()
    xb_nom, _ = fit_gpr_from_csv(args.nominal)
    dfn = pd.read_csv(args.nominal)
    xd_nom = _fit(dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["xd_c4"], log_target=False)
    q_nom = _fit(
        dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["reboiler_duty_kW"], log_target=False
    )
    truth = fit_truth_surface_3d(args.zvaried)
    grid = crto.build_decision_grid(xb_nom, xd_nom, q_nom, econ)

    r2, mae, n = _leave_z_out_r2(args.zvaried)
    print("=== 3B.3 chance-constrained RTO regime map (Design B: feed-z, 1-alpha=0.90) ===")
    print(
        f"  truth surface: in-sample R2={truth.r_squared:.3f}; leave-z=0.375-out R2={r2:.3f} "
        f"MAE={mae:.4f} (n={n})  [audit-F validation]"
    )
    print(f"  spec xB<={SPEC}, decision box R[0.8,3.0] D[33,37], target violation <= {ALPHA:.2f}")
    print(
        "  NOTE: spec is physically unachievable for z>~0.38 within the D-bounds "
        "(distillate-flow limited); operational sigma_z must be tight.\n"
    )

    hdr = f"  {'sigma_z':>7} {'method':>13} {'profit$/h':>9} {'viol':>6} {'kappa':>5}  R*    D*"
    print(hdr)
    realistic_rows = {}
    for sig in SIGMAS:
        dist = crto.DisturbanceModel(sigma=sig)
        rng = np.random.default_rng(SEED)
        # the conditional-quantile estimate needs more data as the disturbance widens
        n_cal = int(1500 * max(1.0, sig / REALISTIC))
        cal = crto.sample_calibration(xb_nom, truth, dist, rng, n=n_cal)
        methods = {
            "oracle": crto.solve_chance_rto(
                grid,
                crto.oracle_backoff(truth, grid, dist, ALPHA),
                SPEC,
                truth,
                dist,
                rng,
                method="oracle",
            ),
            "cqr+apost": crto.aposteriori_tighten(
                grid, crto.cqr_backoff(cal, grid, ALPHA), SPEC, truth, dist, ALPHA, rng
            ),
            "naive-fixed": crto.solve_chance_rto(
                grid, crto.fixed_backoff(cal, ALPHA), SPEC, truth, dist, rng, method="naive-fixed"
            ),
            "naive-adapt": crto.solve_chance_rto(
                grid,
                crto.normalized_backoff(cal, grid, ALPHA),
                SPEC,
                truth,
                dist,
                rng,
                method="naive-adapt",
            ),
        }
        if abs(sig - REALISTIC) < 1e-9:
            realistic_rows = methods
        for name, res in methods.items():
            tag = " <-realistic" if abs(sig - REALISTIC) < 1e-9 else ""
            if not res.feasible_found:
                print(f"  {sig:>7.3f} {name:>13} {'INFEASIBLE':>22}{tag}")
            else:
                print(
                    f"  {sig:>7.3f} {name:>13} {res.profit_usd_per_h:>9.0f} "
                    f"{res.realized_violation:>6.3f} {res.kappa:>5.2f}  "
                    f"{res.reflux_ratio:.2f}  {res.distillate_kmol_h:.1f}{tag}"
                )
        print()

    # --- gate ---
    orc = realistic_rows["oracle"]
    cqr = realistic_rows["cqr+apost"]
    nad = realistic_rows["naive-adapt"]
    checks = {
        "framework valid: oracle controls violation (<= alpha + 0.04)": orc.feasible_found
        and orc.realized_violation <= ALPHA + 0.04,
        "selection effect: naive-adaptive violates (> 2x alpha)": nad.feasible_found
        and nad.realized_violation > 2 * ALPHA,
        "fix works: cqr+aposteriori controls violation (<= alpha + 0.04) at realistic sigma_z": cqr.feasible_found
        and cqr.realized_violation <= ALPHA + 0.04,
    }
    print("  -- gate (3B.3: conditional calibration restores RTO violation control) --")
    ok = True
    for label, passed in checks.items():
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {label}")
    print(f"\n3B.3 {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
