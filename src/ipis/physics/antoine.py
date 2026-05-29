"""Antoine vapor-pressure correlation.

Perry's Chemical Engineers' Handbook, 9th ed., Eq. (4-15).

IMPORTANT — equation form: For the parameter sets tabulated in Perry's
Section 4 (e.g., Example 4-11), Eq. (4-15) is the NATURAL-LOG form:

    ln(P_sat / kPa) = A - B / (T + C),   T in K

Using a base-10 form with these parameters overpredicts by ~340x. Verified
against Perry's Example 4-11: acetone and n-hexane at T = 325.15 K give
P_sat = 87.616 and 58.105 kPa respectively.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AntoineParams:
    """Antoine coefficients for the natural-log form, P in kPa, T in K.

    ln(P_sat / kPa) = A - B / (T + C)

    Attributes:
        A: Dimensionless coefficient.
        B: Coefficient with units of temperature (K).
        C: Temperature offset (K).
        name: Optional component label.
    """

    A: float
    B: float
    C: float
    name: str = ""


def antoine_psat(T: float, params: AntoineParams) -> float:
    """Saturated vapor pressure via Perry's Eq. (4-15), natural-log form.

    Args:
        T: Temperature in K.
        params: Antoine coefficients (natural-log form, kPa).

    Returns:
        Saturated vapor pressure in kPa.

    Raises:
        ValueError: If the denominator (T + C) is non-positive.
    """
    denom = T + params.C
    if denom <= 0:
        raise ValueError(
            f"Antoine denominator (T + C) = {denom:.3f} <= 0 for {params.name or 'component'}; "
            "temperature out of valid range."
        )
    return math.exp(params.A - params.B / denom)
