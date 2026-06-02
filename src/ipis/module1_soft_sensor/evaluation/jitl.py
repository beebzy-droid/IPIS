"""Just-in-time learning (JITL) soft sensor (Phase 1B, literature-standard baseline).

Verified against the primary: Cheng & Chiu (2004), "A new data-based methodology
for nonlinear process modeling", Chem. Eng. Sci. 59, 2801-2810 -- the seminal
JITL soft-sensor paper. JITL runs three steps online per query x_q: (1) select
relevant historical samples by a similarity criterion, (2) build a local model
from them, (3) predict y_q and discard the local model. Euclidean-distance
similarity is the dominant baseline; the local model here is locally-weighted
linear regression (LWR), the Cheng-Chiu original form.

ROLE IN 1B. The original plan made JITL the literature-standard adaptive layer
that closes Gap 2 (regime-shift robustness), wrapped with drift monitoring. This
module IS that baseline; the Shardt open-loop bias-update (bias_update.py) is the
benchmarked comparison against it. Both are evaluated on the SAME blocked-CV
backbone and the SAME physics-anchored features, with the SAME causal delayed-
label constraint (theta=4), so the head-to-head is apples-to-apples. The only
difference under test is the adaptation mechanism: lazy local re-modelling (JITL)
vs a global model plus an O(1) bias term (Shardt).

COMPUTE. JITL is O(N*d^2) per query -- it solves a weighted least-squares local
model from N historical samples for every prediction. The bias-update is O(1) per
step. The number of local fits is reported as the compute proxy; "accuracy per
unit compute" is the axis that makes the comparison publishable.

Similarity / weighting: w_i = exp(-||x_q - x_i||^2 / (2 h^2)) in standardized
feature space; bandwidth h is the single hyperparameter, CV-selected (never test).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.evaluation.blocked_cv import FeatureBuilder
from ipis.module1_soft_sensor.evaluation.drift import FoldResiduals, make_adwin, scan
from ipis.module1_soft_sensor.features.lagged import (
    DEFAULT_INPUT_COLS,
    DEFAULT_TARGET_COL,
    make_lagged_features,
)


def lwr_predict(
    X_db: np.ndarray,
    y_db: np.ndarray,
    x_query: np.ndarray,
    bandwidth: float,
    ridge: float = 1e-6,
) -> float:
    """Locally-weighted linear regression prediction for one query.

    Weights historical samples by a Gaussian kernel of Euclidean distance in the
    (already standardized) feature space, fits a weighted linear model with
    intercept, predicts the query, and discards the model.

        w_i = exp(-||x_query - X_db[i]||^2 / (2 * bandwidth^2))
        beta = (Xa' W Xa + ridge*I)^-1 Xa' W y      (Xa = [1, X_db])
        y_hat = [1, x_query] . beta

    Args:
        X_db: Historical features, shape (N, d), standardized.
        y_db: Historical targets, shape (N,).
        x_query: Query features, shape (d,), standardized with the same scaler.
        bandwidth: Gaussian kernel bandwidth h (> 0), in standardized units.
        ridge: Small Tikhonov term for numerical stability of the local solve.

    Returns:
        The scalar prediction for the query.
    """
    if bandwidth <= 0:
        raise ValueError(f"bandwidth must be > 0, got {bandwidth}")
    X_db = np.asarray(X_db, dtype=float)
    y_db = np.asarray(y_db, dtype=float)
    x_query = np.asarray(x_query, dtype=float)

    d2 = np.sum((X_db - x_query) ** 2, axis=1)
    w = np.exp(-d2 / (2.0 * bandwidth**2))

    n, dim = X_db.shape
    Xa = np.hstack([np.ones((n, 1)), X_db])  # intercept column
    xtw = Xa.T * w  # (d+1, N)
    a = xtw @ Xa + ridge * np.eye(dim + 1)
    b = xtw @ y_db
    beta = np.linalg.solve(a, b)
    return float(np.concatenate([[1.0], x_query]) @ beta)


@dataclass(frozen=True)
class JITLFoldResult:
    """Held-out JITL predictions for one fold, plus the compute proxy."""

    residuals: FoldResiduals
    local_fits: int  # number of LWR local models built (compute proxy)

    @property
    def r2(self) -> float:
        return self.residuals.r2


def jitl_fold_predictions(
    df: pd.DataFrame,
    max_lag: int,
    n_splits: int = 5,
    *,
    label_delay: int,
    bandwidth: float,
    ridge: float = 1e-6,
    input_cols: Sequence[str] = DEFAULT_INPUT_COLS,
    target_col: str = DEFAULT_TARGET_COL,
    feature_builder: FeatureBuilder | None = None,
) -> list[JITLFoldResult]:
    """Always-on JITL predictions per fold, on the blocked-CV backbone.

    Mirrors ``blocked_cv_residuals`` fold mechanics (same TimeSeriesSplit, same
    per-fold leakage-safe build, train-only scaling) but predicts each held-out
    query with a fresh LWR local model instead of a global fit. The historical
    database for a query at test-block position j is the fold's training block
    plus the test rows whose delayed labels have arrived (index <= j - theta),
    enforcing the same causal delayed-label constraint as the bias-update.
    """
    build: FeatureBuilder = feature_builder or (
        lambda seg: make_lagged_features(seg, max_lag, input_cols, target_col)
    )
    n = len(df)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    out: list[JITLFoldResult] = []
    for fold, (train_idx, test_idx) in enumerate(tscv.split(np.arange(n))):
        seg_tr = df.iloc[train_idx].reset_index(drop=True)
        seg_te = df.iloc[test_idx].reset_index(drop=True)
        if len(seg_tr) <= max_lag or len(seg_te) <= max_lag:
            raise ValueError(
                f"Fold segment too short for max_lag={max_lag}: "
                f"train={len(seg_tr)}, test={len(seg_te)}."
            )
        X_tr, y_tr = build(seg_tr)
        X_te, y_te = build(seg_te)
        scaler = StandardScaler().fit(X_tr)
        xtr = scaler.transform(X_tr)
        xte = scaler.transform(X_te)
        ytr = np.asarray(y_tr, dtype=float).ravel()
        yte = np.asarray(y_te, dtype=float).ravel()

        preds = np.empty(len(xte))
        for j in range(len(xte)):
            n_avail = max(0, j - label_delay + 1)  # test rows 0..j-theta
            db_x = np.vstack([xtr, xte[:n_avail]]) if n_avail else xtr
            db_y = np.concatenate([ytr, yte[:n_avail]]) if n_avail else ytr
            preds[j] = lwr_predict(db_x, db_y, xte[j], bandwidth, ridge)

        out.append(
            JITLFoldResult(
                residuals=FoldResiduals(fold=fold, y_true=yte, y_pred=preds),
                local_fits=len(xte),
            )
        )
    return out


def gate_with_drift(
    static_folds: Sequence[FoldResiduals],
    jitl_folds: Sequence[JITLFoldResult],
    *,
    adwin_delta: float = 0.002,
) -> list[JITLFoldResult]:
    """ADWIN-gated hybrid: cheap global model until drift, JITL after.

    For each fold, ADWIN monitors the static model's residual stream; before the
    first detection the cheap global prediction is used, and from the detection
    onward the JITL local prediction is used. This quantifies what the monitoring
    wrapper buys: how much of always-on JITL's benefit is recovered by triggering
    local modelling only after drift, and at what fraction of the local-fit cost.

    static_folds and jitl_folds must be aligned (same folds, same order/length).
    """
    out: list[JITLFoldResult] = []
    for sf, jf in zip(static_folds, jitl_folds, strict=True):
        if sf.y_true.shape != jf.residuals.y_true.shape:
            raise ValueError("static and JITL folds are not aligned in length.")
        residual_stream = sf.y_true - sf.y_pred
        fire = scan(residual_stream, make_adwin(delta=adwin_delta)).first_fire_at_or_after(0)
        switch = len(sf.y_pred) if fire is None else fire
        gated = sf.y_pred.copy()
        gated[switch:] = jf.residuals.y_pred[switch:]
        out.append(
            JITLFoldResult(
                residuals=FoldResiduals(fold=sf.fold, y_true=sf.y_true, y_pred=gated),
                local_fits=len(sf.y_pred) - switch,  # JITL only past the switch
            )
        )
    return out
