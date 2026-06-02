# Module 1 — Lessons Learned

Honest postmortem per phase. This document is for engineering credibility — what worked, what didn't, what would be done differently. Reviewers and interviewers reward this kind of honesty.

Each phase entry follows the structure:

- **What worked** — decisions that paid off
- **What didn't** — decisions that turned out wrong, dead ends, time sinks
- **What I would do differently** — with the benefit of hindsight
- **What this implies for downstream phases**

---

## Phase 1A — Hybrid Model on Debutanizer

*Status: complete (ADR-007).*

### What worked
- **Diagnosing the signal before modeling.** Finding the stable ~15-sample
  u5→C4 transport delay first meant the eventual model was anchored to real
  process structure, not fit blind.
- **Blocked forward-chaining CV over adjacent validation.** This is the single
  highest-value methodological choice in the phase — it exposed a covariate-shift
  failure (test 0.04) that train≈val (0.77/0.75) completely hid.
- **1-SE parsimony.** Selecting maximum parsimony recovered held-out R² = 0.52,
  13× the naive selection, and made the model interpretable.

### What didn't
- **Static single-tray physics at lag 0** — R² = 0.018. The bubble-point math was
  correct (verified against Perry's + Smith, 0% clipping); applying it statically
  to a dynamic process was the error. Correct physics, wrong framing.
- **The 126-feature lagged kitchen-sink PLS** — looked healthy (train ≈ val) and
  scored test 0.04. A textbook reminder that "train ≈ val" is not evidence of
  generalization when val is temporally adjacent.

### What I would do differently
- Lead every soft-sensor effort with lag/signal diagnosis before fitting anything.
- Never trust a temporally-adjacent validation split for a cross-regime claim —
  reach for blocked CV from the first experiment, not after the naive model
  flatters itself.

### Implications for downstream phases
- The negative CV folds (calibration drift: stable correlation, drifting
  slope/intercept) are the exact problem Phase 1B solves with an online
  bias-update — 1A produced the diagnosis that scoped 1B.
- **Architecture pivot:** the as-built model is a dynamic physics-*anchored*
  linear model, not ADR-001's PINN/residual hybrid. ADR-001 anticipated a
  graceful fallback to a standard learner; the empirical findings pushed past
  even that to a physics-feature-anchored linear model. ADR-007 supersedes
  ADR-001; the PINN (Path A) remains private future work, not externally promised.

---

## Phase 1B — Drift Detection & Adaptive Bias-Update

*Status: complete (ADR-008).*

### What worked
- **Residual-based detection on the same CV backbone** (`blocked_cv_residuals`
  pinned to `blocked_cv_r2` by an equivalence test) — one source of truth for the
  fold mechanics, no divergence risk.
- **Shardt open-loop bias-update (feedforward EWMA).** Stable for any λ, one knob,
  faithful to the verified primary. Turned worst fold −1.49 → +0.49 and cut
  cross-regime SE 9.1×.
- **Benchmarking the targeted fix against the literature standard.** Building JITL
  (Cheng & Chiu 2004) as a fair baseline turned a substitution we would have had
  to *defend* into a result we can *claim*: the O(1) bias-update dominates O(N)
  JITL on calibration-drift data.
- **Verify-before-load-bearing.** Every algorithm (ADWIN, Page-Hinkley, CUSUM,
  the bias-update form, θ) was checked against a primary source before it carried
  weight — including a CUSUM ARL₀ validation against the textbook (169.5 vs 168).

### What didn't
- **Page-Hinkley / CUSUM scaled to a single reference σ** over-fire on the
  heteroscedastic residual (later folds run 3× the σ of fold 0). They stayed
  comparators, not the primary.
- **ADWIN as a trigger** — latency ~260 samples on a gradual shift, too slow to be
  the correction. Relegated to a supervisory regime-change flag.
- **Trying to derive θ from the data** (cross-correlation method 3) — inconclusive
  by design: the dataset is "data rich, information poor." Logged as a negative
  result rather than buried.
- **JITL (LWR) is dimension-fragile.** On the raw 112-feature lagged set its
  Euclidean similarity collapsed (curse of dimensionality) and it scored R² ≈ −8;
  it worked only on the low-dim physics-anchored features. The bias-update has no
  such dependence.
- **Detector-gated adaptation was too slow here.** ADWIN-gated JITL ≈ static
  (latency ~260 fires after the catastrophic fold's damage is done) — empirical
  proof that continuous adaptation, not a drift trigger, is what closes Gap 2 on
  this process.

### What I would do differently
- Set detector scale from a robust/per-regime σ from the start, not a single
  reference window.
- Treat θ as a sourced physical constant from the outset, not a tunable — the
  θ-sweep is a sensitivity check, never an optimization target.

### Implications for downstream phases
- **Correction mechanism diverged from plan:** the spec planned JITL retraining;
  the as-built correction is the Shardt bias-update (more principled for a
  calibration-drift failure mode). ADR-008 supersedes the JITL line in the spec.
- **Closed-loop integrator** (Shardt Eq. 6/10, exact tracking) is deferred to
  Module 3 — needed only if the sensor drives control.
- **θ is a load-bearing assumption** (=4, benchmark convention); re-pin on any
  real column with a known analyzer cycle.
- **Conformal uncertainty (MAPIE) is still owed** — planned in the 1A scorecard,
  not yet built. Candidate for 1D or a 1A/1B addendum before 1F writing.

---

## Phase 1C — Cross-Process Transfer

*Status: not started*

---

## Phase 1D — Production-Ready Deployment Stack

*Status: not started*

---

## Phase 1E — SECOM Stress Test

*Status: not started*

---

## Phase 1F — Writing & Submission

*Status: not started*
