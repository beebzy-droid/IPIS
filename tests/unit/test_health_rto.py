"""Tests for the health-constrained RTO (``ipis.integration.health_rto``).

Pure ψ-budget checks always run; the GEKKO/IPOPT solve is gated behind
``pytest.importorskip('gekko')`` so it runs on the repo and skips where the
solver is unavailable.
"""

from __future__ import annotations

import pytest

from ipis.integration.health_rto import (
    EconomicParams,
    HealthRTOResult,
    psi_budget_value,
    solve_health_constrained_rto,
)
from ipis.integration.psi import (
    CoordinateScales,
    OperatingPoint,
    PsiConfig,
    budget_penalty,
)


def _cfg(L1: float = 0.1, L2: float = 0.2) -> PsiConfig:
    return PsiConfig(
        L1=L1,
        L2=L2,
        fortuna_op=OperatingPoint(
            R=2.0, D=35.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=70.0
        ),
        femto_ref_reflux_flow=70.0,
        scales=CoordinateScales(),
    )


def _econ() -> EconomicParams:
    return EconomicParams(
        c4_value_usd_per_kg=0.5,
        gasoline_value_usd_per_kg=0.6,
        energy_cost_usd_per_gj=8.0,
        dhvap_kj_per_kmol=30000.0,
        m_lk_kg_per_kmol=58.12,
        m_hk_kg_per_kmol=86.18,
    )


# ln_xb = -3.0 - 0.5 R  -> xb in ~(0.018, 0.033) over the R box, decreasing in R.
_COEF = (-3.0, -0.5, 0.0, 0.0, 0.0, 0.0)


def _r_in_bounds(r: float) -> bool:
    return 0.8 - 1e-3 <= r <= 3.0 + 1e-3


# --- pure ψ-budget checks (always run) -----------------------------------------


def test_psi_budget_matches_penalty() -> None:
    cfg = _cfg()
    op = OperatingPoint(
        R=2.6, D=36.0, alpha=6.2, R_min=0.9, strip_factor=1.5, reflux_flow=2.6 * 36.0
    )
    direct = budget_penalty(op, cfg)
    via = psi_budget_value(2.6, 36.0, 6.2, 0.9, 1.5, cfg)
    assert via == pytest.approx(direct)


def test_psi_budget_zero_at_anchor() -> None:
    # At the Fortuna regime AND the FEMTO reference flow the budget is zero.
    cfg = _cfg()
    val = psi_budget_value(2.0, 35.0, 6.0, 0.95, 1.4, cfg)
    assert val == pytest.approx(0.0, abs=1e-9)


def test_eps_negative_rejected() -> None:
    with pytest.raises(ValueError):
        solve_health_constrained_rto(
            _COEF, _econ(), alpha=6.0, R_min=0.95, strip_factor=1.4, cfg=_cfg(), eps=-1.0
        )


def test_backoff_consumes_spec_rejected() -> None:
    with pytest.raises(ValueError):
        solve_health_constrained_rto(
            _COEF,
            _econ(),
            alpha=6.0,
            R_min=0.95,
            strip_factor=1.4,
            cfg=_cfg(),
            eps=1.0,
            spec_xb_c4=0.02,
            backoff=0.02,
        )


def test_rto_hold_returns_none() -> None:
    out = solve_health_constrained_rto(
        _COEF,
        _econ(),
        alpha=6.0,
        R_min=0.95,
        strip_factor=1.4,
        cfg=_cfg(),
        eps=1.0,
        rto_hold=True,
    )
    assert out is None


def test_result_to_state_bus_fields() -> None:
    res = HealthRTOResult(
        reflux_ratio=2.0,
        distillate_kmol_h=35.0,
        x_bottoms_lk=0.018,
        reboiler_duty_kw=900.0,
        profit_usd_per_h=1234.0,
        backoff=0.003,
        eps=0.05,
        budget_at_opt=0.04,
        active_constraints=["psi_budget"],
    )
    fields = res.to_state_bus_fields()
    assert fields["setpoint_recommendations"]["reflux_ratio"] == 2.0
    assert "psi_budget" in fields["active_constraints"]


# --- GEKKO/IPOPT solve (repo or where gekko is installed) -----------------------


def test_solve_feasible_and_respects_budget() -> None:
    pytest.importorskip("gekko")
    out = solve_health_constrained_rto(
        _COEF,
        _econ(),
        alpha=6.0,
        R_min=0.95,
        strip_factor=1.4,
        cfg=_cfg(),
        eps=0.5,
        spec_xb_c4=0.05,
        backoff=0.005,
    )
    assert out is not None
    # quality constraint respected
    assert out.x_bottoms_lk <= 0.05 - 0.005 + 1e-4
    # ψ-budget respected at the optimum
    assert out.budget_at_opt <= out.eps + 1e-3
    assert _r_in_bounds(out.reflux_ratio)
    assert 33.0 - 1e-3 <= out.distillate_kmol_h <= 37.0 + 1e-3


def test_tighter_budget_costs_profit() -> None:
    pytest.importorskip("gekko")
    loose = solve_health_constrained_rto(
        _COEF, _econ(), alpha=6.0, R_min=0.95, strip_factor=1.4, cfg=_cfg(), eps=50.0
    )
    tight = solve_health_constrained_rto(
        _COEF, _econ(), alpha=6.0, R_min=0.95, strip_factor=1.4, cfg=_cfg(), eps=0.05
    )
    assert loose is not None and tight is not None
    # The health constraint can only reduce (or hold) the economic optimum.
    assert tight.profit_usd_per_h <= loose.profit_usd_per_h + 1e-6
    assert tight.budget_at_opt <= 0.05 + 1e-3
