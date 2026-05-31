"""Open-loop bias-update for the soft sensor (Phase 1B, step 3).

Verified against the primary: Shardt & Yang (2016), "Development of Soft Sensors
for the Case Where the Time Delay is Random", IFAC-PapersOnLine 49-7, 1193-1198
(/mnt/project/). A soft sensor is a process model Gp_hat plus a bias-update term
GB; the model tracks changes but may be biased in absolute value, and GB
corrects that bias by comparing delayed true values with the soft-sensor output.
GB can only update when a new (delayed) measurement arrives.

The Phase 1A/1B diagnosis (ADR-007): the physics-anchored model's predictor->y
correlation is stable across regimes, but a per-regime calibration offset drifts
(fold residual means -0.013 .. -0.089; fold 1 is bias-dominated, R^2 = -1.49).
That is exactly the bias GB is meant to remove.

FORM (open-loop). The Debutanizer soft sensor estimates C4; it does not drive a
controller, so the system is OPEN-LOOP. Shardt's open-loop conclusion is to use
the most recent available delayed value (his "Case I"). We implement the
feedforward exponentially-weighted form on the delayed RAW residual:

    b_t = (1 - lam) * b_{t-1} + lam * (y_{t-theta} - yhat_{t-theta})
    corrected_t = yhat_t + b_t

  - lam = 1 reduces to b_t = (y_{t-theta} - yhat_{t-theta}), i.e. "use the most
    recent residual" = Shardt's open-loop optimum for a fixed/known delay.
  - lam < 1 exponentially smooths the delayed residual to damp lab noise, at the
    cost of a small tracking lag.
  - Because the update is FEEDFORWARD on the raw residual (no feedback through
    the theta-delay), it is unconditionally stable for any lam in (0, 1]. The
    closed-loop integrator that Shardt requires for exact tracking when the soft
    sensor drives control (Eq. 6, denominator coeffs summing to zero; Eq. 10) is
    NOT needed here and is deferred to Module 3 (RTO/control).

theta is the LABEL (analyzer) delay -- how stale the freshest lab value is --
which is conceptually distinct from the 15-sample transport lag baked into the
features. Defaulted to 15 as a proxy; refine against the real analyzer cycle.

Detection is the trigger (Phase 1B step 2); THIS module is the correction. The
cross-regime R^2 lift / SE reduction is the Module 1 robustness result.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.metrics import r2_score

from ipis.module1_soft_sensor.evaluation.drift import FoldResiduals


def apply_bias_update(
    y_true: Sequence[float],
    y_pred: Sequence[float],
    lam: float,
    delay: int,
    b0: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Causal open-loop EWMA bias update (Shardt 2016, open-loop Case I family).

        b_t = (1 - lam) * b_{t-1} + lam * (y_true[t-delay] - y_pred[t-delay])
        corrected[t] = y_pred[t] + b_t

    Only labels available ``delay`` samples in the past are used, so the result
    is strictly causal. For the first ``delay`` samples no label is available and
    the bias is held at ``b0``. lam=1 is the most-recent-residual rule.

    Args:
        y_true: True (delayed) targets, time-ordered.
        y_pred: Raw model predictions, aligned with y_true.
        lam: EWMA adaptation rate in (0, 1]. 1 = most-recent residual.
        delay: Label/analyzer delay theta in samples (>= 0).
        b0: Initial bias before any label is available.

    Returns:
        (corrected, bias): corrected predictions and the bias trajectory.

    Raises:
        ValueError: If lam not in (0, 1], delay < 0, or lengths differ.
    """
    if not 0.0 < lam <= 1.0:
        raise ValueError(f"lam must be in (0, 1], got {lam}")
    if delay < 0:
        raise ValueError(f"delay must be >= 0, got {delay}")
    yt = np.asarray(y_true, dtype=float).ravel()
    yp = np.asarray(y_pred, dtype=float).ravel()
    if yt.shape != yp.shape:
        raise ValueError(f"y_true {yt.shape} and y_pred {yp.shape} must match.")

    n = yt.shape[0]
    bias = np.empty(n)
    corrected = np.empty(n)
    b = float(b0)
    for t in range(n):
        if t >= delay:
            r = yt[t - delay] - yp[t - delay]
            b = (1.0 - lam) * b + lam * r
        bias[t] = b
        corrected[t] = yp[t] + b
    return corrected, bias


def corrected_fold_r2(
    folds: Sequence[FoldResiduals],
    lam: float,
    delay: int,
    b0: float = 0.0,
) -> list[float]:
    """Per-fold R^2 after applying the causal bias update to each fold's stream.

    Reuses the tested ``FoldResiduals`` (held-out y_true/y_pred) from
    ``blocked_cv_residuals``; the bias update streams within each fold's block
    using only delayed labels (cold start, b0 per block).
    """
    out: list[float] = []
    for f in folds:
        corrected, _ = apply_bias_update(f.y_true, f.y_pred, lam, delay, b0)
        out.append(float(r2_score(f.y_true, corrected)))
    return out


def oracle_debias_r2(folds: Sequence[FoldResiduals]) -> list[float]:
    """Per-fold R^2 if each fold's TRUE residual mean were removed.

    This is the best achievable correction by a single CONSTANT per-fold offset
    (it uses the fold's own held-out labels, so it is not causal). It is the
    ceiling for a constant bias only: where the residual DRIFTS within a fold, a
    tracking update can exceed it, so this is a reference level, not an absolute
    upper bound. Removing the residual mean never decreases a fold's R^2.
    """
    return [float(r2_score(f.y_true, f.y_pred + f.residuals.mean())) for f in folds]
