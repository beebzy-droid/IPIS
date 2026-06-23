"""Unit tests for the Module 5 campaign recorder (``ipis.integration.recorder``)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from ipis.integration.dynamic_plant import DynamicDebutanizerPlant
from ipis.integration.plant import FeatureSynthesizer, FeedSpec, PumpDegradation
from ipis.integration.recorder import CampaignRecorder, CampaignSample


def _xb_stub(R: float, D: float, z: float) -> float:
    return 0.05 * float(np.exp(-0.3 * (R - 1.0)))


def _tray_stub(R: float, D: float) -> float:
    return 104.0 - 2.0 * (R - 2.0)


class _PropStub:
    def relative_volatility(self, temp_c: float) -> float:
        return 6.0

    def liquid_viscosity_cp(self, temp_c: float) -> float:
        return 0.12

    def k_value_hk(self, temp_c: float) -> float:
        return 0.8


def _plant() -> DynamicDebutanizerPlant:
    return DynamicDebutanizerPlant(
        xb_truth=_xb_stub,
        tray_temp=_tray_stub,
        properties=_PropStub(),
        feed=FeedSpec(F=100.0, z_lk=0.5, q=1.0),
        degradation=PumpDegradation(ref_reflux_flow=125.0, base_rate=1.0e-3),
        synthesizer=FeatureSynthesizer(
            feature_names=("rms",), baseline=np.zeros(1), growth=np.ones(1)
        ),
    )


def test_records_plant_fields() -> None:
    plant = _plant()
    rec = CampaignRecorder()
    out = plant.step(3.5, 55.0)
    sample = rec.record(out, cycle=0)
    assert len(rec) == 1
    assert sample.applied_reflux == 3.5
    assert sample.applied_distillate == 55.0
    assert sample.realized_reflux == out.realized_reflux
    assert sample.xb_true == out.xb_true
    assert sample.reflux_flow == out.operating_point.reflux_flow
    assert sample.gilliland_coord == out.operating_point.gilliland_coord
    # intelligence fields default to None until the loop supplies them.
    assert sample.quality_estimate is None
    assert sample.rul_lower_hours is None


def test_optional_intelligence_fields_attach() -> None:
    plant = _plant()
    rec = CampaignRecorder()
    out = plant.step(3.0, 50.0)
    sample = rec.record(
        out,
        cycle=1,
        quality_estimate=0.041,
        quality_half_width=0.007,
        rul_lower_hours=820.0,
        health_flag="WARN",
        aci_quantile=0.012,
        s_event=True,
        coverage_floor=0.75,
    )
    assert sample.quality_estimate == 0.041
    assert sample.health_flag == "WARN"
    assert sample.s_event is True
    assert sample.coverage_floor == 0.75


def test_unknown_intelligence_field_raises() -> None:
    plant = _plant()
    rec = CampaignRecorder()
    out = plant.step(3.0, 50.0)
    with pytest.raises(TypeError, match="unknown intelligence field"):
        rec.record(out, not_a_field=1.0)


def test_default_cycle_is_sequential() -> None:
    plant = _plant()
    rec = CampaignRecorder()
    for _ in range(3):
        rec.record(plant.step(3.0, 50.0))
    assert [s.cycle for s in rec.samples] == [0, 1, 2]
    assert rec.latest is not None
    assert rec.latest.cycle == 2


def test_to_arrays_shapes_and_none_to_nan() -> None:
    plant = _plant()
    rec = CampaignRecorder()
    rec.record(plant.step(3.0, 50.0), quality_estimate=0.04, health_flag="OK")
    rec.record(plant.step(3.0, 50.0))  # no intel -> None -> nan
    arr = rec.to_arrays()
    assert arr["xb_true"].shape == (2,)
    assert arr["quality_estimate"][0] == pytest.approx(0.04)
    assert np.isnan(arr["quality_estimate"][1])
    # flags stay as an object column (strings + None), not floats.
    assert arr["health_flag"].dtype == object
    assert arr["health_flag"][0] == "OK"


def test_to_records_is_json_serializable() -> None:
    plant = _plant()
    rec = CampaignRecorder()
    rec.record(plant.step(3.0, 50.0), s_event=True, coverage_floor=0.75)
    rows = rec.to_records()
    blob = json.dumps(rows)  # must not raise
    assert isinstance(blob, str)
    assert rows[0]["s_event"] is True


def test_empty_recorder() -> None:
    rec = CampaignRecorder()
    assert len(rec) == 0
    assert rec.latest is None
    assert rec.to_arrays() == {}
    assert rec.to_records() == []


def test_sample_field_set_is_stable() -> None:
    # Guard the viewer/analysis contract: the field set is what both consumers expect.
    expected = {
        "cycle",
        "time_h",
        "applied_reflux",
        "applied_distillate",
        "realized_reflux",
        "realized_distillate",
        "sensor_temp_c",
        "xb_true",
        "xb_measured",
        "severity",
        "gilliland_coord",
        "reflux_flow",
        "quality_estimate",
        "quality_half_width",
        "rul_lower_hours",
        "true_rul_hours",
        "health_flag",
        "aci_quantile",
        "s_event",
        "coverage_floor",
    }
    assert set(CampaignSample.__dataclass_fields__) == expected
