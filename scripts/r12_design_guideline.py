"""R1.2: what data environment is required for the diagnostic to return "holds"?

Reviewer 1: on FEMTO the diagnostic returns indeterminate and SCC safely declines, which is
presented as an honest applicability limit. But if a widely used benchmark is rejected for data
scarcity and variability, the cases where the method is genuinely deployable may be very
limited. The practical requirements should be quantified: how many units per condition, and at
what unit-to-unit variability, are needed to obtain a usable verdict?

This script maps the diagnostic's operating envelope by sweeping

  * units per condition  n = 3 .. 160
  * unit-to-unit life scatter sigma_lnA (lognormal pre-exponential), which sets the spread that
    swamped the structural signal on FEMTO

under EXACT similitude (eta = 0), where the correct verdict is "holds". The fraction of trials
returning holds is the diagnostic's power, and the smallest n reaching a usable power is the
design guideline a practitioner needs before committing to the method.

Run:  PYTHONPATH=src python3 scripts/r12_design_guideline.py
"""

from __future__ import annotations

import itertools
import json

import numpy as np

from ipis.module2_pdm.scc.conformal import nominal_rate
from ipis.module2_pdm.scc.deactivation import simulate_condition

E1, A1 = 80e3, 5e3
TEMPS = [600.0, 650.0, 700.0]
N_GRID = [3, 6, 10, 20, 40, 80, 160]
SPREAD_GRID = [0.10, 0.25, 0.50, 0.80]
TRIALS = 40
N_BOOT = 300
CI_FOLD = 4.0  # CI wider than this factor is reported indeterminate (underpowered)


def verdict(n_units, sigma_lna, seed):
    """Diagnostic verdict from the dimensionless-life invariance check."""
    rng = np.random.default_rng(seed)
    lives = {}
    for i, t in enumerate(TEMPS):
        runs = simulate_condition(
            t, n_units, A1, E1, sigma_lna=sigma_lna, eta=0.0, seed=seed * 31 + i
        )
        lives[t] = np.array([r.life for r in runs]) * nominal_rate(t, E1, A1)
    worst = None
    for a, b in itertools.combinations(TEMPS, 2):
        la, lb = lives[a], lives[b]
        boot = np.array(
            [
                np.median(rng.choice(la, len(la), replace=True))
                / np.median(rng.choice(lb, len(lb), replace=True))
                for _ in range(N_BOOT)
            ]
        )
        lo, hi = np.percentile(boot, [2.5, 97.5])
        g = float(np.median(boot))
        if worst is None or abs(np.log(g)) > abs(np.log(worst[0])):
            worst = (g, float(lo), float(hi))
    g, lo, hi = worst
    if hi / lo > CI_FOLD:
        return "indeterminate"
    return "holds" if lo <= 1.0 <= hi else "violated"


def main():
    out = {}
    print("Fraction of trials returning HOLDS under exact similitude (correct verdict).")
    print("Rows: units per condition. Columns: unit-to-unit life scatter sigma_lnA.")
    header = "".join(f"{s:>10.2f}" for s in SPREAD_GRID)
    print(f"{'units':>7}{header}")
    for n in N_GRID:
        cells = []
        for sp in SPREAD_GRID:
            v = [verdict(n, sp, seed) for seed in range(TRIALS)]
            frac = float(np.mean([x == "holds" for x in v]))
            ind = float(np.mean([x == "indeterminate" for x in v]))
            out[f"{n}|{sp}"] = {"holds": frac, "indeterminate": ind}
            cells.append(frac)
        print(f"{n:>7}" + "".join(f"{c:>10.2f}" for c in cells))

    print("\nSmallest number of units reaching 80% holds, by scatter:")
    guideline = {}
    for sp in SPREAD_GRID:
        ok = [n for n in N_GRID if out[f"{n}|{sp}"]["holds"] >= 0.80]
        guideline[sp] = min(ok) if ok else None
        got = f"{min(ok)} units" if ok else f"not reached at n<={max(N_GRID)}"
        print(f"  scatter sigma_lnA = {sp:.2f}: {got}")
    out["guideline_80pct"] = {str(k): v for k, v in guideline.items()}

    print("\nFEMTO reference point: ~6 bearings per condition with a large life spread.")
    for sp in SPREAD_GRID:
        cell = out[f"6|{sp}"]
        print(
            f"  n=6, scatter {sp:.2f}: holds {cell['holds']:.2f}, "
            f"indeterminate {cell['indeterminate']:.2f}"
        )

    with open("out/r12_design_guideline.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r12_design_guideline.json")


if __name__ == "__main__":
    main()
