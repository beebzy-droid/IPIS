"""Phase 1E.1 — SECOM virtual-metrology stress test.

The pipeline that earned its keep on TEP/Debutanizer, applied where its assumptions
are hostile: p ~ n (590 features, 1567 samples), ~4.5% missing, no physics anchors.

Stages:
  1. Load + label-free unsupervised screen (missingness > 40%, near-constant).
  2. Select the virtual-metrology target by stated criteria (D1; see secom_loader).
  3. Model selection: elastic-net regularization path under blocked time-series CV
     with the one-SE parsimony rule (the supervised screen lives INSIDE the folds —
     the elastic net's own shrinkage is the feature selection; imputation is inside
     the estimator pipeline, fit per fold-train).
  4. Time-ordered 70/15/15 split; fit the selected model; ADR-008 bias-update at
     theta in {2,5}; coverage: raw+static-split vs corrected+ACI (the 1D.1b contrast).
  5. Auxiliary validation: are conformal misses enriched for fail==True lots?

Run (cmd, env ipis, repo root; data gitignored under data\\raw\\secom):
    set PYTHONPATH=src
    python scripts\\secom_baseline.py --data-dir data\\raw\\secom
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split
from ipis.module1_soft_sensor.data.secom_loader import (
    SECOMLoader,
    select_vm_target,
    unsupervised_screen,
)
from ipis.module1_soft_sensor.evaluation.bias_update import apply_bias_update
from ipis.module1_soft_sensor.evaluation.blocked_cv import (
    blocked_cv_r2,
    mean_se,
    one_se_selection,
)
from ipis.module1_soft_sensor.evaluation.conformal import (
    ACIConformal,
    SplitConformal,
    marginal_coverage,
    mean_interval_width,
)

# Regularization path: descending alpha = ascending complexity, so the index is the
# complexity axis for one_se_selection (index 0 = strongest shrinkage = simplest).
ALPHAS = np.logspace(1, -3, 13)
L1_RATIO = 0.5


def make_enet(alpha: float) -> Pipeline:
    """Imputer INSIDE the estimator so it is fit on fold-train only (leakage-safe);
    blocked_cv_r2 applies its own train-fit StandardScaler (NaN-passthrough)."""
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("enet", ElasticNet(alpha=alpha, l1_ratio=L1_RATIO, max_iter=20_000)),
        ]
    )


def run(
    data_dir: Path,
    theta_grid: tuple[int, ...] = (2, 5),
    alpha_cov: float = 0.10,
    gamma: float = 0.05,
) -> dict:
    # ---- 1. load + label-free screen ----
    df = SECOMLoader().load(data_dir / "secom.data", data_dir / "secom_labels.data")
    screen = unsupervised_screen(df)
    print(f"[screen] {screen.summary}")

    # ---- 2. target selection (uses fail ONLY to define the problem) ----
    sel = select_vm_target(df, screen.kept)
    target = sel.target
    feats = [c for c in screen.kept if c != target]
    print(
        f"[target] {target}  (|r_fail|={sel.audit.loc[0,'abs_r_fail']:.3f}, "
        f"missing={sel.audit.loc[0,'missing_frac']:.2%})"
    )
    print(sel.audit.to_string(index=False))

    # rows where the target itself is missing cannot be scored
    data = df[df[target].notna()].reset_index(drop=True)
    print(f"[rows] {len(data)} of {len(df)} have the target measured")

    # ---- 3. elastic-net path under blocked CV + one-SE ----
    def builder(seg: pd.DataFrame):
        return seg[feats].to_numpy(float), seg[target].to_numpy(float)

    means, ses = [], []
    for a in ALPHAS:
        scores = blocked_cv_r2(
            data, lambda a=a: make_enet(a), max_lag=0, n_splits=5, feature_builder=builder
        )
        m, s = mean_se(scores)
        means.append(m)
        ses.append(s)
        print(f"  alpha={a:9.4f}  CV R2 = {m:+.4f} ± {s:.4f}")
    idx = int(one_se_selection(list(range(len(ALPHAS))), means, ses))
    alpha_star = float(ALPHAS[idx])
    print(
        f"[one-SE] alpha* = {alpha_star:.4f} (index {idx}; best mean at "
        f"index {int(np.argmax(means))})"
    )

    # ---- 4. final fit + bias-update + conformal coverage ----
    split = time_ordered_split(data)
    scaler = StandardScaler().fit(split.train[feats].to_numpy(float))
    model = make_enet(alpha_star)
    model.fit(
        scaler.transform(split.train[feats].to_numpy(float)), split.train[target].to_numpy(float)
    )

    def predict(frame: pd.DataFrame) -> np.ndarray:
        return np.asarray(model.predict(scaler.transform(frame[feats].to_numpy(float)))).ravel()

    raw_val = predict(split.val)
    y_val = split.val[target].to_numpy(float)
    calib_resid = y_val - raw_val
    raw_test = predict(split.test)
    y_test = split.test[target].to_numpy(float)
    nz = int(np.sum(np.abs(model.named_steps["enet"].coef_) > 1e-10))
    print(
        f"[model] val R2 = {r2_score(y_val, raw_val):+.4f} | "
        f"test R2 (raw) = {r2_score(y_test, raw_test):+.4f} | nonzero coefs = {nz}/{len(feats)}"
    )

    # gamma fixed at the 1D.1b protocol default (conformal_eval.py --gamma 0.05)
    out: dict = {"target": target, "alpha_star": alpha_star, "nonzero": nz, "coverage": {}}
    for theta in theta_grid:
        corrected, _ = apply_bias_update(y_test, raw_test, lam=0.3, delay=theta)
        res_cor = y_test - corrected

        sc = SplitConformal(calib_resid, alpha=alpha_cov)
        lo_s, up_s = sc.interval(raw_test)
        cov_split = marginal_coverage((y_test >= lo_s) & (y_test <= up_s))
        w_split = mean_interval_width(lo_s, up_s)

        # 1D.1b protocol: theta enters through the bias-update delay; ACI runs with
        # immediate feedback via the batch driver (comparable to the TEP table).
        aci = ACIConformal(init_residuals=calib_resid, alpha=alpha_cov, gamma=gamma)
        lo_a, up_a, covered, _ = aci.run(corrected, y_test)
        cov_aci = marginal_coverage(covered)
        w_aci = mean_interval_width(lo_a, up_a)

        # ---- 5. fail enrichment among conformal misses (auxiliary validation) ----
        fail_t = split.test["fail"].to_numpy(bool)
        miss_rate_fail = float(np.mean(~covered[fail_t])) if fail_t.any() else float("nan")
        miss_rate_pass = float(np.mean(~covered[~fail_t]))

        n_fail = int(fail_t.sum())
        print(
            f"[theta={theta}] raw+split: cov={cov_split:.3f} w={w_split:.3f} | "
            f"corrected+ACI: cov={cov_aci:.3f} w={w_aci:.3f} | "
            f"corrected R2={r2_score(y_test, corrected):+.3f} | "
            f"miss-rate fail={miss_rate_fail:.3f} (n={n_fail}) vs pass={miss_rate_pass:.3f}"
        )
        out["coverage"][theta] = {
            "split": {"cov": float(cov_split), "width": float(w_split)},
            "aci": {"cov": float(cov_aci), "width": float(w_aci)},
            "corrected_test_r2": float(r2_score(y_test, corrected)),
            "raw_residual_sd": float(np.std(y_test - raw_test)),
            "corrected_residual_sd": float(np.std(res_cor)),
            "miss_rate_fail": miss_rate_fail,
            "n_fail_test": int(fail_t.sum()),
            "miss_rate_pass": miss_rate_pass,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="SECOM virtual-metrology stress test (1E.1)")
    ap.add_argument("--data-dir", type=Path, default=Path("data/raw/secom"))
    ap.add_argument("--alpha", type=float, default=0.10, help="target miscoverage")
    ap.add_argument("--gamma", type=float, default=0.05, help="ACI step size (1D.1b default)")
    args = ap.parse_args()
    run(args.data_dir, alpha_cov=args.alpha, gamma=args.gamma)
    return 0


if __name__ == "__main__":
    sys.exit(main())
