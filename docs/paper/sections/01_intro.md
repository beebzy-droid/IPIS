# 1. Introduction

> Draft status: 1F.3 v1. Written last; compresses the stable sections. Contribution
> list mirrors outline.md K1–K5 and the claims table.

Soft sensors — models that estimate a slow, expensive, or delayed quality measurement
from fast process signals — are among the oldest and most economically defensible
applications of machine learning in the process industries. They are also among the
most quietly unreliable. The gap between a benchmarked soft sensor and a trusted one
is not, in our experience, a matter of model capacity; it is a set of recurring
production failure modes that standard practice leaves unaddressed.

Five such mechanisms organize this paper. *Selection lotteries:* process data are
autocorrelated and regime-structured, so validation on adjacent or shuffled samples
leaks information and averages regimes away — model choice then depends on the seed,
and the chosen model fails on the regime the validation scheme hid. *Drift:*
calibration decays between laboratory analyses, and the analyses themselves arrive
late and sparsely, so the labels that could correct the drift are themselves delayed.
*Uncalibrated confidence:* prediction intervals inherited from a held-out set assume
exchangeability — precisely the property that drift and regime change destroy — so the
stated coverage is wrong in both directions, and the operator cannot tell which.
*Delay-corrupted bookkeeping:* when a label arrives late, naive online calibration
scores it against the current interval rather than the one issued at prediction time,
silently corrupting the very adaptation meant to fix the previous problem. *Data
scarcity on new regimes:* a sensor built for one operating point collapses on another
(R² of −1.1 to −1.3 in our transfer-gap measurement), and retraining from scratch
discards everything the source regime taught.

Each mechanism has a mature single-thread literature (Section 2): delayed-measurement
estimation, process model migration, conformal prediction for time series. What is
missing is their integration under one validation discipline, with the interactions
made explicit and the result shown to deploy. That integration is this paper's
contribution, and it is deliberately conservative in one dimension: every point model
is linear, both because the negative-control logic requires holding the model class
fixed and because linearity is what keeps every adaptive mechanism O(1) per label and
the deployed system auditable.

Concretely, we contribute:

- **K1 — A selection methodology** that converts the cross-regime lottery into
  reproducible choice: blocked time-series CV whose per-fold spread is treated as
  signal, plus the one-standard-error parsimony rule, applied identically to feature
  sets and regularization paths. On the Debutanizer benchmark this separates a
  4-feature physics set (CV R² +0.145 ± 0.419, test +0.476) from a 126-feature lagged
  set whose failure is visible even out-of-sample (test +0.221); on SECOM (p ≈ n) it
  contains a path explosion spanning four orders of magnitude.
- **K2 — Drift handling at the documented label delay**: an open-loop EWMA bias update
  that cuts cross-fold standard error 9× and lifts held-out R² from +0.476 to +0.857
  on the Debutanizer, with drift alarming on the corrected residual so alarms mean
  intervention, not normal tracking.
- **K3 — Calibrated uncertainty under drift and delay**: adaptive conformal intervals
  on the bias-corrected estimate achieve regime-uniform coverage (0.897–0.903 against
  a 0.90 target, all regimes × delays) where the static construction is invalid in
  both directions (0.847–0.957), together with the delayed-label bookkeeping rule —
  coverage scored against the interval stored at prediction time — that makes online
  calibration correct rather than approximately right.
- **K4 — Transfer, honestly scoped**: the methodology transfers across process
  topology verbatim; within a process, functional scale-bias migration with a GP bias
  achieves 10.0× data efficiency on both evaluated regime pairs, with calibrated
  intervals that widen appropriately with the regime gap — while the linear-source
  degeneracy of per-input affine migration is verified analytically and observed
  empirically to ±0.001–0.006.
- **K5 — A negative control and a deployment**: on SECOM, where no physics exists to
  encode, the point sensor fails (R² = −1.84) but the calibration machinery holds
  0.910–0.915 coverage at 37% narrower width than the static baseline — isolating
  physics anchors as the source of accuracy and conformal calibration as the source of
  honesty — and the full stack serves at p99 = 1.97 ms with restart-safe state.

The paper proceeds as outlined: Section 2 positions the three literatures and the gap;
Section 3 presents the framework, each component introduced by the failure mode it
removes; Section 4 specifies the three case studies and the shared protocol; Section 5
reports results; Section 6 discusses the production stance, the linear-scope tradeoff,
and limitations; Section 7 concludes.
