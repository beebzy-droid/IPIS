"""Conformal PID control at the label horizon: a baseline for claim N1'' (pre-registration
Sec. 5.3 and Appendix A).

Angelopoulos, Candes and Tibshirani (NeurIPS 2023): quantile tracking, an error integrator and a
scorecaster, run on the signed residual score r_t = y_t - yhat_t of the compensated loop's point
model, one side at a time, with a residual used only once its label has arrived.

Timing, as in ``delayed_aci``: the interval for sample t is issued at step t, and the label of
sample s arrives at the end of step s + theta. At issue time the newest known residual is
r_{t-h}, with h = theta + 1, the label horizon.

Sources (pinned): the paper, and where it is silent the authors' code, aangelopoulos/
conformal-time-series at commit b729c3f. Two modes:
- ``mode="code"`` reproduces ``quantile_integrator_log_scorecaster`` (core/methods.py) step for
  step, including its conventions;
- ``mode="phase1"`` is the configuration of Appendix A: the paper's quantities, restricted to
  labels that have arrived. The integrator sums every labelled coverage error, the learning-rate
  window holds the most recent labelled scores, and coverage is recorded at every step. Like the
  compensated loop, conformal PID starts at the first scored row from a seed: the rows before it
  set its initial quantile and fill its learning-rate window, carry no coverage errors, and count
  in the integrator as rows at nominal coverage.
The scorecasters of Appendix A (quantile regression, Theta, matched) are built separately and
passed in.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import NormalDist

import numpy as np
from numpy.typing import ArrayLike

from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile

MODES = ("phase1", "code")

# Appendix A: the multiplier grid follows the compensated loop's ladder (1, 1.5, 2, 3, 5, 7 per
# decade from 0.001), extended to 1.
PID_M_GRID = (
    0.001,
    0.0015,
    0.002,
    0.003,
    0.005,
    0.007,
    0.01,
    0.015,
    0.02,
    0.03,
    0.05,
    0.07,
    0.1,
    0.15,
    0.2,
    0.3,
    0.5,
    0.7,
    1.0,
)
PID_K_FACTORS = (1.0, 10.0)  # K_I = factor x B', B' the largest |r| of the calibration segment
PID_C_SAT_AUTHORS = 5.0  # the authors' most frequent setting (electricity, climate, synthetic)
PID_WINDOW = 200  # burn-in (the seed) and learning-rate window Delta
PID_WARM_ROWS = 100  # the last seed rows whose centred scores set the initial quantile
PID_SCORECAST_MIN = (
    50  # burn_in of scorecasters (a) and (b): zero until the newest labelled index exceeds it
)
PID_DELTA = 0.02  # coverage tolerance of App. C's C_sat heuristic and of F7
PID_QR_LAGS = 3  # the three most recent labelled scores (paper App. F)
_TOL = 1e-9  # the bounds of the selection rule are inclusive; this absorbs rounding


def pid_tan(x: float) -> float:
    """``mytan`` of the authors' code: tan on (-pi/2, pi/2), +-inf outside (numpy functions, as
    there, so that the reproduction agrees to the bit)."""
    if x >= np.pi / 2:
        return math.inf
    if x <= -np.pi / 2:
        return -math.inf
    return float(np.tan(x))


def pid_integrator(x: float, t: int, c_sat: float, k_i: float) -> float:
    """The tan integrator r_t(x) = K_I tan(x log(t + 1) / (C_sat (t + 1))), as in
    ``saturation_fn_log``. With t + 1 the number of coverage errors summed in x it is the paper's
    r_t. Zero if K_I = 0."""
    if k_i == 0:
        return 0.0
    return float(k_i * pid_tan(x * np.log(t + 1) / (c_sat * (t + 1))))


def pid_c_sat(n_steps: int, delta: float) -> float:
    """C_sat = (2 / pi) (ceil(delta log T) - 1 / log T): the heuristic of the paper's Appendix C as
    read from the extracted text, with T the run length and delta the tolerated shortfall of
    coverage. For delta log T <= 1 the ceiling is 1, so the value does not depend on delta."""
    log_t = math.log(n_steps)
    return 2.0 / math.pi * (math.ceil(delta * log_t) - 1.0 / log_t)


def pid_c_sat_purpose(n_steps: int, delta: float) -> float:
    """C_sat = (2 / pi) delta log T: the value at which the tan integrator saturates when the
    cumulative excess of coverage errors reaches delta T at time T, the purpose App. C states."""
    return 2.0 / math.pi * delta * math.log(n_steps)


def pid_c_sat_grid(n_steps: int, delta: float = PID_DELTA) -> tuple[float, float, float]:
    """The three C_sat values of the Appendix A grid: the purpose of App. C, its formula as read,
    and the authors' most frequent setting."""
    return (pid_c_sat_purpose(n_steps, delta), pid_c_sat(n_steps, delta), PID_C_SAT_AUTHORS)


def theta_forecast_table(
    scores: ArrayLike, burn_in: int, max_horizon: int, period: int = 1
) -> np.ndarray:
    """F[k, j]: the (j + 1)-step forecast of a Theta model (statsmodels ``ThetaModel``) fitted to
    scores[0..k], for k = burn_in, ..., T - 2; NaN elsewhere. One fit serves every horizon.
    As in the authors' code the scores pass through ``np.nan_to_num`` before fitting."""
    from statsmodels.tsa.forecasting.theta import ThetaModel

    s = np.asarray(scores, dtype=np.float64)
    table = np.full((s.size, max_horizon), np.nan)
    for k in range(max(burn_in, 0), s.size - 1):
        fit = ThetaModel(np.nan_to_num(s[: k + 1]).astype(float), period=period).fit()
        table[k] = np.asarray(fit.forecast(max_horizon), dtype=np.float64)
    return table


def pid_scorecasts(
    table: np.ndarray, horizon: int, burn_in: int, mode: str = "phase1"
) -> np.ndarray:
    """Theta scorecast c_tau added to q_tau, from ``theta_forecast_table`` (zero until active).

    phase1: c_tau = F[tau - h, h - 1], the h-step forecast of the target's score from every score
        known at issue time, once the newest known index tau - h exceeds the burn-in.
    code: the authors' in-loop scorecaster, defined only for h = 1. At step t it fits the scores
        before index t and stores the one-step forecast, which predicts the score at t, for
        q_{t+1}: c_tau = F[tau - 2, 0] once tau - 1 exceeds the burn-in.
    """
    if mode not in MODES:
        raise ValueError(f"mode in {MODES}")
    T = table.shape[0]
    c = np.zeros(T)
    if mode == "code":
        if horizon != 1:
            raise ValueError("the authors' Theta scorecaster runs only at horizon 1")
        for tau in range(burn_in + 2, T):
            c[tau] = table[tau - 2, 0]
        return c
    if horizon > table.shape[1]:
        raise ValueError("table does not reach this horizon")
    for tau in range(burn_in + 1 + horizon, T):
        c[tau] = table[tau - horizon, horizon - 1]
    return c


def qr_scorecasts(
    scores: ArrayLike, horizon: int, burn_in: int, level: float, n_lags: int = PID_QR_LAGS
) -> np.ndarray:
    """Quantile-regression scorecast (the paper's multi-step scorecaster, App. F, Appendix A).

    For the target tau, a linear quantile regression at ``level`` of the score on its n_lags most
    recent labelled predecessors at the horizon, s_{tau-h}, ..., s_{tau-h-n_lags+1}. It is fitted
    to every labelled pair (scikit-learn ``QuantileRegressor``, HiGHS, no penalty), refitted for
    every target, and zero until the newest labelled index exceeds the burn-in.
    """
    from sklearn.linear_model import QuantileRegressor

    s = np.asarray(scores, dtype=np.float64)
    T = s.size
    c = np.zeros(T)
    first = horizon + n_lags - 1  # first target with a full set of lags
    for tau in range(burn_in + 1 + horizon, T):
        k = tau - horizon  # newest labelled index
        js = np.arange(first, k + 1)
        X = np.column_stack([s[js - horizon - i] for i in range(n_lags)])
        model = QuantileRegressor(quantile=level, alpha=0.0, solver="highs").fit(X, s[js])
        x_now = np.array([[s[tau - horizon - i] for i in range(n_lags)]])
        c[tau] = float(model.predict(x_now)[0])
    return c


def matched_scorecasts(rhat: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    """Scorecasts from the compensated loop's own residual forecast rhat (the matched variant):
    the upper score r is forecast by rhat and the lower score -r by -rhat; zero where rhat is not
    defined (NaN)."""
    r = np.nan_to_num(np.asarray(rhat, dtype=np.float64), nan=0.0)
    return -r, r


def conformal_pid_side(
    scores: ArrayLike,
    alpha: float,
    lr: float,
    horizon: int,
    *,
    window: int,
    k_i: float,
    c_sat: float,
    scorecasts: ArrayLike | None = None,
    mode: str = "phase1",
    proportional_lr: bool = True,
    start: int = 0,
    init_q: float = 0.0,
    seed_age: int = 0,
) -> dict[str, np.ndarray]:
    """One side of conformal PID with feedback delayed to the label horizon h.

    q_{t+1} = QT_{t+1} + r(x) + c_{t+1}, with QT_{t+1} = QT_t + eta (err_p - alpha) for the newest
    labelled sample p = t - h + 1, the tan integrator r of ``pid_integrator`` and the scorecast c.
    err_i = 1{s_i > q_i}. QT is a single-state loop with dead time theta = h - 1.

    phase1: the side issues its first threshold at row ``start``, with QT_start = ``init_q`` and
        q_start = QT_start + c_start; q = QT + r + c at every step from there. The rows before
        ``start`` are a seed: they have no coverage errors, but their scores enter the
        learning-rate window. QT moves once the newest labelled sample p was issued (p >= start).
        x sums (err_i - alpha) over every labelled issued sample, start <= i <= p; the integrator
        takes n = (p - start + 1) + ``seed_age`` terms, that is, it counts ``seed_age`` seed rows
        as rows at nominal coverage (they add nothing to x). eta = lr times the range (max - min)
        of the ``window`` most recent labelled scores, s_{p-window+1}..s_p. Coverage is recorded
        at every issued step. q and covered are NaN and False before ``start``.
    code: as ``quantile_integrator_log_scorecaster``, which starts at q_0 = 0 at row 0 (``start``,
        ``init_q`` and ``seed_age`` must keep their defaults): x sums over i < p and the integrator uses
        t = p; eta uses the scores s_{t-window}..s_{t-1}, and eta = lr at t = 0; coverage is
        recorded from p >= 0 on, so the first h - 1 samples count as misses; q stays 0 until the
        first label arrives.

    Returns ``q`` (the threshold: the side covers s_t iff s_t <= q_t) and ``covered``.
    """
    if mode not in MODES:
        raise ValueError(f"mode in {MODES}")
    s = np.asarray(scores, dtype=np.float64)
    T = s.size
    c = None if scorecasts is None else np.asarray(scorecasts, dtype=np.float64)
    if mode == "phase1":
        return _phase1_side(
            s, alpha, lr, horizon, window, k_i, c_sat, c, proportional_lr, start, init_q, seed_age
        )
    if start != 0 or init_q != 0.0 or seed_age != 0:
        raise ValueError("the authors' code starts at q = 0 at row 0")
    qs = np.zeros(T)
    qts = np.zeros(T)
    covered = np.zeros(T)
    misses = np.zeros(T + 1)  # misses[i] = number of misses among samples 0..i-1
    for t in range(T):
        t_pred = t - horizon + 1
        if t_pred >= 0:
            covered[t] = qs[t] >= s[t]
        misses[t + 1] = misses[t] + (1.0 - covered[t])
        if t_pred < 0:
            continue
        lo, hi = max(t - window, 0), t
        use_raw_lr = t == 0
        x = misses[t_pred] - t_pred * alpha  # errors before the newest
        if proportional_lr and not use_raw_lr:
            lr_t = lr * (s[lo:hi].max() - s[lo:hi].min()) if hi > lo else 0.0
        else:
            lr_t = lr
        grad = alpha if covered[t_pred] else -(1.0 - alpha)
        integ = pid_integrator(x, t_pred, c_sat, k_i)
        if t < T - 1:
            qts[t + 1] = qts[t] - lr_t * grad
            qs[t + 1] = qts[t + 1] + integ
            if c is not None:
                qs[t + 1] += c[t + 1]
    return {"q": qs, "covered": covered.astype(bool)}


def _phase1_side(
    s: np.ndarray,
    alpha: float,
    lr: float,
    horizon: int,
    window: int,
    k_i: float,
    c_sat: float,
    c: np.ndarray | None,
    proportional_lr: bool,
    start: int,
    init_q: float,
    seed_age: int,
) -> dict[str, np.ndarray]:
    """The phase1 recursion of ``conformal_pid_side``."""
    T = s.size
    if not 0 <= start < T:
        raise ValueError("start must index a row of the stream")
    if not 0 <= seed_age <= start:
        raise ValueError("seed_age counts seed rows: 0 <= seed_age <= start")
    cc = np.zeros(T) if c is None else c
    qs = np.full(T, np.nan)
    qts = np.full(T, np.nan)
    covered = np.zeros(T, dtype=bool)
    misses = np.zeros(T + 1)  # misses[i] = number of misses among issued samples start..i-1
    qts[start] = init_q
    qs[start] = init_q + cc[start]
    for t in range(start, T):
        covered[t] = bool(qs[t] >= s[t])
        misses[t + 1] = misses[t] + (0.0 if covered[t] else 1.0)
        if t == T - 1:
            break
        p = t - horizon + 1  # the newest labelled sample
        if p >= start:
            lo, hi = max(p + 1 - window, 0), p + 1
            if proportional_lr:
                lr_t = lr * (s[lo:hi].max() - s[lo:hi].min()) if hi > lo else 0.0
            else:
                lr_t = lr
            grad = alpha if covered[p] else -(1.0 - alpha)
            n = p - start + 1  # labelled issued samples
            integ = pid_integrator(misses[p + 1] - n * alpha, n + seed_age - 1, c_sat, k_i)
            qts[t + 1] = qts[t] - lr_t * grad
        else:
            integ = 0.0
            qts[t + 1] = qts[t]
        qs[t + 1] = qts[t + 1] + integ + cc[t + 1]
    return {"q": qs, "covered": covered}


def conformal_pid_intervals(
    residuals: ArrayLike,
    alpha: float,
    lr: float,
    horizon: int,
    *,
    window: int,
    k_i: float,
    c_sat: float,
    scorecasts: tuple[np.ndarray, np.ndarray] | None = None,
    mode: str = "phase1",
    start: int = 0,
    warm_rows: int = 0,
) -> dict[str, np.ndarray]:
    """Two-sided conformal PID on the signed residual score (the paper's Sec. 3 choice): the
    lower side tracks s = -r, the upper side s = r, each at level alpha / 2, as in the authors'
    tests/base_test.py. The interval for y_t is [yhat_t + lo_t, yhat_t + hi_t] with lo = -q_lower
    and hi = q_upper.

    ``scorecasts``: (c_lower, c_upper), the scorecasts of the two sides, or None.
    ``start`` (phase1): the first issued row; the rows before it are the seed.
    ``warm_rows`` (phase1): if positive, the run starts warm. Each side's tracker starts at the
    conformal quantile at 1 - alpha / 2 (``conformal.conformal_quantile``, as the compensated
    loop's window) of its centred scores s - c over the last ``warm_rows`` seed rows, and the
    integrator counts the ``start`` seed rows as rows at nominal coverage (``seed_age`` of
    ``conformal_pid_side``), so that it is as sensitive as in a run that age. Every scorecast
    must be active in the ``warm_rows`` rows. Otherwise the tracker starts at 0 and the
    integrator at age 0.

    Returns ``lo``, ``hi``, ``empty`` (lo > hi, or a side at the wrong infinity: a miss, width 0),
    ``covered`` (lo <= r <= hi) and ``width`` (hi - lo; 0 if empty; inf if a side is infinite).
    Before ``start`` the bounds and the width are NaN, and ``covered`` is False.
    """
    r = np.asarray(residuals, dtype=np.float64)
    if warm_rows and not 0 < warm_rows <= start:
        raise ValueError("the warm start needs 0 < warm_rows <= start seed rows")
    sides = []
    for k, sign in enumerate((-1.0, 1.0)):
        sc = None if scorecasts is None else np.asarray(scorecasts[k], dtype=np.float64)
        init_q = 0.0
        if warm_rows:
            centred = sign * r[start - warm_rows : start]
            if sc is not None:
                centred = centred - sc[start - warm_rows : start]
            init_q = conformal_quantile(centred, 1.0 - alpha / 2)
        sides.append(
            conformal_pid_side(
                sign * r,
                alpha / 2,
                lr,
                horizon,
                window=window,
                k_i=k_i,
                c_sat=c_sat,
                scorecasts=sc,
                mode=mode,
                start=start,
                init_q=init_q,
                seed_age=start if warm_rows else 0,
            )
        )
    lo, hi = -sides[0]["q"], sides[1]["q"]
    empty = (lo > hi) | (hi == -np.inf) | (lo == np.inf)
    with np.errstate(invalid="ignore"):
        width = np.where(empty, 0.0, hi - lo)
    covered = (lo <= r) & (r <= hi)
    return {"lo": lo, "hi": hi, "empty": empty, "covered": covered, "width": width}


def uninformative_width(width: ArrayLike, y_range: float) -> np.ndarray:
    """U for intervals given by their width: infinite, or wider than the range of y (the rule of
    ``delayed_aci.uninformative``, which takes half-widths)."""
    w = np.asarray(width, dtype=np.float64)
    return ~np.isfinite(w) | (w > y_range)


def pid_tune_pooled(
    segments: Sequence[tuple[np.ndarray, tuple[np.ndarray, np.ndarray] | None, float]],
    horizon: int,
    *,
    alpha: float,
    y_range: float,
    eps: float,
    c_sats: Sequence[float],
    k_factors: Sequence[float] = PID_K_FACTORS,
    window: int = PID_WINDOW,
    grid: Sequence[float] = PID_M_GRID,
    coverage_tol: float = PID_DELTA,
    warm_rows: int = PID_WARM_ROWS,
    scale_to: float | None = None,
) -> dict:
    """Replay tuning of conformal PID (Appendix A), pooled over calibration segments.

    Each segment is (residuals, scorecasts or None, B'). As the compensated loop's replay does,
    conformal PID starts at row ``window`` of the segment from a seed of the rows before it
    (``conformal_pid_intervals`` with start = window and ``warm_rows``; warm_rows = 0 starts the
    tracker at 0), and the replay scores every row from there. For every multiplier m, C_sat and
    K_I = factor x B' it pools, over the scored rows, the uninformative share U, the coverage and
    the median width over all issued intervals (an infinite interval counting as infinitely
    wide), and selects with ``select_pid_config``. ``eps`` is the replay's U target (eps / 2 in
    Phase 1, half of F7's budget); ``scale_to`` is passed on to the selection.
    """
    path: list[dict] = []
    for m in grid:
        for c_sat in c_sats:
            for factor in k_factors:
                flags, cov, widths = [], [], []
                for r, sc, b_prime in segments:
                    out = conformal_pid_intervals(
                        r,
                        alpha,
                        m,
                        horizon,
                        window=window,
                        k_i=factor * b_prime,
                        c_sat=c_sat,
                        scorecasts=sc,
                        start=window,
                        warm_rows=warm_rows,
                    )
                    flags.append(uninformative_width(out["width"][window:], y_range))
                    cov.append(out["covered"][window:])
                    widths.append(out["width"][window:])
                path.append(
                    {
                        "m": float(m),
                        "c_sat": float(c_sat),
                        "k_factor": float(factor),
                        "u": float(np.mean(np.concatenate(flags))),
                        "coverage": float(np.mean(np.concatenate(cov))),
                        "median_width": float(np.median(np.concatenate(widths))),
                    }
                )
    chosen, flag = select_pid_config(path, eps, 1.0 - alpha, coverage_tol, scale_to=scale_to)
    return {"config": chosen, "flag": flag, "path": path}


def gaussian_width_factor(c_from: float, c_to: float) -> float:
    """Factor that takes the width of a central interval of coverage c_from to coverage c_to
    when the residual is Gaussian: z((1 + c_to) / 2) / z((1 + c_from) / 2) (Appendix A.1)."""
    if not (0.0 < c_from < 1.0 and 0.0 < c_to < 1.0):
        raise ValueError("coverages must lie strictly between 0 and 1")
    z = NormalDist().inv_cdf
    return z((1.0 + c_to) / 2.0) / z((1.0 + c_from) / 2.0)


def select_pid_config(
    path: Sequence[dict],
    eps: float,
    coverage_target: float,
    coverage_tol: float,
    *,
    scale_to: float | None = None,
) -> tuple[dict, str]:
    """A replay analogue of F7's criterion. Among configurations with U <= eps and coverage within
    ``coverage_tol`` of the target, the one with the smallest median width ("valid"). If none,
    among those with U <= eps, the one with coverage nearest the target ("coverage"). If none,
    the one with the smallest U ("infeasible"). Ties go to the smaller m, then C_sat, then K_I.
    The bounds are inclusive (with a tolerance of 1e-9 for rounding). With ``scale_to`` (D-P1.11),
    the width compared is the median width scaled to coverage ``scale_to`` by
    ``gaussian_width_factor``."""

    def tie(p: dict) -> tuple[float, float, float]:
        return (p["m"], p["c_sat"], p["k_factor"])

    def width(p: dict) -> float:
        if scale_to is None:
            return float(p["median_width"])
        return float(p["median_width"]) * gaussian_width_factor(p["coverage"], scale_to)

    feasible = [p for p in path if p["u"] <= eps + _TOL]
    valid = [p for p in feasible if abs(p["coverage"] - coverage_target) <= coverage_tol + _TOL]
    if valid:
        return min(valid, key=lambda p: (width(p), *tie(p))), "valid"
    if feasible:
        best = min(feasible, key=lambda p: (abs(p["coverage"] - coverage_target), *tie(p)))
        return best, "coverage"
    return min(path, key=lambda p: (p["u"], *tie(p))), "infeasible"
