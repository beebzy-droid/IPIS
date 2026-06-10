"""Evidence JSON contract: one freeze point between evaluation scripts and figures."""

from __future__ import annotations

import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

EVIDENCE_DIR = Path("docs/paper/evidence")


def dump_evidence(name: str, payload: dict, out_dir: str | Path | None = None) -> Path:
    """Write payload + a provenance stamp to docs/paper/evidence/{name}.json."""
    d = Path(out_dir) if out_dir else EVIDENCE_DIR
    d.mkdir(parents=True, exist_ok=True)
    doc = {
        "_meta": {
            "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "argv": sys.argv,
            "python": platform.python_version(),
        },
        **payload,
    }
    p = d / f"{name}.json"
    p.write_text(json.dumps(doc, indent=2, allow_nan=True))
    return p


def load_evidence(name: str, in_dir: str | Path | None = None) -> dict:
    d = Path(in_dir) if in_dir else EVIDENCE_DIR
    return json.loads((d / f"{name}.json").read_text())
