"""Point models of N1 Phase 1 (pre-registration Sections 5.1 and 5.2).

- Debutanizer (D-P0.1): OLS of y_t on u5_{t-15}, fitted on the training rows. The coefficients
  must equal those of the training-split pre-check (``phase1_precheck.json``).
- TEP: ridge regression of y_t on the 34 inputs (XMEAS 1-22, XMV 1-12) 15 min earlier, fitted
  per run on T1's training rows (3-min rows, inputs lagged 5 rows). The model has no row
  dynamics, so every arm applies the same fitted model with the lag in its own rows (15 at
  1 min): within the dataset every arm shares the point model and the residual stream
  (Section 7). The protocol does not fix the penalty. Bien decided on 2026-10-29, before any
  Phase 1 data:
  the inputs are standardised on the training rows and the penalty is chosen by the one-SE rule
  over 13 values from 1e-3 to 1e3, with 5 contiguous folds of the training rows (as D-P0.1's
  one-SE rule): the largest penalty whose mean held-out MSE is within one standard error of the
  smallest.
- TEP, the estimator-class check (R1.1, R1.4): gradient boosting on the same inputs and rows,
  scikit-learn ``GradientBoostingRegressor`` with its default settings and random_state 0.

A model predicts the label of row t from the inputs of row t - lag, so a residual exists for
t >= lag. Residual streams are written as full-length arrays with NaN before the first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

RIDGE_ALPHAS = tuple(float(a) for a in np.logspace(-3, 3, 13))
RIDGE_FOLDS = 5


@dataclass(frozen=True)
class OLSLag:
    """y_t = b0 + b1 u_{t-lag}."""

    lag: int
    intercept: float
    slope: float

    def residuals(self, u: np.ndarray, y: np.ndarray) -> np.ndarray:
        r = np.full(y.size, np.nan)
        r[self.lag :] = y[self.lag :] - (self.intercept + self.slope * u[: -self.lag])
        return r


def fit_ols_lag(u: np.ndarray, y: np.ndarray, lag: int) -> OLSLag:
    """Least squares on the training rows, as in ``scripts/phase1_precheck.py``."""
    x = np.asarray(u, dtype=float)[:-lag]
    t = np.asarray(y, dtype=float)[lag:]
    design = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(design, t, rcond=None)
    return OLSLag(lag=lag, intercept=float(beta[0]), slope=float(beta[1]))


def lagged_pairs(
    X: np.ndarray, y: np.ndarray, lag: int, stop: int
) -> tuple[np.ndarray, np.ndarray]:
    """Training pairs (inputs of row t - lag, label of row t) for lag <= t < stop."""
    t = np.arange(lag, stop)
    return X[t - lag], y[t]


@dataclass
class TepModel:
    """A fitted TEP point model with its inputs lagged by ``lag`` rows."""

    kind: str  # "ridge" or "gb"
    lag: int
    model: Any
    info: dict[str, Any] = field(default_factory=dict)

    def residuals(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        r = np.full(y.size, np.nan)
        r[self.lag :] = y[self.lag :] - self.model.predict(X[: -self.lag])
        return r

    def at_lag(self, lag: int) -> TepModel:
        """The same fitted model at rows of another cadence, its inputs ``lag`` rows back."""
        return TepModel(kind=self.kind, lag=lag, model=self.model, info=self.info)

    def staged_residuals(self, X: np.ndarray, y: np.ndarray, n_a: int) -> np.ndarray:
        """``residuals`` with rows 0..n_a-1 computed by one call on those rows alone, as stage A
        computes them, and the later rows by a second call. A matrix product can differ in its
        last bit with the size of the matrix it is computed in; this way stage B reproduces stage
        A's calibration residuals bit for bit."""
        r = np.full(y.size, np.nan)
        r[:n_a] = self.residuals(X[:n_a], y[:n_a])
        if y.size > n_a:
            r[n_a:] = y[n_a:] - self.model.predict(X[n_a - self.lag : y.size - self.lag])
        return r


def _ridge(alpha: float) -> Any:
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), Ridge(alpha=alpha))


def fit_ridge_one_se(
    X: np.ndarray,
    y: np.ndarray,
    lag: int,
    n_train: int,
    alphas: tuple[float, ...] = RIDGE_ALPHAS,
    n_folds: int = RIDGE_FOLDS,
) -> TepModel:
    """Ridge with the penalty of the one-SE rule over contiguous folds of the training rows.

    The scaler is fitted inside each fold's training part, and again on all training rows for
    the final model. Ties in the smallest mean MSE go to the smaller penalty.
    """
    Xt, yt = lagged_pairs(X, y, lag, n_train)
    folds = np.array_split(np.arange(yt.size), n_folds)
    mse = np.empty((len(alphas), n_folds))
    for a, alpha in enumerate(alphas):
        for k, test in enumerate(folds):
            train = np.setdiff1d(np.arange(yt.size), test)
            model = _ridge(alpha).fit(Xt[train], yt[train])
            mse[a, k] = float(np.mean((yt[test] - model.predict(Xt[test])) ** 2))
    mean = mse.mean(axis=1)
    se = mse.std(axis=1, ddof=1) / np.sqrt(n_folds)
    best = int(np.argmin(mean))
    within = [a for a in range(len(alphas)) if mean[a] <= mean[best] + se[best]]
    chosen = max(within)
    model = _ridge(alphas[chosen]).fit(Xt, yt)
    info = {
        "alpha": float(alphas[chosen]),
        "alpha_min_mse": float(alphas[best]),
        "cv_mean_mse": [float(v) for v in mean],
        "cv_se": [float(v) for v in se],
        "n_train_pairs": int(yt.size),
        "intercept": float(model[-1].intercept_),
        "coef_standardised": [float(c) for c in model[-1].coef_],
    }
    return TepModel(kind="ridge", lag=lag, model=model, info=info)


def fit_gradient_boosting(X: np.ndarray, y: np.ndarray, lag: int, n_train: int) -> TepModel:
    """scikit-learn's default gradient boosting, random_state 0, on the training pairs."""
    from sklearn.ensemble import GradientBoostingRegressor

    Xt, yt = lagged_pairs(X, y, lag, n_train)
    model = GradientBoostingRegressor(random_state=0).fit(Xt, yt)
    return TepModel(kind="gb", lag=lag, model=model, info={"n_train_pairs": int(yt.size)})
