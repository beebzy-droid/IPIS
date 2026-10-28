"""Design-stage check of F8, the rule for claim 2' (pre-registration D-P1.13, proposed
2026-10-28; library-based, run from the repository root with PYTHONPATH=src).

Question: in the TEP T1 design, how often does F8 fire, and how often does the step-size
statement of claim 2' hold? The design is that of scripts/phase1_power.py, with its residuals,
seeds and compensation forecaster: 15 runs, 5 per regime, Gaussian AR(1) residuals of lag-1
autocorrelation phi, 800 calibration and 600 evaluation rows per run, theta = 4.
- F8 compares the open-loop miss process of the compensated and the uncompensated scores on each
  run's evaluation rows: the delayed loop at gamma = 0, its window seeded with the last 200
  calibration scores, as in pre-registration Section 8. It fires if the paired difference over the
  15 runs, compensated minus uncompensated, of the integrated autocorrelation time (IACT) of the
  miss indicator has a two-sided 95 % t interval that does not lie wholly below 0. The IACT is
  inference.iact (Sokal's automatic window, c = 5; a constant indicator gives 1). The measure was
  chosen over the lag-1 and lag-5 autocorrelation by f8_estimand_check.py.
- The step-size statement holds if, with both loops tuned by replay to eps / 2 on each regime's
  pooled calibration segments (the F5 tuning), the compensated loop's step size is larger in at
  least two of the three regimes and smaller in none.
F8 applies only where P3 predicts a gain: the mean over the 15 runs of the predicted width ratio
(from each run's calibration autocorrelation, before its evaluation rows) at most R*. The share
of studies that meet each candidate R* is reported with F8's firing share among them.
Also reported, per phi: the mean paired differences of the IACT, the lag-1 autocorrelation and
the mean miss run of the open-loop miss indicator, and of the same measures for the tuned loops'
miss indicators.

The statement of claim 2' is made only where F8 is tested and does not fire and the step-size
condition holds; its share is reported for each R*.

Simplifications, as in scripts/phase1_power.py: y_range is the range of the synthetic residual on
the pooled calibration rows; by default the residuals have no 5-row label hold. With --held-share
w, a share w of each run's residual variance is analyzer noise held for HOLD = 5 rows, as T1's
sample-and-hold analyzer holds it (teprob.f adds noise to XMEAS(40) at each 0.25 h sample):
r = sqrt(1 - w) AR(1) + sqrt(w) e, with e constant over blocks of 5 rows at a random phase. The
noise comes from a second generator, so w = 0 reproduces the runs without it. Compensation at
h = 5 cannot predict the noise of the current block.

The lag-1 autocorrelation is the biased sample estimate of inference.acf; a constant miss
indicator counts as 0.

Run (about 10 min each with 2 workers, the held cases about 12 min; results do not depend on the
number of workers):
    set PYTHONPATH=src
    python scripts\\pilots\\f8_persistence_power.py --json --workers 2
    python scripts\\pilots\\f8_persistence_power.py --json --workers 2 --studies 100
        --phis 0.7 0.8 0.85 0.95 --name f8_persistence_power_sweep
    python scripts\\pilots\\f8_persistence_power.py --json --workers 2 --studies 100
        --phis 0.9 0.95 0.97 --held-share 0.2 --name f8_persistence_power_held20
    python scripts\\pilots\\f8_persistence_power.py --json --workers 2 --studies 100
        --phis 0.9 0.95 0.97 --held-share 0.5 --name f8_persistence_power_held50
"""

from __future__ import annotations

import argparse
import hashlib
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy import stats

from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.evaluation.delay_compensation import (
    fit_direct_forecaster,
    predicted_width_ratio,
    select_order,
)
from ipis.module1_soft_sensor.evaluation.inference import acf, iact

ALPHA, WINDOW, EPS, THETA = 0.10, 200, 0.01, 4
TEP_CAL, TEP_EV, N_RUNS, HOLD = 800, 600, 5, 5
ARMS = ("raw", "comp")
RSTAR = (0.90, 0.95)  # candidate applicability thresholds on P3's predicted width ratio
F8_MEASURE = "iact"  # the open-loop persistence measure F8 tests


def ar1(phi: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """As in scripts/phase1_power.py."""
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    c = math.sqrt(1.0 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + c * e[t]
    return x


def mean_miss_run(err: np.ndarray) -> float:
    """Mean length of the runs of consecutive misses (0.0 if there are none)."""
    e = np.concatenate(([0.0], err, [0.0]))
    starts = np.flatnonzero(np.diff(e) == 1.0)
    ends = np.flatnonzero(np.diff(e) == -1.0)
    return float(np.mean(ends - starts)) if starts.size else 0.0


def persistence(err: np.ndarray) -> dict:
    lag1 = float(acf(err, 1)[1]) if np.ptp(err) > 0 else 0.0
    return {"acf1": lag1, "run": mean_miss_run(err), "iact": iact(err)}


def residual(phi: float, seed: int, held: float) -> np.ndarray:
    """AR(1) residual of one run; with held > 0, plus analyzer noise held for HOLD rows."""
    n = TEP_CAL + TEP_EV
    x = ar1(phi, n, np.random.default_rng(seed))
    if held <= 0.0:
        return x
    rng = np.random.default_rng([seed, 1])  # a second stream: the AR(1) part is unchanged
    phase = int(rng.integers(HOLD))
    e = np.repeat(rng.standard_normal(n // HOLD + 2), HOLD)[phase : phase + n]
    return math.sqrt(1.0 - held) * x + math.sqrt(held) * e


def regime(phi: float, study: int, reg: int, held: float = 0.0) -> tuple[list[dict], dict]:
    cal, ev = slice(0, TEP_CAL), slice(TEP_CAL, None)
    xs = [residual(phi, 10_000 * (study + 1) + 100 * reg + r, held) for r in range(N_RUNS)]
    y_range = float(np.ptp(np.concatenate([x[cal] for x in xs])))
    scores: dict[str, list[np.ndarray]] = {"raw": [np.abs(x) for x in xs], "comp": []}
    preds = []
    for x, s in zip(xs, scores["raw"], strict=True):
        order = select_order(x, THETA, max_order=10, fit=cal)
        fc = fit_direct_forecaster(x, THETA, order=order, fit=cal)
        c = np.abs(x - fc.predict(x))
        c[: fc.warmup] = s[: fc.warmup]  # rows before the first full lag window: no prediction
        scores["comp"].append(c)
        preds.append(predicted_width_ratio(acf(x[cal], THETA + order + 1), THETA, order))
    gam = {}
    for arm in ARMS:
        segs = [(sc[cal][WINDOW:], sc[cal][:WINDOW]) for sc in scores[arm]]
        gam[arm] = float(d.replay_tune_pooled(segs, THETA, y_range=y_range, eps=EPS / 2)["gamma"])
    runs = []
    for k in range(N_RUNS):
        row: dict = {"pred_ratio": preds[k]}
        for arm in ARMS:
            sc = scores[arm][k]
            init = sc[cal][-WINDOW:]
            for name, g in (("open", 0.0), ("tuned", gam[arm])):
                res = d.run_delayed_aci(
                    sc[ev], THETA, init_scores=init, alpha=ALPHA, gamma=g, window=WINDOW
                )
                row[f"{name}_{arm}"] = persistence((~res["covered"]).astype(float))
        runs.append(row)
    return runs, gam


def study(args: tuple[float, int, float]) -> dict:
    phi, k, held = args
    runs, gams = [], []
    for reg in range(3):
        r, g = regime(phi, k, reg, held)
        runs += r
        gams.append(g)
    n = len(runs)
    out: dict = {}
    for name in ("open", "tuned"):
        for m in ("acf1", "run", "iact"):
            diff = np.array([r[f"{name}_comp"][m] - r[f"{name}_raw"][m] for r in runs])
            out[f"{name}_{m}_diff"] = float(diff.mean())
            out[f"{name}_{m}_raw"] = float(np.mean([r[f"{name}_raw"][m] for r in runs]))
            if name == "open" and m == F8_MEASURE:
                se = diff.std(ddof=1) / math.sqrt(n)
                hi = diff.mean() + stats.t.ppf(0.975, n - 1) * se
                out["f8_fires"] = bool(hi >= 0.0)
                out["f8_hi"] = float(hi)
    out["pred_ratio"] = float(np.mean([r["pred_ratio"] for r in runs]))
    larger = sum(g["comp"] > g["raw"] for g in gams)
    smaller = sum(g["comp"] < g["raw"] for g in gams)
    out["step_statement_holds"] = bool(larger >= 2 and smaller == 0)
    out["gamma"] = gams
    return out


def summarize(studies: list[dict]) -> dict:
    keys = [k for k in studies[0] if k.endswith(("_diff", "_raw"))]
    pred = np.array([s["pred_ratio"] for s in studies])
    fires = np.array([s["f8_fires"] for s in studies])
    row = {
        "f8_fire_share": float(fires.mean()),
        "pred_ratio_mean": float(pred.mean()),
        "pred_ratio_range": [float(pred.min()), float(pred.max())],
        "applicable_share": {str(r): float(np.mean(pred <= r)) for r in RSTAR},
        "f8_fire_share_if_applicable": {
            str(r): (float(fires[pred <= r].mean()) if np.any(pred <= r) else None) for r in RSTAR
        },
        "step_statement_share": float(np.mean([s["step_statement_holds"] for s in studies])),
        "both_hold_share": float(
            np.mean([(not s["f8_fires"]) and s["step_statement_holds"] for s in studies])
        ),
        "statement_share_if_rule": {
            str(r): float(
                np.mean(
                    [
                        s["pred_ratio"] <= r and not s["f8_fires"] and s["step_statement_holds"]
                        for s in studies
                    ]
                )
            )
            for r in RSTAR
        },
        "mean": {k: float(np.mean([s[k] for s in studies])) for k in keys},
        "gamma_ratio_mean": float(
            np.mean([g["comp"] / g["raw"] for s in studies for g in s["gamma"]])
        ),
    }
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="F8 design-stage check (synthetic)")
    ap.add_argument("--studies", type=int, default=200, help="TEP replicate studies per phi")
    ap.add_argument("--workers", type=int, default=1, help="processes")
    ap.add_argument("--phis", type=float, nargs="+", default=[0.5, 0.9])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--name", default="f8_persistence_power", help="evidence file name")
    ap.add_argument("--held-share", type=float, default=0.0, help="share of held analyzer noise")
    args = ap.parse_args()
    payload: dict = {"tep_t1": {}}
    for phi in args.phis:
        jobs = [(phi, k, args.held_share) for k in range(args.studies)]
        if args.workers > 1:
            with Pool(args.workers) as pool:
                studies = pool.map(study, jobs, chunksize=1)
        else:
            studies = [study(j) for j in jobs]
        payload["tep_t1"][str(phi)] = summarize(studies)
        print(f"phi={phi}: {payload['tep_t1'][str(phi)]}", flush=True)
    if args.json:
        from ipis.shared.evidence import dump_evidence

        payload["settings"] = {
            "studies": args.studies,
            "theta": THETA,
            "alpha": ALPHA,
            "window": WINDOW,
            "tuning_target": EPS / 2,
            "runs": 3 * N_RUNS,
            "rows": [TEP_CAL, TEP_EV],
            "held_share": args.held_share,
            "hold_rows": HOLD,
        }
        lib = Path("src/ipis/module1_soft_sensor/evaluation")
        files = [Path("scripts/pilots/f8_persistence_power.py")] + [
            lib / f for f in ("delayed_aci.py", "delay_compensation.py", "inference.py")
        ]
        payload["sources_sha256"] = {
            f.as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in files
        }
        print("evidence ->", dump_evidence(args.name, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
