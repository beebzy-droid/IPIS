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
