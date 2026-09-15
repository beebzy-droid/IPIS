"""R15c: per-direction coverage under unit-level calibration.

The abstract quotes a DIRECTIONAL worst case ("coverage falls to 0.58"), not a mean, so it
must be recomputed under the unit-level calibration adopted in the R1.5 resolution.
Reports naive and SCC coverage for every ordered calibrate->deploy pair.

NOTE ON STATISTICS: this script averages COVERAGE over seeds and then takes the gap.
scc_gate.py, r15 and r15b average per-seed GAPS, which are clipped at zero and therefore
read higher. Do not mix the two conventions in the manuscript.

Run:  PYTHONPATH=src python3 scripts/r15c_directional.py
"""

import itertools
import json

import numpy as np

from ipis.module2_pdm.scc.conformal import coverage_naive, coverage_scc, score_run
from ipis.module2_pdm.scc.deactivation import simulate_condition

E1, A1, E2, A2 = 80e3, 5e3, 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
AL = 0.10
N = 400
S = 5
res = {}
for eta in [0.0, 2.0]:
    acc = {}
    for s in range(S):
        rng = np.random.default_rng(s * 977 + 11)
        sc = {}
        for i, t in enumerate(TEMPS):
            runs = simulate_condition(t, N, A1, E1, a2=A2, e2=E2, eta=eta, seed=s * 17 + i)
            pk = rng.integers(0, 3, size=len(runs))
            raw = np.empty(len(runs))
            dim = np.empty(len(runs))
            for j, r in enumerate(runs):
                v, vt = score_run(r, FRACS[pk[j]], E1, A1)
                raw[j] = v
                dim[j] = vt
            sc[t] = (raw, dim)
        for a, b in itertools.permutations(TEMPS, 2):
            acc.setdefault((a, b), []).append(
                [coverage_naive(sc[a][0], sc[b][0], AL), coverage_scc(sc[a][1], sc[b][1], AL)]
            )
    print(f"--- eta={eta} (unit-level calibration) ---")
    print(f"{'cal->dep':>14}{'naive cov':>11}{'SCC cov':>9}")
    worst = 1.0
    for (a, b), v in sorted(acc.items()):
        m = np.mean(v, axis=0)
        worst = min(worst, m[0])
        print(f"{f'{a:.0f}->{b:.0f}':>14}{m[0]:>11.3f}{m[1]:>9.3f}")
        res[f"{eta}|{a:.0f}->{b:.0f}"] = {"naive_cov": float(m[0]), "scc_cov": float(m[1])}
    print(f"  WORST naive coverage: {worst:.3f}  (gap {0.9-worst:.3f})")
    res[f"worst_naive_cov_eta{eta}"] = float(worst)
with open("out/directional.json", "w") as fh:
    json.dump(res, fh, indent=2)
