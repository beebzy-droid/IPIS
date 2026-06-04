"""Unit tests for ipis.module1_soft_sensor.evaluation.conformal.

Validate each construction against its published property:
- split conformal -> ~ (1 - alpha) marginal coverage on exchangeable data;
- ACI -> long-run coverage held under drift where static split collapses;
- EnbPI -> ~ (1 - alpha) on a stationary process, width-minimising offsets;
- finite-sample quantile rank + diagnostics arithmetic.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from ipis.module1_soft_sensor.evaluation.conformal import (
    ACI_GAMMA_GRID,
    ACIConformal,
    EnbPI,
    SplitConformal,
    aci_step,
    conformal_quantile,
    enbpi_offsets,
    marginal_coverage,
    mean_interval_width,
    rolling_coverage,
    select_gamma,
    split_conformal_halfwidth,
)

ALPHA = 0.1


# --------------------------------------------------------------------------- #
# conformal_quantile                                                          #
# --------------------------------------------------------------------------- #
def test_conformal_quantile_rank():
    # n=9, level=0.9 -> ceil(0.9*10)=9 -> 9th smallest (the max here).
    scores = np.arange(1.0, 10.0)  # 1..9
    assert conformal_quantile(scores, 0.9) == 9.0
    # n=19, level=0.9 -> ceil(0.9*20)=18 -> 18th smallest.
    scores = np.arange(1.0, 20.0)  # 1..19
    assert conformal_quantile(scores, 0.9) == 18.0


def test_conformal_quantile_edges():
    scores = np.arange(1.0, 10.0)
    assert conformal_quantile(scores, 0.0) == 0.0
    assert math.isinf(conformal_quantile(scores, 1.0))
    # rank > n -> +inf (whole line)
    assert math.isinf(conformal_quantile(np.array([1.0, 2.0, 3.0]), 0.99))


def test_conformal_quantile_empty_raises():
    with pytest.raises(ValueError):
        conformal_quantile(np.array([]), 0.9)


# --------------------------------------------------------------------------- #
# Split conformal                                                             #
# --------------------------------------------------------------------------- #
def test_split_halfwidth_matches_quantile():
    rng = np.random.default_rng(0)
    resid = rng.normal(0, 1, 200)
    hw = split_conformal_halfwidth(resid, ALPHA)
    assert hw == conformal_quantile(np.abs(resid), 1 - ALPHA)


def test_split_marginal_coverage_exchangeable():
    # Exchangeable: calibrate on one i.i.d. block, test on another. Expect ~0.9.
    rng = np.random.default_rng(1)
    calib = rng.normal(0, 1.0, 1000)
    sc = SplitConformal(calib, alpha=ALPHA)
    y_pred = np.zeros(2000)
    y_true = rng.normal(0, 1.0, 2000)
    lo, hi = sc.interval(y_pred)
    cov = marginal_coverage((lo <= y_true) & (y_true <= hi))
    assert 0.86 <= cov <= 0.94


# --------------------------------------------------------------------------- #
# EnbPI                                                                       #
# --------------------------------------------------------------------------- #
def test_enbpi_offsets_minimise_width():
    rng = np.random.default_rng(2)
    resid = rng.normal(0, 1, 500)
    lo, hi = enbpi_offsets(resid, ALPHA)
    width = hi - lo
    # Any other admissible (beta, 1-alpha+beta) split must be no narrower.
    for beta in np.linspace(0, ALPHA, 11):
        q_lo = np.quantile(resid, beta, method="higher")
        q_hi = np.quantile(resid, 1 - ALPHA + beta, method="higher")
        assert (q_hi - q_lo) >= width - 1e-9


def test_enbpi_offsets_symmetric_for_symmetric_residuals():
    # Symmetric residuals -> near-symmetric offsets about 0.
    rng = np.random.default_rng(3)
    resid = rng.normal(0, 1, 5000)
    lo, hi = enbpi_offsets(resid, ALPHA)
    assert abs(lo + hi) < 0.15  # |w_lower + w_upper| ~ 0


def test_enbpi_coverage_stationary():
    rng = np.random.default_rng(4)
    n = 400

    def fit_predict(x_tr, y_tr, x_ev):
        # OLS with intercept.
        a = np.c_[np.ones(len(x_tr)), x_tr]
        coef, *_ = np.linalg.lstsq(a, y_tr, rcond=None)
        return np.c_[np.ones(len(x_ev)), x_ev] @ coef

    x = rng.uniform(-2, 2, (n, 1))
    y = (3.0 * x[:, 0] + rng.normal(0, 1.0, n)).astype(float)
    xt = rng.uniform(-2, 2, (300, 1))
    yt = (3.0 * xt[:, 0] + rng.normal(0, 1.0, 300)).astype(float)

    model = EnbPI(fit_predict, alpha=ALPHA, B=30, s=1, random_state=7).fit(x, y)
    _, lo, hi = model.predict_interval(xt, yt)
    cov = marginal_coverage((lo <= yt) & (yt <= hi))
    assert 0.83 <= cov <= 0.97  # distribution-free, finite-sample slack


# --------------------------------------------------------------------------- #
# ACI                                                                         #
# --------------------------------------------------------------------------- #
def test_aci_step_formula():
    # Covered -> err=0 -> alpha increases by gamma*target (interval can shrink).
    assert aci_step(0.1, True, 0.05, 0.1) == pytest.approx(0.1 + 0.05 * 0.1)
    # Not covered -> err=1 -> alpha decreases by gamma*(1-target) (interval widens).
    assert aci_step(0.1, False, 0.05, 0.1) == pytest.approx(0.1 + 0.05 * (0.1 - 1.0))


def test_aci_holds_coverage_under_drift_where_split_fails():
    # Residual scale doubles partway through -> classic covariate/regime drift.
    rng = np.random.default_rng(5)
    n_cal, n1, n2 = 500, 1500, 1500
    cal = rng.normal(0, 1.0, n_cal)
    drift = np.concatenate([rng.normal(0, 1.0, n1), rng.normal(0, 2.5, n2)])
    y_pred = np.zeros(n1 + n2)
    y_true = drift  # residual == y_true since y_pred == 0

    # Static split, calibrated on the pre-drift block: under-covers after the shift.
    sc = SplitConformal(cal, alpha=ALPHA)
    lo_s, hi_s = sc.interval(y_pred)
    cov_split = marginal_coverage((lo_s <= y_true) & (y_true <= hi_s))

    # ACI with a sliding window adapts and restores ~nominal long-run coverage.
    aci = ACIConformal(cal, alpha=ALPHA, gamma=0.05, window=200)
    lo_a, hi_a, cov_a, _ = aci.run(y_pred, y_true)
    cov_aci = marginal_coverage(cov_a)

    assert cov_split < 0.85  # static method demonstrably under-covers under drift
    assert cov_aci >= 0.87  # adaptive method recovers
    assert cov_aci > cov_split + 0.03


def test_aci_alpha_trace_bounded_and_responsive():
    rng = np.random.default_rng(6)
    cal = rng.normal(0, 1.0, 300)
    y_true = rng.normal(0, 1.0, 1000)
    aci = ACIConformal(cal, alpha=ALPHA, gamma=0.03, window=150)
    _, _, _, atrace = aci.run(np.zeros(1000), y_true)
    # On stationary data alpha_t should hover near the target, not run away.
    assert abs(np.median(atrace) - ALPHA) < 0.06


def test_select_gamma_returns_grid_value():
    rng = np.random.default_rng(8)
    cal = rng.normal(0, 1.0, 300)
    y_true = rng.normal(0, 1.0, 800)
    g = select_gamma(np.zeros(800), y_true, cal, alpha=ALPHA, window=150)
    assert g in ACI_GAMMA_GRID


# --------------------------------------------------------------------------- #
# Diagnostics                                                                 #
# --------------------------------------------------------------------------- #
def test_rolling_coverage_window():
    covered = np.array([1, 1, 0, 1, 1, 1, 0, 1], dtype=bool)
    rc = rolling_coverage(covered, window=3)
    assert rc[0] == pytest.approx(1.0)  # [1]
    assert rc[2] == pytest.approx(2 / 3)  # [1,1,0]
    assert rc[6] == pytest.approx(2 / 3)  # [1,1,0]
    assert rc.shape == covered.shape


def test_marginal_coverage_and_width():
    lo = np.array([0.0, 1.0, 2.0])
    hi = np.array([2.0, 3.0, 4.0])
    assert mean_interval_width(lo, hi) == pytest.approx(2.0)
    assert marginal_coverage(np.array([True, False, True, True])) == pytest.approx(0.75)


def test_mean_width_ignores_infinite():
    lo = np.array([0.0, -math.inf])
    hi = np.array([2.0, math.inf])
    assert mean_interval_width(lo, hi) == pytest.approx(2.0)
