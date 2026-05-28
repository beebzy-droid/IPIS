"""Per-dataset loaders for Module 1.

All loaders return a common interface: a pandas DataFrame with
- Time-ordered rows
- Named feature columns
- A 'target' column
- A 'regime' column (operating regime label, when available)
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class DatasetLoader(Protocol):
    """Common loader interface for Module 1 datasets."""

    def load(self, path: Path) -> pd.DataFrame:
        """Load a dataset from disk into a normalized DataFrame."""
        ...


class DebutanizerLoader:
    """Loader for Fortuna et al. (2007) Debutanizer dataset."""

    def load(self, path: Path) -> pd.DataFrame:  # noqa: ARG002
        """Load Debutanizer data.

        Returns:
            DataFrame with 7 input columns + 'target' column + optional 'regime'.

        Raises:
            NotImplementedError: Placeholder until Phase 1A.
        """
        raise NotImplementedError("Implement in Phase 1A. See docs/module1/spec.md")


class TEPLoader:
    """Loader for Tennessee Eastman Process dataset."""

    def load(self, path: Path) -> pd.DataFrame:  # noqa: ARG002
        """Load TEP data.

        Returns:
            DataFrame with selected XMEAS columns + 'target' + 'disturbance_mode'.

        Raises:
            NotImplementedError: Placeholder until Phase 1C.
        """
        raise NotImplementedError("Implement in Phase 1C. See docs/module1/spec.md")


class SECOMLoader:
    """Loader for SECOM semiconductor dataset."""

    def load(self, path: Path) -> pd.DataFrame:  # noqa: ARG002
        """Load SECOM data.

        Returns:
            DataFrame with 590 features + 'pass_fail' target.

        Raises:
            NotImplementedError: Placeholder until Phase 1E.
        """
        raise NotImplementedError("Implement in Phase 1E. See docs/module1/spec.md")
