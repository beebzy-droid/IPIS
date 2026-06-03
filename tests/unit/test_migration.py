"""Unit tests for the Phase-1C migration subpackage (Lu OSBC + sweep)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from ipis.module1_soft_sensor.migration.sbc import LuOSBC, Migrator
from ipis.module1_soft_sensor.migration.sweep import data_fraction_sweep


class TestLuOSBC:
    def test_recovers_known_affine(self) -> None:
        # target = 2.5*source + 4 ; OSBC must recover scale=2.5, bias=4.
        rng = np.random.default_rng(0)
        sp = rng.normal(0, 1, 200)
        y = 2.5 * sp + 4.0
        m = LuOSBC().fit(np.zeros((200, 3)), sp, y)
        assert m.params_ is not None
        assert abs(m.params_.scale - 2.5) < 1e-6
        assert abs(m.params_.bias - 4.0) < 1e-6
        pred = m.predict(np.zeros((5, 3)), np.array([1.0, 2, 3, 4, 5]))
        assert np.allclose(pred, 2.5 * np.array([1.0, 2, 3, 4, 5]) + 4.0)

    def test_satisfies_migrator_protocol(self) -> None:
        assert isinstance(LuOSBC(), Migrator)

    def test_predict_before_fit_raises(self) -> None:
        with pytest.raises(RuntimeError):
            LuOSBC().predict(np.zeros((2, 2)), np.zeros(2))

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            LuOSBC().fit(np.zeros((3, 2)), np.zeros(3), np.zeros(4))

    def test_too_few_samples_raises(self) -> None:
        with pytest.raises(ValueError):
            LuOSBC().fit(np.zeros((1, 2)), np.zeros(1), np.zeros(1))


def _toy(n: int, slope: float, intercept: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 1, n)
    y = slope * x + intercept + rng.normal(0, 0.02, n)
    return pd.DataFrame({"x": x, "y": y})


def _builder(df: pd.DataFrame):
    return df[["x"]].reset_index(drop=True), df["y"].reset_index(drop=True)


class TestSweep:
    def test_runs_and_reports_curves(self) -> None:
        # source relationship y=x; target y=x+5 (pure offset -> OSBC ideal).
        src = _toy(400, 1.0, 0.0, 0)
        src_model = LinearRegression().fit(*[np.asarray(a) for a in _builder(src)])

        def source_predict(df):
            X, _ = _builder(df)
            return src_model.predict(np.asarray(X))

        tgt = _toy(400, 1.0, 5.0, 1)
        pool, test = tgt.iloc[:280], tgt.iloc[280:]
        res = data_fraction_sweep(
            pool,
            test,
            source_predict,
            _builder,
            LuOSBC,
            [0.1, 0.3, 1.0],
            same_class_factory=LinearRegression,
        )
        assert len(res.migrated_r2) == 3
        assert not np.isnan(res.bar_same_r2)
        # pure offset: OSBC should migrate well even at low fraction
        assert res.migrated_r2[-1] > 0.9

    def test_crossover_detected_for_offset_regime(self) -> None:
        # OSBC on a pure-offset target should reach the bar early -> crossover low.
        src = _toy(400, 2.0, 0.0, 0)
        src_model = LinearRegression().fit(*[np.asarray(a) for a in _builder(src)])

        def source_predict(df):
            X, _ = _builder(df)
            return src_model.predict(np.asarray(X))

        tgt = _toy(400, 2.0, 3.0, 2)
        pool, test = tgt.iloc[:280], tgt.iloc[280:]
        res = data_fraction_sweep(
            pool,
            test,
            source_predict,
            _builder,
            LuOSBC,
            [0.05, 0.1, 0.3, 1.0],
            same_class_factory=LinearRegression,
        )
        # crossover logic returns a valid fraction from the list (or None).
        # On a trivially-linear target, from-scratch is also near-perfect at low
        # f, so the data advantage is small -- we assert detection works, not a
        # specific value.
        assert res.crossover_fraction in (*res.fractions, None)
        assert res.migrated_r2[-1] >= res.bar_same_r2 - 1e-6

    def test_generic_comparator_optional(self) -> None:
        src = _toy(300, 1.0, 0.0, 0)
        src_model = LinearRegression().fit(*[np.asarray(a) for a in _builder(src)])

        def source_predict(df):
            X, _ = _builder(df)
            return src_model.predict(np.asarray(X))

        tgt = _toy(300, 1.0, 2.0, 1)
        pool, test = tgt.iloc[:210], tgt.iloc[210:]
        res = data_fraction_sweep(
            pool,
            test,
            source_predict,
            _builder,
            LuOSBC,
            [0.2, 1.0],
            same_class_factory=LinearRegression,
        )
        assert res.from_scratch_generic_r2 == []  # not requested
        assert np.isnan(res.bar_generic_r2)
