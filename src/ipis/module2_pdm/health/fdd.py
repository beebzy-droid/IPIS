"""Fault-detection scoring on a health-index T^2 stream (Phase 2C).

Turns a stream of Hotelling T^2 values plus an alarm limit into the standard
fault-detection scorecard quantities used in the Tennessee Eastman cross-domain
study: detection delay (first *sustained* alarm after fault onset) and detection
rate (fraction of post-onset samples above the limit). The persistence rule
(require ``persist`` consecutive exceedances) suppresses single-sample spikes,
the same debounce idea used for the FEMTO degradation-onset detector.

Domain-agnostic: it consumes T^2 values from any ``HealthIndexModel`` monitor, so
it serves the TEP study here but applies unchanged to the bearing pipeline.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def first_sustained(over: ArrayLike, start: int, persist: int) -> int | None:
    """Index of the first of ``persist`` consecutive True values at/after ``start``.

    ``over`` is a boolean exceedance stream (T^2 > limit). Returns the index where
    the sustained alarm *begins*, or None if no run of length ``persist`` occurs
    at or after ``start``.
    """
    flags = np.asarray(over, dtype=bool)
    if persist < 1:
        raise ValueError("persist must be >= 1")
    run = 0
    for i in range(start, flags.size):
        run = run + 1 if flags[i] else 0
        if run >= persist:
            return i - persist + 1
    return None


def score_run(
    t2: ArrayLike,
    limit: float,
    onset: int,
    persist: int = 3,
    cadence_min: float = 1.0,
) -> tuple[float | None, float]:
    """Score one faulted run against an alarm limit.

    Returns ``(detection_delay, detection_rate)`` where

      detection_delay = (first sustained alarm at/after ``onset`` - ``onset``)
                        * ``cadence_min``  (None if never sustained-detected)
      detection_rate  = fraction of post-onset samples with T^2 > ``limit``
    """
    values = np.asarray(t2, dtype=float)
    over = values > limit
    idx = first_sustained(over, onset, persist)
    delay = None if idx is None else (idx - onset) * cadence_min
    detection_rate = float(np.mean(over[onset:])) if onset < over.size else 0.0
    return delay, detection_rate


def false_alarm_rate(t2_healthy: ArrayLike, limit: float) -> float:
    """Per-sample exceedance rate on a fault-free stream (instantaneous FAR)."""
    values = np.asarray(t2_healthy, dtype=float)
    return float(np.mean(values > limit))
