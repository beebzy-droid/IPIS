"""Per-dataset loaders for Module 1.

All loaders return a common interface: a pandas DataFrame with
- Time-ordered rows (no shuffling)
- Named feature columns
- A 'y' target column

The Debutanizer loader auto-detects where numeric data begins, making it
robust to header/blank-line variations across dataset mirrors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

# Canonical Debutanizer column names (Fortuna et al., 2007).
# u1: top temperature, u2: top pressure, u3: reflux flow,
# u4: flow to next unit, u5: tray-6 temperature,
# u6/u7: two bottom temperatures, y: C4 bottom composition.
DEBUTANIZER_COLUMNS = ["u1", "u2", "u3", "u4", "u5", "u6", "u7", "y"]
DEBUTANIZER_N_COLUMNS = len(DEBUTANIZER_COLUMNS)


class DatasetLoader(Protocol):
    """Common loader interface for Module 1 datasets."""

    def load(self, path: Path) -> pd.DataFrame:
        """Load a dataset from disk into a normalized DataFrame."""
        ...


def _find_data_start(path: Path, expected_columns: int) -> int:
    """Find the first physical line index that parses as numeric data.

    Robust to a variable number of header text lines and blank lines across
    dataset mirrors.

    Args:
        path: Path to the raw data file.
        expected_columns: Number of whitespace-separated numeric columns expected.

    Returns:
        Zero-based line index where numeric data begins.

    Raises:
        ValueError: If no line with the expected number of numeric columns is found.
    """
    with open(path) as f:
        for i, line in enumerate(f):
            tokens = line.split()
            if len(tokens) != expected_columns:
                continue
            try:
                [float(t) for t in tokens]
            except ValueError:
                continue
            return i
    raise ValueError(
        f"No line with {expected_columns} numeric columns found in {path}. "
        "File format may have changed."
    )


class DebutanizerLoader:
    """Loader for the Fortuna et al. (2007) Debutanizer column dataset.

    Expected file: whitespace-delimited, scientific notation, 8 columns
    (u1-u7 + y), pre-normalized to [0, 1]. Header text and blank lines are
    auto-skipped.
    """

    def load(self, path: Path) -> pd.DataFrame:
        """Load Debutanizer data into a clean DataFrame.

        Args:
            path: Path to the raw Debutanizer .txt file.

        Returns:
            DataFrame with columns u1-u7 and y, in original time order.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If parsing yields an unexpected shape.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"Debutanizer data not found at {path}. "
                "Run: python scripts/download_datasets.py --dataset debutanizer"
            )

        data_start = _find_data_start(path, DEBUTANIZER_N_COLUMNS)

        df = pd.read_csv(
            path,
            sep=r"\s+",
            skiprows=data_start,
            names=DEBUTANIZER_COLUMNS,
            engine="python",
        )

        # Hard assertions: encode what we validated about this dataset.
        if df.shape[1] != DEBUTANIZER_N_COLUMNS:
            raise ValueError(
                f"Expected {DEBUTANIZER_N_COLUMNS} columns, got {df.shape[1]}. "
                "Delimiter or format issue."
            )
        if df.isna().any().any():
            raise ValueError("Parsed Debutanizer data contains missing values.")

        return df.reset_index(drop=True)


class TEPLoader:
    """Loader for Tennessee Eastman Process dataset."""

    def load(self, path: Path) -> pd.DataFrame:  # noqa: ARG002
        """Load TEP data.

        Raises:
            NotImplementedError: Placeholder until Phase 1C.
        """
        raise NotImplementedError("Implement in Phase 1C. See docs/module1/spec.md")


class SECOMLoader:
    """Loader for SECOM semiconductor dataset."""

    def load(self, path: Path) -> pd.DataFrame:  # noqa: ARG002
        """Load SECOM data.

        Raises:
            NotImplementedError: Placeholder until Phase 1E.
        """
        raise NotImplementedError("Implement in Phase 1E. See docs/module1/spec.md")
