# IPIS Source-Content Map

**Purpose:** A precise, verified index of the project's reference library. This map operationalizes the principle "apply only what fits, but miss nothing" — not by memorizing 5,650 pages, but by knowing exactly what each source is authoritative for and where to find it. When building any component, open the mapped section, verify the equation/value against the actual page, then cite.

**Discipline:** Every number that enters the repo (equation coefficients, worked-example targets) must be verified against the actual source page at the moment of use. Synthesized summaries are hypotheses, not ground truth.

**Verification status:** Section locations below were extracted directly from each PDF's bookmarks/TOC (not from second-hand summaries). Specific equation numbers and worked-example values are marked UNVERIFIED until confirmed against the page during build.

---

## Tier 0 — Primary calculation backbone

### Perry's Chemical Engineers' Handbook, 9th ed. (Green & Southard, 2019)
**2,274 pages. The authoritative source for all physics calculations.**

| Section | Title | PDF page | Authoritative for | Feeds |
|---|---|---|---|---|
| §2 | Physical and Chemical Data | 35 | Antoine coefficients, vapor-pressure correlations for C4/C5 | M1 analytical engine |
| §4 | Thermodynamics | 473 | VLE, K-values, bubble/dew point, Raoult/modified-Raoult, Rachford-Rice flash, Peng-Robinson EOS | M1 analytical engine (core) |
| §8 | Process Control | 669 | SPC (Shewhart, CUSUM, EWMA), Cp/Cpk, MPC, RTO objective, process dynamics | M2 (drift/health), M3 (RTO/MPC) |
| §13 | Distillation | 1133 | Relative volatility, Fenske-Underwood-Gilliland shortcut, Murphree efficiency, column material balance | M1 column model |

Other sections present and available if needed: Mathematics (397), Heat & Mass Transfer (509), Fluid & Particle Dynamics (583), Reaction Kinetics (633), Process Economics (755), Heat-Transfer Equipment (945), Reactors (1693), Process Safety (2055).

---

## Tier 1 — Formal methods (meta-modelling / transfer learning)

### Kajero et al., "Meta-modelling in Chemical Process System Engineering" (J. Taiwan Inst. Chem. Eng.)
**35 pages. READ IN FULL. Formal basis for the surrogate and transfer-learning claims.**

| Topic | Location | Authoritative for | Feeds |
|---|---|---|---|
| Meta-model types (Kriging/GPR, SVR, MARS, RBFN, ANN) | §2.2 | Surrogate model selection | M3 |
| Kriging/GPR formulation | §2.2.2 | GPR mean + variance prediction | M3 surrogate |
| Design of computer experiments (LHS, space-filling, EI) | §3.1–3.2 | Sampling DWSIM operating space | M3 |
| Model migration / functional SBC (Yan 2011) | §3.3 | Cross-process transfer formal basis | M1→TEP transfer (Phase 1C) |
| Applications: process design/optimization | §4.1 | GPR surrogate of high-fidelity sim | M3 (paper's main use case) |
| Applications: process control | §4.2 | — (see correction below) | — |

**CRITICAL CORRECTION (ADR-006):** The paper explicitly states data-driven soft sensors trained on online data "cannot be considered as meta-model discussed in this work, because they are not surrogates of a more complex model" (§4.2). Therefore:
- GPR belongs to **M3** (surrogate of DWSIM), NOT the M1 soft-sensor ML layer.
- M1 retains the PINN-regularized NN residual learner (ADR-001 stands).
- The paper's hybrid-model reference (Tsen et al., refs 174–176) independently *supports* the Path B hybrid concept for M1.

---

## Tier 2 — Supplementary simulation/design references (pull just-in-time)

Structure verified from each book's bookmarks/TOC.

### Foo, *Chemical Engineering Process Simulation* (2nd ed.) — 497 pp
**Pull at: DWSIM Tier-2 stage.** Part I is the relevant part.
- Ch 3 — Physical property estimation & phase behavior (p80): property-package selection rationale
- Ch 4 — Simulation of recycle streams (p110): recycle convergence
- Ch 6 — Design & simulation of distillation (p148): column simulation workflow

### Gil Chaves et al., *Process Analysis and Simulation in Chemical Engineering* — 537 pp
**Pull at: DWSIM stage / property-model selection.**
- Ch 1.5 — Convergence Analysis (p28); Ch 1.7 — Sensitivity Analysis (p56); Ch 1.8 — Design Specifications (p64)
- Ch 2 — Thermodynamic & Property Models (p70): EOS, activity coefficients, **2.7 Selection of Thermodynamic Model (p85)** — key for justifying PR for the Debutanizer

### Hameed, *Chemical Process Simulations using Aspen HYSYS* (2025) — 520 pp
**Pull at: Tier-3 Aspen comparison (if pursued).**
- Ch 1.6–1.7 — Fluid package / thermodynamics model selection (p26–27)
- Ch 2 — Physical and Thermodynamic Properties (p41)

### Babu, *Process Plant Simulation* (2004) — 539 pp
**Pull at: DWSIM stage, if recycle/convergence is non-trivial.**
- Ch 2 — Modelling Aspects (p24); Ch 3 — Classification of Mathematical Modelling (p48)
- Modelling theory (deterministic vs stochastic, similarity principles)

### Satpute, *Process Plant Design and Simulation Handbook* — 468 pp
**Pull at: equipment-sizing / practitioner questions (mostly Aspen HYSYS-based).**
- Ch 11 — Distillation Column Sizing using Aspen HYSYS (p227)
- Ch 12 — Optimizer Tool (p246); Ch 14 — Process Plant Design (p316); Ch 15 — HYSYS Dynamics (p359)

### "Chemical Process Design and Simulation" (Aspen Plus/HYSYS) — 418 pp
**Pull at: DWSIM/Aspen stage.** No bookmarks; navigate by TOC text.
- Ch 1.7.1 — Sequential Modular vs Equation-Oriented (p~9 book / verify in PDF)
- Part I — Introduction to Design and Simulation; phase-equilibrium & kinetic data collection

### Duncan & Reimer, *Chemical Engineering Design and Analysis* — 394 pp
**Pull at: fundamentals / teaching framing. Lowest near-term priority.**
- Ch 2 — Process Design (p20); Ch 3 — Models Derived from Laws (p74); Ch 5 — Dimensional Analysis (p249)

---

## Usage protocol

1. **Identify the need** during a build step (e.g., "I need the Antoine coefficients for n-butane").
2. **Locate** via this map (Perry's §2, p35).
3. **Open and verify** the actual page — confirm the equation form, coefficients, units, and any worked-example values.
4. **Implement and cite** (e.g., "Antoine coefficients per Perry's 9th ed., §2") — never reproduce copyrighted text/tables verbatim into the repo.
5. **Scan adjacent sections** for anything applicable we might otherwise miss.
6. **Record** any decision that diverges from a prior plan as an ADR.

This protocol is the operational meaning of "miss nothing": guaranteed retrieval + verification, not claimed memorization.
