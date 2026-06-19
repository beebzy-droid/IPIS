"""Reproduce the SCC robustness sweep across departure T-dependence, magnitude, alpha.

Run:  conda activate ipis  &&  python scripts/scc_robustness.py
"""

from __future__ import annotations

import itertools

import numpy as np

from ipis.module2_pdm.scc.conformal import coverage_naive, coverage_scc, scores_for, tv_distance
from ipis.module2_pdm.scc.deactivation import R, simulate_condition

E1, A1 = 80e3, 5e3
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
N, SEEDS = 300, 3
ETAS = [0.0, 0.5, 1.0, 2.0]


def a2_for(e2: float, pert: float) -> float:
    return pert * A1 * np.exp((e2 - E1) / (R * 650.0))


def setting(e2: float, pert: float, alpha: float) -> tuple[float, float, float, float, float, bool]:
    a2 = a2_for(e2, pert)
    per_pair: dict[tuple[float, tuple[float, float]], np.ndarray] = {}
    for eta in ETAS:
        runs = []
        for s in range(SEEDS):
            sc = {
                temp: scores_for(
                    simulate_condition(temp, N, A1, E1, a2=a2, e2=e2, eta=eta, seed=s * 17 + i),
                    FRACS,
                    E1,
                    A1,
                )
                for i, temp in enumerate(TEMPS)
            }
            rr = {}
            for s_t, t_t in itertools.permutations(TEMPS, 2):
                cn = coverage_naive(sc[s_t][0], sc[t_t][0], alpha)
                cs = coverage_scc(sc[s_t][1], sc[t_t][1], alpha)
                rr[(s_t, t_t)] = np.array(
                    [
                        max(0.0, (1 - alpha) - cn),
                        max(0.0, (1 - alpha) - cs),
                        tv_distance(sc[s_t][1], sc[t_t][1]),
                    ]
                )
            runs.append(rr)
        for pair in runs[0]:
            per_pair[(eta, pair)] = np.mean([r[pair] for r in runs], axis=0)

    pairs = list(itertools.permutations(TEMPS, 2))
    ng0 = float(np.mean([per_pair[(0.0, p)][0] for p in pairs]))
    sg0 = float(np.mean([per_pair[(0.0, p)][1] for p in pairs]))
    sgmax = float(np.mean([per_pair[(ETAS[-1], p)][1] for p in pairs]))
    h = lambda temp: (a2 / A1) * np.exp(-(e2 - E1) / (R * temp))  # noqa: E731
    delta, dtv, gap = [], [], []
    for eta in ETAS:
        for s_t, t_t in pairs:
            delta.append(eta * abs(h(s_t) - h(t_t)))
            gap.append(per_pair[(eta, (s_t, t_t))][1])
            dtv.append(per_pair[(eta, (s_t, t_t))][2])
    delta, dtv, gap = np.array(delta), np.array(dtv), np.array(gap)
    corr = float(np.corrcoef(delta, dtv)[0, 1])
    coef = np.polyfit(delta, dtv, 1)
    hold = float(np.mean(gap <= 2 * (coef[1] + coef[0] * delta) + 1e-9))
    by_eta = {e: np.mean([per_pair[(e, p)][1] for p in pairs]) for e in ETAS}
    mono = all(by_eta[b] >= by_eta[a] - 0.01 for a, b in zip(ETAS[:-1], ETAS[1:], strict=False))
    return ng0, sg0, sgmax, corr, hold, mono


def main() -> None:
    print("Sweep A: departure T-dependence E2 (matched 30% magnitude), alpha=0.10")
    print(
        f"{'E2(kJ)':>8}{'naive g0':>10}{'SCC g0':>8}{'SCC gmax':>10}{'corr':>7}{'bound%':>8}{'mono':>6}"
    )
    for e2 in [95e3, 110e3, 130e3, 150e3]:
        ng0, sg0, sgmax, corr, hold, mono = setting(e2, 0.30, 0.10)
        print(
            f"{e2 / 1e3:>8.0f}{ng0:>10.3f}{sg0:>8.3f}{sgmax:>10.3f}{corr:>7.2f}{hold * 100:>7.0f}%{str(mono):>6}"
        )

    print("\nSweep B: departure magnitude (E2=110kJ), alpha=0.10")
    print(
        f"{'pert':>8}{'naive g0':>10}{'SCC g0':>8}{'SCC gmax':>10}{'corr':>7}{'bound%':>8}{'mono':>6}"
    )
    for pert in [0.15, 0.30, 0.60]:
        ng0, sg0, sgmax, corr, hold, mono = setting(110e3, pert, 0.10)
        print(
            f"{pert:>8.2f}{ng0:>10.3f}{sg0:>8.3f}{sgmax:>10.3f}{corr:>7.2f}{hold * 100:>7.0f}%{str(mono):>6}"
        )

    print("\nSweep C: coverage target alpha (E2=110kJ, 30%)")
    print(
        f"{'alpha':>8}{'naive g0':>10}{'SCC g0':>8}{'SCC gmax':>10}{'corr':>7}{'bound%':>8}{'mono':>6}"
    )
    for alpha in [0.05, 0.10, 0.20]:
        ng0, sg0, sgmax, corr, hold, mono = setting(110e3, 0.30, alpha)
        print(
            f"{alpha:>8.2f}{ng0:>10.3f}{sg0:>8.3f}{sgmax:>10.3f}{corr:>7.2f}{hold * 100:>7.0f}%{str(mono):>6}"
        )


if __name__ == "__main__":
    main()
