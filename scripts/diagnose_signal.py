"""Diagnose where the predictive signal for the C4 target lives in the data.

Pure data analysis -- NO physics assumptions. Run locally from the project
root:

    python scripts/diagnose_signal.py
    python scripts/diagnose_signal.py --path data/raw/debutanizer/debutanizer_data.txt --max-lag 15

Reports, in one pass:
    1. Raw Pearson correlation r (and r^2) of each input u1..u7 with y.
    2. Best lag k in [0, max_lag] for each input: corr(u_i(t-k), y(t)).
       (The analyzer delay is why y was shifted ~8 samples; a relationship
       hidden at lag 0 can appear at the right lag.)
    3. Linear multivariate ceiling: OLS R^2 of y on contemporaneous inputs,
       and on inputs augmented with their lags -- the best a linear static /
       dynamic model could achieve. Calibrates expectations for the module.

This tells us whether to (a) fix the physics variable/lag choice, (b) go
multivariate physics, or (c) reframe physics as a feature with the temporal
ML carrying prediction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")
INPUT_COLS = ["u1", "u2", "u3", "u4", "u5", "u6", "u7"]
Y_COL = "y"


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation coefficient; 0.0 if either series is constant."""
    if np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _ols_r2(X: np.ndarray, y: np.ndarray) -> float:
    """R^2 of an ordinary-least-squares fit of y on X (with intercept)."""
    Xi = np.column_stack([np.ones(len(y)), X])
    beta, _, _, _ = np.linalg.lstsq(Xi, y, rcond=None)
    resid = y - Xi @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else float("nan")


def _best_lag(u: np.ndarray, y: np.ndarray, max_lag: int) -> tuple[int, float]:
    """Best lag k in [0, max_lag] maximizing |corr(u[t-k], y[t])|."""
    best_k, best_r = 0, 0.0
    for k in range(max_lag + 1):
        uu = u[: len(u) - k] if k else u
        yy = y[k:] if k else y
        r = _pearson(uu, yy)
        if abs(r) > abs(best_r):
            best_k, best_r = k, r
    return best_k, best_r


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnose predictive signal for the C4 target.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--max-lag", type=int, default=15)
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

    y = df[Y_COL].to_numpy(dtype=float)

    print("=" * 60)
    print("Signal diagnosis -- contemporaneous correlation with y")
    print("=" * 60)
    print(f"  {'input':6s}{'r':>10s}{'r^2':>10s}")
    for c in INPUT_COLS:
        r = _pearson(df[c].to_numpy(dtype=float), y)
        print(f"  {c:6s}{r:>10.4f}{r * r:>10.4f}")

    print("-" * 60)
    print(f"Best lag k in [0,{args.max_lag}]: corr(u_i(t-k), y(t))")
    print(f"  {'input':6s}{'best_k':>8s}{'r':>10s}{'r^2':>10s}")
    for c in INPUT_COLS:
        k, r = _best_lag(df[c].to_numpy(dtype=float), y, args.max_lag)
        print(f"  {c:6s}{k:>8d}{r:>10.4f}{r * r:>10.4f}")

    print("-" * 60)
    print("Linear multivariate ceiling (OLS R^2):")
    X = df[INPUT_COLS].to_numpy(dtype=float)
    print(f"  contemporaneous inputs           : {_ols_r2(X, y):.4f}")
    # Augment with lags 1..8 of all inputs (dynamic ceiling).
    L = 17
    rows = len(y) - L
    cols = []
    for c in INPUT_COLS:
        u = df[c].to_numpy(dtype=float)
        for k in range(L + 1):
            cols.append(u[L - k : L - k + rows])
    Xdyn = np.column_stack(cols)
    ydyn = y[L:]
    print(f"  inputs + lags 1..{L} (dynamic)      : {_ols_r2(Xdyn, ydyn):.4f}")
    print("-" * 60)
    print("Read: if single-input r^2 are all tiny but the multivariate /")
    print("dynamic ceiling is high, the target is multivariate+dynamic --")
    print("a single-tray static bubble-point cannot capture it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
