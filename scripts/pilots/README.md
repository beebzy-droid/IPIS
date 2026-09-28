# Falsification-first pilots for M1 narrowing (N1)

Synthetic, seeded, standalone (numpy + scipy). Run from this folder.

| script | question | headline result |
|---|---|---|
| dead_time_pilot.py | Does single-state delayed ACI misbehave above gamma_crit? (exact score law) | theta=60, gamma=0.05: marginal cov 0.900, 54.7 % infinite intervals |
| windowed_pilot.py | Same, with the repository's sliding-window quantile and delayed score arrival; drift recovery vs phase-interleaved and Smith variants | 55.2 % infinite at marginal 0.900; recovery 17 / 78 / 12 steps |
| onset_period.py | Is the onset sharp at gamma_crit? Period near 4 theta + 2? | No sharp onset; period close at theta=60, 25-40 % off at theta=20 |
| h2_check.py | Does a linear stochastic model predict sd(alpha) and the infinite fraction? | Within 1-19 % for gamma <= 0.8 gamma_crit; fails near the boundary |

`drift_pilot.py` is intentionally NOT included: it held the quantile at nominal scale,
which manufactured infinite intervals after the drift step (THESIS_STANDARDS L9).

Timing note (2026-09-28): the `phase` loop in these pilots set the level for step t+theta
from err[t] before that label had arrived, i.e. one step less delay than the other loops.
Negligible at theta = 60 but biased in that method's favour. The library
(`delayed_aci.py`) uses the correct period theta + 1; cite only library-generated numbers.
