"""Fenske-Underwood-Gilliland (FUG) shortcut multicomponent distillation.

Equation numbers refer to Perry's Chemical Engineers' Handbook, 9th ed.,
Section 13 (authoritative for formula citations). The Underwood numerical
verification fixture uses Perry's 8th ed., Table 13-6, which prints the
fully converged worked example (theta = 1.3647, R_min = 0.9426) that the
9th ed. compresses into narrative.

Documented assumptions (per Perry's own caveats):
    - Constant molar overflow (inherent in the Underwood equations).
    - Saturated-liquid reflux (not subcooled).
    - Sharp split: only the two key components distribute at minimum reflux.
    - The Underwood R_min step uses Fenske (total-reflux) x_D values as an
      approximation; Perry's notes this inconsistency but retains it for
      shortcut speed.

This is the Tier-1 analytical column model producing y_physics for the
hybrid soft sensor. See ADR-004 (analytical-first physics baseline).
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from scipy.optimize import brentq


def relative_volatility(k_i: float, k_ref: float) -> float:
    """Relative volatility alpha_i = K_i / K_ref. Perry's 9th ed. Eq. (13-33).

    Args:
        k_i: K-value of component i.
        k_ref: K-value of the reference component.

    Returns:
        Relative volatility of i to the reference.

    Raises:
        ValueError: If k_ref is non-positive.
    """
    if k_ref <= 0:
        raise ValueError(f"Reference K-value must be positive, got {k_ref}.")
    return k_i / k_ref


def effective_alpha(*alphas: float) -> float:
    """Geometric-mean effective relative volatility. Perry's Eqs. (13-35)/(13-36).

    Two args -> sqrt(a_top * a_bottom); three args -> cube root of the product.

    Args:
        *alphas: Stage relative volatilities (typically top & bottom, or
            top, middle & bottom).

    Returns:
        Geometric-mean effective relative volatility.

    Raises:
        ValueError: If no alphas given or any is non-positive.
    """
    if not alphas:
        raise ValueError("At least one alpha is required.")
    if any(a <= 0 for a in alphas):
        raise ValueError("All relative volatilities must be positive.")
    product = math.prod(alphas)
    return product ** (1.0 / len(alphas))


def fenske_nmin(
    d_lk: float,
    b_lk: float,
    d_hk: float,
    b_hk: float,
    alpha_lk: float,
) -> float:
    """Minimum stages at total reflux. Perry's 9th ed. Eq. (13-32).

        N_min = log[(D x_LK / B x_LK)(B x_HK / D x_HK)] / log(alpha_LK)

    where the heavy key is the reference component (alpha_HK = 1).

    Args:
        d_lk: Light-key flow in the distillate.
        b_lk: Light-key flow in the bottoms.
        d_hk: Heavy-key (reference) flow in the distillate.
        b_hk: Heavy-key flow in the bottoms.
        alpha_lk: Relative volatility of the light key (referenced to HK).

    Returns:
        Minimum number of equilibrium stages (including reboiler).

    Raises:
        ValueError: If any flow is non-positive or alpha_lk <= 1.
    """
    if min(d_lk, b_lk, d_hk, b_hk) <= 0:
        raise ValueError("All key-component flows must be positive.")
    if alpha_lk <= 1.0:
        raise ValueError(
            f"alpha_lk must exceed 1 (LK more volatile than HK reference), got {alpha_lk}."
        )
    ratio = (d_lk / b_lk) * (b_hk / d_hk)
    return math.log10(ratio) / math.log10(alpha_lk)


def underwood_theta(
    alphas: Mapping[str, float],
    z_feed: Mapping[str, float],
    q: float,
    alpha_hk: float,
    alpha_lk: float,
) -> float:
    """Underwood common root theta. Perry's 9th ed. Eq. (13-38).

        sum_i [ alpha_i z_F,i / (alpha_i - theta) ] = 1 - q

    The relevant root lies between alpha_HK and alpha_LK. Solved to high
    precision (Perry's warns the alpha-theta difference can be small).

    Args:
        alphas: Relative volatility per component (referenced to HK).
        z_feed: Feed mole fraction per component (same keys as alphas).
        q: Feed thermal condition (1.0 = saturated liquid).
        alpha_hk: Relative volatility of the heavy key (lower bracket).
        alpha_lk: Relative volatility of the light key (upper bracket).

    Returns:
        The Underwood root theta in (alpha_HK, alpha_LK).

    Raises:
        ValueError: If keys mismatch or the bracket is invalid.
    """
    if set(alphas) != set(z_feed):
        raise ValueError("alphas and z_feed must have identical component keys.")
    if not (alpha_hk < alpha_lk):
        raise ValueError("Require alpha_hk < alpha_lk to bracket the root.")

    def residual(theta: float) -> float:
        return sum(alphas[c] * z_feed[c] / (alphas[c] - theta) for c in alphas) - (1.0 - q)

    eps = 1e-9
    return brentq(residual, alpha_hk + eps, alpha_lk - eps, xtol=1e-8)


def underwood_rmin(
    alphas: Mapping[str, float],
    x_dist: Mapping[str, float],
    theta: float,
) -> float:
    """Minimum reflux ratio. Perry's 9th ed. Eq. (13-37).

        R_min + 1 = sum_i [ alpha_i x_D,i / (alpha_i - theta) ]

    Note: x_D are the Fenske total-reflux distillate compositions (Perry's
    documented approximation for the shortcut method).

    Args:
        alphas: Relative volatility per component (referenced to HK).
        x_dist: Distillate mole fraction per component (Fenske x_D).
        theta: Underwood root from underwood_theta.

    Returns:
        Minimum reflux ratio R_min.

    Raises:
        ValueError: If keys mismatch.
    """
    if set(alphas) != set(x_dist):
        raise ValueError("alphas and x_dist must have identical component keys.")
    r_min_plus_1 = sum(alphas[c] * x_dist[c] / (alphas[c] - theta) for c in alphas)
    return r_min_plus_1 - 1.0


def gilliland_n(reflux: float, r_min: float, n_min: float) -> float:
    """Actual stages via the Gilliland-Molokanov correlation. Perry's Eq. (13-30).

        (N - N_min)/(N + 1) = 1 - exp[ ((1 + 54.4 Psi)/(11 + 117.2 Psi))
                                       * ((Psi - 1)/sqrt(Psi)) ]
        Psi = (R - R_min)/(R + 1)

    Args:
        reflux: Actual operating reflux ratio R (must exceed r_min).
        r_min: Minimum reflux ratio.
        n_min: Minimum stages (from Fenske).

    Returns:
        Actual number of equilibrium stages N.

    Raises:
        ValueError: If reflux <= r_min (Psi must be positive).
    """
    if reflux <= r_min:
        raise ValueError(f"Operating reflux {reflux} must exceed R_min {r_min}.")
    psi = (reflux - r_min) / (reflux + 1.0)
    y = 1.0 - math.exp(((1.0 + 54.4 * psi) / (11.0 + 117.2 * psi)) * ((psi - 1.0) / math.sqrt(psi)))
    # y = (N - N_min)/(N + 1)  ->  solve for N
    return (n_min + y) / (1.0 - y)
