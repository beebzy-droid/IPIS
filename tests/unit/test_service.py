"""Unit tests for ipis.module1_soft_sensor.serving.service.SoftSensorService.

Cover the soft-sensor-specific behaviours: the bias-update converges to a model
offset, ACI holds coverage online, the delayed-label coverage indicator uses the
*stored* interval (not the current one), drift fires on an injected shift, and the
pickle snapshot round-trips exactly.
"""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module1_soft_sensor.evaluation.drift import CUSUM, make_adwin
from ipis.module1_soft_sensor.serving.service import SoftSensorService

ALPHA = 0.10


def _linear_model(coef: float = 3.0, intercept: float = 0.0):
    """A trivial point model: y_hat = intercept + coef * x[:, 0]."""

    def predict(x: np.ndarray) -> np.ndarray:
        x = np.atleast_2d(np.asarray(x, float))
        return intercept + coef * x[:, 0]

    return predict


def _service(init_resid, **kw):
    return SoftSensorService(_linear_model(), init_residuals=init_resid, alpha=ALPHA, **kw)


# --------------------------------------------------------------------------- #
# predict shape / id handling                                                 #
# --------------------------------------------------------------------------- #
def test_predict_single_returns_dict_with_interval():
    rng = np.random.default_rng(0)
    svc = _service(rng.normal(0, 1, 200))
    out = svc.predict(np.array([1.0]))
    assert set(out) >= {"sample_id", "y_pred_raw", "y_pred", "lower", "upper", "bias", "alpha_t"}
    assert out["lower"] <= out["y_pred"] <= out["upper"]
    assert out["y_pred_raw"] == pytest.approx(3.0)  # 3 * 1.0
    assert svc.n_predict == 1


def test_predict_batch_returns_list_and_assigns_ids():
    rng = np.random.default_rng(1)
    svc = _service(rng.normal(0, 1, 200))
    rows = svc.predict(np.array([[1.0], [2.0], [3.0]]))
    assert isinstance(rows, list) and len(rows) == 3
    assert [r["sample_id"] for r in rows] == ["0", "1", "2"]
    assert rows[1]["y_pred_raw"] == pytest.approx(6.0)
    assert svc.n_predict == 3


def test_explicit_ids_and_mismatch_raises():
    rng = np.random.default_rng(2)
    svc = _service(rng.normal(0, 1, 100))
    svc.predict(np.array([1.0]), sample_id="abc")
    assert "abc" in svc.buffer
    with pytest.raises(ValueError, match="ids for"):
        svc.predict(np.array([[1.0], [2.0]]), sample_id=["only-one"])


# --------------------------------------------------------------------------- #
# bias-update                                                                 #
# --------------------------------------------------------------------------- #
def test_bias_converges_to_constant_model_offset():
    # Model under-predicts truth by a constant 5.0; b_t should approach +5.0.
    rng = np.random.default_rng(3)
    svc = _service(rng.normal(0, 0.5, 200), lam=0.3)
    for k in range(400):
        sid = f"s{k}"
        out = svc.predict(np.array([1.0]), sample_id=sid)
        y_true = out["y_pred_raw"] + 5.0  # truth = raw + 5
        svc.label(sid, y_true)
    assert svc.b == pytest.approx(5.0, abs=0.2)


def test_label_unknown_id_raises():
    rng = np.random.default_rng(4)
    svc = _service(rng.normal(0, 1, 100))
    with pytest.raises(KeyError, match="not in buffer"):
        svc.label("never-predicted", 1.0)


def test_label_consumes_buffer_entry():
    rng = np.random.default_rng(5)
    svc = _service(rng.normal(0, 1, 100))
    svc.predict(np.array([1.0]), sample_id="x")
    svc.label("x", 3.0)
    assert "x" not in svc.buffer  # popped on label
    with pytest.raises(KeyError):
        svc.label("x", 3.0)  # cannot double-label


# --------------------------------------------------------------------------- #
# delayed-label correctness (the subtle one)                                  #
# --------------------------------------------------------------------------- #
def test_delayed_label_uses_stored_interval_not_current():
    # Emit an interval for s0, then drive alpha_t far via many other labels so the
    # CURRENT halfwidth differs from s0's. The coverage decision for s0 must use the
    # interval stored at its predict time.
    rng = np.random.default_rng(6)
    svc = _service(rng.normal(0, 1.0, 300), gamma=0.2, window=100)
    first = svc.predict(np.array([0.0]), sample_id="s0")
    lo0, hi0 = first["lower"], first["upper"]
    # advance state with unrelated samples + labels
    for k in range(150):
        sid = f"k{k}"
        svc.predict(np.array([0.0]), sample_id=sid)
        svc.label(sid, float(rng.normal(0, 1.0)))
    # a y_true that is inside the STORED s0 interval but we verify against stored bounds
    y0 = (lo0 + hi0) / 2.0
    res = svc.label("s0", y0)
    assert res["covered"] is True
    # and a clearly-outside value would be uncovered regardless of current width
    svc2 = _service(rng.normal(0, 1.0, 300))
    f2 = svc2.predict(np.array([0.0]), sample_id="s0")
    res2 = svc2.label("s0", f2["upper"] + 100.0)
    assert res2["covered"] is False


# --------------------------------------------------------------------------- #
# ACI coverage online                                                         #
# --------------------------------------------------------------------------- #
def test_aci_holds_coverage_online_immediate_labels():
    # Stream: model is unbiased, homoscedastic noise; coverage should land ~0.90.
    rng = np.random.default_rng(7)
    cal = rng.normal(0, 1.0, 500)
    svc = _service(cal, lam=0.3, gamma=0.05, window=300)
    for k in range(3000):
        sid = f"t{k}"
        out = svc.predict(np.array([1.0]), sample_id=sid)
        y_true = out["y_pred_raw"] + rng.normal(0, 1.0)
        svc.label(sid, y_true)
    assert 0.86 <= svc.rolling_coverage() <= 0.94


# --------------------------------------------------------------------------- #
# drift detector wiring                                                       #
# --------------------------------------------------------------------------- #
def test_drift_flag_fires_on_injected_shift_adwin():
    # drift_on="raw": the detector sees the un-corrected residual, so a mean shift is
    # visible even though the bias-update would otherwise absorb it (that masking is
    # exactly why drift_on="corrected" alarms only when the correction can't keep up).
    rng = np.random.default_rng(8)
    svc = _service(
        rng.normal(0, 1.0, 300), drift_detector=make_adwin(delta=0.002), drift_on="raw", lam=1.0
    )
    fired = False
    for k in range(600):
        sid = f"d{k}"
        out = svc.predict(np.array([1.0]), sample_id=sid)
        shift = 0.0 if k < 300 else 8.0  # large mean shift in the residual stream
        svc.label(sid, out["y_pred_raw"] + shift + rng.normal(0, 0.3))
        fired = fired or svc.last_drift_flag
    assert fired


def test_no_detector_means_flag_stays_false():
    rng = np.random.default_rng(9)
    svc = _service(rng.normal(0, 1.0, 200), drift_detector=None)
    for k in range(100):
        sid = f"n{k}"
        out = svc.predict(np.array([1.0]), sample_id=sid)
        svc.label(sid, out["y_pred_raw"] + 50.0)
    assert svc.last_drift_flag is False


# --------------------------------------------------------------------------- #
# snapshot round-trip                                                         #
# --------------------------------------------------------------------------- #
def test_snapshot_roundtrip_restores_state_and_continues_identically(tmp_path):
    rng = np.random.default_rng(10)
    cal = rng.normal(0, 1.0, 200)
    snap = tmp_path / "state.pkl"

    a = _service(cal, drift_detector=CUSUM(k=0.5, h=5.0), lam=0.3, gamma=0.05, window=100)
    stream = [(f"s{k}", float(rng.normal(0, 1.0))) for k in range(200)]
    for sid, noise in stream:
        out = a.predict(np.array([1.0]), sample_id=sid)
        a.label(sid, out["y_pred_raw"] + noise)
    a.save_snapshot(snap)

    # fresh service (model re-supplied), restore mutable state
    b = _service(cal, drift_detector=CUSUM(k=0.5, h=5.0), lam=0.3, gamma=0.05, window=100)
    b.load_snapshot(snap)
    assert b.b == pytest.approx(a.b)
    assert b.aci.alpha_t == pytest.approx(a.aci.alpha_t)
    assert b.n_label == a.n_label and b.n_predict == a.n_predict
    assert b.rolling_coverage() == pytest.approx(a.rolling_coverage())

    # continued predictions match bit-for-bit
    pa = a.predict(np.array([1.5]), sample_id="next")
    pb = b.predict(np.array([1.5]), sample_id="next")
    assert pa["y_pred"] == pytest.approx(pb["y_pred"])
    assert pa["lower"] == pytest.approx(pb["lower"])
    assert pa["upper"] == pytest.approx(pb["upper"])


def test_metrics_is_json_shaped():
    rng = np.random.default_rng(11)
    svc = _service(rng.normal(0, 1.0, 100))
    svc.predict(np.array([1.0]), sample_id="m0")
    svc.label("m0", 3.2)
    m = svc.metrics()
    assert set(m) >= {"bias", "alpha_t", "rolling_coverage", "n_predict", "n_label", "params"}
    assert isinstance(m["params"], dict)


def test_param_validation():
    rng = np.random.default_rng(12)
    with pytest.raises(ValueError, match="lam"):
        _service(rng.normal(0, 1, 50), lam=1.5)
    with pytest.raises(ValueError, match="delay"):
        _service(rng.normal(0, 1, 50), delay=-1)
    with pytest.raises(ValueError, match="drift_on"):
        _service(rng.normal(0, 1, 50), drift_on="bogus")
