"""Stage A and stage B of the N1 Phase 1 runner (pre-registration Sections 3F and 5 to 7).

A *unit* is one residual source: the debutanizer, or one TEP arm (T1, T2, T3, and T1 with the
gradient-boosting point model, ``T1_gb``). It holds one residual stream per run: the calibration
rows, then (stage B) the evaluation rows. The TEP streams start at hour 30 (Appendix A.1: "For
TEP the stream is hours 30-100"); the debutanizer's are its 1660 training residuals and then the
719 evaluation residuals.

Stage A (calibration rows only), per unit:
- per stream and theta: the compensation forecaster (BIC order 1 to 10, least squares on the
  calibration rows), the compensated calibration scores and the predicted width ratio (P3), and
  the static split-conformal quantile of the raw and compensated scores (the loop "none");
- per plant (a TEP regime's five runs pooled, or the debutanizer): y_range, and the replay tuning
  of every loop of Section 5.3, raw and compensated, delay-blind (replay at theta = 0 to eps) and
  delay-aware at eps and at eps / 2;
- T1 and the debutanizer: the conformal PID tuning of Appendix A (three scorecasters, 114
  configurations, D-P1.11's selection), with every scorecast computed from calibration rows only,
  and SPCI's window and seeds.
Stage B (all rows), per unit: the calibration quantities recomputed from the full files and
checked against the stage A record (``record.check_fingerprint``); then every cell on the
evaluation rows with stage A's settings (forecasters, step sizes, static quantiles, y_range,
conformal PID configurations), the baselines, the measurements the rules need, and the intervals
of Section 7.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from multiprocessing import Pool
from pathlib import Path
from typing import Any

import numpy as np

from ipis.module1_soft_sensor.evaluation import baselines as b
from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile
from ipis.module1_soft_sensor.evaluation.delay_compensation import (
    DirectForecaster,
    fit_direct_forecaster,
    predicted_width_ratio,
    select_order,
)
from ipis.module1_soft_sensor.evaluation.inference import acf
from ipis.module1_soft_sensor.phase1 import data as dat
from ipis.module1_soft_sensor.phase1 import loops as lp
from ipis.module1_soft_sensor.phase1 import metrics as mt
from ipis.module1_soft_sensor.phase1 import models as pm
from ipis.module1_soft_sensor.phase1 import record as rc
from ipis.module1_soft_sensor.phase1 import rules

ALPHA, EPS = dat.ALPHA, dat.EPS
MAX_ORDER = 10
COMPS = ("raw", "comp")
TUNED_LOOPS = ("sequential", "projected", "phase", "smith", "decaying")
FIXED = {"fixed_0.005": 0.005, "fixed_0.05": 0.05}
TUNED = ("blind", "aware_eps", "aware_half")
POLICIES = ("fixed_0.005", "fixed_0.05", *TUNED, "design")
SCORECASTERS = ("qr", "theta", "matched")
BASELINES = ("pid_qr", "pid_theta", "pid_matched", "spci")
SPCI_SEED = 1103  # A.3: RandomState(1103 + j) for TEP stream j; 1103 for the debutanizer
SENSITIVITY_SKIP = 100  # Section 5.1: a sensitivity analysis excludes the first 100 rows
F7_RUNS, F7_MIN_RUNS = 15, 12  # F7's "smaller in at least 12 of the 15 runs" (Section 6)
PID_GRID = b.PID_M_GRID  # the tests shrink this grid; the runner never does
UNITS = ("debutanizer", "T1", "T2", "T3", "T1_gb")
TEP_UNITS = ("T1", "T2", "T3", "T1_gb")
TEP_EV_ROWS = {"T1": 600, "T2": 1800, "T3": 120, "T1_gb": 600}  # evaluation rows per run
TEP_ARM_OF = {"T1": "T1", "T2": "T2", "T3": "T3", "T1_gb": "T1"}

SOURCES = (
    "src/ipis/module1_soft_sensor/phase1/__init__.py",
    "src/ipis/module1_soft_sensor/phase1/data.py",
    "src/ipis/module1_soft_sensor/phase1/models.py",
    "src/ipis/module1_soft_sensor/phase1/loops.py",
    "src/ipis/module1_soft_sensor/phase1/metrics.py",
    "src/ipis/module1_soft_sensor/phase1/rules.py",
    "src/ipis/module1_soft_sensor/phase1/record.py",
    "src/ipis/module1_soft_sensor/phase1/stages.py",
    "src/ipis/module1_soft_sensor/phase1/verdicts.py",
    "src/ipis/module1_soft_sensor/evaluation/delayed_aci.py",
    "src/ipis/module1_soft_sensor/evaluation/delay_compensation.py",
    "src/ipis/module1_soft_sensor/evaluation/inference.py",
    "src/ipis/module1_soft_sensor/evaluation/conformal.py",
    "src/ipis/module1_soft_sensor/evaluation/baselines.py",
    "src/ipis/module1_soft_sensor/evaluation/baselines_pid.py",
    "src/ipis/module1_soft_sensor/evaluation/baselines_spci.py",
    "src/ipis/module1_soft_sensor/data/loaders.py",
    "src/ipis/module1_soft_sensor/data/preprocessing.py",
    "scripts/phase1_run.py",
)


def settings() -> dict[str, Any]:
    """Every constant the stages use; stage B stops if stage A ran with others."""
    return {
        "alpha": ALPHA,
        "eps": EPS,
        "window": dat.WINDOW,
        "t3_window": dat.ARMS["T3"].window,
        "max_order": MAX_ORDER,
        "tuning_grid": list(d.TUNING_GRID),
        "cap_factor": 0.8,
        "loops": list(TUNED_LOOPS),
        "projected_bounds": list(lp.PROJECTED_BOUNDS),
        "decay_exponent": 0.5 + lp.DECAY_EPS,
        "policies": list(POLICIES),
        "fixed": dict(FIXED),
        "pid_grid": list(PID_GRID),
        "pid_k_factors": list(b.PID_K_FACTORS),
        "pid_window": b.PID_WINDOW,
        "pid_warm_rows": b.PID_WARM_ROWS,
        "pid_scorecast_min": b.PID_SCORECAST_MIN,
        "pid_coverage_tol": b.PID_DELTA,
        "pid_scale_to": 1.0 - ALPHA,
        "pid_eps": EPS / 2,
        "qr_level": 1.0 - ALPHA / 2,
        "spci_seed": SPCI_SEED,
        "n_boot": rules.N_BOOT,
        "min_blocks": rules.MIN_BLOCKS,
        "sensitivity_skip": SENSITIVITY_SKIP,
    }


# --- parallel map ----------------------------------------------------------------------------

Mapper = Callable[[Callable[[Any], Any], Sequence[Any]], list[Any]]


def _serial(fn: Callable[[Any], Any], jobs: Sequence[Any]) -> list[Any]:
    return [fn(j) for j in jobs]


@contextmanager
def mapper(workers: int) -> Iterator[Mapper]:
    """A map over worker processes (``workers`` > 1) or in this process. Results never depend on
    the number of workers: every job is self-contained and seeds its own random state."""
    if workers <= 1:
        yield _serial
        return
    with Pool(workers) as pool:

        def pmap(fn: Callable[[Any], Any], jobs: Sequence[Any]) -> list[Any]:
            if len(jobs) <= 1:
                return [fn(j) for j in jobs]
            return pool.map(fn, jobs, chunksize=1)

        yield pmap


def run_jobs(
    pmap: Mapper, fn: Callable[[Any], Any], jobs: Sequence[Any], cost: Callable[[Any], float]
) -> list[Any]:
    """``pmap`` with the costliest jobs dispatched first; results in the order of ``jobs``."""
    order = sorted(range(len(jobs)), key=lambda i: -cost(jobs[i]))
    done = pmap(fn, [jobs[i] for i in order])
    out: list[Any] = [None] * len(jobs)
    for i, res in zip(order, done, strict=True):
        out[i] = res
    return out


# --- the units ------------------------------------------------------------------------------


@dataclass
class Stream:
    """One run's residual stream in a unit."""

    regime: str  # a TEP regime, or "debutanizer"
    stream: int  # the TEP stream, or 0
    r: np.ndarray  # residuals: calibration rows, then evaluation rows (stage B)
    y: np.ndarray  # the labels on the same rows
    n_cal: int
    n_ev: int
    info: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.regime}/{self.stream}"


@dataclass
class Unit:
    """A residual source and its settings."""

    name: str  # "debutanizer", "T1", "T2", "T3" or "T1_gb"
    streams: list[Stream]
    thetas: tuple[int, ...]
    primary: int
    window: int
    baselines: bool
    run_length: int  # calibration plus evaluation rows of a stream (C_sat's T, Appendix A.2)
    inputs: dict[str, Any] = field(default_factory=dict)

    def plants(self) -> dict[str, list[int]]:
        """Plant -> indices of its streams (a TEP regime's five runs; the debutanizer alone)."""
        out: dict[str, list[int]] = {}
        for i, s in enumerate(self.streams):
            out.setdefault(s.regime, []).append(i)
        return out


def debutanizer_unit(path: Path, stage: str, precheck: dict[str, Any] | None) -> Unit:
    """The debutanizer stream: the OLS of D-P0.1 on the training rows (it must equal the
    pre-check's coefficients, and its residual autocorrelation the pre-check's), its 1660
    training residuals and, in stage B, the 719 evaluation residuals."""
    rows = dat.load_debutanizer(path, stage)
    ols = pm.fit_ols_lag(rows.u5[: rows.n_train], rows.y[: rows.n_train], dat.DEBUT_LAG)
    r = ols.residuals(rows.u5, rows.y)[dat.DEBUT_LAG :]
    y = rows.y[dat.DEBUT_LAG :]
    n_cal = rows.n_train - dat.DEBUT_LAG
    info: dict[str, Any] = {"ols": {"lag": ols.lag, "intercept": ols.intercept, "slope": ols.slope}}
    if precheck is not None:
        info["precheck"] = _check_precheck(ols, r[:n_cal], precheck)
    stream = Stream("debutanizer", 0, r, y, n_cal, rows.n_ev, info)
    return Unit(
        name="debutanizer",
        streams=[stream],
        thetas=dat.DEBUT_THETAS,
        primary=dat.DEBUT_PRIMARY,
        window=dat.WINDOW,
        baselines=True,
        run_length=n_cal + dat.DEBUT_N_EV,
        inputs={"file": Path(path).as_posix(), "sha256": dat.sha256_file(path)},
    )


def _check_precheck(ols: pm.OLSLag, r_cal: np.ndarray, precheck: dict[str, Any]) -> dict[str, Any]:
    """The point model and its training residuals must be those of the committed pre-check."""
    deb = precheck["debutanizer"]
    point = deb["point_model"]
    same = (
        point["lag"] == ols.lag
        and math.isclose(point["intercept"], ols.intercept, rel_tol=1e-12, abs_tol=1e-12)
        and math.isclose(point["slope"], ols.slope, rel_tol=1e-12, abs_tol=1e-12)
    )
    if not same:
        raise ValueError("the debutanizer OLS differs from the pre-check's (phase1_precheck)")
    if r_cal.size + ols.lag != deb["n_train"]:
        raise ValueError("the training split differs from the pre-check's")
    lags = [int(k) for k in deb["residual_acf"]]
    rho = acf(r_cal, max(lags))
    worst = max(abs(float(rho[k]) - float(deb["residual_acf"][str(k)])) for k in lags)
    if worst > 1e-9:
        raise ValueError(f"the residual autocorrelation differs from the pre-check's by {worst}")
    return {"coefficients": "match", "residual_acf_max_abs_diff": worst}


def _arm_stream(rows: dat.ArmRows, r: np.ndarray, model: dict[str, Any]) -> dict[str, Any]:
    s = r[rows.n_train :]
    if not np.all(np.isfinite(s)):
        raise ValueError("a residual of the calibration or evaluation rows is missing")
    return {
        "r": s,
        "y": rows.y[rows.n_train :],
        "n_cal": rows.n_cal,
        "n_ev": rows.n_ev,
        "model": model,
    }


def _tep_run(job: tuple[str, int, str, str, tuple[str, ...]]) -> dict[str, Any]:
    """Load one TEP run, fit its point models on T1's training rows, and build its streams for
    the requested units (worker). Every arm shares the ridge (Section 7): T1 at 3-min rows with
    its inputs 5 rows back, T2 at 1-min rows with them 15 rows back, T3 at T1's event rows. The
    rows up to 70 h are predicted in one call, as in stage A."""
    regime, stream, path, stage, names = job
    d60 = dat.load_tep_rows(Path(path), stage)
    out: dict[str, Any] = {}
    t1 = dat.arm_rows(d60, dat.ARMS["T1"])
    hold = dat.label_hold(t1)
    n_a = t1.n_train + t1.n_cal
    lag = dat.ARMS["T1"].lag
    if any(n in names for n in ("T1", "T2", "T3")):
        ridge = pm.fit_ridge_one_se(t1.X, t1.y, lag, t1.n_train)
        r1 = ridge.staged_residuals(t1.X, t1.y, n_a)
        if "T1" in names:
            out["T1"] = _arm_stream(
                t1, r1, ridge.info | {"kind": "ridge", "lag": lag, "label_hold": hold}
            )
        if "T3" in names:
            idx = dat.t3_rows(t1.minute)
            idx = idx[idx >= t1.n_train]
            n_cal = int(np.sum(idx < n_a))
            out["T3"] = {
                "r": r1[idx],
                "y": t1.y[idx],
                "n_cal": n_cal,
                "n_ev": int(idx.size - n_cal),
                "model": ridge.info
                | {"kind": "ridge, T1's", "lag": lag, "rows": "T1 event rows", "label_hold": hold},
            }
        if "T2" in names:
            t2 = dat.arm_rows(d60, dat.ARMS["T2"])
            lag2 = dat.ARMS["T2"].lag
            r2 = ridge.at_lag(lag2).staged_residuals(t2.X, t2.y, t2.n_train + t2.n_cal)
            out["T2"] = _arm_stream(
                t2,
                r2,
                ridge.info | {"kind": "ridge, T1's", "lag": lag2, "label_hold": dat.label_hold(t2)},
            )
    if "T1_gb" in names:
        gb = pm.fit_gradient_boosting(t1.X, t1.y, lag, t1.n_train)
        rg = gb.staged_residuals(t1.X, t1.y, n_a)
        out["T1_gb"] = _arm_stream(t1, rg, gb.info | {"kind": "gb", "lag": lag, "label_hold": hold})
    return {"regime": regime, "stream": stream, "units": out}


def tep_units(
    data_dir: Path,
    record: Path,
    stage: str,
    names: Sequence[str],
    pmap: Mapper,
) -> list[Unit]:
    """The requested TEP units, from the 15 runs checked against the qualification record."""
    files = dat.tep_files(data_dir, record)
    jobs = [(f.regime, f.stream, str(f.path), stage, tuple(names)) for f in files]
    runs = pmap(_tep_run, jobs)
    inputs = {
        "record": Path(record).as_posix(),
        "record_sha256": dat.sha256_file(record),
        "files": [{"regime": f.regime, "stream": f.stream, "sha256": f.sha256} for f in files],
    }
    out = []
    for name in names:
        arm = dat.ARMS[TEP_ARM_OF[name]]
        streams = [
            Stream(
                regime=run["regime"],
                stream=run["stream"],
                r=run["units"][name]["r"],
                y=run["units"][name]["y"],
                n_cal=run["units"][name]["n_cal"],
                n_ev=run["units"][name]["n_ev"],
                info={"model": run["units"][name]["model"]},
            )
            for run in runs
        ]
        out.append(
            Unit(
                name=name,
                streams=streams,
                thetas=arm.thetas,
                primary=arm.primary,
                window=arm.window,
                baselines=name == "T1",
                run_length=streams[0].n_cal + TEP_EV_ROWS[name],
                inputs=inputs,
            )
        )
    return out


# --- compensation ---------------------------------------------------------------------------


def _predict(fc: DirectForecaster, r: np.ndarray, n_cal: int) -> np.ndarray:
    """Residual forecasts: the calibration rows by one call on those rows alone (as in stage A,
    so that they agree to the bit), the later rows from the whole stream."""
    out = fc.predict(r[:n_cal])
    if r.size > n_cal:
        out = np.concatenate([out, fc.predict(r)[n_cal:]])
    return out


def compensate(
    r: np.ndarray, theta: int, n_cal: int, fixed: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Section 5.3: the direct (theta + 1)-step forecaster, its order by BIC (1 to 10) and its
    coefficients by least squares, both on the calibration rows only; the compensated scores
    |r - rhat| (rows before the first full lag window keep |r|); and P3's predicted width ratio
    from the calibration autocorrelation, at the BIC order.

    ``fixed`` (stage B): stage A's order and coefficients. The forecaster is refitted and checked
    against them, and the forecasts are made with stage A's coefficients."""
    cal = slice(0, n_cal)
    order = select_order(r, theta, max_order=MAX_ORDER, fit=cal)
    fc = fit_direct_forecaster(r, theta, order=order, fit=cal)
    status = None
    if fixed is not None:
        if order != fixed["order"] or fc.n_fit != fixed["n_fit"]:
            raise ValueError(f"theta {theta}: order {order} against stage A's {fixed['order']}")
        status = rc.close_values(f"forecaster theta={theta}", fc.coef, fixed["coef"])
        fc = DirectForecaster(
            horizon=theta + 1,
            order=order,
            coef=np.asarray(fixed["coef"], dtype=np.float64),
            n_fit=fc.n_fit,
        )
    rhat = _predict(fc, r, n_cal)
    s = np.abs(r)
    c = np.abs(r - rhat)
    c[: fc.warmup] = s[: fc.warmup]
    rh = rhat.copy()
    rh[: fc.warmup] = np.nan
    pred = predicted_width_ratio(acf(r[cal], theta + order + 1), theta, order)
    return {
        "order": int(order),
        "coef": [float(v) for v in fc.coef],
        "n_fit": int(fc.n_fit),
        "warmup": int(fc.warmup),
        "rhat": rh,
        "scores": c,
        "predicted_ratio": float(pred),
        "coef_check": status,
    }


# --- conformal PID scorecasts ------------------------------------------------------------------


def _qr_job(job: tuple[str, int, int, np.ndarray]) -> np.ndarray:
    _, theta, _, x = job
    return b.qr_scorecasts(x, theta + 1, b.PID_SCORECAST_MIN, 1.0 - ALPHA / 2)


def _theta_job(job: tuple[str, int, np.ndarray, int]) -> np.ndarray:
    _, _, x, max_h = job
    return b.theta_forecast_table(x, b.PID_SCORECAST_MIN, max_h)


def scorecasts(
    unit: Unit, rhats: dict[tuple[str, int], np.ndarray], upto: str, pmap: Mapper
) -> dict[tuple[str, int, str], tuple[np.ndarray, np.ndarray]]:
    """The scorecasts of Appendix A.2 per stream, theta and scorecaster, as (lower, upper): the
    lower side tracks -r and the upper side r. ``upto`` is "cal" (the calibration rows, stage A)
    or "all" (stage B). Every scorecaster is causal, so the calibration rows of "all" equal
    "cal"; stage B checks it. One Theta table to the longest horizon serves every theta (A.5)."""
    max_h = max(unit.thetas) + 1
    qr_jobs: list[tuple[str, int, int, np.ndarray]] = []
    th_jobs: list[tuple[str, int, np.ndarray, int]] = []
    for s in unit.streams:
        n = s.n_cal if upto == "cal" else s.r.size
        for side, sign in enumerate((-1.0, 1.0)):
            x = sign * s.r[:n]
            th_jobs.append((s.key, side, x, max_h))
            for theta in unit.thetas:
                qr_jobs.append((s.key, theta, side, x))
    qr = run_jobs(pmap, _qr_job, qr_jobs, lambda j: float(j[3].size) ** 2)
    tables = run_jobs(pmap, _theta_job, th_jobs, lambda j: float(j[2].size) ** 1.5)
    qr_of = {(j[0], j[1], j[2]): c for j, c in zip(qr_jobs, qr, strict=True)}
    table_of = {(j[0], j[1]): t for j, t in zip(th_jobs, tables, strict=True)}
    out: dict[tuple[str, int, str], tuple[np.ndarray, np.ndarray]] = {}
    for s in unit.streams:
        n = s.n_cal if upto == "cal" else s.r.size
        for theta in unit.thetas:
            h = theta + 1
            out[(s.key, theta, "qr")] = (qr_of[(s.key, theta, 0)], qr_of[(s.key, theta, 1)])
            out[(s.key, theta, "theta")] = (
                b.pid_scorecasts(table_of[(s.key, 0)], h, b.PID_SCORECAST_MIN),
                b.pid_scorecasts(table_of[(s.key, 1)], h, b.PID_SCORECAST_MIN),
            )
            out[(s.key, theta, "matched")] = b.matched_scorecasts(rhats[(s.key, theta)][:n])
    return out


def _sc_name(key: str, theta: int, name: str) -> str:
    return f"{key}|theta={theta}|{name}"


# --- stage A --------------------------------------------------------------------------------


def _tune_job(job: tuple[Any, ...]) -> dict[str, Any]:
    """One replay tuning (worker): ``loops.replay_tune``'s output."""
    _, segments, theta_replay, loop, y_range, eps, window = job
    out: dict[str, Any] = lp.replay_tune(
        segments, theta_replay, loop=loop, y_range=y_range, eps=eps, alpha=ALPHA, window=window
    )
    return out


def _pid_tune_job(job: tuple[Any, ...]) -> dict[str, Any]:
    _, segments, h, y_range, c_sats = job
    out: dict[str, Any] = b.pid_tune_pooled(
        segments,
        h,
        alpha=ALPHA,
        y_range=y_range,
        eps=EPS / 2,
        c_sats=c_sats,
        grid=PID_GRID,
        scale_to=1.0 - ALPHA,
    )
    return out


def tuning_targets(theta: int) -> dict[str, tuple[int, float]]:
    """Policy -> (theta of the replay, target): delay-blind replays at theta = 0 (Section 5.3)."""
    return {"blind": (0, EPS), "aware_eps": (theta, EPS), "aware_half": (theta, EPS / 2)}


def spci_seed(unit: Unit, s: Stream) -> int:
    return SPCI_SEED if unit.name == "debutanizer" else SPCI_SEED + s.stream


def stage_a(unit: Unit, pmap: Mapper) -> dict[str, Any]:
    """Everything that is fixed from the calibration rows, for one unit."""
    plants = unit.plants()
    cal_scores: dict[tuple[str, int, str], np.ndarray] = {}
    rhats: dict[tuple[str, int], np.ndarray] = {}
    streams: list[dict[str, Any]] = []
    for s in unit.streams:
        if s.r.size != s.n_cal or s.n_ev != 0:
            raise ValueError("stage A takes calibration rows only")
        entry: dict[str, Any] = {
            "key": s.key,
            "regime": s.regime,
            "stream": s.stream,
            "n_cal": s.n_cal,
            "info": s.info,
            "fp_r": rc.fingerprint(s.r),
            "fp_y": rc.fingerprint(s.y),
            "b_prime": float(np.max(np.abs(s.r))),
            "by_theta": {},
        }
        for theta in unit.thetas:
            fc = compensate(s.r, theta, s.n_cal)
            cal_scores[(s.key, theta, "raw")] = np.abs(s.r)
            cal_scores[(s.key, theta, "comp")] = fc["scores"]
            rhats[(s.key, theta)] = fc["rhat"]
            entry["by_theta"][str(theta)] = {
                "order": fc["order"],
                "coef": fc["coef"],
                "n_fit": fc["n_fit"],
                "warmup": fc["warmup"],
                "predicted_ratio": fc["predicted_ratio"],
                "fp_comp": rc.fingerprint(fc["scores"]),
                "static_q": {
                    c: conformal_quantile(cal_scores[(s.key, theta, c)], 1.0 - ALPHA) for c in COMPS
                },
            }
        streams.append(entry)

    y_range = {
        plant: float(np.ptp(np.concatenate([unit.streams[i].y for i in idx])))
        for plant, idx in plants.items()
    }
    w = unit.window
    jobs = []
    for plant, idx in plants.items():
        for theta in unit.thetas:
            for comp in COMPS:
                segs = [
                    (
                        cal_scores[(unit.streams[i].key, theta, comp)][w:],
                        cal_scores[(unit.streams[i].key, theta, comp)][:w],
                    )
                    for i in idx
                ]
                for loop in TUNED_LOOPS:
                    for policy, (th_replay, eps) in tuning_targets(theta).items():
                        key = (plant, theta, comp, loop, policy)
                        jobs.append((key, segs, th_replay, loop, y_range[plant], eps, w))
    tuned = run_jobs(pmap, _tune_job, jobs, lambda j: float(sum(s[0].size for s in j[1])))
    tuning: dict[str, Any] = {}
    for job, res in zip(jobs, tuned, strict=True):
        plant, theta, comp, loop, policy = job[0]
        node = tuning.setdefault(plant, {}).setdefault(str(theta), {}).setdefault(comp, {})
        node.setdefault(loop, {})[policy] = res

    predictions = {}
    for theta in unit.thetas:
        per = {e["key"]: e["by_theta"][str(theta)]["predicted_ratio"] for e in streams}
        mean = float(np.mean(list(per.values())))
        predictions[str(theta)] = {
            "per_stream": per,
            "mean": mean,
            "f8_gate_met": bool(mean <= rules.F8_GATE + rules.TOL),
        }
    out: dict[str, Any] = {
        "stage": "A",
        "unit": unit.name,
        "thetas": list(unit.thetas),
        "primary": unit.primary,
        "window": unit.window,
        "run_length": unit.run_length,
        "inputs": unit.inputs,
        "settings": settings(),
        "streams": streams,
        "y_range": y_range,
        "design_gamma": {str(theta): d.design_gamma(theta) for theta in unit.thetas},
        "tuning": tuning,
        "predictions": predictions,
    }
    if unit.baselines:
        out["pid"] = _pid_stage_a(unit, rhats, y_range, pmap)
        out["spci"] = {
            "w": b.spci_window(unit.streams[0].n_cal),
            "train_len": unit.streams[0].n_cal,
            "seeds": {s.key: spci_seed(unit, s) for s in unit.streams},
        }
    return out


def _pid_stage_a(
    unit: Unit,
    rhats: dict[tuple[str, int], np.ndarray],
    y_range: dict[str, float],
    pmap: Mapper,
) -> dict[str, Any]:
    """Conformal PID's replay tuning on the calibration rows (Appendix A.2)."""
    sc = scorecasts(unit, rhats, "cal", pmap)
    c_sats = b.pid_c_sat_grid(unit.run_length)
    jobs = []
    for plant, idx in unit.plants().items():
        for theta in unit.thetas:
            for name in SCORECASTERS:
                segs = [
                    (
                        unit.streams[i].r,
                        sc[(unit.streams[i].key, theta, name)],
                        float(np.max(np.abs(unit.streams[i].r))),
                    )
                    for i in idx
                ]
                jobs.append(((plant, theta, name), segs, theta + 1, y_range[plant], c_sats))
    tuned = run_jobs(pmap, _pid_tune_job, jobs, lambda j: float(sum(s[0].size for s in j[1])))
    out: dict[str, Any] = {
        "c_sats": list(c_sats),
        "scorecast_fp": {
            _sc_name(k, th, name): [rc.fingerprint(v[0]), rc.fingerprint(v[1])]
            for (k, th, name), v in sc.items()
        },
        "tuning": {},
    }
    for job, res in zip(jobs, tuned, strict=True):
        plant, theta, name = job[0]
        node = out["tuning"].setdefault(plant, {}).setdefault(str(theta), {})
        node[name] = {"config": res["config"], "flag": res["flag"], "path": res["path"]}
    return out


# --- stage B: consistency with stage A ------------------------------------------------------


@dataclass
class Prepared:
    """A stream's full score streams at every theta, built with stage A's forecasters."""

    raw: np.ndarray
    comp: dict[int, np.ndarray]
    rhat: dict[int, np.ndarray]


def _stage_a_entry(a: dict[str, Any], key: str) -> dict[str, Any]:
    for e in a["streams"]:
        if e["key"] == key:
            out: dict[str, Any] = e
            return out
    raise KeyError(key)


def _input_hashes(inputs: dict[str, Any]) -> dict[str, Any]:
    """The inputs without their paths: stage B may read the same files from another place."""
    return {k: v for k, v in inputs.items() if k not in ("file", "record")}


def prepare(unit: Unit, a: dict[str, Any]) -> tuple[dict[str, Prepared], dict[str, Any]]:
    """Recompute stage A's calibration quantities from the full files, check them against the
    record, and build every stream's scores with stage A's forecasters. Returns the scores and
    the outcome of each check ("exact" or "close"); a quantity that differs stops the run."""
    if a["unit"] != unit.name or a["stage"] != "A":
        raise ValueError(f"{unit.name}: not this unit's stage A record")
    if a["settings"] != rc.from_jsonable(rc.to_jsonable(settings())):
        raise ValueError(f"{unit.name}: stage A ran with other settings")
    if [e["key"] for e in a["streams"]] != [s.key for s in unit.streams]:
        raise ValueError(f"{unit.name}: the streams differ from stage A's")
    if _input_hashes(rc.to_jsonable(unit.inputs)) != _input_hashes(a["inputs"]):
        raise ValueError(f"{unit.name}: the input files differ from stage A's")
    checks: dict[str, Any] = {}
    prepared: dict[str, Prepared] = {}
    for s, e in zip(unit.streams, a["streams"], strict=True):
        n = s.n_cal
        if n != e["n_cal"] or s.n_ev <= 0 or s.r.size != n + s.n_ev:
            raise ValueError(f"{s.key}: {n} calibration rows against stage A's {e['n_cal']}")
        c: dict[str, Any] = {
            "r": rc.check_fingerprint(f"{s.key} residuals", rc.fingerprint(s.r[:n]), e["fp_r"]),
            "y": rc.check_fingerprint(f"{s.key} labels", rc.fingerprint(s.y[:n]), e["fp_y"]),
            "b_prime": rc.close_values(f"{s.key} B'", float(np.max(np.abs(s.r[:n]))), e["b_prime"]),
        }
        _check_model(s, e, c)
        comp, rhat = {}, {}
        for theta in unit.thetas:
            want = e["by_theta"][str(theta)]
            out = compensate(s.r, theta, n, fixed=want)
            pre = f"{s.key} theta={theta}"
            c[f"theta={theta}"] = {
                "coef": out["coef_check"],
                "scores": rc.check_fingerprint(
                    f"{pre} scores", rc.fingerprint(out["scores"][:n]), want["fp_comp"]
                ),
                "predicted_ratio": rc.close_values(
                    f"{pre} prediction", out["predicted_ratio"], want["predicted_ratio"]
                ),
                "static_q": {
                    k: rc.close_values(
                        f"{pre} static {k}",
                        conformal_quantile(
                            (np.abs(s.r) if k == "raw" else out["scores"])[:n], 1.0 - ALPHA
                        ),
                        want["static_q"][k],
                    )
                    for k in COMPS
                },
            }
            comp[theta], rhat[theta] = out["scores"], out["rhat"]
        prepared[s.key] = Prepared(raw=np.abs(s.r), comp=comp, rhat=rhat)
        checks[s.key] = c
    for plant, idx in unit.plants().items():
        got = float(
            np.ptp(np.concatenate([unit.streams[i].y[: unit.streams[i].n_cal] for i in idx]))
        )
        checks[f"y_range {plant}"] = rc.close_values(f"y_range {plant}", got, a["y_range"][plant])
    return prepared, checks


def _check_model(s: Stream, e: dict[str, Any], c: dict[str, Any]) -> None:
    """The refitted point model must be stage A's: the debutanizer OLS, or the TEP model's kind
    and lag, and for ridge its penalty and coefficients. (The label hold is checked on all rows
    by ``data.label_hold`` in both stages.)"""
    if "ols" in s.info:
        got_o, want_o = s.info["ols"], e["info"]["ols"]
        c["ols"] = rc.close_values(
            f"{s.key} OLS",
            [got_o["intercept"], got_o["slope"]],
            [want_o["intercept"], want_o["slope"]],
        )
        return
    got, want = s.info["model"], e["info"]["model"]
    if got.get("kind") != want.get("kind") or got.get("lag") != want.get("lag"):
        raise ValueError(f"{s.key}: the point model differs from stage A's")
    if "alpha" in want:
        if got["alpha"] != want["alpha"]:
            raise ValueError(f"{s.key}: ridge penalty {got['alpha']} against {want['alpha']}")
        c["ridge"] = rc.close_values(
            f"{s.key} ridge",
            [got["intercept"], *got["coef_standardised"]],
            [want["intercept"], *want["coef_standardised"]],
        )


# --- stage B: the loop cells ----------------------------------------------------------------


def cell_key(theta: int, comp: str, loop: str, policy: str, pairing: str = "stored") -> str:
    return f"theta={theta}|{comp}|{loop}|{policy}|{pairing}"


def gamma_of(a: dict[str, Any], plant: str, theta: int, comp: str, loop: str, policy: str) -> float:
    """The step size of a cell: fixed, tuned in stage A, or design_gamma(theta)."""
    if policy in FIXED:
        return FIXED[policy]
    if policy == "design":
        return float(a["design_gamma"][str(theta)])
    return float(a["tuning"][plant][str(theta)][comp][loop][policy]["gamma"])


def pairings_of(primary: int, theta: int, loop: str) -> tuple[str, ...]:
    """Arrival pairing, the negative control, runs at theta_doc (the unit's primary theta) on the
    sequential loop, at every policy and with the stored-pairing step size; every other cell is
    stored."""
    if loop == "sequential" and theta == primary and theta > 0:
        return ("stored", "arrival")
    return ("stored",)


def _steps(res: dict[str, np.ndarray], y_range: float) -> dict[str, np.ndarray]:
    return {
        "u": d.uninformative(res["h"], y_range).astype(np.int8),
        "inf": (~np.isfinite(res["h"])).astype(np.int8),
        "cov": res["covered"].astype(np.int8),
    }


def _cells_job(job: tuple[Any, ...]) -> dict[str, Any]:
    """Every loop cell of one stream at one theta (worker), the open-loop miss indicator of F8,
    and the measured width ratio of F6 and the analyzer-speed chart."""
    (key, theta, primary, window, n_cal, y_range, scores, static_q, gammas, feas, keep) = job
    cells: dict[str, Any] = {}
    steps: dict[str, Any] = {}
    open_loop: dict[str, Any] = {}
    for comp in COMPS:
        full = scores[comp]
        cal, ev = full[:n_cal], full[n_cal:]
        init = cal[-window:]
        h = np.full(ev.size, float(static_q[comp]))
        res = {"h": h, "covered": ev <= h, "alpha": np.full(ev.size, ALPHA)}
        k = cell_key(theta, comp, "none", "-")
        cells[k] = mt.loop_metrics(res, y_range) | mt.persistence((~res["covered"]).astype(float))
        if keep:
            steps[k] = _steps(res, y_range)
        for loop in TUNED_LOOPS:
            for policy in POLICIES:
                gamma = gammas[(comp, loop, policy)]
                for pairing in pairings_of(primary, theta, loop):
                    k = cell_key(theta, comp, loop, policy, pairing)
                    if not math.isfinite(gamma):
                        cells[k] = {"not_run": "design_gamma is undefined at this theta"}
                        continue
                    res = lp.run_loop(
                        ev,
                        theta,
                        loop=loop,
                        init_scores=init,
                        gamma=gamma,
                        alpha=ALPHA,
                        window=window,
                        pairing=pairing,
                    )
                    m = mt.loop_metrics(res, y_range)
                    m |= mt.persistence((~res["covered"]).astype(float))
                    m["gamma"] = gamma
                    if policy in TUNED:
                        m["tuning_feasible"] = feas[(comp, loop, policy)]
                    cells[k] = m
                    if keep:
                        steps[k] = _steps(res, y_range)
        ol = d.run_delayed_aci(ev, theta, init_scores=init, alpha=ALPHA, gamma=0.0, window=window)
        err = (~ol["covered"]).astype(float)
        open_loop[comp] = mt.persistence(err) | {"miss_rate": float(err.mean())}
    raw_ev, comp_ev = scores["raw"][n_cal:], scores["comp"][n_cal:]
    measured = float(np.quantile(comp_ev, 1 - ALPHA) / np.quantile(raw_ev, 1 - ALPHA))
    return {
        "key": key,
        "theta": theta,
        "cells": cells,
        "steps": steps,
        "open_loop": open_loop,
        "measured_ratio": measured,
    }


# --- stage B: the baselines -----------------------------------------------------------------


def _indicator_steps(width: np.ndarray, cov: np.ndarray, y_range: float) -> dict[str, np.ndarray]:
    return {
        "u": b.uninformative_width(width, y_range).astype(np.int8),
        "inf": (~np.isfinite(width)).astype(np.int8),
        "cov": np.asarray(cov).astype(np.int8),
    }


def _pid_eval_job(job: tuple[Any, ...]) -> dict[str, Any]:
    """One conformal PID run (worker): from calibration row 200 to the last evaluation row,
    seeded from rows 0-199 (Appendix A.1, A.2); metrics on the evaluation rows, and the replay
    rows for the check against stage A."""
    key, theta, name, r, scs, cfg, b_prime, n_cal, y_range, keep = job
    o = b.conformal_pid_intervals(
        r,
        ALPHA,
        cfg["m"],
        theta + 1,
        window=b.PID_WINDOW,
        k_i=cfg["k_factor"] * b_prime,
        c_sat=cfg["c_sat"],
        scorecasts=scs,
        start=b.PID_WINDOW,
        warm_rows=b.PID_WARM_ROWS,
    )
    rep = slice(b.PID_WINDOW, n_cal)
    width, cov = o["width"][n_cal:], o["covered"][n_cal:]
    metrics = mt.interval_metrics(width, cov, y_range) | mt.persistence((~cov).astype(float))
    metrics["empty_share"] = float(np.mean(o["empty"][n_cal:]))
    return {
        "key": key,
        "theta": theta,
        "name": f"pid_{name}",
        "metrics": metrics,
        "replay": {
            "u_flags": b.uninformative_width(o["width"][rep], y_range),
            "covered": o["covered"][rep],
            "width": o["width"][rep],
        },
        "steps": _indicator_steps(width, cov, y_range) if keep else None,
    }


def _spci_job(job: tuple[Any, ...]) -> dict[str, Any]:
    """One SPCI run (worker), from the first evaluation row (Appendix A.1, A.3)."""
    key, theta, r, n_cal, w, seed, y_range, keep = job
    o = b.spci_rolling(
        r,
        n_cal,
        ALPHA,
        theta + 1,
        w=w,
        train_len=n_cal,
        random_state=np.random.RandomState(seed),
    )
    lo, hi = o["lo"][n_cal:], o["hi"][n_cal:]
    x = r[n_cal:]
    empty = lo > hi
    width = np.where(empty, 0.0, hi - lo)
    cov = (lo <= x) & (x <= hi)
    metrics = mt.interval_metrics(width, cov, y_range) | mt.persistence((~cov).astype(float))
    metrics |= {"empty_share": float(np.mean(empty)), "w": int(w), "seed": int(seed)}
    return {
        "key": key,
        "theta": theta,
        "name": "spci",
        "metrics": metrics,
        "steps": _indicator_steps(width, cov, y_range) if keep else None,
    }


def baselines_stage_b(
    unit: Unit, a: dict[str, Any], prepared: dict[str, Prepared], keep: bool, pmap: Mapper
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Conformal PID with stage A's configurations, and SPCI (Appendix A.2 and A.3). Returns the
    per-stream metrics, the per-step flags (debutanizer) and the checks against stage A."""
    rhats = {(s.key, th): prepared[s.key].rhat[th] for s in unit.streams for th in unit.thetas}
    sc = scorecasts(unit, rhats, "all", pmap)
    checks: dict[str, Any] = {}
    n_cal_of = {s.key: s.n_cal for s in unit.streams}
    for (k, theta_k, name), v in sc.items():
        n = n_cal_of[k]
        label = _sc_name(k, theta_k, name)
        want = a["pid"]["scorecast_fp"][label]
        checks[label] = [
            rc.check_fingerprint(f"{label} lower", rc.fingerprint(v[0][:n]), want[0]),
            rc.check_fingerprint(f"{label} upper", rc.fingerprint(v[1][:n]), want[1]),
        ]
    pid_jobs, spci_jobs = [], []
    for s in unit.streams:
        y_range = a["y_range"][s.regime]
        b_prime = float(_stage_a_entry(a, s.key)["b_prime"])
        for theta in unit.thetas:
            for name in SCORECASTERS:
                cfg = a["pid"]["tuning"][s.regime][str(theta)][name]["config"]
                scs = sc[(s.key, theta, name)]
                pid_jobs.append(
                    (s.key, theta, name, s.r, scs, cfg, b_prime, s.n_cal, y_range, keep)
                )
            seed = a["spci"]["seeds"][s.key]
            spci_jobs.append((s.key, theta, s.r, s.n_cal, a["spci"]["w"], seed, y_range, keep))
    pid = run_jobs(pmap, _pid_eval_job, pid_jobs, lambda j: float(j[3].size))
    spci = run_jobs(
        pmap, _spci_job, spci_jobs, lambda j: float(j[2].size - j[3]) * j[4] * j[3] * 1e-3
    )
    metrics: dict[str, Any] = {}
    steps: dict[str, Any] = {}
    for res in [*pid, *spci]:
        th = str(res["theta"])
        metrics.setdefault(th, {}).setdefault(res["name"], {})[res["key"]] = res["metrics"]
        if res["steps"] is not None:
            steps.setdefault(th, {})[res["name"]] = res["steps"]
    checks["pid_replay"] = _check_pid_replay(unit, a, pid)
    return metrics, steps, checks


def _check_pid_replay(unit: Unit, a: dict[str, Any], pid: list[dict[str, Any]]) -> dict[str, Any]:
    """The calibration rows of each evaluation run of conformal PID are its replay: pooled over a
    plant's streams, they must give the U, coverage and median width stage A recorded for the
    configuration it selected."""
    out: dict[str, Any] = {}
    by = {(r["key"], r["theta"], r["name"]): r["replay"] for r in pid}
    for plant, idx in unit.plants().items():
        for theta in unit.thetas:
            for name in SCORECASTERS:
                reps = [by[(unit.streams[i].key, theta, f"pid_{name}")] for i in idx]
                got = [
                    float(np.mean(np.concatenate([r["u_flags"] for r in reps]))),
                    float(np.mean(np.concatenate([r["covered"] for r in reps]))),
                    float(np.median(np.concatenate([r["width"] for r in reps]))),
                ]
                cfg = a["pid"]["tuning"][plant][str(theta)][name]["config"]
                want = [cfg["u"], cfg["coverage"], cfg["median_width"]]
                out[f"{plant}|theta={theta}|{name}"] = rc.close_values(
                    f"{plant} theta={theta} {name} replay", got, want
                )
    return out


# --- stage B --------------------------------------------------------------------------------


def stage_b(unit: Unit, a: dict[str, Any], pmap: Mapper) -> tuple[dict[str, Any], dict[str, Any]]:
    """Every cell of one unit on its evaluation rows, with stage A's settings. Returns the record
    and, for the debutanizer, the per-step flags of every cell (else empty)."""
    prepared, checks = prepare(unit, a)
    keep = unit.name == "debutanizer"
    jobs = []
    for s in unit.streams:
        entry = _stage_a_entry(a, s.key)
        for theta in unit.thetas:
            gammas: dict[tuple[str, str, str], float] = {}
            feas: dict[tuple[str, str, str], bool] = {}
            for comp in COMPS:
                for loop in TUNED_LOOPS:
                    for policy in POLICIES:
                        gammas[(comp, loop, policy)] = gamma_of(
                            a, s.regime, theta, comp, loop, policy
                        )
                        if policy in TUNED:
                            node = a["tuning"][s.regime][str(theta)][comp][loop][policy]
                            feas[(comp, loop, policy)] = bool(node["feasible"])
            jobs.append(
                (
                    s.key,
                    theta,
                    unit.primary,
                    unit.window,
                    s.n_cal,
                    a["y_range"][s.regime],
                    {"raw": prepared[s.key].raw, "comp": prepared[s.key].comp[theta]},
                    entry["by_theta"][str(theta)]["static_q"],
                    gammas,
                    feas,
                    keep,
                )
            )
    results = run_jobs(pmap, _cells_job, jobs, lambda j: float(j[6]["raw"].size))
    out: dict[str, Any] = {
        "stage": "B",
        "unit": unit.name,
        "thetas": list(unit.thetas),
        "primary": unit.primary,
        "streams": [s.key for s in unit.streams],
        "regime_of": {s.key: s.regime for s in unit.streams},
        "n_ev": {s.key: s.n_ev for s in unit.streams},
        "checks": checks,
        "cells": {},
        "open_loop": {},
        "measured_ratio": {},
        "predicted_ratio": {str(th): a["predictions"][str(th)]["per_stream"] for th in unit.thetas},
    }
    steps: dict[str, Any] = {}
    for res in results:
        th = str(res["theta"])
        for k, m in res["cells"].items():
            out["cells"].setdefault(k, {})[res["key"]] = m
        for comp, m in res["open_loop"].items():
            out["open_loop"].setdefault(th, {}).setdefault(comp, {})[res["key"]] = m
        out["measured_ratio"].setdefault(th, {})[res["key"]] = res["measured_ratio"]
        steps.update(res["steps"])
    if unit.baselines:
        base, base_steps, base_checks = baselines_stage_b(unit, a, prepared, keep, pmap)
        out["baselines"] = base
        out["checks"]["baselines"] = base_checks
        out["f7"] = f7_all(unit, out, prepared)
        for th, row in base_steps.items():
            for name, st in row.items():
                steps[f"theta={th}|{name}"] = st
    if keep:
        out["intervals"] = debutanizer_intervals(steps, pmap)
    else:
        out["summary"] = tep_summary(unit, out)
    return out, steps


def f7_all(unit: Unit, out: dict[str, Any], prepared: dict[str, Prepared]) -> dict[str, Any]:
    """F7's comparison of every baseline with the compensated loop (sequential, stored, tuned to
    eps / 2) at every theta of the unit (Section 6, Appendix A.1, D-P1.11, D-P1.14). It decides
    nothing here: the verdicts take theta = 4 of T1; the other cells are descriptive."""
    keys = [s.key for s in unit.streams]
    res: dict[str, Any] = {}
    for theta in unit.thetas:
        pooled = {
            plant: np.concatenate(
                [prepared[unit.streams[i].key].comp[theta][: unit.streams[i].n_cal] for i in idx]
            )
            for plant, idx in unit.plants().items()
        }
        cal = [pooled[s.regime] for s in unit.streams]
        loop = out["cells"][cell_key(theta, "comp", "sequential", "aware_half")]
        loop_runs = [loop[k] for k in keys]
        min_runs = F7_MIN_RUNS if len(keys) == F7_RUNS else len(keys)
        row: dict[str, Any] = {}
        for name in BASELINES:
            runs = [out["baselines"][str(theta)][name][k] for k in keys]
            row[name] = rules.f7_compare(
                runs, loop_runs, eps=EPS, min_runs=min_runs, calibration_scores=cal
            )
        row["verdict_if_decided_here"] = rules.f7_verdict({n: row[n] for n in BASELINES})
        row["min_runs"] = min_runs
        res[str(theta)] = row
    return res


# --- Section 7 ------------------------------------------------------------------------------

TEP_METRICS = (
    "u",
    "infinite_share",
    "coverage",
    "local_cov_sd",
    "local_cov_min",
    "under_coverage_steps",
    "alpha_sd",
    "width_median",
    "f7_median_width",
    "acf1",
    "mean_miss_run",
    "iact",
)
DIFF_METRICS = (
    "u",
    "infinite_share",
    "coverage",
    "local_cov_min",
    "width_median",
    "f7_median_width",
    "acf1",
    "mean_miss_run",
    "iact",
)


def runs_summary(
    per_stream: dict[str, dict[str, Any]], regime_of: dict[str, str]
) -> dict[str, Any]:
    """Section 7 for TEP: mean and 95 % t interval over the runs, with the regime means, and the
    Wilson interval of the coverage pooled over the runs."""
    keys = list(per_stream)
    out: dict[str, Any] = {}
    for m in TEP_METRICS:
        if any(m not in per_stream[k] for k in keys):
            continue
        vals = [float(per_stream[k][m]) for k in keys]
        regimes: dict[str, list[float]] = {}
        for k, v in zip(keys, vals, strict=True):
            regimes.setdefault(regime_of[k], []).append(v)
        out[m] = rules.t_interval(vals, 0.95) | {
            "regime_means": {g: float(np.mean(v)) for g, v in regimes.items()}
        }
    covered = sum(int(per_stream[k]["covered_count"]) for k in keys)
    n = sum(int(per_stream[k]["n"]) for k in keys)
    out["pooled_coverage"] = rules.f3(covered, n)
    return out


def paired_runs(
    x: dict[str, dict[str, Any]], y: dict[str, dict[str, Any]], metrics: Sequence[str]
) -> dict[str, Any]:
    """Differences between two cells paired by run, with 95 % t intervals."""
    keys = list(x)
    out = {}
    for m in metrics:
        if any(m not in x[k] or m not in y[k] for k in keys):
            continue
        out[m] = rules.t_interval([float(x[k][m]) - float(y[k][m]) for k in keys], 0.95)
    return out


CONTRASTS = (
    "comp_minus_raw",
    "theta_minus_0",
    "arrival_minus_stored",
    "loop_on_minus_off",
    "loop_minus_sequential",
    "policy_minus_aware_half",
)


def contrasts(cells: Sequence[str]) -> dict[str, list[tuple[str, str, str]]]:
    """The one-factor contrasts reported (Section 7: "Each comparison varies one factor"), each
    a list of (label, cell, control cell) with both cells present:
    - compensated minus raw (R4.9's compensation arm);
    - theta minus theta = 0, stored pairing (the delay; F2's contrast in its own cell);
    - arrival minus stored pairing (the negative control);
    - loop on minus loop off: the sequential loop at each policy minus static split conformal
      (R4.9's loop arm);
    - each comparison loop minus the sequential loop, at the same policy;
    - each policy minus delay-aware tuning to eps / 2 (the remedy of N1' and F5), on the same
      loop: delay-blind and the white-noise rule against replay (N1' bullet 3), eps against
      eps / 2, and the fixed step sizes."""
    have = set(cells)
    out: dict[str, list[tuple[str, str, str]]] = {name: [] for name in CONTRASTS}

    def add(name: str, label: str, k: str, control: str) -> None:
        if control in have:
            out[name].append((label, k, control))

    for k in sorted(have):
        theta, comp, loop, policy, pairing = k.split("|")
        if comp == "comp":
            add(
                "comp_minus_raw",
                "|".join((theta, loop, policy, pairing)),
                k,
                "|".join((theta, "raw", loop, policy, pairing)),
            )
        if theta != "theta=0" and pairing == "stored":
            add("theta_minus_0", k, k, "|".join(("theta=0", comp, loop, policy, pairing)))
        if pairing == "arrival":
            add("arrival_minus_stored", k, k, "|".join((theta, comp, loop, policy, "stored")))
            continue
        if loop == "sequential":
            add("loop_on_minus_off", k, k, "|".join((theta, comp, "none", "-", "stored")))
        elif loop != "none":
            add(
                "loop_minus_sequential",
                k,
                k,
                "|".join((theta, comp, "sequential", policy, pairing)),
            )
        if loop != "none" and policy != "aware_half":
            add(
                "policy_minus_aware_half",
                k,
                k,
                "|".join((theta, comp, loop, "aware_half", pairing)),
            )
    return out


def _ran(per_stream: dict[str, Any]) -> bool:
    return all("not_run" not in m for m in per_stream.values())


def tep_summary(unit: Unit, out: dict[str, Any]) -> dict[str, Any]:
    """Section 7 for a TEP unit: every cell over the 15 runs, the one-factor contrasts paired by
    run, and the baselines."""
    regime_of = out["regime_of"]
    cells = out["cells"]
    ran = [k for k, per in cells.items() if _ran(per)]
    res: dict[str, Any] = {
        "cells": {k: runs_summary(cells[k], regime_of) for k in ran},
        "contrasts": {
            name: {label: paired_runs(cells[k], cells[c], DIFF_METRICS) for label, k, c in rows}
            for name, rows in contrasts(ran).items()
        },
    }
    if unit.baselines:
        res["baselines"] = {
            th: {name: runs_summary(per, regime_of) for name, per in row.items()}
            for th, row in out["baselines"].items()
        }
    return res


def _ci_job(job: tuple[str, dict[str, np.ndarray]]) -> tuple[str, dict[str, Any]]:
    k, st = job
    full = {m: rules.block_ci(st[m]) for m in ("u", "inf", "cov")}
    tail = {m: rules.block_ci(st[m][SENSITIVITY_SKIP:]) for m in ("u", "inf", "cov")}
    return k, {"all_rows": full, "without_first_100": tail}


def _paired_job(job: tuple[str, str, np.ndarray, np.ndarray]) -> tuple[str, str, dict[str, Any]]:
    name, label, x, y = job
    return (
        name,
        label,
        {
            "all_rows": rules.paired_block_ci(x, y),
            "without_first_100": rules.paired_block_ci(x[SENSITIVITY_SKIP:], y[SENSITIVITY_SKIP:]),
        },
    )


def debutanizer_intervals(steps: dict[str, dict[str, np.ndarray]], pmap: Mapper) -> dict[str, Any]:
    """Section 7 for the single debutanizer stream: a circular block bootstrap interval for U,
    the infinite share and coverage of every cell and baseline, with and without the first 100
    rows (Section 5.1's sensitivity analysis); and paired intervals, both arms on the same
    blocks, for the one-factor contrasts of U and coverage."""
    singles = run_jobs(pmap, _ci_job, sorted(steps.items()), lambda j: 1.0)
    loop_cells = [k for k in steps if k.count("|") == 4]
    pjobs = []
    for name, rows in contrasts(loop_cells).items():
        for label, k, c in rows:
            for m in ("u", "cov"):
                pjobs.append((name, f"{label}|{m}", steps[k][m], steps[c][m]))
    paired = run_jobs(pmap, _paired_job, pjobs, lambda j: 1.0)
    out: dict[str, Any] = {"cells": dict(singles), "contrasts": {}}
    for name, label, ci in paired:
        out["contrasts"].setdefault(name, {})[label] = ci
    return out


def steps_record(steps: dict[str, dict[str, np.ndarray]]) -> dict[str, Any]:
    """The debutanizer's per-step flags as strings of 0 and 1, for any later paired analysis."""
    return {
        k: {m: "".join(str(int(v)) for v in np.asarray(arr).tolist()) for m, arr in st.items()}
        for k, st in sorted(steps.items())
    }
