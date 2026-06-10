"""Phase 1B, step 3 -- Shardt open-loop bias-update evaluation (Debutanizer).

Run locally from the project root (benchmark data is gitignored, not in CI):

    python scripts/bias_update_eval.py
    python scripts/bias_update_eval.py --label-delay 20 --lams 0.05,0.1,0.2,0.5,1.0

What it does, all on the ADR-007 physics-anchored model:

  1. Reproduces the static baseline: per-fold held-out R^2 under the same
     blocked CV (this should match ADR-007: +0.145 +/- 0.419, worst -1.49).
  2. Sweeps the EWMA adaptation rate lambda for the causal open-loop bias
     update (Shardt 2016), reporting per-fold and CV mean +/- SE for each.
  3. Reports the ORACLE ceiling (each fold's true residual mean removed) -- the
     causal result must land between static and oracle.
  4. Selects lambda by CV mean (never touches test) and reports the held-out
     test R^2 raw vs corrected at that lambda.

label-delay (theta) is the analyzer/label staleness, distinct from the 15-sample
transport lag in the features. Default theta=4 = the Fortuna et al. (2005/2007)
benchmark gas-chromatograph delay (their NARMA uses 4 output lags); the true
plant delay was "great and unknown", so 4 is the benchmark convention. Re-pin
theta to the real analyzer cycle for any other column. The bias update is the CORRECTION; detection (step 2) is
only the trigger. The cross-regime SE reduction is the Module 1 result.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from ipis.module1_soft_sensor.features.physics_features import (
    make_physics_anchored_features,
)
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.evaluation.bias_update import (
    apply_bias_update,
    corrected_fold_r2,
    oracle_debias_r2,
)
from ipis.module1_soft_sensor.evaluation.drift import blocked_cv_residuals

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def _mean_se(scores: list[float]) -> tuple[float, float]:
    a = np.asarray(scores, dtype=float)
    n = len(a)
    return float(a.mean()), (float(a.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0)


def _fold_str(scores: list[float]) -> str:
    return "[" + " ".join(f"{s:+.3f}" for s in scores) + "]"


def main() -> int:
    ap = argparse.ArgumentParser(description="Shardt open-loop bias-update eval.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--transport-lag", type=int, default=15)
    ap.add_argument(
        "--label-delay",
        type=int,
        default=4,
        help="Analyzer/label delay theta (samples). Default 4 = Fortuna "
        "benchmark gas-chromatograph delay (their NARMA uses 4 output lags).",
    )
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument(
        "--lams",
        type=str,
        default="0.1,0.2,0.5,1.0",
        help="Comma-separated EWMA lambdas to sweep.",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="dump the F4 evidence (held-out trace + fold R2s) to docs/paper/evidence/",
    )
    args = ap.parse_args()
    lams = [float(x) for x in args.lams.split(",")]

    try:
        from ipis.module1_soft_sensor.data.loaders import DebutanizerLoader
    except Exception as exc:  # noqa: BLE001
        print(f"Could not import DebutanizerLoader: {exc}")
        return 1
    try:
        df = DebutanizerLoader().load(args.path)
    except FileNotFoundError as exc:
        print(f"Data file not found: {exc}")
        return 1

    split = time_ordered_split(df)
    pool = pd.concat([split.train, split.val], ignore_index=True)
    test = split.test.reset_index(drop=True)
    tlag, theta = args.transport_lag, args.label_delay

    def builder(seg: pd.DataFrame):
        return make_physics_anchored_features(seg, tlag, include_raw_u5=True)

    folds = blocked_cv_residuals(
        pool,
        LinearRegression,
        max_lag=tlag,
        n_splits=args.n_splits,
        feature_builder=builder,
    )

    print("=" * 76)
    print("Phase 1B step 3 -- Shardt open-loop bias-update (physics-anchored model)")
    print("=" * 76)
    print(
        f"  pool={len(pool)} test={len(test)} n_splits={args.n_splits} "
        f"transport_lag={tlag} label_delay(theta)={theta}"
    )
    print("-" * 76)

    raw = [f.r2 for f in folds]
    m, se = _mean_se(raw)
    print(f"  {'static (ADR-007)':<20} {_fold_str(raw)}  CV {m:+.3f} +/- {se:.3f}")

    best_lam, best_m = None, -np.inf
    fold_corrected: dict[str, list[float]] = {}
    for lam in lams:
        c = corrected_fold_r2(folds, lam=lam, delay=theta)
        fold_corrected[f"{lam:g}"] = [float(v) for v in c]
        m, se = _mean_se(c)
        label = f"EWMA lam={lam:g}"
        print(f"  {label:<20} {_fold_str(c)}  CV {m:+.3f} +/- {se:.3f}")
        if m > best_m:
            best_m, best_lam = m, lam

    orc = oracle_debias_r2(folds)
    m, se = _mean_se(orc)
    print(f"  {'oracle (best const)':<20} {_fold_str(orc)}  CV {m:+.3f} +/- {se:.3f}")
    print("-" * 76)

    # Held-out test at the CV-selected lambda (test touched once, here only).
    X_pool, y_pool = builder(pool)
    X_te, y_te = builder(test)
    scaler = StandardScaler().fit(X_pool)
    model = LinearRegression().fit(scaler.transform(X_pool), y_pool)
    yhat_te = np.asarray(model.predict(scaler.transform(X_te))).ravel()
    y_te = np.asarray(y_te, dtype=float).ravel()
    raw_te = r2_score(y_te, yhat_te)
    corr_te, _ = apply_bias_update(y_te, yhat_te, lam=best_lam, delay=theta)
    corr_r2 = r2_score(y_te, corr_te)
    print(f"  CV-selected lambda = {best_lam:g} (by CV mean, test untouched)")
    print(
        f"  held-out test R^2: raw={raw_te:+.4f} -> corrected={corr_r2:+.4f} "
        f"(delta {corr_r2 - raw_te:+.4f})"
    )
    if args.json:
        from ipis.shared.evidence import dump_evidence

        print(
            "evidence ->",
            dump_evidence(
                "bias_trace_debutanizer",
                {
                    "y": [float(v) for v in y_te],
                    "raw_pred": [float(v) for v in yhat_te],
                    "corrected_pred": [float(v) for v in corr_te],
                    "lam": float(best_lam),
                    "theta": int(theta),
                    "raw_test_r2": float(raw_te),
                    "corrected_test_r2": float(corr_r2),
                    "fold_r2_static": [float(v) for v in raw],
                    "fold_r2_corrected": fold_corrected,
                    "fold_r2_oracle": [float(v) for v in orc],
                },
            ),
        )
    print("-" * 76)
    print("  Read: the static row should reproduce ADR-007. The win is a less")
    print("  negative worst fold and a SMALLER CV SE (cross-regime robustness).")
    print("  Oracle = best CONSTANT per-fold offset; a tracking update can")
    print("  exceed it where the residual drifts within a fold. A fold that")
    print("  stays negative after correction is variance/within-block-drift")
    print("  limited, not offset limited -- not expected to be rescued.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
