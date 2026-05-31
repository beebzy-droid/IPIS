"""Blocked (forward-chaining) time-series cross-validation for soft sensors.

Motivation: a single temporally-adjacent validation set shares the train
regime and so OVERSTATES generalization under non-stationarity. On the
Debutanizer it demonstrably selects the worst test model (val peaks at the
complexity where test craters). Forward-chaining CV instead evaluates a model
on several successive future blocks, giving an honest mean and a spread (SE)
across regimes -- which in turn enables a principled parsimony rule that never
inspects the held-out test set.

Leakage safety mirrors the rest of Module 1: within every fold, lagged
features are built SEPARATELY on the fold's train and test segments (first
``max_lag`` rows of each dropped), and the scaler is fit on the fold-train
only. No shuffling; folds are strictly time-ordered (sklearn TimeSeriesSplit).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.features.lagged import (
    DEFAULT_INPUT_COLS,
    DEFAULT_TARGET_COL,
    make_lagged_features,
)


class Estimator(Protocol):
    """Minimal sklearn-style regressor interface."""

    def fit(self, X: Any, y: Any) -> Any: ...
    def predict(self, X: Any) -> Any: ...


FeatureBuilder = Callable[[pd.DataFrame], "tuple[pd.DataFrame, pd.Series]"]


def blocked_cv_r2(
    df: pd.DataFrame,
    make_estimator: Callable[[], Estimator],
    max_lag: int,
    n_splits: int = 5,
    input_cols: Sequence[str] = DEFAULT_INPUT_COLS,
    target_col: str = DEFAULT_TARGET_COL,
    feature_builder: FeatureBuilder | None = None,
) -> list[float]:
    """Per-fold test R^2 under forward-chaining time-series CV.

    For each fold, features are built within the fold's train and test segments
    separately (leakage-safe), the scaler is fit on fold-train only, a FRESH
    estimator is fit, and R^2 is scored on the fold's held-out block.

    Args:
        df: Time-ordered DataFrame (no shuffling will be applied).
        make_estimator: Zero-arg callable returning a fresh unfitted estimator
            with sklearn-style ``fit``/``predict``. Called once per fold so no
            state leaks between folds.
        max_lag: Maximum lag; also the per-fold minimum segment length guard.
        n_splits: Number of forward-chaining folds.
        input_cols: Input columns to lag (used by the default builder).
        target_col: Target column (used by the default builder).
        feature_builder: Optional callable mapping a segment DataFrame to
            (X, y). Defaults to standard lagged features with ``max_lag``. Pass
            a custom builder (e.g. physics-anchored) to compare feature sets
            under identical CV. The builder MUST be leakage-safe per segment.

    Returns:
        List of per-fold R^2 scores (length n_splits).

    Raises:
        ValueError: If any fold segment is too short for the requested max_lag.
    """
    build: FeatureBuilder = feature_builder or (
        lambda seg: make_lagged_features(seg, max_lag, input_cols, target_col)
    )
    n = len(df)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores: list[float] = []
    for train_idx, test_idx in tscv.split(np.arange(n)):
        seg_tr = df.iloc[train_idx].reset_index(drop=True)
        seg_te = df.iloc[test_idx].reset_index(drop=True)
        if len(seg_tr) <= max_lag or len(seg_te) <= max_lag:
            raise ValueError(
                f"Fold segment too short for max_lag={max_lag}: "
                f"train={len(seg_tr)}, test={len(seg_te)}. "
                f"Reduce n_splits or max_lag."
            )
        X_tr, y_tr = build(seg_tr)
        X_te, y_te = build(seg_te)
        scaler = StandardScaler().fit(X_tr)
        est = make_estimator()
        est.fit(scaler.transform(X_tr), y_tr)
        pred = np.asarray(est.predict(scaler.transform(X_te))).ravel()
        scores.append(float(r2_score(y_te, pred)))
    return scores


def one_se_selection(
    complexities: Sequence[float],
    means: Sequence[float],
    ses: Sequence[float],
) -> float:
    """Select the simplest complexity within 1 SE of the best mean score.

    The "one-standard-error rule": find the complexity with the best mean CV
    score, then choose the SIMPLEST (smallest) complexity whose mean is within
    one standard error of that best. This prefers parsimony without ever
    inspecting the held-out test set -- the principled fix for the fact that
    validation cannot distinguish the robust low-complexity model from the
    regime-overfit high-complexity one.

    Args:
        complexities: Candidate complexity values, ASCENDING (e.g. 1..K).
        means: CV mean score per complexity (higher is better).
        ses: CV standard error per complexity.

    Returns:
        The selected (parsimonious) complexity value.

    Raises:
        ValueError: If inputs are empty or of mismatched length.
    """
    if not (len(complexities) == len(means) == len(ses)):
        raise ValueError("complexities, means, ses must have equal length.")
    if len(complexities) == 0:
        raise ValueError("No complexities provided.")
    best_i = int(np.argmax(means))
    threshold = means[best_i] - ses[best_i]
    for c, m in zip(complexities, means, strict=True):
        if m >= threshold:
            return c
    return complexities[best_i]


def mean_se(scores: Sequence[float]) -> tuple[float, float]:
    """Return (mean, standard error) of a list of fold scores."""
    arr = np.asarray(scores, dtype=float)
    n = len(arr)
    if n == 0:
        return float("nan"), float("nan")
    mean = float(arr.mean())
    se = float(arr.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    return mean, se
