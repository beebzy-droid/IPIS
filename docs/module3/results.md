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

*Status: **complete on real twin data.** Run on the 77-row DWSIM feed-z campaign
(`twin_runs_zvaried.csv`) + the 15-row nominal surface (`twin_runs.csv`). The 3B
contribution was reframed from a profit claim to a calibrated-safety claim once
the data showed the selection effect (ADR-014). Reproduce:
`python scripts/run_3b3_regime_map.py --nominal <nominal.csv> --zvaried <zvaried.csv>`.*

### Summary
The 3B chance constraint is CPP-style over the **unmeasured feed-z disturbance**
at a known decision (R, D): maximize profit s.t. P_z[xB(R,D,z) <= spec] >= 1-alpha.
A conformal back-off C(R,D) enters as the constraint margin (xB_nominal + C <= spec).
The headline is **calibrated risk control, not profit** — at realistic feed
variability the chance constraint is barely active and every method lands within
0.5% of the deterministic optimum, so the differentiator is the realized
constraint-violation rate (audit-A).

The finding: a **marginally**-calibrated back-off — including the adaptive/
normalized soft-sensor interval — is **unsafe under RTO selection**. The optimizer
drives toward operating points where the marginal margin under-covers the
*conditional* (1-alpha) quantile, so realized violation reaches ~5x the nominal
level. This is the CPP selection effect / the Gibbs–Cherian–Candès
conditional-coverage gap, on a chemical process. The fix is a **conditional**
formulation (conformalized quantile regression, CQR) plus a **CPP a-posteriori**
calibration step at the selected setpoint, which restores violation control to the
oracle (truth conditional quantile) level across a swept disturbance range.

### Data
- Nominal twin surface (z=0.35): 15-row `twin_runs.csv` -> GPR `(R,D)->xB`,
  `(R,D)->xD`, `(R,D)->reboiler duty` for the objective; bounded-hyperparameter
  GP, seed 20260613 (3B.1).
- Feed-z campaign: 77 clean rows (`twin_runs_zvaried.csv`), grid z in
  {0.30,0.325,0.35,0.375,0.40} x R x D -> the 3-D truth surface `xB(R,D,z)` that
  scores violations, and the calibration residuals for the conformal back-offs.
- Disturbance: z ~ TruncNormal(0.35, sigma_z) on [0.30, 0.40], sigma_z swept
  {0.004,...,0.025}, realistic center **sigma_z ~ 0.006** (well-controlled upstream).
- Physical limit: spec xB <= 0.02 is unachievable for z >~ 0.38 within D in
  [33,37] (distillate-flow limited; min xB at z=0.40 is ~0.048), so the full
  [0.30,0.40] ensemble is infeasible for any method — operational sigma_z must be
  tight (audit-E: DWSIM stage-composition / flow limitation).

### Metrics

Regime map (spec xB<=0.02, target violation <= 0.10; realized violation at the
RTO optimum, profit in USD/h). Canonical run on the committed twin data
(`twin_runs_zvaried.csv`, with the patched z375_13 row; seed 20260614). Violation
rates are Monte-Carlo estimates (4-6k disturbance draws) and carry ~+/-0.01-0.02
of cross-platform sampling noise; the regime structure and the ~5x selection-effect
gap are stable.

| sigma_z | oracle | CQR+a-posteriori | naive-fixed | naive-adaptive |
|---|---|---|---|---|
| 0.004 | 0.084 / $5383 | **0.063 / $5381** | 0.190 / $5388 | 0.429 / $5394 |
| **0.006** | 0.079 / $5374 | **0.101 / $5376** (k=1.53) | 0.167 / $5381 | 0.449 / $5394 |
| 0.008 | 0.101 / $5364 | **0.097 / $5364** | 0.159 / $5374 | 0.472 / $5396 |
| 0.010 | 0.106 / $5351 | **0.066 / $5335** | 0.112 / $5356 | 0.488 / $5396 |
| 0.015 | 0.095 / $5310 | **0.105 / $5298** (k=5.78) | INFEASIBLE | 0.480 / $5396 |
| 0.020 | 0.087 / $5288 | **0.094 / $5282** | INFEASIBLE | 0.482 / $5394 |
| 0.025 | 0.105 / $5271 | INFEASIBLE | INFEASIBLE | 0.502 / $5396 |

| quantity | value | note |
|---|---|---|
| 3-D truth surface | leave-z=0.375-out R^2 0.917, MAE 0.0053 (n=15) | audit-F; interpolation in z validated |
| naive-adaptive realized violation | 0.43–0.50 across all sigma_z | ~5x the 0.10 target — the selection effect |
| CQR+a-posteriori realized violation | 0.063–0.105, sigma_z <= 0.020 | tracks the oracle; infeasible only at 3x realistic |
| a-posteriori inflation kappa | 1.0–1.5 (sigma_z<=0.010), 5.8 at 0.015 | conditional estimate is data-starved as the disturbance widens |
| profit spread at realistic sigma_z | <0.5% (all methods ~$5374–5394) | deterministic optimum ~$5393 — profit is muted |
| violation-rate precision floor | ~0.005 xB (truth MAE) | oracle at 0.08–0.11 not exactly 0.10 reflects this |

### Observations
- The mechanism that matters is **conditional** validity, not the conformal
  label. Split/normalized conformal guarantees only *marginal* coverage; under an
  optimizer that selects against the margin, marginal validity is not enough.
- The oracle (truth conditional (1-alpha) quantile, available because xB is
  monotone in z so q_{1-alpha}[xB] = xB(z_{1-alpha})) realizes violation ~alpha by
  construction — it is the achievable bound the data-driven methods are scored
  against, and it confirms the chance-constraint machinery is correct.
- The conditional-quantile estimate needs more calibration data as the
  disturbance widens (n_cal scaled with sigma_z); at fixed n_cal the CQR method
  goes infeasible early purely from estimation error, not a fundamental limit.
- Back-offs are floored at 0 (a safety margin is non-negative); negative margins
  break the a-posteriori kappa scaling.

### Unexpected findings
- **The naive adaptive method fails *worse* than the fixed margin, not better.**
  The pre-data 3B framing expected the heteroscedastic back-off to be the
  improvement; on the twin it is the most dangerous (violation 0.35–0.51 vs the
  fixed margin's 0.10–0.23) because its small back-off in low-scale regions is
  exactly what the optimizer exploits. The contribution inverted: the adaptive
  method became the cautionary baseline and the conditional+a-posteriori method
  the result.
- **alpha != the realized violation at the selected setpoint** (anticipated in
  3A): setpoint selection is a selection effect, quantified here at ~5x for the
  marginal back-off and closed by the CPP a-posteriori step (smallest kappa>=1
  such that realized violation at the chosen optimum <= alpha on a held-out draw).
- **Profit is muted at realistic disturbance.** Because a tight sigma_z barely
  activates the chance constraint, the safety-vs-profit tension the project
  expected is mild at the realistic operating point; the value of the conditional
  method is calibrated safety, with the profit gap widening only as sigma_z grows.
