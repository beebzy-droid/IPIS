# ADR-017 — Module 5 dynamic plant: GP gain + transport dynamics (Hammerstein), not a mechanistic stage model

Status: Accepted (2026-06-23). Supersedes the informal "CMO + constant-alpha dynamic
stage model" sketch raised at Module 5 option-scale.

## Context

Module 5 lifts the per-cycle composed coverage certificate (M4, Theorem 1) to a horizon
guarantee on a dynamic loop. This requires a dynamic plant. At option-scale a from-scratch
mechanistic dynamic stage model (constant molar overflow + constant relative volatility)
was sketched as the column.

Reading the M4 plant code (`src/ipis/integration/plant.py`) corrected a wrong assumption:
the M4 "column" is NOT a mechanistic model. `DebutanizerPlant.step(R, D)` returns the
truth from an injected Module 3 GP surface `xb_truth(R, D, z)` (a DWSIM-fit
`TruthSurface3D`), plus a `(R, D) -> tray-T` surface. The Perry thermo (Underwood
minimum reflux, O'Connell efficiency, stripping factor) are consistency DIAGNOSTICS, not
governing equations (the code's own scope note says so; see open item O3). The certificate
calibration (alpha_1, alpha_2, the psi-budget Lipschitz constants) was fitted against THIS
GP twin.

## Decision

Build the dynamic plant as a **nonlinear-static + linear-dynamic (Hammerstein-class)
block**: keep the validated GP steady-state surface as the static gain, and wrap it in
linear transport dynamics — a first-order actuator lag on the decisions `(R, D)`, a
first-order process lag on the composition and sensor-temperature response toward the GP
steady state at the realized `(R, D)`, and an analyzer deadtime FIFO on the measured
quality. Pump degradation (`PumpDegradation`) is reused unchanged, driven by the realized
reflux flow, with its timestep aligned to the plant's integration timestep.

Implementation: `src/ipis/integration/dynamic_plant.py`
(`DynamicDebutanizerPlant`, `DynamicPlantOutput`).

## Alternatives considered

- **From-scratch mechanistic stage model (CMO + constant-alpha).** Rejected. Its steady
  state would equal neither the GP twin nor DWSIM, introducing a THIRD inconsistent plant
  and forcing a full re-pin of the certificate calibration. Higher effort, breaks
  continuity with M4, and buys nothing for the horizon-coverage claim, which is
  distribution-free and therefore independent of the plant's mechanistic fidelity.
- **DWSIM-dynamic as the primary vehicle.** Deferred to the confirmation step (plant
  choice (a) in the Module 5 spec): out of sandbox, slow to iterate for the ACI sweep, and
  ships only static trajectory files rather than a CI-rerunnable artifact.

## Consequences

- **Positive.** The settled steady state reproduces the M4 twin exactly
  (`test_steady_state_matches_static_twin`: `xb_true` and `sensor_temp` to rel 1e-6), so
  the composed-certificate machinery transfers with at most the O3 tray-efficiency re-pin.
  Transport lags are first-class and citable. Fully in-sandbox and CI-testable. `psi`
  evolves over the realized (lagged) path, exactly the continuous departure Module 5 needs
  to charge. The deadtime-delayed `xb_measured` is the delayed ACI label; `xb_true` is the
  coverage ground truth — the two are exposed separately for increment 2.
- **Negative / watch.** The dynamics are reduced-order (lumped first-order lags + deadtime),
  not a tray-resolved transient; defensible in a control/PSE venue with cited time
  constants, and the DWSIM-dynamic confirmation (a) backstops fidelity. Time constants are
  illustrative defaults to be pinned to the column. The O1 (`d_sel = 0`) argument must be
  re-verified under deadtime in increment 2 — deadtime changes which residuals ACI sees and
  can in principle re-open the co-selection window.

## Validation

20 unit tests (`tests/unit/test_dynamic_plant.py`, `tests/unit/test_recorder.py`), all
passing; existing integration cluster (54 passed, 2 skipped) unaffected — additive change,
no existing file modified.
