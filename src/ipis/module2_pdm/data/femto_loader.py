"""Loader for the FEMTO-PRONOSTIA (IEEE PHM 2012) bearing dataset.

Structure (validated):
    <bearing>/acc_NNNNN.csv   one snapshot per file, time-ordered
Each acc file: 2560 rows x 6 columns, no header =
    hour, minute, second, 0.1ms_tick, horizontal_accel_g, vertical_accel_g
2560 samples = 25.6 kHz x 0.1 s; snapshots acquired every 10 s (FEMTO convention,
IEEE PHM 2012 challenge). Run-to-failure stops at 20 g vibration amplitude, so for
the run-to-failure sets the last snapshot ~ failure and RUL at snapshot i is
(n_snapshots - 1 - i) * 10 s.

FEMTO files are comma-delimited; a whitespace fallback covers occasional variants.

Operating conditions by bearing-name prefix (Nectoux et al. 2012):
    1 -> 1800 rpm / 4000 N,  2 -> 1650 rpm / 4200 N,  3 -> 1500 rpm / 5000 N.

Unlike CWRU, FEMTO faults are naturally occurring (not seeded to a known
component) and the platform publishes no verified defect-frequency multipliers,
so the FEMTO health index uses time-domain features (see features.time_feature_vector).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FEMTO_FS = 25_600  # Hz
FEMTO_SNAPSHOT_INTERVAL_S = 10.0  # acquisition cadence between consecutive acc files
FEMTO_SAMPLES_PER_SNAPSHOT = 2560  # 0.1 s window

# bearing-name prefix -> (rpm, radial load N)
CONDITION_SPEC: dict[int, tuple[int, int]] = {
    1: (1800, 4000),
    2: (1650, 4200),
    3: (1500, 5000),
}

_ACC_RE = re.compile(r"acc_(\d+)\.csv$", re.IGNORECASE)


def _read_acc(path: Path) -> np.ndarray:
    """Read an acc_*.csv as a (rows, 6) float array, robust to delimiter.

    FEMTO files are inconsistent: most are comma-delimited, some (e.g. Bearing1_4)
    are semicolon-delimited; whitespace is the last fallback.
    """
    a = None
    for delim in (",", ";", None):
        try:
            a = np.loadtxt(path, delimiter=delim)
            break
        except ValueError:
            continue
    if a is None:
        raise ValueError(f"{path.name}: could not parse with ',', ';', or whitespace")
    a = np.atleast_2d(a)
    if a.shape[1] < 6:
        raise ValueError(f"{path.name}: expected >=6 columns, got {a.shape[1]}")
    return a


def load_femto_snapshot(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (horizontal, vertical) acceleration arrays for one acc file."""
    a = _read_acc(Path(path))
    return a[:, 4].astype(float), a[:, 5].astype(float)


@dataclass(frozen=True)
class FEMTOBearing:
    """A FEMTO bearing run: an ordered sequence of snapshot files (lazy-loaded)."""

    name: str
    condition: int
    snapshot_paths: tuple[Path, ...]
    fs: float = FEMTO_FS
    interval_s: float = FEMTO_SNAPSHOT_INTERVAL_S

    @property
    def n_snapshots(self) -> int:
        return len(self.snapshot_paths)

    @property
    def rpm(self) -> int:
        return CONDITION_SPEC[self.condition][0]

    @property
    def load_n(self) -> int:
        return CONDITION_SPEC[self.condition][1]

    @property
    def shaft_hz(self) -> float:
        return self.rpm / 60.0

    def snapshot(self, i: int) -> tuple[np.ndarray, np.ndarray]:
        """Load the i-th snapshot as (horizontal, vertical)."""
        return load_femto_snapshot(self.snapshot_paths[i])

    def iter_snapshots(self):
        """Yield (index, horizontal, vertical) over the whole run, lazily."""
        for i, p in enumerate(self.snapshot_paths):
            h, v = load_femto_snapshot(p)
            yield i, h, v

    def elapsed_s(self, i: int) -> float:
        """Time since the start of the run at snapshot i."""
        return i * self.interval_s

    def time_to_failure_s(self, i: int) -> float:
        """RUL ground truth (run-to-failure sets): seconds from snapshot i to end."""
        return (self.n_snapshots - 1 - i) * self.interval_s


def _condition_from_name(name: str) -> int:
    m = re.search(r"Bearing(\d)_", name)
    if not m:
        raise ValueError(f"cannot parse condition from bearing name {name!r}")
    return int(m.group(1))


def load_femto_bearing(bearing_dir: str | Path) -> FEMTOBearing:
    """Build a `FEMTOBearing` from a directory of acc_*.csv snapshots (sorted)."""
    d = Path(bearing_dir)
    if not d.is_dir():
        raise NotADirectoryError(d)
    files = []
    for p in d.iterdir():
        m = _ACC_RE.search(p.name)
        if m:
            files.append((int(m.group(1)), p))
    if not files:
        raise FileNotFoundError(f"no acc_*.csv snapshots in {d}")
    files.sort(key=lambda t: t[0])
    return FEMTOBearing(
        name=d.name,
        condition=_condition_from_name(d.name),
        snapshot_paths=tuple(p for _, p in files),
    )
