#!/usr/bin/env python3
"""TEP fault-detection scorecard for IPIS Phase 2C (cross-domain anomaly detection).

Applies the SAME health index used on bearings in Module 2 -- Hotelling T^2
(Mahalanobis^2) with chi^2 control limits, fit on a healthy baseline -- to the
Tennessee Eastman fault scenarios produced by generate_tep_faults.py. This is a
cross-domain transfer test of the IPIS anomaly detector (chemical process vs
rotating machinery), NOT a claim of TEP-FDD state-of-the-art: plain T^2 is the
classical FDD baseline (Russell/Braatz/Chiang) that fancier methods are measured
against.

Detector input: the 33 continuous + manipulated variables (XMEAS 1-22, XMV 1-11);
the 19 GC-analyzer composition channels (XMEAS 23-41, 6-15 min sampling delay) are
excluded. Baseline fit on the fault-free d00; alarm limit = 99% chi^2 quantile.
Detection uses a 3-sample persistence (debounce) rule.

Metrics (standard FDD scorecard):
  detection delay = (first sustained T^2 > limit at/after sample 160) - 160, in min
  detection rate  = fraction of post-onset samples [160:960] alarmed
  FAR             = per-sample exceedance on a held-out fault-free window

IDV-3 / 9 / 15 are the known near-undetectable faults; ~0% detection there is
expected for any detector and is reported, not hidden.

    set PYTHONPATH=src
    python scripts/run_tep_fdd.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ipis.module2_pdm.health.fdd import false_alarm_rate, score_run
from ipis.module2_pdm.health.health_index import HealthIndexModel

FDD = Path("data/raw/tep/fdd")
ONSET = 160  # fault-injection sample
CADENCE_MIN = 3.0
FIT = slice(50, 500)  # fault-free baseline fit window on d00 (skip startup transient)
FAR_TEST = slice(500, 960)  # held-out fault-free window for FAR (not used in fit)
PERSIST = 3  # consecutive samples over the limit to declare detection
N_IDV = 20
# CSV cols: 0=time, 1..41=XMEAS_1..41, 42..53=XMV_1..12
VAR_COLS = list(range(1, 23)) + list(range(42, 53))  # XMEAS 1-22 + XMV 1-11 = 33
UNDETECTABLE = {3, 9, 15}


def _load(idv: int) -> np.ndarray:
    return np.loadtxt(FDD / f"d{idv:02d}.csv", delimiter=",")[:, VAR_COLS]


def main() -> int:
    if not (FDD / "d00.csv").exists():
        print(f"[ERROR] {FDD}/d00.csv not found. Run generate_tep_faults.py first.")
        return 1

    d00 = _load(0)
    names = [f"v{c}" for c in VAR_COLS]
    model = HealthIndexModel.fit(d00[FIT], names, warn_q=0.95, alarm_q=0.99)
    limit = model.alarm_t2

    far = false_alarm_rate([model.t2(x) for x in d00[FAR_TEST]], limit)

    print(
        f"Baseline: d00 fit {FIT.start}-{FIT.stop} ({FIT.stop - FIT.start} samples), "
        f"{len(VAR_COLS)} vars, alarm T2={limit:.1f} (chi2 99%)"
    )
    print(f"FAR (fault-free held-out): {far * 100:.1f}%\n")
    print(f"{'IDV':<5}{'delay(min)':>11}{'detect%':>9}{'note':>16}")

    results = {}  # f -> (delay or None, detection_rate)
    for f in range(1, N_IDV + 1):
        t2 = [model.t2(v) for v in _load(f)]
        delay, detrate = score_run(t2, limit, ONSET, PERSIST, CADENCE_MIN)
        results[f] = (delay, detrate)
        delay_str = "not detected" if delay is None else f"{delay:.0f}"
        note = "undetectable" if f in UNDETECTABLE else ""
        print(f"{f:<5}{delay_str:>11}{detrate * 100:>8.0f}%{note:>16}")

    detectable = [f for f in range(1, N_IDV + 1) if f not in UNDETECTABLE]
    det_delays = [results[f][0] for f in detectable if results[f][0] is not None]
    det_rates = [results[f][1] for f in detectable]
    und_rates = [results[f][1] for f in sorted(UNDETECTABLE)]
    print(
        f"\nFAR (fault-free, instantaneous): {far * 100:.1f}%  (99% limit; persistence lowers it)"
    )
    print("Detectable faults (17, excl. IDV-3/9/15):")
    print(
        f"  mean detection delay : {np.mean(det_delays):.0f} min  ({len(det_delays)}/17 detected)"
    )
    print(f"  mean detection rate  : {np.mean(det_rates) * 100:.0f}%")
    print(f"Undetectable IDV-3/9/15 detection rate: {np.mean(und_rates) * 100:.0f}% (expected ~0)")
    print(
        "\nCross-domain transfer of the IPIS T2 detector; plain T2 is the classical "
        "TEP-FDD baseline, so this is breadth, not an FDD SOTA claim."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
