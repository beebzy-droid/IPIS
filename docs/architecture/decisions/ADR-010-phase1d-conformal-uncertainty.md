# ADR-010 — Phase 1D: distribution-free conformal uncertainty (from-primary)

**Status:** Proposed (pending owner ratification)
**Date:** 2026-06-05
**Decision owner:** Bien Busico
**Module:** 1 (soft sensor) — production uncertainty quantification
**Extends:** ADR-007 (physics-anchored model), ADR-008 (drift detection + bias-update),
ADR-009 (cross-process transfer; discharged the *1C* uncertainty claim via Yan's GP posterior)

> Numbers in this ADR are from the synthetic regime-shift check
> (`scripts/conformal_synthetic_check.py`, seed 20260605): a linear signal whose
> residual scale triples at t=1500, α=0.10, sliding window r=200, EnbPI B=30 / s=25.
> The on-the-real-TEP-regimes validation is **pending** (carry-in to 1D.1b).

## Context

The standing ledger debt (HANDOFF §7, spec.md §Uncertainty) is conformal
prediction. ADR-009 discharged the debt **for Phase 1C** using Yan's Bayesian GP
posterior (empirical coverage 92–98%), but that is a *credible* interval tied to
the migration model, not a distribution-free guarantee on the deployed sensor, and
it is not validated online. Production (1D) needs an interval that (a) is
distribution-free and (b) holds coverage **as the process drifts** — the same
calibration-drift the whole module is built around (ADR-007/008).

Standard split conformal (Papadopoulos 2002; Vovk 2005) assumes **exchangeability**,
which a drifting process violates. So the decision is not "add conformal" but *which*
conformal construction, and how it is implemented.

## Decision

**Phase 1D uncertainty = distribution-free conformal, implemented directly from the
primary sources (not via a third-party wrapper), with an adaptive method as the
production primary.**

- **Primary (online): Adaptive Conformal Inference (ACI)** — Gibbs & Candès 2021,
  Eq. 4: `α_{t+1} = α_t + γ(α − err_t)` over a sliding score window. Holds long-run
  coverage under arbitrary distribution shift. γ auto-selected from the published
  candidate grid {0.001…0.128} via `select_gamma` (a verified stand-in for full
  DtACI online tuning, Gibbs & Candès 2024, Alg. 1 — deferred).
- **Comparator (batch/time-series): EnbPI** — Xu & Xie 2021, Algorithm 1. Bootstrap
  LOO-ensemble residuals, width-minimising offset β̂∈[0,α], FIFO residual refresh
  every s steps. No exchangeability; B model fits (vs B·T for jackknife+).
- **Baseline (deliberately weak): split/inductive conformal** — the exchangeability-
  dependent method, kept to *demonstrate* why adaptivity is needed.
- **Implementation vehicle: from-primary, ~250 LOC, unit-tested against the published
  1−α / 1−2α guarantees** (`evaluation/conformal.py`, `tests/unit/test_conformal.py`,
  15 tests). MAPIE retained as an **optional cross-check**, not a runtime dependency.

This is a deviation from spec.md's literal "MAPIE" wording, in the same spirit as the
ADR-007/008 deviations from the original locked plan.

## Rationale

- **Exchangeability is the binding constraint, not the library.** The module's own
  evidence (negative blocked-CV folds with a stable relationship; transfer gap
  −1.08/−1.30) is exactly the regime drift that breaks split conformal. An adaptive
  method is therefore mandatory, not a refinement.
- **Synthetic verification reproduces the failure and the fix** (regime shift at
  t=1500, target 0.90):

  | method | overall | pre-drift | post-drift | mean width |
  |---|---|---|---|---|
  | split (static) | 0.645 | 0.887 | **0.403** | 3.24 |
  | ACI (γ auto) | 0.900 | 0.901 | **0.899** | 6.76 |
  | EnbPI (B=30, s=25) | 0.861 | 0.889 | **0.832** | 5.98 |

  Static split collapses to 40% post-shift; ACI holds nominal across it; EnbPI
  recovers (FIFO lag of ~700 steps at s=25). Marginal coverage alone hides the
  failure — hence per-regime reporting and the rolling-coverage curve are the
  validation instrument.
- **From-primary over wrapper:** MAPIE's `MapieTimeSeriesRegressor` is an opaque layer
  over precisely the equations verified here, and adds version sensitivity. A
  ~250-line transparent implementation is testable against the guarantees and keeps
  the library dependency-free — consistent with the verify-before-load-bearing
  discipline.
- **Model-agnostic by construction:** the interval functions consume point predictions
  and residual sequences, so they compose with the as-built linear sensor (ADR-007)
  and the Shardt bias-update (ADR-008) with no retraining.

## Consequences

### Positive
- Distribution-free intervals with **online-validated** coverage — the production-grade
  uncertainty the ledger owed, not just a marginal/credible interval.
- Fully verified, dependency-free, 15-test module; reusable across 1D serving and 1E.
- The split-vs-ACI contrast is itself a defensible "honest about drift" result.

### Negative
- ACI holds coverage by **widening** under drift (width 6.76 vs split 3.24); the
  honest cost of validity when the model error grows. Width is a reported metric.
- EnbPI's FIFO refresh **lags** abrupt shifts (~700 steps here at s=25); s is a
  coverage-vs-latency knob to tune on the real data.
- Full DtACI (auto-γ without a calibration grid-search) is **not** implemented; the
  intricate expert-weight recursion is deferred rather than shipped unverified.

### Neutral
- γ is data-specific (selected on a calibration stream), analogous to θ and λ.
- The deployed point model stays linear (ADR-007); a nonlinear source (1D.5) would
  interact with this (re-opens Luo, ADR-009) but does not change the conformal layer.

## Revisit triggers
- **1D.1b — validation on the real TEP regimes** (`tep_mode{1,2,3}`): re-run coverage
  per regime on the actual sensor residuals; confirm ACI holds and pick s for EnbPI.
- Need for hands-off γ → implement full DtACI (Gibbs & Candès 2024, Alg. 1).
- A nonlinear source model (1D.5) → re-confirm interval calibration on the lifted model.
- If multi-horizon / multi-target prediction is added → Schlembach et al. (multistep
  multivariate conformal) becomes load-bearing.

## References
- Papadopoulos, Proedrou, Vovk & Gammerman (2002). Inductive confidence machines for
  regression. *ECML*. (split/inductive CP; rank-based calibration quantile)
- Vovk, Gammerman & Shafer (2005). *Algorithmic Learning in a Random World*.
- Barber, Candès, Ramdas & Tibshirani (2021). Predictive inference with the jackknife+.
  *Ann. Statist.* 49(1), 486–507. (worst-case ≥ 1−2α; CV+)
- Xu & Xie (2021). Conformal prediction interval for dynamic time-series. *ICML*.
  (EnbPI, Algorithm 1)
- Gibbs & Candès (2021). Adaptive conformal inference under distribution shift.
  *NeurIPS*. (ACI, Eq. 4)
- Gibbs & Candès (2024). Conformal inference for online prediction with arbitrary
  distribution shifts. (DtACI, Algorithm 1; γ-grid)
- Related ADRs: ADR-007 (model), ADR-008 (drift/bias-update), ADR-009 (transfer).
- See `docs/sources/source-map.md` (Tier-1 conformal section) for the registered
  primaries and verified key results.
