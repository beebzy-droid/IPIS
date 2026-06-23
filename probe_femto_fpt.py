"""Probe: why does the FPT (degradation onset) fire early on some FEMTO bearings?

For each bearing it computes the per-snapshot RMS (physical amplitude, baseline-free)
and the Hotelling-T2 health index fit TWO ways:
  baseline-A : first 20% of snapshots  (the current build_femto_hi_trend default)
  baseline-B : first 30 snapshots      (a small, presumed-clean early window)

If baseline-A fires FPT immediately while baseline-B fires it mid-life, and a large
fraction of baseline-A's "healthy" window already exceeds the ALARM limit, then the
diagnosis is BASELINE CONTAMINATION: the 20% window already contains degradation for
fast bearings, poisoning the T2 reference. The RMS trace (which needs no baseline)
distinguishes this from genuine early degradation: flat-then-rising RMS + early T2
firing => contamination; rising-from-zero RMS => real early degradation.

    set PYTHONPATH=src
    python probe_femto_fpt.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ipis.module2_pdm.data.femto_loader import load_femto_bearing
from ipis.module2_pdm.features.vibration_features import (
    TIME_FEATURE_NAMES,
    time_feature_vector,
)
from ipis.module2_pdm.health.health_index import HealthIndexModel
from ipis.module2_pdm.rul.degradation import ema, first_prediction_time

WARN = 16.92
ALARM = 21.67
BEARINGS = [
    "Learning_set/Bearing1_2",  # FPT 0
    "Learning_set/Bearing2_2",  # FPT 0
    "Learning_set/Bearing3_2",  # FPT 739 (clean control)
]
ROOT = Path("data/raw/femto")


def _t2_trace(feats, n_healthy):
    model = HealthIndexModel.fit(feats[:n_healthy], TIME_FEATURE_NAMES)
    t2 = np.array([model.t2(f) for f in feats])
    return t2, ema(t2, 0.05)


def main() -> int:
    for sub in BEARINGS:
        d = ROOT / sub
        if not d.is_dir():
            print(f"[skip] not found: {d}")
            continue
        b = load_femto_bearing(d)
        n = b.n_snapshots
        feats = np.vstack([time_feature_vector(b.snapshot(i)[0]) for i in range(n)])
        rms = feats[:, 0]  # first time-feature is RMS

        na = max(2, int(0.20 * n))
        nb = min(30, n // 2)
        t2a, sa = _t2_trace(feats, na)
        t2b, sb = _t2_trace(feats, nb)

        fpt_a = first_prediction_time(t2a, WARN, persist=3)
        fpt_b = first_prediction_time(t2b, WARN, persist=3)
        contam_a = float(np.mean(t2a[:na] > ALARM))  # % of "healthy" window already alarming
        contam_b = float(np.mean(t2b[:nb] > ALARM))

        print(f"\n===== {b.name}  (n={n}) =====")
        print(
            f"RMS: snap0={rms[0]:.3f}  med[:30]={np.median(rms[:30]):.3f}  "
            f"med[:20%]={np.median(rms[:na]):.3f}  max={rms.max():.3f}"
        )
        print(f"baseline-A (first {na}=20%):  FPT={fpt_a}  " f"alarm-frac in window={contam_a:.2f}")
        print(f"baseline-B (first {nb}):      FPT={fpt_b}  " f"alarm-frac in window={contam_b:.2f}")
        # coarse early traces
        step = max(1, 200 // 20)
        print(f"{'snap':>6}{'RMS':>9}{'sT2-A':>11}{'sT2-B':>11}")
        for i in range(0, min(200, n), step):
            print(f"{i:>6}{rms[i]:>9.3f}{sa[i]:>11.1f}{sb[i]:>11.1f}")
    print(
        "\nRead: A fires early + high alarm-frac in its window + flat early RMS "
        "=> baseline contamination (fix: clean/adaptive baseline). B firing later "
        "with low alarm-frac confirms a small early window is cleaner."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
