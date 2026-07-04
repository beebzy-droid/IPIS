# Module 3 — Real-Time Optimization (RTO)

This directory holds Module 3 documentation. **Status: complete (3A + 3B); paper under
review (IEEE TCST, 26-0876). 3C closed-loop is future work.**

## Files

- **spec.md** — This technical specification (as-built).
- **scoping.md** — Module-scope decisions D1–D5 (what "RTO" means here, process scope, stack, M1→M3 interface, build order).
- **twin-spec-3a.md** — Twin fidelity decisions T1–T6 for the DWSIM debutaniser.
- **dwsim-walkthrough-3a.md** — Gated build procedure (G0→G4) for the rigorous column.
- **twin-validation.md** — 3A twin validation report (V1–V3).
- **scoping-3b.md** — Uncertainty-aware RTO scoping (the contribution).
- **literature-3b.md** — Positioning against modifier adaptation and conformal-optimization.
- **audit-and-source-requests.md** — Pre-submission audit (A–F) and source list.
- **results.md** — Phase 3A and 3B metrics and observations.
- **paper/** — Paper 2 working copy: outline, claims ledger, sections, frozen evidence (`regime_map.json`), figures (F1–F7).

## Status

| Phase | Status | Notes |
|---|---|---|
| 3A — Twin + deterministic RTO | **✅ Complete** (ADR-013) | DWSIM PR twin, GEKKO economic NLP, fixed-margin back-off baseline |
| 3B — Uncertainty-aware (conformal) RTO | **✅ Complete** (ADR-014) | Chance-constrained regime map; the conformal selection effect — the Paper 2 contribution |
| 3C — Closed-loop on TEP | ⏳ Future work | Online soft sensor in the loop; Bathelt Simulink plant. Out of Paper 2 scope (named as future work) |

## Architecture summary (as-built)

**Scope (D1–D5).** Steady-state RTO with an **uncertainty-aware constraint back-off**: the
specification margin is set from a calibrated conformal interval rather than an ad-hoc safety
factor (D1). First target is the **debutaniser twin** (D2), built on **DWSIM + GEKKO + CoolProp**
with a **GPR surrogate** for in-loop evaluation at 3B (D3; gPROMS ruled out — re-entry trigger
documented). Module 1 feeds Module 3 over `ipis.shared.state_bus` as estimate + interval + drift
flag (D4). Build order: 3A skeleton → 3B contribution → 3C closed-loop (D5).

**Twin (T1–T6, ADR-013).** Binary n-butane / n-hexane proxy (T1, matching the M1 physics layer);
**Peng-Robinson** equation of state (T2); 8 theoretical stages plus a total condenser (DWSIM
configured as **9 stages**, condenser indexed 0, reboiler 8), feed at stage 4, top pressure
4.7 bar with a 0.4 bar column drop (T3); decision variables reflux ratio R ∈ [0.8, 3.0] and
distillate flow D ∈ [33, 37] kmol h⁻¹, with the one-sided spec **x_B (bottoms n-C4) ≤ 0.02** (T4);
literature-default economics with a two-stream profit (overhead at the light-key price, bottoms
at the gasoline price by mass, less reboiler energy), which makes the spec economically active
(T5); a quadratic ln(x_B) surface solved with GEKKO/IPOPT for 3A (T6). The rigorous PR twin is
validated by leave-one-feed-composition-out interpolation (R² ≈ 0.92, MAE ≈ 0.005 in x_B).

**Deterministic RTO (3A).** On the rigorous twin the ln(x_B) surface fits R² ≈ 0.996; the
deterministic optimum sits at R\* ≈ 2.70, D\* ≈ 33.7 with the spec active and the sensor
temperature inside its trained envelope; the back-off carries a profit gradient of ~3–6 USD h⁻¹
per 0.001 of margin.

**Uncertainty-aware RTO — the contribution (3B, ADR-014).** A chance constraint on the
unmeasured bottoms composition, P[x_B ≤ ḡ] ≥ 1−α (α = 0.10), enforced through a data-driven
conformal back-off, swept over the feed-composition disturbance magnitude σ_z. The result is a
**regime map** exhibiting the **conformal selection effect**: a marginally valid back-off (fixed
or locally adaptive) realises ~5× the nominal violation under optimisation, because the optimiser
selects the operating point where the margin under-covers the conditional quantile; an oracle
conditional back-off holds the target by construction (confirming the chance-constraint
formulation is sound); and a **conformalised-quantile-regression back-off with an a-posteriori
calibration step** returns the violation to the oracle level at near-oracle profit over the
operationally realistic disturbance range, degrading diagnosably (via a climbing inflation factor)
only when the disturbance widens several-fold. The contribution is **calibrated safety, not
profit** — at a well-controlled feed all methods earn within half a percent of the deterministic
optimum.

## Publication

Module 3 is reported in **Paper 2**: "Safe real-time optimization under unmeasured disturbances: a finite-sample, distribution-free constraint-satisfaction guarantee,"
submitted to *IEEE Trans. Control Systems Technology* (**26-0876**). LaTeX source in `paper2/tcst/`;
markdown working copy, figures, and frozen evidence in `docs/module3/paper/`.

See `docs/architecture/decisions/` (ADR-013, ADR-014) for the reasoning behind each decision, and
`docs/HANDOFF.md` §10 for the full gated build history.
