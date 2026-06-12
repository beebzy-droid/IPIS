"""Economics anchor for the 3A debutanizer RTO — literature defaults.

Owner-ratified basis (2026-06-13): literature defaults now, plant-realistic
figures slot in later via ``EconomicsAnchor`` overrides without code change.

Pricing structure (the textbook debutanizer incentive):
    Overhead (LPG product)  -> sold at the C4 price, by mass.
    Bottoms (stabilized gasoline) -> sold at the gasoline price, by mass.
Since gasoline > C4 per kg, every kmol of C4 retained in the bottoms is an
UPGRADE (+28.9 USD/kmol at the defaults) and every kmol of C6 lost overhead
is a DOWNGRADE (-42.8 USD/kmol). The optimizer therefore rides the bottoms
C4 spec (RVP proxy) from below — the spec constraint is ACTIVE at the
economic optimum, which is exactly the structure the 3B back-off
contribution requires (back-off width has a direct profit cost).

Provenance of the default constants (all free, citable):

C4 product value — 0.750 USD/gal
    Mont Belvieu propane spot, 2025 annual average (EIA via FRED,
    APROPANEMBTX). Conservative FLOOR for n-butane (n-C4 trades at a
    premium to propane at the same hub).

Gasoline value — 2.10 USD/gal
    U.S. Gulf Coast refined-product spot complex, 2025 annual averages
    (EIA via FRED): jet 2.114, ULSD 2.222 USD/gal; conventional regular
    gasoline (MGASUSGULF) trades in the same band. FLAGGED estimate, not a
    transcribed series value; the optimizer rides the gasoline-C4 SPREAD
    (1.35 USD/gal), robust to +/-0.10 on either leg.

Reboiler energy cost — 5.50 USD/Mcf natural gas
    U.S. industrial NG, 2025 (EIA Natural Gas Monthly Tables 3/22, YTD
    5.56-5.78 USD/Mcf). 1 Mcf = 1.038 MMBtu (HHV) = 1.0951 GJ ->
    5.02 USD/GJ fuel; / 0.80 boiler efficiency -> 6.28 USD/GJ steam.

Density bases (CoolProp, saturated liquid at 60 F / 15.56 C, the NGL
gallon accounting basis): n-C4 583.6 kg/m3 = 2.209 kg/gal; n-C6 663.3
kg/m3 = 2.511 kg/gal.

The 3B headline (profit delta, interval-driven vs fixed-margin back-off at
equal violation rate) is driven by the price SPREADS, not the levels;
plant figures should replace all three legs together.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Verified physical constants (CoolProp, the project property layer) ---
M_C4_KG_PER_KMOL: float = 58.122
M_C6_KG_PER_KMOL: float = 86.175
RHO_C4_LIQ_KG_PER_GAL: float = 2.209  # sat. liquid at 15.56 C (60 F)
RHO_C6_LIQ_KG_PER_GAL: float = 2.511  # sat. liquid at 15.56 C (60 F)
DHVAP_C6_KJ_PER_KMOL: float = 25_930.0  # n-hexane at 110 C (boilup basis)

# --- Literature default prices (provenance in module docstring) ---
DEFAULT_C4_USD_PER_GAL: float = 0.750  # EIA/FRED APROPANEMBTX, 2025 avg
DEFAULT_GASOLINE_USD_PER_GAL: float = 2.10  # EIA USGC spot complex, 2025 (flagged)
DEFAULT_NG_USD_PER_MCF: float = 5.50  # EIA NGM 2025, US industrial
DEFAULT_BOILER_EFFICIENCY: float = 0.80

_MCF_TO_GJ: float = 1.038 * 1.055056  # Mcf -> MMBtu (HHV) -> GJ


@dataclass(frozen=True)
class EconomicsAnchor:
    """Price set driving the RTO objective.

    Defaults are the cited literature anchors; construct with explicit
    values to inject plant-realistic figures (replace all legs together —
    the objective is spread-driven).

    Attributes:
        c4_value_usd_per_kg: LPG-stream product value (overhead, by mass).
        gasoline_value_usd_per_kg: Stabilized-gasoline value (bottoms, by mass).
        energy_cost_usd_per_gj: Cost of reboiler heat delivered.
    """

    c4_value_usd_per_kg: float = DEFAULT_C4_USD_PER_GAL / RHO_C4_LIQ_KG_PER_GAL
    gasoline_value_usd_per_kg: float = DEFAULT_GASOLINE_USD_PER_GAL / RHO_C6_LIQ_KG_PER_GAL
    energy_cost_usd_per_gj: float = DEFAULT_NG_USD_PER_MCF / _MCF_TO_GJ / DEFAULT_BOILER_EFFICIENCY

    def revenue_usd_per_h(
        self,
        d_lk_kmol_h: float,
        d_hk_kmol_h: float,
        b_lk_kmol_h: float,
        b_hk_kmol_h: float,
    ) -> float:
        """Mass-based two-stream revenue, USD/h.

        Overhead (d_lk + d_hk) sells at the C4 price; bottoms (b_lk + b_hk)
        sells at the gasoline price, regardless of which molecule carries
        the mass (the upgrade/downgrade structure).
        """
        overhead_kg_h = d_lk_kmol_h * M_C4_KG_PER_KMOL + d_hk_kmol_h * M_C6_KG_PER_KMOL
        bottoms_kg_h = b_lk_kmol_h * M_C4_KG_PER_KMOL + b_hk_kmol_h * M_C6_KG_PER_KMOL
        return (
            overhead_kg_h * self.c4_value_usd_per_kg + bottoms_kg_h * self.gasoline_value_usd_per_kg
        )

    def energy_cost_usd_per_h(self, reboiler_duty_kw: float) -> float:
        """Reboiler energy cost, USD/h (kW -> GJ/h is x 3600 / 1e6)."""
        return reboiler_duty_kw * 3600.0 / 1.0e6 * self.energy_cost_usd_per_gj

    def profit_usd_per_h(
        self,
        d_lk_kmol_h: float,
        d_hk_kmol_h: float,
        b_lk_kmol_h: float,
        b_hk_kmol_h: float,
        reboiler_duty_kw: float,
    ) -> float:
        """Operating profit proxy: two-stream revenue minus reboiler energy."""
        return self.revenue_usd_per_h(
            d_lk_kmol_h, d_hk_kmol_h, b_lk_kmol_h, b_hk_kmol_h
        ) - self.energy_cost_usd_per_h(reboiler_duty_kw)
