# ADR-007: Module 1 soft-sensor architecture — dynamic, physics-anchored, evaluated under blocked CV

**Status:** Accepted

**Supersedes:** ADR-001 (Path B PINN/residual hybrid) — see ADR-001 revisit triggers; Path A retained as private future work.

**Date:** 2026 (Module 1, Phase 1A)

## Context

The original Module 1 plan (ADR-001) was a hybrid `y_hybrid = y_physics + ML_residual`
built on a steady-state physics estimate. Building and validating it against the
real Debutanizer data (Fortuna et al., normalized [0,1], 2394 rows) produced a
sequence of empirical findings that forced a sharper architecture:

1. **Static single-tray physics failed.** The bubble-point physics-to-data
   bridge, applied at lag 0, scored held-out R^2 = 0.018. The physics math was
   verified correct (Perry's + Smith cross-check; 0% clipping); the failure was
   that it was applied statically.

2. **The problem is dynamic with a stable transport delay.** Signal diagnosis
   found the C4 target is dominated by tray-6 temperature (u5) at a ~15-sample
   transport delay (u5 lag-15 r^2 = 0.51 in every split, including held-out
   test). The delay is STABLE across splits (best-lag 14-15), so dynamic delay
   estimation (Wang DTDE) is NOT required for this dataset.

3. **A naive lagged kitchen-sink model overfits to regime.** A 126-feature
   lagged PLS scored train 0.77 / val 0.75 but test 0.04 — not overfitting in
   the train>>val sense (train ~= val) and not leakage (which would inflate
   test). The cause is covariate shift between the train+val regime and the
   held-out test regime, which a temporally-adjacent validation set cannot
   police (it shares the train regime and rewards regime-specific structure).

4. **Honest blocked CV exposes calibration instability.** Forward-chaining
   time-series CV with a 1-SE parsimony rule selected maximum parsimony (k=1)
   and recovered held-out R^2 = 0.52 (13x over the naive selection), but with
   strongly negative CV folds and SE > |mean| — the signature of cross-regime
   calibration drift (stable correlation, drifting slope/intercept). This is
   the exact scenario Shardt (2016) addresses with an online bias-update term.

## Decision

**The Module 1 soft sensor is a dynamic, physics-anchored, parsimonious model,
selected and judged under blocked time-series cross-validation rather than a
single held-out split.**

Concretely:

- **Features set by physics, not by validation.** A small fixed feature set at
  the transport lag: the bubble-point C4 estimate, the relative volatility
  alpha(T) = Psat_C4/Psat_C6, and the stripping factor `alpha * reflux` (the
  nonlinear multivariate fusion a linear-on-raw model cannot synthesize), plus
  raw u5 at the transport lag.
- **Evaluation backbone = blocked CV + 1-SE parsimony rule** (leakage-safe
  per-fold lagging, train-only scaling, held-out test touched once). A single
  held-out R^2 is explicitly NOT treated as the verdict.
- **Robustness is the primary criterion**, not peak point accuracy.
- **High-capacity ML (XGBoost/LSTM) is deferred.** The binding constraint is
  non-stationarity, not model expressiveness; added capacity is predicted to
  worsen regime-overfit. Any such model must be judged under blocked CV.
- **Wang DTDE is NOT adopted** for this dataset (delay is stable).
- **The deployable answer is adaptive:** Phase 1B drift detection
  (ADWIN/Page-Hinkley) + online bias-update (Shardt) — the response to the
  residual non-stationarity no static model can remove.

## Result (the evidence)

Three models, identical blocked CV (5 folds) + one held-out test:

| Model | Features | Held-out R^2 | CV mean +/- SE | Worst fold |
|---|---|---|---|---|
| u5-only | 1 | 0.395 | +0.034 +/- 0.438 | -1.70 |
| **physics-anchored** | **4** | **0.476** | **+0.145 +/- 0.419** | **-1.49** |
| kitchen-sink PLS | 126 | 0.520 | -0.616 +/- 0.932 | -4.28 |

- The stripping factor carries genuine signal: physics-anchored beats u5-only
  on held-out R^2 (+0.08), CV mean, and 4 of 5 folds.
- Physics-anchored is far more stable than the kitchen sink: ~half the CV SE
  (0.42 vs 0.93), positive vs deeply negative CV mean, worst fold -1.5 vs -4.3,
  with 4 features vs 126.
- Honest tension: the kitchen sink edges the single held-out number (0.52 vs
  0.48), but next to a -0.62 CV mean and a -4.28 fold — its score is a lottery.
  This is precisely why a single held-out R^2 is not the verdict.

**Module 1 finding:** a 4-feature physics-anchored model matches a 126-feature
statistical model on held-out accuracy (0.48 vs 0.52) while being ~2x more
robust across operating regimes — physics-grounded structure is robust under
distribution shift where statistical structure is fragile.

## Consequences

**Positive:** robustness under non-stationarity; interpretability (4 physical
features); a transferable feature basis for Phase 1C; an honest evaluation
methodology reusable for every later model.

**Trade-offs (stated honestly):** ~0.04 lower peak held-out R^2 than the kitchen
sink; modest absolute accuracy (~0.48) on a hard, non-stationary benchmark; a
brutal fold-2 that is unpredictable for ALL models (residual non-stationarity
that motivates Phase 1B, not something physics removes).

**Follow-ons:** Phase 1B drift detection + Shardt bias-update (deployment
answer); Phase 1C transfer to Tennessee Eastman (where the physics features'
transferability is the scientific payoff).

## Note on ADR numbering

A prior plan reserved "ADR-007" for the Module 3 tooling decision
(MATLAB / gPROMS / simulator). ADRs are chronological, so this architecture
decision takes 007; the Module 3 tooling ADR will take the next free number
when Module 3 is scoped.
