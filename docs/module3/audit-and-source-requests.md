# Module 3 — Rigor audit, source requests, and DWSIM walkthrough (2026-06-13)

> Doctorate/industrial review of Module 3 from G0 to the present, the principle
> that **synthetic data validates code only — never results**, source
> verification against the project files, a prioritized list of sources to
> upload, and the step-by-step DWSIM feed-z campaign.

## 0. Provenance discipline (reaffirmed)

- Every **closed** result rests on twin (DWSIM) data: G1a–G4 (3A) and **3B.1**
  (GPR gate) ran on the real 15-row `twin_runs.csv`.
- Every **synthetic** number (3B.2 coverage, 3B.3 frontiers) is a **code-
  validation stand-in**, explicitly `[pending]`, and underpins **no decision**.
  It exists to prove the math is wired correctly; it is discarded when the
  z-campaign lands.
- No conclusion in the audit below depends on synthetic data.

## 1. Source verification (against project files)

Verified present and now read at the formula level:
- **CPP** — Lindemann/Zhao et al., *Conformal Predictive Programming*: quantile
  lemma, quantile reformulation, a priori SAA guarantees, a posteriori
  calibration for the (non-i.i.d.) optimal solution. The formal backbone for 3B.
- **CQR** — Romano/Patterson/Candès, *Conformalized Quantile Regression*: split
  conformal has fixed width; CQR gives valid, heteroscedasticity-adaptive,
  shorter intervals. The interval-engine upgrade for the sensor back-off.
- Conformal base also present: Papadopoulos (ICP), Barber (jackknife+), Gibbs &
  Candès (ACI / arbitrary shifts), Xu & Xie, Schlembach, Astigarraga.
- Migration base present: Lu, Yan, Luo. Soft-sensor delay: Shardt, Guo, Wang.
  TEP: Downs, Bathelt, Vosloo. Drift: Bifet.

**Gaps (NOT in the project files) — these block rigorous positioning:**
- No chemical-engineering RTO-under-uncertainty / modifier-adaptation source.
- No classical chance-constrained *process* optimization source.
- No GP-surrogate-chance-constraint RTO source (the closest prior art).
- No conditional-conformal source (needed for the selection-effect argument).
- No locally-adaptive/normalized conformal source (basis of the current sensor).
- The **Debutanizer soft-sensor benchmark** (Module 1) originates in a text that
  does not appear to be in the files — its primary source should be cited.

## 2. Audit — constraints and needed changes (G0 -> 3B)

**A. Contribution framing (the main change).** The 3B.3 design finding (profit
win is conditional on multi-D freedom + favourable uncertainty/profit
correlation) means the original "higher profit at equal violation" thesis is not
robust on its own. CPP gives the fix: **lead with calibrated risk control**
(a priori + a posteriori conformal guarantees on constraint satisfaction without
knowing the uncertainty field), and report the profit delta as a measured
secondary result. This is now grounded in a verified source, not opinion.

**B. Selection effect -> adopt CPP's two-step.** The realized violation at the
RTO-selected setpoint != alpha because the optimum is not i.i.d. with the
calibration data (CPP, Sec. 3). **Change:** after the RTO selects a setpoint,
add an **a posteriori calibration** step (validate coverage / violation on a
held-out calibration set) and report that, exactly as CPP prescribes. The 3B.3
harness already evaluates realized violation directly; formalize it as the a
posteriori guarantee.

**C. Interval engine -> add CQR variant.** The current `TwinSoftSensor` uses
mean-GP + scale-GP normalized conformal (Lei-style). **Change:** add a CQR
variant (fit the one-sided conditional (1-alpha) quantile of xB | tray-6 T, then
conformalize) and A/B the two on real data (coverage + width). CQR is the field
standard and typically tighter; the comparison strengthens the methods section.

**D. Economics traceability.** The price anchors must be fully datable for an
industrial-grade paper. **Change:** pin exact public series — EIA Mont Belvieu
n-butane spot, EIA USGC conventional gasoline spot, EIA Henry Hub / natural gas
for steam — each with series ID and access date, in `EconomicsAnchor`'s docstring
and a results table. (Public data; no upload needed, but must be cited precisely.)

**E. Stage-composition limitation (state honestly).** DWSIM 9 does not expose
per-stage liquid compositions post-solve, so V4 was dropped (superseded by the
G1a VLE check). **Change:** state this as an explicit modeling limitation —
sensor validation is at the product level (xB) plus the G1a bubble-point check,
not the internal tray composition. A reviewer will ask; pre-empt it.

**F. Surrogate validation rigor.** 3B.1 fit and scored the GPR on the same 15
points. **Change:** add leave-one-out CV of the surrogate on the real twin data
(report LOO-R^2) so the surrogate's predictive validity is not in-sample only.

**G. Critical path / blocking constraint.** All 3B.2/3B.3 *results* are blocked
on the feed-z campaign producing data that (i) closes the C4 mass balance at
<=0.5%, (ii) holds the feed saturated-liquid across z, and (iii) demonstrably
responds to z (xB moves with z at fixed R,D). Until then, 3B.2/3B.3 numbers are
pending by design.

## 3. Sources — ALL ALREADY IN THE PROJECT (corrected 2026-06-13)

Verified by project-knowledge search: **every source below is already present.**
Nothing needs uploading. (Lesson: search the project knowledge before requesting
sources — VERIFY-BEFORE-LOAD-BEARING applies to the project files too.)

**RTO-under-uncertainty + closest prior art — PRESENT:**
- del Rio Chanona, Petsagkourakis, Bradford, et al. (2021), "RTO meets Bayesian
  optimization and DFO: a tale of modifier adaptation," *Comput. Chem. Eng.*
  (`Chanona_...pdf`). Closest prior art: GP modifiers G_p - G ~ GP(mu, sigma^2),
  GP mean corrects the constraint, GP variance drives the acquisition. **3B's
  wedge:** distribution-free conformal interval on a soft-sensor estimate vs
  their Gaussian GP posterior.
- Marchetti, Chachuat, Bonvin (2009), "Modifier-Adaptation Methodology for RTO,"
  *Ind. Eng. Chem. Res.* 48(13) (`Marchetti_...pdf`). Constraint-modifier
  formalism G_m = G + eps^G + lambda^GT(u-u_k) with KKT-matching. **Position the
  conformal back-off as a measurement-based constraint modifier.**
- Chachuat, Srinivasan, Bonvin (2009), "Adaptation strategies for RTO,"
  *Comput. Chem. Eng.* (`Chachuat_...pdf`). The back-off-reduction-via-
  measurement precedent.

**Chance-constrained process optimization — PRESENT:**
- Li, Arellano-Garcia, Wozny (2008), "Chance constrained programming approach to
  process optimization under uncertainty," *Comput. Chem. Eng.* (`Li_...pdf`).

**Soft-sensor + debutanizer provenance — PRESENT (richer than expected):**
- Fortuna, Graziani, Rizzo, Xibilia (2007), *Soft Sensors...* (`Fortuna_...pdf`).
- Debutanizer-specific soft-sensor precedents also present: Ramli (ANN),
  Pani (regression tree/ANFIS, x2), Moghadam (time-variable-parameter),
  Rozanec (LPG debutanizer ML soft sensors). Cite for the Module-1 benchmark.

**Conformal completeness — PRESENT:**
- Lei et al. (2018), "Distribution-Free Predictive Inference for Regression,"
  *JASA* (`Lei_...pdf`) — normalized/locally-adaptive conformal.
- Gibbs, Cherian, Candès (2025), "Conformal prediction with conditional
  guarantees," *JRSS-B* (`Gibbs_..._Conditional_Guarantees.pdf`) — the
  conditional-coverage route for the selection effect.
- Angelopoulos, Bates (2023), "A Gentle Introduction to Conformal Prediction,"
  (`Angelopoulos_...pdf`) — foundational.
- Barber et al. (2023), "Conformal prediction beyond exchangeability," *Ann.
  Statist.* (`Barber_...pdf`) — the non-exchangeable foundation under the RTO's
  operating-point shift.
- Burger, "Distribution-Free Process Monitoring with Conformal Prediction"
  (`Burger_...pdf`); Ma, "Intrinsically Calibrated UQ in Industrial Models..."
  (`Ma_...pdf`) — industrial conformal/UQ precedent.
- Zhang et al., Safe-BOCP (`Zhang_Bayesian_Optimization_...Conformal...pdf`) —
  GP + conformal caution-increasing back-off; the BO analogue.

Plus CPP (`Lindemann_...pdf`) and CQR (`Candes_...pdf`), verified earlier.

**Conclusion: the corpus is complete; proceed to implement the audit changes.**

## 4. DWSIM feed-z campaign — step by step

Goal: `data/raw/dwsim/twin_runs_zvaried.csv` = R x D grid at several feed z,
with z a CLEAN disturbance (feed held saturated-liquid). Column work uses
**DWSIM.Automation3** (the path proven since G1c); the **DWSIM MCP is flash-only**
and is used here only as an *independent thermodynamic cross-check*.

**Step 1 (one-time, GUI) — make the feed saturated liquid.**
1. Open `data/raw/dwsim/debutanizer_3a.dwxmz` in DWSIM 9.0.5.
2. Double-click the **feed material stream** -> Stream editor.
3. Under **Stream Conditions / Flash Specification**, change the spec from
   "Temperature and Pressure" to **"Pressure and Vapor Fraction (PVF)"**; set
   P = feed pressure (4.8 bar) and **Vapor Fraction = 0** (bubble point).
4. Confirm the feed Temperature becomes a *computed* output. Save the file.
   Rationale: with VF=0 fixed, changing z re-computes the bubble-point T, so z is
   an isolated disturbance (no subcooled/two-phase confound).

**Step 2 (independent check that bubble-point T responds to z).** The point is
to confirm the feed disturbance is real *before* the full sweep. Use an
INDEPENDENT thermodynamic reference (CoolProp, Peng-Robinson) — a different
library from DWSIM — computed for the feed at 4.8 bar, VF=0:

| z(n-C4) | bubble-point T (C), CoolProp PR | first-vapor y(n-C4) |
|---|---|---|
| 0.300 | 90.98 | 0.685 |
| 0.325 | 88.62 | 0.714 |
| 0.350 | 86.34 | 0.739 |
| 0.375 | 84.16 | 0.763 |
| 0.400 | 82.07 | 0.784 |

(z=0.35 -> 86.3 C matches the G1a PR feed temperature, confirming consistency.)
Higher n-C4 -> LOWER bubble T, ~2.2 C per 0.025 step.

Three ways to get DWSIM's feed T to compare against this table (any one suffices):
1. **GUI (simplest, no MCP):** with the feed on the PVF (VF=0) spec, change the
   feed n-C4 mole fraction to 0.30, read the computed feed Temperature; repeat at
   0.40. It must match the table within ~1-3 C and decrease with n-C4.
2. **DWSIM MCP flash (via Claude Code):** hand Claude Code this instruction —
   "Use the DWSIM flash MCP to compute the bubble point (Peng-Robinson,
   n-butane/n-hexane, P = 4.8 bar, vapor fraction = 0) at n-C4 mole fractions
   0.30, 0.35, 0.40; report temperature and incipient-vapor composition." Claude
   Code knows the MCP's flash-tool signature; it returns T per z.
3. **Sweep self-report:** the campaign already records the feed T per run; the
   z=0.35 rows must show ~86 C.

**Arbiter:** DWSIM's feed T must track the CoolProp table (direction + ~1-3 C).
If it does, the feed-z mechanism is physically correct and the sweep can run.

**Step 3 (the sweep, Claude Code + DWSIM.Automation3).** Run the corrected
`run_zvaried_sweep.py` (the three fixes from review must be in place):
- **V2 screen at 0.5%** (not 2%): drop any run with |xD*D + xB*B - z*F|/(z*F) > 0.005.
- **Feed-z setter targets the stream's INPUT composition** (overall mole
  fractions) then re-flashes — NOT the phase-result MoleFraction field. Read it
  back to confirm it took.
- **PLATEAU -> drop** (not accept), so z=0.35 reproduces the 15-row twin.
Grid: z in {0.30,0.325,0.35,0.375,0.40}, R in {0.8,1.5,2.2,3.0},
D in {37,36,34.5,33}; outer z -> middle R (reload+set z) -> inner D.

**Step 4 (the arbiter self-checks the script must print).**
- (a) the z=0.35 rows reproduce `twin_runs.csv` to the decimal;
- (b) **xB moves monotonically with z at fixed (R,D)** (e.g. at R=1.5, D=34.5,
  xB increases as z goes 0.30->0.40 by an order ~0.01+). **This (b) is the real
  arbiter** that the feed actually changed — the readback alone is necessary but
  not sufficient (the run_015 lesson: a field can read back yet not drive the solve).
If (a) and (b) both hold, the campaign is trustworthy.

**Step 5 (consume).** Bring back `twin_runs_zvaried.csv`. Then:
`python scripts/run_3b2_sensor_check.py --nominal data/raw/dwsim/twin_runs.csv
--zvaried data/raw/dwsim/twin_runs_zvaried.csv` closes 3B.2 on real data; the
3B.3 driver fits the 3-D truth and runs the frontiers. `[pending]` slots fill;
the measured delta picks the tier-1/tier-2 headline.
