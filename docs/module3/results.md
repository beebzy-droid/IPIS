# Module 3 — Results

## Phase 3A — DWSIM debutanizer twin + deterministic RTO

*Status: **complete** (ADR-013). Steady-state twin built in DWSIM 9.0.5 (Peng-Robinson,
binary n-C4/n-C6), driven via DWSIM.Automation3/pythonnet; RTO surrogate + GEKKO NLP in
`ipis.module3_rto`. Gates G1a/G1b/G1c/G2/G3 PASS.*

### Summary
A rigorous Peng-Robinson debutanizer column (9 stages, total condenser, feed stage 4,
4.7→5.1 bar) was built in DWSIM as the steady-state twin for the RTO, replacing the
Phase-3A shortcut FUG stand-in. The twin was validated against the Module 1 physics
bridge (G1a: PR-vs-ideal-Raoult bubble-point agreement ≤ 3.2 °C across the column
envelope, the deviation a mild liquid non-ideality PR captures and the M1 code omits),
loaded and solved through a committed `DWSIM.Automation3` script, and swept over the
R × D decision box (16-run grid). A quadratic ln(xB) surface fit to the **real PR**
bottoms compositions (R² = 0.996, ×1.13 residual band — smoother than the shortcut's
×1.74) feeds a GEKKO/IPOPT economic NLP that maximizes a two-stream upgrade objective
(overhead at the C4 price, bottoms at the gasoline price) subject to xB,C4 ≤ 0.02.
**The twin changed the answer:** the shortcut's master operating point (R = 1.5, D =
34.5) is spec-feasible on the shortcut (xB = 0.0124) but INFEASIBLE on the rigorous
twin (xB = 0.0243 > 0.02) — the PR split is less sharp, so the RTO feasible region
shifts to higher reflux / lower distillate. The deterministic optimum (R* ≈ 2.70,
D* ≈ 33.7) sits at sensor-stage T ≈ 101.4 °C, inside the M1 soft-sensor envelope, so the
3A RTO is self-consistent with the Module 1 sensor's region of validity.

### Data
DWSIM 9.0.5 steady-state twin, `data/raw/dwsim/debutanizer_3a.dwxmz` (gitignored).
Feed 100 kmol/h, z(n-C4) = 0.35, saturated liquid, 4.8 bar. 16-run sweep over
R ∈ {0.8, 1.5, 2.2, 3.0} × D ∈ {33, 34.5, 36, 37} kmol/h (bottoms = 100 − D as the
reboiler product-molar-flow spec; reflux ratio as the condenser spec). One run
(run_015, R = 3.0 / B = 65.5) dropped: in the high-purity, over-refluxed regime the
Wang–Henke solver reaches no mass-balance-closing steady state at 1e-5 tolerance and is
initialization-path-dependent — its fine-stepped result failed the V2 closure check by
1.4%. The remaining **15 rows** exceed the 12-point surrogate minimum; the dropped
over-purified corner is bracketed by runs 13–14 and is never selected by the RTO. Master
row reproduces G1c to the decimal (xB 0.0243, xD 0.9684, duty 609.3 kW).

### Metrics

| quantity | value | basis / note |
|---|---|---|
| G1a VLE agreement (PR vs M1 Raoult) | ≤ +3.2 °C | max at mid-composition, → 0 at pure ends |
| master case duty (twin vs shortcut) | 609.3 vs 621 kW | 1.9% — independent twin confirmation |
| ln(xB) surface fit (15 rows, real PR) | R² 0.996, ×1.13 band | shortcut was R² 0.98, ×1.74 |
| RTO optimum | R* 2.70, D* 33.7 kmol/h | rides the xB = 0.02 spec |
| optimum sensor-stage T | 101.4 °C | IN the M1 envelope [100, 112] |
| profit gradient | 2.7–5.2 USD/h per 0.001 back-off | vs ~1.9 on the shortcut |
| validation | V1–V3 PASS | V4 dropped (superseded by G1a) |

### Observations
- The bottoms quality spec is **active** at the economic optimum, as designed: the
  two-stream upgrade economics (gasoline > C4 per kg) pull the column to retain C4 in
  the bottoms right up to the 0.02 limit, so back-off width carries a direct, measurable
  profit cost — the lever Phase 3B converts from a fixed margin into an interval-driven one.
- The rigorous twin gives a **smoother** surrogate surface than the idealized shortcut,
  which modestly softens (does not remove) the ADR-006 case for a GPR surrogate at 3B.
- The deterministic optimum being M1-envelope-valid means the 3A RTO can be trusted
  standalone; the coupling value is at the margins the optimizer is tempted toward.

### Unexpected findings
- **Feasibility inversion.** The single most consequential number: the operating point
  that looked comfortably feasible on the shortcut (xB = 0.0124) violates the spec on the
  rigorous twin (xB = 0.0243). This is the twin justifying its own existence — an RTO
  tuned on the shortcut would have recommended an infeasible setpoint.
- **The 3B motivation surfaced from the validation, not by design.** Mapping the sweep
  against the envelope showed that every *cold* envelope exit (sensor < 100 °C) coincides
  with spec-infeasibility (the RTO never operates there), while the only *feasible* exits
  are HOT (sensor > 112 °C) at over-purified high-reflux corners. The economically-tempting
  high-R region is exactly where the soft sensor leaves its trained envelope — a concrete,
  quantified argument for uncertainty-aware back-off that the deterministic 3A study
  produced as a by-product.
- **Solver instability is regime-specific.** DWSIM's column solver is well-behaved across
  the RTO-relevant region but loses single-steady-state resolution in the high-purity
  over-refluxed corner — a caveat that now governs the 3B GPR-over-DWSIM sampling plan
  (continuation + mass-balance screening required there).

## Phase 3B — Uncertainty-aware RTO (paper-2 contribution)

*Status: **machinery complete, awaiting twin data.** 3B.1 (GPR surrogate) and
3B.2 (conformal soft sensor) built and gated on synthetic stand-ins; 3B.3
(head-to-head harness) built. Real magnitude pending the DWSIM feed-z campaign
(`twin_runs_zvaried.csv`). Numbers marked **[pending]** fill when that lands.*

### Summary
Phase 3A's constraint back-off was a fixed margin chosen by the engineer. Phase
3B replaces it with the **calibrated conformal half-width of the soft-sensor
estimate of the bottoms C4 fraction**: the RTO subtracts from the spec an
operating-point-dependent upper bound earned from data, not a hand-set constant.
The contribution is stated in two tiers, primary first:

1. **Calibrated risk control (the robust claim).** The conformal soft sensor
   delivers distribution-free, guaranteed ~90% one-sided coverage of the true
   bottoms quality *without a priori knowledge of the heteroscedastic
   uncertainty field*. Carried into the RTO chance constraint
   (`y_hat + C+ <= spec`), this produces setpoints that respect a target
   violation rate by construction. A fixed-margin baseline can match a target
   violation rate only if the correct margin is known in advance — which
   presupposes exactly the uncertainty structure the conformal layer estimates
   from data. This advantage holds regardless of the profit comparison.

2. **Profit at matched violation rate (the conditional claim).** Where the
   operating geometry permits — genuine (R, D) freedom *and* low-sensor-
   uncertainty regions that are also profitable — the heteroscedastic back-off
   attains higher profit than the best fixed margin at the same violation rate.
   This is **measured, not assumed**: the harness traces both Pareto frontiers
   and reports the matched-violation delta. The magnitude is conditional and may
   be modest; on an effectively 1-D setpoint problem the two frontiers coincide.

### Data
- Nominal twin surface (z=0.35): the 15-row `twin_runs.csv` (Phase 3A) -> GPR
  `(R,D)->xB` and `(R,D)->tray-6 T` (3B.1).
- Feed-z campaign **[pending]**: `R x D` grid at feed z in {0.30,...,0.40} ->
  `twin_runs_zvaried.csv`, supplying (i) the conformal sensor's calibration
  residuals (tray-6 T -> xB scatter from the unmeasured z disturbance) and (ii)
  the 3-D truth surface `xB(R,D,z)` used to score violations.
- Disturbance ensemble: feed composition z (primary, unmeasured; ±0.05 about
  0.35) + tray-6 measurement noise sigma ~ 0.75 C. Rationale: feed-z is the
  dominant real debutanizer disturbance and is unmeasured, so the single-feature
  sensor genuinely cannot resolve it — the regime where empirical conformal
  intervals beat closed-form noise propagation.

### Metrics

| quantity | value | note |
|---|---|---|
| 3B.1 GPR ln(xB) fit (15 pts) | R^2 1.0, monotone | reproduces 3A optimum (profit within 1.4 USD/h) |
| 3B.1 GPR vs quadratic | ~equal on binary surface | GPR value = variance + flexibility, not fit gain |
| 3B.2 one-sided coverage | 0.90 (synthetic, mean of seeds) | **[pending]** real value on z-campaign |
| 3B.2 width heteroscedasticity (CV) | ~0.23 (synthetic) | >0 required; cliff width ~2x sharp-region |
| 3B.3 profit delta @ matched violation | **[pending]** | synthetic with consistent surfaces: +6.6 USD/h (favourable geometry) to ~0 (1-D geometry) |
| coverage as a gate | enforced | scoping D3; no profit claim until coverage holds |

### Observations
- The interval-driven mechanism is the *adaptivity*, not the conformal label:
  plain split conformal yields a constant width — identical to a fixed margin —
  so any advantage comes entirely from the local scale model `sigma_hat(x)`
  making the back-off heteroscedastic (tight where the sensor is sharp, wide at
  the cliff / outside the trained envelope).
- The RTO optimum sits in the high-reflux region, which is where the sensor is
  sharpest (over-purified column, weak feed-z sensitivity), so the interval-
  driven back-off there is small relative to a worst-case fixed margin — the
  source of any profit upside.
- Coverage is a random variable centred on the target; single-split estimates
  scatter (±~0.03 at the campaign's calibration size), so the gate reads a
  finite-sample band, not a single exceedance.

### Unexpected findings
- **The frontiers can coincide.** When the setpoint decision is effectively 1-D
  (violation monotone in one effective variable, here reflux), every back-off
  scheme that hits a target violation rate selects ~the same setpoint and earns
  the same profit — the scheme changes only the parameterization (b vs alpha),
  not the achievable frontier. The interval-driven *profit* win is therefore
  conditional on multi-D setpoint freedom and on low-uncertainty regions being
  profitable; in a synthetic where these were anti-correlated, the delta was ~0.
  This is why the contribution leads with calibrated risk control (tier 1), which
  is geometry-independent, and treats the profit delta (tier 2) as a measured
  result whose magnitude the twin will decide.
- **alpha does not equal the realized violation rate at the selected setpoint.**
  Setpoint selection introduces a selection effect, so the conformal coverage
  level and the RTO's realized violation rate are related but not identical —
  the harness measures the realized rate directly rather than assuming it.
