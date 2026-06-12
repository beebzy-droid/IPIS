# Module 3 — RTO: scoping (D1–D5 for ratification)

> Status: OPEN, awaiting ratification per decision. Standing inputs: Module 3 = RTO,
> "constrained setpoint recommendations" (HANDOFF module map); GPR surrogate belongs
> here (ADR 006); Shardt closed-loop integrator (Eq. 6/10) deferred here; MATLAB
> confirmed IN; gPROMS candidacy to be decided NOW; digital-twin layer = DWSIM +
> GEKKO + CoolProp; Module 1 delivers calibrated soft-sensor estimates with valid
> conformal intervals.

## D1 — What "RTO" means in IPIS scope

| option | description | tradeoff |
|---|---|---|
| A. Steady-state RTO | Classic two-step: twin reconciled to plant state → constrained economic optimization → setpoint recommendation at a slow cadence (hours) | Industry-standard, matches "setpoint recommendations" wording; ignores transients |
| B. Dynamic RTO / eMPC | Optimize trajectories over a dynamic model | Much heavier modeling + solver burden; duplicates what plant MPC layers do; M1's integrator deferral suggests control was always a later concern |
| **C. Steady-state RTO with uncertainty-aware constraint back-off (RECOMMENDED)** | Option A, but constraint margins are set from Module 1's *calibrated conformal intervals* — the soft-sensor's honest uncertainty becomes the back-off, replacing ad-hoc safety margins | Same solver burden as A; converts Module 1's headline capability (validity) into economic value; this is the second-paper hook — uncertainty-aware RTO with distribution-free guarantees is publishable in its own right |

**Recommendation: C.** It is A plus exactly one idea, and that idea is the one
Module 1 uniquely enables. The quantitative claim it sets up: back-off width = f(ACI
interval) → less conservative than worst-case margins, still 0.90-valid → measurable
profit delta vs fixed-margin RTO on the same twin.

## D2 — Process scope and first target

| option | description | tradeoff |
|---|---|---|
| **A. Debutanizer twin first (RECOMMENDED)** | DWSIM steady-state column twin (n-butane/stabilized-gasoline split, CoolProp/DIPPR props already in repo); optimize reflux/duty against C4-spec constraint, M1 sensor closing the quality loop | The physics, the lag, the sensor, and the VLE code all exist; smallest credible RTO |
| B. TEP first | Bathelt closed-loop Simulink plant; richer constraints | TEP economics are canned; the Simulink plant is a *dynamic* target — better as the M3 stress test than the first build |
| C. Both from day one | — | Violates the build-small-close-formally pattern that worked for M1 |

**Recommendation: A then B** — debutanizer twin for 3A/3B, TEP-in-Simulink as the
3C transfer/closed-loop case (mirrors the M1 Debutanizer→TEP arc, which the paper
narrative already established as the house style).

## D3 — Optimization + twin stack

| component | option | verdict |
|---|---|---|
| Steady-state twin | DWSIM (in stack) | IN — free, scriptable via Python automation |
| Equation-oriented optimization | GEKKO (in stack) | IN — IPOPT under the hood, handles the constrained economic NLP |
| Property layer | CoolProp + existing `ipis.physics` (DIPPR-101, bubble point) | IN — reuse |
| Surrogate over the twin | GPR per ADR 006 | IN at 3B — DWSIM eval is slow inside an optimizer loop; GPR surrogate + expected-improvement style refinement is the ADR-006 plan landing where it was always meant to |
| MATLAB/Simulink | Bathelt TEP plant + control-loop experiments | IN (confirmed) — its role is the 3C closed-loop testbed and the Shardt integrator validation, NOT the optimizer |
| **gPROMS** | Custom equation-oriented modeling + parameter estimation | **OUT (RECOMMENDED)** — licensing cost, and nothing load-bearing it adds over DWSIM+GEKKO+MATLAB for this scope. Revisit trigger: if 3B's surrogate-over-DWSIM proves too slow/inaccurate AND the twin must go equation-oriented dynamic, gPROMS (or Pyomo+DAE as the free alternative) re-enters |

## D4 — Module 1 → Module 3 interface

| option | description | tradeoff |
|---|---|---|
| A. Point estimate only | RTO consumes ỹ_t | Discards M1's distinguishing output |
| **B. Estimate + interval via the state bus (RECOMMENDED)** | `ipis.shared.state_bus` carries (ỹ_t, C_t, drift-alarm flag); RTO maps interval width → constraint back-off and treats a drift alarm as an RTO hold | The bus types (HealthFlag/ModuleStatus/OperationalState) were built for exactly this; first real consumer of the M1 serving layer |
| C. Full residual window | RTO re-derives its own uncertainty | Duplicates M1; violates module boundaries |

**Recommendation: B.** Also defines the 3C trigger for the deferred Shardt
integrator: it enters only when the RTO recommendation is allowed to close the loop.

## D5 — Build order

- **3A — Twin + deterministic RTO (the skeleton):** DWSIM debutanizer twin validated
  against the dataset's operating envelope; GEKKO economic NLP (maximize C4 recovery
  value − energy cost s.t. spec); fixed-margin back-off baseline. Closeout: twin
  validation table + one optimization case study, ADR for the twin fidelity choices.
- **3B — Uncertainty-aware RTO (the contribution):** M1 intervals → chance-style
  back-off; GPR surrogate (ADR 006) for in-loop twin evaluation; head-to-head
  vs 3A's fixed margins (profit delta at equal constraint-violation rate). This is
  paper 2's results section.
- **3C — Closed-loop on TEP (the stress test):** Bathelt Simulink plant; RTO
  recommendations applied; Shardt closed-loop integrator validated; regime shifts
  from M1's own TEP regimes reused as the disturbance script.
- Gates carried: 1D.4 (OT bus) naturally merges into 3C's plumbing; 1D.5 (nonlinear
  source) stays review-triggered and independent.

## Asks before 3A starts

1. Ratify D1–D5 (or amend).
2. Confirm DWSIM is installable on the Windows box (GUI app + `DWSIM.Automation`
   from Python; sandbox cannot run it — validation splits sandbox/owner like M1 data
   runs did).
3. One number to anchor 3A's economics: a representative price/cost pair (C4 product
   value vs reboiler energy cost) — literature defaults acceptable if you'd rather
   not source plant-realistic figures.
