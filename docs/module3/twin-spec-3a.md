# 3A DWSIM Debutanizer Twin — Specification

> Status: SPEC v1, 2026-06-13. Decisions T1–T6 below follow the ratified
> Module 3 scoping (D1-C, D2-A, D3, D5). The twin executes owner-side in
> DWSIM; the sandbox validates exports via `scripts/validate_twin.py`.
> Companion code: `src/ipis/module3_rto/{economics,column_model,rto_nlp}.py`
> (24 unit tests, suite green at 263).

## T1 — Component slate

| option | tradeoff |
|---|---|
| **A. Binary nC4/nC6 (DECIDED)** | Identical to the Module 1 physics-bridge proxy (butane = LK, n-hexane = stabilized-gasoline HK). Every twin state is directly checkable against `ipis.physics` bubble-point inversion; DWSIM convergence is trivial. |
| B. 5-component cut (C3, iC4, nC4, iC5, C6+) | More realistic C5 distribution, but breaks the 1:1 check against the M1 physics layer and adds convergence surface area before the skeleton exists. Re-enters at 3B **if** the GPR surrogate's residuals show the binary proxy is the fidelity bottleneck. |

## T2 — Property package

**Peng-Robinson.** Nonpolar light-hydrocarbon system; PR is the standard
recommendation for this class and matches the near-ideal assumption already
baked into the M1 VLE code (ideal-solution modified Raoult). NRTL/UNIQUAC
add binary-interaction degrees of freedom the system does not need.
Cross-check at mid-envelope (CoolProp reference): α(nC4/nC6) = 5.97 at
106 °C — the twin's K-value ratio at tray 6 should land within ±10% of this.

## T3 — Column configuration

| item | value | basis |
|---|---|---|
| Theoretical stages | **8** (incl. reboiler) | The binary proxy at α≈6 needs only N_min≈5 for a near-total split; at a realistic-N column (15+) the spec constraint is numerically vertical and the RTO degenerate (verified by grid scan). N=8 gives xB_C4 spanning 0.0002–0.046 over the decision box with leverage in **both** R and D — the smallest credible RTO testbed. ≈16–20 real trays at 45–50% Murphree efficiency; tray 6 exists, consistent with the M1 sensor location. Revisit alongside T1-B. |
| Feed stage | 4 (mid-column) | Symmetric split for the binary. |
| Condenser | Total | LPG product taken as liquid. |
| Reboiler | Kettle | Standard. |
| Top pressure | 4.7 bar | Mid M1 envelope [4.5, 5.5]. |
| Column ΔP | 0.4 bar | Nominal per M1 bridge comment. |
| Feed | 100 kmol/h, z(nC4) = 0.35, saturated liquid | Representative stabilizer feed; matches `ShortcutColumnModel` defaults. |

## T4 — Decision variables and constraint

RTO handles: **reflux ratio R ∈ [0.8, 3.0]** and **distillate rate
D ∈ [33, 37] kmol/h** (the surface trust region). Quality constraint:
**x(nC4) in bottoms ≤ 0.02** (RVP proxy). The two-stream economics
(overhead at C4 price, bottoms at gasoline price) make this constraint
ACTIVE at the optimum — verified on the shortcut model: the optimizer rides
the spec from below, and back-off width carries a direct profit cost
(≈ −1.9 USD/h per 0.001 back-off at the literature anchors).

## T5 — Economics anchor (owner-ratified: literature defaults)

| leg | default | provenance |
|---|---|---|
| C4 (overhead, by mass) | 0.750 USD/gal → 0.3395 USD/kg | Mont Belvieu propane spot, 2025 annual avg (EIA via FRED, APROPANEMBTX). Conservative floor for n-C4 (trades at a premium to propane). |
| Gasoline (bottoms, by mass) | 2.10 USD/gal → 0.8364 USD/kg | EIA USGC spot complex 2025 (jet 2.114, ULSD 2.222 USD/gal on FRED); conventional gasoline in the same band. FLAGGED estimate; the objective rides the 1.35 USD/gal **spread**, robust to ±0.10 on either leg. |
| Reboiler energy | 5.50 USD/Mcf NG → 6.28 USD/GJ steam | EIA Natural Gas Monthly 2025 (industrial, Tables 3/22, YTD 5.56–5.78); 1 Mcf = 1.0951 GJ HHV; 0.80 boiler efficiency. |

Density bases (CoolProp, sat. liquid 60 °F): nC4 2.209 kg/gal, nC6 2.511
kg/gal. Upgrade incentive +28.9 USD per kmol C4 retained in bottoms;
downgrade −42.8 USD per kmol C6 lost overhead. Plant-realistic figures slot
into `EconomicsAnchor(...)` later — replace all three legs together.

## T6 — Surrogate architecture (3A vs 3B)

`ColumnModel` protocol → grid evaluation → **quadratic surface on ln(xB)**
→ GEKKO/IPOPT NLP. Duty needs no surrogate (exactly linear:
Q = (R+1)·D·ΔH_v/3600, ΔH_v = 25.93 kJ/mol nC6 at 110 °C — boilup is
hexane-rich; nC4 is near its 152 °C critical point, wrong latent-heat
basis). Known limitation, kept deliberately: the quadratic's max ln-residual
is 0.55 (×1.74 band on xB; cubic only improves to ×1.41) concentrated at
the high-R/high-D saturation corner — at zero back-off the surface-feasible
optimum violates the true spec by ~17%. This is (a) the in-repo
demonstration of *why* back-off exists and (b) the ADR-006 GPR motivation,
which replaces the quadratic at 3B behind the same protocol.

## Build steps (owner, DWSIM GUI)

1. New steady-state simulation; add n-Butane, n-Hexane; property package
   Peng-Robinson.
2. ChemSep/rigorous column: 8 stages, total condenser, kettle reboiler,
   feed stage 4; feed stream 100 kmol/h, z = {nC4: 0.35, nC6: 0.65},
   saturated liquid at 4.7 bar.
3. Column pressures: condenser 4.7 bar, reboiler 5.1 bar (linear profile).
4. Specifications: reflux ratio = R, distillate molar rate = D
   (the two RTO handles — do NOT spec compositions).
5. Case grid (Sensitivity Analysis or manual): R ∈ {0.8, 1.5, 2.2, 3.0} ×
   D ∈ {33, 34.5, 36, 37} kmol/h = 16 runs.
6. Export per converged run: `run_id, reflux_ratio, distillate_kmol_h,
   feed_kmol_h, z_c4, tray6_T_C, top_P_bar, xD_c4, xB_c4,
   reboiler_duty_kW` (+ optional `tray6_x_c4_liq` to enable check V4).
7. `python scripts\validate_twin.py twin_runs.csv` → writes
   `docs/module3/twin-validation.md`. All checks must PASS before the twin
   replaces the shortcut model in the surface fit.

## Acceptance (3A closeout gate)

- Validation table: V1–V3 PASS (V4 if tray profile exported).
- `fit_ln_xb_surface` on the twin grid: R² > 0.95 reported with the
  ln-residual band.
- One optimization case study (`run_case_study`) on the twin surface:
  spec constraint active, back-off profit gradient reported.
- ADR-013 filed for the T1–T6 fidelity choices.
