"""Infer the analyzer/label delay theta from input->output lag structure.

Method 3 (ADR-008 follow-up). The Phase 1A transport lag (u5->y ~ 15) is the SUM
of two delays: process transport (6th tray -> bottoms) + analyzer (GC) delay on
y. We decompose it using variable physical locations in the Fortuna debutanizer:

    u1 top temp, u2 top pressure, u3 reflux, u4 downstream flow,
    u5 6th-tray temp, u6 & u7 BOTTOM temps; y = C4 in the bottoms.

u6/u7 are co-located with the C4 sampling point, so process transport from a
bottom thermocouple to the sampled liquid is ~0 and the cross-correlation lag
(u6/u7 -> y) is dominated by the ANALYZER delay alone ~ theta. u5 (mid-column)
-> y carries tray->bottoms transport + analyzer delay ~ 15. Hence:

    theta ~ lag(u6/u7 -> y);   tray->bottoms transport ~ lag(u5) - theta.

ASSUMPTION (stated, not hidden): bottom-temperature -> bottoms-C4 process
coupling is fast relative to the sampling interval (same physical location,
thermal/composition response quick). If that coupling is itself slow or weak,
this over-estimates theta and the peak will be broad/low -- in which case theta
is NOT identifiable from this dataset, which is a valid (citable) outcome.

Cross-correlation lag is scale-invariant, so the normalized benchmark data is
fine. This is a diagnostic (not CI; needs the gitignored data).

    python scripts/infer_label_delay.py
    python scripts/infer_label_delay.py --max-lag 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.features.lagged import (
    DEFAULT_INPUT_COLS,
    DEFAULT_TARGET_COL,
)

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")
# Physical role of each input in the Fortuna debutanizer (for the read-out).
_ROLE = {
    "u1": "top temp",
    "u2": "top pressure",
    "u3": "reflux flow",
    "u4": "downstream flow",
    "u5": "6th-tray temp (anchor ~15)",
    "u6": "BOTTOM temp A (-> theta)",
    "u7": "BOTTOM temp B (-> theta)",
}
# Weak-peak guard: |r| below this means the lag estimate is unreliable.
_WEAK_R = 0.20


def xcorr_profile(u: np.ndarray, y: np.ndarray, max_lag: int) -> np.ndarray:
    """Pearson r between u(t-k) and y(t) for k = 0..max_lag (input leads output)."""
    u = np.asarray(u, dtype=float)
    y = np.asarray(y, dtype=float)
    u = (u - u.mean()) / u.std()
    y = (y - y.mean()) / y.std()
    out = np.empty(max_lag + 1)
    for k in range(max_lag + 1):
        a = u if k == 0 else u[:-k]  # u(t-k)
        b = y[k:]  # y(t)
        out[k] = float(np.corrcoef(a, b)[0, 1])
    return out


def peak_lag(profile: np.ndarray) -> tuple[int, float]:
    """Lag of maximum |r| and the signed r there."""
    k = int(np.argmax(np.abs(profile)))
    return k, float(profile[k])


def main() -> int:
    ap = argparse.ArgumentParser(description="Infer analyzer/label delay theta.")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH)
    ap.add_argument("--max-lag", type=int, default=25)
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

    y = df[DEFAULT_TARGET_COL].to_numpy()
    ml = args.max_lag

    print("=" * 72)
    print("Infer analyzer/label delay theta -- input->output cross-correlation")
    print("=" * 72)
    print(f"  n={len(df)} max_lag={ml}")
    print(f"  {'input':<6} {'role':<28} {'peak lag':>8} {'r@peak':>8}")
    print("-" * 72)

    peaks: dict[str, tuple[int, float]] = {}
    for c in DEFAULT_INPUT_COLS:
        prof = xcorr_profile(df[c].to_numpy(), y, ml)
        k, r = peak_lag(prof)
        peaks[c] = (k, r)
        flag = "  (weak)" if abs(r) < _WEAK_R else ""
        print(f"  {c:<6} {_ROLE.get(c, ''):<28} {k:>8} {r:>+8.3f}{flag}")

    print("-" * 72)
    u5_lag = peaks["u5"][0]
    bottoms = [c for c in ("u6", "u7") if abs(peaks[c][1]) >= _WEAK_R]
    if not bottoms:
        print("  Bottom-temp correlations are WEAK -- theta is NOT identifiable")
        print("  from this dataset. Keep theta=4 as the sourced benchmark value;")
        print("  report this as a negative result (data rich, information poor).")
        return 0

    theta_est = float(np.mean([peaks[c][0] for c in bottoms]))
    print(f"  u5 (6th-tray) peak lag        = {u5_lag}  (anchor; expect ~15)")
    print(f"  bottom-temp peak lag (theta)  = {theta_est:g}  from {bottoms}")
    transport = u5_lag - theta_est
    print(f"  implied tray->bottoms transport = {transport:g}  (= u5_lag - theta)")
    print("-" * 72)
    print(f"  Read: theta_est ~ {theta_est:g} vs benchmark convention 4. A value")
    print("  near 4 corroborates the convention FROM the data; a sharp peak is")
    print("  trustworthy, a broad/low one is not. The u5 anchor should land near")
    print("  15 -- if it does not, the cross-correlation lag is not tracking the")
    print("  process lag and theta_est should not be trusted either.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
