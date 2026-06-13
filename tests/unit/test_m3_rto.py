"""Unit tests for the Module 3 / 3A RTO skeleton (data-free)."""

from __future__ import annotations

import pytest

from ipis.module3_rto.column_model import ShortcutColumnModel
from ipis.module3_rto.economics import (
    M_C4_KG_PER_KMOL,
    EconomicsAnchor,
)
from ipis.module3_rto.rto_nlp import (
    DEFAULT_SPEC_XB_C4,
    LnXbSurface,
    fit_ln_xb_surface,
    solve_rto,
)


# ---------------------------------------------------------------- economics
class TestEconomicsAnchor:
    def test_default_anchor_values(self):
        """Defaults reproduce the cited conversions to 3 significant figures."""
        e = EconomicsAnchor()
        assert e.c4_value_usd_per_kg == pytest.approx(0.3395, rel=1e-3)
        assert e.gasoline_value_usd_per_kg == pytest.approx(0.8364, rel=1e-3)
        assert e.energy_cost_usd_per_gj == pytest.approx(6.278, rel=1e-3)

    def test_upgrade_incentive_positive(self):
        """Gasoline > C4 per kg: retaining C4 in bottoms must add revenue."""
        e = EconomicsAnchor()
        base = e.revenue_usd_per_h(35.0, 0.0, 0.0, 65.0)
        upgraded = e.revenue_usd_per_h(34.0, 0.0, 1.0, 65.0)
        delta = upgraded - base
        expected = M_C4_KG_PER_KMOL * (e.gasoline_value_usd_per_kg - e.c4_value_usd_per_kg)
        assert delta == pytest.approx(expected)
        assert delta > 0.0

    def test_energy_cost_unit_path(self):
        """1000 kW for 1 h is 3.6 GJ at the anchor's USD/GJ rate."""
        e = EconomicsAnchor(energy_cost_usd_per_gj=10.0)
        assert e.energy_cost_usd_per_h(1000.0) == pytest.approx(36.0)

    def test_override_slot(self):
        """Plant-realistic figures replace defaults without code change."""
        e = EconomicsAnchor(
            c4_value_usd_per_kg=0.5,
            gasoline_value_usd_per_kg=1.0,
            energy_cost_usd_per_gj=12.0,
        )
        assert e.c4_value_usd_per_kg == 0.5
        assert e.energy_cost_usd_per_gj == 12.0


# ------------------------------------------------------------- column model
class TestShortcutColumnModel:
    def test_mass_balance_closes(self):
        m = ShortcutColumnModel()
        r = m.evaluate(1.5, 35.0)
        f_lk = m.feed_kmol_h * m.z_lk
        bottoms = m.feed_kmol_h - r.distillate_kmol_h
        recovered = r.x_distillate_lk * r.distillate_kmol_h + r.x_bottoms_lk * bottoms
        assert recovered == pytest.approx(f_lk, rel=1e-8)

    def test_xb_monotone_decreasing_in_reflux(self):
        m = ShortcutColumnModel()
        xbs = [m.evaluate(r, 34.0).x_bottoms_lk for r in (0.8, 1.5, 2.5, 3.0)]
        assert all(a >= b - 1e-12 for a, b in zip(xbs, xbs[1:], strict=False))

    def test_xb_monotone_decreasing_in_distillate(self):
        m = ShortcutColumnModel()
        xbs = [m.evaluate(1.5, d).x_bottoms_lk for d in (33.0, 34.0, 35.0, 36.0)]
        assert all(a >= b - 1e-12 for a, b in zip(xbs, xbs[1:], strict=False))

    def test_duty_exactly_linear(self):
        """Q = (R+1) D dHvap/3600 — the analytic-duty assumption of the NLP."""
        m = ShortcutColumnModel()
        r = m.evaluate(2.0, 35.0)
        assert r.reboiler_duty_kw == pytest.approx(3.0 * 35.0 * 25_930.0 / 3600.0)

    def test_more_stages_sharper_split(self):
        lo = ShortcutColumnModel(n_stages=6.0).evaluate(1.5, 35.0).x_bottoms_lk
        hi = ShortcutColumnModel(n_stages=10.0).evaluate(1.5, 35.0).x_bottoms_lk
        assert hi < lo

    def test_unphysical_distillate_raises(self):
        m = ShortcutColumnModel()
        with pytest.raises(ValueError):
            m.evaluate(1.5, 100.0)  # D = F leaves no bottoms HK flow


# -------------------------------------------------------------- surface/NLP
class TestRTONLP:
    @pytest.fixture(scope="class")
    def surface(self) -> LnXbSurface:
        return fit_ln_xb_surface(ShortcutColumnModel())

    def test_surface_fit_quality(self, surface):
        """Quadratic on ln(xB): R^2 and residual band as documented."""
        assert surface.r_squared > 0.97
        assert surface.max_abs_resid < 0.7  # x2 multiplicative band ceiling

    def test_spec_constraint_active_at_optimum(self, surface):
        """The upgrade economics must pin the optimum on the C4 spec."""
        res = solve_rto(surface, backoff=0.0)
        assert "c4_spec_backoff" in res.active_constraints
        assert res.x_bottoms_lk == pytest.approx(DEFAULT_SPEC_XB_C4, rel=0.02)

    def test_backoff_costs_profit_monotonically(self, surface):
        """Wider back-off must never increase profit (the 3B lever)."""
        profits = [
            solve_rto(surface, backoff=b).profit_usd_per_h for b in (0.0, 0.0025, 0.005, 0.01)
        ]
        assert all(a >= b - 1e-6 for a, b in zip(profits, profits[1:], strict=False))
        assert profits[0] - profits[-1] > 1.0  # gradient is material, not noise

    def test_backoff_tightens_delivered_xb(self, surface):
        loose = solve_rto(surface, backoff=0.0).x_bottoms_lk
        tight = solve_rto(surface, backoff=0.01).x_bottoms_lk
        assert tight < loose

    def test_rto_hold_returns_none(self, surface):
        """D4: a Module 1 drift alarm holds the recommendation."""
        assert solve_rto(surface, rto_hold=True) is None

    def test_backoff_exceeding_spec_raises(self, surface):
        with pytest.raises(ValueError):
            solve_rto(surface, backoff=DEFAULT_SPEC_XB_C4)

    def test_state_bus_fields(self, surface):
        res = solve_rto(surface, backoff=0.005)
        fields = res.to_state_bus_fields()
        assert set(fields) == {"setpoint_recommendations", "active_constraints"}
        assert set(fields["setpoint_recommendations"]) == {
            "reflux_ratio",
            "distillate_kmol_h",
        }

    def test_surface_predict_matches_lstsq_basis(self, surface):
        """predict_ln is the same polynomial the fit used (no basis drift)."""
        b = surface.coef
        r, d = 1.7, 35.2
        manual = b[0] + b[1] * r + b[2] * d + b[3] * r**2 + b[4] * d**2 + b[5] * r * d
        assert surface.predict_ln(r, d) == pytest.approx(manual)


# ------------------------------------------------------- validation harness
class TestValidateTwin:
    @pytest.fixture(scope="class")
    def fixture_df(self):
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from validate_twin import make_selftest_fixture

        return make_selftest_fixture()

    def test_selftest_fixture_passes_all_checks(self, fixture_df):
        from validate_twin import validate

        results = validate(fixture_df)
        assert results and all(r.passed for r in results)

    def test_missing_column_raises(self, fixture_df):
        from validate_twin import validate

        with pytest.raises(ValueError, match="missing required columns"):
            validate(fixture_df.drop(columns=["xb_c4"]))

    def test_envelope_passes_when_feasible_region_in_envelope(self):
        """V1 passes if at least one feasible (xB<=spec) point is in-envelope."""
        import pandas as pd
        from validate_twin import check_envelope

        df = pd.DataFrame(
            {
                "tray6_T_C": [106.0, 99.0, 118.0],  # in / cold / hot
                "top_P_bar": [4.7, 4.7, 4.7],
                "xb_c4": [0.015, 0.05, 0.004],  # feasible / infeasible / feasible-hot
            }
        )
        res = check_envelope(df)
        assert res.passed  # the 106 C row is feasible AND in-envelope
        assert "3B flag" in res.detail

    def test_envelope_fails_when_no_feasible_point_in_envelope(self):
        """V1 fails only if the feasible set never lands inside the envelope."""
        import pandas as pd
        from validate_twin import check_envelope

        df = pd.DataFrame(
            {
                "tray6_T_C": [99.0, 118.0],  # cold + hot, none in [100,112]
                "top_P_bar": [4.7, 4.7],
                "xb_c4": [0.05, 0.004],
            }
        )
        assert not check_envelope(df).passed

    def test_mass_balance_violation_fails(self, fixture_df):
        from validate_twin import check_mass_balance

        bad = fixture_df.copy()
        bad.loc[bad.index[0], "xb_c4"] = 0.5  # breaks closure
        assert not check_mass_balance(bad).passed

    def test_monotonicity_violation_fails(self, fixture_df):
        from validate_twin import check_monotonicity

        bad = fixture_df.copy()
        d0 = bad["distillate_kmol_h"].iloc[0]
        grp = bad[bad["distillate_kmol_h"] == d0].sort_values("reflux_ratio")
        bad.loc[grp.index[-1], "xb_c4"] = grp["xb_c4"].iloc[0] + 0.1
        assert not check_monotonicity(bad).passed

    def test_render_markdown_reports_fail(self, fixture_df):
        from validate_twin import CheckResult, render_markdown

        md = render_markdown([CheckResult("V1 envelope", False, "1 row outside")], "x.csv", 5)
        assert "FAIL" in md and "Overall: **FAIL**" not in md  # table cell, bold line
        assert "**Overall: FAIL**" in md


class TestSurfaceFitVariants:
    """The from-points / from-csv fit paths (G2 consumption)."""

    def test_from_points_matches_model_grid(self):
        """from_points on the model's own grid reproduces the grid fit."""
        import numpy as np

        from ipis.module3_rto.rto_nlp import fit_ln_xb_surface_from_points

        m = ShortcutColumnModel()
        rs, ds, xbs = [], [], []
        for r in np.linspace(0.8, 3.0, 9):
            for d in np.linspace(33.0, 37.0, 9):
                try:
                    resp = m.evaluate(float(r), float(d))
                except ValueError:
                    continue
                rs.append(r)
                ds.append(d)
                xbs.append(resp.x_bottoms_lk)
        surf = fit_ln_xb_surface_from_points(np.array(rs), np.array(ds), np.array(xbs))
        grid = fit_ln_xb_surface(m)
        assert surf.r_squared == pytest.approx(grid.r_squared, rel=1e-9)

    def test_from_points_too_few_raises(self):
        import numpy as np

        from ipis.module3_rto.rto_nlp import fit_ln_xb_surface_from_points

        with pytest.raises(ValueError, match="need >= 12"):
            fit_ln_xb_surface_from_points(np.arange(5.0), np.arange(5.0), np.full(5, 0.01))

    def test_from_points_drops_nonpositive_xb(self):
        """Non-positive xB rows are dropped; fit still succeeds on the rest."""
        import numpy as np

        from ipis.module3_rto.rto_nlp import fit_ln_xb_surface_from_points

        m = ShortcutColumnModel()
        rs, ds, xbs = [], [], []
        for r in np.linspace(0.8, 3.0, 4):
            for d in np.linspace(33.0, 37.0, 4):
                try:
                    resp = m.evaluate(float(r), float(d))
                except ValueError:
                    continue
                rs.append(r)
                ds.append(d)
                xbs.append(resp.x_bottoms_lk)
        # inject two non-positive rows that must be dropped (would crash log())
        rs += [1.0, 2.0]
        ds += [35.0, 35.0]
        xbs += [0.0, -1.0]
        surf = fit_ln_xb_surface_from_points(np.array(rs), np.array(ds), np.array(xbs))
        assert surf.r_squared > 0.9  # varied real xB -> well-defined, good fit

    def test_from_csv_roundtrip(self, tmp_path):
        import csv as _csv

        import numpy as np

        from ipis.module3_rto.rto_nlp import fit_ln_xb_surface_from_csv

        m = ShortcutColumnModel()
        p = tmp_path / "twin.csv"
        with open(p, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["reflux_ratio", "distillate_kmol_h", "xb_c4"])
            for r in np.linspace(0.8, 3.0, 6):
                for d in np.linspace(33.0, 37.0, 6):
                    try:
                        resp = m.evaluate(float(r), float(d))
                    except ValueError:
                        continue
                    w.writerow([r, d, resp.x_bottoms_lk])
        surf = fit_ln_xb_surface_from_csv(str(p))
        assert surf.r_squared > 0.9

    def test_from_csv_missing_column_raises(self, tmp_path):
        from ipis.module3_rto.rto_nlp import fit_ln_xb_surface_from_csv

        p = tmp_path / "bad.csv"
        p.write_text("reflux_ratio,distillate_kmol_h\n1.5,34.5\n")
        with pytest.raises(ValueError, match="missing columns"):
            fit_ln_xb_surface_from_csv(str(p))


class TestGPRSurrogate:
    """3B.1: GP surrogate over the twin (ADR-006)."""

    @pytest.fixture(scope="class")
    def twin_csv(self, tmp_path_factory):
        import csv as _csv

        p = tmp_path_factory.mktemp("twin") / "twin.csv"
        rows = [
            (1, 0.8, 37.0, 101.4, 0.033466),
            (2, 0.8, 36.0, 99.4, 0.040582),
            (3, 0.8, 34.5, 96.7, 0.053404),
            (4, 0.8, 33.0, 94.5, 0.068177),
            (5, 1.5, 37.0, 111.2, 0.012444),
            (6, 1.5, 36.0, 108.7, 0.015817),
            (7, 1.5, 34.5, 103.9, 0.024291),
            (8, 1.5, 33.0, 98.3, 0.038581),
            (9, 2.2, 37.0, 116.5, 0.006495),
            (10, 2.2, 36.0, 114.3, 0.008364),
            (11, 2.2, 34.5, 107.6, 0.015151),
            (12, 2.2, 33.0, 97.1, 0.032282),
            (13, 3.0, 37.0, 119.8, 0.003903),
            (14, 3.0, 36.0, 117.9, 0.005068),
            (16, 3.0, 33.0, 94.0, 0.030860),
        ]
        with open(p, "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(
                [
                    "run_id",
                    "reflux_ratio",
                    "distillate_kmol_h",
                    "feed_kmol_h",
                    "z_c4",
                    "tray6_T_C",
                    "top_P_bar",
                    "xd_c4",
                    "xb_c4",
                    "reboiler_duty_kW",
                    "tray6_x_c4_liq",
                ]
            )
            for rid, r, d, t, xb in rows:
                w.writerow([rid, r, d, 100, 0.35, t, 4.7, 0.9, xb, 600, ""])
        return str(p)

    def test_gpr_interpolates_and_monotone(self, twin_csv):
        import warnings

        import numpy as np

        warnings.filterwarnings("ignore")
        from ipis.module3_rto.surrogate import fit_gpr_from_csv

        gpr_xb, gpr_tt = fit_gpr_from_csv(twin_csv)
        assert gpr_xb.r_squared > 0.999
        # monotone in R and D on a coarse grid
        rs = np.linspace(0.8, 3.0, 12)
        ds = np.linspace(33.0, 37.0, 10)
        assert all(
            gpr_xb.predict(rs[i], d) >= gpr_xb.predict(rs[i + 1], d) - 1e-5
            for d in ds
            for i in range(len(rs) - 1)
        )

    def test_gpr_optimum_matches_3a(self, twin_csv):
        import warnings

        warnings.filterwarnings("ignore")
        from ipis.module3_rto.rto_nlp import fit_ln_xb_surface_from_csv, solve_rto
        from ipis.module3_rto.rto_surface import solve_rto_surface
        from ipis.module3_rto.surrogate import fit_gpr_from_csv

        gpr_xb, _ = fit_gpr_from_csv(twin_csv)
        quad = fit_ln_xb_surface_from_csv(twin_csv)
        gpr_opt = solve_rto_surface(gpr_xb.predict, backoff=0.0)
        quad_opt = solve_rto(quad, backoff=0.0)
        assert "c4_spec_backoff" in gpr_opt.active_constraints
        assert abs(gpr_opt.distillate_kmol_h - quad_opt.distillate_kmol_h) < 0.5
        assert abs(gpr_opt.profit_usd_per_h - quad_opt.profit_usd_per_h) < 5.0

    def test_gpr_reproducible(self, twin_csv):
        import warnings

        warnings.filterwarnings("ignore")
        from ipis.module3_rto.surrogate import fit_gpr_from_csv

        a, _ = fit_gpr_from_csv(twin_csv)
        b, _ = fit_gpr_from_csv(twin_csv)
        assert a.predict(2.0, 35.0) == b.predict(2.0, 35.0)


class TestSurfaceRTOSolver:
    """The generic grid solver (constant + adaptive back-off)."""

    def test_constant_backoff_tightens(self):
        from ipis.module3_rto.rto_surface import solve_rto_surface

        import math

        # analytic surface spanning ~0.004-0.05, monotone down in R and D
        def surf(r, d):
            return 0.1 * math.exp(-0.9 * r) * math.exp(-0.1 * (d - 33.0))

        loose = solve_rto_surface(surf, backoff=0.0)
        tight = solve_rto_surface(surf, backoff=0.005)
        assert loose is not None and tight is not None
        assert tight.x_bottoms_lk <= loose.x_bottoms_lk + 1e-9

    def test_adaptive_backoff_callable(self):
        from ipis.module3_rto.rto_surface import solve_rto_surface

        import math

        def surf(r, d):
            return 0.1 * math.exp(-0.9 * r) * math.exp(-0.1 * (d - 33.0))

        # operating-point-dependent back-off (proxy for interval width)
        res = solve_rto_surface(surf, backoff=lambda r, d: 0.002 + 0.001 * r)
        assert res is not None
        assert res.backoff_at_opt > 0.0

    def test_infeasible_returns_none(self):
        from ipis.module3_rto.rto_surface import solve_rto_surface

        # surface always above spec even at best corner
        res = solve_rto_surface(lambda r, d: 0.5, backoff=0.0)
        assert res is None
