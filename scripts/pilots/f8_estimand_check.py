"""Which persistence measure should F8 test? (pre-registration D-P1.13 and A.9, 2026-10-28;
library-based, run from the repository root with PYTHONPATH=src.)

F8 compares the open-loop miss process of compensated and uncompensated scores, paired over the
15 TEP T1 runs at theta = 4, where P3 predicts a gain (mean predicted width ratio at most 0.95).
T1 holds each analyzer reading, with its noise, for 5 rows, which compensation at h = 5 cannot
predict. This script compares three measures of the miss process under that hold: the lag-1 and
the lag-5 (= h) autocorrelation and the IACT. For each it reports how often F8's t test would
fire among the studies the gate admits, though compensation works, and, without the gate, how
often its interval lies wholly below 0 ("confirm"): at phi = 0.5 compensation has nothing to
remove, so that share is the false confirmation rate. The IACT did best in most cells, and F8
tests it (f8_persistence_power.py, F8_MEASURE).

The residuals, seeds, held-noise model and gate are those of f8_persistence_power.py (imported
from it); the step-size tuning is left out, as it does not enter these measures.

Run (about 6 min with 2 workers):
    set PYTHONPATH=src
    python scripts\\pilots\\f8_estimand_check.py --json --workers 2
It prints a table and writes docs/paper/evidence/f8_estimand_check.json.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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

_SPEC = importlib.util.spec_from_file_location(
    "f8_persistence_power", Path(__file__).with_name("f8_persistence_power.py")
)
f8 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(f8)

MEASURES = ("acf1", "acf5", "iact")
GATE = 0.95


def measures(err: np.ndarray) -> dict:
    if np.ptp(err) == 0:
        return {"acf1": 0.0, "acf5": 0.0, "iact": 1.0}
    r = acf(err, 5)
    return {"acf1": float(r[1]), "acf5": float(r[5]), "iact": iact(err)}


def study(args: tuple[float, int, float]) -> dict:
    phi, k, held = args
    cal, ev = slice(0, f8.TEP_CAL), slice(f8.TEP_CAL, None)
    runs = []
    for reg in range(3):
        for r in range(f8.N_RUNS):
            x = f8.residual(phi, 10_000 * (k + 1) + 100 * reg + r, held)
            s = np.abs(x)
            order = select_order(x, f8.THETA, max_order=10, fit=cal)
            fc = fit_direct_forecaster(x, f8.THETA, order=order, fit=cal)
            c = np.abs(x - fc.predict(x))
            c[: fc.warmup] = s[: fc.warmup]
            row = {
                "pred": predicted_width_ratio(acf(x[cal], f8.THETA + order + 1), f8.THETA, order)
            }
            for arm, sc in (("raw", s), ("comp", c)):
                res = d.run_delayed_aci(
                    sc[ev],
                    f8.THETA,
                    init_scores=sc[cal][-f8.WINDOW :],
                    alpha=f8.ALPHA,
                    gamma=0.0,
                    window=f8.WINDOW,
                )
                row[arm] = measures((~res["covered"]).astype(float))
            runs.append(row)
    n = len(runs)
    out: dict = {"pred": float(np.mean([r["pred"] for r in runs]))}
    for m in MEASURES:
        diff = np.array([r["comp"][m] - r["raw"][m] for r in runs])
        hi = diff.mean() + stats.t.ppf(0.975, n - 1) * diff.std(ddof=1) / math.sqrt(n)
        out[m] = {
            "diff": float(diff.mean()),
            "raw": float(np.mean([r["raw"][m] for r in runs])),
            "fires": bool(hi >= 0.0),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="F8 estimand comparison under T1's label hold")
    ap.add_argument("--studies", type=int, default=200)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    cells = [(phi, 0.0) for phi in (0.5, 0.7)]
    cells += [(phi, w) for w in (0.0, 0.2, 0.5) for phi in (0.8, 0.9, 0.95, 0.97)]
    result: dict = {}
    for phi, w in cells:
        jobs = [(phi, k, w) for k in range(args.studies)]
        if args.workers > 1:
            with Pool(args.workers) as pool:
                res = pool.map(study, jobs, chunksize=2)
        else:
            res = [study(j) for j in jobs]
        gate = np.array([o["pred"] <= GATE for o in res])
        row: dict = {"pred_ratio_mean": float(np.mean([o["pred"] for o in res]))}
        row["gate_share"] = float(gate.mean())
        for m in MEASURES:
            fires = np.array([o[m]["fires"] for o in res])
            row[m] = {
                "mean_diff": float(np.mean([o[m]["diff"] for o in res])),
                "mean_raw": float(np.mean([o[m]["raw"] for o in res])),
                "fire_share_if_gated": float(fires[gate].mean()) if gate.any() else None,
                "confirm_share_ungated": float(np.mean(~fires)),
            }
        result[f"phi {phi}, held {w}"] = row
        cells_txt = "; ".join(
            f"{m} {row[m]['mean_diff']:+.3f} on {row[m]['mean_raw']:.3f}, fires "
            + (
                f"{100 * row[m]['fire_share_if_gated']:.0f} %"
                if row[m]["fire_share_if_gated"] is not None
                else "n/a"
            )
            for m in MEASURES
        )
        print(f"phi {phi} held {w}: gate {100 * row['gate_share']:.0f} % | {cells_txt}", flush=True)
    if args.json:
        from ipis.shared.evidence import dump_evidence

        lib = Path("src/ipis/module1_soft_sensor/evaluation")
        files = [
            Path("scripts/pilots/f8_estimand_check.py"),
            Path("scripts/pilots/f8_persistence_power.py"),
        ] + [lib / f for f in ("delayed_aci.py", "delay_compensation.py", "inference.py")]
        payload = {
            "cells": result,
            "settings": {"studies": args.studies, "gate": GATE, "theta": f8.THETA},
            "sources_sha256": {
                f.as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in files
            },
        }
        print("evidence ->", dump_evidence("f8_estimand_check", payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
