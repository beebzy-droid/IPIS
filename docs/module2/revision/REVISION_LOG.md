# RESS major revision log — JRESS-D-26-04700

Decision: **Major revision**, Assoc. Editor Prof. Marko Cepin, 2 reviewers. Revised manuscript
due **2026-10-07**. Theory not challenged by either reviewer; all comments concern evidence
breadth, scope honesty, and one internal inconsistency.

Ratified scope (2026-09-07): D1 = C-MAPSS as the second dataset for R2.1; D2 = unit-level
calibration as primary with block conformal as the principled generalisation ("report both").

**Rule for this revision: no number enters the manuscript unless it comes from a committed
script in `scripts/` that reproduces it.** The previously published finite-sample sweep was run
ad hoc and was not reproducible; that is fixed here.

---

## Status board

| # | Reviewer ask | Type | Status | Evidence |
|---|---|---|---|---|
| R1.5 | Within-unit temporal dependence breaks exchangeability | rerun + theory | **DONE** | `scripts/r15_exchangeability.py` |
| R2m2 | Bound%=100 may mean loose, not valid; report tightness | analysis | **DONE** | `scripts/r15b_certificate.py` |
| — | Finite-sample sweep not reproducible from repo | reproducibility | **DONE** | `scripts/r15b_certificate.py` |
| R2.3 | Discrete-mode (Javanmardi) baseline in Fig. 2 | experiment | **DONE** | `scripts/r23_discrete_mode.py` |
| R1.1 | Bound conservatism vs base-model complexity | experiment | TODO | — |
| R1.4 | Misspecified physics may amplify shift | experiment | **DONE** | `scripts/r14_misspecification.py` |
| R1.2 | Design guideline: units/SNR needed for "holds" | experiment | TODO | — |
| R2.1 | Certificate on a second, non-authored dataset | new dataset | TODO | C-MAPSS FD002/FD004 |
| R2.2 | Derive psi for Lundberg-Palmgren + numeric example | appendix | TODO | — |
| R2.4 | Back-off 1.01 vs own degeneracy definition | concession | TODO | — |
| R1.3 | FEMTO is a lab testbed, not "field" | writing sweep | TODO | — |
| R2m1 | State m=1 in tested case; norm choice for m>1 | writing | TODO | — |
| R2m3 | Move the (pair, eta) clarification into Sec 3.4 | writing | TODO | — |

---

## R1.5 — within-unit dependence (RESOLVED, conclusions unchanged)

**The reviewer is right.** `scores_for()` stacked one score per (unit, monitoring fraction),
so with `FRACS = [0.3, 0.5, 0.7]` each unit contributed 3 strongly dependent calibration
points while Theorem 1 assumes i.i.d. draws.

Measured dependence at eta=0, T=650K: pairwise correlations across fractions
**0.965 / 0.883 / 0.877**, mean rho = **0.908**, design effect 1+(F-1)rho = **2.82**. So the
published n = 1200 stacked scores carried an effective n of about **426**, barely above the
**400** units.

Three calibration schemes compared (400 units/condition, 5 seeds, alpha = 0.10):

| scheme | n_cal | naive gap (eta=0) | SCC gap (eta=0) | SCC gap (eta=2) |
|---|---|---|---|---|
| stacked (as published) | 1200 | 0.131 | 0.006 | 0.103 |
| **unit (PRIMARY)** | 400 | 0.132 | **0.011** | **0.097** |
| block_max (simultaneous) | 400 | 0.164 | 0.007 | 0.173 |

**The violation did not manufacture the finding.** Under proper unit-level i.i.d. calibration
the headline is unchanged: naive conformal miscovers by ~0.13 while SCC recovers to ~0.011.

The change in the floor is exactly what theory predicts: losing 3x stacking should inflate the
finite-sample floor by sqrt(3) = 1.73, giving 0.006 x 1.73 = 0.010 against **0.011 observed**.

`block_max` (per-unit maximum score) is the stronger option: it certifies coverage
*simultaneously at every monitoring point* of a unit rather than at one sampled point, which is
the more useful maintenance guarantee, at the cost of a larger gap under departure (0.173 at
eta=2).

**Manuscript actions:** primary results move to unit-level; report block conformal as the
generalisation for multi-point monitoring; state explicitly that exchangeability is across
*units*, not across time steps within a unit.

## Certificate under unit-level calibration (headline preserved)

`dTV ~ 0.139 + 0.51*delta`, held-out **R^2 = 0.773** (was 0.792), corr(delta, dTV) = **0.947**,
a-priori bound holds on **100%** of held-out configurations.

## Finite-sample floor, rebuilt and unit-indexed

The published sweep (0.12 at n=200 to 0.04 at n=1600) was not reproducible from any committed
script, and its `n` mixed dependent stacked scores. Rebuilt against independent **units**:

| units | intercept a | a*sqrt(units) | SCC gap (eta=0) |
|---|---|---|---|
| 50 | 0.424 | 3.00 | 0.020 |
| 100 | 0.260 | 2.60 | 0.020 |
| 200 | 0.190 | 2.68 | 0.010 |
| 400 | 0.146 | 2.92 | 0.014 |
| 800 | 0.096 | 2.71 | 0.007 |

log-log slope of intercept vs units = **-0.513** against the -0.500 predicted by n^-1/2.
`a*sqrt(n)` is stable, confirming the scaling.

## R2m2 — bound tightness (HONEST NEGATIVE, must be reported)

The reviewer's suspicion is correct: Bound% = 100 in every row because the bound is
**conservative by roughly 8x**, not because it is sharp.

At 400 units/condition, held-out configurations: mean measured coverage gap **0.046**, mean
certified bound **0.384**, margin (bound - gap) mean **0.339**, min **0.268**, max **0.552**.

Source of the looseness is the **intercept**, not the physics slope: at delta = 0 the bound is
2a = 0.278 against a measured gap of 0.011. The intercept is the finite-sample floor of the
plug-in histogram TV estimator, and it decays as n^-1/2 (0.424 at 50 units to 0.096 at 800), so
tightness improves with calibration size. The 2x factor from the swap argument in Lemma 1 is a
second, irreducible source.

**Manuscript action:** report margin alongside Bound% in Table 1; state the conservatism factor
explicitly; frame the certificate as a worst-case planning bound rather than a sharp estimate,
and name the estimator floor as the dominant term.


## R2.3 — discrete-mode clustering baseline (DONE)

The three testbed temperatures are treated as the known discrete modes of Javanmardi and
Huellermeier, which is the fairest possible reading of their method. Coverage gap, target 0.90,
unit-level calibration, mean over targets and 5 seeds:

| eta | scenario | discrete-mode | SCC | naive/pooled |
|---|---|---|---|---|
| 0.0 | seen | 0.011 | 0.009 | n/a |
| 0.5 | seen | 0.017 | 0.031 | n/a |
| 1.0 | seen | 0.009 | 0.045 | n/a |
| 0.0 | unseen | 0.078 | **0.009** | 0.093 |
| 0.5 | unseen | 0.109 | **0.025** | 0.128 |
| 1.0 | unseen | 0.138 | **0.040** | 0.159 |

**Honest in both directions.** When the target regime HAS its own run-to-failure data, discrete
mode calibration is near-oracle and beats SCC once the departure is large (0.009 vs 0.045 at
eta=1). SCC matches it at eta=0 while using no target failure data at all.

When the target regime has NO failure history, which is the situation SCC exists for,
discrete-mode conformal has no calibration set for that mode, must fall back to the nearest
mode, and lands close to regime-blind pooling (0.078 to 0.138 against pooled 0.093 to 0.159).
SCC holds at 0.009 to 0.040, a 3.5x to 8.7x smaller gap.

**Manuscript action:** add as a third series in the coverage figure; state plainly that with
target failure data the discrete remedy is preferable under strong departure, and that SCC's
advantage is specifically the no-target-data regime.

## R1.4 — misspecified physics: backfire risk and its detectability (DONE)

Misspecification is applied to the activation energy while holding k(T_ref) fixed, so only the
BETWEEN-temperature behaviour of the scale is distorted, which is what similitude depends on.

Decoupled (only the scale is wrong; isolates the reviewer's question):

| dE/E | naive gap | SCC gap | verdict |
|---|---|---|---|
| -50% | 0.132 | 0.076 | degraded |
| -31% | 0.132 | 0.047 | ok |
| 0% | 0.132 | 0.011 | ok |
| +19% | 0.132 | 0.036 | ok |
| +62% | 0.132 | 0.105 | degraded |
| +100% | 0.132 | 0.139 | **backfire** |

Safe band (SCC gap <= 0.05): |dE/E| up to **31%**. SCC remains better than not scaling out to
+62%; it becomes worse than the unscaled baseline only at **+100%**.

Coupled (one wrong model drives predictor AND scale, the realistic case) is far more fragile:
backfire appears from **-10%** (0.072 vs 0.061) and -19% (0.157 vs 0.030).

**Detectability (the mitigation).** The dimensionless-life invariance check, which uses source
data only and needs no target failure history, returns:

| dE/E | g | 95% CI | verdict |
|---|---|---|---|
| -10% | 1.215 | [1.16, 1.27] | violated |
| 0% | 0.967 | [0.92, 1.01] | **holds** |
| +10% | 0.769 | [0.73, 0.81] | violated |
| +100% | 0.098 | [0.09, 0.10] | violated |

The diagnostic returns **holds only at the correct scale** and flags **violated at every
misspecification tested, including the -10% point where coupled backfire begins**. The failure
mode the reviewer identifies is therefore detectable before deployment.

**New capability finding:** the runtime diagnostic catches SCALE MISSPECIFICATION, not only
similitude departure. This was not claimed in the submitted manuscript and should be stated.

**Manuscript action:** new subsection quantifying the tolerance band, the coupled-case fragility,
and the diagnostic's detection of both; extend Section 3.5 to state the diagnostic's dual role.
