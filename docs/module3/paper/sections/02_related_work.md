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
Río Chanona et al. (2021), building on Ferreira et al. (2018) and del Río-Chanona et al.
(2019), use Gaussian-process regression to capture the cost- and constraint-mismatch
non-parametrically and embed trust-region and acquisition-function ideas from Bayesian
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
