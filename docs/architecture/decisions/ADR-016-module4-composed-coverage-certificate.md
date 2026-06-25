# ADR-016 — Module 4 (Integration): tight coupling and a composed closed-loop coverage certificate

**Status:** Accepted (ratified twice during the Module 4 build; logged here for the record)
**Date:** 2026-06-23
**Decision owner:** Bien Busico
**Module:** 4 (full integration) — health-aware RTO with a joint safety certificate
**Relates to:** ADR-007 (physics-anchored soft sensor / M1), ADR-014 (conditional conformal
in M3 / RTO), ADR-015 (M2 PdM scope), and the `ipis.shared.state_bus` contract that the three
modules already write to.

## Context

HANDOFF §0.5 designated full IPIS integration as the work after the three module papers. Two
forks had to be settled before any build: (1) integration *depth* — loose coupling (shared bus,
independent services, one dashboard) versus tight coupling (the RTO consumes the M2 health/RUL
bound as a constraint and the M1 interval as a soft measurement); and (2) the *demonstrator
plant* — one unifying physics model versus a federated demo on each module's own benchmark.
The integration also had to clear a standing theoretical objection: conformal coverage rests on
exchangeability, and a closed loop appears to break it because the controller selects the test
regime using the predictions under test.

## Decision

1. **Tight coupling.** Module 4 is health-aware real-time optimization: the optimizer trades
   production against remaining useful life, consuming the calibrated RUL lower bound as a
   constraint and the soft-sensor interval as a backed-off quality measurement. This is the
   genuinely new contribution and the basis of Paper 4; loose coupling was rejected as an
   engineering exercise without a new claim.

2. **One unifying twin, real components.** The demonstration runs entirely on a calibrated
   Fenske–Underwood–Gilliland twin (`ShortcutColumnModel`) carrying a quality variable, a
   degrading reflux pump, and an RTO objective, with the **real** M1/M2/M3 component code
   instantiated on synthetic twin data. DWSIM-dynamic and real-plant data were deliberately
   scoped out so the contribution is the *certificate*, not the simulator. (The dynamic/physical
   realization is Module 5; real-plant validation is the long-term capstone.)

3. **A per-cycle composed certificate, enforced as one convex budget.** The joint safety event
   is `S_k = {x_k <= x_spec} AND {rho_k >= rho_min}`. Its coverage is bounded by a Bonferroni
   composition of the two module miscoverages plus a per-module similitude-departure penalty
   `2 L_j ||dpsi_j||` (a physically computable instance of the non-exchangeable-conformal gap)
   and a selection penalty. The certificate is converted into a single convex `psi`-budget that
   the modifier-adaptation NLP enforces directly, so the flagship guarantee and the operating
   floor are the same constraint.

4. **Causal timing resolves the feedback objection.** The selection penalty is exactly zero
   whenever the decision is formed before the measurement it is conditioned against. The
   synchronous orchestrator guarantees this by construction (decision `u_k` formed from
   information strictly before cycle k), so the conformal-selection term vanishes as a loop
   property rather than an assumption.

## Consequences

- **Positive.** A derived, enforceable, distribution-free guarantee on the joint closed-loop
  outcome; a clean two-arm demonstration (floor met at 0.988 under the budget, collapses to
  0.000 without it, contrast carried by equipment life); full reproducibility from one script.
- **Accepted limitations (stated as results, then carried into the roadmap).** The guarantee is
  per-cycle and marginal (horizon coverage is Module 5, via adaptive conformal inference); the
  Bonferroni composition is conservative (tightening via a joint-failure model is open item O4);
  the twin is quasi-static and binary-key (dynamic realization is Module 5, generalization to
  other units is long-term); validation is simulation-only (real-plant data is the capstone).
- **Code surface.** Eight modules under `src/ipis/integration/` (`psi`, `plant`, `orchestrator`,
  `health_rto`, `coverage`, `wiring`, `lipschitz`, `calibrate`), 77 tests, and the
  `scripts/run_twin_coverage.py` demo. Manuscript in `paper4/`.

## References

- Module manuscripts: CACE-D-26-00944 (M1), JRESS-D-26-04509 (M2/SCC), CACE-D-26-01040 (M3).
- Theory spike and term-by-term derivation: `docs/module4/formalization-spike.md`.
- Non-exchangeable conformal coverage gap and adaptive conformal inference are cited in
  `paper4/references.bib` (Barber et al. 2023; Gibbs & Candès 2021).
