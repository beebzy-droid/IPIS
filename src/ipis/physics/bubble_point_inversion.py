"""Soft-sensor physics: bubble-point inversion for light-key composition.

The soft sensor needs the INVERSE of a design calculation: given measured
temperature and pressure, infer the light-key (C4) liquid mole fraction.
For an ideal binary (light key + representative heavy) at its bubble point,
modified Raoult's law with gamma = 1 (Perry's Eqs. 4-195/196; Smith
"Introduction to Chemical Engineering Thermodynamics" 9th ed. Eq. 13.20)
reduces to:

    P = x_L * Psat_L(T) + (1 - x_L) * Psat_H(T)

which inverts in closed form (no iteration) for the light-key fraction:

    x_L = (P - Psat_H(T)) / (Psat_L(T) - Psat_H(T))

This is the soft-sensor y_physics generator. Ideal-solution (gamma = 1) is
justified for adjacent n-alkanes: Smith 9th ed. names "adjacent members of a
homologous series" (e.g. n-hexane/n-heptane) as conforming closely to
ideal-solution behavior.

Configuration for the debutanizer (ratified):
    - Light key:        n-butane (C4) -- the measured residual in the bottoms.
    - Representative heavy: n-hexane (C6) -- stands in for the C5+ naphtha.
      Chosen because it is the unique single n-alkane that (a) puts the
      bottoms hotter than the tray-6 temperature (physically required, since
      tray 6 is above the reboiler) and (b) keeps n-butane subcritical
      (< 152 C) at the operating temperature. n-C5 is too light; n-C7 pushes
      the bottom above n-butane's critical temperature.

Both Perry's S4 and Smith Ch. 13 state Raoult's law is invalid above the
critical temperature of any species; the n-butane t_max = 425.12 K (152 C)
ceiling is enforced by dippr101_psat(strict_range=True).
"""

from __future__ import annotations

from ipis.physics.dippr101 import N_BUTANE, N_HEXANE, DIPPR101Params, dippr101_psat


def light_key_fraction(
    T: float,
    P: float,
    light: DIPPR101Params = N_BUTANE,
    heavy: DIPPR101Params = N_HEXANE,
    *,
    clip: bool = True,
) -> float:
    """Light-key liquid mole fraction by ideal-binary bubble-point inversion.

        x_L = (P - Psat_H(T)) / (Psat_L(T) - Psat_H(T))

    Args:
        T: Temperature in K (must be within both components' valid ranges).
        P: Pressure in Pa.
        light: Light-key DIPPR-101 params (default n-butane).
        heavy: Representative-heavy DIPPR-101 params (default n-hexane).
        clip: If True, clip the result to [0, 1] (physical mole fraction).
            Out-of-range raw values indicate the (T, P) point is outside the
            bubble-point validity window for this binary; clipping yields a
            usable boundary value while preserving monotonicity.

    Returns:
        Light-key mole fraction (clipped to [0, 1] if clip=True).

    Raises:
        ValueError: If T is outside either component's valid range (e.g. the
            light key is supercritical), or the Psat denominator is degenerate.
    """
    psat_l = dippr101_psat(T, light, strict_range=True)
    psat_h = dippr101_psat(T, heavy, strict_range=True)
    denom = psat_l - psat_h
    if abs(denom) < 1e-9:
        raise ValueError(
            f"Degenerate volatility: Psat_light ~ Psat_heavy at T={T:.2f} K "
            f"({light.name}/{heavy.name}); cannot invert."
        )
    x_l = (P - psat_h) / denom
    if clip:
        return min(1.0, max(0.0, x_l))
    return x_l
