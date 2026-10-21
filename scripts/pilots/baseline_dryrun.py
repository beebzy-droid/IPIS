"""Dry run of the Appendix A baselines in the design of F7 (pre-registration Appendix A.5;
2026-10-20; library-based, run from the repository root with PYTHONPATH=src).

Question: do the Appendix A implementations of conformal PID and SPCI run end to end in the F7
design, at what cost, and how far are they from the compensated loop when the residual is a
Gaussian AR(1)? This is a design check of the code and the tuning rules, not evidence on F7,
which is decided on the TEP runs.

Design, as scripts/phase1_power.py sets up TEP: 5 runs of one regime, each a Gaussian AR(1)
residual stream of lag-1 autocorrelation phi (0.5 or 0.9, the TEP values of the power analysis)
with its own numpy seed; 800 calibration and 600 evaluation rows; theta = 4 (h = 5); 90 %
intervals; budget eps = 1 % and tuning target eps / 2; y_range is the range of the residual on
the pooled calibration rows, as in the power analysis.
- Compensated loop: the direct (theta + 1)-step forecaster fitted on the calibration rows, its
  order from select_order; delayed ACI on |r - rhat| with the replay-tuned step size; the first
  200 calibration rows seed the window and are not replayed.
- Conformal PID with each scorecaster of Appendix A.2 (QR and Theta, which forecast once the
  newest labelled index exceeds 50; matched): one run per series from calibration row 200, seeded
  from the rows before it (the tracker starts at the conformal 0.95 quantile of each side's
  centred scores over rows 100-199). pid_tune_pooled replays the pooled calibration rows from row
  200 (joint grid of m, C_sat and K_I). Two selections from the same replay: F7 as ratified (the
  smallest replayed median width) and D-P1.11 (that width scaled to 0.90 coverage). Also
  evaluated: the first draft's selection rule (the largest m of the first U-feasible run of the
  grid, C_sat as read from App. C, K_I = B'), applied to this grid and recursion.
- SPCI: spci_rolling at h = 5 with w = spci_window(800) = 87, refitted every step on at most 800
  labelled residuals, random state 1103 + run.
Reported per method and run: the median width over all issued evaluation intervals (an infinite
interval counting as infinitely wide), the uninformative share U and the marginal coverage. Per
method, against the compensated loop: the change of the mean run-median width, the number of
runs in which the run-median width is smaller, and whether F7's conditions would hold in this
design (5 runs, not 15: "narrower" means at least 5 % on the mean and in at least 4 of 5 runs);
the same with each run's width scaled to the loop's coverage in that run (D-P1.11); the coverage
gap. Timings on one core.

Run from the repository root (about 20 min per phi on one core):
    set PYTHONPATH=src
    python scripts\\pilots\\baseline_dryrun.py --phi 0.5 --out docs\\paper\\evidence\\baseline_dryrun_phi05.json
    python scripts\\pilots\\baseline_dryrun.py --phi 0.9 --out docs\\paper\\evidence\\baseline_dryrun_phi09.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from importlib import metadata
from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.evaluation import baselines as b
from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.evaluation.delay_compensation import (
    fit_direct_forecaster,
    select_order,
)

ALPHA, EPS, WINDOW, THETA = 0.1, 0.01, 200, 4
H = THETA + 1
CAL, EV, RUNS = 800, 600, 5
SEED0 = 5000  # run k uses numpy seed SEED0 + k
NARROWER_RUNS = 4  # of 5; F7 asks 12 of 15
TOL = 1e-9  # inclusive bounds


def ar1(phi: float, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    c = math.sqrt(1.0 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + c * e[t]
    return x


def summary(width: np.ndarray, covered: np.ndarray, y_range: float) -> dict[str, float]:
    w = np.asarray(width, dtype=float)
    return {
        "median_width": float(np.median(w)),
        "u": float(np.mean(~np.isfinite(w) | (w > y_range))),
        "coverage": float(np.mean(covered)),
    }


def narrower(rw: np.ndarray, lw: np.ndarray, valid: bool) -> dict:
    ratio = float(rw.mean() / lw.mean())
    runs = int(np.sum(rw < lw))
    return {
        "width_vs_loop_pct": 100.0 * (ratio - 1.0),
        "runs_narrower": runs,
        "f7_conditions_in_this_design": bool(
            valid and ratio <= 0.95 + TOL and rw.size == RUNS and runs >= NARROWER_RUNS
        ),
    }


def compare(runs: list[dict], loop: list[dict]) -> dict:
    """Against the compensated loop, over the runs both have: validity, F7 as ratified, and the
    coverage-matched comparison of D-P1.11 (each run's width scaled to the loop's coverage in
    that run by the Gaussian quantile ratio)."""
    n = len(runs)
    rw = np.array([r["median_width"] for r in runs])
    lw = np.array([r["median_width"] for r in loop[:n]])
    rc = np.array([r["coverage"] for r in runs])
    lc = np.array([r["coverage"] for r in loop[:n]])
    u = float(np.mean([r["u"] for r in runs]))
    cov = float(rc.mean())
    valid = u <= 2 * EPS + TOL and abs(cov - (1 - ALPHA)) <= 0.02 + TOL
    scaled = rw * np.array([b.gaussian_width_factor(c, cl) for c, cl in zip(rc, lc, strict=True)])
    return {
        "runs": n,
        "mean_u": u,
        "mean_coverage": cov,
        "valid": bool(valid),
        "coverage_gap_pp": 100.0 * (cov - float(lc.mean())),
        "as_ratified": narrower(rw, lw, valid),
        "coverage_matched": narrower(scaled, lw, valid),
    }


def run_pid(
    xs: list[np.ndarray], scs: list, cfg: dict, y_range: float, ev: slice
) -> list[dict[str, float]]:
    """One run per series from row WINDOW, seeded and warm-started as in the replay."""
    out = []
    for x, sc in zip(xs, scs, strict=True):
        k_i = cfg["k_factor"] * float(np.max(np.abs(x[:CAL])))
        o = b.conformal_pid_intervals(
            x,
            ALPHA,
            cfg["m"],
            H,
            window=WINDOW,
            k_i=k_i,
            c_sat=cfg["c_sat"],
            scorecasts=sc,
            start=WINDOW,
            warm_rows=b.PID_WARM_ROWS,
        )
        out.append(summary(o["width"][ev], o["covered"][ev], y_range))
    return out


def first_draft_rule(path: list[dict], c_sat: float) -> dict | None:
    """The first draft's selection rule: along m, at C_sat as read and K_I = B', the largest m
    of the first run of configurations with U within the target."""
    chosen, started = None, False
    for p in path:
        if p["c_sat"] != c_sat or p["k_factor"] != 1.0:
            continue
        if p["u"] <= EPS / 2 + TOL:
            chosen, started = p, True
        elif started:
            break
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phi", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spci-runs", type=int, default=RUNS)
    args = ap.parse_args()

    cal, ev = slice(0, CAL), slice(CAL, None)
    xs = [ar1(args.phi, CAL + EV, SEED0 + k) for k in range(RUNS)]
    y_range = float(np.ptp(np.concatenate([x[cal] for x in xs])))
    timing: dict[str, float] = {}
    out: dict = {"phi": args.phi, "y_range": y_range, "timing_s": timing}

    # compensated loop
    t0 = time.time()
    comp, rhat = [], []
    for x in xs:
        order = select_order(x, THETA, max_order=10, fit=cal)
        fc = fit_direct_forecaster(x, THETA, order=order, fit=cal)
        xh = fc.predict(x)
        c = np.abs(x - xh)
        c[: fc.warmup] = np.abs(x[: fc.warmup])
        rh = xh.copy()
        rh[: fc.warmup] = np.nan
        comp.append(c)
        rhat.append(rh)
    segs = [(c[cal][WINDOW:], c[cal][:WINDOW]) for c in comp]
    gamma = d.replay_tune_pooled(segs, THETA, y_range=y_range, eps=EPS / 2)["gamma"]
    loop = []
    for c in comp:
        res = d.run_delayed_aci(
            c[ev], THETA, init_scores=c[cal][-WINDOW:], alpha=ALPHA, gamma=gamma, window=WINDOW
        )
        loop.append(summary(2.0 * res["h"], res["covered"], y_range))
    out["loop"] = {"gamma": gamma, "runs": loop}
    timing["loop"] = round(time.time() - t0, 1)

    # conformal PID: scorecasts of the two sides (lower side scores -r, upper side r)
    c_sats = b.pid_c_sat_grid(CAL + EV)
    burn = b.PID_SCORECAST_MIN
    variants: dict[str, list] = {}
    t0 = time.time()
    variants["qr"] = [
        tuple(b.qr_scorecasts(sg * x, H, burn, 1 - ALPHA / 2) for sg in (-1.0, 1.0)) for x in xs
    ]
    timing["qr_scorecasts"] = round(time.time() - t0, 1)
    t0 = time.time()
    variants["theta"] = [
        tuple(
            b.pid_scorecasts(b.theta_forecast_table(sg * x, burn, H), H, burn) for sg in (-1.0, 1.0)
        )
        for x in xs
    ]
    timing["theta_tables"] = round(time.time() - t0, 1)
    variants["matched"] = [b.matched_scorecasts(rh) for rh in rhat]

    for name, scs in variants.items():
        t0 = time.time()
        segs_pid = [
            (x[cal], (sc[0][cal], sc[1][cal]), float(np.max(np.abs(x[cal]))))
            for x, sc in zip(xs, scs, strict=True)
        ]
        tune = b.pid_tune_pooled(
            segs_pid, H, alpha=ALPHA, y_range=y_range, eps=EPS / 2, c_sats=c_sats
        )
        entry: dict = {
            "replay_valid_configs": sum(
                1
                for p in tune["path"]
                if p["u"] <= EPS / 2 + TOL and abs(p["coverage"] - (1 - ALPHA)) <= b.PID_DELTA + TOL
            ),
            "replay_configs": len(tune["path"]),
        }
        for label, scale_to in (("as_ratified", None), ("d_p1_11", 1 - ALPHA)):
            cfg, flag = b.select_pid_config(
                tune["path"], EPS / 2, 1 - ALPHA, b.PID_DELTA, scale_to=scale_to
            )
            runs = run_pid(xs, scs, cfg, y_range, ev)
            entry[label] = {
                "config": cfg,
                "flag": flag,
                "runs": runs,
                "vs_loop": compare(runs, loop),
            }
        draft = first_draft_rule(tune["path"], c_sats[1])
        draft_runs = None if draft is None else run_pid(xs, scs, draft, y_range, ev)
        entry["first_draft_rule"] = {
            "config": draft,
            "runs": draft_runs,
            "vs_loop": None if draft_runs is None else compare(draft_runs, loop),
        }
        out[f"pid_{name}"] = entry
        timing[f"pid_{name}_tune_and_runs"] = round(time.time() - t0, 1)

    # SPCI
    t0 = time.time()
    w = b.spci_window(CAL)
    spci = []
    for k, x in enumerate(xs[: args.spci_runs]):
        o = b.spci_rolling(x, CAL, ALPHA, H, w=w, train_len=CAL, random_state=1103 + k)
        lo, hi = o["lo"][ev], o["hi"][ev]
        spci.append(summary(hi - lo, (lo <= x[ev]) & (x[ev] <= hi), y_range))
    out["spci"] = {"w": w, "runs": spci, "vs_loop": compare(spci, loop)}
    timing["spci"] = round(time.time() - t0, 1)
    timing["spci_per_step"] = round(timing["spci"] / max(1, args.spci_runs * EV), 3)

    packages = {}
    for name in ("numpy", "scipy", "scikit-learn", "statsmodels"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    out["_meta"] = {
        "python": platform.python_version(),
        "packages": packages,
        "sources_sha256": b.source_sha256(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    for key in ("pid_qr", "pid_theta", "pid_matched"):
        for label in ("as_ratified", "d_p1_11"):
            print(key, label, out[key][label]["config"], out[key][label]["vs_loop"])
    print("spci", out["spci"]["vs_loop"])


if __name__ == "__main__":
    main()
