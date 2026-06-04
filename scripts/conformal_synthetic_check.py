"""Phase 1D conformal sanity check on a synthetic regime shift (no external data).

Mirrors the project's synthetic-verification habit (cf. the Luo 1.0x verification):
construct a stream whose residual scale step-changes partway through (a regime/
calibration drift), then compare three interval constructions on identical data.

Expected, and the whole point of choosing an *adaptive* method:
  - static split conformal (calibrated once, pre-drift) UNDER-COVERS after the shift;
  - ACI and EnbPI recover ~nominal long-run coverage by adapting online.

Run (cmd, from repo root, env ``ipis``):
    set PYTHONPATH=src
    python scripts\\conformal_synthetic_check.py

Writes ``conformal_synthetic_check.png`` to the current directory.
"""

from __future__ import annotations

import numpy as np

from ipis.module1_soft_sensor.evaluation.conformal import (
    ACIConformal,
    EnbPI,
    SplitConformal,
    marginal_coverage,
    mean_interval_width,
    rolling_coverage,
    select_gamma,
)

ALPHA = 0.10
TARGET = 1.0 - ALPHA
SEED = 20260605


def _ols_fit_predict(x_tr: np.ndarray, y_tr: np.ndarray, x_ev: np.ndarray) -> np.ndarray:
    a = np.c_[np.ones(len(x_tr)), x_tr]
    coef, *_ = np.linalg.lstsq(a, y_tr, rcond=None)
    return np.c_[np.ones(len(x_ev)), x_ev] @ coef


def main() -> None:
    rng = np.random.default_rng(SEED)

    # --- data: linear signal, residual std 1.0 -> 3.0 at the regime boundary ---
    n_train, n_cal, n_pre, n_post = 600, 600, 1500, 1500
    beta = 3.0

    def make(n: int, sd: float) -> tuple[np.ndarray, np.ndarray]:
        x = rng.uniform(-2, 2, (n, 1))
        y = beta * x[:, 0] + rng.normal(0, sd, n)
        return x, y

    x_train, y_train = make(n_train, 1.0)
    x_cal, y_cal = make(n_cal, 1.0)
    x_pre, y_pre = make(n_pre, 1.0)
    x_post, y_post = make(n_post, 3.0)  # <-- drift: residual scale triples
    x_test = np.vstack([x_pre, x_post])
    y_test = np.concatenate([y_pre, y_post])

    # point model fit once on the pre-drift training block (the deployed sensor)
    coef_fit = _ols_fit_predict  # closure reused for EnbPI ensemble too
    p_cal = coef_fit(x_train, y_train, x_cal)
    cal_resid = y_cal - p_cal
    p_test = coef_fit(x_train, y_train, x_test)

    boundary = n_pre

    # --- 1) static split conformal (drift-blind baseline) ---
    sc = SplitConformal(cal_resid, alpha=ALPHA)
    lo_s, hi_s = sc.interval(p_test)
    cov_s = (lo_s <= y_test) & (y_test <= hi_s)

    # --- 2) ACI (gamma auto-selected from the published grid on the calib stream) ---
    gamma = select_gamma(p_cal, y_cal, cal_resid, alpha=ALPHA, window=200)
    aci = ACIConformal(cal_resid, alpha=ALPHA, gamma=gamma, window=200)
    lo_a, hi_a, cov_a, _ = aci.run(p_test, y_test)

    # --- 3) EnbPI (bootstrap LOO ensemble + FIFO residual refresh) ---
    enb = EnbPI(coef_fit, alpha=ALPHA, B=30, s=25, random_state=SEED).fit(x_train, y_train)
    _, lo_e, hi_e = enb.predict_interval(x_test, y_test)
    cov_e = (lo_e <= y_test) & (y_test <= hi_e)

    # --- report (overall + per-regime, since marginal coverage hides the failure) ---
    def block(cov: np.ndarray) -> tuple[float, float, float]:
        return (
            marginal_coverage(cov),
            marginal_coverage(cov[:boundary]),
            marginal_coverage(cov[boundary:]),
        )

    rows = [
        ("split (static)", *block(cov_s), mean_interval_width(lo_s, hi_s), gamma),
        (f"ACI (gamma={gamma:.3f})", *block(cov_a), mean_interval_width(lo_a, hi_a), gamma),
        ("EnbPI (B=30,s=25)", *block(cov_e), mean_interval_width(lo_e, hi_e), gamma),
    ]
    print(f"\nTarget coverage = {TARGET:.2f}  (alpha={ALPHA})   drift @ t={boundary}\n")
    print(f"{'method':<20} {'overall':>8} {'pre':>7} {'post':>7} {'mean_w':>8}")
    print("-" * 54)
    for name, ov, pre, post, w, _g in rows:
        print(f"{name:<20} {ov:>8.3f} {pre:>7.3f} {post:>7.3f} {w:>8.2f}")

    # --- plot rolling coverage (the dashboard view of online validity) ---
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        win = 200
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(rolling_coverage(cov_s, win), label="split (static)", lw=1.6)
        ax.plot(rolling_coverage(cov_a, win), label=f"ACI (gamma={gamma:.3f})", lw=1.6)
        ax.plot(rolling_coverage(cov_e, win), label="EnbPI", lw=1.6)
        ax.axhline(TARGET, color="k", ls="--", lw=1, label=f"target {TARGET:.2f}")
        ax.axvline(boundary, color="grey", ls=":", lw=1, label="regime shift")
        ax.set_xlabel(f"time step (trailing {win}-step coverage)")
        ax.set_ylabel("rolling coverage")
        ax.set_ylim(0.4, 1.02)
        ax.set_title("Online coverage under a residual-scale regime shift")
        ax.legend(loc="lower left", fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig("conformal_synthetic_check.png", dpi=130)
        print("\nsaved conformal_synthetic_check.png")
    except ImportError:
        print("\n(matplotlib not available; skipped plot)")


if __name__ == "__main__":
    main()
