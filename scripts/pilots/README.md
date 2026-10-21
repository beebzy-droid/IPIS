# Falsification-first pilots for M1 narrowing (N1)

Synthetic, seeded, standalone (numpy + scipy). Run from this folder.

| script | question | headline result |
|---|---|---|
| dead_time_pilot.py | Does single-state delayed ACI misbehave above gamma_crit? (exact score law) | theta=60, gamma=0.05: marginal cov 0.900, 54.7 % infinite intervals |
| windowed_pilot.py | Same, with the repository's sliding-window quantile and delayed score arrival; drift recovery vs phase-interleaved and Smith variants | 55.2 % infinite at marginal 0.900; recovery 17 / 78 / 12 steps |
| onset_period.py | Is the onset sharp at gamma_crit? Period near 4 theta + 2? | No sharp onset; period close at theta=60, 25-40 % off at theta=20 |
| h2_check.py | Does a linear stochastic model predict sd(alpha) and the infinite fraction? | Within 1-19 % for gamma <= 0.8 gamma_crit; fails near the boundary |
| persistence_pilot.py (2026-10-09; library-based, run from the repo root with `PYTHONPATH=src`) | Do the white-noise model and its design rule survive autocorrelated residuals? Does tuning gamma without the delay control the infinite share once the delay acts? | No. At lag-1 autocorrelation >= 0.9 the model under-predicts sd(alpha) by 38-76 %; delay-blind tuning gives 6.8-27.7 % infinite intervals at theta = 4-20, the white-noise rule 16.7-42.7 %, delay-aware replay tuning 0.2-0.8 % (budget 1 %); marginal coverage 0.900-0.901 in every cell |
| compensation_pilot.py (2026-10-13; library-based, run from the repo root with `PYTHONPATH=src`) | Does a (theta+1)-step residual predictor ahead of the loop (delay compensation) narrow intervals, cut unusable intervals and allow faster adaptation, and is its width ratio predictable from the autocorrelation? | Synthetic AR(1), phi = 0.965, all numbers on evaluation rows: median width -51 % (theta = 3) and -37 % (theta = 7); tuned step size 2.8-4.3 times larger at the same 1 % budget; worst local coverage 0.55 -> 0.78 (theta = 3); measured width ratio 0.7-4.4 % below the prediction in all 8 cells (phi = 0.9 and 0.965); tuning to 1 % gives 0.4-1.45 % out of sample at phi = 0.965 |
| p2_bound_check.py (2026-10-13; library-based, run from the repo root with `PYTHONPATH=src`) | Does Proposition P2 hold (level bounds; realised miscoverage within (1 + 2 gamma (theta + 1)) / (gamma T)) for adversarial positive scores? | 36 cases (theta up to 60, gamma up to 0.2; persistent, step and spike scores): no violation; largest deviation / bound 0.345 |
| p3_shape_check.py (2026-10-17) | How far can the ratio of 90 % interval widths stray from the standard-deviation ratio that P3 predicts, when the residual is not Gaussian? | AR(1), phi = 0.9, one-step horizon, 2 million steps: Gaussian +0.02 %, uniform -5.5 %, t5 -4.2 %, Laplace -0.7 % |
| baseline_dryrun.py (2026-10-20; library-based, run from the repo root with `PYTHONPATH=src`; evidence `docs/paper/evidence/baseline_dryrun_phi05.json` and `_phi09.json`) | Do the Appendix A baselines run end to end in the F7 design (TEP T1, theta = 4, 5 runs), at what cost, and how far are they from the compensated loop? | AR(1), phi = 0.5 / 0.9, F7 as ratified: conformal PID with the QR scorecaster +0.8 / +1.1 % in width, with the matched scorecaster 0.0 / 0.0 %, with Theta +22 / +13 %; SPCI -3.1 / -1.6 %; all valid, none meets F7 (nor D-P1.11's coverage-matched F7). At the loop's coverage, QR, matched and SPCI are -2.8 to +2.0 %. The first draft's selection rule gave conformal PID +11 to +32 % |

`drift_pilot.py` is intentionally NOT included: it held the quantile at nominal scale,
which manufactured infinite intervals after the drift step (THESIS_STANDARDS L9).

Timing note (2026-09-28): the `phase` loop in these pilots set the level for step t+theta
from err[t] before that label had arrived, i.e. one step less delay than the other loops.
Negligible at theta = 60 but biased in that method's favour. The library
(`delayed_aci.py`) uses the correct period theta + 1; cite only library-generated numbers.
