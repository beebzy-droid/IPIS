# ADR-014 — Phase 3B: conditional-conformal back-offs for chance-constrained RTO

**Status:** Accepted
**Date:** 2026-06-14
**Decision owner:** Bien Busico
**Module:** 3 (RTO) — Phase 3B (uncertainty-aware RTO; paper-2 contribution)
**Extends:** ADR-013 (DWSIM twin + deterministic RTO), scoping.md D1–D5 (feed-z
disturbance ensemble at known R, D)
**Supersedes (framing):** the earlier 3B framing "an adaptive conformal back-off
earns more profit than a fixed margin" (Design A: tray-6 soft sensor pooled over
R, D, z)

## Context

3B adds uncertainty to the 3A deterministic RTO. The ratified scope (D5) is a
CPP-style chance constraint over the **unmeasured feed-composition disturbance**
z (feed n-C4 mole fraction) at a **known** decision (R, D):

    maximize  profit(R, D)   s.t.   P_z[ xB(R, D, z) <= spec ] >= 1 - alpha

The RTO optimizes the nominal (z=0.35) GP surrogate and cannot see z; the 3-D
truth surface xB(R, D, z) — fit on the 77-row feed-z campaign, leave-z-out
R²=0.927 / MAE 0.0048 — supplies the true bottoms composition at the realized
(R, D, z), so realized constraint violation is scored honestly. The conformal
back-off C(R, D) enters as a constraint margin: xB_nominal(R, D) + C(R, D) <= spec.

An exploratory run of the originally-planned method (normalized/adaptive
one-sided conformal, the M1 soft-sensor interval machinery) exposed a failure
that reframes the contribution.

## Decisions (B1–B6)

**B1 — The contribution is calibrated *safety*, not profit.** At realistic feed
variability (sigma_z ~ 0.006; B3) the chance constraint is barely active and
every back-off lands within 0.5% of the deterministic optimum (~$5393/h). Profit
is not the differentiator; the realized constraint-violation rate is. The 3B
headline is therefore violation control, reported with profit as a secondary
axis. (Audit-A: lead with calibrated risk control.)

**B2 — A marginally-calibrated back-off is unsafe under RTO selection (the
finding).** A back-off with only *marginal* conformal coverage — including the
adaptive/normalized variant — is exploited by the optimizer, which drives toward
operating points where the margin under-covers the *conditional* (1-alpha)
quantile. On the real twin, the normalized back-off yields realized violation
0.43–0.50 across all sigma_z against a 0.10 target (~5x nominal). This is the CPP
selection effect (Lindemann et al.) / the conditional-coverage gap of
Gibbs–Cherian–Candès, demonstrated on a chemical process. The fixed (constant)
margin over-violates at small sigma_z and is infeasible for sigma_z >= 0.015.

**B3 — Realistic disturbance magnitude sigma_z ~ 0.006, swept 0.004–0.025.**
Well-controlled upstream feed (operator anchor). The spec is physically
unachievable for z >~ 0.38 within the D-bounds (distillate-flow limited: min
xB at z=0.40 is ~0.048), so the full [0.30, 0.40] ensemble is infeasible for all
methods — operational sigma_z *must* be tight, which the anchor reflects.

**B4 — The fix: conditional CQR + CPP a-posteriori calibration.** Conformalized
quantile regression (Romano–Patterson–Candès) estimates the *conditional*
(1-alpha) quantile of xB over (R, D) directly (gradient-boosted quantile loss +
one-sided conformal correction), so the optimizer cannot exploit a
marginal-vs-conditional gap. A CPP a-posteriori step then inflates the back-off
by the smallest kappa >= 1 such that the realized violation at the *selected*
optimum is <= alpha on a held-out validation draw (reported on an independent
test draw). Result: realized violation 0.063–0.105 tracking the oracle (the truth
conditional quantile) across sigma_z <= 0.020, at near-oracle profit; infeasible
only at the extreme sigma_z = 0.025 (3x realistic). (Audit-B, Audit-C.)

**B5 — Back-offs are non-negative; the conditional estimate scales with the
disturbance.** A safety margin is floored at 0 (negative margins break kappa
scaling). The conditional-quantile estimate needs more calibration data as the
disturbance widens; n_cal is scaled with sigma_z (1500 at the realistic center).
The a-posteriori kappa search handles the feasibility *window* (large kappa
over-tightens to an empty feasible set) and evaluates violation on a fixed
validation z-draw so viol(kappa) is monotone.

**B6 — The normalized/adaptive method is retained as the documented baseline.**
It is the method that fails; it anchors the negative result. The tray-6 soft
sensor (Design A, closed-loop feedback) is deferred to 3C.

## Consequences

- Engages three project-corpus sources as the methodological spine: CPP
  (selection effect + a-posteriori), Gibbs–Cherian–Candès (conditional
  coverage), CQR (the conditional estimator). Closest prior art (del Río Chanona
  2021, GP-modifier RTO) is separated by the distribution-free conformal
  treatment vs a Gaussian posterior.
- Honest caveat for the paper: the truth surface carries ~0.006 xB error
  (leave-z-out MAE), the floor on violation-rate precision; the oracle landing at
  0.08–0.11 rather than exactly 0.10 is that floor. Violation rates are reported
  with this uncertainty band, not as point values.
- Code: `ipis.module3_rto.chance_rto` (engine), `scripts/run_3b3_regime_map.py`
  (the regime map + gate), `tests/unit/test_m3_chance_rto.py`. The 3A
  deterministic RTO and economics anchor are unchanged.
