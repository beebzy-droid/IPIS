"""O2 discharge: the empirical Lipschitz constant L1 of M1's conformal radius.

The composed certificate (``docs/module4/formalization-spike.md`` §5) carries a
term ``2 L1 ||Delta psi_1||`` that bounds how fast M1's coverage can degrade as
the operating point departs from the Fortuna calibration anchor in similitude
coordinates. L1 is the one empirical constant in that floor that was left open
(O2); this module estimates it.

Procedure: run M1 (frozen calibration) over several operating regimes spanning
the envelope; at each regime collect the split-conformal nonconformity scores
``|y_true - y_pred|`` and take their ``1 - alpha1`` quantile (the conformal
radius that regime would demand); place each regime at its psi_1 coordinate; then
L1 is the largest finite-difference slope of the radius over psi_1-space
(``psi.estimate_lipschitz``). The binding regime pair is reported so the worst
departure direction is auditable.

The score collection is duck-typed against M1's ``predict`` contract, so the
sweep is validated in the sandbox with a synthetic sensor whose radius grows at a
known rate; on the repo, pass the real ``SoftSensorService`` and the per-regime
calibration data.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import numpy.typing as npt

from ipis.integration.psi import (
    OperatingPoint,
    PsiConfig,
    estimate_lipschitz,
    psi1,
)


class ScoringSoftSensor(Protocol):
    """M1's predict contract (returns a dict carrying ``y_pred``)."""

    def predict(self, features: npt.NDArray[np.float64], sample_id: str) -> object: ...


def nonconformity_scores(
    soft_sensor: ScoringSoftSensor,
    features_rows: Sequence[Sequence[float]],
    y_true: Sequence[float],
) -> list[float]:
    """Split-conformal scores ``|y_true - y_pred|`` for a regime's calibration set.

    Reads M1 in predict-only mode (no ``label`` calls), so the calibration state
    is frozen and the scores reflect this regime alone.
    """
    if len(features_rows) != len(y_true):
        raise ValueError("features_rows and y_true must have equal length")
    scores: list[float] = []
    for i, (x, y) in enumerate(zip(features_rows, y_true, strict=True)):
        r = soft_sensor.predict(np.asarray(x, dtype=float), f"o2_{i}")
        if isinstance(r, list):
            r = r[0]
        scores.append(abs(float(y) - float(r["y_pred"])))  # type: ignore[index]
    return scores


def score_quantile(scores: Sequence[float], alpha1: float) -> float:
    """The split-conformal ``1 - alpha1`` radius: the k-th smallest nonconformity
    score with ``k = ceil((n+1)(1-alpha1))`` (Vovk/Lei). When ``k > n`` the radius
    is formally infinite (the guarantee is vacuous); we cap at the largest score."""
    s = np.sort(np.asarray(scores, dtype=float))
    n = s.size
    if n == 0:
        raise ValueError("no scores to take a quantile of")
    k = min(int(np.ceil((n + 1) * (1.0 - alpha1))), n)
    return float(s[k - 1])


@dataclass(frozen=True)
class L1Report:
    """Result of the L1 sweep."""

    l1: float
    psi1_points: tuple[tuple[float, ...], ...]
    quantiles: tuple[float, ...]
    binding_pair: tuple[int, int]


def l1_sweep(
    operating_points: Sequence[OperatingPoint],
    quantiles: Sequence[float],
    cfg: PsiConfig,
) -> L1Report:
    """L1 and the binding regime pair from per-regime conformal radii.

    ``operating_points[i]`` is the regime whose conformal radius is
    ``quantiles[i]``; each is placed at ``psi1(op, cfg.scales)``.
    """
    if len(operating_points) != len(quantiles):
        raise ValueError("operating_points and quantiles must have equal length")
    if len(operating_points) < 2:
        raise ValueError("need at least two regimes to estimate a slope")
    pts = [psi1(op, cfg.scales) for op in operating_points]
    q = np.asarray(quantiles, dtype=float)
    l1 = estimate_lipschitz(pts, q)

    best, pair = 0.0, (0, 1)
    for i in range(len(q)):
        for j in range(i + 1, len(q)):
            dist = float(np.linalg.norm(pts[i] - pts[j]))
            if dist > 0.0:
                slope = abs(q[i] - q[j]) / dist
                if slope > best:
                    best, pair = slope, (i, j)
    return L1Report(
        l1=l1,
        psi1_points=tuple(tuple(float(v) for v in p) for p in pts),
        quantiles=tuple(float(v) for v in q),
        binding_pair=pair,
    )


def l1_from_regime_data(
    soft_sensor: ScoringSoftSensor,
    regimes: Sequence[tuple[OperatingPoint, Sequence[Sequence[float]], Sequence[float]]],
    cfg: PsiConfig,
    alpha1: float,
) -> L1Report:
    """End-to-end O2: per regime ``(operating_point, features, y_true)`` collect
    M1's conformal radius, then sweep for L1."""
    ops = [op for op, _, _ in regimes]
    quantiles = [
        score_quantile(nonconformity_scores(soft_sensor, feats, ys), alpha1)
        for _, feats, ys in regimes
    ]
    return l1_sweep(ops, quantiles, cfg)
