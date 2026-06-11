# 3. The framework

> Draft status: 1F.3 v1. Equations are transcribed from the implementation
> (`evaluation/{bias_update,conformal,blocked_cv}.py`, `migration/functional_sbc.py`,
> `serving/service.py`) so the paper's math is bit-faithful to what produced Section 5.
> Citation keys in [brackets] resolve at LaTeX conversion. Figure F1 shows both panels.

Figure F1a summarizes the offline/online pipeline; each component below is introduced
by the production failure mode it removes. Throughout, $y_t$ is the (delayed,
infrequent) quality measurement, $\hat{y}_t$ the soft-sensor estimate, and $\theta$ the
label delay in samples — a first-class protocol parameter, not an afterthought.

## 3.1 Physics-derived features and transport-lag diagnosis

*Failure mode: complexity set by validation.* Rather than offering the model every
input at every lag and letting validation choose (the $k = 126$ kitchen sink of
Section 5.1), the feature set is fixed by the process physics. For the debutanizer
column, three quantities follow from the vapor–liquid equilibrium of the
butane–stabilized-gasoline separation: a bubble-point estimate of the light-key
fraction obtained by inverting the bubble-point condition at the measured tray
temperature and pressure (Antoine/DIPPR-101 vapor pressures; n-hexane as the
heavy-component proxy) [Smith et al. 2018]; the relative volatility $\alpha(T)$
evaluated at the same state; and a stripping factor coupling $\alpha(T)$ with the
reflux signal. The raw tray temperature at the transport lag is retained as a robust
backbone, giving $k = 4$ features.

The transport lag itself is diagnosed, never assumed. A lag scan of the
target–temperature cross-correlation exposes the column's hydraulic transport delay as
a stable interior maximum ($u_5$ at lag 15, $r^2 \approx 0.51$ on the debutanizer); at
lag 0 the same physics appears to fail ($R^2 \approx 0.02$). The diagnostic posture
matters: a lag-zero failure indicts the data alignment, not the thermodynamics, and
resolving it costs one scan rather than a model-class escalation.

## 3.2 Selection: blocked time-series cross-validation with the one-SE rule

*Failure mode: the selection lottery under autocorrelation and regime shift.*
Validation on adjacent or randomly shuffled samples leaks autocorrelated information
and averages away regime structure; selection then varies with the seed. We use
$K$-fold blocked CV ($K = 5$): the pool is cut into contiguous time blocks, features
are built within each segment separately (so lagged features cannot straddle a
boundary), the scaler is fit on fold-train only, and a gap of the maximum lag
separates train from validation blocks. The per-fold $R^2$ spread — including
strongly negative folds (Table T1) — is retained as the signal, not suppressed as
noise.

Formally, let the pool be $\{(x_t, y_t)\}_{t=1}^{N}$ in time order and let
$B_1, \dots, B_K$ be its partition into $K$ contiguous blocks of (near-)equal length.
For fold $k$, the validation set is $B_k$ and the training set is
$\bigcup_{j \neq k} B_j$ with the $\ell$ samples adjacent to each boundary of $B_k$
removed, where $\ell$ is the maximum lag used by any feature; feature construction is
applied to each contiguous segment independently, so no lagged feature spans a
boundary in either direction. The fold score is the validation $R^2$ of the pipeline
(imputer where applicable, scaler, estimator) fit on the gapped training set, and we
report $\bar{R}^2 \pm \mathrm{SE}$ over folds together with the worst fold. Two
properties matter. The gap makes the fold estimate leakage-free under serial
dependence of range $\leq \ell$: no validation point shares lagged inputs with any
training point. And contiguity makes each fold a *regime probe* — if the pool spans
operating regimes, at least one fold must validate on a regime the model under-saw in
training, which is precisely the deployment event the per-fold spread is meant to
price.

Model choice on any complexity path (feature sets; the elastic-net $\alpha$ path of
Section 5.5) then follows the one-standard-error rule [Hastie et al. 2009]: take the
complexity with the best mean CV score and select the *simplest* complexity whose mean
lies within one standard error of it. The rule encodes that validation cannot
distinguish the robust low-complexity model from the regime-overfit high-complexity
one, and resolves the tie toward parsimony — without ever touching the held-out test
set. On SECOM this is the difference between $R^2 \approx -1.8$ and $R^2 \approx
-10^4$ (Figure F3).

## 3.3 Drift: open-loop bias update with a corrected-residual alarm

*Failure mode: slow drift and regime offsets under delayed, infrequent labels.*
Following the open-loop case of [Shardt & Yang 2016], the deployed estimate carries a
causal EWMA bias term driven only by labels that have already arrived:

$$
b_t = (1 - \lambda)\, b_{t-1} + \lambda \left( y_{t-\theta} - \hat{y}_{t-\theta} \right),
\qquad
\tilde{y}_t = \hat{y}_t + b_t,
$$

with $b$ held at $b_0 = 0$ until the first label. $\lambda$ is CV-selected on the pool
(test untouched; $\lambda = 0.1$ on the debutanizer), and $\theta$ is the documented
analyzer delay. The update is open-loop — it never feeds a controller — so the
stability concerns of closed-loop bias correction do not arise; what it buys is the
9× cross-fold SE reduction and the rescue of regime-shifted folds reported in
Section 5.2. Because a tracking update can absorb genuine drift, drift *alarming* is
performed on the corrected residual $y_t - \tilde{y}_t$ (ADWIN [Bifet & Gavaldà
2007]): the detector fires only when the bias update can no longer keep up, which is
the event that warrants intervention.

## 3.4 Calibrated uncertainty: adaptive conformal intervals under label delay

*Failure mode: uncalibrated confidence under drift.* Split conformal prediction
[Papadopoulos et al. 2002] turns held-out absolute residuals
$s_i = |y_i - \tilde{y}_i|$ into a distribution-free interval
$\tilde{y}_t \pm Q_{1-\alpha}(s)$, but its guarantee requires exchangeability —
exactly what drift destroys (Section 5.3). We therefore deploy adaptive conformal
inference [Gibbs & Candès 2021]: after each label, the working miscoverage level is
updated by

$$
\alpha_{t+1} = \alpha_t + \gamma\,(\alpha - \mathrm{err}_t),
\qquad
\mathrm{err}_t = \mathbf{1}\{ y_t \notin C_t \},
$$

with target $\alpha = 0.10$, step $\gamma = 0.05$, a rolling score window of 200, and
$\alpha_t$ deliberately not clipped to $[0,1]$ — the score quantile handles the
extremes, matching the original construction. The interval is formed around the
*bias-corrected* estimate, so the conformal layer prices residual uncertainty after
the drift mechanism of §3.3 has done its work; the composition, not either piece
alone, produces the regime-uniform coverage of Table T2. EnbPI [Xu & Xie 2021] is
carried as a comparator and behaves as its FIFO residual ensemble predicts.

Label delay interacts with conformal bookkeeping in a way that is easy to get wrong:
when a label for sample $i$ arrives $\theta$ samples late, its coverage indicator must
be evaluated against the interval *issued at prediction time* $C_i$, not the interval
the (since-adapted) state would issue now. The serving layer (§3.6) enforces this
structurally by storing $(\hat{y}_i, \tilde{y}_i, C_i)$ per sample identifier and
scoring arrivals against the stored tuple.

## 3.5 Transfer: functional scale-bias migration, composed with the online layer

*Failure mode: data scarcity on a new operating regime.* When a sibling regime of the
same process exists, the source sensor is migrated rather than retrained. Among the
scale-bias correction family, the functional form of [Yan et al. 2011],

$$
\tilde{y}^{\mathrm{new}}(x) = s(x)\, \hat{y}^{\mathrm{src}}(x) + \delta(x),
\qquad \delta \sim \mathcal{GP}(0, k),
$$

keeps the source model's structure while a zero-mean GP bias repairs the relationship
change locally — and supplies calibrated posterior intervals for free. Two honest
scoping notes carry into the results. First, parameter-level migration requires a
shared input space; across genuinely different processes (debutanizer → TEP) it is
mathematically inapplicable, and what transfers is the *methodology* — the full
§3.1–3.4 recipe, verbatim. Second, for a *linear* source the per-input affine
re-scaling of [Luo et al. 2015] absorbs the source weights entirely and provably
collapses to from-scratch regression; Section 5.4 shows the empirical face of that
identity. Migration is offline; deployed migrated sensors still run the §3.3 online
update, and this two-layer composition is load-bearing (the bare-migration control of
Section 5.4 caps below threshold).

## 3.6 Serving: two asynchronous flows over mutable state

*Failure mode: stateless model hosting cannot represent a sensor whose calibration is
a function of delayed labels.* The deployed object is not a frozen function but a
frozen point model plus mutable state $(b_t, \alpha_t, \text{score window})$. The
service (Figure F1b) is therefore organized as two asynchronous flows: a
high-frequency *predict* flow that reads state ($\tilde{y}_t$ and $C_t$ in
microseconds — the model is a linear map, an EWMA, and a quantile lookup), and a
low-frequency *label* flow that mutates it under an explicit lock, pairing each
arrival with its stored prediction tuple (§3.4). Mutable state is snapshot to disk for
restart safety; the immutable model travels as a registry bundle (frozen estimator,
calibration residuals, protocol parameters) and is never serialized into the
snapshot. The compute path being trivially cheap is a design consequence, not an
accident: every adaptive mechanism in §3.3–3.4 is $O(1)$ per label, so the 200 ms
soft-sensor budget is spent on I/O, and the measured p99 of 1.97 ms (Section 5.6)
carries two orders of magnitude of headroom.
