# M1 revision audit and plan (JPROCONT-D-26-00618, rejected; decision date TBC from EM header)

Four reviewers, three recommending rejection. Reviewer 1 called the core idea novel and
recommended major revision. This document records what was verified against the code,
what must change, and the order of work. It is the working plan for the revision.

Audit rule: every allegation gets a verdict backed by file contents, never inference.
Where the code could not be reached remotely, the verdict is NOT VERIFIED and the check
is assigned to a local session.

---

## Part 1. Audit findings

| ID | Allegation (reviewer) | Verdict | Evidence | Severity |
|---|---|---|---|---|
| A1 | One-SE rule selects k=1, not the deployed k=4 (R4.3) | **CONFIRMED** | `one_se_selection` in `evaluation/blocked_cv.py` returns the simplest complexity whose mean >= best - SE. With best = +0.145 +/- 0.419, threshold = -0.274; `u5`-only (+0.034, k=1) qualifies. | CRITICAL |
| A2 | Delayed labels are not simulated in the conformal layer (R4.8, R2.2) | **CONFIRMED** | `ACIConformal.run` calls `self.update(y_pred[t], y_true[t])` inside the same loop iteration that issues the interval. `conformal_eval.py` passes `theta` only to `apply_bias_update`, never to the ACI object. | CRITICAL |
| A3 | Paper's CV protocol is not the implemented one (R4.4) | **CONFIRMED** | `blocked_cv_r2` uses `sklearn TimeSeriesSplit(n_splits)` (forward-chaining, expanding window, no `gap` argument). Paper S3.2 describes leave-one-contiguous-block-out with an explicit `l`-sample gap. Different protocols. | CRITICAL |
| A4 | theta=4 is not a "documented analyzer delay" (R4.7) | **CONFIRMED** | `evaluation/bias_update.py` docstring: the true plant delay was "great and unknown", so 4 is "the benchmark convention" from the Fortuna NARMA structure. | MAJOR |
| A5 | "Regime-uniform" coverage is not statistically supported (R2.4) | **CONFIRMED** | Binomial SE at p=0.90, n=300 is 0.0173. The reported 0.897-0.903 spread is 0.35 SE. Distinguishing a 0.006 coverage difference at 95% would need ~19,200 samples per regime. | MAJOR |
| A6 | gamma inconsistency, 0.05 in protocol vs 0.001 in Figure 6 (R2.minor1) | **CONFIRMED** | `conformal_eval.py` defaults `--gamma 0.05`; the synthetic F6 run used 0.001. | MINOR |
| A7 | Unclipped alpha_t may produce degenerate intervals (R2.3) | **NOT A BUG; REPORTING GAP** | `conformal_quantile` documents and implements the conformal convention: level >= 1 returns +inf (whole line), level <= 0 returns 0.0 (point). Behaviour is defined and correct. The paper simply never reports alpha_t range, degenerate-interval counts, or the width distribution. | MODERATE |
| A8 | Serving layer mis-pairs delayed labels | **REFUTED; IMPLEMENTATION IS CORRECT** | `serving/service.py` stores `sample_id -> (raw, corrected, lower, upper)` and on `label()` pops the stored tuple, stepping ACI against the interval actually emitted for that sample. Its docstring notes that `ACIConformal.update` assumes immediate feedback, which is why the service does the pairing itself. | NO FIX NEEDED |
| A9 | Leakage: transport lag diagnosed on the full target; SECOM target chosen using full data (R4.5, R2.5) | **NOT VERIFIED** | Feature/lag modules not reachable at probed paths; GitHub API rate-limited during audit. Must be checked locally. | UNKNOWN, potentially CRITICAL |
| A10 | S4.2 cites C6, C7, C8 but only C1-C5 exist (R2.minor2) | **CONFIRMED** | Introduced during the K-to-C contribution renumbering. | MINOR |
| A11 | Table 4 mixes a test metric with a CV metric (R2.minor3) | **CONFIRMED** | The cell reads "+0.31 -> CV +0.45", comparing quantities that are not comparable. | MINOR |
| A12 | Negative control is confounded; physics attribution not identified (R1.1, R2.1, R4.1) | **CONFIRMED, SCIENTIFICALLY DECISIVE** | SECOM differs from the debutanizer in process, target, dimensionality, missingness, temporal structure and estimator simultaneously. R2 is additionally right that anonymised sensor data is not physics-free: unknown variable meaning does not remove underlying physical relationships. | CRITICAL |

### What A2 and A8 mean together

The delayed-label correctness property is **correctly implemented in the serving path
and never exercised by the evaluation that produced Table 3.** The claim is true of the
software and unsupported by the experiment. This is the cleanest possible version of a
claim-evidence gap: the fix is to route the evaluation through the mechanism that
already exists, then measure what the incorrect pairing costs.

### Accountability

A1, A3, A5, A10 and A11 originate in work done during manuscript preparation, and A12 in
a framing decision taken on my recommendation. Specifically: S3.2's formal CV definition
was written without reading `blocked_cv.py`, so the methods section describes a protocol
the study did not run; the one-SE rule was stated as governing feature-set choice without
checking it against Table 1; and the negative control was promoted to the lead
contribution without testing whether the causal attribution was identified. Recorded here
so the process failure is fixed alongside the paper.

---

## Part 2. What the reviewers got right that improves the science

Two criticisms point at a better paper rather than a smaller one.

**The matched ablation (R2.1, R4.1).** Keep the process, target, estimator and split
fixed; vary only the physics information. Correct features, shuffled features,
misspecified features, features removed. If accuracy degrades monotonically while
coverage holds, the attribution is *identified* rather than illustrated. This is the
experiment the paper's thesis always required.

**The three-way delay comparison (R2.2).** Compare (a) immediate feedback, (b) delayed
feedback scored against the stored interval, (c) delayed feedback scored against the
arrival-time interval. This converts an asserted correctness property into a measured
result, and (c) quantifies the error the paper warns about.

Together these replace a confounded cross-dataset contrast with two controlled
experiments on the same process. SECOM survives as an external-validity case, not as the
load-bearing control.

---

## Part 3. Revision plan

Sequencing rule: nothing is written until the evidence it describes exists and is frozen.
Phases 0 and 1 gate everything else because they can invalidate existing numbers.

### Phase 0. Integrity audit (local, blocking, ~3 days)

1. Resolve A9. Trace the transport-lag diagnosis and the SECOM target selection. Confirm
   whether either touches data outside the training partition. If yes, move both inside a
   nested procedure and mark every affected number for regeneration.
2. Reconcile A1. Decide and document: either deploy k=1 per the stated rule, or restrict
   the one-SE rule to regularization paths and state the actual feature-set criterion.
   The honest finding, that the CV spread at this sample size cannot separate the feature
   sets, is itself reportable and consistent with A5.
3. Reconcile A3. The implemented forward-chaining protocol is the more defensible one and
   is what R2.6 asked for. Rewrite S3.2 to describe `TimeSeriesSplit` exactly, including
   how leakage safety is achieved (per-segment feature construction) rather than by an
   `l`-gap.
4. Correct A4, A6, A10, A11 in the manuscript.
5. Freeze: `evidence/audit_phase0.json` recording every decision and every number that
   must be regenerated.

### Phase 1. The matched negative control (~2 weeks)

Debutanizer, one target, one estimator family, one split. Arms:
- full physics features (reference)
- physics features with values shuffled across time (destroys the physical relation,
  preserves marginal distribution and dimensionality)
- misspecified physics (wrong component proxy, wrong pressure assumption)
- physics removed, raw lags only at matched dimensionality
- optional: same arms with a nonlinear estimator, answering R1.1

Report for each arm: point accuracy, coverage, and full width distribution. Replicate
across seeds with confidence intervals. The claim stands or falls here.

### Phase 2. Delayed-label isolation (~1 week)

Build an event-queue harness that drives the existing `serving/service.py` path, then run
the three-way comparison from R2.2 at several delays, including variable and missing
labels. Report coverage and width for each. Add the timeline figure R2 requested.

### Phase 3. Statistical hardening (~1 week)

Binomial confidence intervals on every coverage number. Full width distributions
(median, percentiles, maximum) alongside every mean. alpha_t trajectory, range, and
counts of infinite or degenerate intervals. Bias-correction versus ACI ablation
(raw/corrected x split/ACI, four cells). Migration: finer fraction grid, more repeats,
confidence intervals on the efficiency ratio, and the Bayesian-versus-conformal
interpretation distinction R2.7 demands.

### Phase 4. Reproducibility and rewriting (~2 weeks)

Physics feature equations, denormalisation, units, thermodynamic assumptions, and the
n-hexane proxy justification (R2.6, R4.6). Migration specified to reproduction standard
(R2.7). Number every equation. Separate methodology from case-study values in S3 (R3).
Rewrite C1-C5 concisely, separating original developments from integration and results
(R2.8). Distinguish static from prequential online evaluation everywhere (R2.6, R4.10).

### Phase 5. Venue and resubmission (~1 week)

Target selection under THESIS_STANDARDS S5 and S6. JPC is closed for this manuscript.
The strengthened paper, with an identified causal claim and a measured delay result, is a
stronger submission than the version that was rejected. Candidates to evaluate against
scope and last two issues: Control Engineering Practice, ISA Transactions, Chemical
Engineering Science, Engineering Applications of Artificial Intelligence.

---

## Part 4. Standing decisions

- The manuscript is under review nowhere. It may not be submitted until the revision is
  complete (THESIS_STANDARDS S6.1).
- No prose is written for a result that does not yet exist as frozen evidence.
- Every reviewer comment gets a written disposition (accepted and fixed, accepted and
  deferred with reason, or rebutted with evidence) before resubmission.
- The four reviews are archived verbatim in `docs/module1/reviews/JPROCONT-D-26-00618/`.

---
*Audit performed against commit state on `main` (2026). Findings A1-A8, A10-A12
verified against file contents; A9 outstanding and assigned to Phase 0.*


---

## Addendum 2026-09-28: A9 resolved, and the plan superseded by N1

**A9 verdict: CONFIRMED on both halves, plus two provenance findings.**
- TEP: `scripts/conformal_eval.py` loads the full regime file, calls
  `diagnose_transport_lag(df)` (argmax |corr(XMEAS_3, y)|, lags 0-40) on train, validation
  and test together, and only then calls `time_ordered_split(df)`. Leakage.
- SECOM: `select_vm_target(df)` ranks |point-biserial r| against the fail label over all
  1,567 rows, test period included. The docstring defends it as problem definition; the
  test-period labels are nonetheless consulted.
- Debutanizer: lag 15 is a hard-coded default in `physics_features.py`; no scan exists in
  `src/`. Provenance not reproducible from the repository.
- Physics features rest on assumed ranges in `physics_bridge/bridge.py`: tray-6
  temperature 100-112 C, column pressure 4.5-5.5 bar; n-hexane heavy proxy; bubble-point
  estimate clipped to [0, 1]. Nominal assumptions, not dataset facts (R2.6a, R4.6).

**Plan status.** The phased plan in Part 3 is superseded by `M1_NARROWING_PROPOSAL.md`
(N1) once ratified. Phase 0 integrity fixes carry over unchanged. SECOM, migration and the
physics-attribution claim leave the manuscript; every reviewer comment keeps a disposition
in `docs/reviews/REVIEW_REGISTER.csv`.
