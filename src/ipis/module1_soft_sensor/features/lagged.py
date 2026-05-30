"""Lagged-feature construction for dynamic soft sensing.

The Debutanizer C4 target is dominated by tray-6 temperature (u5) at a
transport delay of ~15 samples (see signal diagnosis: u5 lag-15 r^2 = 0.51;
linear ceiling with lags 1..17 = 0.79, vs 0.21 contemporaneous). Static
features cannot capture this; the model must see lagged inputs.

For each input column, this builds copies shifted by k = 0..max_lag, so that
row t carries u_i(t-k) for every input i and lag k. The target is y(t).

LEAKAGE SAFETY: lagging is applied WITHIN an already-split, time-ordered
segment, and the first `max_lag` rows of each segment (which would otherwise
require history from before the segment) are dropped. This guarantees no
feature in val/test borrows raw inputs across a split boundary -- the
conservative, unimpeachable choice. Combined with train-only scaling and the
no-shuffle split (data.preprocessing.time_ordered_split), the held-out score
is leakage-free.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

DEFAULT_INPUT_COLS: tuple[str, ...] = ("u1", "u2", "u3", "u4", "u5", "u6", "u7")
DEFAULT_TARGET_COL: str = "y"


def lagged_feature_names(input_cols: Sequence[str], max_lag: int) -> list[str]:
    """Column names produced by make_lagged_features, in build order.

    Names follow ``{col}_lag{k}`` for k = 0..max_lag (lag0 = contemporaneous).
    """
    if max_lag < 0:
        raise ValueError(f"max_lag must be >= 0, got {max_lag}")
    return [f"{c}_lag{k}" for c in input_cols for k in range(max_lag + 1)]


def make_lagged_features(
    df: pd.DataFrame,
    max_lag: int,
    input_cols: Sequence[str] = DEFAULT_INPUT_COLS,
    target_col: str = DEFAULT_TARGET_COL,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build lagged-input features and the aligned target from ONE segment.

    Row t of the output holds u_i(t-k) for every input i and lag k in
    0..max_lag; the aligned target is y(t). The first ``max_lag`` rows are
    dropped (insufficient history), so this must be called per split segment
    to avoid cross-boundary leakage.

    Args:
        df: One time-ordered segment (e.g. a single split's DataFrame).
        max_lag: Maximum lag in samples (k = 0..max_lag inclusive).
        input_cols: Input columns to lag.
        target_col: Target column.

    Returns:
        (X, y): feature DataFrame and aligned target Series, index reset.

    Raises:
        ValueError: If max_lag < 0, a column is missing, or the segment is
            too short to yield any rows after dropping history.
    """
    if max_lag < 0:
        raise ValueError(f"max_lag must be >= 0, got {max_lag}")
    missing = [c for c in (*input_cols, target_col) if c not in df.columns]
    if missing:
        raise ValueError(f"Columns not found: {missing}. Have: {list(df.columns)}")
    if len(df) <= max_lag:
        raise ValueError(f"Segment length {len(df)} <= max_lag {max_lag}; no rows would remain.")

    cols: dict[str, pd.Series] = {}
    for c in input_cols:
        for k in range(max_lag + 1):
            cols[f"{c}_lag{k}"] = df[c].shift(k)
    X = pd.DataFrame(cols)
    y = df[target_col]

    # Drop the first max_lag rows (NaNs from shifting = insufficient history).
    X = X.iloc[max_lag:].reset_index(drop=True)
    y = y.iloc[max_lag:].reset_index(drop=True)
    return X, y
