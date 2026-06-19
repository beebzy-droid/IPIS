"""Reproduce the SCC gate: eta=0 coverage recovery + controlled-departure study.

Run:  conda activate ipis  &&  python scripts/scc_gate.py
"""

from __future__ import annotations

import itertools

import numpy as np

from ipis.module2_pdm.scc.conformal import coverage_naive, coverage_scc, scores_for, tv_distance
from ipis.module2_pdm.scc.deactivation import R, simulate_condition

E1, A1 = 80e3, 5e3
E2, A2 = 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
ALPHA, N, SEEDS = 0.10, 400, 5
ETAS = [0.0, 0.25, 0.5, 1.0, 2.0]


def departure(s: float, t: float, eta: float) -> float:
    h = (A2 / A1) * np.exp(-(E2 - E1) / (R * np.array([s, t])))
    return float(eta * abs(h[0] - h[1]))


def one_run(eta: float, seed: int) -> dict[tuple[float, float], np.ndarray]:
    sc = {
        temp: scores_for(
            simulate_condition(temp, N, A1, E1, a2=A2, e2=E2, eta=eta, seed=seed * 17 + i),
            FRACS,
            E1,
            A1,
        )
        for i, temp in enumerate(TEMPS)
    }
    out = {}
    for s_t, t_t in itertools.permutations(TEMPS, 2):
        cn = coverage_naive(sc[s_t][0], sc[t_t][0], ALPHA)
        cs = coverage_scc(sc[s_t][1], sc[t_t][1], ALPHA)
        out[(s_t, t_t)] = np.array(
            [
                max(0.0, (1 - ALPHA) - cn),
                max(0.0, (1 - ALPHA) - cs),
                tv_distance(sc[s_t][1], sc[t_t][1]),
            ]
        )
    return out


def main() -> None:
    agg = {}
    for eta in ETAS:
        runs = [one_run(eta, s) for s in range(SEEDS)]
        for pair in runs[0]:
            agg[(eta, pair)] = np.mean([r[pair] for r in runs], axis=0)

    print(f"{'eta':>5}{'naive gap':>11}{'SCC gap':>9}{'2*dTV':>8}{'Barber ok':>10}")
    rows = []
    for eta in ETAS:
        vals = np.array([agg[(eta, p)] for p in itertools.permutations(TEMPS, 2)])
        ok = all(
            agg[(eta, p)][1] <= 2 * agg[(eta, p)][2] + 0.02
            for p in itertools.permutations(TEMPS, 2)
        )
        print(
            f"{eta:>5.2f}{vals[:, 0].mean():>11.3f}{vals[:, 1].mean():>9.3f}{2 * vals[:, 2].mean():>8.3f}{str(ok):>10}"
        )
        for s_t, t_t in itertools.permutations(TEMPS, 2):
            g = agg[(eta, (s_t, t_t))]
            rows.append((departure(s_t, t_t, eta), g[1], g[2]))

    arr = np.array(rows)
    delta, dtv = arr[:, 0], arr[:, 2]
    rng = np.random.default_rng(1)
    idx = rng.permutation(len(arr))
    tr, te = idx[: int(0.6 * len(idx))], idx[int(0.6 * len(idx)) :]
    design = np.vstack([np.ones_like(delta[tr]), delta[tr]]).T
    coef, *_ = np.linalg.lstsq(design, dtv[tr], rcond=None)
    pred = coef[0] + coef[1] * delta[te]
    r2 = 1 - np.sum((dtv[te] - pred) ** 2) / np.sum((dtv[te] - dtv[te].mean()) ** 2)
    bound = 2 * (coef[0] + coef[1] * delta[te])
    print(f"\na-priori certificate: dTV ~ {coef[0]:.3f} + {coef[1]:.2f}*delta")
    print(f"  held-out R^2(dTV from physical departure) = {r2:.3f}")
    print(
        f"  held-out gap <= 2*(a+b*delta) holds on {100 * np.mean(arr[te, 1] <= bound + 1e-9):.0f}%"
    )


if __name__ == "__main__":
    main()
