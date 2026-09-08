"""Probe: which dimensionless reduction actually restores exchangeability on C-MAPSS?

A  raw sensors (no reduction)
B  ambient referral by theta, delta (standard-day correction)
C  gas-path deviation from the regime's HEALTHY baseline, then referred.
   Uses early-life operating data at the target regime, which a commissioned asset has;
   it uses NO target failure data, so the paper's central claim is preserved.
"""

from __future__ import annotations

import itertools

import numpy as np
from cmapss_loader import load
from r21_cmapss import (
    ALPHA,
    SENSORS,
    TARGET,
    attach_referred,
    one_snapshot_per,
)
from sklearn.linear_model import Ridge

BASE_CYCLES = 20


def add_baseline_dev(df):
    """C: subtract each regime's healthy baseline (mean over first BASE_CYCLES) per sensor."""
    healthy = df[df.cycle <= BASE_CYCLES]
    base = healthy.groupby("regime")[SENSORS].mean()
    sd = healthy.groupby("regime")[SENSORS].std().replace(0, 1.0)
    out = df.copy()
    for s in SENSORS:
        out[f"d_{s}"] = (df[s] - df.regime.map(base[s])) / df.regime.map(sd[s])
    return out


def evaluate(df, feats, seeds=3):
    units = np.array(sorted(df.unit.unique()))
    regimes = sorted(df.regime.unique())
    gaps = []
    for seed in range(seeds):
        rng = np.random.default_rng(seed)
        perm = rng.permutation(units)
        n = len(perm) // 3
        tr_u, cal_u, te_u = perm[:n], perm[n : 2 * n], perm[2 * n :]
        cal = {r: one_snapshot_per(df, cal_u, r, rng) for r in regimes}
        te = {r: one_snapshot_per(df, te_u, r, rng) for r in regimes}
        for a, b in itertools.permutations(regimes, 2):
            tr = df[(df.regime == a) & (df.unit.isin(tr_u))]
            m = Ridge(alpha=1.0).fit(tr[feats].to_numpy(), tr["rul_cap"].to_numpy())
            sc = m.predict(cal[a][feats].to_numpy()) - cal[a]["rul_cap"].to_numpy()
            tt = m.predict(te[b][feats].to_numpy()) - te[b]["rul_cap"].to_numpy()
            q = np.sort(sc)[min(int(np.ceil((1 - ALPHA) * (len(sc) + 1))), len(sc)) - 1]
            gaps.append(max(0.0, TARGET - float(np.mean(tt <= q))))
    return float(np.mean(gaps))


def main():
    df = add_baseline_dev(attach_referred(load("FD002")))
    variants = {
        "A raw": SENSORS,
        "B ambient referral": [f"r_{s}" for s in SENSORS],
        "C baseline deviation": [f"d_{s}" for s in SENSORS],
    }
    print("FD002, mean coverage gap over 30 ordered regime pairs (target 0.90)")
    for name, feats in variants.items():
        print(f"  {name:>22}: {evaluate(df, feats):.3f}")


if __name__ == "__main__":
    main()
