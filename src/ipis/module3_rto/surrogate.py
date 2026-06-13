"""GPR surrogate over the DWSIM twin (ADR-006) — the 3B in-loop plant model.

Replaces the 3A quadratic ln(xB) surface (`rto_nlp.LnXbSurface`) with a
Gaussian-process surrogate behind the same role: map (R, D) -> ln(x_B) (and a
companion (R, D) -> tray-6 T surface for the envelope check). The GP also
exposes a predictive std, which 3B can use for surrogate-refinement sampling;
the *headline* 3B uncertainty, however, is the soft-sensor conformal interval
(scoping D1-D3), NOT this surrogate variance — they are different quantities
(surrogate epistemic uncertainty about the twin surface vs sensor measurement
uncertainty).

Reproducibility (project principle: results reproduce to the decimal across
machines): inputs are standardized, kernel hyperparameters are BOUNDED
(the sklearn/type-II-MLE equivalent of MAP regularization on the GP
log-hyperparameters — prevents pathological length-scale collapse), the
optimizer is restarted from a fixed RNG seed, and a small nugget (alpha)
absorbs the twin's solver-level noise.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

_SEED = 20260613
_N_RESTARTS = 8
_ALPHA = 1e-6  # numerical nugget; solver noise handled by the WhiteKernel


@dataclass(frozen=True)
class GPRSurface:
    """A fitted GP surrogate z(R, D) with standardized-input bookkeeping.

    Attributes:
        gp: The fitted GaussianProcessRegressor (operates in standardized X).
        x_mean: Per-input training mean (for standardization).
        x_std: Per-input training std.
        r_squared: Leave-in-sample R^2 on the training points.
        log_target: True if the GP was fit on ln(z) (predict() exponentiates).
    """

    gp: GaussianProcessRegressor
    x_mean: np.ndarray
    x_std: np.ndarray
    r_squared: float
    log_target: bool

    def _xz(self, r: float, d: float) -> np.ndarray:
        return (np.array([[r, d]], float) - self.x_mean) / self.x_std

    def predict(self, r: float, d: float) -> float:
        """Posterior mean at (R, D); exponentiated if fit on a log target."""
        m = float(self.gp.predict(self._xz(r, d))[0])
        return float(np.exp(m)) if self.log_target else m

    def predict_std(self, r: float, d: float) -> float:
        """Posterior std at (R, D), in the GP's (possibly log) target space."""
        _, s = self.gp.predict(self._xz(r, d), return_std=True)
        return float(s[0])


def _fit(r: np.ndarray, d: np.ndarray, z: np.ndarray, log_target: bool) -> GPRSurface:
    r = np.asarray(r, float)
    d = np.asarray(d, float)
    z = np.asarray(z, float)
    finite = np.isfinite(r) & np.isfinite(d) & np.isfinite(z) & (z > 0 if log_target else True)
    r, d, z = r[finite], d[finite], z[finite]
    if r.size < 6:
        raise ValueError(f"Only {r.size} usable points; need >= 6 for the GP.")

    x = np.column_stack([r, d])
    x_mean, x_std = x.mean(0), x.std(0)
    x_std[x_std == 0] = 1.0
    xz = (x - x_mean) / x_std
    y = np.log(z) if log_target else z

    # Bounded kernel = MAP-equivalent regularization: length scales confined to
    # [0.3, 5] in standardized units (sub-grid to whole-box), signal/noise bounded.
    kernel = ConstantKernel(1.0, (1e-2, 1e2)) * Matern(
        length_scale=[1.0, 1.0], length_scale_bounds=(0.3, 5.0), nu=2.5
    ) + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-8, 1e-1))
    gp = GaussianProcessRegressor(
        kernel=kernel,
        alpha=_ALPHA,
        normalize_y=True,
        n_restarts_optimizer=_N_RESTARTS,
        random_state=_SEED,
    )
    gp.fit(xz, y)

    pred = gp.predict(xz)
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return GPRSurface(gp=gp, x_mean=x_mean, x_std=x_std, r_squared=r2, log_target=log_target)


def fit_gpr_ln_xb(r, d, x_bottoms) -> GPRSurface:
    """GP surrogate for ln(x_B) over (R, D) — the load-bearing 3B surface."""
    return _fit(r, d, x_bottoms, log_target=True)


def fit_gpr_tray_t(r, d, tray_t_c) -> GPRSurface:
    """GP surrogate for sensor-stage temperature over (R, D) — envelope check."""
    return _fit(r, d, tray_t_c, log_target=False)


def fit_gpr_from_csv(
    csv_path: str,
    r_col: str = "reflux_ratio",
    d_col: str = "distillate_kmol_h",
    xb_col: str = "xb_c4",
    t_col: str = "tray6_T_C",
) -> tuple[GPRSurface, GPRSurface]:
    """Fit both GP surfaces (ln xB, tray-6 T) from a twin sweep CSV."""
    import pandas as pd

    df = pd.read_csv(csv_path)
    missing = [c for c in (r_col, d_col, xb_col, t_col) if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    xb = fit_gpr_ln_xb(df[r_col].to_numpy(), df[d_col].to_numpy(), df[xb_col].to_numpy())
    tt = fit_gpr_tray_t(df[r_col].to_numpy(), df[d_col].to_numpy(), df[t_col].to_numpy())
    return xb, tt
