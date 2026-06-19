"""Fitted-artifact bundle for the Module 2 PdM service (Phase 2D).

Bundles everything the online service needs into one JSON-serialisable artifact,
mirroring the M1 serving/loader split (model artifact separate from mutable state):

  * the 2A Hotelling-T^2 health model (mean / precision / chi^2 limits),
  * the 2B trajectory-similarity RUL library (run-to-failure log1p(DI) arcs),
  * the calibrated conformal back-off (in HOURS) for the one-sided lower bound,
  * the degradation-index EMA alpha and the FPT persistence count.

JSON (not pickle) keeps the model artifact portable and inspectable; the service's
mutable per-equipment state is snapshotted separately (pickle), as in M1.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ipis.module2_pdm.health.health_index import HealthIndexModel
from ipis.module2_pdm.rul.similarity import SimilarityRUL


@dataclass
class PdMArtifact:
    """Everything the PdM service needs, loadable from one file."""

    health_model: HealthIndexModel
    similarity: SimilarityRUL
    conformal_delta_hours: float  # one-sided lower-bound back-off, in hours
    ema_alpha: float = 0.05  # degradation-index EMA smoothing
    fpt_persist: int = 3  # consecutive warn-exceedances to declare onset


def save_artifact(artifact: PdMArtifact, path: str | Path) -> Path:
    """Serialise the artifact to JSON."""
    hm = artifact.health_model
    sim = artifact.similarity
    payload = {
        "health_model": {
            "feature_names": list(hm.feature_names),
            "mean": hm.mean.tolist(),
            "precision": hm.precision.tolist(),
            "warn_t2": hm.warn_t2,
            "alarm_t2": hm.alarm_t2,
        },
        "similarity": {
            "library": [[hi.tolist(), rul.tolist()] for hi, rul in sim._lib],
            "interval": sim.interval,
            "mode": sim.mode,
            "max_sig": sim.max_sig,
            "phi_floor": sim.phi_floor,
        },
        "conformal_delta_hours": artifact.conformal_delta_hours,
        "ema_alpha": artifact.ema_alpha,
        "fpt_persist": artifact.fpt_persist,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload))
    return target


def load_artifact(path: str | Path) -> PdMArtifact:
    """Reconstruct a PdMArtifact (and its sub-models) from JSON."""
    payload = json.loads(Path(path).read_text())
    hm_d = payload["health_model"]
    health_model = HealthIndexModel(
        feature_names=tuple(hm_d["feature_names"]),
        mean=np.asarray(hm_d["mean"], dtype=float),
        precision=np.asarray(hm_d["precision"], dtype=float),
        warn_t2=float(hm_d["warn_t2"]),
        alarm_t2=float(hm_d["alarm_t2"]),
    )
    s_d = payload["similarity"]
    library = [
        (np.asarray(hi, dtype=float), np.asarray(rul, dtype=float)) for hi, rul in s_d["library"]
    ]
    similarity = SimilarityRUL(
        library=library,
        interval=float(s_d["interval"]),
        mode=s_d["mode"],
        max_sig=int(s_d["max_sig"]),
        phi_floor=float(s_d["phi_floor"]),
    )
    return PdMArtifact(
        health_model=health_model,
        similarity=similarity,
        conformal_delta_hours=float(payload["conformal_delta_hours"]),
        ema_alpha=float(payload["ema_alpha"]),
        fpt_persist=int(payload["fpt_persist"]),
    )
