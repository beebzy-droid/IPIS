# Module 1 — Results

This document is populated as each phase completes. Each phase section follows the structure:

- **Summary** — one paragraph
- **Metrics** — table with minimum/target/stretch achieved
- **Key plots** — link to figures in `notebooks/` or `models/`
- **Observations** — what the results actually mean
- **Unexpected findings** — anomalies worth flagging

> **Methodology note (read before the metrics).** The original 1A scorecard
> below was framed as *RMSE reduction vs. pure ML* on a single split plus
> conformal coverage. Phase 1A's empirical findings (ADR-007) replaced that with
> a more honest **cross-regime** metric: held-out test R² and the spread of
> forward-chaining blocked-CV folds (mean ± SE). The original bands are kept
> visible for traceability; "Achieved" reports the as-measured methodology and
> flags what was not measured. Conformal coverage (MAPIE) was **not** built in
> 1A/1B and remains owed (candidate: 1D or a 1A/1B addendum).

---

## Phase 1A — Hybrid Model on Debutanizer

*Status: **complete** (ADR-007). Architecture pivoted from ADR-001's PINN/residual-hybrid to a dynamic, physics-anchored linear model — see ADR-007 and the divergence note in lessons-learned.*

### Summary
A static single-tray bubble-point physics estimate applied at lag 0 scored
held-out R² = 0.018 — the physics math verified correct (Perry's + Smith
cross-check, 0% clipping); the failure was that it was applied *statically*.
Signal diagnosis found the C4 target is dominated by 6th-tray temperature (u5)
at a stable ~15-sample transport delay (u5 lag-15 r² ≈ 0.51 in every split,
including held-out test). A naive 126-feature lagged PLS overfit to regime
(train 0.77 / val 0.75 / **test 0.04**) — not classic overfitting (train ≈ val)
and not leakage, but covariate shift a temporally-adjacent validation set cannot
police. Forward-chaining blocked CV with a 1-SE parsimony rule recovered held-out
test **R² = 0.52** (13× the naive selection) and exposed strongly negative CV
folds with SE > |mean| — the signature of cross-regime calibration drift that
defines the Phase 1B problem. The physics-anchored feature model carried into 1B
as the static baseline scores held-out test R² = 0.476.

### Metrics

| Metric (original plan) | Minimum | Target | Stretch | Achieved |
|---|---|---|---|---|
| RMSE reduction vs. pure ML (regime shifts) | ≥20% | ≥30% | ≥40% | *Reframed → see 1B: worst-fold R² −1.49 → +0.49 after bias-update* |
| RMSE reduction vs. pure ML (overall) | ≥10% | ≥20% | ≥30% | *Reframed → blocked-CV R²; naive 0.04 → CV-selected 0.52 held-out* |
| Conformal interval coverage | 90–97% | 93–96% | 94–96% | **Not measured** (MAPIE not built; owed) |
| Training stability | Converges | 3 seeds | 5 seeds | **N/A** — final model is a deterministic linear fit (no seed sensitivity); a consequence of the PINN→linear pivot |

### Observations
The decisive methodological lesson: a temporally-adjacent validation split
*cannot* certify cross-regime generalization — it shares the train regime and
rewards regime-specific structure. Blocked forward-chaining CV is the honest
instrument and is what turned an apparently-good model (val 0.75) into a correct
verdict (test 0.04 → fix → 0.52).

### Unexpected findings
Maximum parsimony (k=1) won under the 1-SE rule — the single physics-anchored
lagged feature beat the 126-feature model out-of-sample. The negative CV folds
were not noise; they are calibration drift, and they set up Phase 1B.

---

## Phase 1B — Drift Detection & Adaptive Bias-Update

*Status: **complete** (ADR-008). Correction mechanism is the Shardt open-loop bias-update, not the originally-planned JITL retraining — see lessons-learned.*

### Summary
Residual change detection (ADWIN primary; Page-Hinkley and an in-house
ARL₀-validated CUSUM as comparators) on the same blocked-CV backbone, paired with
a causal **Shardt (2016) open-loop bias-update** — a feedforward EWMA on the
delayed residual, b_t = (1−λ)b_{t−1} + λ(y_{t−θ} − ŷ_{t−θ}). Label/analyzer delay
θ = 4 (Fortuna GC delay, sourced; their NARMA uses 4 output lags). λ selected by
CV (test untouched).

### Metrics (θ = 4, λ = 0.1)

| Metric | Static (ADR-007) | Corrected | Change |
|---|---|---|---|
| Blocked-CV mean R² | +0.145 | **+0.648** | +0.50 |
| **Blocked-CV SE** | 0.419 | **0.046** | **9.1× tighter** |
| Worst fold R² | −1.49 | **+0.487** | catastrophe removed |
| Held-out test R² | +0.476 | **+0.857** | +0.38 |

θ-sensitivity bracket: θ=2 → CV +0.707±0.044; θ=4 → +0.648±0.046; θ=8 →
+0.599±0.060. All solidly positive, SE 7–9× tighter than static across the bracket.

### Observations
The **SE collapse (0.419 → 0.046) is the result**, not the mean lift: it converts
"competitive mean R² with large cross-regime variance" into "strictly dominant on
worst-case robustness" — the deployable claim. Detection is the trigger; the
bias-update is the correction.

### Unexpected findings
- Corrected CV (+0.648) **exceeds the best-constant-offset oracle** (+0.540): the
  update tracks within-fold drift, not just a flat offset.
- **θ is not identifiable from this dataset** (cross-correlation method 3:
  bottom-temp lag 17 > combined u5 lag 15 → physically impossible analyzer delay;
  premise falsified). θ=4 retained as sourced convention. A clean, citable
  negative result.

---

## Phase 1C — Cross-Process Transfer (Debutanizer → TEP)

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
