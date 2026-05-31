"""Phase 1B, step 2 -- residual drift detection on the Debutanizer soft sensor.

Run locally from the project root (the benchmark data is gitignored, so this
does not run in CI):

    python scripts/detect_drift.py
    python scripts/detect_drift.py --path data/raw/debutanizer/debutanizer_data.txt

What it does (two analyses, both on the ADR-007 physics-anchored model):

  A. CROSS-REGIME CV STREAM. Builds the honest out-of-sample residual stream
     under the SAME forward-chaining blocked CV used for selection, then runs
     ADWIN (primary), Page-Hinkley, and CUSUM over it. Reports per-fold
     held-out R^2 and residual-mean (where the static model goes biased/
     negative), and where each detector fires.

  B. STATIC BIAS GROWTH (the headline). Fits the physics-anchored model on
     TRAIN only, then streams its residuals across VAL then TEST in time order.
     A calibration-drifting model's residual MEAN walks away from zero as it
     crosses into the later regime; the detectors flag where. That fire point
     is the TRIGGER for the Phase 1B step-3 Shardt bias-update -- detection
     corrects nothing on its own.

The reference residual sigma (detector scale) is estimated from the model's
in-control residuals; override with --ref-sigma. Detector thresholds are
general-knowledge SPC / streaming defaults scaled to that sigma (only ADWIN's
delta is scale-free); they are not project primary-source constants.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.evaluation.drift import (
    blocked_cv_residuals,
    build_detectors,
    concat_residual_stream,
    scan,
)
from ipis.module1_soft_sensor.features.physics_features import (
    make_physics_anchored_features,
)

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def _forward_residuals(
    builder, make_estimator, train: pd.DataFrame, segments: list[pd.DataFrame]
) -> tuple[np.ndarray, list[int]]:
    """Fit on train; stream residuals across each later segment in order.

    Each segment is built separately (leakage-safe per-segment lagging) and the
    scaler is fit on train only. Returns the concatenated residual stream and
    the cumulative boundary indices (the start of each segment in the stream).
    """
    X_tr, y_tr = builder(train)
    scaler = StandardScaler().fit(X_tr)
    model = make_estimator().fit(scaler.transform(X_tr), y_tr)

    pieces: list[np.ndarray] = []
    boundaries: list[int] = []
    cursor = 0
    for seg in segments:
        X_s, y_s = builder(seg)
        pred = np.asarray(model.predict(scaler.transform(X_s))).ravel()
        res = np.asarray(y_s, dtype=float).ravel() - pred
        boundaries.append(cursor)
        cursor += len(res)
        pieces.append(res)
    return (np.concatenate(pieces) if pieces else np.asarray([])), boundaries


def _fmt_fires(fires: list[int], cap: int = 8) -> str:
    if not fires:
        return "(none)"
    head = ", ".join(str(i) for i in fires[:cap])
    return head + (f", ... (+{len(fires) - cap} more)" if len(fires) > cap else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 1B residual drift detection.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--transport-lag", type=int, default=15)
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument(
        "--ref-sigma",
        type=float,
        default=None,
        help="Reference residual sigma for detector scale (default: estimated "
        "from in-control residuals).",
    )
    ap.add_argument(
        "--monitor-abs",
        action="store_true",
        help="Monitor |residual| (accuracy drift) instead of signed.",
    )
    ap.add_argument(
        "--cooldown",
        type=int,
        default=None,
        help="Refractory period (samples) collapsing a sustained "
        "shift into distinct triggers (default: transport_lag).",
    )
    args = ap.parse_args()

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
    tlag = args.transport_lag
    cooldown = tlag if args.cooldown is None else args.cooldown

    def builder(seg: pd.DataFrame):
        return make_physics_anchored_features(seg, tlag, include_raw_u5=True)

    def make_model() -> LinearRegression:
        return LinearRegression()

    transform = (lambda a: np.abs(a)) if args.monitor_abs else (lambda a: a)
    monitored = "|residual|" if args.monitor_abs else "signed residual"

    print("=" * 74)
    print(f"Phase 1B -- residual drift detection (monitoring {monitored})")
    print("=" * 74)
    print(
        f"  rows: train={len(split.train)} val={len(split.val)} "
        f"test={len(split.test)}  transport_lag={tlag}"
    )

    # ----------------------------------------------------------------- A
    print("-" * 74)
    print("A. Cross-regime CV stream (physics-anchored model, blocked CV)")
    folds = blocked_cv_residuals(
        pool,
        make_model,
        max_lag=tlag,
        n_splits=args.n_splits,
        feature_builder=builder,
    )
    for f in folds:
        r = f.residuals
        print(
            f"    fold {f.fold}: R^2={f.r2:+.3f}  resid mean={r.mean():+.4f}  "
            f"std={r.std():.4f}  n={len(r)}"
        )
    stream_a = transform(concat_residual_stream(folds))
    # Reference sigma: in-control = earliest fold residual std (most calibrated).
    ref_sigma = args.ref_sigma or float(folds[0].residuals.std())
    print(
        f"    reference sigma = {ref_sigma:.4f}"
        + ("" if args.ref_sigma is None else " (user override)")
    )
    print(f"    stream length = {len(stream_a)}")
    for det in build_detectors(ref_sigma):
        s = scan(stream_a, det, cooldown=cooldown)
        print(f"      {det.name:<22} fires at: {_fmt_fires(s.fire_indices)}")

    # ----------------------------------------------------------------- B
    print("-" * 74)
    print("B. Static bias growth: fit on TRAIN, stream residuals val -> test")
    stream_b, bounds = _forward_residuals(builder, make_model, split.train, [split.val, split.test])
    val_start, test_start = bounds[0], bounds[1]
    stream_b_m = transform(stream_b)
    val_res = stream_b[val_start:test_start]
    test_res = stream_b[test_start:]
    print(f"    val  residual mean={val_res.mean():+.4f} std={val_res.std():.4f}")
    print(f"    test residual mean={test_res.mean():+.4f} std={test_res.std():.4f}")
    print(f"    val->test boundary at stream index {test_start}")
    ref_sigma_b = args.ref_sigma or float(val_res.std())
    print(
        f"    reference sigma = {ref_sigma_b:.4f}"
        + ("" if args.ref_sigma is None else " (user override)")
    )
    for det in build_detectors(ref_sigma_b):
        s = scan(stream_b_m, det, cooldown=cooldown)
        lat = s.detection_latency(test_start)
        lat_str = "(no fire after boundary)" if lat is None else f"latency={lat}"
        print(f"      {det.name:<22} fires at: {_fmt_fires(s.fire_indices)}  " f"{lat_str}")

    print("-" * 74)
    print("  Read: in A, the folds where resid mean walks off zero are the")
    print("  calibration-drift folds (ADR-007's negative folds). In B, a fire")
    print("  shortly after the val->test boundary is the TRIGGER for the step-3")
    print("  Shardt bias-update. Detection flags WHEN to recalibrate; it does")
    print("  not itself reduce the cross-regime error -- that is step 3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
