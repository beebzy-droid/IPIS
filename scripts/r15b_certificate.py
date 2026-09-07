"""R1.5b + R2m2: a-priori certificate, finite-sample floor, and bound tightness.

Re-runs the certificate study under UNIT-LEVEL calibration (one score per unit, so
Theorem 1's i.i.d. hypothesis holds verbatim) and adds:

  * the finite-sample intercept sweep indexed explicitly on the number of UNITS
    (the published n=200..1600 sweep was run ad hoc and never committed; it is
    rebuilt here and re-indexed, since stacked scores are not independent draws);
  * bound tightness (R2 minor 2): Bound% = 100 alone cannot distinguish a valid
    bound from a vacuous one, so we report the margin between the certified bound
    and the measured coverage gap.

Run:  PYTHONPATH=src python3 scripts/r15b_certificate.py
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
from ipis.module2_pdm.scc.deactivation import R, simulate_condition

E1, A1 = 80e3, 5e3
E2, A2 = 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
ALPHA = 0.10
ETAS = [0.0, 0.25, 0.5, 1.0, 2.0]


def unit_scores(temp, n_units, eta, seed, rng):
    """One score per unit: each unit contributes one randomly chosen monitoring fraction."""
    runs = simulate_condition(temp, n_units, A1, E1, a2=A2, e2=E2, eta=eta, seed=seed)
    raw = np.empty(len(runs))
    dim = np.empty(len(runs))
    picks = rng.integers(0, len(FRACS), size=len(runs))
    for i, run in enumerate(runs):
        v, vt = score_run(run, FRACS[picks[i]], E1, A1)
        raw[i] = v
        dim[i] = vt
    return raw, dim


def departure(s, t, eta):
    h = (A2 / A1) * np.exp(-(E2 - E1) / (R * np.array([s, t])))
    return float(eta * abs(h[0] - h[1]))


def collect(n_units, seeds):
    """rows: (delta, scc_gap, dTV, naive_gap) over all (eta, ordered pair, seed)."""
    rows = []
    for eta in ETAS:
        per_pair = {}
        for s in range(seeds):
            rng = np.random.default_rng(s * 977 + 11)
            sc = {t: unit_scores(t, n_units, eta, s * 17 + i, rng) for i, t in enumerate(TEMPS)}
            for a, b in itertools.permutations(TEMPS, 2):
                cn = coverage_naive(sc[a][0], sc[b][0], ALPHA)
                cs = coverage_scc(sc[a][1], sc[b][1], ALPHA)
                per_pair.setdefault((a, b), []).append(
                    [max(0.0, 0.9 - cn), max(0.0, 0.9 - cs), tv_distance(sc[a][1], sc[b][1])]
                )
        for (a, b), v in per_pair.items():
            m = np.mean(v, axis=0)
            rows.append([departure(a, b, eta), m[1], m[2], m[0]])
    return np.array(rows)


def certificate(rows, seed=1):
    """Fit a + L*delta on 60% of configurations, validate the bound on the held-out 40%."""
    delta, gap, dtv = rows[:, 0], rows[:, 1], rows[:, 2]
    idx = np.random.default_rng(seed).permutation(len(rows))
    tr, te = idx[: int(0.6 * len(idx))], idx[int(0.6 * len(idx)) :]
    design = np.vstack([np.ones_like(delta[tr]), delta[tr]]).T
    coef, *_ = np.linalg.lstsq(design, dtv[tr], rcond=None)
    pred = coef[0] + coef[1] * delta[te]
    r2 = 1 - np.sum((dtv[te] - pred) ** 2) / np.sum((dtv[te] - dtv[te].mean()) ** 2)
    bound = 2 * pred
    holds = float(np.mean(gap[te] <= bound + 1e-9))
    margin = bound - gap[te]  # tightness: how much slack the certificate carries
    return {
        "a": float(coef[0]),
        "L": float(coef[1]),
        "r2": float(r2),
        "corr": float(np.corrcoef(delta, dtv)[0, 1]),
        "holds": holds,
        "margin_mean": float(margin.mean()),
        "margin_min": float(margin.min()),
        "margin_max": float(margin.max()),
        "gap_mean": float(gap[te].mean()),
        "bound_mean": float(bound.mean()),
    }


def main():
    out = {}

    print("=== certificate under UNIT-LEVEL calibration (400 units/condition, 5 seeds) ===")
    rows = collect(400, 5)
    c = certificate(rows)
    out["certificate_unit_400"] = c
    print(f"  dTV ~ {c['a']:.3f} + {c['L']:.2f}*delta")
    print(f"  held-out R^2 = {c['r2']:.3f}   corr(delta,dTV) = {c['corr']:.3f}")
    print(f"  bound holds on {100 * c['holds']:.0f}% of held-out configurations")
    print("\n=== R2 minor 2: bound TIGHTNESS (is the bound informative or vacuous?) ===")
    print(f"  mean measured gap  = {c['gap_mean']:.3f}")
    print(f"  mean certified bnd = {c['bound_mean']:.3f}")
    print(
        f"  margin (bound - gap): mean {c['margin_mean']:.3f}, "
        f"min {c['margin_min']:.3f}, max {c['margin_max']:.3f}"
    )

    print("\n=== finite-sample floor vs NUMBER OF UNITS (rebuilt, unit-indexed) ===")
    print(f"{'units':>7}{'intercept a':>13}{'a*sqrt(n)':>11}{'SCC gap eta=0':>15}")
    sweep = {}
    for n_units in [50, 100, 200, 400, 800]:
        r = collect(n_units, 3)
        cc = certificate(r)
        g0 = float(np.mean(r[r[:, 0] == 0.0][:, 1]))
        sweep[n_units] = {"a": cc["a"], "gap_eta0": g0}
        print(f"{n_units:>7}{cc['a']:>13.3f}{cc['a'] * np.sqrt(n_units):>11.2f}{g0:>15.3f}")
    out["floor_sweep_units"] = sweep

    ns = np.array(sorted(sweep))
    a_vals = np.array([sweep[n]["a"] for n in ns])
    slope = np.polyfit(np.log(ns), np.log(a_vals), 1)[0]
    out["floor_loglog_slope"] = float(slope)
    print(f"\n  log-log slope of intercept vs units = {slope:.3f}  (n^-1/2 predicts -0.500)")

    with open("out/r15b_certificate.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r15b_certificate.json")


if __name__ == "__main__":
    main()
