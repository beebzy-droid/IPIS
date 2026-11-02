# N1 Phase 1 runner

Status, 2026-10-29: written after the freeze (tag `n1-phase1-freeze`, commit 6e2e58d), as step 6
of Section 9 of `PHASE1_PREREGISTRATION.md`. This document maps every item of Sections 5 to 7 and
Appendix A to the code, and states each reading where the protocol is silent. Under Section 10,
runner code is not a deviation if it implements those sections as written, leaves the frozen
code's behaviour unchanged and the existing tests pass. Two items needed more than a reading:
- Bien decided the TEP ridge penalty rule and the T3 window on 2026-10-29, before any Phase 1
  number existed (Section 4 below). The T3 window is deviation 1 in Section 10.
- Runs of the extended generator outside the study (mode1, stream 2000, 3 h; mode2, stream 3000,
  2 h; the 15 runs of 100 h of Section 4; all at 60 s) show that each new analyzer value is
  written one 60-s row after the analyzer's instant. Section 10 of the pre-registration records
  the correction to Section 2 that follows; no fixed setting changes (reading R2).

An independent check of the runner against the protocol ran on 2026-10-29 (Section 7 below), and
a full-size dress rehearsal on synthetic inputs on 2026-11-03 (Section 8).

## 1. What runs, and in what order

Code: `src/ipis/module1_soft_sensor/phase1/` and `scripts/phase1_run.py`; tests in
`tests/unit/test_phase1_runner.py`. The frozen library (`evaluation/delayed_aci.py`,
`delay_compensation.py`, `inference.py`, `conformal.py`, `baselines*.py`) is imported, never edited.

| Module | Role |
|---|---|
| `data` | Datasets, TEP arms T1 to T3, segments, input checks (hashes, time column, label hold) |
| `models` | Point models: the debutanizer OLS, the TEP ridge (one-SE rule), gradient boosting |
| `loops` | The loops of Section 5.3 the library does not run (decaying, projected bounds) and the replay tuning of every loop; the loop none (split conformal) is applied in `stages` with stage A's quantile |
| `metrics` | Section 5.4's metrics and the persistence measures of D-P1.12 |
| `rules` | F1 to F3 and F5 to F8 (Section 6; F4 is the literature sweep) and the intervals of Section 7 |
| `record` | Evidence JSON, array fingerprints, provenance |
| `stages` | Stage A and stage B |
| `verdicts` | The F-verdicts from the stage A and stage B records |

The run has two stages, so that every prediction and every tuned setting is on record before an
evaluation row is read (Section 3F):

1. **Commit the runner.** Stage A refuses to run from sources that differ from the last commit,
   so the stage A record names committed code.
2. **Stage A** parses calibration rows only: the debutanizer's training rows (the file's data rows
   are counted, and only the first 70 % parsed) and the TEP rows up to 70 h
   (`np.loadtxt(max_rows=4200)`). Every input file is also identified by its SHA-256, which reads
   its bytes but parses no value. Stage A writes `docs/paper/evidence/phase1_stageA_<unit>.json`
   for the units `debutanizer`, `T1`, `T2`, `T3` and `T1_gb` (T1 with gradient boosting). Each
   holds the point models' settings (the OLS coefficients; the ridge penalty and coefficients; for
   gradient boosting its training size), the forecasters and P3's predicted width ratios (with
   F8's gate), every replay-tuned step size with its path, the static quantiles, y_range,
   conformal PID's tuning and SPCI's window and seeds.
3. **Commit and push the stage A files.** That commit is the record that the predictions came
   first. Stage B refuses to start if a stage A file is not committed, has changed since, or its
   commit is not on the branch's upstream (the remote-tracking branch git updates at each push),
   or if the sources, Python or a package version differ from stage A's; it records the commit.
   Stage A refuses to run again for a unit that has a stage B file.
4. **Stage B** reads every row, recomputes stage A's calibration quantities from the same files
   and checks them against the record (Section 5 below), then runs every cell with stage A's
   settings. It writes `phase1_stageB_<unit>.json` and, for the debutanizer, the per-step flags of
   every cell in `phase1_stageB_debutanizer_steps.json`.
5. **Verdicts**: `phase1_verdicts.json`, the decided rules and the descriptive cells, from the
   records of every unit.

Commands (repository root, `ipis` environment, Windows cmd; the 15 TEP runs in
`data\raw\tep\phase1`, or give `--tep-dir`):

```
set PYTHONPATH=src
python scripts\phase1_run.py --stage A --workers 6
python scripts\phase1_run.py --stage B --workers 6
python scripts\phase1_run.py --verdicts
```

The script sets every BLAS library to one thread before numpy loads, and MKL, if numpy uses it,
to its reproducible code path (`MKL_CBWR`), so that no result depends on a thread count; it
spreads the work over `--workers` processes. Results do not depend on the number of workers
(tested for both stages on a unit without baselines; the independent check confirmed it with the
baselines under Windows' spawn start method).

## 2. Map of the protocol to the code

| Protocol | Code | Notes |
|---|---|---|
| 5.1 point model, OLS of y_t on u5_{t-15}, training rows 0-1674 | `models.fit_ols_lag`, `stages.debutanizer_unit` | Coefficients checked against `phase1_precheck.json` to 1e-12, and the residual autocorrelation at the pre-check's lags to 1e-9 |
| 5.1 calibration segment, the 1660 training residuals; forecaster fitted there | `stages.compensate` with `fit=slice(0, 1660)` | |
| 5.1 y_range over the 1660 rows with residuals | `stage_a`, `y_range` | |
| 5.1 evaluation rows 1675-2393; window initialised with the last 200 training scores; no burn-in | `stages._cells_job` | Every evaluation row counts |
| 5.1 sensitivity analysis without the first 100 rows | `stages.debutanizer_intervals`, `without_first_100` | |
| 5.1 theta in {0, 1, 3, 7, 12}; theta_doc = 3, 7 secondary | `data.DEBUT_THETAS` | |
| 5.2 the 15 runs, checked against the qualification record | `data.tep_files` | SHA-256 of every file before use |
| 5.2 segments 0-30, 30-70, 70-100 h | `data.segment_sizes` | By the nominal minute of each row (R1) |
| 5.2 tuning pooled over a regime's five runs; each run evaluated on its own segment | `stage_a` (plants), `_cells_job` | |
| 5.2 y_range over the pooled calibration segments of a regime | `stage_a`, `y_range` | |
| 5.2 ridge on XMEAS 1-22 and XMV 1-12, inputs lagged by the label age (5 rows at 3 min, 15 at 1 min) | `models.fit_ridge_one_se`, `TepModel.at_lag`, `data.TEP_INPUT_COLUMNS` | One model per run for every arm (R3a); penalty by Bien's rule (Section 4) |
| 5.2 gradient boosting, the estimator-class check | `models.fit_gradient_boosting`, unit `T1_gb` | R5 |
| 5.2 arms T1 (3-min rows, theta 0, 2, 4), T2 (1-min rows, theta 0, 4, 14), T3 (event cadence, theta 0, labelled rows only) | `data.ARMS`, `data.arm_rows`, `data.t3_rows` | R1 to R3 |
| 5.3 compensation: direct (theta + 1)-step predictor, BIC order 1-10 on the calibration segment, least squares, rows before the first lag window keep the raw score, loop sees abs(r - r_hat) | `stages.compensate` | |
| 5.3 predicted width ratio from the calibration autocorrelation | `stages.compensate`: `predicted_width_ratio(acf(r_cal, theta + p + 1), theta, p)` | At the BIC order p (Section 3F) |
| 5.3 six step-size policies | `stages.POLICIES`, `stages.gamma_of` | R9 |
| 5.3 tuning rule: grid, cap 0.8 gamma_crit, largest value below the first exceedance, infeasible at 0.001 flagged, seed rows not replayed, no burn-in; delay-blind replays at theta = 0 | `loops.replay_tune` | Equal to `delayed_aci.replay_tune_pooled` for the loops it runs (tested) |
| 5.3 loops: sequential (primary), none, projected [0.01, 0.5], phase, Smith, decaying; every loop tuned by the same replay | `loops.run_loop`, `loops.run_decaying`; none in `stages._cells_job` from stage A's quantile | R10 |
| 5.3 baselines, Appendix A | `stages._pid_stage_a`, `stages.baselines_stage_b` | R12 |
| 5.3 pairing: stored primary, arrival at theta_doc the negative control | `stages.pairings_of` | R11 |
| 5.4 U, the infinite share, coverage with its Wilson 95 % interval, rolling coverage sd and minimum, steps below 0.80, sd(alpha) and range, width median, p90 and p99 over finite intervals, F7's median over all intervals | `metrics.interval_metrics`, `metrics.loop_metrics` | R13, R14 |
| 5.4 analyzer-speed chart: static 90 % quantiles of compensated and raw evaluation scores, against P3 | `_cells_job` (`measured_ratio`), `verdicts.analyzer_speed_chart` | As `scripts/phase1_power.py` measures it |
| 6 F1 to F3 and F5 to F8 | `rules`, `verdicts` | R16 to R21 |
| 7 debutanizer CIs: circular block bootstrap, B = 2000, block max(25, ceil(2 IACT)), same blocks for differences, fewer than 8 blocks unreliable | `rules.block_ci`, `rules.paired_block_ci` | Seed 0 |
| 7 TEP CIs: t intervals over the 15 runs, regime reported, differences paired by run | `stages.runs_summary`, `stages.paired_runs` | R22 |
| 7 F7 by its rule alone; paired width differences reported with t intervals | `rules.narrower` | Coverage-matched, unscaled and empirical-quantile widths |
| 7 F8 by its paired two-sided 95 % t interval | `rules.f8` | |
| A.1 four baselines in F7; recommend the narrowest that meets F7; a flagged tuning reported | `rules.f7_verdict`, `verdicts` (`pid_tuning_flags`) | |
| A.1 information: point model of the dataset; calibration-fixed quantities use all calibration rows | `stages` | The gradient-boosting check runs without baselines |
| A.1 run span: conformal PID from calibration row 200 to the last evaluation row, seeded from rows 0-199; SPCI from the first evaluation row | `_pid_eval_job`, `_spci_job` | |
| A.1 cells: T1 at theta 0, 2, 4 (F7 at 4); debutanizer at 0, 1, 3, 7, 12 | `Unit.baselines` | Not T2, T3 or `T1_gb` |
| A.1 empty interval: a miss of width 0; infinite: uninformative | `baselines_pid.conformal_pid_intervals`, `_spci_job` | |
| A.2 conformal PID settings, three scorecasters, grid of 114, C_sat from T = 1400 and 2379, K_I from B', D-P1.11's selection (scale_to 0.90), replay target eps / 2 | `_pid_stage_a`, `_pid_tune_job` | `pid_tune_pooled`, `select_pid_config` unchanged |
| A.3 SPCI: w = round(300 T_cal / 2755), T_cal most recent known residuals, refitted every step, RandomState(1103 + j) for TEP stream j and RandomState(1103) for the debutanizer, anew for each theta | `_spci_job`, `stages.spci_seed` | R12 |
| D-P1.11 coverage-matched width; D-P1.14 empirical factor and coverage clipping | `rules.f7_compare` | R15 |

## 3. Readings where the protocol is silent

- **R1, TEP rows.** Row i of a run (from 0) is written at simulation second 60 (i + 1), its
  nominal minute i + 1. The driver writes it before that second's integration step, so the time
  column reads (60 (i + 1) - 1) s, in hours to five decimals; the loader checks it to 2e-5 h.
  Segments use the nominal minute: training (0, 1800], calibration (1800, 4200], evaluation
  (4200, 6000]. T1 keeps the rows at whole multiples of 3 min (2000 rows: 600, 800 and 600), the
  rows a 180-s recording writes; T2 keeps every row (1800, 2400 and 1800).
- **R2, the analyzer's timing.** `teprob.f` updates XMEAS(40) at whole multiples of 0.25 h with the
  composition captured 0.25 h earlier. The update happens in the integration step after the row
  written at that instant, so in the CSV a new value first appears at minute 15k + 1 and is held
  for 15 rows; at T1 it first appears at row 5k (minute 15k + 3) and is held for 5 rows. A reading
  is therefore 6 T1 rows (16 T2 rows) old when it first appears, not 5 as Section 2 says. Nothing
  fixed changes: the input lag (5 and 15 rows) and the dead times (theta at most 4 and 14) count
  the rows from the row whose inputs give the prediction to the row in which the label is
  written, which is the 0.25 h of Section 2's table; the extra row only puts the inputs one row
  (3 min at T1, 1 min at T2) after the composition's capture at a block's first row. Both stages
  check that the label is constant within every block of that phase (`data.label_hold`) and
  stop otherwise; the tests check the convention on a 2-h run of the generator
  (`tests/fixtures/`). On the 15 runs of 100 h of Section 4 the label is constant in every block
  of that phase, at T1 and T2, with a new value at every block start, and not constant in the
  blocks one row earlier.
- **R3, T3.** The labelled rows are the T1 rows where a new analyzer value appears, j = 5, 10,
  15, ... (minute 15k + 3); j = 0 holds the initial value. T3 takes the shared point model's T1
  residuals at those rows: 160 calibration and 120 evaluation events per run. The calibrator issues
  the interval for event k from the inputs of row 5k - 5, the row in which event k - 1's label
  appears, so theta = 0 (counted from the sample, theta would be 1; R2's convention is the one
  that keeps the three fixed dead times consistent). Window: deviation 1 (40 events).
- **R3a, one point model for every arm.** Section 7: "within a dataset, every arm shares the point
  model and the residual stream." Per run, the ridge is fitted once, on T1's training rows (3-min
  rows, inputs 5 rows back, 595 pairs). It has no row dynamics, so T2 applies the same fitted model
  at 1-min rows with the inputs 15 rows back, and T3 uses T1's residuals at its event rows: T1's
  residuals are T2's at every third row (tested). The arms then differ only in the calibrator's
  cadence and theta. Gradient boosting (R5) is fitted on the same T1 rows and runs in T1 only.
- **R4, ridge penalty** (Bien, 2026-10-29): Section 4 below.
- **R5, gradient boosting.** scikit-learn `GradientBoostingRegressor` with its default settings
  and random_state 0, on T1's inputs and rows, every loop, policy and theta, no baselines (A.1:
  "The gradient-boosting check runs without baselines"). Descriptive.
- **R6, the debutanizer** is as Section 5.1, with the pre-check checks of Section 2 above.
- **R7, the residual streams.** TEP: hours 30-100, 1400 T1 rows (A.1). Debutanizer: the 1660
  training residuals and the 719 evaluation residuals (2379). Stage B builds every calibration
  array by the same calls as stage A (one prediction call on the rows up to 70 h; forecasts of
  the calibration rows on those rows alone), because a matrix product can differ in its last bit
  with the size of the matrix it is computed in.
- **R8, windows and seeds.** Replay: the first 200 calibration scores seed the window, the rest are
  replayed. Evaluation: the window holds the last 200 calibration scores and the level starts at
  alpha, as in the power analysis and the pilots. T3: 40 and 40.
- **R9, step-size policies.** Fixed 0.005, fixed 0.05, delay-blind (replay at theta = 0 to eps),
  delay-aware to eps and to eps / 2, and `design_gamma(theta)`; a cell whose `design_gamma` is
  undefined (NaN) is recorded as not run. With compensation on, the delay-blind replay runs the
  compensated scores of the cell's theta at theta = 0: the forecaster must use the labels in hand
  at the true delay, and only the tuning ignores it. Infeasible tunings are evaluated at 0.001 and
  flagged in the cell (`tuning_feasible`).
- **R10, loops.** Sequential, Smith and phase are `run_delayed_aci` unchanged; projected is
  `run_delayed_aci` with bounds (0.01, 0.5). Decaying is the sequential update with step
  c n^-0.6 for the n-th label received in the run (Angelopoulos, Barber and Bates 2024, Sec. 1.1
  and 4, checked in the paper's body), applied to the level as every loop of Section 5.3 is; c is
  tuned by the same replay and cap, and n restarts with each run (replay or evaluation), as the
  level does. None is split conformal: the conformal quantile at 0.90 of all calibration scores,
  recorded in stage A, one half-width for every evaluation row. The phase and Smith loops are
  tuned under the same cap of 0.8 gamma_crit(theta), as "the same replay" says.
- **R11, arrival pairing.** At theta_doc of each unit (debutanizer 3, T1 and `T1_gb` 4, T2 14; not
  T3, whose only theta is 0), on the sequential loop, at every policy, with the step size tuned
  under stored pairing, so that only the pairing varies.
- **R12, baselines.** Stage A builds every scorecast from calibration rows only and tunes conformal
  PID by `pid_tune_pooled` on each regime's pooled calibration segments (the debutanizer: its own).
  Stage B recomputes the scorecasts on the whole stream, checks that their calibration rows match
  stage A's, runs conformal PID from row 200 with stage A's configuration, and checks that its
  calibration rows reproduce the replayed U, coverage and median width stage A recorded. B' is the
  largest abs(r) of the run's calibration rows. SPCI's stream j is the MRG32k3a stream number of
  the run; the random state is created anew for each theta.
- **R13, metrics.** Rolling coverage over trailing windows of 100 steps (`np.convolve`, the windows
  ending at steps 99 on, as `delayed_aci.diagnostics`); "steps spent in under-coverage episodes"
  is the number of those windows below 0.80. Every cell also reports the lag-1 autocorrelation,
  the mean miss run and the IACT of its miss indicator (D-P1.12).
- **R14, F7's width** is the median over all issued evaluation intervals, an infinite interval
  counting as infinitely wide; an empty set counts as width 0 and a miss.
- **R15, D-P1.14 (i).** The quantiles come from the absolute compensated calibration scores at the
  cell's theta of the run's regime, pooled over its five runs, all calibration rows (warm-up rows
  included, as the loop sees them); n in the clip is the number of evaluation intervals of the
  run (600).
- **R16, F2.** TEP: per run, U at theta = 4 minus U at theta = 0, raw, sequential, stored,
  delay-blind; the increase is shown if the mean is at least 0.01 and the two-sided 97.5 % t
  interval lies above 0, as `scripts/phase1_power.py` tests it. Debutanizer: the per-step flags
  at theta = 3 and 0, the paired block bootstrap at 0.975; a cell with fewer than 8 blocks cannot
  show the increase (it is descriptive). F2 fires if neither cell shows it; with one, the claim is
  restricted to that dataset.
- **R17, F3** is tested only in a primary cell that shows F2's increase, in the same cell (counts
  pooled over the 15 runs for TEP); it fires if 0.90 lies outside the Wilson interval in any cell
  where it is tested.
- **R18, F5 and F6.** F5a and F5b: T1 at theta = 4, sequential, stored, tuned to eps / 2, raw and
  compensated; mean U over the 15 runs above 0.02. F6: the mean over the runs of measured /
  predicted - 1, the prediction from stage A.
- **R19, F7.** Decided at T1, theta = 4, by `rules.f7_compare` for each baseline (min 12 of 15
  runs); the loop is compensated, sequential, stored, tuned to eps / 2. Conformal PID's tuning
  flag per regime is reported beside it (A.1). The other baseline cells are computed the same way
  and are descriptive.
- **R20, F8.** The gate is the mean predicted ratio at T1, theta = 4, recorded in stage A. The test
  uses the open-loop miss indicators of stage B (the delayed loop at gamma = 0, window seeded with
  the last 200 calibration scores), raw and compensated. The step-size condition uses stage A's
  step sizes, sequential, tuned to eps / 2, per regime.
- **R21, F1.** "At realistic theta" (the M1 narrowing proposal's F1) is read as the delays Section 2
  documents that the grids hold: the debutanizer at 1, 3, 7 and 12 (its 20 to 75 min range,
  theta_doc 3 and the secondary 7), T1 at 4 and T2 at 14. Section 2 documents T3's theta = 0 too,
  but under deviation 1 T3 is descriptive only, so F1 is evaluated without it. Cells: raw,
  sequential, stored, every policy whose step size lies in (0, 0.8 gamma_crit], the region
  `design_gamma` searches. The measured sd(alpha) and infinite share are means over the runs that
  share a step size (a tuned policy has one per regime). The error is predicted / measured - 1,
  as in `scripts/pilots/persistence_pilot.py`. A measured infinite share of 0 from N intervals
  resolves no share below one interval: there the error is undefined, and the model counts as off
  if it predicts more than 1.25 infinite intervals (25 % above the one that could have gone
  unseen). F1 fires if any cell is off by more than 25 % in either quantity. The compensated cells
  are reported beside it.
- **R22, Section 7.** TEP: every cell's mean and 95 % t interval over the 15 runs for U, the
  infinite share, coverage, rolling-coverage sd and minimum, under-coverage steps, sd(alpha), the
  widths and the persistence measures, with regime means and the pooled Wilson interval.
  Debutanizer: the block-bootstrap interval of U, the infinite share and coverage for every cell
  and baseline, with and without the first 100 rows. The one-factor contrasts, paired by run (TEP)
  or on the same blocks (debutanizer, for U and coverage): compensated minus raw; theta minus
  theta = 0; arrival minus stored; loop on minus loop off (the sequential loop at each policy minus
  static split conformal, R4.9's 2x2); each comparison loop minus the sequential loop; and each
  policy minus delay-aware tuning to eps / 2 (delay-blind and the white-noise rule against replay,
  N1' bullet 3; eps against eps / 2; the fixed step sizes).
- **R23, descriptive cells.** The debutanizer's F5a, F5b, F6 and F7 cells (Section 6), every theta
  other than the primary ones, `T1_gb`, T2 and T3 are computed with the same functions and
  labelled descriptive in the verdicts file.
- **R24, provenance.** Every stage A, stage B and verdicts file, and the steps file, records the
  SHA-256 of the sources (CRLF read as LF, as git stores them), Python and the package versions,
  and the git commit. Stage A records the SHA-256 of every input file, and stage B stops if they
  differ; the stage B and steps files record the SHA-256 of the stage A file they used, and the
  verdicts file that of every evidence file it reads. Evidence JSON is strict (non-finite numbers
  as the strings "inf", "-inf" and "nan") and written with LF line ends.

## 4. Decisions taken for the runner (Bien, 2026-10-29, before any Phase 1 number)

- **TEP ridge penalty** (option "CV, one-SE rule (Recommended)"). Inputs standardised on the
  training rows; the penalty from 13 values, `logspace(-3, 3, 13)`; 5 contiguous folds of the
  training pairs, the scaler refitted inside each fold; the largest penalty whose mean held-out MSE
  is within one standard error of the smallest (as D-P0.1's one-SE rule), ties to the smaller
  penalty at the minimum. On 15 runs of 100 h of the generator outside the study (mode1: streams
  3001, 3126, 3135, 3144, 3150; mode2: 3000, 3103, 3115, 3127, 3130; mode3: 3002, 3101, 3110,
  3113, 3116), the fold standard errors are 9 to 99 % of the smallest mean MSE, and the rule picks
  the top of the grid, 1000, in 7 of 15 (the minimum-MSE penalty: in 1 of 15). Out of sample it
  does no worse: on the calibration hours its T1 residual sd averages 0.732 against 0.742 for the
  minimum-MSE penalty (R^2 0.30 against 0.26). Its residuals are slightly more autocorrelated
  (lag 1: 0.86 against 0.84), so P3's predicted width ratio at theta = 4 averages 0.866 against
  0.881. Every run's penalty is in the stage A record, so the paper can report how often the
  grid's top binds.
- **T3 window** (option "Run it with a 40-event window (Recommended)"). Section 5.3's 200-row seed
  does not fit the 160 events of T3's calibration hours. The window is 40 events, the 10 h that
  T1's 200 rows span: seed 40, replay 120, evaluate 120. Logged as deviation 1 in Section 10 of
  the pre-registration; no rule is decided on T3.
- **Gradient boosting** (proposed with the runner and confirmed by the independent check): R5.

## 5. Checks built into the run

Stage B stops before it reads an evaluation result if any of these fails:
- the settings, the streams or the input files' SHA-256 differ from stage A's;
- the sources, Python or a package version differ from stage A's (unless overridden, which the
  record would show);
- a point model differs: its kind and input lag; the ridge penalty exactly; the OLS and ridge
  coefficients to a relative 1e-9 (gradient boosting through its residuals, below);
- an array differs: every calibration residual and label stream, every compensated calibration
  score stream and every conformal PID scorecast, by SHA-256. If only the bytes differ, the
  summaries must agree as they would if every element agreed to a relative 1e-12 (each sum within
  1e-12 of the sum of the magnitudes it adds); the record then marks the check "close" instead of
  "exact". That accepts last-bit differences and rejects any element that moves by more than
  1e-12 of the sum of magnitudes (for 800 residuals of unit size, 8e-10);
- a forecaster's order, a coefficient, a predicted ratio, a static quantile, y_range or B';
- conformal PID's calibration rows do not reproduce the replay stage A selected on.

The verdicts stop if a unit's records are missing or a stage A file is not the one stage B used.
The console reports "all exact" or lists the checks that matched only within tolerance.

## 6. Tests

`tests/unit/test_phase1_runner.py`:
- the generator's conventions on its own output (a 2-h run outside the study in
  `tests/fixtures/`): time column, the 15-row hold from minute 15k + 1, T1's blocks, T3's rows;
- the data handling on synthetic files: segments, T1 and T2 rows, label hold and its phase, T3
  rows and counts, hash checks, the debutanizer split and pre-check checks, stage A's debutanizer
  unit unchanged whatever the evaluation rows hold; the 15 runs loaded at full size for every TEP
  unit in both stages, stage A's arrays reproduced bit for bit, T2's residuals equal to T1's at
  every third row;
- the models: staged residuals, the one-SE rule;
- the loops: `replay_tune` against the library for the sequential, Smith and phase loops; the
  projected bounds; the decaying loop at exponent 0 against the sequential loop and its schedule;
  split conformal (`loops.run_static`);
- the metrics and every rule on hand-computed cases, including F7's coverage matching, D-P1.14's
  clipping and F1's zero-measured cells; the contrasts, each varying one factor;
- the records: strict JSON, line ends, fingerprints and their tolerance;
- both stages end to end on small units with the real theta grids: every cell of the design run,
  stage B's checks all exact, stage B stopping on a changed calibration row and on a changed
  setting, results independent of the number of workers (both stages), F2, F3, F5a, F5b, F6, F8
  and the SPCI and conformal PID cells of F7 equal to a computation from the frozen library alone,
  and the command line's verdicts (stopping when a unit's records are missing);
- the commit and push checks, on a throwaway repository with a local remote.

The tests pass under Python 3.12 (numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2, pandas 2.2.3,
statsmodels 0.14.4) and Python 3.11 (numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1, pandas 3.1.0,
statsmodels 0.15.0), as do the library's 110 tests.

## 7. Independent check (2026-10-29)

An agent that had not seen the runner checked it against the protocol, the design-stage scripts and
the generator, cold. It recomputed F2, F3, F5a, F5b, F6, F7 (all four baselines) and F8 from the
frozen library at protocol sizes and found every value equal to the runner's, bit for bit; it
reproduced the analyzer timing and confirmed the Section 10 note and deviation 1. Its two major
findings were fixed: T2 had its own ridge, against Section 7 (now R3a), and stage A parsed the
debutanizer's evaluation rows before dropping them (now counted, not parsed). So were its minor
findings: F1's zero-measured cells and its delays (R21), the loop and policy contrasts (R22), the
tests (Section 6), and the tolerance's wording and the package-version check (Section 5); and its
trivial ones (the Section 10 note, this document, conformal PID's flag beside F7, committing the
runner before stage A).

## 8. Dress rehearsal (2026-11-03)

The whole run at full size on synthetic inputs, not study data: 15 TEP-like files of 100 h at
60 s with the generator's time column and analyzer hold, a qualification record holding their
SHA-256, a 2394-row debutanizer-like file and its pre-check. It used the final sources, the
commit checks overridden, and 2 worker processes on 2 cores.

| Step | Time | Output |
|---|---|---|
| Stage A | 24 min: debutanizer 7, T1 12, T2 3, T3 under 1, `T1_gb` 1 | 5 files, 2.1 MB; no tuning flagged infeasible; every conformal PID tuning "valid" |
| Stage B | 84 min: debutanizer 29, T1 54; T2, T3 and `T1_gb` 1 together | 5 files and the steps file, 11.3 MB (largest 2.96 MB); 1359 checks against stage A, all exact; every cell of the design run |
| Verdicts | 2 s | `phase1_verdicts.json`, 0.17 MB |

Peak memory was 182 MB per process. Nearly all of stage B is spent in the two units with
baselines.
