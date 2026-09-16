"""R2.1b: do either of the physically motivated psi candidates identify the C-MAPSS residual?

`r21_cmapss.py` shows that the dimensionless CALIBRATION transfers to C-MAPSS. This script
answers the second half of Reviewer 2's major comment 1: whether the A-PRIORI CERTIFICATE
transfers, i.e. whether a departure quantity psi computed without target failure data predicts
the residual coverage gap the way it does on the catalyst testbed.

Two candidates, both derivable before the target asset has failed:

  psi_amb   ambient referred distance, the Euclidean distance between the two regimes in
            (log theta, log delta). This is the departure in the corrected-condition
            coordinates themselves.
  psi_sig   healthy gas-path signature distance, the distance between the two regimes' mean
            referred sensor signatures over early-life (healthy) cycles of the TRAINING
            engines only. This is the departure the standard-day referral fails to absorb.

The SCC gaps are produced by exactly the protocol of `r21_cmapss.py` (engine-disjoint thirds,
one snapshot per engine per regime, ridge predictor fitted per source regime in the
gas-path-deviation coordinates), so only psi differs between the two arms.

Run:  PYTHONPATH=src python3 scripts/r21b_psi_candidates.py
"""

from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd
from cmapss_loader import load
from r21_cmapss import (
    ALPHA,
    BASE_CYCLES,
    SENSORS,
    TARGET,
    attach_referred,
    certificate,
    fit_predictor,
    one_snapshot_per,
)

DATASETS = ["FD002", "FD004"]
SEEDS = 3


def psi_matrices(df: pd.DataFrame, train_units, regimes) -> dict[str, dict]:
    """Both departure candidates, computed from healthy/operating data only."""
    amb = df.groupby("regime")[["theta", "delta"]].first()
    coord = np.column_stack([np.log(amb["theta"].to_numpy()), np.log(amb["delta"].to_numpy())])
    idx = {r: i for i, r in enumerate(amb.index)}
    psi_amb = {
        x: {y: float(np.linalg.norm(coord[idx[x]] - coord[idx[y]])) for y in regimes}
        for x in regimes
    }

    heal = df[(df.cycle <= BASE_CYCLES) & (df.unit.isin(train_units))]
    sig = heal.groupby("regime")[[f"r_{s}" for s in SENSORS]].mean()
    sig = (sig - sig.mean()) / sig.std().replace(0, 1.0)
    psi_sig = {
        x: {y: float(np.linalg.norm(sig.loc[x] - sig.loc[y])) for y in regimes} for x in regimes
    }
    return {"psi_amb": psi_amb, "psi_sig": psi_sig}


def gaps_with_both_psi(ds: str) -> list[dict]:
    """Per (seed, ordered regime pair): SCC gap plus both psi values."""
    df = attach_referred(load(ds))
    regimes = sorted(df.regime.unique())
    units = np.array(sorted(df.unit.unique()))
    feats = [f"d_{s}" for s in SENSORS]

    rows = []
    for seed in range(SEEDS):
        rng = np.random.default_rng(seed)
        perm = rng.permutation(units)
        n_tr = len(perm) // 3
        tr_u, cal_u, te_u = perm[:n_tr], perm[n_tr : 2 * n_tr], perm[2 * n_tr :]

        psis = psi_matrices(df, tr_u, regimes)
        cal = {r: one_snapshot_per(df, cal_u, r, rng) for r in regimes}
        te = {r: one_snapshot_per(df, te_u, r, rng) for r in regimes}
        models = {
            r: fit_predictor(df[(df.regime == r) & (df.unit.isin(tr_u))], feats, "ridge")
            for r in regimes
        }

        for a, b in itertools.permutations(regimes, 2):
            m = models[a]
            s_cal = m.predict(cal[a][feats].to_numpy()) - cal[a]["rul_cap"].to_numpy()
            s_te = m.predict(te[b][feats].to_numpy()) - te[b]["rul_cap"].to_numpy()
            k = min(int(np.ceil((1 - ALPHA) * (len(s_cal) + 1))), len(s_cal))
            q = np.sort(s_cal)[k - 1]
            rows.append(
                {
                    "seed": seed,
                    "src": a,
                    "tgt": b,
                    "psi_amb": psis["psi_amb"][a][b],
                    "psi_sig": psis["psi_sig"][a][b],
                    "scc_gap": max(0.0, TARGET - float(np.mean(s_te <= q))),
                }
            )
    return rows


def main() -> None:
    out = {}
    print(f"{'dataset':>8}{'psi candidate':>18}{'corr':>8}{'slope L':>10}{'bound holds':>13}")
    for ds in DATASETS:
        rows = gaps_with_both_psi(ds)
        for cand in ("psi_amb", "psi_sig"):
            arm = [{**r, "psi": r[cand]} for r in rows]
            cert = certificate(arm)
            out[f"{ds}|{cand}"] = cert
            print(
                f"{ds:>8}{cand:>18}{cert['corr']:>8.3f}{cert['L']:>10.4f}"
                f"{cert['holds'] * 100:>12.0f}%"
            )
        flat = pd.DataFrame(rows).groupby(["src", "tgt"], as_index=False).mean(numeric_only=True)
        out[f"{ds}|floor"] = {
            "gap_mean": float(flat.scc_gap.mean()),
            "gap_std": float(flat.scc_gap.std()),
            "gap_min": float(flat.scc_gap.min()),
            "gap_max": float(flat.scc_gap.max()),
        }
        print(
            f"{'':>8}{'residual gap':>18}  mean {flat.scc_gap.mean():.3f}  "
            f"sd {flat.scc_gap.std():.3f}  range {flat.scc_gap.min():.3f}-{flat.scc_gap.max():.3f}"
        )

    with open("out/r21b_psi_candidates.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r21b_psi_candidates.json")


if __name__ == "__main__":
    main()
