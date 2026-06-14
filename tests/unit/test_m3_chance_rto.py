"""Unit tests for chance_rto (Module 3, Phase 3B).

Uses a SYNTHETIC monotone-in-z twin surface to validate the machinery only
(code check, not a scientific result): xB increases with z, decreases with R/D,
mirroring the debutanizer so the conformal-RTO invariants are exercised.
"""

from __future__ import annotations

import numpy as np
import pytest

from ipis.module3_rto import chance_rto as crto
from ipis.module3_rto.economics import EconomicsAnchor
from ipis.module3_rto.surrogate import (
    _fit,
    fit_gpr_ln_xb,
    fit_truth_surface_3d,
)


def _synthetic_xb(r, d, z):
    # positive, increasing in z, decreasing in R and D; ~0.005..0.12 over the box
    return np.exp(18.0 * (z - 0.35) - 0.55 * r - 0.06 * (d - 33.0) - 3.4)


@pytest.fixture(scope="module")
def surfaces(tmp_path_factory):
    rs = np.linspace(0.8, 3.0, 6)
    ds = np.linspace(33.0, 37.0, 5)
    zs = np.array([0.30, 0.325, 0.35, 0.375, 0.40])
    rows = []
    for z in zs:
        for r in rs:
            for d in ds:
                xb = float(np.clip(_synthetic_xb(r, d, z), 1e-4, 0.5))
                xd = float(np.clip(0.80 + 0.5 * (r - 0.8) / 2.2, 0.0, 0.999))
                q = 400.0 + 220.0 * r
                rows.append((r, d, 100.0, z, 95.0, 4.7, xd, xb, q, ""))
    cols = "reflux_ratio,distillate_kmol_h,feed_kmol_h,z_c4,tray6_T_C,top_P_bar,xd_c4,xb_c4,reboiler_duty_kW,tray6_x_c4_liq"
    base = tmp_path_factory.mktemp("crto")
    zv = base / "zvaried.csv"
    nm = base / "nominal.csv"
    with open(zv, "w") as f:
        f.write(cols + "\n")
        for row in rows:
            f.write(",".join(str(x) for x in row) + "\n")
    with open(nm, "w") as f:
        f.write(cols + "\n")
        for row in rows:
            if abs(row[3] - 0.35) < 1e-9:
                f.write(",".join(str(x) for x in row) + "\n")
    import pandas as pd

    dfn = pd.read_csv(nm)
    xb_nom = fit_gpr_ln_xb(dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["xb_c4"])
    xd_nom = _fit(dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["xd_c4"], log_target=False)
    q_nom = _fit(
        dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["reboiler_duty_kW"], log_target=False
    )
    truth = fit_truth_surface_3d(str(zv))
    grid = crto.build_decision_grid(xb_nom, xd_nom, q_nom, EconomicsAnchor(), n_r=31, n_d=21)
    return xb_nom, truth, grid


class TestDisturbanceModel:
    def test_quantile_monotone_and_centered(self):
        dm = crto.DisturbanceModel(sigma=0.01)
        assert dm.quantile(0.5) == pytest.approx(0.35, abs=1e-6)
        assert dm.quantile(0.9) > dm.quantile(0.1)
        assert 0.30 <= dm.quantile(0.001) and dm.quantile(0.999) <= 0.40

    def test_draw_in_support(self):
        dm = crto.DisturbanceModel(sigma=0.02)
        z = dm.draw(5000, np.random.default_rng(0))
        assert z.min() >= 0.30 and z.max() <= 0.40
        assert z.mean() == pytest.approx(0.35, abs=0.01)


class TestConformalQuantile:
    def test_finite_sample_level(self):
        s = np.arange(1, 101, dtype=float)  # 1..100
        # one-sided 90%: ceil(101*0.9)/100 = 91/100 -> the 91st value
        assert crto.one_sided_quantile(s, 0.10) == pytest.approx(91.0)


class TestBackoffsNonNegative:
    def test_all_backoffs_nonnegative(self, surfaces):
        xb_nom, truth, grid = surfaces
        dm = crto.DisturbanceModel(sigma=0.008)
        rng = np.random.default_rng(1)
        cal = crto.sample_calibration(xb_nom, truth, dm, rng, n=400)
        assert (crto.oracle_backoff(truth, grid, dm, 0.10) >= 0).all()
        assert (crto.cqr_backoff(cal, grid, 0.10) >= 0).all()
        assert (crto.normalized_backoff(cal, grid, 0.10) >= 0).all()
        assert crto.fixed_backoff(cal, 0.10) >= 0


class TestSolveAndScore:
    def test_infeasible_when_margin_exceeds_spec(self, surfaces):
        _, truth, grid = surfaces
        dm = crto.DisturbanceModel(sigma=0.006)
        res = crto.solve_chance_rto(
            grid, 1.0, 0.02, truth, dm, np.random.default_rng(0), method="x"
        )
        assert not res.feasible_found  # a margin of 1.0 makes xB+1 <= 0.02 impossible

    def test_oracle_controls_violation(self, surfaces):
        """Framework invariant: the oracle conditional quantile -> realized viol ~ alpha."""
        xb_nom, truth, grid = surfaces
        dm = crto.DisturbanceModel(sigma=0.008)
        rng = np.random.default_rng(2)
        res = crto.solve_chance_rto(
            grid,
            crto.oracle_backoff(truth, grid, dm, 0.10),
            0.02,
            truth,
            dm,
            rng,
            method="oracle",
            n_violation=6000,
        )
        assert res.feasible_found
        assert res.realized_violation <= 0.10 + 0.05


class TestSelectionEffectAndFix:
    def test_naive_adaptive_overviolates_and_cqr_fixes(self, surfaces):
        """The headline: the marginal/adaptive back-off is exploited by the RTO
        (realized violation >> alpha); CQR + a-posteriori restores control."""
        xb_nom, truth, grid = surfaces
        dm = crto.DisturbanceModel(sigma=0.008)
        rng = np.random.default_rng(3)
        cal = crto.sample_calibration(xb_nom, truth, dm, rng, n=2000)
        naive = crto.solve_chance_rto(
            grid,
            crto.normalized_backoff(cal, grid, 0.10),
            0.02,
            truth,
            dm,
            rng,
            method="naive-adapt",
            n_violation=6000,
        )
        cqr = crto.aposteriori_tighten(
            grid, crto.cqr_backoff(cal, grid, 0.10), 0.02, truth, dm, 0.10, rng
        )
        assert naive.feasible_found and naive.realized_violation > 0.10  # selection effect
        assert cqr.feasible_found
        assert cqr.realized_violation < naive.realized_violation  # the fix helps
        assert cqr.realized_violation <= 0.10 + 0.05  # and controls near target
        assert cqr.kappa >= 1.0
