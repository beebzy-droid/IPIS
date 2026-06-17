"""Tests for RUL features, PHM-2012 score, and the RUL regressor (Phase 2B)."""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module2_pdm.rul.degradation import degradation_index, first_prediction_time
from ipis.module2_pdm.rul.rul_model import (
    RULModel,
    lower_bound_coverage,
    phm2012_score,
    rul_feature_matrix,
)


def test_rul_features_shape_and_causal_slope():
    di = np.array([1.0, 1.0, 2.0, 4.0])
    X = rul_feature_matrix(di)
    assert X.shape == (4, 2)
    assert X[0, 1] == 0.0  # first slope defined as 0
    # slope is backward diff of log1p(level)
    assert X[2, 1] == pytest.approx(np.log1p(2.0) - np.log1p(1.0))


def test_phm2012_perfect_score_is_one():
    rul = np.array([100.0, 50.0, 10.0])
    assert phm2012_score(rul, rul) == pytest.approx(1.0)


def test_phm2012_late_5pct_scores_half():
    # over-estimate RUL by 5% (Er = -5) -> 0.5 (late, harsh)
    actual = np.array([100.0])
    pred = np.array([105.0])
    assert phm2012_score(pred, actual) == pytest.approx(0.5, abs=1e-6)


def test_phm2012_early_20pct_scores_half():
    # under-estimate RUL by 20% (Er = +20) -> 0.5 (early, lenient)
    actual = np.array([100.0])
    pred = np.array([80.0])
    assert phm2012_score(pred, actual) == pytest.approx(0.5, abs=1e-6)


def test_phm2012_late_penalized_harder_than_early():
    actual = np.array([100.0])
    late = phm2012_score(np.array([110.0]), actual)  # 10% late
    early = phm2012_score(np.array([90.0]), actual)  # 10% early
    assert late < early


def _synth_bearing(seed, life=160, onset=80, rate=0.06):
    """Synthetic run-to-failure T2 from a common process (flat healthy -> exp rise)."""
    rng = np.random.RandomState(seed)
    r = rate * (1.0 + 0.03 * rng.randn())  # small rate jitter
    t2 = np.empty(life)
    t2[:onset] = 9.0 + 0.5 * rng.randn(onset)
    k = np.arange(life - onset)
    t2[onset:] = 9.0 + np.exp(r * k) + 0.5 * rng.randn(life - onset)
    rul = (life - 1 - np.arange(life)).astype(float)  # snapshots-to-failure
    return np.abs(t2), rul


def _post_fpt(t2, rul, warn=16.9):
    di = degradation_index(t2, alpha=0.05)
    fpt = first_prediction_time(t2, warn_limit=warn, persist=3)
    fpt = 0 if fpt is None else fpt
    return di[fpt:], rul[fpt:]


def test_rul_leave_one_bearing_out_synthetic():
    # five bearings from a common degradation process (exchangeable)
    bearings = [_post_fpt(*_synth_bearing(seed=s)) for s in range(5)]

    test_idx = 4
    train = [b for i, b in enumerate(bearings) if i != test_idx]
    di_test, rul_test = bearings[test_idx]

    # calibrate the conformal back-off on one held-out training bearing
    di_cal, rul_cal = train[0]
    di_fit = np.concatenate([b[0] for b in train[1:]])
    rul_fit = np.concatenate([b[1] for b in train[1:]])

    model = RULModel.fit(di_fit, rul_fit, alpha=0.1, di_calib=di_cal, rul_calib=rul_cal)
    pred = model.predict(di_test)
    lower = model.lower_bound(di_test)
    assert lower.shape == pred.shape and np.all(np.isfinite(lower))

    horizon = rul_test >= 10.0
    assert phm2012_score(pred[horizon], rul_test[horizon]) > 0.4
    # predictions decrease as the bearing degrades (RUL falls)
    assert np.corrcoef(pred, rul_test)[0, 1] > 0.8
    # NOTE: the conformal lower bound may sit ABOVE the point prediction when the
    # regressor is biased low -- its guarantee is coverage P(RUL>=L)>=1-alpha, not
    # position vs the point estimate. Tight coverage is NOT asserted here: split
    # conformal guarantees only MARGINAL coverage under exchangeability, which a
    # single held-out-bearing trajectory violates. Marginal coverage is tested below.


def test_conformal_lower_bound_marginal_coverage():
    # Pool snapshots across bearings and split randomly -> exchangeable calib/test.
    # Conformal is model-agnostic, so the lower bound must cover >= 1 - alpha here
    # regardless of regressor misspecification.
    bearings = [_post_fpt(*_synth_bearing(seed=s)) for s in range(8)]
    di = np.concatenate([b[0] for b in bearings])
    rul = np.concatenate([b[1] for b in bearings])
    rng = np.random.RandomState(0)
    idx = rng.permutation(len(di))
    n = len(di)
    fit_i, cal_i, test_i = idx[: n // 2], idx[n // 2 : 3 * n // 4], idx[3 * n // 4 :]
    model = RULModel.fit(di[fit_i], rul[fit_i], alpha=0.1, di_calib=di[cal_i], rul_calib=rul[cal_i])
    cov = lower_bound_coverage(rul[test_i], model.lower_bound(di[test_i]))
    assert cov >= 0.85  # target 0.90, finite-sample tolerance


def test_phm2012_requires_positive_actual():
    with pytest.raises(ValueError):
        phm2012_score(np.array([0.0]), np.array([0.0]))
