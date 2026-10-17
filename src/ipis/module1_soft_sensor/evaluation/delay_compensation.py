"""Delay compensation for conformal soft sensors (IPIS M1, proposed claim N1'').

When laboratory labels arrive theta calibrator updates late, adaptive conformal calibration is an
integral loop with dead time theta (``delayed_aci``). Process residuals are persistent, so the miss
process that drives the loop is persistent too, and the loop issues unusable intervals that marginal
coverage cannot reveal. Process control answers dead time in two ways. The Smith predictor takes the
dead time out of the loop (the ``smith`` loop of ``delayed_aci``). Minimum-variance control (Astrom
1970) predicts the disturbance over the dead time; its output variance is the (dead time + 1)-step
prediction-error variance of the disturbance, which Harris (1989) made the benchmark of
control-performance assessment. This module applies the second idea.

Applied to a soft sensor:
- a direct (theta + 1)-step predictor of the residual, built from labels available at issue time,
  shifts the interval centre;
- the conformal loop then calibrates only the prediction error;
- the ratio of the compensated to the uncompensated interval width is predicted from the residual
  autocorrelation alone (``predicted_width_ratio``).

The predictor is open-loop: it is driven by labelled residuals only, never by its own output or by
the calibration loop. Its coefficients stay fixed after ``fit_direct_forecaster``; they do not
adapt online.

Timing is the same as ``delayed_aci``: the interval for sample t is issued from the labels of
samples s <= t - theta - 1, so the forecast horizon is h = theta + 1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class DirectForecaster:
    """Least-squares direct h-step predictor r_t ~ c + sum_j b_j r_{t-h-j}, j = 0..order-1."""

    horizon: int
    order: int
    coef: np.ndarray  # intercept first, then b_0 .. b_{order-1}
    n_fit: int

    @property
    def warmup(self) -> int:
        """First index t with a prediction: t - h - order + 1 >= 0."""
        return self.horizon + self.order - 1

    def predict(self, r: ArrayLike) -> np.ndarray:
        """Predictions for every t >= warmup (NaN before); uses r_s only for s <= t - h."""
        r = np.asarray(r, dtype=np.float64)
        out = np.full(r.size, np.nan)
        idx = np.arange(self.warmup, r.size)
        if idx.size:
            out[idx] = _design(r, idx, self.horizon, self.order) @ self.coef
        return out


def _design(r: np.ndarray, idx: np.ndarray, horizon: int, order: int) -> np.ndarray:
    cols = [np.ones(idx.size)] + [r[idx - horizon - j] for j in range(order)]
    return np.column_stack(cols)


def _targets(r: np.ndarray, horizon: int, order: int, fit: slice | None) -> np.ndarray:
    start, stop, _ = (fit or slice(None)).indices(r.size)
    return np.arange(max(start, horizon + order - 1), stop)


def fit_direct_forecaster(
    r: ArrayLike, theta: int, order: int = 3, fit: slice | None = None
) -> DirectForecaster:
    """Fit the direct (theta + 1)-step residual predictor on the targets r_t with t in ``fit``.

    ``fit`` defaults to every row. Features may reach back before ``fit.start``; they must be
    labelled history, never future rows.
    """
    if theta < 0 or order < 1:
        raise ValueError("theta must be >= 0 and order >= 1")
    r = np.asarray(r, dtype=np.float64)
    h = theta + 1
    idx = _targets(r, h, order, fit)
    if idx.size <= order + 1:
        raise ValueError("too few targets to fit the forecaster")
    coef, *_ = np.linalg.lstsq(_design(r, idx, h, order), r[idx], rcond=None)
    return DirectForecaster(horizon=h, order=order, coef=coef, n_fit=int(idx.size))


def select_order(r: ArrayLike, theta: int, max_order: int = 10, fit: slice | None = None) -> int:
    """Order with the smallest BIC of the direct regression on a common target set."""
    r = np.asarray(r, dtype=np.float64)
    h = theta + 1
    idx = _targets(r, h, max_order, fit)  # the same targets for every candidate order
    n = idx.size
    best, best_bic = 1, math.inf
    for p in range(1, max_order + 1):
        x = _design(r, idx, h, p)
        coef, *_ = np.linalg.lstsq(x, r[idx], rcond=None)
        rss = float(np.sum((r[idx] - x @ coef) ** 2))
        bic = n * math.log(rss / n) + (p + 1) * math.log(n)
        if bic < best_bic:
            best, best_bic = p, bic
    return best


def predicted_width_ratio(acf: ArrayLike, theta: int, order: int) -> float:
    """Width of compensated over uncompensated intervals implied by an autocorrelation sequence.

    The best linear predictor of r_t from r_{t-h}, ..., r_{t-h-order+1} (h = theta + 1) leaves
    the error-variance fraction 1 - c' R^{-1} c, with c_j = rho_{h+j} and R_jk = rho_|j-k|. Its
    square root is the ratio of standard deviations. It equals the ratio of interval widths when
    the prediction error and the residual share one standardized distribution, as for Gaussian
    residuals; otherwise the width ratio can differ. For an AR(1) of coefficient phi the fraction
    is 1 - phi^(2h) at every order.

    ``acf`` holds rho_0 = 1, rho_1, ...; at least h + order lags are needed.
    """
    rho = np.asarray(acf, dtype=np.float64)
    h = theta + 1
    if rho.size < h + order:
        raise ValueError(f"need autocorrelations up to lag {h + order - 1}")
    big_r = np.array([[rho[abs(j - k)] for k in range(order)] for j in range(order)])
    c = rho[h : h + order]
    explained = float(c @ np.linalg.solve(big_r, c))
    return math.sqrt(max(0.0, 1.0 - explained))
