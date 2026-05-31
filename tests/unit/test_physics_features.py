"""Tests for physics-motivated features (Path B).

Checks the vectorized vapor pressure against Perry's check values, the
relative-volatility ordering (C4 more volatile than C6), bubble-point bounds,
the multivariate stripping-factor construction, and leakage-safe shapes for the
physics-anchored feature builders.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ipis.module1_soft_sensor.features.physics_features import (
    PHYSICS_FEATURE_COLS,
    _psat_vec,
    add_physics_features,
    make_physics_anchored_features,
    make_u5_only_features,
)
from ipis.physics.dippr101 import N_BUTANE


def _df(n: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # Mid-range normalized inputs so denormalized T stays in the valid window.
    cols = {c: rng.uniform(0.3, 0.7, n) for c in ["u1", "u2", "u3", "u4", "u5", "u6", "u7"]}
    df = pd.DataFrame(cols)
    df["y"] = rng.uniform(0, 1, n)
    return df


class TestPsatVec:
    def test_butane_tmax_checkvalue(self) -> None:
        # Vectorized psat must match Perry's Table 2-8 at Tmax.
        val = _psat_vec(np.array([425.12]), N_BUTANE)[0]
        assert val == pytest.approx(3.770e6, rel=0.01)

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="outside valid range"):
            _psat_vec(np.array([450.0]), N_BUTANE)  # > butane t_max


class TestAddPhysicsFeatures:
    def test_adds_expected_columns(self) -> None:
        out = add_physics_features(_df())
        for c in PHYSICS_FEATURE_COLS:
            assert c in out.columns

    def test_relative_volatility_gt_one(self) -> None:
        # C4 is more volatile than C6 -> alpha > 1 everywhere in range.
        out = add_physics_features(_df())
        assert (out["rel_volatility"] > 1.0).all()

    def test_bubble_point_in_unit_interval(self) -> None:
        out = add_physics_features(_df())
        assert out["bubble_point_c4"].between(0.0, 1.0).all()

    def test_stripping_factor_is_alpha_times_reflux(self) -> None:
        df = _df()
        out = add_physics_features(df)
        expected = out["rel_volatility"] * df["u3"]
        assert np.allclose(out["stripping_factor"], expected)

    def test_missing_column_raises(self) -> None:
        df = _df().drop(columns=["u3"])
        with pytest.raises(ValueError, match="Column 'u3' not found"):
            add_physics_features(df)


class TestMakePhysicsAnchoredFeatures:
    def test_shapes_with_u5(self) -> None:
        # 3 physics features + u5 = 4 columns; n - lag rows.
        X, y = make_physics_anchored_features(_df(40), transport_lag=10, include_raw_u5=True)
        assert X.shape == (30, 4)
        assert len(y) == 30
        assert not X.isna().any().any()

    def test_shapes_without_u5(self) -> None:
        X, y = make_physics_anchored_features(_df(40), transport_lag=10, include_raw_u5=False)
        assert X.shape == (30, 3)

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="transport_lag"):
            make_physics_anchored_features(_df(8), transport_lag=10)


class TestMakeU5OnlyFeatures:
    def test_single_feature_shape(self) -> None:
        X, y = make_u5_only_features(_df(40), transport_lag=10)
        assert X.shape == (30, 1)
        assert len(y) == 30

    def test_lag_alignment(self) -> None:
        # Deterministic u5 so the shift is checkable.
        df = pd.DataFrame(
            {
                "u1": 0.5,
                "u2": 0.5,
                "u3": 0.5,
                "u4": 0.5,
                "u5": np.arange(20, dtype=float) / 20.0,
                "u6": 0.5,
                "u7": 0.5,
                "y": np.arange(20, dtype=float),
            }
        )
        X, y = make_u5_only_features(df, transport_lag=5)
        # Row 0 -> original t=5; u5_lag5 = u5(0) = 0.0; y = y(5) = 5.
        assert X["u5_lag5"].iloc[0] == pytest.approx(0.0)
        assert y.iloc[0] == pytest.approx(5.0)


def test_end_to_end_physics_feeds_linear_model() -> None:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    df = _df(300, seed=1)
    X, y = make_physics_anchored_features(df, transport_lag=15)
    Xs = StandardScaler().fit_transform(X)
    model = LinearRegression().fit(Xs, y)
    pred = model.predict(Xs)
    assert pred.shape == (len(y),)
    assert np.isfinite(pred).all()
