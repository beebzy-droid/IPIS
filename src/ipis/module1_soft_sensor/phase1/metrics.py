"""Metrics of N1 Phase 1 (pre-registration Section 5.4) and the persistence measures (Section 8,
F8).

Per issued interval: its half-width h (or, for the baselines, its bounds), whether it covers.
- U, the primary metric: the share of issued intervals that are infinite or wider than y_range
  (``delayed_aci.uninformative``); the infinite share beside it;
- marginal coverage with the Wilson 95 % interval of the observed coverage;
- rolling coverage over trailing windows of 100 steps (the windows ending at steps 99 on): its
  sd and minimum, and the number of those steps at which it is below 0.80 (the steps spent in
  under-coverage episodes);
- the level of the conformal window: its sd and range;
- the width over the finite intervals: median, p90 and p99, with the infinite share beside it;
  and F7's width, the median over all issued intervals with an infinite interval counting as
  infinitely wide.
Persistence of a miss indicator: the lag-1 autocorrelation (``inference.acf``; 0 for a constant
indicator), the mean length of runs of consecutive misses, and the IACT (``inference.iact``,
Sokal's window with c = 5; 1 for a constant indicator).
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ipis.module1_soft_sensor.evaluation.inference import acf, iact

Z95 = 1.959963984540054
LOCAL = 100
UNDER = 0.80


def wilson(successes: float, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval of a binomial proportion."""
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def rolling(covered: np.ndarray, local: int = LOCAL) -> np.ndarray:
    c = np.asarray(covered, dtype=float)
    if c.size < local:
        return c
    return np.convolve(c, np.ones(local) / local, mode="valid")


def _finite_width_stats(width: np.ndarray) -> dict[str, float]:
    fin = width[np.isfinite(width)]
    q = np.percentile(fin, [50, 90, 99]) if fin.size else [math.nan] * 3
    return {"width_median": float(q[0]), "width_p90": float(q[1]), "width_p99": float(q[2])}


def interval_metrics(
    width: np.ndarray, covered: np.ndarray, y_range: float, level: np.ndarray | None = None
) -> dict[str, Any]:
    """Section 5.4 metrics of a run of issued intervals given by width (2h, or hi - lo)."""
    w = np.asarray(width, dtype=np.float64)
    cov = np.asarray(covered, dtype=bool)
    n = int(w.size)
    roll = rolling(cov)
    lo, hi = wilson(float(cov.sum()), n)
    out: dict[str, Any] = {
        "n": n,
        "u": float(np.mean(~np.isfinite(w) | (w > y_range))),
        "infinite_share": float(np.mean(~np.isfinite(w))),
        "coverage": float(cov.mean()),
        "covered_count": int(cov.sum()),
        "coverage_wilson95": [float(lo), float(hi)],
        "local_cov_sd": float(roll.std()),
        "local_cov_min": float(roll.min()),
        "under_coverage_steps": int(np.sum(roll < UNDER)) if cov.size >= LOCAL else 0,
        "f7_median_width": float(np.median(w)),
        **_finite_width_stats(w),
    }
    if level is not None:
        a = np.asarray(level, dtype=np.float64)
        out.update(alpha_sd=float(a.std()), alpha_min=float(a.min()), alpha_max=float(a.max()))
    return out


def loop_metrics(res: dict[str, np.ndarray], y_range: float) -> dict[str, Any]:
    """Metrics of a loop run (``run_loop`` or ``run_static``): width = 2h."""
    return interval_metrics(2.0 * res["h"], res["covered"], y_range, res["alpha"])


def mean_miss_run(err: np.ndarray) -> float:
    """Mean length of the runs of consecutive misses (0.0 if there are none)."""
    e: np.ndarray = np.concatenate((np.zeros(1), np.asarray(err, dtype=float), np.zeros(1)))
    starts = np.flatnonzero(np.diff(e) == 1.0)
    ends = np.flatnonzero(np.diff(e) == -1.0)
    return float(np.mean(ends - starts)) if starts.size else 0.0


def persistence(err: np.ndarray) -> dict[str, float]:
    """Lag-1 autocorrelation, mean miss run and IACT of a 0/1 miss indicator."""
    e = np.asarray(err, dtype=float)
    lag1 = float(acf(e, 1)[1]) if np.ptp(e) > 0 else 0.0
    return {"acf1": lag1, "mean_miss_run": mean_miss_run(e), "iact": iact(e)}
