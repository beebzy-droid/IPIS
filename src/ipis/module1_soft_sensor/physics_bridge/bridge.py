"""Physics-to-data bridge for the soft sensor.

Connects the first-principles bubble-point inversion (real engineering units)
to the pre-normalized [0, 1] Debutanizer benchmark data, which has no
published denormalization constants.

Pipeline:
    1. Denormalize the relevant normalized inputs to nominal real units
       (linear map using literature nominal ranges).
    2. Run bubble-point inversion -> y_physics (light-key fraction, real units).
    3. Affine output scale-bias correction (output-only SBC, Lu & Gao 2008a,
       degenerate case): y_norm ~= S_O * y_physics + B_O, fit by least squares.
       S_O, B_O absorb the unknown min-max normalization constants of the
       target. The Path B ML residual (built later) handles the remaining
       nonlinear physics-vs-truth gap; this affine step only undoes the
       linear normalization.

Why affine SBC and not full functional SBC: the normalization is itself an
affine transform, so its inverse is affine. The five model-migration papers
(Yan 2011 etc.) use full functional SBC for TWO-process migration; the M1
normalization problem is one process + a units mismatch, so only the
degenerate output-affine case applies here (see ADR / source-map).

Configuration (ratified): tray-6 temperature drives the physics (the
pressure-compensated control temperature, most sensitive to C4 breakthrough
and safely subcritical), with bottom pressure derived from top pressure plus
a nominal column delta-P.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ipis.physics.bubble_point_inversion import light_key_fraction

# --- Nominal denormalization ranges (literature; SBC absorbs residual scale) ---
# Tray-6 temperature: Fortuna et al. debutanizer ~102-110 C; widen slightly for headroom.
TRAY6_T_MIN_C: float = 100.0
TRAY6_T_MAX_C: float = 112.0
# Column pressure: top ~4-5 bar; bottom = top + nominal column delta-P (~0.3-0.5 bar).
COL_P_MIN_BAR: float = 4.5
COL_P_MAX_BAR: float = 5.5

_C_TO_K = 273.15
_BAR_TO_PA = 1.0e5


def denormalize(norm: float, lo: float, hi: float) -> float:
    """Map a [0, 1] normalized value to real units: lo + norm * (hi - lo)."""
    return lo + norm * (hi - lo)


@dataclass(frozen=True)
class BridgeConfig:
    """Nominal ranges for denormalizing the physics-driving inputs."""

    t_min_c: float = TRAY6_T_MIN_C
    t_max_c: float = TRAY6_T_MAX_C
    p_min_bar: float = COL_P_MIN_BAR
    p_max_bar: float = COL_P_MAX_BAR


def physics_estimate(
    t_norm: float,
    p_norm: float,
    config: BridgeConfig | None = None,
) -> float:
    """Compute y_physics (light-key fraction) from normalized T and P inputs.

    Args:
        t_norm: Normalized tray-6 temperature in [0, 1].
        p_norm: Normalized column pressure in [0, 1].
        config: Denormalization ranges (defaults to module nominals).

    Returns:
        Light-key (C4) mole fraction in [0, 1] from bubble-point inversion.
    """
    cfg = config or BridgeConfig()
    t_k = denormalize(t_norm, cfg.t_min_c, cfg.t_max_c) + _C_TO_K
    p_pa = denormalize(p_norm, cfg.p_min_bar, cfg.p_max_bar) * _BAR_TO_PA
    return light_key_fraction(t_k, p_pa)


@dataclass
class AffineSBC:
    """Output-only affine scale-bias correction: y_norm ~= S_O * y_physics + B_O.

    Fit by ordinary least squares. Degenerate (output-only) case of the
    input-output SBC of Lu & Gao (2008a).

    Attributes:
        scale: Fitted S_O.
        bias: Fitted B_O.
        r_squared: Coefficient of determination of the fit.
        n: Number of points used.
    """

    scale: float = field(default=float("nan"))
    bias: float = field(default=float("nan"))
    r_squared: float = field(default=float("nan"))
    n: int = 0

    def fit(self, y_physics: Sequence[float], y_target: Sequence[float]) -> AffineSBC:
        """Least-squares fit of S_O, B_O mapping y_physics onto y_target.

        Args:
            y_physics: Physics estimates (real-unit light-key fractions).
            y_target: Normalized target values from the dataset.

        Returns:
            Self, with scale, bias, r_squared, n populated.

        Raises:
            ValueError: If inputs differ in length, have < 2 points, or
                y_physics has zero variance (cannot fit a slope).
        """
        if len(y_physics) != len(y_target):
            raise ValueError("y_physics and y_target must have the same length.")
        n = len(y_physics)
        if n < 2:
            raise ValueError("Need at least 2 points to fit an affine model.")

        mean_x = sum(y_physics) / n
        mean_y = sum(y_target) / n
        sxx = sum((x - mean_x) ** 2 for x in y_physics)
        sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(y_physics, y_target, strict=True))
        if sxx < 1e-15:
            raise ValueError("y_physics has zero variance; cannot fit a slope.")

        self.scale = sxy / sxx
        self.bias = mean_y - self.scale * mean_x
        ss_tot = sum((y - mean_y) ** 2 for y in y_target)
        ss_res = sum(
            (y - (self.scale * x + self.bias)) ** 2
            for x, y in zip(y_physics, y_target, strict=True)
        )
        self.r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-15 else float("nan")
        self.n = n
        return self

    def predict(self, y_physics: float) -> float:
        """Apply the fitted affine correction to a physics estimate."""
        return self.scale * y_physics + self.bias
