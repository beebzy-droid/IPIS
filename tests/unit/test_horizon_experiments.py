"""Unit tests for the Module 5 horizon experiments (``horizon_experiments``).

Small parameter counts keep these fast; the full-resolution sweeps live in
``scripts/run_horizon_sweeps.py``.
"""

from __future__ import annotations

import math

from ipis.integration.coverage import CoverageConfig
from ipis.integration.horizon_experiments import (
    deadtime_sweep,
    gamma_sweep,
    two_arm_contrast,
)

_CFG = CoverageConfig(
    spec_xb_c4=0.02, rul_min_hours=200.0, alpha1=0.10, alpha2=0.10, eps=0.05, n_seeds=2, n_cycles=50
)


def test_two_arm_contrast_blind_violates_constrained_holds() -> None:
    t = two_arm_contrast(_CFG)
    assert t.floor == 0.75
    # both arms meet the quality spec ...
    assert t.blind.quality_coverage >= 0.95
    assert t.constrained.quality_coverage >= 0.95
    # ... but the blind arm's over-reflux drives projected RUL below the floor.
    assert t.blind.rul_coverage < 0.5
    assert t.constrained.rul_coverage >= 0.95
    # so S_k collapses for the blind arm and holds for the constrained arm.
    assert not t.blind.meets_floor
    assert t.constrained.meets_floor
    assert t.blind.s_coverage < t.constrained.s_coverage
    # the cap binds in the constrained arm (psi-budget active), not the blind arm.
    assert t.constrained.frac_psi_binding > 0.5
    assert t.blind.frac_psi_binding == 0.0


def test_deadtime_validity_invariant() -> None:
    d = deadtime_sweep(_CFG, [0, 2, 8], campaign_cycles=120)
    assert d.floor == 0.75
    # S_k coverage holds the floor for every label delay (validity invariant to deadtime).
    for p in d.points:
        assert p.s_ci_lo >= d.floor, f"D_a={p.d_a} S_k CI lower {p.s_ci_lo} below floor"
        assert p.interval_coverage > 0.80


def test_gamma_sweep_union_bound_goes_vacuous() -> None:
    g = gamma_sweep(_CFG, [0.008, 0.032], campaign_cycles=120, union_horizons=[1, 10, 1000])
    assert g.selected_gamma in (0.001, 0.002, 0.004, 0.008, 0.016, 0.032, 0.064, 0.128)
    assert math.isfinite(g.aci_mean_half_width)
    hw_by_k = {u.horizon_k: u.bonferroni_half_width for u in g.union_bound}
    # Bonferroni widens with K and is vacuous (inf) at a realistic horizon, where ACI stays finite.
    assert hw_by_k[1] <= hw_by_k[10]
    assert math.isinf(hw_by_k[1000])  # vacuous at a realistic horizon
    assert math.isfinite(g.aci_mean_half_width)  # ACI stays finite where Bonferroni is not


def test_two_arm_quality_high_both_arms() -> None:
    # guardrail: the contrast is RUL-driven, not a quality artifact.
    t = two_arm_contrast(_CFG)
    assert t.blind.quality_coverage == 1.0 or t.blind.quality_coverage >= 0.95
