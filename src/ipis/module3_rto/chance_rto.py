"""Chance-constrained RTO with conformal back-offs (Module 3, Phase 3B).

CPP-style (Lindemann et al., *Conformal Predictive Programming*) chance
constraint over the **unmeasured feed-z disturbance** at a known decision
(R, D). The RTO optimizes the nominal (z=0.35) surrogate and cannot see z; the
3-D truth surface xB(R, D, z) supplies the *true* bottoms composition at the
realized (R, D, z), so realized constraint violation is scored honestly.

Central result (the 3B contribution): a conformal back-off is **safe** as an
RTO constraint margin only if it is **conditionally** valid. A marginally
calibrated back-off -- even an adaptive/normalized one (Lei et al.) -- is
exploited by the optimizer, which drives toward operating points where the
marginal margin under-covers the *conditional* (1-alpha) quantile; realized
violation then far exceeds the nominal level (the CPP selection effect; the
conditional-coverage gap of Gibbs-Cherian-Candes). A conditional formulation
(CQR; Romano-Patterson-Candes) plus a CPP **a-posteriori** calibration step at
the selected setpoint restores violation control to the oracle level.

This module is plant-model-agnostic: it consumes fitted GP surfaces from
``surrogate`` and the ``EconomicsAnchor`` profit proxy. The headline metric is
the realized constraint-violation rate at the RTO optimum; profit at matched
(guaranteed) violation is secondary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import truncnorm

from .economics import (
    M_C4_KG_PER_KMOL,
    M_C6_KG_PER_KMOL,
    EconomicsAnchor,
)
from .surrogate import GPRSurface, TruthSurface3D

FEED_KMOL_H = 100.0
Z_NOMINAL = 0.35


# --------------------------------------------------------------------------- #
# Disturbance model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DisturbanceModel:
    """Truncated-normal feed-composition disturbance z ~ N(z0, sigma) on [lo, hi].

    The support [lo, hi] is the feed-z campaign sampling range; the truth surface
    is only validated to interpolate within it, so draws are clipped to it.
    """

    sigma: float
    z0: float = Z_NOMINAL
    lo: float = 0.30
    hi: float = 0.40

    @property
    def _ab(self) -> tuple[float, float]:
        return (self.lo - self.z0) / self.sigma, (self.hi - self.z0) / self.sigma

    def quantile(self, p: float) -> float:
        """The p-quantile of z (used for the monotone-in-z oracle shortcut)."""
        a, b = self._ab
        return float(truncnorm.ppf(p, a, b, loc=self.z0, scale=self.sigma))

    def draw(self, n: int, rng: np.random.Generator) -> np.ndarray:
        a, b = self._ab
        return truncnorm.rvs(a, b, loc=self.z0, scale=self.sigma, size=n, random_state=rng)


# --------------------------------------------------------------------------- #
# Vectorized grid prediction (the fitted GPs predict scalars; batch directly)
# --------------------------------------------------------------------------- #
def _grid2d(surf: GPRSurface, r: np.ndarray, d: np.ndarray) -> np.ndarray:
    xz = (np.column_stack([r, d]) - surf.x_mean) / surf.x_std
    m = surf.gp.predict(xz)
    return np.exp(m) if surf.log_target else m


def _grid3d(truth: TruthSurface3D, r: np.ndarray, d: np.ndarray, z: np.ndarray) -> np.ndarray:
    xz = (np.column_stack([r, d, z]) - truth.x_mean) / truth.x_std
    return np.exp(truth.gp.predict(xz))


# --------------------------------------------------------------------------- #
# Decision grid (precomputed nominal surfaces + profit)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DecisionGrid:
    """Dense (R, D) grid with nominal xB and profit precomputed once."""

    r: np.ndarray
    d: np.ndarray
    xb_nominal: np.ndarray
    profit: np.ndarray

    @property
    def n(self) -> int:
        return self.r.size


def build_decision_grid(
    xb_nom: GPRSurface,
    xd_nom: GPRSurface,
    q_nom: GPRSurface,
    econ: EconomicsAnchor,
    *,
    r_bounds: tuple[float, float] = (0.8, 3.0),
    d_bounds: tuple[float, float] = (33.0, 37.0),
    n_r: int = 67,
    n_d: int = 61,
    feed_kmol_h: float = FEED_KMOL_H,
) -> DecisionGrid:
    """Precompute the nominal-z xB and operating-profit fields over a dense grid."""
    gr = np.linspace(*r_bounds, n_r)
    gd = np.linspace(*d_bounds, n_d)
    mr, md = (a.ravel() for a in np.meshgrid(gr, gd))
    xb = np.clip(_grid2d(xb_nom, mr, md), 0.0, 1.0)
    xd = np.clip(_grid2d(xd_nom, mr, md), 0.0, 1.0)
    q = _grid2d(q_nom, mr, md)
    b = feed_kmol_h - md
    overhead_kg = md * xd * M_C4_KG_PER_KMOL + md * (1.0 - xd) * M_C6_KG_PER_KMOL
    bottoms_kg = b * xb * M_C4_KG_PER_KMOL + b * (1.0 - xb) * M_C6_KG_PER_KMOL
    revenue = overhead_kg * econ.c4_value_usd_per_kg + bottoms_kg * econ.gasoline_value_usd_per_kg
    energy = q * 3600.0 / 1.0e6 * econ.energy_cost_usd_per_gj
    return DecisionGrid(r=mr, d=md, xb_nominal=xb, profit=revenue - energy)


# --------------------------------------------------------------------------- #
# Calibration set (residuals of the nominal model vs the truth over z)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CalibrationSet:
    r: np.ndarray
    d: np.ndarray
    z: np.ndarray
    xb_truth: np.ndarray
    xb_nominal: np.ndarray

    @property
    def residual(self) -> np.ndarray:
        """xB_truth - xB_nominal: the error the back-off must upper-bound."""
        return self.xb_truth - self.xb_nominal


def sample_calibration(
    xb_nom: GPRSurface,
    truth: TruthSurface3D,
    disturbance: DisturbanceModel,
    rng: np.random.Generator,
    *,
    n: int = 1500,
    r_bounds: tuple[float, float] = (0.8, 3.0),
    d_bounds: tuple[float, float] = (33.0, 37.0),
) -> CalibrationSet:
    """Draw (R, D) uniform in the box and z ~ disturbance; evaluate truth + nominal."""
    r = rng.uniform(*r_bounds, n)
    d = rng.uniform(*d_bounds, n)
    z = disturbance.draw(n, rng)
    xt = np.clip(_grid3d(truth, r, d, z), 0.0, 1.0)
    xn = np.clip(_grid2d(xb_nom, r, d), 0.0, 1.0)
    return CalibrationSet(r=r, d=d, z=z, xb_truth=xt, xb_nominal=xn)


# --------------------------------------------------------------------------- #
# Conformal quantile (one-sided, finite-sample corrected)
# --------------------------------------------------------------------------- #
def one_sided_quantile(scores: np.ndarray, alpha: float) -> float:
    """Split-conformal (1-alpha) upper quantile: the ceil((n+1)(1-alpha))-th
    smallest score (the finite-sample-valid order statistic). If that index
    exceeds n, no finite upper bound exists at this level and +inf is returned.
    """
    s = np.sort(np.asarray(scores, float))
    n = s.size
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        return float("inf")
    return float(s[k - 1])


# --------------------------------------------------------------------------- #
# Back-off builders -> per-grid-point margin C(R, D) (array) or scalar
# --------------------------------------------------------------------------- #
def oracle_backoff(
    truth: TruthSurface3D, grid: DecisionGrid, disturbance: DisturbanceModel, alpha: float
) -> np.ndarray:
    """Ground-truth conditional (1-alpha) back-off.

    xB is monotone increasing in z, so the (1-alpha) quantile of xB(R, D, z) over
    z equals xB at the (1-alpha) quantile of z. This is the achievable ideal: by
    construction the realized violation at any active point equals alpha.
    """
    z_hi = disturbance.quantile(1.0 - alpha)
    q_hi = np.clip(_grid3d(truth, grid.r, grid.d, np.full(grid.n, z_hi)), 0.0, 1.0)
    return np.maximum(q_hi - grid.xb_nominal, 0.0)


def fixed_backoff(calib: CalibrationSet, alpha: float) -> float:
    """Constant margin = pooled one-sided (1-alpha) quantile of the residuals."""
    return one_sided_quantile(calib.residual, alpha)


def normalized_backoff(calib: CalibrationSet, grid: DecisionGrid, alpha: float) -> np.ndarray:
    """BASELINE (the method that fails): normalized/locally-adaptive one-sided
    conformal (Lei et al.). Scale sigma_hat(R, D) is a GP on |residual|; the score
    is residual/sigma_hat. Marginally valid, NOT conditionally valid -- the RTO
    exploits the gap.
    """
    from .surrogate import _fit

    # scale GP is the BASELINE's local-std estimate; subsample the fit for speed
    # (full-fidelity scale does not change its marginal-vs-conditional failure).
    n = calib.r.size
    if n > 800:
        sub = np.random.default_rng(0).choice(n, 800, replace=False)
        sr, sd, sres = calib.r[sub], calib.d[sub], calib.residual[sub]
    else:
        sr, sd, sres = calib.r, calib.d, calib.residual
    scale = _fit(sr, sd, np.abs(sres) + 1e-5, log_target=False)
    sig_c = np.maximum(_grid2d(scale, calib.r, calib.d), 1e-5)
    q = one_sided_quantile(calib.residual / sig_c, alpha)
    sig_g = np.maximum(_grid2d(scale, grid.r, grid.d), 1e-5)
    return np.maximum(q * sig_g, 0.0)


def cqr_backoff(calib: CalibrationSet, grid: DecisionGrid, alpha: float) -> np.ndarray:
    """CONDITIONAL back-off (the fix): one-sided conformalized quantile regression.

    Fit the conditional (1-alpha) quantile of xB_truth over (R, D) by gradient-
    boosted quantile regression, then add the one-sided conformal correction
    Q_{1-alpha}({xB_truth - qhat}). Targets the conditional quantile directly, so
    the optimizer cannot exploit a marginal-vs-conditional gap.
    """
    from sklearn.ensemble import GradientBoostingRegressor

    xc = np.column_stack([calib.r, calib.d])
    gbr = GradientBoostingRegressor(
        loss="quantile", alpha=1.0 - alpha, n_estimators=200, max_depth=3, random_state=0
    )
    gbr.fit(xc, calib.xb_truth)
    e = calib.xb_truth - gbr.predict(xc)
    corr = one_sided_quantile(e, alpha)
    q_hi = gbr.predict(np.column_stack([grid.r, grid.d])) + corr
    return np.maximum(np.clip(q_hi, 0.0, 1.0) - grid.xb_nominal, 0.0)


# --------------------------------------------------------------------------- #
# Solve + score
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ChanceRTOResult:
    method: str
    feasible_found: bool
    reflux_ratio: float = float("nan")
    distillate_kmol_h: float = float("nan")
    profit_usd_per_h: float = float("nan")
    backoff_at_opt: float = float("nan")
    realized_violation: float = float("nan")
    kappa: float = 1.0  # a-posteriori inflation factor applied (1.0 = none)


def _solve_index(grid: DecisionGrid, backoff: np.ndarray | float, spec: float) -> int | None:
    c = np.full(grid.n, float(backoff)) if np.ndim(backoff) == 0 else np.asarray(backoff, float)
    feasible = (grid.xb_nominal + c) <= spec
    if not feasible.any():
        return None
    return int(np.argmax(np.where(feasible, grid.profit, -np.inf)))


def realized_violation(
    truth: TruthSurface3D,
    r: float,
    d: float,
    disturbance: DisturbanceModel,
    spec: float,
    rng: np.random.Generator,
    n: int = 4000,
) -> float:
    """Monte-Carlo P_z[ xB_truth(r, d, z) > spec ] over the disturbance."""
    z = disturbance.draw(n, rng)
    return _violation_on_z(truth, r, d, z, spec)


def _violation_on_z(truth: TruthSurface3D, r: float, d: float, z: np.ndarray, spec: float) -> float:
    """Violation fraction on a FIXED z-sample (deterministic across calls)."""
    xb = np.clip(_grid3d(truth, np.full(z.size, r), np.full(z.size, d), z), 0.0, 1.0)
    return float(np.mean(xb > spec))


def solve_chance_rto(
    grid: DecisionGrid,
    backoff: np.ndarray | float,
    spec: float,
    truth: TruthSurface3D,
    disturbance: DisturbanceModel,
    rng: np.random.Generator,
    *,
    method: str = "",
    n_violation: int = 4000,
) -> ChanceRTOResult:
    """Maximize nominal profit s.t. xB_nominal + backoff <= spec; score the truth."""
    i = _solve_index(grid, backoff, spec)
    if i is None:
        return ChanceRTOResult(method=method, feasible_found=False)
    c_at = float(backoff) if np.ndim(backoff) == 0 else float(np.asarray(backoff)[i])
    viol = realized_violation(truth, grid.r[i], grid.d[i], disturbance, spec, rng, n_violation)
    return ChanceRTOResult(
        method=method,
        feasible_found=True,
        reflux_ratio=float(grid.r[i]),
        distillate_kmol_h=float(grid.d[i]),
        profit_usd_per_h=float(grid.profit[i]),
        backoff_at_opt=c_at,
        realized_violation=viol,
    )


def aposteriori_tighten(
    grid: DecisionGrid,
    base_backoff: np.ndarray,
    spec: float,
    truth: TruthSurface3D,
    disturbance: DisturbanceModel,
    alpha: float,
    rng: np.random.Generator,
    *,
    method: str = "cqr+aposteriori",
    kappa_max: float = 6.0,
    tol: float = 1e-2,
    n_validate: int = 6000,
    n_test: int = 6000,
    max_iter: int = 24,
) -> ChanceRTOResult:
    """CPP a-posteriori step: inflate the back-off by the smallest kappa>=1 such
    that the realized violation at the *selected* optimum is <= alpha on a held-out
    validation draw; report on an independent test draw. Restores the guarantee the
    selection effect breaks. Returns infeasible if no feasible kappa complies.

    The feasible-in-kappa region is a window (large kappa over-tightens to an empty
    feasible set), so the search first locates the largest feasible kappa, checks
    that it can comply, then bisects for the smallest compliant kappa. Violation is
    evaluated on a FIXED validation z-sample so viol(kappa) is monotone.
    """
    val_rng = np.random.default_rng(rng.integers(1 << 31))
    z_val = disturbance.draw(n_validate, val_rng)

    def fv(kappa: float) -> tuple[bool, float]:
        i = _solve_index(grid, kappa * base_backoff, spec)
        if i is None:
            return (False, float("nan"))
        return (True, _violation_on_z(truth, grid.r[i], grid.d[i], z_val, spec))

    feas1, v1 = fv(1.0)
    if not feas1:
        return ChanceRTOResult(method=method, feasible_found=False, kappa=1.0)
    if v1 <= alpha + tol:
        kappa = 1.0
    else:
        # locate largest feasible kappa in [1, kappa_max]
        feas_max, _ = fv(kappa_max)
        if feas_max:
            k_fmax = kappa_max
        else:
            a, b = 1.0, kappa_max
            for _ in range(max_iter):
                m = 0.5 * (a + b)
                if fv(m)[0]:
                    a = m
                else:
                    b = m
            k_fmax = a
        # can the most-tightened feasible point comply?
        if fv(k_fmax)[1] > alpha + tol:
            return ChanceRTOResult(method=method, feasible_found=False, kappa=k_fmax)
        # bisect for the smallest compliant kappa in [1, k_fmax]
        a, b = 1.0, k_fmax
        for _ in range(max_iter):
            m = 0.5 * (a + b)
            fm, vm = fv(m)
            if fm and vm <= alpha + tol:
                b = m
            else:
                a = m
            if b - a < 1e-3:
                break
        kappa = b

    i = _solve_index(grid, kappa * base_backoff, spec)
    if i is None:
        return ChanceRTOResult(method=method, feasible_found=False, kappa=kappa)
    test_rng = np.random.default_rng(rng.integers(1 << 31))
    viol = realized_violation(truth, grid.r[i], grid.d[i], disturbance, spec, test_rng, n_test)
    return ChanceRTOResult(
        method=method,
        feasible_found=True,
        reflux_ratio=float(grid.r[i]),
        distillate_kmol_h=float(grid.d[i]),
        profit_usd_per_h=float(grid.profit[i]),
        backoff_at_opt=float(kappa * np.asarray(base_backoff)[i]),
        realized_violation=viol,
        kappa=kappa,
    )
