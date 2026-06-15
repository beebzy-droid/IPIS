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
