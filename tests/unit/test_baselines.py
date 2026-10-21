"""Unit tests for the label-horizon baselines of claim N1'' (pre-registration Appendix A):
conformal PID control and SPCI. The bit-for-bit checks against the authors' code need their
repositories and are run by the scripts in scripts/baselines/; these tests cover the definitions."""

from __future__ import annotations

import math

import numpy as np
import pytest

from ipis.module1_soft_sensor.evaluation import baselines as b
from ipis.module1_soft_sensor.evaluation import baselines_pid, baselines_spci


def test_facade_reexports_every_public_name() -> None:
    """``baselines`` is the import point of scripts and tests: it must carry every public name of
    the two modules, the same objects, plus its own provenance helper and the one private helper
    the tests use."""
    own = {"SOURCES", "source_sha256"}
    reexported = {"_weighted_quantile_presorted"}
    for mod in (baselines_pid, baselines_spci):
        reexported |= {
            k
            for k, v in vars(mod).items()
            if not k.startswith("_")
            and getattr(v, "__module__", mod.__name__) == mod.__name__
            and not isinstance(v, type(math))
            and k != "annotations"
        }
    assert set(b.__all__) == own | reexported
    for name in reexported:
        source = baselines_pid if hasattr(baselines_pid, name) else baselines_spci
        assert getattr(b, name) is getattr(source, name)
    digests = b.source_sha256()
    assert len(digests) == 3 and all(len(v) == 64 for v in digests.values())


def _ar1(phi: float, n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + math.sqrt(1.0 - phi * phi) * e[t]
    return x


# ------------------------------------------------------------------ conformal PID


def test_tan_integrator_saturates_and_vanishes_without_gain() -> None:
    assert b.pid_tan(math.pi / 2) == math.inf
    assert b.pid_tan(-math.pi / 2) == -math.inf
    assert b.pid_tan(0.3) == pytest.approx(math.tan(0.3))
    assert b.pid_integrator(5.0, 100, 2.0, 0.0) == 0.0
    t, c_sat, k_i = 99, 0.5, 3.0
    x_sat = (math.pi / 2) * c_sat * (t + 1) / math.log(t + 1)
    assert b.pid_integrator(0.99 * x_sat, t, c_sat, k_i) < math.inf
    assert b.pid_integrator(1.01 * x_sat, t, c_sat, k_i) == math.inf


def test_c_sat_values() -> None:
    log_t = math.log(1400)
    assert b.pid_c_sat(1400, 0.02) == pytest.approx(2 / math.pi * (1 - 1 / log_t))
    # independent of delta while delta log T <= 1; the ceiling steps up beyond
    assert b.pid_c_sat(1400, 0.1) == b.pid_c_sat(1400, 0.02)
    assert b.pid_c_sat(1400, 0.2) == pytest.approx(2 / math.pi * (2 - 1 / log_t))
    # the purpose value saturates the integrator at a cumulative excess of delta T at time T
    c = b.pid_c_sat_purpose(1400, 0.02)
    x_sat = (math.pi / 2) * c * 1400 / math.log(1400)
    assert x_sat == pytest.approx(0.02 * 1400)
    grid = b.pid_c_sat_grid(1400)
    assert grid == (c, b.pid_c_sat(1400, 0.02), 5.0)


@pytest.mark.parametrize("mode", b.MODES)
@pytest.mark.parametrize("horizon", [1, 2, 5])
def test_quantile_tracking_is_a_dead_time_loop(mode: str, horizon: int) -> None:
    """Fixed learning rate, no integrator, no scorecaster: q_{t+1} = q_t + lr (err_{t-h+1} - a),
    and q stays 0 until the first label arrives. The authors' code never records coverage for
    the first h - 1 samples, so it counts them as misses; phase1 records every step."""
    rng = np.random.default_rng(horizon)
    s = rng.standard_normal(300)
    lr, a = 0.07, 0.05
    out = b.conformal_pid_side(
        s, a, lr, horizon, window=50, k_i=0.0, c_sat=1.0, mode=mode, proportional_lr=False
    )
    q = np.zeros(s.size)
    err = np.zeros(s.size)
    for t in range(s.size):
        unrecorded = mode == "code" and t < horizon - 1
        err[t] = 1.0 if unrecorded else float(s[t] > q[t])
        if t >= horizon - 1 and t < s.size - 1:
            q[t + 1] = q[t] + lr * (err[t - horizon + 1] - a)
    np.testing.assert_allclose(out["q"], q, rtol=0, atol=1e-12)
    assert np.all(out["q"][:horizon] == 0.0)


@pytest.mark.parametrize("horizon", [1, 4])
@pytest.mark.parametrize("start", [0, 37])
def test_phase1_recursion_uses_every_labelled_error_and_score(horizon: int, start: int) -> None:
    """Phase 1: q = QT + r + c at every issued step from ``start``, QT starting at init_q. The
    integrator sums every labelled issued error, the newest included, with the paper's r_t at
    t = the number of errors plus the seed age; eta is lr times the range of the window most
    recent labelled scores, the newest included, seed rows among them."""
    rng = np.random.default_rng(20 + horizon)
    s = rng.standard_normal(250)
    a, lr, window, k_i, c_sat = 0.05, 0.1, 30, 2.0, 0.7
    q0, age = (0.4, 30) if start else (0.0, 0)
    c = rng.standard_normal(250) * 0.1
    out = b.conformal_pid_side(
        s,
        a,
        lr,
        horizon,
        window=window,
        k_i=k_i,
        c_sat=c_sat,
        scorecasts=c,
        mode="phase1",
        start=start,
        init_q=q0,
        seed_age=age,
    )
    q, qt, err = np.full(s.size, np.nan), np.full(s.size, np.nan), np.zeros(s.size)
    qt[start], q[start] = q0, q0 + c[start]
    for t in range(start, s.size):
        err[t] = float(s[t] > q[t])
        if t == s.size - 1:
            break
        p = t - horizon + 1
        integ = 0.0
        qt[t + 1] = qt[t]
        if p >= start:
            win = s[max(p + 1 - window, 0) : p + 1]
            eta = lr * (win.max() - win.min())
            n = p - start + 1
            x = err[start : p + 1].sum() - n * a
            arg = x * math.log(n + age) / (c_sat * (n + age))
            integ = k_i * (math.inf if arg >= math.pi / 2 else math.tan(arg))
            qt[t + 1] = qt[t] + eta * (err[p] - a)
        q[t + 1] = qt[t + 1] + integ + c[t + 1]
    np.testing.assert_allclose(out["q"], q, rtol=0, atol=1e-12)
    assert not out["covered"][:start].any()
    with pytest.raises(ValueError):
        b.conformal_pid_side(
            s, a, lr, horizon, window=window, k_i=k_i, c_sat=c_sat, mode="code", start=3
        )


def test_phase1_warm_start_seeds_each_side_from_its_centred_scores() -> None:
    """The tracker of each side starts at the conformal 0.95 quantile of s - c over the last
    warm_rows seed rows; nothing is issued before ``start``."""
    rng = np.random.default_rng(8)
    r = rng.standard_normal(300)
    c_up = rng.standard_normal(300) * 0.2
    c_lo = -c_up
    start, warm = 120, 60
    out = b.conformal_pid_intervals(
        r,
        0.1,
        0.05,
        3,
        window=50,
        k_i=1.0,
        c_sat=0.55,
        scorecasts=(c_lo, c_up),
        start=start,
        warm_rows=warm,
    )
    from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile

    up0 = conformal_quantile(r[start - warm : start] - c_up[start - warm : start], 0.95)
    lo0 = conformal_quantile(-r[start - warm : start] - c_lo[start - warm : start], 0.95)
    assert out["hi"][start] == pytest.approx(up0 + c_up[start])
    assert out["lo"][start] == pytest.approx(-(lo0 + c_lo[start]))
    assert np.all(np.isnan(out["hi"][:start])) and not out["covered"][:start].any()
    # the whole run is the two sides started warm, with the integrator aged by the seed
    kw = {"window": 50, "k_i": 1.0, "c_sat": 0.55, "start": start, "seed_age": start}
    up = b.conformal_pid_side(r, 0.05, 0.05, 3, scorecasts=c_up, init_q=up0, **kw)["q"]
    lo = b.conformal_pid_side(-r, 0.05, 0.05, 3, scorecasts=c_lo, init_q=lo0, **kw)["q"]
    np.testing.assert_array_equal(out["hi"], up)
    np.testing.assert_array_equal(out["lo"], -lo)
    with pytest.raises(ValueError):
        b.conformal_pid_intervals(r, 0.1, 0.05, 3, window=50, k_i=1.0, c_sat=0.55, warm_rows=10)


@pytest.mark.parametrize("horizon", [1, 5])
def test_phase1_warm_started_pid_is_causal_after_the_seed(horizon: int) -> None:
    """From the first issued row on, the interval for sample tau depends on residuals up to
    tau - h only; the seed rows enter through the warm start, as the compensated loop's window
    seed does (Appendix A.1)."""
    r = _ar1(0.8, 400, seed=9)
    start, warm = 200, 100
    kw = {"window": 200, "k_i": 2.0, "c_sat": 0.55, "start": start, "warm_rows": warm}
    base = b.conformal_pid_intervals(r, 0.1, 0.02, horizon, **kw)
    for tau in (start + horizon, 300, 399):
        r2 = r.copy()
        r2[tau - horizon + 1 :] += 3.0
        out = b.conformal_pid_intervals(r2, 0.1, 0.02, horizon, **kw)
        np.testing.assert_array_equal(out["hi"][: tau + 1], base["hi"][: tau + 1])
        np.testing.assert_array_equal(out["lo"][: tau + 1], base["lo"][: tau + 1])


def test_quantile_tracking_long_run_coverage() -> None:
    """Prop. 1 of the paper: |mean(err) - a| <= (B + lr) / (lr T) for scores bounded by B."""
    rng = np.random.default_rng(3)
    s = rng.uniform(-1.0, 1.0, 5000)
    lr, a = 0.05, 0.05
    out = b.conformal_pid_side(
        s, a, lr, 1, window=50, k_i=0.0, c_sat=1.0, mode="phase1", proportional_lr=False
    )
    err = 1.0 - out["covered"].astype(float)
    assert abs(err.mean() - a) <= (1.0 + lr) / (lr * s.size)


@pytest.mark.parametrize("horizon", [1, 3, 6])
def test_phase1_pid_uses_only_scores_known_at_issue_time(horizon: int) -> None:
    rng = np.random.default_rng(10 + horizon)
    s = rng.standard_normal(400)
    kw = {"window": 40, "k_i": 2.0, "c_sat": 0.55, "mode": "phase1"}
    base = b.conformal_pid_side(s, 0.05, 0.1, horizon, **kw)["q"]
    for tau in (60, 150, 399):
        s2 = s.copy()
        s2[tau - horizon + 1 :] = rng.standard_normal(s.size - (tau - horizon + 1)) * 5.0
        q2 = b.conformal_pid_side(s2, 0.05, 0.1, horizon, **kw)["q"]
        np.testing.assert_array_equal(q2[: tau + 1], base[: tau + 1])


def test_code_mode_learning_rate_looks_ahead_beyond_horizon_two() -> None:
    """The reason for the phase1 learning-rate window: at h >= 3 the authors' window reaches
    scores not yet labelled at issue time."""
    rng = np.random.default_rng(5)
    s = rng.standard_normal(200)
    h, tau = 4, 120
    kw = {"window": 30, "k_i": 0.0, "c_sat": 1.0, "mode": "code"}
    base = b.conformal_pid_side(s, 0.05, 0.1, h, **kw)["q"]
    s2 = s.copy()
    s2[tau - 2] = 50.0  # labelled only after the issue time of tau
    q2 = b.conformal_pid_side(s2, 0.05, 0.1, h, **kw)["q"]
    assert q2[tau] != base[tau]


def test_scorecast_alignment() -> None:
    T, burn, h = 40, 10, 3
    table = np.arange(T * 4, dtype=float).reshape(T, 4)
    c = b.pid_scorecasts(table, h, burn, "phase1")
    assert np.all(c[: burn + 1 + h] == 0.0)
    for tau in range(burn + 1 + h, T):
        assert c[tau] == table[tau - h, h - 1]
    c1 = b.pid_scorecasts(table, 1, burn, "code")
    assert np.all(c1[: burn + 2] == 0.0)
    for tau in range(burn + 2, T):
        assert c1[tau] == table[tau - 2, 0]
    with pytest.raises(ValueError):
        b.pid_scorecasts(table, 2, burn, "code")


def test_theta_table_is_causal_and_serves_all_horizons() -> None:
    pytest.importorskip("statsmodels")
    s = _ar1(0.8, 80, seed=1)
    table = b.theta_forecast_table(s, 60, 4)
    assert np.all(np.isnan(table[:60])) and np.all(np.isnan(table[-1]))
    s2 = s.copy()
    s2[71:] = 9.0
    table2 = b.theta_forecast_table(s2, 60, 4)
    np.testing.assert_array_equal(table2[:71], table[:71])
    assert np.all(np.isfinite(table[60:-1]))


@pytest.mark.parametrize("horizon", [1, 3])
def test_qr_scorecasts_are_causal_and_track_the_conditional_quantile(horizon: int) -> None:
    rng = np.random.default_rng(30 + horizon)
    T, burn = 320, 200
    s = np.zeros(T)
    for t in range(horizon, T):  # s_t = 0.8 s_{t-h} + noise: the conditional median is 0.8 s_{t-h}
        s[t] = 0.8 * s[t - horizon] + rng.standard_normal()
    c = b.qr_scorecasts(s, horizon, burn, 0.5)
    assert np.all(c[: burn + 1 + horizon] == 0.0)
    tail = np.arange(burn + 1 + horizon, T)
    assert np.corrcoef(c[tail], 0.8 * s[tail - horizon])[0, 1] > 0.95
    tau = 260
    s2 = s.copy()
    s2[tau - horizon + 1 :] += 7.0
    c2 = b.qr_scorecasts(s2, horizon, burn, 0.5)
    np.testing.assert_array_equal(c2[: tau + 1], c[: tau + 1])


def test_matched_scorecasts_mirror_the_residual_forecast() -> None:
    rhat = np.array([np.nan, np.nan, 0.2, -0.1])
    lo, up = b.matched_scorecasts(rhat)
    np.testing.assert_array_equal(up, [0.0, 0.0, 0.2, -0.1])
    np.testing.assert_array_equal(lo, [-0.0, -0.0, -0.2, 0.1])


@pytest.mark.parametrize("horizon", [1, 3])
def test_phase1_pid_with_scorecaster_uses_only_labelled_residuals(horizon: int) -> None:
    """Information parity: the interval for sample tau depends on residuals up to tau - h only,
    through every term, the Theta scorecaster included."""
    pytest.importorskip("statsmodels")
    r = _ar1(0.9, 90, seed=7)
    burn, tau = 50, 75

    def interval(res: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        sc = tuple(
            b.pid_scorecasts(b.theta_forecast_table(sign * res, burn, horizon), horizon, burn)
            for sign in (-1.0, 1.0)
        )
        out = b.conformal_pid_intervals(
            res, 0.1, 0.1, horizon, window=burn, k_i=3.0, c_sat=0.55, scorecasts=sc
        )
        return out["lo"], out["hi"]

    lo, hi = interval(r)
    r2 = r.copy()
    r2[tau - horizon + 1 :] += 4.0
    lo2, hi2 = interval(r2)
    np.testing.assert_array_equal(lo2[: tau + 1], lo[: tau + 1])
    np.testing.assert_array_equal(hi2[: tau + 1], hi[: tau + 1])
    assert lo2[tau + 1] != lo[tau + 1] or hi2[tau + 1] != hi[tau + 1]


def test_two_sided_intervals_count_empty_sets_as_misses_of_width_zero() -> None:
    r = np.array([0.0, 0.5, -0.5, 2.0, 0.1, -0.1])
    out = b.conformal_pid_intervals(r, 0.1, 0.0, 1, window=2, k_i=0.0, c_sat=1.0)
    # lr = 0, no integrator, no scorecaster: q = 0 on both sides, interval [0, 0]
    np.testing.assert_array_equal(out["lo"], 0.0)
    np.testing.assert_array_equal(out["hi"], 0.0)
    np.testing.assert_array_equal(out["covered"], [True, False, False, False, False, False])
    # scorecasts of -1 on both sides from step 2 on: q = -1, so lo = 1 > hi = -1
    minus = np.r_[0.0, 0.0, np.full(r.size - 2, -1.0)]
    out = b.conformal_pid_intervals(
        r, 0.1, 0.0, 1, window=0, k_i=0.0, c_sat=1.0, scorecasts=(minus, minus)
    )
    np.testing.assert_array_equal(out["empty"], [False, False, True, True, True, True])
    np.testing.assert_array_equal(out["width"][2:], 0.0)
    assert not out["covered"][2:].any()


def test_uninformative_width_flags_infinite_and_too_wide() -> None:
    w = np.array([0.0, 1.0, 1.5, 1.6, np.inf])
    np.testing.assert_array_equal(b.uninformative_width(w, 1.5), [False, False, False, True, True])


def _cfg(m: float, u: float, cov: float, width: float, c_sat: float = 1.0) -> dict:
    return {"m": m, "c_sat": c_sat, "k_factor": 1.0, "u": u, "coverage": cov, "median_width": width}


def test_pid_config_selection_follows_f7() -> None:
    eps, target, tol = 0.005, 0.9, 0.02
    path = [
        _cfg(0.01, 0.0, 0.89, 2.8),
        _cfg(0.02, 0.0, 0.895, 2.7),  # narrowest valid
        _cfg(0.05, 0.004, 0.86, 2.5),  # narrower, but coverage outside the tolerance
        _cfg(0.1, 0.02, 0.9, 2.4),  # narrower, but U above eps
    ]
    assert b.select_pid_config(path, eps, target, tol) == (path[1], "valid")
    no_valid = [path[2], path[3], _cfg(0.2, 0.001, 0.85, 3.0)]
    assert b.select_pid_config(no_valid, eps, target, tol) == (path[2], "coverage")
    none_feasible = [_cfg(0.01, 0.3, 0.9, 2.0), _cfg(0.1, 0.02, 0.9, 2.0)]
    assert b.select_pid_config(none_feasible, eps, target, tol) == (none_feasible[1], "infeasible")
    tied = [_cfg(0.02, 0.0, 0.9, 2.7, c_sat=5.0), _cfg(0.02, 0.0, 0.9, 2.7, c_sat=0.5)]
    assert b.select_pid_config(tied, eps, target, tol)[0]["c_sat"] == 0.5
    # the bounds are inclusive despite rounding: 2640 / 3000 covered and 15 / 3000 uninformative
    edge = [_cfg(0.01, 15 / 3000, 2640 / 3000, 2.0), _cfg(0.02, 0.0, 0.9, 2.9)]
    assert abs(2640 / 3000 - 0.9) > 0.02  # the rounding the tolerance absorbs
    assert b.select_pid_config(edge, eps, target, tol) == (edge[0], "valid")
    # D-P1.11: scaled to 0.90 coverage, a narrower set that covers less can lose
    scaled = [_cfg(0.01, 0.0, 0.88, 2.70), _cfg(0.02, 0.0, 0.90, 2.80)]
    assert b.select_pid_config(scaled, eps, target, tol)[0] is scaled[0]
    assert b.select_pid_config(scaled, eps, target, tol, scale_to=0.9)[0] is scaled[1]


def test_gaussian_width_factor() -> None:
    assert b.gaussian_width_factor(0.9, 0.9) == 1.0
    assert b.gaussian_width_factor(0.88, 0.90) == pytest.approx(1.6448536 / 1.5547736, rel=1e-6)
    assert b.gaussian_width_factor(0.92, 0.90) < 1.0
    with pytest.raises(ValueError):
        b.gaussian_width_factor(1.0, 0.9)


def test_pid_tuning_covers_the_grid() -> None:
    r = _ar1(0.5, 600, seed=2) * 0.1
    seg = (r, None, float(np.max(np.abs(r))))
    c_sats = b.pid_c_sat_grid(600)
    out = b.pid_tune_pooled([seg], 2, alpha=0.1, y_range=float(np.ptp(r)), eps=0.05, c_sats=c_sats)
    assert len(out["path"]) == len(b.PID_M_GRID) * len(c_sats) * len(b.PID_K_FACTORS)
    assert out["config"]["m"] in b.PID_M_GRID
    assert out["flag"] in ("valid", "coverage", "infeasible")


# ------------------------------------------------------------------ SPCI


def test_spci_window_keeps_the_authors_ratio() -> None:
    assert b.spci_window(2755) == 300
    assert b.spci_window(800) == 87
    assert b.spci_window(1660) == 181


def test_weighted_quantile_matches_definition() -> None:
    rng = np.random.default_rng(0)
    a = np.sort(rng.standard_normal(50)).astype(np.float32)
    w = rng.uniform(0.1, 1.0, 50).astype(np.float32)
    q = np.array([0.0, 0.1, 0.5, 0.9, 1.0], dtype=np.float32)
    got = b._weighted_quantile_presorted(a, q, w)
    pos = (np.cumsum(w.astype(float)) - 0.5 * w) / w.sum()
    want = np.interp(q.astype(float), pos, a.astype(float))
    np.testing.assert_allclose(got, want, rtol=0, atol=1e-5)
    assert got[0] == a[0] and got[-1] == a[-1]


def test_quantile_forest_leaf_weights_and_monotone_quantiles() -> None:
    rng = np.random.default_rng(1)
    X = rng.standard_normal((300, 5))
    y = X[:, 0] + 0.3 * rng.standard_normal(300)
    f = b.QuantileForest(random_state=0).fit(X, y)
    # per tree, the weights of the in-bag samples of each leaf sum to one
    for e in range(f.n_estimators):
        for leaf in np.unique(f.leaves_[e][f.leaves_[e] >= 0]):
            assert f.weights_[e][f.leaves_[e] == leaf].sum() == pytest.approx(1.0, rel=1e-5)
    _, levels = b.spci_quantile_levels(0.1)
    pred = f.predict(rng.standard_normal((4, 5)), np.sort(levels))
    assert np.all(np.diff(pred, axis=0) >= 0)
    again = b.QuantileForest(random_state=0).fit(X, y).predict(X[:3], levels)
    np.testing.assert_array_equal(again, f.predict(X[:3], levels))


def test_spci_pairs_follow_the_horizon(monkeypatch: pytest.MonkeyPatch) -> None:
    """The forest is fitted on windows of w residuals, each with the residual h steps after the
    window's last one as its target, and queried at the last w residuals."""
    seen: dict = {}
    real = baselines_spci.QuantileForest

    class Spy(real):  # type: ignore[misc, valid-type]
        def fit(self, X, y):  # type: ignore[no-untyped-def]
            seen["X"], seen["y"] = np.array(X), np.array(y)
            return super().fit(X, y)

        def predict(self, X, q):  # type: ignore[no-untyped-def]
            seen["query"] = np.array(X)
            return super().predict(X, q)

    monkeypatch.setattr(baselines_spci, "QuantileForest", Spy)
    past = np.arange(30, dtype=float)
    w, h = 4, 3
    b.spci_fit_predict(past, h, w, 0.1, random_state=0)
    X, y = seen["X"], seen["y"]
    assert X.shape == (30 - w - h + 1, w) and y.size == X.shape[0]
    np.testing.assert_array_equal(y, X[:, -1] + h)
    np.testing.assert_array_equal(X[:, 1:] - X[:, :-1], 1.0)
    np.testing.assert_array_equal(seen["query"], [past[-w:]])


def test_spci_rolling_is_causal_and_equals_block_at_horizon_one() -> None:
    r = _ar1(0.7, 360, seed=4)
    kw = {"w": 8, "train_len": 150}
    base = b.spci_rolling(r, 300, 0.1, 3, random_state=11, **kw)
    r2 = r.copy()
    r2[330 - 3 + 1 :] += 10.0
    moved = b.spci_rolling(r2, 300, 0.1, 3, random_state=11, **kw)
    np.testing.assert_array_equal(moved["lo"][:331], base["lo"][:331])
    np.testing.assert_array_equal(moved["hi"][:331], base["hi"][:331])
    roll = b.spci_rolling(r, 300, 0.1, 1, random_state=np.random.RandomState(5), **kw)
    block = b.spci_block(r[150:], 150, 0.1, 1, w=8, random_state=np.random.RandomState(5))
    np.testing.assert_array_equal(roll["lo"][300:], block["lo"])
    np.testing.assert_array_equal(roll["hi"][300:], block["hi"])


def test_spci_covers_iid_residuals_near_nominal() -> None:
    rng = np.random.default_rng(6)
    r = rng.standard_normal(700)
    out = b.spci_rolling(r, 400, 0.1, 2, w=10, train_len=300, random_state=1)
    cov = np.mean((out["lo"][400:] <= r[400:]) & (r[400:] <= out["hi"][400:]))
    assert 0.83 <= cov <= 0.97
    assert np.all(out["lo"][400:] <= out["hi"][400:])
