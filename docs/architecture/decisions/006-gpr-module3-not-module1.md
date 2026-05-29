# ADR 006 — GPR Belongs to Module 3 (Surrogate), Not Module 1 (Soft Sensor)

**Status:** Accepted
**Date:** 2026-05-29
**Decision owner:** Bien Busico

## Context

A synthesized planning document ("brain-transfer" context file) proposed Gaussian Process Regression (GPR/Kriging) as the Module 1 soft-sensor ML layer, citing the Kajero et al. meta-modelling paper as authority. This conflicts with ADR-001, which specifies a PINN-regularized neural-network residual learner for Module 1.

The Kajero et al. paper was read in full and checked against the actual source rather than the synthesized summary.

## Decision

**GPR belongs to Module 3 (as a surrogate of the DWSIM high-fidelity model) and to the cross-process transfer formal basis (functional scale-and-bias correction / model migration) — NOT to the Module 1 soft-sensor ML layer.**

Module 1 retains the PINN-regularized NN residual learner per ADR-001.

## Rationale

- **The paper explicitly excludes online-data soft sensors from "meta-models."** It states that data-driven models (ANN, RBFN, SVM, GPR) used in soft-sensor development "cannot be considered as meta-model discussed in this work, because they are not surrogates of a more complex model" (Section 4.2). The paper's entire GPR framework concerns surrogates of high-fidelity simulations.
- **Correct placement of the paper's contributions:**
  - GPR meta-model → Module 3 surrogate of DWSIM (the paper's main application, Section 4.1).
  - Functional SBC migration (Yan et al., 2011) → formal basis for the cross-process transfer claim (Gap 1).
  - The paper's hybrid first-principle + ANN reference (Tsen et al.) → independently *supports* the Module 1 Path B hybrid concept.
- **GPR's strength is real but belongs where the paper places it.** Its mean+variance output is attractive for uncertainty quantification, but Module 1's calibrated intervals are handled by conformal prediction (ADR-stack) without changing the residual learner.

## Consequences

### Positive

- Architecture grounded in the primary source, not a synthesized summary.
- ADR-001 reinforced rather than silently overwritten.
- The meta-modelling paper's methods are correctly allocated (M3 surrogate, transfer basis).

### Negative

- None significant. GPR is still used in the project; it is relocated, not removed.

### Neutral

- If the Module 1 PINN-NN residual underperforms, a GPR residual could be reconsidered as an alternative — but that would be a new ADR.

## Note — verification discipline

This correction, together with the base-10 Antoine-form error caught the same session (the synthesized doc's `10 ** (...)` vs. the correct natural-log form, a ~340x error), demonstrates why the source-content map and the "verify against the actual page before use" protocol exist. Synthesized summaries are treated as hypotheses; primary sources are authority.

## References

- ADR-001 (Path B PINN strategy — retained)
- Kajero, Chen, Yao, Chuang, Wong, "Meta-modelling in Chemical Process System Engineering," J. Taiwan Inst. Chem. Eng. (Sections 3.3, 4.1, 4.2)
- Yan et al. (2011), Bayesian migration of GPR, Chemical Engineering Journal 166(3)
- docs/sources/source-map.md
