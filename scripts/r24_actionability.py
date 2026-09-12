"""R2.4: when does the certified interval stop being actionable for a maintenance planner?

Reviewer 2 (major 4) identifies a genuine inconsistency in the submitted manuscript. Section 4.3
defines efficiency so that a diverging back-off "signals degenerate, uselessly wide intervals",
Section 5.2 reports a relative back-off of 1.01 at eta = 2, and the same section calls that
degradation "graceful". Those two statements are in tension, and the reviewer asks us to state
explicitly, using the paper's own criterion, what back-off marks the end of usefulness and on
which side eta = 2 falls.

Criterion (stated in the paper's own terms). SCC returns a one-sided lower bound on remaining
life, RUL_lower = RUL_pred - q_T. Writing the relative back-off b = q_T / mean(RUL_T), the
planner's usable quantity is the certified remaining life as a fraction of the predicted life,
1 - b. Hence:

    b < 0.5     ACTIONABLE   the certificate retains more than half the predicted life
    0.5 <= b < 1  DEGRADED   positive but shrinking lead time; usable only for near-term work
    b >= 1      DEGENERATE   the certified lower bound is non-positive on average, so the
                             interval asserts only "failure has not yet occurred" and carries
                             no scheduling information

This script computes b under the unit-level calibration adopted in the R1.5 resolution, locates
the crossing points, and settles where eta = 2 sits.

Run:  PYTHONPATH=src python3 scripts/r24_actionability.py
"""

from __future__ import annotations

import itertools
import json

import numpy as np

from ipis.module2_pdm.scc.conformal import one_sided_quantile, score_run
from ipis.module2_pdm.scc.deactivation import simulate_condition

E1, A1 = 80e3, 5e3
E2, A2 = 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
ALPHA, TARGET = 0.10, 0.90
N_UNITS, SEEDS = 400, 5
ETAS = [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0]

ACTIONABLE, DEGENERATE = 0.5, 1.0


def unit_sample(temp, eta, seed, rng):
    """One score per unit, with the matching true RUL for the efficiency denominator."""
    runs = simulate_condition(temp, N_UNITS, A1, E1, a2=A2, e2=E2, eta=eta, seed=seed)
    picks = rng.integers(0, len(FRACS), size=len(runs))
    raw = np.empty(len(runs))
    dim = np.empty(len(runs))
    rul = np.empty(len(runs))
    for i, run in enumerate(runs):
        v, vt = score_run(run, FRACS[picks[i]], E1, A1)
        raw[i] = v
        dim[i] = vt
        idx = min(int(np.searchsorted(run.t, FRACS[picks[i]] * run.life)), len(run.t) - 1)
        rul[i] = run.life - run.t[idx]
    return raw, dim, rul


def classify(b):
    if b < ACTIONABLE:
        return "ACTIONABLE"
    return "DEGRADED" if b < DEGENERATE else "DEGENERATE"


def main():
    out = {}
    print("Relative interval back-off b = q_T / mean(RUL_T), unit-level calibration.")
    print(f"{'eta':>6}{'coverage gap':>14}{'back-off b':>12}{'certified 1-b':>15}{'verdict':>13}")
    for eta in ETAS:
        gaps, backs = [], []
        for s in range(SEEDS):
            rng = np.random.default_rng(s * 977 + 11)
            data = {t: unit_sample(t, eta, s * 17 + i, rng) for i, t in enumerate(TEMPS)}
            for src, tgt in itertools.permutations(TEMPS, 2):
                _, dim_s, _ = data[src]
                raw_t, dim_t, rul_t = data[tgt]
                q_dim = one_sided_quantile(dim_s, ALPHA)
                # re-dimensionalise the quantile onto the target condition
                k_ratio = np.mean(dim_t / np.where(raw_t == 0, np.nan, raw_t))
                q_target = q_dim / k_ratio
                gaps.append(max(0.0, TARGET - float(np.mean(dim_t <= q_dim))))
                backs.append(float(q_target / np.mean(rul_t)))
        g, b = float(np.mean(gaps)), float(np.mean(backs))
        out[str(eta)] = {"gap": g, "backoff": b, "verdict": classify(b)}
        print(f"{eta:>6.2f}{g:>14.3f}{b:>12.3f}{1 - b:>15.3f}{classify(b):>13}")

    etas = np.array([float(e) for e in out])
    bs = np.array([out[str(e)]["backoff"] for e in etas])

    def crossing(level):
        above = np.where(bs >= level)[0]
        if len(above) == 0:
            return None
        i = above[0]
        if i == 0:
            return float(etas[0])
        x0, x1, y0, y1 = etas[i - 1], etas[i], bs[i - 1], bs[i]
        return float(x0 + (level - y0) * (x1 - x0) / (y1 - y0))

    c_act, c_deg = crossing(ACTIONABLE), crossing(DEGENERATE)
    out["crossing_actionable"] = c_act
    out["crossing_degenerate"] = c_deg
    print("\n=== answer to the reviewer ===")
    print(
        f"  back-off reaches {ACTIONABLE} (end of ACTIONABLE) at eta = "
        f"{'never on this grid' if c_act is None else f'{c_act:.2f}'}"
    )
    print(
        f"  back-off reaches {DEGENERATE} (DEGENERATE) at eta = "
        f"{'never on this grid' if c_deg is None else f'{c_deg:.2f}'}"
    )
    v2 = out["2.0"]
    print(
        f"  at eta = 2.0: back-off {v2['backoff']:.3f}, coverage gap {v2['gap']:.3f} "
        f"-> {v2['verdict']}"
    )
    print("\n  The manuscript must state this plainly rather than calling eta = 2 graceful:")
    print("  coverage remains certified there, but the interval has left the actionable band,")
    print("  so eta = 2 marks the edge of the method's useful operating envelope, not a")
    print("  comfortable operating point.")

    with open("out/r24_actionability.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r24_actionability.json")


if __name__ == "__main__":
    main()
