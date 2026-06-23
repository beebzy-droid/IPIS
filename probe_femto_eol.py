"""Probe: end-of-life amplitude across FEMTO bearings (validates the 20 g threshold).

Option A (amplitude-extrapolation RUL) assumes peak |accel| converges to ~20 g at
failure across bearings -- a fixed, bearing-independent threshold. This prints,
per bearing: peak |accel| over the last 5 snapshots, peak over the whole run, and
RMS at the last snapshot, for both channels. If EOL peak clusters near ~20 g the
threshold is solid; bearings well short of it are flagged hard cases.

    set PYTHONPATH=src
    python probe_femto_eol.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ipis.module2_pdm.data.femto_loader import load_femto_bearing

BEARINGS = [
    "Learning_set/Bearing1_1",
    "Learning_set/Bearing1_2",
    "Learning_set/Bearing2_1",
    "Learning_set/Bearing2_2",
    "Learning_set/Bearing3_1",
    "Full_Test_Set/Bearing1_3",
]
ROOT = Path("data/raw/femto")
TAIL = 5  # snapshots at end to summarise


def main() -> int:
    print(f"{'bearing':<14}{'n':>6}{'EOL peak':>10}{'life peak':>11}{'EOL rms':>9}")
    for sub in BEARINGS:
        d = ROOT / sub
        if not d.is_dir():
            print(f"{sub.split('/')[-1]:<14}  (not found: {d})")
            continue
        b = load_femto_bearing(d)
        n = b.n_snapshots

        eol_peak = 0.0
        eol_rms = 0.0
        for i in range(max(0, n - TAIL), n):
            h, v = b.snapshot(i)
            both = np.concatenate([h, v])
            eol_peak = max(eol_peak, float(np.max(np.abs(both))))
        h_last, v_last = b.snapshot(n - 1)
        eol_rms = float(np.sqrt(np.mean(np.concatenate([h_last, v_last]) ** 2)))

        life_peak = 0.0
        for i in range(n):
            h, v = b.snapshot(i)
            life_peak = max(life_peak, float(np.max(np.abs(np.concatenate([h, v])))))

        print(f"{b.name:<14}{n:>6}{eol_peak:>10.1f}{life_peak:>11.1f}{eol_rms:>9.2f}")
    print(
        "\n(FEMTO stop criterion ~ 20 g peak amplitude; clustering near 20 g => "
        "fixed threshold for amplitude-extrapolation RUL.)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
