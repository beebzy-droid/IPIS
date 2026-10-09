"""Unit tests for ``scripts/phase1_precheck.py`` (N1 Phase 1 pre-checks).

Synthetic inputs with planted structure: a GC value held between 15-min updates and recorded
every 6 or 12 min, an interpolated (not held) label, and AR(1) sequences of known persistence.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase1_precheck.py"
_spec = importlib.util.spec_from_file_location("phase1_precheck", _SCRIPT)
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


def _ar1(phi: float, n: int, rng: np.random.Generator) -> np.ndarray:
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + math.sqrt(1.0 - phi * phi) * e[t]
    return x


def _held(values: np.ndarray, ts_min: float, cycle_min: float) -> np.ndarray:
    """Record a value held between analyzer updates every cycle_min, sampled every ts_min."""
    idx = np.floor(np.arange(values.size) * ts_min / cycle_min).astype(int)
    first = np.r_[0, np.flatnonzero(np.diff(idx)) + 1]
    out = np.empty_like(values)
    for a, b in zip(first, [*first[1:], values.size], strict=True):
        out[a:b] = values[a]
    return out


def _debutanizer_file(tmp_path: Path, ts_min: float | None, seed: int = 7) -> Path:
    """2394-row file in the loader's format; u5 drives y at lag 15; label held unless ts_min is None."""
    rng = np.random.default_rng(seed)
    n, lag = 2394, 15
    u = np.column_stack([_ar1(0.98, n, rng) for _ in range(7)])
    y = np.zeros(n)
    y[lag:] = -0.7 * u[:-lag, 4] + 0.5 * _ar1(0.95, n, rng)[lag:]
    if ts_min is not None:
        y = _held(y, ts_min, 15.0)
    data = np.column_stack([u, y])
    data = (data - data.min(axis=0)) / (data.max(axis=0) - data.min(axis=0))
    path = tmp_path / "debutanizer.txt"
    with path.open("w") as f:
        f.write("u1 u2 u3 u4 u5 u6 u7 y\n\n")
        for row in data:
            f.write("  ".join(f"{v:.7e}" for v in row) + "\n")
    return path


def test_repeat_profile_counts_held_runs() -> None:
    x = np.repeat(np.arange(100, dtype=float), [2, 3] * 50)
    p = pc.repeat_profile(x)
    assert p["mean_run"] == pytest.approx(2.5)
    assert p["repeat_share"] == pytest.approx(150 / 249)
    assert p["run_hist"]["2"] == 50 and p["run_hist"]["3"] == 50


@pytest.mark.parametrize(("share", "expected"), [(0.6, 6.0), (0.2, 12.0)])
def test_implied_ts_for_held_label(share: float, expected: float) -> None:
    label, reference = {"repeat_share": share}, {"repeat_share": 0.0}
    assert pc.implied_ts(label, reference, 15.0) == pytest.approx(expected)


def test_implied_ts_none_when_not_held_or_reference_repeats() -> None:
    assert pc.implied_ts({"repeat_share": 0.02}, {"repeat_share": 0.0}, 15.0) is None
    assert pc.implied_ts({"repeat_share": 0.6}, {"repeat_share": 0.3}, 15.0) is None


def test_mean_run_of_counts_only_the_value() -> None:
    x = np.array([0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0], dtype=float)
    assert pc.mean_run_of(x, 1.0) == pytest.approx(3.0)
    assert pc.mean_run_of(np.zeros(5), 1.0) == 0.0


def test_iact_white_and_ar1() -> None:
    assert pc.iact(np.random.default_rng(0).standard_normal(20_000)) == pytest.approx(1.0, abs=0.15)
    # AR(1): IACT = (1 + phi) / (1 - phi) = 19 for phi = 0.9; estimator sd is about 0.8 at n = 2e5
    ar = _ar1(0.9, 200_000, np.random.default_rng(1))
    assert pc.iact(ar) == pytest.approx(19.0, rel=0.15)


@pytest.mark.parametrize(("ts_min", "lo", "hi"), [(6.0, 5.5, 6.5), (12.0, 11.5, 12.5)])
def test_debutanizer_recovers_planted_cadence(tmp_path: Path, ts_min, lo, hi) -> None:
    out = pc.debutanizer(_debutanizer_file(tmp_path, ts_min), 15.0, lag=15)
    assert out["held_label"] is True
    assert lo <= out["ts_implied_min"] <= hi
    assert (out["n_train"], out["n_val_unread"], out["n_test_unread"]) == (1675, 359, 360)
    assert set(out["open_loop_miss"]) == {"0", "3", "7"}
    assert 0.05 <= out["open_loop_miss"]["0"]["miss_rate"] <= 0.15


def test_debutanizer_not_held_implies_nothing(tmp_path: Path) -> None:
    out = pc.debutanizer(_debutanizer_file(tmp_path, None), 15.0, lag=15)
    assert out["held_label"] is False
    assert out["ts_implied_min"] is None
    assert out["residual_acf"]["1"] > 0.8  # planted AR(1) noise with phi = 0.95
