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
