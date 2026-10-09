# ADR-012 — Phase 1E: SECOM stress-test framing and the transfer-gate closure

**Status:** Accepted
**Date:** 2026-06-05
**Decision owner:** Bien Busico
**Module:** 1 (soft sensor) — Phase 1E stress test
**Extends:** ADR-007 (model + blocked CV/one-SE), ADR-008 (bias-update), ADR-010 (conformal)

## Context

Phases 1A–1D established the pipeline on TEP and the Debutanizer — datasets with named
variables and exploitable thermodynamics. A publication-grade claim needs the opposite:
a dataset hostile to the pipeline's assumptions. UCI SECOM (1,567 samples × 590
anonymized semiconductor sensor features, ~3 months of 2008 line data, 104 fails = 6.6%,
~4.5% missing cells, 32 features >40% missing, 116 near-constant) supplies p ≈ n, heavy
missingness, severe imbalance, and **no physics anchors** — the no-physics negative
control. Structural mismatch: SECOM's native label is binary; Module 1's machinery
(Shardt bias-update, ACI regression intervals) is regression.

## Decisions

**D1 — Virtual-metrology regression framing.** One continuous measurement is held out as
the soft-sensor target, selected by stated, auditable criteria: missingness ≤ 5%,
non-degenerate variance, and maximal |point-biserial correlation| with pass/fail — i.e.
the yield-relevant measurement a VM sensor would exist to predict (selected: x59,
|r| = 0.156, 0.45% missing; full audit table emitted by the run). The fail label is used
ONLY to define the problem — never as a model feature — and target selection precedes
any model fitting. The alternative (conformal classification on pass/fail) was rejected
because it leaves the ADR-008 bias-update — a core paper component — untested and breaks
the one-framework-three-datasets narrative; noted honestly as out of scope.

**D2 — Screening under p ≈ n.** Two layers with different leakage rules: (i) label-free
unsupervised filters (>40% missing; near-zero variance), applied once on the full data —
no selection leakage is possible because no target is consulted (kept 442/590);
(ii) supervised selection = the elastic net's own shrinkage (l1_ratio 0.5, α path
10 → 1e-3), living entirely inside blocked time-series CV folds, with median imputation
inside the estimator pipeline so it is fit on fold-train only. Model choice by the
one-SE rule on the path. Univariate top-k and MI ranking were rejected as a second
selection mechanism to tune; the elastic net does screening and shrinkage in one
estimator consistent with the 1A linear philosophy.

**D3 — Transfer arm gated, then CLOSED.** SECOM has no sibling process; the only
meaningful 1C analog was temporal migration (early window → late window). The gate
condition was "1E.1 shows a signal worth migrating." Outcome: within-SECOM test R² is
negative (raw −1.84; bias-corrected −0.16) — **there is no signal to migrate**, so a
transfer arm would measure noise. The gate is closed, not deferred.

**Protocol holds constant:** blocked CV + one-SE (ADR-007), θ ∈ {2, 5} via the
bias-update delay, ACI with γ = 0.05 and the `aci.run` immediate-feedback driver —
exactly the 1D.1b protocol, so SECOM coverage numbers are directly comparable to the
TEP table.

## Results (the stress test bites — by design)

The elastic-net path under blocked CV explodes at weak shrinkage (CV R² to −7×10⁴ with
same-magnitude SEs — the p ≈ n amplification of the Debutanizer's cross-regime lottery);
one-SE selects maximal shrinkage (α* = 10, 6/441 coefficients) and contains the damage
to test R² = −1.84 raw / −0.16 corrected. Yet corrected+ACI coverage is 0.910/0.915
(θ = 2/5; target 0.90) at width 12.8, versus the over-covering static split at 0.953 /
width 20.2. Fail-enrichment of conformal misses is inconclusive (n = 9 fails in test).
Deterministic; reproduced exactly on the owner's machine against the canonical UCI bytes.

## Consequences

### Positive
- The paper gains its honest arm: **validity without accuracy** — conformal coverage is
  model-agnostic and survives a failed point model with 37% narrower intervals than the
  static baseline; physics anchors are isolated as the *accuracy* difference, and the
  one-SE rule is shown doing real work precisely where p ≈ n makes selection a lottery.
- Loader/screen/target-selection are reusable for any future high-dimensional tabular
  process dataset; 9 data-free tests guard the UCI format (quoted datetimes, NaN tokens,
  duplicate timestamps).

### Negative
- The headline VM sensor on SECOM is not deployable for point prediction — stated
  plainly rather than tuned around. Nonlinear models (1D.5, gated) are the natural
  post-review extension and SECOM now locates exactly where the linear sensor breaks.
- Target choice is ours to defend; the criteria are stated and the audit table is part
  of the run output for that reason.
- The fail-enrichment check is underpowered at n = 9 and is reported as such.

## Revisit triggers
- 1D.5 (nonlinear source) opening → rerun `secom_baseline.py` with the nonlinear
  estimator under the identical protocol; if R² turns meaningfully positive, the 1E.2
  temporal-transfer question may be re-opened with a signal to migrate.
- A reviewer challenge to the VM framing → the classification track (conformal
  classification on pass/fail; Papadopoulos pattern-recognition primary already in the
  source map) is the documented alternative.

## References
- `src/ipis/module1_soft_sensor/data/secom_loader.py`, `scripts/secom_baseline.py`,
  `tests/unit/test_secom.py`; results.md §1E.
- UCI SECOM (McCann & Johnston, 2008). Protocol: ADR-007/008/010; 1D.1b
  (`scripts/conformal_eval.py`).
