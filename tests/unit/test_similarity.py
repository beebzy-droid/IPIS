"""Tests for trajectory-similarity RUL (Phase 2B, Option B)."""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module2_pdm.rul.rul_model import phm2012_score
from ipis.module2_pdm.rul.similarity import SimilarityRUL, _best_match, _shape


def test_shape_centering_removes_offset():
    x = np.array([1.0, 2.0, 4.0])
    assert np.allclose(_shape(x), _shape(x + 100.0))  # vertical offset removed


def test_best_match_finds_embedded_shape():
    # a curved signature embedded in a longer trajectory at a known place, + offset
    sig = np.array([0.0, 1.0, 4.0, 9.0])  # rising, curved
    hi = np.concatenate([np.zeros(20), sig + 50.0, np.full(5, 9.0 + 50.0)])
    end, d = _best_match(_shape(sig), hi)
    assert end == 23  # last sample of the embedded signature (20 + 4 - 1)
    assert d < 1e-9  # exact shape match despite the +50 offset


def _arc(scale, life, p=2.0, seed=0):
    """Curved monotone degradation arc DI = scale*exp(3*(k/life)^p); hi = log1p(DI)."""
    rng = np.random.RandomState(seed)
    k = np.arange(life)
    di = scale * np.exp(3.0 * (k / life) ** p) * (1.0 + 0.02 * rng.randn(life))
    hi = np.log1p(np.abs(di))
    rul = (life - 1 - k).astype(float)
    return hi, rul


def test_predict_invariant_to_16000x_scale_spread():
    # library bearings span a 100000x scale range (the regression-killing spread),
    # similar lives, same shape. Similarity must recover RUL regardless of scale.
    library = [
        _arc(scale=1.0, life=150, seed=1),
        _arc(scale=50.0, life=145, seed=2),
        _arc(scale=2000.0, life=155, seed=3),
        _arc(scale=100000.0, life=150, seed=4),
    ]
    model = SimilarityRUL(library, interval=1.0)
    hi_test, rul_test = _arc(scale=500.0, life=150, seed=9)  # unseen scale

    fracs = np.arange(0.40, 0.96, 0.05)
    preds, trues = [], []
    for f in fracs:
        t = int(f * len(hi_test))
        preds.append(model.predict_one(hi_test[:t]))
        trues.append(rul_test[t])
    preds, trues = np.array(preds), np.array(trues)
    assert phm2012_score(preds, trues) > 0.4
    # predictions decrease as the bearing ages
    assert np.corrcoef(preds, trues)[0, 1] > 0.7


def test_short_library_trajectory_handled():
    library = [(_arc(1.0, 150)[0], _arc(1.0, 150)[1]), (np.array([0.0, 1.0]), np.array([1.0, 0.0]))]
    model = SimilarityRUL(library, interval=1.0)
    hi_test, _ = _arc(1.0, 150, seed=7)
    out = model.predict_one(hi_test[:100])
    assert np.isfinite(out)


def test_insufficient_signal_returns_max_uncertainty():
    library = [_arc(1.0, 120, seed=1), _arc(1.0, 200, seed=2)]
    model = SimilarityRUL(library, interval=1.0)
    # a single-sample window -> not enough shape; fall back to longest library life
    out = model.predict_one(np.array([3.0]))
    assert out == pytest.approx(199.0)  # max rul[0] across library (life 200 -> 199)


def test_empty_library_raises():
    with pytest.raises(ValueError):
        SimilarityRUL([])


def test_invalid_mode_raises():
    with pytest.raises(ValueError):
        SimilarityRUL([_arc(1.0, 120)], mode="bogus")


def test_absolute_mode_recovers_rul_similar_lives():
    # similar lives so absolute read-off is valid; different scales (offset removed)
    library = [
        _arc(scale=1.0, life=150, seed=1),
        _arc(scale=2000.0, life=150, seed=2),
        _arc(scale=100000.0, life=150, seed=3),
    ]
    model = SimilarityRUL(library, interval=1.0, mode="absolute")
    hi_test, rul_test = _arc(scale=500.0, life=150, seed=9)
    fracs = np.arange(0.40, 0.96, 0.05)
    preds = np.array([model.predict_one(hi_test[: int(f * len(hi_test))]) for f in fracs])
    trues = np.array([rul_test[int(f * len(hi_test))] for f in fracs])
    assert phm2012_score(preds, trues) > 0.4
