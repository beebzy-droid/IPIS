"""Unit tests for the delay compensation of conformal soft sensors (proposed claim N1'')."""

from __future__ import annotations

import math

import numpy as np
import pytest

from ipis.module1_soft_sensor.evaluation.delay_compensation import (
    fit_direct_forecaster,
    predicted_width_ratio,
    select_order,
)


def _ar1(phi: float, n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + math.sqrt(1.0 - phi * phi) * e[t]
    return x


@pytest.mark.parametrize("theta", [0, 3, 7])
def test_width_ratio_for_ar1_is_sqrt_one_minus_phi_power(theta: int) -> None:
    phi = 0.965
    acf = phi ** np.arange(40)
    expected = math.sqrt(1.0 - phi ** (2 * (theta + 1)))
    for order in (1, 3, 8):
        assert predicted_width_ratio(acf, theta, order) == pytest.approx(expected, rel=1e-9)


def test_width_ratio_is_one_for_white_noise() -> None:
    acf = np.r_[1.0, np.zeros(30)]
    assert predicted_width_ratio(acf, 3, 5) == pytest.approx(1.0)


def test_width_ratio_needs_enough_lags() -> None:
    with pytest.raises(ValueError):
        predicted_width_ratio(np.ones(5), 3, 3)


def test_forecaster_recovers_ar1_direct_coefficient_and_error_variance() -> None:
    phi, theta = 0.9, 3
    x = _ar1(phi, 60_000)
    f = fit_direct_forecaster(x, theta, order=1, fit=slice(0, 30_000))
    assert f.coef[1] == pytest.approx(phi ** (theta + 1), abs=0.02)
    pred = f.predict(x)
    err = (x - pred)[30_000:]
    assert np.var(err) == pytest.approx(1.0 - phi ** (2 * (theta + 1)), rel=0.05)


def test_forecaster_uses_no_future_labels() -> None:
    x = _ar1(0.9, 2_000, seed=3)
    f = fit_direct_forecaster(x, 3, order=4, fit=slice(0, 1_000))
    base = f.predict(x)
    y = x.copy()
    y[1_500:] += 100.0  # change labels from t = 1500 on
    moved = f.predict(y)
    # with h = 4, a prediction at t uses labels up to t - 4 only
    np.testing.assert_array_equal(base[:1_504], moved[:1_504])
    assert np.all(np.isnan(base[: f.warmup]))
    assert not np.any(np.isnan(base[f.warmup :]))


def test_select_order_finds_two_for_ar2() -> None:
    rng = np.random.default_rng(1)
    n = 40_000
    x = np.zeros(n)
    e = rng.standard_normal(n)
    for t in range(2, n):
        x[t] = 1.2 * x[t - 1] - 0.5 * x[t - 2] + e[t]
    assert select_order(x, 0, max_order=6) == 2


def test_forecaster_rejects_bad_arguments() -> None:
    x = _ar1(0.5, 100)
    with pytest.raises(ValueError):
        fit_direct_forecaster(x, -1)
    with pytest.raises(ValueError):
        fit_direct_forecaster(x[:5], 3, order=3)
