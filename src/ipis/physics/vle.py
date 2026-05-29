"""Vapor-liquid equilibrium calculations.

Bubble-point pressure via modified Raoult's law, Perry's Eqs. (4-195),
(4-196):

    P = sum_i x_i * gamma_i * P_i^sat
    y_i = x_i * gamma_i * P_i^sat / P

The activity-coefficient model is pluggable (IdealSolution for near-ideal
hydrocarbon systems, WilsonBinary for non-ideal systems). With
IdealSolution, this reduces to Raoult's law (Perry's Eq. 4-194).
"""

from __future__ import annotations

from collections.abc import Sequence

from ipis.physics.activity import ActivityModel
from ipis.physics.antoine import AntoineParams, antoine_psat


def bubble_pressure(
    x: Sequence[float],
    T: float,
    components: Sequence[AntoineParams],
    activity_model: ActivityModel,
) -> tuple[float, list[float]]:
    """Bubble-point pressure and vapor composition (modified Raoult's law).

    Perry's Eqs. (4-195), (4-196).

    Args:
        x: Liquid mole fractions, summing to ~1.
        T: Temperature in K.
        components: Antoine parameters per component, same order as x.
        activity_model: Activity-coefficient model (Ideal or Wilson).

    Returns:
        (P_bubble in kPa, vapor mole fractions y).

    Raises:
        ValueError: If lengths mismatch or x does not sum to ~1.
    """
    if not (len(x) == len(components)):
        raise ValueError("x and components must have the same length.")
    if abs(sum(x) - 1.0) > 1e-6:
        raise ValueError(f"Liquid mole fractions must sum to 1, got {sum(x):.6f}.")

    psats = [antoine_psat(T, c) for c in components]
    gammas = activity_model.gamma(x, T)
    partials = [xi * gi * pi for xi, gi, pi in zip(x, gammas, psats, strict=True)]
    P = sum(partials)
    y = [p / P for p in partials]
    return P, y
