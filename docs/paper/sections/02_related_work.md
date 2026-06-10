# 2. Related work

> Draft status: 1F.3 v1. All primaries are in the project source map and were read in
> the original; characterizations below are checked against those readings. Citation
> keys resolve at LaTeX conversion.

Three literatures meet in this work: soft sensing under delayed and infrequent
measurements, process model migration, and conformal prediction for time series. Each
supplies one mechanism; none, to our knowledge, has been integrated into a single
deployable pipeline with a common validation discipline and an adversarial negative
control.

## 2.1 Soft sensing under delayed, infrequent, and irregular measurements

That quality labels arrive late and sparsely is the defining constraint of industrial
soft sensing, and the literature treats it with increasing structure. [Guo et al.
2014] incorporate delayed, infrequent and irregular measurements into online
estimation through a Kalman-filter/data-fusion construction, establishing the pattern
of running a fast model between slow labels and reconciling on arrival. [Shardt &
Yang 2016] design bias-update terms for the case where the time delay is random but
known, analyzing open- versus closed-loop behavior; our §3.3 adopts their open-loop
case with a fixed documented delay — deliberately the simplest member of the family —
and demonstrates that, composed with adaptive conformal calibration, it suffices for
regime-uniform validity. [Wang et al. 2021] push in the complementary direction:
when the delay itself is unknown and time-varying, they estimate it dynamically
(SD-DU search) and weight a relevance vector machine accordingly, demonstrated on a
wastewater plant. Our transport-lag *diagnosis* (§3.1) is the static counterpart of
their dynamic estimation; the framework would accept their estimator as a drop-in
where delays drift. What this thread lacks is calibrated uncertainty: corrections are
point corrections, and confidence in the corrected estimate is left to ad-hoc
variance heuristics.

## 2.2 Process model migration

The migration thread asks when a model developed on one process (or regime) can be
adapted to another with little new data. [Lu & Gao 2008a,b] formalize process
similarity and output-side scale-bias correction; [Lu et al. 2009] develop the
migration methodology; [Yan et al. 2011] make the correction *functional* — an
input-dependent scale and a zero-mean GP bias — within a Bayesian treatment that
yields posterior intervals; [Luo et al. 2015] add prior information through per-input
affine re-scaling. Two boundaries of this family are, in our reading, under-stated in
the literature and matter in practice. First, the shared-input-space requirement is
explicit in the primaries but routinely elided downstream: parameter-level migration
across genuinely different processes is not merely hard but undefined, which is why
our cross-process claim is methodological (§3.5). Second, the interaction with source
model class: for a linear source, Luo's re-scaling provably collapses to from-scratch
regression — an identity we verify analytically and observe empirically to
±0.001–0.006 (§5.4) — so reported gains of that method presuppose a nonlinear source.
The thread also leaves open what migration composes with online: our two-layer result
(migration offline, bias update online; the composition load-bearing) addresses the
within-regime drift that otherwise caps migrated performance.

## 2.3 Conformal prediction for time series

Inductive (split) conformal prediction [Papadopoulos et al. 2002] provides
distribution-free finite-sample coverage under exchangeability, with [Barber et al.
2021] extending the toolkit (jackknife+) under weaker conditions. Time series break
exchangeability, and the responses split into ensemble and adaptive families: EnbPI
[Xu & Xie 2021] maintains a FIFO ensemble of residuals with no exchangeability
assumption; adaptive conformal inference [Gibbs & Candès 2021] performs online
gradient updates on the working miscoverage level and guarantees long-run coverage
under arbitrary distribution shift. A recent line addresses precisely the feedback
imperfections that a delayed-label deployment exhibits: [Wang, Zecchin & Simeone 2025]
treat *intermittent* feedback (IM-OCP, with long-run coverage and sub-linear regret
when labels arrive only sporadically); [Wang, Zecchin & Simeone 2026] treat *corrupted*
feedback, where the miscoverage indicator itself is unreliable; and [Hou et al. 2025]
operate under sporadic edge–cloud feedback. The theoretical problem of online conformal
calibration under imperfect or delayed feedback is therefore established, and we do not
claim it as ours.

What this thread has not addressed is the *instantiation* that §3.4 and §3.6 require: in
a soft sensor the delayed label must be reconciled with the conformal layer **and** with
an upstream drift corrector, and the reconciliation has to be structurally correct in a
serving system, not only in an update rule. Two specifics follow. First, delay is
threaded through *both* mechanisms — the bias update of §3.3 consumes the label at its
documented delay, and only the corrected residual then feeds the conformal layer — so
the interval prices uncertainty after drift removal rather than around a stale point
estimate; this composition, not the conformal update alone, yields the regime-uniform
coverage of Table T2. Second, the coverage indicator for a late label must be scored
against the interval *stored at that sample's prediction time*, not the interval the
since-adapted state would issue on arrival; the IM-OCP/corrupted-feedback analyses model
*when or whether* feedback arrives, whereas our concern is the bookkeeping that pairs
each arriving label with its originating interval. Our serving layer (§3.6) enforces
that pairing by construction. The contribution here is integration and correct
deployment, not a new conformal guarantee.

## 2.4 The gap

Selection robustness, drift correction, delay handling, calibrated uncertainty,
migration, and deployment each have mature single-thread treatments. What is missing
is their *integration under one validation discipline* — blocked CV with a parsimony
rule applied identically to feature sets, drift parameters, and regularization paths —
with the interactions made explicit (bias correction before conformal calibration;
migration composed with online updating; delay threaded through both the corrector
and the conformal bookkeeping), engineering evidence that the result deploys, and a
negative control that shows where the performance actually comes from. That
integration, and the honest accounting it forces, is the contribution.
