"""Evidence records of the N1 Phase 1 runner: JSON conversion, array fingerprints and
provenance.

Stage A writes what it fixed from the calibration rows; stage B recomputes those quantities from
the full files and checks them against the record before it uses any evaluation row. Arrays are
not stored. Each is recorded by a fingerprint: the SHA-256 of its float64 bytes and a few
summaries. Stage B expects the same SHA-256. If the bytes differ, the summaries must agree as
they would if every element agreed to a relative 1e-12 (about 4500 units in the last place):
each sum within 1e-12 of the sum of the magnitudes it adds (twice that for squares and the
weighted sum), each single value within 1e-12 of its magnitude. That accepts the last-bit
differences a platform can give and the record marks them "close"; it rejects any element that
moves by more than 1e-12 of the sum of magnitudes (for 800 residuals of unit size, 8e-10), and
stage B stops. Scalars and short vectors (a step size, a coefficient) must agree element by
element to a relative 1e-9.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np

REL_TOL = 1e-9  # scalars and short vectors, element by element
FP_TOL = 1e-12  # array summaries: relative to the magnitudes they add


def to_jsonable(x: Any) -> Any:
    """Arrays to lists and non-finite floats to the strings "inf", "-inf" and "nan", so that the
    evidence is strict JSON."""
    if isinstance(x, dict):
        return {str(k): to_jsonable(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [to_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return to_jsonable(x.tolist())
    if isinstance(x, bool | np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, float | np.floating):
        v = float(x)
        return v if math.isfinite(v) else str(v)
    return x


def from_jsonable(x: Any) -> Any:
    """The inverse of ``to_jsonable`` for the non-finite floats."""
    if isinstance(x, dict):
        return {k: from_jsonable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [from_jsonable(v) for v in x]
    if isinstance(x, str) and x in ("inf", "-inf", "nan"):
        return float(x)
    return x


def write_evidence(path: Path, payload: dict[str, Any], compact: bool = False) -> str:
    """Write ``payload`` with a provenance stamp (as ``ipis.shared.evidence.dump_evidence``) as
    strict JSON with LF line ends on every platform (``compact``: no indentation, for the large
    stage B records); returns ``evidence_sha256`` of the file."""
    doc = {
        "_meta": {
            "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "argv": sys.argv,
            "python": platform.python_version(),
        },
        **payload,
    }
    if compact:
        text = json.dumps(to_jsonable(doc), separators=(",", ":"), allow_nan=False)
    else:
        text = json.dumps(to_jsonable(doc), indent=1, allow_nan=False)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((text + "\n").encode("utf-8"))
    return evidence_sha256(p)


def evidence_sha256(path: Path) -> str:
    """SHA-256 of a text file with CRLF read as LF: the hash of the file as git stores it, whatever
    line ends a Windows checkout gives it."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read_evidence(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = from_jsonable(json.loads(Path(path).read_text(encoding="utf-8")))
    return out


def fingerprint(a: np.ndarray) -> dict[str, Any]:
    """SHA-256 of the float64 bytes and order-sensitive summaries of an array; ``mag_*`` are the
    sums of magnitudes that bound the summaries' rounding."""
    x = np.ascontiguousarray(a, dtype=np.float64).ravel()
    fin = x[np.isfinite(x)]
    w = np.linspace(1.0, 2.0, fin.size) if fin.size else fin
    ab = np.abs(fin)
    return {
        "sha256": hashlib.sha256(x.tobytes()).hexdigest(),
        "n": int(x.size),
        "n_finite": int(fin.size),
        "sum_abs": float(np.sum(ab)),
        "sum_sq": float(np.sum(fin * fin)),
        "weighted": float(np.sum(w * fin)),
        "mag_weighted": float(np.sum(w * ab)),
        "min": float(fin.min()) if fin.size else math.nan,
        "max": float(fin.max()) if fin.size else math.nan,
        "first": float(x[0]) if x.size else math.nan,
        "last": float(x[-1]) if x.size else math.nan,
    }


def _close(a: float, b: float, tol: float) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    return a == b or abs(a - b) <= tol


def check_fingerprint(name: str, got: dict[str, Any], want: dict[str, Any]) -> str:
    """ "exact" if the bytes agree; "close" if only the summaries agree as an element-wise
    relative ``FP_TOL`` allows (module docstring); raises otherwise."""
    if got["sha256"] == want["sha256"]:
        return "exact"
    if got["n"] != want["n"] or got["n_finite"] != want["n_finite"]:
        raise ValueError(f"{name}: {got['n']} values against stage A's {want['n']}")
    bound = {
        "sum_abs": float(want["sum_abs"]),
        "sum_sq": 2.0 * float(want["sum_sq"]),
        "weighted": 2.0 * float(want["mag_weighted"]),
    }
    keys = ("sum_abs", "sum_sq", "weighted", "min", "max", "first", "last")
    bad = [
        k
        for k in keys
        if not _close(float(got[k]), float(want[k]), FP_TOL * bound.get(k, abs(float(want[k]))))
    ]
    if bad:
        raise ValueError(f"{name}: differs from stage A in {bad}")
    return "close"


def close_values(name: str, got: Any, want: Any) -> str:
    """Floats or lists of floats: "exact" if equal, "close" if every element agrees to a relative
    ``REL_TOL`` (zeros to 1e-12 of the largest magnitude); raises otherwise."""
    g = np.atleast_1d(np.asarray(got, dtype=np.float64))
    w = np.atleast_1d(np.asarray(want, dtype=np.float64))
    if g.shape != w.shape:
        raise ValueError(f"{name}: shape {g.shape} against stage A's {w.shape}")
    if np.array_equal(g, w, equal_nan=True):
        return "exact"
    fin = np.abs(w[np.isfinite(w)])
    floor = 1e-12 * float(fin.max()) if fin.size else 0.0
    if np.allclose(g, w, rtol=REL_TOL, atol=floor, equal_nan=True):
        return "close"
    raise ValueError(f"{name}: {g.tolist()} differs from stage A's {w.tolist()}")


PACKAGES = ("numpy", "scipy", "scikit-learn", "statsmodels", "pandas")


def provenance(sources: tuple[str, ...], root: Path = Path(".")) -> dict[str, Any]:
    """SHA-256 of every source file the run depends on (CRLF read as LF, as git stores it), and
    the package versions."""
    packages: dict[str, str | None] = {}
    for name in PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    hashes = {}
    for f in sources:
        p = root / f
        hashes[f] = evidence_sha256(p) if p.exists() else None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "sources_sha256": hashes,
    }
