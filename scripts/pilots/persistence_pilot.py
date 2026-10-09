"""N1 Phase 1 pre-data pilot: residual persistence (synthetic, library-based).

Questions, answered before any process-data run:
  A. Does the white-noise noise-gain model (``delayed_aci.noise_gain_sd``) predict the level
     volatility and the infinite-interval share when residuals are autocorrelated, as process
     residuals are? Does a coloured variant, driven by the spectrum of the open-loop miss
     indicator from an independent calibration segment, do better?
  B. If the step size is tuned on historical data without the label delay (delay-blind), or by
     the white-noise design rule, is the infinite share still controlled once the delay acts?
     Does tuning by replaying the calibration segment through the delayed loop (delay-aware)
     control it out of sample?

Residual stream: |x_t|, with x a unit-variance Gaussian AR(1) of lag-1 autocorrelation phi
(phi = 0 is the white case the model assumes). Library loop only: sequential, stored pairing,
sliding-window quantile R = 200, alpha* = 0.10. Calibration and evaluation segments come from
the same stream but do not overlap.

Run from the repository root (about 5 min):
    set PYTHONPATH=src
    python scripts\\pilots\\persistence_pilot.py
"""

from __future__ import annotations

import math

import numpy as np

from ipis.module1_soft_sensor.evaluation import delayed_aci as d

ALPHA, WINDOW = 0.10, 200
N_INIT, N_CAL, N_EVAL = 300, 10_000, 20_000
EPS = 0.01  # budget on the infinite-interval share used for tuning in part B
GRID = (0.001, 0.0015, 0.002, 0.003, 0.005, 0.007, 0.01, 0.015, 0.02, 0.03, 0.05, 0.07, 0.1)
W = np.linspace(-np.pi, np.pi, 4096, endpoint=False)


def ar1_scores(phi: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """|x_t| for a unit-variance Gaussian AR(1) with lag-1 autocorrelation phi."""
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    c = math.sqrt(1.0 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + c * e[t]
    return np.abs(x)


def segments(phi: float, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = ar1_scores(phi, N_INIT + N_CAL + N_EVAL, np.random.default_rng(seed))
    return s[:N_INIT], s[N_INIT : N_INIT + N_CAL], s[N_INIT + N_CAL :]


def miss_spectrum(err: np.ndarray, max_lag: int = 400) -> np.ndarray:
    """Blackman-Tukey spectrum (Tukey-Hanning taper) of a 0/1 miss sequence on W.

    Normalised so that mean over W equals the variance; a white sequence therefore
    reproduces the white-noise model exactly.
    """
    x = err - err.mean()
    n = x.size
    c = np.array([np.dot(x[: n - k], x[k:]) / n for k in range(max_lag + 1)])
    lags = np.arange(1, max_lag + 1)
    taper = 0.5 * (1.0 + np.cos(np.pi * lags / max_lag))
    s = c[0] + 2.0 * (np.cos(np.outer(W, lags)) * (c[1:] * taper)).sum(axis=1)
    return np.maximum(s, 0.0)


def coloured_sd(gamma: float, theta: int, spectrum: np.ndarray) -> float:
    """Level sd of the linear dead-time loop driven by noise with the given spectrum."""
    den = np.exp(1j * W * (theta + 1)) - np.exp(1j * W * theta) + gamma
    return math.sqrt(float(np.mean(gamma**2 / np.abs(den) ** 2 * spectrum)))


def infinite_share(scores, init, theta: int, gamma: float, burn: int) -> tuple[float, dict]:
    res = d.run_delayed_aci(
        scores, theta, init_scores=init, alpha=ALPHA, gamma=gamma, window=WINDOW
    )
    return float(np.mean(~np.isfinite(res["h"][burn:]))), res


def part_a(n_seeds: int = 5, burn: int = 2000) -> None:
    print("A. Level sd and infinite share: measured vs white-noise and coloured models")
    print(
        "   phi theta  gamma | sd meas  white (err)    coloured (err) | inf meas  white  coloured"
        " | cov"
    )
    for phi in (0.0, 0.5, 0.9, 0.97):
        for theta in (0, 4, 8, 20):
            for gamma in (0.005, 0.02, 0.05):
                if gamma >= 0.8 * d.gamma_crit(theta):
                    continue
                sd_m, inf_m, sd_c, cov = [], [], [], []
                for seed in range(n_seeds):
                    init, cal, ev = segments(phi, seed)
                    open_loop = d.run_delayed_aci(
                        cal, theta, init_scores=init, alpha=ALPHA, gamma=0.0, window=WINDOW
                    )
                    err = (~open_loop["covered"]).astype(float)[500:]
                    sd_c.append(coloured_sd(gamma, theta, miss_spectrum(err)))
                    share, res = infinite_share(ev, cal[-WINDOW:], theta, gamma, burn)
                    inf_m.append(share)
                    sd_m.append(float(res["alpha"][burn:].std()))
                    cov.append(float(res["covered"][burn:].mean()))
                m_sd, w_sd, c_sd = np.mean(sd_m), d.noise_gain_sd(gamma, theta), np.mean(sd_c)
                c_inf = 0.5 * math.erfc(ALPHA / (c_sd * math.sqrt(2.0)))
                print(
                    f"  {phi:4.2f} {theta:5d} {gamma:6.3f} | {m_sd:.4f}  {w_sd:.4f} ({100 * (w_sd / m_sd - 1):+4.0f}%)"
                    f"  {c_sd:.4f} ({100 * (c_sd / m_sd - 1):+4.0f}%) | {100 * np.mean(inf_m):6.2f}%"
                    f" {100 * d.infinite_fraction_pred(gamma, theta):6.2f}% {100 * c_inf:6.2f}%"
                    f" | {np.mean(cov):.3f}"
                )


def tune(cal: np.ndarray, init: np.ndarray, theta: int, burn: int) -> float:
    """Largest grid step size whose replayed infinite share is <= EPS (capped at 0.8 gamma_crit)."""
    best = GRID[0]
    for gamma in GRID:
        if gamma >= 0.8 * d.gamma_crit(theta):
            break
        if infinite_share(cal, init, theta, gamma, burn)[0] > EPS:
            break
        best = gamma
    return best


def part_b(n_seeds: int = 3, burn: int = 1000) -> None:
    print("\nB. Step size tuned delay-blind (replay at theta = 0), delay-aware (replay at theta),")
    print("   or by the white-noise rule; evaluated at theta on an independent segment")
    print(
        "   phi theta | blind: gamma  inf    cov  | aware: gamma  inf    cov  | white rule: gamma  inf    cov"
    )
    for phi in (0.5, 0.9, 0.97):
        for theta in (4, 8, 20):
            rows = []
            for seed in range(n_seeds):
                init, cal, ev = segments(phi, seed)
                gammas = (
                    tune(cal, init, 0, burn),
                    tune(cal, init, theta, burn),
                    d.design_gamma(theta),
                )
                row = []
                for gamma in gammas:
                    share, res = infinite_share(ev, cal[-WINDOW:], theta, gamma, burn)
                    row.append((gamma, share, float(res["covered"][burn:].mean())))
                rows.append(row)
            cells = [np.mean([r[j] for r in rows], axis=0) for j in range(3)]
            print(
                f"  {phi:4.2f} {theta:5d} |"
                + " |".join(f"  {g:.4f} {100 * p:5.2f}% {c:.3f}" for g, p, c in cells)
            )


if __name__ == "__main__":
    part_a()
    part_b()
