# Paper 2 — draft v1 (concatenated)

> When conformal prediction is unsafe for real-time optimization: the constraint selection effect and a conditionally-calibrated remedy. Target: Journal of Process Control. Auto-concatenated from sections/00–07; edit sections, not this file.

# 0. Abstract

Real-time optimization (RTO) drives a process toward a quality constraint it cannot
measure online, so it must subtract a back-off — a safety margin — from the
specification. Conformal prediction is the natural distribution-free way to size that
back-off from data, but we show it is unsafe under optimization. An RTO that optimizes
against a marginally-valid conformal back-off — even a locally-adaptive one — is a
selection mechanism: it drives the operating point to where the margin under-covers the
conditional constraint quantile, and on a rigorous Peng–Robinson distillation twin the
realized constraint-violation rate reaches roughly five times the nominal level across
the disturbance range. We identify this conformal selection effect as the
optimization-induced loss of marginal coverage, and verify against an oracle — which uses
the true conditional quantile — that the failure lies in the back-off, not the
chance-constrained formulation. Restoring safety requires conditional validity: a
conformalized-quantile-regression back-off with an a-posteriori calibration step returns
the realized violation to the oracle level, within a Monte-Carlo band, at near-oracle
profit over the operationally realistic disturbance range, degrading only — and
diagnosably, through a climbing inflation factor — when the disturbance widens several-fold
and the conditional estimate runs out of calibration data. A regime map over disturbance
magnitude bounds where each back-off controls violation. The contribution is calibrated
safety, not profit: at a well-controlled feed the constraint is barely active and all
methods earn within half a percent of the deterministic optimum. The mechanism is
general — any conformal interval used as a hard optimization constraint is exposed to it —
and the portable rule is to size the margin conditionally and to read the a-posteriori
inflation as a data-adequacy signal.

**Keywords:** real-time optimization; chance-constrained optimization; conformal
prediction; conditional coverage; constraint back-off; distillation.

---

# 1. Introduction

Real-time optimization (RTO) continuously re-computes the operating point of a process
to maximise an economic objective as conditions drift. Its economic value comes from
pushing the process against its constraints — a distillation column earns more as it
drives a product composition to the edge of specification — but the most important
constraints are often on quality variables that are not measured online: a laboratory
assay or an inferential estimate stands in for a true composition that the controller
never sees in real time. To operate safely against such a constraint, RTO must subtract a
**back-off** from the specification: a margin that absorbs the gap between the model's
nominal prediction and the realised quality under an unmeasured disturbance. Sizing that
margin is the central difficulty of RTO under uncertainty. Too small and the process
violates specification whenever the disturbance is adverse; too large and the economic
benefit of the optimisation is given away.

Conformal prediction is the natural tool for the job. It converts any predictor into an
interval with a finite-sample, distribution-free coverage guarantee, assuming only
exchangeability of the data — no Gaussian residuals, no parametric disturbance law. Using
the upper edge of a conformal interval as the back-off promises exactly what a chance
constraint asks for: cover the realised quality at the nominal level, from data, without
distributional assumptions. This paper asks whether that promise survives contact with
the optimiser, and finds that it does not.

We show that an RTO optimising against a *marginally*-valid conformal back-off is unsafe.
A conformal margin guarantees coverage on average over the calibration distribution of
operating points, but the optimiser does not sample that distribution — it deliberately
seeks the boundary of the feasible region, which is where the margin is tightest relative
to the local risk and therefore where coverage is worst. The argmax is a selection
operator, and it selects for under-coverage. On a rigorous binary-distillation twin, a
back-off that is marginally valid — including a locally-adaptive, heteroscedastic one that
widens where the data are noisier — yields a realised constraint-violation rate of roughly
five times the nominal level across the entire disturbance range. The failure is
structural, not a matter of the disturbance being large, and adaptivity in the margin's
width does not cure it. We call this the **conformal selection effect**: it is the
optimisation-induced loss of the marginal coverage guarantee, the constraint-space
analogue of the winner's curse in post-selection inference. The same phenomenon was named
in the abstract sense by the conformal-predictive-programming literature (Zhao et al.,
2024), which observed that a decision optimised against sampled constraints is no longer
independent of them; here we instantiate it in a process-RTO loop, quantify its severity,
and isolate what fixes it.

What fixes it is conditional validity. A back-off built from conformalised quantile
regression (Romano, Patterson and Candès, 2019) targets the conditional constraint
quantile at each operating point rather than a calibration average, so there is no
systematic margin-versus-risk gap for the optimiser to exploit. The residual finite-sample
error is closed by an a-posteriori calibration at the selected setpoint, in the manner of
conformal predictive programming. On the twin, this conditional method returns the
realised violation to the level of an oracle that knows the true conditional quantile — to
within the Monte-Carlo estimation band — at near-oracle profit, over the operationally
realistic disturbance range. An oracle margin, available here because the twin furnishes
the plant response, holds the violation at the nominal level by construction; that it does
so confirms that the failure of the marginal methods lies in the back-off, not in the
chance-constrained formulation itself.

The method is not unconditionally safe, and we map where it holds. Sweeping the
disturbance magnitude produces a regime map: the conditional method tracks the oracle up
to roughly three times the realistic disturbance, a constant margin over-violates and then
becomes infeasible, and the a-posteriori inflation factor climbs from near unity to nearly
sixfold before the conditional estimate, too, runs out of calibration data and can no
longer certify the target. That inflation factor is an interpretable diagnostic — the
process operator sees the safety margin being stretched before it breaks. Finally, we are
explicit that the contribution is calibrated *safety*, not profit: at a well-controlled
feed the constraint is barely active and every method earns within half a percent of the
deterministic optimum, so the value of the conditional method is the violation it removes,
not any profit it adds.

The contributions are:

- **R1.** We identify and quantify the conformal selection effect in RTO: a
  marginally-valid back-off, fixed or locally-adaptive, realises roughly five times the
  nominal violation under optimisation, while an oracle conditional margin holds the
  target — establishing that the failure is the selection effect, not the chance-constraint
  formulation. (§5.1–5.2)
- **R2.** We show that conditional validity is the structural remedy: a CQR back-off with
  an a-posteriori calibration step tracks the oracle to within the Monte-Carlo band at
  near-oracle profit over the realistic disturbance range, with the a-posteriori inflation
  reduced from a primary guarantee to a small residual correction. (§5.3)
- **R3.** We characterise the disturbance-magnitude regime over which each margin controls
  violation, where a constant margin becomes infeasible, and where the conditional method
  itself is data-starved — reading the a-posteriori inflation as a data-adequacy
  diagnostic. (§5.4–5.5)

Section 2 places the work against RTO-under-uncertainty, conformal prediction, and
conformal optimisation. Section 3 formalises the chance-constrained RTO, the four
back-offs, the selection-effect argument, and the a-posteriori step. Section 4 describes
the twin and the experimental design, Section 5 reports the regime map, and Section 6
draws out the general design rule, the limitations, and the bridge to a closed-loop
extension with an online soft sensor.

---

# 2. Related work

This work sits at the intersection of three lines: real-time optimization under
uncertainty, conformal prediction and its conditional-validity theory, and the recent
use of conformal prediction inside optimization. We review each and then state the gap.

## 2.1 Real-time optimization under uncertainty

The dominant paradigm for steady-state RTO under plant–model mismatch is **modifier
adaptation** (Marchetti et al., 2009; Chachuat et al., 2009), which adds first-order
correction terms to the model cost and constraints so that, on convergence, the
model-based optimum is a KKT point of the plant. Modifier adaptation corrects the
*nominal* prediction but does not, by itself, supply a probabilistic margin against an
unmeasured disturbance; safety against constraint violation is handled implicitly,
through conservative tuning or filtering of the modifiers.

A data-driven branch replaces or augments the modifiers with learned surrogates. del
Río Chanona et al. (2021), extending the Gaussian-process modifier-adaptation line (del
Río-Chanona et al., 2019), use Gaussian-process regression to capture the cost- and
constraint-mismatch non-parametrically and embed trust-region and acquisition-function
ideas from Bayesian
optimization to manage risk during exploration. There, the GP *mean* corrects the
constraint and the GP *variance* drives excitation and sizes the trust region; the
scheme is probabilistic in its exploration but does not issue a distribution-free,
finite-sample coverage guarantee on the constraint, and its risk control is a
trust-region containment rather than a calibrated back-off. The closely related
stochastic-MPC line (Bradford et al., 2019, 2020) does subtract explicit GP-posterior
back-offs from constraints, but in a receding-horizon control setting and under a
Gaussian posterior assumption.

The classical route to explicit probabilistic constraints is **chance-constrained
programming** (Li et al., 2008), which constrains the probability of satisfaction
directly, computes joint-constraint probabilities by sampling under an assumed
(typically multivariate-normal) disturbance law, and trades feasibility against
profitability through the miss level. This is the formulation we adopt in Eq. (1); the
distinction in this paper is that the back-off enforcing it is built distribution-free
from data rather than from an assumed Gaussian law.

## 2.2 Conformal prediction and conditional validity

Conformal prediction (Vovk et al., 2005; Angelopoulos and Bates, 2023) converts any
point predictor into a set with a finite-sample, distribution-free **marginal** coverage
guarantee under exchangeability. Split conformal and its locally-weighted variants (Lei
et al., 2018) rescale the residual by a spread estimate to make interval width adapt to
the input, and conformalized quantile regression (Romano, Patterson and Candès, 2019)
goes further by conformalising a quantile-regression estimate so that the interval
targets the *conditional* quantile while retaining the marginal guarantee. These methods
all deliver coverage *on average* over the calibration distribution.

The limit of that guarantee is the subject of a conditional-validity literature.
Exact distribution-free *conditional* coverage is impossible without further assumptions
(Vovk, 2012; Lei and Wasserman, 2014), and recent work characterises and partially
restores conditional guarantees (Gibbs, Cherian and Candès, 2023). A parallel strand
relaxes exchangeability itself — for distribution shift and dependent data (Tibshirani
et al., 2019; Barber et al., 2023; Gibbs and Candès, 2021). The gap between marginal and
conditional validity is precisely what an optimiser exploits in this paper: a margin
calibrated on average under-covers at the specific operating point an optimiser selects.

## 2.3 Conformal prediction inside optimization

Conformal prediction has recently been brought inside chance-constrained optimization.
**Conformal predictive programming** (CPP; Zhao et al., 2024) uses the conformal quantile
lemma to reformulate a chance-constrained program as a deterministic quantile-constrained
one, supporting any conformal variant and providing feasibility guarantees. Critically
for the present work, CPP observes that once a decision is optimised against
sampled constraint evaluations those evaluations are no longer independent of the
decision — the exchangeability that underwrites the conformal guarantee is broken by the
optimisation itself — and it restores a guarantee *a posteriori*, by re-calibrating the
selected solution on a second, independent dataset. Related uses of conformal sets to
certify safety in optimisation and control include online-conformal safety guarantees
for Bayesian optimisation (Zhang et al., 2024) and conformal back-offs proposed for
predictive control.

CPP supplies the a-posteriori calibration machinery this paper uses (Section 3.4) and
names the loss-of-independence mechanism in the abstract. What it does not do — and what
no work in §2.1 does — is instantiate the mechanism in a process real-time optimisation
loop, quantify how severely a *marginally-valid* (including locally-adaptive) back-off is
degraded by the optimiser, or separate the two remedies the problem actually needs: a
*conditional* construction to remove the systematic selection bias, with a-posteriori
calibration left to cover only the finite-sample residual. CPP treats the a-posteriori
step as the primary guarantee; we show that without conditional validity that step is
either large or infeasible, and that a conditional back-off makes it small.

## 2.4 Gap

No existing treatment (i) places a distribution-free conformal constraint back-off inside
a chemical-process RTO loop, (ii) exposes and quantifies the optimiser-induced selection
effect that drives a marginally-valid margin to several times its nominal violation, and
(iii) identifies conditional validity as the structural remedy — relegating a-posteriori
calibration to a residual correction and reading its inflation factor as a data-adequacy
diagnostic. This paper provides that treatment, on a rigorous debutanizer twin, and maps
the disturbance regime over which it holds. The soft-sensor framework of the companion
paper supplies the model-based estimate of the unmeasured constraint that the back-off
corrects; here that estimate is taken as given and the focus is the back-off itself.

---

# 3. Problem formulation and methods

## 3.1 Chance-constrained real-time optimization under an unmeasured disturbance

We consider steady-state real-time optimization (RTO) of a distillation column whose
product-quality constraint cannot be measured online. The decision is the operating
point $u=(R,D)$, with $R$ the reflux ratio and $D$ the distillate molar flow; the
admissible set is the box $\mathcal{U}=[0.8,3.0]\times[33,37]$ (kmol h$^{-1}$ for
$D$). The plant is subject to an exogenous disturbance $z$ — the feed light-key
(n-butane) mole fraction — that is **not** manipulated and **not** measured in real
time. We model it as a truncated normal,
$$
z \sim \mathcal{F}_\sigma \;=\; \mathcal{N}\!\left(z_0,\sigma_z^2\right)\big|_{[z_{\mathrm{lo}},\,z_{\mathrm{hi}}]},
\qquad z_0=0.35,\;[z_{\mathrm{lo}},z_{\mathrm{hi}}]=[0.30,0.40],
$$
where the support is the range over which the plant model below is validated and
$\sigma_z$ parameterises the disturbance magnitude (swept in Section 4; the
operationally realistic value is $\sigma_z\approx 0.006$).

The constrained quantity is the bottoms light-key composition
$g(u,z)=x_{B}(R,D,z)$, which must satisfy the quality specification
$g(u,z)\le\bar g$ with $\bar g = 0.02$. Because $g$ is unmeasured, the optimiser sees
only a **nominal model** $\hat g(u)=x_B(R,D,z_0)$ — the column's predicted bottoms
composition at the nominal feed. The economic objective $\pi(u)$ is an operating
profit (two product streams valued by mass minus reboiler energy; Section 3.5). A
naïve deterministic RTO solves $\max_{u}\pi(u)$ s.t. $\hat g(u)\le\bar g$, ignoring
$z$; because the column drives the bottoms composition up against the spec to maximise
the valuable light key recovered downstream, the constraint is active at the optimum
and any feed excursion $z>z_0$ pushes the realised $g(u,z)$ over $\bar g$.

The principled formulation is a **chance constraint** on the unmeasured quantity:
$$
\max_{u\in\mathcal U}\; \pi(u)
\quad\text{s.t.}\quad
\mathbb{P}_{z\sim\mathcal F_\sigma}\!\left[\,g(u,z)\le \bar g\,\right]\;\ge\;1-\alpha,
\tag{1}
$$
with miss level $\alpha=0.10$. Equivalently, writing
$Q^{z}_{1-\alpha}[\,g(u,\cdot)\,]$ for the $(1-\alpha)$-quantile of $g(u,z)$ over the
disturbance, the constraint is $Q^{z}_{1-\alpha}[\,g(u,\cdot)\,]\le\bar g$. RTO has no
access to this quantile; it enforces a surrogate constraint by subtracting a
**back-off** $C(u)\ge 0$ — a data-driven safety margin — from the spec applied to the
nominal model:
$$
\max_{u\in\mathcal U}\; \pi(u)
\quad\text{s.t.}\quad
\hat g(u) + C(u)\;\le\;\bar g .
\tag{2}
$$
The entire content of an uncertainty-aware RTO is in how $C(u)$ is constructed. The
back-off is correct when $\hat g(u)+C(u)$ upper-bounds the conditional quantile,
$\hat g(u)+C(u)\ge Q^{z}_{1-\alpha}[\,g(u,\cdot)\,]$, so that any $u$ feasible in (2) is
feasible in (1).

**The oracle.** Because $g(u,z)$ is monotone increasing in $z$ at every $u$ (more light
key in the feed yields more in the bottoms — verified on the twin, Section 4), the
conditional quantile collapses to a single model evaluation,
$$
Q^{z}_{1-\alpha}[\,g(u,\cdot)\,] \;=\; g\!\left(u,\,z_{1-\alpha}\right),
\qquad z_{1-\alpha}=\mathcal F_\sigma^{-1}(1-\alpha),
$$
giving the **oracle back-off** $C_{\mathrm{orc}}(u)=\big[g(u,z_{1-\alpha})-\hat g(u)\big]_+$,
where $[\cdot]_+=\max(\cdot,0)$ enforces a non-negative margin. The oracle requires the
true plant response and is therefore not deployable; it is the achievable benchmark
against which data-driven back-offs are measured. By construction it makes the realised
violation at any active optimum equal to $\alpha$, which we use to confirm that the
chance-constraint machinery itself is sound (Section 5).

## 3.2 Conformal constraint back-offs

Conformal prediction supplies the natural distribution-free route to $C(u)$ from data.
We assume a **calibration set** of plant evaluations
$\{(u_i,z_i,g_i)\}_{i=1}^{n}$ obtained by sampling $u_i\sim\mathrm{Unif}(\mathcal U)$ and
$z_i\sim\mathcal F_\sigma$ and recording $g_i=g(u_i,z_i)$ (in deployment these are
historical operating records; here they are queries to the validated truth surface).
Define the **model residuals** $r_i=g_i-\hat g(u_i)$ — the amount by which the realised
bottoms composition exceeds the nominal prediction under the disturbance.

For a one-sided upper bound at level $1-\alpha$, the finite-sample split-conformal
quantile of scores $\{s_i\}_{i=1}^n$ is the order statistic
$$
\widehat Q_{1-\alpha}(\{s_i\}) \;=\; s_{(k)},\qquad
k=\big\lceil (n+1)(1-\alpha)\big\rceil ,
\tag{3}
$$
($+\infty$ if $k>n$), where $s_{(k)}$ is the $k$-th smallest score. We compare four
constructions of $C(u)$, all floored at zero.

**Fixed (constant) margin.** The simplest back-off ignores the operating point:
$C_{\mathrm{fix}}=\widehat Q_{1-\alpha}(\{r_i\})$. It is marginally valid over the
calibration distribution but spends the same margin everywhere, regardless of local
sensitivity to $z$.

**Normalised / locally adaptive (the baseline).** Heteroscedastic conformal prediction
(Lei et al.) scales the score by an estimate of the local spread. We fit a Gaussian-
process scale model $\hat s(u)$ to $\{|r_i|\}$ and conformalise the studentised scores:
$$
C_{\mathrm{nrm}}(u) \;=\; \widehat Q_{1-\alpha}\!\big(\{\,r_i/\hat s(u_i)\,\}\big)\,\cdot\,\hat s(u).
$$
This is the back-off a soft-sensor interval would supply — adaptive in width, and the
method our earlier design adopted. It is marginally valid but, crucially, *not*
conditionally valid, which is the failure analysed in Section 3.3.

**Conformalised quantile regression (CQR, the conditional construction).** Rather than
scale a marginal residual, CQR (Romano, Patterson & Candès) targets the conditional
quantile directly. We fit a gradient-boosted quantile regressor
$\hat q_{1-\alpha}(u)$ to predict $g$ from $u$ at the $(1-\alpha)$ level, form the
one-sided conformity scores $E_i=g_i-\hat q_{1-\alpha}(u_i)$, and correct:
$$
C_{\mathrm{cqr}}(u) \;=\; \big[\,\hat q_{1-\alpha}(u) + \widehat Q_{1-\alpha}(\{E_i\}) - \hat g(u)\,\big]_+ .
$$
Because $\hat q_{1-\alpha}(u)$ estimates the conditional $(1-\alpha)$ quantile at each
$u$, $C_{\mathrm{cqr}}$ tracks the local conditional risk; the conformal correction
restores finite-sample marginal validity on top.

## 3.3 The selection effect: why marginal validity fails under optimisation

Split and normalised conformal prediction guarantee **marginal** coverage: averaged
over the calibration distribution of operating points,
$$
\mathbb{P}_{u\sim\mathrm{Unif}(\mathcal U),\,z\sim\mathcal F_\sigma}\!\left[\,g(u,z)\le \hat g(u)+C(u)\,\right]\;\ge\;1-\alpha .
\tag{4}
$$
They do **not** guarantee **conditional** coverage at a particular operating point,
$\mathbb{P}_{z}[\,g(u,z)\le\hat g(u)+C(u)\mid u\,]\ge 1-\alpha$; the conditional level
varies over $\mathcal U$, exceeding $1-\alpha$ where the back-off is loose and falling
below it where the back-off is tight (Gibbs, Cherian & Candès).

RTO is precisely an operator that selects against this variation. The optimiser in (2)
chooses, among points feasible under the back-off, the most profitable — which is the
point pressing hardest against the spec, i.e. where $\hat g(u)+C(u)$ approaches $\bar g$
from below. Profit is maximised by recovering more light key into the bottoms, so the
optimiser is drawn to operating points with the *smallest* back-off relative to the
true local risk. The $\arg\max$ therefore systematically lands where $C(u)$
**under-covers** the conditional quantile, and the realised violation at the selected
point $u^\star$ exceeds the nominal $\alpha$ — often severely. This is a
constraint-space analogue of post-selection inference (the "winner's curse"): a margin
that is valid on average is not valid at the point an optimiser deliberately seeks out.
We refer to it as the **conformal selection effect**. It is intrinsic to placing a
marginally-calibrated interval inside an optimisation loop and is not repaired by making
the interval adaptive in width: a normalised back-off whose scale model $\hat s(u)$ is
smooth still leaves exploitable pockets of under-coverage, and the optimiser finds them.

The conditional construction is the structural fix. Because $C_{\mathrm{cqr}}(u)$
estimates the conditional quantile at every $u$, there is no systematic average-versus-
local gap for the optimiser to exploit; the residual discrepancy is finite-sample
estimation error rather than a coverage-target mismatch, and it is small where the
calibration set is adequate. Section 5 shows the normalised back-off realising roughly
five times the nominal violation across the disturbance range while the CQR back-off
tracks the oracle.

## 3.4 A-posteriori calibration at the selected setpoint

Conditional targeting removes the *systematic* selection bias but not the finite-sample
residual: at a given calibration size the CQR optimum may still violate slightly. We
close the gap with a conformal-predictive-programming a-posteriori step (Zhao et
al.), adapted to the feasibility structure of (2). After solving (2) with a base
back-off $C_0(\cdot)$ and obtaining $u^\star$, we inflate the back-off by a scalar
$\kappa\ge 1$, re-solve, and seek the smallest $\kappa$ for which the realised violation
at the *resolved* optimum meets the target on held-out data:
$$
\kappa^\star=\min\Big\{\kappa\ge 1 : \hat v\big(u^\star(\kappa)\big)\le\alpha\Big\},
\qquad u^\star(\kappa)=\arg\max_{u}\big\{\pi(u):\hat g(u)+\kappa\,C_0(u)\le\bar g\big\},
$$
where $\hat v(u)=\widehat{\mathbb{P}}_z[g(u,z)>\bar g]$ is a Monte-Carlo estimate of the
realised violation. Three implementation points make the search well-posed. First, the
feasible set in $\kappa$ is an **interval**: as $\kappa$ grows the back-off enlarges
until no operating point satisfies the tightened constraint, so we first locate the
largest feasible $\kappa$ and verify it can comply before bisecting for the smallest
compliant $\kappa$ within $[1,\kappa_{\max}]$. Second, $\hat v(\kappa)$ is evaluated on a
**fixed** validation disturbance sample so that it is monotone in $\kappa$ and the
bisection is deterministic; the reported violation uses an independent test sample to
avoid optimism. Third, when even the largest feasible $\kappa$ violates, the instance is
declared infeasible — the honest outcome when the data cannot certify the target. The
inflation factor $\kappa^\star$ is itself an interpretable diagnostic: it measures how
far the conditional estimate must be stretched to be safe, and its growth signals the
onset of calibration-data starvation (Section 5).

## 3.5 Process twin, surrogates, and economics

**Twin.** The plant is a rigorous DWSIM 9.0.5 model of a debutanizer, reduced to the
binary n-butane / n-hexane system (light key / stabilised-gasoline proxy) under the
Peng–Robinson equation of state, with nine equilibrium stages (condenser indexed $0$,
reboiler $8$), feed on stage $4$, top pressure $4.7$ bar and a $0.4$ bar column drop.
The feed is $100$ kmol h$^{-1}$. The model is driven from Python via DWSIM's
automation interface; a feed-composition campaign over a grid in $(z,R,D)$ yields the
plant evaluations used below. The binary reduction keeps every twin state checkable
against first-principles vapour–liquid equilibrium and matches the soft-sensor physics
proxy of the companion paper.

**Surrogates.** Two Gaussian-process surfaces stand in for the plant in (2). The
**truth surface** $g(u,z)=x_B(R,D,z)$ is fit on the full feed-composition campaign and
supplies the *realised* bottoms composition used to score violations and to define the
oracle; it is validated by leaving one feed-composition slice out and predicting it
(Section 5). The **nominal surfaces** — $\hat g(u)$, the distillate purity, and the
reboiler duty needed for profit — are fit on the nominal ($z_0=0.35$) sweep and define
the optimiser's model and objective. All GPs use a Matérn-$5/2$ kernel on standardised
inputs with bounded hyperparameters (a maximum-a-posteriori regularisation of the
log-hyperparameters that prevents length-scale collapse and makes fits reproducible
across machines) and a fixed optimiser seed.

**Economics.** Operating profit is a two-stream proxy: the overhead stream is valued at
the light-key (LPG) price and the bottoms at the stabilised-gasoline price, both by
mass, minus the reboiler energy cost. Because gasoline outvalues the light key per unit
mass, every kilomole of light key retained in the bottoms is an upgrade, so profit
increases as the column rides the bottoms-composition spec from below — making the
quality constraint economically active and the back-off width a direct profit cost.
Price anchors are literature defaults (regional spot benchmarks), documented with their
sources; the contribution depends on the price *spread*, not the absolute levels.

---

# 4. Case-study design

## 4.1 Plant evaluations: the feed-composition campaign

The twin of Section 3.5 is exercised over a grid in the decision and disturbance
variables to produce the plant evaluations all results rest on. The campaign spans
feed light-key fractions $z\in\{0.30,0.325,0.35,0.375,0.40\}$ crossed with reflux
ratios and distillate flows covering the decision box, each case solved to convergence
in DWSIM and screened for mass-balance closure and solver staleness. The accepted set
is $77$ operating points. A nominal sub-sweep at $z_0=0.35$ supplies the $15$ points
that fit the optimiser's nominal surfaces $\hat g$, distillate purity, and reboiler
duty; the full $77$-point set fits the truth surface $g(u,z)$.

Two campaign facts shape the design. First, the bottoms composition responds strongly
and monotonically to feed composition: at a fixed mid-box setpoint $x_B$ rises by an
order of magnitude across the sampled $z$ range, confirming that the disturbance
genuinely propagates to the constrained quantity and that the monotone-$z$ oracle of
Section 3.1 is well-founded. Second, the specification is **physically unattainable for
large feed excursions**: for $z\gtrsim0.38$ the minimum achievable $x_B$ within the
distillate-flow bounds exceeds the spec (at $z=0.40$ the column floor is $x_B\approx
0.048$, well above $\bar g=0.02$), because removing enough light key to meet spec would
require a distillate flow outside the operable range. The whole $[0.30,0.40]$ ensemble
is therefore infeasible for *any* back-off, which is itself the design rationale for a
tightly controlled feed: the operational disturbance must be small, consistent with the
realistic $\sigma_z\approx0.006$ anchor below.

## 4.2 Disturbance sweep and calibration

The disturbance magnitude is swept over
$\sigma_z\in\{0.004,0.006,0.008,0.010,0.015,0.020,0.025\}$, with $\sigma_z=0.006$ taken
as the operationally realistic centre (a well-controlled upstream feed) and the larger
values probing how each method degrades as the feed becomes more variable. For each
$\sigma_z$ the calibration set of Section 3.2 is drawn with size scaled to the
disturbance, $n=\lfloor 1500\cdot\max(1,\sigma_z/0.006)\rfloor$, reflecting that the
conditional-quantile estimate needs more data as the disturbance widens; at the
realistic centre $n=1500$. All draws use a fixed seed so the regime map reproduces
exactly on a given platform.

## 4.3 Methods compared

Four back-off constructions enter the comparison: the **oracle** (the true conditional
quantile, Section 3.1) as the achievable benchmark; the **constant margin**
($C_{\mathrm{fix}}$) and the **normalised/adaptive** back-off ($C_{\mathrm{nrm}}$) as
the two marginally-valid baselines — the latter being the soft-sensor-style interval our
earlier design used; and the **conditional method**, CQR with a-posteriori calibration
($C_{\mathrm{cqr}}$ followed by the $\kappa$-step of Section 3.4), as the proposed
remedy. Each method produces a back-off field over the decision box; the RTO of Eq. (2)
selects the profit-maximising feasible setpoint; that setpoint is then scored against
the truth surface.

## 4.4 Metrics and protocol

The **primary** metric is the realised constraint-violation rate at the selected
setpoint, $\hat v(u^\star)=\widehat{\mathbb P}_z[g(u^\star,z)>\bar g]$, estimated by
Monte-Carlo over the disturbance ($4\text{–}6\times10^{3}$ draws); the target is
$\hat v\le\alpha=0.10$. The **secondary** metric is the operating profit
$\pi(u^\star)$, reported only to show that calibrated safety is not bought at a profit
cost — never as a performance claim in its own right, because at realistic disturbance
the constraint is barely active and all methods sit within a fraction of a percent of
the deterministic optimum. Feasibility is itself an outcome: a method is reported
infeasible at a given $\sigma_z$ when no back-off (after a-posteriori inflation, where
applicable) admits a setpoint meeting the target. The a-posteriori inflation factor
$\kappa^\star$ is logged as a data-adequacy diagnostic.

Because the realised violation is a Monte-Carlo quantity, the reported rates carry
sampling noise of order $\pm0.01\text{–}0.02$ across platforms even though they are
seeded within a platform; the regime *structure* and the magnitude of the selection
effect are stable to this noise. The truth surface itself is validated by a
leave-one-feed-composition-slice-out test — fitting on all $z\neq0.375$ and predicting
the held-out $z=0.375$ slice — which bounds the accuracy of every violation estimate
(Section 5.6). The specification is $\bar g=0.02$, the miss level $\alpha=0.10$, the
decision box $[0.8,3.0]\times[33,37]$, and the master seed $20260614$ throughout.

---

# 5. Results

The four back-off constructions are compared across the disturbance sweep on the
committed twin data (seed $20260614$); Table 1 is the full regime map and Figure 3 its
headline projection — realised violation against disturbance magnitude for every method,
with the nominal target $\alpha=0.10$ marked. The reading is consistent across the
sweep and is summarised method by method below.

## 5.1 The selection effect: marginal back-offs are unsafe under optimisation

The normalised/adaptive back-off — the soft-sensor-style interval, marginally valid by
construction — fails dramatically. Its realised violation sits at $0.43\text{–}0.50$
across the entire disturbance range against the $0.10$ target, roughly **five times**
the nominal level, with no dependence on $\sigma_z$: the failure is structural, not a
matter of the disturbance being large. The mechanism is visible in the selected
setpoint. At every $\sigma_z$ the adaptive method drives the optimiser to the low-$D$
corner near $R\approx2.83,\,D\approx33.7$ — close to the deterministic optimum, where
the back-off is smallest relative to the true local risk. This is precisely the
operating point the selection-effect argument of Section 3.3 predicts: among feasible
points the optimiser takes the most profitable, which is the one where the marginally-
calibrated margin under-covers the conditional quantile. Making the interval adaptive in
width does not help, because the smooth scale model still leaves under-covered pockets
for the optimiser to occupy.

The constant margin is less catastrophic but still unsafe and ultimately unusable. At
small disturbance it over-violates modestly ($0.17\text{–}0.19$ at
$\sigma_z\le0.006$) — a single margin sized to the pooled residual is too loose where
the column is sensitive and too tight where it is not — and for $\sigma_z\ge0.015$ no
constant margin admits a feasible setpoint at all: the margin required to cover the
worst region of the box exceeds the spec headroom everywhere. Neither marginal
construction controls the violation rate that the chance constraint demands.

## 5.2 The oracle confirms the chance constraint is sound

That the marginal methods fail is a property of the *back-off*, not of the formulation.
The oracle back-off — the true conditional quantile, available here because the twin
furnishes the plant response — realises a violation of $0.079\text{–}0.106$ across all
seven disturbance levels, i.e. $\approx\alpha$ by construction, and remains feasible to
the largest $\sigma_z$ tested. The oracle is not a deployable method (it needs the plant
it is meant to protect), but it certifies two things: the chance-constrained RTO of
Eq. (1) is correctly posed, and a back-off that is *conditionally* correct controls the
violation rate exactly where the marginal ones do not. The oracle is therefore the bar
the data-driven conditional method must reach.

## 5.3 Conditional calibration restores violation control

The proposed method — CQR with a-posteriori calibration — tracks the oracle. Its
realised violation is $0.063\text{–}0.105$ for $\sigma_z\le0.020$, within about $0.01$
of the oracle at every level and inside the target band, and it does so at near-oracle
profit (Table 1: the CQR and oracle profit columns differ by at most a few dollars per
hour at each $\sigma_z$). Two features distinguish it from the marginal baselines. It
selects setpoints that *move with the disturbance* — from $D\approx34.3$ at the realistic
$\sigma_z=0.006$ out to $D\approx36.6$ at $\sigma_z=0.020$ — backing the column away from
the corner as the feed becomes more variable, exactly as the conditional risk requires
and exactly what the marginal methods fail to do. And where the residual finite-sample
gap would otherwise let it violate, the a-posteriori step closes it: at
$\sigma_z=0.006$ the conditional quantile alone is slightly optimistic and the inflation
$\kappa=1.53$ restores the target; the reported violation is on an independent test
draw. The conditional construction supplies the right *shape* of back-off and the
a-posteriori step supplies the right *scale*.

## 5.4 The boundary: conditional estimation runs out of data

The conditional method is not unconditionally safe; it degrades, gracefully and
diagnosably, as the disturbance outgrows the calibration set. The a-posteriori inflation
$\kappa$ is the signal. For $\sigma_z\le0.010$ it stays near unity ($1.0\text{–}1.5$):
the conditional estimate is already close to correct and little stretching is needed. At
$\sigma_z=0.015$ it jumps to $5.78$ — the estimate must be stretched nearly six-fold to
be certified safe, and the method is operating at the edge of its feasible-$\kappa$
window. At $\sigma_z=0.025$ — more than four times the realistic disturbance — no
feasible inflation certifies the target and the method is reported infeasible, even
though the oracle remains feasible there. The gap between the two is the finite-sample
cost of not knowing the plant: with the truth surface the conditional quantile is exact;
estimated from a calibration set whose support must widen with $\sigma_z$, it eventually
cannot be pinned down tightly enough for an optimiser to lean on. The $\kappa$ trace
(Figure 7) makes this a readable property of the method rather than a silent failure —
the operator sees the safety margin being stretched before it breaks.

## 5.5 Safety, not profit

A deliberate non-result is that the proposed method does not earn more money. At the
realistic disturbance the chance constraint is barely active: every method, including
the deterministic optimum (profit $\approx\$5393\,\mathrm{h}^{-1}$), lies within $0.5\%$
of every other (Table 1; Figure 5). The marginally-higher profit of the unsafe adaptive
method is not an advantage — it is the profit of operating at a setpoint that violates
the spec half the time. The contribution is therefore not a profit improvement but
*calibrated violation control at no profit cost*: the conditional method buys safety
that the marginal methods cannot deliver, while giving up essentially nothing in
operating profit at the realistic operating point. The profit separation between
methods only opens up as $\sigma_z$ grows and the constraint begins to bind, at which
point the marginal methods are already either grossly violating or infeasible.

## 5.6 Surrogate validation and precision accounting

Every violation rate above is read against the truth surface, so its credibility rests
on that surface interpolating the disturbance faithfully. The leave-one-feed-
composition-slice-out test — fitting on all $z\neq0.375$ and predicting the held-out
$z=0.375$ slice — gives $R^2=0.917$ and a mean absolute error of $0.0053$ in $x_B$ over
$15$ held-out points (Figure 6). That error is the precision floor on the violation
estimates: it is why the oracle lands at $0.08\text{–}0.11$ rather than exactly $0.10$,
and it bounds how finely any method's violation can be resolved. Layered on top is the
Monte-Carlo sampling noise of the violation estimator itself, of order
$\pm0.01\text{–}0.02$ across platforms; re-running the map on a different machine moves
individual rates by at most this much while leaving the regime structure and the
five-fold selection-effect gap intact. We therefore report violation rates as estimates
with a band, not as point values — the qualitative claims (marginal fails $\sim$5×,
conditional tracks the oracle, the data-starvation boundary) all sit far outside that
band.

---

# 6. Discussion

## 6.1 The general lesson: conformal-in-the-loop needs conditional validity

The result is narrow in its case study but general in its mechanism. Nothing in the
selection-effect argument of Section 3.3 is specific to a debutanizer or to feed
composition: it follows from two facts that hold whenever a conformal interval is placed
inside an optimisation. First, split and locally-adaptive conformal prediction guarantee
coverage *marginally*, averaged over the calibration distribution, and the conditional
coverage varies across the input space. Second, an optimiser is a selection operator
that seeks the boundary of the feasible region and therefore lands preferentially where
the margin is tightest relative to the local risk — which is where coverage is worst.
Any pipeline with these two features — a marginally-calibrated margin and an optimiser
pressing on it — will exhibit the same degradation. This includes back-offs in
stochastic and learning-based model-predictive control, constraint handling in safe
Bayesian optimisation, and any chance-constrained program that sizes its margin from a
marginally-valid predictor. The practical implication is a design rule: a conformal
margin used as a hard optimisation constraint must be *conditionally* valid at the
operating point, not merely marginally valid over a calibration set. Where conditional
validity cannot be guaranteed in advance, an a-posteriori calibration at the selected
solution (Zhao et al., 2024) is necessary — but, as Section 5.4 shows, that step is
small and reliable only when the base margin is already conditional; on a marginal base
it must inflate the margin severalfold and can fail outright.

## 6.2 What the method does and does not buy

The contribution is calibrated violation control, and the honest accounting of its value
is in two parts. On safety, the conditional method delivers what the marginal baselines
cannot: a realised violation that tracks the oracle to within the Monte-Carlo band across
the operationally realistic disturbance range, where the naive-adaptive margin violates
roughly five times the nominal rate and the fixed margin is either over-violating or
infeasible. On profit, the method buys essentially nothing at the realistic operating
point — every method, including the deterministic optimum, lies within half a percent
(Section 5.5) — because at a well-controlled feed the chance constraint is barely active.
We regard the second fact as a feature of the honest framing, not a weakness: the value
of a safety margin is not that it raises profit but that it removes a violation the
unsafe alternative incurs while appearing to be slightly more profitable. The profit
separation only widens as the disturbance grows and the constraint begins to bind, at
which point the marginal methods have already failed. A reader looking for a profit
headline will not find one here, and should not: the result is about constraint
integrity under uncertainty.

## 6.3 Limitations

Several boundaries should be read with the result. The plant is a *simulation* twin —
a rigorous DWSIM Peng–Robinson model, validated by leave-one-disturbance-out
interpolation (R²=0.917, MAE 0.0053 in x_B), but not plant data; the selection-effect
mechanism is structural and should transfer, but the specific magnitudes (the five-fold
factor, the regime boundaries) are twin-specific. The study uses a single binary
n-butane/n-hexane system, one unmeasured disturbance (feed composition), and a
two-dimensional decision; a higher-dimensional decision or several simultaneous
disturbances would enlarge the space over which the conditional quantile must be
estimated and would therefore bring the data-starvation boundary of Section 5.4 to
*smaller* disturbance magnitudes than observed here. The reported violation rates are
Monte-Carlo estimates carrying a ±0.01–0.02 band, and the truth-surface error (~0.005 in
x_B) is a precision floor below which no violation difference can be resolved; the
qualitative claims sit far outside that band, but fine rankings near the target should
not be over-read. The oracle is a benchmark, not a method — it uses the true plant
response and the monotone-in-z structure to evaluate the conditional quantile in one
shot; the conformal methods make no monotonicity assumption, but a non-monotone or
multi-modal constraint response would require the oracle itself to be estimated rather
than read off, complicating only the benchmark and not the proposed method. Finally, the
a-posteriori step requires an independent calibration draw at the selected setpoint; in
deployment this is a held-out window of operating data, and its size sets how tightly the
residual gap can be closed.

## 6.4 Toward closed-loop and plant deployment

This paper is the static, open-loop foundation: the disturbance is unmeasured and the
optimiser commits to a setpoint under a calibrated margin. The natural extension is
closed-loop, where an online estimate of the constrained quantity — supplied by the soft
sensor of the companion paper, which infers the unmeasured composition from tray
temperatures — feeds back so that the back-off contracts as the disturbance becomes
partially observed and the operating point tracks it. That closed-loop study, with the
sensor in the loop and the disturbance evolving in time, is left to future work; the
exchangeability questions it raises (calibration under feedback and temporal dependence)
connect directly to the beyond-exchangeability conformal literature of Section 2.2. The
other clear next steps are validation on plant or pilot data, where the disturbance law
is empirical rather than assumed, and extension to multi-component products and
higher-dimensional decisions, where the conditional-estimation cost is the binding
constraint. In all of these, the design rule of Section 6.1 is the portable result: size
the margin conditionally, and read the a-posteriori inflation as the signal that the
data can no longer certify the target.

---

# 7. Conclusion

Real-time optimisation must subtract a back-off from a quality specification to protect a
constraint it cannot measure, and conformal prediction is the natural distribution-free
way to size that back-off. We have shown that the natural choice is unsafe: an optimiser
pressing on a marginally-valid conformal margin — even a locally-adaptive one — is a
selection mechanism that drives the operating point to where the margin under-covers the
conditional constraint quantile, so the realised violation reaches roughly five times the
nominal level across the disturbance range. An oracle margin built from the true
conditional quantile holds the violation at the target, confirming that the failure is in
the back-off, not the chance-constrained formulation. The remedy is conditional validity:
a conformalised-quantile-regression back-off, with an a-posteriori calibration step at the
selected setpoint, returns the realised violation to the oracle level at near-oracle
profit over the operationally realistic disturbance range, and degrades only — and
diagnosably, through a climbing inflation factor — when the disturbance widens beyond
several times the realistic level and the conditional estimate runs out of calibration
data. A regime map over disturbance magnitude characterises where each margin controls
violation, where a constant margin becomes infeasible, and where even the conditional
method can no longer certify the target.

The contribution is calibrated safety, not profit: at a well-controlled feed the
constraint is barely active and all methods earn within half a percent of the
deterministic optimum, so the value of the conditional method is the violation it
removes, not the profit it adds. The mechanism is general — any conformal interval used
as a hard optimisation constraint is exposed to the same selection effect — and the
portable design rule is to size the margin conditionally and to read the a-posteriori
inflation as a data-adequacy signal. Demonstrated here on a rigorous binary-distillation
twin, the approach sets up a closed-loop extension in which an online soft sensor of the
unmeasured quality feeds the back-off as the disturbance is partially observed.

---

## References

See references.md (themed list; elsarticle BibTeX at LaTeX conversion).
