# SCC paper — structure & claims–evidence map (for review)

**Target:** Reliability Engineering & System Safety (RESS)
**Class:** elsarticle `[5p,times]` two-column · `\usepackage{lineno}\linenumbers` ·
`\bibliographystyle{elsarticle-num-names}` · `\address{Chemical Engineer, Quezon City, Philippines}`
**House standard:** Paper 1 (CACE-D-26-00944) — split sections 01–07, end-matter, highlights, cover letter (.docx).

**Working title:** *Similarity-Calibrated Conformal prediction: data-free coverage
guarantees for remaining-useful-life intervals under operating-regime transfer.*

---

## One-line thesis
Calibrating the conformal nonconformity score in a **dimensionless** space (Buckingham Π)
restores approximate score-exchangeability across operating regimes, yielding a coverage
certificate **computable a priori from physical parameters** — no target failure data and
no density-ratio estimation.

## Novelty seam (verified over 4 deep scans)
- Dimensionless/Buckingham-Π transfer learning exists → but **point accuracy only, no coverage guarantee**.
- Shift/weighted conformal exists → but **needs density ratios estimated from target data**.
- **Union is empty:** no method uses physical similarity to deliver a distribution-free
  coverage guarantee under transfer. SCC fills it; the a-priori, data-free certificate is the wedge.

---

## Section plan (split elsarticle)
1. **Introduction** — prognostic UQ; the operating-regime *coverage-transfer* problem;
   the two-literature gap; contributions (C1–C4 below); honest scope (simulation + diagnostic).
2. **Background & related work** — split/Barber non-exchangeable conformal; shift/weighted
   conformal (density ratios); conformal RUL (Javanmardi 2023, RobustUQ 2025, …);
   Buckingham-Π transfer (JCP 2022; vehicles 2024; RL 2025). State the seam precisely.
3. **Method — SCC** — dimensionless reduction (Def. 1); procedure; **Theorem 1** (certificate)
   + proof; **Cor. 1** (a-priori); estimating L (intercept a ~ n^-1/2); **diagnostic** (3-way).
   [= the compiled theory note, integrated.]
4. **Experimental design** — catalyst-deactivation simulator (Levenspiel/Perry's Sec. 7
   kinetics; Arrhenius; lognormal unit variability; noise); predictor + one-sided score;
   3 temperature regimes; controlled departure (2nd channel, E2≠E1, weight η); metrics
   (coverage, efficiency, operational bound, diagnostic); **gate criteria fixed in advance.**
5. **Results** — see evidence table.
6. **Discussion** — what the certificate buys; envelope (diagnostic); vs shift-conformal;
   limitations (H1–H2 are hypotheses; simulation; real-data future work).
7. **Conclusions.**
End-matter: Data & code availability · CRediT (sole author) · Generative-AI disclosure.
Highlights (5). Cover letter (.docx).

---

## Contributions
- **C1** — Dimensionless (Π-space) conformal calibration restoring cross-regime score-exchangeability.
- **C2** — An **a-priori coverage certificate** (Thm 1 + Cor 1): gap ≤ 2L‖ΔΠ‖, from physics, no target data.
- **C3** — A **similitude diagnostic** giving SCC a self-aware operating envelope (holds/violated/indeterminate).
- **C4** — A controlled-physics validation protocol that tests the certificate **non-circularly** (departure sweep).

---

## Claims–evidence map (every claim → evidence → status)
| # | Claim | Evidence | Status |
|---|-------|----------|--------|
| 1 | Naive conformal miscovers across regimes | η=0: coverage→0.58, gap to 0.32 | ✓ solid |
| 2 | SCC recovers coverage | η=0: gap 0.006 (target 0.90) | ✓ solid |
| 3 | A-priori bound holds (not curve-fit) | 100% of **held-out** (pair,η); Barber 100% | ✓ solid |
| 4 | Physics predicts the mismatch | δ→d_TV held-out **R²=0.79**, corr 0.95 | ✓ solid |
| 5 | Graceful degradation under unmodeled physics | gap 0.006→0.103 & efficiency 0.28→1.01, monotone | ✓ solid |
| 6 | Not cherry-picked | robust across E2(95–150kJ), pert(15–60%), α(.05–.20) | ✓ solid |
| 7 | Certificate tightens with data | intercept 0.12→0.04, ~n^-1/2 | ✓ solid |
| 8 | Diagnostic discriminates | synthetic: holds/violated/indeterminate correct | ✓ solid |
| 9 | FEMTO = applicability limit (not validation) | FEMTO→indeterminate (underpowered, CI fold 2.6–4.4×) | ✓ honest limit |
| 10 | Real-process validation | — | ✗ **future work (plant data)** |

## Key numbers to feature
- Target 1−α=0.90; naive gap 0.13–0.34 vs **SCC gap 0.006**.
- Held-out: bound holds **100%**, δ→d_TV **R²=0.79**.
- Departure: gap **0.006→0.103**, efficiency **0.28→1.01** (graceful, both monotone).
- Certificate intercept **0.12→0.04** (~n^-1/2).
- L10 cross-condition prediction **1.63×**; FEMTO bootstrap CI fold **2.6–4.4×** → indeterminate.

## Honesty / risk posture (must be explicit in the paper)
- H1–H2 are **falsifiable physical hypotheses**, not theorems; guarantee is conditional on them.
- Validation is **controlled simulation** (similitude genuine, not assumed by the estimator).
- FEMTO is an **honest applicability limit**, not a real-data win.
- **Real field data is the stated future work** — the route to real-data validation / a revision response.

## Reviewer-objection ledger (pre-empt)
- *"Just Barber + Buckingham-Π."* → No parent provides an a-priori, data-free certificate; that property is new (Cor. 1).
- *"Cherry-picked departure."* → Robustness sweep (claim 6).
- *"Coverage held by trivial intervals."* → Efficiency reported alongside coverage (claim 5).
- *"Simulation only."* → Conceded; diagnostic + plant-data future work; controlled sim tests theory non-circularly.

## Immediate next steps
1. Your review of `scc_theory.pdf` (the math) — sign-off gates everything.
2. On sign-off: consolidate validated code into repo (`src/ipis/module2_pdm/scc/` + `scripts/`), commit/push.
3. Draft §1–§2 and §4–§5 around the locked evidence; integrate theory note as §3.
4. Build figures (coverage bars naive-vs-SCC; gap & efficiency vs η; bound-vs-measured held-out; diagnostic CIs).
5. Highlights + cover letter (.docx).
