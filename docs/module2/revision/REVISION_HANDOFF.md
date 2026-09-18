# RESS revision — CONTINUATION BRIEF (read this first)

**Manuscript:** JRESS-D-26-04700, *Reliability Engineering & System Safety*, **major revision**,
Assoc. Editor Prof. Marko Cepin. **Revised manuscript due 2026-10-07.**

This file plus `REVISION_LOG.md` are designed to be SUFFICIENT on their own. A fresh session
should be able to finish the revision from these two files plus `paper3/` with nothing lost.
`REVISION_LOG.md` holds the evidence and the numbers; this file holds the state, the decisions,
the rebuild instructions, and the remaining work.

---

## 1. Where the revision stands

**All analysis is COMPLETE and all 12 reviewer comments are now answered in the manuscript
(last one written 2026-09-16), plus the reproducibility rebuild. Remaining: figures (task 10),
the response letter (task 11), and the submission package (task 12).**

| Item | Status |
|---|---|
| R1.5 within-unit dependence | DONE — `scripts/r15_exchangeability.py` |
| R2m2 bound tightness | DONE — `scripts/r15b_certificate.py` |
| finite-sample sweep rebuilt (reproducibility gap) | DONE — `scripts/r15b_certificate.py` |
| R2.3 discrete-mode baseline | DONE — `scripts/r23_discrete_mode.py`; manuscript Section 5.6 2026-09-16 |
| R1.4 misspecification + detectability | DONE — `scripts/r14_misspecification.py`; manuscript Section 5.7 and Section 3.5 2026-09-16 |
| R2.1 C-MAPSS second dataset | DONE — `scripts/cmapss_loader.py`, `scripts/r21_cmapss.py`, `scripts/r21b_psi_candidates.py`; written into the manuscript 2026-09-16 |
| R1.1 base-model complexity | DONE — `scripts/r11_base_model.py`; manuscript Section 5.4 2026-09-16 |
| R1.2 design guideline | DONE — `scripts/r12_design_guideline.py`; manuscript Section 5.8 2026-09-16 |
| R2.2 Lundberg-Palmgren psi derivation | DONE — `scripts/r22_lundberg_palmgren.py`; manuscript Appendix B 2026-09-16 |
| R2.4 actionability concession | DONE — `scripts/r24_actionability.py`; manuscript Sections 4.3, 5.2, abstract, discussion, conclusions 2026-09-16 |
| R1.3 terminology sweep | DONE 2026-09-15 - `scripts/r13_terminology_sweep.py` (`--audit` guards it) |
| R2m1, R2m3 | DONE 2026-09-16 — R2m1 in Sections 3.3, 5.3 and Appendix B; R2m3 moved into Section 3.4 |
| **Manuscript rewrite** | **TODO** |
| **Response-to-reviewers letter** | **TODO** |

## 2. Decisions already ratified by Bien — do not relitigate

1. **D1:** C-MAPSS FD002/FD004 is the second dataset for R2.1.
2. **D2:** unit-level calibration (one score per unit) is PRIMARY; block conformal is reported as
   the principled generalisation for multi-point monitoring.
3. **Narrowing the certificate claim is APPROVED.** The dimensionless CALIBRATION is validated on
   real data; the A-PRIORI CERTIFICATE is scoped to assets whose governing law identifies psi.
   Abstract and conclusions must be narrowed accordingly.
4. **R2.4 is conceded, not argued.** eta = 2 is degenerate by the paper's own criterion.

## 3. Standing rules for this revision

* **No number enters the manuscript unless a committed script in `scripts/` reproduces it.**
  This rule exists because the previously published finite-sample sweep was unreproducible.
* Prose uses hyphens only. No em-dashes or en-dashes.
* No `\paragraph{}` run-in heads (that formatting caused the first desk rejection).
* "field" means operational in-service data ONLY. FEMTO is an accelerated laboratory test
  platform; C-MAPSS is externally authored simulation. Neither is field data. Run
  `python scripts/r13_terminology_sweep.py --audit` before committing any paper3 prose.
* Proofs stay in the appendix; the body stays an engineering narrative.
* Single-column `\documentclass[review,times]{elsarticle}`, no microtype.

## 4. Rebuilding the lab (the sandbox resets between sessions)

```bash
mkdir -p /tmp/rev/{src/ipis/module2_pdm/scc,scripts,out,data/cmapss}
# copy src/ipis/module2_pdm/scc/{conformal,deactivation,diagnostic,__init__}.py from the repo
# copy scripts/*.py from the repo
cd /tmp/rev && PYTHONPATH=src python3 scripts/<script>.py
```

**C-MAPSS data.** Not committed (large, and NASA's licence governs redistribution).
Official source: `https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip`
Cite: A. Saxena and K. Goebel (2008), "Turbofan Engine Degradation Simulation Data Set", NASA
Prognostics Data Repository, NASA Ames Research Center, Moffett Field, CA.
Place `train_FD002.txt` and `train_FD004.txt` in `/tmp/rev/data/cmapss/`.
**Verified provenance (re-checked 2026-09-16 against the files Bien supplied):**
`train_FD004.txt` MD5 `8b510e2c1460ba87214f58ceb3cd0266`, 10,350,705 bytes, 61,249 lines.
`train_FD002.txt` MD5 `b6eaab2a6b589e5e41d43ca2f99e379b`,
9,082,480 bytes, 53,759 lines. A GitHub mirror (`edwardzjl/CMAPSSData`) was confirmed
byte-identical to the official NASA release on 2026-09-08.

Sandbox network note: NASA's host is NOT reachable from the sandbox allowlist (GitHub and PyPI
only). Use the verified mirror, or have the file uploaded.

## 5. Numbers that MUST change in the manuscript

**APPLIED 2026-09-15.** Every change below is now in `paper3/`; see the task-2 section of
`REVISION_LOG.md`. Table 1 was additionally re-run under unit-level calibration
(`scripts/r15d_robustness_unit.py`), and its Bound% is now a genuine held-out number.

Old values came from stacked calibration (3 dependent scores per unit). New values use
unit-level calibration. **Old -> New:**

| Quantity | Old (submitted) | New (unit-level) | Where |
|---|---|---|---|
| SCC recovery at eta=0 (mean gap) | within 0.006 | **within 0.011** | abstract, 5.1, conclusions |
| SCC per-pair coverage deviation | 0.006 | **0.009** | 5.1 |
| worst naive coverage, eta=0 | 0.58 | **0.572** | abstract, 5.1 |
| worst naive gap, eta=0 | 0.34 | **0.328** | 5.1 |
| SCC gap at eta=2 | 0.103 | **0.097** | 5.2 |
| held-out R^2 (delta predicts dTV) | 0.79 | **0.773** | abstract, 5.3 |
| corr(delta, dTV) | 0.95 | **0.947** | 5.3 |
| finite-sample intercept sweep | 0.12 at n=200 to 0.04 at n=1600 | rebuilt and re-indexed on UNITS: 0.424 at 50 units to 0.096 at 800; log-log slope **-0.513** vs -0.500 predicted | 5.3 |
| back-off at eta=2 | 1.01 "graceful" | **1.011, DEGENERATE** by the paper's own criterion | 4.3, 5.2, 6 |
| bound holds | 100% (validity only) | 100% valid BUT **conservative by ~8x**; mean gap 0.046 vs mean bound 0.384 | 5.3, 5.4, Table 1 |

**UNCHANGED and still correct:** 10.2x scale span; 600/650/700 K; E1 = 80 kJ/mol; failure at
a <= 0.3; FEMTO ~6 bearings/condition, 7x spread, CI 2.6-4.4, 1.63x L10 ratio, indeterminate.

### STATISTICAL WARNING — do not mix two different statistics

Coverage gaps can be summarised two ways and they do NOT agree, because gaps are clipped at zero:

* **mean of per-seed gaps** (what `scc_gate.py`, `r15`, `r15b` report): eta=0 SCC = **0.011**
* **gap of the seed-averaged coverage** (what the directional table reports): eta=0 SCC = 0.003

Pick ONE convention, state it in the caption, and use it consistently. Recommended: keep the
mean-of-per-seed-gaps convention, because it matches the originally published statistic and is
the conservative reading.

### Directional coverage at eta=0, unit-level (for the abstract and 5.1)

| cal -> dep | naive coverage | SCC coverage |
|---|---|---|
| 600->650 | 1.000 | 0.897 |
| 600->700 | 1.000 | 0.891 |
| 650->600 | 0.666 | 0.906 |
| 650->700 | 1.000 | 0.894 |
| 700->600 | **0.572** | 0.908 |
| 700->650 | 0.669 | 0.898 |

Naive both over-covers (1.000, wasteful) and under-covers (0.572, unsafe); SCC holds 0.891-0.908.

## 6. Response plan, comment by comment

Full evidence and tables are in `REVISION_LOG.md`. This is the argument to make.

**R1.1 base-model complexity.** Concede the risk, show it lands on the naive baseline only.
Naive miscoverage worsens 3.5x with capacity (0.127 physics to 0.449 forest); SCC is flat at
0.007-0.014 across physics/linear/forest/MLP, and is BETTER under departure with flexible models.
State the caveat: the learned predictor must be fitted in dimensionless coordinates.

**R1.2 deployability.** Give the design guideline: 3 units at scatter 0.10, 6 at 0.25, 10 at
0.50, 40 at 0.80 for 80% power. FEMTO's indeterminate verdict is PREDICTED by its position in
this map (few units and large spread), not a quirk. C-MAPSS at ~260 units/regime is far inside
the feasible region. The method is not restricted to rare data environments.

**R1.3 terminology.** Reviewer is correct. FEMTO/PRONOSTIA is an accelerated LABORATORY testbed.
Replace "field benchmark" and "field data limit" with "experimental benchmark" everywhere
(abstract, 5.5, 6, 7). Reserve "field" for genuinely operational data, which we do not have.

**R1.4 misspecification.** Quantify tolerance: safe band |dE/E| <= 31%, still better than no
scaling to +62%, backfire only at +100% when only the scale is wrong. Coupled misspecification
(one wrong model driving predictor AND scale) is fragile from -10%. Then the mitigation: the
invariance diagnostic returns holds ONLY at the true scale and violated at every misspecification
tested, including the -10% backfire onset. New capability to state: the diagnostic detects SCALE
MISSPECIFICATION, not only similitude departure.

**R1.5 temporal dependence.** Concede fully. rho = 0.908 across monitoring fractions, design
effect 2.82, so n=1200 stacked carried effective n ~ 426 against 400 units. Primary analysis
moves to unit-level. Headline unchanged (naive 0.132, SCC 0.011), and the shift matches the
sqrt(3) theory prediction (0.006 x 1.73 = 0.010 vs 0.011 observed). Offer block conformal
(per-unit max) as the stronger SIMULTANEOUS guarantee over the monitored trajectory. State that
exchangeability is across UNITS, not across time steps within a unit.

**R2.1 second dataset.** Lead with the positive: on C-MAPSS FD002 (260 engines) and FD004 (249),
six regimes, ~260 units per regime (43x FEMTO's power), naive loses ~0.58 coverage and SCC
recovers to 0.060 and 0.058, replicated. Then report the negative honestly: neither psi candidate
(ambient referred distance; healthy gas-path signature distance) predicts the residual, which
behaves as a near-constant floor; the bound holds on only 67-83% of held-out regime pairs against
100% on the testbed. Conclude by separating the two halves of the contribution. This is the
honest answer to "no case where the bound is checked against an asset the author did not design".

**R2.2 psi derivation.** New appendix. Buckingham Pi on (t, P, C, n) gives Pi_1 = t*n and
Pi_2 = P/C; Lundberg-Palmgren is the relation between them, so sigma = 10^6 (C/P)^p/(60n).
ISO 281's modified life L_nm = a_1 a_ISO L_10 with a_ISO = f(e_C C_u/P, kappa) identifies exactly
what is left over, so psi is the LUBRICATION REGIME (kappa = nu/nu_1) plus contamination.
Numerical instance on NSK 6804RS at the published PRONOSTIA conditions reproduces the 1.63x L10
ratio from first principles. Practitioner's lesson: at a matched thermal state ||d psi|| = 0.091;
a 25 C spread gives 1.060, 12x larger. Thermal state breaks similitude for bearings, not load.
**Tie this to R2.1:** psi is identifiable where the governing standard enumerates the residual
groups (ISO 281 does; nothing equivalent exists for a turbofan gas path). psi-identifiability,
not the bound, is the practical boundary of the method.

**R2.3 discrete-mode baseline.** Add as a third series. Be honest in both directions: when the
target regime HAS failure data, discrete-mode clustering is near-oracle and beats SCC under
strong departure (0.009 vs 0.045 at eta=1). When it does NOT, discrete-mode falls back to the
nearest mode and lands near pooling (0.078-0.138 vs pooled 0.093-0.159) while SCC holds
0.009-0.040. SCC's advantage is specifically the no-target-failure-data regime.

**R2.4 actionability.** Concede. Define b = q_T/mean(RUL_T) with b<0.5 actionable,
0.5<=b<1 degraded, b>=1 degenerate. Measured: actionable ends at eta = 0.68, degeneracy begins
at eta = 1.97, and eta = 2 gives b = 1.011 with certified 1-b = -0.011, i.e. DEGENERATE. Remove
the word "graceful" for eta = 2 and publish the operating envelope instead.

**R2m1.** State explicitly that the tested case is m = 1 (a single scalar departure driven by
eta), and note that the norm choice in Eq. (1) is immaterial at m = 1 but would need specifying
once m > 1 is exercised.

**R2m2.** Report tightness beside validity in Table 1: mean measured gap 0.046 vs mean certified
bound 0.384, margin mean 0.339 (min 0.268, max 0.552), i.e. conservative by ~8x. Name the
dominant source: the finite-sample floor of the plug-in TV estimator (at delta=0 the bound is
2a = 0.278 against a measured gap of 0.011), which decays as n^-1/2 (0.424 at 50 units to 0.096
at 800). The 2x from the Lemma 1 swap argument is a second, irreducible source. Frame the
certificate as a worst-case planning bound, not a sharp estimate.

**R2m3.** Move the clarification that the L fit uses multiple (pair, eta) configurations from
Section 5.3 up into Section 3.4, so the procedure is not misread as relying on three pairs.

## 7. Remaining task checklist

1. **DONE 2026-09-15.** Terminology sweep R1.3 across `paper3/` (abstract, Sections 1, 5.5,
   6, 7). Re-run the audit after each task below, including the new C-MAPSS text.
2. **DONE 2026-09-15.** Section 5 number changes applied; the clipped per-seed convention is
   stated in Section 4.3. Table 1 re-run unit-level with a margin column.
3. **DONE 2026-09-16.** C-MAPSS written in: Section 4.4 (design), Section 5.5 (results,
   Table 2), intro contribution 4 and scope paragraph, discussion limitation (iii), two bib
   entries. Both psi candidates now have a committed script, `r21b_psi_candidates.py`.
4. **DONE 2026-09-16.** R1.1 in Section 5.4 (Table 2), R2.3 in new Section 5.6 (Table 4), R1.4
   in new Section 5.7 (Table 5), R1.2 at the head of Section 5.8 (Table 6). One open decision
   raised in the log: whether to multiplicity-correct the diagnostic verdict, which currently
   has a ceiling near 0.86 under exact similitude. CLOSED 2026-09-16: Bien ratified leaving the
   diagnostic as submitted, honest sentence kept.
5. **DONE 2026-09-16.** Appendix B with Tables B.1 and B.2; cross-referenced from Sections 3.2,
   5.5 and 5.8. `scc_paper.tex` now resets appendix float counters (latent numbering bug).
6. **DONE 2026-09-16.** Section 3.5 now states the dual role and points at Section 5.7.
7. **DONE 2026-09-16.** Bands defined in Section 4.3 as a reporting scale (not a fourth
   criterion), envelope stated in Section 5.2 (actionable to eta=0.68, degenerate from
   eta=1.97), Fig. 2 caption updated, and all four remaining "graceful" claims rewritten. Zero
   occurrences left in source or PDF.
8. **DONE 2026-09-16.** Abstract restructured (249/250 words) with C-MAPSS and the scoped,
   conservative bound; conclusions split into three paragraphs separating the calibration claim
   from the certificate claim. FEMTO dropped from the abstract for space, so the drafted R1.3
   response text in the log needs a one-line fix before the letter goes out.
9. **DONE 2026-09-16.** R2m1 ($m=1$ here, norm immaterial at $m=1$, concrete $m=2$ case in
   Appendix B), R2m2 completed with the irreducible factor of two from Lemma 1, R2m3 moved into
   Section 3.4. Fixed a symbol collision: Section 3.4 had used $m$ for the number of source
   conditions while $m$ is the dimension of psi elsewhere.
10. **DONE 2026-09-16.** `scripts/scc_figures.py` (new) regenerates fig1-fig3 from the
    evidence scripts: fig1 gains a C-MAPSS panel and a discrete-mode series, fig2 shades the
    actionability bands, fig3 annotates the margin. fig4_diagnostic is untouched and remains
    the one figure with no generator; closing that needs the n and departure it was drawn
    with. Fixed a caption that wrote the bound as $2(a+b\\delta)$, colliding with the
    back-off $b$ from task 7.
11. Write the point-by-point response letter (9 major + 3 minor).
12. Rebuild the flat EM variant and zip; verify single-column, no run-in heads, 0 undefined cites.
    Also rewrite `paper3/highlights.docx` (5 bullets, <=85 chars, must reflect C-MAPSS and the
    scoped certificate) and `paper3/cover_letter.docx`, both of which predate the narrowing.

## 8. Files

* `docs/module2/revision/REVISION_LOG.md` — all evidence, tables, numbers, manuscript actions.
* `docs/module2/revision/REVISION_HANDOFF.md` — this file.
* `scripts/scc_figures.py` — regenerates fig1-fig3 from the evidence JSONs and scripts.
* `scripts/r1*.py`, `scripts/r2*.py`, `scripts/cmapss_loader.py` — 15 revision scripts, all
  black- and ruff-clean, each reproducing the numbers it reports.
* `paper3/` — manuscript source (single-column elsarticle, sections 01-08). Tables as of
  2026-09-16: 1 robustness, 2 base model, 3 C-MAPSS, 4 discrete mode, 5 misspecification,
  6 design map.
