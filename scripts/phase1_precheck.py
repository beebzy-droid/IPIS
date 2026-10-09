"""N1 Phase 1 pre-checks on the TRAINING split only (pre-registration, D-P1.2 and D-P1.6).

1. Label cadence. Is the recorded quality variable a held analyzer value? Reports the share of
   samples equal to their predecessor and the run lengths of equal values, for the label and for
   a continuously measured reference input. A value held between analyzer updates every C minutes
   and recorded every Ts < C minutes repeats in a share of about 1 - Ts / C of the samples:
   0.6 for Ts = 6 min and 0.2 for Ts = 12 min with the 15-min debutanizer GC (Fortuna et al.
   2007 state Ts = 6 min in Sec. 4.1 and Ts = 12 min in Sec. 6.2), 0.8 for the 0.25 h TEP product
   analyzer recorded every 0.05 h (Downs and Vogel 1993, Table 5). A share near zero means the
   label was not recorded as a held value, and then nothing about Ts is implied.
2. Residual persistence of the ratified debutanizer point model (D-P0.1: OLS on u5 at the lag
   frozen in docs/paper/evidence/debutanizer_lag_scan.json), in-sample on the training split:
   residual autocorrelation and integrated autocorrelation time (IACT).
3. Persistence of the open-loop miss indicator on the same residuals (level fixed at alpha*,
   sliding window R = 200 fed with loop dead time theta in {0, 3, 7}, the documented debutanizer
   delays at Ts = 12 and 6 min in the library's convention theta = label age - 1): the
   disturbance that drives the calibration loop.

Validation and test rows are never read. Run from the repository root:

    set PYTHONPATH=src
    python scripts\\phase1_precheck.py --json
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")
DEFAULT_TEP_DIR = Path("data/raw/tep")
ACF_LAGS = (1, 2, 3, 5, 10, 15, 20, 30, 50, 100)
ALPHA, WINDOW, BURN = 0.10, 200, 200


def repeat_profile(x: np.ndarray, max_run: int = 10) -> dict:
    """Share of samples equal to their predecessor, and the run-length histogram of equal values."""
    x = np.asarray(x, dtype=float)
    same = x[1:] == x[:-1]
    breaks = np.flatnonzero(~same) + 1
    runs = np.diff(np.concatenate(([0], breaks, [x.size])))
    hist = {str(k): int(np.sum(runs == k)) for k in range(1, max_run + 1)}
    hist[f">{max_run}"] = int(np.sum(runs > max_run))
    return {
        "repeat_share": float(same.mean()),
        "mean_run": float(runs.mean()),
        "n_runs": int(runs.size),
        "run_hist": hist,
    }


def mean_run_of(x: np.ndarray, value: float) -> float:
    """Mean length of the runs in which x equals value (0.0 if there are none)."""
    hit = np.concatenate(([False], np.asarray(x) == value, [False])).astype(int)
    edges = np.diff(hit)
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return float((ends - starts).mean()) if starts.size else 0.0


def implied_ts(label: dict, reference: dict, cycle_min: float) -> float | None:
    """Recording interval implied by a held label, Ts = C (1 - repeat share); None if not held.

    Held means the label repeats in at least 10 % of samples while the continuously measured
    reference input repeats in under 5 %.
    """
    held = label["repeat_share"] >= 0.1 and reference["repeat_share"] < 0.05
    return cycle_min * (1.0 - label["repeat_share"]) if held else None


def acf(x: np.ndarray, lags) -> dict:
    x = np.asarray(x, dtype=float) - np.mean(x)
    c0 = float(np.dot(x, x))
    return {str(k): float(np.dot(x[:-k], x[k:]) / c0) for k in lags if k < x.size}


def iact(x: np.ndarray, c: float = 5.0) -> float:
    """Integrated autocorrelation time with Sokal's automatic window (smallest M >= c tau(M))."""
    x = np.asarray(x, dtype=float) - np.mean(x)
    n = x.size
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f))[:n]
    rho = r / r[0]
    tau = 1.0
    for m in range(1, n):
        tau = 1.0 + 2.0 * float(rho[1 : m + 1].sum())
        if m >= c * tau:
            break
    return tau


def debutanizer(path: Path, cycle_min: float, lag: int | None = None) -> dict:
    """All debutanizer pre-checks on the training split; lag defaults to the frozen evidence."""
    from ipis.module1_soft_sensor.data.loaders import DebutanizerLoader
    from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
    from ipis.module1_soft_sensor.evaluation.delayed_aci import run_delayed_aci

    split = time_ordered_split(DebutanizerLoader().load(path))
    tr = split.train
    if lag is None:
        from ipis.shared.evidence import load_evidence

        lag = int(load_evidence("debutanizer_lag_scan")["argmax_lag"])
    y_rep, u_rep = repeat_profile(tr["y"].to_numpy()), repeat_profile(tr["u5"].to_numpy())
    ts_implied = implied_ts(y_rep, u_rep, cycle_min)
    held = ts_implied is not None

    u = tr["u5"].to_numpy(float)[:-lag]
    y = tr["y"].to_numpy(float)[lag:]
    design = np.column_stack([np.ones_like(u), u])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ beta
    r2 = 1.0 - float(resid.var() / y.var())

    scores = np.abs(resid)
    miss = {}
    for theta in (0, 3, 7):
        res = run_delayed_aci(
            scores[WINDOW:],
            theta,
            init_scores=scores[:WINDOW],
            alpha=ALPHA,
            gamma=0.0,
            window=WINDOW,
        )
        err = (~res["covered"]).astype(float)[BURN:]
        miss[str(theta)] = {
            "miss_rate": float(err.mean()),
            "acf1": acf(err, (1,))["1"],
            "iact": iact(err),
            "mean_miss_run": mean_run_of(err, 1.0),
        }
    return {
        "n_train": len(tr),
        "n_val_unread": len(split.val),
        "n_test_unread": len(split.test),
        "label_y": y_rep,
        "reference_u5": u_rep,
        "held_label": bool(held),
        "gc_cycle_min_assumed": cycle_min,
        "ts_implied_min": ts_implied,
        "point_model": {"lag": lag, "intercept": float(beta[0]), "slope": float(beta[1])},
        "r2_in_sample": r2,
        "residual_acf": acf(resid, ACF_LAGS),
        "residual_iact": iact(resid),
        "open_loop_miss": miss,
    }


def tep(tep_dir: Path) -> dict:
    from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
    from ipis.module1_soft_sensor.data.tep_loader import TEPLoader

    out = {}
    for mode in ("mode1", "mode2", "mode3"):
        tr = time_ordered_split(TEPLoader().load(tep_dir / f"tep_{mode}.csv")).train
        out[mode] = {
            "n_train": len(tr),
            "label_XMEAS_40": repeat_profile(tr["y"].to_numpy()),
            "reference_XMEAS_7": repeat_profile(tr["XMEAS_7"].to_numpy()),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="N1 Phase 1 pre-checks (training split only)")
    ap.add_argument("--path", type=Path, default=DEFAULT_DATA_PATH, help="debutanizer data file")
    ap.add_argument("--tep-dir", type=Path, default=DEFAULT_TEP_DIR)
    ap.add_argument("--cycle-min", type=float, default=15.0, help="GC cycle (Fortuna Sec. 6.2)")
    ap.add_argument("--skip-tep", action="store_true")
    ap.add_argument("--json", action="store_true", help="dump evidence to docs/paper/evidence/")
    ap.add_argument("--evidence-dir", type=Path, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    payload: dict = {"debutanizer": debutanizer(args.path, args.cycle_min)}
    b = payload["debutanizer"]
    print(
        f"debutanizer: train n={b['n_train']}; val {b['n_val_unread']} and "
        f"test {b['n_test_unread']} not read"
    )
    for name in ("label_y", "reference_u5"):
        p = b[name]
        print(
            f"  {name:13s} repeat share {p['repeat_share']:.3f}  mean run {p['mean_run']:.2f}  "
            f"runs {p['run_hist']}"
        )
    ts = b["ts_implied_min"]
    print(
        f"  held label: {b['held_label']}; implied Ts = "
        + (f"{ts:.1f} min (GC cycle {args.cycle_min:g} min)" if ts is not None else "n/a")
    )
    print(
        f"  point model: OLS on u5 at lag {b['point_model']['lag']}, in-sample r2 {b['r2_in_sample']:.3f}"
    )
    print(
        "  residual acf: "
        + "  ".join(f"{k}:{v:+.3f}" for k, v in b["residual_acf"].items())
        + f"  | IACT {b['residual_iact']:.1f}"
    )
    for theta, m in b["open_loop_miss"].items():
        print(
            f"  open-loop miss, theta={theta}: rate {m['miss_rate']:.3f}  acf1 {m['acf1']:+.3f}  "
            f"IACT {m['iact']:.1f}  mean miss run {m['mean_miss_run']:.2f}"
        )
    if not args.skip_tep:
        payload["tep"] = tep(args.tep_dir)
        for mode, t in payload["tep"].items():
            for name in ("label_XMEAS_40", "reference_XMEAS_7"):
                p = t[name]
                print(
                    f"tep {mode} {name:17s} repeat share {p['repeat_share']:.3f}  "
                    f"mean run {p['mean_run']:.2f}  runs {p['run_hist']}"
                )
    if args.json:
        from ipis.shared.evidence import dump_evidence

        print("evidence ->", dump_evidence("phase1_precheck", payload, args.evidence_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
