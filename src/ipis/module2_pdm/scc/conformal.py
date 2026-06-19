"""Similarity-Calibrated Conformal (SCC): split-conformal RUL bounds in a dimensionless
score space, restoring approximate exchangeability across operating regimes.

The one-sided over-prediction score ``V = rul_pred - rul_true`` is non-dimensionalised
by the physics-derived characteristic life scale ``sigma(T) = 1/k_nom(T)`` (so the
dimensionless score is ``Vtil = V / sigma = V * k_nom(T)``). Calibrating the conformal
quantile on ``Vtil`` and re-dimensionalising it by the *target* scale gives a lower RUL
bound whose coverage transfers across regimes under dynamic similitude. The naive
baseline (``sigma == 1``) calibrates on raw ``V`` and miscovers whenever the life scale
differs between calibration and target conditions.

Coverage guarantee: under the Lipschitz-similitude assumption the cross-regime coverage
gap is bounded by ``2 * d_TV(Vtil_S, Vtil_T)`` (Barber et al. 2023, non-exchangeable
split conformal), which is in turn controlled by the physical similitude-departure
mismatch — an a-priori, data-free certificate. See the SCC theory note and Barber,
Candès, Ramdas & Tibshirani (2023), *Conformal prediction beyond exchangeability*.
"""

from __future__ import annotations

import numpy as np

from ipis.module2_pdm.scc.deactivation import A_FAIL, DeactivationRun, R


def nominal_rate(temperature: float, e1: float, a1: float) -> float:
    """Nominal (population) Arrhenius rate k_nom(T) = a1 exp(-e1/RT); scale = 1/k_nom."""
    return float(a1 * np.exp(-e1 / (R * temperature)))


def score_run(run: DeactivationRun, frac: float, e1: float, a1: float) -> tuple[float, float]:
    """One-sided RUL over-prediction score at fraction ``frac`` of the run's life.

    Returns ``(V, Vtil)`` where ``V = rul_pred - rul_true`` (positive = dangerous
    over-prediction) and ``Vtil = V * k_nom(T)`` is its dimensionless form. The
    predictor extrapolates remaining life from the observed activity using the nominal
    rate (it knows the temperature, not the unit's pre-exponential or any unmodeled
    channel); the conformal layer covers the residual.
    """
    k_nom = nominal_rate(run.temperature, e1, a1)
    idx = min(int(np.searchsorted(run.t, frac * run.life)), len(run.t) - 1)
    a_obs = run.a_obs[idx]
    rul_true = run.life - run.t[idx]
    rul_pred = max(np.log(max(a_obs, 1e-3) / A_FAIL), 0.0) / k_nom
    v = rul_pred - rul_true
    return v, v * k_nom


def scores_for(
    runs: list[DeactivationRun], fracs: list[float], e1: float, a1: float
) -> tuple[np.ndarray, np.ndarray]:
    """Stack raw and dimensionless scores over all runs and monitoring fractions."""
    raw: list[float] = []
    dimensionless: list[float] = []
    for run in runs:
        for frac in fracs:
            v, vtil = score_run(run, frac, e1, a1)
            raw.append(v)
            dimensionless.append(vtil)
    return np.asarray(raw), np.asarray(dimensionless)


def one_sided_quantile(scores: np.ndarray, alpha: float) -> float:
    """Finite-sample (1-alpha) conformal quantile (the ceil((1-alpha)(n+1)) order stat)."""
    n = len(scores)
    k = min(int(np.ceil((1.0 - alpha) * (n + 1))), n)
    return float(np.sort(scores)[k - 1])


def coverage_naive(v_cal: np.ndarray, v_test: np.ndarray, alpha: float) -> float:
    """Empirical coverage of the naive (raw-score) lower bound calibrated on ``v_cal``."""
    q = one_sided_quantile(v_cal, alpha)
    return float(np.mean(v_test <= q))


def coverage_scc(vtil_cal: np.ndarray, vtil_test: np.ndarray, alpha: float) -> float:
    """Empirical coverage of the SCC (dimensionless) bound; re-dimensionalisation cancels."""
    q = one_sided_quantile(vtil_cal, alpha)
    return float(np.mean(vtil_test <= q))


def tv_distance(x: np.ndarray, y: np.ndarray, bins: int = 40) -> float:
    """Histogram estimate of total-variation distance between two score samples."""
    lo = float(min(x.min(), y.min()))
    hi = float(max(x.max(), y.max()))
    edges = np.linspace(lo, hi, bins + 1)
    p, _ = np.histogram(x, edges, density=True)
    q, _ = np.histogram(y, edges, density=True)
    return float(0.5 * np.sum(np.abs(p - q) * np.diff(edges)))
