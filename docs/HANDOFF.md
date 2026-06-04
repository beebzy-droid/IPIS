# IPIS — Project Handoff & Continuity Doc

**Single source of truth for resuming work across chat sessions.** This repo is
the memory; chat sessions are disposable and compress. A fresh session becomes
fully productive by reading this file plus the artifacts it points to.

---

## 0. How to use this doc (read first)

**Why it exists.** The assistant (Claude) has **no persistent memory between
sessions** and **cannot reliably record things mid-session** — each turn it sees
only the live conversation (which compresses as it grows) plus this repo.
Therefore continuity cannot depend on the assistant "remembering." It depends on
this committed file.

**Update protocol (self-enforcing):**
- Update and commit `docs/HANDOFF.md` **at the end of every phase**, and **whenever
  a decision becomes load-bearing** (a number, a method choice, a parked/deferred
  item). Bump the changelog at the bottom.
- The assistant proposes the diff; the owner (Bien) commits it (see working
  agreement). If a session is ending, the assistant should offer to update this
  file before close.

**Resume order for a new session:**
1. This file (`docs/HANDOFF.md`) — working agreement + live thread.
2. The latest ADR in `docs/architecture/decisions/`.
3. `docs/module1/results.md` + `docs/module1/lessons-learned.md`.
4. `docs/sources/source-map.md` before building anything that needs a number.

Then jump to **§9 Resume here**.

---

## 1. Working agreement (how we operate)

**Coworker mode.** Division of labor is fixed:
- **Bien** runs *all* terminal commands and *all* git operations, on **Windows
  `cmd`** (not PowerShell/bash — give `cmd`-syntax, one command per line, no `\`
  line-continuations). Conda env is **`ipis`**, Python **3.11+**.
- **Claude** builds and tests code in its own Linux sandbox, then hands off
  finished files for Bien to place (usually via `%USERPROFILE%\Downloads\`) and
  commit. Claude never assumes it can run the repo's tests directly against
  Bien's machine; it validates in-sandbox against a faithful local copy.

**Verify-before-load-bearing.** No equation, coefficient, threshold, or algorithm
enters the repo until it's checked against a primary source *at the moment of
use*. Synthesized summaries are hypotheses, not truth. This has already caught
real errors. Project library is indexed in `docs/sources/source-map.md`; new
sources get registered there (Tier-1) when first used.

**Numbers-first.** Lead with quantified results (R², SE, latency, compute, %).
Every recommendation ties to a measurable outcome. Bounded estimates beat vague
claims. Honest about uncertainty and failure modes — the lessons-learned doc is a
feature, not an afterthought.

**Option-scale deliberation.** Before an engineering choice (detector, model
form, etc.), walk the full option space against primaries, recommend, get
ratification, *then* build. This pattern produced every 1B decision.

**Quality gates (run before every commit):**
```cmd
black src tests scripts
ruff check src tests scripts
pytest tests/unit --no-cov -q
```
Ruff config: line-length 100, select E/W/F/I/B/C4/UP/N/SIM, ignore E501/N803/N806;
tests ignore S101/SIM300. Black default. Scripts that need the (gitignored)
benchmark data are **not** CI-tested; library code + unit tests **are**.

---

## 2. Project vision

**IPIS — Integrated Process Intelligence System.** A hybrid, digital-twin-backed
framework with three modules on a first-principles physics layer:

1. **Module 1 — Soft Sensor** — real-time prediction of hard-to-measure quality
   variables. **(in progress)**
2. **Module 2 — Predictive Maintenance** — anomaly detection + RUL. **(planned)**
3. **Module 3 — RTO** — constrained setpoint recommendations. **(planned)**

Digital twin layer = **DWSIM + GEKKO + CoolProp**. Operational bus = MQTT +
InfluxDB. Front = Streamlit + FastAPI.

**Three gaps it claims to close** (one per failure mode in industrial AI):
- Cross-process generalization (models don't transfer across plant topologies).
- Grade-transition robustness (models degrade during operating-regime shifts).
- POC-to-production gap (87% of industrial AI projects fail at deployment).

**Tech stack:** PyTorch, scikit-learn, XGBoost, **River** (online), **MAPIE**
(conformal); DWSIM/CoolProp/GEKKO; OPC-UA (asyncua)/MQTT/InfluxDB/FastAPI/
Streamlit; MLflow/Hydra/Docker/GitHub Actions/pytest. Owner: **Bien Busico**.

---

## 3. Dataset hierarchy (ADR-003)

| Role | Dataset | Question |
|---|---|---|
| Primary (development) | **Debutanizer Column** (Fortuna et al.) | Does the hybrid beat baselines? |
| Secondary (transfer) | **Tennessee Eastman (TEP)** | Does it transfer across topologies? (21 disturbance modes) |
| Supplementary (stress) | **SECOM** (semiconductor, 590 feat) | Does it survive a different industry? |

Debutanizer specifics: 7 inputs (u1 top temp, u2 top pressure, u3 reflux, u4
downstream flow, u5 6th-tray temp, u6/u7 bottom temps), y = C4 in bottoms; 2,394
samples; analyzer = gas chromatograph.

---

## 4. Decision log (ADRs)

| ADR | Title | Status |
|---|---|---|
| 001 | Path B PINN (residual hybrid, not pure PINN) | **Superseded by ADR-007** |
| 002 | OPC-UA/MQTT infrastructure at Level 1 scope | Accepted |
| 003 | Three-dataset hierarchy (distinct validation roles) | Accepted |
| 004 | Analytical-first physics baseline | Accepted (supersedes DWSIM-first sequencing) |
| 005 | MATLAB/Simulink scope | Accepted |
| 006 | GPR belongs to Module 3 (surrogate), not Module 1 | Accepted |
| 007 | Dynamic physics-anchored soft sensor (Phase 1A) | Accepted; supersedes 001 |
| 008 | Phase 1B drift detection + Shardt bias-update | Accepted |

Note: ADRs 001–006 use bare numbering, 007/008 use `ADR-NNN-` prefix. All live in
`docs/architecture/decisions/`. Cosmetic renaming to one scheme is a deferred
cleanup task.

---

## 5. Module 1 roadmap (phases)

| Phase | Scope | Status | Target |
|---|---|---|---|
| **1A** | Hybrid model on Debutanizer | **✅ Complete** (ADR-007) | Wks 1–4 |
| **1B** | Drift detection + adaptive correction | **✅ Complete** (ADR-008) | Wks 5–7 |
| **1C** | Cross-process transfer (Debutanizer → TEP) | **▶ NEXT** | Wks 8–12 |
| 1D | Production deployment stack | Not started | Wks 13–16 |
| 1E | SECOM stress test | Not started | Wks 17–18 |
| 1F | Writing & submission | Not started | Wks 19–20 |

1C target (publishable contribution): fine-tune the Debutanizer model on TEP with
**<30% of the data a full retrain needs**. 1D includes the conformal/MAPIE work
and FastAPI (<200ms) + Streamlit dashboard + Docker/CI. 1E applies the framework
as-is to SECOM and documents where it breaks.

---

## 6. Completed work — detailed state

### Phase 1A — physics-anchored soft sensor (ADR-007)
- **Journey:** static single-tray bubble-point physics at lag 0 → R²=**0.018**
  (physics math verified vs Perry's + Smith, 0% clipping; failure was applying it
  *statically*). Signal diagnosis: C4 driven by **u5 at a stable ~15-sample
  transport lag** (lag-15 r²≈0.51 in every split). Naive 126-feature lagged PLS
  overfit to regime: train 0.77 / val 0.75 / **test 0.04** (covariate shift, not
  classic overfit, not leakage). **Blocked forward-chaining CV + 1-SE parsimony**
  recovered held-out test **R²=0.52** (k=1, 13× the naive selection) and exposed
  negative CV folds (SE > |mean|) = cross-regime calibration drift.
- **As-built model** carried into 1B: physics-anchored linear, held-out test
  **R²=0.476**, blocked-CV **+0.145 ± 0.419**, worst fold **−1.49**.
- **Key lesson:** a temporally-adjacent validation split cannot certify
  cross-regime generalization. Blocked CV is the honest instrument.

### Phase 1B — drift detection + Shardt bias-update (ADR-008)
- **Detection** (`evaluation/drift.py`): **ADWIN** primary (δ=0.002, scale-free,
  0 false alarms over 2e5 in-control), **Page-Hinkley** + in-house **CUSUM**
  comparators (CUSUM ARL₀-validated: k=0.5σ,h=4σ → 169.5 vs textbook 168). ADWIN
  is **supervisory** (regime flag), *not* the trigger — latency ~260 too slow.
  PH/CUSUM over-fire on the heteroscedastic residual when scaled to a single σ.
- **Correction** (`evaluation/bias_update.py`): **Shardt (2016) open-loop
  bias-update** — feedforward EWMA on the delayed residual,
  `b_t = (1−λ)b_{t−1} + λ(y_{t−θ} − ŷ_{t−θ})`, `corrected = ŷ_t + b_t`. λ=1 =
  most-recent-residual (Shardt open-loop Case I). Feedforward → unconditionally
  stable. Closed-loop integrator (Shardt Eq.6/10) **deferred to M3**.
- **θ = 4** (label/analyzer delay) — Fortuna GC delay (their NARMA uses 4 output
  lags). **Distinct from the ~15 transport lag in the features.** λ CV-selected.

**Headline result (θ=4, λ=0.1):**

| metric | static | bias-update | JITL always (h=2) | JITL gated |
|---|---|---|---|---|
| CV mean R² | +0.145 | **+0.648** | +0.405 | +0.146 |
| CV SE | 0.419 | **0.046** | 0.215 | 0.419 |
| worst fold | −1.49 | **+0.487** | −0.392 | −1.49 |
| held-out test | +0.476 | **+0.857** | +0.519 | +0.506 |
| local fits (compute) | 0 | **0** | 1,620 | 37 |

- Bias-update **dominates** the literature-standard JITL (Cheng & Chiu 2004,
  `evaluation/jitl.py`, locally-weighted linear) on every axis at zero local
  fits. The drift is a per-regime *offset* on a *stable* relationship; the
  bias-update targets exactly that.
- Oracle (best constant per-fold offset) = +0.540 CV; the causal update **exceeds**
  it (tracks within-fold drift).
- θ-bracket: θ=2 → 0.707±0.044; θ=4 → 0.648±0.046; θ=8 → 0.599±0.060 (monotonic,
  all positive, SE 7–9× tighter).

### Negative / honest results (on record)
- **θ not identifiable from data** (`scripts/infer_label_delay.py`, cross-corr
  method 3): u5 anchor=15 (gate passed) but bottom-temp lag=17 > 15 → implied
  transport −2 (impossible) → premise falsified. θ=4 kept as sourced convention.
- **JITL is dimension-fragile**: R²≈−8 on the raw 112-feature lagged set (curse of
  dimensionality); works only on low-dim physics-anchored features.
- **Detector-gated adaptation too slow**: ADWIN-gated JITL ≈ static — proves
  adaptation here must be *continuous*, not drift-triggered.

---

## 7. The ledger — parked / deferred / owed

- **PARKED — Wang DTDE (dynamic time-delay re-estimation, SD-DU + WRVM).** Best
  lag is stable (14–15) across all splits, so delay re-estimation solves a problem
  we don't have. Revisit only if a future process shows unstable delay.
- **DEFERRED to M3 — closed-loop integrator bias term** (Shardt Eq.6/10, Σaⱼ=0,
  exact tracking). Needed only if the soft sensor drives control.
- **OWED before 1F — conformal prediction (MAPIE).** Was a planned 1A scorecard
  metric, never built. Lands in **1D** (or a 1A/1B addendum). The only genuine
  missing deliverable (the model/drift divergences from the original spec are
  recorded, defensible pivots).
- **LOAD-BEARING ASSUMPTION — θ=4.** Benchmark convention; the true plant delay
  was "great and unknown." Re-pin on any real column. Sensitivity bracket is the
  defense.
- **DEFERRED cleanup — ADR numbering** (bare 00N vs ADR-NNN prefix). Cosmetic.

---

## 8. Repo structure (where things live)

```
src/ipis/module1_soft_sensor/
  evaluation/
    blocked_cv.py      # blocked_cv_r2, mean_se, Estimator/FeatureBuilder types
    drift.py           # ADWIN/PH/CUSUM detectors, scan, blocked_cv_residuals,
                       #   FoldResiduals  (NOTE: blocked_cv_residuals lives HERE,
                       #   pinned to blocked_cv_r2 by an equivalence test)
    bias_update.py     # Shardt open-loop EWMA bias-update, corrected_fold_r2, oracle
    jitl.py            # locally-weighted linear (Cheng-Chiu), gating, JITLFoldResult
  features/
    lagged.py          # make_lagged_features, DEFAULT_INPUT_COLS/TARGET_COL
    physics_features.py# make_physics_anchored_features (u5 lag, bubble-pt, stripping)
  physics_bridge/      # dippr101, bubble_point_inversion, bridge
  data/                # loaders (DebutanizerLoader), preprocessing (time_ordered_split, DataSplit)
scripts/               # detect_drift, bias_update_eval, infer_label_delay, jitl_vs_bias_eval
tests/unit/            # test_drift, test_bias_update, test_jitl  (~140 tests total)
docs/
  HANDOFF.md           # THIS FILE
  module1/             # spec, results, lessons-learned
  architecture/        # system-overview, decisions/ (ADRs)
  sources/source-map.md
```

Splits: `time_ordered_split` → train 1675 / val 359 / test 360 (0.70/0.15/0.15).
Pool (train+val) = 2034 used for blocked CV; test = held-out final regime.

---

## 9. Sources registered (Tier-1) and the discipline

`docs/sources/source-map.md` is the index. Tier-0 = Perry's (9th authoritative
for citations, 8th/7th cross-check; **edition-internal fixtures** rule — a
fixture's input and expected value must come from the same edition). Tier-1
sources used so far:
- **Shardt & Yang 2016** — bias-update form, open-loop Case I, integrator (M3).
- **Bifet & Gavaldà 2007** — ADWIN.
- **Page 1954** — CUSUM / Page-Hinkley.
- **Montgomery (SPC)** — CUSUM ARL₀ validation.
- **Fortuna et al. 2005/2007** — Debutanizer benchmark, θ=4 source.
- **Cheng & Chiu 2004** — JITL baseline.

**1C reference backbone (model migration), in the project library:** Lu & Gao
2008 (process similarity), Lu 2008 (inclusive similarity), Lu et al. 2009
(similarity + migration), Yan et al. 2011 (Bayesian migration of GPR), Luo et al.
2015 (Bayesian improved migration), Kajero et al. (meta-modelling review:
scale-bias correction, functional SBC, Bayesian migration). Guo/Zhao/Huang 2014
and Wang et al. 2021 (DTDE-WRVM) were the 1B soft-sensor-delay backbone.

---

## 10. RESUME HERE → Phase 1C COMPLETE (cross-process transfer)

**Status:** 1A ✅, 1B ✅, **1C ✅ (data + part-A baseline + 3-method migration + MAPIE)**.
**Next:** write up Phase 1C, then 1D (production stack incl. MAPIE productionization),
1E (SECOM), 1F (writing).

### 1C framing (DECIDED, user-ratified): A + C, not literal Debutanizer→TEP
SBC migration requires a *shared input space* + *similar processes* (verified from
Lu 2008/2009, Yan 2011, Luo 2015), so literal Debutanizer→TEP parameter migration
is mathematically inapplicable (disjoint variables). 1C = **(A) methodology
transfer** (the recipe rebuilt on TEP works) + **(C) within-TEP regime migration**
(SBC across TEP operating regimes, <30%/data-efficiency framing). Rejected (B) deep
transfer learning.

### Data (DONE)
COSTEP (Simulink) abandoned (non-reproducible reactor-pressure startup trip; known
TEP sensitivity = missing init `Mode1xInitial.mat` + override loops). Pivoted to the
**Russell/Chiang/Braatz closed-loop FORTRAN** (the d00–d21 simulator), compiled
headless with gfortran, generated in-sandbox. Three operating-point regimes
(`data/raw/tep/tep_mode{1,2,3}.csv`, 2000 rows = 100 h @ 3-min, IDV 8+10+13
excitation, SETPT(14)/(15)=reactor-feed D/E mol% = the G/H lever):
mode1 G 53.8±1.0, mode2 G 58.2±1.1, mode3 G 63.4±1.7; all 0% pressure-pinned,
multivar R² 0.57–0.71. **Feed-ratio operating points, NOT canonical Downs&Vogel
modes** — honest framing, sufficient for Option C. Target = XMEAS(40)=G; analyzer
delay → **θ≈5 documented** (θ=2 empirical best on this data). Reproduce via
`scripts/generate_tep_modes.py` (needs Braatz repo + gfortran). Canonical mv-per
modes 1/3/4 fetched (LFS) as **supplementary** (loader + converter built) but
**under-excited** for soft sensing (within-mode R²~0.04) → generated regimes are headline.

### Part A — single-mode baseline (DONE, `scripts/tep_baseline.py`)
The Debutanizer recipe transfers to TEP: static physics-anchored blocked-CV R²
−0.089±0.493 (same calibration-drift signature), test +0.31; **1B bias-update
applied unchanged** recovers it to CV +0.19 (θ=5) / +0.45 (θ=2) → **methodology
transfers across topology**. Transfer gap: mode1 model → mode2/mode3 R² −1.08/−1.30
(migration motivation).

### Part C — 3-method migration (DONE) — HEADLINE: ~10× data efficiency
Code: `src/ipis/module1_soft_sensor/migration/{sbc,functional_sbc,matrix_sbc,sweep}.py`,
`scripts/tep_migration.py --method {osbc,yan,luo} --bias-update lam,theta --n-repeats k`.
Two-layer architecture: **migration (offline, across regime) + 1B bias-update
(online, within regime)** — the bias-update removes within-mode drift that
otherwise caps every curve. **ROBUST metric = data efficiency to reach 90% of the
from-scratch ceiling** (the strict "exceed the ceiling" crossover is BRITTLE here
because ceilings coincide — it flipped 20%↔100% across seeds; NOT headlined).
Reproduce with `--n-repeats 8` (n_repeats=3 too noisy at low f); GP O(n³) → subsample.

| method | form | params | mode2 data-eff | verdict |
|---|---|---|---|---|
| **Lu OSBC** (2008a) | output-only `S_O·z+B_O` | 2 | ~3.3× | preserves source shape; can't fix relationship change |
| **Luo matrix** (2015) | per-input `ρ₀·x+λ₀` inside z + output affine | 2d+2 | **~1.0× (no gain)** | for a LINEAR source ≡ from-scratch (ρ₀ absorbs source weights); needs nonlinear source |
| **Yan functional** (2011) | `s(x)·z+δ(x)`, δ=GP | GP | **~10×** | adds local nonparametric bias; keeps source AND fixes relationship → **winner** |

Yan (n_repeats=8): mode2 & mode3 both reach 90% of from-scratch full accuracy at
~5% target data vs ~50% from-scratch = **~10×**; **calibrated 95% GP intervals**
(coverage 92–98%, WIDER for the larger mode3 gap 2.8–4.0 vs 2.6–3.2) → **MAPIE/
conformal debt DISCHARGED** on the transferred model. **Bigger gap ⇒ migration helps
MORE** (mode3 dominance even stronger). Luo ≡ from-scratch VERIFIED analytically +
synthetic (R²=1.0=from-scratch on a different linear target) + TEP (migrated tracks
from-scratch ±0.005 every fraction). **METHODOLOGICAL TAKEAWAY: migrate a
parametric/linear source by ADDING a nonparametric bias (Yan), NOT by reshaping its
inputs (Luo).** `Migrator` interface gained optional `source_fn` (built-features →
source pred; only Luo uses it). ~36 migration+tep tests; full suite ~190.

### Ledger
- **MAPIE/conformal: DISCHARGED** for 1C via Yan's calibrated GP posterior (still
  owed as a *productionization* item for 1D).
- All three staged migration primaries (Lu, Yan, Luo) now built + benchmarked.
- Honest caveats baked in: regimes are feed-ratio operating points (not canonical
  modes); report data-efficiency not the brittle crossover; θ is data-specific.

### NEXT ACTION: write up Phase 1C
The arc: (A) methodology transfers across topology (Debutanizer recipe → TEP, test
R² 0.31, bias-update recovers) + transfer gap −1.08/−1.30 motivates migration →
(C) 3-method SBC migration with the two-layer composition → **Yan ~10× data-
efficient + calibrated intervals**, OSBC ~3.3×, Luo ≡ from-scratch (with the
linear-source explanation). Then ADR for 1C, then Phase 1D.

---

## Changelog of this doc
- **2026-06-03** — Created. Working agreement + project vision + full 1A/1B state
  (through the JITL head-to-head) + parked/deferred/owed ledger.
- **2026-06-03** — 1C framing decided (A+C). COSTEP abandoned; pivoted to
  Russell/Braatz FORTRAN. 3 TEP operating-mode datasets validated; TEP loader +
  physics features + tests. Target=XMEAS(40); θ≈5.
- **2026-06-04** — Part-A baseline done (recipe transfers; transfer gap −1.08/−1.30).
  Canonical mv-per modes fetched (supplementary, under-excited). 3-method migration
  COMPLETE: two-layer composition (migration + 1B bias-update); robust data-efficiency
  metric; **Yan ~10× + calibrated intervals (MAPIE discharged)**, OSBC ~3.3×, Luo ≡
  from-scratch (linear-source degeneracy, verified). Doc de-duplicated/rebuilt.
  Resume = Phase 1C writeup.
