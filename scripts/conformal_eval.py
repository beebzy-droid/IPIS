"""Phase 1D.1b -- validate conformal coverage on the real TEP regimes.

For each operating-mode regime, fit the physics-anchored linear sensor on train,
calibrate conformal on the held-out val block, and measure coverage on the
held-out test stream. Compares four interval constructions on identical data:

  (i)   raw sensor + split conformal      -- exchangeability baseline
  (ii)  bias-corrected sensor + split     -- ADR-008 correction, static interval
  (iii) bias-corrected sensor + ACI       -- ADR-010 PRIMARY (online, adaptive)
  (iv)  EnbPI                              -- ADR-010 comparator (standalone ensemble)

Reports per-regime marginal coverage + mean width, an EnbPI batch-size (s) sweep,
and a per-regime rolling-coverage figure. The point of (i) vs (iii): within-mode
IDV drift makes the raw, static interval under-cover; the bias-update + ACI restore
nominal coverage -- the real-data analogue of the 1D.1 synthetic check.

The deployed sensor is the bias-corrected linear model (ADR-007 + ADR-008); split
and ACI wrap *its* residuals exactly. EnbPI brings its own bootstrap ensemble and
FIFO residual refresh, so it is reported as a self-contained alternative, not a
layer on top of the bias-update.

Two input paths:
  --from-pipeline (default): reconstruct predictions via the repo's TEPLoader /
    make_tep_physics_features / time_ordered_split (mirrors scripts/tep_baseline.py),
    then apply the bias-update. Needs the gitignored CSVs in --data-dir.
  --from-csv DIR: skip the pipeline; read {mode}.csv with columns
    `y_true,y_pred[,y_pred_corrected]`. Zero repo-internal deps -- use this if your
    local loader/feature signatures have drifted from the committed ones.

Run (cmd, env ipis, from repo root):
    set PYTHONPATH=src
    python scripts\\conformal_eval.py
    python scripts\\conformal_eval.py --modes mode1,mode2,mode3 --theta 2 --lam 0.3
    python scripts\\conformal_eval.py --from-csv preds_dir

Writes ``conformal_coverage_tep.png`` to the current directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.evaluation.conformal import (
    ACIConformal,
    EnbPI,
    SplitConformal,
    marginal_coverage,
    mean_interval_width,
    rolling_coverage,
)

ALPHA_DEFAULT = 0.10


def _fit_predict_ols(x_tr: np.ndarray, y_tr: np.ndarray, x_ev: np.ndarray) -> np.ndarray:
    """Standardise on train, fit OLS, predict at x_ev (EnbPI's injected learner)."""
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    sc = StandardScaler().fit(x_tr)
    model = LinearRegression().fit(sc.transform(x_tr), y_tr)
    return model.predict(sc.transform(x_ev))


def _regime_arrays_from_pipeline(
    mode: str, data_dir: Path, lam: float, theta: int, transport_lag: int
) -> dict[str, np.ndarray]:
    """Reconstruct train/val/test predictions for one regime via the repo pipeline."""
    import pandas as pd
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
    from ipis.module1_soft_sensor.data.tep_loader import TEPLoader
    from ipis.module1_soft_sensor.evaluation.bias_update import apply_bias_update
    from ipis.module1_soft_sensor.features.tep_physics_features import (
        diagnose_transport_lag,
        make_tep_physics_features,
    )

    df = TEPLoader().load(data_dir / f"tep_{mode}.csv")
    lag = diagnose_transport_lag(df) if transport_lag < 0 else transport_lag

    def feats(seg: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        x, y = make_tep_physics_features(seg, transport_lag=lag)
        return np.asarray(x, float), np.asarray(y, float).ravel()

    split = time_ordered_split(df)
    x_tr, y_tr = feats(split.train)
    x_va, y_va = feats(split.val)
    x_te, y_te = feats(split.test)

    sc = StandardScaler().fit(x_tr)
    model = LinearRegression().fit(sc.transform(x_tr), y_tr)
    raw_va = model.predict(sc.transform(x_va))
    raw_te = model.predict(sc.transform(x_te))
    cor_va, _ = apply_bias_update(y_va, raw_va, lam=lam, delay=theta)
    cor_te, _ = apply_bias_update(y_te, raw_te, lam=lam, delay=theta)

    return {
        "lag": np.array([lag]),
        "x_tr": x_tr,
        "y_tr": y_tr,
        "x_te": x_te,
        "y_va": y_va,
        "raw_va": raw_va,
        "cor_va": cor_va,
        "y_te": y_te,
        "raw_te": raw_te,
        "cor_te": cor_te,
    }


def _regime_arrays_from_csv(
    mode: str, csv_dir: Path, lam: float, theta: int
) -> dict[str, np.ndarray]:
    """Load precomputed predictions for one regime; split into calib(val)/eval(test)."""
    import pandas as pd

    from ipis.module1_soft_sensor.evaluation.bias_update import apply_bias_update

    df = pd.read_csv(csv_dir / f"{mode}.csv")
    y = df["y_true"].to_numpy(float)
    raw = df["y_pred"].to_numpy(float)
    cor = (
        df["y_pred_corrected"].to_numpy(float)
        if "y_pred_corrected" in df.columns
        else apply_bias_update(y, raw, lam=lam, delay=theta)[0]
    )
    cut = int(0.5 * len(y))  # first half = calibration, second half = evaluation
    return {
        "lag": np.array([-1]),
        "x_tr": np.empty((0, 0)),
        "y_tr": np.empty(0),
        "x_te": np.empty((0, 0)),
        "y_va": y[:cut],
        "raw_va": raw[:cut],
        "cor_va": cor[:cut],
        "y_te": y[cut:],
        "raw_te": raw[cut:],
        "cor_te": cor[cut:],
    }


def _evaluate_regime(
    a: dict[str, np.ndarray], alpha: float, gamma: float, window: int, enbpi_b: int, enbpi_s: int
) -> dict[str, object]:
    """Run the four constructions on one regime; return coverage/width + curves."""
    out: dict[str, object] = {}

    # (i) raw sensor + split: calibrate on |val raw residual|, evaluate on test
    sc_raw = SplitConformal(a["y_va"] - a["raw_va"], alpha=alpha)
    lo, hi = sc_raw.interval(a["raw_te"])
    cov_raw = (lo <= a["y_te"]) & (a["y_te"] <= hi)
    out["raw_split"] = (marginal_coverage(cov_raw), mean_interval_width(lo, hi), cov_raw)

    # (ii) corrected sensor + split
    sc_cor = SplitConformal(a["y_va"] - a["cor_va"], alpha=alpha)
    lo, hi = sc_cor.interval(a["cor_te"])
    cov_cs = (lo <= a["y_te"]) & (a["y_te"] <= hi)
    out["cor_split"] = (marginal_coverage(cov_cs), mean_interval_width(lo, hi), cov_cs)

    # (iii) corrected sensor + ACI [primary]
    aci = ACIConformal(a["y_va"] - a["cor_va"], alpha=alpha, gamma=gamma, window=window)
    lo, hi, cov_aci, _ = aci.run(a["cor_te"], a["y_te"])
    out["cor_aci"] = (marginal_coverage(cov_aci), mean_interval_width(lo, hi), cov_aci)

    # (iv) EnbPI [standalone] -- only on the pipeline path (needs train features)
    if a["x_tr"].size and a["x_te"].size:
        enb = EnbPI(_fit_predict_ols, alpha=alpha, B=enbpi_b, s=enbpi_s, random_state=0)
        enb.fit(a["x_tr"], a["y_tr"])
        _, lo, hi = enb.predict_interval(a["x_te"], a["y_te"])
        cov_e = (lo <= a["y_te"]) & (a["y_te"] <= hi)
        out["enbpi"] = (marginal_coverage(cov_e), mean_interval_width(lo, hi), cov_e)
    return out


def _enbpi_s_sweep(a: dict[str, np.ndarray], alpha: float, enbpi_b: int, s_grid: list[int]) -> None:
    if not (a["x_tr"].size and a["x_te"].size):
        return
    print("\n  EnbPI batch-size (s) sweep [coverage / width]:")
    for s in s_grid:
        enb = EnbPI(_fit_predict_ols, alpha=alpha, B=enbpi_b, s=s, random_state=0)
        enb.fit(a["x_tr"], a["y_tr"])
        _, lo, hi = enb.predict_interval(a["x_te"], a["y_te"])
        cov = marginal_coverage((lo <= a["y_te"]) & (a["y_te"] <= hi))
        print(f"    s={s:>3}  coverage {cov:.3f}  width {mean_interval_width(lo, hi):.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 1D.1b conformal coverage on TEP regimes.")
    ap.add_argument("--data-dir", type=Path, default=Path("data/raw/tep"))
    ap.add_argument(
        "--from-csv",
        type=Path,
        default=None,
        help="dir of {mode}.csv (y_true,y_pred[,y_pred_corrected])",
    )
    ap.add_argument("--modes", default="mode1,mode2,mode3")
    ap.add_argument("--alpha", type=float, default=ALPHA_DEFAULT)
    ap.add_argument("--lam", type=float, default=0.3, help="bias-update EWMA rate")
    ap.add_argument(
        "--theta", type=int, default=2, help="label/analyzer delay (2 empirical, 5 documented)"
    )
    ap.add_argument("--transport-lag", type=int, default=-1, help="-1 = diagnose")
    ap.add_argument("--gamma", type=float, default=0.05, help="ACI step size")
    ap.add_argument("--window", type=int, default=200, help="ACI sliding score window")
    ap.add_argument("--enbpi-B", type=int, default=30)
    ap.add_argument("--enbpi-s", type=int, default=25)
    ap.add_argument(
        "--json",
        action="store_true",
        help="merge this run's coverage into docs/paper/evidence/coverage_tep.json "
        "(run once per theta; runs merge by theta key)",
    )
    args = ap.parse_args()

    modes = [m for m in args.modes.split(",") if m]
    target = 1.0 - args.alpha
    regimes: dict[str, dict[str, np.ndarray]] = {}
    for m in modes:
        try:
            if args.from_csv is not None:
                regimes[m] = _regime_arrays_from_csv(m, args.from_csv, args.lam, args.theta)
            else:
                regimes[m] = _regime_arrays_from_pipeline(
                    m, args.data_dir, args.lam, args.theta, args.transport_lag
                )
        except FileNotFoundError as exc:
            print(f"  {m}: data not found ({exc}); skipped")

    if not regimes:
        print("No regimes loaded. Check --data-dir or --from-csv.")
        return 1

    print("=" * 74)
    print(
        f"Phase 1D.1b -- conformal coverage on TEP regimes   target={target:.2f} (alpha={args.alpha})"
    )
    print(
        f"bias-update lam={args.lam} theta={args.theta} | ACI gamma={args.gamma} window={args.window}"
    )
    print("=" * 74)

    results: dict[str, dict[str, object]] = {}
    for m, a in regimes.items():
        res = _evaluate_regime(a, args.alpha, args.gamma, args.window, args.enbpi_B, args.enbpi_s)
        results[m] = res
        lag = int(a["lag"][0])
        print(f"\n[{m}]  n_test={a['y_te'].size}  transport_lag={lag if lag >= 0 else 'n/a'}")
        print(f"  {'construction':<26} {'coverage':>9} {'width':>8}")
        print("  " + "-" * 45)
        label = {
            "raw_split": "raw + split (baseline)",
            "cor_split": "corrected + split",
            "cor_aci": "corrected + ACI [primary]",
            "enbpi": "EnbPI [standalone]",
        }
        for key in ("raw_split", "cor_split", "cor_aci", "enbpi"):
            if key in res:
                cov, w, _ = res[key]  # type: ignore[misc]
                print(f"  {label[key]:<26} {cov:>9.3f} {w:>8.2f}")

    # EnbPI s-sweep on the first regime
    first = next(iter(regimes.values()))
    _enbpi_s_sweep(first, args.alpha, args.enbpi_B, [1, 10, 25, 50])

    if args.json:
        import json as _json

        from ipis.shared.evidence import EVIDENCE_DIR, dump_evidence

        key_map = {
            "split": "raw_split",
            "cor_split": "cor_split",
            "aci": "cor_aci",
            "enbpi": "enbpi",
        }
        path = EVIDENCE_DIR / "coverage_tep.json"
        doc: dict = {"target": target, "regimes": {}}
        if path.exists():
            prev = _json.loads(path.read_text())
            doc["regimes"] = prev.get("regimes", {})
        for m, res in results.items():
            slot = doc["regimes"].setdefault(m, {})
            entry = {}
            for out_name, res_key in key_map.items():
                if res_key in res:
                    cov, w, _ = res[res_key]  # type: ignore[misc]
                    entry[out_name] = {"cov": float(cov), "width": float(w)}
            slot[str(args.theta)] = entry
        print("evidence ->", dump_evidence("coverage_tep", doc))

    # verdict
    aci_cov = [results[m]["cor_aci"][0] for m in results if "cor_aci" in results[m]]  # type: ignore[index]
    raw_cov = [results[m]["raw_split"][0] for m in results if "raw_split" in results[m]]  # type: ignore[index]
    print("\n" + "-" * 74)
    if aci_cov:
        held = all(abs(c - target) <= 0.03 for c in aci_cov)
        print(
            f"  corrected+ACI coverage range [{min(aci_cov):.3f}, {max(aci_cov):.3f}] "
            f"-> {'HOLDS within +/-0.03 of target' if held else 'OUTSIDE +/-0.03 (tune gamma/window)'}"
        )
    if raw_cov:
        print(
            f"  raw+split coverage range    [{min(raw_cov):.3f}, {max(raw_cov):.3f}]  (exchangeability baseline)"
        )

    # rolling-coverage figure: one subplot per regime
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        win = max(50, args.window // 2)
        n = len(results)
        fig, axes = plt.subplots(1, n, figsize=(5.2 * n, 4.2), squeeze=False)
        for ax, (m, res) in zip(axes[0], results.items(), strict=False):
            ax.plot(rolling_coverage(res["raw_split"][2], win), label="raw+split", lw=1.4)  # type: ignore[index]
            ax.plot(rolling_coverage(res["cor_aci"][2], win), label="corrected+ACI", lw=1.4)  # type: ignore[index]
            if "enbpi" in res:
                ax.plot(rolling_coverage(res["enbpi"][2], win), label="EnbPI", lw=1.2)  # type: ignore[index]
            ax.axhline(target, color="k", ls="--", lw=1)
            ax.set_ylim(0.3, 1.02)
            ax.set_title(m)
            ax.set_xlabel(f"test step (trailing {win})")
        axes[0][0].set_ylabel("rolling coverage")
        axes[0][0].legend(loc="lower left", fontsize=8)
        fig.suptitle(f"Phase 1D.1b -- conformal coverage on TEP regimes (target {target:.2f})")
        fig.tight_layout()
        fig.savefig("conformal_coverage_tep.png", dpi=130)
        print("\nsaved conformal_coverage_tep.png")
    except ImportError:
        print("\n(matplotlib not available; skipped plot)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
