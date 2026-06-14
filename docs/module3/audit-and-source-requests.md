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

## 3. Sources to upload (prioritized, exact)

**Tier 1 — RTO-under-uncertainty + closest prior art (positioning-critical):**
1. del Rio Chanona, E.A., Petsagkourakis, P., Bradford, E., et al. (2021).
   "Real-time optimization meets Bayesian optimization and derivative-free
   optimization: A tale of modifier adaptation." *Computers & Chemical
   Engineering*. — **Closest prior art** (GP posterior tightens joint chance
   constraints under plant-model mismatch). 3B's wedge = distribution-free
   conformal calibration vs Gaussian GP posterior.
2. Marchetti, A., Chachuat, B., Bonvin, D. (2009). "Modifier-Adaptation
   Methodology for Real-Time Optimization." *Ind. Eng. Chem. Res.* 48(13),
   6022-6033. — The constraint-modifier paradigm 3B's back-off connects to.
3. Chachuat, B., Srinivasan, B., Bonvin, D. (2009). "Adaptation strategies for
   real-time optimization." *Comput. Chem. Eng.* 33(10), 1557-1567. — Survey;
   the back-off-reduction-via-measurement precedent.

**Tier 1 — chance-constrained process optimization (classical ChemE):**
4. Li, P., Arellano-Garcia, H., Wozny, G. (2008). "Chance constrained
   programming approach to process optimization under uncertainty." *Comput.
   Chem. Eng.* 32(1-2), 25-45.

**Tier 1 — soft-sensor benchmark provenance:**
5. Fortuna, L., Graziani, S., Rizzo, A., Xibilia, M.G. (2007). *Soft Sensors for
   Monitoring and Control of Industrial Processes.* Springer. — Primary source of
   the **Debutanizer** benchmark used in Module 1; also the standard soft-sensor
   reference.

**Tier 2 — conformal methodology completeness:**
6. Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R.J., Wasserman, L. (2018).
   "Distribution-Free Predictive Inference for Regression." *JASA* 113(523),
   1094-1111. — Locally-adaptive/normalized conformal; basis of the current
   sensor's scale model.
7. Gibbs, I., Cherian, J.J., Candès, E.J. (2025). "Conformal prediction with
   conditional guarantees." *JRSS-B* 87(4), 1100-1126. — The conditional-coverage
   route; explains/fixes the alpha != realized-violation selection effect.
8. Angelopoulos, A.N., Bates, S. (2023). "Conformal Prediction: A Gentle
   Introduction." *Foundations and Trends in ML* 16(4). — Foundational; cited by
   CPP itself.

**Tier 2 — safe-optimization analogue (optional but strong):**
9. The Safe-BOCP paper (Bayesian optimization with formal safety guarantees via
   online conformal prediction), IEEE J-STSP 2024 (KCLIP). — GP + conformal
   caution-increasing back-off; the BO analogue of 3B.

(Items 1-5 are the ones that genuinely block the paper's framing. 6-9 deepen the
conformal rigor and pre-empt reviewers.)

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

**Step 2 (independent check, DWSIM MCP flash) — confirm T responds to z.**
Using the DWSIM MCP flash on a copy of the feed (P=4.8 bar, VF=0):
- flash at z(nC4)=0.30 -> record bubble-point T
- flash at z(nC4)=0.40 -> record bubble-point T
These must differ (higher nC4 -> lower bubble T). This validates the feed-spec
physics *independently of the Automation sweep*, before spending the full run.

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
