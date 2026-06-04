"""Luo (2015) matrix scale-bias correction -- the middle-ground migration method.

Verified against the primary: Luo, Yao & Gao (2015), Chem. Eng. Sci. 134, 23-35.
Their migration model (Eq. 7), least-squares form (Eq. 12):

    y(x) = rho_1 * z(rho_0 . x + lambda_0) + lambda_1 + eps

where z(.) is the source-model predictor, rho_0 = diag(rho_{0,1..d}) is a diagonal
matrix of PER-INPUT slope parameters and lambda_0 the vector of per-input biases
(the input transformation x~ = rho_0 . x + lambda_0), and rho_1, lambda_1 are the
scalar output slope/bias. theta = [rho_1, lambda_1, rho_0(d), lambda_0(d)], size
2d+2, fit by least squares. (Luo's Bayesian normal-inverse-gamma + MCMC layer is
their refinement for prior incorporation + uncertainty; the least-squares core is
implemented here as the canonical middle ground between OSBC and Yan.)

This is more expressive than Lu OSBC (which scales the OUTPUT only, 2 scalars) and
cheaper than Yan's functional GP. Unlike OSBC/Yan, Luo evaluates the source model
at TRANSFORMED inputs, so it needs a `source_fn` callable (built-feature matrix ->
source prediction), not just the precomputed source predictions.

NOTE (applicability): for a LINEAR source model z, z(rho_0.x+lambda_0) is linear in
x with per-input coefficients rho_1*w_k*rho_{0,k}; since the source weights w_k are
fixed and nonzero, rho_0 can realize ANY linear map -- so Luo collapses to
from-scratch linear regression and the migration benefit is lost. Luo's input
re-scaling is meaningful only for a NONLINEAR source. This is verified empirically
in the Phase-1C sweep (Luo ~= from-scratch on the linear physics-anchored source).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.optimize import least_squares

SourceFn = Callable[[np.ndarray], np.ndarray]  # built features -> source prediction


class LuoMatrixSBC:
    """Luo (2015) matrix scale-bias correction, least-squares (Eq. 7 / Eq. 12)."""

    def __init__(self, max_nfev: int = 2000) -> None:
        self.max_nfev = max_nfev
        self.theta_: np.ndarray | None = None
        self.d_: int | None = None
        self._source_fn: SourceFn | None = None

    def _eta(self, theta: np.ndarray, X: np.ndarray, source_fn: SourceFn) -> np.ndarray:
        d = X.shape[1]
        rho1, lam1 = theta[0], theta[1]
        rho0 = theta[2 : 2 + d]
        lam0 = theta[2 + d : 2 + 2 * d]
        x_t = rho0 * X + lam0  # per-input affine transform
        return rho1 * np.asarray(source_fn(x_t), dtype=float).ravel() + lam1

    def fit(
        self,
        X: np.ndarray,
        source_pred: np.ndarray,  # unused (Luo re-evaluates z at transformed inputs)
        y: np.ndarray,
        source_fn: SourceFn | None = None,
    ) -> LuoMatrixSBC:
        if source_fn is None:
            raise ValueError(
                "LuoMatrixSBC requires source_fn (source model on transformed inputs)."
            )
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        if X.shape[0] != y.shape[0]:
            raise ValueError("X and y must share the same number of rows.")
        if X.shape[0] < 3:
            raise ValueError("LuoMatrixSBC needs >= 3 target samples.")
        d = X.shape[1]
        self.d_ = d
        self._source_fn = source_fn
        theta0 = np.concatenate(
            [[1.0, 0.0], np.ones(d), np.zeros(d)]
        )  # identity init = source unchanged

        def resid(theta: np.ndarray) -> np.ndarray:
            return self._eta(theta, X, source_fn) - y

        # 'trf' (not 'lm') so the fit is robust when n_samples < n_params (2d+2);
        # at tiny target fractions Luo is underdetermined -- itself a disadvantage
        # vs OSBC (2 params) and Yan, but trf returns a regularized solution.
        res = least_squares(resid, theta0, method="trf", max_nfev=self.max_nfev)
        self.theta_ = res.x
        return self

    def predict(
        self, X: np.ndarray, source_pred: np.ndarray, source_fn: SourceFn | None = None
    ) -> np.ndarray:
        if self.theta_ is None:
            raise RuntimeError("LuoMatrixSBC.predict called before fit.")
        sf = source_fn if source_fn is not None else self._source_fn
        if sf is None:
            raise RuntimeError("LuoMatrixSBC.predict needs source_fn.")
        return self._eta(self.theta_, np.asarray(X, dtype=float), sf)
