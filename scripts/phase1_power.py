"""N1 Phase 1 design-stage power analysis (synthetic, library-based; pre-registration Sec. 3E).

Residual streams are Gaussian AR(1) of lag-1 autocorrelation phi. The debutanizer values come from
the committed pre-check (docs/paper/evidence/phase1_precheck.json: lag-1 0.970, IACT 62, roughly
AR(1) with phi = 0.965 from lag 10 to lag 100). For TEP the pre-registration fixes phi = 0.5 and
0.9, because its residuals do not exist until the generator has run.

Three questions, each answered with the analysis code that Phase 1 will use:
1. Debutanizer, F2. Segments: 1660 calibration rows, 719 evaluation rows, theta = 3. How often
   does the primary test detect the delay-attributable increase in uninformative intervals at the
   delay-blind step size? This uses the paired block bootstrap and its 8-block floor.
2. Debutanizer, F6. How far does the measured width ratio of compensated to uncompensated
   intervals stray from the ratio predicted by the calibration-segment autocorrelation?
3. TEP, F2, F5a, F5b and F6. Design (pre-registration D-P1.8): 15 independent 100-h runs, 5 per
   regime (in Phase 1 each on its own MRG32k3a stream; here each synthetic run has its own numpy
   seed). At the 3-min cadence each run gives 800 calibration rows
   (hours 30-70) and 600 evaluation rows (hours 70-100), at theta = 4. Step sizes are tuned on the
   pooled calibration rows of a regime's five runs; the first 200 rows of each calibration segment
   seed the conformal window and are not replayed. The compensation forecaster is fitted on the
   whole calibration segment.
   - F2: the paired difference over runs, tested with a two-sided Bonferroni 97.5 % t interval.
   - F5a and F5b: the distribution, over studies, of the 15-run mean uninformative share U of the
     uncompensated and the compensated loop, each tuned by replay to the budget eps = 1 %, to
     eps / 2 and to eps / 4. This calibrates the safety factor of the tuning target.
   - F6: the mean relative error, over runs, of the width ratio predicted from the calibration
     autocorrelation.

Simplifications, stated in the pre-registration: y_range is the range of the synthetic residual on
the calibration rows, not of y; the debutanizer bootstrap uses 1000 replicates (2000 in Phase 1);
the AR(1) residuals have no 5-row label hold, which TEP arm T1 has.

Run from the repository root (about 1 h with 2 workers; results do not depend on the number):
    set PYTHONPATH=src
    python scripts\\phase1_power.py --json --workers 2
"""

from __future__ import annotations

import argparse
import math
from multiprocessing import Pool

import numpy as np
from scipy import stats

from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.evaluation.delay_compensation import (
    fit_direct_forecaster,
    predicted_width_ratio,
    select_order,
)
from ipis.module1_soft_sensor.evaluation.inference import (
    acf,
    block_length,
    n_blocks,
    paired_block_bootstrap_ci,
)

ALPHA, WINDOW, EPS = 0.10, 200, 0.01
TARGETS = {"eps": EPS, "half": EPS / 2, "quarter": EPS / 4}  # replay-tuning targets
ARMS = ("raw", "comp")


def ar1(phi: float, n: int, rng: np.random.Generator) -> np.ndarray:
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    c = math.sqrt(1.0 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + c * e[t]
    return x


def u_flags(scores, init, theta: int, gamma: float, y_range: float) -> np.ndarray:
    res = d.run_delayed_aci(
        scores, theta, init_scores=init, alpha=ALPHA, gamma=gamma, window=WINDOW
    )
    return d.uninformative(res["h"], y_range).astype(float)


def tuned_gamma(cal: np.ndarray, theta: int, y_range: float) -> float:
    out = d.replay_tune(cal[WINDOW:], theta, init_scores=cal[:WINDOW], y_range=y_range, eps=EPS)
    return float(out["gamma"])


def debutanizer_case(phi: float, seed: int, theta: int = 3, n_cal: int = 1660, n_ev: int = 719):
    rng = np.random.default_rng(seed)
    x = ar1(phi, n_cal + n_ev, rng)
    cal, ev = slice(0, n_cal), slice(n_cal, None)
    y_range = float(np.ptp(x[cal]))
    s = np.abs(x)
    g = tuned_gamma(s[cal], 0, y_range)
    init = s[cal][-WINDOW:]
    u_th, u_0 = (u_flags(s[ev], init, th, g, y_range) for th in (theta, 0))
    diff = u_th - u_0
    b = block_length(diff)
    reliable = n_blocks(diff.size, b) >= 8
    lo, _ = paired_block_bootstrap_ci(u_th, u_0, b, n_boot=1000, level=0.975, seed=seed)
    detected = reliable and diff.mean() >= 0.01 and lo > 0
    # F6: width ratio predicted from calibration autocorrelation vs measured on evaluation rows
    order = select_order(x, theta, max_order=10, fit=cal)
    xhat = fit_direct_forecaster(x, theta, order=order, fit=cal).predict(x)
    pred = predicted_width_ratio(acf(x[cal], theta + order + 1), theta, order)
    comp = np.abs(x - xhat)[ev]
    meas = float(np.quantile(comp, 1 - ALPHA) / np.quantile(s[ev], 1 - ALPHA))
    return {
        "gamma_blind": g,
        "effect": float(diff.mean()),
        "reliable": bool(reliable),
        "detected": bool(detected),
        "width_rel_error": meas / pred - 1.0,
    }


TEP_CAL, TEP_EV = 800, 600  # 3-min rows: hours 30-70 calibrate, hours 70-100 evaluate


def tep_regime(phi: float, study: int, regime: int, theta: int = 4, n_runs: int = 5) -> list[dict]:
    """Five runs of one regime; step sizes are tuned on their pooled calibration segments."""
    cal, ev = slice(0, TEP_CAL), slice(TEP_CAL, None)
    xs = [
        ar1(phi, TEP_CAL + TEP_EV, np.random.default_rng(10_000 * (study + 1) + 100 * regime + r))
        for r in range(n_runs)
    ]
    y_range = float(np.ptp(np.concatenate([x[cal] for x in xs])))
    scores: dict[str, list[np.ndarray]] = {"raw": [np.abs(x) for x in xs], "comp": []}
    preds = []
    for x, s in zip(xs, scores["raw"], strict=True):
        order = select_order(x, theta, max_order=10, fit=cal)
        fc = fit_direct_forecaster(x, theta, order=order, fit=cal)
        c = np.abs(x - fc.predict(x))
        c[: fc.warmup] = s[: fc.warmup]  # rows before the first full lag window: no prediction
        scores["comp"].append(c)
        preds.append(predicted_width_ratio(acf(x[cal], theta + order + 1), theta, order))

    def pooled(arm: str, th: int, eps: float) -> float:
        segs = [(sc[cal][WINDOW:], sc[cal][:WINDOW]) for sc in scores[arm]]
        return float(d.replay_tune_pooled(segs, th, y_range=y_range, eps=eps)["gamma"])

    g_blind = pooled("raw", 0, EPS)
    gam = {(arm, tgt): pooled(arm, theta, eps) for arm in ARMS for tgt, eps in TARGETS.items()}
    out = []
    for k in range(n_runs):
        s, c = scores["raw"][k], scores["comp"][k]
        init = {"raw": s[cal][-WINDOW:], "comp": c[cal][-WINDOW:]}
        f2 = u_flags(s[ev], init["raw"], theta, g_blind, y_range) - u_flags(
            s[ev], init["raw"], 0, g_blind, y_range
        )
        meas = float(np.quantile(c[ev], 1 - ALPHA) / np.quantile(s[ev], 1 - ALPHA))
        row = {"f2": float(f2.mean()), "width_rel_error": meas / preds[k] - 1.0}
        for (arm, tgt), g in gam.items():
            sc = scores[arm][k]
            row[f"u_{arm}_{tgt}"] = float(np.mean(u_flags(sc[ev], init[arm], theta, g, y_range)))
            row[f"gamma_{arm}_{tgt}"] = g
        out.append(row)
    return out


def tep_study(args: tuple[float, int]) -> dict:
    phi, study = args
    runs = [r for regime in range(3) for r in tep_regime(phi, study, regime)]
    n_runs = len(runs)
    f2 = np.array([r["f2"] for r in runs])
    se = f2.std(ddof=1) / math.sqrt(n_runs) if np.ptp(f2) > 0 else 0.0
    lo = f2.mean() - stats.t.ppf(1 - 0.025 / 2, n_runs - 1) * se
    out = {"f2_detected": bool(f2.mean() >= 0.01 and lo > 0), "f2_effect": float(f2.mean())}
    for arm in ARMS:
        for tgt in TARGETS:
            out[f"u_{arm}_{tgt}"] = float(np.mean([r[f"u_{arm}_{tgt}"] for r in runs]))
    for tgt in TARGETS:
        out[f"gamma_ratio_{tgt}"] = float(
            np.mean([r[f"gamma_comp_{tgt}"] / r[f"gamma_raw_{tgt}"] for r in runs])
        )
    out["width_mean_rel_error"] = float(np.mean([r["width_rel_error"] for r in runs]))
    return out


def summarize_tep(studies: list[dict]) -> dict:
    row: dict = {
        "power_f2": float(np.mean([s["f2_detected"] for s in studies])),
        "mean_f2_effect": float(np.mean([s["f2_effect"] for s in studies])),
        "f6_pass_at_tolerance": {
            str(tol): float(np.mean([abs(s["width_mean_rel_error"]) <= tol for s in studies]))
            for tol in (0.10, 0.15, 0.20)
        },
        "gamma_ratio_comp_raw": {
            tgt: float(np.mean([s[f"gamma_ratio_{tgt}"] for s in studies])) for tgt in TARGETS
        },
        "u": {},
        "study_mean_u": {},
    }
    for arm in ARMS:
        for tgt in TARGETS:
            key = f"{arm}_{tgt}"
            u = np.array([s[f"u_{key}"] for s in studies])
            row["u"][key] = {
                "mean": float(u.mean()),
                "p95": float(np.quantile(u, 0.95)),
                "max": float(u.max()),
                "share_above_eps": float(np.mean(u > EPS)),
                "share_above_1.5eps": float(np.mean(u > 1.5 * EPS)),
                "share_above_2eps": float(np.mean(u > 2 * EPS)),
            }
            row["study_mean_u"][key] = u.tolist()
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="N1 Phase 1 power analysis (synthetic)")
    ap.add_argument("--reps", type=int, default=200, help="debutanizer replicates per phi")
    ap.add_argument("--studies", type=int, default=200, help="TEP replicate studies per phi")
    ap.add_argument("--workers", type=int, default=1, help="processes for the TEP studies")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--parts", nargs="+", default=["debutanizer", "tep"])
    args = ap.parse_args()

    payload: dict = {"debutanizer": {}, "tep": {}}
    for phi in (0.965, 0.970) if "debutanizer" in args.parts else ():
        cases = [debutanizer_case(phi, seed) for seed in range(args.reps)]
        rel = np.abs([c["width_rel_error"] for c in cases])
        row = {
            "power_f2": float(np.mean([c["detected"] for c in cases])),
            "share_unreliable": float(np.mean([not c["reliable"] for c in cases])),
            "mean_effect": float(np.mean([c["effect"] for c in cases])),
            "median_gamma_blind": float(np.median([c["gamma_blind"] for c in cases])),
            "width_rel_error_p95": float(np.quantile(rel, 0.95)),
            "width_rel_error_median": float(np.median(rel)),
        }
        payload["debutanizer"][str(phi)] = row
        print(f"debutanizer phi={phi}: {row}", flush=True)
    for phi in (0.5, 0.9) if "tep" in args.parts else ():
        jobs = [(phi, k) for k in range(args.studies)]
        if args.workers > 1:
            with Pool(args.workers) as pool:
                studies = pool.map(tep_study, jobs, chunksize=1)
        else:
            studies = [tep_study(j) for j in jobs]
        row = summarize_tep(studies)
        payload["tep"][str(phi)] = row
        brief = {k: v for k, v in row.items() if k != "study_mean_u"}
        print(f"tep phi={phi}: {brief}", flush=True)
    if args.json:
        from ipis.shared.evidence import dump_evidence

        payload["settings"] = {
            "reps": args.reps,
            "studies": args.studies,
            "eps": EPS,
            "targets": TARGETS,
        }
        print("evidence ->", dump_evidence("phase1_power", payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
