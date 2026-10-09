# M1 narrowing proposal (N1): the delayed-label calibration loop

Status: RATIFIED 2026-09-28 by Bien Busico, with D-P0.1 (obey the one-SE rule, k = 1).
Phase 0 started the same day (Section 10) and closed 2026-10-09 (Section 11). An amendment to the
claim is proposed in `PHASE1_PREREGISTRATION.md` and is not ratified; until it is, Sections 3 to 6
stand as ratified. Inputs: `docs/reviews/REVIEW_REGISTER.csv` (42 records), `M1_REVISION_AUDIT.md`
(A1-A12), a literature check, and three falsification-first pilots
(`scripts/pilots/`, synthetic data, reproducible).

## 1. Why the previous manuscript failed (from the register)

- Identification: the physics attribution rested on a cross-dataset contrast (A12).
- Claim-evidence gap: the delayed-label pairing was asserted, never exercised (A2).
- Methods did not match code (A3); the stated selection rule did not produce the selected
  model (A1); data-dependent choices touched the test period (A9).
- Diluted novelty: five contributions, mostly existing methods (R3.2, R2.8b).

The lesson is structural: one falsifiable claim, tested by matched controls on one
process, beats five claims tested by contrast across datasets.

## 2. What changed in the literature (checked 2026-09-28)

El Halabi and Brandt, arXiv 2609.07251 (7 Sep 2026), "Adaptive Conformal Inference Under
Delayed Feedback." Verified contents: a tau-delayed ACI recursion in which each level is
updated from the level used tau steps earlier, alpha_{t+tau} = alpha_t + gamma(alpha - err_t),
decomposed into tau interleaved ACI chains; a finite-sample long-run coverage bound; an
approximate marginal bound; a delay-to-memory ratio r = tau/L; simulated residual processes
(AR, GARCH, Markov switching); a queue of issued (set, level) pairs in Algorithm 2.

Consequences for M1:
1. A delayed-ACI coverage theorem is no longer available to us as a novelty claim.
2. Stored-interval pairing is implicit in their Algorithm 2; it cannot be our headline.
3. Their recursion is phase-interleaved and therefore free of dead-time feedback. The
   single-state recursion a practitioner builds, and that `serving/service.py` implements,
   alpha_{s+1} = alpha_s + gamma(alpha* - err_{s-theta}), is a different dynamical system:
   an integral loop with dead time. They do not analyse it.
4. Their related-work section states that control-theoretic ACI formulations (conformal PID
   and others) do not focus on delayed feedback. A search for Smith-predictor or dead-time
   compensation combined with conformal calibration returned only classical control work.

Caveat: three targeted searches, not a systematic review. A Scopus, Web of Science and
Google Scholar sweep is the first task of Phase 1 and can falsify the novelty (F4).

## 3. The N1 claim

In a soft sensor whose laboratory labels arrive theta samples late, the natural single-state
implementation of adaptive conformal calibration is a stochastically driven integral loop
with dead time. Its interval volatility and its fraction of unusable (infinite) intervals are
predicted by the loop's noise gain and rise continuously with gamma toward the linear
stability limit gamma_crit(theta) = 2 sin(pi / (4 theta + 2)), while marginal coverage stays
at nominal and cannot detect the degradation.

## 4. Pilot evidence (synthetic, alpha* = 0.10, 20 seeds unless noted)

Stationary, sliding-window quantile (R = 200), delayed score arrival, theta = 60,
gamma_crit = 0.0260:

| loop | gamma | marginal cov. | sd(alpha) | infinite intervals | min local cov. |
|---|---|---|---|---|---|
| sequential | 0.005 | 0.900 | 0.017 | 0.0 % | 0.76 |
| sequential | 0.050 | 0.900 | 0.334 | 55.2 % | 0.59 |
| phase-interleaved (El Halabi & Brandt) | 0.050 | 0.900 | 0.048 | 1.1 % | 0.78 |
| Smith-predictor variant | 0.050 | 0.900 | 0.055 | 5.3 % | 0.75 |

Marginal coverage reads 0.900 in every row, including the row where more than half of all
issued intervals are the entire real line.

Onset (exact score law, 10 seeds): degradation rises continuously, not at a threshold.
At 0.8 gamma_crit the infinite-interval fraction is already 8.7 % (theta = 60) and 20.8 %
(theta = 20).

Linear stochastic model (impulse-response noise gain, var(eta) = alpha*(1 - alpha*)):

| theta | gamma / gamma_crit | sd(alpha) predicted | measured | error | inf. predicted | measured |
|---|---|---|---|---|---|---|
| 20 | 0.50 | 0.065 | 0.064 | +1 % | 6.1 % | 6.7 % |
| 20 | 0.80 | 0.132 | 0.111 | +19 % | 22.4 % | 20.8 % |
| 60 | 0.50 | 0.038 | 0.037 | +1 % | 0.4 % | 0.5 % |
| 60 | 0.80 | 0.077 | 0.068 | +13 % | 9.7 % | 8.7 % |
| 60 | 0.95 | 0.168 | 0.091 | +85 % | 27.6 % | 16.8 % |

The model is accurate in the design region (<= 0.8 gamma_crit) and fails near the boundary,
where saturation caps alpha. Design rule, computed by `delayed_aci.design_gamma` (the source
of truth; a coarser pilot grid gave 0.030 at theta = 4): the largest gamma with predicted
infinite share <= 1 % is 0.0347 (theta = 4), 0.0244 (20), 0.0146 (60), 0.0093 (120) and
0.0052 (240, capped at 0.8 gamma_crit because the unconstrained 1 % value lies outside the
validated region). The repository default gamma = 0.05 violates the rule at every delay tested.

Recovery after a residual-scale step (1 to 3, theta = 60):

| loop | gamma | coverage, first 1000 | steps to 0.85 | infinite, first 3000 |
|---|---|---|---|---|
| sequential, tuned | 0.02 | 0.901 +/- 0.005 | 17 +/- 10 | 21.2 % |
| phase-interleaved | 0.05 | 0.877 +/- 0.007 | 78 +/- 12 | 2.7 % |
| Smith-predictor variant | 0.05 | 0.900 +/- 0.003 | 12 +/- 7 | 14.0 % |

What the pilots refuted: (a) a sharp stability threshold; (b) dominance of the
Smith-predictor variant, which trades transient efficiency for speed. What they
confirmed: (c) marginal-coverage blindness; (d) a predictive linear stochastic model in
the design region; (e) slower drift recovery of phase-interleaving.

Confound caught during piloting: a first drift pilot held the quantile at nominal scale,
which manufactured infinite intervals for every method after the step. It was rerun with
the sliding-window quantile the repository actually uses; only the rerun is reported.

## 5. Paper specification under N1

Working titles, to be finalised after Phase 1:
- "Laboratory delay turns adaptive conformal calibration into a dead-time loop: noise-gain
  analysis and a design rule for soft sensors"
- "Why marginal coverage hides failure in delayed-label conformal soft sensors"

Contributions, separated as R2.8b requires:
- Original analysis. O1: the single-state delayed recursion as an integral loop with dead
  time, with its linear stability limit. O2: a stochastic noise-gain model predicting
  sd(alpha) and the infinite-interval fraction. O3: a design rule gamma_eps(theta).
- Original evaluation insight. O4: marginal coverage is blind to the degradation; report the
  infinite-interval fraction, local coverage dispersion, and the alpha spectrum.
- Integration and comparison. I1: remedies compared on equal footing (design-rule
  sequential, phase-interleaved, Smith variant). I2: pairing correctness as a matched
  negative control (immediate, delayed-stored, delayed-arrival; R2.2, R4.8). I3: the
  open-loop bias update of Shardt and Yang (2016), driven by the raw residual and
  unconditionally stable under delay, contrasted with the closed-loop ACI (R2.m4).
- Results. E1: synthetic with known ground truth. E2: debutanizer (passive industrial data)
  and TEP regimes with laboratory delays spanning realistic values, with linear and
  nonlinear point models to show the loop result does not depend on estimator class
  (R1.1, R1.4).

Removed from this manuscript, with reasons logged in the register: SECOM, model migration,
physics-attribution claims, the selection-lottery contribution (selection moves to methods).

Every comparison is a matched control: same process, target, estimator and split, one
factor varied.

## 6. Falsification conditions

- F1: on debutanizer or TEP residuals at realistic theta, measured sd(alpha) or infinite
  fraction deviates from the linear-model prediction by more than 25 % inside the design
  region.
- F2: the degradation does not appear at realistic (theta, gamma) on process data.
- F3: marginal coverage does detect the degradation (outside its binomial interval).
- F4: the systematic sweep finds the single-state dead-time analysis already published.

If F1 to F3 fire, the result is synthetic-only and the paper changes shape and venue. If F4
fires, the contribution narrows to the process validation and the design rule.

## 7. Phase-0 decisions needed with this ratification

- D-P0.1 (A1, R4.3). Recommended: obey the stated one-SE rule, which selects the
  single-feature model (u5 at the transport lag, k = 1). This answers R4.3 by following
  the rule and removes the assumption-laden physics features from the load-bearing path.
  Cost: point-model test R^2 of +0.395 instead of +0.476, immaterial to N1 because the
  claim concerns the calibration loop, not point accuracy.
- D-P0.2 (R2.6a, R4.6). Consequence of D-P0.1: physics features leave the paper's core.
  They stay in the repository with their assumptions documented: tray-6 temperature
  100 to 112 C, column pressure 4.5 to 5.5 bar, n-hexane heavy proxy, bubble-point
  estimate clipped to [0, 1].

Leakage fixes apply regardless: TEP transport lag diagnosed on the training split only;
debutanizer lag re-derived on the training pool with its provenance committed.

## 8. Venue (provisional; decided in Phase 5 after the claim survives process data)

Topical fit, general knowledge pending verification:
- Journal of Process Control: dead time, soft sensors, laboratory delay; the literature
  lineage this work builds on. It rejected the predecessor, so submitting there requires
  full disclosure and the editor's acceptance of the paper as new work.
- Control Engineering Practice: applied control, dead-time compensation, soft sensing;
  independent editorial board.
- ISA Transactions: dense dead-time-compensation literature; process automation.

Acceptance rates will be taken from each journal's own published metrics, not from
aggregator sites. The objective is the highest acceptance probability subject to two
constraints the charter imposes: Q1 indexing and genuine topical fit. Optimising for
acceptance rate alone would push toward less selective venues a PhD committee discounts.

## 9. Limitations of this proposal

- Pilots are synthetic, one drift type (scale step), one target level (alpha* = 0.10).
- The noise-gain model assumes E[err | alpha] = alpha, exact only for a known score law;
  Phase 1 tests it with estimated quantiles on process data.
- Race risk: the arXiv authors could publish a single-state follow-up. Mitigation is pace
  without shortcuts, and a preprint as soon as Phase 1 evidence is frozen.

## 10. Ratification record and positioning constraints (2026-09-28)

Ratified: N1 as M1's single claim; D-P0.1 (point model = the one-SE selection, k = 1,
u5 at the transport lag); D-P0.2 (physics features leave the core, assumptions documented).

Positioning constraints from `LITERATURE_SWEEP_N1.md` (the claim must respect all four):
- Do not claim that large gamma makes the level oscillate: Gibbs and Candes (2021, S2.1)
  state it qualitatively and chose gamma = 0.005 empirically.
- Do not claim the concept that gamma should depend on delay: El Halabi and Brandt (2026,
  Fig. 18) select gamma* per delay empirically, for the phase-interleaved recursion. Ours is
  the analytical noise-gain rule for the single-state recursion, with a prediction of the
  infinite-interval share.
- Required baselines: projected ACI (level clipped to a band, as used with delayed feedback in
  arXiv 2607.05882), decaying step sizes (Angelopoulos, Barber and Bates 2024), phase-interleaved
  tau-DACI, plus the design-rule and Smith variants.
- Pilot correction: the phase-interleaved pilot updated the level one step before its label
  arrived (one step less delay; 1.7 % at theta = 60, favouring that method). The library uses
  period theta + 1; all Phase 1 numbers come from the library, not the pilots.

Phase 0 deliverables (code-ready, validated on synthetic data, 11 tests passing):
`evaluation/delayed_aci.py` (loops, event-queue pairing, noise-gain model, design rule,
diagnostics), TEP lag diagnosed on the training split in `scripts/conformal_eval.py`, and
`scripts/diagnose_debutanizer_lag.py` (pool-only lag provenance). Real-data runs are
owner-side; their outputs are frozen as evidence before any Phase 1 number is reported.

## 11. Phase 0 results (closed 2026-10-09)

Evidence was produced owner-side on Windows (Python 3.11.15) and pushed in 1791362 and 56d0a0a.

- Debutanizer lag (A9, R4.5): scanned on the train + validation pool only (n = 2034; the
  360-row test block was not read). |r| peaks at lag 15 (r = -0.724, r^2 = 0.524), an interior
  maximum on a flat plateau (r^2 >= 0.500 for lags 13 to 17). The sign is physical: a hotter
  sixth tray means less C4 in the bottoms. Evidence: `docs/paper/evidence/debutanizer_lag_scan.json`.
- TEP lag (A9, R4.5): the training-split lag equals the full-file lag in all three regimes
  (0, 0, 0), so the leak changed no reported number. The printed result is committed as
  `docs/paper/evidence/tep_lag_compare.json`, and R4.5 closes with that file. Lag 0 is a
  boundary result from one driver, XMEAS_3, the E-feed flow, which the control system
  manipulates. It says the scan found no transport delay; it does not show that none exists.
  Phase 1 aligns TEP by the analyzer's documented dead time instead (product analysis sampled
  every 0.25 h with 0.25 h dead time; Downs and Vogel 1993, Table 5).
- Library: the 11 tests in `tests/unit/test_delayed_aci.py` pass on Windows and Linux.
- Delay provenance (R4.7). Fortuna et al. (2007, Sec. 6.2, p. 117): the GC has a 15-min
  measuring cycle and an estimated 30-min location delay, so C4 is known about 45 min late. With
  Ts = 12 min their newest label is y(k-4), 48 min old. The previous manuscript's delay of 4 (its
  bias-update code used the label 4 samples old) is therefore the documented latency at
  Ts = 12 min, not only a NARMA convention. In the dead-time convention of `delayed_aci`
  (theta = label age - 1) it is theta = 3.
- Recording interval. The same book describes a debutanizer set with ten candidate inputs
  recorded at Ts = 6 min (Sec. 4.1; Table 4.1 counts out of 2394). It also gives a delay range of
  20 to 60 min (Sec. 5.5, p. 97). At 6 min the 45-min delay is a label age of 8 (theta = 7). The
  public file has 2394 rows and the seven inputs of Table A.1, which Sec. 6.2 models at 12 min. The
  book does not say whether it is the Sec. 4.1 recording; `scripts/phase1_precheck.py` tests which
  Ts the file supports.
- Code-ready items: R2.2, R2.3, R2.4, R2.m1, R3.3 and R4.8 (`evaluation/delayed_aci.py`).
  R4.4 and R2.6b: the code is forward-chaining (`evaluation/blocked_cv.py`), so what remains is
  the Methods text (Phase 4).

Pre-data finding that changes Phase 1 (`scripts/pilots/persistence_pilot.py`, synthetic,
library-generated; theta here is the library's theta).
- On AR(1) residual streams with lag-1 autocorrelation 0.9 or more, the white-noise noise-gain
  model of Section 4 under-predicts sd(alpha) by 38 to 76 %.
- At that persistence, in every cell where the measured infinite-interval share exceeds 0.1 %,
  the model under-predicts the share, by factors of 1.9 to more than 200.
- With the sliding-window quantile, its infinite-share predictions miss by more than 25 % in some
  cells at every persistence level tested, including uncorrelated residuals. F1 as specified would
  therefore fire.
- Under persistence the delay does more harm, not less. At gamma = 0.02 and autocorrelation 0.9,
  the infinite share is 0.7 % with no delay, 8.4 % at theta = 4 and 14.9 % at theta = 8.
- Marginal coverage reads 0.900 to 0.901 in every cell.

The amendment proposed in response, and the Phase 1 design, are in `PHASE1_PREREGISTRATION.md`.
