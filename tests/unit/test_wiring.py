"""Tests for the production wiring (``ipis.integration.wiring``).

Adapter mapping is duck-typed, so it runs in the sandbox with stub services that
mimic the real M1/M2 dict contracts; the factory is exercised end-to-end with a
real plant and the real health-constrained RTO (GEKKO).
"""

from __future__ import annotations

import numpy as np
import pytest

from ipis.integration.health_rto import EconomicParams
from ipis.integration.orchestrator import CycleRecord
from ipis.integration.plant import (
    FeatureSynthesizer,
    FeedSpec,
    PumpDegradation,
)
from ipis.integration.psi import CoordinateScales, OperatingPoint, PsiConfig
from ipis.integration.wiring import (
    M1Adapter,
    M1FeatureTransform,
    M2Adapter,
    build_integrated_orchestrator,
)

# --- stub services mimicking the real dict contracts ---------------------------


class _StubM1Service:
    def __init__(self) -> None:
        self.labelled: list[tuple[str, float]] = []

    def predict(self, features, sample_id):
        return {
            "y_pred": 0.010,
            "lower": 0.0097,
            "upper": 0.0103,
            "bias": 0.0,
            "drift_flag": False,
        }

    def label(self, sample_id, y_true):
        self.labelled.append((sample_id, y_true))
        return {"covered": True}


class _StubM2Service:
    def observe(self, equipment_id, features):
        return {"health_score": 0.9, "flag": "OK", "rul_hours": 500.0}


class _StubSurface:
    coef = (-3.84, -0.37, 0.0, 0.0, 0.0, 0.0)


class _Prop:
    def relative_volatility(self, t):
        return 6.0

    def liquid_viscosity_cp(self, t):
        return 0.12

    def k_value_hk(self, t):
        return 0.8


def _psi_cfg() -> PsiConfig:
    return PsiConfig(
        L1=0.05,
        L2=0.30,
        fortuna_op=OperatingPoint(
            R=1.9, D=35.0, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=66.5
        ),
        femto_ref_reflux_flow=66.5,
        scales=CoordinateScales(),
    )


# --- adapter mapping (sandbox) --------------------------------------------------


def _out(temp_c: float, r: float = 2.0, d: float = 35.0):
    op = OperatingPoint(R=r, D=d, alpha=6.0, R_min=0.95, strip_factor=1.4, reflux_flow=r * d)

    class _O:
        sensor_temp_c = temp_c
        operating_point = op

    return _O()


def test_feature_transform_matches_add_physics_features() -> None:
    pytest.importorskip("ipis.module1_soft_sensor.features.physics_features")
    import pandas as pd

    from ipis.module1_soft_sensor.features.physics_features import (
        PHYSICS_FEATURE_COLS,
        add_physics_features,
    )

    ft = M1FeatureTransform(include_raw_u5=False, transport_lag=2)
    o = _out(106.0, 2.0, 35.0)
    for _ in range(4):
        v = ft(o)  # constant input -> lagged value equals current
    assert len(v) == 3
    u5, u2 = (106.0 - 100.0) / 12.0, (5.0 - 4.5) / 1.0
    u3 = (2.0 * 35.0 - 26.0) / (111.0 - 26.0)
    ref = add_physics_features(pd.DataFrame({"u5": [u5], "u2": [u2], "u3": [u3]}))
    ref = ref[list(PHYSICS_FEATURE_COLS)].to_numpy(float)[0]
    assert np.allclose(v, ref)


def test_feature_transform_raw_u5_adds_a_column() -> None:
    pytest.importorskip("ipis.module1_soft_sensor.features.physics_features")
    ft = M1FeatureTransform(include_raw_u5=True, transport_lag=0)
    assert len(ft(_out(106.0))) == 4  # 3 physics + raw u5


def test_feature_transform_lag_uses_past_sample() -> None:
    pytest.importorskip("ipis.module1_soft_sensor.features.physics_features")
    ft = M1FeatureTransform(include_raw_u5=False, transport_lag=3)
    outs = [ft(_out(t)) for t in (106.0, 107.0, 108.0, 109.0, 110.0)]
    base = M1FeatureTransform(include_raw_u5=False, transport_lag=0)(_out(106.0))
    assert np.allclose(outs[3], base)  # 4th cycle emits the t-3 sample (106 C)


def test_m1_adapter_maps_estimate_and_halfwidth() -> None:
    a = M1Adapter(_StubM1Service())
    r = a.predict(np.array([0.5, 0.5]), "0")
    assert r.estimate == pytest.approx(0.010)
    assert r.half_width == pytest.approx((0.0103 - 0.0097) / 2.0)
    assert r.drift is False


def test_m1_adapter_handles_batch_list() -> None:
    class _Batch(_StubM1Service):
        def predict(self, features, sample_id):
            return [super().predict(features, sample_id)]

    r = M1Adapter(_Batch()).predict(np.array([0.5, 0.5]), "0")
    assert r.estimate == pytest.approx(0.010)


def test_m1_adapter_label_forwards() -> None:
    svc = _StubM1Service()
    M1Adapter(svc).label("7", 0.012)
    assert svc.labelled == [("7", 0.012)]


def test_m2_adapter_maps_fields() -> None:
    r = M2Adapter(_StubM2Service()).observe("pump", np.zeros(2))
    assert r.health_score == pytest.approx(0.9)
    assert r.flag == "OK"
    assert r.rul_hours == pytest.approx(500.0)


def test_m2_adapter_rul_absent_is_none() -> None:
    class _NoRul:
        def observe(self, equipment_id, features):
            return {"health_score": 0.95, "flag": "OK"}

    assert M2Adapter(_NoRul()).observe("pump", np.zeros(2)).rul_hours is None


# --- full integrated cycle via the factory (GEKKO) -----------------------------


def test_build_integrated_orchestrator_runs_a_cycle() -> None:
    pytest.importorskip("gekko")
    pytest.importorskip("ipis.module1_soft_sensor.features.physics_features")

    def xb_truth(R, D, z):
        c = _StubSurface.coef
        return float(np.exp(c[0] + c[1] * R + c[2] * D))

    def tray_temp(R, D):
        return 104.0 - 2.0 * (R - 1.9)

    orch = build_integrated_orchestrator(
        soft_sensor=_StubM1Service(),
        pdm=_StubM2Service(),
        ln_xb_surface=_StubSurface(),
        econ=EconomicParams(0.62, 0.55, 6.5, 30000.0, 58.12, 86.18),
        xb_truth=xb_truth,
        tray_temp=tray_temp,
        properties=_Prop(),
        degradation=PumpDegradation(ref_reflux_flow=66.5, base_rate=1e-3),
        feature_synthesizer=FeatureSynthesizer(
            feature_names=("rms",), baseline=np.zeros(1), growth=np.ones(1)
        ),
        psi_cfg=_psi_cfg(),
        feed=FeedSpec(F=100.0, z_lk=0.35),
        spec_xb_c4=0.012,
        eps=0.05,
    )
    rec = orch.run_cycle()
    assert isinstance(rec, CycleRecord)
    # M1 estimate/half-width propagated into the bus fields.
    assert rec.quality_estimate == pytest.approx(0.010)
    assert rec.quality_half_width == pytest.approx(0.0003)
    assert rec.state_fields["equipment_health"]["reflux_pump_P101"] == pytest.approx(0.9)
