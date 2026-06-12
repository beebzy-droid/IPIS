# Module 1 — Lessons Learned

Honest postmortem per phase. This document is for engineering credibility — what worked, what didn't, what would be done differently. Reviewers and interviewers reward this kind of honesty.

Each phase entry follows the structure:

- **What worked** — decisions that paid off
- **What didn't** — decisions that turned out wrong, dead ends, time sinks
- **What I would do differently** — with the benefit of hindsight
- **What this implies for downstream phases**

---

## Phase 1A — Hybrid Model on Debutanizer

*Status: complete (ADR-007).*

### What worked
- **Diagnosing the signal before modeling.** Finding the stable ~15-sample
  u5→C4 transport delay first meant the eventual model was anchored to real
  process structure, not fit blind.
- **Blocked forward-chaining CV over adjacent validation.** This is the single
  highest-value methodological choice in the phase — it exposed a covariate-shift
  failure (test 0.04) that train≈val (0.77/0.75) completely hid.
- **1-SE parsimony.** Selecting maximum parsimony recovered held-out R² = 0.52,
  13× the naive selection, and made the model interpretable.

### What didn't
- **Static single-tray physics at lag 0** — R² = 0.018. The bubble-point math was
  correct (verified against Perry's + Smith, 0% clipping); applying it statically
  to a dynamic process was the error. Correct physics, wrong framing.
- **The 126-feature lagged kitchen-sink PLS** — looked healthy (train ≈ val) and
  scored test 0.04. A textbook reminder that "train ≈ val" is not evidence of
  generalization when val is temporally adjacent.

### What I would do differently
- Lead every soft-sensor effort with lag/signal diagnosis before fitting anything.
- Never trust a temporally-adjacent validation split for a cross-regime claim —
  reach for blocked CV from the first experiment, not after the naive model
  flatters itself.

### Implications for downstream phases
- The negative CV folds (calibration drift: stable correlation, drifting
  slope/intercept) are the exact problem Phase 1B solves with an online
  bias-update — 1A produced the diagnosis that scoped 1B.
- **Architecture pivot:** the as-built model is a dynamic physics-*anchored*
  linear model, not ADR-001's PINN/residual hybrid. ADR-001 anticipated a
  graceful fallback to a standard learner; the empirical findings pushed past
  even that to a physics-feature-anchored linear model. ADR-007 supersedes
  ADR-001; the PINN (Path A) remains private future work, not externally promised.

---

## Phase 1B — Drift Detection & Adaptive Bias-Update

*Status: complete (ADR-008).*

### What worked
- **Residual-based detection on the same CV backbone** (`blocked_cv_residuals`
  pinned to `blocked_cv_r2` by an equivalence test) — one source of truth for the
  fold mechanics, no divergence risk.
- **Shardt open-loop bias-update (feedforward EWMA).** Stable for any λ, one knob,
  faithful to the verified primary. Turned worst fold −1.49 → +0.49 and cut
  cross-regime SE 9.1×.
- **Benchmarking the targeted fix against the literature standard.** Building JITL
  (Cheng & Chiu 2004) as a fair baseline turned a substitution we would have had
  to *defend* into a result we can *claim*: the O(1) bias-update dominates O(N)
  JITL on calibration-drift data.
- **Verify-before-load-bearing.** Every algorithm (ADWIN, Page-Hinkley, CUSUM,
  the bias-update form, θ) was checked against a primary source before it carried
  weight — including a CUSUM ARL₀ validation against the textbook (169.5 vs 168).

### What didn't
- **Page-Hinkley / CUSUM scaled to a single reference σ** over-fire on the
  heteroscedastic residual (later folds run 3× the σ of fold 0). They stayed
  comparators, not the primary.
- **ADWIN as a trigger** — latency ~260 samples on a gradual shift, too slow to be
  the correction. Relegated to a supervisory regime-change flag.
- **Trying to derive θ from the data** (cross-correlation method 3) — inconclusive
  by design: the dataset is "data rich, information poor." Logged as a negative
  result rather than buried.
- **JITL (LWR) is dimension-fragile.** On the raw 112-feature lagged set its
  Euclidean similarity collapsed (curse of dimensionality) and it scored R² ≈ −8;
  it worked only on the low-dim physics-anchored features. The bias-update has no
  such dependence.
- **Detector-gated adaptation was too slow here.** ADWIN-gated JITL ≈ static
  (latency ~260 fires after the catastrophic fold's damage is done) — empirical
  proof that continuous adaptation, not a drift trigger, is what closes Gap 2 on
  this process.

### What I would do differently
- Set detector scale from a robust/per-regime σ from the start, not a single
  reference window.
- Treat θ as a sourced physical constant from the outset, not a tunable — the
  θ-sweep is a sensitivity check, never an optimization target.

### Implications for downstream phases
- **Correction mechanism diverged from plan:** the spec planned JITL retraining;
  the as-built correction is the Shardt bias-update (more principled for a
  calibration-drift failure mode). ADR-008 supersedes the JITL line in the spec.
- **Closed-loop integrator** (Shardt Eq. 6/10, exact tracking) is deferred to
  Module 3 — needed only if the sensor drives control.
- **θ is a load-bearing assumption** (=4, benchmark convention); re-pin on any
  real column with a known analyzer cycle.
- **Conformal uncertainty (MAPIE) is still owed** — planned in the 1A scorecard,
  not yet built. Candidate for 1D or a 1A/1B addendum before 1F writing.

---

## Phase 1C — Cross-Process Transfer

*Status: **complete** (ADR-009).*

### What worked
- **Honoring the SBC scope constraint up front.** Reading Lu/Yan/Luo closely enough
  to see that model migration needs a shared input space turned a doomed task
  (literal Debutanizer→TEP) into the right one (A+C). The framing decision was the
  highest-leverage move in the phase.
- **Reusing 1B unchanged.** The Shardt bias-update code, written for the
  Debutanizer, dropped onto TEP with zero edits and recovered the static model the
  same way — concrete evidence the recipe is portable, not bespoke.
- **Data efficiency as the metric.** Switching from the brittle ceiling-crossover
  to "fraction to reach 90% of the from-scratch ceiling" produced a stable,
  reproducible ~10× result that matched to the decimal across machines.
- **Verify-before-load-bearing on the Luo claim.** Predicting analytically that
  Luo ≡ from-scratch for a linear source, then confirming it three ways
  (synthetic R² 1.00, TEP tracking ±0.003), is exactly the discipline that makes a
  negative result publishable rather than a hand-wave.

### What didn't
- **COSTEP/Simulink** burned time before the Russell/Braatz pivot — a reminder to
  validate a data source's reproducibility before building on it.
- **The strict crossover metric** flipped 20%↔100% across seeds and nearly led to
  an overclaim ("<30% confirmed"); caught it on the second machine-reproduction and
  reframed. Knife-edge metrics where two curves coincide should be distrusted by
  default.
- **`lm` solver + small fractions.** Luo's 22 parameters made `lm` fail when
  n_samples < n_params at the 5% fraction; `trf` was needed. A reminder that
  solver choice interacts with the experiment design (the data-fraction grid).
- **DataFrame-fitted scaler + numpy calls** flooded thousands of warnings and
  slowed Luo to a crawl — fit on numpy when the model will be called on numpy.

### What I would do differently
- Pin the data-efficiency metric and `--n-repeats ≥ 8` from the start, before
  reporting any crossover number.
- Build a nonlinear source variant earlier so Luo isn't degenerate — the
  three-method comparison would have been more informative with a source where all
  three methods are viable.

### Implications for downstream phases
- **1D:** Yan's GP is O(n³) → needs subsampling or a sparse/conformal replacement
  for production; the MAPIE wrapper owed for productionization lands here. A
  nonlinear source model would also re-open Luo as a viable middle ground.
- **Writing (1F):** the cleanest story is the methodological lesson — *migrate a
  parametric source by adding a nonparametric bias, not by reshaping its inputs* —
  backed by the OSBC/Luo/Yan contrast and the ~10× + calibrated-interval result.

---

## Phase 1D — Production-Ready Deployment Stack

*Status: not started*

---

## Phase 1E — SECOM Stress Test

*Status: not started*

---

## Phase 1F — Writing & Submission

*Status: not started*


## Phase 1F — writing & submission

- **The evidence freeze pays for itself during writing, not after.** Argv-stamped
  evidence JSONs caught a wrong regeneration command (bare migration read 3.3×/n-a
  until `--bias-update 0.3,2` restored the documented two-layer conditions) and
  killed a figure that never existed (the "Debutanizer α-path" panel — the 1A lottery
  was always fold-spread evidence). Run conditions belong in the command; provenance
  stamps make the difference auditable.
- **Sweep the literature on every "first to" claim before a reviewer does.** §2.3's
  "not aware of prior work" on delayed-feedback conformal prediction was refuted by
  the IM-OCP/corrupted-feedback line. The repositioned claim — the engineering
  instantiation (delay through both correction layers + stored-interval pairing
  enforced structurally) — is narrower and stronger because it is defensible.
- **Verify references at publisher-metadata level; CVs and memory both fail.** The
  sweep caught a wrong first author (Qiushuo Hou, mis-recalled as Jing), a wrong
  edition year (Smith 9th ed = 2022, not 2018), and resolved a page-number conflict
  where the author's own CV was the outlier against Semantic Scholar + ADS bibcode.
  Rule: machine-derived publisher metadata > hand-maintained pages > recollection.
- **BibTeX silently eats fields after inline `%` comments inside entries** — the
  "empty year" warning on a complete entry was the tell. TODOs go in `note` fields.
- **Mounted "PDFs" may not be PDFs.** The project-source files were ZIP archives of
  JPEG page scans (PK magic); `pdftotext` returned empty without erroring loudly.
  Check file magic before concluding a document has no text layer.


## Reviewer pass (post-1F)

- **"Compiles clean" is not "renders correctly."** pdflatex silently DROPS unicode
  Greek and math glyphs in text mode — λ, θ, ≈, × vanished from prose with zero
  errors and a 0-undefined log. The defect was invisible to every exit-code check and
  found only by rasterizing pages and looking. Rule: visually inspect at least the
  pages carrying tables, equations, and Greek-letter prose before calling a PDF final.
- **Pandoc artifacts survive successful compiles.** Auto-width tables overflowed the
  page by up to 1224 pt (the user-visible "text overlaps"), and `\hypertarget` slugs
  printed as literal body text without hyperref. Hand-write submission tables; strip
  hypertargets post-conversion; treat the Overfull count in the log as a gate.
- **Write for the journal's discipline, not the work's toolchain.** The serving stack
  is software, but CACE readers are process engineers: "two async flows over mutable
  state" became "estimation and reconciliation paths over a calibration state," and
  Docker/CI/test-count evidence became analyzer-cycle feasibility. The figure labels
  carry register too — F1's panel (b) needed relabeling, not just the prose.
