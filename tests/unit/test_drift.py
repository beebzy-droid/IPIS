"""Unit tests for evaluation.drift (Phase 1B residual drift detection)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from ipis.module1_soft_sensor.evaluation.blocked_cv import blocked_cv_r2
from ipis.module1_soft_sensor.evaluation.drift import (
    CUSUM,
    DriftScan,
    blocked_cv_residuals,
    build_detectors,
    concat_residual_stream,
    make_adwin,
    make_page_hinkley,
    scan,
)

_RNG = np.random.default_rng(0)


def _shift_stream(
    sigma: float = 0.10, n: int = 1000, shift_at: int = 500, shift: float = 0.15
) -> np.ndarray:
    res = _RNG.normal(0.0, sigma, n)
    res[shift_at:] += shift
    return res


def _fortuna_like(n: int = 600, seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    u = rng.uniform(0.2, 0.8, size=(n, 7))
    df = pd.DataFrame(u, columns=[f"u{i}" for i in range(1, 8)])
    # y driven by u5 at lag 15 plus noise (signal the lagged model can fit).
    u5 = df["u5"].to_numpy()
    y = np.empty(n)
    y[:15] = 0.3
    y[15:] = 0.6 * u5[:-15] + rng.normal(0, 0.02, n - 15)
    df["y"] = y
    return df


# --------------------------------------------------------------------------- #
# CUSUM
# --------------------------------------------------------------------------- #
class TestCUSUM:
    def test_rejects_nonpositive_params(self) -> None:
        with pytest.raises(ValueError):
            CUSUM(k=0.0, h=1.0)
        with pytest.raises(ValueError):
            CUSUM(k=0.1, h=0.0)

    def test_flat_in_control_stream_never_fires(self) -> None:
        det = CUSUM(k=0.05, h=0.5)
        assert not any(det.update(0.0) for _ in range(1000))

    def test_detects_positive_mean_shift(self) -> None:
        det = CUSUM(k=0.05, h=0.5)
        s = scan(_shift_stream(), det)
        assert s.n_detections >= 1
        assert s.first_fire_at_or_after(500) is not None

    def test_detects_negative_mean_shift(self) -> None:
        det = CUSUM(k=0.05, h=0.5)
        res = _RNG.normal(0.0, 0.10, 1000)
        res[500:] -= 0.20
        s = scan(res, det)
        assert s.first_fire_at_or_after(500) is not None

    def test_resets_sums_after_detection(self) -> None:
        det = CUSUM(k=0.05, h=0.3)
        for _ in range(50):
            det.update(0.5)  # force a detection
        det.reset()
        assert det._c_hi == 0.0 and det._c_lo == 0.0
        assert not det.drift_detected

    def test_arl0_matches_textbook_at_h4sigma(self) -> None:
        # k=0.5sigma, h=4sigma two-sided -> ARL0 ~ 168 (Montgomery).
        sigma = 0.10
        big = np.random.default_rng(123).normal(0.0, sigma, 400_000)
        det = CUSUM(k=0.5 * sigma, h=4.0 * sigma)
        last, rls = 0, []
        for i, x in enumerate(big):
            if det.update(float(x)):
                rls.append(i - last)
                last = i
        arl0 = float(np.mean(rls))
        assert 140 < arl0 < 200  # within tolerance of the textbook 168


# --------------------------------------------------------------------------- #
# river-backed detectors
# --------------------------------------------------------------------------- #
class TestRiverDetectors:
    def test_adwin_detects_shift_and_names(self) -> None:
        det = make_adwin()
        assert det.name.startswith("ADWIN")
        s = scan(_shift_stream(), det)
        assert s.first_fire_at_or_after(500) is not None

    def test_adwin_no_false_alarm_in_control(self) -> None:
        det = make_adwin(delta=0.002)
        noise = np.random.default_rng(5).normal(0.0, 0.10, 5000)
        s = scan(noise, det)
        assert s.n_detections == 0

    def test_page_hinkley_detects_shift(self) -> None:
        det = make_page_hinkley(delta=0.05, threshold=0.8)
        s = scan(_shift_stream(), det)
        assert s.first_fire_at_or_after(500) is not None

    def test_reset_makes_scan_independent(self) -> None:
        det = make_adwin()
        stream = _shift_stream()  # one fixed array, scanned twice
        s1 = scan(stream, det)
        s2 = scan(stream, det)  # scan() resets internally -> identical result
        assert s1.fire_indices == s2.fire_indices


# --------------------------------------------------------------------------- #
# build_detectors
# --------------------------------------------------------------------------- #
class TestBuildDetectors:
    def test_rejects_nonpositive_sigma(self) -> None:
        with pytest.raises(ValueError):
            build_detectors(0.0)

    def test_returns_trio_in_order(self) -> None:
        dets = build_detectors(0.10)
        assert len(dets) == 3
        assert dets[0].name.startswith("ADWIN")
        assert dets[1].name.startswith("PageHinkley")
        assert dets[2].name == "CUSUM"

    def test_trio_all_detect_known_shift(self) -> None:
        stream = _shift_stream()
        for det in build_detectors(0.10):
            s = scan(stream, det)
            assert s.first_fire_at_or_after(500) is not None, det.name


# --------------------------------------------------------------------------- #
# scan / DriftScan
# --------------------------------------------------------------------------- #
class TestScan:
    def test_counts_samples_and_empty_stream(self) -> None:
        s = scan([], CUSUM(k=0.05, h=0.5))
        assert s.n_samples == 0
        assert s.n_detections == 0

    def test_latency_helpers(self) -> None:
        s = DriftScan("x", n_samples=100, fire_indices=[10, 60, 80])
        assert s.first_fire_at_or_after(50) == 60
        assert s.detection_latency(50) == 10
        assert s.first_fire_at_or_after(90) is None
        assert s.detection_latency(90) is None

    def test_cooldown_collapses_sustained_flood(self) -> None:
        # Sustained large shift makes CUSUM re-fire every sample; cooldown
        # should collapse that into far fewer distinct trigger events.
        res = np.concatenate([np.zeros(100), np.full(400, 0.5)])
        det = CUSUM(k=0.05, h=0.3)
        no_cd = scan(res, det, cooldown=0)
        with_cd = scan(res, det, cooldown=50)
        assert with_cd.n_detections < no_cd.n_detections
        assert with_cd.first_fire_at_or_after(100) is not None

    def test_cooldown_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            scan([0.0, 1.0], CUSUM(k=0.05, h=0.3), cooldown=-1)


# --------------------------------------------------------------------------- #
# blocked_cv_residuals (the equivalence pin)
# --------------------------------------------------------------------------- #
class TestBlockedCvResiduals:
    def test_shapes_and_fold_count(self) -> None:
        df = _fortuna_like()
        folds = blocked_cv_residuals(df, LinearRegression, max_lag=15, n_splits=5)
        assert len(folds) == 5
        for f in folds:
            assert f.y_true.shape == f.y_pred.shape
            assert f.residuals.shape == f.y_true.shape

    def test_matches_blocked_cv_r2(self) -> None:
        # The pin: per-fold R^2 from residuals must equal blocked_cv_r2 exactly.
        df = _fortuna_like()
        r2_direct = blocked_cv_r2(df, LinearRegression, max_lag=15, n_splits=5)
        folds = blocked_cv_residuals(df, LinearRegression, max_lag=15, n_splits=5)
        r2_from_res = [f.r2 for f in folds]
        assert np.allclose(r2_direct, r2_from_res, atol=1e-12)

    def test_concat_stream_length(self) -> None:
        df = _fortuna_like()
        folds = blocked_cv_residuals(df, LinearRegression, max_lag=15, n_splits=5)
        stream = concat_residual_stream(folds)
        assert stream.shape[0] == sum(len(f.residuals) for f in folds)

    def test_too_short_segment_raises(self) -> None:
        df = _fortuna_like(n=60)
        with pytest.raises(ValueError):
            blocked_cv_residuals(df, LinearRegression, max_lag=50, n_splits=5)
