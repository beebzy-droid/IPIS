"""Inference for serially dependent indicator sequences (IPIS M1, Phase 1 analysis plan, Sec. 7).

The per-step outcomes of a calibration loop (covered, infinite, uninformative) are autocorrelated,
so binomial intervals are too narrow. This module provides:
- the integrated autocorrelation time (IACT) with Sokal's automatic window, the same estimator as
  ``scripts/phase1_precheck.py``;
- the pre-registered block-length rule;
- circular block bootstrap intervals for a mean and for a paired difference of means.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import ArrayLike


def acf(x: ArrayLike, max_lag: int) -> np.ndarray:
    """Biased sample autocorrelations rho_0 .. rho_max_lag (rho_0 = 1)."""
    x = np.asarray(x, dtype=np.float64) - np.mean(x)
    n = x.size
    if max_lag >= n:
        raise ValueError("max_lag must be smaller than the series length")
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f))[: max_lag + 1]
    return r / r[0]


def iact(x: ArrayLike, c: float = 5.0) -> float:
    """Integrated autocorrelation time, Sokal's window: the smallest M with M >= c tau(M).

    A constant series has no defined autocorrelation; it returns 1.0.
    """
    x = np.asarray(x, dtype=np.float64) - np.mean(x)
    n = x.size
    if n < 2 or not np.any(x):
        return 1.0
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f))[:n]
    rho = r / r[0]
    tau = 1.0
    for m in range(1, n):
        tau = 1.0 + 2.0 * float(rho[1 : m + 1].sum())
        if m >= c * tau:
            break
    return max(tau, 1.0)


def block_length(x: ArrayLike, floor: int = 25) -> int:
    """Pre-registered rule: the larger of ``floor`` and the next integer above 2 x IACT."""
    return max(floor, math.ceil(2.0 * iact(x)))


def circular_block_bootstrap_ci(
    x: ArrayLike, block: int, *, n_boot: int = 2000, level: float = 0.95, seed: int = 0
) -> tuple[float, float]:
    """Percentile interval for the mean of x from a circular block bootstrap."""
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    if not 1 <= block <= n:
        raise ValueError("block must lie in [1, len(x)]")
    k = math.ceil(n / block)
    rng = np.random.default_rng(seed)
    offsets = np.arange(block)
    means = np.empty(n_boot)
    for start in range(0, n_boot, 200):  # chunks bound the index array to 200 x n entries
        m = min(200, n_boot - start)
        starts = rng.integers(0, n, size=(m, k))
        idx = (starts[:, :, None] + offsets[None, None, :]).reshape(m, -1)[:, :n] % n
        means[start : start + m] = x[idx].mean(axis=1)
    tail = (1.0 - level) / 2.0
    lo, hi = np.quantile(means, [tail, 1.0 - tail])
    return float(lo), float(hi)


def paired_block_bootstrap_ci(
    x: ArrayLike,
    y: ArrayLike,
    block: int,
    *,
    n_boot: int = 2000,
    level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Interval for mean(x - y): both arms resampled with the same blocks."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.shape != y.shape:
        raise ValueError("paired sequences must have the same length")
    return circular_block_bootstrap_ci(x - y, block, n_boot=n_boot, level=level, seed=seed)


def n_blocks(n: int, block: int) -> int:
    """Number of whole blocks in a series of length n (Sec. 7: below 8 the interval is unreliable)."""
    return n // block
