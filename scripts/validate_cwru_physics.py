"""Phase 2A real-data validation: do CWRU envelope peaks land on the
physics-predicted bearing fault frequencies?

Run from repo root after placing CWRU data in data/raw/cwru/:

    set PYTHONPATH=src
    python scripts/validate_cwru_physics.py                  # default 105.mat (inner race)
    python scripts/validate_cwru_physics.py 130.mat 0.007    # outer race
    python scripts/validate_cwru_physics.py 222.mat          # ball fault

For an inner-race file (105/106/107/108) the dominant squared-envelope peak should
sit on BPFI; outer-race on BPFO; ball on BSF. This is the first end-to-end check
that the physics layer (Smith & Randall Table 2 multipliers) matches reality.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ipis.module2_pdm.data.cwru_loader import load_cwru_mat
from ipis.module2_pdm.features.vibration_features import (
    dominant_frequency,
    envelope_spectrum,
    fault_band_features,
    time_features,
)
from ipis.module2_pdm.physics.bearing_frequencies import CWRU_DE_6205

DEFAULT_FILE = "105.mat"
RESONANCE_BAND = (2000.0, 5000.0)  # CWRU DE structural resonance (12k set, Nyquist 6 kHz)


def main(argv: list[str]) -> int:
    fname = argv[0] if argv else DEFAULT_FILE
    path = Path("data/raw/cwru") / fname
    if not path.exists():
        print(f"[ERROR] not found: {path}  (place CWRU files in data/raw/cwru/)")
        return 1

    rec = load_cwru_mat(path)  # fs defaults to 12 kHz (12k DE fault set)
    if rec.de is None or rec.shaft_hz is None:
        print(f"[ERROR] {fname} missing DE channel or RPM")
        return 1

    print(f"File          : {fname}")
    print(f"Shaft speed   : {rec.rpm:.0f} rpm  ({rec.shaft_hz:.2f} Hz)")
    print(f"Samples / fs  : {rec.de.size} @ {rec.fs:.0f} Hz  ({rec.de.size / rec.fs:.2f} s)")

    tf = time_features(rec.de)
    print(f"DE kurtosis   : {tf.kurtosis:.2f}  (healthy ~3; >3 = impulsive fault)")
    print(f"DE crest      : {tf.crest_factor:.2f}    RMS: {tf.rms:.4f}")

    defects = CWRU_DE_6205.published.at_shaft_hz(rec.shaft_hz)
    print("\nPhysics-predicted fault frequencies (Hz):")
    print(
        f"  BPFO={defects.bpfo:6.1f}  BPFI={defects.bpfi:6.1f}  "
        f"BSF={defects.bsf:6.1f}  FTF={defects.ftf:6.1f}"
    )

    freqs, amp = envelope_spectrum(rec.de, rec.fs, band=RESONANCE_BAND, squared=True)
    peak = dominant_frequency(freqs, amp, f_lo=20.0, f_hi=400.0)
    print(f"\nDominant squared-envelope peak in 20-400 Hz: {peak:.1f} Hz")

    # Which predicted defect is the peak closest to?
    cands = {"BPFO": defects.bpfo, "BPFI": defects.bpfi, "BSF": defects.bsf, "FTF": defects.ftf}
    nearest = min(cands, key=lambda k: abs(cands[k] - peak))
    err = abs(cands[nearest] - peak)
    pct = 100.0 * err / cands[nearest] if cands[nearest] else float("inf")
    print(f"Closest defect: {nearest} ({cands[nearest]:.1f} Hz)  |  miss {err:.1f} Hz ({pct:.1f}%)")

    feats = fault_band_features(
        rec.de, rec.fs, defects, band=RESONANCE_BAND, n_harmonics=3, bw_hz=5.0
    )
    print("\nFault-band energy ratios (higher = stronger signature):")
    for d in ("bpfo", "bpfi", "bsf", "ftf"):
        print(f"  {d.upper():4s}: {feats[f'{d}_ratio']:.4f}")
    strongest = max(("bpfo", "bpfi", "bsf", "ftf"), key=lambda d: feats[f"{d}_ratio"])
    print(f"Strongest signature: {strongest.upper()}")

    verdict = "MATCH" if (pct < 2.0) else "CHECK (peak off predicted defect — try a different band)"
    print(f"\nVerdict: dominant peak is within {pct:.1f}% of {nearest}  ->  {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
