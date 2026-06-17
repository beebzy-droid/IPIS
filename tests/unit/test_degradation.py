"""Tests for the degradation index and first-prediction-time (Phase 2B)."""

from __future__ import annotations

import numpy as np

from ipis.module2_pdm.rul.degradation import (
    degradation_index,
    ema,
    first_prediction_time,
)


def test_ema_smooths_and_is_causal():
    x = np.array([0.0, 10.0, 0.0, 0.0, 0.0])
    s = ema(x, alpha=0.5)
    # the spike is attenuated and bleeds forward (causal), never exceeds input peak
    assert s[1] < 10.0
    assert s[2] > 0.0  # memory of the spike persists
    assert np.all(s <= 10.0)


def test_degradation_index_is_monotone():
    rng = np.random.RandomState(0)
    t2 = np.concatenate([9 + rng.randn(50), np.linspace(9, 5000, 50)])
    di = degradation_index(t2, alpha=0.05)
    assert np.all(np.diff(di) >= -1e-9)  # non-decreasing
    assert di[-1] > di[0]


def test_degradation_index_causal_prefix_invariant():
    # DI at time t must not depend on future samples (streaming-safe)
    rng = np.random.RandomState(1)
    t2 = np.concatenate([9 + rng.randn(40), np.linspace(9, 3000, 40)])
    di_full = degradation_index(t2, alpha=0.1)
    di_prefix = degradation_index(t2[:30], alpha=0.1)
    assert np.allclose(di_full[:30], di_prefix, atol=1e-9)


def test_fpt_detects_onset_not_runin():
    # flat healthy, then a sustained rise; FPT should land near the rise, not at 0
    healthy = np.full(100, 9.0)
    rise = np.linspace(9.0, 2000.0, 100)
    t2 = np.concatenate([healthy, rise])
    fpt = first_prediction_time(t2, warn_limit=16.9, alpha=0.1, persist=3)
    assert fpt is not None
    assert 100 <= fpt <= 130  # onset is at/after the healthy->rise boundary


def test_fpt_none_when_always_healthy():
    t2 = np.full(200, 9.0)
    assert first_prediction_time(t2, warn_limit=16.9) is None
