"""Physics-motivated features for the soft sensor (Path B).

The diagnostics showed a single-tray bubble-point estimate is nearly linear in
tray-6 temperature over the operating range, so it carries about the same
signal as raw lagged u5 (both r^2 ~= 0.51). Physics therefore earns its place
only through a NONLINEAR, MULTIVARIATE fusion that a linear model on raw lagged
inputs cannot form for itself. That feature is the stripping factor.

Features computed here (each a physically-grounded function of the inputs):
    - bubble_point_c4: ideal-binary bubble-point C4 mole fraction at tray-6
      (n-C4 / n-C6, from u5 and u2). Thermodynamic baseline; ~ lagged u5.
    - rel_volatility:  alpha = Psat_C4(T) / Psat_C6(T) at tray-6. Nonlinear in
      temperature (from DIPPR-101 vapor pressures); measures separation ease.
    - stripping_factor: alpha * reflux_proxy (u3). The amount of C4 reaching
      the bottoms scales with the stripping factor ~= relative volatility times
      vapor/liquid traffic (set by reflux). This PRODUCT is what a linear model
      on raw [u5, u3] cannot synthesize -- the genuine multivariate-physics
      contribution. Sign/scale are left to the downstream model.

Temperature and pressure are denormalized via nominal ranges (BridgeConfig);
reflux (u3) is used as a normalized proxy (its scale is absorbed by the model
coefficient). All are physically motivated, not a rigorous stage simulation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ipis.module1_soft_sensor.physics_bridge.bridge import BridgeConfig, denormalize
from ipis.physics.dippr101 import N_BUTANE, N_HEXANE, DIPPR101Params

PHYSICS_FEATURE_COLS: tuple[str, ...] = (
    "bubble_point_c4",
    "rel_volatility",
    "stripping_factor",
)

_C_TO_K = 273.15
_BAR_TO_PA = 1.0e5


def _psat_vec(T: np.ndarray, p: DIPPR101Params) -> np.ndarray:
    """Vectorized DIPPR-101 vapor pressure (Pa) with range validation."""
    T = np.asarray(T, dtype=float)
    t_lo = float(T.min())
    t_hi = float(T.max())
    if t_lo < p.t_min or t_hi > p.t_max:
        raise ValueError(
            f"Temperature outside valid range [{p.t_min:.2f}, {p.t_max:.2f}] K "
            f"for {p.name or 'component'} (min={t_lo:.2f}, max={t_hi:.2f})."
        )
    return np.exp(p.C1 + p.C2 / T + p.C3 * np.log(T) + p.C4 * (T**p.C5))


def add_physics_features(
    df: pd.DataFrame,
    config: BridgeConfig | None = None,
    t_col: str = "u5",
    p_col: str = "u2",
    reflux_col: str = "u3",
    light: DIPPR101Params = N_BUTANE,
    heavy: DIPPR101Params = N_HEXANE,
) -> pd.DataFrame:
    """Return a copy of df with physics-motivated feature columns appended.

    Adds: bubble_point_c4, rel_volatility, stripping_factor (see module docs).

    Args:
        df: DataFrame with the normalized input columns.
        config: Denormalization ranges (defaults to BridgeConfig nominals).
        t_col: Normalized tray-6 temperature column.
        p_col: Normalized pressure column.
        reflux_col: Normalized reflux column (stripping proxy).
        light: Light-key DIPPR-101 params (default n-butane).
        heavy: Representative-heavy DIPPR-101 params (default n-hexane).

    Returns:
        Copy of df with the three physics feature columns added.

    Raises:
        ValueError: If a required column is missing, or denormalized
            temperatures fall outside the components' valid ranges.
    """
    cfg = config or BridgeConfig()
    for c in (t_col, p_col, reflux_col):
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found. Have: {list(df.columns)}")

    out = df.copy()
    t_k = denormalize(df[t_col].to_numpy(float), cfg.t_min_c, cfg.t_max_c) + _C_TO_K
    p_pa = denormalize(df[p_col].to_numpy(float), cfg.p_min_bar, cfg.p_max_bar) * _BAR_TO_PA

    psat_l = _psat_vec(t_k, light)
    psat_h = _psat_vec(t_k, heavy)

    bubble = (p_pa - psat_h) / (psat_l - psat_h)
    out["bubble_point_c4"] = np.clip(bubble, 0.0, 1.0)
    alpha = psat_l / psat_h
    out["rel_volatility"] = alpha
    out["stripping_factor"] = alpha * df[reflux_col].to_numpy(float)
    return out


def make_physics_anchored_features(
    df: pd.DataFrame,
    transport_lag: int = 15,
    include_raw_u5: bool = True,
    config: BridgeConfig | None = None,
    target_col: str = "y",
) -> tuple[pd.DataFrame, pd.Series]:
    """Build the small, fixed physics-anchored feature set at the transport lag.

    Complexity is set BY PHYSICS, not by validation: the physics features (and
    optionally raw u5) are taken at a single transport lag, yielding a compact
    matrix -- in deliberate contrast to the 126-feature lagged kitchen sink.

    Args:
        df: One time-ordered segment (call per split/fold for leakage safety).
        transport_lag: The transport delay in samples (single lag, default 15).
        include_raw_u5: Also include raw u5 at the transport lag (robust backbone).
        config: Denormalization ranges.
        target_col: Target column.

    Returns:
        (X, y): compact feature DataFrame and aligned target, first
        ``transport_lag`` rows dropped (insufficient history).

    Raises:
        ValueError: If the segment is too short for the requested lag.
    """
    if len(df) <= transport_lag:
        raise ValueError(f"Segment length {len(df)} <= transport_lag {transport_lag}.")

    feat = add_physics_features(df, config=config)
    cols: dict[str, pd.Series] = {}
    for c in PHYSICS_FEATURE_COLS:
        cols[f"{c}_lag{transport_lag}"] = feat[c].shift(transport_lag)
    if include_raw_u5:
        cols[f"u5_lag{transport_lag}"] = feat["u5"].shift(transport_lag)

    X = pd.DataFrame(cols).iloc[transport_lag:].reset_index(drop=True)
    y = feat[target_col].iloc[transport_lag:].reset_index(drop=True)
    return X, y


def make_u5_only_features(
    df: pd.DataFrame,
    transport_lag: int = 15,
    target_col: str = "y",
) -> tuple[pd.DataFrame, pd.Series]:
    """Single-feature baseline: raw u5 at the transport lag (the backbone)."""
    if len(df) <= transport_lag:
        raise ValueError(f"Segment length {len(df)} <= transport_lag {transport_lag}.")
    X = pd.DataFrame({f"u5_lag{transport_lag}": df["u5"].shift(transport_lag)})
    X = X.iloc[transport_lag:].reset_index(drop=True)
    y = df[target_col].iloc[transport_lag:].reset_index(drop=True)
    return X, y
