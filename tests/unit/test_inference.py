"""Unit tests for the dependent-data inference helpers (Phase 1 analysis plan, Sec. 7)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from ipis.module1_soft_sensor.evaluation.inference import (
    acf,
    block_length,
    circular_block_bootstrap_ci,
    iact,
    n_blocks,
    paired_block_bootstrap_ci,
)


def _ar1(phi: float, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + math.sqrt(1.0 - phi * phi) * e[t]
    return x


def test_acf_of_ar1() -> None:
    r = acf(_ar1(0.8, 100_000, 0), 3)
    assert r[0] == pytest.approx(1.0)
    np.testing.assert_allclose(r[1:], [0.8, 0.64, 0.512], atol=0.02)


def test_iact_white_ar1_and_constant() -> None:
    assert iact(np.random.default_rng(0).standard_normal(20_000)) == pytest.approx(1.0, abs=0.15)
    assert iact(_ar1(0.9, 200_000, 1)) == pytest.approx(19.0, rel=0.15)
    assert iact(np.ones(50)) == 1.0


def test_block_length_rule() -> None:
    assert block_length(np.random.default_rng(0).standard_normal(5_000)) == 25
    assert block_length(_ar1(0.97, 100_000, 2)) >= 2 * 50  # IACT about 66 for phi = 0.97


def test_bootstrap_interval_brackets_the_mean_and_is_reproducible() -> None:
    x = _ar1(0.9, 4_000, 3) + 2.0
    lo, hi = circular_block_bootstrap_ci(x, 50, n_boot=500, seed=7)
    assert lo < x.mean() < hi
    assert (lo, hi) == circular_block_bootstrap_ci(x, 50, n_boot=500, seed=7)


def test_dependent_data_need_long_blocks() -> None:
    x = _ar1(0.95, 4_000, 4)
    lo1, hi1 = circular_block_bootstrap_ci(x, 1, n_boot=800, seed=1)
    lo2, hi2 = circular_block_bootstrap_ci(x, 100, n_boot=800, seed=1)
    assert (hi2 - lo2) > 3.0 * (hi1 - lo1)  # iid resampling understates the uncertainty


def test_paired_interval_of_identical_arms_is_zero() -> None:
    x = _ar1(0.5, 1_000, 5)
    assert paired_block_bootstrap_ci(x, x, 25, n_boot=200) == (0.0, 0.0)
    with pytest.raises(ValueError):
        paired_block_bootstrap_ci(x, x[:-1], 25)


def test_n_blocks_and_block_bounds() -> None:
    assert n_blocks(719, 100) == 7
    with pytest.raises(ValueError):
        circular_block_bootstrap_ci(np.ones(10), 11)
