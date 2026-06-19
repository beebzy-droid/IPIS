"""Tests for the Phase-2D PdM service (ipis.module2_pdm.serving).

The integration test feeds a synthetic healthy->degrading sequence sample by
sample and asserts the OperationalState transitions the IPIS contract expects:
health_score falls, the flag escalates OK->WARN->ALARM, and the RUL appears only
after the degradation onset (FPT) and then shrinks. Unit tests cover RUL gating
and artifact / state round-trips.
"""

from __future__ import annotations

import numpy as np

from ipis.module2_pdm.health.health_index import HealthIndexModel
from ipis.module2_pdm.rul.similarity import SimilarityRUL
from ipis.module2_pdm.serving.loader import PdMArtifact, load_artifact, save_artifact
from ipis.module2_pdm.serving.service import PdMService
from ipis.shared.state_bus import HealthFlag, OperationalState

INTERVAL = 10.0
N_FEAT = 5


def build_artifact(seed: int = 0) -> PdMArtifact:
    """Synthetic artifact: T^2 model on healthy data + 3 run-to-failure arcs."""
    rng = np.random.default_rng(seed)
    healthy = rng.standard_normal((200, N_FEAT))
    hm = HealthIndexModel.fit(
        healthy, tuple(f"v{i}" for i in range(N_FEAT)), warn_q=0.95, alarm_q=0.99
    )
    library = []
    for k in range(3):
        n = 180 + 20 * k
        di = np.exp(np.linspace(np.log(5.0), np.log(500.0 + 100.0 * k), n))  # rising
        hi = np.log1p(np.maximum.accumulate(di))
        rul = np.linspace(n * INTERVAL, 0.0, n)  # countdown in seconds
        library.append((hi, rul))
    sim = SimilarityRUL(library=library, interval=INTERVAL, mode="phase")
    # larger alpha so the EMA responds within a short synthetic run
    return PdMArtifact(health_model=hm, similarity=sim, conformal_delta_hours=0.2, ema_alpha=0.3)


def _run_degrading(svc: PdMService, eid: str, seed: int = 1) -> list[dict]:
    rng = np.random.default_rng(seed)
    records = []
    for _ in range(30):  # healthy plateau
        records.append(svc.observe(eid, rng.standard_normal(N_FEAT)))
    for i in range(90):  # ramp the mean up -> T^2 climbs through warn then alarm
        records.append(svc.observe(eid, rng.standard_normal(N_FEAT) + 0.12 * i))
    return records


def test_health_score_falls_over_degradation():
    svc = PdMService(build_artifact())
    recs = _run_degrading(svc, "pump_P101")
    assert recs[-1]["health_score"] < recs[0]["health_score"]
    assert recs[0]["health_score"] > 0.9  # starts healthy
    assert recs[-1]["health_score"] < 0.2  # ends degraded


def test_flag_escalates_ok_warn_alarm():
    svc = PdMService(build_artifact())
    recs = _run_degrading(svc, "pump_P101")
    flags = [r["flag"] for r in recs]
    assert flags[0] == HealthFlag.OK
    assert HealthFlag.WARN in flags
    assert HealthFlag.ALARM in flags
    assert flags[-1] == HealthFlag.ALARM
    # OK must precede the first ALARM
    assert flags.index(HealthFlag.OK) < flags.index(HealthFlag.ALARM)


def test_rul_absent_before_fpt_then_present():
    svc = PdMService(build_artifact())
    recs = _run_degrading(svc, "pump_P101")
    assert recs[0]["fpt"] is None and recs[0]["rul_hours"] is None  # healthy: no RUL
    with_rul = [r for r in recs if r["rul_hours"] is not None]
    assert with_rul, "RUL should appear once past FPT"
    assert all(r["fpt"] is not None for r in with_rul)
    assert all(r["rul_hours"] >= 0.0 for r in with_rul)


def test_rul_is_bounded_and_trends_down_toward_eol():
    svc = PdMService(build_artifact())
    recs = _run_degrading(svc, "pump_P101")
    ruls = [r["rul_hours"] for r in recs if r["rul_hours"] is not None]
    assert len(ruls) >= 5
    max_life_h = max(float(rul[0]) for _, rul in svc.similarity._lib) / 3600.0
    assert max(ruls) > 0.0  # a positive RUL is produced
    assert all(0.0 <= r <= max_life_h + 1e-9 for r in ruls)  # never exceeds longest ref life
    n = len(ruls)
    # RUL trends downward as the asset approaches failure (early window > late window)
    assert np.mean(ruls[: n // 3]) > np.mean(ruls[2 * n // 3 :])


def test_operational_state_fields_and_object():
    svc = PdMService(build_artifact())
    _run_degrading(svc, "pump_P101")
    fields = svc.operational_state_fields()
    assert "pump_P101" in fields["equipment_health"]
    assert "pump_P101" in fields["health_flags"]
    assert "pump_P101" in fields["remaining_useful_life"]  # past FPT by end of run

    state = svc.build_operational_state(sequence_id=42)
    assert isinstance(state, OperationalState)
    assert state.sequence_id == 42
    assert state.equipment_health["pump_P101"] < 0.2
    assert state.module_status["m2"].module_id == "m2"


def test_multiple_equipment_tracked_independently():
    svc = PdMService(build_artifact())
    rng = np.random.default_rng(7)
    for _ in range(40):
        svc.observe("healthy_pump", rng.standard_normal(N_FEAT))  # stays healthy
    _run_degrading(svc, "failing_pump")
    fields = svc.operational_state_fields()
    assert fields["health_flags"]["healthy_pump"] == HealthFlag.OK
    assert fields["health_flags"]["failing_pump"] == HealthFlag.ALARM
    assert "healthy_pump" not in fields["remaining_useful_life"]  # no FPT -> no RUL
    assert "failing_pump" in fields["remaining_useful_life"]


def test_wrong_feature_count_raises():
    svc = PdMService(build_artifact())
    try:
        svc.observe("pump", [1.0, 2.0])  # expects 5
    except ValueError:
        return
    raise AssertionError("expected ValueError on wrong feature count")


def test_artifact_round_trip(tmp_path):
    art = build_artifact()
    p = save_artifact(art, tmp_path / "pdm.json")
    loaded = load_artifact(p)
    x = np.array([0.3, -0.2, 0.5, 0.1, -0.4])
    # reconstructed health model reproduces T^2 exactly
    assert loaded.health_model.t2(x) == art.health_model.t2(x)
    assert loaded.similarity.interval == art.similarity.interval
    assert loaded.conformal_delta_hours == art.conformal_delta_hours
    # full pipeline behaves the same on the loaded artifact
    svc0, svc1 = PdMService(art), PdMService(loaded)
    r0 = _run_degrading(svc0, "p")[-1]
    r1 = _run_degrading(svc1, "p")[-1]
    assert r0["flag"] == r1["flag"]
    assert r0["rul_hours"] == r1["rul_hours"]


def test_state_snapshot_round_trip(tmp_path):
    svc = PdMService(build_artifact())
    _run_degrading(svc, "pump_P101")
    before = svc.operational_state_fields()
    svc.save_state(tmp_path / "state.pkl")

    svc2 = PdMService(build_artifact())
    svc2.load_state(tmp_path / "state.pkl")
    after = svc2.operational_state_fields()
    assert after["equipment_health"] == before["equipment_health"]
    assert after["remaining_useful_life"] == before["remaining_useful_life"]
