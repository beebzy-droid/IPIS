# N1 Phase 1 pre-registration

Status, 2026-10-17: **D-P1.1 to D-P1.6 ratified; D-P1.7 to D-P1.9 proposed; not frozen.**
- Bien ratified D-P1.1 to D-P1.6 on 2026-10-13 ("I'm inline with your recommendation").
- The training-split pre-check has run. Its evidence is in commit 98ac681
  (`docs/paper/evidence/phase1_precheck.json`); results are in Section 8.
- D-P1.7 to D-P1.9 are proposed and await ratification:
  - D-P1.7: elevate the claim to delay-compensated calibration, with SPCI and conformal PID as
    required baselines and the rules F5b, F6 and F7 that test it (Sections 4, 5.3 and 6).
  - D-P1.8: amend the TEP design after two findings: the excitation trips many runs, and the
    simulator's random-number generator repeats within 0.55 to 141 h, within 100 h for 41 of the
    58 seeds in the source (Sections 3D and 5.2).
  - D-P1.9: recalibrate F5 from the power analysis (Section 6).

The freeze follows their ratification. Until then no Phase 1 number exists from the debutanizer
validation or test rows or from new TEP runs.

Checks of this draft:
- 2026-10-09: two independent checks compared the numbers with the pilot outputs and the
  citations with the sources, and tested the logic of Section 6. They found an off-by-one in the
  delay convention, gaps that left the falsification tests undecidable, and several wording
  errors. All were corrected.
- 2026-10-13, first check of the additions. It found missed shutdowns and a seed rule that took 14
  of the 29 odd seeds listed in `teprob.f`; a pilot width ratio measured on the rows the forecaster was fitted on;
  prior art described too narrowly (conformal PID's scorecaster forecasts at the label horizon, and
  SPCI has a multi-step version); the ratified N1' text altered; F5 numbers quoted for the wrong
  arm; and an unstated assumption in P2.
- 2026-10-13, second check, of the corrections. It found the same seed used in two regimes, which
  makes those runs dependent; an F7 that bound only the baselines; an inaccurate account of why F5
  changed; an F4 that did not cover claim 2; a wrong condition in P3; and smaller slips.
- 2026-10-13, third check, of those corrections. It found that distinct seeds do not give
  independent runs either: the simulator's generator loses precision in double arithmetic and
  settles into short cycles that seeds share. It also found an F7 sentence left from the old rule,
  F6 assigned to two decisions, and smaller gaps.
- 2026-10-17, fourth check, of the generator replacement and the stream design. It reproduced the
  diagnosis, the MRG32k3a code and its stream jumps, the default build and every number of
  Sections 3D and 5.2. It found text that still described the seed design and smaller gaps.

All are corrected here. Each TEP run now draws from its own MRG32k3a stream, and the runs were
re-qualified (Sections 3D and 5.2). The power analysis was re-run with 200 studies per
persistence level (Section 3E). F5 and F7 were redefined, and F4 extended (Section 6).

## 1. Purpose

Phase 1 decides whether N1 survives process data. It tests:
- whether the delayed calibration loop degrades at documented delays (F2);
- whether marginal coverage misses that degradation (F3);
- whether delay-aware replay tuning holds a budget on uninformative intervals, with and without
  compensation (F5a, F5b);
- whether the width gain of delay compensation is predicted from the residual autocorrelation
  alone (F6, new);
- whether SPCI or conformal PID at the label horizon beats the compensated loop (F7, comparative,
  new).

## 2. Delay provenance (answers R4.7)

**Convention.** In `delayed_aci` the label of the interval issued at update s is first used at
update s + theta + 1. theta = 0 means the label arrives in time for the next update; that is
ordinary ACI.

A label that becomes available D after its sample, with updates every Du, has label age
a = ceil(D / Du) updates and dead time theta = a - 1. This assumes the usual scan order: new labels
are read at the start of a scan, before the interval is issued. If the calibrator issued first,
theta would be a, not a - 1. El Halabi and Brandt (2026) write tau = a.

| Process | Label and analyzer | Delay D | Update interval Du | Label age a | Dead time theta |
|---|---|---|---|---|---|
| Debutanizer (Fortuna et al. 2007) | C4 in the bottoms, by a GC on the deisopentanizer overhead; 15-min measuring cycle (Sec. 6.2, p. 117) | About 45 min (15-min cycle plus about 30 min for the analyzer's location; Sec. 6.2, p. 117). Ranges: 20 to 60 min (Sec. 5.5, p. 97); 30 to 75 min (Siddharth, Pathak and Pani 2019, p. 42) | 12 min (Sec. 6.2) | 4: the book's newest label is y(k-4), 48 min old | **3** (primary, Section 8) |
| | | | 6 min (see note) | 8 | **7** (secondary) |
| | | | per new GC value (15 min) | 3 | 2 |
| | | 20 to 75 min | 12 or 6 min | 2 to 13 | 1 to 12 |
| TEP (Downs and Vogel 1993) | XMEAS(40), G in the product; sampling interval 0.25 h (Table 5) | 0.25 h dead time (Table 5) | 0.05 h, the repository data | 5 | **4** |
| | | | per new analyzer value (0.25 h) | 1 | 0 |
| | | | 1 min (DCS execution) | 15 | 14 |

- **Recording interval of the public debutanizer file.** The book gives two values:
  - Sec. 4.1 (p. 53) describes a debutanizer set with ten candidate inputs recorded at Ts = 6 min,
    analysed for outliers in Table 4.1 (p. 72, all counts out of 2394);
  - the public file has 2394 rows and the seven inputs u1 to u7 that Table A.1 lists, and Sec. 6.2,
    where models on those inputs are built, states Ts = 12 min.

  The book does not say whether the public file is the Sec. 4.1 recording. The pre-check found the
  label is not recorded as a held value (Section 8), so the file cannot settle the question. Under
  the Section 5.1 rule, theta_doc = 3 is primary and theta = 7 is secondary.
- **The rejected manuscript's delay of 4.** Its bias-update code used the label 4 samples old
  (`apply_bias_update`, `y_true[t - delay]`). That equals Fortuna's documented latency at
  Ts = 12 min, not only a NARMA convention. In the convention above it is theta = 3.
- **TEP analyzer.** The Russell-Braatz simulator implements the analyzer as sample-and-hold. At
  each 0.25 h instant XMEAS(37-41) takes the composition captured 0.25 h earlier, plus noise
  (`teprob.f` lines 736-761, camaramm/tennessee-eastman-profBraatz commit 0643318). At 3-min rows a
  reading is held for 5 rows and is 5 rows old when it appears. The pre-check confirmed 5-row holds
  in all three regime files, and a 60-s run of the extended generator gave 15-row holds.
- **DCS execution rate.** A 1-min DCS execution rate is common (general knowledge, not verified).
  At that rate the debutanizer GC would give theta = 44 if the calibrator updated every row on held
  labels.
- **TEP alignment.** Phase 0 found a transport lag of 0 from XMEAS_3. That is an E-feed flow the
  control system manipulates, and 0 is the edge of the scanned range. Phase 1 aligns the TEP inputs
  at the analyzer's documented dead time instead (D-P1.3).

## 3. Pre-data findings (synthetic or simulator-only, library-generated)

### A and B. Persistence breaks the white-noise model and delay-blind tuning (`scripts/pilots/persistence_pilot.py`)

Residual streams are |x_t|, with x a Gaussian AR(1) of lag-1 autocorrelation phi.
- Settings: sequential loop, stored pairing, window R = 200, alpha* = 0.10. Here theta is the
  library's theta.
- Seeds: 5 in part A, 3 in part B. Calibration and evaluation segments do not overlap.

**A. The white-noise model is not a reliable predictor of the tail at any persistence, and, for
gamma >= 0.02, fails on sd(alpha) once phi reaches 0.9.** The delay also does more harm as
persistence rises. Marginal coverage reads 0.900 to 0.901 in every cell.

| phi | white-model error in sd(alpha), gamma >= 0.02 | infinite share at gamma = 0.02, theta = 0 / 4 / 8 / 20 |
|---|---|---|
| 0 | -6 % to +5 % | 0.00 / 0.02 / 0.12 / 0.92 % |
| 0.5 | -21 % to -11 % | 0.06 / 0.41 / 0.72 / 2.32 % |
| 0.9 | -63 % to -47 % | 0.74 / 8.40 / 14.92 / 22.99 % |
| 0.97 | -76 % to -64 % | 2.02 / 13.00 / 23.91 / 40.84 % |

- **The tail.** Even at phi = 0 the model's infinite share is off by more than 25 % in several
  cells: +67 % at theta = 0, gamma = 0.05; -30 % at theta = 8, gamma = 0.05; -62 % at theta = 20,
  gamma = 0.02. At phi = 0.5 it is under-predicted by 38 to 85 % for theta >= 4. F1 as ratified
  (25 % on sd or on the infinite share) would therefore fire at every persistence level tested.
- **Small step sizes.** At gamma = 0.005 the white model over-predicts sd(alpha) by 22 to 38 % even
  for phi = 0, because the sliding-window quantile adds feedback of its own.
- **Coloured variant.** This drives the same loop transfer function with the spectrum of the
  open-loop miss indicator, estimated on an independent calibration segment. It predicts sd(alpha)
  within -4 % to +24 % for phi <= 0.9, and over-predicts by 9 to 40 % at phi = 0.97. Its
  Gaussian-tail estimate of the infinite share is unreliable: 18.3 % predicted against 3.6 %
  measured at phi = 0.9, theta = 0, gamma = 0.05.

**B. Step-size tuning, budget eps = 1 % infinite intervals, evaluated at theta on an independent
segment.** Step sizes are means over 3 seeds. In the pilot, tuning searched the grid upward and
stopped at the first violation.

| phi | quantity | delay-blind (replay at theta = 0) | delay-aware (replay at theta) | model-based rule `design_gamma` |
|---|---|---|---|---|
| | | theta = 4 / 8 / 20 | theta = 4 / 8 / 20 | theta = 4 / 8 / 20 |
| 0.5 | gamma | 0.030 / 0.030 / 0.030 | 0.020 / 0.020 / 0.013 | 0.035 / 0.031 / 0.024 |
| 0.5 | infinite share | 2.1 / 3.4 / 7.4 % | 0.4 / 0.7 / 0.3 % | 3.1 / 3.7 / 4.0 % |
| 0.9 | gamma | 0.018 / 0.018 / 0.018 | 0.008 / 0.006 / 0.004 | as above |
| 0.9 | infinite share | 7.5 / 13.4 / 20.4 % | 0.6 / 0.8 / 0.4 % | 16.7 / 23.4 / 26.2 % |
| 0.97 | gamma | 0.010 / 0.010 / 0.010 | 0.003 / 0.002 / 0.002 | as above |
| 0.97 | infinite share | 6.8 / 13.8 / 27.7 % | 0.2 / 0.3 / 0.7 % | 18.7 / 30.5 / 42.7 % |

What this means:
1. On serially correlated residuals the phenomenon is stronger, not weaker.
2. The ratified model-based design rule (O3) is anti-conservative there.
3. Tuning on history without the delay is anti-conservative.
4. Replaying history through the delayed loop meets the budget out of sample. The price is a step
   size 1.5 to 6 times smaller than delay-blind tuning gives, which means slower adaptation.

Limits of the pilot: Gaussian AR(1) scores, stationary, one window length, three to five seeds.

### C. Delay compensation removes most of that price (`scripts/pilots/compensation_pilot.py`, 2026-10-13)

This is the 2x2 of R4.9:
- **Compensation**: off, or on through the direct (theta + 1)-step residual predictor of
  `evaluation/delay_compensation.py`, with its order chosen by BIC on the calibration segment.
- **Loop**: off (static split conformal), or on (delayed ACI tuned by replay, eps = 1 %).

Set-up:
- Residuals are a synthetic Gaussian AR(1) with phi = 0.965; 3 seeds.
- 10 000 calibration rows, followed by 20 000 evaluation rows. The forecaster, the static quantile
  and the step size come from the calibration rows. Every number below is measured on the
  evaluation rows, with no burn-in.
- phi = 0.965 matches the debutanizer residuals at lags of 10 and more (Section 8). At lags 2 to 5
  they decay faster, so this table is not a debutanizer prediction; Section 3F gives that.
- U is the uninformative share defined in Section 5.4, with y_range the range of the synthetic
  series on the calibration rows.

| theta | width ratio, compensated / raw: measured (predicted) | tuned gamma, raw -> compensated | U, raw -> compensated | median width, raw -> compensated | worst local coverage, raw -> compensated | U at gamma = 0.02, raw -> compensated |
|---|---|---|---|---|---|---|
| 0 | 0.258 (0.270) | 0.0090 -> 0.0367 | 0.95 -> 0.38 % | 3.19 -> 0.87 | 0.62 -> 0.84 | 2.46 -> 0.00 % |
| 3 | 0.491 (0.510) | 0.0038 -> 0.0150 | 1.12 -> 0.41 % | 3.39 -> 1.66 | 0.55 -> 0.78 | 10.25 -> 0.87 % |
| 7 | 0.649 (0.667) | 0.0023 -> 0.0100 | 0.83 -> 1.43 % | 3.47 -> 2.20 | 0.50 -> 0.70 | 21.48 -> 8.43 % |
| 12 | 0.772 (0.779) | 0.0020 -> 0.0057 | 1.45 -> 0.98 % | 3.52 -> 2.65 | 0.44 -> 0.62 | 31.19 -> 17.59 % |

- At phi = 0.9 the measured (predicted) ratios are 0.432 (0.447), 0.748 (0.769), 0.894 (0.910) and
  0.962 (0.968) at theta = 0, 3, 7 and 12.
- Marginal coverage is 0.899 to 0.900 in every loop-on cell.
- The first version of this table measured the ratio on the calibration rows, where the forecaster
  was fitted, and reported agreement within 1 %. Out of sample the measured ratio is 0.7 to 4.4 %
  below the prediction.

What this means:
1. The width ratio follows from the calibration-segment autocorrelation alone, to within 5 %. In
   all eight cells (both phi) the measured ratio is below the prediction, by 0.7 to 4.4 %. The cells
   of one seed share its raw evaluation scores, so these errors are not independent.
2. At theta = 3 and 7, compensation narrows the median interval of the tuned loop by 51 % and 37 %.
3. It raises the worst local coverage from 0.55 to 0.78 (theta = 3) and from 0.50 to 0.70
   (theta = 7).
4. It allows a 2.8 to 4.3 times larger step size within the same budget (ratios of the seed-mean
   step sizes; 1.5 to 2.1 times at phi = 0.9), which means faster adaptation.
5. Tuning to eps on the calibration rows does not hold eps exactly out of sample. Three of the
   eight tuned cells exceed 1 %: raw at theta = 3 (1.12 %), compensated at theta = 7 (1.43 %) and
   raw at theta = 12 (1.45 %). This is why D-P1.9 tunes with a safety factor (Section 6).
6. The benefit falls as the label ages, as the predicted ratio says.

### D. TEP feasibility: trips, and a random-number generator that repeats (2026-10-13 to 10-17)

**Trips.** Any violated operating limit shuts the simulated plant down; `teprob.f` tests the
noise-free states. From that row on, the simulator writes XMEAS 1-22 unchanged and without
measurement noise, so three unchanged rows in succession mark the shutdown (`shutdown_time`; a
freeze in the last rows also counts). A test on the written pressure or temperature is a
diagnostic only (`limit_time`), because the written values carry measurement noise.
- The first detector tested whether the written pressure or temperature exceeded its limit. A
  pressure trip can be written as exactly 3000.0 (the E15.7 output rounds it), which that strict
  test misses, and a shutdown on any other limit is invisible to it. Seed 4651207999 in mode1, for
  example, shut down on pressure at 5.15 h and was qualified by the first detector.
- The second detector counted a written reading at the limit as a trip. A noisy reading can cross
  3000 kPa a row before the shutdown or, in principle, without one. Selection now uses the freeze
  alone.

**Random numbers** (`scripts/tep_rng_check.py`; record `docs/paper/evidence/tep_rng_check.json`).
`teprob.f` draws every disturbance and noise term from TESUB7, the congruential generator
G <- 9228907 G mod 2^32 evaluated in double precision. The product exceeds 2^53, so IEEE double
arithmetic rounds it; the state gains trailing zero bits until G = 2^k m, after which the
recursion is exact with period 2^(30 - k) draws. A counting build gives 952 326 draws per simulated
hour. Over the source's own seed and the 57 seeds listed in `teprob.f`:

| Settled k | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 11 |
|---|---|---|---|---|---|---|---|---|
| Seeds | 17 | 24 | 8 | 2 | 4 | 1 | 1 | 1 |
| Period of the random stream | 141 h | 70.5 h | 35.2 h | 17.6 h | 8.8 h | 4.4 h | 2.2 h | 0.55 h |

- So 41 of the 58 seeds repeat their random stream within 100 h. With k = 4, the evaluation
  segment of a 100-h run (hours 70-100) would reuse the random numbers of the training segment
  (hours 0-30).
- For each k the odd m form two cycles (the multiplier is 3 mod 8). Different seeds with the same
  k and cycle draw the same numbers at different phases, so distinct seeds do not give
  independent runs. A seed used in two regimes gives two runs with the same random stream; their
  trip times often nearly coincide (for example 37.03 and 37.32 h for seed 1039839281 in mode1 and
  mode2; `generate_tep_modes.py --modes mode1 mode2 --seeds 1039839281 --record-s 60`).
- These periods hold for IEEE double arithmetic, as with gfortran 13 on x86-64. Whether the
  classic TEP data sets, generated in the 1990s, were affected depends on the arithmetic of the
  machine that generated them, which is not documented.
- A preliminary web search found no report of this defect. The systematic sweep should check
  (`LITERATURE_SWEEP_N1.md`).

**The remedy.** For Phase 1 runs, `generate_tep_modes.py --streams` replaces TESUB7 with MRG32k3a
(L'Ecuyer 1999; period about 2^191), exact in double precision by construction. Run j starts at
stream j, j x 2^127 draws from the RngStreams seed (12345, ..., 12345); a 100-h run uses about
10^8 draws, so no two runs share a random number. The Fortran code reproduces the Python reference
draw for draw (200 000 draws, no mismatch). Its first output from the RngStreams seed,
0.12701112204657714, and its stream jumps agree with an independent implementation (the mrg32k3a
package 2.0.2, checked 2026-10-17). The plant model, the disturbance definitions and the
controllers are unchanged. Without `--streams` or `--seeds` the generator compiles the source
unchanged, and reproduces the three Phase-1C files byte for byte (SHA-256 ca6c1129...d07560,
a6fc520d...59159d and f11802cb...b55a423, checked on 2026-10-13 against the committed generator).

**Within 100 h, with separate streams** (`scripts/tep_seed_qualification.py`; record
`docs/paper/evidence/tep_seed_qualification.json`). Streams 1 to 76 were dealt to the regimes in
rotation and each was run in its own regime (Section 5.2).
- mode1 tripped in 21 of its 26 candidates (5 survived, 19 %); mode2 in 11 of 25 (14 survived,
  56 %); mode3 in 8 of 25 (17 survived, 68 %). Trips fell between 5.8 h and 96.5 h.
- Every trip is a pressure trip. At the first frozen row of all 40 tripped runs the written
  pressure is 3000.00 to 3000.16 kPa and the temperature 120.36 to 120.44 C.

**Within 300 h** (D-P1.4's duration; original generator). Five seeds picked by hand from the first
seed list (2144342545, 2589274931, 3485834345, 4243534565 and 4356565463) tripped in all 15 runs,
between 24.3 h and 261.0 h. To reproduce: `generate_tep_modes.py --seeds 2144342545 2589274931
3485834345 4243534565 4356565463 --hours 300 --record-s 60`.

**D-P1.4's fallback fails.** It said: if a 300-h run trips, use the longest duration that does
not. The shortest of those trips, 24.3 h, is shorter than the 30-h training segment, so the
fallback leaves runs that cannot be used. D-P1.8 replaces it with the stream rule at 100 h.

The Phase-1C regime files used the source's own seed (k = 3, period 141 h), so none of them
repeats within its 100 h. All three share that one stream, however; they serve in Phase 1 only as
the pre-check's evidence on the analyzer's label hold (Section 8).

### E. Power (`scripts/phase1_power.py`, evidence `docs/paper/evidence/phase1_power.json`, 2026-10-13)

These are synthetic AR(1) residuals, analysed with the Phase 1 code. The debutanizer uses
phi = 0.965 and 0.970 (Section 8), with 200 replicates each. TEP uses phi = 0.5 and 0.9, with 200
studies of 15 independent runs each, in the D-P1.8 design.

Simplifications, which Phase 1 does not share:
- y_range is the range of the synthetic residual, not of y;
- the debutanizer bootstrap uses 1000 replicates (Phase 1: 2000);
- the residuals have no 5-row label hold, which TEP arm T1 has.

| Question | Debutanizer (1660 calibration rows, 719 evaluation rows, theta = 3) | TEP T1 (15 runs, 800 calibration and 600 evaluation rows each, theta = 4) |
|---|---|---|
| F2: probability the primary test detects the delay effect at the delay-blind step size | 0.12 and 0.095 (mean effect 2.4 and 2.0 percentage points) | 0.91 and 0.99 (mean effect 1.9 and 6.2 percentage points) |
| F6: width-ratio prediction error | single stream: median 11 to 12 %, 95th percentile 33 to 38 % | mean over 15 runs within 10 % in 100 % of studies at both phi |
| Step size, compensated / raw, both tuned to eps | n/a | 1.04 and 2.18 times |

The 15-run mean U of TEP T1, by loop and replay-tuning target (200 studies per phi):

| Loop, tuning target | phi = 0.5: mean over studies; 95th percentile | phi = 0.5: share of studies above eps; above 2 eps | phi = 0.9: mean over studies; 95th percentile | phi = 0.9: share of studies above eps; above 2 eps |
|---|---|---|---|---|
| Uncompensated, eps | 0.59 %; 1.43 % | 21 %; 0.5 % | 0.93 %; 2.36 % | 38 %; 9.5 % |
| Uncompensated, eps / 2 | 0.33 %; 1.00 % | 5.0 %; 0 % | 0.65 %; 1.71 % | 24.5 %; 4.0 % |
| Uncompensated, eps / 4 | 0.23 %; 0.60 % | 1.0 %; 0 % | 0.52 %; 1.54 % | 16 %; 1.5 % |
| Compensated, eps | 0.65 %; 1.64 % | 21 %; 1.5 % | 0.92 %; 2.09 % | 38.5 %; 7.0 % |
| Compensated, eps / 2 | 0.35 %; 0.97 % | 5.0 %; 0 % | 0.55 %; 1.44 % | 14 %; 2.5 % |
| Compensated, eps / 4 | 0.25 %; 0.64 % | 0 %; 0 % | 0.34 %; 1.03 % | 5.5 %; 0.5 % |

Consequences:
- The debutanizer cannot carry F2 on its own. With a single stream whose residual IACT is 62, its
  role is the real-plant demonstration, reported with honest intervals.
- The replicated TEP runs carry the inference.
- Tuned to eps, the loop meets eps on average (mean U 0.59 % and 0.93 %, uncompensated). The
  15-run mean is a mean of rare, clustered events, however, and its spread is wide: it exceeds eps
  in 21 % and 38 % of studies. F5 as ratified would therefore fire on a working loop in at least
  that share of studies (its mean criterion alone).
- At phi = 0.9 none of the three targets tried keeps the uncompensated loop's 15-run mean within eps
  in 95 % of studies (16 % above eps even at eps / 4). A test at eps would test the spread, not the
  method. D-P1.9 therefore tunes to eps / 2 and tests at 2 eps (Section 6).
- Compensation narrows the spread at high persistence (at eps / 4, 5.5 % of studies above eps,
  against 16 % uncompensated). It buys 2.2 times the step size at phi = 0.9, and little at
  phi = 0.5 (1.04 times).

### F. What P3 predicts for the debutanizer (training split only)

With a one-lag predictor at dead time theta, the width ratio is sqrt(1 - rho(theta + 1)^2), from
the pre-check autocorrelations (Section 8). Higher orders can only lower it.

| theta | 0 | 1 | 2 | 3 | 4 | 7 | 9 | 12 | 14 |
|---|---|---|---|---|---|---|---|---|---|
| rho(theta + 1) | 0.970 | 0.915 | 0.855 | not recorded | 0.759 | not recorded | 0.698 | not recorded | 0.631 |
| Predicted ratio, one lag | 0.24 | 0.40 | 0.52 | 0.52 to 0.65 | 0.65 | 0.65 to 0.72 | 0.72 | 0.72 to 0.78 | 0.78 |

- A range assumes rho lies between its neighbouring recorded lags.
- At theta_doc = 3 the debutanizer is predicted to gain less than the AR(1) pilot of Section 3C:
  0.52 to 0.65 with one lag, against 0.51 predicted for the pilot. The one-lag value is an upper
  bound; at the BIC order the prediction may be lower.
- **The analyzer-speed chart in one example.** Fortuna et al. attribute 30 of the 45 min to the
  analyzer's location. At Ts = 12 min, removing those 30 min would take the label age from 4 to 2,
  theta from 3 to 1, and the predicted ratio from 0.52-0.65 to 0.40. The compensated interval would
  be a further 22 to 38 % narrower.
- The Phase 1 runner computes the exact prediction, at the BIC order, from the training residuals.
  It writes the prediction to the evidence before it reads the evaluation rows.

## 4. The claim

**Ratified N1' (D-P1.1, 2026-10-13), verbatim.** Suppose a soft sensor's laboratory or analyzer
labels arrive theta calibrator updates late.
- The natural single-state adaptive conformal recursion is then an integral loop with dead time
  theta. It is linearly stable only for gamma < 2 sin(pi / (4 theta + 2)).
- Process residuals are serially correlated. On them, the loop issues a material share of
  uninformative intervals at documented analyzer delays, while marginal coverage reads nominal.
- Step sizes tuned on history without the delay are anti-conservative. So is the model-based rule
  that assumes uncorrelated residuals.
- Tuning instead by replaying historical residuals through the delayed loop, capped by the
  stability limit, keeps the uninformative share within a stated budget out of sample.

Proposed (D-P1.9): the stated budget is 2 eps for the mean over the TEP runs, held by tuning to
eps / 2 (F5a, Section 6). Section 3E gives the reason: the run mean of rare, clustered events
spreads too widely for a test at eps.

**Proposed N1'' (D-P1.7): delay-compensated conformal calibration with a predictable width.** It
keeps N1' as the diagnosis and adds three things.
- **Remedy.** Predict the persistent part of the residual theta + 1 updates ahead from the labels in
  hand, centre the interval on that prediction, and let the delayed loop calibrate only the
  prediction error. In control terms, the predictable part of the disturbance is removed before the
  dead-time loop acts on it: the minimum-variance principle (Astrom 1970). The miss process that
  drives the loop becomes less persistent, so the loop holds the budget at a larger step size.
- **Design tool.** The width of the compensated interval relative to the uncompensated one is
  predicted from the residual autocorrelation alone, at every analyzer delay, before deployment
  (P3). The chart of that ratio against label age prices analyzer speed and location
  (Section 3F). Its precision depends on how much data it is checked on. In simulation, one
  debutanizer-length stream strays from the prediction by 11 to 12 % (median) and up to 33 to
  38 % (95th percentile); the mean over 15 TEP runs stays within 10 % (Section 3E).
- **Validation.** Both are tested out of sample on process data, against SPCI and conformal PID at
  the label horizon.

One-sentence result for the editor (to be filled with Phase 1 numbers): *"With the laboratory late
by theta samples, conformal soft-sensor intervals can be X % narrower and stay usable, and the
achievable width at a given analyzer delay can be read off the residual autocorrelation before
deployment."*

Three propositions carry the analysis. Each is short and engineering-facing.
- **P1, stability.** The linearised single-state delayed loop is stable if and only if
  0 < gamma < 2 sin(pi / (4 theta + 2)). This is Levin and May (1976) applied to the loop.
- **P2, why marginal coverage cannot detect the failure.**
  - Statement: for any sequence of positive scores, the level stays in
    [-gamma(theta+1), 1 + gamma(theta+1)], and the realised miscoverage of the T labelled samples
    satisfies |mean(err) - alpha*| <= (1 + 2 gamma (theta + 1)) / (gamma T).
  - The scores must be positive. At a level of 1 or more the library issues a half-width of 0, and
    a score of exactly 0 then counts as covered, so the level can climb without bound. Absolute
    residuals of a continuous variable are positive with probability 1.
  - Consequence: marginal coverage converges to nominal by construction, however many intervals are
    infinite.
  - Origin: this extends the Gibbs and Candes (2021) argument to the single-state delayed
    recursion; El Halabi and Brandt (2026) prove the analogue for the phase-interleaved one.
  - Numerical check (`scripts/pilots/p2_bound_check.py`): 36 adversarial cases (theta up to 60,
    gamma up to 0.2, persistent, step and spike scores, all positive), with no violation and a
    largest ratio of deviation to bound of 0.345.
- **P3, delay-limited width.**
  - Statement: let the residual r be stationary with autocorrelation rho. The best linear predictor
    of r_t from the p most recent labels available at issue time, r_{t-theta-1}, ...,
    r_{t-theta-p}, leaves the error-variance fraction 1 - c' R^{-1} c. Here c_j = rho(theta + j)
    for j = 1, ..., p, and R_jk = rho(|j - k|) (`predicted_width_ratio`).
  - The fraction cannot rise as p grows. Its limit is the (theta + 1)-step minimum-variance
    prediction error, which Harris (1989) made the benchmark of control-performance assessment. No
    linear predictor of those labels does better.
  - The square root of the fraction is the ratio of standard deviations. It is the ratio of
    interval widths when the prediction error and the residual share one standardized
    distribution, as for Gaussian residuals. Otherwise the two can differ: for AR(1) residuals
    with phi = 0.9 and uniform or t5 innovations, the width ratio at a one-step horizon is 4.2 to
    5.5 % below the standard-deviation ratio (`scripts/pilots/p3_shape_check.py`, 2 million
    steps).
  - For AR(1) residuals the fraction is 1 - phi^(2(theta+1)) at every p.

**Positioning.** Sources: the 2026-10-13 web sweep, full texts read (`LITERATURE_SWEEP_N1.md`,
rows 11 and 12). Section 10 of `M1_NARROWING_PROPOSAL.md` still binds, except where it names the
noise-gain rule as the contribution, which N1' superseded. Forecasting at the label horizon is
prior art:
- **Conformal PID** (Angelopoulos, Candes and Tibshirani, NeurIPS 2023).
  - Its scorecaster forecasts the quantile of the next score. In the COVID experiment it forecasts
    the quantile of the score at t + 4, matching the 4-week horizon (Sec. 1.2, App. E).
  - The paper does not discuss delayed feedback or dead time. It does not say whether the
    quantile-tracking update waits for the delayed outcome.
  - Its learning rate is a fixed fraction of the trailing maximum score. The paper notes that
    "extremely high learning rates result in volatile sets" (Sec. 2.1).
- **SPCI** (Xu and Xie, ICML 2023; it builds on EnbPI, by the same authors).
  - It predicts conditional quantiles of the future residual from the past w residuals with a
    quantile random forest.
  - Its multi-step version (Sec. 5.2, App. B.3, Algorithm 3) fits one forest per horizon, with
    labels revealed only every S steps.
  - It refits its forest as residuals arrive, but has no feedback loop on coverage, so it has no
    step size and no dead-time loop.
  - Its own coverage guarantee is asymptotic, under stated assumptions (Thm 2). A split variant
    (Algorithm 2, Prop. 1) has a finite-sample guarantee under exchangeability. It gives no width
    bound.
- **El Halabi and Brandt (2026)** analyse delayed-feedback ACI without compensation.

N1'' does not claim forecasting the residual or the score at the label horizon. It claims four
things:
1. the dead-time analysis of the single-state loop on persistent residuals (P1, P2, Sections 3A
   and 3B);
2. compensation analysed and tested as dead-time compensation of that loop: its effect on the
   persistence of the miss process, on the step size that holds the budget, and on local coverage.
   Conformal PID reports more stable coverage and tighter sets from a scorecaster ahead of quantile
   tracking (Sec. 2.3), without delays; claim 2 is limited to the delayed loop and its step size;
3. the delay-limited width bound P3 and the analyzer-speed chart;
4. validation on process data, with SPCI multi-step and conformal PID at the label horizon as
   baselines. SPCI is the conditional EnbPI that R4.9 asked for.

Harris (1989) and Astrom (1970) are cited from general knowledge; their bibliographic records are to
be verified before the manuscript (L10).

| Ratified contribution | Under N1'' |
|---|---|
| O1 dead-time loop and stability limit | Unchanged (P1) |
| O2 noise-gain model | Kept as the sd model for uncorrelated residuals (within 1 to 19 % with a known score law, `h2_check.py`); its failure on persistent residuals is a reported result (Section 3A) |
| O3 design rule | Delay compensation plus replay tuning to eps / 2, capped at 0.8 gamma_crit (Sections 5.3 and 6) |
| O4 marginal-coverage blindness | Unchanged, now with the bound P2 |
| New O5 | Delay-limited width bound P3 and the analyzer-speed chart |
| I1, I2, E1, E2 | Unchanged |
| I3, the open-loop bias update | Replaced by the compensation arm of the 2x2 that R4.9 asked for |

## 5. Design

### 5.1 Debutanizer: real plant data, one stream

- **Point model** (D-P0.1): OLS of y_t on u5_{t-15}, fitted on the training split (rows 0-1674).
- **Calibration (tuning) segment**: the training residuals, in-sample. A two-parameter model on
  1660 rows has negligible optimism; this is stated as a limitation. The compensation forecaster is
  fitted on the same rows.
- **y_range for U** (Section 5.4): the range of y on the calibration segment, i.e. over the 1660
  training rows that have residuals.
- **Evaluation stream**: validation plus test rows (1675-2393, 719 rows). The window is
  initialised with the last 200 training scores. Primary analysis has no burn-in; a sensitivity
  analysis excludes the first 100 rows.
- **Disclosure**: the lag of 15 was chosen on the raw training and validation data. No
  calibration-loop statistic of those rows has been computed.
- **Delays**: theta in {0, 1, 3, 7, 12}. theta_doc = 3 is primary and 7 is secondary (Section 8).
- **Matched control**: the interval for y_t can be issued at update t - theta - 1 only if u5_{t-15}
  is known by then, which requires theta <= 14. Every theta in the grid meets this. One residual
  stream therefore serves every theta.

### 5.2 TEP: simulated, replicated (D-P1.3; D-P1.8 replaces D-P1.4)

- **Generator** (`scripts/generate_tep_modes.py`, extended 2026-10-13) adds four settings:
  - `--streams` replaces the simulator's generator with MRG32k3a and starts run j at stream j
    (Section 3D). Phase 1 uses it.
  - `--seeds` keeps the original generator and only replaces its constant G. It is kept for
    comparison, not for Phase 1.
  - `--hours` sets the run length, and `--record-s` the recording interval.
  - Without `--streams` or `--seeds` it reproduces the Phase-1C files byte for byte.
  - After each run it reports the shutdown time, if any (`shutdown_time`, Section 3D).
- **Runs**: 100 h each (the Phase-1C duration), recorded every 60 s, 5 per regime.
- **Stream rule** (`scripts/tep_seed_qualification.py`):
  - The candidates are streams 1, 2, 3, ..., dealt to mode1, mode2 and mode3 in rotation before
    any run, so no stream serves two regimes.
  - A candidate qualifies for its regime if its 100-h run there does not shut down (the freeze
    detector). Each regime takes its first five qualifiers.
  - Applied on 2026-10-17, reading trip status only (Section 3D). The record holds every
    candidate's status, the SHA-256 of each run's data file, the compiler version and the SHA-256
    of the sources. The rule selected:
    - mode1: streams 19, 31, 49, 55, 76
    - mode2: streams 5, 11, 14, 20, 23
    - mode3: streams 3, 6, 9, 18, 24
  - Before the freeze, Bien checks that his build reproduces the 15 chosen runs byte for byte
    (`tep_seed_qualification.py --verify`, which deletes each file after hashing). If any run
    differs, he re-runs the qualification, his record replaces this one, and the difference is
    logged in Section 10.
- **Limitation**: excluding tripped realizations makes the evidence conditional on the plant
  staying within its limits for 100 h. Survival selects calmer disturbance paths, most strongly in
  mode1, where 5 of 26 candidates survived. The same conditioning holds on a real plant, where soft
  sensors are not judged during a shutdown.
- **Segments within a run**: hours 0-30 train the point model; 30-70 are the calibration segment;
  70-100 are the evaluation segment.
- **Tuning**: step sizes are tuned on the pooled calibration segments of a regime's five runs
  (`replay_tune_pooled`), standing in for the longer history a plant tunes on. Each run is evaluated
  on its own segment.
- **y_range for U**: the range of y, XMEAS(40), over the pooled calibration segments of the
  regime's five runs.
- **Point models**: ridge regression on XMEAS 1-22 and XMV 1-12, with inputs lagged by the
  analyzer's label age (5 rows at 3 min, 15 rows at 1 min). Gradient boosting on the same inputs is
  the estimator-class check (R1.1, R1.4).
- **Arms**:
  - T1, data cadence: 3-min rows, decimated from 1 min; theta in {0, 2, 4}.
  - T2, execution cadence: 1-min rows; theta in {0, 4, 14}.
  - T3, event cadence: the calibrator updates only on a new analyzer value, so theta = 0. Metrics
    are computed on labelled rows only.

  In each arm theta <= label age - 1, so the issue-time inputs exist.

### 5.3 Factors common to both

- **Compensation** (D-P1.7): off, or the direct (theta + 1)-step residual predictor
  `fit_direct_forecaster`.
  - Its order is chosen by BIC (1 to 10) on the calibration segment.
  - It is fitted there, on the whole segment, by least squares on r_{t-theta-1}, ...,
    r_{t-theta-p}. Rows before the first full lag window keep their uncompensated score.
  - The interval is centred at y_hat + r_hat, and the loop sees |r - r_hat|.
  - The predicted width ratio is `predicted_width_ratio` of the calibration-segment
    autocorrelation.
- **gamma policies**:
  - fixed 0.005 (the default of Gibbs and Candes 2021);
  - fixed 0.05 (the repository default and the rejected manuscript's protocol);
  - delay-blind tuned;
  - delay-aware tuned at eps;
  - delay-aware tuned at eps / 2 (the safety factor of D-P1.9);
  - `design_gamma(theta)`.
- **Tuning rule** (as in the compensation pilot and the power analysis):
  - Search the grid 0.001, 0.0015, 0.002, 0.003, 0.005, 0.007, 0.01, 0.015, 0.02, 0.03, 0.05,
    0.07, 0.1 upward, capped at 0.8 gamma_crit(theta).
  - Select the largest value below the first value whose replayed uninformative share on the
    calibration segment exceeds the target.
  - If 0.001 already exceeds the target, the arm is reported as infeasible at this budget and
    evaluated at 0.001, flagged.
  - The first 200 rows of the calibration segment seed the conformal window and are not
    replayed. Every replayed step counts: the replay has no burn-in.
  - Delay-blind tuning replays at theta = 0.
- **Loops**: sequential is primary. The comparison loops are:
  - none: static split conformal, calibrated once on the calibration segment (the loop-off arm of
    the 2x2 that R4.9 asked for);
  - projected to [0.01, 0.5];
  - phase-interleaved tau-DACI;
  - the Smith variant;
  - decaying step sizes. These are implemented only after the schedule is verified in the body of
    Angelopoulos, Barber and Bates (2024); otherwise the loop is reported as not implemented.

  Every loop is tuned by the same replay.
- **Baselines at the label horizon** (D-P1.7). Each gets the same information as the compensated
  loop: the same point model, and only residuals whose labels have arrived by issue time.
  - SPCI multi-step (Xu and Xie 2023, Algorithm 3) at horizon theta + 1: a quantile random forest
    on the most recent available residuals, refitted as the paper does. It has no coverage
    feedback. Its residuals come from the same point model, in place of EnbPI's leave-one-out
    ensemble; this substitution isolates the interval method.
  - Conformal PID (Angelopoulos, Candes and Tibshirani 2023): quantile tracking, the integrator and
    a scorecaster that forecasts the score quantile at t + theta + 1. Each coverage error is fed back
    when its label arrives. Its learning-rate multiplier gets its own grid and cap, and is tuned by
    the same replay to the same target as the compensated loop. Its sets can be empty; an empty set
    counts as a miss and as width 0.
  - Configurations follow each paper. Where a paper is silent, they follow the authors' public
    code. They are written into Appendix A, and checked, before the freeze commit.
  - A baseline that cannot be run as specified is reported as not implemented, with the reason.
    Only F7 depends on the baselines. A baseline not implemented is dropped from claim 4 of
    Section 4, and the paper says so.
- **Pairing**: stored is primary. Arrival pairing at theta_doc is the negative control (R2.2,
  R4.8).

### 5.4 Metrics

- **Primary**: the uninformative share U. It is the share of issued intervals that are infinite or
  wider than y_range (Sections 5.1 and 5.2; `delayed_aci.uninformative`). The text also calls
  these intervals unusable.
- **Also reported**:
  - the infinite share;
  - marginal coverage with the Wilson 95 % interval of the observed coverage;
  - rolling coverage (window 100): its sd and minimum;
  - the number of steps spent in under-coverage episodes (rolling coverage below 0.80);
  - sd(alpha) and the alpha range;
  - interval width: median, p90 and p99, over finite intervals (`delayed_aci.diagnostics`), with
    the infinite share reported beside them. F7 uses its own convention: the median over all
    issued intervals, an infinite interval counting as infinitely wide.
- **Analyzer-speed chart**: at every theta of the grid, the width ratio of compensated to raw,
  measured as the ratio of the static 90 % quantiles of the two score streams on the evaluation
  rows, against the ratio predicted from the calibration autocorrelation (P3).

## 6. Endpoints, falsification and decision rules

**Primary cells**: the debutanizer at theta_doc = 3, and TEP arm T1 at theta = 4 (15 runs).
**F2 and F3 are tested on the N1' diagnosis**: compensation off, the sequential loop, stored
pairing, and the delay-blind step size, tuned at theta = 0 to eps. For F2 and F3, every other cell
and policy is descriptive and labelled so. Section 3E shows the debutanizer has little power for
F2, so in practice the TEP decides it; the rule stays as ratified.

| ID | Fires if | Consequence |
|---|---|---|
| F2, existence | Neither primary cell shows an increase in U over the theta = 0 control on the same stream of at least 1 percentage point with a Bonferroni 97.5 % CI that excludes 0 | The process claim fails. Per the ratified rule, the paper becomes synthetic-only and the venue is re-planned. If only one cell shows the increase, the claim is restricted to that dataset and the paper says so |
| F3, blindness | In a primary cell where F2's criterion is met, in the same arm, 0.90 lies outside the Wilson 95 % interval of the observed marginal coverage. For TEP the interval uses counts pooled over the 15 runs. The Wilson interval assumes independence, so under autocorrelation it is narrower than the true one, which makes this test strict | The blindness claim is dropped |
| F5a, budget of the N1' remedy (recalibrated by D-P1.9) | In TEP T1 at theta = 4, the uncompensated sequential loop, tuned by replay to eps / 2 on each regime's pooled calibration segments, has a mean U above 2 eps (2 %) over the 15 runs | N1' bullet 4 fails: replay tuning alone does not hold the budget, and the paper says so |
| F5b, budget of the N1'' remedy (new; D-P1.7, D-P1.9) | The same, with compensation on | The remedy claim narrows to whichever loop meets the budget, or to reporting only |
| F6, width bound (new, D-P1.7) | In TEP T1 at theta = 4, the mean over the 15 runs of measured / predicted width ratio - 1 lies outside +-10 %. Predictions come from each run's calibration autocorrelation; measurements are static 90 % quantiles on its evaluation rows. Design check (Section 3E): in simulation (Gaussian residuals, no label hold) a correct model stays inside +-10 % in 100 % of studies. The real margin is smaller: non-Gaussian shape alone can move the ratio by about 5 % (P3), and the pilot errors of Section 3C all lie on one side (-0.7 to -4.4 %) | The predictive claim P3 is dropped; the width gains are reported as measured only |
| F7, comparison (new, D-P1.7) | In TEP T1 at theta = 4, a baseline (SPCI multi-step or conformal PID at the label horizon) meets the validity conditions, and either the compensated loop does not, or the baseline is narrower. The compensated loop is the sequential loop, stored pairing, tuned with the F5 safety factor. Validity, the same for every method: mean U over the 15 runs at most 2 eps (the F5 budget), and mean marginal coverage within 2 percentage points of 0.90. Narrower: the mean over the runs of the run-median width is at least 5 % smaller, and the run-median width is smaller in at least 12 of the 15 runs (with equal widths, 12 of 15 occurs with probability 1.8 %). Medians are over all issued intervals, an infinite interval counting as infinitely wide | N1'' does not claim the best remedy. The compensated loop is presented as the analysable reference (whose width P3 predicts, unless F6 fired), and the better method is recommended by name. If F5b also fired, the remedy claim follows F5b |
| F1, as ratified (secondary) | The white model is off by more than 25 % in sd(alpha) or in the infinite share inside the design region | Reported. Section 3A predicts it fires on the infinite share at every persistence level. It is not decisive under D-P1.1 |
| F4 | The systematic sweep finds one of these already published: (i) the single-state dead-time analysis; (ii) a delay-limited (minimum-variance) bound on conformal interval width; (iii) an analysis of a residual or score forecaster ahead of a delayed online conformal loop, for its effect on miss persistence, step size or local coverage | (i) As ratified. (ii) P3 and the chart leave the claims. (iii) Claim 2 of Section 4 leaves the claims |

Why F5 changed (D-P1.9), fixed before any process data:
- **What changed.** As ratified, F5 tuned the uncompensated loop to eps and fired if its 15-run mean
  U exceeded eps, or if the one-sided 95 % t upper bound exceeded 2 eps. D-P1.9 tunes to eps / 2
  and fires if the mean exceeds 2 eps. The tested budget doubles, from 1 % to 2 % uninformative
  intervals, and the tuning target halves. F5a keeps the test for the N1' procedure; F5b adds it
  for the compensated loop.
- **Why.** In 200 simulated studies per persistence level, the loop tuned to eps meets eps on
  average, but its 15-run mean exceeds eps in 21 % (phi = 0.5) and 38 % (phi = 0.9) of studies.
  At phi = 0.9 none of the three targets tried brings that share below 5 % for the uncompensated loop
  (Section 3E).
- **The upper-bound criterion is dropped.** The five runs of a regime share one tuned step size,
  so the 15 run means are dependent, and a t bound over them has no known error rate. A bound made
  too narrow by that dependence would also be too lenient, not too strict. The simulation
  calibrates the error rate of the mean rule directly.
- **Design-stage false-firing rates** of the new rule (200 studies at phi = 0.5 and 0.9): F5a 0 %
  and 4.0 % (one-sided 95 % upper bound 7.1 %); F5b 0 % and 2.5 %.
- **1.5 eps was considered and rejected**: it would fire on the uncompensated loop in 8.5 % of
  studies at phi = 0.9.
- **If D-P1.9 is not ratified**, F5a and F5b use the F5 rule as ratified (tuning to eps; firing if
  the 15-run mean U exceeds eps or its one-sided 95 % t upper bound exceeds 2 eps), and F7's
  validity bound on U becomes eps.

The debutanizer cells are reported for F5a, F5b, F6 and F7 with their intervals and are
descriptive there. Its analyzer-speed chart is reported against the prediction recorded before
its evaluation rows are read (Section 3F).

## 7. Analysis plan

- **Debutanizer CIs**: circular block bootstrap of the per-step indicator sequences
  (`evaluation/inference.py`), with B = 2000.
  - The block length is the larger of 25 and the next integer above twice the IACT of the
    sequence (for differences, of the paired difference sequence). The IACT uses Sokal's
    automatic window with c = 5.
  - Differences between arms use the same blocks for both arms.
  - If fewer than 8 blocks fit in the 719-row stream, the interval is reported as unreliable and
    that cell counts only as descriptive.
- **TEP CIs**: the runs are independent replications: each draws from its own MRG32k3a stream
  (Section 5.2). Report means and t-based intervals over the 15 runs, with regime as a reported
  factor. Differences between arms are paired by run. Within a regime the five runs share their
  tuned step sizes, a dependence the t-intervals ignore; regime means are reported alongside. This
  makes F2's Bonferroni t interval, like the dropped F5 bound, somewhat lenient toward N1'. The
  power analysis checked how often F2 detects a real delay effect, not how often it fires without
  one.
- **F7** is decided by its Section 6 rule alone; no t interval enters it. The paired difference in
  run-median width is reported with a t interval, as a description.
- **Matched controls**: within a dataset, every arm shares the point model and the residual stream.
  Each comparison varies one factor.
- **Power**: Section 3E.

## 8. Pre-check results (training split only; commit 98ac681)

| Item | Result | Consequence |
|---|---|---|
| Debutanizer label hold | Repeat share 0.001 (label) against 0.006 (u5); mean run 1.00 | Not held, so Ts is not implied. theta_doc = 3 primary, 7 secondary |
| D-P0.1 model, in-sample | r^2 0.501; slope -0.967 on u5 at lag 15 | Matches the Phase 0 pool scan (r^2 0.524) |
| Residual persistence | Lag 1: 0.970; 2: 0.915; 3: 0.855; 5: 0.759; 10: 0.698; 15: 0.631; 20: 0.547; 30: 0.364; 50: 0.166; 100: 0.026. IACT 62.4 | About AR(1) with phi = 0.965 from lag 10 on. This is the pilot's worst regime (Section 3) |
| Open-loop miss process at theta = 0 / 3 / 7 | Rate 0.123 / 0.124 / 0.123; lag-1 0.77 to 0.79; IACT 13.1 to 13.7; mean miss run 5.0 to 5.4 | The disturbance driving the loop is persistent |
| TEP label hold (3 regimes) | Exactly 5-row runs (repeat share 0.801); reference XMEAS_7 not held | Confirms Downs and Vogel Table 5 in the data |

`tests/unit/test_phase1_precheck.py` (9 tests) checks the script on synthetic data with planted
structure.

## 9. Decisions

| ID | Decision | Status |
|---|---|---|
| D-P1.1 | N1' in place of the model-prediction claim | Ratified 2026-10-13 |
| D-P1.2 | theta convention, grids, theta_doc by pre-check | Ratified 2026-10-13; theta_doc = 3 |
| D-P1.3 | TEP inputs aligned at the analyzer's label age | Ratified 2026-10-13 |
| D-P1.4 | 5 seeds x 300 h x 3 regimes | Ratified 2026-10-13; infeasible (Section 3D); replaced by D-P1.8 if ratified |
| D-P1.5 | eps = 1 %; U; primary cells and single primary policy | Ratified 2026-10-13 |
| D-P1.6 | Debutanizer tuning on training residuals, evaluation on validation plus test | Ratified 2026-10-13 |
| D-P1.7 | Elevate to N1'' (Section 4): delay compensation, the width bound P3 and the analyzer-speed chart, SPCI multi-step and conformal PID as baselines, and the rules that test them: F5b, F6 (tolerance +-10 %) and F7. If D-P1.7 is not ratified, F5b, F6 and F7 lapse | **Proposed** |
| D-P1.8 | TEP: 100-h runs, each from its own MRG32k3a stream in place of the simulator's generator; streams dealt to the regimes in rotation and qualified by the freeze detector (Section 5.2); segments 0-30 / 30-70 / 70-100 h; pooled tuning per regime | **Proposed** |
| D-P1.9 | F5a and F5b tune to eps / 2 and fire above 2 eps, which doubles the tested budget, without the upper-bound criterion. Fixed by the power analysis (200 studies per persistence level) before any process data. If not ratified, the ratified F5 rule applies to both (Section 6) | **Proposed** |

Sequence:
1. Ratify D-P1.7 to D-P1.9.
2. Bien checks that his build reproduces the 15 chosen TEP runs byte for byte (Section 5.2).
3. Write and check the baseline configurations (Appendix A).
4. Make the freeze commit.
5. Bien generates the 15 TEP runs (commands in the hand-off).
6. Implement the Phase 1 runner, with tests: point models, the arms and baselines of Section 5,
   and evidence JSON for every cell.
7. Bien runs it; the F-verdicts are recorded.
8. The paper's shape is decided.

## 10. Freeze record and deviations

Freeze commit: pending. Deviations after the freeze: none yet. Each deviation will be dated and
justified, and its effect on the F-verdicts stated.

## Appendix A. Baseline configurations (to be completed before the freeze)

For SPCI multi-step and conformal PID: the settings each paper states, the settings taken from the
authors' public code where a paper is silent, the source of each, and the check that the
implementation reproduces one result of each paper. It also fixes SPCI's residual window w (the
paper gives none) and conformal PID's learning-rate grid, its cap and its integrator constants.
Empty until step 3 of the sequence in Section 9.
