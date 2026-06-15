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
