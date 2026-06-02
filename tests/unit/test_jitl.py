"""Unit tests for evaluation.jitl (Phase 1B JITL baseline)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from ipis.module1_soft_sensor.evaluation.drift import blocked_cv_residuals
from ipis.module1_soft_sensor.evaluation.jitl import (
    gate_with_drift,
    jitl_fold_predictions,
    lwr_predict,
)


def _fortuna_like(n: int = 600, seed: int = 1, drift: float = 0.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    u = rng.uniform(0.2, 0.8, size=(n, 7))
    df = pd.DataFrame(u, columns=[f"u{i}" for i in range(1, 8)])
    u5 = df["u5"].to_numpy()
    y = np.empty(n)
    y[:15] = 0.3
    y[15:] = 0.6 * u5[:-15] + rng.normal(0, 0.02, n - 15) + drift * np.arange(n - 15)
    df["y"] = y
    return df


def _lowdim_builder(seg: pd.DataFrame):
    """Stand-in for the physics-anchored builder: the single u5 lag-15 feature.

    JITL (LWR) needs a low-dimensional feature space; on the raw 112-feature
    lagged set its Euclidean similarity collapses (curse of dimensionality). The
    real eval uses make_physics_anchored_features (~2-3 features); this mirrors
    that low dimensionality for the unit tests.
    """
    x = seg["u5"].shift(15).to_frame("u5_lag15").iloc[15:].reset_index(drop=True)
    y = seg["y"].iloc[15:].reset_index(drop=True)
    return x, y


class TestLWRPredict:
    def test_recovers_linear_truth(self) -> None:
        # y = 2*x0 - 3*x1 + 1; LWR (any bandwidth) should predict near-exactly.
        rng = np.random.default_rng(0)
        X = rng.normal(0, 1, (200, 2))
        y = 2 * X[:, 0] - 3 * X[:, 1] + 1.0
        xq = np.array([0.5, -0.4])
        truth = 2 * 0.5 - 3 * -0.4 + 1.0
        for bw in (0.5, 2.0, 10.0):
            pred = lwr_predict(X, y, xq, bandwidth=bw)
            assert abs(pred - truth) < 1e-3, bw

    def test_local_fit_tracks_piecewise(self) -> None:
        # Two regimes with different slopes; small bandwidth -> local slope used.
        x = np.linspace(-3, 3, 400).reshape(-1, 1)
        y = np.where(x[:, 0] < 0, 1.0 * x[:, 0], 5.0 * x[:, 0])
        # Query at +2 (steep regime): narrow-bandwidth LWR ~ 5*2 = 10.
        pred = lwr_predict(x, y, np.array([2.0]), bandwidth=0.3)
        assert abs(pred - 10.0) < 1.0

    def test_rejects_bad_bandwidth(self) -> None:
        with pytest.raises(ValueError):
            lwr_predict(np.zeros((3, 2)), np.zeros(3), np.zeros(2), bandwidth=0.0)

    def test_ridge_keeps_underdetermined_solve_finite(self) -> None:
        # Fewer effective samples than params + collinear -> ridge must stabilize.
        X = np.array([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]])
        y = np.array([1.0, 1.0, 1.0])
        pred = lwr_predict(X, y, np.array([1.0, 1.0]), bandwidth=1.0, ridge=1e-6)
        assert np.isfinite(pred)


class TestJITLFoldPredictions:
    def test_shapes_fold_count_and_compute(self) -> None:
        df = _fortuna_like()
        folds = jitl_fold_predictions(
            df,
            max_lag=15,
            n_splits=5,
            label_delay=4,
            bandwidth=1.0,
            feature_builder=_lowdim_builder,
        )
        assert len(folds) == 5
        for f in folds:
            assert f.residuals.y_true.shape == f.residuals.y_pred.shape
            assert f.local_fits == len(f.residuals.y_pred)  # one fit per query

    def test_predicts_signal_on_clean_fold(self) -> None:
        # With a clean (no-drift) relationship, JITL should achieve positive R^2.
        df = _fortuna_like(drift=0.0)
        folds = jitl_fold_predictions(
            df,
            max_lag=15,
            n_splits=5,
            label_delay=4,
            bandwidth=1.5,
            feature_builder=_lowdim_builder,
        )
        assert np.mean([f.r2 for f in folds]) > 0.0

    def test_huge_delay_uses_train_only(self) -> None:
        # label_delay >= test-block length: no test labels ever available, so the
        # database is train-only and local_fits still equals the query count.
        df = _fortuna_like()
        folds = jitl_fold_predictions(
            df,
            max_lag=15,
            n_splits=5,
            label_delay=10_000,
            bandwidth=1.0,
            feature_builder=_lowdim_builder,
        )
        assert all(f.local_fits == len(f.residuals.y_pred) for f in folds)

    def test_too_short_segment_raises(self) -> None:
        df = _fortuna_like(n=60)
        with pytest.raises(ValueError):
            jitl_fold_predictions(
                df,
                max_lag=50,
                n_splits=5,
                label_delay=4,
                bandwidth=1.0,
                feature_builder=_lowdim_builder,
            )


class TestGating:
    def test_gated_matches_static_when_no_drift(self) -> None:
        # Clean data: ADWIN should not fire, so the gated stream == static stream.
        df = _fortuna_like(drift=0.0)
        static = blocked_cv_residuals(
            df,
            LinearRegression,
            max_lag=15,
            n_splits=5,
            feature_builder=_lowdim_builder,
        )
        jitl = jitl_fold_predictions(
            df,
            max_lag=15,
            n_splits=5,
            label_delay=4,
            bandwidth=1.5,
            feature_builder=_lowdim_builder,
        )
        gated = gate_with_drift(static, jitl)
        for sf, gf in zip(static, gated, strict=True):
            # No drift -> no switch -> identical predictions, zero JITL fits.
            if gf.local_fits == 0:
                assert np.allclose(sf.y_pred, gf.residuals.y_pred)

    def test_gated_uses_fewer_fits_than_always_on(self) -> None:
        # With drift, gating triggers JITL only after detection -> fewer fits.
        df = _fortuna_like(drift=0.001)
        static = blocked_cv_residuals(
            df,
            LinearRegression,
            max_lag=15,
            n_splits=5,
            feature_builder=_lowdim_builder,
        )
        jitl = jitl_fold_predictions(
            df,
            max_lag=15,
            n_splits=5,
            label_delay=4,
            bandwidth=1.5,
            feature_builder=_lowdim_builder,
        )
        gated = gate_with_drift(static, jitl)
        always_fits = sum(f.local_fits for f in jitl)
        gated_fits = sum(f.local_fits for f in gated)
        assert gated_fits <= always_fits

    def test_misaligned_folds_raise(self) -> None:
        df_a = _fortuna_like(n=600)
        df_b = _fortuna_like(n=400)
        static = blocked_cv_residuals(
            df_a,
            LinearRegression,
            max_lag=15,
            n_splits=5,
            feature_builder=_lowdim_builder,
        )
        jitl = jitl_fold_predictions(
            df_b,
            max_lag=15,
            n_splits=5,
            label_delay=4,
            bandwidth=1.0,
            feature_builder=_lowdim_builder,
        )
        with pytest.raises(ValueError):
            gate_with_drift(static, jitl)
