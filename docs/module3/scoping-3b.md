# Phase 3B — Scoping: uncertainty-aware RTO (the paper-2 contribution)

> Status: DRAFT for ratification, 2026-06-13. Decisions at option scale before code,
> per house style. Builds on 3A (ADR-013): rigorous twin, deterministic RTO, spec
> active at the optimum, profit gradient 2.7–5.2 USD/h per 0.001 back-off, and the
> finding that the economically-tempting high-reflux region pushes the soft sensor out
> of its trained envelope. Extends ADR-006 (GPR in Module 3), ADR-010 (conformal),
> scoping.md D1-C/D4/D5.

## The thesis in one line

In 3A the constraint back-off was a **fixed margin** (we swept b ∈ {0, 0.0025, 0.005,
0.010}). In 3B it becomes the **calibrated conformal half-width of the soft-sensor
estimate of xB** — adaptive, distribution-free, and tighter exactly where the sensor is
sharp. Claim: an interval-driven back-off achieves higher profit than any fixed margin
**at the same constraint-violation rate**, because the sensor's uncertainty is
heteroscedastic across the operating box (3A evidence: intervals widen at the high-R
envelope exits). The deliverable is that profit delta, measured on the twin.

## Data flow (what "the RTO sees" vs ground truth)

```
twin (R,D) ──► tray-6 T  ──► M1 conformal soft sensor ──► (ŷ_xB , C)  ──► RTO chance
   │                                                                        constraint
   └────────────────────────► TRUE xB  ────────────────► VIOLATION check (true xB > spec)
```
The RTO never sees true xB — only the sensor estimate ŷ and its half-width C. Violations
are scored against the twin's true xB. This is the whole point: the interval must pay for
the sensor's imperfection without over-paying.

## D1 — Chance-constraint formulation

| option | form | tradeoff |
|---|---|---|
| **A. One-sided conformal UCB (RECOMMEND)** | ŷ + C⁺ ≤ spec, C⁺ = one-sided conformal upper bound at 1−α | Distribution-free coverage; one-sided (the spec is one-sided xB≤0.02) so C⁺ < the symmetric two-sided half-width — less conservative *for free*. Uses `conformal_quantile` on signed residuals / `enbpi_offsets` upper leg. |
| B. Gaussian parametric | ŷ + z_{1−α}·σ ≤ spec | Simpler, but assumes Gaussian residuals — forfeits the distribution-free guarantee that is the headline. |
| C. Scenario / robust | worst-case over an uncertainty set | Most conservative; collapses toward a fixed margin — the baseline, not the contribution. |

Recommend **A**, and specifically the **one-sided** bound: the constraint is xB ≤ spec,
so we need an upper bound on true xB, not a symmetric interval. This is both correct and
strictly less conservative than a two-sided half-width — it widens the expected profit gain.

## D2 — Which sensor, and how it attaches to the twin

| option | tradeoff |
|---|---|
| A. Literal Module-1 (Debutanizer-trained) weights on the twin | Disjoint input spaces (the Module 1 C6 lesson) — the twin's tray-6 T need not lie in the Debutanizer model's domain; intervals become meaningless extrapolation. Reject. |
| **B. M1 conformal-soft-sensor METHODOLOGY calibrated on twin data (RECOMMEND)** | The Module 1 *recipe* — physics-anchored feature (tray-6 T via bubble-point inversion) + conformal intervals — rebuilt on twin (tray-6 T → xB) pairs. Methodology transfer, the house pattern (1C). Self-consistent uncertainty; sidesteps the disjoint-space trap. |
| C. Synthetic noise model on true xB | Too artificial — the uncertainty wouldn't reflect a real sensor's structure. |

Recommend **B**. The sensor's mean can be the physics bridge (bubble-point inversion) or a
light ML map; the conformal layer is calibrated on held-out twin residuals.

## D3 — Interval engine and coverage

| option | tradeoff |
|---|---|
| Split conformal (`SplitConformal`) | Simplest; valid under exchangeability. Honest baseline if the RTO operates at quasi-static setpoints. |
| **Adaptive CI (`ACIConformal`, RECOMMEND)** | Maintains long-run coverage under the operating-point shift the RTO induces as it moves setpoints; consistent with Module 1's choice. `select_gamma` tunes the step. |

Recommend **ACI**, one-sided, target **1−α = 0.90** (per scoping D1-C), with empirical
coverage validated on the twin via `marginal_coverage` / `rolling_coverage` before any
profit claim. **Coverage is a gate, not a footnote** — if the twin-sensor intervals don't
hit 90%, the chance constraint is void and the profit comparison is meaningless.

## D4 — Head-to-head experiment (the results section)

Compare profit **at equal constraint-violation rate** — not raw profit (which any reckless
margin can inflate).

- **Fixed-margin baseline (3A):** sweep b → trace the (violation rate, profit) frontier.
- **Interval-driven (3B):** sweep α → trace its own (violation rate, profit) frontier.
- **Headline:** the interval-driven frontier Pareto-dominates; and at the violation rate
  the 90% guarantee delivers, report the profit delta vs the fixed margin giving the same
  violation rate.
- **Violation** = twin TRUE xB > spec at the RTO-recommended setpoint, over the scenario
  ensemble (D5).

Recommend the **Pareto-frontier comparison** with the 90%-coverage operating point called
out as the headline number.

## D5 — Surrogate and disturbance ensemble

| piece | decision |
|---|---|
| In-loop twin model | **GPR over the twin** (ADR-006), replacing the 3A quadratic; 3B.1 verifies it reproduces the 15-row surface and the R*≈2.70/D*≈33.7 optimum. **High-purity caveat (3A):** sample with continuation + per-point mass-balance screening — the DWSIM solver is initialization-sensitive in the over-refluxed corner. |
| Disturbance / scenario ensemble | Vary feed composition z (and/or measurement-noise realizations) across a set of scenarios so the violation rate is a meaningful frequentist statistic, not a single point. |

**Win condition, stated honestly:** interval-driven beats fixed-margin **iff the sensor
uncertainty is heteroscedastic** across the box. 3A evidence says it is (intervals widen
at the high-R envelope exits), but the gain magnitude must be **measured, not assumed** —
if the twin-sensor turns out near-homoscedastic, the delta shrinks toward zero and we
report that honestly.

## D6 — Build order (sub-gates, open-loop)

- **3B.1** — GPR surrogate over the twin; verify it reproduces the 3A surface + optimum.
- **3B.2** — conformal soft sensor on the twin (tray-6 T → xB, one-sided ACI); validate
  90% coverage; wire the chance-constraint solve through `OperationalState`.
- **3B.3** — head-to-head: fixed-margin vs interval-driven frontiers; profit delta at
  equal violation rate.

3B stays **open-loop** (the RTO recommends setpoints; it does not close the loop). The
Shardt closed-loop integrator is deferred to **3C** per scoping D5.

## The prize (order-of-magnitude, to be measured)

At the 3A gradient (≈3 USD/h per 0.001 back-off) a saved back-off of ~0.003 at equal
safety is ≈ 8–16 USD/h ≈ **$70–140k/yr** at the literature anchors. This is the quantity
3B.3 measures; it is contingent on the heteroscedasticity above, so the scoping commits to
*measuring* it, not to a number.

## Asks before 3B.1 starts

1. Ratify D1–D6 (or amend).
2. Confirm the one-sided UCB framing (D1-A) over a two-sided interval.
3. Confirm the sensor is the M1 methodology calibrated on the twin (D2-B), not literal
   Debutanizer weights.
4. Pick the disturbance ensemble (D5): feed-z variation, measurement-noise realizations,
   or both — this sets what "violation rate" is averaged over.
5. Confirm 3B stays open-loop (Shardt integrator parked for 3C).
