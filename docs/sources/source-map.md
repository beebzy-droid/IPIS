# IPIS Source-Content Map

**Purpose:** A precise, verified index of the project's reference library. This map operationalizes the principle "apply only what fits, but miss nothing" — not by memorizing pages, but by knowing exactly what each source is authoritative for and where to find it. When building any component, open the mapped section, verify the equation/value against the actual page, then cite.

**Discipline:** Every number that enters the repo (equation coefficients, worked-example targets) must be verified against the actual source page at the moment of use. Synthesized summaries are hypotheses, not ground truth. This discipline has already caught real errors (see Verification Record).

**Verification status:** Section locations were extracted directly from each source's bookmarks/TOC. Specific equation numbers and worked-example values are marked VERIFIED once confirmed against the page during build; otherwise UNVERIFIED.

---

## Edition-priority rule (operating policy)

Per the project owner's board-exam guidance, the three Perry's editions are complementary, not redundant: there is content in the 8th not in the 9th, and vice versa.

- **For formulas, theories, concepts, derivations:** search 9th -> 8th -> 7th, take whichever is clearest. These are stable across editions (Fenske's equation does not change between 1997 and 2019). Equation-number citations anchor to the **9th ed.** as the authoritative reference.
- **For specific numerical values (coefficients, worked-example results):** values drift between editions (re-measured constants, updated property methods) — analogous to how tabulated molar masses shift by decimals over time. Therefore: **a test fixture's expected value AND the inputs that produce it must come from the same edition** (edition-internal fixtures). Mixing a 9th-ed input with an 8th-ed expected value creates a phantom failure — correct code tested against a mismatched target. Each fixture's docstring names its source edition.

Observed example of value drift: the FUG worked example gives distillate D = 48.25 (9th ed.) vs D = 49.2 (8th ed.) for the nominally same problem, because the editions used different property methods for the K-values.

---

## Tier 0 — Primary calculation backbone (Perry's, three editions)

### Perry's 9th ed. (Green & Southard, 2019) — 2,274 pp. AUTHORITATIVE for citations.

| Section | Title | PDF page | Authoritative for | Feeds |
|---|---|---|---|---|
| S2 | Physical and Chemical Data | 35 | Antoine coefficients, vapor-pressure correlations | M1 analytical engine |
| S4 | Thermodynamics | 473 | VLE, K-values, bubble/dew point, Raoult, Peng-Robinson | M1 analytical engine (core) |
| S8 | Process Control | 669 | SPC (Shewhart, CUSUM, EWMA), Cp/Cpk, MPC, RTO | M2 (drift/health), M3 (RTO/MPC) |
| S13 | Distillation | 1133 | Relative volatility, Fenske-Underwood-Gilliland, Murphree | M1 column model |

VERIFIED from 9th ed.: Antoine natural-log form Eq. 4-15 (Ex. 4-11: acetone P_sat=87.616 kPa, n-hexane 58.105 kPa); Wilson Eqs. 4-163/164 (gamma1=1.8053, gamma2=1.2869); bubble pressure Eqs. 4-195/196 (Ex. 4-11: P=108.134 kPa, y1=0.5851); Fenske Eq. 13-32 (n-C4/i-C5: N_min=6.10).

### Perry's 8th ed. (Green & Perry, 2008) — 2,735 pp. Cross-check + fuller worked examples.

| Section | Title | PDF page | Authoritative for | Feeds |
|---|---|---|---|---|
| S13 | Distillation | 1431 | FUG worked example with EXPLICIT converged values | M1 column model |

VERIFIED from 8th ed.: S13 (PDF p1457, Table 13-6) prints the fully converged Underwood example the 9th ed. compresses into narrative — theta = 1.3647, R_min = 0.9426 (q=1, sat. liquid; alpha and z_F as tabulated). This is the source of the M1 Underwood fixture.

### Perry's 7th ed. (Perry & Green, 1997) — 2,641 pp. Formula/theory support only.

Used only to confirm equation forms when 9th/8th differ. No fixtures sourced from 7th ed.

Other 9th-ed. sections available if needed: Mathematics (397), Heat & Mass Transfer (509), Fluid & Particle Dynamics (583), Reaction Kinetics (633), Process Economics (755), Reactors (1693), Process Safety (2055).

---

## Tier 1 — Formal methods (meta-modelling / model migration / transfer)

### Kajero et al., "Meta-modelling in Chemical Process System Engineering" (J. Taiwan Inst. Chem. Eng.) — 35 pp. READ IN FULL.

Survey/basis for surrogate and transfer claims. Meta-model types S2.2; Kriging/GPR S2.2.2; DoE/space-filling S3.1-3.2; model migration / SBC S3.3; applications S4.

**CRITICAL CORRECTION (ADR-006):** S4.2 explicitly excludes online-data soft sensors from "meta-models" ("not surrogates of a more complex model"). Therefore GPR -> M3 (DWSIM surrogate) and transfer basis, NOT the M1 soft-sensor ML layer. M1 keeps the PINN-NN residual (ADR-001). The paper's hybrid first-principle+ANN reference (Tsen et al.) independently supports Path B.

### The five model-migration primary papers (Gao group + Yan/Luo) — VERIFIED in full

The scale-and-bias correction (SBC) lineage. Core form, verified identical across three of these papers:
**y_new = S_O * f(S_I * x_new + B_I) + B_O**, f = base model, S/B = scale/bias, I/O = input/output.

| Paper | Method | Key content | IPIS use |
|---|---|---|---|
| **Lu & Gao (2008a)**, Ind. Eng. Chem. Res. 47(6) 1967 | **Parametric SBC** (OSBC / IOSBC) | Output-only (OSBC: S_O*f+B_O) and input-output (IOSBC) least-squares correction. Eq. 13 bound estimate rho0=(xmax~-xmin~)/(xmax-xmin) = min-max denorm. | **M1 bridge** (output-affine special case) |
| **Lu & Gao (2008b)**, IECR 47(23) 9508 | Inclusive-similarity (bagging/ensemble of ANNs) | Migration when one process's attribute ranges subset another's. | (reference) |
| **Lu, Yao & Gao (2009)**, AIChE J. 55(9) 2318 | Similarity taxonomy + family-similarity migration | Formal classification: scale/inclusive/family; physical vs functional shift-and-scale (Defs 16-18). | Phase 1C framing |
| **Yan et al. (2011)**, Chem. Eng. J. 166(3) 1095 | **Functional SBC** (GPR) | Output scale becomes function s(x)=b0+sum(bj*xj); bias delta(x) a zero-mean GPR; Bayesian (integrate out beta); EI-based joint optimization. | **Phase 1C** (canonical) + M3 |
| **Luo, Yao & Gao (2015)**, Chem. Eng. Sci. 134, 23 | Bayesian parametric SBC | Normal-inverse-gamma priors on migration params; MCMC; sequential LHD/NLHD design. | M1 (if calibration uncertainty wanted) |

**Parametric vs functional — the distinction that determines placement:**
- *Parametric SBC* (Lu & Gao 2008a): S, B constants, least-squares. Cannot add flexibility the base model lacks (linear base -> linear new model). Sufficient for undoing an affine transform.
- *Functional SBC* (Yan 2011): scale is a function + GPR bias, Bayesian. Flexible enough to migrate between genuinely different processes.

**Mapping to IPIS use cases (verified against primary sources, not the Kajero summary):**
- **M1 normalization bridge** = the *degenerate* output-only case: y_norm = S_O * y_physics + B_O. S_O, B_O are the inverse of the unknown min-max constants. Just affine output calibration, least-squares (Lu & Gao 2008a OSBC). Does NOT need GPR/Bayesian machinery. The Path B ML residual handles the remaining nonlinear physics gap; the affine fit only undoes the linear normalization.
- **Phase 1C transfer** (Debutanizer -> TEP) = genuine two-process migration: functional SBC with GPR (Yan 2011). This is where the full apparatus earns its place.

**Key caveat:** all five papers migrate between TWO similar processes using data from BOTH. The M1 normalization problem is one process + a units mismatch — so only the degenerate affine case applies to M1. The full migration framework is a Phase 1C tool, not an M1 tool.

---

## Tier 1.5 — Foundational ChemE texts (theory/derivation support + cross-checks)

Canonical textbooks that supplement Perry's for theory, derivations, and independent cross-checking. Perry's remains AUTHORITATIVE for citations; these provide a second authoritative source on the underlying physics. Edition-internal-fixtures discipline still applies (a numeric value and its inputs come from the same source). Structure verified from bookmarks/TOC.

| Text (ed.) | pp | Authoritative-support for | Feeds | Priority |
|---|---|---|---|---|
| **Seader, *Separation Process Principles* (3rd)** | 849 | Distillation, absorption/stripping, VLE, equilibrium-stage & rate-based methods, FUG shortcut. Part 1 Fundamentals (p28); **Part 2 Separations by Phase Addition/Creation (p232) = distillation/VLE** | **M1 column model + bubble-point cross-check**; M3 rate-based | **Immediate** |
| **Smith Van Ness Abbott, *Intro to Chemical Engineering Thermodynamics* (9th)** | 781 | VLE formulations (Ch 13, p477), Phase-equilibrium intro (Ch 12, p448), solution thermodynamics & activity coefficients (Ch 10, p375), EOS/volumetric (Ch 3, p86), fugacity | **M1 bubble-point/activity-model cross-check** (second source vs Perry's S4) | **Immediate** |
| **Coughanowr, *Process Systems Analysis and Control* (3rd)** | 630 | Process dynamics, transfer functions, controller design, stability, frequency response | M2 (drift/dynamics), M3 (control/MPC/RTO) — supports Perry's S8 | Later (M2/M3) |
| **Welty et al., *Fundamentals of Momentum, Heat and Mass Transfer* (7th)** | 774 | Transport phenomena: fluid mechanics, heat transfer, mass transfer | Column hydraulics, reboiler/condenser, mass-transfer efficiency; M3 / rate-based | Later (equipment) |
| **Himmelblau, *Basic Principles and Calculations in ChemE* (9th)** | 912 | Material & energy balances, units, stoichiometry, gas laws, recycle | Foundational sanity-checking of balances anywhere | General support |
| **Levenspiel, *Chemical Reaction Engineering* (3rd)** | 685 | Reactor kinetics & design | Not directly relevant (debutanizer has no reactor); future if IPIS extends to reactive systems | Future/general |
| **Nan, *Theory and Problems for Chemistry Olympiad*** | (PDF parse glitch) | General organic/inorganic/physical chemistry — component properties, reaction & physical chem concepts | General chemistry support | General support |

Immediate use: before building the physics-to-data bridge, the bubble-point inversion and pseudo-binary key approximation can be cross-checked against Seader (Part 2, distillation/VLE) and Smith (Ch 12-13 VLE; Ch 10 activity coefficients) as a second authoritative source — the same verify-against-the-page discipline applied to a confirming source.

## Tier 2 — Supplementary simulation/design references (pull just-in-time)

Structure verified from each book's bookmarks/TOC. None touch the M1 analytical engine (pure Perry's); all are DWSIM/Aspen-stage references.

- **Foo, Chemical Engineering Process Simulation (497 pp)** — property-package selection (Ch 3 p80), recycle convergence (Ch 4 p110), distillation simulation (Ch 6 p148). Pull at DWSIM Tier-2.
- **Gil Chaves et al., Process Analysis and Simulation (537 pp)** — convergence (1.5 p28), sensitivity (1.7 p56), design specs (1.8 p64), thermodynamic-model selection (2.7 p85). Pull at DWSIM / property-model selection.
- **Hameed, Chemical Process Simulations using Aspen HYSYS (520 pp)** — fluid-package selection (1.6-1.7 p26), properties (Ch 2 p41). Pull at Tier-3 Aspen.
- **Babu, Process Plant Simulation (539 pp)** — modelling aspects (Ch 2 p24), model classification (Ch 3 p48), recycle convergence. Pull at DWSIM if recycle non-trivial.
- **Satpute, Process Plant Design and Simulation Handbook (468 pp)** — distillation sizing in HYSYS (Ch 11 p227), optimizer (Ch 12 p246), dynamics (Ch 15 p359). Pull for equipment sizing.
- **"Chemical Process Design and Simulation" (Aspen Plus/HYSYS) (418 pp)** — sequential-modular vs equation-oriented; phase-equilibrium & kinetic data collection. No bookmarks; navigate by TOC. Pull at DWSIM/Aspen.
- **Duncan & Reimer, Chemical Engineering Design and Analysis (394 pp)** — process design (Ch 2 p20), models from laws (Ch 3 p74), dimensional analysis & dynamic scaling (Ch 5 p249). Pull for fundamentals / dimensionless-group framing.

---

## Tier 1 (cont.) — Time-delay soft-sensor methods (primary-verified)

Three papers on soft sensing under measurement delay, read from the primary
PDFs (in /mnt/project/). Directly relevant to Module 1's dynamic soft sensor,
where the C4 signal lives in tray-6 temperature (u5) at a ~15-sample transport
delay. NOTE: two `.md` brain-transfer summaries of these exist and are accurate
as a MAP, but are summaries, not primary; numbers below are verified against
the actual papers.

| Paper | Method | Verified key result | IPIS use |
|---|---|---|---|
| **Wang et al. (2021)**, *Control Eng. Practice* (WWTP/BSM1) | **DTDE-WRVM**: Fuzzy Curve Analysis static delimitation + adaptive sliding-window dynamic delay + weighted RVM | RMSE **-55.7%** (0.0972 -> 0.0431) from making the delay *dynamic*. Delay drifts with flow rate. | **Staged**: the principled lag upgrade IF the delay drifts. The Debutanizer diagnostic showed delay STABLE (best-lag 14-15 across all splits), so NOT adopted now (ADR-007). |
| **Guo et al. (2014)**, *J. Process Control* | **Kalman filter + data fusion**: fast/regular/delay-free measurement fused with infrequent/irregular/delayed measurement; LTI state-space avoids augmented state (cost independent of delay length) | Demonstrated on a **binary distillation column** with delayed composition. | M1-late / M3: needs a state-space column model. LTI (linear) limitation noted. |
| **Shardt (2016)**, *J. Process Control* | Soft sensor = **process model + bias-update term**; design of the bias-update for stability under random delay; open- vs closed-loop | Establishes when a static bias loses tracking and that closed-loop needs an integrating term. | Theory under the affine SBC now; the calibration-drift finding (negative CV with stable correlation, ADR-007) is its exact motivating scenario. Full use at M3 closed-loop. |

**Caveat (verification discipline):** Wang's reported test R^2 = 0.987 is flagged as test-set-optimistic (training delays appear reused at test); cite the directly-stated **-55.7% RMSE** instead. The `.md` summaries are reading guides, not citable sources.

---


## Tier 1 (cont.) — Tennessee Eastman process & simulator (Phase 1C)

The TEP transfer-study sources, read from the primary PDFs (in /mnt/project/).
TEP is the Phase-1C cross-process target. NOTE: these define the process and the
simulators; the DATA OF RECORD is generated by the Russell/Braatz closed-loop
FORTRAN (last row), not by COSTEP (abandoned — see Verification Record).

| Source | What it is | Verified key content | IPIS use |
|---|---|---|---|
| **Downs & Vogel (1993)**, *Comput. Chem. Eng.* 17(3) 245 | The foundational TEP definition | 4 irreversible exothermic Arrhenius reactions (A+C+D->G, A+C+E->H, A+E->F, 3D->2F); **G reaction has the higher activation energy (more temp-sensitive)**; 5 units (reactor/condenser/separator/compressor/stripper); **41 XMEAS + 12 XMV**; 6 modes by G/H mass ratio (50/50, 10/90, 90/10 x rate); **target XMEAS(40)=G mol% in product**; composition analyzers delayed — product stream 0.25 h sample + 0.25 h dead time. | **Phase 1C** physics-anchored G features (D/E ratio, reactor T, pressure); documented label delay **theta~=5** at 3-min cadence |
| **Bathelt et al. (2015)**, IFAC-PapersOnLine 48(8) 309 | Revision of the TEP simulator | Adds measurements + the revised C-mex; documents simulation settings for the closed-loop model. | Reference for simulator settings / additional measurements |
| **Vosloo et al. (COSTEP)**, *SoftwareX* | Complete open Simulink TEP (MIT) | Full variable/parameter access; control-mode (open/Braatz/Ricker/custom) + mode-selection + disturbance blocks; R2024b + Simulink + DSP + Signal Processing. | **ABANDONED** for data gen (non-reproducible reactor-pressure startup trip at ~0.40 h under Ricker, disturbances off; sample-time conflict in the analyzer-delay subsystem). |
| **Russell, Chiang & Braatz** closed-loop TEP (FORTRAN; `temain_mod.f`+`teprob.f`) | The d00-d21 simulator | Closed-loop plant-wide control; `COMMON/PV/ XMEAS(41),XMV(12)`, `COMMON/CTRLALL/ SETPT(20)`; output every 180 s; **SETPT(14)/(15) = reactor-feed D/E mol% = the G/H lever** (verified empirically). Compiles headless with gfortran. | **DATA OF RECORD (Phase 1C)** — 3 operating-mode regimes generated in-sandbox (G 53.8/58.2/63.4 mol%); reproducible via `scripts/generate_tep_modes.py` |

**Framing caveat (verified from Lu 2008/2009, Yan 2011, Luo 2015):** SBC migration
requires a *shared input space* and *similar processes*; Debutanizer->TEP shares
no variables, so literal parameter migration is inapplicable. Phase 1C = (A)
methodology transfer + (C) within-TEP regime migration. The generated regimes are
feed-ratio operating points (high-G side for pressure margin), NOT the canonical
Downs & Vogel G/H modes — sufficient for the Option-C claim, framed honestly.


## Verification Record (errors caught by the protocol)

1. **GPR misplacement** — synthesized doc placed GPR as M1 ML layer; primary source (Kajero S4.2) shows it belongs to M3/transfer. (ADR-006)
2. **Base-10 Antoine bug** — synthesized doc used 10**(A-B/(T+C)); Perry's Eq. 4-15 is natural-log exp(...). Base-10 gave 29,714 kPa vs correct 87.616 kPa — a ~340x error.
3. **SBC over-scoping** — initial framing implied full functional SBC for the M1 normalization bridge; primary sources show M1 needs only the degenerate affine output case (Lu & Gao 2008a), with full functional SBC (Yan 2011) reserved for Phase 1C.
4. **Static single-tray physics misframed as the predictor** — initial bridge applied bubble-point physics at lag 0 (R^2 = 0.018); diagnosis showed the problem is dynamic (transport delay ~15) and that single-tray physics ~= lagged u5. Corrected to a dynamic, physics-anchored model evaluated under blocked CV (ADR-007).
5. **SBC mis-scoped for Debutanizer->TEP** — the staged migration papers were lined up for a literal Debutanizer->TEP migration, but the SBC equation requires a shared input space (verified from Lu 2008/2009, Luo 2015, Yan 2011). Debutanizer and TEP share no variables -> literal parameter migration inapplicable. Re-scoped Phase 1C to A (methodology transfer) + C (within-TEP regime migration), where the papers validly apply.
6. **COSTEP unusable for headless data gen** — COSTEP (Simulink) had a non-reproducible reactor-pressure startup trip (~0.40 h) under Ricker with disturbances off, plus a discrete-in-continuous-If sample-time conflict in the analyzer-delay block; not fixable without interactive access. Pivoted to the Russell/Braatz closed-loop FORTRAN (compiles headless, stable, more cited for data gen), which became the data of record.

---

## Usage protocol

1. **Identify the need** during a build step (e.g., "Antoine coefficients for n-butane").
2. **Locate** via this map (Perry's S2, p35).
3. **Open and verify** the actual page — equation form, coefficients, units, worked-example values; respect the edition-priority rule.
4. **Implement and cite** (9th ed. for equations; source edition for any numeric fixture) — never reproduce copyrighted text/tables verbatim.
5. **Scan adjacent sections** for anything applicable that might otherwise be missed.
6. **Record** any decision that diverges from a prior plan as an ADR.

This protocol is the operational meaning of "miss nothing": guaranteed retrieval + verification, not claimed memorization.
