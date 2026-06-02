"""Phase 1B head-to-head -- JITL vs Shardt bias-update (Debutanizer).

Run locally from the project root (gitignored data; not CI):

    python scripts/jitl_vs_bias_eval.py
    python scripts/jitl_vs_bias_eval.py --bandwidths 0.5,1,2,4 --lams 0.1,0.2,0.5,1

Four mechanisms on the SAME physics-anchored model, SAME blocked-CV folds, SAME
causal delayed-label constraint (theta=4):

  1. static            -- ADR-007 baseline (no adaptation)
  2. bias-update       -- Shardt open-loop EWMA (bias_update.py), O(1)/step
  3. JITL always-on    -- locally-weighted linear, literature standard, O(N*d^2)/query
  4. JITL ADWIN-gated  -- global model until drift fires, JITL after

Reports per-fold and CV mean+/-SE R^2, worst fold, held-out test R^2, and the
compute proxy (number of LWR local fits). bandwidth and lambda are CV-selected
(test untouched). The publishable axis is accuracy *per unit compute*: does the
O(1) bias-update match the O(N) literature standard on calibration-drift data?
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.evaluation.bias_update import (
    apply_bias_update,
    corrected_fold_r2,
)
from ipis.module1_soft_sensor.evaluation.drift import (
    blocked_cv_residuals,
    make_adwin,
    scan,
)
from ipis.module1_soft_sensor.evaluation.jitl import (
    gate_with_drift,
    jitl_fold_predictions,
    lwr_predict,
)
from ipis.module1_soft_sensor.features.physics_features import (
    make_physics_anchored_features,
)

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def _mean_se(scores: list[float]) -> tuple[float, float]:
    a = np.asarray(scores, dtype=float)
    n = len(a)
    return float(a.mean()), (float(a.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0)


def _row(name: str, folds_r2: list[float], test_r2: float, fits: int) -> str:
    m, se = _mean_se(folds_r2)
    worst = min(folds_r2)
    return (
        f"  {name:<20} CV {m:+.3f}+/-{se:.3f}  worst {worst:+.3f}  "
        f"test {test_r2:+.3f}  local_fits {fits:>6}"
    )


def _jitl_block(
    train: pd.DataFrame,
    test: pd.DataFrame,
    builder,
    theta: int,
    bandwidth: float,
    ridge: float = 1e-6,
) -> np.ndarray:
    """Causal always-on JITL predictions for a single train->test split."""
    X_tr, y_tr = builder(train)
    X_te, y_te = builder(test)
    scaler = StandardScaler().fit(X_tr)
    xtr, xte = scaler.transform(X_tr), scaler.transform(X_te)
    ytr = np.asarray(y_tr, dtype=float).ravel()
    yte = np.asarray(y_te, dtype=float).ravel()
    preds = np.empty(len(xte))
    for j in range(len(xte)):
        n_avail = max(0, j - theta + 1)
        db_x = np.vstack([xtr, xte[:n_avail]]) if n_avail else xtr
        db_y = np.concatenate([ytr, yte[:n_avail]]) if n_avail else ytr
        preds[j] = lwr_predict(db_x, db_y, xte[j], bandwidth, ridge)
    return preds


def main() -> int:
    ap = argparse.ArgumentParser(description="JITL vs bias-update head-to-head.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--transport-lag", type=int, default=15)
    ap.add_argument("--label-delay", type=int, default=4)
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--lams", type=str, default="0.1,0.2,0.5,1.0")
    ap.add_argument("--bandwidths", type=str, default="0.5,1.0,2.0,4.0")
    args = ap.parse_args()
    lams = [float(x) for x in args.lams.split(",")]
    bws = [float(x) for x in args.bandwidths.split(",")]

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

    print("=" * 80)
    print("Phase 1B head-to-head -- JITL vs Shardt bias-update (physics-anchored)")
    print("=" * 80)
    print(
        f"  pool={len(pool)} test={len(test)} n_splits={args.n_splits} "
        f"transport_lag={tlag} theta={theta}"
    )
    print("-" * 80)

    # --- static baseline (shared) ---
    static = blocked_cv_residuals(
        pool,
        LinearRegression,
        max_lag=tlag,
        n_splits=args.n_splits,
        feature_builder=builder,
    )
    static_r2 = [f.r2 for f in static]

    # held-out test: pool-fit global model
    X_pool, y_pool = builder(pool)
    X_te, y_te = builder(test)
    scaler = StandardScaler().fit(X_pool)
    gmodel = LinearRegression().fit(scaler.transform(X_pool), y_pool)
    yhat_te = np.asarray(gmodel.predict(scaler.transform(X_te))).ravel()
    y_te = np.asarray(y_te, dtype=float).ravel()
    static_test = r2_score(y_te, yhat_te)
    print(_row("static", static_r2, static_test, 0))

    # --- bias-update (CV-select lambda) ---
    best_lam, best = lams[0], -np.inf
    for lam in lams:
        m, _ = _mean_se(corrected_fold_r2(static, lam=lam, delay=theta))
        if m > best:
            best, best_lam = m, lam
    bias_r2 = corrected_fold_r2(static, lam=best_lam, delay=theta)
    bias_test_pred, _ = apply_bias_update(y_te, yhat_te, lam=best_lam, delay=theta)
    print(_row(f"bias-update (l={best_lam:g})", bias_r2, r2_score(y_te, bias_test_pred), 0))

    # --- JITL always-on (CV-select bandwidth) ---
    best_bw, best, best_folds = bws[0], -np.inf, None
    for bw in bws:
        folds = jitl_fold_predictions(
            pool,
            max_lag=tlag,
            n_splits=args.n_splits,
            label_delay=theta,
            bandwidth=bw,
            feature_builder=builder,
        )
        m, _ = _mean_se([f.r2 for f in folds])
        if m > best:
            best, best_bw, best_folds = m, bw, folds
    jitl_r2 = [f.r2 for f in best_folds]
    jitl_fits = sum(f.local_fits for f in best_folds)
    jitl_test_pred = _jitl_block(pool, test, builder, theta, best_bw)
    print(
        _row(
            f"JITL always (h={best_bw:g})",
            jitl_r2,
            r2_score(y_te, jitl_test_pred),
            jitl_fits,
        )
    )

    # --- JITL ADWIN-gated (reuse best-bandwidth folds) ---
    gated = gate_with_drift(static, best_folds)
    gated_r2 = [g.r2 for g in gated]
    gated_fits = sum(g.local_fits for g in gated)
    # held-out test gating: global until ADWIN fires on its residual, JITL after
    fire = scan(y_te - yhat_te, make_adwin()).first_fire_at_or_after(0)
    switch = len(yhat_te) if fire is None else fire
    gated_test_pred = yhat_te.copy()
    gated_test_pred[switch:] = jitl_test_pred[switch:]
    print(_row("JITL gated", gated_r2, r2_score(y_te, gated_test_pred), gated_fits))

    print("-" * 80)
    print("  Read: bias-update is O(1)/step (local_fits=0); JITL always-on rebuilds")
    print("  a local model every query. If bias-update matches/beats JITL at zero")
    print("  local fits, the targeted fix dominates the literature standard on this")
    print("  calibration-drift problem. Gated JITL shows how much benefit the drift")
    print("  trigger recovers at a fraction of always-on's fits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
