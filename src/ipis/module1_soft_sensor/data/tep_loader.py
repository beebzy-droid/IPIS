"""Loader for the Phase-1C Tennessee Eastman multimode dataset.

Mirrors the Debutanizer loader contract: returns a time-ordered pandas DataFrame
with named columns and a 'y' target. The CSVs are produced by
generate_tep_modes.py (Russell/Braatz closed-loop simulator) with layout:
    time, XMEAS_1..XMEAS_41, XMV_1..XMV_12   (no header)

Target y = XMEAS_40 (component G mol% in the product stream, stream 11) -- the
delayed gas-chromatograph quality variable. Soft-sensor inputs are the fast
continuous measurements (XMEAS 1-22) plus XMV; the composition analyzers
(XMEAS 23-41) are the delayed variables and are NOT used as inputs (only #40 as
the label).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

N_XMEAS = 41
N_XMV = 12
TEP_TARGET_XMEAS = 40  # component G in product (stream 11)
TEP_COLUMNS = (
    ["time"]
    + [f"XMEAS_{i}" for i in range(1, N_XMEAS + 1)]
    + [f"XMV_{i}" for i in range(1, N_XMV + 1)]
)
TEP_N_COLUMNS = len(TEP_COLUMNS)  # 54

# Fast continuous measurements available in real time (XMEAS 1-22); the
# composition analyzers XMEAS 23-41 are delayed and excluded as inputs.
TEP_FAST_INPUTS = [f"XMEAS_{i}" for i in range(1, 23)]


class TEPLoader:
    """Loader for a single TEP operating-mode CSV from generate_tep_modes.py."""

    def load(self, path: Path) -> pd.DataFrame:
        """Load one TEP mode CSV into a normalized, time-ordered DataFrame.

        Args:
            path: Path to a tep_mode*.csv (54 comma-separated numeric columns,
                no header).

        Returns:
            DataFrame with columns time, XMEAS_1..41, XMV_1..12, and y (= the
            target composition XMEAS_40), in original time order.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If parsing yields an unexpected column count.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"TEP data file not found: {path}")
        df = pd.read_csv(path, header=None)
        if df.shape[1] != TEP_N_COLUMNS:
            raise ValueError(
                f"Expected {TEP_N_COLUMNS} columns (time + {N_XMEAS} XMEAS + "
                f"{N_XMV} XMV), got {df.shape[1]} in {path}."
            )
        df.columns = TEP_COLUMNS
        df["y"] = df[f"XMEAS_{TEP_TARGET_XMEAS}"]
        return df


def load_modes(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    """Load several modes at once.

    Args:
        paths: Mapping of mode name -> CSV path (e.g. {"mode1": Path(...)}).

    Returns:
        Mapping of mode name -> loaded DataFrame.
    """
    loader = TEPLoader()
    return {name: loader.load(p) for name, p in paths.items()}
