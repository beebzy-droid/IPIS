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
            validate(fixture_df.drop(columns=["xB_c4"]))

    def test_envelope_violation_fails(self, fixture_df):
        from validate_twin import check_envelope

        bad = fixture_df.copy()
        bad.loc[bad.index[0], "tray6_T_C"] = 130.0  # outside [100, 112]
        assert not check_envelope(bad).passed

    def test_mass_balance_violation_fails(self, fixture_df):
        from validate_twin import check_mass_balance

        bad = fixture_df.copy()
        bad.loc[bad.index[0], "xB_c4"] = 0.5  # breaks closure
        assert not check_mass_balance(bad).passed

    def test_monotonicity_violation_fails(self, fixture_df):
        from validate_twin import check_monotonicity

        bad = fixture_df.copy()
        d0 = bad["distillate_kmol_h"].iloc[0]
        grp = bad[bad["distillate_kmol_h"] == d0].sort_values("reflux_ratio")
        bad.loc[grp.index[-1], "xB_c4"] = grp["xB_c4"].iloc[0] + 0.1
        assert not check_monotonicity(bad).passed

    def test_render_markdown_reports_fail(self, fixture_df):
        from validate_twin import CheckResult, render_markdown

        md = render_markdown([CheckResult("V1 envelope", False, "1 row outside")], "x.csv", 5)
        assert "FAIL" in md and "Overall: **FAIL**" not in md  # table cell, bold line
        assert "**Overall: FAIL**" in md
