"""Tests for blocked time-series CV and the 1-SE parsimony rule.

Covers: correct fold count, leakage-safe per-fold construction (a learnable
lagged signal scores positively), the segment-too-short guard, fresh estimator
per fold, and the 1-SE rule's parsimony behavior on hand-built inputs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.cross_decomposition import PLSRegression

from ipis.module1_soft_sensor.evaluation.blocked_cv import (
    blocked_cv_r2,
    mean_se,
    one_se_selection,
)


def _signal_df(n: int = 1200, lag: int = 5, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    u = {c: rng.uniform(0, 1, n) for c in ["u1", "u2", "u3", "u4", "u5", "u6", "u7"]}
    df = pd.DataFrame(u)
    df["y"] = 0.7 * df["u5"].shift(lag).fillna(0) + 0.04 * rng.standard_normal(n)
    return df


class TestBlockedCvR2:
    def test_returns_one_score_per_fold(self) -> None:
        df = _signal_df()
        scores = blocked_cv_r2(
            df,
            make_estimator=lambda: PLSRegression(n_components=3),
            max_lag=8,
            n_splits=5,
        )
        assert len(scores) == 5
        assert all(np.isfinite(s) for s in scores)

    def test_learnable_signal_scores_positive(self) -> None:
        df = _signal_df(lag=5)
        scores = blocked_cv_r2(
            df,
            make_estimator=lambda: PLSRegression(n_components=4),
            max_lag=8,
            n_splits=5,
        )
        assert np.mean(scores) > 0.3

    def test_segment_too_short_raises(self) -> None:
        df = _signal_df(n=120)
        with pytest.raises(ValueError, match="too short"):
            blocked_cv_r2(
                df,
                make_estimator=lambda: PLSRegression(n_components=2),
                max_lag=17,
                n_splits=10,
            )

    def test_fresh_estimator_each_fold(self) -> None:
        calls = {"n": 0}

        def factory() -> PLSRegression:
            calls["n"] += 1
            return PLSRegression(n_components=2)

        blocked_cv_r2(_signal_df(), make_estimator=factory, max_lag=8, n_splits=5)
        assert calls["n"] == 5


class TestOneSeSelection:
    def test_picks_simplest_within_one_se(self) -> None:
        ks = [1, 2, 3, 4, 5]
        means = [0.40, 0.58, 0.59, 0.60, 0.62]
        ses = [0.05, 0.05, 0.05, 0.05, 0.05]  # threshold = 0.62 - 0.05 = 0.57
        assert one_se_selection(ks, means, ses) == 2

    def test_falls_back_to_best_when_nothing_within_se(self) -> None:
        ks = [1, 2, 3]
        means = [0.10, 0.20, 0.90]
        ses = [0.01, 0.01, 0.01]  # threshold = 0.89; only k=3 qualifies
        assert one_se_selection(ks, means, ses) == 3

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="equal length"):
            one_se_selection([1, 2], [0.5], [0.1, 0.1])

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="No complexities"):
            one_se_selection([], [], [])


class TestMeanSe:
    def test_mean_and_se(self) -> None:
        m, se = mean_se([0.4, 0.5, 0.6])
        assert m == pytest.approx(0.5)
        assert se == pytest.approx(np.std([0.4, 0.5, 0.6], ddof=1) / np.sqrt(3))

    def test_single_value_se_zero(self) -> None:
        m, se = mean_se([0.5])
        assert m == pytest.approx(0.5)
        assert se == 0.0
