# ADR 004 — Analytical-First Physics Baseline

**Status:** Accepted
**Date:** 2026-05-29
**Decision owner:** Bien Busico
**Supersedes:** the DWSIM-first sequencing implied by ADR-001 and the master specification

## Context

ADR-001 established the Path B residual hybrid (first-principles baseline + ML residual) and named "DWSIM Debutanizer column, analytical fallback" as the physics source — implying DWSIM-first, with an analytical model only as a fallback if the DWSIM bridge failed.

Two facts surfaced during planning that were not known when ADR-001 was written:

1. **The benchmark Debutanizer data is pre-normalized to [0,1] with no published denormalization constants.** Driving any physical simulator (analytical, DWSIM, or Aspen) in real engineering units requires reconstructing operating ranges from literature — a complication independent of which backend is used.
2. **DWSIM-first is the single highest-risk item in Module 1.** It is a .NET application with a historically fragile Python bridge, and a failed install would block all physics work before the hybrid concept is even validated.

## Decision

**Build the analytical Python physics engine first.** Implement the first-principles column model — Antoine vapor pressure, modified Raoult's law bubble-point, relative volatility, and the Fenske-Underwood-Gilliland shortcut — grounded in Perry's Chemical Engineers' Handbook (9th ed.) and validated against Perry's worked examples via unit tests.

DWSIM becomes a Tier-2 fidelity enhancement (swapped in after the analytical engine is validated), and Aspen a Tier-3 optional cross-validation. The `PhysicsModel` interface exposes a single `predict()` contract, so backends are interchangeable without architectural change.

## Rationale

- **De-risks the critical path.** The architecture is proven end-to-end with zero simulator-install dependency.
- **CI-reproducible.** A Python analytical engine runs anywhere; anyone cloning the repo can reproduce it without a proprietary license.
- **Validated against authority.** Each function is unit-tested against Perry's worked examples (e.g., Example 4-11: bubble pressure 108.134 kPa, y1 = 0.5851 — verified against the source page).
- **New information legitimately changes the plan.** The pre-normalization discovery post-dates ADR-001.
- **Swappable backend.** Higher-fidelity DWSIM/Aspen shrink the ML residual later; they are enhancements, not prerequisites.

## Consequences

### Positive

- Lowest-risk route to a working hybrid; no install blocker.
- Fully reproducible physics layer; textbook-validated.
- The analytical engine is a reusable, citable asset for the publication.

### Negative

- Analytical (FUG/ideal-VLE) is lower fidelity than a rigorous tray-by-tray simulation; the ML residual must do more work.
- The pre-normalization issue still requires an explicit framing choice (reconstruct units vs. physics-structured grey-box) — deferred but not eliminated.

### Neutral

- DWSIM/Aspen remain on the roadmap as fidelity tiers, gated on need and (for Aspen) license-legal access.

## Revisit triggers

- If the analytical engine cannot represent the Debutanizer adequately (residual not learnable), escalate to DWSIM sooner.
- If a real-unit dataset (e.g., industrial partner data) arrives, re-evaluate whether full first-principles in engineering units becomes worthwhile.

## References

- ADR-001 (Path B PINN strategy)
- Perry's Chemical Engineers' Handbook, 9th ed., Sections 2, 4, 13
- IPIS Master Technical Specification, Section 5 (Digital-Twin / Physics Strategy)
