# Paper outline (Phase 1F.1)

**Working title:** A physics-informed, drift-adaptive soft-sensor framework with
calibrated uncertainty under delayed labels: from benchmark validation to a negative
control and production serving

**Venue:** Computers & Chemical Engineering (primary; elsarticle). Fallback: Journal of
Process Control with the narrow conformal-under-drift framing (extractable from the same
ledger; see ADR-012-era D2 decision in HANDOFF).

**Format:** markdown drafts in `docs/paper/sections/`, LaTeX conversion as a late
sub-phase (ratified D3). Target ~9,000–11,000 words + 8 figures + 3 tables.

---

## Contribution statement (the paragraph reviewers quote back)

Production soft sensors fail through five named mechanisms: model-selection lotteries
under autocorrelation, unhandled drift, delayed/infrequent labels, uncalibrated
confidence, and data scarcity on new processes. We present an integrated framework that
addresses each with a deliberately simple, auditable core — physics-derived features on
a linear sensor, blocked time-series CV with a one-standard-error rule, open-loop bias
updating, adaptive conformal intervals, and Bayesian model migration — validated on the
Tennessee Eastman process and the Debutanizer benchmark, stress-tested on SECOM as a
no-physics negative control, and shipped as a stateful serving architecture that honors
the delayed-label structure end to end. The negative control is a contribution, not a
concession: it isolates physics anchors as the source of point accuracy while
demonstrating that conformal validity (0.91 vs 0.90 target) survives even a failed
point model — the framework tells the truth about its own uncertainty.

Numbered contributions:
- **K1** Selection methodology: blocked CV + one-SE turns cross-regime lotteries into
  reproducible selection (Debutanizer; SECOM p≈n containment). [C1–C3]
- **K2** Drift + delayed labels: Shardt open-loop bias-update + ADWIN-on-corrected, with
  the delay θ treated as a first-class protocol parameter. [C4, C5, C8]
- **K3** Calibrated uncertainty under drift: from-primary ACI achieving regime-uniform
  0.90 ± 0.003 where static split conformal swings 0.847–0.957. [C7, C8]
- **K4** Transfer, honestly scoped: the methodology transfers across process topology
  unchanged (Debutanizer→TEP); Yan-style Bayesian GP migration with MAP regularization
  achieves ~10× data efficiency in within-process regime migration (TEP mode→mode),
  with literal cross-process parameter migration shown inapplicable (disjoint input
  spaces) and Luo degeneracy under a linear source documented. [C6]
- **K5** The negative control + deployment: SECOM validity-without-accuracy, and a
  two-flow stateful serving architecture (stored-interval invariant) with container/CI
  and a live monitor. [C9–C11]

---

## Section map (targets; evidence keys → claims_evidence.md)

1. **Introduction** (~900 w) — the five failure modes; contributions K1–K5; paper map.
   *Write last.*
2. **Related work** (~1,200 w) — three threads: (a) soft sensing under
   delayed/infrequent/irregular measurements (Guo 2014; Shardt 2016; Wang 2021);
   (b) process model migration (Lu 2008a/b, 2009; Luo 2015; Yan 2011); (c) conformal
   prediction for time series (Papadopoulos 2002; Barber jackknife+; Xu & Xie EnbPI;
   Gibbs & Candès ACI; Schlembach; Astigarraga review). Gap: no integrated treatment of
   selection + drift + delay + calibration + transfer in one deployable framework.
3. **Framework** (~2,500 w) — architecture figure F1; then per-component:
   3.1 physics features + transport-lag diagnosis (C2, C3); 3.2 blocked CV + one-SE
   (C1); 3.3 bias-update + drift detection (C4, C5); 3.4 adaptive conformal under
   delayed labels (C7, C8 — protocol: θ via bias-update, γ=0.05, ACI step);
   3.5 migration: methodology transfer + within-process regime migration (C6); 3.6 serving architecture (C11 — two flows,
   stored-interval invariant, snapshot).
4. **Case-study design** (~900 w) — TEP (Downs & Vogel; Bathelt revision; COSTEP),
   Debutanizer (Fortuna 2007), SECOM (UCI; VM framing + audited target selection, D1);
   splits, θ ∈ {2,5}, α = 0.10, metrics (R², coverage, width, data efficiency).
5. **Results** (~2,200 w) — 5.1 selection + features (F2, F3, T1); 5.2 drift + bias
   (F4); 5.3 coverage (F6 synthetic, F7 real-TEP, T2); 5.4 migration (F5; regime-migration framing explicit); 5.5 negative
   control (T3, F8); 5.6 deployment (latency note per C11 gap decision).
6. **Discussion** (~1,100 w) — validity-without-accuracy as the production stance;
   the linear-scope defense + nonlinear extension (anticipated objection, ADR-012
   revisit trigger); limitations stated plainly: single-instance serving, n=9
   enrichment inconclusive, VM target choice ours-to-defend (audit table is the
   defense), regime migration shown within one process (TEP); cross-process parameter migration inapplicable by construction.
7. **Conclusion** (~350 w).
Appendices: A — ADR index mapping decisions to sections; B — reproducibility
(deterministic runs, 67 tests, CI).

## Figure & table inventory (single `make figures` entry point; scripts under `scripts/paper_figures/`)

| ID | Content | Source | Status |
|---|---|---|---|
| F1 | Framework/serving architecture diagram | drawn (tikz/draw.io) | to draw |
| F2 | Physics-feature ablation by regime (Debutanizer) | new emitter | to script |
| F3 | CV path mean±SE vs α: Debutanizer lottery + SECOM explosion | new emitter (+ `secom_baseline.py` data) | to script |
| F4 | Residual trace raw vs corrected around drift | new emitter | to script |
| F5 | Regime-migration data-efficiency curve (TEP mode→mode) | re-run 1C emitter | to script |
| F6 | Synthetic conformal collapse (split vs ACI vs EnbPI) | `scripts/conformal_synthetic_check.py` | ✅ exists |
| F7 | Real-TEP coverage by regime × method × θ | new emitter from `conformal_eval.py` | to script |
| F8 | SECOM band segment (optional) | `secom_baseline.py` extension | optional |
| T1 | Transport-lag diagnosis table | results §1A | ✅ numbers |
| T2 | Coverage: dataset × method × θ (cov, width) | results §1D.1b + §1E | ✅ numbers |
| T3 | Cross-dataset summary (R², coverage; the negative-control row) | results | ✅ numbers |

## Writing order (drafting plan after 1F.1)
1. **1F.2** — figure emitters (`scripts/paper_figures/`) + the latency benchmark
   decision (C11 gap) → all evidence frozen.
2. **1F.3** — Results section first (it transcribes the ledger), then Framework, then
   Case-study design.
3. **1F.4** — Related work (PDFs are in-project), Discussion, Introduction, Conclusion,
   abstract.
4. **1F.5** — LaTeX/elsarticle conversion, reference list, submission package
   (highlights, cover letter, CRediT, data statement).
