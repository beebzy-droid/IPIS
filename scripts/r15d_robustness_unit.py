"""R1.5d: robustness sweep re-run under UNIT-LEVEL calibration, with bound tightness.

Why this script exists
----------------------
`scripts/scc_robustness.py` produced Table 1 of the submitted manuscript using STACKED
calibration (`scores_for`, one score per (unit, monitoring fraction)). The R1.5 resolution
makes unit-level calibration the primary analysis, so Table 1 had to be re-run on the same
footing as Sections 5.1-5.3 or the manuscript would mix two calibration schemes, which is
exactly the inconsistency Reviewer 1 flagged.

Two further corrections relative to `scc_robustness.py`:

  * Bound% is now computed on HELD-OUT configurations (the intercept and slope are fit on
    60% of the (pair, eta) configurations and validated on the disjoint 40%), matching the
    Table 1 caption and `r15b_certificate.py`. The submitted script fit and checked on the
    same points, so the published "held-out" claim was not what the code computed.
  * R2 minor 2: the margin (certified bound minus measured gap) is reported per setting, so
    the table shows whether the bound is tight or merely valid.

Convention: coverage gaps are clipped at zero and averaged over seeds and pairs, the same
convention used by `scc_gate.py`, `r15_exchangeability.py` and `r15b_certificate.py`.

Run:  PYTHONPATH=src python3 scripts/r15d_robustness_unit.py
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
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
N_UNITS, SEEDS = 400, 5
ETAS = [0.0, 0.5, 1.0, 2.0]
PAIRS = list(itertools.permutations(TEMPS, 2))


def a2_for(e2: float, pert: float) -> float:
    """Pre-exponential of the secondary channel at a matched departure magnitude."""
    return float(pert * A1 * np.exp((e2 - E1) / (R * 650.0)))


def unit_scores(temp, n_units, a2, e2, eta, seed, rng):
    """One score per unit: each unit contributes one randomly chosen monitoring fraction."""
    runs = simulate_condition(temp, n_units, A1, E1, a2=a2, e2=e2, eta=eta, seed=seed)
    raw = np.empty(len(runs))
    dim = np.empty(len(runs))
    picks = rng.integers(0, len(FRACS), size=len(runs))
    for i, run in enumerate(runs):
        v, vt = score_run(run, FRACS[picks[i]], E1, A1)
        raw[i] = v
        dim[i] = vt
    return raw, dim


def collect(e2: float, pert: float, alpha: float) -> np.ndarray:
    """rows: (eta, delta, scc_gap, dTV, naive_gap) per (eta, ordered pair), seed-averaged."""
    a2 = a2_for(e2, pert)
    rows = []
    for eta in ETAS:
        per_pair: dict[tuple[float, float], list[list[float]]] = {}
        for s in range(SEEDS):
            rng = np.random.default_rng(s * 977 + 11)
            sc = {
                t: unit_scores(t, N_UNITS, a2, e2, eta, s * 17 + i, rng)
                for i, t in enumerate(TEMPS)
            }
            for a, b in PAIRS:
                cn = coverage_naive(sc[a][0], sc[b][0], alpha)
                cs = coverage_scc(sc[a][1], sc[b][1], alpha)
                per_pair.setdefault((a, b), []).append(
                    [
                        max(0.0, (1 - alpha) - cn),
                        max(0.0, (1 - alpha) - cs),
                        tv_distance(sc[a][1], sc[b][1]),
                    ]
                )
        for (a, b), v in per_pair.items():
            m = np.mean(v, axis=0)
            h = (a2 / A1) * np.exp(-(e2 - E1) / (R * np.array([a, b])))
            rows.append([eta, float(eta * abs(h[0] - h[1])), m[1], m[2], m[0]])
    return np.array(rows)


def setting(e2: float, pert: float, alpha: float, seed: int = 1) -> dict:
    """Acceptance criteria plus bound tightness for one robustness setting."""
    rows = collect(e2, pert, alpha)
    eta, delta, gap, dtv, naive = rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3], rows[:, 4]

    at0 = eta == ETAS[0]
    at_max = eta == ETAS[-1]
    by_eta = [float(np.mean(gap[eta == e])) for e in ETAS]

    idx = np.random.default_rng(seed).permutation(len(rows))
    tr, te = idx[: int(0.6 * len(idx))], idx[int(0.6 * len(idx)) :]
    design = np.vstack([np.ones_like(delta[tr]), delta[tr]]).T
    coef, *_ = np.linalg.lstsq(design, dtv[tr], rcond=None)
    bound = 2 * (coef[0] + coef[1] * delta[te])

    return {
        "naive_g0": float(np.mean(naive[at0])),
        "scc_g0": float(np.mean(gap[at0])),
        "scc_gmax": float(np.mean(gap[at_max])),
        "corr": float(np.corrcoef(delta, dtv)[0, 1]),
        "holds": float(np.mean(gap[te] <= bound + 1e-9)),
        "gap_mean": float(np.mean(gap[te])),
        "bound_mean": float(np.mean(bound)),
        "margin_mean": float(np.mean(bound - gap[te])),
        "monotone": bool(all(b >= a - 0.01 for a, b in zip(by_eta[:-1], by_eta[1:], strict=False))),
    }


def show(label: str, value: str, res: dict) -> None:
    print(
        f"{value:>8}{res['naive_g0']:>10.3f}{res['scc_g0']:>8.3f}{res['scc_gmax']:>10.3f}"
        f"{res['gap_mean']:>9.3f}{res['bound_mean']:>9.3f}{res['margin_mean']:>9.3f}"
        f"{res['holds'] * 100:>7.0f}%{str(res['monotone']):>6}"
    )


HEAD = (
    f"{'value':>8}{'naive g0':>10}{'SCC g0':>8}{'SCC gmax':>10}"
    f"{'gap':>9}{'bound':>9}{'margin':>9}{'bound%':>8}{'mono':>6}"
)


def main() -> None:
    out: dict[str, dict] = {"config": {"n_units": N_UNITS, "seeds": SEEDS, "etas": ETAS}}

    print(f"UNIT-LEVEL robustness sweep ({N_UNITS} units/condition, {SEEDS} seeds)")
    print("gap/bound/margin are means over HELD-OUT configurations (60/40 split)\n")

    print("Sweep A: departure T-dependence E2 (matched 30% magnitude), alpha=0.10")
    print(HEAD)
    for e2 in [95e3, 110e3, 130e3, 150e3]:
        res = setting(e2, 0.30, 0.10)
        out[f"E2_{e2 / 1e3:.0f}"] = res
        show("E2", f"{e2 / 1e3:.0f}", res)

    print("\nSweep B: departure magnitude (E2=110kJ), alpha=0.10")
    print(HEAD)
    for pert in [0.15, 0.30, 0.60]:
        res = setting(110e3, pert, 0.10)
        out[f"pert_{pert:.2f}"] = res
        show("pert", f"{pert:.2f}", res)

    print("\nSweep C: coverage target alpha (E2=110kJ, 30%)")
    print(HEAD)
    for alpha in [0.05, 0.10, 0.20]:
        res = setting(110e3, 0.30, alpha)
        out[f"alpha_{alpha:.2f}"] = res
        show("alpha", f"{alpha:.2f}", res)

    with open("out/r15d_robustness_unit.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r15d_robustness_unit.json")


if __name__ == "__main__":
    main()
