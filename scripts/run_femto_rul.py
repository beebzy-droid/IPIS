"""Leave-one-bearing-out RUL evaluation on FEMTO degradation HI trends (Phase 2B).

Consumes the femto_hi_*.csv files produced by build_femto_hi_trend.py (columns:
index, elapsed_s, rul_s, t2, health_score, flag). For each bearing it builds the
Option-E degradation index DI = cummax(EMA(t2)), finds the degradation onset (FPT),
and keeps the post-FPT (DI, RUL) pairs. Then, leave-one-bearing-out:

  - fit the RUL regressor on the other bearings' post-FPT pairs,
  - calibrate the one-sided lower conformal bound on a held-out training bearing
    (falls back to training residuals if < 3 bearings),
  - predict RUL on the test bearing, score with PHM-2012 and record lower-bound
    coverage.

PHM-2012 is reported twice: over the full post-FPT trajectory, and over the
prognostic horizon (RUL >= 10% of the bearing's post-FPT max) -- the score is
brutal as RUL -> 0 (a 1-snapshot error is a huge % error), so the horizon figure
is the fair comparison to the challenge's truncation-point protocol.

Run from repo root after building several trends:

    set PYTHONPATH=src
    python scripts/build_femto_hi_trend.py Learning_set/Bearing1_1
    python scripts/build_femto_hi_trend.py Learning_set/Bearing1_2
    python scripts/build_femto_hi_trend.py Full_Test_Set/Bearing1_3
    ... (more bearings -> better calibration)
    python scripts/run_femto_rul.py
"""

from __future__ import annotations

import csv
import glob
from pathlib import Path

import numpy as np

from ipis.module2_pdm.rul.degradation import degradation_index, first_prediction_time
from ipis.module2_pdm.rul.rul_model import (
    RULModel,
    lower_bound_coverage,
    phm2012_score,
)

WARN_LIMIT_DF9 = 16.92  # chi2.ppf(0.95, df=9): WARN control limit for the 9-feature HI


def _load_trend(path: Path) -> tuple[str, np.ndarray, np.ndarray]:
    t2, rul = [], []
    with path.open() as f:
        for row in csv.DictReader(f):
            t2.append(float(row["t2"]))
            rul.append(float(row["rul_s"]))
    name = path.stem.replace("femto_hi_", "")
    return name, np.asarray(t2), np.asarray(rul)


def _post_fpt(t2: np.ndarray, rul: np.ndarray):
    di = degradation_index(t2, alpha=0.05)
    fpt = first_prediction_time(t2, warn_limit=WARN_LIMIT_DF9, persist=3)
    fpt = 0 if fpt is None else fpt
    return di[fpt:], rul[fpt:], fpt


def main() -> int:
    files = sorted(glob.glob("data/processed/femto_hi_*.csv"))
    if len(files) < 2:
        print(
            f"[ERROR] need >= 2 femto_hi_*.csv in data/processed/ (found {len(files)}). "
            f"Run build_femto_hi_trend.py on several bearings first."
        )
        return 1

    bearings = []
    print(f"{'bearing':<16}{'snaps':>7}{'FPT':>7}{'post-FPT':>10}{'EOL min':>9}")
    for fp in files:
        name, t2, rul = _load_trend(Path(fp))
        di, rul_pf, fpt = _post_fpt(t2, rul)
        bearings.append((name, di, rul_pf))
        print(f"{name:<16}{len(t2):>7}{fpt:>7}{len(rul_pf):>10}{rul.max() / 60:>9.1f}")
    print()

    if len(bearings) < 3:
        print(
            "[WARN] < 3 bearings: lower bound calibrated on training residuals "
            "(optimistic). Add bearings for an honest held-out calibration.\n"
        )

    all_true, all_lower = [], []
    print(f"{'held-out':<16}{'PHM(full)':>11}{'PHM(horizon)':>14}{'cover':>8}{'n':>6}")
    phm_h_list = []
    for i, (name, di_test, rul_test) in enumerate(bearings):
        others = [b for j, b in enumerate(bearings) if j != i]
        if len(others) >= 2:
            di_cal, rul_cal = others[0][1], others[0][2]
            di_fit = np.concatenate([b[1] for b in others[1:]])
            rul_fit = np.concatenate([b[2] for b in others[1:]])
        else:  # only one training bearing -> no separate calibration split
            di_cal = rul_cal = None
            di_fit, rul_fit = others[0][1], others[0][2]

        model = RULModel.fit(di_fit, rul_fit, alpha=0.1, di_calib=di_cal, rul_calib=rul_cal)
        pred = model.predict(di_test)
        lower = model.lower_bound(di_test)

        horizon = rul_test >= 0.1 * rul_test.max()
        phm_full = phm2012_score(pred[rul_test > 0], rul_test[rul_test > 0])
        phm_h = phm2012_score(pred[horizon], rul_test[horizon])
        cov = lower_bound_coverage(rul_test, lower)
        phm_h_list.append(phm_h)
        all_true.append(rul_test)
        all_lower.append(lower)
        print(f"{name:<16}{phm_full:>11.3f}{phm_h:>14.3f}{cov:>8.2f}{len(rul_test):>6}")

    pooled_cov = lower_bound_coverage(np.concatenate(all_true), np.concatenate(all_lower))
    print()
    print(f"Mean PHM-2012 (horizon)     : {np.mean(phm_h_list):.3f}  (1.0 = perfect)")
    print(f"Pooled lower-bound coverage : {pooled_cov:.3f}  (target >= 0.90)")
    print(
        "Note: leave-one-bearing-out breaks exchangeability, so per-bearing "
        "coverage varies; the pooled figure is the fair marginal estimate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
