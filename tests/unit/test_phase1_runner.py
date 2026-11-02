"""Unit tests for the N1 Phase 1 runner (``ipis.module1_soft_sensor.phase1``).

Inputs: a 2-h run of the extended generator outside the study (``tests/fixtures/
tep_mode2_stream3000_2h_60s.csv``: ``generate_tep_modes.generate("mode2", stream=3000, hours=2,
record_s=60)``, SHA-256 8a75ddd2...), which fixes the conventions the data module assumes; TEP-like
files written with those conventions (60-s rows, the generator's time column, XMEAS(40) held in
15-row blocks from minute 15k + 1); a debutanizer-like file; and AR(1) residual streams. They check
the data handling, the runner's loops and replay against the frozen library, the rules against
hand-computed cases, the records, the two stages end to end (stage B stopping when its
calibration rows differ from stage A's), the decided rules against an independent computation
from the frozen library, and the command line.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

from ipis.module1_soft_sensor.evaluation import baselines as b
from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.phase1 import data as dat
from ipis.module1_soft_sensor.phase1 import loops as lp
from ipis.module1_soft_sensor.phase1 import metrics as mt
from ipis.module1_soft_sensor.phase1 import models as pm
from ipis.module1_soft_sensor.phase1 import record as rc
from ipis.module1_soft_sensor.phase1 import rules
from ipis.module1_soft_sensor.phase1 import stages as st
from ipis.module1_soft_sensor.phase1 import verdicts as vd

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "phase1_precheck.py"
_spec = importlib.util.spec_from_file_location("phase1_precheck", _SCRIPT)
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


def _ar1(phi: float, n: int, rng: np.random.Generator) -> np.ndarray:
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + math.sqrt(1.0 - phi * phi) * e[t]
    return x


# --- data ---------------------------------------------------------------------------------


def _tep_csv(path: Path, seed: int, shift_min: int = 0, time_offset_s: float = -1.0) -> Path:
    """6000 rows as generate_tep_modes.py --record-s 60 writes them: the time column reads
    (60 (i + 1) - 1) s in hours; XMEAS(40) takes a new value at minute 15k + 1 (+ shift_min)."""
    rng = np.random.default_rng(seed)
    n = 6000
    drivers = np.column_stack([_ar1(p, n, rng) for p in (0.999, 0.99, 0.95)])
    X = drivers @ rng.normal(size=(3, 34)) + 0.3 * rng.standard_normal((n, 34)) + 50.0
    comp = 40.0 + drivers @ rng.normal(size=3)
    y = np.empty(n)
    minute = np.arange(1, n + 1)
    k = np.maximum((minute - 1 - shift_min) // 15, 0)
    sample = np.maximum(15 * (k - 1), 0)
    y[:] = comp[sample] + 0.5 * rng.standard_normal(k.max() + 1)[k]
    data = np.zeros((n, 54))
    data[:, 0] = (60.0 * minute + time_offset_s) / 3600.0
    data[:, 1:23] = X[:, :22]
    data[:, 23:40] = rng.normal(30, 5, size=(n, 17))
    data[:, 40] = y
    data[:, 41] = 1.0
    data[:, 42:54] = X[:, 22:]
    lines = [f"{row[0]:12.5f}," + ",".join(f"{v:15.7E}" for v in row[1:]) for row in data]
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.fixture(scope="module")
def tep_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _tep_csv(tmp_path_factory.mktemp("tep") / "run.csv", 1)


def test_tep_rows_and_segments(tep_file: Path) -> None:
    a = dat.load_tep_rows(tep_file, "A")
    full = dat.load_tep_rows(tep_file, "B")
    assert a.shape == (4200, 54) and full.shape == (6000, 54)
    np.testing.assert_array_equal(a, full[:4200])
    t1a, t1 = dat.arm_rows(a, dat.ARMS["T1"]), dat.arm_rows(full, dat.ARMS["T1"])
    assert (t1a.n_train, t1a.n_cal, t1a.n_ev) == (600, 800, 0)
    assert (t1.n_train, t1.n_cal, t1.n_ev) == (600, 800, 600)
    np.testing.assert_array_equal(t1.minute, np.arange(3, 6001, 3))
    t2 = dat.arm_rows(full, dat.ARMS["T2"])
    assert (t2.n_train, t2.n_cal, t2.n_ev) == (1800, 2400, 1800)
    assert t1.X.shape == (2000, 34) and t2.y.shape == (6000,)
    np.testing.assert_array_equal(t1.y, full[2::3, 40])


def test_label_hold_and_t3_rows(tep_file: Path) -> None:
    full = dat.load_tep_rows(tep_file, "B")
    t1, t2 = dat.arm_rows(full, dat.ARMS["T1"]), dat.arm_rows(full, dat.ARMS["T2"])
    h1, h2 = dat.label_hold(t1), dat.label_hold(t2)
    assert (h1["rows_per_block"], h1["blocks"], h1["first_block_row"]) == (5, 400, 0)
    assert (h2["rows_per_block"], h2["blocks"]) == (15, 400)
    assert h1["share_new_value_at_block_start"] == 1.0
    idx = dat.t3_rows(t1.minute)
    np.testing.assert_array_equal(idx, np.arange(5, 2000, 5))
    assert np.all(t1.minute[idx] % 15 == 3)
    # the T1 row of each event shows a value that differs from the row before it
    assert np.all(t1.y[idx] != t1.y[idx - 1])
    ev = idx[idx >= t1.n_train]
    assert int(np.sum(ev < t1.n_train + t1.n_cal)) == 160 and int(np.sum(ev >= 1400)) == 120


def test_label_hold_rejects_another_phase(tmp_path: Path) -> None:
    shifted = dat.load_tep_rows(_tep_csv(tmp_path / "s3.csv", 2, shift_min=3), "B")
    with pytest.raises(ValueError, match="held"):
        dat.label_hold(dat.arm_rows(shifted, dat.ARMS["T1"]))
    shifted1 = dat.load_tep_rows(_tep_csv(tmp_path / "s1.csv", 2, shift_min=1), "B")
    with pytest.raises(ValueError, match="held"):
        dat.label_hold(dat.arm_rows(shifted1, dat.ARMS["T2"]))


def test_time_column_is_checked(tmp_path: Path) -> None:
    bad = _tep_csv(tmp_path / "bad.csv", 3, time_offset_s=-30.0)
    with pytest.raises(ValueError, match="time column"):
        dat.load_tep_rows(bad, "A")


_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tep_mode2_stream3000_2h_60s.csv"


def test_generator_conventions_on_a_real_run() -> None:
    """The conventions ``data`` assumes, on the generator's own output (a run outside the study):
    the time column, the 15-row hold from minute 15k + 1, the T1 blocks from row 5k, and new
    values at the T3 rows."""
    d60 = np.loadtxt(_FIXTURE, delimiter=",")
    assert d60.shape == (120, 54)
    assert np.max(np.abs(d60[:, 0] - dat.tep_time_column(120))) < dat.TIME_TOL_H
    minute = np.arange(1, 121)
    changes = minute[1:][np.diff(d60[:, dat.TEP_Y_COLUMN]) != 0]
    np.testing.assert_array_equal(changes, np.arange(16, 121, 15))  # minute 15k + 1
    t1, t2 = dat.arm_rows(d60, dat.ARMS["T1"]), dat.arm_rows(d60, dat.ARMS["T2"])
    assert dat.label_hold(t1)["blocks"] == 8 and dat.label_hold(t2)["blocks"] == 8
    assert dat.label_hold(t1)["share_new_value_at_block_start"] == 1.0
    idx = dat.t3_rows(t1.minute)
    np.testing.assert_array_equal(idx, np.arange(5, 40, 5))
    assert np.all(t1.y[idx] != t1.y[idx - 1])
    assert np.all(t1.y[idx + 4] == t1.y[idx])  # held for the block's five rows


def test_tep_files_checks_hashes(tmp_path: Path) -> None:
    chosen = {"mode1": [1, 4, 7, 10, 13], "mode2": [2, 5, 8, 11, 14], "mode3": [3, 6, 9, 12, 15]}
    log = []
    src = _tep_csv(tmp_path / "src.csv", 4)
    for regime, streams in chosen.items():
        for s in streams:
            path = tmp_path / dat.tep_file_name(regime, s)
            path.write_bytes(src.read_bytes() + str(s).encode())
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            log.append({"stream": s, regime: {"csv_sha256": sha}})
    record = tmp_path / "record.json"
    record.write_text(
        json.dumps({"_meta": {"hours": 100, "record_s": 60}, "chosen": chosen, "log": log})
    )
    files = dat.tep_files(tmp_path, record)
    assert [(f.regime, f.stream) for f in files][:2] == [("mode1", 1), ("mode1", 4)]
    (tmp_path / dat.tep_file_name("mode2", 5)).write_bytes(b"changed")
    with pytest.raises(ValueError, match="SHA-256"):
        dat.tep_files(tmp_path, record)


@pytest.mark.slow
def test_tep_units_at_full_size(tmp_path: Path) -> None:
    """The 15 runs loaded for every TEP unit, in both stages: stage A sees calibration rows only,
    and stage B reproduces them bit for bit."""
    chosen = {
        "mode1": [19, 31, 49, 55, 76],
        "mode2": [5, 11, 14, 20, 23],
        "mode3": [3, 6, 9, 18, 24],
    }
    log = []
    for regime, streams in chosen.items():
        for s in streams:
            path = _tep_csv(tmp_path / dat.tep_file_name(regime, s), 100 + s)
            log.append({"stream": s, regime: {"csv_sha256": dat.sha256_file(path)}})
    record = tmp_path / "record.json"
    record.write_text(
        json.dumps({"_meta": {"hours": 100, "record_s": 60}, "chosen": chosen, "log": log})
    )
    names = ("T1", "T2", "T3", "T1_gb")
    stage_a = st.tep_units(tmp_path, record, "A", names, st._serial)
    stage_b = st.tep_units(tmp_path, record, "B", names, st._serial)
    sizes = {u.name: (u.streams[0].n_cal, u.streams[0].n_ev, u.run_length) for u in stage_b}
    assert sizes == {
        "T1": (800, 600, 1400),
        "T2": (2400, 1800, 4200),
        "T3": (160, 120, 280),
        "T1_gb": (800, 600, 1400),
    }
    assert [u.baselines for u in stage_b] == [True, False, False, False]
    assert [u.thetas for u in stage_b] == [(0, 2, 4), (0, 4, 14), (0,), (0, 2, 4)]
    assert [u.window for u in stage_b] == [200, 200, 40, 200]
    for ua, ub in zip(stage_a, stage_b, strict=True):
        assert [s.key for s in ua.streams] == [s.key for s in ub.streams]
        assert len(ua.plants()) == 3 and all(len(v) == 5 for v in ua.plants().values())
        for sa, sb in zip(ua.streams, ub.streams, strict=True):
            assert sa.n_ev == 0 and sa.r.size == sa.n_cal == sb.n_cal
            np.testing.assert_array_equal(sa.r, sb.r[: sa.n_cal])
            np.testing.assert_array_equal(sa.y, sb.y[: sa.n_cal])
            assert sa.info["model"].get("alpha") == sb.info["model"].get("alpha")
    t1, t2, t3 = stage_b[0], stage_b[1], stage_b[2]
    for s1, s2, s3 in zip(t1.streams, t2.streams, t3.streams, strict=True):
        np.testing.assert_array_equal(s3.r, s1.r[::5])  # events at T1 rows 600, 605, ...
        # one point model for every arm: T1's rows are every third T2 row (Section 7)
        np.testing.assert_allclose(s2.r[2::3], s1.r, rtol=0, atol=1e-12)
        assert s2.info["model"]["alpha"] == s1.info["model"]["alpha"]
        assert s2.info["model"]["lag"] == 15 and s1.info["model"]["lag"] == 5
        assert s1.info["model"]["label_hold"]["blocks"] == 400
        assert s2.info["model"]["label_hold"]["blocks"] == 400


def _debutanizer_file(path: Path, seed: int = 7) -> Path:
    """2394 rows in the loader's format; u5 drives y at lag 15 with persistent residuals."""
    rng = np.random.default_rng(seed)
    n, lag = 2394, 15
    u = np.column_stack([_ar1(0.98, n, rng) for _ in range(7)])
    y = np.zeros(n)
    y[lag:] = -0.7 * u[:-lag, 4] + 0.5 * _ar1(0.95, n, rng)[lag:]
    data = np.column_stack([u, y])
    data = (data - data.min(axis=0)) / (data.max(axis=0) - data.min(axis=0))
    with path.open("w") as f:
        f.write("u1 u2 u3 u4 u5 u6 u7 y\n\n")
        for row in data:
            f.write("  ".join(f"{v:.7e}" for v in row) + "\n")
    return path


def test_debutanizer_unit_matches_the_precheck(tmp_path: Path) -> None:
    path = _debutanizer_file(tmp_path / "deb.txt")
    pre = {"debutanizer": pc.debutanizer(path, 15.0, lag=15)}
    a = st.debutanizer_unit(path, "A", pre)
    full = st.debutanizer_unit(path, "B", pre)
    sa, sb = a.streams[0], full.streams[0]
    assert (sa.n_cal, sa.n_ev, sa.r.size) == (1660, 0, 1660)
    assert (sb.n_cal, sb.n_ev, sb.r.size) == (1660, 719, 2379)
    assert a.run_length == full.run_length == 2379
    np.testing.assert_array_equal(sa.r, sb.r[:1660])
    assert sa.info["precheck"]["residual_acf_max_abs_diff"] < 1e-12
    pre["debutanizer"]["point_model"]["slope"] *= 1.001
    with pytest.raises(ValueError, match="pre-check"):
        st.debutanizer_unit(path, "A", pre)


def test_stage_a_never_parses_debutanizer_evaluation_rows(tmp_path: Path) -> None:
    """Stage A's unit, everything ``stage_a`` computes from, is the same whatever rows 1675 on
    hold, even text that does not parse; stage B, which reads them, stops on such text."""
    path = _debutanizer_file(tmp_path / "deb.txt")
    pre = {"debutanizer": pc.debutanizer(path, 15.0, lag=15)}
    lines = path.read_text().splitlines(keepends=True)
    first = next(i for i, line in enumerate(lines) if line[:1].isdigit())
    broken = tmp_path / "broken.txt"
    broken.write_text("".join(lines[: first + 1675]) + "not a number\n" * 719)
    a, b_ = (st.debutanizer_unit(p, "A", pre) for p in (path, broken))
    sa, sb = a.streams[0], b_.streams[0]
    np.testing.assert_array_equal(sa.r, sb.r)
    np.testing.assert_array_equal(sa.y, sb.y)
    assert (sa.n_cal, sa.n_ev, sa.info) == (sb.n_cal, sb.n_ev, sb.info)
    assert (a.thetas, a.window, a.run_length) == (b_.thetas, b_.window, b_.run_length)
    assert a.inputs["sha256"] != b_.inputs["sha256"]  # the files differ, and the record says so
    with pytest.raises(ValueError):
        st.debutanizer_unit(broken, "B", pre)
    short = tmp_path / "short.txt"
    short.write_text("".join(lines[: first + 2000]))
    with pytest.raises(ValueError, match="2394"):
        st.debutanizer_unit(short, "A", pre)


# --- models -------------------------------------------------------------------------------


def test_staged_residuals_reproduce_the_first_call() -> None:
    rng = np.random.default_rng(5)
    X = rng.standard_normal((2000, 34))
    y = X @ rng.standard_normal(34) + rng.standard_normal(2000)
    model = pm.fit_ridge_one_se(X, y, 5, 600)
    staged = model.staged_residuals(X, y, 1400)
    np.testing.assert_array_equal(staged[:1400], model.residuals(X[:1400], y[:1400]))
    np.testing.assert_allclose(staged, model.residuals(X, y), rtol=0, atol=1e-12)
    assert np.isnan(staged[:5]).all() and np.isfinite(staged[5:]).all()


def test_ridge_one_se_rule() -> None:
    rng = np.random.default_rng(6)
    X = rng.standard_normal((600, 34))
    y = X[:, :3] @ np.array([1.0, -0.5, 0.2]) + 0.5 * rng.standard_normal(600)
    info = pm.fit_ridge_one_se(X, y, 5, 600).info
    mean, se = np.array(info["cv_mean_mse"]), np.array(info["cv_se"])
    best = int(np.argmin(mean))
    within = [i for i in range(len(mean)) if mean[i] <= mean[best] + se[best]]
    assert info["alpha"] == pm.RIDGE_ALPHAS[max(within)]
    assert info["alpha_min_mse"] == pm.RIDGE_ALPHAS[best]
    assert info["n_train_pairs"] == 595


# --- loops --------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scores() -> list[tuple[np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(11)
    return [(np.abs(x[200:]), np.abs(x[:200])) for x in (_ar1(0.9, 800, rng) for _ in range(3))]


@pytest.mark.parametrize("loop", ["sequential", "smith", "phase"])
def test_replay_tune_is_the_library_replay(scores: list, loop: str) -> None:
    y_range = 6.0
    for theta in (0, 4):
        ours = lp.replay_tune(
            scores, theta, loop=loop, y_range=y_range, eps=0.005, alpha=0.1, window=200
        )
        lib = d.replay_tune_pooled(scores, theta, y_range=y_range, eps=0.005, loop=loop)
        assert ours == lib


def test_projected_replay_uses_the_bounds(scores: list) -> None:
    out = lp.replay_tune(scores, 4, loop="projected", y_range=6.0, eps=0.01, alpha=0.1, window=200)
    for g, share in out["path"]:
        flags = [
            d.uninformative(
                d.run_delayed_aci(
                    s, 4, init_scores=i, gamma=g, loop="projected", bounds=lp.PROJECTED_BOUNDS
                )["h"],
                6.0,
            )
            for s, i in scores
        ]
        assert share == float(np.mean(np.concatenate(flags)))


@pytest.mark.parametrize("pairing", ["stored", "arrival"])
def test_decaying_loop_with_exponent_zero_is_sequential(scores: list, pairing: str) -> None:
    s, init = scores[0]
    ours = lp.run_decaying(
        s, 3, init_scores=init, alpha=0.1, c=0.02, window=200, pairing=pairing, exponent=0.0
    )
    lib = d.run_delayed_aci(s, 3, init_scores=init, gamma=0.02, window=200, pairing=pairing)
    for k in ("h", "covered", "alpha"):
        np.testing.assert_array_equal(ours[k], lib[k])


def test_decaying_step_schedule() -> None:
    s = np.array([5.0, 0.1, 0.1, 5.0, 0.1])
    init = np.linspace(0.5, 1.5, 20)
    out = lp.run_decaying(s, 0, init_scores=init, alpha=0.1, c=0.3, window=20)
    level = [0.1]
    for n, e in enumerate((~out["covered"]).astype(float)[:-1], start=1):
        level.append(level[-1] + 0.3 * n**-0.6 * (0.1 - e))
    np.testing.assert_allclose(out["alpha"], level, rtol=0, atol=1e-15)


def test_static_loop() -> None:
    cal = np.arange(1.0, 101.0)
    out = lp.run_static(cal, np.array([50.0, 95.0, 91.0]), 0.1)
    assert out["h"].tolist() == [91.0] * 3
    assert out["covered"].tolist() == [True, False, True]


# --- metrics ------------------------------------------------------------------------------


def test_interval_metrics() -> None:
    width = np.array([1.0, np.inf, 3.0, 0.5] * 50)
    covered = np.array([True, True, False, True] * 50)
    m = mt.interval_metrics(width, covered, 2.0, np.full(200, 0.1))
    assert m["u"] == 0.5 and m["infinite_share"] == 0.25 and m["coverage"] == 0.75
    assert m["covered_count"] == 150 and m["n"] == 200
    assert m["f7_median_width"] == 2.0  # median over all intervals, inf counted as widest
    assert m["width_median"] == 1.0  # median over finite intervals
    assert m["under_coverage_steps"] == 101 and m["local_cov_min"] == pytest.approx(0.75)
    assert m["alpha_sd"] == 0.0


def test_persistence() -> None:
    err = np.array([0, 1, 1, 0, 1, 1, 1, 0, 0, 0], dtype=float)
    assert mt.mean_miss_run(err) == 2.5
    assert mt.persistence(np.zeros(20)) == {"acf1": 0.0, "mean_miss_run": 0.0, "iact": 1.0}


# --- rules --------------------------------------------------------------------------------


def test_t_interval() -> None:
    x = [0.02, 0.01, 0.03, 0.015, 0.025]
    ci = rules.t_interval(x, 0.975)
    from scipy import stats

    half = stats.t.ppf(0.9875, 4) * np.std(x, ddof=1) / math.sqrt(5)
    assert ci["mean"] == pytest.approx(0.02) and ci["lo"] == pytest.approx(0.02 - half)
    assert rules.t_interval([0.1, 0.1], 0.95)["lo"] == pytest.approx(0.1)
    assert math.isnan(rules.t_interval([1.0, np.inf], 0.95)["lo"])


def test_f2_and_f3() -> None:
    shows = rules.f2_tep([0.03, 0.02, 0.04, 0.03, 0.02], [0.0] * 5)
    assert shows["shows_increase"]
    assert not rules.f2_tep([0.009] * 5, [0.0] * 5)["shows_increase"]  # below 1 point
    assert not rules.f2_tep([0.05, -0.04, 0.05, -0.04, 0.03], [0.0] * 5)["shows_increase"]
    assert rules.f2_verdict({"a": False, "b": False})["fires"]
    v = rules.f2_verdict({"a": True, "b": False})
    assert not v["fires"] and v["restricted_to"] == "a"
    assert rules.f3(900, 1000)["nominal_outside"] is False
    assert rules.f3(860, 1000)["nominal_outside"] is True


def test_f2_debutanizer_needs_eight_blocks() -> None:
    rng = np.random.default_rng(3)
    u0 = np.zeros(719)
    u3 = (rng.uniform(size=719) < 0.05).astype(float)
    out = rules.f2_debutanizer(u3, u0)
    assert out["ci975"]["blocks"] >= 8 and out["shows_increase"]
    step = np.r_[np.zeros(400), np.ones(319)]  # IACT about 92: a block of 184, 3 blocks fit
    out = rules.f2_debutanizer(step, u0)
    assert out["ci975"]["blocks"] < 8 and out["descriptive"] and not out["shows_increase"]


def test_f5_f6_boundaries() -> None:
    assert not rules.f5([0.02] * 15, 0.01)["fires"]
    assert rules.f5([0.0201] * 15, 0.01)["fires"]
    assert not rules.f6([1.1] * 15, [1.0] * 15)["fires"]
    assert rules.f6([1.11] * 15, [1.0] * 15)["fires"]


def test_f8() -> None:
    pred = [0.8] * 15
    below = rules.f8(pred, [5.0] * 15, [7.0 + 0.1 * k for k in range(15)], [0.02] * 3, [0.01] * 3)
    assert below["tested"] and not below["fires"] and below["step_statement_made"]
    same = rules.f8(pred, [7.0] * 15, [7.0] * 15, [0.02, 0.02, 0.01], [0.01] * 3)
    assert same["fires"] and not same["step_statement_made"]
    ungated = rules.f8([0.96] * 15, [7.0] * 15, [7.0] * 15, [0.02] * 3, [0.01] * 3)
    assert not ungated["tested"] and not ungated["fires"]
    mixed = rules.f8(pred, [5.0] * 15, [7.0] * 15, [0.02, 0.02, 0.005], [0.01] * 3)
    assert not mixed["step_condition"]


def _runs(width: float, cov: float, u: float = 0.0, n: int = 600) -> list[dict]:
    return [{"f7_median_width": width, "coverage": cov, "u": u, "n": n} for _ in range(15)]


def test_f7_compare() -> None:
    cal = [np.abs(np.random.default_rng(0).standard_normal(4000))] * 15
    loop = _runs(2.0, 0.90)
    narrow = rules.f7_compare(_runs(1.8, 0.90), loop, eps=0.01, min_runs=12, calibration_scores=cal)
    assert narrow["fires"] and narrow["coverage_matched_gaussian"]["width_change_pct"] < -5
    wide = rules.f7_compare(_runs(1.95, 0.90), loop, eps=0.01, min_runs=12, calibration_scores=cal)
    assert not wide["fires"]
    # narrower only because it covers less: the coverage-matched width is not narrower
    low = rules.f7_compare(_runs(1.85, 0.885), loop, eps=0.01, min_runs=12, calibration_scores=cal)
    assert low["unscaled"]["narrower"] and not low["coverage_matched_gaussian"]["narrower"]
    bad_loop = rules.f7_compare(
        _runs(2.5, 0.90), _runs(2.0, 0.90, u=0.03), eps=0.01, min_runs=12, calibration_scores=cal
    )
    assert bad_loop["fires"] and not bad_loop["loop"]["valid"]
    invalid = rules.f7_compare(
        _runs(1.0, 0.85), loop, eps=0.01, min_runs=12, calibration_scores=cal
    )
    assert not invalid["fires"]
    # half-normal scores: the empirical factor is close to the Gaussian one
    f_emp = rules.empirical_factor(cal[0], 0.88, 0.90, 600)
    assert f_emp == pytest.approx(rules.gaussian_factor(0.88, 0.90, 600), rel=0.03)
    assert (
        rules.clip_coverage(1.0, 600) == 1 - 1 / 1200 and rules.clip_coverage(0.0, 600) == 1 / 1200
    )
    v = rules.f7_verdict({"a": narrow, "b": wide, "c": bad_loop})
    assert v["fires"] and v["baselines_meeting"] == ["a", "c"] and v["recommended"] == "a"


def test_f1_cell() -> None:
    assert not rules.f1_cell(0.8 * d.gamma_crit(4) * 1.01, 4, 0.01, 0.01, 600)["in_region"]
    sd = d.noise_gain_sd(0.02, 4)
    pred = d.infinite_fraction_pred(0.02, 4)
    cell = rules.f1_cell(0.02, 4, sd, pred, 600)
    assert cell["in_region"] and cell["err_sd"] == pytest.approx(0.0) and not cell["off_by_25pct"]
    assert rules.f1_cell(0.02, 4, 2 * sd, pred, 600)["off_sd"]
    assert rules.f1_cell(0.02, 4, sd, 2 * pred, 600)["off_inf"]
    # a measured share of 0: off only if the model predicts more than 1.25 infinite intervals
    zero = rules.f1_cell(0.02, 4, sd, 0.0, 600)
    assert zero["err_inf"] is None
    assert zero["off_inf"] == (pred * 600 > 1.25)
    big = rules.f1_cell(0.05, 3, d.noise_gain_sd(0.05, 3), 0.0, 719)
    assert big["inf_pred_count"] > 1.25 and big["off_inf"]


# --- records ------------------------------------------------------------------------------


def test_json_round_trip_and_line_ends(tmp_path: Path) -> None:
    payload = {"a": [1.0, math.inf, -math.inf], "b": {"c": np.float64(2.5), "d": np.int64(3)}}
    sha = rc.write_evidence(tmp_path / "x.json", payload)
    raw = (tmp_path / "x.json").read_bytes()
    assert b"\r" not in raw and b"Infinity" not in raw and sha == hashlib.sha256(raw).hexdigest()
    back = rc.read_evidence(tmp_path / "x.json")
    assert back["a"][1] == math.inf and back["a"][2] == -math.inf and back["b"]["d"] == 3
    (tmp_path / "y.json").write_bytes(raw.replace(b"\n", b"\r\n"))
    assert rc.evidence_sha256(tmp_path / "y.json") == sha
    nan = rc.read_evidence(tmp_path / "x.json") | {"n": math.nan}
    rc.write_evidence(tmp_path / "z.json", nan, compact=True)
    assert math.isnan(rc.read_evidence(tmp_path / "z.json")["n"])


def test_fingerprints() -> None:
    x = np.random.default_rng(1).standard_normal(800)
    fp = rc.fingerprint(x)
    assert rc.check_fingerprint("x", rc.fingerprint(x.copy()), fp) == "exact"
    ulp = x.copy()
    ulp[10] = np.nextafter(ulp[10], np.inf)
    assert rc.check_fingerprint("x", rc.fingerprint(ulp), fp) == "close"
    moved = x.copy()
    moved[10] += 1e-6
    with pytest.raises(ValueError, match="differs"):
        rc.check_fingerprint("x", rc.fingerprint(moved), fp)
    with pytest.raises(ValueError, match="values"):
        rc.check_fingerprint("x", rc.fingerprint(x[:-1]), fp)
    assert rc.close_values("v", [1.0, 2.0], [1.0, 2.0]) == "exact"
    with pytest.raises(ValueError):
        rc.close_values("v", 1.0, 1.001)


# --- the stages, end to end ---------------------------------------------------------------


def _unit(
    name: str,
    keys: list[tuple[str, int]],
    thetas: tuple[int, ...],
    primary: int,
    window: int,
    baselines: bool,
    n_cal: int,
    n_ev: int,
    seed: int,
) -> tuple[st.Unit, st.Unit]:
    """The stage A and stage B views of a synthetic unit."""
    cal, full = [], []
    for i, (regime, stream) in enumerate(keys):
        rng = np.random.default_rng(seed + i)
        r = 0.3 * _ar1(0.9, n_cal + n_ev, rng)
        y = 2.0 + r + 0.5 * _ar1(0.99, n_cal + n_ev, rng)
        info = {"model": {"kind": "synthetic", "lag": 0}}
        full.append(st.Stream(regime, stream, r, y, n_cal, n_ev, info))
        cal.append(st.Stream(regime, stream, r[:n_cal].copy(), y[:n_cal].copy(), n_cal, 0, info))

    def unit(streams: list[st.Stream]) -> st.Unit:
        return st.Unit(
            name, streams, thetas, primary, window, baselines, n_cal + n_ev, {"synthetic": 1}
        )

    return unit(cal), unit(full)


@pytest.fixture(scope="module")
def run_all(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Stage A, a JSON round trip, stage B and the verdicts on small synthetic units."""
    out = tmp_path_factory.mktemp("stages")
    keys3 = [("mode1", 19), ("mode2", 5), ("mode3", 3)]
    units = {
        "debutanizer": _unit(
            "debutanizer", [("debutanizer", 0)], (0, 1, 3, 7, 12), 3, 200, True, 300, 150, 1
        ),
        "T1": _unit("T1", keys3, (0, 2, 4), 4, 200, True, 260, 60, 10),
        "T3": _unit("T3", keys3, (0,), 0, 40, False, 160, 120, 20),
    }
    grid = st.PID_GRID
    st.PID_GRID = (0.005, 0.05)
    try:
        A, B, U, steps = {}, {}, {}, {}
        for name, (ua, ub) in units.items():
            path_a = out / f"phase1_stageA_{name}.json"
            rc.write_evidence(path_a, st.stage_a(ua, st._serial))
            A[name] = rc.read_evidence(path_a)
            rec, stp = st.stage_b(ub, A[name], st._serial)
            rec["stage_a_sha256"] = rc.evidence_sha256(path_a)
            rc.write_evidence(out / f"phase1_stageB_{name}.json", rec, compact=True)
            B[name] = rc.read_evidence(out / f"phase1_stageB_{name}.json")
            U[name] = ub
            if stp:
                steps = st.steps_record(stp)
                rc.write_evidence(
                    out / "phase1_stageB_debutanizer_steps.json", {"steps": steps}, compact=True
                )
        verdict = vd.verdicts(A, B, steps)
    finally:
        st.PID_GRID = grid
    return {"A": A, "B": B, "units": U, "steps": steps, "verdicts": verdict, "dir": out}


@pytest.mark.slow
def test_stage_b_reproduces_stage_a_exactly(run_all: dict) -> None:
    def leaves(node: object) -> list:
        if isinstance(node, dict):
            return [x for v in node.values() for x in leaves(v)]
        if isinstance(node, list):
            return [x for v in node for x in leaves(v)]
        return [node]

    for name, rec in run_all["B"].items():
        statuses = [x for x in leaves(rec["checks"]) if x in ("exact", "close")]
        assert statuses and set(statuses) == {"exact"}, name


@pytest.mark.slow
def test_every_cell_of_the_design_is_run(run_all: dict) -> None:
    for name, rec in run_all["B"].items():
        unit = run_all["units"][name]
        want = set()
        for theta in unit.thetas:
            for comp in st.COMPS:
                want.add(st.cell_key(theta, comp, "none", "-"))
                for loop in st.TUNED_LOOPS:
                    for policy in st.POLICIES:
                        for pairing in st.pairings_of(unit.primary, theta, loop):
                            want.add(st.cell_key(theta, comp, loop, policy, pairing))
        assert set(rec["cells"]) == want
        for per in rec["cells"].values():
            assert set(per) == {s.key for s in unit.streams}
    arrival = [k for k in run_all["B"]["T1"]["cells"] if k.endswith("arrival")]
    assert len(arrival) == 2 * len(st.POLICIES) and all("theta=4|" in k for k in arrival)


@pytest.mark.slow
def test_stage_a_tuning_and_cells_agree(run_all: dict) -> None:
    a, rec = run_all["A"]["T1"], run_all["B"]["T1"]
    for theta in (0, 2, 4):
        for comp in st.COMPS:
            node = a["tuning"]["mode2"][str(theta)][comp]["sequential"]["aware_half"]
            cell = rec["cells"][st.cell_key(theta, comp, "sequential", "aware_half")]["mode2/5"]
            assert cell["gamma"] == node["gamma"] and cell["tuning_feasible"] == node["feasible"]
            assert node["gamma"] < 0.8 * d.gamma_crit(theta)
    raw0 = a["tuning"]["mode1"]["0"]["raw"]["sequential"]["blind"]
    raw4 = a["tuning"]["mode1"]["4"]["raw"]["sequential"]["blind"]
    assert raw0 == raw4  # delay-blind tuning replays at theta = 0 on the same raw scores
    assert set(a["pid"]["tuning"]["mode3"]["4"]) == {"qr", "theta", "matched"}
    assert a["spci"]["w"] == b.spci_window(260) and a["spci"]["seeds"]["mode1/19"] == 1103 + 19
    assert run_all["A"]["debutanizer"]["spci"]["seeds"]["debutanizer/0"] == 1103


@pytest.mark.slow
def test_verdicts_cover_every_rule(run_all: dict) -> None:
    v = run_all["verdicts"]
    assert set(v["decided"]) == {"F1", "F2", "F3", "F5a", "F5b", "F6", "F7", "F8"}
    assert set(v["summary"]) >= {"F2_fires", "F7_fires", "F8_fires", "F1_fires"}
    f7 = v["decided"]["F7"]
    assert {"pid_qr", "pid_theta", "pid_matched", "spci"} <= set(f7)
    assert v["decided"]["F2"]["tep_T1_theta4"]["ci975"]["n"] == 3
    deb = v["descriptive"]["debutanizer"]["3"]
    assert deb["F2"]["ci975"]["level"] == 0.975 and "F7" in deb
    assert "T3" in v["descriptive"] and "0" in v["descriptive"]["T3"]


@pytest.mark.slow
def test_stage_b_stops_on_a_changed_calibration_row(
    run_all: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(st, "PID_GRID", (0.005, 0.05))  # the grid stage A ran with
    a = run_all["A"]["T3"]
    unit = run_all["units"]["T3"]
    r = unit.streams[1].r.copy()
    r[50] += 1e-3
    changed = st.Unit(
        unit.name,
        [
            st.Stream(s.regime, s.stream, r if i == 1 else s.r, s.y, s.n_cal, s.n_ev, s.info)
            for i, s in enumerate(unit.streams)
        ],
        unit.thetas,
        unit.primary,
        unit.window,
        unit.baselines,
        unit.run_length,
        unit.inputs,
    )
    with pytest.raises(ValueError, match="residuals"):
        st.stage_b(changed, a, st._serial)
    other = dict(a, settings=dict(a["settings"], eps=0.02))
    with pytest.raises(ValueError, match="settings"):
        st.stage_b(unit, other, st._serial)


def test_results_do_not_depend_on_the_workers() -> None:
    """Both stages, serial and over two worker processes (a unit without baselines, so that the
    test holds under Windows' spawn as well)."""
    ua, ub = _unit("T3", [("mode1", 19), ("mode2", 5)], (0,), 0, 40, False, 160, 120, 30)
    serial = st.stage_a(ua, st._serial)
    with st.mapper(2) as pmap:
        pooled = st.stage_a(ua, pmap)
        a = rc.from_jsonable(json.loads(json.dumps(rc.to_jsonable(serial))))
        b_pooled, _ = st.stage_b(ub, a, pmap)
    b_serial, _ = st.stage_b(ub, a, st._serial)
    assert json.dumps(rc.to_jsonable(serial)) == json.dumps(rc.to_jsonable(pooled))
    assert json.dumps(rc.to_jsonable(b_serial)) == json.dumps(rc.to_jsonable(b_pooled))


_RUNNER = Path(__file__).resolve().parents[2] / "scripts" / "phase1_run.py"


def _runner_module() -> object:
    spec = importlib.util.spec_from_file_location("phase1_run", _RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.slow
def test_command_line_verdicts(run_all: dict, capsys: pytest.CaptureFixture) -> None:
    """``phase1_run.py --verdicts`` on the records of the end-to-end run."""
    import argparse

    runner = _runner_module()
    with pytest.raises(SystemExit, match="phase1_stageA_T2.json is missing"):
        runner.run_verdicts(argparse.Namespace(evidence_dir=run_all["dir"]))
    runner.run_verdicts(argparse.Namespace(evidence_dir=run_all["dir"], allow_partial=True))
    out = rc.read_evidence(run_all["dir"] / "phase1_verdicts.json")
    assert out["summary"] == run_all["verdicts"]["summary"]
    assert out["units"] == ["T1", "T3", "debutanizer"]
    assert out["decided"]["F1"]["units_missing"] == ["T2"]
    assert set(out["inputs_sha256"]) >= {
        (run_all["dir"] / f"phase1_stage{s}_{u}.json").as_posix()
        for s in "AB"
        for u in ("debutanizer", "T1", "T3")
    }
    assert "F2_fires" in capsys.readouterr().out
    assert runner.committed(run_all["dir"] / "phase1_verdicts.json") is not None
    assert runner._close_checks({"a": ["exact", "close"], "b": {"c": "close"}}) == ["/a/1", "/b/c"]


def test_stage_a_must_be_committed_and_pushed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``committed`` and ``pushed`` on a throwaway repository with a local remote."""
    import shutil
    import subprocess

    if shutil.which("git") is None:
        pytest.skip("git is not available")
    runner = _runner_module()
    remote, work = tmp_path / "remote.git", tmp_path / "work"

    def g(*args: str) -> None:
        subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)

    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True, capture_output=True)
    g("symbolic-ref", "HEAD", "refs/heads/main")
    g("config", "user.name", "test")
    g("config", "user.email", "test@example.org")
    g("config", "commit.gpgsign", "false")
    f = work / "phase1_stageA_T1.json"
    f.write_text("{}\n")
    monkeypatch.chdir(work)
    assert runner.committed(f) == "not committed"
    g("add", f.name)
    g("commit", "-q", "--no-verify", "-m", "stage A")
    assert runner.committed(f) is None
    reason, sha = runner.pushed(f)
    assert sha is not None and reason is not None  # nothing pushed yet
    g("push", "-q", "--no-verify", "-u", "origin", "main")
    assert runner.pushed(f) == (None, sha)
    f.write_text('{"a": 1}\n')
    assert runner.committed(f) == "changed since the last commit"
    g("commit", "-q", "--no-verify", "-am", "stage A again")
    reason, sha2 = runner.pushed(f)
    assert sha2 != sha and reason is not None and "not pushed" in reason


def _tune_cal(sc: np.ndarray, n: int, th: int, eps: float, y_range: float) -> float:
    """The library's replay tuning on one calibration segment (seed 200, the rest replayed)."""
    segs = [(sc[:n][200:], sc[:n][:200])]
    return float(d.replay_tune_pooled(segs, th, y_range=y_range, eps=eps)["gamma"])


def _run_ev(sc: np.ndarray, n: int, th: int, g: float, y_range: float) -> tuple:
    """The library's loop on the evaluation rows, its window the last 200 calibration scores."""
    res = d.run_delayed_aci(sc[n:], th, init_scores=sc[:n][-200:], gamma=g, window=200)
    return res, float(np.mean(d.uninformative(res["h"], y_range)))


@pytest.mark.slow
def test_decided_rules_match_an_independent_computation(run_all: dict) -> None:
    """F2, F3, F5a, F5b, F6, F8 and the baseline cells of F7 at T1, theta = 4, recomputed from the
    frozen library alone, as the design-stage scripts compute them (one stream per regime here, so
    a regime's pooled tuning is its run's)."""
    from scipy import stats

    from ipis.module1_soft_sensor.evaluation.delay_compensation import (
        fit_direct_forecaster,
        predicted_width_ratio,
        select_order,
    )
    from ipis.module1_soft_sensor.evaluation.inference import acf, iact

    A, B = run_all["A"]["T1"], run_all["B"]["T1"]
    ours = vd.tep_rules(A, B, 4)
    W, ALPHA, EPS, TH = 200, 0.1, 0.01, 4
    streams = run_all["units"]["T1"].streams
    f2, covered, u5a, u5b, meas, pred, diff8, g_comp, g_raw = ([] for _ in range(9))
    for s in streams:
        r, n = s.r, s.n_cal
        cal, ev = slice(0, n), slice(n, None)
        y_range = float(np.ptp(s.y[cal]))
        raw = np.abs(r)
        order = select_order(r, TH, max_order=10, fit=cal)
        fc = fit_direct_forecaster(r, TH, order=order, fit=cal)
        comp = np.abs(r - fc.predict(r))
        comp[: fc.warmup] = raw[: fc.warmup]
        pred.append(predicted_width_ratio(acf(r[cal], TH + order + 1), TH, order))

        blind = _tune_cal(raw, n, 0, EPS, y_range)
        res4, u4 = _run_ev(raw, n, TH, blind, y_range)
        f2.append(u4 - _run_ev(raw, n, 0, blind, y_range)[1])
        covered.append(int(res4["covered"].sum()))
        g_raw.append(_tune_cal(raw, n, TH, EPS / 2, y_range))
        g_comp.append(_tune_cal(comp, n, TH, EPS / 2, y_range))
        u5a.append(_run_ev(raw, n, TH, g_raw[-1], y_range)[1])
        u5b.append(_run_ev(comp, n, TH, g_comp[-1], y_range)[1])
        meas.append(float(np.quantile(comp[ev], 0.9) / np.quantile(raw[ev], 0.9)))
        ol = [_run_ev(sc, n, TH, 0.0, y_range)[0] for sc in (comp, raw)]
        diff8.append(
            iact((~ol[0]["covered"]).astype(float)) - iact((~ol[1]["covered"]).astype(float))
        )
        # the baselines of F7: SPCI and conformal PID with the matched scorecaster
        o = b.spci_rolling(
            r,
            n,
            ALPHA,
            TH + 1,
            w=b.spci_window(n),
            train_len=n,
            random_state=np.random.RandomState(1103 + s.stream),
        )
        lo, hi = o["lo"][ev], o["hi"][ev]
        got = B["baselines"]["4"]["spci"][s.key]
        assert got["f7_median_width"] == float(np.median(hi - lo))
        assert got["coverage"] == float(np.mean((lo <= r[ev]) & (r[ev] <= hi)))
        rh = fc.predict(r)
        rh[: fc.warmup] = np.nan
        sc = b.matched_scorecasts(rh)
        bp = float(np.max(np.abs(r[cal])))
        tuned = b.pid_tune_pooled(
            [(r[cal], (sc[0][cal], sc[1][cal]), bp)],
            TH + 1,
            alpha=ALPHA,
            y_range=y_range,
            eps=EPS / 2,
            c_sats=b.pid_c_sat_grid(n + s.n_ev),
            grid=(0.005, 0.05),
            scale_to=0.9,
        )["config"]
        assert tuned == A["pid"]["tuning"][s.regime]["4"]["matched"]["config"]
        o = b.conformal_pid_intervals(
            r,
            ALPHA,
            tuned["m"],
            TH + 1,
            window=W,
            k_i=tuned["k_factor"] * bp,
            c_sat=tuned["c_sat"],
            scorecasts=sc,
            start=W,
            warm_rows=100,
        )
        got = B["baselines"]["4"]["pid_matched"][s.key]
        assert got["f7_median_width"] == float(np.median(o["width"][ev]))
        assert got["u"] == float(np.mean(b.uninformative_width(o["width"][ev], y_range)))
    k = len(streams)
    assert ours["F2"]["diff_per_run"] == f2
    se = np.std(f2, ddof=1) / math.sqrt(k) if np.ptp(f2) > 0 else 0.0
    assert ours["F2"]["ci975"]["lo"] == pytest.approx(np.mean(f2) - stats.t.ppf(0.9875, k - 1) * se)
    assert ours["F3"]["covered"] == sum(covered)
    assert ours["F5a"]["u_per_run"] == u5a and ours["F5b"]["u_per_run"] == u5b
    assert ours["F6"]["measured_per_run"] == meas and ours["F6"]["predicted_per_run"] == pred
    assert ours["F8"]["iact_diff_per_run"] == diff8
    assert (
        ours["F8"]["gamma_comp_by_regime"] == g_comp and ours["F8"]["gamma_raw_by_regime"] == g_raw
    )
    assert ours["F8"]["mean_predicted_ratio"] == pytest.approx(np.mean(pred))


def test_contrasts_vary_one_factor() -> None:
    cells = [
        st.cell_key(0, "raw", "sequential", "blind"),
        st.cell_key(4, "raw", "sequential", "blind"),
        st.cell_key(4, "comp", "sequential", "blind"),
        st.cell_key(4, "raw", "sequential", "blind", "arrival"),
        st.cell_key(4, "raw", "none", "-"),
        st.cell_key(4, "raw", "smith", "blind"),
        st.cell_key(4, "raw", "sequential", "aware_half"),
    ]
    c = st.contrasts(cells)
    assert set(c) == set(st.CONTRASTS)
    assert c["comp_minus_raw"] == [("theta=4|sequential|blind|stored", cells[2], cells[1])]
    assert (cells[1], cells[1], cells[0]) in c["theta_minus_0"]
    assert c["arrival_minus_stored"] == [(cells[3], cells[3], cells[1])]
    assert set(c["loop_on_minus_off"]) == {(k, k, cells[4]) for k in (cells[1], cells[6])}
    assert c["loop_minus_sequential"] == [(cells[5], cells[5], cells[1])]
    assert c["policy_minus_aware_half"] == [(cells[1], cells[1], cells[6])]
    fields = ("theta", "comp", "loop", "policy", "pairing")
    varied = {
        "comp_minus_raw": {"comp"},
        "theta_minus_0": {"theta"},
        "arrival_minus_stored": {"pairing"},
        "loop_on_minus_off": {"loop", "policy"},  # the static loop has no step size
        "loop_minus_sequential": {"loop"},
        "policy_minus_aware_half": {"policy"},
    }
    for name, rows in c.items():  # each contrast varies one factor only
        for _, k, control in rows:
            pairs = zip(fields, k.split("|"), control.split("|"), strict=True)
            diff = {f for f, a, b_ in pairs if a != b_}
            assert diff == varied[name], (name, k, control)
