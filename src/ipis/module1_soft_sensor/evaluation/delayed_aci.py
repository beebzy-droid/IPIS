"""Delayed-feedback adaptive conformal calibration for soft sensors (IPIS M1, claim N1).

Timing convention (matches ``scripts/pilots``): at step t the sensor issues the interval
for sample t from its current state; at the END of step t it receives every label whose
delay has elapsed, so the label of sample s arrives at the end of step s + theta_s.
theta = 0 is ordinary immediate-feedback ACI. El Halabi and Brandt (2026) write tau = theta + 1.

Loops, i.e. how the calibration level moves when the label of sample s arrives:
    sequential  a <- a + g (a* - err_s)                     single state: an integral loop
                                                             with dead time theta
    projected   sequential, then a <- clip(a, lo, hi)
    smith       a <- a + g (a* - [err_s - c(a_s) + c(a)])   c = clip(., 0, 1); the model
                E[err | a] = a removes the dead time from the loop (Smith-predictor form)
    phase       level_t = level_{t-P} + g (a* - err_{t-P}), P = theta + 1: P interleaved,
                delay-free ACI chains (tau-DACI of El Halabi and Brandt 2026); fixed delay only

Pairing, the bookkeeping rule (reviewer items R2.2, R4.8):
    stored   err_s = 1{score_s > h_s}, h_s = half-width ISSUED for sample s       (correct)
    arrival  err_s = 1{score_s > h_t}, h_t = half-width issued at arrival step t (incorrect;
             the defect latent in ``ACIConformal.update`` via its scalar last half-width)

Scores enter the conformal window only when their label arrives.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile

LOOPS = ("sequential", "projected", "smith", "phase")
PAIRINGS = ("stored", "arrival")


def gamma_crit(theta: int) -> float:
    """Linear stability limit of the single-state delayed loop.

    Linearised about E[err | a] = a, the level error obeys e_{t+1} - e_t + g e_{t-theta} = 0,
    asymptotically stable iff 0 < g < 2 cos(theta pi / (2 theta + 1)) = 2 sin(pi / (4 theta + 2))
    (Levin and May 1976; Kuruklis 1994). theta = 0 gives 2, theta = 1 gives 1.
    """
    if theta < 0:
        raise ValueError("theta must be >= 0")
    return 2.0 * math.sin(math.pi / (4 * theta + 2))


def noise_gain_sd(gamma: float, theta: int, alpha: float = 0.1, n_freq: int | None = None) -> float:
    """Stationary sd of the level predicted by the linear stochastic loop model.

    e_{t+1} = e_t - g (e_{t-theta} + eta_{t-theta}), var(eta) = a*(1 - a*), so
    H(z) = -g / (z^{theta+1} - z^theta + g) and sd^2 = var(eta) (1/2pi) int |H(e^{iw})|^2 dw.
    Validated to within 1-19 % for g <= 0.8 gamma_crit (pilots/h2_check.py); overestimates
    near the limit, where saturation of the level caps its excursions. inf at or above the limit.
    """
    if gamma <= 0:
        raise ValueError("gamma must be > 0")
    if gamma >= gamma_crit(theta):
        return math.inf
    n = n_freq or max(2**16, 256 * (theta + 1))
    w = np.linspace(-np.pi, np.pi, n, endpoint=False)
    den = np.exp(1j * w * (theta + 1)) - np.exp(1j * w * theta) + gamma
    return math.sqrt(alpha * (1.0 - alpha) * float(np.mean(gamma**2 / np.abs(den) ** 2)))


def infinite_fraction_pred(gamma: float, theta: int, alpha: float = 0.1) -> float:
    """Predicted share of issued intervals equal to the whole line: P(level <= 0) = Phi(-a*/sd)."""
    sd = noise_gain_sd(gamma, theta, alpha)
    return 0.5 if math.isinf(sd) else 0.5 * math.erfc(alpha / (sd * math.sqrt(2.0)))


def design_gamma(theta: int, alpha: float = 0.1, eps: float = 0.01, n_grid: int = 400) -> float:
    """N1 design rule: largest step size with predicted infinite-interval share <= eps.

    Searched only on (0, 0.8 gamma_crit], the region where the model is validated, so the
    result is capped at 0.8 gamma_crit. Returns NaN if no step size in that region complies.
    """
    gmax = 0.8 * gamma_crit(theta)
    best = float("nan")
    for g in np.linspace(gmax / n_grid, gmax, n_grid):
        if infinite_fraction_pred(float(g), theta, alpha) > eps:
            break
        best = float(g)
    return best


def run_delayed_aci(
    scores,
    theta,
    *,
    init_scores,
    alpha: float = 0.1,
    gamma: float = 0.005,
    window: int = 200,
    loop: str = "sequential",
    pairing: str = "stored",
    bounds: tuple[float, float] = (0.0, 1.0),
) -> dict[str, np.ndarray]:
    """Replay a residual stream through a delayed conformal calibrator.

    scores: |y_t - yhat_t|, revealed to the calibrator only when the label arrives.
    theta: int, or per-sample int array; a negative entry is a label that never arrives.
    Returns ``h`` (half-width, inf = whole line), ``covered`` (true coverage of the ISSUED
    interval), ``alpha`` (level used at issue) and ``fed`` (error signal the loop received).
    """
    if loop not in LOOPS or pairing not in PAIRINGS:
        raise ValueError(f"loop in {LOOPS}, pairing in {PAIRINGS}")
    s = np.asarray(scores, dtype=np.float64)
    T = s.size
    fixed = np.isscalar(theta)
    d = np.full(T, int(theta)) if fixed else np.asarray(theta, dtype=int)
    if loop == "phase" and not fixed:
        raise ValueError("phase-interleaving requires a fixed delay")
    win = deque(np.abs(np.asarray(init_scores, dtype=np.float64)).tolist(), maxlen=window)
    if not win:
        raise ValueError("init_scores must seed the window")
    arrivals: dict[int, list[int]] = {}
    for i in range(T):
        if d[i] >= 0 and i + d[i] < T:
            arrivals.setdefault(int(i + d[i]), []).append(i)
    h = np.empty(T)
    used = np.empty(T)
    covered = np.empty(T, dtype=bool)
    fed = np.full(T, np.nan)
    a, lo, hi = float(alpha), bounds[0], bounds[1]
    period = int(theta) + 1 if loop == "phase" else 0
    for t in range(T):
        if loop == "phase":
            a = alpha if t < period else used[t - period] + gamma * (alpha - fed[t - period])
        h[t] = conformal_quantile(np.asarray(win), 1.0 - a)
        used[t], covered[t] = a, s[t] <= h[t]
        for i in arrivals.get(t, ()):
            e = float(s[i] > (h[i] if pairing == "stored" else h[t]))
            fed[i] = e
            if loop == "sequential":
                a += gamma * (alpha - e)
            elif loop == "projected":
                a = min(max(a + gamma * (alpha - e), lo), hi)
            elif loop == "smith":
                a += gamma * (alpha - (e - min(max(used[i], 0.0), 1.0) + min(max(a, 0.0), 1.0)))
            win.append(s[i])
    return {"h": h, "covered": covered, "alpha": used, "fed": fed}


def diagnostics(res: dict[str, np.ndarray], local: int = 100) -> dict[str, float]:
    """Everything R2.3/R2.4 asked to see: marginal coverage with a Wilson 95 % interval,
    infinite share, the finite-width distribution, local-coverage dispersion, level range."""
    c = res["covered"].astype(float)
    n, p = c.size, float(c.mean())
    z = 1.959963984540054
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    h = res["h"]
    fin = h[np.isfinite(h)]
    roll = np.convolve(c, np.ones(local) / local, mode="valid") if n >= local else c
    q = np.percentile(fin, [50, 90, 99]) if fin.size else [np.nan] * 3
    return {
        "coverage": p,
        "coverage_lo95": centre - half,
        "coverage_hi95": centre + half,
        "infinite_share": float(np.mean(~np.isfinite(h))),
        "width_median": float(2 * q[0]),
        "width_p90": float(2 * q[1]),
        "width_p99": float(2 * q[2]),
        "width_max": float(2 * fin.max()) if fin.size else np.nan,
        "local_cov_sd": float(roll.std()),
        "local_cov_min": float(roll.min()),
        "alpha_min": float(res["alpha"].min()),
        "alpha_max": float(res["alpha"].max()),
    }
