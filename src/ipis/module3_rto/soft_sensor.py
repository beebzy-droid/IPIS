"""Twin soft sensor for 3B — the M1 conformal methodology on twin data.

Scoping D2: transfer the *methodology* (physics-anchored feature + conformal
intervals), not the literal Debutanizer weights (the C6 disjoint-input trap).
The sensor maps the inferential tray-6 temperature to the bottoms C4 fraction
and reports a one-sided upper bound at coverage ``1 - alpha`` — the back-off the
RTO subtracts from the spec (scoping D1: ``y_hat + C+ <= spec``).

The uncertainty is real because feed composition z is an UNMEASURED disturbance
(scoping D5, ratified 2026-06-13): at a given measured tray-6 T the true xB
scatters with z, and the single-feature sensor cannot resolve it. That scatter
is heteroscedastic across the operating box, so the normalized conformal width
(NormalizedOneSidedConformal) varies — the mechanism by which the interval-driven
back-off beats a fixed margin (3B.3).

Components:
  - mean model  mu_hat(T)    : monotone GP, tray-6 T -> xB
  - scale model sigma_hat(T) : GP on |residual|, the conditional uncertainty
  - conformal   one-sided normalized upper bound, calibrated on a held-out split
Coverage on a held-out test split is a GATE (scoping D3) before any profit claim.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

from ipis.module1_soft_sensor.evaluation.conformal import (
    NormalizedOneSidedConformal,
    marginal_coverage,
)

_SEED = 20260613
_SCALE_FLOOR = 1e-4  # keep sigma_hat strictly positive for the normalized score


def _gp(length_bounds=(0.3, 5.0)) -> GaussianProcessRegressor:
    # WhiteKernel floor kept well above jitter so the mean does NOT interpolate
    # noisy points — overfitting shrinks train residuals and biases sigma_hat,
    # which breaks calib/test exchangeability and undercovers.
    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
        length_scale=1.0, length_scale_bounds=length_bounds, nu=2.5
    ) + WhiteKernel(1e-3, (1e-5, 1e0))
    return GaussianProcessRegressor(
        kernel=kernel, alpha=1e-6, normalize_y=True, n_restarts_optimizer=6, random_state=_SEED
    )


@dataclass
class CoverageReport:
    """One-sided coverage of the upper bound on a held-out test split."""

    target: float
    empirical: float
    n_test: int
    mean_halfwidth: float
    halfwidth_cv: float  # coefficient of variation of C+ -> heteroscedasticity check

    @property
    def passed(self) -> bool:
        # one-sided coverage must reach the target (small slack for finite n)
        return self.empirical >= self.target - 0.05


class TwinSoftSensor:
    """tray-6 T -> (xB estimate, one-sided upper back-off C+)."""

    def __init__(self, alpha: float = 0.10) -> None:
        self.alpha = float(alpha)
        self._mu: GaussianProcessRegressor | None = None
        self._sigma: GaussianProcessRegressor | None = None
        self._t_mean = 0.0
        self._t_std = 1.0
        self._conformal: NormalizedOneSidedConformal | None = None

    def _z(self, t: np.ndarray) -> np.ndarray:
        return (np.asarray(t, float).reshape(-1, 1) - self._t_mean) / self._t_std

    def fit(self, t_train, xb_train, t_calib, xb_calib) -> None:
        """Fit mu on train, scale on train residuals, calibrate conformal on calib."""
        t_tr = np.asarray(t_train, float)
        y_tr = np.asarray(xb_train, float)
        self._t_mean, self._t_std = t_tr.mean(), t_tr.std() or 1.0

        self._mu = _gp().fit(self._z(t_tr), y_tr)
        resid_tr = y_tr - self._mu.predict(self._z(t_tr))
        # scale model on log|resid| for positivity, exponentiate back
        self._sigma = _gp().fit(self._z(t_tr), np.log(np.abs(resid_tr) + _SCALE_FLOOR))

        t_ca = np.asarray(t_calib, float)
        y_ca = np.asarray(xb_calib, float)
        e_ca = y_ca - self._mu.predict(self._z(t_ca))  # signed
        sig_ca = self._scale(t_ca)
        self._conformal = NormalizedOneSidedConformal(e_ca, sig_ca, alpha=self.alpha)

    def _scale(self, t) -> np.ndarray:
        assert self._sigma is not None
        return np.exp(self._sigma.predict(self._z(t))) + _SCALE_FLOOR

    def predict(self, t) -> tuple[np.ndarray, np.ndarray]:
        """Return (xB estimate, one-sided upper back-off C+) at tray-6 T."""
        assert self._mu is not None and self._conformal is not None
        yhat = self._mu.predict(self._z(t))
        cplus = self._conformal.upper_halfwidth(self._scale(t))
        return yhat, cplus

    def upper_bound(self, t) -> np.ndarray:
        yhat, cplus = self.predict(t)
        return yhat + cplus

    def validate_coverage(self, t_test, xb_test_true) -> CoverageReport:
        """One-sided empirical coverage P(true xB <= upper bound) on a test split."""
        t = np.asarray(t_test, float)
        y = np.asarray(xb_test_true, float)
        yhat, cplus = self.predict(t)
        covered = y <= (yhat + cplus)
        return CoverageReport(
            target=1.0 - self.alpha,
            empirical=float(marginal_coverage(covered)),
            n_test=y.size,
            mean_halfwidth=float(cplus.mean()),
            halfwidth_cv=float(cplus.std() / cplus.mean()) if cplus.mean() else 0.0,
        )

    def backoff_callable(self, tray_t_surface):
        """Adapter for solve_rto_surface: (R, D) -> C+ via the tray-6 T surface.

        The RTO works in (R, D); the sensor in tray-6 T. Compose them with the
        3B.1 GPR tray-T surface so the chance-constraint back-off is the sensor's
        one-sided half-width at the operating point's expected tray-6 T.
        """

        def _bo(r: float, d: float) -> float:
            t = float(tray_t_surface(r, d))
            _, cplus = self.predict([t])
            return float(cplus[0])

        return _bo
