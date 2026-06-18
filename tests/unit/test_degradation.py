"""Tests for the degradation index and first-prediction-time (Phase 2B)."""

from __future__ import annotations

import numpy as np

from ipis.module2_pdm.rul.degradation import (
    degradation_index,
    ema,
    first_prediction_time,
    robust_baseline_window,
    robust_first_prediction_time,
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


def test_robust_baseline_skips_runin_and_onset():
    # run-in (high-variance head) -> flat plateau -> rising onset; baseline must
    # land in the plateau, not the head and not the rise.
    rng = np.random.RandomState(0)
    runin = 9.0 + 8.0 * rng.randn(40, 4)  # noisy head
    plateau = 9.0 + 0.3 * rng.randn(200, 4)  # quiet
    rise = np.linspace(9.0, 200.0, 120)[:, None] + 0.3 * rng.randn(120, 4)
    feats = np.vstack([runin, plateau, rise])
    start, w = robust_baseline_window(feats, window=100)
    assert 40 <= start <= 140  # inside the plateau (after run-in, before the rise)
    assert w == 100


def test_robust_fpt_only_after_baseline():
    rng = np.random.RandomState(1)
    # run-in spike at the head would trip a naive detector at index 0
    head = np.concatenate([np.full(5, 50.0), 9.0 + 0.3 * rng.randn(195)])
    rise = np.linspace(9.0, 3000.0, 100)
    t2 = np.concatenate([head, rise])
    # naive FPT fires at the head spike...
    assert first_prediction_time(t2, warn_limit=16.9, persist=3) <= 5
    # ...robust FPT (scanning only after the baseline window) fires at the real rise
    fpt = robust_first_prediction_time(t2, baseline_end=200, warn_limit=16.9, persist=3)
    assert fpt is not None and fpt >= 200
