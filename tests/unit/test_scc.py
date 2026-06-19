"""Tests for Similarity-Calibrated Conformal (SCC): simulator similitude, naive-vs-SCC
coverage recovery, the Barber coverage-gap certificate, graceful degradation, and the
three-way similitude diagnostic."""

from __future__ import annotations

import itertools

import numpy as np

from ipis.module2_pdm.scc.conformal import (
    coverage_naive,
    coverage_scc,
    scores_for,
    tv_distance,
)
from ipis.module2_pdm.scc.deactivation import A_FAIL, simulate_condition
from ipis.module2_pdm.scc.diagnostic import FEMTO_COND, P_EXP, diagnose, l10_ratio

E1, A1 = 80e3, 5e3
FRACS = [0.3, 0.5, 0.7]
ALPHA = 0.10


def test_eta0_similitude_collapses_dimensionless_curve():
    # at fraction f of a run's own life, noise-free activity is A_FAIL**f for ALL T
    for temp in (600.0, 700.0):
        run = simulate_condition(temp, 1, A1, E1, noise=0.0, sigma_lna=0.0, seed=0)[0]
        idx = int(np.searchsorted(run.t, 0.5 * run.life))
        assert abs(run.a_true[idx] - A_FAIL**0.5) < 1e-2


def test_life_scale_ratio_across_conditions():
    lo = simulate_condition(600.0, 200, A1, E1, seed=1)
    hi = simulate_condition(700.0, 200, A1, E1, seed=2)
    ratio = np.mean([r.life for r in lo]) / np.mean([r.life for r in hi])
    assert ratio > 5.0  # Arrhenius gives ~10x; defeats naive cross-condition calibration


def test_naive_miscovers_scc_recovers():
    # calibrate on short-life (700 K), deploy on long-life (600 K)
    s = scores_for(simulate_condition(700.0, 400, A1, E1, seed=3), FRACS, E1, A1)
    t = scores_for(simulate_condition(600.0, 400, A1, E1, seed=4), FRACS, E1, A1)
    naive = coverage_naive(s[0], t[0], ALPHA)
    scc = coverage_scc(s[1], t[1], ALPHA)
    assert naive < 0.80  # naive undercovers badly
    assert abs(scc - (1 - ALPHA)) < 0.08  # SCC recovers to ~0.90


def test_certificate_bound_holds():
    s = scores_for(simulate_condition(700.0, 400, A1, E1, seed=5), FRACS, E1, A1)
    t = scores_for(simulate_condition(600.0, 400, A1, E1, seed=6), FRACS, E1, A1)
    scc_gap = max(0.0, (1 - ALPHA) - coverage_scc(s[1], t[1], ALPHA))
    assert scc_gap <= 2 * tv_distance(s[1], t[1]) + 0.02  # Barber bound


def test_departure_degrades_gracefully():
    def scc_gap(eta: float) -> float:
        s = scores_for(
            simulate_condition(600.0, 400, A1, E1, a2=4e5, e2=110e3, eta=eta, seed=7), FRACS, E1, A1
        )
        t = scores_for(
            simulate_condition(700.0, 400, A1, E1, a2=4e5, e2=110e3, eta=eta, seed=8), FRACS, E1, A1
        )
        return max(0.0, (1 - ALPHA) - coverage_scc(s[1], t[1], ALPHA))

    assert scc_gap(2.0) > scc_gap(0.0) + 0.02  # unmodeled physics widens the gap


def _synthetic_lives(kind: str, n_per: int, seed: int = 0) -> dict[int, np.ndarray]:
    rng = np.random.default_rng(seed)
    if kind == "similitude":  # lives obey L10
        cap = 2e4
        return {
            c: cap**P_EXP / ((p**P_EXP) * (n / 60.0)) * rng.lognormal(0, 0.25, n_per)
            for c, (p, n) in FEMTO_COND.items()
        }
    spread = 0.25 if kind == "violated" else 0.6
    return {c: rng.lognormal(np.log(3 * 3600), spread, n_per) for c in FEMTO_COND}


def test_diagnostic_discriminates():
    assert diagnose(_synthetic_lives("similitude", 40))[0] == "holds"
    assert diagnose(_synthetic_lives("violated", 40))[0] == "violated"
    assert diagnose(_synthetic_lives("femto", 6))[0] == "indeterminate"


def test_l10_ratio_matches_published_conditions():
    # condition 1 (4000 N, 1800 rpm) should outlast condition 3 (5000 N, 1500 rpm) ~1.63x
    assert abs(l10_ratio(1, 3) - (5000 / 4000) ** 3 * (1500 / 1800)) < 1e-9
    assert 1.5 < l10_ratio(1, 3) < 1.75


def test_scores_shapes():
    runs = simulate_condition(650.0, 10, A1, E1, seed=9)
    raw, dim = scores_for(runs, FRACS, E1, A1)
    assert raw.shape == dim.shape == (len(runs) * len(FRACS),)
    assert np.all(np.isfinite(raw)) and np.all(np.isfinite(dim))
    # spot-check a permutation invariance of the pooled TV (sanity on the estimator)
    assert tv_distance(raw, raw) < 1e-9


def test_all_condition_pairs_scc_not_worse_than_naive_at_eta0():
    temps = [600.0, 650.0, 700.0]
    sc = {
        T: scores_for(simulate_condition(T, 300, A1, E1, seed=int(T)), FRACS, E1, A1) for T in temps
    }
    for s_t, t_t in itertools.permutations(temps, 2):
        naive = coverage_naive(sc[s_t][0], sc[t_t][0], ALPHA)
        scc = coverage_scc(sc[s_t][1], sc[t_t][1], ALPHA)
        # SCC's coverage is at least as close to target as naive's (or both adequate)
        assert abs(scc - (1 - ALPHA)) <= abs(naive - (1 - ALPHA)) + 0.05
