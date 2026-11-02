# N1 Phase 1 results

Status, 2026-11-03: step 7 of Section 9 of `PHASE1_PREREGISTRATION.md`, the run and its
F-verdicts. Every number is read from the evidence of commit bd6454d
(`docs/paper/evidence/phase1_*.json`). A number marked "derived" is a count, ratio or percentage
computed from recorded numbers after the verdicts; nothing else was computed after them. Step 8,
the paper's shape, was decided by Bien on 2026-11-03 (Section 10), on what Section 9 lists.

## 1. The run

| Step | Commit | Time (UTC, 2026-11-02) | Notes |
|---|---|---|---|
| Runner | 5ed6f0c | 21:40 | The 15 files of step 6, byte-identical to the checked bundle (`PHASE1_RUNNER.md`) |
| Stage A | 133b0f3 | Files 21:43 to 21:50; committed 21:50, then pushed | Calibration rows only; 613 s on 6 workers |
| Stage B and verdicts | bd6454d | Started about 22:16; files 22:27 to 22:46; verdicts 22:46 | 1822 s; 1359 checks against stage A, all exact |

- Stage B refuses to start unless stage A's commit is on the upstream branch; it recorded
  133b0f3 for every unit. Sources, Python and packages were the same in both stages: Windows
  10.0.26300, Python 3.11.15, numpy 1.26.4, scipy 1.17.1, scikit-learn 1.8.0, pandas 2.3.3,
  statsmodels 0.15.0.
- Inputs: the 15 TEP runs of the qualification record, each with the SHA-256 the record holds;
  the debutanizer file (SHA-256 03ce599a...), whose OLS (intercept 0.9284057386811501, slope
  -0.9666407605697984) equals the pre-check's, with residual autocorrelations within 6.7e-16 of it.
- Deviations: none during the run. Deviation 1 (the T3 window) and the analyzer-timing note were
  logged in Section 10 before it.
- Recomputation: the verdicts recomputed from the committed stage A and stage B files in another
  environment (Linux, Python 3.12.3, numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.2) are the
  same; of 4772 values, 236 differ in the last digits (largest relative difference 1.3e-9).
- Warnings: in T1's stage B, statsmodels warned twice of an overflow in `exp` inside its bounded
  transform of the smoothing weight, while fitting the Theta model of conformal PID's theta
  scorecaster. The transform then returns its bound; every check against stage A was exact and
  the cell's results are finite.
- Stage A, recorded before any evaluation row (`phase1_stageA_*.json`): no tuning flagged
  infeasible at T1, `T1_gb`, T3 or the debutanizer; 9 at T2, all mode1 and uncompensated (the
  replay to eps / 2 at theta = 4, and to eps and eps / 2 at theta = 14, for the sequential,
  projected and Smith loops). There U exceeds its target already at the grid's smallest step,
  0.001 (0.75 to 0.76 % at theta = 4 against 0.5 %; 1.72 to 1.73 % at theta = 14 against 1 %), so
  those cells run at 0.001, flagged, as Section 5.3 fixes. Every conformal PID tuning is
  "valid". The ridge's one-SE penalty is the grid's top, 1000, in 10 of the 15 runs
  (`PHASE1_RUNNER.md`, Section 4: 7 of 15 outside the study).

## 2. Decided rules (Section 6)

| Rule | Cell | Result | Criterion | Verdict |
|---|---|---|---|---|
| F2 | TEP T1, theta = 4 against 0: uncompensated, sequential, stored, delay-blind | U rises by 6.04 pp, 97.5 % CI [3.41, 8.68]; in 13 of 15 runs (derived) | At least 1 pp, CI above 0 | Shown |
| F2 | Debutanizer, theta = 3 against 0, same loop | U is 0 at both: rise 0.00 pp (28 blocks of 25) | The same, block bootstrap | Not shown |
| | | | | **F2 does not fire; the process claim is restricted to TEP** |
| F3 | TEP T1, theta = 4 (the cell where F2 is shown) | Coverage 0.8974 (8077 of 9000), Wilson 95 % [0.8910, 0.9035] | 0.90 outside the interval | **Does not fire** |
| F5a | TEP T1, theta = 4, uncompensated, replay to eps / 2 | Mean U 0.30 % (two runs above 0: mode3/3 3.67 %, mode3/24 0.83 %) | Mean U above 2 % | **Does not fire** |
| F5b | The same, compensated | Mean U 0.18 % (mode1/19 0.83 %, mode1/49 1.83 %) | Mean U above 2 % | **Does not fire** |
| F6 | TEP T1, theta = 4 | Mean of measured / predicted - 1: -4.9 %, 95 % CI [-13.2, +3.5]; predicted ratio 0.880, measured 0.835; runs -27.5 % (mode3/18) to +16.0 % (mode1/19) | Mean outside +-10 % | **Does not fire** |
| F7 | TEP T1, theta = 4, four baselines | The compensated loop is valid (U 0.18 %, coverage 0.8961). No baseline is both valid and narrower (Section 4 below) | A valid baseline narrower by 5 % in 12 of 15 runs, or the loop invalid | **Does not fire**; no baseline recommended |
| F8 | TEP T1, theta = 4 | Gate: mean predicted ratio 0.880, at most 0.95, so tested. IACT of the open-loop misses, compensated minus not: -4.69, 95 % CI [-7.82, -1.55]; lower in 12 of 15 runs (derived) | CI not wholly below 0 | **Does not fire** |
| F8, step size | Replay to eps / 2, per regime | Compensated 0.007, 0.007, 0.007; uncompensated 0.003, 0.003, 0.007: larger in 2 regimes, smaller in none | Larger in 2 or more, smaller in none, F8 held | **Statement made** |
| F1 (secondary) | Debutanizer theta 1, 3, 7, 12; T1 theta 4; T2 theta 14; uncompensated, sequential, every policy in the design region | All 47 cells off by more than 25 %: sd(alpha) predicted / measured - 1 from -33 to -73 %; infinite share from -81 to -100 % in the 24 cells with infinite intervals | Any cell off by more than 25 % | **Fires**; reported, not decisive (D-P1.1) |
| F4 | Literature | (iii) fired on 2026-10-22, and claim 2 became claim 2' (D-P1.12); the screens of Section 9, step 2 are due before submission | | Under D-P1.15 |

Beside F8 (95 % t intervals, compensated minus not): lag-1 autocorrelation of the misses -0.058
[-0.103, -0.013]; mean miss run -0.64 [-1.14, -0.14]; miss rate -1.0 pp [-2.2, +0.2].

## 3. TEP, T1 at theta = 4

Means over the 15 runs (`phase1_stageB_T1.json`, `summary.cells`); width in units of y.

| Cell | U (%) | Coverage | Run-median width | Worst rolling coverage | sd(alpha) | IACT of the misses |
|---|---|---|---|---|---|---|
| Uncompensated, static split conformal (loop off) | 0.00 | 0.9003 | 2.670 | 0.735 | 0.0000 | 8.75 |
| Uncompensated, delay-blind (the N1' diagnosis; F2, F3) | 6.89 | 0.8974 | 2.563 | 0.781 | 0.0614 | 5.45 |
| Uncompensated, white-noise rule `design_gamma` | 18.19 | 0.8989 | 2.441 | 0.815 | 0.0984 | 3.55 |
| Uncompensated, replay to eps / 2 (the N1' remedy; F5a) | 0.30 | 0.8926 | 2.586 | 0.731 | 0.0234 | 7.84 |
| Compensated, static split conformal (loop off) | 0.00 | 0.8998 | 2.101 | 0.771 | 0.0000 | 4.81 |
| Compensated, delay-blind | 5.19 | 0.8990 | 2.095 | 0.815 | 0.0521 | 3.46 |
| Compensated, replay to eps / 2 (the N1'' remedy; F5b, F7) | 0.18 | 0.8961 | 2.124 | 0.797 | 0.0251 | 3.97 |

Section 7's paired contrasts (mean and 95 % t interval over the 15 runs; `summary.contrasts`):

| Contrast | U (pp) | Coverage (pp) | Run-median width | Worst rolling coverage (pp) | IACT |
|---|---|---|---|---|---|
| Compensated minus uncompensated, replay to eps / 2 | -0.12 [-0.75, +0.51] | +0.36 [-0.07, +0.78] | -0.461 [-0.723, -0.200] | +6.53 [+1.84, +11.22] | -3.87 [-6.25, -1.49] |
| Delay-blind minus replay to eps / 2, uncompensated | +6.59 [+4.18, +9.00] | +0.49 [+0.21, +0.77] | -0.023 [-0.103, +0.056] | +5.00 [+2.37, +7.63] | -2.39 [-4.45, -0.33] |
| `design_gamma` minus replay to eps / 2, uncompensated | +17.89 [+15.04, +20.74] | +0.63 [+0.29, +0.98] | -0.145 [-0.242, -0.047] | +8.33 [+5.29, +11.38] | -4.29 [-6.46, -2.13] |
| Loop on minus loop off, compensated, replay to eps / 2 | +0.18 [-0.10, +0.46] | -0.37 [-2.11, +1.38] | +0.023 [-0.102, +0.149] | +2.53 [-0.36, +5.43] | -0.85 [-1.90, +0.21] |
| Arrival minus stored pairing, uncompensated (negative control) | -0.30 [-0.83, +0.23] | -0.64 [-0.91, -0.38] | -0.062 [-0.108, -0.016] | -1.07 [-2.10, -0.03] | +0.11 [-0.20, +0.42] |

At equal budget the compensated loop is narrower by 0.461 (derived: 17.8 % of the uncompensated
loop's 2.586, 95 % CI 7.7 to 28.0 %).

## 4. F7: the baselines at T1, theta = 4

The compensated loop: U 0.18 %, coverage 0.8961, mean run-median width 2.125. Validity: mean U at
most 2 % and mean coverage within 2 pp of 0.90. Width change: the baseline's mean run-median width
against the loop's (positive: the baseline is wider); in brackets, runs in which the baseline is
narrower.

| Baseline | U (%) | Coverage | Valid | Coverage-matched, Gaussian (the test) | Coverage-matched, empirical | Unscaled | Fires |
|---|---|---|---|---|---|---|---|
| Conformal PID, quantile scorecaster | 0.00 | 0.8941 | Yes | +1.6 % (8 of 15) | +1.7 % | +1.3 % (7 of 15) | No |
| Conformal PID, theta scorecaster | 0.00 | 0.8994 | Yes | +17.7 % (0 of 15) | +17.9 % | +19.2 % (0 of 15) | No |
| Conformal PID, matched scorecaster | 0.00 | 0.8947 | Yes | -1.5 % (8 of 15) | -1.3 % | -1.8 % (9 of 15) | No |
| SPCI multi-step | 0.00 | 0.8673 | No (coverage) | +1.6 % (4 of 15) | +2.1 % | -5.8 % (10 of 15) | No |

The matched conformal PID is the closest: its coverage-matched width differs from the loop's by
-0.031, 95 % CI [-0.093, +0.031]. Every conformal PID tuning is "valid" in every regime.

## 5. The analyzer-speed chart (P3)

Width ratio, compensated over uncompensated (static 90 % quantiles of the evaluation scores),
predicted in stage A from the calibration autocorrelation and measured in stage B; error derived
as measured / predicted - 1.

| Unit | theta | Predicted | Measured | Error (%) |
|---|---|---|---|---|
| Debutanizer | 0 | 0.212 | 0.126 | -40.4 |
| Debutanizer | 1 | 0.366 | 0.243 | -33.7 |
| Debutanizer | 3 | 0.559 | 0.415 | -25.8 |
| Debutanizer | 7 | 0.680 | 0.518 | -23.9 |
| Debutanizer | 12 | 0.738 | 0.574 | -22.1 |
| T1 | 0 | 0.472 | 0.386 | -18.2 |
| T1 | 2 | 0.735 | 0.705 | -4.1 |
| T1 | 4 | 0.880 | 0.835 | -5.0 |
| T2 | 0 | 0.312 | 0.176 | -43.6 |
| T2 | 4 | 0.616 | 0.585 | -5.1 |
| T2 | 14 | 0.890 | 0.842 | -5.4 |
| T3 | 0 | 0.863 | 0.829 | -3.9 |
| `T1_gb` | 0 | 0.464 | 0.431 | -7.1 |
| `T1_gb` | 2 | 0.704 | 0.703 | -0.2 |
| `T1_gb` | 4 | 0.838 | 0.834 | -0.4 |

The measured ratio is below the predicted one in all 15 cells: the measured gain is never smaller
than predicted. (F6 is the per-run mean of the error, -4.9 % at T1 theta = 4; the chart's -5.0 %
is the ratio of the means.)

## 6. Debutanizer (descriptive)

One stream, 719 evaluation rows. The F2 cells: U is 0 at theta = 0, 1, 3 and 7; at theta = 12 it
rises by 5.42 pp, 97.5 % CI [0.00, 18.36] (11 blocks), not shown. The uncompensated loop's
coverage is below 0.90 at every theta, theta = 0 included (0.8651 to 0.8776).

| theta | Cell | U (%) | Coverage | Median width | Worst rolling coverage | IACT of the misses |
|---|---|---|---|---|---|---|
| 0 | Uncompensated, static split conformal | 0.00 | 0.7497 | 0.316 | 0.06 | 47.24 |
| 0 | Uncompensated, delay-blind = replay to eps / 2 | 0.00 | 0.8776 | 0.343 | 0.56 | 15.68 |
| 0 | Compensated, replay to eps / 2 | 0.00 | 0.8999 | 0.055 | 0.83 | 2.31 |
| 3 | Uncompensated, static split conformal | 0.00 | 0.7497 | 0.316 | 0.06 | 47.24 |
| 3 | Uncompensated, delay-blind | 0.00 | 0.8734 | 0.345 | 0.53 | 16.79 |
| 3 | Uncompensated, `design_gamma` | 22.53 | 0.9026 | 0.309 | 0.78 | 2.81 |
| 3 | Uncompensated, replay to eps / 2 | 0.00 | 0.8651 | 0.345 | 0.46 | 19.18 |
| 3 | Compensated, static split conformal | 0.00 | 0.8762 | 0.167 | 0.73 | 5.38 |
| 3 | Compensated, delay-blind | 2.64 | 0.8999 | 0.178 | 0.80 | 4.74 |
| 3 | Compensated, replay to eps / 2 | 0.00 | 0.8999 | 0.189 | 0.80 | 5.11 |

- Block-bootstrap contrasts at theta = 3 (95 %, all rows): coverage, compensated minus not, replay
  to eps / 2: +3.5 pp [-3.8, +11.4]; loop on minus off: compensated +2.4 pp [-0.7, +5.3],
  uncompensated +11.5 pp [-0.1, +27.3] (8 blocks of 82).
- Persistence at theta = 3, open loop: IACT 24.7 uncompensated, 5.2 compensated; mean miss run 5.85
  and 2.72; replay step size to eps / 2: 0.002 and 0.010.
- Baselines at theta = 3: conformal PID with the matched scorecaster 0.9013 coverage, F7 width
  0.192 (the compensated loop: 0.189); quantile scorecaster 0.9221 (outside 0.90 +- 0.02);
  theta scorecaster 0.9040, 0.221; SPCI 0.8623 (outside).

## 7. The other arms (descriptive)

The quantities of the decided rules, computed in the same way. F2: rise in U over theta = 0 with
its 97.5 % CI; F5a and F5b: mean U; F6: mean error with 95 % CI; F8: gate and IACT difference
with 95 % CI.

| Arm | theta | F2 rise (pp) | F5a U (%) | F5b U (%) | F6 error (%) | F8 gate | F8 IACT difference |
|---|---|---|---|---|---|---|---|
| T1 | 0 | - | 0.23 | 0.11 | -17.3 [-27.3, -7.2] | 0.472 | -7.24 [-10.16, -4.32] |
| T1 | 2 | +3.00 [+1.67, +4.33] | 0.12 | 0.19 | -3.3 [-13.9, +7.3] | 0.735 | -6.11 [-9.02, -3.21] |
| `T1_gb` | 0 | - | 0.77 | 0.14 | -7.3 [-16.3, +1.8] | 0.464 | -7.69 [-10.32, -5.06] |
| `T1_gb` | 2 | +2.34 [+0.01, +4.68] | 1.47 | 0.16 | +0.2 [-9.7, +10.0] | 0.704 | -6.35 [-9.17, -3.53] |
| `T1_gb` | 4 | +3.71 [+0.90, +6.52] | 1.39 | 0.47 | -0.2 [-9.2, +8.9] | 0.838 | -4.84 [-7.41, -2.26] |
| T2 | 0 | - | 0.14 | 0.17 | -44.2 [-53.2, -35.3] | 0.312 | -13.43 [-16.10, -10.77] |
| T2 | 4 | +3.07 [+1.06, +5.09] | 0.12 | 0.12 | -4.0 [-15.7, +7.7] | 0.616 | -10.71 [-13.54, -7.89] |
| T2 | 14 | +11.46 [+5.23, +17.68] | 0.00 | 0.47 | -5.2 [-13.4, +2.9] | 0.890 | -4.25 [-6.75, -1.76] |
| T3 | 0 | - | 0.28 | 0.33 | -3.5 [-12.5, +5.5] | 0.863 | -0.65 [-1.14, -0.17] |

F1 with compensation (descriptive): off by more than 25 % in 40 of its 41 cells.

## 8. The claims under Section 6

- **N1', diagnosis.** Holds on TEP and is restricted to TEP (F2). At T1 theta = 4 the delay-blind
  loop issues 6.89 % uninformative intervals, 6.04 pp more than at theta = 0, while coverage reads
  nominal (F3: 0.8974, interval containing 0.90). On the debutanizer the delay does not raise U at
  theta_doc; there the uncompensated loop under-covers at every theta, theta = 0 included, and
  static split conformal covers 0.7497.
- **N1', anti-conservative tuning (bullet 3).** Descriptive support on TEP: delay-blind tuning
  +6.59 pp of U and `design_gamma` +17.89 pp against the replay; F1 fires in every realistic cell.
- **N1', remedy (bullet 4; F5a).** Holds: 0.30 % against the 2 % budget.
- **N1'', remedy (F5b).** Holds: 0.18 %, with intervals 17.8 % narrower (CI 7.7 to 28.0 %) at the
  same budget and worst rolling coverage 6.5 pp higher.
- **N1'', design tool (P3; F6).** Holds at T1 theta = 4: -4.9 % (CI -13.2 to +3.5). Its error has
  one sign in every cell of the chart: the prediction is conservative.
- **N1'', validation (F7).** No baseline is valid and narrower; no baseline is recommended. The
  matched conformal PID is within 1.5 % (8 of 15 runs narrower); SPCI under-covers.
- **Claim 2' (F8).** Holds: compensation makes the miss process less persistent (IACT -4.69), and
  the larger step size is stated (0.007 against 0.003 in two regimes, equal in the third).
  D-P1.15 still applies to later prior art.
- **F1.** Fires, as Section 3A predicted; reported.
- **The sentence for the editor (Section 4), filled:** with the TEP analyzer four calibrator
  updates late (theta = 4), compensated conformal intervals were 17.8 % narrower (95 % CI 7.7 to
  28.0 %) at the same 2 % budget of uninformative intervals (measured 0.18 % and 0.30 %), and the
  measured width ratio (0.835) was 5 % below the one predicted from the calibration residuals'
  autocorrelation (0.880).

## 9. What bears on step 8 (assessment, for Bien's decision)

1. **On TEP the loop adds nothing measurable to compensated split conformal.** Loop on minus off:
   coverage -0.37 pp [-2.11, +1.38], worst rolling coverage +2.53 pp [-0.36, +5.43]; width +0.023.
   Compensation does the work (static widths 2.670 and 2.101). The loop's case rests on the
   debutanizer, where static split conformal covers only 0.7497, which suggests (not tested) that
   the test rows differ from the training rows. There the loop lifts coverage from 0.7497 to
   0.8651 uncompensated and from 0.8762 to 0.8999 compensated, with block-bootstrap intervals that
   just include 0. The paper should say this rather than imply the loop is needed on stationary
   data.
2. **P3 is conservative.** It holds where it is decided (T1 theta = 4), but the measured ratio is
   below the predicted one in all 15 chart cells: by 0.2 to 5.4 % at theta >= 2 on TEP, by 3.9 to
   43.6 % at theta = 0 (T3 3.9 %, `T1_gb` 7.1 %, T1 18.2 %, T2 43.6 %) and by 22 to 40 % on the
   debutanizer. The design tool is honest as a lower bound on the gain.
3. **F7 is a tie, not a win.** The matched conformal PID is within 1.5 % (CI of the difference
   includes 0). What the compensated loop adds is a width predicted before deployment and an
   explicit stability limit.
4. **The diagnosis is TEP-only (F2).** On the debutanizer the delay changes little: U stays 0 up
   to theta = 7, and the uncompensated loop's coverage is 0.8776 at theta = 0 and 0.8734 at
   theta = 3. Its under-coverage is present without delay. The paper says so, as the rule
   requires.
5. **Robustness of the point model.** The ridge is at the grid's top in 10 of 15 runs. Gradient
   boosting (`T1_gb`, descriptive) gives the same picture: rise 3.71 pp at theta = 4, budget held
   (1.39 % and 0.47 %), P3 error -0.2 %, IACT -4.84.
6. **Cadence.** At 1-min rows (T2) the delay costs more (+11.46 pp at theta = 14); at the event
   cadence (T3) persistence barely changes (IACT -0.65).
7. **Before submission:** the screens of Section 9, step 2 (F4, D-P1.15); then the venue sequence
   of `VENUE_STRATEGY_N1.md`, Section 4.

## 10. Step 8, decided (Bien, 2026-11-03)

The paper's shape, as proposed after the verdicts and ratified by Bien:
- **One N1'' paper.** TEP (15 runs, three operating modes) is the process evidence; the
  debutanizer (one stream) is a descriptive real-plant case.
- **Its claims are those the rules left standing** (Section 8): the N1' diagnosis, on TEP only;
  replay tuning (F5a); compensation (F5b) with its width gain; P3 and the analyzer-speed chart;
  claim 2' with the step-size statement; the comparison with the four baseline configurations
  (F7) as a tie with the best; F1 reported.
- **Stated up front:** the diagnosis is TEP-only; on stationary data compensated split conformal
  matches the loop, which earns its place when the process drifts; P3 is a lower bound on the
  gain.
- **Order of work:** the screens still due (pre-registration Section 9, step 2; F4 under
  D-P1.15), then the venue sequence of `VENUE_STRATEGY_N1.md`, Section 4, starting with a
  presubmission inquiry to the Journal of Process Control.

The manuscript is written in the private `ipis-papers` repo (`docs/PAPER_LIFECYCLE.md`); its plan
is `ipis-papers/paper/N1_OUTLINE.md`.
