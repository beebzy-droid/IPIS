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
