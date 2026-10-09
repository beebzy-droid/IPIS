# ADR-009 — Phase 1C: cross-process transfer via scale-bias-correction model migration

**Status:** Accepted
**Date:** 2026-06-04
**Decision owner:** Bien Busico
**Module:** 1 (soft sensor) — methodology transfer to Tennessee Eastman (TEP)
**Extends:** ADR-007 (physics-anchored model), ADR-008 (drift detection + bias-update),
ADR-003 (three-dataset hierarchy: TEP is the transfer dataset)

> Numbers in this ADR are from the Phase-1C data-fraction sweep on TEP operating
> regimes generated from the Russell/Chiang/Braatz closed-loop simulator, scored
> on a held-out target test split, with the two-layer composition (offline
> migration + 1B online bias-update) and n_repeats=8 random-subset averaging.

## Context

ADR-003 designated TEP as the transfer dataset for Module 1. The naive reading —
migrate the Debutanizer soft sensor *directly* onto TEP — is mathematically
inapplicable: scale-bias-correction (SBC) model migration requires a **shared
input space and similar processes** (verified from Lu & Gao 2008/2009, Yan 2011,
Luo 2015). The Debutanizer (C4 in a distillation column, 7 column-temperature/
flow inputs) and TEP (product G in a reactor-separator-stripper, 41 XMEAS / 12
XMV) share no variables, so no SBC parameter map exists between them.

Two questions therefore had to be separated:
1. Does the *methodology* (physics-anchored features + blocked CV + Shardt
   bias-update) transfer to a chemically unrelated process?
2. Within a single process, does SBC migration across operating regimes reduce
   the target data needed for a new regime, versus training from scratch?

Constraints: the canonical TEP modes (Downs & Vogel / Bathelt) require a working
closed-loop simulator. The first attempt (COSTEP, a Simulink port) suffered a
non-reproducible reactor-pressure startup trip — a known TEP sensitivity to
missing steady-state initialization (`Mode1xInitial.mat`) and mode-override
loops. A reproducible data source was needed before any modelling.

## Decision

**Frame Phase 1C as A + C, not literal Debutanizer→TEP.**
- **(A) Methodology transfer:** rebuild the Phase-1A/1B recipe unchanged on TEP to
  predict G (XMEAS 40), and show it carries the same calibration-drift signature
  and bias-update recovery.
- **(C) Within-TEP regime migration:** benchmark three SBC methods against
  from-scratch baselines on a data-fraction sweep, composed with the 1B online
  bias-update, using **data efficiency** (not ceiling-crossover) as the metric.
- Rejected (B) deep transfer-learning — out of scope and unjustified for a
  parametric soft sensor.

Supporting decisions:
- **Data of record = Russell/Chiang/Braatz closed-loop FORTRAN simulator**, three
  feed-ratio operating regimes (G 53.8 / 58.2 / 63.4 mol%, IDV 8+10+13 excitation,
  SETPT(14)/(15) feed-ratio lever). COSTEP/Simulink abandoned. Canonical mv-per
  modes kept supplementary only (under-excited for soft sensing).
- **Two-layer architecture:** migration is offline/across-regime; the 1B
  bias-update is online/within-regime. They compose.
- **Headline method = Yan functional SBC**; OSBC and Luo benchmarked alongside.

## Rationale

- **SBC scope is a primary-source constraint, not a modelling choice.** The
  shared-input-space requirement is explicit in Lu/Yan/Luo; honoring it is what
  makes the A+C framing correct rather than a dodge.
- **Data efficiency over ceiling-crossover.** The strict "migrated ≥ from-scratch
  ceiling" crossover is brittle when the ceilings coincide (they do, since both
  converge with enough data) — it flipped 20%↔100% across seeds. Data efficiency
  (fraction to reach 90% of the from-scratch ceiling) is the standard, robust
  transfer-learning metric. Results (mode 2, two-layer, n_repeats=8):
  - **Yan functional SBC: ~10×** — 90% of full accuracy at ~5% target data vs
    ~50% from-scratch, with calibrated 95% intervals (coverage 92–98%, wider for
    the larger mode-3 gap). Yan adds a zero-mean GP bias on top of the source
    predictor, so it keeps the source structure *and* fixes the relationship
    change. **Winner.**
  - **Lu OSBC: ~3.3×** — output-only affine (2 params) preserves the source's
    input-output shape; modest gain, cannot fix a relationship change.
  - **Luo matrix-SBC: ~1.0× (no gain)** — for a *linear* source, the per-input
    diagonal scaling `ρ₀` absorbs the fixed source weights and the model collapses
    to from-scratch linear regression. Verified analytically + synthetic (R² 1.00
    = from-scratch) + TEP (tracks from-scratch to ±0.001–0.003 every fraction).
- **The two-layer composition is load-bearing.** Within-mode IDV drift caps
  from-scratch bars at ~0.15–0.22 untreated; the 1B bias-update (ADR-008, applied
  unchanged) removes it and exposes migration's low-data advantage.
- **MAPIE/conformal debt discharged for 1C** via Yan's GP posterior; intervals are
  calibrated and gap-scaled.

## Consequences

### Positive
- Methodology demonstrated to transfer across process topology (column → reactor),
  strengthening the soft-sensor recipe as a reusable asset.
- A defensible, reproducible ~10× data-efficiency result with calibrated
  uncertainty — the strongest quantitative claim in Module 1 so far.
- Clean methodological lesson (add a nonparametric bias; don't reshape inputs)
  grounded in three primaries and triple-verified.

### Negative
- The TEP regimes are feed-ratio operating points, not canonical Downs & Vogel
  modes; the claim is "within-process regime migration," not "across the textbook
  modes." Must be stated honestly in any writeup.
- Yan's GP is O(n³) → requires subsampling for tractability; a productionization
  concern for 1D.
- Luo carries 2d+2 parameters and is underdetermined at small target fractions
  (needs ≥ 2d+2 samples; uses `trf`, not `lm`).

### Neutral
- The `Migrator` interface gained an optional `source_fn` (built-features → source
  prediction) used only by Luo (which re-evaluates the source at transformed
  inputs); OSBC and Yan ignore it.
- θ (label/analyzer delay) is data-specific and re-pinned per dataset (θ=2 best on
  generated data; θ=5 documented; θ=5 hurt the 1-min canonical data).

## Revisit triggers
- A nonlinear source model (e.g., the GP/XGBoost variant in 1D) — Luo matrix-SBC
  would then no longer be degenerate and should be re-benchmarked.
- Acquisition of canonical, properly-excited TEP modes — re-run the sweep to check
  the data-efficiency result holds on textbook modes.
- 1D productionization — replace the GP-posterior interval with a conformal
  (MAPIE) wrapper and re-validate coverage online.

## References
- Lu, Y. & Gao, F. (2008). Model migration with output scale-bias correction.
  *Journal of Process Control* / related (OSBC). Also Lu et al. (2009).
- Yan, W. (2011). Functional scale-bias correction via Gaussian-process model
  migration.
- Luo, L., Yao, Y. & Gao, F. (2015). Bayesian improved model migration methodology
  for fast process modeling by incorporating prior information. *Chemical
  Engineering Science* 134, 23–35. (Eq. 7 migration model; Eq. 12 least-squares.)
- Downs, J. J. & Vogel, E. F. (1993). A plant-wide industrial process control
  problem. *Computers & Chemical Engineering* 17(3), 245–255.
- Russell, Chiang & Braatz — Tennessee Eastman closed-loop simulator (data of
  record); Bathelt et al. (2015) revision.
- Shardt, Y. & Yang, Y. (2016) — open-loop bias-update (ADR-008).
- Related ADRs: ADR-003 (dataset hierarchy), ADR-004 (analytical-first physics),
  ADR-007 (physics-anchored model), ADR-008 (drift detection + bias-update).
- See `docs/sources/source-map.md` for the registered TEP Tier-1 sources and
  Verification Records #5 (SBC mis-scope) and #6 (COSTEP unusable).
