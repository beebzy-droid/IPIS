"""Degradation index and first-prediction-time for FEMTO RUL (Phase 2B, Option E).

The raw Hotelling-T^2 health series is noisy and non-stationary (run-in transients,
single-snapshot excursions against static control limits). For RUL it is turned
into a clean, *causal*, monotone degradation index:

    DI(t) = cummax( EMA_alpha( T2(t) ) )

EMA smooths run-in spikes and noise; the cumulative max enforces monotonicity (a
degradation index never recovers) — the textbook RUL health-indicator shape (Lei
2018). Both operations use only past samples, so DI is deployable on a streaming
bearing (no end-of-life normalization, hence no leakage).

The first-prediction-time (FPT) is the degradation onset: the first snapshot where
the *smoothed* (pre-cummax) HI stays above the WARN control limit for `persist`
consecutive snapshots. RUL is only predicted for t >= FPT (the degradation phase);
before onset, remaining life is long and not meaningfully estimable from the HI.
"""

from __future__ import annotations

import numpy as np


def ema(x: np.ndarray, alpha: float) -> np.ndarray:
    """Causal exponential moving average. alpha in (0,1]; smaller = smoother."""
    x = np.asarray(x, dtype=float).ravel()
    if not (0.0 < alpha <= 1.0):
        raise ValueError("alpha must be in (0, 1]")
    out = np.empty_like(x)
    acc = x[0]
    for i, v in enumerate(x):
        acc = alpha * v + (1.0 - alpha) * acc
        out[i] = acc
    return out


def degradation_index(t2: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """Monotone smoothed degradation index: cummax(EMA(T2)) (causal, Option E)."""
    smoothed = ema(t2, alpha)
    return np.maximum.accumulate(smoothed)


def first_prediction_time(
    t2: np.ndarray,
    warn_limit: float,
    alpha: float = 0.05,
    persist: int = 3,
) -> int | None:
    """Degradation onset (FPT): first index where smoothed T2 stays > warn_limit.

    Returns the start index of the first run of `persist` consecutive snapshots
    above `warn_limit` on the smoothed (pre-cummax) HI, or None if never.
    """
    smoothed = ema(t2, alpha)
    run = 0
    for i, v in enumerate(smoothed):
        run = run + 1 if v > warn_limit else 0
        if run >= persist:
            return i - persist + 1
    return None
