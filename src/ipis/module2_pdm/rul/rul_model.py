"""RUL regression on the degradation index, with a one-sided lower bound (Phase 2B).

Pipeline (degradation phase, t >= FPT):
  features  : [log1p(DI), DI_slope]  -- level and causal rate of the monotone
              degradation index (degradation.py). log1p tames the ~5-decade T^2
              dynamic range; the slope distinguishes fast vs slow degradation at a
              given level.
  regressor : any sklearn-style estimator (default LinearRegression).
  bound     : one-sided LOWER conformal bound L(x) with P(RUL >= L) >= 1 - alpha.
              For maintenance this is the safe quantity -- the bearing lasts at
              least L with high confidence -- so the bound is conservative by design.

The lower bound reuses the finite-sample conformal quantile from Module 1
(evaluation.conformal): with signed residual r = y_true - y_pred,
    L = y_pred - conformal_quantile(y_pred - y_true, 1 - alpha)
=> P(y_pred - y_true <= q) >= 1 - alpha => P(y_true >= y_pred - q) >= 1 - alpha.

Headline metric: PHM-2012 asymmetric score (Nectoux 2012). Late predictions
(RUL overestimate) are penalized ~4x harder than early ones: a 5% late estimate
and a 20% early estimate both score 0.5; a perfect estimate scores 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.base import RegressorMixin
from sklearn.linear_model import LinearRegression

from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile

_LN_HALF = np.log(0.5)


def rul_feature_matrix(di: np.ndarray) -> np.ndarray:
    """Features [log1p(DI), slope] from a degradation-index series (causal slope)."""
    di = np.asarray(di, dtype=float).ravel()
    level = np.log1p(np.maximum(di, 0.0))
    slope = np.empty_like(level)
    slope[0] = 0.0
    slope[1:] = np.diff(level)  # backward difference -> causal
    return np.column_stack([level, slope])


def phm2012_score(rul_pred: np.ndarray, rul_true: np.ndarray) -> float:
    """Mean PHM-2012 asymmetric score in (0, 1]; points with rul_true<=0 skipped."""
    p = np.asarray(rul_pred, dtype=float).ravel()
    t = np.asarray(rul_true, dtype=float).ravel()
    m = t > 0.0
    if not np.any(m):
        raise ValueError("phm2012_score needs at least one point with rul_true > 0")
    p, t = p[m], t[m]
    er = 100.0 * (t - p) / t  # >0 early (under-estimate), <=0 late (over-estimate)
    a = np.where(er <= 0.0, np.exp(-_LN_HALF * er / 5.0), np.exp(_LN_HALF * er / 20.0))
    return float(np.mean(a))


@dataclass
class RULModel:
    """RUL regressor on degradation-index features + one-sided lower conformal bound."""

    regressor: RegressorMixin
    alpha: float = 0.1
    _q: float = 0.0  # conformal back-off (fitted)

    @classmethod
    def fit(
        cls,
        di_train: np.ndarray,
        rul_train: np.ndarray,
        alpha: float = 0.1,
        regressor: RegressorMixin | None = None,
        di_calib: np.ndarray | None = None,
        rul_calib: np.ndarray | None = None,
    ) -> RULModel:
        """Fit the regressor; calibrate the lower bound on a held-out split if given.

        If no calibration split is supplied, residuals are taken on the training
        data (optimistic -- prefer a real split, e.g. a held-out bearing).
        """
        reg = regressor if regressor is not None else LinearRegression()
        reg.fit(rul_feature_matrix(di_train), np.asarray(rul_train, float).ravel())
        model = cls(regressor=reg, alpha=float(alpha))
        if di_calib is not None and rul_calib is not None:
            cal_pred = model.predict(di_calib)
            model._q = conformal_quantile(
                cal_pred - np.asarray(rul_calib, float).ravel(), 1.0 - alpha
            )
        else:
            tr_pred = model.predict(di_train)
            model._q = conformal_quantile(
                tr_pred - np.asarray(rul_train, float).ravel(), 1.0 - alpha
            )
        return model

    def predict(self, di: np.ndarray) -> np.ndarray:
        """Point RUL prediction (clipped at 0)."""
        pred = self.regressor.predict(rul_feature_matrix(di))
        return np.maximum(pred, 0.0)

    def lower_bound(self, di: np.ndarray) -> np.ndarray:
        """One-sided lower confidence bound L with P(RUL >= L) >= 1 - alpha."""
        return np.maximum(self.predict(di) - self._q, 0.0)


def lower_bound_coverage(rul_true: np.ndarray, lower: np.ndarray) -> float:
    """Empirical P(RUL_true >= L): should be >= 1 - alpha if calibrated."""
    t = np.asarray(rul_true, float).ravel()
    lo = np.asarray(lower, float).ravel()
    return float(np.mean(t >= lo))
