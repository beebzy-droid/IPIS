"""N1'' pre-data pilot: delay-compensated conformal calibration (synthetic, library-based).

The 2x2 that reviewer R4.9 asked for: residual compensation (off / on) x calibration loop (off,
static split conformal / on, delayed ACI tuned by replay). Compensation is the direct
(theta + 1)-step residual predictor of ``delay_compensation``; its order is chosen by BIC on the
calibration segment. Also checks the width ratio predicted from the calibration-segment
autocorrelation alone (``predicted_width_ratio``) against the measured ratio.

Everything is fitted or tuned on the calibration segment (forecaster, static quantile, step size)
and measured on the evaluation segment, which follows it and does not overlap it. The measured
width ratio is the ratio of the 90 % quantiles of the compensated and raw scores on the evaluation
rows, as in the pre-registration (Sec. 5.4, F6). Tuning and evaluation use no burn-in, as the
pre-registered protocol does.

Residuals: x_t, a unit-variance Gaussian AR(1) of lag-1 autocorrelation phi. phi = 0.965 matches
the debutanizer training residuals at lags of 10 and more (docs/paper/evidence/phase1_precheck.json:
lag-1 0.970, lag-10 0.698, lag-50 0.166, IACT 62); at lags 2 to 5 they decay faster than this
AR(1), so the gain at theta = 3 is smaller on the debutanizer itself. Budget eps = 1 % unusable
intervals.

Run from the repository root (about 4 min):
    set PYTHONPATH=src
    python scripts\\pilots\\compensation_pilot.py
"""

from __future__ import annotations

import math

import numpy as np

from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.evaluation.delay_compensation import (
    fit_direct_forecaster,
    predicted_width_ratio,
    select_order,
)
from ipis.module1_soft_sensor.evaluation.inference import acf

ALPHA, WINDOW, EPS = 0.10, 200, 0.01
N_INIT, N_CAL, N_EVAL = 300, 10_000, 20_000


def ar1(phi: float, n: int, rng: np.random.Generator) -> np.ndarray:
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    c = math.sqrt(1.0 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + c * e[t]
    return x


def loop_metrics(scores: np.ndarray, init: np.ndarray, theta: int, gamma: float, y_range: float):
    res = d.run_delayed_aci(
        scores, theta, init_scores=init, alpha=ALPHA, gamma=gamma, window=WINDOW
    )
    h, cov = res["h"], res["covered"].astype(float)
    roll = np.convolve(cov, np.ones(100) / 100, mode="valid")
    fin = h[np.isfinite(h)]
    return {
        "U": float(np.mean(d.uninformative(h, y_range))),
        "width": float(2 * np.median(fin)) if fin.size else math.inf,
        "cov": float(cov.mean()),
        "local_min": float(roll.min()),
    }


def one_case(phi: float, theta: int, seed: int) -> dict:
    x = ar1(phi, N_INIT + N_CAL + N_EVAL, np.random.default_rng(1000 + seed))
    cal = slice(N_INIT, N_INIT + N_CAL)
    ev = slice(N_INIT + N_CAL, None)
    y_range = float(np.ptp(x[cal]))
    order = select_order(x, theta, max_order=10, fit=cal)
    xhat = fit_direct_forecaster(x, theta, order=order, fit=cal).predict(x)
    pred = predicted_width_ratio(acf(x[cal], theta + order + 1), theta, order)
    raw, comp = np.abs(x), np.abs(x - xhat)
    out = {
        "order": order,
        "pred_ratio": pred,
        "meas_ratio": float(np.quantile(comp[ev], 1 - ALPHA) / np.quantile(raw[ev], 1 - ALPHA)),
    }
    for arm, s in (("raw", raw), ("comp", comp)):
        out[f"static_{arm}"] = float(2 * np.quantile(s[cal], 1 - ALPHA))
        out[f"static_{arm}_cov"] = float(np.mean(s[ev] <= out[f"static_{arm}"] / 2))
        init = s[cal][-WINDOW:]
        tuned = d.replay_tune(
            s[cal][WINDOW:], theta, init_scores=s[cal][:WINDOW], y_range=y_range, eps=EPS
        )
        out[f"{arm}_gamma"] = tuned["gamma"]
        out[f"{arm}_feasible"] = tuned["feasible"]
        for key, val in loop_metrics(s[ev], init, theta, tuned["gamma"], y_range).items():
            out[f"{arm}_{key}"] = val
        for key, val in loop_metrics(s[ev], init, theta, 0.02, y_range).items():
            out[f"{arm}_g02_{key}"] = val
    return out


def main() -> None:
    print(
        "phi theta | width ratio comp/raw: measured on evaluation rows, predicted"
        " | loop off (static): cov raw, comp"
    )
    print("          | loop on, replay-tuned: gamma, U, median width, min local cov (raw -> comp)")
    print("          | fixed gamma = 0.02: U (raw -> comp)")
    for phi in (0.9, 0.965):
        for theta in (0, 3, 7, 12):
            runs = [one_case(phi, theta, s) for s in range(3)]

            def m(k: str, runs: list[dict] = runs) -> float:
                return float(np.mean([r[k] for r in runs]))

            print(
                f"{phi:5.3f} {theta:3d} | {m('meas_ratio'):.3f}, {m('pred_ratio'):.3f} "
                f"(order {m('order'):.1f})"
                f" | {m('static_raw_cov'):.3f}, {m('static_comp_cov'):.3f}"
            )
            print(
                f"          | {m('raw_gamma'):.4f} -> {m('comp_gamma'):.4f}, "
                f"{100 * m('raw_U'):.2f}% -> {100 * m('comp_U'):.2f}%, "
                f"{m('raw_width'):.3f} -> {m('comp_width'):.3f}, "
                f"{m('raw_local_min'):.2f} -> {m('comp_local_min'):.2f}; "
                f"cov {m('raw_cov'):.3f} / {m('comp_cov'):.3f}; "
                f"feasible {all(r['raw_feasible'] and r['comp_feasible'] for r in runs)}"
            )
            print(f"          | {100 * m('raw_g02_U'):.2f}% -> {100 * m('comp_g02_U'):.2f}%")


if __name__ == "__main__":
    main()
