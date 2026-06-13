# ADR-013 — Phase 3A: DWSIM debutanizer twin and deterministic RTO

**Status:** Accepted
**Date:** 2026-06-13
**Decision owner:** Bien Busico
**Module:** 3 (RTO) — Phase 3A (twin + deterministic RTO skeleton)
**Extends:** ADR-006 (GPR belongs in Module 3), scoping.md D1–D5 (uncertainty-aware
steady-state RTO; debutanizer twin first; DWSIM+GEKKO+CoolProp; state-bus interface)

## Context

Module 3 needs a steady-state process model to optimize against. The shortcut FUG
model (`ipis.module3_rto.column_model.ShortcutColumnModel`, Perry's 9th ed. Sec. 13)
served as the 3A skeleton's stand-in, but the 3A deliverable is a *rigorous* twin so
the RTO surrogate is fit to first-principles VLE rather than to idealized constant-α
shortcut behaviour. The twin is built in DWSIM 9.0.5 and driven from Python; the RTO
surrogate, NLP, and economics live in `ipis.module3_rto`.

Execution detoured through a DWSIM MCP server (flash-only — its prebuilt worker stubs
both column construction and case loading), then settled on **DWSIM.Automation3 via
pythonnet** (the route scoping.md anticipated), which loads the GUI-built `.dwxmz` and
becomes the committed twin-execution engine (`scripts/run_g1c.py`, `run_g2_sweep.py`,
`run_g2_analysis.py`).

## Decisions — twin fidelity (T1–T6)

**T1 — Binary n-butane / n-hexane.** Matches the Module 1 physics-bridge proxy (C4 =
LK, n-hexane = stabilized-gasoline HK), so every twin state is checkable against
`ipis.physics`. A 5-component cut re-enters only if 3B's surrogate residuals show the
binary proxy is the fidelity bottleneck.

**T2 — Peng-Robinson.** Standard for nonpolar light hydrocarbons; consistent with the
near-ideal assumption in the M1 VLE code. Verified against CoolProp at mid-envelope
(α ≈ 5.97 at 106 °C).

**T3 — 9 stages (0-indexed: condenser = 0, reboiler = 8), feed at stage 4.** N = 8
equilibrium + total condenser. At realistic stage counts the binary split at α ≈ 6 is
numerically razor-sharp and the RTO degenerate; N = 8 spans xB ≈ 0.004–0.07 across the
decision box with leverage in both R and D. Top P = 4.7 bar, column ΔP = 0.4 bar
(reboiler 5.1 bar), set on the General tab (DWSIM 9 derives the per-stage profile).

**T4 — Decision variables R ∈ [0.8, 3.0], D ∈ [33, 37] kmol/h; quality spec
xB,C4 ≤ 0.02.** The column is specified by reflux ratio (condenser) + bottoms product
molar flow (reboiler), so the RTO distillate handle D is encoded as bottoms = F − D.

**T5 — Literature-default economics, two-stream (upgrade) structure.** Overhead at the
C4 price (0.750 USD/gal, EIA/FRED MB propane 2025 floor), bottoms at the gasoline price
(2.10 USD/gal, EIA USGC 2025, flagged), steam 6.28 USD/GJ (EIA NGM 5.50 USD/Mcf / 0.80
boiler eff). The gasoline > C4 spread makes the bottoms spec ACTIVE at the optimum;
plant figures slot into `EconomicsAnchor` later.

**T6 — Quadratic ln(xB) surface → GEKKO/IPOPT NLP; duty analytic.** The only fitted
nonlinearity is ln(xB); reboiler duty and all stream flows are analytic. At 3B the
ADR-006 GPR surrogate replaces the quadratic behind the same `ColumnModel` protocol.

## Decisions — validation gates (G1–G3) and findings

**G1a — VLE consistency (PASS).** PR-vs-(M1 ideal-Raoult) bubble-point comparison across
the envelope: max deviation +3.2 °C (mid-composition, vanishing at the pure ends) — a
mild liquid non-ideality PR captures and ideal-Raoult omits. Checkpoint bands read on
the PR basis thereafter (feed ≈ 86 °C, not 83).

**V4 (stage physics-bridge) DROPPED, superseded by G1a.** DWSIM 9 does not expose
per-stage liquid compositions post-solve (Stage.l/v/Kvalues empty; pp flash needs a
material-stream context), so a stage-level check would compare a Raoult estimate against
a Raoult inversion — circular. G1a already performed the VLE-consistency check rigorously
with the real PR package. G3 = V1–V3.

**V1 — coverage semantics, not all-grid.** The sweep grid deliberately explores beyond
nominal, so requiring every point in the [100, 112] °C envelope is the wrong test. V1
passes iff a *spec-feasible* operating region sits inside the envelope, and reports the
map plus feasible HOT exits as the 3B motivation.

**Headline finding — the twin earns its keep.** At the master case (R = 1.5, D = 34.5)
the rigorous twin gives xB = 0.0243 > 0.02 spec — INFEASIBLE — whereas the shortcut said
0.0124 (feasible). The rigorous PR split is less sharp; the RTO feasible region shifts to
higher R / lower D than the shortcut implied.

**Deterministic optimum is M1-valid.** On the 15-row twin surface (R² = 0.996, ×1.13
residual band — smoother than the shortcut's ×1.74), the RTO optimum is R* ≈ 2.70,
D* ≈ 33.7 at sensor-stage T ≈ 101.4 °C, inside the M1 envelope. The feasible HOT
envelope exits (sensor > 112 °C) occur only at over-purified high-R/high-D corners the
economics never select — these are the concrete 3B hook (the economically-tempting
high-reflux region pushes the sensor out of its trained envelope). Profit gradient
≈ 2.7–5.2 USD/h per 0.001 back-off (≈ 2–3× the shortcut's, because the tighter feasible
region raises the back-off stake).

## Consequences

- **run_015 dropped.** At R = 3.0 / B = 65.5 (high-purity, over-refluxed) DWSIM's
  Wang–Henke solver at 1e-5 tolerance reaches no mass-balance-closing steady state and is
  initialization-path-dependent; the fine-stepped result failed V2 by 1.4%. Dropped (15
  rows ≥ 12 needed; the corner is covered by runs 13–14 and never visited by the RTO). V2
  caught it — the harness working as intended.
- **3B sampling caveat.** The same solver instability will appear inside the ADR-006
  GPR-over-DWSIM expected-improvement loop; sampling the high-purity corner must use
  continuation + per-point mass-balance screening.
- The DWSIM MCP server is retired after G1a (flash-only). DWSIM.Automation3 (pythonnet
  3.1.0, .NET Fx 4.8, ipis env) is the twin-execution engine; `pythonnet` is now part of
  the ipis environment.
- A full BUILD-FROM-SCRATCH Automation twin (no `.dwxmz` binary dependency) remains parked
  for the publication-reproducibility freeze.
