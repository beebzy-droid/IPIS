"""Unit and regression tests for the N1 delayed-ACI library (M1 revision)."""

import math
from itertools import pairwise

import numpy as np
import pytest

from ipis.module1_soft_sensor.evaluation.delayed_aci import (
    design_gamma,
    diagnostics,
    gamma_crit,
    infinite_fraction_pred,
    noise_gain_sd,
    run_delayed_aci,
)


def _stream(n, seed=0, shift=None, scale=3.0):
    rng = np.random.default_rng(seed)
    sc = np.ones(n)
    if shift is not None:
        sc[shift:] = scale
    return np.abs(rng.normal(0, 1, n)) * sc, np.abs(rng.normal(0, 1, 200))


def test_gamma_crit_known_values_and_monotone():
    assert gamma_crit(0) == pytest.approx(2.0)
    assert gamma_crit(1) == pytest.approx(1.0)
    assert all(gamma_crit(k + 1) < gamma_crit(k) for k in range(60))


def test_noise_gain_matches_closed_form_without_delay():
    a, g = 0.1, 0.05
    assert noise_gain_sd(g, 0, a) == pytest.approx(math.sqrt(g * a * (1 - a) / (2 - g)), rel=1e-3)


def test_noise_gain_matches_impulse_response_with_delay():
    a, g, th, n = 0.1, 0.05, 5, 20000
    e, imp = np.zeros(n), np.zeros(n)
    imp[0] = 1.0
    for t in range(n - 1):
        e[t + 1] = e[t] - g * ((e[t - th] + imp[t - th]) if t >= th else 0.0)
    assert noise_gain_sd(g, th, a) == pytest.approx(math.sqrt(a * (1 - a) * np.sum(e**2)), rel=1e-3)


def test_noise_gain_is_infinite_beyond_the_limit():
    assert math.isinf(noise_gain_sd(1.01 * gamma_crit(10), 10))


def test_design_rule_is_monotone_capped_and_compliant():
    thetas = (4, 20, 60, 120)
    gs = [design_gamma(th) for th in thetas]
    assert all(np.isfinite(gs))
    assert all(b <= a for a, b in pairwise(gs))
    assert all(g <= 0.8 * gamma_crit(th) + 1e-12 for g, th in zip(gs, thetas, strict=True))
    assert infinite_fraction_pred(gs[2], 60) <= 0.01


def test_without_delay_all_loops_coincide():
    s, init = _stream(3000, seed=1)
    runs = {
        lp: run_delayed_aci(s, 0, init_scores=init, gamma=0.05, loop=lp)
        for lp in ("sequential", "phase", "smith")
    }
    assert np.array_equal(runs["sequential"]["h"], runs["phase"]["h"])
    assert np.array_equal(runs["sequential"]["h"], runs["smith"]["h"])


def test_pairing_matters_only_under_delay():
    s, init = _stream(4000, seed=2, shift=2000)
    h0 = {
        p: run_delayed_aci(s, 0, init_scores=init, gamma=0.05, pairing=p)["h"]
        for p in ("stored", "arrival")
    }
    assert np.array_equal(h0["stored"], h0["arrival"])
    h20 = {
        p: run_delayed_aci(s, 20, init_scores=init, gamma=0.02, pairing=p)["h"]
        for p in ("stored", "arrival")
    }
    assert not np.array_equal(h20["stored"], h20["arrival"])


def test_projected_level_stays_in_bounds():
    s, init = _stream(4000, seed=3, shift=2000)
    a = run_delayed_aci(s, 30, init_scores=init, gamma=0.05, loop="projected", bounds=(0.01, 0.5))[
        "alpha"
    ]
    assert a.min() >= 0.01 - 1e-12 and a.max() <= 0.5 + 1e-12


def test_missing_labels_never_reach_the_loop():
    s, init = _stream(1000, seed=4)
    d = np.full(1000, 5)
    d[::3] = -1
    assert np.all(np.isnan(run_delayed_aci(s, d, init_scores=init, gamma=0.01)["fed"][::3]))


def test_phase_interleaving_rejects_variable_delay():
    s, init = _stream(100)
    with pytest.raises(ValueError):
        run_delayed_aci(s, np.full(100, 3), init_scores=init, loop="phase")


def test_marginal_coverage_hides_the_limit_cycle():
    """N1 regression: past the limit, marginal coverage stays nominal while a large share of
    intervals is the whole line; the design rule removes it at the same delay."""
    s, init = _stream(20000, seed=5)
    bad = diagnostics(run_delayed_aci(s, 60, init_scores=init, gamma=0.05))
    assert abs(bad["coverage"] - 0.9) < 0.02 and bad["infinite_share"] > 0.30
    good = diagnostics(run_delayed_aci(s, 60, init_scores=init, gamma=design_gamma(60)))
    assert good["infinite_share"] < 0.05
