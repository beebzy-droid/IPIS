"""DIPPR equation 101 vapor-pressure correlation.

Perry's Chemical Engineers' Handbook, 9th ed., Table 2-8 (Vapor Pressure of
Organic Compounds). Equation 101 form:

    ln(P_sat / Pa) = C1 + C2/T + C3 ln(T) + C4 * T^C5,   T in K

This is the 5-constant form Perry's 9th ed. tabulates (more accurate over a
wide range than the 3-constant Antoine form in antoine.py). Used for the
n-alkane vapor pressures in the soft-sensor bubble-point inversion.

Constants verified against Perry's Table 2-8 Tmin/Tmax check values and
known normal boiling points (see tests). Each compound's valid range is
[Tmin, Tmax]; Tmax is at/near the critical temperature, beyond which the
correlation must not be used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class DIPPR101Params:
    """DIPPR-101 coefficients (P in Pa, T in K) with validity range.

    ln(P_sat / Pa) = C1 + C2/T + C3 ln(T) + C4 * T^C5

    Attributes:
        C1, C2, C3, C4, C5: DIPPR-101 coefficients.
        t_min: Lower validity temperature (K).
        t_max: Upper validity temperature (K); at/near critical temperature.
        name: Component label.
    """

    C1: float
    C2: float
    C3: float
    C4: float
    C5: float
    t_min: float
    t_max: float
    name: str = ""


def dippr101_psat(T: float, p: DIPPR101Params, *, strict_range: bool = True) -> float:
    """Saturated vapor pressure via DIPPR-101 (Perry's Table 2-8 form), in Pa.

    Args:
        T: Temperature in K.
        p: DIPPR-101 coefficients with validity range.
        strict_range: If True, raise when T is outside [t_min, t_max]. The
            upper bound matters physically: above the critical temperature the
            species has no vapor pressure and any VLE using it is invalid.

    Returns:
        Saturated vapor pressure in Pa.

    Raises:
        ValueError: If strict_range and T is outside [t_min, t_max].
    """
    if strict_range and not (p.t_min <= T <= p.t_max):
        raise ValueError(
            f"T={T:.2f} K outside valid range [{p.t_min:.2f}, {p.t_max:.2f}] "
            f"for {p.name or 'component'}; above t_max the species is supercritical."
        )
    return math.exp(p.C1 + p.C2 / T + p.C3 * math.log(T) + p.C4 * (T**p.C5))


# --- Perry's 9th ed. Table 2-8 constants (n-alkanes), VERIFIED ---
# Each reproduces Perry's P(Tmin), P(Tmax), and the known normal boiling point.
N_BUTANE = DIPPR101Params(
    66.343, -4363.2, -7.046, 9.4509e-6, 2, t_min=134.86, t_max=425.12, name="n-butane"
)
N_PENTANE = DIPPR101Params(
    78.741, -5420.3, -8.8253, 9.6171e-6, 2, t_min=143.42, t_max=469.7, name="n-pentane"
)
N_HEXANE = DIPPR101Params(
    104.65, -6995.5, -12.702, 1.2381e-5, 2, t_min=177.83, t_max=507.6, name="n-hexane"
)
N_HEPTANE = DIPPR101Params(
    87.829, -6996.4, -9.8802, 7.2099e-6, 2, t_min=182.57, t_max=540.2, name="n-heptane"
)
