"""Tests for the FEMTO-PRONOSTIA loader (synthetic acc_*.csv snapshots)."""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module2_pdm.data.femto_loader import (
    FEMTO_FS,
    FEMTO_SNAPSHOT_INTERVAL_S,
    load_femto_bearing,
    load_femto_snapshot,
)


def _write_snapshot(path, n=2560, h=0.5, v=-0.3, delimiter=","):
    rows = np.zeros((n, 6))
    rows[:, 0], rows[:, 1], rows[:, 2] = 9, 39, 39  # hour, min, sec
    rows[:, 3] = np.arange(n)  # tick
    rows[:, 4] = h + 0.01 * np.random.RandomState(0).randn(n)  # horizontal
    rows[:, 5] = v + 0.01 * np.random.RandomState(1).randn(n)  # vertical
    np.savetxt(path, rows, delimiter=delimiter, fmt="%.6f")


def _make_bearing(tmp_path, name="Bearing1_1", n_snaps=5):
    d = tmp_path / name
    d.mkdir()
    for k in range(1, n_snaps + 1):
        _write_snapshot(d / f"acc_{k:05d}.csv")
    return d


def test_load_snapshot_channels(tmp_path):
    p = tmp_path / "acc_00001.csv"
    _write_snapshot(p, h=0.7, v=-0.2)
    h, v = load_femto_snapshot(p)
    assert h.shape == (2560,) and v.shape == (2560,)
    assert abs(h.mean() - 0.7) < 0.05
    assert abs(v.mean() + 0.2) < 0.05


def test_bearing_sorted_and_counted(tmp_path):
    d = _make_bearing(tmp_path, "Bearing2_3", n_snaps=7)
    b = load_femto_bearing(d)
    assert b.n_snapshots == 7
    assert b.name == "Bearing2_3"
    # files must be in numeric order
    idxs = [int(p.stem.split("_")[1]) for p in b.snapshot_paths]
    assert idxs == sorted(idxs)


def test_condition_mapping(tmp_path):
    b1 = load_femto_bearing(_make_bearing(tmp_path, "Bearing1_1"))
    assert b1.condition == 1 and b1.rpm == 1800 and b1.load_n == 4000
    assert b1.shaft_hz == pytest.approx(30.0)
    assert b1.fs == FEMTO_FS
    b3 = load_femto_bearing(_make_bearing(tmp_path, "Bearing3_2"))
    assert b3.condition == 3 and b3.rpm == 1500


def test_rul_ground_truth(tmp_path):
    b = load_femto_bearing(_make_bearing(tmp_path, "Bearing1_2", n_snaps=10))
    assert b.elapsed_s(0) == 0.0
    assert b.elapsed_s(3) == 3 * FEMTO_SNAPSHOT_INTERVAL_S
    assert b.time_to_failure_s(9) == 0.0  # last snapshot ~ failure
    assert b.time_to_failure_s(0) == 9 * FEMTO_SNAPSHOT_INTERVAL_S


def test_whitespace_delimiter_fallback(tmp_path):
    d = tmp_path / "Bearing1_4"
    d.mkdir()
    _write_snapshot(d / "acc_00001.csv", delimiter=" ")
    b = load_femto_bearing(d)
    h, v = b.snapshot(0)
    assert h.shape == (2560,)


def test_iter_snapshots(tmp_path):
    b = load_femto_bearing(_make_bearing(tmp_path, "Bearing1_1", n_snaps=4))
    seen = [(i, h.shape, v.shape) for i, h, v in b.iter_snapshots()]
    assert len(seen) == 4
    assert seen[0][1] == (2560,)


def test_empty_dir_raises(tmp_path):
    d = tmp_path / "Bearing1_1"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        load_femto_bearing(d)


def test_bad_name_raises(tmp_path):
    d = tmp_path / "NotABearing"
    d.mkdir()
    (d / "acc_00001.csv").write_text("0,0,0,0,0.1,0.2\n")
    with pytest.raises(ValueError):
        load_femto_bearing(d)
