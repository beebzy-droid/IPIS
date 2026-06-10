# 5. Results

> Draft status: 1F.3 v1. Every number below is transcribed from the frozen,
> provenance-stamped evidence in `docs/paper/evidence/` (commit-pinned) or from the
> results ledger; no value is computed at writing time. Citation keys in [brackets]
> resolve at LaTeX conversion. Figures F1–F7 are rendered by
> `scripts/paper_figures/make_all.py` from the same evidence files.

## 5.1 Feature philosophy and model selection (K1, K2 — Debutanizer)

Table T1 / Figure F2 report the feature ablation under the identical blocked
time-series CV protocol (5 folds, transport lag 15, plain linear regression, scaler fit
per fold-train). The four arms differ only in where model complexity comes from.

**T1 — Debutanizer feature ablation (blocked CV; held-out test n = 360).**

| arm | k | blocked-CV R² | worst fold | test R² |
|---|---|---|---|---|
| u5 only (backbone) | 1 | +0.034 ± 0.438 | −1.697 | +0.395 |
| physics only | 3 | +0.120 ± 0.479 | −1.770 | +0.440 |
| physics + u5 (deployed) | 4 | **+0.145 ± 0.419** | −1.494 | **+0.476** |
| lagged raw (kitchen sink) | 126 | −1.604 ± 1.421 | −6.248 | +0.221 |

Three observations. First, the thermodynamically grounded set (bubble-point estimate,
relative volatility α(T), stripping factor) dominates on every metric while using 4
features instead of 126: complexity set by physics beats complexity set by validation.
Second, the kitchen sink's failure is not a cross-validation artifact — its held-out
test R² (+0.221) is less than half the deployed set's (+0.476), so the overfitting is
visible out-of-sample as well. Third, the negative folds in *every* arm are the
cross-regime selection lottery that motivates the protocol: under naive adjacent
validation these regime shifts are averaged away and selection becomes seed-dependent;
under blocked CV they surface as the per-fold spread that the one-standard-error rule
then acts on. The deployed arm's row is bit-identical to the static row of the
independent bias-update evaluation (Section 5.2), an internal consistency check across
two separately written evaluation scripts.

The transport-lag diagnosis precedes all of this: at lag 0 the physics bridge appears
to fail (static R² ≈ 0.02), which a naive reading would call a physics error; lag
scanning recovers u5 at lag 15 as a stable interior maximum (r² ≈ 0.51). The lag-zero
failure is diagnostic of transport delay, not of the thermodynamics [results §1A].

## 5.2 Drift handling under delayed labels (K2 — Debutanizer, TEP)

Figure F4 shows the held-out residual trace before and after the open-loop bias-update
[Shardt 2016] at the documented analyzer delay (λ = 0.1 CV-selected on the pool, test
untouched; θ = 4). The static model's per-fold R² spread of [+0.224, **−1.494**,
+0.574, +0.728, +0.695] (CV +0.145 ± 0.419) collapses to [+0.614, +0.487, +0.684,
+0.704, +0.751] (CV +0.648 ± **0.046**) — a 9× reduction in cross-fold standard error,
which is the robustness claim: the update rescues the regime-shifted fold (−1.49 →
+0.49) without sacrificing the good ones. On the held-out test window the same
mechanism moves R² from +0.476 to **+0.857** (Δ +0.381). The correction also exceeds
the best *constant* per-fold offset (oracle CV +0.540), confirming that within-fold
drift tracking — not merely offset removal — is doing work.

The same recipe applied unchanged to the TEP regimes reproduces the signature
(blocked-CV −0.089 ± 0.493 static; bias-update recovery to CV +0.19 at θ = 5, +0.45 at
θ = 2) — the methodology transfers across process topology before any model migration
is attempted [results §1C, Part A].

## 5.3 Calibrated uncertainty under drift and delay (K3 — TEP, synthetic)

Static split conformal [Papadopoulos 2002] assumes exchangeability; process drift
breaks it. On a controlled synthetic stress test (residual scale ×3 mid-stream, target
0.90), split coverage collapses to 0.403 while ACI [Gibbs & Candès 2021] holds 0.899
and EnbPI [Xu & Xie 2021] recovers with FIFO lag (0.832) — Figure F6. The real TEP
regimes exhibit the production version of this failure: not a collapse but
*inconsistency* (Table T2 / Figure F7).

**T2 — Empirical coverage (target 0.90), TEP regimes × delay θ; n_test = 300/regime.**

| regime | construction | θ = 2 cov (width) | θ = 5 cov (width) |
|---|---|---|---|
| mode 1 | raw + split | 0.847 (1.79) | 0.847 (1.79) |
| | corrected + ACI | **0.900** (1.72) | 0.897 (2.04) |
| | EnbPI | 0.897 (2.11) | 0.897 (2.11) |
| mode 2 | raw + split | 0.847 (2.11) | 0.847 (2.11) |
| | corrected + ACI | **0.900** (1.90) | 0.903 (2.18) |
| | EnbPI | 0.857 (2.26) | 0.857 (2.26) |
| mode 3 | raw + split | 0.957 (3.18) | 0.957 (3.18) |
| | corrected + ACI | **0.900** (2.01) | 0.900 (2.48) |
| | EnbPI | 0.873 (2.49) | 0.873 (2.49) |

The static baseline swings from under-coverage (0.847, modes 1–2) to over-coverage
(0.957, mode 3) — invalid in both directions, and the over-covering regime pays for its
nominal-looking number with the widest intervals (3.18). The corrected + ACI
construction is regime-uniform at the target — coverage range [0.897, 0.903] across all
six regime × delay cells — with widths 1.7–2.5, and is robust to the label delay (θ
enters through the bias-update; ACI is driven by the 1D.1b protocol, γ = 0.05). EnbPI
sits between the two, structurally limited by its FIFO residual window on these
mild-drift regimes (its batch-size parameter is flat here: coverage 0.897–0.910 over
s ∈ {1, 10, 25, 50}).

## 5.4 Model migration across operating regimes (K4 — TEP)

Migration is evaluated as within-process regime migration (mode 1 → modes 2, 3) under
the two-layer composition — offline migration plus the Section 5.2 online bias-update
(λ = 0.3, θ = 2) — with n = 8 random-subset repeats per data fraction; literal
cross-process parameter migration is mathematically inapplicable here because the
source and target input spaces are disjoint [ADR-009]. The metric is **data
efficiency**: the ratio of data fractions at which from-scratch and migrated models
reach 90% of the from-scratch ceiling. (The stricter ceiling-crossover statistic
flipped between 20% and 100% across seeds in preliminary runs and is not headlined.)

Figure F5: Yan functional scale-bias correction [Yan 2011] — a per-input affine plus a
zero-mean GP bias on the source predictor — reaches 90% of the ceiling at **5%** of
target data versus **50%** from scratch on *both* targets: **10.0× data efficiency**,
with calibrated 95% GP posterior intervals (coverage 92–98%) that are appropriately
wider for the larger mode-3 regime gap (widths 2.84–3.96 vs 2.65–3.16). Luo matrix
scale-bias correction [Luo 2015] yields exactly 1.0× on both targets: for a linear
source its per-input scaling absorbs the source weights and the method is from-scratch
regression in disguise — the migrated and from-scratch curves coincide to ±0.001–0.006
at every fraction, the empirical face of an identity we also verify analytically.
Output-only correction [Lu 2008] lands between (1.0× / 4.0×). A bare-migration control
(no bias-update layer) caps every migrated curve below the 90% threshold on mode 2:
the two-layer composition is load-bearing, because within-regime drift otherwise
swamps the cross-regime correction.

## 5.5 The negative control: no physics anchors (K5 — SECOM)

SECOM inverts every assumption the framework exploits: 590 anonymized features over
1,567 samples (p ≈ n), 4.5% missing cells, no thermodynamic structure. Framed as
virtual metrology (target x59, selected by stated criteria — missingness ≤ 5%, maximal
|point-biserial r| = 0.156 with pass/fail; audit table in the run output), the
elastic-net path under blocked CV explodes at weak shrinkage — CV R² reaching −7 × 10⁴
with standard errors of the same magnitude (Figure F3), the p ≈ n amplification of the
Section 5.1 lottery. The one-SE rule selects maximal shrinkage (α* = 10, 6/441 nonzero
coefficients) and contains the damage; the resulting sensor still fails as a point
predictor: test R² = **−1.84** raw, −0.16 after the bias-update absorbs a large
calibration offset — even corrected, it cannot beat predicting the mean.

Coverage, however, survives (Table T3): corrected + ACI delivers 0.910 / 0.915 (θ =
2/5) against the 0.90 target at mean width 12.8, where the static split over-covers
(0.953) at width 20.2 — 37% wider. **Conformal validity is model-agnostic; point
accuracy is what the physics anchors buy.** On a process where the sensor cannot be
made accurate, the framework still tells the truth about its own uncertainty. The
fail-enrichment of conformal misses is inconclusive (9 failing lots in the test
window) and is reported only as such.

**T3 — Cross-dataset summary (the negative-control row is the point).**

| dataset | physics anchors | point R² (raw → corrected) | ACI coverage (target 0.90) |
|---|---|---|---|
| Debutanizer | yes (VLE bridge) | +0.476 → **+0.857** | — (Section 5.3 protocol on TEP) |
| TEP regimes | yes (process features) | +0.31 → CV +0.45 (θ=2) | **0.897–0.903**, all cells |
| SECOM | **none** | −1.84 → −0.16 | **0.910 / 0.915** |

## 5.6 Deployment evidence (K5)

The serving stack (Figure F1b) was exercised end-to-end: 243 tests pass (CI: lint,
unit, Docker build, container smoke on `/health` and `/predict`), and client-observed
latency on commodity hardware is p50 1.23 ms / p90 1.51 / p99 1.97 over 10⁴ single-row
predictions — including HTTP and serialization — with batch-32 amortizing to ≈46 µs
per row and the delayed-label `/label` round-trip at p50 0.97 ms. The 200 ms
soft-sensor budget is met with two orders of magnitude of headroom; the path is
I/O-bound by construction, since the deployed object is a linear model, an EWMA, and a
quantile lookup. Correctness under delayed labels is enforced structurally: the
coverage indicator for a late label is computed against the interval *stored when that
sample was predicted*, not the interval current at arrival time (Figure F1b, dashed) —
by which time α_t and the score window have moved on.
