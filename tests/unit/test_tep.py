"""Unit tests for the TEP loader and physics-anchored features (Phase 1C).

Synthetic-data based so they run in CI without the gitignored TEP CSVs; the real
54-column format is validated separately during data generation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ipis.module1_soft_sensor.data.tep_loader import (
    TEP_N_COLUMNS,
    TEP_TARGET_XMEAS,
    TEPLoader,
)
from ipis.module1_soft_sensor.features.tep_physics_features import (
    add_tep_physics_features,
    diagnose_transport_lag,
    make_tep_physics_features,
)


def _write_synthetic_tep(path, n=300, seed=0):
    """Write a headerless 54-col TEP-format CSV with a learnable G signal."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) * 0.05
    xmeas = rng.normal(1.0, 0.1, (n, 41))
    xmeas[:, 1] = 3664 + rng.normal(0, 60, n)  # XMEAS_2 D feed
    xmeas[:, 2] = 4509 + rng.normal(0, 200, n)  # XMEAS_3 E feed
    xmeas[:, 8] = 120.4 + rng.normal(0, 0.1, n)  # XMEAS_9 reactor temp
    # G (XMEAS_40, index 39) driven by D/E ratio + noise
    xmeas[:, 39] = 30 + 50 * (xmeas[:, 1] / xmeas[:, 2]) + rng.normal(0, 0.3, n)
    xmv = rng.normal(50, 5, (n, 12))
    data = np.column_stack([t, xmeas, xmv])
    pd.DataFrame(data).to_csv(path, header=False, index=False)
    return data


class TestTEPLoader:
    def test_loads_named_columns_and_target(self, tmp_path):
        p = tmp_path / "tep_mode1.csv"
        _write_synthetic_tep(p)
        df = TEPLoader().load(p)
        assert df.shape[1] == TEP_N_COLUMNS + 1  # +y
        assert "XMEAS_40" in df.columns and "XMV_12" in df.columns and "time" in df.columns
        # y must equal the target composition column
        assert np.allclose(df["y"], df[f"XMEAS_{TEP_TARGET_XMEAS}"])

    def test_time_order_preserved(self, tmp_path):
        p = tmp_path / "tep.csv"
        _write_synthetic_tep(p)
        df = TEPLoader().load(p)
        assert df["time"].is_monotonic_increasing

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            TEPLoader().load("/nonexistent/tep.csv")

    def test_wrong_column_count_raises(self, tmp_path):
        p = tmp_path / "bad.csv"
        pd.DataFrame(np.zeros((10, 12))).to_csv(p, header=False, index=False)
        with pytest.raises(ValueError, match="columns"):
            TEPLoader().load(p)


class TestTEPPhysicsFeatures:
    def test_derived_features_added(self, tmp_path):
        p = tmp_path / "tep.csv"
        _write_synthetic_tep(p)
        df = TEPLoader().load(p)
        out = add_tep_physics_features(df)
        assert "DE_ratio" in out and "T_DE" in out
        assert np.allclose(out["DE_ratio"], df["XMEAS_2"] / df["XMEAS_3"])

    def test_shapes_and_lag_drop(self, tmp_path):
        p = tmp_path / "tep.csv"
        _write_synthetic_tep(p, n=300)
        df = TEPLoader().load(p)
        lag = 5
        X, y = make_tep_physics_features(df, transport_lag=lag)
        assert len(X) == len(df) - lag == len(y)
        assert all(c.endswith(f"_lag{lag}") for c in X.columns)
        # 8 base + 2 derived = 10 features
        assert X.shape[1] == 10

    def test_no_derived_gives_base_only(self, tmp_path):
        p = tmp_path / "tep.csv"
        _write_synthetic_tep(p)
        df = TEPLoader().load(p)
        X, _ = make_tep_physics_features(df, transport_lag=2, include_derived=False)
        assert X.shape[1] == 8
        assert not any("DE_ratio" in c or "T_DE" in c for c in X.columns)

    def test_negative_lag_raises(self, tmp_path):
        p = tmp_path / "tep.csv"
        _write_synthetic_tep(p)
        df = TEPLoader().load(p)
        with pytest.raises(ValueError):
            make_tep_physics_features(df, transport_lag=-1)

    def test_features_carry_signal(self, tmp_path):
        # On synthetic data where G = f(D/E), an OLS on the features must fit well.
        from sklearn.linear_model import LinearRegression

        p = tmp_path / "tep.csv"
        _write_synthetic_tep(p, n=500)
        df = TEPLoader().load(p)
        X, y = make_tep_physics_features(df, transport_lag=0)
        r2 = LinearRegression().fit(X, y).score(X, y)
        assert r2 > 0.8  # strong by construction

    def test_diagnose_lag_returns_valid_range(self, tmp_path):
        p = tmp_path / "tep.csv"
        _write_synthetic_tep(p)
        df = TEPLoader().load(p)
        lag = diagnose_transport_lag(df, max_lag=20)
        assert 0 <= lag <= 20
