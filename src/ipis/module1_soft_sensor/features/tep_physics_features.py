"""Physics-anchored features for the TEP product-G soft sensor (Phase 1C).

Analytical-first (ADR-004): the feature set is derived from the reaction
chemistry, not feature-hunted. Product G is made by A + C + D -> G and competes
with A + C + E -> H; both are irreversible, exothermic, ~first-order in reactant
partial pressures, and the G reaction has the higher activation energy (more
temperature-sensitive). So the G/H split is governed by:

  - D/E feed ratio      XMEAS_2 / XMEAS_3        (D -> G, E -> H: the split)
  - reactor temperature XMEAS_9                  (Arrhenius; G favored hotter)
  - T x (D/E)           interaction              (temperature modulates the split)
  - reactant supply     XMEAS_1 (A), XMEAS_4 (C) (shared first-order reactants)
  - reactor pressure    XMEAS_7                  (gas-phase partial pressures)
  - residence / holdup  XMEAS_6, XMEAS_8         (feed rate, reactor level)

All evaluated at a transport lag (the analog of the Debutanizer's ~15-sample
reactor->product delay), to be diagnosed empirically on the data. This mirrors
make_physics_anchored_features for the Debutanizer so the same modeling recipe
applies unchanged -- the Phase-1C "methodology transfers across topology" claim.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

# Base physics drivers (fast, real-time measurements).
TEP_PHYSICS_BASE = [
    "XMEAS_2",
    "XMEAS_3",
    "XMEAS_9",
    "XMEAS_7",
    "XMEAS_1",
    "XMEAS_4",
    "XMEAS_6",
    "XMEAS_8",
]


def add_tep_physics_features(df: pd.DataFrame) -> pd.DataFrame:
    """Append derived analytical features (D/E ratio, T x (D/E)) to a copy."""
    out = df.copy()
    out["DE_ratio"] = out["XMEAS_2"] / out["XMEAS_3"]
    out["T_DE"] = out["XMEAS_9"] * out["DE_ratio"]
    return out


def make_tep_physics_features(
    df: pd.DataFrame,
    transport_lag: int,
    *,
    base_cols: Sequence[str] = TEP_PHYSICS_BASE,
    include_derived: bool = True,
    target_col: str = "y",
) -> tuple[pd.DataFrame, pd.Series]:
    """Build lagged physics-anchored features and aligned target for TEP G.

    Args:
        df: TEP DataFrame from TEPLoader (named XMEAS/XMV columns + y).
        transport_lag: Reactor->product transport delay in samples (3-min units).
        base_cols: Fast measurements to lag as features.
        include_derived: Add D/E ratio and T x (D/E) interaction (also lagged).
        target_col: Target column name (default 'y' = XMEAS_40, component G).

    Returns:
        (X, y): feature DataFrame and aligned target Series, both with the first
        `transport_lag` rows dropped.
    """
    if transport_lag < 0:
        raise ValueError(f"transport_lag must be >= 0, got {transport_lag}")
    feat = add_tep_physics_features(df) if include_derived else df.copy()
    cols: dict[str, pd.Series] = {}
    use = list(base_cols) + (["DE_ratio", "T_DE"] if include_derived else [])
    for c in use:
        cols[f"{c}_lag{transport_lag}"] = feat[c].shift(transport_lag)
    X = pd.DataFrame(cols).iloc[transport_lag:].reset_index(drop=True)
    y = feat[target_col].iloc[transport_lag:].reset_index(drop=True)
    return X, y


def diagnose_transport_lag(
    df: pd.DataFrame,
    *,
    driver_col: str = "XMEAS_3",
    target_col: str = "y",
    max_lag: int = 40,
) -> int:
    """Estimate the reactor->product transport lag by peak |cross-correlation|.

    Uses a single strong driver (default E feed, XMEAS_3, strongly anti-correlated
    with G) and returns the lag in samples that maximizes |corr(driver_{t-lag}, y_t)|.
    A diagnostic aid only -- the chosen lag should be sanity-checked physically.
    """
    y = df[target_col].to_numpy()
    x = df[driver_col].to_numpy()
    best_lag, best_abs = 0, -1.0
    for lag in range(max_lag + 1):
        r = np.corrcoef(x, y)[0, 1] if lag == 0 else np.corrcoef(x[:-lag], y[lag:])[0, 1]
        if abs(r) > best_abs:
            best_abs, best_lag = abs(r), lag
    return best_lag
