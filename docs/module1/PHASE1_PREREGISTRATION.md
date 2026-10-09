# N1 Phase 1 pre-registration (DRAFT, 2026-10-09)

Status: **DRAFT, not frozen.** It freezes when three things have happened:
1. Bien ratifies the decisions in Section 9.
2. `scripts/phase1_precheck.py` has run on the training split and its evidence is committed.
3. The freeze commit is recorded in Section 10.

Until then no Phase 1 number exists from the debutanizer validation or test rows or from new TEP
runs. Two independent checks of this draft were made on 2026-10-09. They compared the numbers with
the pilot output and the citations with the sources, and tested the logic of Section 6. They found
an off-by-one in the delay convention, gaps that left the falsification tests undecidable, and
several wording errors. All are corrected below.

## 1. Purpose

Phase 1 decides whether N1 survives process data. It tests three things:
- whether the delayed calibration loop degrades at documented delays on real and simulated process
  residuals (F2);
- whether marginal coverage misses that degradation (F3);
- whether a delay-aware remedy controls it (F5, new).

It also proposes replacing the white-noise noise-gain model as the load-bearing prediction
(D-P1.1), because a pre-data pilot shows that model fails on serially correlated residuals
(Section 3).

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
| Debutanizer (Fortuna et al. 2007) | C4 in the bottoms, by a GC on the deisopentanizer overhead; 15-min measuring cycle (Sec. 6.2, p. 117) | About 45 min (15-min cycle plus about 30 min for the analyzer's location; Sec. 6.2, p. 117). Ranges: 20 to 60 min (Sec. 5.5, p. 97); 30 to 75 min (Siddharth, Pathak and Pani 2019, p. 42) | 12 min (Sec. 6.2) | 4: the book's newest label is y(k-4), 48 min old | **3** |
| | | | 6 min (see note) | 8 | **7** |
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

  The book does not say whether the public file is the Sec. 4.1 recording. The pre-check
  (Section 8) tests which Ts the file supports, from the share of repeated label values: about 0.2
  at 12 min and 0.6 at 6 min, provided the GC value was recorded as held.
- **The rejected manuscript's delay of 4.** Its bias-update code used the label 4 samples old
  (`apply_bias_update`, `y_true[t - delay]`). That equals Fortuna's documented latency at
  Ts = 12 min, not only a NARMA convention. In the convention above it is theta = 3.
- **TEP analyzer.** The Russell-Braatz simulator implements the analyzer as sample-and-hold. At
  each 0.25 h instant XMEAS(37-41) takes the composition captured 0.25 h earlier, plus noise
  (`teprob.f` lines 736-761, camaramm/tennessee-eastman-profBraatz commit 0643318). At 3-min rows a
  reading is held for 5 rows and is 5 rows old when it appears.
- **DCS execution rate.** A 1-min DCS execution rate is common (general knowledge, not verified).
  At that rate the debutanizer GC would give theta = 44 if the calibrator updated every row on held
  labels.
- **TEP alignment.** Phase 0 found a transport lag of 0 from XMEAS_3. That is an E-feed flow the
  control system manipulates, and 0 is the edge of the scanned range. Phase 1 aligns the TEP inputs
  at the analyzer's documented dead time instead (D-P1.3).

## 3. Pre-data findings (synthetic, library-generated: `scripts/pilots/persistence_pilot.py`)

Residual streams are |x_t|, with x a Gaussian AR(1) of lag-1 autocorrelation phi.
- Settings: sequential loop, stored pairing, window R = 200, alpha* = 0.10. Here theta is the
  library's theta.
- Seeds: 5 in part A, 3 in part B. Calibration and evaluation segments do not overlap.
- Runtime: about 3 min.

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

What this means for Phase 1:
1. On serially correlated residuals the phenomenon is stronger, not weaker.
2. The ratified model-based design rule (O3) is anti-conservative there.
3. Tuning on history without the delay is anti-conservative.
4. Replaying history through the delayed loop meets the budget out of sample. The price is a step
   size 1.5 to 6 times smaller than delay-blind tuning gives, which means slower adaptation; Phase 1
   measures that cost on process data.

Limits of the pilot: Gaussian AR(1) scores, stationary, one window length, three to five seeds.

## 4. Proposed amendment to the claim (D-P1.1)

**Ratified N1 (2026-09-28).** The loop's "interval volatility and its fraction of unusable
(infinite) intervals are predicted by the loop's noise gain".

**Proposed N1'.** Suppose a soft sensor's laboratory or analyzer labels arrive theta calibrator
updates late.
- The natural single-state adaptive conformal recursion is then an integral loop with dead time
  theta. It is linearly stable only for gamma < 2 sin(pi / (4 theta + 2)).
- Process residuals are serially correlated. On them, the loop issues a material share of
  uninformative intervals at documented analyzer delays, while marginal coverage reads nominal.
- Step sizes tuned on history without the delay are anti-conservative. So is the model-based rule
  that assumes uncorrelated residuals.
- Tuning instead by replaying historical residuals through the delayed loop, capped by the
  stability limit, keeps the uninformative share within a stated budget out of sample.

| Ratified contribution | Under N1' |
|---|---|
| O1 dead-time loop and stability limit | Unchanged |
| O2 noise-gain model predicting sd(alpha) and the infinite share | The sd(alpha) model for uncorrelated residuals (within 1 to 19 % with a known score law, `h2_check.py`). The spectral form explains sd(alpha) for correlated residuals. The model's failure on the tail and on process residuals is reported as a result |
| O3 model-based design rule | Delay-aware replay tuning, capped at 0.8 gamma_crit(theta). The model-based rule stays as a reference arm |
| O4 marginal-coverage blindness | Unchanged. The primary metric becomes the uninformative share |
| I1-I3, E1-E2 | Unchanged, with every loop tuned by the same replay on the same data |

Positioning: Section 10 of `M1_NARROWING_PROPOSAL.md` still binds. The idea that gamma should
depend on the delay belongs to El Halabi and Brandt (2026, Fig. 18), who choose gamma per delay
empirically, in simulation, for the phase-interleaved recursion. N1' claims three things:
- the analysis of the single-state loop;
- evidence on process residuals that delay-blind tuning and the model-based rule are
  anti-conservative;
- a deployment procedure validated out of sample on process data.

## 5. Design

### 5.1 Debutanizer: real plant data, one stream

- **Point model** (D-P0.1): OLS of y_t on u5_{t-15}, fitted on the training split (rows 0-1674).
- **Calibration (tuning) segment**: the training residuals, in-sample. A two-parameter model on
  1660 rows has negligible optimism; this is stated as a limitation.
- **Evaluation stream**: validation plus test rows (1675-2393, 719 rows). The window is
  initialised with the last 200 training scores. Primary analysis has no burn-in; a sensitivity
  analysis excludes the first 100 rows.
- **Disclosure**: the lag of 15 was chosen on the raw training and validation data. No
  calibration-loop statistic of those rows has been computed.
- **Delays**: theta in {0, 1, 3, 7, 12}, with theta_doc = 3 or 7 set by the pre-check. If the file
  cannot settle it, theta_doc = 3 (the conservative value) and 7 is secondary.
- **Matched control**: the interval for y_t can be issued at update t - theta - 1 only if u5_{t-15}
  is known by then, which requires theta <= 14. Every theta in the grid meets this. One residual
  stream therefore serves every theta, so the delay comparison is a matched control.

### 5.2 TEP: simulated, replicated (D-P1.3, D-P1.4)

- **Generator**: `scripts/generate_tep_modes.py` is extended with three settings:
  - a seed: the random-number constant G set in `teprob.f` SUBROUTINE TEINIT, line 1187 at commit
    0643318 (the classic d00-d21 sets used the distinct values listed beside it);
  - a run duration;
  - a recording interval.
- **Runs**: 5 seeds x 300 h per regime (mode1 to mode3), recorded every 60 s.
- **Segments within a run**: hours 0-100 train the point model; 100-200 are the calibration
  segment; 200-300 are the evaluation segment.
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

- **gamma policies**:
  - fixed 0.005 (the default of Gibbs and Candes 2021);
  - fixed 0.05 (the repository default and the rejected manuscript's protocol);
  - delay-blind tuned;
  - delay-aware tuned;
  - `design_gamma(theta)`.
- **Tuning rule** (as in the pilot):
  - Search the grid 0.001, 0.0015, 0.002, 0.003, 0.005, 0.007, 0.01, 0.015, 0.02, 0.03, 0.05,
    0.07, 0.1 upward, capped at 0.8 gamma_crit(theta).
  - Select the largest value below the first value whose replayed uninformative share on the
    calibration segment exceeds eps.
  - If 0.001 already exceeds eps, the arm is reported as infeasible at this budget and evaluated
    at 0.001, flagged.
  - Delay-blind tuning replays at theta = 0; delay-aware tuning replays at the deployment theta.
- **Loops**: sequential is primary. The comparison loops are:
  - projected to [0.01, 0.5];
  - phase-interleaved tau-DACI;
  - the Smith variant;
  - decaying step sizes. These are implemented only after the schedule is verified in the body of
    Angelopoulos, Barber and Bates (2024); otherwise the loop is reported as not implemented.

  Every loop is tuned by the same delay-aware replay.
- **Pairing**: stored is primary. Arrival pairing at theta_doc is the negative control (R2.2,
  R4.8).

### 5.4 Metrics

- **Primary**: the uninformative share U, i.e. the share of issued intervals that are infinite or
  wider than the range of y on the calibration segment.
- **Also reported**:
  - the infinite share;
  - marginal coverage with the Wilson 95 % interval of the observed coverage;
  - rolling coverage (window 100): its sd and minimum;
  - the number of steps spent in under-coverage episodes (rolling coverage below 0.80);
  - sd(alpha) and the alpha range;
  - interval width: median, p90 and p99.

## 6. Endpoints, falsification and decision rules

**Primary cells**: the debutanizer at theta_doc, and TEP arm T1 at theta = 4 (pooled over regimes
and seeds). **Primary policy for F2**: delay-blind tuning, the practice it models. Every other cell
and policy, including gamma = 0.005 and 0.05, is descriptive and labelled so.

| ID | Fires if | Consequence |
|---|---|---|
| F2, existence | Neither primary cell shows an increase in U over the theta = 0 control on the same stream of at least 1 percentage point with a Bonferroni 97.5 % CI that excludes 0 | The process claim fails. Per the ratified rule, the paper becomes synthetic-only and the venue is re-planned. If only one cell shows the increase, the claim is restricted to that dataset and the paper says so |
| F3, blindness | In a primary cell where F2's criterion is met, 0.90 lies outside the Wilson 95 % interval of the observed marginal coverage. For TEP the interval uses counts pooled over the 15 runs. The Wilson interval assumes independence, so under autocorrelation it is narrower than the true one, which makes this test strict | The blindness claim is dropped |
| F5, remedy (new) | In TEP T1 at theta = 4, delay-aware tuning gives a mean U above eps = 1 % over the 15 runs, or a one-sided 95 % t upper bound (14 degrees of freedom) above 2 eps. The debutanizer cell is reported with its interval and is descriptive for F5 | The remedy claim narrows to whichever loop meets the budget, or to reporting only |
| F1, as ratified (now secondary) | The white model is off by more than 25 % in sd(alpha) or in the infinite share inside the design region | Reported. Section 3 predicts it fires at every persistence level, on the infinite share. It is no longer decisive once D-P1.1 is ratified |
| F4 | The systematic sweep finds the single-state dead-time analysis already published | As ratified |

## 7. Analysis plan

- **Debutanizer CIs**: circular block bootstrap of the per-step indicator sequences, with B = 2000.
  - The block length is the larger of 25 and the next integer above twice the IACT of the
    sequence (for differences, of the paired difference sequence). The IACT uses Sokal's
    automatic window with c = 5, as `phase1_precheck.iact` does.
  - Differences between theta arms use the same blocks for both arms.
  - If fewer than 8 blocks fit in the 719-row stream, the interval is reported as unreliable and
    that cell counts only as descriptive for F2.
- **TEP CIs**: the runs are independent replications. Report means and t-based intervals over the
  15 runs, with regime as a reported factor. Differences between arms are paired by run.
- **Matched controls**: within a dataset, every arm shares the point model and the residual stream.
  Each comparison varies one factor.
- **Power, before the freeze**:
  - debutanizer: simulate AR(1) residual streams of 719 rows, using the lag-1 autocorrelation the
    pre-check measures;
  - TEP: simulate the 15-run design at phi = 0.5 and phi = 0.9, from the pilot.
  - Report the probability that F2's primary test detects the effect at the delay-blind gamma, and
    the expected upper bound used by F5.

## 8. Pre-checks before the freeze (training split only)

Run `python scripts\phase1_precheck.py --json`. It writes
`docs/paper/evidence/phase1_precheck.json`. The validation and test rows are not read.

- **Debutanizer label hold**: the repeat share and run lengths of the label, against u5 as a
  continuously measured reference. They give the implied Ts and so theta_doc (Section 5.1).
- **Residual persistence of the D-P0.1 model**: autocorrelation and IACT, which feed the power
  analysis.
- **Open-loop miss persistence** at theta in {0, 3, 7}.
- **TEP label hold**: 5-row runs are expected at 3-min rows.

`tests/unit/test_phase1_precheck.py` (9 tests) checks the script on synthetic data with planted
structure:
- labels held at Ts = 6 and 12 min are recovered within 0.5 min;
- a label that changes at every sample is reported as not held;
- held runs are counted correctly;
- the IACT of AR(1) noise matches (1 + phi) / (1 - phi).

## 9. Decisions for ratification

| ID | Decision | Recommendation |
|---|---|---|
| D-P1.1 | Adopt N1' (Section 4) in place of the ratified model-prediction claim | Adopt |
| D-P1.2 | theta in the library convention (Section 2), the grids in 5.1 and 5.2, and theta_doc fixed by the pre-check | Adopt |
| D-P1.3 | Align TEP inputs at the analyzer's label age, not at the scanned lag | Adopt |
| D-P1.4 | Extend the TEP generator (seed, duration, 60-s recording): 5 seeds x 300 h x 3 regimes, run by Bien with gfortran under WSL | Adopt. If a 300-h run trips a shutdown limit, use the longest duration that does not, and record it here |
| D-P1.5 | eps = 1 %; U measured against the calibration-segment range of y; the primary cells and the single primary policy of Section 6 | Adopt |
| D-P1.6 | Debutanizer: tune on training residuals, evaluate on validation plus test (719 rows), with the 5.1 disclosure | Adopt |

Sequence:
1. Bien runs the pre-check. It reads only the training split, so its evidence may be committed
   before ratification, and it informs D-P1.1.
2. After ratification, the power analysis is computed and the freeze commit is made.
3. Implementation, each part with tests:
   - the U metric;
   - the replay tuner;
   - the paired block bootstrap;
   - the decaying-step loop, if its schedule is verified;
   - the generator extension;
   - the Phase 1 runner.
4. Bien runs TEP generation and the runner; the evidence JSON is frozen.
5. F-verdicts are recorded and the paper's shape is decided.

Estimate: two to three weeks of the six-to-ten-week budget.

## 10. Freeze record and deviations

Freeze commit: pending. Deviations after the freeze: none yet. Each deviation will be dated and
justified, and its effect on the F-verdicts stated.
