"""Unit tests for the ψ-coordinate system (``ipis.integration.psi``)."""

from __future__ import annotations

import numpy as np
import pytest

from ipis.integration.psi import (
    AFFINITY_BHP_EXPONENT,
    CoordinateScales,
    OperatingPoint,
    PsiConfig,
    budget_penalty,
    certified_coverage,
    departures,
    estimate_lipschitz,
    evaluate_budget,
    psi1,
    psi2,
    pump_load,
)


def _fortuna() -> OperatingPoint:
    # Stand-in M1 calibration regime; numbers are illustrative, not load-bearing.
    return OperatingPoint(
        R=2.5, D=50.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=125.0
    )


def _config(L1: float = 0.10, L2: float = 0.20) -> PsiConfig:
    return PsiConfig(
        L1=L1,
        L2=L2,
        fortuna_op=_fortuna(),
        femto_ref_reflux_flow=125.0,
        scales=CoordinateScales(),
    )


def test_operating_point_validation() -> None:
    with pytest.raises(ValueError):
        OperatingPoint(
            R=2.5, D=-1.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=125.0
        )
    with pytest.raises(ValueError):
        OperatingPoint(
            R=2.5, D=50.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=0.0
        )
    with pytest.raises(ValueError):
        OperatingPoint(
            R=np.inf, D=50.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=125.0
        )


def test_gilliland_coordinate() -> None:
    op = _fortuna()
    expected = (op.R - op.R_min) / (op.R + 1.0)
    assert op.gilliland_coord == pytest.approx(expected)


def test_psi1_components() -> None:
    op = _fortuna()
    s = CoordinateScales()
    v = psi1(op, s)
    assert v.shape == (3,)
    assert v[0] == pytest.approx(op.alpha)
    assert v[1] == pytest.approx(op.gilliland_coord)
    assert v[2] == pytest.approx(op.strip_factor)


def test_affinity_cubic_load() -> None:
    # Doubling reflux flow must multiply pump load by 2^3 = 8 (Perry Table 10-13).
    assert pytest.approx(3.0) == AFFINITY_BHP_EXPONENT
    base = pump_load(125.0, 125.0)
    doubled = pump_load(250.0, 125.0)
    assert base == pytest.approx(1.0)
    assert doubled == pytest.approx(8.0)


def test_zero_departure_at_anchor() -> None:
    # psi1 anchored at the Fortuna regime; psi2 anchored at the FEMTO ref flow.
    cfg = _config()
    op = _fortuna()  # equals fortuna_op AND reflux_flow == femto_ref
    d1, d2 = departures(op, cfg)
    assert d1 == pytest.approx(0.0, abs=1e-12)
    assert d2 == pytest.approx(0.0, abs=1e-12)
    assert budget_penalty(op, cfg) == pytest.approx(0.0, abs=1e-12)


def test_psi2_anchor_value() -> None:
    cfg = _config()
    at_ref = psi2(_fortuna(), cfg.femto_ref_reflux_flow, cfg.scales)
    assert at_ref[0] == pytest.approx(1.0)


def test_penalty_monotone_in_reflux() -> None:
    cfg = _config()
    near = OperatingPoint(
        R=2.5, D=50.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=130.0
    )
    far = OperatingPoint(
        R=2.5, D=50.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=160.0
    )
    assert budget_penalty(near, cfg) < budget_penalty(far, cfg)


def test_penalty_responds_to_reflux_ratio() -> None:
    # Moving R away from the anchor shifts the Gilliland coordinate -> nonzero d1.
    cfg = _config()
    shifted = OperatingPoint(
        R=4.0, D=50.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=125.0
    )
    d1, d2 = departures(shifted, cfg)
    assert d1 > 0.0
    assert d2 == pytest.approx(0.0, abs=1e-12)


def test_certified_coverage_arithmetic() -> None:
    assert certified_coverage(0.05, 0.05, 0.02) == pytest.approx(0.88)


def test_evaluate_budget_feasibility() -> None:
    cfg = _config()
    far = OperatingPoint(
        R=4.0, D=50.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=200.0
    )
    tight = evaluate_budget(far, cfg, eps=0.01, alpha1=0.05, alpha2=0.05)
    loose = evaluate_budget(far, cfg, eps=1e6, alpha1=0.05, alpha2=0.05)
    assert tight.feasible is False
    assert tight.slack < 0.0
    assert loose.feasible is True
    assert loose.coverage_floor == pytest.approx(1.0 - 0.10 - 1e6)


def test_lipschitz_recovers_known_slope() -> None:
    # q = 0.3 * x along a 1-D psi axis -> Lipschitz constant 0.3.
    xs = np.linspace(0.0, 1.0, 11).reshape(-1, 1)
    q = 0.3 * xs.ravel()
    assert estimate_lipschitz(xs, q) == pytest.approx(0.3, rel=1e-9)


def test_lipschitz_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        estimate_lipschitz([[0.0], [1.0]], [0.0, 1.0, 2.0])


def test_required_lipschitz_constants() -> None:
    # Non-finite Lipschitz constants must be rejected at construction.
    with pytest.raises(ValueError):
        PsiConfig(
            L1=float("nan"),
            L2=0.2,
            fortuna_op=_fortuna(),
            femto_ref_reflux_flow=125.0,
        )
