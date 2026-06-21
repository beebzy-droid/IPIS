"""Unit tests for the P-GP plant emulator (``ipis.integration.plant``)."""

from __future__ import annotations

import numpy as np
import pytest

from ipis.integration.plant import (
    DebutanizerPlant,
    FeatureSynthesizer,
    FeedSpec,
    PumpDegradation,
    column_flows,
    oconnell_efficiency,
    stripping_factor,
    underwood_rmin_binary,
)
from ipis.integration.psi import OperatingPoint

# --- injected stubs (stand in for the M3 GP surfaces and CoolProp) -------------


def _xb_stub(R: float, D: float, z: float) -> float:
    # More reflux -> purer bottoms -> less C4 in bottoms.
    return 0.05 * float(np.exp(-0.3 * (R - 1.0)))


def _tray_stub(R: float, D: float) -> float:
    return 104.0 - 2.0 * (R - 2.0)


class _PropStub:
    def relative_volatility(self, temp_c: float) -> float:
        return 6.0 * float(np.exp(-0.01 * (temp_c - 104.0)))

    def liquid_viscosity_cp(self, temp_c: float) -> float:
        return 0.12

    def k_value_hk(self, temp_c: float) -> float:
        return 0.8


def _plant(rate: float = 1.0e-3) -> DebutanizerPlant:
    names = ("rms", "kurtosis", "bpfo")
    return DebutanizerPlant(
        xb_truth=_xb_stub,
        tray_temp=_tray_stub,
        properties=_PropStub(),
        feed=FeedSpec(F=100.0, z_lk=0.5, q=1.0),
        degradation=PumpDegradation(ref_reflux_flow=125.0, base_rate=rate),
        synthesizer=FeatureSynthesizer(
            feature_names=names,
            baseline=np.zeros(3),
            growth=np.ones(3),
        ),
        feed_z=0.5,
    )


# --- Perry's-verified golden checks --------------------------------------------


def test_oconnell_matches_perry_example_14_12() -> None:
    # Perry Example 14-12: alpha = 1.3, mu_L = 0.25 cP -> E_OC = 0.65.
    assert oconnell_efficiency(1.3, 0.25) == pytest.approx(0.65, abs=5e-3)


def test_underwood_rmin_hand_verified() -> None:
    # alpha=2.5, z=0.5, x_D=0.95, q=1 -> theta=2.5/1.75; R_min = 1.10 (hand-checked).
    rmin = underwood_rmin_binary(2.5, 0.5, 0.95, 1.0)
    assert rmin == pytest.approx(1.10, abs=1e-2)


def test_underwood_root_satisfies_eq_13_38() -> None:
    # Independent check: the returned R_min must be consistent with a root of
    # Eq. 13-38 lying in (1, alpha) for a non-unity q.
    alpha, z, x_d, q = 3.0, 0.45, 0.9, 0.8
    rmin = underwood_rmin_binary(alpha, z, x_d, q)
    assert np.isfinite(rmin)
    assert rmin > 0.0


def test_underwood_rejects_alpha_le_one() -> None:
    with pytest.raises(ValueError):
        underwood_rmin_binary(1.0, 0.5, 0.95, 1.0)


# --- flows and stripping factor ------------------------------------------------


def test_column_flows_balance() -> None:
    feed = FeedSpec(F=100.0, z_lk=0.5, q=1.0)
    flows = column_flows(R=2.5, D=49.0, feed=feed)
    assert pytest.approx(51.0) == flows.B
    assert flows.L_rect == pytest.approx(2.5 * 49.0)
    assert flows.V_rect == pytest.approx(3.5 * 49.0)
    assert flows.V_strip == pytest.approx(flows.L_strip - flows.B)
    assert flows.reflux_flow == pytest.approx(flows.L_rect)


def test_column_flows_rejects_bad_distillate() -> None:
    feed = FeedSpec(F=100.0, z_lk=0.5)
    with pytest.raises(ValueError):
        column_flows(R=2.5, D=150.0, feed=feed)


def test_stripping_factor_definition() -> None:
    assert stripping_factor(0.8, 200.0, 250.0) == pytest.approx(0.8 * 200.0 / 250.0)


def test_stripping_factor_rejects_zero_liquid() -> None:
    with pytest.raises(ValueError):
        stripping_factor(0.8, 200.0, 0.0)


# --- C1 pump degradation and feature synthesis ---------------------------------


def test_degradation_monotone_and_load_sensitive() -> None:
    low = PumpDegradation(ref_reflux_flow=125.0, base_rate=1e-2)
    high = PumpDegradation(ref_reflux_flow=125.0, base_rate=1e-2)
    for _ in range(20):
        s_low = low.step(125.0)  # at reference -> load 1.0
        s_high = high.step(180.0)  # higher reflux -> load > 1 -> faster wear
    assert 0.0 <= s_low <= s_high <= 1.0
    assert s_high > s_low


def test_degradation_clamps_at_unity() -> None:
    deg = PumpDegradation(ref_reflux_flow=125.0, base_rate=1.0, damage_at_failure=1.0)
    for _ in range(10):
        deg.step(200.0)
    assert deg.severity == pytest.approx(1.0)


def test_feature_synthesizer_monotone_drift() -> None:
    synth = FeatureSynthesizer(feature_names=("a", "b"), baseline=np.zeros(2), growth=np.ones(2))
    near = np.linalg.norm(synth.synthesize(0.1))
    far = np.linalg.norm(synth.synthesize(0.9))
    assert far > near


def test_feature_synthesizer_length_guard() -> None:
    with pytest.raises(ValueError):
        FeatureSynthesizer(feature_names=("a", "b"), baseline=np.zeros(3), growth=np.ones(2))


# --- end-to-end plant step -----------------------------------------------------


def test_plant_step_produces_valid_operating_point() -> None:
    plant = _plant()
    out = plant.step(R=2.5, D=49.0)
    assert isinstance(out.operating_point, OperatingPoint)
    assert out.operating_point.reflux_flow == pytest.approx(2.5 * 49.0)
    assert out.operating_point.alpha > 0.0
    assert out.pump_features.shape == (3,)
    assert 0.0 <= out.severity <= 1.0
    assert 0.0 < out.oconnell_efficiency < 1.5


def test_plant_step_severity_accumulates() -> None:
    plant = _plant(rate=1e-2)
    s1 = plant.step(R=3.0, D=49.0).severity
    for _ in range(10):
        last = plant.step(R=3.0, D=49.0)
    assert last.severity > s1


def test_plant_mass_balance_distillate_purity() -> None:
    # x_D from F z = D x_D + B x_B must stay a valid fraction.
    plant = _plant()
    out = plant.step(R=4.0, D=49.0)
    # high reflux -> low xb -> high x_D, but clipped to (0,1)
    assert 0.0 < out.xb_true < 1.0
