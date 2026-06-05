"""Stateful online soft-sensor service core (Phase 1D.2a).

Framework-agnostic: no FastAPI, no asyncio, no MLflow here. This class composes the
as-built Module-1 pieces into the two asynchronous flows a soft sensor actually has,
given delayed/infrequent labels:

  predict flow (high-frequency, reads state):
      features -> raw = point_predict(x);  corrected = raw + b_t
      (lower, upper) = ACI interval around `corrected`
      remember (raw, corrected, lower, upper) under a sample_id

  label/update flow (low-frequency, mutates state) when a delayed assay arrives:
      e_raw = y_true - raw            (bias error on the RAW residual, ADR-008)
      b_t   = (1 - lam) * b_t + lam * e_raw
      ACI step on the STORED interval's coverage indicator (ADR-010)
      drift detector fed the residual; emit drift_flag

The bias recursion is bit-equivalent to ``apply_bias_update`` (Shardt 2016, open-loop
Case I) when labels arrive in order, ``delay`` samples late -- the delay is realised
physically by the sample_id -> prediction ring buffer rather than an index shift, so
the 1D.1b coverage result transfers to this live path.

DELAYED-LABEL CORRECTNESS: the ACI coverage indicator for a label is computed against
the interval that was *emitted for that sample* (stored in the buffer), not the
service's current interval -- by the time a delayed label arrives, alpha_t and the
score window have moved on. ``ACIConformal.update`` assumes immediate feedback and is
therefore not used; the service drives ``aci_step`` + the score window directly.

State separation: the immutable point model + hyper-parameters are reloaded from the
registry (1D.2c); only the MUTABLE state (b_t, the ACI object, the drift detector, the
prediction buffer, counters, recent-coverage window) is snapshotted. ``save_snapshot``/
``load_snapshot`` pickle that mutable bundle (river detectors are picklable); the model
is never pickled into the snapshot.

Concurrency: this core is synchronous. The asyncio mutation lock that serialises
concurrent ``/label`` calls is added by the FastAPI layer (1D.2b).
"""

from __future__ import annotations

import math
import pickle
from collections import OrderedDict, deque
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from ipis.module1_soft_sensor.evaluation.conformal import ACIConformal, aci_step

FloatArray = NDArray[np.float64]
# (m, n_features) -> (m,) point predictions; injected so the core stays framework-free.
PointPredict = Callable[[FloatArray], FloatArray]


@runtime_checkable
class SupportsDrift(Protocol):
    """Structural type for a drift detector (matches drift.DriftDetector)."""

    drift_detected: bool

    def update(self, value: float) -> bool: ...

    def reset(self) -> None: ...


class SoftSensorService:
    """Online soft sensor: linear point model + bias-update + ACI interval + drift.

    Parameters
    ----------
    point_predict : PointPredict
        ``(X) -> y_raw`` for a 2-D feature array; the frozen model (scaler+regressor).
    lam : float
        Bias-update EWMA rate in (0, 1] (ADR-008). 1.0 = most-recent residual.
    delay : int
        Label/analyzer delay in samples (>= 0). Metadata for the live path (the buffer
        realises it); sizes the default buffer if ``buffer_size`` is None.
    alpha : float
        Target miscoverage; intervals target coverage ``1 - alpha``.
    gamma : float
        ACI step size (ADR-010).
    window : int | None
        ACI sliding score-window length; None = expanding.
    init_residuals : array
        Calibration residuals (corrected) to seed the ACI score window.
    drift_detector : SupportsDrift | None
        Injected detector (e.g. ``make_adwin()``); None disables drift monitoring.
    drift_on : str
        Residual fed to the detector: "corrected" (default; alarms when the bias-update
        can no longer hold) or "raw".
    buffer_size : int | None
        Max retained predictions awaiting labels. None -> ``max(64, 4 * (delay + 1))``.
    snapshot_path, snapshot_every : optional
        If set, auto-pickle the mutable state every ``snapshot_every`` labels.
    """

    def __init__(
        self,
        point_predict: PointPredict,
        *,
        lam: float = 0.3,
        delay: int = 0,
        alpha: float = 0.10,
        gamma: float = 0.05,
        window: int | None = 200,
        init_residuals: FloatArray,
        drift_detector: SupportsDrift | None = None,
        drift_on: str = "corrected",
        buffer_size: int | None = None,
        snapshot_path: str | Path | None = None,
        snapshot_every: int = 50,
    ) -> None:
        if not 0.0 < lam <= 1.0:
            raise ValueError(f"lam must be in (0, 1], got {lam}")
        if delay < 0:
            raise ValueError(f"delay must be >= 0, got {delay}")
        if drift_on not in ("corrected", "raw"):
            raise ValueError("drift_on must be 'corrected' or 'raw'")

        self.point_predict = point_predict
        self.lam = float(lam)
        self.delay = int(delay)
        self.drift_on = drift_on
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None
        self.snapshot_every = int(snapshot_every)

        # --- mutable state (snapshotted) ---
        self.b = 0.0
        self.aci = ACIConformal(init_residuals, alpha=alpha, gamma=gamma, window=window)
        self.detector = drift_detector
        self.last_drift_flag = False
        self._buf_size = buffer_size if buffer_size is not None else max(64, 4 * (self.delay + 1))
        self.buffer: OrderedDict[str, tuple[float, float, float, float]] = OrderedDict()
        self.recent_covered: deque[bool] = deque(maxlen=(window or 500))
        self.n_predict = 0
        self.n_label = 0
        self._next_id = 0

    # ---------------------------------------------------------------- predict #
    def predict(
        self, features: FloatArray, sample_id: str | list[str] | None = None
    ) -> dict | list[dict]:
        """Predict + interval for one row (1-D) or a batch (2-D). Reads state only."""
        x = np.asarray(features, dtype=float)
        single = x.ndim == 1
        x2 = np.atleast_2d(x)
        m = x2.shape[0]

        raw = np.asarray(self.point_predict(x2), dtype=float).ravel()
        corrected = raw + self.b  # b is constant across a batch (labels mutate it)
        lower, upper = self.aci.interval(corrected)  # one halfwidth for the batch

        ids = self._resolve_ids(sample_id, m)
        rows: list[dict] = []
        for i, sid in enumerate(ids):
            self.buffer[sid] = (
                float(raw[i]),
                float(corrected[i]),
                float(lower[i]),
                float(upper[i]),
            )
            self.buffer.move_to_end(sid)
            rows.append(
                {
                    "sample_id": sid,
                    "y_pred_raw": float(raw[i]),
                    "y_pred": float(corrected[i]),
                    "lower": float(lower[i]),
                    "upper": float(upper[i]),
                    "bias": self.b,
                    "alpha_t": self.aci.alpha_t,
                    "drift_flag": self.last_drift_flag,
                }
            )
        while len(self.buffer) > self._buf_size:  # FIFO eviction of oldest unlabeled
            self.buffer.popitem(last=False)
        self.n_predict += m
        return rows[0] if single else rows

    # ------------------------------------------------------------------ label #
    def label(self, sample_id: str, y_true: float) -> dict:
        """Fold a delayed label into the bias-update, ACI, and drift detector."""
        if sample_id not in self.buffer:
            raise KeyError(
                f"sample_id {sample_id!r} not in buffer "
                f"(unknown, already labeled, or evicted; buffer holds {len(self.buffer)})"
            )
        raw, corrected, lower, upper = self.buffer.pop(sample_id)
        y = float(y_true)

        # bias-update on the RAW residual (ADR-008)
        self.b = (1.0 - self.lam) * self.b + self.lam * (y - raw)

        # ACI step against the STORED interval (delayed-label-correct)
        covered = bool(lower <= y <= upper)
        self.aci.alpha_t = aci_step(
            self.aci.alpha_t, covered, self.aci.gamma, self.aci.target_alpha
        )
        self.aci.scores.append(abs(y - corrected))

        # drift on the chosen residual stream
        if self.detector is not None:
            resid = (y - corrected) if self.drift_on == "corrected" else (y - raw)
            self.last_drift_flag = bool(self.detector.update(float(resid)))

        self.recent_covered.append(covered)
        self.n_label += 1
        if self.snapshot_path is not None and self.n_label % self.snapshot_every == 0:
            self.save_snapshot()

        return {
            "sample_id": sample_id,
            "y_true": y,
            "residual_raw": y - raw,
            "residual_corrected": y - corrected,
            "covered": covered,
            "bias": self.b,
            "alpha_t": self.aci.alpha_t,
            "drift_flag": self.last_drift_flag,
            "rolling_coverage": self.rolling_coverage(),
            "n_label": self.n_label,
        }

    # ----------------------------------------------------------- diagnostics #
    def rolling_coverage(self) -> float:
        """Empirical coverage over the recent-label window (the dashboard curve)."""
        return float(np.mean(self.recent_covered)) if self.recent_covered else math.nan

    def metrics(self) -> dict:
        """JSON-able state summary for /metrics and /state."""
        return {
            "bias": self.b,
            "alpha_t": self.aci.alpha_t,
            "target_coverage": 1.0 - self.aci.target_alpha,
            "rolling_coverage": self.rolling_coverage(),
            "drift_flag": self.last_drift_flag,
            "n_predict": self.n_predict,
            "n_label": self.n_label,
            "pending_labels": len(self.buffer),
            "params": {
                "lam": self.lam,
                "delay": self.delay,
                "gamma": self.aci.gamma,
                "alpha": self.aci.target_alpha,
                "drift_on": self.drift_on,
                "buffer_size": self._buf_size,
            },
        }

    # -------------------------------------------------------------- snapshot #
    def _state_bundle(self) -> dict:
        return {
            "b": self.b,
            "aci": self.aci,
            "detector": self.detector,
            "last_drift_flag": self.last_drift_flag,
            "buffer": self.buffer,
            "recent_covered": self.recent_covered,
            "n_predict": self.n_predict,
            "n_label": self.n_label,
            "_next_id": self._next_id,
        }

    def save_snapshot(self, path: str | Path | None = None) -> Path:
        """Pickle the MUTABLE state (not the model) for restart-safety."""
        target = Path(path) if path else self.snapshot_path
        if target is None:
            raise ValueError("no snapshot path configured")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as fh:
            pickle.dump(self._state_bundle(), fh)
        return target

    def load_snapshot(self, path: str | Path | None = None) -> None:
        """Restore mutable state onto a service already constructed with the model."""
        target = Path(path) if path else self.snapshot_path
        if target is None:
            raise ValueError("no snapshot path configured")
        with target.open("rb") as fh:
            s = pickle.load(fh)  # noqa: S301 - trusted local snapshot written by us
        self.b = s["b"]
        self.aci = s["aci"]
        self.detector = s["detector"]
        self.last_drift_flag = s["last_drift_flag"]
        self.buffer = s["buffer"]
        self.recent_covered = s["recent_covered"]
        self.n_predict = s["n_predict"]
        self.n_label = s["n_label"]
        self._next_id = s["_next_id"]

    # ----------------------------------------------------------------- utils #
    def _resolve_ids(self, sample_id: str | list[str] | None, m: int) -> list[str]:
        if sample_id is None:
            ids = [str(self._next_id + i) for i in range(m)]
            self._next_id += m
            return ids
        if isinstance(sample_id, str):
            if m != 1:
                raise ValueError("a single sample_id was given for a batch of size > 1")
            return [sample_id]
        if len(sample_id) != m:
            raise ValueError(f"{len(sample_id)} ids for {m} rows")
        return list(sample_id)
