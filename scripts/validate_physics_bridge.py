"""Validate the physics-to-data bridge against the real Debutanizer data.

Run locally from the project root (the benchmark data is gitignored, so this
does not run in CI):

    python scripts/validate_physics_bridge.py
    python scripts/validate_physics_bridge.py --path data/raw/debutanizer/debutanizer_data.txt

What it does:
    1. Loads the Debutanizer dataset via the existing DebutanizerLoader.
    2. Maps normalized inputs -> y_physics via bubble-point inversion
       (tray-6 temperature u5; pressure from top pressure u2).
    3. Fits the affine output-SBC y_norm ~= S_O * y_physics + B_O.
    4. Reports scale, bias, R^2 -- the empirical test of whether the physics
       proxy carries real signal about the C4 target.

Interpreting R^2 (physics ALONE, before the ML residual):
    R^2 > ~0.5   physics proxy tracks the target well; strong base for Path B.
    ~0.2-0.5     meaningful signal; the ML residual carries the rest (expected).
    < ~0.1       proxy barely tracks; revisit Decision 1 (try bottom temp /
                 multi-input) or Decision 3 (representative heavy). NOT a code
                 bug -- a modeling-assumption signal.

Column mapping (Fortuna et al. debutanizer): u1 top temp, u2 top pressure,
u3 reflux flow, u4 distillate flow, u5 6th-tray temp (pressure-compensated),
u6/u7 bottom temps, y = C4 in bottoms. Physics uses u5 (T) and u2 (P).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ipis.module1_soft_sensor.physics_bridge.bridge import (
    AffineSBC,
    BridgeConfig,
    physics_estimate,
)

# Tray-6 temperature and column pressure columns (normalized inputs).
T_COL = "u5"  # 6th-tray temperature (pressure-compensated control variable)
P_COL = "u2"  # top pressure (proxy for column pressure; SBC absorbs offset)
Y_COL = "y"  # C4 content in bottoms (normalized target)

# Default real-data location (matches repo convention; gitignored).
DEFAULT_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the physics-to-data bridge.")
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Path to the Debutanizer data file (default: {DEFAULT_DATA_PATH}).",
    )
    args = parser.parse_args()

    try:
        from ipis.module1_soft_sensor.data.loaders import DebutanizerLoader
    except Exception as exc:  # noqa: BLE001
        print(f"Could not import DebutanizerLoader: {exc}")
        print("Run from the project root with the ipis package installed.")
        return 1

    try:
        df = DebutanizerLoader().load(args.path)
    except FileNotFoundError as exc:
        print(f"Data file not found: {exc}")
        print(f"Expected at: {args.path}  (override with --path)")
        return 1

    for col in (T_COL, P_COL, Y_COL):
        if col not in df.columns:
            print(f"Column '{col}' not found. Available: {list(df.columns)}")
            return 1

    cfg = BridgeConfig()
    y_physics: list[float] = []
    y_target: list[float] = []
    n_clipped = 0
    for t_norm, p_norm, y in zip(df[T_COL], df[P_COL], df[Y_COL], strict=True):
        xp = physics_estimate(float(t_norm), float(p_norm), cfg)
        if xp in (0.0, 1.0):
            n_clipped += 1
        y_physics.append(xp)
        y_target.append(float(y))

    sbc = AffineSBC().fit(y_physics, y_target)

    print("=" * 56)
    print("Physics-to-data bridge -- affine output-SBC fit")
    print("=" * 56)
    print(f"  rows used            : {sbc.n}")
    print(f"  clipped to [0,1]     : {n_clipped} ({100 * n_clipped / sbc.n:.1f}%)")
    print(f"  physics range        : [{min(y_physics):.4f}, {max(y_physics):.4f}]")
    print(f"  target range         : [{min(y_target):.4f}, {max(y_target):.4f}]")
    print(f"  scale  S_O           : {sbc.scale:+.5f}")
    print(f"  bias   B_O           : {sbc.bias:+.5f}")
    print(f"  R^2 (physics alone)  : {sbc.r_squared:.4f}")
    print("-" * 56)
    if n_clipped > 0.2 * sbc.n:
        print("  NOTE: >20% of points clipped -- many (T,P) fall outside the")
        print("  bubble-point validity window. Consider widening/retuning the")
        print("  nominal ranges (BridgeConfig) or revisiting the heavy choice.")
    if sbc.r_squared < 0.1:
        print("  NOTE: low R^2 -- the physics proxy barely tracks the target.")
        print("  This is a modeling-assumption signal, not a code bug.")
        print("  Revisit Decision 1 (temperature input) or Decision 3 (heavy).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
