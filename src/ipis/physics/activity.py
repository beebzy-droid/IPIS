"""Liquid-phase activity-coefficient models.

Pluggable models behind a common interface so the VLE engine is agnostic to
the choice. For near-ideal light-hydrocarbon systems (the Debutanizer's
C4/C5 mixture) use IdealSolution (gamma = 1). For strongly non-ideal
systems (e.g., acetone/n-hexane in Perry's Example 4-11) use WilsonBinary.

References:
    Perry's Chemical Engineers' Handbook, 9th ed., Eqs. (4-163), (4-164)
    (Wilson equation).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class ActivityModel(Protocol):
    """Common interface for activity-coefficient models."""

    def gamma(self, x: Sequence[float], T: float) -> list[float]:
        """Return activity coefficients for liquid mole fractions x at temperature T."""
        ...


class IdealSolution:
    """Ideal solution: gamma_i = 1 for all components (Raoult's law).

    Appropriate for near-ideal systems such as light-hydrocarbon mixtures.
    """

    def gamma(self, x: Sequence[float], T: float) -> list[float]:  # noqa: ARG002
        """Return a list of 1.0 with the same length as x."""
        return [1.0] * len(x)


@dataclass(frozen=True)
class WilsonBinary:
    """Binary Wilson activity-coefficient model.

    Perry's Eqs. (4-163), (4-164):
        Lambda_12 = (V2/V1) exp(-a12 / RT)
        Lambda_21 = (V1/V2) exp(-a21 / RT)
        ln g1 = -ln(x1 + x2 L12) + x2 * lam
        ln g2 = -ln(x2 + x1 L21) - x1 * lam
        lam   = L12/(x1 + x2 L12) - L21/(x2 + x1 L21)

    Attributes:
        V: Molar volumes (V1, V2) in cm^3/mol.
        a: Interaction energies (a12, a21) in cal/mol.
        R: Gas constant in cal/(mol K). Default 1.987.
    """

    V: tuple[float, float]
    a: tuple[float, float]
    R: float = 1.987

    def _lambdas(self, T: float) -> tuple[float, float]:
        rt = self.R * T
        v1, v2 = self.V
        a12, a21 = self.a
        lam12 = (v2 / v1) * math.exp(-a12 / rt)
        lam21 = (v1 / v2) * math.exp(-a21 / rt)
        return lam12, lam21

    def gamma(self, x: Sequence[float], T: float) -> list[float]:
        """Return [gamma_1, gamma_2] for a binary mixture.

        Args:
            x: Liquid mole fractions [x1, x2]; must sum to ~1 and have length 2.
            T: Temperature in K.

        Returns:
            [gamma_1, gamma_2].

        Raises:
            ValueError: If x is not length 2.
        """
        if len(x) != 2:
            raise ValueError("WilsonBinary supports binary mixtures only (len(x) == 2).")
        x1, x2 = x[0], x[1]
        lam12, lam21 = self._lambdas(T)
        lam = lam12 / (x1 + x2 * lam12) - lam21 / (x2 + x1 * lam21)
        ln_g1 = -math.log(x1 + x2 * lam12) + x2 * lam
        ln_g2 = -math.log(x2 + x1 * lam21) - x1 * lam
        return [math.exp(ln_g1), math.exp(ln_g2)]
