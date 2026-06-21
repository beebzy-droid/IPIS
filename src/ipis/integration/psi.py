"""Similitude coordinate system for IPIS closed-loop coverage propagation.

Instantiates the SCC similitude departure (Paper 3) on the debutanizer's
dimensionless coordinates and exposes the ψ-budget penalty that enters the
modifier-adaptation RTO as the constraint of
``docs/module4/formalization-spike.md`` §6::

    B(u) = 2 * (L1 * ||psi1(u) - psi1_star|| + L2 * ||psi2(u) - psi2_star||) <= eps

Enforcing ``B(u) <= eps`` certifies, per §5::

    P(S_k) >= 1 - (alpha1 + alpha2) - eps

Coordinate backbone -- Perry's Chemical Engineers' Handbook, 9th ed. (forms
verified in ``docs/module4/perry-verification.md``):

  * relative volatility         alpha = K_lk / K_hk          (Eq. 13-33)
  * Gilliland reflux coordinate  Psi_G = (R - Rmin) / (R + 1) (Eq. 13-30)
  * stripping factor             S = K * V / L               (Eq. 13-44)
  * pump affinity laws           Q ~ N, H ~ N^2, BHP ~ N^3   (Table 10-13)

``psi1`` lives in normalized (alpha, Psi_G, S) space (Module 1 regime).
``psi2`` lives in normalized pump-load space, coupled to the decision through
the affinity laws (Module 2 / FEMTO regime).

Within one RTO solve the regime fields (``alpha``, ``R_min``, ``strip_factor``)
are held at the current estimate while the decision (``R``, ``D``) varies; the
cross-cycle coupling (decision -> next regime) is handled by re-evaluating the
regime each cycle in the orchestrator, consistent with the per-cycle treatment
of the formalization spike.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
import numpy.typing as npt

# --- Perry's-verified physical constants ---------------------------------------

AFFINITY_BHP_EXPONENT: float = 3.0
"""Brake horsepower scales as the cube of impeller speed (Perry Table 10-13).
With capacity Q ~ N this gives BHP ~ Q^3, i.e. the reflux-pump mechanical load
scales as (reflux-flow ratio)^3 relative to the calibration reference."""


# --- Operating point and configuration -----------------------------------------


@dataclass(frozen=True)
class OperatingPoint:
    """Physical state at one RTO cycle.

    The decision is ``(R, D)``. The regime fields ``alpha``, ``R_min`` and
    ``strip_factor`` are supplied by the thermo/plant layer (CoolProp + Underwood
    for ``R_min``, the proper section flows for ``S``); ``psi.py`` does not
    recompute them, it only normalizes. ``reflux_flow`` is the rectifying liquid
    flow L = R*D seen by the reflux pump and drives the affinity-law load.
    """

    R: float  # reflux ratio L/D (decision)
    D: float  # distillate molar rate (decision)
    alpha: float  # relative volatility K_lk/K_hk at the key stage (Eq. 13-33)
    R_min: float  # Underwood minimum reflux for the current regime (Eq. 13-37/38)
    strip_factor: float  # S = K*V/L (Eq. 13-44), from the thermo layer
    reflux_flow: float  # rectifying liquid flow L seen by the reflux pump

    def __post_init__(self) -> None:
        for name in ("R", "D", "alpha", "R_min", "strip_factor", "reflux_flow"):
            val = getattr(self, name)
            if not np.isfinite(val):
                raise ValueError(f"OperatingPoint.{name} must be finite, got {val!r}")
        if self.D <= 0 or self.reflux_flow <= 0 or self.alpha <= 0:
            raise ValueError("D, reflux_flow and alpha must be strictly positive")

    @property
    def gilliland_coord(self) -> float:
        """Gilliland abscissa Psi_G = (R - Rmin)/(R + 1) -- Perry Eq. 13-30."""
        return (self.R - self.R_min) / (self.R + 1.0)


@dataclass(frozen=True)
class CoordinateScales:
    """Characteristic scales (the SCC normalizers, sigma) that render the nominal
    nonconformity-score distribution regime-invariant. Set at SCC calibration;
    the unit defaults below are deliberate placeholders -- override at calibration.
    """

    alpha_scale: float = 1.0
    gilliland_scale: float = 1.0
    strip_scale: float = 1.0
    pump_load_scale: float = 1.0


@dataclass(frozen=True)
class PsiConfig:
    """Full ψ-coordinate configuration for one debutanizer integration.

    ``L1`` and ``L2`` are REQUIRED (no defaults) by design: a configuration
    cannot be built without committing to Lipschitz constants and their
    provenance. ``L2`` loads from the Paper 3 robustness sweep
    (``docs/paper/evidence/``); ``L1`` from the Module 1 sweep -- open item O2,
    estimated via :func:`estimate_lipschitz`. Do not fabricate these.
    """

    L1: float  # Lipschitz constant of the M1 score-quantile in psi1-space (O2)
    L2: float  # Lipschitz constant of the M2 score-quantile in psi2-space (Paper 3)
    fortuna_op: OperatingPoint  # M1 calibration regime (column anchor)
    femto_ref_reflux_flow: float  # M2 calibration reference reflux flow (pump anchor)
    scales: CoordinateScales = CoordinateScales()

    def __post_init__(self) -> None:
        if not (np.isfinite(self.L1) and np.isfinite(self.L2)):
            raise ValueError("L1 and L2 must be finite Lipschitz constants")
        if self.L1 < 0 or self.L2 < 0:
            raise ValueError("Lipschitz constants must be non-negative")
        if self.femto_ref_reflux_flow <= 0:
            raise ValueError("femto_ref_reflux_flow must be strictly positive")


# --- Coordinate maps ------------------------------------------------------------


def psi1(op: OperatingPoint, scales: CoordinateScales) -> npt.NDArray[np.float64]:
    """Module 1 similitude coordinate: normalized (alpha, Psi_G, S)."""
    return np.array(
        [
            op.alpha / scales.alpha_scale,
            op.gilliland_coord / scales.gilliland_scale,
            op.strip_factor / scales.strip_scale,
        ],
        dtype=np.float64,
    )


def pump_load(reflux_flow: float, ref_flow: float) -> float:
    """Affinity-law pump load relative to the calibration reference.

    BHP ~ N^3 and Q ~ N (Perry Table 10-13) give load ~ (Q/Q_ref)^3, with the
    reflux flow standing in for pump capacity Q.
    """
    return (reflux_flow / ref_flow) ** AFFINITY_BHP_EXPONENT


def psi2(
    op: OperatingPoint, ref_flow: float, scales: CoordinateScales
) -> npt.NDArray[np.float64]:
    """Module 2 similitude coordinate: normalized pump load (affinity-coupled)."""
    return np.array(
        [pump_load(op.reflux_flow, ref_flow) / scales.pump_load_scale],
        dtype=np.float64,
    )


def _psi1_star(cfg: PsiConfig) -> npt.NDArray[np.float64]:
    return psi1(cfg.fortuna_op, cfg.scales)


def _psi2_star(cfg: PsiConfig) -> npt.NDArray[np.float64]:
    # At the FEMTO reference flow the load ratio is 1.0 by construction.
    return np.array([1.0 / cfg.scales.pump_load_scale], dtype=np.float64)


# --- Departures, penalty, and the certificate ----------------------------------


def departures(op: OperatingPoint, cfg: PsiConfig) -> tuple[float, float]:
    """Return (||Delta psi1||, ||Delta psi2||) for the operating point."""
    d1 = float(np.linalg.norm(psi1(op, cfg.scales) - _psi1_star(cfg)))
    d2 = float(
        np.linalg.norm(
            psi2(op, cfg.femto_ref_reflux_flow, cfg.scales) - _psi2_star(cfg)
        )
    )
    return d1, d2


def budget_penalty(op: OperatingPoint, cfg: PsiConfig) -> float:
    """B(u) = 2 (L1 ||Delta psi1|| + L2 ||Delta psi2||) -- spike §6."""
    d1, d2 = departures(op, cfg)
    return 2.0 * (cfg.L1 * d1 + cfg.L2 * d2)


def certified_coverage(alpha1: float, alpha2: float, eps: float) -> float:
    """Lower bound on P(S_k) when B(u) <= eps holds -- spike §5/§6."""
    return 1.0 - (alpha1 + alpha2) - eps


class BudgetReport(NamedTuple):
    """One-cycle ψ-budget evaluation for logging by the coverage harness."""

    penalty: float
    d1: float
    d2: float
    slack: float  # eps - B(u); a hard-constraint feasibility margin
    coverage_floor: float  # certified lower bound on P(S_k)
    feasible: bool


def evaluate_budget(
    op: OperatingPoint,
    cfg: PsiConfig,
    eps: float,
    alpha1: float,
    alpha2: float,
) -> BudgetReport:
    """Evaluate the ψ-budget constraint and the certificate at one operating point."""
    d1, d2 = departures(op, cfg)
    penalty = 2.0 * (cfg.L1 * d1 + cfg.L2 * d2)
    slack = eps - penalty
    return BudgetReport(
        penalty=penalty,
        d1=d1,
        d2=d2,
        slack=slack,
        coverage_floor=certified_coverage(alpha1, alpha2, eps),
        feasible=slack >= 0.0,
    )


# --- Lipschitz estimation (open item O2 / Paper 3 sweep) ------------------------


def estimate_lipschitz(
    psi_points: npt.ArrayLike, score_quantiles: npt.ArrayLike
) -> float:
    """Empirical Lipschitz constant of a score-quantile in psi-space.

    Given the psi-coordinates of calibration regimes and the (1 - alpha)
    nonconformity-score quantile measured at each, return the largest
    finite-difference slope ``|q_i - q_j| / ||psi_i - psi_j||`` over all pairs --
    a conservative estimate of the local Lipschitz constant L used in the SCC
    departure bound (Paper 3). Feed M1 calibration data here to discharge O2.
    """
    pts = np.atleast_2d(np.asarray(psi_points, dtype=np.float64))
    q = np.asarray(score_quantiles, dtype=np.float64).ravel()
    if pts.shape[0] != q.shape[0]:
        raise ValueError("psi_points and score_quantiles must have equal length")
    best = 0.0
    for i in range(len(q)):
        for j in range(i + 1, len(q)):
            dist = float(np.linalg.norm(pts[i] - pts[j]))
            if dist > 0.0:
                best = max(best, abs(q[i] - q[j]) / dist)
    return best
