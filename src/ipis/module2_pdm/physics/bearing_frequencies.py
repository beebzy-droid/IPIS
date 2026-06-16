"""Bearing characteristic defect frequencies — Module 2 physics layer.

This is the M2 analogue of the VLE physics in M1: the fault-frequency kinematics
are first-principles (bearing geometry + shaft speed), not fitted. They define
where, in an envelope spectrum, energy must appear for each localized defect.

Kinematic relations (no-slip; Randall & Antoni 2011 [tutorial], Smith & Randall
2015 Eqs. in §1). With n rolling elements, ball diameter d, pitch diameter D,
contact angle phi, and shaft frequency f_r:

    FTF  = (f_r / 2) * (1 - (d/D) cos phi)               # cage
    BPFO = (n f_r / 2) * (1 - (d/D) cos phi)             # outer race
    BPFI = (n f_r / 2) * (1 + (d/D) cos phi)             # inner race
    BSF  = (D f_r / 2d) * (1 - ((d/D) cos phi)**2)       # rolling element

The f_r in BSF is required (Smith & Randall 2015 explicitly note it is missing
from one widely-cited reference). Real bearings slip, so observed frequencies
deviate up to ~1-2% from these kinematic values.

VERIFY-BEFORE-LOAD-BEARING. The CWRU bearing multipliers below are taken from the
primary source (Smith & Randall 2015, Table 2) and are the ground truth. The
geometry (d, D, phi) is *not* published there; it is back-validated by
`self_consistency_residual`, which confirms the geometry reproduces the published
multipliers to <1%. For CWRU work, prefer the published multipliers; the
geometry path generalizes to FEMTO / hardware where only geometry is known.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Tolerance for the no-slip kinematic identity (slip causes ~1-2% drift in
# practice; geometry-vs-published agreement should be far tighter, <1%).
SELF_CONSISTENCY_TOL = 0.01


@dataclass(frozen=True)
class BearingGeometry:
    """Rolling-element bearing geometry for defect-frequency computation.

    Diameters are unit-agnostic (only the ratio d/D enters); contact angle in
    radians. n is the number of rolling elements.
    """

    n_rolling_elements: int
    ball_diameter: float
    pitch_diameter: float
    contact_angle_rad: float = 0.0

    def __post_init__(self) -> None:
        if self.n_rolling_elements <= 0:
            raise ValueError("n_rolling_elements must be positive")
        if not (0.0 < self.ball_diameter < self.pitch_diameter):
            raise ValueError("require 0 < ball_diameter < pitch_diameter")

    @property
    def _gamma(self) -> float:
        """The dimensionless group (d/D) cos(phi) that drives every multiplier."""
        return (self.ball_diameter / self.pitch_diameter) * math.cos(self.contact_angle_rad)


@dataclass(frozen=True)
class DefectMultipliers:
    """Defect frequencies expressed as multiples of shaft speed (order domain)."""

    bpfo: float
    bpfi: float
    ftf: float
    bsf: float

    def at_shaft_hz(self, shaft_hz: float) -> DefectFrequencies:
        """Scale order-domain multipliers to Hz at a given shaft speed."""
        if shaft_hz < 0:
            raise ValueError("shaft_hz must be non-negative")
        return DefectFrequencies(
            bpfo=self.bpfo * shaft_hz,
            bpfi=self.bpfi * shaft_hz,
            ftf=self.ftf * shaft_hz,
            bsf=self.bsf * shaft_hz,
        )


@dataclass(frozen=True)
class DefectFrequencies:
    """Defect frequencies in Hz at a specific shaft speed."""

    bpfo: float
    bpfi: float
    ftf: float
    bsf: float


def multipliers_from_geometry(geom: BearingGeometry) -> DefectMultipliers:
    """Order-domain defect multipliers from first-principles kinematics."""
    g = geom._gamma
    n = geom.n_rolling_elements
    return DefectMultipliers(
        bpfo=(n / 2.0) * (1.0 - g),
        bpfi=(n / 2.0) * (1.0 + g),
        ftf=(1.0 / 2.0) * (1.0 - g),
        bsf=(geom.pitch_diameter / (2.0 * geom.ball_diameter)) * (1.0 - g * g),
    )


def frequencies_from_geometry(geom: BearingGeometry, shaft_hz: float) -> DefectFrequencies:
    """Defect frequencies in Hz from geometry and shaft speed."""
    return multipliers_from_geometry(geom).at_shaft_hz(shaft_hz)


def self_consistency_residual(geom: BearingGeometry, published: DefectMultipliers) -> float:
    """Max relative error between geometry-derived and published multipliers.

    This is the verify-before-load-bearing gate for the physics layer: if a
    bearing's geometry does not reproduce its primary-sourced published
    multipliers, the geometry is wrong and must not be used. Returns a single
    scalar (the worst of the four relative errors) for assertion in tests.
    """
    derived = multipliers_from_geometry(geom)
    pairs = (
        (derived.bpfo, published.bpfo),
        (derived.bpfi, published.bpfi),
        (derived.ftf, published.ftf),
        (derived.bsf, published.bsf),
    )
    return max(abs(d - p) / p for d, p in pairs)


@dataclass(frozen=True)
class KnownBearing:
    """A catalogued bearing: identity, geometry, and primary-sourced multipliers."""

    name: str
    geometry: BearingGeometry
    published: DefectMultipliers
    source: str


# CWRU rig bearings. Multipliers are VERIFIED from Smith & Randall (2015),
# "Rolling element bearing diagnostics using the CWRU data: A benchmark study,"
# MSSP 64-65, Table 2. Geometry (d, D, phi, n) for the 6205 is the widely-used
# value set, back-validated by self_consistency_residual against Table 2
# (residual < 1%; see tests). The 6203 geometry is intentionally omitted: its
# multipliers are taken directly from Table 2 (primary), and its d/D is not
# needed for CWRU fan-end analysis. 0.028 in. DE faults used an equivalent NTN
# bearing (Smith & Randall, Table 2 footnote) — flag in the file manifest.
CWRU_DE_6205 = KnownBearing(
    name="SKF 6205-2RS JEM (CWRU drive end)",
    geometry=BearingGeometry(
        n_rolling_elements=9,
        ball_diameter=0.3126,  # in (widely-cited 6205 value)
        pitch_diameter=1.537,  # in
        contact_angle_rad=0.0,  # deep-groove, radial
    ),
    published=DefectMultipliers(bpfo=3.585, bpfi=5.415, ftf=0.3983, bsf=2.357),
    source="Smith & Randall 2015, Table 2 (multipliers); geometry back-validated",
)

# Fan-end 6203: multipliers from Smith & Randall Table 2 (primary). Geometry not
# catalogued (not required for CWRU FE analysis; would be back-validated if added).
CWRU_FE_6203_MULTIPLIERS = DefectMultipliers(bpfo=3.053, bpfi=4.947, ftf=0.3816, bsf=1.994)

KNOWN_BEARINGS: dict[str, KnownBearing] = {"cwru_de_6205": CWRU_DE_6205}
