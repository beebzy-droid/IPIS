"""Loader for the canonical mv-per Tennessee Eastman xlsx datasets (Phase 1C).

These are the canonical Ricker operating modes (1, 3, 4) generated from the
properly-initialized decentralized controller -- the textbook Downs & Vogel G/H
modes, stronger than the feed-ratio regimes our own generator produces.

Provenance: github.com/mv-per/tennessee-eastman-dataset (git-LFS).

Quirks handled (confirmed from the files):
- Columns are mislabeled `Time, xmv-1..xmv-41` but are actually `Time` plus the
  41 XMEAS (verified: xmv-2/3 = D/E feed ~3650/4450, xmv-40 = G ~53.8 mol%,
  xmv-7 = reactor pressure, xmv-9 = reactor temp). We rename xmv-k -> XMEAS_k.
- There are NO manipulated variables (XMV) in these files -- only the 41 XMEAS.
  The physics features use XMEAS only, so this does not affect the soft sensor.
- Sampling is 1 min (Time step 0.016667 h); we decimate to the 3-min TEP grid by
  default to match the rest of the project and the real measurement cadence.

Returns the SAME contract as TEPLoader (named XMEAS columns, time, y=XMEAS_40),
so the baseline and migration code run on canonical modes unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

N_XMEAS = 41
TEP_TARGET_XMEAS = 40  # component G in product
DEFAULT_DECIMATE = 3  # 1-min source -> 3-min TEP cadence


class TEPCanonicalLoader:
    """Loader for the mv-per canonical TEP xlsx (modes 1/3/4)."""

    def __init__(self, decimate: int = DEFAULT_DECIMATE) -> None:
        if decimate < 1:
            raise ValueError(f"decimate must be >= 1, got {decimate}")
        self.decimate = decimate

    def load(self, path: Path) -> pd.DataFrame:
        """Load a canonical TEP xlsx into the standard TEP DataFrame contract.

        Args:
            path: Path to a mode*_normal_*.xlsx file.

        Returns:
            DataFrame with columns time, XMEAS_1..41, y (= XMEAS_40), decimated
            to the 3-min grid and re-indexed.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the column layout is not the expected Time + 41.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Canonical TEP file not found: {path}")
        raw = pd.read_excel(path)
        # expect Time + 41 measurement columns labelled xmv-1..xmv-41
        meas = [c for c in raw.columns if str(c).lower().startswith("xmv-")]
        if len(meas) != N_XMEAS:
            raise ValueError(
                f"Expected {N_XMEAS} measurement columns (xmv-1..41), found "
                f"{len(meas)} in {path}. Layout may differ from the mv-per format."
            )
        time_col = next((c for c in raw.columns if str(c).lower() == "time"), None)
        rename = {c: f"XMEAS_{str(c).split('-')[1]}" for c in meas}
        df = raw.rename(columns=rename)
        if time_col is not None:
            df = df.rename(columns={time_col: "time"})
        else:
            df["time"] = range(len(df))
        keep = ["time"] + [f"XMEAS_{i}" for i in range(1, N_XMEAS + 1)]
        df = df[keep]
        if self.decimate > 1:
            df = df.iloc[:: self.decimate].reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)
        df["y"] = df[f"XMEAS_{TEP_TARGET_XMEAS}"]
        return df
