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

## 10. RESUME HERE → Phase 1C (cross-process transfer) — DATA STAGE DONE

**Framing DECIDED (user-ratified): A + C, not literal Debutanizer→TEP.**
SBC migration requires a *shared input space* and *similar processes* (verified
from Lu 2008/2009 + Luo 2015 + Yan 2011 primaries), so literal Debutanizer→TEP
parameter migration is mathematically inapplicable (disjoint variables; the
linear physics-anchored model has no transferable params/features). 1C is:
- **(A) Methodology transfer** — the physics-anchoring + transport-lag + blocked-CV
  + drift + bias-update *recipe* rebuilt on TEP needs <30% of the data a
  from-scratch black-box needs. (Matches ADR-003 "transfer across topologies".)
- **(C) Within-TEP regime migration** — SBC migrates a TEP soft sensor across
  *operating regimes* (the staged papers' valid use: similar process, different
  operating point), targeting <30% of full-retrain data.
- **Rejected (B):** deep transfer-learning / domain-adaptation — reopens the deep
  path (ADR-001 superseded), high risk, doesn't use the staged papers.

**TEP TARGET (grounded, Downs & Vogel 1993):** y = **XMEAS(40), component G mol%**
in the product stream, predicted from the fast measurements (XMEAS 1-22 + XMV).
The composition analyzers (XMEAS 23-41) are *delayed* GC readings; product
analyzer = 0.25 h sample + 0.25 h dead time → **θ ≈ 5 samples at the 3-min
cadence — DOCUMENTED, not assumed (upgrades 1B's convention θ=4).**

**DATA — DONE (in-sandbox, validated).** COSTEP (Simulink) was abandoned after a
non-reproducible reactor-pressure startup trip. Pivoted to the **Russell/Chiang/
Braatz closed-loop FORTRAN** (the d00-d21 simulator), compiled headless with
gfortran and run by Claude directly. Three operating-point regimes generated
(2000 rows each, 100 h at 3-min cadence, IDV 8+10+13 excitation):

| mode | SETPT14/15 | G mean±std (mol%) | reactor P max | learnable R² |
|---|---|---|---|---|
| mode1 (base) | 6.882/18.776 | 53.84±0.97 | 2983 (0% pinned) | 0.59 |
| mode2 (mid-G) | 7.600/17.600 | 58.21±1.14 | 2945 (0% pinned) | 0.57 |
| mode3 (high-G) | 8.500/16.500 | 63.43±1.72 | 2895 (0% pinned) | 0.71 |

Regimes are feed-ratio-induced operating points on the HIGH-G side (low-G pins
the 3000 kPa trip), NOT the canonical Downs & Vogel G/H modes — honest framing,
sufficient for the Option-C claim. **Transfer gap demonstrated:** a mode1 model
scores R²=0.59 in-sample but **−1.08 on mode2, −1.30 on mode3** → migration is
clearly needed. Data is gitignored; reproduce via `generate_tep_modes.py` (needs
the Braatz repo + gfortran). Diagnosed feature transport_lag = 0 (contemporaneous
at 3-min); distinct from the analyzer label-delay θ≈5.

**BUILT this stage (new files, tested, lint-clean):**
- `data/tep_loader.py` — TEPLoader (54-col CSV → named DataFrame, y=XMEAS_40).
- `features/tep_physics_features.py` — analytical-first G features (D/E ratio,
  reactor T, T×(D/E), A/C feeds, pressure, residence) + transport-lag diagnosis.
- `tests/unit/test_tep.py` — 10 tests (synthetic-format, CI-safe).

**NEXT ACTION:** build the **single-mode soft-sensor baseline** (part A) on mode1
(blocked-CV, physics features, the same recipe), then the **3-method SBC migration**
across modes (Lu OSBC baseline → Yan Bayesian functional SBC primary → Luo matrix
SBC), on a **data-fraction sweep** (R² vs % mode_j data; <30% = crossover where
migrated ≥ from-scratch-at-100%). **Yan's GP bias delivers the owed MAPIE/conformal
uncertainty on the transferred model** — fold MAPIE into 1C.

**Migration methods (staged primaries):**
- **Lu OSBC/IOSBC (2008):** scalar slope+bias; fewest data; global-linear only.
- **Luo matrix-SBC (2015):** per-input diagonal S + vector B + Bayesian prior.
- **Yan Bayesian functional SBC (2011):** s(x)·f_o(x)+δ(x), δ=zero-mean GP;
  nonlinear + native uncertainty (→ discharges MAPIE debt).

**Two correction layers compose:** migration (offline, across modes) + 1B
bias-update (online, within mode) = migrated base + online bias-update.


---

## Changelog of this doc
- **2026-06-03** — Created. Working agreement + project vision + full 1A/1B state
  (through the JITL head-to-head) + parked/deferred/owed ledger.
- **2026-06-03** — 1C framing decided (A+C; SBC inapplicable to literal
  Debutanizer→TEP). COSTEP abandoned (pressure-trip); pivoted to Russell/Braatz
  closed-loop FORTRAN generated in-sandbox. 3 TEP operating-mode datasets
  validated (G 53.8/58.2/63.4, transfer gap −1.08/−1.30). TEP loader +
  physics-anchored features + 10 tests built. Target=XMEAS(40); θ≈5 documented.
  Resume = single-mode baseline → 3-method SBC migration + data-fraction sweep.
