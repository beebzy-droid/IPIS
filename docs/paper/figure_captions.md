# Figure captions

> Phase 1F.4. Self-contained captions (CACE readers skim figures before text); every
> number is from the frozen evidence. At 1F.5 these become the LaTeX \caption{} bodies.
> NOTE: F6 currently renders from the 1D.1b script, not from a `paper_figures` emitter —
> port it into the emitter package during 1F.5 for one-command regeneration.

**Figure F1 — Framework and serving architecture.** (a) The offline/online pipeline:
physics-derived features (bubble-point estimate, relative volatility α(T), stripping
factor) feed blocked time-series CV with one-SE selection; the frozen linear sensor is
corrected online by an open-loop EWMA bias update at the documented label delay θ, and
adaptive conformal intervals are computed on the corrected residuals; drift alarming
acts on the corrected residual, and migration (offline) initializes sensors for sibling
regimes. (b) Serving as two asynchronous flows over mutable state (bᵗ, αᵗ, score
window): the predict flow reads state and stores the issued interval per sample; the
delayed label flow mutates state under a lock and scores coverage against the interval
stored at prediction time (dashed), not the since-adapted current interval.

**Figure F2 — Feature ablation on the debutanizer (identical blocked-CV protocol).**
Bars: blocked-CV R² mean ± SE; red dashes: worst fold; k = number of features. The
physics-anchored set with the raw lagged temperature (k = 4) dominates (CV +0.145 ±
0.419, test +0.476), while the 126-feature lagged kitchen sink collapses (CV −1.604 ±
1.421, worst fold −6.248) and its failure is visible out-of-sample as well (test
+0.221): complexity set by physics beats complexity set by validation.

**Figure F3 — SECOM elastic-net CV path (p ≈ n selection lottery).** Mean blocked-CV
−R² (log scale) ± SE along the regularization path, complexity increasing to the right.
The path explodes by four orders of magnitude (to −R² ≈ 7 × 10⁴) at weak shrinkage; the
one-standard-error rule (blue) selects maximal shrinkage α* = 10 (6/441 nonzero
coefficients), adjacent to the best CV mean (red), containing the lottery that pure
CV-mean selection would re-enter.

**Figure F4 — Held-out residual trace, raw vs. bias-corrected (debutanizer).** Residuals
on the 360-sample test window before (red) and after (blue) the open-loop EWMA bias
update (λ = 0.1 CV-selected on the pool; θ = 4). The correction removes the calibration
offset and tracks within-window drift, lifting held-out R² from +0.476 to +0.857; the
residual sd drops accordingly. The same mechanism reduces cross-fold SE 9× in CV
(Table T1 vs. §5.2).

**Figure F5 — Data efficiency of regime migration (TEP, mode 1 → modes 2 and 3;
two-layer = migration + online bias update, n = 8 repeats).** Held-out R² vs. fraction
of target-regime data for the migrated sensor (blue, ± sd) and from-scratch training
(red); dashed line: 90% of the from-scratch ceiling. Yan functional scale-bias
migration reaches the threshold at 5% of target data vs. 50% from scratch on both
targets — 10.0× data efficiency — with calibrated GP posterior intervals (coverage
92–98%) that widen appropriately for the larger mode-3 regime gap.

**Figure F6 — Coverage under a controlled drift stress (synthetic; target 0.90).**
Residual scale is tripled mid-stream. Static split conformal collapses to 0.403
coverage; adaptive conformal inference re-attains 0.899 by adapting the working
miscoverage level; EnbPI recovers to 0.832 with the lag of its FIFO residual window.
The controlled version of the real-regime inconsistency in Figure F7.

**Figure F7 — Empirical coverage on real TEP regimes (target 0.90, dashed; n = 300 per
regime; θ ∈ {2, 5}).** Static split conformal on raw residuals is invalid in both
directions — under-covering modes 1–2 (0.847) and over-covering mode 3 (0.957, at the
widest intervals, 3.18). The corrected + ACI construction is regime-uniform at the
target (range [0.897, 0.903] across all six regime × delay cells) at widths 1.7–2.5;
EnbPI sits between. Validity here is a property of the composition: bias correction
first, conformal calibration on what remains.
