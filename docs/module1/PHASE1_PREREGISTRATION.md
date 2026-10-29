# N1 Phase 1 pre-registration

Status, 2026-10-29: **D-P1.1 to D-P1.15 ratified; frozen (Section 10).**
- Bien ratified D-P1.1 to D-P1.6 on 2026-10-13 ("I'm inline with your recommendation").
- The training-split pre-check has run. Its evidence is in commit 98ac681
  (`docs/paper/evidence/phase1_precheck.json`); results are in Section 8.
- Bien ratified D-P1.7 to D-P1.9 on 2026-10-20 ("ratified D-P1.7-9"), as written in the
  2026-10-17 draft, after the bundle's checks passed on his machine (manifest, 56 tests, ruff and
  black):
  - D-P1.7: elevate the claim to delay-compensated calibration, with SPCI and conformal PID as
    required baselines and the rules F5b, F6 and F7 that test it (Sections 4, 5.3 and 6).
  - D-P1.8: amend the TEP design after two findings: the excitation trips many runs, and the
    simulator's random-number generator repeats within 0.55 to 141 h, within 100 h for 41 of the
    58 seeds in the source (Sections 3D and 5.2).
  - D-P1.9: recalibrate F5 from the power analysis (Section 6).
- Bien ratified D-P1.10 to D-P1.12 on 2026-10-27 ("ratified, PM and especially I am inline with
  your recommendation"), as written in commit bf78757:
  - D-P1.10: the baseline configurations of Appendix A;
  - D-P1.11: F7's "narrower" condition at matched coverage;
  - D-P1.12: claim 2', after F4 (iii) fired.
- Bien ratified D-P1.13 and D-P1.14 on 2026-10-28 ("ratified D-P1.13-14"), as written in commit
  9277784, after the third pass of the fifth check (A.9):
  - D-P1.13: the rule F8, which can reject claim 2' (Sections 6 and 9);
  - D-P1.14: a check of F7's coverage scaling, reported beside it, and an edge case of D-P1.11.
- Bien ratified D-P1.15 on 2026-10-29, choosing "Clause by clause (Recommended)" over "Strict:
  claim 2' leaves whole" in the decision dialog: prior art found after the freeze by the screens
  still due removes from claim 2' only the part it covers (Sections 6 and 9). Section 9 records
  the text he selected word for word.

The protocol is frozen at the commit that adds the freeze record of Section 10. The steps before
it:
- 2026-10-22: Bien's build reproduced the 15 chosen TEP runs byte for byte (Section 5.2).
- 2026-10-22: the Scopus and Web of Science sweep decided F4 (`LITERATURE_SWEEP_N1.md`, rows 21
  to 32; rows 33 to 38 add the 2026-10-27 exports and a first Google Scholar pass, and rows 39
  to 44 the citing sets and full texts of 2026-10-28).
  - (i) and (ii) do not fire.
  - (iii) fires on its local-coverage clause. Wang and Hyndman (arXiv 2410.13115, 2024) compare
    a delayed online conformal loop with and without a residual forecast on local coverage (one
    dataset, one figure). As ratified, claim 2 left the claims; D-P1.12 keeps the narrower
    claim 2' (Section 9).
  - The sweep also re-attributes P2's bound (Section 4) and narrows Section 3D's report on the
    TEP generator (Kitchin 2026).
- 2026-10-27: Bien ratified D-P1.10 to D-P1.12.
- 2026-10-27 and 28: the third pass of the fifth check ran (A.9). Nothing critical; two major
  findings led to D-P1.13 and D-P1.14.
- 2026-10-28: the citing sets of W9 and W10 (116 records, five new) were screened, and the seven
  texts still due were read, for R073 the thesis in place of the chapter
  (`LITERATURE_SWEEP_N1.md`, rows 39 to 44). No F4 verdict changed; the positioning gained four
  constraints (P13 to P16 there). Bien ratified D-P1.13 and D-P1.14, and a focused check
  covered the day's changes (A.10).
- 2026-10-29: Bien ratified D-P1.15, which the focused check's one major finding led to
  (A.10).

At the freeze no Phase 1 number exists from the debutanizer validation or test rows or from
new TEP runs.

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
- 2026-10-20, fifth check, of the first version of Appendix A. It confirmed the code readings,
  the authors' two code defects and the reproduction numbers. It found that rules of that
  version, not the method, would have decided F7 against conformal PID. Taking the largest
  feasible multiplier made it 8 to 21 % wider than the compensated loop in six synthetic T1
  designs, against F7's 5 % margin. A Theta scorecaster, which forecasts the score rather than the
  quantile Section 5.3 asks for, cost another 5 to 8 %. It also found a C_sat reading that
  contradicts its stated purpose, an SPCI window set for 2755 training residuals where TEP T1 has
  800, and smaller gaps. Appendix A was rewritten (A.7).
- 2026-10-20, second pass of the fifth check, of the rewrite. It confirmed that the rewrite
  resolves the 13 findings, that the code matches A.2 and A.3, and every number of A.4 and A.5.
  It found four major problems. Conformal PID's replay started cold while the compensated loop's
  starts from a seeded window, which biased the selection. F7's coverage band can decide the
  comparison. A.6 left out the paper's section on the effect of scorecasting. D-P1.10 understated
  what it changes. Appendix A was revised (A.8), and D-P1.11 was proposed (ratified 2026-10-27).
  A third, focused pass on these revisions stopped twice on the account's usage limit on
  2026-10-21, and ran on 2026-10-27 (next item).
- 2026-10-27, third pass of the fifth check, cold, by an agent that had not seen the work. Its
  scope: the second pass's resolutions, the database sweep and its consequences, and the edits of
  2026-10-27. Everything mechanical reproduced, and the F4 verdicts held. It found that claim 2'
  had no rule that could reject it, and that A.1 misstated which way the Gaussian coverage
  scaling errs; also version labels of Wang and Hyndman, stale status text and smaller slips.
  D-P1.13 and D-P1.14 were proposed and the text corrected (A.9).
- 2026-10-28, a re-check and a micro-check by the same agent, of those corrections, of D-P1.13
  and D-P1.14 and of F8's design check. The re-check found that F8's design check left out T1's
  label hold; F8 was moved to the IACT (A.9).
- 2026-10-28, a focused check before the freeze, by the same agent: the third sweep batch, rows
  39 to 44 of the sweep, the ratification and the freeze record. Nothing critical; its one major
  finding led to D-P1.15 (A.10).

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
  new);
- whether compensation makes the miss process that drives the loop less persistent, where P3
  predicts a gain (F8, D-P1.13, ratified 2026-10-28).

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
  (`LITERATURE_SWEEP_N1.md`). [2026-10-22: Scopus (S8, 10 records) and Web of Science (W8, 11)
  hold no report.
  - The one prior account is Kitchin's Rust port of the simulator (tep-rust, GitHub; its log of
    August 2026; `LITERATURE_SWEEP_N1.md`, row 32). It records that the product exceeds 2^53 on
    77 % of draws, so that rounding is part of the generator, and that even seeds have shorter
    periods.
  - Its cycle search found no return to the starting state within 2e9 states. Such a search
    cannot see the cycles above: a state that has gained trailing zero bits never returns to its
    start.
  - The precision loss is therefore Kitchin's, and is cited. The eventual cycles of 0.55 to
    141 h, and their sharing across seeds, remain unreported.]

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

Ratified 2026-10-20 (D-P1.9): the stated budget is 2 eps for the mean over the TEP runs, held by
tuning to eps / 2 (F5a, Section 6). Section 3E gives the reason: the run mean of rare, clustered
events spreads too widely for a test at eps.

**Ratified N1'' (D-P1.7, 2026-10-20), verbatim: delay-compensated conformal calibration with a
predictable width.** It keeps N1' as the diagnosis and adds three things.
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
    [2026-10-22: the extension is not new. Wang and Hyndman (arXiv 2410.13115: Prop. 4 of v1,
    October 2024, which is Cor. 1 of v2, February 2026; label corrected 2026-10-28) bound the
    coverage gap of the same single-state delayed recursion, in quantile space, by
    (b + eta h) / (eta (T - h)). P2 is its analogue in level space, for positive
    scores. What N1 adds is the consequence under delay, read together with the infinite share
    (`LITERATURE_SWEEP_N1.md`, row 21). 2026-10-28: further bounds that grow with the delay or
    with the batch size of a batched update are cited beside it (there, P11 and P15).]
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
    the quantile of the score at t + 4, matching the 4-week horizon (Sec. 1.2, App. E [App. F in
    the NeurIPS version; corrected 2026-10-20]).
  - The paper does not discuss delayed feedback or dead time. It does not say whether the
    quantile-tracking update waits for the delayed outcome. [2026-10-20: the authors' code does
    wait, and the COVID experiment ran that way, at a dead time of 3; Appendix A.6.]
  - Its learning rate is a fixed fraction of the trailing maximum score. The paper notes that
    "extremely high learning rates result in volatile sets" (Sec. 2.1).
- **SPCI** (Xu and Xie, ICML 2023; it builds on EnbPI, by the same authors).
  - It predicts conditional quantiles of the future residual from the past w residuals with a
    quantile random forest.
  - Its multi-step version (Sec. 5.2, App. B.3, Algorithm 3 [printed in App. C; corrected
    2026-10-20]) fits one forest per horizon, with labels revealed only every S steps.
  - It refits its forest as residuals arrive, but has no feedback loop on coverage, so it has no
    step size and no dead-time loop.
  - Its own coverage guarantee is asymptotic, under stated assumptions (Thm 2). A split variant
    (Algorithm 2, Prop. 1) has a finite-sample guarantee under exchangeability. It gives no width
    bound.
- **El Halabi and Brandt (2026)** analyse delayed-feedback ACI without compensation.
- **Wang and Hyndman (arXiv 2410.13115, 2024)** [added 2026-10-22; `LITERATURE_SWEEP_N1.md`,
  row 21].
  - Multi-step conformal PID, whose P control "shows an h-period delay in updating the quantile
    estimate".
  - AcMCP adds to it a forecast of the h-step error. On the electricity data it is compared with
    the same loop without that forecast on coverage over rolling windows (Fig. 8), at one fixed
    step size.
  - Its Cor. 1 (Prop. 4 in v1) is the analogue of P2.
- **Dixit et al. (2023), Szabadvary (2024) and Zaffran et al. (2022)** [added 2026-10-22; rows 22
  to 24]: delayed-feedback ACI run without analysis; a heuristic of larger step sizes at longer
  horizons, against which P1's limit falls with the delay; and the step-size trade-off on AR(1)
  residuals without delay.
- **Meng et al. (2026), Qiu et al. (2026) and Areces et al. (2025)** [added 2026-10-28; rows 39,
  40 and 44]:
  - a conformal PID-type soft sensor on the sulfur recovery unit, each label used at once, with
    a delay-free bound on the length of a miss run;
  - delayed-feedback adaptive conformal prediction (a fixed delay of 6) whose step size a
    label-free uncertainty signal raises, judged on marginal coverage and width;
  - a quantile model linear in past scores, whose gain grows with their lag-1 autocorrelation,
    without delay, and a coverage bound that grows with the batch size of a batched update.

N1'' does not claim forecasting the residual or the score at the label horizon. It claims four
things:
1. the dead-time analysis of the single-state loop on persistent residuals (P1, P2, Sections 3A
   and 3B);
2. compensation analysed and tested as dead-time compensation of that loop: its effect on the
   persistence of the miss process, on the step size that holds the budget, and on local coverage.
   Conformal PID reports more stable coverage and tighter sets from a scorecaster ahead of quantile
   tracking (Sec. 2.3), without delays [2026-10-20: wrong for its COVID experiment, which ran with a
   dead time of 3, and where Sec. 3.3 and Figs. 2, 9 and 10 credit the scorecaster with better
   local coverage, without isolating it; screened under F4 (iii), which does not fire; claim 2 is
   the isolated, delay-aware analysis; Appendix A.6]; claim 2 is limited to the delayed loop and
   its step size [2026-10-22: F4 (iii) fired on its local-coverage clause
   (`LITERATURE_SWEEP_N1.md`, row 21), so claim 2 leaves the claims as ratified. D-P1.12,
   ratified 2026-10-27, keeps claim 2': compensation's effect on the persistence of the miss
   process and on the step size that holds the budget, with the label delay varied at a fixed
   predictor. Local coverage is then reported, not claimed (Section 9). 2026-10-28: "a fixed
   predictor" means a fixed point model; the compensation forecaster is refitted for each theta
   (Section 5.3). D-P1.13, ratified 2026-10-28, adds the rule F8 that tests claim 2' (Section
   6). D-P1.15, ratified 2026-10-29, decides what prior art found after the freeze removes from
   claim 2' (Section 9)];
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
    logged in Section 10. [Done 2026-10-22: 15 of 15 runs byte-identical on Bien's machine,
    under WSL; `docs/paper/evidence/tep_seed_verify_owner_2026-10-22.txt`. The 2026-10-17 record
    stands.]
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
| F7, comparison (new, D-P1.7) | In TEP T1 at theta = 4, a baseline (SPCI multi-step or conformal PID at the label horizon) meets the validity conditions, and either the compensated loop does not, or the baseline is narrower. The compensated loop is the sequential loop, stored pairing, tuned with the F5 safety factor. Validity, the same for every method: mean U over the 15 runs at most 2 eps (the F5 budget), and mean marginal coverage within 2 percentage points of 0.90. Narrower: the mean over the runs of the run-median width is at least 5 % smaller, and the run-median width is smaller in at least 12 of the 15 runs (with equal widths, 12 of 15 occurs with probability 1.8 %). Medians are over all issued intervals, an infinite interval counting as infinitely wide [2026-10-20: applied to four baselines, D-P1.10; D-P1.11 compares coverage-matched widths; both ratified 2026-10-27; Appendix A.1] | N1'' does not claim the best remedy. The compensated loop is presented as the analysable reference (whose width P3 predicts, unless F6 fired), and the better method is recommended by name. If F5b also fired, the remedy claim follows F5b |
| F8, persistence (new, D-P1.13, ratified 2026-10-28) | In TEP T1 at theta = 4, where P3 predicts a gain: the mean over the 15 runs of the predicted width ratio, computed from each run's calibration autocorrelation before its evaluation rows are read, is at most 0.95. F8 fires if the paired difference over the 15 runs, compensated minus uncompensated, of the integrated autocorrelation time (IACT) of the open-loop miss indicator on the evaluation rows has a two-sided 95 % t interval that does not lie wholly below 0. The open-loop miss indicator is that of the delayed loop at gamma = 0 (the disturbance that drives the loop, Section 8), its window seeded with the last 200 calibration scores. The IACT uses Sokal's automatic window with c = 5 (`inference.iact`, as in Sections 7 and 8); a constant miss indicator gives 1. Design check (Gaussian AR(1) residuals, `scripts/pilots/f8_persistence_power.py`). Without a label hold (200 studies at phi = 0.5 and 0.9, 100 at 0.7, 0.8, 0.85 and 0.95): the mean predicted ratio is 0.999, 0.986, 0.947, 0.901, 0.819 and 0.658, so F8 is tested at phi >= 0.85 in every study and at phi = 0.8 in 70 %. Where tested it fires in 1.4 % of studies at phi = 0.8 and in none at 0.85 to 0.95, on this grid. The mean difference in IACT is -0.99 on 3.42 at phi = 0.8 and -3.45 on 6.17 at 0.9. Where not tested the effect is negligible (0.00 at phi = 0.5, -0.24 at 0.7), and F8 would fire in 98.5 % and 55 % of studies; at phi = 0.5, where compensation has nothing to remove, the interval lies wholly below 0 in 1.5 % of studies (`f8_estimand_check.json`). With T1's label hold (phi = 0.9, 0.95 and 0.97; `f8_estimand_check.json`, 200 studies per cell): T1 holds each XMEAS(40) reading, with its noise (sd 0.5, `teprob.f` XNS(40)), for 5 rows, and compensation at h = 5 cannot predict the current block's noise. With a fifth of the residual variance held, F8 is tested in every study and fires in at most 0.5 %. With half held, the gate admits 18 % of studies at phi = 0.9 and all at 0.95 and 0.97, and F8 fires in 53, 19 and 17 % of those it admits although compensation works (mean difference in IACT -0.75 to -2.28). The held share is not known before the data; the Phase-1C intervals (`coverage_tep.json`, another model) suggest roughly 25 to 100 % | Claim 2' leaves the claims: compensation's effect on persistence and step size is reported as measured. If P3 predicts no gain (mean ratio above 0.95), claim 2' is not tested on TEP, is reported as measured, and the paper says why. The larger step size is stated only if F8 is tested and does not fire, and the compensated loop's step size, tuned as for F5, is larger in at least two of the three regimes and smaller in none. Design check, share of studies in which the statement is made: 98.5 % at phi = 0.9, 87 % at 0.85, 47 % at 0.8 and none at 0.5; with a fifth of the variance held, 88 to 99 %; with half held, 3 % at phi = 0.9 and 51 to 64 % at 0.95 and 0.97 (`f8_persistence_power_held20.json` and `_held50.json`, 100 studies per cell). The lag-1 autocorrelation and the mean miss run of the miss indicator are reported beside F8. A fired F8 bears on claim 2' alone; no other rule depends on it |
| F1, as ratified (secondary) | The white model is off by more than 25 % in sd(alpha) or in the infinite share inside the design region | Reported. Section 3A predicts it fires on the infinite share at every persistence level. It is not decisive under D-P1.1 |
| F4 | The systematic sweep finds one of these already published: (i) the single-state dead-time analysis; (ii) a delay-limited (minimum-variance) bound on conformal interval width; (iii) an analysis of a residual or score forecaster ahead of a delayed online conformal loop, for its effect on miss persistence, step size or local coverage | (i) As ratified. (ii) P3 and the chart leave the claims. (iii) Claim 2 of Section 4 leaves the claims [2026-10-22, the database sweep (`LITERATURE_SWEEP_N1.md`, rows 21 to 32): (i) and (ii) do not fire; (iii) fires on its local-coverage clause (row 21); D-P1.12, ratified 2026-10-27. 2026-10-28: rows 39 to 44, the citing sets of W9 and W10 and the seven texts still due, change no verdict. From the freeze to submission, D-P1.15 applies (iii) to claim 2' clause by clause] |

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
  validity bound on U becomes eps. D-P1.9 was ratified on 2026-10-20, so this fallback lapsed.

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
  run-median width is reported with a t interval, as a description. [2026-10-28: under D-P1.11
  that is done for the coverage-matched widths F7 tests and for the unscaled widths; D-P1.14
  adds the widths matched by the loop's own score quantiles.]
- **F8** (D-P1.13, ratified 2026-10-28) is decided by its paired two-sided 95 % t interval over the
  15 runs.
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
| D-P1.4 | 5 seeds x 300 h x 3 regimes | Ratified 2026-10-13; infeasible (Section 3D); replaced by D-P1.8 on 2026-10-20 |
| D-P1.5 | eps = 1 %; U; primary cells and single primary policy | Ratified 2026-10-13 |
| D-P1.6 | Debutanizer tuning on training residuals, evaluation on validation plus test | Ratified 2026-10-13 |
| D-P1.7 | Elevate to N1'' (Section 4): delay compensation, the width bound P3 and the analyzer-speed chart, SPCI multi-step and conformal PID as baselines, and the rules that test them: F5b, F6 (tolerance +-10 %) and F7. If D-P1.7 is not ratified, F5b, F6 and F7 lapse | Ratified 2026-10-20 |
| D-P1.8 | TEP: 100-h runs, each from its own MRG32k3a stream in place of the simulator's generator; streams dealt to the regimes in rotation and qualified by the freeze detector (Section 5.2); segments 0-30 / 30-70 / 70-100 h; pooled tuning per regime | Ratified 2026-10-20 |
| D-P1.9 | F5a and F5b tune to eps / 2 and fire above 2 eps, which doubles the tested budget, without the upper-bound criterion. Fixed by the power analysis (200 studies per persistence level) before any process data. If not ratified, the ratified F5 rule applies to both (Section 6) | Ratified 2026-10-20 |
| D-P1.10 | The baseline configurations of Appendix A. Their text leaves Sections 5.3 and 6 as ratified, but changes how both are applied. (i) F7's "a baseline" becomes four baselines: SPCI, and conformal PID with a quantile-regression, a Theta and a matched scorecaster. Under equal widths that raises F7's chance of firing on the run count from 1.8 % to at most 7.2 %. If several meet F7, all are named and the narrowest is recommended. (ii) Only the quantile-regression scorecaster forecasts the score quantile that Section 5.3 names. Theta (the authors' code) and matched (the compensated loop's predictor) are added, which can only make F7 easier to fire. (iii) Section 5.3 tunes conformal PID's multiplier; D-P1.10 tunes m, C_sat and K_I jointly by the same replay to the same U target, and selects by a replay analogue of F7's coverage and width conditions. (iv) Conformal PID starts from the compensated loop's seed rows, with a warm tracker and an integrator aged by the seed, as "the same information" requires. (v) SPCI's window keeps the authors' ratio to the training length (87 and 181). (vi) One information exception at the calibration boundary is common to all methods. (vii) Reporting: the coverage gap and the coverage-matched width change are reported beside F7 (A.1). (viii) [2026-10-22] The matched scorecaster has the structure of AcMCP (Wang and Hyndman 2024), which is not run separately (A.2). [2026-10-28: with D-P1.11 ratified the coverage-matched change is F7's test, so (vii) reports the unscaled change beside it (A.1, A.9)] | Ratified 2026-10-27 |
| D-P1.11 | F7's "narrower" condition compares coverage-matched widths. In each run, the baseline's run-median width is scaled to the compensated loop's coverage in that run by z((1 + c_loop) / 2) / z((1 + c_baseline) / 2). The mean of the scaled widths must be at least 5 % smaller than the loop's mean run-median width, and the scaled width smaller in at least 12 of 15 runs. Validity is unchanged. Conformal PID is then selected by its replayed median width scaled to 0.90 coverage. Why: F7's coverage band is worth 5.5 % of width at a 2-point gap, and 11 % at 4 points (A.1), so F7 as ratified can recommend a method for covering less. Fixed before any process data, from the dry run (A.5) and the second pass of the fifth check (A.8). If not ratified, F7 stays as ratified, conformal PID is selected by unscaled width, and the coverage-matched change is reported beside the verdict (A.1) | Ratified 2026-10-27 |
| D-P1.12 | Claim 2 after F4 (iii). The database sweep fired F4 (iii) on its local-coverage clause. Wang and Hyndman (arXiv 2410.13115, v1 2024-10-17) compare a delayed P + I loop with and without a residual forecast (AcMCP against MPI) on coverage over rolling windows, for one dataset in one figure, and find a "similar coverage pattern". They fix the step size and count no miss runs (`LITERATURE_SWEEP_N1.md`, row 21). As ratified, claim 2 leaves the claims. D-P1.12 keeps claim 2': compensation's effect on the persistence of the miss process and on the step size that holds the uninformative budget, with the label delay varied at a fixed predictor. Persistence is measured as in Section 8 (the lag-1 autocorrelation of the miss indicator, the mean miss run and the IACT), reported beside Section 5.4's metrics. Local coverage is reported as a result, with that paper cited, and is not claimed. Why: the rule fires on any one of three components, but the prior work covers only one of them, and only in one figure. The two it lacks are the analysis N1'' was built for. Proposed before any Phase 1 data. If not ratified, claim 2 leaves the claims as ratified, and compensation stays as the remedy that F5b, F6 and F7 test. [2026-10-28 (A.9): the quoted words are those of v2 (2026-02-02); v1's Sec. 5.3, on the same Fig. 8, reads "MPI and AcMCP coverage display similar pattern". "A fixed predictor" means a fixed point model; the compensation forecaster is refitted for each theta (Section 5.3). As written, claim 2' had no rule that could reject it; D-P1.13 (ratified 2026-10-28) adds one. The paper states that F4 (iii) fired and that claim 2 was narrowed before any data] | Ratified 2026-10-27 |
| D-P1.13 | A rule for claim 2': F8 (Section 6). The third pass of the fifth check found that claim 2' (D-P1.12) could not fail. No rule fires if compensation leaves the miss process as persistent, or the tuned step size unchanged, though the ratified N1'' text states both directions (A.9, finding 2). F8 tests persistence on the TEP runs, where P3 predicts a gain: the IACT of the open-loop miss indicator, compensated against uncompensated, paired over the 15 T1 runs at theta = 4. The IACT is the long-run persistence that sets the variance of the loop's level, and with it the step size that holds the budget. Where P3 predicts no gain the effect is negligible, and a test would only measure that; claim 2' is then reported as measured, and the paper says why. The step size is tuned per regime, so each arm has only three values; a larger step size is stated only beside an F8 that holds, and only if it is larger in at least two regimes and smaller in none. The lag-1 autocorrelation and the mean miss run are reported beside F8, as D-P1.12 states. The debutanizer and the other delays are descriptive. The threshold, 0.95 on the mean predicted width ratio, comes from the design check: without a label hold, where it admits a study, F8 fires in at most 1.4 % of studies on the simulated grid (phi = 0.8), and in none from phi = 0.85 on. The measure was chosen among three (`scripts/pilots/f8_estimand_check.py`, 200 studies per cell): the lag-1 and lag-5 autocorrelation and the IACT of the miss indicator. All three confirm a reduction falsely in at most 1.5 % of studies when compensation has nothing to remove (phi = 0.5). The IACT fires least, where compensation works, in three of the five admitted cells where they differ: at phi = 0.8 without the hold (0.7 % against 7.4 % for lag 1 and 2.2 % for lag 5) and at phi = 0.95 and 0.97 with half the variance held (19 and 17 % against 27 and 22 % for lag 1). It fires more in two: at phi = 0.9 with a fifth held (0.5 % against 0 % for both lags) and at phi = 0.9 with half held (53 % against 36 % for lag 1, the same as lag 5), where the gate admits 36 of 200 studies. T1's label hold weakens F8 whatever the measure: compensation cannot remove analyzer noise held over the label's 5 rows, so with half the residual variance held F8 fires in 17 to 53 % of the studies it admits, although compensation works; with a fifth held, in at most 0.5 % (A.9, re-check finding 1). That risk falls on claim 2' alone. Proposed before any Phase 1 data. If not ratified, claim 2' stays as D-P1.12 wrote it, and the paper presents it as descriptive: a direction is stated only where the paired 95 % t interval over the 15 runs excludes zero | Ratified 2026-10-28 |
| D-P1.14 | Two additions to D-P1.11. (i) Beside F7's coverage-matched comparison, the evidence reports the same comparison with each run's factor taken from the loop's own scores: q(c_loop) / q(c_baseline), with q(c) the empirical c-quantile (linear interpolation) of the absolute compensated calibration scores of the regime's five runs, pooled (the debutanizer: its calibration segment). For half-normal scores this equals the Gaussian factor; it stands in for the unknown shape of each baseline's own scores. It decides nothing: if it and the Gaussian factor disagree on F7, the paper reports both. Why: the Gaussian factor under-corrects under heavier tails, which favours whichever method covers less. In the dry run, t3 tails would move the closest competitor from -2.8 % to -4.5 % at the loop's coverage, against F7's 5 % margin (A.1, A.9). (ii) A run coverage of exactly 0 or 1 is clipped to [1 / (2n), 1 - 1 / (2n)] before scaling, with n the run's number of labelled evaluation intervals; otherwise the factor is infinite or zero. Proposed before any Phase 1 data. If not ratified, F7 is reported as D-P1.11 states, and a run coverage of 0 or 1, if it occurs, is reported as leaving that run's scaled width undefined | Ratified 2026-10-28 |
| D-P1.15 | Later prior art and claim 2'. F4 stays in force until submission. Prior art found after the freeze by the screens still due (Section 9, step 2) is decided by F4 as written for (i) and (ii). F4 (iii)'s consequence for claim 2 is spent, so for claim 2' it applies clause by clause: a published analysis or comparison of a residual or score forecaster ahead of a delayed online conformal loop, for its effect on miss persistence, removes the persistence part of claim 2'. F8 is still decided and still gates the step-size statement, but its result is reported, not claimed; one for its effect on the step size that holds a coverage or interval budget removes the step-size statement. Either way the paper cites the work. Row 21's [of `LITERATURE_SWEEP_N1.md`] strict reading applies: one comparison with and without the forecaster, on the clause's measure, is enough, without theory. Why: D-P1.12 kept claim 2' because prior work covered only one of claim 2's three parts. A later find on another part is decided the same way, fixed before any Phase 1 data. [2026-10-29: the text Bien selected in the decision dialog, word for word, with its list markers removed and the bracket after "Row 21's" added. It closes A.10's finding 1. The alternative offered, "Strict: claim 2' leaves whole", would have removed claim 2' whole on any later find under (iii)] | Ratified 2026-10-29 |

Sequence:
1. Ratify D-P1.7 to D-P1.9. Done 2026-10-20.
2. Bien checks that his build reproduces the 15 chosen TEP runs byte for byte (Section 5.2). Done
   2026-10-22: 15 of 15.
   - The database sweep decides F4. Done 2026-10-22: (iii) fired, and D-P1.12 was proposed
     (`LITERATURE_SWEEP_N1.md`). On 2026-10-27, S4 added no new record, W10's file proved to
     be SPCI's own record, with no linked citation, and a first Google Scholar pass (rows 33 to
     38) changed no verdict. On 2026-10-28 the citing sets of W9 and W10 and the seven texts
     still due (rows 39 to 44) changed none either. Due before submission: Li and Zhu's App. G.1
     (row 37 (f)), a new screen of Wang and Hyndman's revision (row 21), the chapter of row 43
     if it becomes available, and the full Google Scholar pass. They can only add prior art,
     which would be logged in Section 10 and decided by F4 as D-P1.15 applies it.
3. Write and check the baseline configurations (Appendix A). Written, checked (fifth check) and
   rewritten twice on 2026-10-20, after the check and after its second pass. Bien ratified
   D-P1.10, D-P1.11 and D-P1.12 on 2026-10-27. The third, focused pass ran on 2026-10-27 (A.9).
   Bien ratified D-P1.13 and D-P1.14 on 2026-10-28, and a focused check covered the changes of
   that day (A.10). Its one major finding led to D-P1.15, ratified 2026-10-29.
4. Make the freeze commit: the commit that adds Section 10's freeze record, tagged
   `n1-phase1-freeze`.
5. Bien generates the 15 TEP runs (commands in the hand-off).
6. Implement the Phase 1 runner, with tests: point models, the arms and baselines of Section 5,
   and evidence JSON for every cell.
7. Bien runs it; the F-verdicts are recorded.
8. The paper's shape is decided.

## 10. Freeze record and deviations

**Freeze, 2026-10-29.** The protocol is frozen at the commit that adds this record, tagged
`n1-phase1-freeze` (an annotated tag; `git rev-list -n 1 n1-phase1-freeze` prints its hash). As
they stand in that commit, the freeze fixes:
- the purpose and the delay provenance (Sections 1 and 2), the pre-data findings (Section 3),
  the claims and propositions (Section 4), the design and metrics (Section 5), the rules F1 to
  F8 (Section 6), the analysis plan (Section 7) and the decisions D-P1.1 to D-P1.15 (Section 9);
- the baseline configurations (Appendix A);
- the code these rest on: `src/ipis/module1_soft_sensor/evaluation/`, the TEP generator
  (`scripts/generate_tep_modes.py --streams`) and the scripts and evidence files cited above.

At the freeze no Phase 1 number exists from the debutanizer validation or test rows or from new
TEP runs. Before it, the 15 TEP runs were generated only to read their trip status and hashes
(Section 5.2); they are generated for analysis after it (Section 9, step 5).

A deviation is a change to anything fixed above, including the behaviour of the fixed code.
Code added after the freeze to run Phase 1 (Section 9, step 6) is not one if it implements
Sections 5 to 7 and Appendix A as written, leaves the fixed code's behaviour unchanged, and the
existing tests still pass. Every "If not ratified" fallback of Section 9 lapsed with its
decision's ratification, so none applies.

Deviations after the freeze: none yet. Each deviation will be dated and justified, and its
effect on the F-verdicts stated. Prior art found after the freeze is logged here too. If the
screens still due find it (Section 9, step 2), its bearing on F4 is decided as D-P1.15 applies
it.

## Appendix A. Baseline configurations (D-P1.10; fixed 2026-10-20, before the freeze)

This appendix fixes the settings of the baselines of Section 5.3 and gives the source of each.
The code is in `src/ipis/module1_soft_sensor/evaluation/`: `baselines_pid.py` for conformal PID
and `baselines_spci.py` for SPCI, both imported through `baselines.py`. The sources are the papers
and, where a paper is silent, the authors' code:
- conformal PID: the paper as published at NeurIPS 2023; aangelopoulos/conformal-time-series,
  commit b729c3f;
- SPCI: arXiv 2212.03463v3, the ICML 2023 version; hamrel-cxu/SPCI-code, commit d598dd3.

Where the code contradicts its paper, or would use a label before it arrives, the paper governs
unless a reason is given. Every departure from either source is listed below with its reason. No
Phase 1 data existed when these settings were fixed.

This is the third version of the appendix. The fifth check found that the first version's tuning
rule and scorecaster, not the method, would have decided F7 against conformal PID (A.7). The
second version tuned conformal PID by a replay analogue of F7's criterion and ran it with three
scorecasters. A second pass of the same check found that its replay started conformal PID cold
while the compensated loop's replay starts from a seeded window, and three more problems (A.8).
This version starts conformal PID from the same seed, and D-P1.11 was proposed (ratified
2026-10-27). A third pass of the check, on 2026-10-27, found problems that led to corrections and
to D-P1.14 (A.9); its re-check and a micro-check followed on 2026-10-28 (A.9), and a focused
check before the freeze (A.10).

### A.1 Common to both

- **Baselines in F7.** There are four: SPCI, and conformal PID with each scorecaster of A.2
  (quantile regression, Theta and matched). Each counts as a baseline in F7, which fires if any one
  of them meets its rule.
  - A conformal PID whose tuning is flagged (A.2) enters F7 at the configuration selected, and the
    flag is reported. F7 judges validity on the evaluation runs.
  - If several baselines meet F7, the paper names all of them, and recommends by name the one
    with the smallest mean run-median width (under D-P1.11, the coverage-matched width).
  - If all widths were equal and the runs independent, the chance that at least one of the four
    is narrower in 12 of the 15 runs would be at most 4 x 1.8 % = 7.2 %. The five runs of a
    regime share their tuned settings, so they are not independent; this holds for F7's own
    1.8 % too. F7 also requires the 5 % margin on the mean.
- **Information.** Every baseline uses the primary point model of its dataset, as the
  compensated loop does (Sections 5.1 and 5.2). The gradient-boosting check runs without
  baselines. When the interval for sample t is issued, the known residuals are r_s for s <= t - h,
  with h = theta + 1, in the timing of `delayed_aci`.
  - One exception applies to every method. Quantities fixed once from the calibration segment use
    all its rows, including the last theta, whose labels arrive during the first theta evaluation
    steps.
  - These quantities are the compensated loop's forecaster and window seed (Section 5.3), the
    matched scorecaster, which is that forecaster, and conformal PID's K_I.
  - The effect is of order theta / T_cal: 4 of 800 rows at TEP T1, theta = 4. Those rows enter a
    least-squares fit, or set K_I if one of them holds the largest residual (a 0.5 % chance per
    run).
  - In the replay on the calibration rows the same quantities are in-sample: the loop's
    forecaster, the matched scorecaster and K_I were fitted on the rows being replayed. The
    quantile-regression and Theta scorecasters are causal in the replay as in evaluation.
  - The seeds work the same way. The compensated loop starts its replay at calibration row 200
    with a window of rows 0-199, and conformal PID starts there from those rows (A.2). Both use
    the last theta seed rows before their labels arrive.
  - SPCI and the other two scorecasters use labelled residuals only.
- **Run span.** Conformal PID runs once per series, from calibration row 200 to the last
  evaluation row, seeded from rows 0-199 (A.2). The same run gives the replay rows (200 to the end
  of calibration) and the evaluation rows. For TEP the stream is hours 30-100 (1400 rows); for the
  debutanizer it is the 1660 training residuals and then the 719 evaluation rows (2379 rows).
  SPCI issues intervals from the first evaluation row and is refitted on labelled residuals from
  the calibration rows on. Metrics come from the evaluation rows only, as for the compensated
  loop.
- **Cells.** TEP T1 at theta = 0, 2 and 4, with F7 decided at theta = 4. The debutanizer at
  theta = 0, 1, 3, 7 and 12, descriptive. Not T2 or T3: no rule depends on them, and they would
  multiply the cost (A.5).
- **Metrics.** U, coverage and width are as in Section 5.4, with width hi - lo.
  - An empty interval (lo > hi, or a side at the wrong infinity) is a miss of width 0.
  - An infinite interval is uninformative.
  - F7 takes the median over all issued intervals, an infinite interval counting as infinitely
    wide.
- **Coverage beside width.** F7's validity band is set on nominal coverage, not on the loop's.
  A baseline at 0.88 passes it, and so does a loop at 0.92. The gap between the two can therefore
  reach 4 points; with the loop near nominal it is about 2 points. [Corrected 2026-10-28 (A.9):
  this text said the bound P2 keeps the loop near nominal. It does not at these lengths: at
  T = 600 and theta = 4 the bound is 10 points at gamma = 0.02 and 18 points at gamma = 0.01.
  Near-nominal coverage is an empirical result (Section 3C and A.5).]
  - For Gaussian residuals a 2-point gap alone narrows a central interval by 5.5 %
    (z(0.94) / z(0.95) = 0.945), and a 4-point gap by 11 % (z(0.94) / z(0.96) = 0.888). Both
    exceed F7's 5 % margin, so F7 as first ratified can fire on coverage alone.
  - The coverage-matched width change scales each run's baseline run-median width to the loop's
    coverage in that run by z((1 + c_loop) / 2) / z((1 + c_baseline) / 2).
  - The scaling assumes a Gaussian shape, as P3 does. For heavier tails it under-corrects, which
    favours whichever method covers less: the baseline when it covers less than the loop, the
    loop when it covers more. [Corrected 2026-10-28 (A.9): this text said it errs toward the
    baseline. In the dry run (A.5) the closest competitor, conformal PID (c) at phi = 0.9, covers
    0.8 points more than the loop: -2.8 % under the Gaussian scaling, -3.7 % (t5), -4.5 % (t3)
    and -4.1 % (Laplace). For SPCI at phi = 0.9, 1.3 points below the loop: +2.0 %, +3.0 %,
    +3.9 % and +3.7 %. The error is 0.9 to 1.9 % of width per coverage point, against F7's 5 %
    margin. D-P1.14 adds a scaling by the loop's own score quantiles beside it.]
  - D-P1.11 (ratified 2026-10-27) makes this coverage-matched width F7's "narrower" test. [The
    fallback written for its rejection no longer applies: F7 as first ratified, with the
    coverage-matched change reported beside the verdict.] Beside each F7 comparison the evidence
    reports the coverage gap (the baseline's mean coverage minus the loop's) and the unscaled
    width change. [2026-10-28: before D-P1.11 the coverage-matched change was the one reported
    beside F7; it is now the test, so the unscaled change takes its place (A.9).]

### A.2 Conformal PID control

| Setting | Phase 1 | Source |
|---|---|---|
| Score and sides | Signed residual. The lower side tracks s = -r and the upper side s = r, each at alpha / 2 = 0.05. Interval [yhat - q_lo, yhat + q_up] | Paper Sec. 3 ("construct prediction sets using the asymmetric (signed) residual score"); code tests/base_test.py lines 131-133 (alpha / 2 per side) |
| Update | q_{t+1} = QT_{t+1} + r(x) + c_{t+1}: quantile tracking QT (Eq. 7), the integrator r and the scorecast c | Paper Eq. (5), with q-hat_{t+1} = QT_{t+1} + c_{t+1}, and Sec. 2.4; code core/methods.py, `quantile_integrator_log_scorecaster` (lines 170-248) |
| Delayed feedback | The update that sets q for sample t + 1 uses the coverage error of sample p = t + 1 - h, the newest labelled one. QT is then a single-state integral loop with dead time theta: the loop of N1', in quantile space | Code: `ahead` = h and t_pred = t - ahead + 1 (lines 216-218). The paper does not discuss delayed feedback (A.6) |
| Seed and start | Calibration rows 0-199 are the seed, as for the compensated loop's replay. Conformal PID issues its first interval at row 200. Each side's tracker starts at the conformal quantile at 1 - alpha / 2 (`conformal_quantile`, the rule of the loop's window) of the side's centred scores s - c over seed rows 100-199, where every scorecaster is active. The seed rows carry no coverage errors; their scores enter the learning-rate window, and the integrator counts them as rows at nominal coverage. QT moves once the newest labelled sample was issued | See "The seeded start" below |
| Coverage record | Every issued step, from row 200 | The code records none before p = 0, and counts the first h - 1 samples as misses, in the tracker's gradient and in the integrator |
| Learning rate | eta = m (max - min) of the Delta = 200 most recent labelled scores, s_{p-199}, ..., s_p. The window is full from the first update (p = 200), when it holds seed scores | Paper Sec. 2.1: eta = 0.1 B-hat_t, with B-hat_t = max{s_{t-Delta+1}, ..., s_t}. Code line 215: the range of the 200 scores before t. See "Departures in the learning rate" below |
| Integrator | r(x) = K_I tan(x log(n) / (C_sat n)), +-inf beyond +-pi/2. x sums (err_i - alpha / 2) over every labelled issued sample, 200 <= i <= p. n = p + 1: the p - 199 issued samples and the 200 seed rows, counted at nominal coverage | Paper Sec. 1.1 (after Eq. 4) and App. C; Eq. (5) sums over i <= t. Code `saturation_fn_log` and `mytan` (lines 131-144). Departure: code line 224 sums over i < p, leaving out the newest labelled error. Phase 1 follows the paper |
| Window Delta | 200 rows: the learning-rate window and the seed | Paper Sec. 2.1 ("we also set the window length ∆ to be the same as the length of the burn-in period"); code T_burnin |
| Scorecaster | Three variants, (a) to (c) below, each a separate baseline in F7. Scorecasts (a) and (b) are zero until the newest labelled index exceeds 50 (`PID_SCORECAST_MIN`), so with h <= 13 they are active from row 64 on; (c) starts with its forecaster | See the rows below. The code starts its scorecaster after its burn-in |
| (a) Quantile regression | Per side, a linear quantile regression at level 1 - alpha / 2 = 0.95. For target tau it regresses the score on its three most recent labelled values at the horizon, s_{tau-h}, s_{tau-h-1} and s_{tau-h-2}. No penalty. It is fitted to every labelled pair (scikit-learn `QuantileRegressor`, HiGHS) and refitted for every target | Paper Sec. 1.2 and App. F, the COVID experiment, which has the paper's only multi-step scorecaster: "an ℓ1-penalized quantile regression as implemented by sklearn.linear_model.QuantileRegressor", with penalty 10, on the three most recent scores and the three most recent case and death counts of all 50 states. The authors' notebook uses level 0.9 (1 - alpha / 2 at that experiment's alpha = 0.2), score lags 4 to 6 at the 4-week horizon, and the 10 most recent points. See "Departures in scorecaster (a)" below |
| (b) Theta | statsmodels `ThetaModel`, period 1, default fit. It is refitted at every step on every score known at issue time, and c for sample tau is its h-step forecast from s_0, ..., s_{tau-h} | Paper Sec. 1.2 (electricity: a Theta scorecaster "re-trained at every time point"); code lines 229-235. See "Scorecaster (b)" below |
| (c) Matched | c = r-hat for the upper side and -r-hat for the lower. r-hat is the compensated loop's own residual forecast (`fit_direct_forecaster`, the same order and fit). c is zero before its first full lag window | No source: it holds the predictor equal, so that F7 compares the two calibration architectures (A.7, finding 2). [2026-10-22: its structure, P + I plus a residual forecast, is that of AcMCP (Wang and Hyndman, arXiv 2410.13115; `LITERATURE_SWEEP_N1.md`, row 21). AcMCP's own forecast has nothing to use at a label delay. An MA(h - 1) model of the h-step errors forecasts only its mean h or more steps ahead, and the shorter-horizon errors its regression uses do not exist when each target has one prediction. AcMCP then reduces to its P + I core, which (c) extends with the best linear predictor of the residual (P3). It is not run separately; to be confirmed by the third pass. 2026-10-28: confirmed (A.9). In the paper's Sec. 4.2 and the authors' R code the MA(h - 1) term is its own h-step forecast, i.e. its mean, and the regression needs same-origin shorter-horizon errors that a soft sensor does not have] |
| Tuning grid | m: the compensated loop's ladder (1, 1.5, 2, 3, 5 and 7 per decade, from 0.001), extended to 1, giving 19 values; the cap is 1. C_sat: (2 / pi) delta log T, (2 / pi)(ceil(delta log T) - 1 / log T) and 5, with delta = 0.02 and T the run length. That is 0.092, 0.549 and 5 for TEP T1 (T = 1400), and 0.099, 0.555 and 5 for the debutanizer (T = 2379). K_I: B' and 10 B', with B' the largest abs(r) on the run's calibration segment. In all, 114 configurations | m: the paper's default is 0.1; the code's configurations use 0, 0.01, 0.05, 0.1, 0.5 and 1, which the grid spans, and the cap is their largest value. For C_sat and K_I, see "The integrator constants" below |
| Tuning | Replay on the pooled calibration segments of a regime's five runs (the debutanizer: its own segment), each run from its seeded start at row 200 and scored from there, as the loop's replay is. The selection is a replay analogue of F7's criterion. Among configurations with replayed U <= eps / 2 and replayed coverage within 0.02 of 0.90, take the smallest replayed median width over all issued intervals ("valid"). If there is none, take the coverage nearest 0.90 among those with U <= eps / 2 ("coverage"). If there is none, take the smallest U ("infeasible"). The bounds are inclusive (a tolerance of 1e-9 absorbs rounding: 2640 / 3000 counts as 0.88). Ties go to the smaller m, then C_sat, then K_I. Under D-P1.11 the width compared is the replayed median width scaled to 0.90 coverage (A.1) | Section 5.3: "its own grid and cap, and is tuned by the same replay to the same target as the compensated loop". The replay and the U target are the compensated loop's; the coverage and width conditions are F7's, on the pooled replay rows, where F7 averages run medians and run coverages |
| Empty sets | A miss of width 0 (Section 5.3) | The authors' evaluation reflects an inverted set instead (tests/base_test.py line 141, minsize 0). That convention is used only in A.4 |

**Departures in the learning rate.**
- The range, as in the code, not the paper's maximum. The scores take both signs: their range
  measures their spread, while their maximum mixes spread and location.
- The window ends at the newest labelled score. The code's window, the 200 scores before t, holds
  h - 2 unlabelled scores at h >= 3, and leaves out the labelled s_t at h = 1. At h = 2 the two
  windows coincide.
- At t = 0 the code takes an unscaled first step, eta = m. Phase 1's first step comes at p = 200,
  with a full window.

**The seeded start.**
- The code starts at q = 0 at its first row and learns its scale during a burn-in. The paper's
  "Without a loss of generality, set q1 = 0" is a step in the proof of Prop. 1 (App. A), not a
  setting.
- The compensated loop starts its replay at calibration row 200 with its window filled by rows
  0-199. A conformal PID started cold at row 0 must learn its scale inside those 200 rows, and
  scorecasters that switch on at row 200 add a second transient. Its replayed coverage is then
  biased: low with the matched scorecaster (0.880-0.890, against 0.885-0.900 in evaluation), high
  with quantile regression (0.915-0.920, against 0.892-0.898). The selection then rejects m
  values that are valid once the run is warm. The second pass of the fifth check measured this
  (A.8, finding 1).
- Section 5.3 gives each baseline "the same information as the compensated loop". Phase 1
  therefore starts conformal PID where the loop's replay starts, from the same seed rows, with
  its tracker at the seed's conformal quantile. It is a departure from the code, with this
  reason.
- The tracker's start uses seed rows 100-199 only, because scorecasters (a) and (b) need 50
  labelled scores before they forecast, and the tracker of a side follows the quantile of its
  centred score s - c.
- The integrator counts the 200 seed rows as rows at nominal coverage: they add nothing to x,
  and n is the run's age, p + 1. A run that restarted its count at row 200 would put the
  integrator's most sensitive stage, where log(n) / n is large and a few misses saturate it,
  inside the scored replay. In an intermediate dry run with the warm tracker but the count
  restarted, no configuration with C_sat = 0.549 and K_I = B' met the U target at phi = 0.9,
  with any of the three scorecasters. With the age, 12 of the 19 m values do with the matched
  scorecaster. [2026-10-28 (A.9): the intermediate run came from a working version of the code
  with the age set to 0, which the committed code does not offer, so it is not reproducible
  from the repository. Its output is kept outside it; the third pass of the check confirmed it
  there, and confirmed the 12 of 19 by a rerun of the committed code.]

**Departures in scorecaster (a).**
- No penalty. A penalty of 10 sets every slope to zero at score scales from 1e-5 to 1, so the
  model is in effect a quantile of recent scores (`LITERATURE_SWEEP_N1.md`, row 20).
- Every labelled pair instead of the last 10. This uses more data and no information the
  compensated loop does not have.
- No covariates: a single residual stream has none.

**Scorecaster (b).**
- The code adds to q_{t+1} a forecast of the score of sample t, made without it, at h = 1. That
  forecast is one step stale. At h >= 2 the code stops with "setting an array element with a
  sequence" (checked). Phase 1 aligns the forecast as the paper describes.
- On the paper's own Table 2 data, mode "phase1" (the aligned forecast, with the integrator and
  window of this table) narrows the median set from 0.178 to 0.085 at the same coverage, 0.900
  (A.4).
- A Theta model forecasts the score, not its quantile, which is what Section 5.3 asks of a
  scorecaster. Scorecaster (c) also forecasts the score. Both are kept: (b) is the authors' code
  and (c) the matched comparison. Counting them in F7 can only make F7 easier to fire.

**The integrator constants.**
- App. C states their purposes:
  - K_I: "to place the integrator on the same scale as the scores"; with B' a bound on the scores,
    K_I = B'.
  - C_sat: that "the tan function has an asymptote at the correct point", for coverage of at
    least 1 - alpha - delta by time T.
- The C_sat formula is read from the extracted PDF text, where its parentheses are lost:
  "Csat = 2 π ⌈log(T)δ⌉ − 1/ log(T)". Two readings follow.
  - Read as (2 / pi)(ceil(delta log T) - 1 / log T), it puts the asymptote where the mean excess of
    misses per labelled step reaches (1 - 1 / log T) / log T. That is 0.119 for TEP T1 and 0.112
    for the debutanizer, about six times delta. The value is the same for any delta up to 0.128.
  - The value that meets the stated purpose is (2 / pi) delta log T, at which that mean excess
    reaches delta.
- The authors never used the heuristic. Their (K_I, C_sat) are (10, 5) for electricity, climate
  and the synthetic series, (200, 1) or (100, 0.1) for stocks, and (1000, 2) for COVID. App. C
  adds that "the numbers can be fine-tuned during a burn-in period by hand or algorithmically".
- Phase 1 therefore puts into the replay grid both readings and the authors' most frequent C_sat,
  with K_I at B' and 10 B'.

### A.3 SPCI multi-step at horizon h

| Setting | Phase 1 | Source |
|---|---|---|
| Residuals | The point model's residuals, in place of EnbPI's leave-one-out ensemble | Section 5.3 |
| Estimator | Algorithm 3's forest for horizon h. Its training pairs are windows of w consecutive known residuals, each with the residual h steps after its last as the target. It is queried at the last w known residuals | Paper Sec. 3.3 (Eq. 13) and Sec. 5.2; Algorithm 3, one forest per horizon, printed in App. C, to which App. B.3 refers; code `multi_step_QRF` (SPCI_class.py lines 336-360) |
| Refits | At every step, on the T_cal most recent known residuals, or on all known ones if fewer. T_cal is 800 for TEP T1 (796 are known at the first evaluation step at theta = 4) and 1660 for the debutanizer | See "Why SPCI refits at every step" below |
| w | round(300 T_cal / 2755): 87 for TEP T1 and 181 for the debutanizer | The paper gives none ("w ≥ 1"). The code uses 300 for its electric and wind data (lines 797 and 801), 200 for solar and 500 for its simulations. On the electric data 2755 training residuals stand behind w = 300. The tutorial says: "If there are not so many residuals, one can decrease it" (notebook cells 3 and 8). Phase 1 keeps the electric data's ratio of w to the training length |
| Quantile forest | Meinshausen's quantile regression forest: 10 trees, maximum depth 2, squared-error splits, all features, bootstrap. It reproduces sklearn-quantile 0.0.29 on scikit-learn's forest, to the bit in the reference environment (A.4) | Code lines 66-68 and `train_QRF` (lines 362-389); paper Sec. 3.3 ("we use the Python implementation of QRF by (Roebroek, 2022)") |
| beta | Grid {0, alpha / 4, alpha / 2, 3 alpha / 4, alpha}. beta-hat minimises the predicted width at the query | Paper Eq. (11); code bins = 5 (line 70) and `binning_use_RF_quantile_regr`. Departure from the code: for S > 1 it chooses beta-hat at the window that ends S - 1 steps before the query. Phase 1 chooses it at the query, as Algorithm 3 does |
| Interval | [yhat_t + Q(beta-hat), yhat_t + Q(1 - alpha + beta-hat)] | Paper Eq. (10) |
| Random state | numpy RandomState(1103 + j) for TEP stream j, and RandomState(1103) for the debutanizer, created anew for each theta. Every refit draws its tree seeds from it | The authors' driver gives 1103 + itrial to its EnbPI point forests (SPCI_class.py lines 789-800). Its quantile forests draw from numpy's global state, which the driver does not seed. Phase 1 gives them a reproducible state of their own |

**Why SPCI refits at every step.**
- Algorithm 1 refits at every t, and the code slides a window of the training length
  (SPCI_class.py lines 268-269).
- Algorithm 3 refits every S steps because its labels arrive in blocks of S ("revealed only in every
  S step", App. B.3). In Phase 1 a label arrives every step, h steps late.

The code switches to `SampleRandomForestQuantileRegressor` above 10 000 training pairs (line 370).
Phase 1 never reaches that: it has fewer than 1500 pairs.

The Phase 1 runner passes w = `spci_window(T_cal)` explicitly. The default of `spci_rolling`,
w = 300, is the authors' setting on the electric data and serves the reproduction (A.4).

### A.4 Reproduction check (2026-10-20)

The scripts are in `scripts/baselines/`, with a README. The record is
`docs/paper/evidence/baseline_reproduction.json`. It holds the SHA-256 of the modules and scripts
that produced each result, and confirms that every result came from the modules and scripts it
hashes. The freeze commit must carry exactly those files; `collect.py` rerun on the committed
tree must still report `all_results_from_this_code`. The reference environment is
Python 3.11 with numpy 1.23.5, scikit-learn 1.1.3, sklearn-quantile 0.0.29 and statsmodels 0.13.5.
SPCI's code needs scikit-learn below 1.2, and torch is replaced by a shim on its random-forest path.

| Check | Published | Authors' code, rerun | IPIS implementation |
|---|---|---|---|
| Conformal PID, Table 1: California COVID deaths, 4-week horizon (ahead = 4); base forecaster and conformal PID | 14 printed values | All 14 reproduced | Mode "code" reproduces all four q sequences bit for bit. Two of them, the base forecaster's (lr 0, no integrator, no scorecaster), are zero throughout, so the table checks two non-trivial sequences |
| Conformal PID, Table 2: electricity, AR forecaster, Theta scorecaster (period 48), ahead = 1; ACI and conformal PID | 14 printed values | All 14 reproduced | Mode "code" reproduces both q sequences of conformal PID bit for bit. Mode "phase1" from row 0 without a seed, as the paper's experiment runs (A.2's integrator and window, the scorecaster aligned): coverage 0.900, median set size 0.085, mean 0.088, against 0.9, 0.178 and 0.177 published |
| Conformal PID, randomised | n/a | The authors' function | 600 random side-runs: ahead 1 to 7, precomputed scorecasts or none, proportional learning rate on and off, lr and K_I including 0, and C_sat from 0.01 to 2, with 304 runs reaching an infinite q. 12 runs of the in-loop Theta scorecaster at ahead = 1 (period 1 and 4). Mode "code" agrees exactly in all of them. The authors' Theta path stops at ahead = 2 and 3 with a ValueError |
| SPCI's quantile forest | n/a | sklearn-quantile 0.0.29 | 40 of 40 random cases agree bit for bit, 10 of them with tied targets |
| SPCI, Table 3: electric data, 90 % intervals, three trials | Coverage 0.93 (sd 0.0048), width 0.22 (sd 0.0017) | Coverage 0.928 (sd 0.0008), width 0.220 (sd 0.0010) | `spci_block` reproduces the authors' intervals bit for bit at S = 1, 2 and 3 (5 of 5 runs); `spci_rolling` does at S = 1 (1 run) |

- **SPCI's spread.** The means reproduce to the two printed decimals; the spread across trials
  does not.
  - Here the trials vary numpy's global seed for the EnbPI ensemble (seed = trial) and for the
    SPCI stage (1000 + 10 trial + S), with the base forest's random_state fixed at the tutorial's
    1103.
  - The authors' driver gives the base forest 1103 + itrial and leaves numpy's state unseeded, so
    its trial-to-trial variation cannot be recreated from the published code.
- **SPCI at S > 1.** The runs at S = 2 and 3 test the SPCI stage at S > 1 on one-step EnbPI
  residuals (the ensemble is fitted at stride 1). They do not test the authors' multi-step
  pipeline, and no published multi-step value is compared.
- **Environment.** "Bit for bit" holds in the reference environment. Phase 1 runs in the IPIS
  environment, whose newer numpy can order tied residuals differently in the forest's sort.
  - The fifth check found QuantileForest identical across the two environments in all 20 cases
    without ties, and different in all 10 with ties (largest difference 0.015).
  - Continuous residuals have no ties with probability one.
  - Theta forecasts are identical across statsmodels 0.13.5 and 0.14.4.
  - Each Phase 1 evidence file records its environment.

### A.5 Cost and dry run

**Dry run** (`scripts/pilots/baseline_dryrun.py`; evidence
`docs/paper/evidence/baseline_dryrun_phi05.json` and `baseline_dryrun_phi09.json`).
- Design: the TEP T1 design on synthetic Gaussian AR(1) residuals, phi = 0.5 and 0.9, as in the
  power analysis. Five runs of one regime, 800 calibration and 600 evaluation rows, theta = 4,
  eps = 1 % and target eps / 2. Conformal PID as in A.2, seeded start included.
- It is a check of the code and the tuning rules, not evidence on F7. Width changes are means
  over five runs of the run-median width, relative to the compensated loop.
- In this design F7's "narrower" means at least 5 % on the mean and in at least 4 of 5 runs.
- "At the loop's coverage" scales each run's width to the loop's coverage in that run (A.1).

F7 as ratified, conformal PID selected by unscaled replayed width:

| Method | phi | Selected on the replay | Width vs loop | Narrower runs | Mean U | Mean coverage | Coverage gap (points) | At the loop's coverage |
|---|---|---|---|---|---|---|---|---|
| Compensated loop | 0.5 | gamma 0.02 | 3.266 (mean run-median width) | n/a | 0.40 % | 0.899 | n/a | n/a |
| PID (a) QR | 0.5 | m 0.015, C_sat 5, K_I B'; valid | +0.8 % | 1 of 5 | 0.00 % | 0.899 | 0.0 | +0.8 % |
| PID (b) Theta | 0.5 | m 0.005, C_sat 0.549, K_I B'; valid | +22.4 % | 0 of 5 | 0.00 % | 0.899 | 0.0 | +22.4 % |
| PID (c) matched | 0.5 | m 0.015, C_sat 5, K_I B'; valid | 0.0 % | 2 of 5 | 0.00 % | 0.899 | 0.0 | -0.1 % |
| SPCI | 0.5 | w 87 | -3.1 % | 4 of 5 | 0.00 % | 0.885 | -1.4 | +0.8 % |
| Compensated loop | 0.9 | gamma 0.01 | 2.619 (mean run-median width) | n/a | 0.00 % | 0.894 | n/a | n/a |
| PID (a) QR | 0.9 | m 0.015, C_sat 5, K_I B'; valid | +1.1 % | 2 of 5 | 0.00 % | 0.894 | 0.0 | +1.1 % |
| PID (b) Theta | 0.9 | m 0.001, C_sat 5, K_I B'; valid | +13.4 % | 0 of 5 | 0.00 % | 0.896 | +0.2 | +11.5 % |
| PID (c) matched | 0.9 | m 0.0015, C_sat 5, K_I B'; valid | 0.0 % | 3 of 5 | 0.00 % | 0.903 | +0.8 | -2.8 % |
| SPCI | 0.9 | w 87 | -1.6 % | 4 of 5 | 0.00 % | 0.881 | -1.3 | +2.0 % |

D-P1.11, conformal PID selected by replayed width scaled to 0.90 coverage, and the first draft's
selection rule (the largest m of the first U-feasible run, C_sat as read, K_I = B'), applied to
the same grid and recursion:

| Method | phi | Selected on the replay (D-P1.11) | At the loop's coverage | Narrower runs at matched coverage | Mean coverage | First draft's selection rule: m; width vs loop |
|---|---|---|---|---|---|---|
| PID (a) QR | 0.5 | m 0.01, C_sat 5, K_I B'; valid | +1.1 % | 2 of 5 | 0.900 | m 0.1; +11.2 % |
| PID (b) Theta | 0.5 | m 0.005, C_sat 0.549, K_I B'; valid | +22.4 % | 0 of 5 | 0.899 | m 0.07; +31.5 % |
| PID (c) matched | 0.5 | m 0.005, C_sat 5, K_I B'; valid | -1.5 % | 3 of 5 | 0.903 | m 0.1; +12.0 % |
| SPCI | 0.5 | w 87 | +0.8 % | 3 of 5 | 0.885 | n/a |
| PID (a) QR | 0.9 | m 0.007, C_sat 5, K_I B'; valid | -0.7 % | 2 of 5 | 0.901 | m 0.07; +15.2 % |
| PID (b) Theta | 0.9 | m 0.003, C_sat 5, K_I B'; valid | +11.5 % | 0 of 5 | 0.895 | m 0.07; +28.6 % |
| PID (c) matched | 0.9 | m 0.0015, C_sat 5, K_I B'; valid | -2.8 % | 5 of 5 | 0.903 | m 0.07; +13.8 % |
| SPCI | 0.9 | w 87 | +2.0 % | 1 of 5 | 0.881 | n/a |

What the dry run shows:
1. Under either rule, none of the four baselines meets F7's conditions in this design. With the
   selection of F7 as ratified, three come within -3.1 % to +1.1 % of the compensated loop's
   width as measured. Under either selection they come within -2.8 % to +2.0 % at the loop's
   coverage. Conformal PID with the Theta scorecaster is 11 to 22 % wider.
2. Coverage moves the comparison. SPCI's -3.1 % (phi = 0.5) goes with 1.4 points less coverage
   and becomes +0.8 % at the loop's coverage. The matched conformal PID's 0.0 % (phi = 0.9) goes
   with 0.8 points more coverage and becomes -2.8 %.
3. The closest competitor is conformal PID with the compensated loop's own predictor: -2.8 % at
   matched coverage at phi = 0.9, narrower in 5 of 5 runs, short of the 5 % margin. With the
   predictor held equal, the two calibration architectures are within 3 %.
4. The first draft's selection rule would have made conformal PID 11 to 32 % wider. The revised
   rules are what make F7 a live test.
5. Every tuning ended "valid"; 36 to 39 of the 114 replayed configurations met the criterion.

**Cost.** The timings come from this dry run, two jobs on the container's two cores (Python
3.12), and from timing runs of the scorecasters and of one SPCI refit at the debutanizer's sizes
(2379 rows; w = 181 on 1660 residuals). An earlier session measured 15 to 30 % less, partly
because its scorecasters started later. The Phase 1 totals extrapolate from the slower figures.

| Item | Measured | Phase 1 |
|---|---|---|
| Theta scorecaster | 38 to 43 s per series of 1400 rows and side; 2.3 times that at 2379 rows. One table to the longest horizon serves every theta | TEP T1: 15 runs x 2 sides, 20 min. Debutanizer: 2 sides, 3 min |
| Quantile-regression scorecaster | 58 to 60 s per series of 1400 rows, side and theta; 4.1 times that at 2379 rows | TEP T1: 15 x 2 x 3, 88 min. Debutanizer: 2 x 5, 41 min |
| Conformal PID tuning (114 configurations, five runs pooled) and evaluation | 9.5 to 10.5 s per scorecaster and cell | 6 min |
| SPCI | 0.14 s per interval at w = 87 on 800 residuals; 4.4 times that at w = 181 on 1660 | TEP T1: 15 runs x 3 theta x 600 intervals, 62 min. Debutanizer: 5 theta x 719, 36 min |
| Total | | About 4.3 h on one core. The runner can split the work over runs |

### A.6 Correction to Section 4, screened under F4 (iii)

- **What Section 4 says.** The paper "does not say whether the quantile-tracking update waits for
  the delayed outcome". Claim 2 says conformal PID's scorecaster result is "without delays".
- **What the code shows** (`LITERATURE_SWEEP_N1.md`, rows 16 and 19). With `ahead` = h the update
  waits: the coverage error it uses is h - 1 samples old. The paper's COVID experiment (Table 1)
  ran this way at ahead = 4, a dead time of 3, with a quantile-regression scorecaster ahead of the
  tracker. Table 1 reports a longest run of errors of 2, against 6 for the base forecaster. The
  paper does not mention the delay. "Without delays" is therefore wrong for that experiment, and
  Section 4 marks the correction.
- **What the paper claims for the scorecaster.** Sec. 3.3, "The effect of scorecasting", says
  that "Figures 2 and 3 already showcase examples in which scorecasting offers significant
  improvement in coverage and set sizes". It adds that further COVID-19 examples in App. F
  "display similar benefits to scorecasting". Figure 2 (California) and Figures 9 and 10 (New York,
  Texas) plot coverage over a trailing 10-week window, a local coverage, for conformal PID
  against the base forecaster, all at the 4-week horizon (checked 2026-10-20; the authors'
  tests/make_plots.sh builds every COVID figure from these two methods).
- **Screen under F4 (iii).** F4 (iii) fires on "an analysis of a residual or score forecaster
  ahead of a delayed online conformal loop, for its effect on miss persistence, step size or local
  coverage". The paper attributes better coverage, local coverage included, to scorecasting in a
  loop that its code delays. Three things keep this from being that analysis:
  - every COVID comparison is conformal PID against the uncalibrated base forecaster: no table or
    figure runs the delayed tracker with and without the scorecaster, so the scorecaster's own
    effect is not isolated;
  - the delay is neither recognised nor varied, and every COVID result is at one horizon;
  - nothing is said about step size, stability or the persistence of misses under the delay.
  - Verdict: F4 (iii) does not fire. The margin is narrower than Table 1 alone suggested.
- **For the manuscript.**
  - It cites Sec. 3.3 and Figures 2, 9 and 10 as prior evidence that a system with a score
    forecaster ahead of a delayed tracker shows better local coverage than an uncalibrated
    forecaster, and states the delay the paper does not.
  - Claim 2's novelty is the isolated, delay-aware analysis: compensation on and off within the
    same delayed loop, its effect on the persistence of misses and on the step size that holds
    the budget, across delays. Local coverage counts for claim 2 only through that ablation.
  - [2026-10-22: the database sweep found that ablation for local coverage, in Wang and Hyndman
    (AcMCP against MPI, electricity data, Fig. 8; `LITERATURE_SWEEP_N1.md`, row 21). It meets
    this section's first two conditions, not the third. F4 (iii) fired on its local-coverage
    clause; see D-P1.12.]

### A.7 Fifth check, and what changed

The fifth check (2026-10-20) reviewed the first version of this appendix, the code, the tests,
the scripts and both papers. It confirmed the code readings and the two stated defects of the
authors' code. It also confirmed that the quantile tracker at ahead = h is a single-state loop
with dead time h - 1, and it confirmed the reproduction numbers. It reran conformal PID's code
mode against the authors' function in 600 random side-runs with no mismatch.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | Critical | Taking the largest feasible m widened conformal PID by 8 to 21 % over the compensated loop in six synthetic T1 designs, against F7's 5 % margin. PID's width rises with m, while the loop's width is flat in gamma. The grid was coarser than the loop's | m is selected on the replay by an analogue of F7's criterion; the grid follows the loop's ladder (A.2) |
| 2 | Critical | The Theta scorecaster forecasts a level, not the quantile that Section 5.3 asks for. Its source cell joined two experiments, and the paper is not silent on a multi-step scorecaster. Theta alone cost conformal PID 5 to 8 % in width | Three scorecasters: quantile regression (the paper's multi-step design), Theta (the authors' code, aligned) and matched (the compensated loop's predictor). F7 counts each (A.1, A.2) |
| 3 | Major | The C_sat formula as read contradicts its stated purpose. K_I and C_sat were left untuned, unlike every configuration the authors published | Both readings and the authors' C_sat, with K_I at B' and 10 B', go into the replay grid (A.2) |
| 4 | Major | SPCI's w = 300 came with 2755 training residuals; TEP T1 has 800. The check found no consistent effect of w | w keeps the authors' ratio: 87 and 181 (A.3) |
| 5 | Minor | The rule "the paper governs" was not honoured for the integrator's newest error, the learning-rate window at h = 1, and the range in place of the maximum | The integrator and the window follow the paper; the range follows the code, with its reason; the rule now reads "unless a reason is given" (A.2) |
| 6 | Minor | K_I uses calibration rows whose labels arrive only after the first evaluation step; so do the compensated loop's forecaster and window seed | Stated as an exception common to every method (A.1) |
| 7 | Minor | Citation slips: the tan integrator is in Sec. 1.1 and App. C; Algorithm 3 is printed in App. C; the NeurIPS version puts the COVID details in App. F; q1 = 0 is a step of a proof; the code's update is an instance of Eq. (5) | Corrected here; Section 4 marks its two |
| 8 | Minor | A.4 overstated the conformal PID evidence: two of the four Table 1 sequences are zero, and no reproduced run saturated | Worded as two non-trivial sequences per table; the randomised check is now a script (`cpid_random.py`) in the record (A.4) |
| 9 | Minor | The SPCI row of A.4 had to report the spread, the seed choices and what S > 1 tests | Done (A.4) |
| 10 | Minor | "Bit for bit" holds only in the reference environment | Stated (A.4) |
| 11 | Minor | Section 4's "without delays" conflicts with the code reading | Corrected and screened under F4 (iii) (A.6) |
| 12 | Minor | Nine points unstated: the integrator's index and argument; the learning-rate window; the refit size at the start; the point model; flagged tuning in F7; the first step at h = 1; the code's early misses; the seeds of the authors' forests; the cost | Stated in A.1 to A.5 |
| 13 | Minor | Hygiene: a test cited a missing script, the README wrote the record to the working directory, and a test rebuilt SPCI's pairs instead of observing them | Fixed: the test now records the pairs the forest is given |

### A.8 Second pass of the fifth check, and what changed

The second pass (2026-10-20) reviewed the rewrite, the revised code, the evidence and both
papers. It re-merged the reproduction record from its inputs (identical but for the timestamp)
and ran three experiments in the dry-run design. It found the 13 first-pass findings resolved as
A.7 states, the code as A.2 and A.3 state, and every number of A.4 and A.5 as its evidence files
state. Overfitting the replay was not a problem: in its 33 studies the selected configuration was
valid in evaluation every time.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | Major | Conformal PID's replay started cold at row 0, the compensated loop's from a window seeded with rows 0-199. At small m PID had not learned its scale by row 200, so the selection rejected values that are valid warm. In 12 studies a warm start moved the selected m from 0.01-0.02 to 0.002 or less in 6, and made 3 studies meet F7's conditions in the dry-run design | Conformal PID starts at row 200 from the same seed, its tracker at the seed's conformal quantile and its integrator aged by the seed (A.2, "The seeded start"); scorecasters (a) and (b) start after 50 labelled scores, so that they are active in the seed rows used. The dry run was rerun (A.5) |
| 2 | Major | Selecting the narrowest valid configuration pushes conformal PID to the low edge of the coverage band, and F7's band, set on nominal coverage, allows a gap of up to 4 points to the loop, worth about 11 % of width; A.1 said 2 points and 5.5 % | A.1 corrected. D-P1.11 proposed: F7's "narrower" at matched coverage, and the selection by coverage-scaled width. If D-P1.11 is not ratified, the coverage-matched change is reported beside F7, and the paper's wording when F7 fires on coverage is fixed now (A.1) |
| 3 | Major | A.6 rested on Table 1 and left out Sec. 3.3, "The effect of scorecasting", and Figs. 2, 9 and 10, which credit the scorecaster with better local coverage in the delayed COVID loop | A.6 and `LITERATURE_SWEEP_N1.md` row 19 now argue the verdict against them: no ablation, no recognition or variation of the delay, nothing on step size or persistence. F4 (iii) still does not fire; claim 2 is stated as the isolated, delay-aware analysis |
| 4 | Major | D-P1.10 said Sections 5.3 and 6 were unchanged, but four baselines raise F7's run-count false-firing rate from 1.8 % to at most 7.2 %; two scorecasters do not forecast a quantile; C_sat and K_I are tuned too; no tie rule; the reporting rule was missing | D-P1.10 rewritten to state each change (Section 9); tie rule in A.2, row "Tuning" [pointer corrected 2026-10-28; it said A.1] |
| 5 | Minor | abs(0.88 - 0.9) = 0.020000000000000018 > 0.02, so a pooled coverage of exactly 2640 / 3000 was excluded | Inclusive bounds with a 1e-9 tolerance in `select_pid_config` and the dry run; a test covers the case |
| 6 | Minor | "F7's own criterion" overstated the replay rule, which pools rows where F7 averages runs | Worded as a replay analogue (A.2) |
| 7 | Minor | In the replay, K_I, the matched forecaster and the loop's forecaster are in-sample; QR and Theta are causal | Stated (A.1) |
| 8 | Minor | The record's hashes name untracked files | The freeze commit must carry exactly the recorded files (A.4) |
| 9 | Minor | A.5's "first draft's rule" is the first draft's selection rule on the revised grid and recursion | Labelled so (A.5) |
| 10 | Minor | Wording slips: the pilots README's "first three", "three" bracketed corrections in Section 4 (there are four), and "8 to 21 %" credited to the rule and the scorecaster together | Corrected in the README, `M1_NARROWING_PROPOSAL.md` and `REVIEW_LOG.md` |
| 11 | Minor | API traps: `spci_rolling` defaults to w = 300; `pid_tune_pooled`'s eps is the replay target | Stated in A.3 and in the docstring |
| 12 | Minor | The 1.8 % and 7.2 % assume independent runs, but a regime's runs share tuned settings | Stated (A.1) |

Not yet independently checked: the resolutions above, the integrator's seed age (A.2, "The
seeded start"), D-P1.11 and the rerun dry run. A third, focused pass of the check was started
twice and stopped both times on the account's usage limit (2026-10-21). It is to run before the
freeze. [2026-10-27: Bien approved it, and it started the same day. Its scope also covers the
database sweep's changes: the F4 verdicts, D-P1.12, the re-attribution of P2, Section 3D and
the screening log. It ran; see A.9.]

### A.9 Third pass of the fifth check, and what changed

The third pass ran on 2026-10-27 and 28, cold, by an agent that had not seen the work. It
checked the resolutions of A.8 and what had never been checked independently (the seeded start
and the integrator's age, D-P1.11, the rerun dry run), the database sweep and its consequences,
and the edits of 2026-10-27. It found nothing critical, and everything mechanical reproduced:
- 95 of 95 tests pass, and the CI's ruff and black are clean.
- An independent transcription of A.2 matched `_phase1_side` with the warm start in 120 random
  cases (largest difference 4.6e-12). Changing residuals whose labels had not arrived changed no
  issued interval in 480 runs, apart from the seed-row exception of A.1. The authors' code mode
  matched their function in 250 of 250 new random runs.
- Every cell of A.5 matches its evidence, and a partial rerun of the dry run reproduced it.
- The screening log and its summary reproduced byte for byte. 20 of 20 X3 and 9 of 10 X2
  decisions, and all 23 F and A notes, agree with the abstracts.
- The tep-rust quotes and dates are exact. In a double-precision TESUB7 run (four seeds, 10^6
  draws) the number of trailing zero bits settled by draw 5 and never fell, and the starting
  state never recurred, as Section 3D argues.
- A.2 row (c) holds: at a label delay AcMCP reduces to its P + I core plus a constant.
- Rows 33 to 35 and 37 of `LITERATURE_SWEEP_N1.md` agree with their sources, and row 36 as far
  as its Sec. 4.1, beyond which the page was not reachable. The 48 Google Scholar codes agree
  with the result pages. Nothing fires F4.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | Major | A.1 said the Gaussian coverage scaling errs toward the baseline under heavier tails. It errs toward whichever method covers less. In the dry run the closest competitor, conformal PID (c) at phi = 0.9, covers more than the loop: -2.8 % under the Gaussian factor, -3.7 to -4.5 % under t5, t3 and Laplace tails, against F7's 5 % margin | A.1 corrected (`scripts/pilots/coverage_scaling_tails.py`, evidence `coverage_scaling_tails.json`). D-P1.14 proposed: the comparison scaled by the loop's own score quantiles is reported beside F7 |
| 2 | Major | Claim 2' had no rule that could reject it. The N1'' text states its directions (less persistent misses, a larger step size), and Section 3E predicts only 1.04 times the step size at phi = 0.5. "A fixed predictor" was ambiguous, since the forecaster is refitted for each theta | D-P1.13 proposed: the rule F8 (Section 6), with a design check (`scripts/pilots/f8_persistence_power.py`). "A fixed predictor" is glossed as a fixed point model (Sections 4 and 9). The paper states that F4 (iii) fired and that claim 2 was narrowed before any data |
| 3 | Minor | Wang and Hyndman's labels and quotes followed v2 (2026-02-02), while the text dated the work to v1 (2024-10-17), where the bound is Prop. 4, the eating-out result Fig. 12, and Fig. 8 reads "MPI and AcMCP coverage display similar pattern" | Labels corrected in Section 4, D-P1.12 and `LITERATURE_SWEEP_N1.md` row 21. The priority holds on v1 |
| 4 | Minor | Stale status text: "D-P1.11 is proposed" in the list of checks and the introduction to this appendix; "to be confirmed by the third pass" in A.2 row (c); A.8 finding 4 pointed to A.1 for the tie rule. `M1_NARROWING_PROPOSAL.md` still called D-P1.10 and D-P1.11 proposed and F4 (iii) unfired, and `REVIEW_LOG.md` stopped at 2026-10-20 | Corrected with dated brackets; the log has rows for 2026-10-22 and 2026-10-27 |
| 5 | Minor | A.1, D-P1.10 (vii) and Section 7 reported the coverage-matched change beside F7, which under D-P1.11 is the test itself. A.1 called F7's first form "as ratified", and credited P2 with keeping the loop near nominal, though at T = 600 and theta = 4 its bound is 10 points at gamma = 0.02 and 18 at gamma = 0.01 | The unscaled change is reported beside F7 (A.1, D-P1.10 bracket, Section 7); "as first ratified"; near-nominal coverage stated as empirical |
| 6 | Minor | D-P1.11's factor is undefined at a run coverage of exactly 0 or 1 | D-P1.14 (ii) clips the coverage |
| 7 | Minor | The screening log coded R207, an interval method (PICP and PINAW), X2: the default for the reference-list searches codes any record without "conformal" X2. R259 likewise | R207, R259 and R269 (found by a scan of the X2 records for interval terms) recoded X3, and R205 and R339 after the re-check: X2 103, X3 206 |
| 8 | Minor | `LITERATURE_SWEEP_N1.md` row 31 (c) counted R073 as an application with delayed feedback; its abstract has no delay | Corrected in row 31 |
| 9 | Minor | Precision in rows 33 to 38: in row 37 (e) the completed windows belong to the score history, not the pacing update; row 37 (b)'s quote is from Sec. IV.B.2; G2's count left out its abstract-level item; row 37 (f)'s App. G.1 was missing from "still due"; the verdict's "no comparison" sentence did not name the measures | Corrected in `LITERATURE_SWEEP_N1.md` |
| 10 | Minor | "G4 found nothing" stood as support for the process positioning, which G4 cannot test, and the W10 bracket read as if the narrowed search had run | Both reworded |
| 11 | Minor | A.2's evidence for the integrator's age, an intermediate dry run, cannot be produced with the committed code | Stated in A.2. The pass confirmed that output, and the 12 of 19 by a rerun of the committed code |
| 12 | For information | The authors are revising Wang and Hyndman (github.com/xqnwang/cpts, commit d972b6e of 2026-10-27): eta = 0.1 B-hat_t, delayed feedback named, and a finite-window bound on local coverage | On a search of its source nothing more fires. The published version is screened again before submission (`LITERATURE_SWEEP_N1.md`, row 21 and "still due") |

**Re-check, 2026-10-28.** The same agent checked the corrections above, D-P1.13, D-P1.14 and
F8's design check. It found the 12 findings resolved, D-P1.13 and D-P1.14 sound and decidable,
and every quoted number equal to its evidence. Everything it reran reproduced, including an
independent regeneration of both F8 evidence files (identical apart from the timestamp). It
found:

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | Major, for D-P1.13 | F8's design check left out T1's label hold. `teprob.f` adds noise of sd 0.5 to each 0.25 h XMEAS(40) sample (XNS(40), through TESUB6) and holds the reading for 5 rows, and compensation at h = 5 cannot predict the noise of the current block. The Phase-1C intervals suggest that noise is 25 to 100 % of T1's residual variance. In synthetic runs with half the variance held, F8 fired in 35 to 80 % of the studies its gate admitted | The design check gained a held-noise option and was run at held shares of 20 and 50 % (`f8_persistence_power_held20.json`, `_held50.json`). Three measures of the miss process were compared under the hold (`f8_estimand_check.py`), and F8 now tests the IACT, which did best in most cells, in place of the lag-1 autocorrelation. The F8 row and D-P1.13 give the results. The risk falls on claim 2' alone: a fired F8 takes it off the claims, and no other rule depends on it |
| 2 | Minor | The F8 row's step-size shares were for the step condition alone | The row gives the share of studies in which the statement is made: F8 tested and holding, and the step condition |
| 3 | Minor | The commitment that the paper states that F4 (iii) fired lived only in D-P1.13, and would lapse with it | Moved to D-P1.12's bracket |
| 4 | Minor | Wording: the appendix introduction credited the pass with the corrections; v1's quote is from its Sec. 5.3; A.1 cited Section 3E for coverage; A.9 overstated the check of row 36; the pilots README gave 0.436 for 0.435; Section 9 step 2 lacked two items due | Corrected |
| 5 | Trivial | R205 and R339 were still coded X2; the F8 evidence had no source hashes; the F8 row named neither the autocorrelation estimator nor the convention for a constant miss indicator; "at most 8.6 %" holds on the simulated grid only | R205 and R339 recoded X3 (X2 103, X3 206); source hashes added to the F8 evidence; the estimator and convention named; "on the simulated grid" |

**Micro-check, 2026-10-28.** The same agent checked the held-noise option, the comparison of
the three measures, the switch of F8 to the IACT, and every number of the F8 row, D-P1.13, this
table and the pilots README against the evidence. The implementation is correct: with w = 0 the
residual is the plain AR(1), and every field that does not depend on F8's measure equals the
earlier evidence. The switch is justified, and nothing blocks the freeze once D-P1.13 and D-P1.14
are ratified. It found a miscount in D-P1.13 (three of five admitted cells, not of four), one
rounding, and a comparison file that hashed its scripts but not the library; all three are
corrected. For the record: the false confirmation rate was simulated only where the gate is
closed (phi = 0.5), and the IACT's window truncation shrinks the measured reduction toward zero,
so that source of error falls against confirming. Independent regenerations of the five F8
evidence files match the committed ones apart from their timestamps (and, for the comparison,
the hash list).

### A.10 Focused check before the freeze, and what changed

The check ran on 2026-10-28, by the agent of A.9. Its scope was the changes since commit
9277784: the third sweep batch, rows 39 to 44 of `LITERATURE_SWEEP_N1.md`, the ratification of
D-P1.13 and D-P1.14, and the freeze record. The agent read the eight texts before reading the
rows. It found nothing critical, no change to any F4 verdict, and one gap in the rules.
Everything mechanical reproduced:
- The screening log and its summary reproduced byte for byte from the raw exports, whose hashes
  match the manifest. A recount from W9.xls and W10.xls gave 106 unique records, 10 in both
  sets, 5 new and 7 matched by the refinement string. The codes of all 12 records whose
  abstracts it read are right.
- Every quote in rows 39 to 44 is verbatim. The citations, record numbers and query codes agree
  with the log.
- 95 of 95 tests pass, and the ruff and black of the CI and of pre-commit are clean. Every
  changed file uses LF and adds no non-ASCII text.
- D-P1.13 and D-P1.14 are byte-identical to commit 9277784 apart from their status cells.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | Major | Section 10 logged later prior art "with its bearing on F4", but F4 (iii)'s consequence for claim 2 is spent. Nothing said whether a later find on miss persistence or on the step size removes all of claim 2' or only the clause it covers, so the choice would have been made with Phase 1 results in hand | D-P1.15 (Section 9), proposed with a strict alternative and ratified 2026-10-29: later prior art is decided clause by clause. The F4 row, Section 9 step 2 and Section 10 point to it |
| 2 | Minor | Row 40's argument on (iii) left room for the literal reading. It misdescribed Qiu et al.'s signal (a projected gradient norm plus a loss variance, Eq. 10), left out the paper's claim that the signal "bridges the temporal gap" of the delay, and did not say why row 21's strict reading does not apply. It called a radius tracked in score space "ACI" | Row 40 rests the verdict on two grounds: the signal is not a forecast of the score, and no step size is analysed or reported. Row 21's reading applied because every element of (iii) was present there. "Adaptive conformal prediction" in row 40, P14, Section 4 and the log note |
| 3 | Minor | Row 40 said the paper's coverage statement concerns the undelayed rule. It concerns the delayed Eq. 1, and is asserted without proof, like Fig. 1's | Corrected |
| 4 | Minor | Row 44: the batched update holds the parameter, not the threshold; "grows with the feedback lag" contradicted "no delayed feedback"; the conditional-coverage results for m > 1 went unaddressed | Corrected in row 44. P2's origin (Section 4) now points to P11 and P15 |
| 5 | Minor | The verdict's positioning bullet and the review log were looser than P13. They left out the nearest record, Yu and Wang (row 42 (a)), whose reference labels arrive later but whose delay is neither set nor analysed | Both aligned with P13, which names row 42 (a). The manuscript says "no analysis of the conformal loop under laboratory delay" |
| 6 | Minor | Nothing recorded why Areces et al.'s LQT and Meng et al.'s update are not F7 baselines | P16: A.2 (a) has the structure of SQT + scorecaster, with a threshold linear in the three latest labelled scores, which LQT of order 3 would fit by online gradient descent; Meng et al.'s update is a conformal PID variant without delay handling, represented by conformal PID |
| 7 | Minor | Row 42 (c) left out Liu and Hassan's residual corrector, the element that (iii) names | Added: it is ablated on point error only, ahead of a queue without a loop |
| 8 | Minor | Section 12 of `M1_NARROWING_PROPOSAL.md` stopped at "proposed" | A 2026-10-28 entry |
| 9 | Trivial | Section 10 did not say what counts as a deviation in code, or that the "If not ratified" fallbacks lapsed | Section 10 says both |
| 10 | Trivial | A.10 was cited before it existed. The list of checks and the introduction to this appendix stopped at 2026-10-27 | This section; both lists completed |
| 11 | Trivial | "Seven full texts", though R073's was a thesis; row 31's bracket listed six | "Seven texts", with the thesis named; row 41 added to row 31 |
| 12 | Trivial | Row 43: the chapter's title differs from the thesis's, the theorem is 3.1.1, the coverage figures also show basic ACI, and the two abstracts match closely, not exactly | Corrected |
| 13 | Trivial | Row 42: the step-size grid belongs to the tuned variant, and Zhu et al.'s sensitivity runs vary reconfiguration-cost parameters, not only weights | Corrected |
| 14 | Trivial | Row 40: h = 20 is the "history window" of Sec. IV.D | Said so |
| 15 | Trivial | The Scholar table's G3 row was not updated, and the summary's mapping check counts W9 and W10 as satisfied by construction | G3 row updated; the summary carries a note on the searches it cannot check |
| 16 | Trivial (for information) | Meng et al.'s proof of Thm 1 is deterministic and does not derive the stated probability | Row 39 and P13 cite the theorem as stated, without leaning on it |

**Micro-check, 2026-10-29.** The same agent checked the fixes above and D-P1.15. All 16
findings (1 major, 7 minor, 8 trivial) are resolved as the table says, and the log, the tests
and the lint reproduce. It found that the D-P1.15 row had edited the text Bien selected, though
the rule was the same; the row now gives that text word for word, with its provenance in a
dated bracket. Four wording points were corrected as well: the scope "by the screens still
due" in the summaries of D-P1.15, a date in `M1_NARROWING_PROPOSAL.md`, row 44's "a
forecaster's effect on the step size", and row 40's account of Fig. 4, which compares runs
with and without the signal on marginal measures.
