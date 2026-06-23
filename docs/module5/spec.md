# Module 5 — Dynamic / physical realization (spec)

Status: ACTIVE. Increment 1 complete. One session per module; this is Module 5.

## Goal

Move IPIS off the quasi-static FUG/GP twin onto a DYNAMIC, physically realistic loop
(real actuator and measurement dynamics + transport lags) and upgrade the per-cycle
composed coverage certificate (Module 4, Theorem 1) to a LONG-RUN / HORIZON coverage
guarantee under feedback-induced dependence, via adaptive conformal inference (ACI;
Gibbs & Candes 2021, already in the M1 serving stack).

## Ratified decisions

- **Plant choice: (b) -> (a).** Build the in-sandbox dynamic loop first (primary,
  reproducible vehicle); DWSIM-dynamic follows as the high-fidelity confirmation and the
  place open item O3 (tray-efficiency re-pin) is resolved. Rationale: the horizon-coverage
  claim is distribution-free, so it is plant-fidelity-agnostic for *validity*; the
  in-sandbox loop iterates ~10-50x faster for the ACI step-size sweep and O1 analysis and
  ships in CI. (b) proves the claim; (a) strengthens the story.

- **Dynamic-plant design: Hammerstein-class, GP gain + transport dynamics**
  (`src/ipis/integration/dynamic_plant.py`). This REVERSES the earlier "from-scratch
  CMO + constant-alpha stage model" sketch (see ADR-017). The M4 plant truth is the
  Module 3 GP surface `xb_truth(R, D, z)`; a mechanistic stage model would disagree with
  both that surface and DWSIM and force a full re-pin of the certificate calibration
  (alpha_1, alpha_2, psi-budget). Instead we keep the validated GP surface as the static
  gain and wrap it in linear transport dynamics. By construction the settled steady state
  reproduces the M4 twin exactly (test asserts xb_true and sensor_temp to rel 1e-6), so
  the certificate machinery transfers with at most the O3 re-pin.

## Transport elements (each pinned to the column at draft time)

| Element | Symbol | Default | Source class | Effect on the loop |
|---|---|---|---|---|
| Actuator / flow-loop lag on (R, D) | `tau_act` | ~1 min | valve stroke + flow loop | `psi` evolves over the REALIZED path, not the commanded step |
| Composition settling | `tau_proc` | ~30 min | column holdup / throughput | RTO acts on a lagged composition |
| Sensor-stage temperature | `tau_temp` | ~15 min | tray thermal response | M1 feature is a lagged temperature |
| Analyzer deadtime | `deadtime_h` | ~5 min | GC cycle | the M1 label (and thus ACI) arrives DELAYED |

Defaults are illustrative orders of magnitude (verify-before-load-bearing). The plant's
integration timestep `dt` (default ~1 min) is fixed; one `step` advances the dynamics by
`dt` and accrues exactly `dt` of pump degradation (the plant aligns `PumpDegradation.dt`
to its own clock). The RTO/decision interval is many `dt` steps and is the orchestrator's
concern (increment 2).

## Increment plan

1. **DONE — dynamic plant + recorder.** `dynamic_plant.py`
   (`DynamicDebutanizerPlant`, `DynamicPlantOutput`, `first_order_step`) and
   `recorder.py` (`CampaignRecorder`, `CampaignSample`). 20 unit tests
   (`tests/unit/test_dynamic_plant.py`, `test_recorder.py`), incl. the load-bearing
   steady-state-consistency check vs the M4 static twin, actuator/process/deadtime
   behavior, and psi-on-realized-path. `DynamicPlantOutput` satisfies the `PlantOutput`
   protocol structurally, so the M4 orchestrator/feature-transform/coverage consume it.
2a. **DONE — dynamic orchestrator + ACI horizon read-off + O1 under deadtime.**
   `src/ipis/integration/dynamic_orchestrator.py`
   (`DynamicClosedLoopOrchestrator`, `DynamicCycleRecord`): holds `u_k` across
   `steps_per_cycle` plant steps, routes the cycle-delayed label (`label_delay_cycles` =
   `D_a`) to M1's `ACIConformal`, evaluates `S_k`, records every cycle via
   `CampaignRecorder`. Records are `CycleRecord`-compatible, so the proven `run_coverage`
   Wilson harness measures horizon coverage directly. 26 Module-5 tests pass; existing
   integration cluster unaffected (54 passed, 2 skipped). Results at `D_a = 2`,
   `alpha_1 = alpha_2 = 0.10`, `eps = 0.05` (floor 0.75): M1 ACI interval coverage of `x_k`
   over 400 cycles = **0.900** (target 0.90); `S_k` over 3 x 120 cycles = **1.000**, Wilson
   lower bound **0.989** >= floor. O1 re-verified: `Delta_sel = 0` preserved under deadtime,
   cost moves to the ACI rate not validity (`docs/module5/o1-deadtime-timing.md`).
2b. **DONE — sweeps and figures.** `src/ipis/integration/horizon_experiments.py`
   (`two_arm_contrast`, `deadtime_sweep`, `gamma_sweep`) over a reusable dynamic demo loop
   `src/ipis/integration/dynamic_demo.py` (delayed-ACI soft sensor + capped back-off RTO).
   `scripts/run_horizon_sweeps.py` emits the three figures (`docs/module5/figures/`) and
   frozen evidence (`docs/paper/evidence/module5_horizon_sweeps.json`). 4 experiment tests
   pass (62 passed, 1 skipped across Module 5 + regression). Results (`alpha_1=alpha_2=0.10`,
   `eps=0.05`, floor 0.75):
   - **Figure 1 / two-arm (headline):** both arms meet the quality spec (q=1.000), but the
     health-blind RTO over-refluxes and projected RUL falls below the floor (rul=0.008), so
     `S_k = 0.008` (meets_floor False); the conformal health-constrained loop holds
     `S_k = 1.000`, Wilson lower 0.989 (meets_floor True). The cap (not `eps`) selects the
     arm; both are scored against the same floor.
   - **Figure 2 / deadtime:** `S_k = 1.000` for every `D_a in {0,1,2,4,8}` — validity
     invariant to deadtime, as O1 predicts; interval coverage holds ~0.90 throughout.
   - **Figure 3 / gamma + union bound:** interval coverage stays near 0.90 across `gamma`
     with the half-width shrinking as `gamma` rises; the naive K-cycle Bonferroni interval
     is vacuous (infinite) at `K >= 50`, where ACI keeps a finite ~0.0011 half-width.
3. **THEN — paper (NEXT).** Draft Paper 5 around the three figures. Venue option-scaled at
   draft time (JPC / Control Engineering Practice / IEEE TCST, or CACE/IECR for the PSE angle).

## Open items carried

- **O1** causal timing under deadtime — re-verify (increment 2). 
- **O3** tray-efficiency re-pin (O'Connell at actual alpha(T), mu_L(T)) — matters more in a
  dynamic twin; resolved at the DWSIM-dynamic confirmation (plant choice (a)).
- ACI step-size / learning-rate tuning for the horizon target (increment 3).

## Visualization & dissemination track (parallel; added 2026-06-23)

Viz maturity tracks module maturity. Register is HMI / CAD (operator-training-simulator
look), professionally simple. Characters are human operators / scale figures and the
walkthrough POV ONLY — never cartoon mascots representing the modules; the modules stay
instrumented stations and panels. End state: a research monograph (book) with the
interactive twin as its companion.

| Tier | Form | Rides on | Gated to |
|---|---|---|---|
| V1 | interactive 2D operations schematic, hover-for-parameters, animated over a campaign | `CampaignRecorder` (built) | Module 5 |
| V2 | multi-unit 2D operations board + first 3D CAD walkthrough (scale figures) | V1 + plantwide composition | plantwide milestone |
| V3 | immersive 3D twin over real/emulated DCS; the book's companion | V2 + real-plant data | real-plant / book |

`CampaignRecorder.to_records()` is the V1 data contract (JSON rows); `to_arrays()` is the
analysis/plotting contract. The recorder is deliberately decoupled from M1/M2/certificate
so the same log feeds the viewer and the horizon analysis.

## Files (increment 1)

- `src/ipis/integration/dynamic_plant.py`
- `src/ipis/integration/recorder.py`
- `tests/unit/test_dynamic_plant.py`
- `tests/unit/test_recorder.py`
- `docs/module5/spec.md` (this file)
- `docs/architecture/decisions/ADR-017-module5-dynamic-plant-hammerstein.md`
