"""C-MAPSS loader and physics-derived referred (corrected) conditions.

Reviewer 2 (major 1) asks for the coverage certificate itself, not only the diagnostic, to be
checked on a physically grounded dataset whose true departure was NOT authored by us, with
enough replication per operating condition that the comparison is well powered.

C-MAPSS FD002/FD004 (Saxena and Goebel, NASA PCoE) fits: 260 and 249 turbofan engines run to
failure across exactly SIX operating regimes, with every engine visiting every regime, giving
~260 units per regime against the ~6 bearings per condition that made FEMTO indeterminate.

The dimensionless scale is NOT fitted. Gas-turbine similitude is the textbook application of
the Buckingham Pi theorem: performance collapses onto referred (corrected) parameters built
from the stagnation temperature and pressure ratios

    theta = T_t / T_std,    delta = P_t / P_std,     T_std = 288.15 K, P_std = 101325 Pa

with T_t, P_t obtained from the recorded operating settings (altitude, Mach number, throttle
resolver angle) through the standard atmosphere and the isentropic stagnation relations.
Corrected mass flow W*sqrt(theta)/delta and corrected speed N/sqrt(theta) are the classical
groups; the cumulative gas throughput per unit time therefore scales as delta/sqrt(theta),
which is the damage-accumulation clock used here.

Run:  PYTHONPATH=src python3 scripts/cmapss_loader.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

T_STD, P_STD = 288.15, 101325.0
GAMMA = 1.4
COLS = ["unit", "cycle", "os1", "os2", "os3"] + [f"s{i}" for i in range(1, 22)]
DATA_DIR = "data/cmapss"


def standard_atmosphere(alt_kft: float) -> tuple[float, float]:
    """Ambient static temperature (K) and pressure (Pa) at altitude in thousands of feet."""
    h = alt_kft * 1000.0
    if h <= 36089.0:
        ratio = 1.0 - 6.87559e-6 * h
        return 288.15 * ratio, 101325.0 * ratio**5.2559
    t = 216.65
    p = 22632.1 * np.exp(-4.80637e-5 * (h - 36089.0))
    return t, float(p)


def referred_conditions(alt_kft: float, mach: float, tra: float) -> dict[str, float]:
    """theta, delta and the derived damage-clock scale for one operating regime."""
    t_amb, p_amb = standard_atmosphere(alt_kft)
    f = 1.0 + 0.5 * (GAMMA - 1.0) * mach**2
    t_t = t_amb * f
    p_t = p_amb * f ** (GAMMA / (GAMMA - 1.0))
    theta = t_t / T_STD
    delta = p_t / P_STD
    # throttle resolver angle sets the power fraction; part power reduces core loading.
    power = tra / 100.0
    # damage clock: gas throughput per unit time scales as delta/sqrt(theta), scaled by power.
    clock = power * delta / np.sqrt(theta)
    return {
        "t_amb": t_amb,
        "p_amb": p_amb,
        "T_t": t_t,
        "P_t": p_t,
        "theta": theta,
        "delta": delta,
        "power": power,
        "clock": clock,
    }


def load(dataset: str = "FD002", data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Load a C-MAPSS training file, label operating regimes, and attach true RUL."""
    df = pd.read_csv(f"{data_dir}/train_{dataset}.txt", sep=r"\s+", header=None, names=COLS)
    key = df[["os1", "os2", "os3"]].round({"os1": 0, "os2": 2, "os3": 0})
    uniq = key.drop_duplicates().sort_values(["os1", "os2", "os3"]).reset_index(drop=True)
    lookup = {tuple(r): i for i, r in enumerate(uniq.to_numpy())}
    df["regime"] = [lookup[tuple(r)] for r in key.to_numpy()]
    life = df.groupby("unit")["cycle"].transform("max")
    df["rul"] = life - df["cycle"]
    return df


def regime_table(df: pd.DataFrame) -> pd.DataFrame:
    """Physics-derived referred conditions for each regime present in the data."""
    rows = []
    for rid, sub in df.groupby("regime"):
        alt, mach, tra = sub[["os1", "os2", "os3"]].iloc[0]
        rc = referred_conditions(float(alt), float(mach), float(tra))
        rows.append(
            {
                "regime": rid,
                "alt_kft": round(float(alt), 1),
                "mach": round(float(mach), 2),
                "tra": round(float(tra), 0),
                "engines": sub.unit.nunique(),
                "rows": len(sub),
                **{k: round(v, 4) for k, v in rc.items() if k in ("theta", "delta", "clock")},
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    for ds in ["FD002", "FD004"]:
        df = load(ds)
        tab = regime_table(df)
        print(
            f"=== {ds}: {df.unit.nunique()} engines, {len(df)} rows, "
            f"{df.regime.nunique()} operating regimes ==="
        )
        print(tab.to_string(index=False))
        c = tab["clock"]
        print(
            f"  damage-clock spread across regimes: {c.max() / c.min():.1f}x "
            f"(min {c.min():.3f}, max {c.max():.3f})"
        )
        print()


if __name__ == "__main__":
    main()
