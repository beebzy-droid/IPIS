"""Similitude diagnostic: decide, from calibration data alone, whether the physics
similitude premise underpinning the SCC certificate HOLDS, is VIOLATED, or is
INDETERMINATE (underpowered) on a given dataset.

Under exact dynamic similitude the dimensionless life ``D = life * n * P^p`` (the
bearing dynamic-capacity constant cancels) is condition-independent, so for any pair
of operating conditions ``g = median(D | c) / median(D | c')`` equals 1. Equivalently,
``g`` is the empirical median-life ratio divided by the Lundberg-Palmgren / ISO 281
prediction ``T_L(c)/T_L(c') = (P'/P)^p (n'/n)``. A bootstrap CI on ``g`` gives a
three-way verdict: 1 inside a tight CI -> HOLDS; 1 outside -> VIOLATED; CI wider than a
preset fold -> INDETERMINATE. On INDETERMINATE or VIOLATED data SCC declines its
a-priori certificate and defers to data-driven (weighted) conformal — making it aware
of its own operating envelope rather than silently over-certifying.

This is the limits-case tool for run-to-failure cohorts (e.g. FEMTO/PRONOSTIA), whose
small per-condition counts and large within-condition spread typically return
INDETERMINATE — consistent with Nectoux et al.'s report that L10 does not govern FEMTO.
"""

from __future__ import annotations

import itertools

import numpy as np

# FEMTO / PRONOSTIA operating conditions: (equivalent load P [N], speed n [rpm]).
FEMTO_COND: dict[int, tuple[float, float]] = {
    1: (4000.0, 1800.0),
    2: (4200.0, 1650.0),
    3: (5000.0, 1500.0),
}
P_EXP = 3.0  # ball-bearing L10 load-life exponent


def l10_ratio(ci: int, cj: int, cond: dict[int, tuple[float, float]] = FEMTO_COND) -> float:
    """Lundberg-Palmgren / ISO 281 predicted life ratio T_L(ci)/T_L(cj)."""
    p_i, n_i = cond[ci]
    p_j, n_j = cond[cj]
    return float((p_j / p_i) ** P_EXP * (n_j / n_i))


def _bootstrap_median_ratio(li: np.ndarray, lj: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for b in range(n_boot):
        out[b] = np.median(rng.choice(li, len(li))) / np.median(rng.choice(lj, len(lj)))
    return out


def diagnose(
    lives_by_cond: dict[int, np.ndarray],
    cond: dict[int, tuple[float, float]] = FEMTO_COND,
    *,
    wide_fold: float = 2.0,
    n_boot: int = 2000,
    seed: int = 0,
) -> tuple[str, dict[tuple[int, int], dict[str, object]]]:
    """Return (overall_verdict, per_pair_detail).

    ``overall_verdict`` is "violated" if any pair rejects similitude, else
    "indeterminate" if any pair is underpowered, else "holds".
    """
    conds = [c for c in lives_by_cond if len(lives_by_cond[c]) > 1]
    detail: dict[tuple[int, int], dict[str, object]] = {}
    for ci, cj in itertools.combinations(conds, 2):
        boot = _bootstrap_median_ratio(
            np.asarray(lives_by_cond[ci]), np.asarray(lives_by_cond[cj]), n_boot, seed
        )
        g = boot / l10_ratio(ci, cj, cond)
        lo, hi = (float(x) for x in np.percentile(g, [2.5, 97.5]))
        ci_fold = hi / lo
        if ci_fold > wide_fold:
            verdict = "indeterminate"
        elif lo <= 1.0 <= hi:
            verdict = "holds"
        else:
            verdict = "violated"
        detail[(ci, cj)] = {
            "verdict": verdict,
            "g_median": round(float(np.median(g)), 3),
            "ci95": (round(lo, 3), round(hi, 3)),
            "ci_fold": round(ci_fold, 2),
        }
    verdicts = {d["verdict"] for d in detail.values()}
    if "violated" in verdicts:
        overall = "violated"
    elif "indeterminate" in verdicts:
        overall = "indeterminate"
    else:
        overall = "holds"
    return overall, detail
