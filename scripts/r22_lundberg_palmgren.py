"""R2.2: sigma and psi derived for rolling-contact fatigue, with a numerical instance.

Reviewer 2 (major 2): the paper sketches how the dimensionless scale and the similitude
departure arise for rolling-contact fatigue, but never derives psi for that law; only the
simulator's knob eta stands in for psi anywhere. A practitioner has no worked example of
deciding which Buckingham Pi groups become the scale and which remain as the departure.

DERIVATION
----------
Governing quantities for bearing fatigue life: life t [T], applied dynamic equivalent load
P [F], basic dynamic load rating C [F], rotational speed n [1/T]. With two independent
dimensions (force, time) and four quantities, Buckingham Pi gives two groups:

    Pi_1 = t * n          (life expressed in revolutions)
    Pi_2 = P / C          (load ratio)

The Lundberg-Palmgren rating life is the relation between them,

    Pi_1 = 10^6 * Pi_2^(-p),        p = 3 (ball), 10/3 (roller),

so the SCALE-SETTING content is exactly the load-speed group, and the characteristic life is

    sigma = T_L = 10^6 * (C/P)^p / (60 n)      [hours, n in rpm].

WHAT IS LEFT OVER IS PSI
------------------------
ISO 281 does not stop at the basic rating life. The modified life is

    L_nm = a_1 * a_ISO * L_10,     a_ISO = f( e_C * C_u / P , kappa ),

and the arguments of a_ISO are precisely the dimensionless groups the basic rating life does
NOT absorb:

    kappa = nu / nu_1     viscosity ratio (the lubrication regime)
    e_C * C_u / P         contamination and fatigue-load-limit group

Therefore, for rolling-contact fatigue,

    sigma absorbs LOAD and SPEED;
    psi  is the LUBRICATION REGIME (principally kappa), plus contamination.

The reference viscosity is itself fixed by geometry and speed (ISO 281):

    nu_1 = 4500 * n^-0.5 * d_m^-0.5     (n >= 1000 rpm)
    nu_1 = 45000 * n^-0.83 * d_m^-0.5   (n <  1000 rpm)

with d_m the mean bearing diameter in mm and nu_1 in mm^2/s. The actual viscosity nu follows
the lubricant and its OPERATING TEMPERATURE through the Walther/ASTM D341 relation. Two
operating conditions are in similitude when they share kappa, whatever their loads and speeds.

NUMERICAL INSTANCE
------------------
Worked on the published PRONOSTIA/FEMTO operating conditions (Nectoux et al. 2012), NSK 6804RS
deep-groove ball bearings, so the example connects directly to the benchmark used in the paper.

Run:  PYTHONPATH=src python3 scripts/r22_lundberg_palmgren.py
"""

from __future__ import annotations

import itertools
import json

import numpy as np

# --- published bearing and test parameters ---------------------------------------
BORE_MM, OD_MM = 20.0, 32.0  # NSK 6804RS
D_M = 0.5 * (BORE_MM + OD_MM)  # mean diameter, mm
C_RATING_N = 4000.0  # basic dynamic load rating, N
P_EXP = 3.0  # ball bearing exponent

# PRONOSTIA/FEMTO operating conditions: (speed rpm, radial load N)
CONDITIONS = {1: (1800.0, 4000.0), 2: (1650.0, 4200.0), 3: (1500.0, 5000.0)}

# Illustrative grease base oil: ISO VG 100, nu40 = 100, nu100 = 11.4 mm^2/s
NU40, NU100 = 100.0, 11.4


def walther_coefficients(nu40=NU40, nu100=NU100):
    """ASTM D341: log10(log10(nu + 0.7)) = A - B*log10(T[K])."""
    z = lambda nu: np.log10(np.log10(nu + 0.7))
    t40, t100 = 313.15, 373.15
    b = (z(nu40) - z(nu100)) / (np.log10(t100) - np.log10(t40))
    a = z(nu40) + b * np.log10(t40)
    return float(a), float(b)


def viscosity_at(temp_c, a=None, b=None):
    """Kinematic viscosity (mm^2/s) at a given temperature in Celsius."""
    if a is None or b is None:
        a, b = walther_coefficients()
    t = temp_c + 273.15
    return float(10 ** (10 ** (a - b * np.log10(t))) - 0.7)


def reference_viscosity(n_rpm, d_m=D_M):
    """ISO 281 reference viscosity nu_1 (mm^2/s)."""
    if n_rpm >= 1000.0:
        return float(4500.0 * n_rpm**-0.5 * d_m**-0.5)
    return float(45000.0 * n_rpm**-0.83 * d_m**-0.5)


def characteristic_life_h(n_rpm, load_n, c=C_RATING_N, p=P_EXP):
    """sigma = L10 in hours: the scale-setting group."""
    l10_mrev = (c / load_n) ** p
    return float(1e6 * l10_mrev / (60.0 * n_rpm))


def main():
    a, b = walther_coefficients()
    out = {"walther_A": a, "walther_B": b, "d_m_mm": D_M, "C_N": C_RATING_N}
    print(f"Walther coefficients for the illustrative VG100 grease: A={a:.4f}, B={b:.4f}")
    print(
        f"  check: nu(40C) = {viscosity_at(40, a, b):.1f}, "
        f"nu(100C) = {viscosity_at(100, a, b):.1f} mm^2/s (targets 100.0 and 11.4)"
    )

    print("\n=== SCALE: sigma absorbs load and speed (PRONOSTIA conditions) ===")
    print(f"{'cond':>5}{'n [rpm]':>10}{'P [N]':>8}{'C/P':>8}{'L10 [Mrev]':>13}{'sigma [h]':>11}")
    sigmas = {}
    for cid, (n, load) in CONDITIONS.items():
        sig = characteristic_life_h(n, load)
        sigmas[cid] = sig
        print(
            f"{cid:>5}{n:>10.0f}{load:>8.0f}{C_RATING_N / load:>8.3f}"
            f"{(C_RATING_N / load) ** P_EXP:>13.3f}{sig:>11.2f}"
        )
    ratio = max(sigmas.values()) / min(sigmas.values())
    out["sigma_h"] = sigmas
    out["sigma_ratio"] = ratio
    print(f"  characteristic-life ratio across conditions: {ratio:.2f}x")

    print("\n=== PSI: the lubrication regime is what the scale does NOT absorb ===")
    print(f"{'cond':>5}{'n [rpm]':>10}{'nu_1':>9}{'T [C]':>8}{'nu':>9}{'kappa':>9}")
    # (a) all three conditions at a common operating temperature
    kappa_common = {}
    for cid, (n, _load) in CONDITIONS.items():
        nu1 = reference_viscosity(n)
        nu = viscosity_at(60.0, a, b)
        kappa_common[cid] = nu / nu1
        print(f"{cid:>5}{n:>10.0f}{nu1:>9.2f}{60.0:>8.1f}{nu:>9.1f}{nu / nu1:>9.3f}")
    dpsi_common = {
        f"{x}->{y}": abs(np.log(kappa_common[x]) - np.log(kappa_common[y]))
        for x, y in itertools.permutations(CONDITIONS, 2)
    }
    worst_common = max(dpsi_common.values())
    out["kappa_common_temp"] = kappa_common
    out["dpsi_common_temp_max"] = float(worst_common)
    print(f"  largest departure ||d psi|| = |ln kappa_S - ln kappa_T| = {worst_common:.3f}")

    # (b) the same three conditions running at different thermal states
    temps = {1: 50.0, 2: 60.0, 3: 75.0}
    print(f"\n{'cond':>5}{'n [rpm]':>10}{'nu_1':>9}{'T [C]':>8}{'nu':>9}{'kappa':>9}")
    kappa_thermal = {}
    for cid, (n, _load) in CONDITIONS.items():
        nu1 = reference_viscosity(n)
        nu = viscosity_at(temps[cid], a, b)
        kappa_thermal[cid] = nu / nu1
        print(f"{cid:>5}{n:>10.0f}{nu1:>9.2f}{temps[cid]:>8.1f}{nu:>9.1f}{nu / nu1:>9.3f}")
    dpsi_thermal = {
        f"{x}->{y}": abs(np.log(kappa_thermal[x]) - np.log(kappa_thermal[y]))
        for x, y in itertools.permutations(CONDITIONS, 2)
    }
    worst_thermal = max(dpsi_thermal.values())
    out["kappa_thermal"] = kappa_thermal
    out["dpsi_thermal_max"] = float(worst_thermal)
    print(f"  largest departure ||d psi|| = {worst_thermal:.3f}")

    print("\n=== practitioner's reading ===")
    print(f"  load and speed vary by {ratio:.2f}x in characteristic life yet cost NOTHING in")
    print("  similitude, because sigma absorbs them exactly.")
    print(f"  at a common thermal state the residual departure is small: {worst_common:.3f}")
    print(
        f"  a 25 C spread in operating temperature raises it to {worst_thermal:.3f}, "
        f"{worst_thermal / worst_common:.0f}x larger."
    )
    print("  => for rolling-contact fatigue the THERMAL/LUBRICATION state, not the load,")
    print("     is what breaks similitude and must be matched or reported as psi.")

    with open("out/r22_lundberg_palmgren.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r22_lundberg_palmgren.json")


if __name__ == "__main__":
    main()
