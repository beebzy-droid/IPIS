"""R1.4: risk that the dimensionless correction AMPLIFIES the shift under misspecified physics.

Reviewer 1 notes that SCC assumes the governing degradation law is known, which in real
machinery it often is not, and asks what happens when the physical model is partially wrong:
can dividing by a wrong scale sigma(theta) make things worse than not scaling at all?

Design. The true kinetics use activation energy E1_true. The practitioner assumes E_assumed.
To isolate the *similitude-relevant* error we hold the nominal rate at a reference temperature
fixed, k(T_ref) = k_true(T_ref), by re-fitting the pre-exponential:

    A_assumed = A_true * exp((E_assumed - E_true) / (R * T_ref))

so misspecification distorts only how the scale varies BETWEEN temperatures, which is exactly
what similitude depends on. Two variants:

  decoupled  predictor keeps the true kinetics, only the SCALE is misspecified. Isolates the
             risk the reviewer names: is the dimensionless correction itself harmful?
  coupled    predictor and scale both use the assumed kinetics (what a practitioner with one
             wrong model actually gets).

Backfire is declared where the SCC coverage gap exceeds the naive (unscaled) gap.

Run:  PYTHONPATH=src python3 scripts/r14_misspecification.py
"""

from __future__ import annotations

import itertools
import json

import numpy as np

from ipis.module2_pdm.scc.conformal import nominal_rate, one_sided_quantile
from ipis.module2_pdm.scc.deactivation import A_FAIL, R, simulate_condition

E1_TRUE, A1_TRUE = 80e3, 5e3
E2, A2 = 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
ALPHA = 0.10
N_UNITS = 400
SEEDS = 5
T_REF = 650.0
TARGET = 1 - ALPHA
E_GRID = [40e3, 55e3, 65e3, 72e3, 80e3, 88e3, 95e3, 110e3, 130e3, 160e3]


def a_for(e_assumed):
    """Pre-exponential that keeps k(T_REF) equal to the true rate."""
    return A1_TRUE * np.exp((e_assumed - E1_TRUE) / (R * T_REF))


def scores(temp, eta, seed, rng, e_pred, a_pred, e_scale, a_scale):
    """Unit-level scores with independently specified predictor and scale kinetics."""
    runs = simulate_condition(temp, N_UNITS, A1_TRUE, E1_TRUE, a2=A2, e2=E2, eta=eta, seed=seed)
    picks = rng.integers(0, len(FRACS), size=len(runs))
    k_pred = nominal_rate(temp, e_pred, a_pred)
    k_scale = nominal_rate(temp, e_scale, a_scale)
    raw = np.empty(len(runs))
    dim = np.empty(len(runs))
    for i, run in enumerate(runs):
        idx = min(int(np.searchsorted(run.t, FRACS[picks[i]] * run.life)), len(run.t) - 1)
        rul_true = run.life - run.t[idx]
        rul_pred = max(np.log(max(run.a_obs[idx], 1e-3) / A_FAIL), 0.0) / k_pred
        v = rul_pred - rul_true
        raw[i] = v
        dim[i] = v * k_scale
    return raw, dim


def run_setting(e_assumed, eta, coupled):
    a_assumed = a_for(e_assumed)
    e_pred, a_pred = (e_assumed, a_assumed) if coupled else (E1_TRUE, A1_TRUE)
    naive_gaps, scc_gaps = [], []
    for s in range(SEEDS):
        rng = np.random.default_rng(s * 977 + 11)
        sc = {
            t: scores(t, eta, s * 17 + i, rng, e_pred, a_pred, e_assumed, a_assumed)
            for i, t in enumerate(TEMPS)
        }
        for a, b in itertools.permutations(TEMPS, 2):
            qn = one_sided_quantile(sc[a][0], ALPHA)
            qs = one_sided_quantile(sc[a][1], ALPHA)
            naive_gaps.append(max(0.0, TARGET - float(np.mean(sc[b][0] <= qn))))
            scc_gaps.append(max(0.0, TARGET - float(np.mean(sc[b][1] <= qs))))
    return float(np.mean(naive_gaps)), float(np.mean(scc_gaps))


def main():
    out = {}
    for coupled in [False, True]:
        label = "coupled (predictor + scale wrong)" if coupled else "decoupled (scale only wrong)"
        print(f"\n=== {label} ===")
        print(f"{'E_assumed':>11}{'rel.err':>9}{'naive gap':>11}{'SCC gap':>10}{'verdict':>12}")
        for e in E_GRID:
            ng, sg = run_setting(e, 0.0, coupled)
            rel = (e - E1_TRUE) / E1_TRUE
            verdict = "BACKFIRE" if sg > ng else ("degraded" if sg > 0.05 else "ok")
            out[f"{'coupled' if coupled else 'decoupled'}|{e:.0f}"] = {
                "rel_err": rel,
                "naive": ng,
                "scc": sg,
                "backfire": bool(sg > ng),
            }
            print(f"{e / 1e3:>9.0f}k{rel:>+9.0%}{ng:>11.3f}{sg:>10.3f}{verdict:>12}")

    # tolerance band: largest |rel err| on the decoupled sweep with SCC gap still under 0.05
    dec = {k: v for k, v in out.items() if k.startswith("decoupled")}
    ok = [abs(v["rel_err"]) for v in dec.values() if v["scc"] <= 0.05]
    bad = [abs(v["rel_err"]) for v in dec.values() if v["backfire"]]
    print(f"\nSafe band (SCC gap <= 0.05): |dE/E| up to {max(ok):.0%}" if ok else "\nno safe band")
    print(
        f"Backfire (SCC worse than unscaled) first at |dE/E| = {min(bad):.0%}"
        if bad
        else "No backfire anywhere on the tested grid: scaling never worse than not scaling."
    )

    with open("out/r14_misspecification.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("wrote out/r14_misspecification.json")


# ---------------------------------------------------------------------------
# Is the dangerous regime DETECTABLE before deployment?
#
# Under a correct scale and exact similitude the dimensionless life D = life * k(T) is
# condition-invariant, so the ratio of median D between any two conditions is 1. A wrong
# activation energy tilts the scale between temperatures and drives that ratio away from 1.
# This is the catalyst-testbed form of the runtime similitude diagnostic in Section 3.5, and
# it uses only source-side data: no target failure history is required.
# ---------------------------------------------------------------------------


def invariance_check(e_assumed, n_boot=400, seed=0):
    """Bootstrap CI on the dimensionless-life ratio; returns (g, lo, hi, verdict)."""
    a_assumed = a_for(e_assumed)
    rng = np.random.default_rng(seed)
    lives = {}
    for i, t in enumerate(TEMPS):
        runs = simulate_condition(t, N_UNITS, A1_TRUE, E1_TRUE, a2=A2, e2=E2, eta=0.0, seed=100 + i)
        lives[t] = np.array([r.life for r in runs]) * nominal_rate(t, e_assumed, a_assumed)
    ratios = []
    for a, b in itertools.combinations(TEMPS, 2):
        la, lb = lives[a], lives[b]
        boot = np.array(
            [
                np.median(rng.choice(la, len(la), replace=True))
                / np.median(rng.choice(lb, len(lb), replace=True))
                for _ in range(n_boot)
            ]
        )
        ratios.append(
            (
                float(np.median(boot)),
                float(np.percentile(boot, 2.5)),
                float(np.percentile(boot, 97.5)),
            )
        )
    # worst pair drives the verdict
    worst = max(ratios, key=lambda r: abs(np.log(r[0])))
    g, lo, hi = worst
    if hi / lo > 4.0:
        verdict = "indeterminate"
    elif lo <= 1.0 <= hi:
        verdict = "holds"
    else:
        verdict = "violated"
    return g, lo, hi, verdict


def detectability():
    print("\n=== is the dangerous regime detectable BEFORE deployment? ===")
    print("dimensionless-life invariance check (source data only; g=1 under correct scale)")
    print(f"{'E_assumed':>11}{'rel.err':>9}{'g':>8}{'95% CI':>18}{'verdict':>16}")
    rows = {}
    for e in E_GRID:
        g, lo, hi, verdict = invariance_check(e)
        rel = (e - E1_TRUE) / E1_TRUE
        rows[f"{e:.0f}"] = {"rel_err": rel, "g": g, "lo": lo, "hi": hi, "verdict": verdict}
        print(f"{e / 1e3:>9.0f}k{rel:>+9.0%}{g:>8.3f}{f'[{lo:.2f}, {hi:.2f}]':>18}{verdict:>16}")
    with open("out/r14_detectability.json", "w") as fh:
        json.dump(rows, fh, indent=2)
    print("wrote out/r14_detectability.json")
    return rows


if __name__ == "__main__":
    main()
    detectability()
