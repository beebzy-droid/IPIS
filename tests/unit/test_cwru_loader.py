"""Tests for the CWRU `.mat` loader.

Uses a synthetic `.mat` written with the real CWRU variable schema. This checks
loader correctness (key matching, prefix-mismatch handling, missing channels) —
not science; the real CWRU files validate the physics separately.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.io import savemat

from ipis.module2_pdm.data.cwru_loader import FS_12K_DE, load_cwru_mat


def _write_mat(path, prefix="105", channels=("DE", "FE", "BA"), rpm=1797, n=2048):
    d = {}
    for ch in channels:
        d[f"X{prefix}_{ch}_time"] = np.random.RandomState(0).randn(n, 1)
    if rpm is not None:
        d[f"X{prefix}RPM"] = np.array([[rpm]])
    savemat(str(path), d)


def test_loads_all_channels_and_rpm(tmp_path):
    p = tmp_path / "105.mat"
    _write_mat(p, prefix="105", rpm=1797, n=4096)
    rec = load_cwru_mat(p)
    assert rec.de is not None and rec.de.shape == (4096,)
    assert rec.fe is not None and rec.ba is not None
    assert rec.rpm == pytest.approx(1797.0)
    assert rec.fs == FS_12K_DE
    assert rec.shaft_hz == pytest.approx(1797.0 / 60.0)
    assert rec.source_file == "105.mat"


def test_prefix_need_not_match_filename(tmp_path):
    """CWRU quirk: variable prefix can differ from filename; match by suffix."""
    p = tmp_path / "105.mat"
    _write_mat(p, prefix="999", rpm=1750)  # prefix 999 in a file named 105
    rec = load_cwru_mat(p)
    assert rec.de is not None
    assert rec.rpm == pytest.approx(1750.0)


def test_missing_base_channel_is_none(tmp_path):
    p = tmp_path / "097.mat"
    _write_mat(p, prefix="097", channels=("DE", "FE"), rpm=1797)
    rec = load_cwru_mat(p)
    assert rec.ba is None
    assert rec.de is not None and rec.fe is not None


def test_channel_accessor_raises_on_absent(tmp_path):
    p = tmp_path / "097.mat"
    _write_mat(p, prefix="097", channels=("DE",), rpm=1797)
    rec = load_cwru_mat(p)
    assert rec.channel("de") is rec.de
    with pytest.raises(KeyError):
        rec.channel("ba")
    with pytest.raises(ValueError):
        rec.channel("xx")


def test_fs_override(tmp_path):
    p = tmp_path / "x.mat"
    _write_mat(p, prefix="100", rpm=1730)
    rec = load_cwru_mat(p, fs=48_000)
    assert rec.fs == 48_000


def test_missing_rpm_is_none(tmp_path):
    p = tmp_path / "norpm.mat"
    _write_mat(p, prefix="105", rpm=None)
    rec = load_cwru_mat(p)
    assert rec.rpm is None
    assert rec.shaft_hz is None
