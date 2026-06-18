"""Trajectory-similarity RUL for FEMTO (Option B; Wang 2008 family).

The probe refuted a fixed amplitude failure threshold (EOL peak 7-48 g, RMS 1-8 g),
so threshold-extrapolation (Option A) does not apply. Similarity matching needs no
threshold: it reads RUL off a *library* of known run-to-failure trajectories by
matching the SHAPE of the test bearing's degradation arc to library arcs.

Scale is the central difficulty here -- the degradation index spans ~16,000x across
bearings at failure. Matching is therefore done on **mean-centered** windows in
log1p(DI) space: subtracting each window's mean removes the vertical offset, so the
distance compares shape (slope/curvature), not absolute level. Sliding the test
signature along each library trajectory finds the best-matching phase; the library
RUL at that phase is one estimate, and estimates are combined across library
bearings with a similarity (distance) weight.

Causality: the test signature uses only data up to the current time; library
trajectories are full (known) run-to-failure arcs. Both are mean-centered the same
way, so the comparison is consistent.

Limitation (documented): pure phase matching assumes comparable degradation *rates*
within the library; differing rates bias the RUL read-off. Aggregation across the
library and the conformal bound absorb part of this; time-scaling is a future lever.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def _shape(seg: np.ndarray) -> np.ndarray:
    """Mean-center a 1-D segment (remove vertical offset -> compare shape only)."""
    seg = np.asarray(seg, dtype=float)
    return seg - seg.mean()


def _best_match(sig_shape: np.ndarray, hi: np.ndarray) -> tuple[int, float]:
    """Slide a (mean-centered) signature along `hi`; return (best_end_idx, rmse).

    The signature's last sample aligns to `best_end_idx` in `hi`. If `hi` is shorter
    than the signature, the most-recent part of the signature is compared end-aligned.
    """
    ls = sig_shape.size
    hi = np.asarray(hi, dtype=float)
    if hi.size < ls:
        sig_tail = sig_shape[-hi.size :]
        wc = hi - hi.mean()
        d = float(np.sqrt(np.mean((wc - (sig_tail - sig_tail.mean())) ** 2)))
        return hi.size - 1, d
    windows = sliding_window_view(hi, ls)  # (n, ls)
    wc = windows - windows.mean(axis=1, keepdims=True)
    dist = np.sqrt(np.mean((wc - sig_shape) ** 2, axis=1))
    j = int(np.argmin(dist))
    return j + ls - 1, float(dist[j])


@dataclass
class SimilarityRUL:
    """RUL by trajectory-shape matching against a library of (hi, rul) arcs.

    Uses **phase-ratio (time-scaling)** prediction: matching borrows only the PHASE
    (fraction of the degradation arc elapsed) from the library; RUL is then computed
    from the test bearing's OWN elapsed time, RUL = elapsed * (1 - phi) / phi. This
    is rate-invariant -- a test bearing that degrades faster or slower than the
    library still gets a correct RUL, because absolute time comes from its own clock,
    not the library's. (Reading absolute library RUL instead fails badly when rates
    differ, e.g. the longest-life bearing.)

    library  : list of (hi, rul) per training bearing -- hi = log1p(DI) over the
               degradation arc; rul (same time units as `interval`) is used only for
               the insufficient-signal fallback.
    interval : seconds between snapshots (FEMTO = 10 s); sets the RUL time unit. The
               library rul must be in these units.
    max_sig  : cap on the test-signature length (recent window) for cost/locality.
    phi_floor: clip on the matched phase to bound RUL when phi -> 0 (early life).
    """

    library: list[tuple[np.ndarray, np.ndarray]]
    interval: float = 10.0
    mode: str = "phase"  # "phase" (rate-invariant time-scaling) | "absolute" (library RUL read-off)
    max_sig: int = 400
    phi_floor: float = 0.05
    _lib: list[tuple[np.ndarray, np.ndarray]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in ("phase", "absolute"):
            raise ValueError("mode must be 'phase' or 'absolute'")
        self._lib = [
            (np.asarray(hi, float).ravel(), np.asarray(rul, float).ravel())
            for hi, rul in self.library
        ]
        if not self._lib:
            raise ValueError("library must contain at least one trajectory")

    def predict_one(self, test_hi_segment: np.ndarray) -> float:
        """Point RUL for a test bearing observed up to now (hi from FPT to current t)."""
        seg = np.asarray(test_hi_segment, float).ravel()[-self.max_sig :]
        if seg.size < 2:
            # not enough degradation signal yet -> longest library life (max uncertainty)
            return max(float(rul[0]) for _, rul in self._lib)
        sig_shape = _shape(seg)
        elapsed = (seg.size - 1) * self.interval  # test's own elapsed arc time
        phases, abs_ruls, dists = [], [], []
        for hi, rul in self._lib:
            end, d = _best_match(sig_shape, hi)
            phases.append(end / (hi.size - 1) if hi.size > 1 else 1.0)
            abs_ruls.append(float(rul[end]))
            dists.append(d)
        dists = np.asarray(dists, float)
        bw = float(np.median(dists)) + 1e-9
        w = np.exp(-(dists**2) / (2.0 * bw**2))
        if w.sum() <= 0.0:
            w = np.ones_like(w)
        if self.mode == "absolute":
            return float(np.sum(w * np.asarray(abs_ruls)) / np.sum(w))
        phi = float(np.clip(np.sum(w * np.asarray(phases)) / np.sum(w), self.phi_floor, 1.0))
        return elapsed * (1.0 - phi) / phi

    def predict_many(self, segments: list[np.ndarray]) -> np.ndarray:
        """Point RUL for several observation windows."""
        return np.array([self.predict_one(s) for s in segments], dtype=float)
