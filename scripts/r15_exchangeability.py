"""R1.5: within-unit temporal dependence in the conformal calibration layer.

The published SCC results stacked one score per (unit, monitoring fraction) pair, so a
unit with F monitoring fractions contributed F strongly dependent calibration points.
Theorem 1 assumes i.i.d. calibration draws. This script quantifies the consequence and
evaluates two exchangeability-respecting alternatives.

Calibration schemes
-------------------
stacked     as published: n = n_units * F dependent scores (reference only)
unit        one randomly chosen monitoring fraction per unit; n = n_units i.i.d. scores.
            Theorem 1 applies verbatim. PRIMARY.
block_max   per-unit block score = max over the unit's monitoring fractions. Exchangeable
            across units and certifies coverage SIMULTANEOUSLY at every monitoring point
            of a unit, a stronger and more useful maintenance guarantee.

Run:  PYTHONPATH=src python3 scripts/r15_exchangeability.py
"""

from __future__ import annotations

import itertools
import json

import numpy as np

from ipis.module2_pdm.scc.conformal import (
    coverage_naive,
    coverage_scc,
    score_run,
    tv_distance,
)
from ipis.module2_pdm.scc.deactivation import simulate_condition

E1, A1 = 80e3, 5e3
E2, A2 = 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
ALPHA = 0.10
N_UNITS = 400
SEEDS = 5
ETAS = [0.0, 0.25, 0.5, 1.0, 2.0]


def per_unit_scores(runs, fracs, e1, a1):
    """(n_units, F) arrays of raw and dimensionless scores, preserving unit grouping."""
    raw = np.empty((len(runs), len(fracs)))
    dim = np.empty((len(runs), len(fracs)))
    for i, run in enumerate(runs):
        for j, frac in enumerate(fracs):
            v, vt = score_run(run, frac, e1, a1)
            raw[i, j] = v
            dim[i, j] = vt
    return raw, dim


def reduce_scheme(raw, dim, scheme, rng):
    """Collapse (n_units, F) score matrices to a 1-D calibration/test sample."""
    if scheme == "stacked":
        return raw.ravel(), dim.ravel()
    if scheme == "unit":
        pick = rng.integers(0, raw.shape[1], size=raw.shape[0])
        idx = np.arange(raw.shape[0])
        return raw[idx, pick], dim[idx, pick]
    if scheme == "block_max":
        # max over the unit's monitoring fractions -> simultaneous coverage over the
        # monitored trajectory. Taken on the dimensionless score; the raw-score twin uses
        # the same fraction so the naive baseline stays comparable.
        jmax = np.argmax(dim, axis=1)
        idx = np.arange(raw.shape[0])
        return raw[idx, jmax], dim[idx, jmax]
    raise ValueError(scheme)


def one_run(eta, seed, scheme):
    rng = np.random.default_rng(seed * 977 + 11)
    mats = {}
    for i, temp in enumerate(TEMPS):
        runs = simulate_condition(temp, N_UNITS, A1, E1, a2=A2, e2=E2, eta=eta, seed=seed * 17 + i)
        mats[temp] = per_unit_scores(runs, FRACS, E1, A1)
    red = {t: reduce_scheme(*mats[t], scheme, rng) for t in TEMPS}
    out = {}
    for s_t, t_t in itertools.permutations(TEMPS, 2):
        cn = coverage_naive(red[s_t][0], red[t_t][0], ALPHA)
        cs = coverage_scc(red[s_t][1], red[t_t][1], ALPHA)
        out[(s_t, t_t)] = np.array(
            [
                max(0.0, (1 - ALPHA) - cn),
                max(0.0, (1 - ALPHA) - cs),
                tv_distance(red[s_t][1], red[t_t][1]),
                len(red[s_t][1]),
            ]
        )
    return out


def dependence_diagnostic():
    """How correlated are the within-unit scores? (the reason stacking is not i.i.d.)"""
    runs = simulate_condition(650.0, N_UNITS, A1, E1, a2=A2, e2=E2, eta=0.0, seed=3)
    _, dim = per_unit_scores(runs, FRACS, E1, A1)
    cors = []
    for a, b in itertools.combinations(range(len(FRACS)), 2):
        cors.append(float(np.corrcoef(dim[:, a], dim[:, b])[0, 1]))
    # design effect for a mean under equicorrelation rho: 1 + (F-1)*rho
    rho = float(np.mean(cors))
    F = len(FRACS)
    return cors, rho, 1 + (F - 1) * rho


def main():
    cors, rho, deff = dependence_diagnostic()
    print("=== within-unit score dependence (eta=0, T=650K) ===")
    print(f"pairwise correlations across monitoring fractions: {[round(c, 3) for c in cors]}")
    print(f"mean rho = {rho:.3f}   design effect 1+(F-1)rho = {deff:.2f}")
    print(
        f"stacked n = {N_UNITS * len(FRACS)} scores, but effective n ~ "
        f"{N_UNITS * len(FRACS) / deff:.0f} (vs {N_UNITS} units)"
    )

    results = {}
    print("\n=== coverage gap by calibration scheme (mean over pairs and seeds) ===")
    print(f"{'scheme':>10}{'eta':>7}{'naive gap':>11}{'SCC gap':>10}{'2*dTV':>9}{'n_cal':>8}")
    for scheme in ["stacked", "unit", "block_max"]:
        for eta in ETAS:
            runs = [one_run(eta, s, scheme) for s in range(SEEDS)]
            pairs = list(itertools.permutations(TEMPS, 2))
            vals = np.array([np.mean([r[p] for r in runs], axis=0) for p in pairs])
            ng, sg, tv, ncal = vals[:, 0].mean(), vals[:, 1].mean(), vals[:, 2].mean(), vals[0, 3]
            results[f"{scheme}|{eta}"] = {"naive": ng, "scc": sg, "tv": tv, "n_cal": int(ncal)}
            print(f"{scheme:>10}{eta:>7.2f}{ng:>11.3f}{sg:>10.3f}{2 * tv:>9.3f}{int(ncal):>8}")

    with open("out/r15_results.json", "w") as fh:
        json.dump(results, fh, indent=2)
    print("\nwrote out/r15_results.json")


if __name__ == "__main__":
    main()
