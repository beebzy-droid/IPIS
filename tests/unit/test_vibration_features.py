"""Tests for vibration feature extraction.

Headline test: `test_envelope_recovers_injected_fault_frequency` builds a
synthetic bearing-fault signal (impulse train modulating a resonance) and asserts
the squared-envelope spectrum peaks at the injected fault frequency. This
validates the demodulation pipeline mathematically, independent of real data.
"""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module2_pdm.features.vibration_features import (
    dominant_frequency,
    envelope_spectrum,
    fault_band_features,
    time_features,
)
from ipis.module2_pdm.physics.bearing_frequencies import DefectFrequencies


def _simulate_bearing_fault(
    fs=12000, dur=1.0, f_fault=120.0, f_res=3000.0, decay=800.0, noise=0.05, seed=0
):
    """Impulse train at f_fault; each impulse excites a decaying sinusoid at f_res."""
    rng = np.random.RandomState(seed)
    n = int(fs * dur)
    t = np.arange(n) / fs
    x = np.zeros(n)
    period = 1.0 / f_fault
    for k in range(1, int(dur * f_fault)):
        t0 = k * period
        i0 = int(t0 * fs)
        if i0 >= n:
            break
        tt = t[i0:] - t0
        x[i0:] += np.exp(-decay * tt) * np.sin(2 * np.pi * f_res * tt)
    x += noise * rng.randn(n)
    return x


def test_envelope_recovers_injected_fault_frequency():
    fs = 12000
    f_fault = 118.0
    x = _simulate_bearing_fault(fs=fs, dur=1.0, f_fault=f_fault, f_res=3200.0)
    freqs, amp = envelope_spectrum(x, fs, band=(2000, 4500), squared=True)
    peak = dominant_frequency(freqs, amp, f_lo=20.0, f_hi=400.0)
    assert abs(peak - f_fault) < 2.0, f"recovered {peak:.1f} Hz, expected {f_fault}"


def test_envelope_works_without_bandpass():
    fs = 12000
    f_fault = 95.0
    x = _simulate_bearing_fault(fs=fs, f_fault=f_fault, noise=0.02)
    freqs, amp = envelope_spectrum(x, fs, band=None, squared=True)
    peak = dominant_frequency(freqs, amp, f_lo=20.0, f_hi=400.0)
    assert abs(peak - f_fault) < 3.0


def test_fault_band_features_flag_correct_defect():
    """Energy ratio is highest at the defect matching the injected frequency."""
    fs = 12000
    bpfi = 162.0  # inject at BPFI
    x = _simulate_bearing_fault(fs=fs, f_fault=bpfi, f_res=3000.0)
    defects = DefectFrequencies(bpfo=107.0, bpfi=bpfi, ftf=12.0, bsf=70.0)
    feats = fault_band_features(x, fs, defects, band=(2000, 4500), n_harmonics=2, bw_hz=4.0)
    ratios = {k: v for k, v in feats.items() if k.endswith("_ratio")}
    assert max(ratios, key=ratios.get) == "bpfi_ratio"
    assert feats["bpfi_ratio"] > feats["bpfo_ratio"]


def test_time_features_sine_reference():
    """Unit sine: RMS=1/sqrt2, crest=sqrt2, kurtosis~1.5 (Gaussian-3 convention)."""
    fs = 10000
    t = np.arange(fs) / fs
    x = np.sin(2 * np.pi * 50 * t)
    f = time_features(x)
    assert f.rms == pytest.approx(1 / np.sqrt(2), rel=1e-2)
    assert f.crest_factor == pytest.approx(np.sqrt(2), rel=1e-2)
    assert f.kurtosis == pytest.approx(1.5, rel=0.05)  # sine kurtosis = 1.5


def test_kurtosis_gaussian_vs_impulsive():
    """Gaussian noise ~3; an impulsive fault signal is markedly higher."""
    rng = np.random.RandomState(1)
    gauss = rng.randn(20000)
    fault = _simulate_bearing_fault(dur=2.0, f_fault=100.0, noise=0.01)
    kg = time_features(gauss).kurtosis
    kf = time_features(fault).kurtosis
    assert 2.7 < kg < 3.3
    assert kf > kg


def test_empty_signal_raises():
    with pytest.raises(ValueError):
        time_features(np.array([]))


def test_band_validation():
    x = np.random.RandomState(0).randn(4096)
    with pytest.raises(ValueError):
        envelope_spectrum(x, fs=12000, band=(5000, 7000))  # high > Nyquist(6000)
