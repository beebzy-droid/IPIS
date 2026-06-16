# Module 2 — Predictive Maintenance (anomaly detection + RUL)

This directory holds Module 2 documentation. **Status: scoping (ADR-015 proposed,
ratify-on-read). No code yet — this spec and ADR-015 precede the build, per the
house discipline (option-scale deliberation before code).**

Module 2 is the designated parallel track for the paper-review-wait period (Paper 1
CACE-D-26-00944 and Paper 2 JPROCONT-D-26-00565 both under review). It is largely
independent of Modules 1 and 3 (≈10–20 % asset reuse — the conformal/drift/serving
stack and the `state_bus` contract — versus ≈70–80 % for M3).

## Files

- **spec.md** — This technical specification (scope; updated to as-built per phase).
- **results.md** — *(created at first result freeze)* per-phase metrics and observations.
- **lessons-learned.md** — *(created at first phase close)* honest postmortem per phase.

## Status

| Phase | Scope | Status |
|---|---|---|
| 2A — Health index + anomaly detection (FEMTO + CWRU) | Vibration feature pipeline, physics-anchored fault-frequency features, health index, ADWIN/SPC alarming | ▶ Next (after ADR-015 ratified) |
| 2B — RUL prognosis with calibrated bounds | RUL regressor on FEMTO; conformal one-sided lower bound on RUL; PHM-2012 scoring; coverage across the 3 operating conditions | Planned |
| 2C — Cross-domain anomaly stress (TEP IDV) | Detector methodology transfer to a process fault set; FDR/FAR per IDV mode; **no RUL claim** | Planned |
| 2D — Serving + state-bus integration | M2 writes `equipment_health` / `health_flags` / `remaining_useful_life`; reuse FastAPI/Streamlit/conformal stack | Planned |

The phase letters mirror the Module 1 (1A–1F) and Module 3 (3A–3C) convention. Gating
and the HANDOFF update-at-every-phase rule apply unchanged.

## Scope (decisions D1–D6, ADR-015)

**Problem (D1).** Module 2 produces the three quantities the operational state bus already
contracts: a per-equipment **health score** ∈ [0,1], a **health flag** (OK/WARN/ALARM), and
a **remaining useful life** in time units. Two sub-tasks: (i) anomaly/health detection
(is the asset degrading, and how far), and (ii) RUL prognosis (how much life is left, with
a calibrated bound). `OperationalState` is frozen — M2 adds **no** ad-hoc fields.

**Dataset hierarchy (D2), mirroring ADR-003.**

| Role | Dataset | Question it answers | Sub-task |
|---|---|---|---|
| Primary (development) | **FEMTO-PRONOSTIA** (IEEE PHM 2012) | Can we estimate RUL with calibrated bounds, and does coverage hold across operating conditions? | Health + RUL |
| Secondary (diagnosis) | **CWRU** (Case Western, seeded faults) | Does the physics-anchored fault-frequency layer correctly localise inner/outer/ball faults? | Anomaly / fault diagnosis |
| Cross-domain stress | **TEP IDV** (in-repo generator) | Does the detection methodology transfer to a process fault set (not just rotating equipment)? | Anomaly only — **no RUL** |

Rationale for choosing a **bearing run-to-failure** primary over TEP-as-primary or C-MAPSS:
the IPIS v2 hardware testbed is a motor-bearing rig with ADXL355 accelerometers, so a
bearing-vibration software target makes the eventual `HardwareDataRouter` bridge a drop-in
(identical features: RMS, kurtosis, crest factor, band energies). FEMTO supplies **both**
sub-tasks in one dataset; TEP supplies anomaly only (its IDV faults are step/random
disturbances, not degradation-to-failure, so it carries no RUL target — stated honestly).
Full option table and tradeoffs in ADR-015.

**FEMTO-PRONOSTIA specifics (verified).** 17 accelerated run-to-failure bearings across 3
operating conditions (1800 rpm/4000 N → 7; 1650 rpm/4200 N → 7; 1500 rpm/5000 N → 3); the
IEEE PHM 2012 Challenge defines a **6-train / 11-test** split (2 training bearings per
condition). Two accelerometers (horizontal + vertical), 25.6 kHz, 0.1 s snapshot every 10 s;
naturally degraded (all defect types co-develop) with the run terminated when vibration
exceeds **20 g** (the failure marker that defines true RUL). Naturally-degraded means
frequency signatures are weak/mixed — which is exactly why FEMTO is a RUL benchmark and not
a clean classification benchmark, and why CWRU is the diagnosis dataset.

**Physics layer (D3) — the IPIS signature for M2.** Bearing **characteristic defect
frequencies** are first-principles kinematics (geometry + shaft speed), the M2 analogue of
the VLE physics in M1. With N rolling elements, ball diameter d, pitch diameter D, contact
angle φ, shaft frequency f_r:

- FTF  = (f_r/2)·(1 − (d/D)cos φ)            (cage)
- BPFO = (N·f_r/2)·(1 − (d/D)cos φ)          (outer race)
- BPFI = (N·f_r/2)·(1 + (d/D)cos φ)          (inner race)
- BSF  = (D·f_r/2d)·(1 − ((d/D)cos φ)²)       (rolling element)

Features = energy in narrow bands around {1×, BPFO, BPFI, BSF, FTF and harmonics} from the
envelope spectrum, plus the classic time-domain set (RMS, kurtosis, crest factor, peak-freq)
that the v2 PdM MQTT topic already publishes. **Verify-before-load-bearing:** these formulas
(esp. the BSF prefactor, which appears in two forms in the literature) are pinned against
Harris, *Rolling Bearing Analysis*, and ISO 15243 at implementation, with edition-internal
fixtures — the same discipline applied to Perry's in M1.

**Failure-mode taxonomy (D4) — two layers.**

*Diagnostic (what kind):*
- Localised defects with frequency signatures: outer race (BPFO; ≈40 % of bearing failures),
  inner race (BPFI + 1× sidebands), rolling element (BSF, 2×BSF), cage (FTF).
- Shaft/assembly faults with 1×/2× harmonic signatures (the v2 fault-injection set):
  imbalance (1× radial), misalignment (1×/2× axial), looseness (harmonic series).
- Process faults (TEP cross-domain): IDV 1–21 step/random/sticking — mapped to **detection
  only**.

*Degradation stage (how far) — drives health score and RUL:*
- Stage 0 Healthy (baseline HI) → Stage 1 Incipient (HI departs baseline; lead-time clock
  starts) → Stage 2 Degradation (monotonic HI rise; RUL trackable) → Stage 3 Failure
  (FEMTO: >20 g; hardware: alarm). Injected-fault severity bins: mild/moderate/severe
  (v2: 6.2 / 12.3 / 27.7 N imbalance force, F = mω²r).

**Success metrics (D5) — numbers-first.**

*Anomaly/health:*
- AUROC (healthy vs degraded windows) **≥ 0.90** (the v2 hardware target).
- Detection lead time: incipient-fault flag at **≥ 25 % of remaining life before EOL** on
  FEMTO test bearings (and ≤ 10 min post-injection on hardware) — earlier is the value.
- False-positive rate **< 1 alarm/h** in the healthy phase (v2 target); on TEP, FDR
  maximised at **FAR < 5 %** per IDV mode (standard TEP monitoring).

*RUL:*
- **RMSE** and **MAE** (dataset time unit) on the 11 held-out FEMTO test bearings.
- **PHM 2012 Score** = mean A_i, asymmetric and bounded ≤ 1 (higher better):
  with %Er = 100·(ActRUL − RUL)/ActRUL, A_i = exp(−ln 0.5 · Er/5) for Er ≤ 0 (late /
  over-estimate, penalised harder) and exp(+ln 0.5 · Er/20) for Er > 0 (early). This is the
  benchmark headline.
- **Calibrated conformal RUL interval** — a **one-sided lower bound** on RUL with coverage
  **≥ 1−α (α = 0.10)** that holds **across all 3 FEMTO operating conditions** (regime-uniform
  coverage, the M1-style claim), width reported. The one-sided lower bound matches the
  "never over-promise remaining life" safety asymmetry — the M3 one-sided-spec insight reused.

**Contribution (the M2 headline, one claim).** *Physics-anchored, conditionally-calibrated
RUL:* a conformal lower bound on remaining useful life whose coverage holds across operating
conditions, built on first-principles bearing characteristic-defect-frequency features. It
reuses the M1 conformal/drift assets and the M3 one-sided-interval discipline (the ≈10–20 %
reuse) while making a prognosis claim neither other module makes.

**Build order (D6).** 2A (features + health + diagnosis on FEMTO/CWRU) → 2B (RUL + conformal
bound) → 2C (TEP cross-domain anomaly) → 2D (serving + state-bus). Reuse, don't re-implement:
`evaluation/conformal.py` (ACI/EnbPI/split, one-sided variant added), `evaluation/drift.py`
(ADWIN/PH/CUSUM), `evaluation/blocked_cv.py` (forward-chaining CV + one-SE — mandatory here
too: bearing degradation is non-stationary, so a temporally-adjacent split would over-state
generalisation exactly as it did in 1A), and the FastAPI/Streamlit/`state_bus` serving layer.

## Open ratification item (read first)

ADR-015 is **Proposed**. The one decision that genuinely benefits from owner sign-off before
the build is **D2 (dataset hierarchy)** — specifically electing a bearing run-to-failure
primary over the §0.5-listed TEP-or-C-MAPSS alternatives. Everything downstream (taxonomy,
metrics, physics layer) follows from that pick. Ratify D2 → start 2A.

## Datasets — acquisition note

FEMTO-PRONOSTIA and CWRU are external downloads (not yet in-repo); they get registered as
Tier-1 sources in `docs/sources/source-map.md` at first use, and live under
`data/raw/femto/` and `data/raw/cwru/` (gitignored, like all `data/raw/*`). TEP IDV runs are
reproducible from the in-repo `scripts/generate_tep_modes.py` (Russell/Braatz simulator) —
**note:** what is currently in-repo are feed-ratio operating regimes (IDV 8+10+13 as
*excitation*); canonical d00–d21 *fault-labelled* runs for the 2C anomaly task are generated
from the same simulator with the fault flags set, not committed files.

See `docs/architecture/decisions/ADR-015-module2-pdm-scope.md` for the full reasoning, and
`docs/HANDOFF.md` §0.5 for the live thread.
