"""Distribution-free conformal prediction intervals for the IPIS soft sensor (Phase 1D).

Each construction is implemented directly from its primary source (registered in
``docs/sources/source-map.md``) rather than via a third-party wrapper, so the
finite-sample behaviour is transparent and unit-testable against the published
coverage guarantees.

Methods
-------
- ``split_conformal_halfwidth`` / ``SplitConformal`` -- inductive (split) CP,
  Papadopoulos et al. 2002; Vovk et al. 2005. Single calibration pass; the
  ``ceil((1 - alpha)(n + 1))``-th order statistic of the calibration scores.
  Exchangeability-dependent -> the deliberately-weak baseline that *under-covers*
  under regime drift.
- ``enbpi_offsets`` / ``EnbPI`` -- Ensemble Batch Prediction Intervals,
  Xu & Xie 2021 (ICML), Algorithm 1. Bootstrap LOO-ensemble residuals, a
  width-minimising offset ``beta_hat in [0, alpha]``, and a FIFO residual update
  every ``s`` steps. No exchangeability assumption; ``B`` model fits (vs ``B*T``
  for jackknife+, Barber et al. 2021).
- ``aci_step`` / ``ACIConformal`` -- Adaptive Conformal Inference,
  Gibbs & Candes 2021, Eq. (4): ``alpha_{t+1} = alpha_t + gamma * (alpha - err_t)``
  over a sliding score window. Maintains long-run coverage under *arbitrary*
  distribution shift by tuning the score-quantile online. ``select_gamma`` grids
  the published candidate set; full DtACI (2024, Algorithm 1) is a documented
  follow-up, not implemented here.

Diagnostics
-----------
``marginal_coverage``, ``rolling_coverage``, ``mean_interval_width`` -- the online
validation instruments the Phase 1D conformal debt requires (coverage validated
*online*, not only marginally).

All functions are model-agnostic: they consume point predictions and residual
sequences, so they compose with the as-built physics-anchored linear soft sensor
(ADR-007) and the Shardt open-loop bias-update (ADR-008) without retraining.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable, Sequence

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

# A fit-predict callable: fit on (X_train, y_train) and return predictions at X_eval.
# Injected so this module stays dependency-free and testable with a closure.
FitPredictFn = Callable[[FloatArray, FloatArray, FloatArray], FloatArray]


# --------------------------------------------------------------------------- #
# Finite-sample conformal quantile                                            #
# --------------------------------------------------------------------------- #
def conformal_quantile(scores: Sequence[float] | FloatArray, level: float) -> float:
    """Finite-sample conformal quantile of ``scores`` at coverage ``level``.

    Returns the ``ceil(level * (n + 1))``-th smallest score (1-indexed). This is
    the split-conformal rule (Papadopoulos 2002; Vovk 2005): with ``level = 1 -
    alpha`` it yields marginal coverage ``>= 1 - alpha`` under exchangeability.

    Edge cases follow the conformal convention:
      - ``level >= 1`` (or rank ``> n``) -> ``+inf`` (interval = whole line).
      - ``level <= 0`` -> ``0.0`` (degenerate empty/point interval).
    """
    s = np.sort(np.asarray(scores, dtype=np.float64))
    n = s.size
    if n == 0:
        raise ValueError("conformal_quantile requires at least one score")
    if level >= 1.0:
        return math.inf
    if level <= 0.0:
        return 0.0
    rank = math.ceil(level * (n + 1))  # 1-indexed
    if rank > n:
        return math.inf
    return float(s[rank - 1])


# --------------------------------------------------------------------------- #
# Split / inductive conformal (baseline)                                      #
# --------------------------------------------------------------------------- #
def split_conformal_halfwidth(calib_residuals: FloatArray, alpha: float) -> float:
    """Symmetric split-conformal half-width from calibration residuals.

    Half-width is the ``1 - alpha`` conformal quantile of the *absolute*
    calibration residuals. Interval at a test point is ``y_hat +/- halfwidth``.
    """
    return conformal_quantile(np.abs(np.asarray(calib_residuals, np.float64)), 1.0 - alpha)


class SplitConformal:
    """Static split-conformal interval calibrated once (the drift-blind baseline)."""

    def __init__(self, calib_residuals: FloatArray, alpha: float = 0.1) -> None:
        self.alpha = float(alpha)
        self.halfwidth = split_conformal_halfwidth(calib_residuals, alpha)

    def interval(self, y_pred: FloatArray) -> tuple[FloatArray, FloatArray]:
        y_pred = np.asarray(y_pred, np.float64)
        return y_pred - self.halfwidth, y_pred + self.halfwidth


class NormalizedOneSidedConformal:
    """Locally-adaptive one-sided upper conformal bound (Lei 2018, normalized).

    For a one-sided spec ``y <= s`` we need an UPPER bound ``U(x)`` with
    ``P(y <= U) >= 1 - alpha``, then enforce ``U <= s``. Two ingredients make
    the bound *heteroscedastic* — the property that lets it beat a fixed margin:

      - signed nonconformity ``e_i = y_i - y_hat_i`` (an *upper* bound uses the
        signed residual, not |e|, so it is tighter than a two-sided half-width
        for free when the mean model is roughly unbiased);
      - a local scale ``sigma_hat(x_i) > 0`` (a model of the conditional residual
        magnitude). The score is ``s_i = e_i / sigma_hat(x_i)`` and the bound is
        ``U(x) = y_hat(x) + sigma_hat(x) * q`` with ``q`` the ``1 - alpha``
        conformal quantile of the scores. Width ``= sigma_hat(x) * q`` scales
        with the local uncertainty: tight where the sensor is sharp, wide near
        the cliff / outside the calibrated envelope.

    With constant ``sigma_hat`` this reduces to a one-sided split-conformal
    bound (the constant-width baseline) — so the heteroscedasticity, hence any
    advantage over a fixed margin, comes entirely from a non-constant scale.
    """

    def __init__(
        self,
        calib_residuals: FloatArray,
        calib_scales: FloatArray,
        alpha: float = 0.1,
    ) -> None:
        e = np.asarray(calib_residuals, np.float64)
        sig = np.asarray(calib_scales, np.float64)
        if e.shape != sig.shape:
            raise ValueError("residuals and scales must have the same shape")
        if np.any(sig <= 0.0):
            raise ValueError("scales must be strictly positive")
        self.alpha = float(alpha)
        self.q = conformal_quantile(e / sig, 1.0 - alpha)  # signed -> one-sided

    def upper_halfwidth(self, scale: FloatArray) -> FloatArray:
        """Back-off ``C+ = scale * q`` at a test point's local scale."""
        return np.asarray(scale, np.float64) * self.q

    def upper_bound(self, y_pred: FloatArray, scale: FloatArray) -> FloatArray:
        """Upper confidence bound ``U = y_hat + scale * q``."""
        return np.asarray(y_pred, np.float64) + self.upper_halfwidth(scale)


# --------------------------------------------------------------------------- #
# EnbPI -- Ensemble Batch Prediction Intervals (Xu & Xie 2021, Algorithm 1)    #
# --------------------------------------------------------------------------- #
def enbpi_offsets(residuals: FloatArray, alpha: float, n_grid: int = 51) -> tuple[float, float]:
    """Width-minimising (lower, upper) offsets for EnbPI from a *signed* residual set.

    Implements lines 13-15 of Algorithm 1:
        beta_hat = argmin_{beta in [0, alpha]} [ q(1 - alpha + beta) - q(beta) ]
        (w_lower, w_upper) = ( q(beta_hat), q(1 - alpha + beta_hat) )
    where ``q(p)`` is the empirical ``p``-quantile of the residual set. Offsets are
    added to the point prediction, so ``w_lower`` is typically negative.
    """
    r = np.asarray(residuals, np.float64)
    betas = np.linspace(0.0, alpha, n_grid)
    lo_q = np.quantile(r, betas, method="higher")
    hi_q = np.quantile(r, np.clip(1.0 - alpha + betas, 0.0, 1.0), method="higher")
    j = int(np.argmin(hi_q - lo_q))
    return float(lo_q[j]), float(hi_q[j])


class EnbPI:
    """EnbPI runner (Xu & Xie 2021, Algorithm 1).

    Pre-trains ``B`` bootstrap models once; builds LOO-ensemble residuals; serves
    sequential intervals and refreshes the residual buffer FIFO every ``s`` steps
    as labels arrive. ``fit_predict`` is injected (model-agnostic, testable).

    Parameters
    ----------
    fit_predict : FitPredictFn
        ``(X_train, y_train, X_eval) -> y_eval_pred``.
    alpha : float
        Target miscoverage (coverage ``1 - alpha``).
    B : int
        Number of bootstrap models.
    s : int
        Batch size for the FIFO residual refresh (Algorithm 1, lines 17-22).
    phi : callable
        Aggregation over the ensemble; mean by default (paper default).
    """

    def __init__(
        self,
        fit_predict: FitPredictFn,
        alpha: float = 0.1,
        B: int = 30,
        s: int = 1,
        phi: Callable[[FloatArray], FloatArray] | None = None,
        random_state: int | None = None,
    ) -> None:
        self.fit_predict = fit_predict
        self.alpha = float(alpha)
        self.B = int(B)
        self.s = int(s)
        self.phi = phi or (lambda a: np.mean(a, axis=0))
        self.rng = np.random.default_rng(random_state)
        self._fitted = False

    def fit(self, X_train: FloatArray, y_train: FloatArray) -> EnbPI:
        X_train = np.asarray(X_train, np.float64)
        y_train = np.asarray(y_train, np.float64)
        n = y_train.shape[0]
        self._Xtr, self._ytr = X_train, y_train

        # Bootstrap index sets and per-bag predictors (Algorithm 1, lines 1-4).
        self._bags: list[NDArray[np.intp]] = [
            self.rng.integers(0, n, size=n) for _ in range(self.B)
        ]
        # LOO membership: for each training i, which bags excluded it.
        self._loo_resid = np.empty(n, dtype=np.float64)
        # Cache per-bag predictions on the training set to assemble LOO means.
        bag_train_pred = np.empty((self.B, n), dtype=np.float64)
        for b, idx in enumerate(self._bags):
            bag_train_pred[b] = self.fit_predict(X_train[idx], y_train[idx], X_train)
        # Which bags exclude i (vectorised membership test).
        self._excludes_i = np.array(
            [[i not in set(idx.tolist()) for idx in self._bags] for i in range(n)]
        )  # shape (n, B); n is small (~2k) so this is fine
        for i in range(n):
            mask = self._excludes_i[i]
            if not mask.any():  # every bag contained i (rare); fall back to all bags
                mask = np.ones(self.B, dtype=bool)
            loo_pred_i = self.phi(bag_train_pred[mask, i : i + 1])[0]
            self._loo_resid[i] = y_train[i] - loo_pred_i  # signed residual (line 8)
        self._resid = deque(self._loo_resid.tolist(), maxlen=n)
        self._fitted = True
        return self

    def _loo_predict(self, X_eval: FloatArray) -> FloatArray:
        """phi over the T LOO predictors at X_eval (Algorithm 1, line 12)."""
        n = self._ytr.shape[0]
        bag_eval = np.array(
            [self.fit_predict(self._Xtr[idx], self._ytr[idx], X_eval) for idx in self._bags]
        )  # (B, m)
        loo_preds = np.empty((n, X_eval.shape[0]), dtype=np.float64)
        for i in range(n):
            mask = self._excludes_i[i]
            if not mask.any():
                mask = np.ones(self.B, dtype=bool)
            loo_preds[i] = self.phi(bag_eval[mask])
        return self.phi(loo_preds)

    def predict_interval(
        self, X_test: FloatArray, y_test: FloatArray
    ) -> tuple[FloatArray, FloatArray, FloatArray]:
        """Sequential intervals over the test block; ``y_test`` revealed as feedback.

        Returns ``(point, lower, upper)``. ``y_test[t]`` is only used *after* the
        interval at ``t`` is emitted (online protocol), then folded into the FIFO
        residual buffer every ``s`` steps (lines 17-22).
        """
        if not self._fitted:
            raise RuntimeError("call fit() before predict_interval()")
        X_test = np.asarray(X_test, np.float64)
        y_test = np.asarray(y_test, np.float64)
        m = X_test.shape[0]
        point = self._loo_predict(X_test)
        lower = np.empty(m, np.float64)
        upper = np.empty(m, np.float64)
        pending: list[float] = []
        for t in range(m):
            w_lo, w_hi = enbpi_offsets(np.asarray(self._resid), self.alpha)
            lower[t], upper[t] = point[t] + w_lo, point[t] + w_hi
            pending.append(y_test[t] - point[t])  # signed residual from revealed label
            if (t + 1) % self.s == 0:  # FIFO refresh in batches of s
                for r in pending:
                    self._resid.append(r)
                pending.clear()
        return point, lower, upper


# --------------------------------------------------------------------------- #
# ACI -- Adaptive Conformal Inference (Gibbs & Candes 2021, Eq. 4)             #
# --------------------------------------------------------------------------- #
def aci_step(alpha_t: float, covered: bool, gamma: float, target_alpha: float) -> float:
    """One ACI update (Eq. 4): ``alpha_{t+1} = alpha_t + gamma * (target - err_t)``.

    ``err_t = 0`` if the realised value was covered, else ``1``. ``alpha_t`` is not
    hard-clipped to [0, 1]; the score-quantile handles the extremes (level >= 1 ->
    whole line, level <= 0 -> point), matching the paper.
    """
    err = 0.0 if covered else 1.0
    return alpha_t + gamma * (target_alpha - err)


class ACIConformal:
    """Online adaptive-conformal interval over a sliding score window.

    Deployment loop (matches a FastAPI serving endpoint):
        1. ``interval(point_pred)`` -> (lower, upper) using current ``alpha_t``.
        2. later, when the lab/analyzer label arrives, ``update(point_pred, y_true)``
           appends the score and applies the ACI step.

    Parameters
    ----------
    init_residuals : array
        Calibration residuals to seed the score window (offline calibration block).
    alpha : float
        Target miscoverage.
    gamma : float
        ACI step size (Gibbs & Candes default grid via ``select_gamma``).
    window : int | None
        Sliding window ``r`` of recent conformity scores; ``None`` = expanding
        (standard conformal uses ``r = t``). A finite window tracks drift faster.
    """

    def __init__(
        self,
        init_residuals: FloatArray,
        alpha: float = 0.1,
        gamma: float = 0.05,
        window: int | None = None,
    ) -> None:
        self.target_alpha = float(alpha)
        self.alpha_t = float(alpha)
        self.gamma = float(gamma)
        scores = np.abs(np.asarray(init_residuals, np.float64)).tolist()
        self.scores: deque[float] = deque(scores, maxlen=window)
        self._last_halfwidth = self._halfwidth()

    def _halfwidth(self) -> float:
        return conformal_quantile(np.asarray(self.scores), 1.0 - self.alpha_t)

    def interval(self, y_pred: FloatArray) -> tuple[FloatArray, FloatArray]:
        hw = self._halfwidth()
        self._last_halfwidth = hw
        y_pred = np.asarray(y_pred, np.float64)
        return y_pred - hw, y_pred + hw

    def update(self, y_pred: float, y_true: float) -> None:
        score = abs(float(y_true) - float(y_pred))
        covered = score <= self._last_halfwidth
        self.alpha_t = aci_step(self.alpha_t, covered, self.gamma, self.target_alpha)
        self.scores.append(score)

    def run(
        self, y_pred: FloatArray, y_true: FloatArray
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        """Convenience batch driver. Returns ``(lower, upper, covered, alpha_trace)``."""
        y_pred = np.asarray(y_pred, np.float64)
        y_true = np.asarray(y_true, np.float64)
        m = y_pred.shape[0]
        lo = np.empty(m, np.float64)
        hi = np.empty(m, np.float64)
        cov = np.empty(m, bool)
        atrace = np.empty(m, np.float64)
        for t in range(m):
            lo[t], hi[t] = self.interval(y_pred[t])
            cov[t] = lo[t] <= y_true[t] <= hi[t]
            atrace[t] = self.alpha_t
            self.update(float(y_pred[t]), float(y_true[t]))
        return lo, hi, cov, atrace


# Published DtACI candidate step-size grid (Gibbs & Candes 2024, Sec. 4).
ACI_GAMMA_GRID: tuple[float, ...] = (0.001, 0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128)


def select_gamma(
    y_pred: FloatArray,
    y_true: FloatArray,
    init_residuals: FloatArray,
    alpha: float = 0.1,
    window: int | None = None,
    grid: Sequence[float] = ACI_GAMMA_GRID,
) -> float:
    """Pick the ACI step size from ``grid`` minimising |marginal coverage - (1 - alpha)|.

    A lightweight, fully-verified stand-in for full DtACI online tuning: run ACI on
    a calibration stream for each candidate gamma and keep the best. Ties broken by
    the narrower mean interval (favour tighter intervals at equal coverage).
    """
    best_gamma, best_err, best_width = grid[0], math.inf, math.inf
    for g in grid:
        aci = ACIConformal(init_residuals, alpha=alpha, gamma=g, window=window)
        lo, hi, cov, _ = aci.run(y_pred, y_true)
        err = abs(marginal_coverage(cov) - (1.0 - alpha))
        width = mean_interval_width(lo, hi)
        if err < best_err - 1e-9 or (abs(err - best_err) <= 1e-9 and width < best_width):
            best_gamma, best_err, best_width = g, err, width
    return best_gamma


# --------------------------------------------------------------------------- #
# Coverage / width diagnostics (online validation instrument)                 #
# --------------------------------------------------------------------------- #
def marginal_coverage(covered: NDArray[np.bool_]) -> float:
    """Overall empirical coverage rate."""
    c = np.asarray(covered, dtype=bool)
    return float(c.mean()) if c.size else math.nan


def rolling_coverage(covered: NDArray[np.bool_], window: int = 100) -> FloatArray:
    """Trailing-window empirical coverage (the online validation curve).

    Element ``t`` is the mean coverage over the most recent ``min(t + 1, window)``
    points. This is what a dashboard plots to show coverage holding under drift.
    """
    c = np.asarray(covered, dtype=np.float64)
    if c.size == 0:
        return c
    csum = np.cumsum(c)
    out = np.empty_like(c)
    for t in range(c.size):
        lo = max(0, t - window + 1)
        total = csum[t] - (csum[lo - 1] if lo > 0 else 0.0)
        out[t] = total / (t - lo + 1)
    return out


def mean_interval_width(lower: FloatArray, upper: FloatArray) -> float:
    """Mean interval width (ignores non-finite widths from degenerate quantiles)."""
    w = np.asarray(upper, np.float64) - np.asarray(lower, np.float64)
    finite = w[np.isfinite(w)]
    return float(finite.mean()) if finite.size else math.inf
