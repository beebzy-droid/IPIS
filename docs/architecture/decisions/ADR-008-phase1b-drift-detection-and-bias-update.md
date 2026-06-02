# ADR-008 — Phase 1B: residual drift detection and Shardt open-loop bias-update

- **Status:** Accepted
- **Date:** 2026-06-02
- **Supersedes/extends:** ADR-007 (physics-anchored model selection)
- **Module:** 1 (soft sensor) — Debutanizer C4 (Fortuna et al. benchmark)

> Numbers in this ADR are from the project's blocked (forward-chaining)
> time-series CV on the train+val pool (5 folds, leakage-safe per-fold lagging,
> train-only scaling) plus a single held-out test regime. The `static` baseline
> reproduces ADR-007 exactly (CV +0.145 ± 0.419, worst fold −1.49), which is the
> harness self-check.

## Context

ADR-007 selected a physics-anchored linear model. Phase 1A diagnosis established
the failure mode is **calibration drift, not delay drift and not signal loss**:
the u5(t−15)→y correlation is stable across every regime (block r² 0.50–0.74),
yet a model fit on one regime is biased on the next. The blocked-CV residual
means per fold are −0.023 / −0.089 / −0.013 / −0.029 / −0.044; fold 1 is
bias-dominated and scores R² = −1.49. The cross-regime CV SE (0.419) — not the
mean — is what makes the static model undeployable: worst-case behaviour is a
catastrophe.

Two delays are involved and must not be conflated:
- **Transport lag ≈ 15 samples** — the u5→y process-dynamics lag (Phase 1A best
  predictive lag). Lives in the *features*.
- **Label/analyzer delay θ** — how stale the freshest C4 lab value is. Lives in
  the *bias update*. Pinned to **θ = 4** from the benchmark: Fortuna et al.
  (2005/2007) report the C4 gas-chromatograph delay as 4 output lags in their
  NARMA model; the true plant delay was documented as "great and unknown", so 4
  is the benchmark convention.

## Decision

A two-part chain on the physics-anchored model:

1. **Detection (trigger) — residual change detection.** Monitor the signed
   prediction residual with **ADWIN** (Bifet & Gavaldà 2007) as primary
   (single parameter δ=0.002, distribution-free FP/FN bounds, auto time-scale),
   with **Page-Hinkley** and an in-house **CUSUM** (Page 1954; ARL₀-validated
   vs Montgomery) as comparators. Implemented in `evaluation/drift.py`,
   evaluated on the same blocked-CV backbone (`blocked_cv_residuals`, pinned to
   `blocked_cv_r2` by an equivalence test).

2. **Correction — Shardt open-loop bias-update.** Verified against the primary
   (Shardt & Yang 2016): a soft sensor is a process model plus a bias-update
   term that corrects absolute bias from delayed labels. We are **open-loop**
   (the sensor estimates C4, does not drive control), and Shardt's open-loop
   conclusion is to use the most recent available value. Form:

   ```
   b_t = (1-λ)·b_{t-1} + λ·(y_{t-θ} − ŷ_{t-θ});   corrected = ŷ_t + b_t
   ```

   - λ=1 = most-recent-residual (Shardt open-loop optimum).
   - Feedforward on the raw residual → unconditionally stable for any λ∈(0,1].
   - λ selected by CV mean (test untouched). θ = 4.
   - Implemented in `evaluation/bias_update.py`.

## Results

**Headline (θ=4, CV-selected λ=0.1):**

| metric | static (ADR-007) | corrected | change |
|---|---|---|---|
| CV mean R² | +0.145 | **+0.648** | +0.50 |
| **CV SE** | 0.419 | **0.046** | **9.1× tighter** |
| worst fold R² | −1.49 | **+0.487** | catastrophe removed |
| held-out test R² | +0.476 | **+0.857** | +0.38 |

The corrected CV (+0.648) **exceeds the best-constant-offset oracle** (+0.540),
because the update tracks within-fold drift, not only a flat offset. The SE
collapse (0.419 → 0.046) is the operative result: it turns "competitive mean R²
with large cross-regime variance" into "strictly dominant on worst-case
robustness."

**θ-sensitivity (robustness to the analyzer-delay assumption):**

| θ | corrected CV | CV-λ | held-out test |
|---|---|---|---|
| 2 | +0.707 ± 0.044 | 1.0 | +0.956 |
| **4 (sourced)** | **+0.648 ± 0.046** | 0.1 | **+0.857** |
| 8 | +0.599 ± 0.060 | 0.1 | +0.817 |

Monotonic decay with staleness, all solidly positive, SE 7–9× tighter across the
bracket. The λ–θ coupling is physically coherent (fresh labels → λ=1; stale →
λ=0.1). θ=4 is adopted because the benchmark sources it, not because it scores
best (θ=2 does).

**Head-to-head vs the literature-standard adaptive layer (JITL).** JITL
(Cheng & Chiu 2004) — locally-weighted linear regression, the canonical adaptive
soft sensor — was benchmarked on the same blocked-CV folds, same physics-anchored
features, same causal θ=4 constraint. The bias-update dominates on every axis at
zero local model fits:

| mechanism | CV mean | CV SE | worst fold | held-out test | local fits |
|---|---|---|---|---|---|
| static (ADR-007) | +0.145 | 0.419 | −1.49 | +0.476 | 0 |
| **Shardt bias-update (λ=0.1)** | **+0.648** | **0.046** | **+0.487** | **+0.857** | **0** |
| JITL always-on (h=2) | +0.405 | 0.215 | −0.392 | +0.519 | 1,620 |
| JITL ADWIN-gated | +0.146 | 0.419 | −1.49 | +0.506 | 37 |

Reading: JITL *partially* rescues the catastrophic fold (−1.49 → −0.39) but the
bias-update *fully* does (→ +0.49), with 4.7× tighter SE and zero local fits vs
JITL's 1,620. The drift here is a per-regime *offset* on a *stable* relationship;
the bias-update targets exactly that with one O(1) term, while JITL rebuilds an
O(N·d²) local model every query to relearn a relationship that did not change.
**JITL-gated barely moved** (= static): ADWIN's ~260-sample latency means it
triggers local modelling only after the catastrophic fold's damage is done —
quantifying, against JITL, why adaptation here must be *continuous*, not
detector-gated. Right tool for calibration drift; not "JITL is bad".

## Consequences

**Positive**
- Worst-case robustness: CV SE 0.419 → 0.046; worst fold −1.49 → +0.49.
- Held-out test +0.476 → +0.857.
- Faithful to a verified primary (Shardt 2016) for the open-loop case.
- Causal and online: uses only labels available θ steps in the past.

**Negative / limits (stated plainly)**
- **θ is load-bearing and assumed.** θ=4 is the benchmark convention; the true
  plant delay was "great and unknown." Any other column requires re-pinning θ.
- **Small-θ residual autocorrelation.** As θ→1 the correction degenerates toward
  first-differencing the residual, inflating R² artificially (θ=1 gives CV
  +0.91 — reported only as a boundary, not used). θ=4 is weakly affected and is
  the physically sanctioned value.
- **Variance-limited folds are not rescued.** Fold 2 (residual std 0.157, ~3× the
  others) is variance-limited, not offset-limited; it stays the weakest
  corrected fold across all θ. This is expected, not a failure of the method.
- **Detection latency.** ADWIN flags genuine regime transitions cleanly (fired at
  CV-stream indices 511, 735; zero false alarms in-control) but its latency on a
  gradual shift is ~260 samples — too slow to *be* the correction. Its role is
  supervisory (regime flag), not the trigger; the workhorse is the per-sample
  bias update. Page-Hinkley/CUSUM over-fire on the heteroscedastic residual when
  scaled to a single reference σ, so they remain comparators, not the primary.

## Alternatives considered and rejected

- **Closed-loop integrator bias term** (Shardt Eq. 6/10, Σaⱼ=0 for exact
  tracking). Required only when the sensor drives control; with θ=15 feedback it
  risks oscillation. **Deferred to Module 3** (RTO/control).
- **Dynamic time-delay re-estimation (Wang DTDE / SD-DU + WRVM).** The best lag is
  stable (14–15) across all splits, so delay re-estimation addresses a problem we
  do not have. **Parked.**
- **Detector-triggered one-shot recalibration.** The bias is continuous and
  per-regime (every fold biased, varying offset), not a single step — a one-shot
  reset under-corrects. **Rejected** in favour of a continuous update. Confirmed
  empirically: ADWIN-gated JITL barely beats static (CV +0.146, worst −1.49).
- **JITL (Cheng & Chiu 2004) as the adaptive layer** — the original plan's
  literature standard. **Benchmarked, not dominant here**: on this calibration-
  drift problem the O(1) bias-update beats O(N) JITL on CV mean, SE, worst fold
  and test (table above). Also dimension-fragile: JITL (LWR) collapsed (R² ≈ −8)
  on the raw 112-feature lagged set, working only on the low-dim physics-anchored
  features. JITL retained as the reported baseline, not the deployed mechanism.
- **Page-Hinkley / CUSUM as primary detector.** Over-fire on residual-scale,
  heteroscedastic streams; ADWIN (scale-free, bounded FP) is primary.

## Sources (Tier 1 — register in docs/sources/source-map.md)

- Shardt, Y. A. W. & Yang, X. (2016). *Development of Soft Sensors for the Case
  Where the Time Delay is Random.* IFAC-PapersOnLine 49-7, 1193–1198. — bias
  update form, open-loop Case I, integrator (Eq. 6/10) for closed loop.
- Bifet, A. & Gavaldà, R. (2007). *Learning from Time-Changing Data with Adaptive
  Windowing.* SIAM SDM. — ADWIN.
- Page, E. S. (1954). *Continuous Inspection Schemes.* Biometrika 41. —
  CUSUM / Page-Hinkley.
- Montgomery, D. C. *Introduction to Statistical Quality Control.* — tabular
  CUSUM ARL₀ (validation reference).
- Cheng, C. & Chiu, M. S. (2004). *A new data-based methodology for nonlinear
  process modeling.* Chem. Eng. Sci. 59, 2801–2810. — JITL baseline.
- Fortuna, L., Graziani, S., Xibilia, M. G. (2005/2007). — Debutanizer benchmark,
  C4 gas-chromatograph delay (4 output lags), θ source.

## Follow-ups

- Pin θ to the real analyzer cycle if deploying outside the benchmark.
- Module 3: revisit the closed-loop integrator form if the soft sensor drives
  control.
