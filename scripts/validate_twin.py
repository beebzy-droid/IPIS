"""Validate a DWSIM debutanizer-twin export against the 3A acceptance checks.

Owner-side workflow:
    1. Build the twin in DWSIM per docs/module3/twin-spec-3a.md.
    2. Run the case grid (Sensitivity Analysis or manual), export CSV with
       the REQUIRED_COLUMNS below (one row per converged steady state).
    3. python scripts\\validate_twin.py path\\to\\twin_runs.csv
       -> writes docs/module3/twin-validation.md (the closeout table).

Checks (each PASS/FAIL with numbers, never silent):
    V1  Operating envelope — tray-6 T in [100, 112] C and top P in
        [4.5, 5.5] bar (the Module 1 physics-bridge envelope; the twin must
        live where the soft sensor was built).
    V2  Mass-balance closure — |F*z - D*xD - B*xB| / (F*z) <= 0.5% per row
        (catches non-converged DWSIM rows that still export numbers).
    V3  Monotonicity — at fixed D, increasing R must not increase xB_C4
        and must increase reboiler duty (physical sanity of the response).
    V4  Physics-bridge consistency — where the optional tray-6 liquid C4
        column is exported, compare against the Module 1 bubble-point
        inversion at (T_tray6, P); report mean/max deviation (diagnostic,
        threshold 0.15 abs — shortcut-vs-rigorous disagreement is expected,
        gross disagreement means the twin is in the wrong regime).

Sandbox self-test: scripts/validate_twin.py --selftest generates a fixture
grid from the ShortcutColumnModel and validates it (V4 skipped: the
shortcut model carries no tray profile).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = [
    "run_id",
    "reflux_ratio",
    "distillate_kmol_h",
    "feed_kmol_h",
    "z_c4",
    "tray6_T_C",
    "top_P_bar",
    "xD_c4",
    "xB_c4",
    "reboiler_duty_kW",
]
OPTIONAL_TRAY6_X_COLUMN = "tray6_x_c4_liq"

ENVELOPE_T_C = (100.0, 112.0)
ENVELOPE_P_BAR = (4.5, 5.5)
MASS_BALANCE_TOL = 0.005
PHYSICS_DEVIATION_TOL = 0.15


@dataclass
class CheckResult:
    """One validation check outcome."""

    name: str
    passed: bool
    detail: str


def check_envelope(df: pd.DataFrame) -> CheckResult:
    """V1: every run inside the Module 1 physics-bridge envelope."""
    t_ok = df["tray6_T_C"].between(*ENVELOPE_T_C)
    p_ok = df["top_P_bar"].between(*ENVELOPE_P_BAR)
    bad = df[~(t_ok & p_ok)]
    detail = (
        f"T range [{df['tray6_T_C'].min():.1f}, {df['tray6_T_C'].max():.1f}] C "
        f"(env {ENVELOPE_T_C}); P range [{df['top_P_bar'].min():.2f}, "
        f"{df['top_P_bar'].max():.2f}] bar (env {ENVELOPE_P_BAR}); "
        f"{len(bad)}/{len(df)} rows outside"
    )
    return CheckResult("V1 envelope", bad.empty, detail)


def check_mass_balance(df: pd.DataFrame) -> CheckResult:
    """V2: per-row light-key balance closure within tolerance."""
    f_lk = df["feed_kmol_h"] * df["z_c4"]
    bottoms = df["feed_kmol_h"] - df["distillate_kmol_h"]
    closure = (f_lk - df["distillate_kmol_h"] * df["xD_c4"] - bottoms * df["xB_c4"]).abs() / f_lk
    worst = float(closure.max())
    n_bad = int((closure > MASS_BALANCE_TOL).sum())
    return CheckResult(
        "V2 mass balance",
        n_bad == 0,
        f"worst closure {worst:.4%} (tol {MASS_BALANCE_TOL:.1%}); {n_bad} rows over",
    )


def check_monotonicity(df: pd.DataFrame) -> CheckResult:
    """V3: at fixed D, xB_C4 non-increasing and duty increasing in R."""
    violations: list[str] = []
    for d_val, grp in df.groupby("distillate_kmol_h"):
        g = grp.sort_values("reflux_ratio")
        if len(g) < 2:
            continue
        dx = np.diff(g["xB_c4"].to_numpy())
        dq = np.diff(g["reboiler_duty_kW"].to_numpy())
        if (dx > 1e-9).any():
            violations.append(f"xB increases with R at D={d_val}")
        if (dq <= 0.0).any():
            violations.append(f"duty non-increasing with R at D={d_val}")
    return CheckResult(
        "V3 monotonicity",
        not violations,
        "; ".join(violations) if violations else "xB(R) non-increasing, Q(R) increasing at every D",
    )


def check_physics_bridge(df: pd.DataFrame) -> CheckResult | None:
    """V4: tray-6 liquid C4 vs Module 1 bubble-point inversion (optional)."""
    if OPTIONAL_TRAY6_X_COLUMN not in df.columns:
        return None
    from ipis.physics.bubble_point_inversion import light_key_fraction

    pred = df.apply(
        lambda row: light_key_fraction(row["tray6_T_C"] + 273.15, row["top_P_bar"] * 1.0e5),
        axis=1,
    )
    dev = (pred - df[OPTIONAL_TRAY6_X_COLUMN]).abs()
    return CheckResult(
        "V4 physics bridge",
        float(dev.max()) <= PHYSICS_DEVIATION_TOL,
        f"|x_C4 dev| mean {dev.mean():.3f} / max {dev.max():.3f} " f"(tol {PHYSICS_DEVIATION_TOL})",
    )


def validate(df: pd.DataFrame) -> list[CheckResult]:
    """Run all checks; raises on schema problems (fail loud, not silent)."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    if df.empty:
        raise ValueError("CSV has no rows.")
    results = [check_envelope(df), check_mass_balance(df), check_monotonicity(df)]
    v4 = check_physics_bridge(df)
    if v4 is not None:
        results.append(v4)
    return results


def render_markdown(results: list[CheckResult], source: str, n_rows: int) -> str:
    """The closeout validation table."""
    lines = [
        "# 3A twin validation",
        "",
        f"Source: `{source}` ({n_rows} runs). Checks defined in "
        "`scripts/validate_twin.py`; envelope from the Module 1 physics bridge.",
        "",
        "| check | result | detail |",
        "|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.name} | {'PASS' if r.passed else 'FAIL'} | {r.detail} |")
    lines.append("")
    overall = all(r.passed for r in results)
    lines.append(f"**Overall: {'PASS' if overall else 'FAIL'}**")
    lines.append("")
    return "\n".join(lines)


def make_selftest_fixture() -> pd.DataFrame:
    """Fixture grid from the shortcut model (the sandbox dry run)."""
    from ipis.module3_rto.column_model import ShortcutColumnModel

    m = ShortcutColumnModel()
    rows = []
    i = 0
    for r in (0.8, 1.5, 2.2, 3.0):
        for d in (33.0, 34.5, 36.0, 37.0):
            try:
                resp = m.evaluate(r, d)
            except ValueError:
                continue
            i += 1
            rows.append(
                {
                    "run_id": i,
                    "reflux_ratio": r,
                    "distillate_kmol_h": d,
                    "feed_kmol_h": m.feed_kmol_h,
                    "z_c4": m.z_lk,
                    "tray6_T_C": 106.0,  # nominal mid-envelope placeholder
                    "top_P_bar": 4.9,
                    "xD_c4": resp.x_distillate_lk,
                    "xB_c4": resp.x_bottoms_lk,
                    "reboiler_duty_kW": resp.reboiler_duty_kw,
                }
            )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", help="DWSIM twin export CSV")
    parser.add_argument("--selftest", action="store_true", help="validate a shortcut-model fixture")
    parser.add_argument(
        "--out",
        default="docs/module3/twin-validation.md",
        help="output markdown path",
    )
    args = parser.parse_args(argv)

    if args.selftest:
        df, source = make_selftest_fixture(), "selftest (ShortcutColumnModel fixture)"
    elif args.csv:
        df, source = pd.read_csv(args.csv), args.csv
    else:
        parser.error("provide a CSV path or --selftest")

    results = validate(df)
    md = render_markdown(results, source, len(df))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md)
    print(md)
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
