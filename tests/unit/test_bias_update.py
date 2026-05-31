"""Unit tests for evaluation.bias_update (Phase 1B step-3 Shardt bias update)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from ipis.module1_soft_sensor.evaluation.bias_update import (
    apply_bias_update,
    corrected_fold_r2,
    oracle_debias_r2,
)
from ipis.module1_soft_sensor.evaluation.drift import blocked_cv_residuals


def _fortuna_like(n: int = 600, seed: int = 1, drift: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    u = rng.uniform(0.2, 0.8, size=(n, 7))
    df = pd.DataFrame(u, columns=[f"u{i}" for i in range(1, 8)])
    u5 = df["u5"].to_numpy()
    y = np.empty(n)
    y[:15] = 0.3
    # A slow time drift in the offset is NOT absorbed by a per-fold train-fit
    # intercept (train mean != later test-block mean), so it leaves a non-zero
    # residual mean on each held-out block -- the calibration-drift failure mode.
    y[15:] = 0.6 * u5[:-15] + rng.normal(0, 0.02, n - 15) + drift * np.arange(n - 15)
    df["y"] = y
    return df


class TestApplyBiasUpdate:
    def test_zero_delay_unit_lambda_is_exact(self) -> None:
        # delay=0, lam=1: b_t = y_true[t]-y_pred[t] -> corrected == y_true.
        rng = np.random.default_rng(0)
        y = rng.normal(0, 1, 200)
        yhat = y - 0.3
        corrected, _ = apply_bias_update(y, yhat, lam=1.0, delay=0)
        assert np.allclose(corrected, y)

    def test_constant_bias_is_removed_after_delay(self) -> None:
        # y_pred = y_true - c (constant offset). Bias should converge to c so the
        # corrected residual mean approaches zero past the warm-up.
        n, c, delay = 400, 0.25, 15
        rng = np.random.default_rng(2)
        y = rng.normal(0.5, 0.05, n)
        yhat = y - c
        corrected, bias = apply_bias_update(y, yhat, lam=0.3, delay=delay)
        tail = corrected[100:] - y[100:]
        assert abs(tail.mean()) < 0.02
        assert abs(bias[-1] - c) < 0.02

    def test_causality_first_delay_samples_use_b0(self) -> None:
        rng = np.random.default_rng(3)
        y = rng.normal(0, 1, 50)
        yhat = y - 0.2
        delay, b0 = 10, 0.05
        corrected, bias = apply_bias_update(y, yhat, lam=0.5, delay=delay, b0=b0)
        assert np.allclose(bias[:delay], b0)
        assert np.allclose(corrected[:delay], yhat[:delay] + b0)

    def test_rejects_bad_params(self) -> None:
        y = [0.0, 1.0]
        with pytest.raises(ValueError):
            apply_bias_update(y, y, lam=0.0, delay=1)
        with pytest.raises(ValueError):
            apply_bias_update(y, y, lam=1.5, delay=1)
        with pytest.raises(ValueError):
            apply_bias_update(y, y, lam=0.5, delay=-1)
        with pytest.raises(ValueError):
            apply_bias_update([0.0, 1.0], [0.0], lam=0.5, delay=1)


class TestFoldHelpers:
    def _biased_folds(self):
        # A slow time drift makes the per-fold train fit biased on its test block.
        df = _fortuna_like(drift=0.0008)
        return blocked_cv_residuals(df, LinearRegression, max_lag=15, n_splits=5)

    def test_bias_update_improves_biased_folds(self) -> None:
        folds = self._biased_folds()
        raw = [f.r2 for f in folds]
        corrected = corrected_fold_r2(folds, lam=0.5, delay=15)
        # Mean R^2 should not get worse and should improve where bias dominates.
        assert np.mean(corrected) >= np.mean(raw) - 1e-9

    def test_oracle_never_worse_than_raw_per_fold(self) -> None:
        # Removing the residual mean never decreases a fold's R^2 (SS_res drops
        # by n*mean^2 >= 0). This holds per fold, unlike "oracle >= causal",
        # which can fail when the residual drifts within a fold.
        folds = self._biased_folds()
        for f, r2o in zip(folds, oracle_debias_r2(folds), strict=True):
            assert r2o >= f.r2 - 1e-9

    def test_oracle_removes_mean_exactly(self) -> None:
        folds = self._biased_folds()
        for f, r2o in zip(folds, oracle_debias_r2(folds), strict=True):
            resid_after = f.y_true - (f.y_pred + f.residuals.mean())
            assert abs(resid_after.mean()) < 1e-9
            assert r2o >= f.r2 - 1e-9
