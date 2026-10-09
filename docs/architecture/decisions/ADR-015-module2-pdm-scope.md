# ADR-015 — Module 2 (Predictive Maintenance): dataset, taxonomy, and success metric

**Status:** Accepted (D2 ratified by action — FEMTO + CWRU downloaded and placed
2026-06-16; build proceeds to Phase 2A)
**Date:** 2026-06-16
**Decision owner:** Bien Busico
**Module:** 2 (predictive maintenance) — anomaly detection + RUL
**Relates to:** ADR-003 (three-dataset hierarchy), ADR-008 (drift detection),
ADR-010 (from-primary conformal), ADR-014 (one-sided conformal in M3), and the
`ipis.shared.state_bus` Module-2 contract.

> No numbers in this ADR are produced by an M2 experiment yet — none exist. The
> dataset characteristics, scoring functions, and bearing kinematics below were
> verified against primary/standard sources during scoping (see References) and
> become repo fixtures only after re-verification at implementation
> (verify-before-load-bearing).

## Context

HANDOFF §0.5 designates Module 2 — predictive maintenance (anomaly detection + RUL)
— as the next track, to be scoped before any code. The state bus
(`OperationalState`) already fixes M2's outputs: a per-equipment **health score**
∈ [0,1], a **health flag** (OK/WARN/ALARM), and **remaining useful life** in time
units. So M2 is two sub-tasks, not one: detect/quantify degradation, and predict
remaining life with a usable bound.

Three constraints frame the dataset choice:

1. **Two sub-tasks need data that supports both.** Anomaly/health detection needs
   labelled or trendable degradation; RUL needs run-to-failure trajectories with a
   defined end-of-life.
2. **The IPIS v2 hardware target is bearing vibration.** The v2 Hardware Master
   specifies a motor-bearing testbed with ADXL355 accelerometers, fault injection
   (imbalance + bearing races), vibration features (RMS, kurtosis, crest factor,
   peak-freq), and an original run-to-failure dataset (IPIS-PdM-001). A bearing-
   vibration software target makes the eventual `HardwareDataRouter` a drop-in.
   *(Hardware is reference only here; the immediate deliverable is software M2 in
   IPIS v1.)*
3. **House disciplines apply unchanged:** physics-anchored features, blocked CV +
   one-SE, conformal intervals where they matter, numbers-first, ≈10–20 % asset
   reuse expected.

§0.5 lists candidates as the in-repo TEP IDV faults, or a bearing / NASA C-MAPSS
RUL set. The pick is the load-bearing scope decision.

## Decision

**Adopt a three-dataset hierarchy with a bearing run-to-failure primary, mirroring
ADR-003.**

- **Primary (health + RUL): FEMTO-PRONOSTIA** (IEEE PHM 2012). Supplies both
  sub-tasks; vibration accelerometers match the v2 testbed.
- **Secondary (fault diagnosis): CWRU** seeded-fault bearing — clean
  inner/outer/ball-race labels to validate the physics-anchored fault-frequency
  layer that FEMTO cannot cleanly support.
- **Cross-domain anomaly stress: TEP IDV** from the in-repo simulator — proves the
  detection methodology transfers to a process fault set; **no RUL claimed on TEP.**

Supporting decisions: physics layer = bearing characteristic defect frequencies
(BPFO/BPFI/BSF/FTF) as the M2 analogue of M1's VLE; success metric pair =
AUROC/lead-time/FAR for detection and RMSE/MAE/**PHM-2012 Score**/**conformal
one-sided RUL coverage** for prognosis; headline contribution = *physics-anchored,
conditionally-calibrated RUL.* Full D1–D6 in `docs/module2/spec.md`.

## Rationale

- **FEMTO over TEP-as-primary.** TEP IDV faults are step/random/sticking
  disturbances, not degradation-to-failure — there is **no RUL target** to regress.
  Making TEP the primary would silently drop half of M2's contracted output (RUL).
  TEP keeps its honest role: a cross-domain *detection* check (the ADR-003
  "different industry" slot), at the ≈10–20 % reuse the HANDOFF predicted.
- **FEMTO over C-MAPSS.** C-MAPSS is a strong RUL benchmark, but it is gas-path
  turbofan data with no bearing vibration. It would give RUL while breaking the
  alignment with the v2 hardware and forfeiting the bearing-kinematics physics
  layer — i.e., RUL without the IPIS signature. FEMTO gives RUL *and* the physics
  *and* the hardware match.
- **Why a separate CWRU.** FEMTO bearings are *naturally* degraded — all defect
  types (balls, rings, cage) co-develop, so frequency signatures are weak and
  mixed (the PRONOSTIA authors note classical frequency-signature methods struggle
  on it). That is ideal for RUL but poor for verifying a fault-localisation layer.
  CWRU's seeded single-component faults are the clean test for the BPFO/BPFI/BSF
  physics.
- **Physics layer is genuinely first-principles.** BPFO/BPFI/BSF/FTF derive from
  bearing geometry and shaft speed — verified consistent across multiple sources.
  This preserves the "physics-anchored" identity M1 and M3 carry, rather than a
  pure black-box PdM model.
- **Conformal RUL is conformal-where-it-matters.** Maintenance scheduling under an
  asymmetric late-penalty wants a guaranteed-conservative *lower* bound on
  remaining life — a one-sided interval, exactly the M3 spec insight (ADR-014)
  reused. Coverage that holds across FEMTO's 3 operating conditions is the
  M1-style regime-uniform claim (ADR-010).
- **Blocked CV is mandatory again.** Bearing degradation is strongly
  non-stationary; a temporally-adjacent validation split would over-state
  generalisation exactly as it did on the Debutanizer in Phase 1A. Forward-chaining
  CV + one-SE (reused from `evaluation/blocked_cv.py`) is the honest instrument.

## Consequences

### Positive
- Both contracted sub-tasks (health + RUL) are covered by one primary dataset.
- Software pre-aligns with the v2 hardware; the `HardwareDataRouter` bridge becomes
  a feature-name remap, not a re-model.
- M2 inherits a crisp, paper-shaped contribution consistent with the IPIS thesis
  (physics-informed + calibrated uncertainty), distinct from M1/M3.
- Maximal reuse: conformal, drift, blocked-CV, serving, and state-bus assets all
  carry over.

### Negative
- Two external dataset downloads (FEMTO, CWRU) must be acquired and registered;
  neither is in-repo yet.
- FEMTO's naturally-mixed signatures make per-defect diagnosis on FEMTO itself
  unreliable — hence the CWRU dependency (a second dataset to manage).
- The PHM-2012 Score is only comparable on the same test set; cross-paper
  comparison must cite the identical 11-bearing split.

### Neutral
- M2 phase letters (2A–2D) mirror M1/M3; the per-phase HANDOFF-update rule applies.
- The vibration feature set is broader than M1's tabular inputs (envelope spectrum
  + band energies), but reduces to the same low-dimensional, physics-anchored
  feature vector the downstream estimators expect.

## Revisit triggers
- **D2 not ratified / owner prefers a different primary** — if RUL is deprioritised
  in favour of a pure process-anomaly module, TEP-primary becomes viable and this
  ADR is rewritten.
- **v2 hardware data arrives (IPIS-PdM-001)** — promote it to the primary
  validation set; FEMTO becomes the public benchmark and the transfer source.
- **A nonlinear/process RUL need emerges** — re-evaluate C-MAPSS as a second RUL
  benchmark for cross-domain RUL transfer.
- **Bearing kinematics fail their fixture check** against Harris/ISO 15243 at
  implementation — revisit the physics-feature definitions (esp. the BSF prefactor).

## References

- Nectoux, P. et al. (2012). *PRONOSTIA: An experimental platform for bearings
  accelerated degradation tests.* IEEE Int. Conf. on PHM, Denver. (FEMTO dataset;
  17 run-to-failure bearings, 3 conditions, 6-train/11-test, 25.6 kHz, 20 g EOL;
  PHM-2012 percent-error asymmetric score.)
- Case Western Reserve University Bearing Data Center (CWRU) — seeded-fault bearing
  benchmark (drive-/fan-end, inner/outer/ball, graded fault diameters).
- Harris, T. A. *Rolling Bearing Analysis*; **ISO 15243** (rolling-bearing damage
  and failure modes) — authoritative for the BPFO/BPFI/BSF/FTF kinematics
  (pin at implementation, edition-internal fixtures).
- Saxena, A. et al. — NASA/PHM-2008 (C-MAPSS) asymmetric RUL score (the
  exp(d/10) late / exp(−d/13) early form), considered and not selected as primary.
- Downs & Vogel (1993); Russell/Chiang/Braatz TEP simulator — cross-domain anomaly
  source (in-repo generator).
- Related ADRs: ADR-003 (dataset hierarchy pattern), ADR-008 (ADWIN/PH/CUSUM),
  ADR-010 (from-primary conformal, ACI), ADR-014 (one-sided conformal in M3).
- `docs/module2/spec.md` (full D1–D6); `docs/sources/source-map.md` (Tier-1
  registration of FEMTO/CWRU/Harris/ISO 15243 at first use).
