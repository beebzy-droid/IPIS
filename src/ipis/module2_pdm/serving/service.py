"""Online predictive-maintenance service (Module 2, Phase 2D).

Framework-agnostic (no FastAPI / asyncio here, mirroring M1's service split). It
composes the Phase-2A health index and the Phase-2B similarity RUL into the three
OperationalState fields the state bus contracts, per ``equipment_id``:

    equipment_health[eid]      <- 2A health_score in [0,1]
    health_flags[eid]          <- 2A OK/WARN/ALARM
    remaining_useful_life[eid] <- 2B calibrated RUL lower bound, in HOURS,
                                   present only AFTER the degradation onset (FPT)

The service is *stateful*: it accumulates each equipment's T^2 history, derives the
causal degradation index DI = cummax(EMA(T^2)), detects the first-prediction-time
(FPT), and once past FPT reads RUL off the similarity library and applies the
conformal back-off. Before FPT, RUL is omitted ("when available"), matching the
contract and the honest position that remaining life is not estimable from the HI
until degradation has begun.

Caveat carried from 2B: the served RUL is a *calibrated lower bound under the
library-similarity assumption*, not an unconditional point estimate.
"""

from __future__ import annotations

import pickle
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ipis.module2_pdm.rul.degradation import degradation_index, first_prediction_time
from ipis.module2_pdm.serving.loader import PdMArtifact
from ipis.shared.state_bus import HealthFlag, ModuleStatus, OperationalState


class PdMService:
    """Stateful PdM estimator producing OperationalState M2 fields per equipment."""

    def __init__(self, artifact: PdMArtifact) -> None:
        self.health_model = artifact.health_model
        self.similarity = artifact.similarity
        self.conformal_delta_hours = float(artifact.conformal_delta_hours)
        self.ema_alpha = float(artifact.ema_alpha)
        self.fpt_persist = int(artifact.fpt_persist)
        self._t2_hist: dict[str, list[float]] = {}
        self._last: dict[str, dict] = {}

    # ------------------------------------------------------------------ core #
    def observe(self, equipment_id: str, features: np.ndarray | list[float]) -> dict:
        """Ingest one feature vector for an equipment; return its assessment.

        Returns a dict with t2, health_score, flag, fpt (onset index or None) and
        rul_hours (None until FPT, then the calibrated lower bound in hours).
        """
        x = np.asarray(features, dtype=float).ravel()
        if x.size != self.health_model.n_features:
            raise ValueError(f"expected {self.health_model.n_features} features, got {x.size}")
        t2 = self.health_model.t2(x)
        hist = self._t2_hist.setdefault(equipment_id, [])
        hist.append(t2)

        fpt = self._fpt(hist)
        record = {
            "equipment_id": equipment_id,
            "t2": t2,
            "health_score": self.health_model.health_score(x),
            "flag": self.health_model.flag(x),
            "fpt": fpt,
            "rul_hours": self._rul_hours(hist, fpt),
        }
        self._last[equipment_id] = record
        return record

    def _fpt(self, hist: list[float]) -> int | None:
        if len(hist) < self.fpt_persist:
            return None
        return first_prediction_time(
            np.asarray(hist, dtype=float),
            self.health_model.warn_t2,
            self.ema_alpha,
            self.fpt_persist,
        )

    def _rul_hours(self, hist: list[float], fpt: int | None) -> float | None:
        if fpt is None or (len(hist) - fpt) < 2:
            return None
        di = degradation_index(np.asarray(hist, dtype=float), self.ema_alpha)
        hi = np.log1p(di)[fpt:]  # log1p(DI) over the degradation arc, FPT -> now
        rul_seconds = self.similarity.predict_one(hi)
        rul_hours = rul_seconds / 3600.0
        return max(0.0, rul_hours - self.conformal_delta_hours)

    # ---------------------------------------------------- contract emission #
    def operational_state_fields(self) -> dict:
        """The three OperationalState M2 dicts from the latest assessments."""
        equipment_health: dict[str, float] = {}
        health_flags: dict[str, HealthFlag] = {}
        remaining_useful_life: dict[str, float] = {}
        for eid, rec in self._last.items():
            equipment_health[eid] = rec["health_score"]
            health_flags[eid] = rec["flag"]
            if rec["rul_hours"] is not None:
                remaining_useful_life[eid] = rec["rul_hours"]
        return {
            "equipment_health": equipment_health,
            "health_flags": health_flags,
            "remaining_useful_life": remaining_useful_life,
        }

    def build_operational_state(
        self, sequence_id: int, timestamp: datetime | None = None
    ) -> OperationalState:
        """Assemble a full OperationalState carrying only this module's fields."""
        ts = timestamp or datetime.now(UTC)
        f = self.operational_state_fields()
        return OperationalState(
            timestamp=ts,
            sequence_id=sequence_id,
            equipment_health=f["equipment_health"],
            health_flags=f["health_flags"],
            remaining_useful_life=f["remaining_useful_life"],
            module_status={"m2": ModuleStatus(module_id="m2", healthy=True, last_update=ts)},
        )

    # ------------------------------------------------------- state snapshot #
    def save_state(self, path: str | Path) -> Path:
        """Pickle the mutable per-equipment state (not the model)."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as fh:
            pickle.dump({"t2_hist": self._t2_hist, "last": self._last}, fh)
        return target

    def load_state(self, path: str | Path) -> None:
        """Restore mutable state onto a service already built with the artifact."""
        with Path(path).open("rb") as fh:
            s = pickle.load(fh)  # noqa: S301 - trusted local snapshot written by us
        self._t2_hist = s["t2_hist"]
        self._last = s["last"]
