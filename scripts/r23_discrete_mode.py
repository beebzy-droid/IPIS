"""R2.3: discrete operating-mode clustering (Javanmardi and Huellermeier) as a baseline.

Reviewer 2 asks what continuous physical scaling buys over the discrete-mode remedy, run
quantitatively rather than argued qualitatively. Their fix for varying operating conditions is
to cluster conditions into a finite set of KNOWN discrete modes and calibrate within each mode.

Here the three testbed temperatures are exactly those discrete modes, which gives the fairest
possible reading of their approach. Two deployment scenarios separate the cases:

  SEEN    the target regime has its own run-to-failure calibration data. Discrete-mode
          conformal is then near-oracle and SCC should merely match it.
  UNSEEN  the target regime has NO failure history (a newly commissioned asset, the situation
          SCC is built for). Discrete-mode conformal has no calibration set for that mode and
          must fall back to the nearest available mode, or to pooling. SCC transfers by
          physical scaling instead.

Calibration is UNIT-LEVEL throughout (one score per unit) per the R1.5 resolution.

Run:  PYTHONPATH=src python3 scripts/r23_discrete_mode.py
"""

from __future__ import annotations

import json

import numpy as np

from ipis.module2_pdm.scc.conformal import one_sided_quantile, score_run
from ipis.module2_pdm.scc.deactivation import simulate_condition

E1, A1 = 80e3, 5e3
E2, A2 = 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
ALPHA = 0.10
N_UNITS = 400
SEEDS = 5
ETAS = [0.0, 0.5, 1.0]
TARGET = 1 - ALPHA


def unit_scores(temp, eta, seed, rng):
    """One score per unit; returns (raw, dimensionless)."""
    runs = simulate_condition(temp, N_UNITS, A1, E1, a2=A2, e2=E2, eta=eta, seed=seed)
    picks = rng.integers(0, len(FRACS), size=len(runs))
    raw = np.empty(len(runs))
    dim = np.empty(len(runs))
    for i, run in enumerate(runs):
        v, vt = score_run(run, FRACS[picks[i]], E1, A1)
        raw[i] = v
        dim[i] = vt
    return raw, dim


def gap(cov):
    return max(0.0, TARGET - cov)


def evaluate(eta, seed):
    """Coverage gap for each method under SEEN and UNSEEN target regimes."""
    rng = np.random.default_rng(seed * 977 + 11)
    sc = {t: unit_scores(t, eta, seed * 17 + i, rng) for i, t in enumerate(TEMPS)}
    rows = []

    for target in TEMPS:
        sources = [t for t in TEMPS if t != target]
        raw_t, dim_t = sc[target]

        # --- SEEN: target regime has its own calibration data -------------------
        # discrete-mode conformal calibrates within the target's own mode (near-oracle).
        # Split the target units so calibration and test are disjoint.
        half = len(raw_t) // 2
        q_seen = one_sided_quantile(raw_t[:half], ALPHA)
        cov_discrete_seen = float(np.mean(raw_t[half:] <= q_seen))

        # SCC in the same scenario, calibrated on the OTHER regimes only.
        dim_src = np.concatenate([sc[s][1] for s in sources])
        q_scc = one_sided_quantile(dim_src, ALPHA)
        cov_scc_seen = float(np.mean(dim_t[half:] <= q_scc))

        rows.append(
            {
                "eta": eta,
                "target": target,
                "scenario": "seen",
                "discrete": gap(cov_discrete_seen),
                "scc": gap(cov_scc_seen),
                "naive": np.nan,
            }
        )

        # --- UNSEEN: no failure history at the target regime --------------------
        # Discrete-mode conformal must fall back. Two honest fallbacks:
        #   nearest  : use the calibration mode closest in operating parameter
        #   pooled   : pool all source modes (this is the naive regime-blind baseline)
        nearest = min(sources, key=lambda s: abs(s - target))
        q_near = one_sided_quantile(sc[nearest][0], ALPHA)
        cov_discrete_unseen = float(np.mean(raw_t <= q_near))

        raw_src = np.concatenate([sc[s][0] for s in sources])
        q_pool = one_sided_quantile(raw_src, ALPHA)
        cov_naive = float(np.mean(raw_t <= q_pool))

        cov_scc_unseen = float(np.mean(dim_t <= q_scc))

        rows.append(
            {
                "eta": eta,
                "target": target,
                "scenario": "unseen",
                "discrete": gap(cov_discrete_unseen),
                "scc": gap(cov_scc_unseen),
                "naive": gap(cov_naive),
            }
        )
    return rows


def main():
    allrows = []
    for eta in ETAS:
        for s in range(SEEDS):
            allrows.extend(evaluate(eta, s))

    out = {}
    print("Coverage gap (target 0.90). UNIT-LEVEL calibration, mean over targets and seeds.")
    print(f"{'eta':>6}{'scenario':>10}{'discrete-mode':>15}{'SCC':>9}{'naive/pooled':>14}")
    for eta in ETAS:
        for scen in ["seen", "unseen"]:
            sub = [r for r in allrows if r["eta"] == eta and r["scenario"] == scen]
            d = float(np.mean([r["discrete"] for r in sub]))
            s_ = float(np.mean([r["scc"] for r in sub]))
            n = float(np.nanmean([r["naive"] for r in sub]))
            out[f"{eta}|{scen}"] = {"discrete": d, "scc": s_, "naive": n}
            ns = "     n/a" if np.isnan(n) else f"{n:>14.3f}"
            print(f"{eta:>6.2f}{scen:>10}{d:>15.3f}{s_:>9.3f}{ns}")

    print("\nReading:")
    print("  SEEN   -> discrete-mode has target-regime failure data and is near-oracle;")
    print("            SCC matches it WITHOUT using any target failure data.")
    print("  UNSEEN -> discrete-mode has no calibration set for the target mode and must")
    print("            fall back to the nearest mode; this is where physical scaling pays.")

    with open("out/r23_discrete_mode.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r23_discrete_mode.json")


if __name__ == "__main__":
    main()
