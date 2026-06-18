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


def robust_baseline_window(
    feats: np.ndarray,
    window: int | None = None,
    search_frac: float = 0.5,
) -> tuple[int, int]:
    """Pick the quietest early window as the healthy baseline -> (start, width).

    Scans windows in the first `search_frac` of life and returns the one with the
    lowest total (standardized) feature variance. Run-in transients (high variance)
    and degradation onset (rising -> high variance) are both auto-skipped, so the
    baseline lands on the genuine healthy plateau. The width is sized for a stable
    covariance (>= ~10x the feature count), since a too-small window gives an
    under-determined covariance and a useless T2.
    """
    feats = np.asarray(feats, dtype=float)
    n, p = feats.shape
    w = window if window is not None else max(100, n // 10)
    w = min(w, max(2, n // 2))
    mu = feats.mean(axis=0)
    sd = feats.std(axis=0) + 1e-12
    z = (feats - mu) / sd
    hi = max(w, int(search_frac * n))
    n_pos = hi - w + 1
    if n_pos < 1:
        return 0, min(w, n)
    cs = np.cumsum(np.vstack([np.zeros(p), z]), axis=0)
    cs2 = np.cumsum(np.vstack([np.zeros(p), z**2]), axis=0)
    s = np.arange(n_pos)
    wsum = cs[s + w] - cs[s]
    wsum2 = cs2[s + w] - cs2[s]
    var = wsum2 / w - (wsum / w) ** 2
    return int(np.argmin(var.sum(axis=1))), w


def robust_first_prediction_time(
    t2: np.ndarray,
    baseline_end: int,
    warn_limit: float,
    alpha: float = 0.05,
    persist: int = 3,
) -> int | None:
    """FPT detected only AFTER the baseline window (no onset inside the healthy fit).

    Avoids the run-in head tripping the detector: the first `baseline_end` snapshots
    (which include any run-in transient and the healthy plateau) are not scanned.
    """
    smoothed = ema(t2, alpha)
    run = 0
    for i in range(int(baseline_end), len(smoothed)):
        run = run + 1 if smoothed[i] > warn_limit else 0
        if run >= persist:
            return i - persist + 1
    return None
