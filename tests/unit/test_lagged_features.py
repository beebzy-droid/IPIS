"""Tests for lagged-feature construction.

Verifies correct lag alignment, the drop of insufficient-history rows, column
naming/order, and the per-segment contract that prevents cross-boundary
leakage. A small end-to-end check confirms the features feed a PLS fit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ipis.module1_soft_sensor.features.lagged import (
    lagged_feature_names,
    make_lagged_features,
)


def _toy(n: int = 30) -> pd.DataFrame:
    # Distinct, monotone columns so lag alignment is checkable by eye.
    return pd.DataFrame(
        {
            "u1": np.arange(n, dtype=float),
            "u2": np.arange(n, dtype=float) * 10,
            "u3": np.arange(n, dtype=float),
            "u4": np.arange(n, dtype=float),
            "u5": np.arange(n, dtype=float),
            "u6": np.arange(n, dtype=float),
            "u7": np.arange(n, dtype=float),
            "y": np.arange(n, dtype=float) * 100,
        }
    )


class TestLaggedFeatureNames:
    def test_order_and_content(self) -> None:
        names = lagged_feature_names(["u1", "u2"], max_lag=2)
        assert names == [
            "u1_lag0",
            "u1_lag1",
            "u1_lag2",
            "u2_lag0",
            "u2_lag1",
            "u2_lag2",
        ]

    def test_negative_lag_raises(self) -> None:
        with pytest.raises(ValueError, match="max_lag must be >= 0"):
            lagged_feature_names(["u1"], -1)


class TestMakeLaggedFeatures:
    def test_shapes_and_row_drop(self) -> None:
        df = _toy(30)
        X, y = make_lagged_features(df, max_lag=5)
        # 30 rows - 5 dropped = 25; 7 inputs * (5+1) lags = 42 features.
        assert X.shape == (25, 42)
        assert len(y) == 25

    def test_no_nans_after_drop(self) -> None:
        X, y = make_lagged_features(_toy(30), max_lag=5)
        assert not X.isna().any().any()
        assert not y.isna().any()

    def test_lag_alignment(self) -> None:
        # Row 0 of output is original row index max_lag. u1_lag0 = u1(t),
        # u1_lag1 = u1(t-1), etc. With u1 = 0,1,2,..., at t=5: lag0=5, lag1=4, lag3=2.
        X, y = make_lagged_features(_toy(30), max_lag=5)
        assert X["u1_lag0"].iloc[0] == pytest.approx(5.0)
        assert X["u1_lag1"].iloc[0] == pytest.approx(4.0)
        assert X["u1_lag3"].iloc[0] == pytest.approx(2.0)
        # Target is contemporaneous y(t): at t=5, y = 500.
        assert y.iloc[0] == pytest.approx(500.0)

    def test_target_is_contemporaneous(self) -> None:
        # y must align to the SAME t as lag0 (no peeking at future target).
        X, y = make_lagged_features(_toy(30), max_lag=3)
        # u5_lag0 at row 0 is u5(t=3)=3; y at row 0 is y(t=3)=300.
        assert X["u5_lag0"].iloc[0] == pytest.approx(3.0)
        assert y.iloc[0] == pytest.approx(300.0)

    def test_missing_column_raises(self) -> None:
        df = _toy(10).drop(columns=["u7"])
        with pytest.raises(ValueError, match="Columns not found"):
            make_lagged_features(df, max_lag=2)

    def test_segment_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="no rows would remain"):
            make_lagged_features(_toy(5), max_lag=5)

    def test_per_segment_contract_no_cross_boundary(self) -> None:
        # Building within two separate segments must NOT mix their values:
        # the second segment's lag history comes only from itself, and its
        # first max_lag rows are dropped (not filled from the first segment).
        full = _toy(40)
        seg_b = full.iloc[20:].reset_index(drop=True)
        Xb, yb = make_lagged_features(seg_b, max_lag=5)
        # First retained row of seg_b is its own index 5 -> original t=25.
        # u1 = 0..39, so seg_b row5 u1 = 25; lag5 = 20 (still within seg_b).
        assert Xb["u1_lag0"].iloc[0] == pytest.approx(25.0)
        assert Xb["u1_lag5"].iloc[0] == pytest.approx(20.0)
        assert len(yb) == 15  # 20 - 5


def test_end_to_end_feeds_pls() -> None:
    from sklearn.cross_decomposition import PLSRegression
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame({c: rng.uniform(0, 1, n) for c in ["u1", "u2", "u3", "u4", "u5", "u6", "u7"]})
    df["y"] = 0.7 * df["u5"].shift(5).fillna(0) + 0.05 * rng.standard_normal(n)
    X, y = make_lagged_features(df, max_lag=8)
    Xs = StandardScaler().fit_transform(X)
    model = PLSRegression(n_components=3).fit(Xs, y)
    pred = model.predict(Xs).ravel()
    assert pred.shape == (len(y),)
    assert np.isfinite(pred).all()
