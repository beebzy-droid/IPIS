"""Decision rules F1 to F8 of N1 Phase 1 (pre-registration Section 6) and the inference of
Section 7.

Each function takes per-run (TEP) or per-step (debutanizer) quantities that stage B has measured
and returns the numbers the rule uses and its outcome. The rules, as frozen:
- F2: in a primary cell, the increase in U over the theta = 0 control on the same stream, at the
  delay-blind step size, of at least 1 percentage point with a Bonferroni 97.5 % interval that
  excludes 0 (TEP: a t interval over the 15 runs; debutanizer: the circular block bootstrap of
  Section 7, descriptive if fewer than 8 blocks fit). F2 fires if neither primary cell shows it.
- F3: in a primary cell that shows F2's increase, 0.90 outside the Wilson 95 % interval of the
  observed marginal coverage (TEP: counts pooled over the 15 runs).
- F5a and F5b: the mean U over the 15 runs above 2 eps.
- F6: the mean over the runs of measured / predicted width ratio - 1 outside +-10 %.
- F7 (Appendix A, D-P1.11, D-P1.14): a baseline valid, and either the compensated loop not
  valid or the baseline narrower at the loop's coverage.
- F8 (D-P1.13): if the mean predicted width ratio is at most 0.95, the paired two-sided 95 % t
  interval of the IACT difference of the open-loop miss indicators not wholly below 0.
- F1 (secondary): the white model off by more than 25 % in sd(alpha) or in the infinite share,
  inside the design region (0 < gamma <= 0.8 gamma_crit, where ``design_gamma`` searches).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
from scipy import stats

from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.evaluation.baselines_pid import gaussian_width_factor
from ipis.module1_soft_sensor.evaluation.inference import (
    block_length,
    circular_block_bootstrap_ci,
    n_blocks,
    paired_block_bootstrap_ci,
)
from ipis.module1_soft_sensor.phase1.metrics import wilson

TOL = 1e-9  # inclusive bounds absorb rounding, as in Appendix A
N_BOOT = 2000  # Section 7
MIN_BLOCKS = 8  # Section 7: fewer blocks make the interval unreliable
BOOT_SEED = 0
NOMINAL = 0.90


def t_interval(x: Sequence[float] | np.ndarray, level: float) -> dict[str, Any]:
    """Mean and two-sided t interval at ``level`` over independent replications. Undefined
    (NaN bounds) if a value is not finite or there is a single replication."""
    a = np.asarray(x, dtype=np.float64)
    n = int(a.size)
    if n == 0:
        raise ValueError("no replications")
    if not np.all(np.isfinite(a)):
        with np.errstate(invalid="ignore"):  # inf - inf in a difference of widths gives nan
            mean = float(np.mean(a))
        return {"mean": mean, "lo": math.nan, "hi": math.nan, "n": n, "level": level}
    mean = float(a.mean())
    if n < 2:
        return {"mean": mean, "lo": math.nan, "hi": math.nan, "n": n, "level": level}
    se = float(a.std(ddof=1) / math.sqrt(n)) if np.ptp(a) > 0 else 0.0
    half = float(stats.t.ppf(0.5 + level / 2.0, n - 1)) * se
    return {"mean": mean, "lo": mean - half, "hi": mean + half, "n": n, "level": level}


def block_ci(x: np.ndarray, level: float = 0.95, seed: int = BOOT_SEED) -> dict[str, Any]:
    """Section 7's interval for the mean of one per-step indicator sequence. A block longer than
    the sequence leaves no interval (NaN bounds), and the cell is unreliable."""
    a = np.asarray(x, dtype=np.float64)
    block = block_length(a)
    blocks = n_blocks(a.size, block)
    lo = hi = math.nan
    if block <= a.size:
        lo, hi = circular_block_bootstrap_ci(a, block, n_boot=N_BOOT, level=level, seed=seed)
    return {
        "mean": float(a.mean()),
        "lo": lo,
        "hi": hi,
        "block": int(block),
        "blocks": int(blocks),
        "reliable": bool(blocks >= MIN_BLOCKS),
        "level": level,
    }


def paired_block_ci(
    x: np.ndarray, y: np.ndarray, level: float = 0.95, seed: int = BOOT_SEED
) -> dict[str, Any]:
    """Section 7's interval for mean(x - y), both arms resampled with the same blocks; the block
    length comes from the paired difference sequence. A block longer than the sequence leaves
    no interval (NaN bounds), and the cell is unreliable."""
    a = np.asarray(x, dtype=np.float64)
    b = np.asarray(y, dtype=np.float64)
    diff = a - b
    block = block_length(diff)
    blocks = n_blocks(diff.size, block)
    lo = hi = math.nan
    if block <= diff.size:
        lo, hi = paired_block_bootstrap_ci(a, b, block, n_boot=N_BOOT, level=level, seed=seed)
    return {
        "mean": float(diff.mean()),
        "lo": lo,
        "hi": hi,
        "block": int(block),
        "blocks": int(blocks),
        "reliable": bool(blocks >= MIN_BLOCKS),
        "level": level,
    }


# --- F2 and F3 ---------------------------------------------------------------------------


def f2_tep(u_theta: Sequence[float], u_zero: Sequence[float]) -> dict[str, Any]:
    """Per-run U at the primary theta minus U at theta = 0, at the delay-blind step size: the
    increase is shown if its mean is at least 1 point and the Bonferroni 97.5 % t interval
    excludes 0 (as ``scripts/phase1_power.py`` tests it)."""
    diff = np.asarray(u_theta, dtype=np.float64) - np.asarray(u_zero, dtype=np.float64)
    ci = t_interval(diff, 0.975)
    shows = ci["mean"] >= 0.01 - TOL and ci["lo"] > 0.0
    return {"diff_per_run": diff.tolist(), "ci975": ci, "shows_increase": bool(shows)}


def f2_debutanizer(u_theta: np.ndarray, u_zero: np.ndarray) -> dict[str, Any]:
    """Per-step uninformative flags at theta_doc and at theta = 0 on the same stream. With fewer
    than 8 blocks the interval is unreliable and the cell only descriptive, so it cannot show
    the increase (as ``scripts/phase1_power.py`` tests it)."""
    ci = paired_block_ci(u_theta, u_zero, level=0.975)
    shows = ci["reliable"] and ci["mean"] >= 0.01 - TOL and ci["lo"] > 0.0
    return {"ci975": ci, "shows_increase": bool(shows), "descriptive": not ci["reliable"]}


def f2_verdict(shows: dict[str, bool]) -> dict[str, Any]:
    """F2 fires if neither primary cell shows the increase; with one, the claim is restricted."""
    showing = [cell for cell, s in shows.items() if s]
    return {
        "fires": not showing,
        "cells_showing": showing,
        "restricted_to": showing[0] if len(showing) == 1 else None,
    }


def f3(covered_count: int, n: int, nominal: float = NOMINAL) -> dict[str, Any]:
    """F3's test: the nominal coverage outside the Wilson 95 % interval of the observed one."""
    lo, hi = wilson(float(covered_count), n)
    return {
        "coverage": covered_count / n,
        "covered": int(covered_count),
        "n": int(n),
        "wilson95": [lo, hi],
        "nominal_outside": bool(not lo <= nominal <= hi),
    }


# --- F5 and F6 ---------------------------------------------------------------------------


def f5(u_runs: Sequence[float], eps: float) -> dict[str, Any]:
    """F5a / F5b: the mean U over the runs above 2 eps."""
    u = np.asarray(u_runs, dtype=np.float64)
    return {
        "u_per_run": u.tolist(),
        "mean_u": float(u.mean()),
        "budget": 2 * eps,
        "fires": bool(u.mean() > 2 * eps + TOL),
    }


def f6(measured: Sequence[float], predicted: Sequence[float]) -> dict[str, Any]:
    """F6: mean over runs of measured / predicted - 1 outside +-10 %."""
    m = np.asarray(measured, dtype=np.float64)
    p = np.asarray(predicted, dtype=np.float64)
    err = m / p - 1.0
    mean = float(err.mean())
    return {
        "measured_per_run": m.tolist(),
        "predicted_per_run": p.tolist(),
        "error_per_run": err.tolist(),
        "mean_error": mean,
        "error_ci95": t_interval(err, 0.95),
        "fires": bool(abs(mean) > 0.10 + TOL),
    }


# --- F8 ---------------------------------------------------------------------------------


F8_GATE = 0.95


def f8(
    predicted_ratio: Sequence[float],
    iact_comp: Sequence[float],
    iact_raw: Sequence[float],
    gamma_comp_by_regime: Sequence[float],
    gamma_raw_by_regime: Sequence[float],
) -> dict[str, Any]:
    """F8 (D-P1.13) and the step-size statement of claim 2'."""
    pred = float(np.mean(predicted_ratio))
    tested = pred <= F8_GATE + TOL
    diff = np.asarray(iact_comp, dtype=np.float64) - np.asarray(iact_raw, dtype=np.float64)
    ci = t_interval(diff, 0.95)
    fires = bool(tested and ci["hi"] >= 0.0)
    pairs = list(zip(gamma_comp_by_regime, gamma_raw_by_regime, strict=True))
    larger = sum(gc > gr for gc, gr in pairs)
    smaller = sum(gc < gr for gc, gr in pairs)
    step = larger >= 2 and smaller == 0
    return {
        "mean_predicted_ratio": pred,
        "gate": F8_GATE,
        "tested": bool(tested),
        "iact_diff_per_run": diff.tolist(),
        "ci95": ci,
        "fires": fires,
        "gamma_comp_by_regime": [float(g) for g in gamma_comp_by_regime],
        "gamma_raw_by_regime": [float(g) for g in gamma_raw_by_regime],
        "regimes_gamma_larger": int(larger),
        "regimes_gamma_smaller": int(smaller),
        "step_condition": bool(step),
        "step_statement_made": bool(tested and not fires and step),
    }


# --- F7 ---------------------------------------------------------------------------------


def clip_coverage(c: float, n: int) -> float:
    """D-P1.14 (ii): a run coverage of exactly 0 or 1 is clipped to [1 / (2n), 1 - 1 / (2n)]."""
    return min(max(float(c), 1.0 / (2 * n)), 1.0 - 1.0 / (2 * n))


def gaussian_factor(c_from: float, c_to: float, n: int) -> float:
    """D-P1.11's factor, on clipped coverages."""
    return gaussian_width_factor(clip_coverage(c_from, n), clip_coverage(c_to, n))


def empirical_factor(scores: np.ndarray, c_from: float, c_to: float, n: int) -> float:
    """D-P1.14 (i): q(c_to) / q(c_from), q the empirical quantile (linear interpolation) of the
    loop's absolute compensated calibration scores, on clipped coverages."""
    s = np.abs(np.asarray(scores, dtype=np.float64))
    q_to = float(np.quantile(s, clip_coverage(c_to, n)))
    q_from = float(np.quantile(s, clip_coverage(c_from, n)))
    return q_to / q_from


def valid(runs: Sequence[dict[str, Any]], eps: float, nominal: float = NOMINAL) -> dict[str, Any]:
    """F7's validity: mean U at most 2 eps and mean coverage within 2 points of nominal."""
    u = float(np.mean([r["u"] for r in runs]))
    cov = float(np.mean([r["coverage"] for r in runs]))
    ok = u <= 2 * eps + TOL and abs(cov - nominal) <= 0.02 + TOL
    return {"mean_u": u, "mean_coverage": cov, "valid": bool(ok)}


def narrower(widths: np.ndarray, loop_widths: np.ndarray, min_runs: int) -> dict[str, Any]:
    """F7's "narrower": the mean run-median width at least 5 % smaller, and smaller in at least
    ``min_runs`` runs. Infinite widths count as infinitely wide. Beside it, the paired
    difference (baseline - loop) with a 95 % t interval, as Section 7 describes it."""
    w = np.asarray(widths, dtype=np.float64)
    lw = np.asarray(loop_widths, dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = float(np.mean(w) / np.mean(lw))
        diff = w - lw
    runs = int(np.sum(w < lw))
    ok = bool(ratio <= 0.95 + TOL and runs >= min_runs)
    change = 100.0 * (ratio - 1.0) if math.isfinite(ratio) else math.nan
    return {
        "mean_width": float(np.mean(w)),
        "loop_mean_width": float(np.mean(lw)),
        "width_change_pct": change,
        "runs_narrower": runs,
        "narrower": ok,
        "paired_diff_ci95": t_interval(diff, 0.95),
    }


def f7_compare(
    baseline: Sequence[dict[str, Any]],
    loop: Sequence[dict[str, Any]],
    *,
    eps: float,
    min_runs: int,
    calibration_scores: Sequence[np.ndarray],
) -> dict[str, Any]:
    """One baseline against the compensated loop, run by run.

    The test (D-P1.11): each run's baseline width scaled to the loop's coverage in that run by
    the Gaussian factor. Reported beside it: the unscaled comparison, the comparison scaled by
    the loop's own score quantiles (D-P1.14 (i); ``calibration_scores[k]`` holds the pooled
    compensated calibration scores of run k's regime) and the coverage gap.
    """
    b_valid, l_valid = valid(baseline, eps), valid(loop, eps)
    bw = np.array([r["f7_median_width"] for r in baseline], dtype=np.float64)
    lw = np.array([r["f7_median_width"] for r in loop], dtype=np.float64)
    bc = [r["coverage"] for r in baseline]
    lc = [r["coverage"] for r in loop]
    ns = [int(r["n"]) for r in baseline]
    if [int(r["n"]) for r in loop] != ns or len(calibration_scores) != len(ns):
        raise ValueError("the baseline, the loop and the scores must cover the same runs")

    def scaled(factor: Callable[[int], float]) -> tuple[np.ndarray, list[float]]:
        f = [factor(k) for k in range(len(ns))]
        return bw * np.array(f), f

    g_w, g_f = scaled(lambda k: gaussian_factor(bc[k], lc[k], ns[k]))
    e_w, e_f = scaled(lambda k: empirical_factor(calibration_scores[k], bc[k], lc[k], ns[k]))
    gauss = narrower(g_w, lw, min_runs) | {"factor_per_run": g_f}
    emp = narrower(e_w, lw, min_runs) | {"factor_per_run": e_f}
    unscaled = narrower(bw, lw, min_runs)
    fires = b_valid["valid"] and (not l_valid["valid"] or gauss["narrower"])
    return {
        "baseline": b_valid,
        "loop": l_valid,
        "coverage_gap_pp": 100.0 * (b_valid["mean_coverage"] - l_valid["mean_coverage"]),
        "coverage_matched_gaussian": gauss,
        "coverage_matched_empirical": emp,
        "unscaled": unscaled,
        "fires": bool(fires),
        "empirical_disagrees": bool(
            b_valid["valid"] and l_valid["valid"] and gauss["narrower"] != emp["narrower"]
        ),
    }


def f7_verdict(comparisons: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """F7 fires if any baseline meets its rule (A.1). All that do are named, and the one with the
    smallest mean coverage-matched width is recommended."""
    meeting = [name for name, c in comparisons.items() if c["fires"]]
    best = None
    if meeting:
        best = min(meeting, key=lambda n: comparisons[n]["coverage_matched_gaussian"]["mean_width"])
    return {"fires": bool(meeting), "baselines_meeting": meeting, "recommended": best}


# --- F1 ---------------------------------------------------------------------------------


def in_design_region(gamma: float, theta: int) -> bool:
    """0 < gamma <= 0.8 gamma_crit(theta), the region ``design_gamma`` searches."""
    return bool(math.isfinite(gamma) and 0.0 < gamma <= 0.8 * d.gamma_crit(theta) + TOL)


def f1_cell(
    gamma: float, theta: int, sd_measured: float, inf_measured: float, n_intervals: int
) -> dict[str, Any]:
    """The white model against one cell inside the design region. The error is predicted /
    measured - 1, as in ``scripts/pilots/persistence_pilot.py``. A measured infinite share of 0
    from ``n_intervals`` intervals resolves no share below one interval, so there the error is
    undefined and the model counts as off if it predicts more than 1.25 infinite intervals (25 %
    above the one interval that could have gone unseen)."""
    if not in_design_region(gamma, theta):
        return {"gamma": gamma, "in_region": False}
    sd_pred = d.noise_gain_sd(gamma, theta)
    inf_pred = d.infinite_fraction_pred(gamma, theta)
    err_sd = sd_pred / sd_measured - 1.0 if sd_measured > 0 else None
    err_inf = inf_pred / inf_measured - 1.0 if inf_measured > 0 else None
    off_sd = err_sd is not None and abs(err_sd) > 0.25 + TOL
    if inf_measured > 0:
        off_inf = err_inf is not None and abs(err_inf) > 0.25 + TOL
    else:
        off_inf = inf_pred * n_intervals > 1.25 + TOL
    return {
        "gamma": gamma,
        "in_region": True,
        "sd_pred": sd_pred,
        "sd_measured": sd_measured,
        "err_sd": err_sd,
        "inf_pred": inf_pred,
        "inf_measured": inf_measured,
        "err_inf": err_inf,
        "n_intervals": int(n_intervals),
        "inf_pred_count": inf_pred * n_intervals,
        "off_sd": bool(off_sd),
        "off_inf": bool(off_inf),
        "off_by_25pct": bool(off_sd or off_inf),
    }
