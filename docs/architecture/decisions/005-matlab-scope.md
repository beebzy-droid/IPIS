# ADR 005 — MATLAB / Simulink Scope in IPIS

**Status:** Accepted
**Date:** 2026-05-29
**Decision owner:** Bien Busico

## Context

MATLAB/Simulink is a core skill in the author's toolset and a strong tool for control design and dynamic simulation. The question is where — if anywhere — it belongs in IPIS, applying the same test used for PINNs, GNNs, and time-series foundation models: does it solve a specific identified problem, or is it being added because it is a known tool?

## Decision

- **Excluded from Module 1.** The soft-sensor physics engine is implemented in pure Python (Perry's-grounded VLE via `math`/`scipy`; later CoolProp). Python fully covers the required calculations.
- **Conditional in Phase 1C (cross-process transfer).** The canonical Tennessee Eastman simulator is the Downs-Vogel Simulink model. MATLAB is a legitimate touchpoint if that simulator is used to generate data — but it is optional, since pure-Python TEP datasets (e.g., Rieth et al. extended dataset) exist.
- **Strong fit in Module 3 (RTO).** Simulink + Model Predictive Control Toolbox is best-in-class for control design. This is where MATLAB most earns inclusion.

## Rationale

- **Reproducibility.** MATLAB is license-locked. A public portfolio repo whose foundational module requires MATLAB cannot be run by a reviewer or hiring manager with only Python. Module 1 must stay Python-only.
- **No problem to solve in Module 1.** Python (CoolProp/scipy/thermo) already covers VLE and shortcut distillation; MATLAB would add a second runtime and a bridge layer for no gain.
- **Real value where it fits.** Control design (Module 3) and the reference TEP model (Phase 1C) are genuine MATLAB strengths.
- **Consistent principle.** Same place-where-it-solves-a-real-problem test applied uniformly across all technology decisions.

## Consequences

### Positive

- Module 1 stays clean, Python-only, and reproducible by anyone.
- Infrastructure built in Module 1 is reused across modules without a language split.

### Negative

- MATLAB's control-design strengths are deferred to Module 3.
- If Phase 1C uses the Simulink TEP model, a MATLAB dependency enters there (mitigated by the Python TEP dataset alternative).

### Neutral

- The decision is revisited at Module 3, where MATLAB inclusion is expected to be justified.

## Revisit triggers

- Module 3 control design begins and Simulink + MPC Toolbox is the right tool.
- A real plant or partner requires Simulink-based models.
- Phase 1C requires the canonical Simulink TEP simulator and no adequate Python dataset is available.

## References

- ADR-003 (three-dataset hierarchy; TEP as secondary dataset)
- IPIS Master Technical Specification, Section 4 (Technology Decision Matrix)
- Downs & Vogel (1993), Tennessee Eastman process; Rieth et al. (2017), extended TEP dataset
