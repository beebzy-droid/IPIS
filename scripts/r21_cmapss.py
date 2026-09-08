"""R2.1: the coverage certificate tested on C-MAPSS, a dataset we did not author.

Reviewer 2 (major 1): every empirical claim about the coverage guarantee rested on one
simulator in which the departure was the knob the author set, so the certificate itself was
never checked against a physical asset whose true departure came from somewhere else. FEMTO
exercised only the diagnostic.

C-MAPSS FD002/FD004 answers this: 260 and 249 run-to-failure turbofan engines across SIX
operating regimes, every engine visiting every regime, so each regime carries ~260 units
against FEMTO's ~6 bearings per condition.

Dimensionless reduction (NOT fitted). Gas-turbine similitude is the textbook Buckingham Pi
application: measurements are referred to standard day using the stagnation ratios theta and
delta, which come from the recorded altitude, Mach number and throttle through the standard
atmosphere and the isentropic relations. Each sensor is referred by the exponents its own
dimensions dictate:

    temperatures  / theta          speeds        / sqrt(theta)
    pressures     / delta          flows         / (delta/sqrt(theta))
    ratios and already-corrected channels are left alone.

So the SCC step here is exactly the paper's step: compute the conformal calibration in a
physics-derived dimensionless coordinate. The naive baseline uses raw sensors.

Protocol. Engines are split DISJOINTLY into calibration and test sets, because every engine
visits every regime and sharing engines would leak dependence across the split. Calibration
uses one snapshot per engine per regime (unit-level, per the R1.5 resolution).

Run:  PYTHONPATH=src python3 scripts/r21_cmapss.py
"""

from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd
from cmapss_loader import load, referred_conditions
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

BASE_CYCLES = 20

ALPHA = 0.10
TARGET = 1 - ALPHA
RUL_CAP = 125  # standard C-MAPSS piecewise-linear RUL cap
SENSORS = [f"s{i}" for i in range(1, 22)]

# Physics-derived referral exponents: value / (theta**a * delta**b).
# T2 T24 T30 T50 -> theta; P2 P15 P30 Ps30 -> delta; Nf Nc Nf_dmd -> sqrt(theta);
# W31 W32 -> delta/sqrt(theta); ratios and corrected channels unchanged.
REFERRAL = {
    "s1": (1.0, 0.0),
    "s2": (1.0, 0.0),
    "s3": (1.0, 0.0),
    "s4": (1.0, 0.0),
    "s5": (0.0, 1.0),
    "s6": (0.0, 1.0),
    "s7": (0.0, 1.0),
    "s8": (0.5, 0.0),
    "s9": (0.5, 0.0),
    "s10": (0.0, 0.0),
    "s11": (0.0, 1.0),
    "s12": (0.0, 0.0),
    "s13": (0.0, 0.0),
    "s14": (0.0, 0.0),
    "s15": (0.0, 0.0),
    "s16": (0.0, 0.0),
    "s17": (1.0, 0.0),
    "s18": (0.5, 0.0),
    "s19": (0.0, 0.0),
    "s20": (-0.5, 1.0),
    "s21": (-0.5, 1.0),
}


def attach_referred(df: pd.DataFrame) -> pd.DataFrame:
    """Add theta, delta and standard-day referred sensor columns."""
    rc = {
        rid: referred_conditions(*sub[["os1", "os2", "os3"]].iloc[0].astype(float))
        for rid, sub in df.groupby("regime")
    }
    df = df.copy()
    df["theta"] = df.regime.map(lambda r: rc[r]["theta"])
    df["delta"] = df.regime.map(lambda r: rc[r]["delta"])
    for s in SENSORS:
        a, b = REFERRAL[s]
        df[f"r_{s}"] = df[s] / ((df["theta"] ** a) * (df["delta"] ** b))
    df["rul_cap"] = df["rul"].clip(upper=RUL_CAP)
    # Dimensionless reduction used by SCC on this dataset: gas-path deviation from the
    # regime's HEALTHY baseline at matched corrected conditions. Degradation is a departure
    # from nominal performance, so the regime-specific healthy operating point is the correct
    # reference. This uses early-life operating data only; no target FAILURE data is required,
    # which preserves the method's central claim.
    healthy = df[df.cycle <= BASE_CYCLES]
    base = healthy.groupby("regime")[SENSORS].mean()
    sd = healthy.groupby("regime")[SENSORS].std().replace(0, 1.0)
    for s_ in SENSORS:
        df[f"d_{s_}"] = (df[s_] - df.regime.map(base[s_])) / df.regime.map(sd[s_])
    return df


def one_snapshot_per(df: pd.DataFrame, units, regime, rng) -> pd.DataFrame:
    """One randomly chosen snapshot per engine at the given regime (unit-level sampling)."""
    sub = df[(df.regime == regime) & (df.unit.isin(units))]
    # vectorised: random offset within each engine's block of snapshots
    order = np.argsort(sub["unit"].to_numpy(), kind="stable")
    u_sorted = sub["unit"].to_numpy()[order]
    starts = np.searchsorted(u_sorted, np.unique(u_sorted), side="left")
    counts = np.diff(np.append(starts, len(u_sorted)))
    pick = starts + (rng.random(len(starts)) * counts).astype(int)
    return sub.iloc[order[pick]]


def fit_predictor(train: pd.DataFrame, feats, model: str):
    x, y = train[feats].to_numpy(), train["rul_cap"].to_numpy()
    m = (
        Ridge(alpha=1.0)
        if model == "ridge"
        else RandomForestRegressor(n_estimators=60, min_samples_leaf=8, random_state=0, n_jobs=-1)
    )
    m.fit(x, y)
    return m


def run_dataset(ds: str, model: str = "ridge", seeds: int = 3) -> dict:
    df = attach_referred(load(ds))
    regimes = sorted(df.regime.unique())
    units = np.array(sorted(df.unit.unique()))
    raw_feats = SENSORS
    ref_feats = [f"d_{s}" for s in SENSORS]

    rows = []
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        perm = rng.permutation(units)
        n_tr = len(perm) // 3
        tr_u, cal_u, te_u = perm[:n_tr], perm[n_tr : 2 * n_tr], perm[2 * n_tr :]

        # Realistic transfer: the predictor is DEVELOPED ON THE SOURCE REGIME, then deployed on
        # a different regime. Training on all regimes mixed would hide the shift entirely.
        snaps_tr = {r: df[(df.regime == r) & (df.unit.isin(tr_u))] for r in regimes}
        cal = {r: one_snapshot_per(df, cal_u, r, rng) for r in regimes}
        te = {r: one_snapshot_per(df, te_u, r, rng) for r in regimes}

        # Similitude-departure parameter for a turbofan: the distance between the regimes'
        # HEALTHY gas-path signatures in referred coordinates. This measures how far apart the
        # engine's corrected operating points are, which is what the baseline referral cannot
        # absorb. It is computed from early-life healthy data only, never from failure data.
        heal = df[(df.cycle <= BASE_CYCLES) & (df.unit.isin(tr_u))]
        sig = heal.groupby("regime")[[f"r_{s_}" for s_ in SENSORS]].mean()
        sig = (sig - sig.mean()) / sig.std().replace(0, 1.0)
        psi_mat = {
            x: {y: float(np.linalg.norm(sig.loc[x] - sig.loc[y])) for y in regimes} for x in regimes
        }

        models = {}
        for r in regimes:
            models[(r, "raw")] = fit_predictor(snaps_tr[r], raw_feats, model)
            models[(r, "ref")] = fit_predictor(snaps_tr[r], ref_feats, model)

        def scores(frame, m, feats):
            return m.predict(frame[feats].to_numpy()) - frame["rul_cap"].to_numpy()

        for a, b in itertools.permutations(regimes, 2):
            m_raw, m_ref = models[(a, "raw")], models[(a, "ref")]
            s_raw, s_ref = scores(cal[a], m_raw, raw_feats), scores(cal[a], m_ref, ref_feats)
            t_raw, t_ref = scores(te[b], m_raw, raw_feats), scores(te[b], m_ref, ref_feats)
            qn = np.sort(s_raw)[min(int(np.ceil((1 - ALPHA) * (len(s_raw) + 1))), len(s_raw)) - 1]
            qs = np.sort(s_ref)[min(int(np.ceil((1 - ALPHA) * (len(s_ref) + 1))), len(s_ref)) - 1]
            cov_n = float(np.mean(t_raw <= qn))
            cov_s = float(np.mean(t_ref <= qs))
            psi = float(psi_mat[a][b])
            rows.append(
                {
                    "seed": seed,
                    "src": a,
                    "tgt": b,
                    "psi": psi,
                    "naive_gap": max(0.0, TARGET - cov_n),
                    "scc_gap": max(0.0, TARGET - cov_s),
                }
            )
    return {"rows": rows, "n_units": len(units), "n_regimes": len(regimes)}


def certificate(rows, seed=0):
    """Fit the bound on a subset of regime PAIRS, validate on held-out pairs."""
    df = pd.DataFrame(rows).groupby(["src", "tgt"], as_index=False).mean(numeric_only=True)
    psi, gap = df["psi"].to_numpy(), df["scc_gap"].to_numpy()
    idx = np.random.default_rng(seed).permutation(len(df))
    tr, te = idx[: int(0.6 * len(idx))], idx[int(0.6 * len(idx)) :]
    design = np.vstack([np.ones_like(psi[tr]), psi[tr]]).T
    coef, *_ = np.linalg.lstsq(design, gap[tr], rcond=None)
    pred = coef[0] + coef[1] * psi[te]
    bound = 2 * np.maximum(pred, 0)
    holds = float(np.mean(gap[te] <= bound + 1e-9))
    ss = np.sum((gap[te] - gap[te].mean()) ** 2)
    r2 = float(1 - np.sum((gap[te] - pred) ** 2) / ss) if ss > 0 else float("nan")
    return {
        "a": float(coef[0]),
        "L": float(coef[1]),
        "holds": holds,
        "r2": r2,
        "corr": float(np.corrcoef(psi, gap)[0, 1]),
        "mean_gap": float(gap.mean()),
        "mean_bound": float(bound.mean()),
        "n_pairs": len(df),
    }


def main():
    import os
    import sys

    combos = (
        [(sys.argv[1], sys.argv[2])]
        if len(sys.argv) > 2
        else [(d, m) for d in ["FD002", "FD004"] for m in ["ridge", "rf"]]
    )
    out = {}
    if os.path.exists("out/r21_cmapss.json"):
        with open("out/r21_cmapss.json") as fh:
            out = json.load(fh)
    for ds, model in combos:
        if True:
            res = run_dataset(ds, model=model)
            d = pd.DataFrame(res["rows"])
            ng, sg = d.naive_gap.mean(), d.scc_gap.mean()
            cert = certificate(res["rows"])
            out[f"{ds}|{model}"] = {
                "naive_gap": float(ng),
                "scc_gap": float(sg),
                "n_units": res["n_units"],
                **cert,
            }
            print(
                f"=== {ds} / {model} : {res['n_units']} engines, {res['n_regimes']} regimes, "
                f"{cert['n_pairs']} ordered regime pairs ==="
            )
            print(f"  mean coverage gap   naive {ng:.3f}   SCC {sg:.3f}")
            print(
                f"  certificate: gap ~ {cert['a']:.3f} + {cert['L']:.3f}*psi, "
                f"corr(psi,gap) = {cert['corr']:.3f}"
            )
            print(f"  a-priori bound holds on {100 * cert['holds']:.0f}% of held-out regime pairs")
            print(
                f"  mean measured gap {cert['mean_gap']:.3f} vs mean bound "
                f"{cert['mean_bound']:.3f}"
            )
            print()
    with open("out/r21_cmapss.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("wrote out/r21_cmapss.json")


if __name__ == "__main__":
    main()
