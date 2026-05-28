"""Preprocessing for Module 1: splitting and (optional) normalization.

Time-ordered splitting is mandatory for soft sensors. Shuffling would leak
future information into the training set and inflate performance — a silent
and serious methodological error.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DataSplit:
    """A time-ordered train/validation/test split."""

    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame

    def summary(self) -> dict[str, int]:
        """Row counts per split."""
        return {
            "train": len(self.train),
            "val": len(self.val),
            "test": len(self.test),
            "total": len(self.train) + len(self.val) + len(self.test),
        }


def time_ordered_split(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> DataSplit:
    """Split a DataFrame into train/val/test preserving temporal order.

    The first `train_frac` of rows become train, the next `val_frac` become
    validation, and the remainder become test. No shuffling.

    Args:
        df: Time-ordered DataFrame.
        train_frac: Fraction of rows for training (0 < train_frac < 1).
        val_frac: Fraction of rows for validation (0 < val_frac < 1).

    Returns:
        DataSplit with train, val, and test DataFrames.

    Raises:
        ValueError: If fractions are invalid or leave no test data.
    """
    if not 0 < train_frac < 1:
        raise ValueError(f"train_frac must be in (0, 1), got {train_frac}")
    if not 0 < val_frac < 1:
        raise ValueError(f"val_frac must be in (0, 1), got {val_frac}")
    if train_frac + val_frac >= 1:
        raise ValueError(
            f"train_frac + val_frac must be < 1 to leave test data, " f"got {train_frac + val_frac}"
        )

    n = len(df)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    return DataSplit(
        train=df.iloc[:train_end].reset_index(drop=True),
        val=df.iloc[train_end:val_end].reset_index(drop=True),
        test=df.iloc[val_end:].reset_index(drop=True),
    )
