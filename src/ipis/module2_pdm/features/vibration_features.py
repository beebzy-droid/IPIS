"""Vibration feature extraction for bearing diagnostics (Module 2, Phase 2A).

Two feature families:

1. Time-domain scalars (the classic condition-monitoring set, also published by
   the IPIS v2 PdM MQTT topic): RMS, peak, crest/shape/impulse/clearance factors,
   kurtosis, skewness. Kurtosis here is the 4th standardized moment with
   Gaussian == 3 (vibration convention): healthy ~3, impulsive fault > 3.

2. Squared-envelope spectrum (SES) and fault-band energy. Bearing faults produce
   an impulse train that amplitude-modulates a structural resonance; demodulation
   recovers the repetition (fault) frequency. Pipeline (Randall & Antoni 2011):
   optional band-pass around the resonance -> analytic signal via Hilbert ->
   squared envelope -> FFT. Energy concentrated at BPFO/BPFI/BSF/FTF and harmonics
   is the diagnostic signature.

Band selection: a fixed band may be supplied; automatic kurtogram/spectral-kurtosis
band selection is a planned 2A enhancement (tracked in spec.md).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt

from ipis.module2_pdm.physics.bearing_frequencies import DefectFrequencies


@dataclass(frozen=True)
class TimeFeatures:
    """Time-domain scalar features (Gaussian-3 kurtosis convention)."""

    rms: float
    peak: float
    std: float
    crest_factor: float
    shape_factor: float
    impulse_factor: float
    clearance_factor: float
    kurtosis: float
    skewness: float


def time_features(x: np.ndarray) -> TimeFeatures:
    """Compute time-domain scalar features for a 1-D signal."""
    x = np.asarray(x, dtype=float).ravel()
    if x.size == 0:
        raise ValueError("empty signal")
    mean = x.mean()
    xc = x - mean
    std = float(xc.std(ddof=0))
    abs_x = np.abs(x)
    rms = float(np.sqrt(np.mean(x**2)))
    peak = float(abs_x.max())
    mean_abs = float(abs_x.mean())
    mean_sqrt = float(np.mean(np.sqrt(abs_x)))

    # Guards for constant/zero signals.
    crest = peak / rms if rms > 0 else 0.0
    shape = rms / mean_abs if mean_abs > 0 else 0.0
    impulse = peak / mean_abs if mean_abs > 0 else 0.0
    clearance = peak / (mean_sqrt**2) if mean_sqrt > 0 else 0.0
    if std > 0:
        kurt = float(np.mean(xc**4) / std**4)  # Gaussian == 3
        skew = float(np.mean(xc**3) / std**3)
    else:
        kurt, skew = 0.0, 0.0

    return TimeFeatures(
        rms=rms,
        peak=peak,
        std=std,
        crest_factor=crest,
        shape_factor=shape,
        impulse_factor=impulse,
        clearance_factor=clearance,
        kurtosis=kurt,
        skewness=skew,
    )


def _bandpass_sos(low: float, high: float, fs: float, order: int = 4) -> np.ndarray:
    nyq = fs / 2.0
    if not (0 < low < high < nyq):
        raise ValueError(f"band ({low},{high}) must satisfy 0<low<high<Nyquist({nyq})")
    return butter(order, [low / nyq, high / nyq], btype="band", output="sos")


def envelope_spectrum(
    x: np.ndarray,
    fs: float,
    band: tuple[float, float] | None = None,
    squared: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Squared-envelope spectrum of a signal.

    Returns (freqs_hz, amplitude) for the non-negative frequency axis. With
    `band` given, the signal is zero-phase band-pass filtered first (resonance
    demodulation). `squared=True` gives the squared-envelope spectrum (SES, the
    Randall & Antoni recommendation); `False` gives the plain envelope spectrum.
    """
    x = np.asarray(x, dtype=float).ravel()
    if x.size < 16:
        raise ValueError("signal too short for envelope analysis")
    if band is not None:
        x = sosfiltfilt(_bandpass_sos(band[0], band[1], fs), x)

    analytic = hilbert(x)
    env = np.abs(analytic)
    env = env**2 if squared else env
    env = env - env.mean()  # remove DC so the fault line is not buried under f=0

    n = env.size
    spec = np.abs(np.fft.rfft(env)) * (2.0 / n)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    return freqs, spec


def band_energy(
    freqs: np.ndarray,
    amp: np.ndarray,
    f_center: float,
    bw_hz: float,
    n_harmonics: int = 1,
) -> float:
    """Summed spectral amplitude within +/- bw_hz of f_center and its harmonics."""
    if f_center <= 0:
        return 0.0
    total = 0.0
    for h in range(1, n_harmonics + 1):
        fc = f_center * h
        mask = (freqs >= fc - bw_hz) & (freqs <= fc + bw_hz)
        if np.any(mask):
            total += float(amp[mask].sum())
    return total


def fault_band_features(
    x: np.ndarray,
    fs: float,
    defects: DefectFrequencies,
    band: tuple[float, float] | None = None,
    n_harmonics: int = 3,
    bw_hz: float = 5.0,
) -> dict[str, float]:
    """Envelope-spectrum energy at each defect frequency, normalized to total.

    Returns a dict with raw band energies and their fraction of total
    envelope-spectrum energy for BPFO/BPFI/BSF/FTF (energy ratio = the
    diagnostic feature). Higher ratio at a given defect frequency => that fault.
    """
    freqs, amp = envelope_spectrum(x, fs, band=band, squared=True)
    total = float(amp.sum()) or 1.0
    out: dict[str, float] = {}
    for name, fc in (
        ("bpfo", defects.bpfo),
        ("bpfi", defects.bpfi),
        ("bsf", defects.bsf),
        ("ftf", defects.ftf),
    ):
        e = band_energy(freqs, amp, fc, bw_hz=bw_hz, n_harmonics=n_harmonics)
        out[f"{name}_energy"] = e
        out[f"{name}_ratio"] = e / total
    return out


def dominant_frequency(
    freqs: np.ndarray,
    amp: np.ndarray,
    f_lo: float,
    f_hi: float,
) -> float:
    """Frequency of the largest envelope-spectrum peak within [f_lo, f_hi] Hz."""
    mask = (freqs >= f_lo) & (freqs <= f_hi)
    if not np.any(mask):
        return float("nan")
    idx = np.argmax(amp[mask])
    return float(freqs[mask][idx])


# Order of the combined feature vector used by the health index (Option C).
FEATURE_VECTOR_NAMES: tuple[str, ...] = (
    "rms",
    "peak",
    "std",
    "crest_factor",
    "shape_factor",
    "impulse_factor",
    "clearance_factor",
    "kurtosis",
    "skewness",
    "bpfo_ratio",
    "bpfi_ratio",
    "bsf_ratio",
    "ftf_ratio",
)

# Time-domain-only vector (the first 9 of FEATURE_VECTOR_NAMES). Used for the FEMTO
# health index, where verified defect frequencies are unavailable so fault-band
# ratios are omitted.
TIME_FEATURE_NAMES: tuple[str, ...] = FEATURE_VECTOR_NAMES[:9]


def time_feature_vector(x: np.ndarray) -> np.ndarray:
    """Time-domain feature vector ordered as `TIME_FEATURE_NAMES` (FEMTO HI input)."""
    tf = time_features(x)
    return np.array(
        [
            tf.rms,
            tf.peak,
            tf.std,
            tf.crest_factor,
            tf.shape_factor,
            tf.impulse_factor,
            tf.clearance_factor,
            tf.kurtosis,
            tf.skewness,
        ],
        dtype=float,
    )


def feature_vector(
    x: np.ndarray,
    fs: float,
    defects: DefectFrequencies,
    band: tuple[float, float] | None = None,
    n_harmonics: int = 3,
    bw_hz: float = 5.0,
) -> np.ndarray:
    """Combined time-domain + fault-band-ratio feature vector (Option C).

    Returns a 1-D array ordered as `FEATURE_VECTOR_NAMES`. This is the vector the
    health index models with Hotelling T^2; it captures both impulsiveness
    (time-domain) and fault-specific energy (envelope ratios).
    """
    tf = time_features(x)
    fb = fault_band_features(x, fs, defects, band=band, n_harmonics=n_harmonics, bw_hz=bw_hz)
    return np.array(
        [
            tf.rms,
            tf.peak,
            tf.std,
            tf.crest_factor,
            tf.shape_factor,
            tf.impulse_factor,
            tf.clearance_factor,
            tf.kurtosis,
            tf.skewness,
            fb["bpfo_ratio"],
            fb["bpfi_ratio"],
            fb["bsf_ratio"],
            fb["ftf_ratio"],
        ],
        dtype=float,
    )
