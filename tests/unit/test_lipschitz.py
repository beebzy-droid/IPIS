"""Tests for the O2 L1 sweep (``ipis.integration.lipschitz``)."""

from __future__ import annotations

import numpy as np
import pytest

from ipis.integration.lipschitz import (
    L1Report,
    l1_from_regime_data,
    l1_sweep,
    nonconformity_scores,
    score_quantile,
)
from ipis.integration.psi import CoordinateScales, OperatingPoint, PsiConfig, psi1


def _cfg() -> PsiConfig:
    return PsiConfig(
        L1=0.1,
        L2=0.2,
        fortuna_op=OperatingPoint(
            R=1.9, D=35.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=66.5
        ),
        femto_ref_reflux_flow=66.5,
        scales=CoordinateScales(),
    )


def _op(alpha: float, r: float = 1.9) -> OperatingPoint:
    return OperatingPoint(
        R=r, D=35.0, alpha=alpha, R_min=0.95, strip_factor=1.4, reflux_flow=r * 35.0
    )


# --- score quantile ------------------------------------------------------------


def test_score_quantile_conformal_level() -> None:
    # 19 scores, alpha=0.1 -> ceil(20*0.9)/19 = 18/19 -> the 18th-smallest.
    scores = list(np.linspace(0.0, 1.8, 19))
    q = score_quantile(scores, 0.1)
    assert q == pytest.approx(1.7, abs=1e-9)


def test_score_quantile_empty_raises() -> None:
    with pytest.raises(ValueError):
        score_quantile([], 0.1)


def test_nonconformity_scores_abs_residual() -> None:
    class _Stub:
        def predict(self, features, sample_id):
            return {"y_pred": 0.010}

    s = nonconformity_scores(_Stub(), [[0.5, 0.5], [0.5, 0.5]], [0.012, 0.007])
    assert s == pytest.approx([0.002, 0.003])


# --- sweep recovers a planted L1 -----------------------------------------------


def test_l1_sweep_recovers_planted_slope() -> None:
    cfg = _cfg()
    ops = [_op(a) for a in (6.0, 6.4, 6.8, 7.2, 7.6)]
    p0 = psi1(ops[0], cfg.scales)
    l_true = 0.5
    # radius grows linearly with distance from the first regime in psi_1 space.
    quantiles = [0.01 + l_true * float(np.linalg.norm(psi1(op, cfg.scales) - p0)) for op in ops]
    rep = l1_sweep(ops, quantiles, cfg)
    assert isinstance(rep, L1Report)
    assert rep.l1 == pytest.approx(l_true, rel=1e-6)
    # the binding pair includes the anchor regime (index 0) and the farthest.
    assert 0 in rep.binding_pair


def test_l1_sweep_needs_two_regimes() -> None:
    with pytest.raises(ValueError):
        l1_sweep([_op(6.0)], [0.01], _cfg())


def test_l1_sweep_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        l1_sweep([_op(6.0), _op(6.4)], [0.01], _cfg())


# --- end-to-end with a synthetic, departure-sensitive sensor -------------------


def test_l1_from_regime_data_end_to_end() -> None:
    cfg = _cfg()
    rng = np.random.default_rng(0)
    ops = [_op(a) for a in (6.0, 6.6, 7.2)]
    p0 = psi1(ops[0], cfg.scales)

    class _DepartureSensor:
        """y_pred error scale grows with similitude departure (planted behavior)."""

        def __init__(self) -> None:
            self._scale = 0.0

        def set_regime(self, op: OperatingPoint) -> None:
            self._scale = 0.001 + 0.4 * float(np.linalg.norm(psi1(op, cfg.scales) - p0))

        def predict(self, features, sample_id):
            return {"y_pred": float(rng.normal(0.0, self._scale))}

    sensor = _DepartureSensor()
    regimes = []
    for op in ops:
        sensor.set_regime(op)
        feats = [[0.5, 0.5]] * 400
        ys = [0.0] * 400  # truth 0; |y_pred - 0| are the scores
        regimes.append((op, feats, ys))

    rep = l1_from_regime_data(sensor, regimes, cfg, alpha1=0.1)
    # radius should increase with departure -> a positive, finite L1.
    assert rep.l1 > 0.0
    assert np.isfinite(rep.l1)
    assert rep.quantiles[2] > rep.quantiles[0]
