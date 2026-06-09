# Module 1 — Results

This document is populated as each phase completes. Each phase section follows the structure:

- **Summary** — one paragraph
- **Metrics** — table with minimum/target/stretch achieved
- **Key plots** — link to figures in `notebooks/` or `models/`
- **Observations** — what the results actually mean
- **Unexpected findings** — anomalies worth flagging

> **Methodology note (read before the metrics).** The original 1A scorecard
> below was framed as *RMSE reduction vs. pure ML* on a single split plus
> conformal coverage. Phase 1A's empirical findings (ADR-007) replaced that with
> a more honest **cross-regime** metric: held-out test R² and the spread of
> forward-chaining blocked-CV folds (mean ± SE). The original bands are kept
> visible for traceability; "Achieved" reports the as-measured methodology and
> flags what was not measured. Conformal coverage (MAPIE) was **not** built in
> 1A/1B and remains owed (candidate: 1D or a 1A/1B addendum).

---

## Phase 1A — Hybrid Model on Debutanizer

*Status: **complete** (ADR-007). Architecture pivoted from ADR-001's PINN/residual-hybrid to a dynamic, physics-anchored linear model — see ADR-007 and the divergence note in lessons-learned.*

### Summary
A static single-tray bubble-point physics estimate applied at lag 0 scored
held-out R² = 0.018 — the physics math verified correct (Perry's + Smith
cross-check, 0% clipping); the failure was that it was applied *statically*.
Signal diagnosis found the C4 target is dominated by 6th-tray temperature (u5)
at a stable ~15-sample transport delay (u5 lag-15 r² ≈ 0.51 in every split,
including held-out test). A naive 126-feature lagged PLS overfit to regime
(train 0.77 / val 0.75 / **test 0.04**) — not classic overfitting (train ≈ val)
and not leakage, but covariate shift a temporally-adjacent validation set cannot
police. Forward-chaining blocked CV with a 1-SE parsimony rule recovered held-out
test **R² = 0.52** (13× the naive selection) and exposed strongly negative CV
folds with SE > |mean| — the signature of cross-regime calibration drift that
defines the Phase 1B problem. The physics-anchored feature model carried into 1B
as the static baseline scores held-out test R² = 0.476.

### Metrics

| Metric (original plan) | Minimum | Target | Stretch | Achieved |
|---|---|---|---|---|
| RMSE reduction vs. pure ML (regime shifts) | ≥20% | ≥30% | ≥40% | *Reframed → see 1B: worst-fold R² −1.49 → +0.49 after bias-update* |
| RMSE reduction vs. pure ML (overall) | ≥10% | ≥20% | ≥30% | *Reframed → blocked-CV R²; naive 0.04 → CV-selected 0.52 held-out* |
| Conformal interval coverage | 90–97% | 93–96% | 94–96% | **Not measured** (MAPIE not built; owed) |
| Training stability | Converges | 3 seeds | 5 seeds | **N/A** — final model is a deterministic linear fit (no seed sensitivity); a consequence of the PINN→linear pivot |

### Observations
The decisive methodological lesson: a temporally-adjacent validation split
*cannot* certify cross-regime generalization — it shares the train regime and
rewards regime-specific structure. Blocked forward-chaining CV is the honest
instrument and is what turned an apparently-good model (val 0.75) into a correct
verdict (test 0.04 → fix → 0.52).

### Unexpected findings
Maximum parsimony (k=1) won under the 1-SE rule — the single physics-anchored
lagged feature beat the 126-feature model out-of-sample. The negative CV folds
were not noise; they are calibration drift, and they set up Phase 1B.

---

## Phase 1B — Drift Detection & Adaptive Bias-Update

*Status: **complete** (ADR-008). Correction mechanism is the Shardt open-loop bias-update, not the originally-planned JITL retraining — see lessons-learned.*

### Summary
Residual change detection (ADWIN primary; Page-Hinkley and an in-house
ARL₀-validated CUSUM as comparators) on the same blocked-CV backbone, paired with
a causal **Shardt (2016) open-loop bias-update** — a feedforward EWMA on the
delayed residual, b_t = (1−λ)b_{t−1} + λ(y_{t−θ} − ŷ_{t−θ}). Label/analyzer delay
θ = 4 (Fortuna GC delay, sourced; their NARMA uses 4 output lags). λ selected by
CV (test untouched).

### Metrics (θ = 4, λ = 0.1)

| Metric | Static (ADR-007) | Corrected | Change |
|---|---|---|---|
| Blocked-CV mean R² | +0.145 | **+0.648** | +0.50 |
| **Blocked-CV SE** | 0.419 | **0.046** | **9.1× tighter** |
| Worst fold R² | −1.49 | **+0.487** | catastrophe removed |
| Held-out test R² | +0.476 | **+0.857** | +0.38 |

θ-sensitivity bracket: θ=2 → CV +0.707±0.044; θ=4 → +0.648±0.046; θ=8 →
+0.599±0.060. All solidly positive, SE 7–9× tighter than static across the bracket.

**Head-to-head vs JITL (literature-standard adaptive layer).** Same folds, same
physics-anchored features, same causal θ=4:

| mechanism | CV mean | CV SE | worst fold | held-out test | local fits |
|---|---|---|---|---|---|
| static | +0.145 | 0.419 | −1.49 | +0.476 | 0 |
| **bias-update (λ=0.1)** | **+0.648** | **0.046** | **+0.487** | **+0.857** | **0** |
| JITL always-on (h=2) | +0.405 | 0.215 | −0.392 | +0.519 | 1,620 |
| JITL ADWIN-gated | +0.146 | 0.419 | −1.49 | +0.506 | 37 |

The O(1) bias-update beats O(N) JITL on every axis at zero local fits. JITL
partially rescues the catastrophic fold (−1.49 → −0.39); the bias-update fully
does (→ +0.49). Gated JITL ≈ static — ADWIN's latency triggers local modelling
too late — confirming adaptation here must be continuous, not detector-gated.

### Observations
The **SE collapse (0.419 → 0.046) is the result**, not the mean lift: it converts
"competitive mean R² with large cross-regime variance" into "strictly dominant on
worst-case robustness" — the deployable claim. Detection is the trigger; the
bias-update is the correction.

### Unexpected findings
- Corrected CV (+0.648) **exceeds the best-constant-offset oracle** (+0.540): the
  update tracks within-fold drift, not just a flat offset.
- **θ is not identifiable from this dataset** (cross-correlation method 3:
  bottom-temp lag 17 > combined u5 lag 15 → physically impossible analyzer delay;
  premise falsified). θ=4 retained as sourced convention. A clean, citable
  negative result.

---

## Phase 1C — Cross-Process Transfer (Debutanizer → TEP)

*Status: **complete** (ADR-009). Framing A+C (methodology transfer + within-TEP
regime migration); literal Debutanizer→TEP parameter migration is mathematically
inapplicable (disjoint input spaces — see ADR-009).*

### Summary
The Phase-1A/1B recipe (physics-anchored features + forward-chaining blocked CV +
Shardt open-loop bias-update), built on a distillation column, was rebuilt
**unchanged** on the Tennessee Eastman reactor-separator-stripper process to
predict product component G (XMEAS 40). Part A: the recipe transfers across
topology — the static physics-anchored model shows the same calibration-drift
signature (blocked-CV R² −0.089 ± 0.493, the Debutanizer pattern), held-out test
R² 0.31, and the bias-update recovers it to CV +0.19 (θ=5, documented analyzer
delay) / +0.45 (θ=2, empirical best). A mode-1 model applied to other operating
regimes collapses (R² −1.08 / −1.30) — the transfer gap that motivates migration.
Part C: three scale-bias-correction methods (Lu OSBC, Luo matrix-SBC, Yan
functional SBC) were benchmarked on a data-fraction sweep against from-scratch
baselines, composed with the 1B online bias-update (the two-layer architecture).
**Yan functional SBC is ~10× more data-efficient than training from scratch** —
reaching 90% of full-retrain accuracy with ~5% of the target data vs ~50% — and
carries calibrated 95% prediction intervals (coverage 92–98%, widening with the
regime gap), discharging the MAPIE/conformal debt for 1C. OSBC is ~3.3×; Luo
collapses to from-scratch (1.0×) on the linear source.

### Data
Three TEP operating-point regimes generated in-sandbox from the Russell/Chiang/
Braatz closed-loop simulator (COSTEP/Simulink abandoned — non-reproducible
reactor-pressure startup trip; see ADR-009): 2000 rows each (100 h at the 3-min
analyzer cadence), G means 53.8 / 58.2 / 63.4 mol% (gaps 4.4 / 5.2 ≫ within-mode
std ~1.3), 0% pressure-pinned, single-mode multivariate R² 0.57–0.71. These are
**feed-ratio operating points, not the canonical Downs & Vogel G/H modes** —
honest framing, sufficient for the within-process migration claim. Canonical
mv-per modes 1/3/4 fetched as a supplementary check; they are textbook-clean
(mode 3 = 90 mol% G) but under-excited for soft-sensor training (within-mode
R² ~0.04) — which is itself why deliberate excitation was injected for the
headline data.

### Metrics — data efficiency (mode 2, two-layer = migration + online bias-update, n_repeats = 8)

| method | form | params | data efficiency | calibrated intervals |
|---|---|---|---|---|
| Lu OSBC (2008a) | output-only `S_O·z + B_O` | 2 | ~3.3× | — |
| Luo matrix-SBC (2015) | per-input `ρ₀·x + λ₀` inside z, + output affine | 2d+2 | ~1.0× (no gain) | — |
| **Yan functional SBC (2011)** | `s(x)·z + δ(x)`, δ = zero-mean GP | GP | **~10×** | **95% coverage 92–98%** |

Data efficiency = (from-scratch data fraction) / (migrated data fraction) to reach
90% of the from-scratch-at-100% R². Yan reaches the target at ~5% target data on
both regimes; the larger mode-3 gap gives *more* migration benefit and *wider*
intervals (2.8–4.0 vs mode-2 2.6–3.2). The strict "exceed the from-scratch
ceiling" crossover is **not** reported as a headline: it is brittle here because
migrated and from-scratch ceilings coincide (it flipped 20%↔100% across seeds);
data efficiency is the robust metric.

### Observations
- **Methodology transfers across topology.** The exact Debutanizer recipe (down to
  the bias-update code) works on a chemically unrelated reactor process. The
  shared structure is the *method*, not the variables.
- **The right way to migrate a parametric source is to add a nonparametric bias
  (Yan), not to reshape its inputs (Luo).** OSBC's output-only rigidity preserves
  the source's input-output shape (so it migrates, but cannot fix a relationship
  change); Yan adds local GP corrections on top of the preserved source (fixes the
  relationship *and* keeps the structure → ~10×).
- **The two-layer composition is essential.** Within-mode drift (IDV random walks
  over 100 h) caps every from-scratch bar at ~0.15–0.22 if untreated; the 1B
  online bias-update removes it, lifting all curves and exposing migration's
  low-data advantage.
- **MAPIE/conformal discharged for 1C.** Yan's GP posterior gives calibrated 95%
  intervals on the transferred model that widen with the regime gap (still owed as
  a *productionization* item for 1D).

### Unexpected findings
- **Luo matrix-SBC ≡ from-scratch for a linear source.** For a linear base model
  z, `z(ρ₀·x + λ₀)` is linear in x with coefficients `ρ₁·w_k·ρ_{0,k}`; since the
  source weights w_k are fixed and nonzero, ρ₀ can realize *any* linear map, so
  Luo's least-squares fit equals from-scratch linear regression — verified
  analytically, on synthetic data (R² 1.00 = from-scratch on a different linear
  target), and on TEP (migrated tracks from-scratch to ±0.001–0.003 at every
  fraction). Luo's input-reshaping needs a *nonlinear* source to add value, and
  its 2d+2 parameters make it underdetermined at small target fractions.
- **Bigger regime gap ⇒ more migration benefit** (mode 3 dominance stronger than
  mode 2): a from-scratch model with little data struggles most on the harder
  regime, while migration leverages the source.
- **θ is data-specific.** The documented analyzer delay θ=5 helped the generated
  data (+0.19) but the empirical optimum was θ=2 (+0.45); on the 1-min-native
  canonical data θ=5 *hurt* (−0.45). Re-pinned per dataset.

---

## Phase 1D — Production-Ready Deployment Stack

*Status: 1D complete — 1D.1/1b (conformal), 1D.2 (serving stack), 1D.3 (dashboard). 1D.4/1D.5 gated. Next: Phase 1E.*

### 1D.1 — conformal uncertainty (ADR-010)

Distribution-free intervals implemented from-primary (`evaluation/conformal.py`,
15 tests): split (baseline), EnbPI (Xu & Xie 2021), ACI (Gibbs & Candès 2021,
primary). Model-agnostic — wraps the bias-corrected linear sensor's residuals with no
retrain. Synthetic stress test (residual scale ×3 mid-stream, target 0.90): static
split collapses to 0.40 post-shift; ACI holds 0.90 (widening 3.24→6.76); EnbPI recovers
to 0.83 with a FIFO lag. Isolates the failure mode adaptivity fixes.

### 1D.1b — coverage on the real TEP regimes

`scripts/conformal_eval.py` on `tep_mode{1,2,3}` (train-fit, val-calibrate, test-eval;
bias-update λ=0.3, θ∈{2,5}; ACI γ=0.05, window=200):

| construction | mode1 | mode2 | mode3 |
|---|---|---|---|
| raw + split | 0.847 | 0.847 | 0.957 |
| corrected + split | 0.897 / 0.873 | 0.903 / 0.890 | 0.927 / 0.880 |
| **corrected + ACI** | **0.900 / 0.897** | **0.900 / 0.903** | **0.900 / 0.900** |
| EnbPI (standalone) | 0.897 | 0.857 | 0.873 |

(θ=2 / θ=5; single value = θ-invariant.)

corrected+ACI delivers regime-uniform **0.90 ± 0.003** where raw static split swings
0.847–0.957 (under mode1/2, over mode3) and EnbPI 0.857–0.897. ACI is θ-robust;
EnbPI's batch size `s` is flat on these mild-drift regimes (use s=1).

### Observations
- Real within-mode drift is mild; the dramatic split-collapse is a synthetic
  construct. The real production case is cross-regime coverage *inconsistency*, which
  ACI resolves to uniform nominal coverage.
- The deployed interval = bias-corrected linear sensor + ACI; EnbPI is a standalone
  comparator (no bias-update; cannot ingest the causal correction) and is dominated
  here on both coverage-accuracy and width.

---

### 1D.2 — production serving stack (ADR-011)

The soft sensor is served as two asynchronous flows over mutable state, because labels
are delayed and infrequent: a high-frequency `predict` (reads state) and a low-frequency
`label` (mutates the bias-update, ACI, and drift detector). `SoftSensorService`
(`serving/service.py`) is the framework-agnostic core; FastAPI (`serving/api.py`) wraps
it with a mutation lock and a lifespan snapshot.

Endpoints: `POST /predict` (batch-first), `POST /label`, `GET /health` (lock-free),
`GET /metrics`, `GET /state`. The deployed object is the bias-corrected linear sensor +
ACI (1D.1b-confirmed); the bias recursion is bit-faithful to ADR-008, so the 1D.1b
coverage result transfers to the live path.

Correctness detail (delayed labels): the ACI coverage indicator for a late label is
computed against the interval *stored when that sample was predicted*, not the service's
current interval — by the time an assay arrives, alpha_t and the score window have moved
on. Verified by unit test.

Model delivery: a joblib `ModelBundle` (frozen sklearn pipeline + calibration residuals
+ params) is the interchange format. MLflow is optional, used for registry + tracking
only (params, metrics, the registered model, and the bundle artifact); serving loads the
bundle from MLflow or a local file, with a committed synthetic fixture as the default
(joblib fallback so it runs offline / in CI). A real MLflow log->resolve->serve
round-trip is covered by a test (skipped when MLflow is absent).

Validation: 49 unit tests (15 conformal + 13 service + 11 api + 10 loader). The lean
serving container (`Dockerfile` + `requirements-serving.txt`; no torch/mlflow/streamlit)
was built and run locally (`/health` 200, `/predict` schema OK) and GitHub Actions CI is
green: a `test` job (pinned black/ruff on `src tests` + the 49 tests with `PYTHONPATH=src`)
and a `docker` job (image build + `/health`/`/predict` smoke).

#### Observations
- The serving hot path is microsecond compute (linear + EWMA + interval lookup), so the
  sub-200 ms latency target is I/O/serialization-bound, not inference-bound. Yan's GP
  (1C) is offline migration only and never on the serving path (GP is O(n^3)).
- State is in-process + a pickle snapshot (single instance; Redis deferred). The pickle
  carries only mutable state (b_t, the ACI object, the river detector, the prediction
  buffer, counters) — the immutable model reloads from the registry, never pickled into
  the snapshot.

### 1D.3 — Streamlit monitoring dashboard

A thin Streamlit client over the live FastAPI service (two processes; the dashboard
exercises the real 1D.2 stack rather than embedding the service). It drives a sample
stream, calls `/predict`, queues each sample's ground truth at predict time, and posts it
via `/label` once a configurable delay elapses — the same delayed-label flow the service
is built around. Panels: the conformal band with arriving labels overlaid, the rolling
empirical coverage against the 0.90 target, and a metrics strip (b_t, alpha_t, coverage,
label count, drift light).

The default stream is synthetic (3 features matching the committed fixture model) with a
drift toggle that inflates the residual scale — the live demonstration of the 1D.1
result: the ACI band visibly widens while rolling coverage holds near target. A TEP
replay source is available when the gitignored data and a TEP bundle are present.

Engineering notes (test-pinned where it matters): pre-label `rolling_coverage` is
`math.nan` in the service but JSON carries no NaN, so it arrives client-side as
null/None — all dashboard metric formatting is None/NaN-safe and a regression test pins
that wire contract. Streamlit/altair/pandas are imported lazily inside the render
function, so the module (and its pure helpers — the stream generator and the HTTP
client) imports and tests without Streamlit installed; 9 unit tests run in the lean CI,
with the client tested against the real app via FastAPI's TestClient.

#### Observations
- The dashboard is deliberately stateless with respect to the sensor: all b_t / alpha_t /
  coverage state lives in the service and is read back over HTTP, so what the panels show
  is the deployed object's actual state, not a parallel reimplementation.
- Streamlit's rerun-the-whole-script model makes the stream state (`st.session_state`)
  the only dashboard-owned state; everything else is fetched fresh each interaction.

## Phase 1E — SECOM Stress Test

*Status: not started*

---

## Phase 1F — Writing & Submission

*Status: not started*
