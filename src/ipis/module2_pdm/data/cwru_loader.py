"""Loader for Case Western Reserve University (CWRU) bearing `.mat` files.

Schema (confirmed from a real file, 2026-06-16):
    X{n}_DE_time   drive-end accelerometer   (the fault-bearing signal)
    X{n}_FE_time   fan-end accelerometer
    X{n}_BA_time   base accelerometer        (not always present)
    X{n}RPM        shaft speed, rev/min       (note: no underscore before RPM)

The `{n}` prefix is usually the file number but does NOT always match the
filename (a documented CWRU quirk; Smith & Randall 2015). Therefore channels are
matched by SUFFIX, never by reconstructing the prefix from the filename.

Sampling rate is not stored in the file. The 12 kHz Drive-End fault set is
12 kHz; the 48 kHz Drive-End set and the normal baseline are 48 kHz. `fs` is an
explicit parameter (default 12 kHz for the 12k DE fault set used in Phase 2A) so
a wrong default can never silently corrupt a spectrum — pin per Smith & Randall.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat

FS_12K_DE = 12_000  # Hz, "12k Drive End Bearing Fault Data" set
FS_48K = 48_000  # Hz, "48k Drive End" set and the normal baseline

_CHANNEL_SUFFIX = {"de": "_DE_time", "fe": "_FE_time", "ba": "_BA_time"}


@dataclass(frozen=True)
class CWRURecord:
    """One CWRU acquisition: up to three accelerometer channels + shaft speed."""

    de: np.ndarray | None
    fe: np.ndarray | None
    ba: np.ndarray | None
    rpm: float | None
    fs: float
    source_file: str

    @property
    def shaft_hz(self) -> float | None:
        """Shaft rotational frequency in Hz (RPM / 60)."""
        return None if self.rpm is None else self.rpm / 60.0

    def channel(self, name: str) -> np.ndarray:
        """Return a named channel ('de'|'fe'|'ba'), raising if it is absent."""
        name = name.lower()
        if name not in _CHANNEL_SUFFIX:
            raise ValueError(f"unknown channel {name!r}; expected de/fe/ba")
        arr = getattr(self, name)
        if arr is None:
            raise KeyError(f"channel {name!r} not present in {self.source_file}")
        return arr


def _match_suffix(keys: list[str], suffix: str) -> str | None:
    """First variable key ending in `suffix` (prefix-agnostic), or None."""
    hits = [k for k in keys if k.endswith(suffix)]
    return hits[0] if hits else None


def load_cwru_mat(path: str | Path, fs: float = FS_12K_DE) -> CWRURecord:
    """Load a CWRU `.mat` file into a `CWRURecord`.

    Channels absent from the file come back as None rather than raising, so the
    same loader works for files that lack a base accelerometer.
    """
    path = Path(path)
    mat = loadmat(path)
    keys = [k for k in mat if not k.startswith("__")]

    def get(suffix: str) -> np.ndarray | None:
        k = _match_suffix(keys, suffix)
        if k is None:
            return None
        return np.asarray(mat[k]).squeeze().astype(float)

    rpm_key = next((k for k in keys if k.endswith("RPM")), None)
    rpm = float(np.asarray(mat[rpm_key]).squeeze()) if rpm_key is not None else None

    return CWRURecord(
        de=get(_CHANNEL_SUFFIX["de"]),
        fe=get(_CHANNEL_SUFFIX["fe"]),
        ba=get(_CHANNEL_SUFFIX["ba"]),
        rpm=rpm,
        fs=float(fs),
        source_file=path.name,
    )
