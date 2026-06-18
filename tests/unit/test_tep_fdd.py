"""Tests for the Phase-2C fault-detection scoring (ipis.module2_pdm.health.fdd).

Unit tests cover the pure persistence/delay logic on hand-built exceedance and
T^2 streams. One integration test fits a real HealthIndexModel on synthetic
healthy data and asserts a clear step fault is detected promptly while a
fault-free stream is not, mirroring how the TEP scorecard is computed.
"""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module2_pdm.health.fdd import false_alarm_rate, first_sustained, score_run
from ipis.module2_pdm.health.health_index import HealthIndexModel


def test_first_sustained_basic():
    # first run of 3 consecutive True starts at index 2
    over = [False, False, True, True, True, False]
    assert first_sustained(over, 0, 3) == 2


def test_first_sustained_requires_full_run():
    # only 2 consecutive -> not enough for persist=3
    assert first_sustained([True, True, False, True, True], 0, 3) is None


def test_first_sustained_respects_start():
    # an early sustained run before `start` is ignored
    over = [True, True, True, False, False, True, True, True]
    assert first_sustained(over, 3, 3) == 5


def test_first_sustained_persist_one_is_first_crossing():
    assert first_sustained([False, False, True, False], 0, 1) == 2


def test_first_sustained_invalid_persist():
    with pytest.raises(ValueError):
        first_sustained([True, True], 0, 0)


def test_score_run_delay_and_rate():
    # limit=10; healthy below, fault above from onset=4
    t2 = [1, 2, 1, 2, 50, 60, 55, 70]  # onset=4, sustained from index 4
    delay, rate = score_run(t2, limit=10.0, onset=4, persist=3, cadence_min=3.0)
    assert delay == 0.0  # detected exactly at onset
    assert rate == pytest.approx(1.0)  # all post-onset samples over limit


def test_score_run_not_detected_when_flat():
    t2 = [1.0] * 20
    delay, rate = score_run(t2, limit=10.0, onset=5, persist=3, cadence_min=3.0)
    assert delay is None
    assert rate == 0.0


def test_score_run_delay_is_positive_when_late():
    # onset=2 but sustained alarm only begins at index 5 -> delay (5-2)*cadence
    t2 = [1, 1, 1, 50, 1, 50, 60, 70]
    delay, _ = score_run(t2, limit=10.0, onset=2, persist=3, cadence_min=2.0)
    assert delay == pytest.approx((5 - 2) * 2.0)


def test_false_alarm_rate():
    assert false_alarm_rate([1, 2, 3, 100, 200], limit=10.0) == pytest.approx(0.4)


def test_score_run_integration_with_health_index():
    """Fit a real T^2 model on healthy data; a step fault detects, flat does not."""
    rng = np.random.default_rng(0)
    healthy = rng.standard_normal((400, 5))
    names = [f"v{i}" for i in range(5)]
    model = HealthIndexModel.fit(healthy, names, warn_q=0.95, alarm_q=0.99)
    limit = model.alarm_t2

    onset = 50
    faulted = rng.standard_normal((100, 5))
    faulted[onset:] += 6.0  # large mean step on all channels after onset
    t2 = [model.t2(x) for x in faulted]
    delay, rate = score_run(t2, limit, onset, persist=3, cadence_min=1.0)
    assert delay is not None and delay <= 3.0  # detected within a few samples
    assert rate > 0.9

    flat = rng.standard_normal((150, 5))
    far = false_alarm_rate([model.t2(x) for x in flat], limit)
    assert far < 0.10  # ~1% expected at the 99% limit; loose bound for noise
