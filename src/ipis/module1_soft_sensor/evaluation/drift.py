"""Residual drift detection for the soft sensor (Phase 1B, step 2).

The Phase 1A diagnosis (ADR-007) established that the Debutanizer failure mode
is CALIBRATION drift, not delay drift and not signal loss: the predictor->y
correlation is stable across regimes (u5(t-15)->y r^2 ~ 0.50-0.74 in every
block) yet a model fit on one regime is biased on the next, because the
slope/intercept of the map drifts. That bias appears as a drift in the MEAN of
the prediction residual e(t) = y(t) - yhat(t).

This module monitors e(t) with three change detectors and reports where each
fires. Detection is only the TRIGGER for the Phase 1B step-3 Shardt
bias-update; on its own it corrects nothing -- this is stated plainly so the
detector is not mistaken for the result.

Detectors (all reduce to "the mean of the monitored stream shifted"):

    - ADWIN (Bifet & Gavalda, 2007, SIAM SDM): adaptive variable-length window
      with a Hoeffding-bound test between sub-windows. Single parameter delta
      (false-positive probability) with rigorous FP/FN bounds; auto-discovers
      the change time-scale, so no window or threshold must be guessed. This is
      the PRIMARY detector precisely because it needs no scale tuning. (river.)

    - Page-Hinkley (Page, 1954, Biometrika): cumulative deviation of the stream
      from its running mean, compared against the running minimum; flags when
      the gap exceeds threshold lambda. SECONDARY sensitivity check. Known to
      be the most tuning-sensitive of the three (noise-sensitive; normality
      assumed) -- defaults here are scaled to a reference residual sigma, not
      adopted blind, and should still be checked per dataset. (river.)

    - CUSUM (Page, 1954; tabular two-sided form, Montgomery SPC): two one-sided
      cumulative sums of the residual against a known target (0 for a
      calibrated model) with allowance k and decision interval h, both in
      residual units. The interpretable SPC anchor ("residual bias breached the
      control limit"). river ships no standalone CUSUM, so it is implemented
      here; the implementation is validated against the textbook in-control
      average run length (k=0.5sigma, h=4sigma -> ARL0 ~ 168).

We monitor the SIGNED residual (mean/bias drift = the diagnosed failure). Point
the runner at |e(t)| instead to watch accuracy/scatter degradation.

The detector parameter values are general-knowledge SPC / streaming-ML
defaults scaled to the data; only ADWIN's delta is scale-free. None of these
thresholds is a project primary-source constant.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from ipis.module1_soft_sensor.evaluation.blocked_cv import (
    Estimator,
    FeatureBuilder,
)
from ipis.module1_soft_sensor.features.lagged import (
    DEFAULT_INPUT_COLS,
    DEFAULT_TARGET_COL,
    make_lagged_features,
)

try:  # river is an optional runtime dependency (add to the env for scripts).
    from river import drift as _river_drift
except ImportError as _exc:  # pragma: no cover - exercised only without river
    _river_drift = None
    _RIVER_IMPORT_ERROR: ImportError | None = _exc
else:
    _RIVER_IMPORT_ERROR = None


# --------------------------------------------------------------------------- #
# Detector interface
# --------------------------------------------------------------------------- #
class DriftDetector(Protocol):
    """Minimal uniform interface for a streaming change detector."""

    name: str

    def update(self, value: float) -> bool:
        """Feed one observation; return True iff drift is flagged at this step."""
        ...

    def reset(self) -> None:
        """Return the detector to its initial (no-history) state."""
        ...


# --------------------------------------------------------------------------- #
# In-house CUSUM (river has no standalone CUSUM)
# --------------------------------------------------------------------------- #
@dataclass
class CUSUM:
    """Two-sided tabular CUSUM (Page 1954; Montgomery, Introduction to SPC).

    Tracks two one-sided cumulative sums of the deviation d = x - target:

        C_hi_t = max(0, C_hi_{t-1} + d - k)
        C_lo_t = max(0, C_lo_{t-1} - d - k)

    and flags drift when either exceeds the decision interval h. Both sums
    reset to zero after a detection (standard restart). For a calibrated soft
    sensor the residual target is 0; k is the allowance (slack, typically
    0.5*sigma) and h the decision interval (typically 4-5*sigma), expressed in
    residual units.

    Args:
        k: Allowance / slack in residual units (must be > 0).
        h: Decision interval (control limit) in residual units (must be > 0).
        target: Known in-control mean of the stream (0 for a residual).
        name: Label used in reports.
    """

    k: float
    h: float
    target: float = 0.0
    name: str = "CUSUM"
    _c_hi: float = field(default=0.0, init=False, repr=False)
    _c_lo: float = field(default=0.0, init=False, repr=False)
    drift_detected: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError(f"k (allowance) must be > 0, got {self.k}")
        if self.h <= 0:
            raise ValueError(f"h (decision interval) must be > 0, got {self.h}")

    def update(self, value: float) -> bool:
        d = float(value) - self.target
        self._c_hi = max(0.0, self._c_hi + d - self.k)
        self._c_lo = max(0.0, self._c_lo - d - self.k)
        self.drift_detected = self._c_hi > self.h or self._c_lo > self.h
        if self.drift_detected:
            self._c_hi = 0.0
            self._c_lo = 0.0
        return self.drift_detected

    def reset(self) -> None:
        self._c_hi = 0.0
        self._c_lo = 0.0
        self.drift_detected = False


# --------------------------------------------------------------------------- #
# river-backed detectors (ADWIN, Page-Hinkley)
# --------------------------------------------------------------------------- #
def _require_river() -> None:
    if _river_drift is None:  # pragma: no cover - exercised only without river
        raise ImportError(
            "The 'river' package is required for ADWIN / Page-Hinkley. "
            "Install it into the env: pip install river"
        ) from _RIVER_IMPORT_ERROR


class _RiverAdapter:
    """Wrap a river detector in the uniform DriftDetector interface."""

    def __init__(self, detector, name: str) -> None:
        self._detector = detector
        self.name = name

    def update(self, value: float) -> bool:
        self._detector.update(float(value))
        return bool(self._detector.drift_detected)

    @property
    def drift_detected(self) -> bool:
        return bool(self._detector.drift_detected)

    def reset(self) -> None:
        # river detectors expose clone() -> fresh, unfitted copy of same params.
        self._detector = self._detector.clone()


def make_adwin(delta: float = 0.002) -> _RiverAdapter:
    """ADWIN detector (river). delta = bound on the false-positive rate."""
    _require_river()
    return _RiverAdapter(_river_drift.ADWIN(delta=delta), f"ADWIN(delta={delta:g})")


def make_page_hinkley(
    *,
    min_instances: int = 30,
    delta: float = 0.005,
    threshold: float = 50.0,
    alpha: float = 0.9999,
    mode: str = "both",
) -> _RiverAdapter:
    """Page-Hinkley detector (river). threshold (lambda) is in residual units."""
    _require_river()
    ph = _river_drift.PageHinkley(
        min_instances=min_instances,
        delta=delta,
        threshold=threshold,
        alpha=alpha,
        mode=mode,
    )
    return _RiverAdapter(ph, f"PageHinkley(lambda={threshold:.3g})")


def build_detectors(
    ref_sigma: float,
    *,
    adwin_delta: float = 0.002,
    cusum_k_sigma: float = 0.5,
    cusum_h_sigma: float = 5.0,
    ph_delta_sigma: float = 0.5,
    ph_threshold_sigma: float = 8.0,
) -> list[DriftDetector]:
    """Standard trio configured against a reference residual sigma.

    Defaults are the calibrated values from the Phase 1B probe:
      - ADWIN delta=0.002 (scale-free; 0 false alarms over 2e5 in-control).
      - CUSUM k=0.5*sigma, h=5*sigma (two-sided ARL0 ~ 475 samples; the in-house
        implementation matches textbook ARL0=168 at h=4*sigma).
      - Page-Hinkley delta=0.5*sigma, threshold=8*sigma (the tuning-sensitive
        comparator; lower thresholds false-alarm on residual-scale noise).

    Args:
        ref_sigma: Reference residual standard deviation (estimated on an
            in-control window, e.g. early-fold residuals). Must be > 0.

    Returns:
        [ADWIN, Page-Hinkley, CUSUM] as uniform DriftDetectors.
    """
    if ref_sigma <= 0:
        raise ValueError(f"ref_sigma must be > 0, got {ref_sigma}")
    return [
        make_adwin(delta=adwin_delta),
        make_page_hinkley(
            delta=ph_delta_sigma * ref_sigma,
            threshold=ph_threshold_sigma * ref_sigma,
        ),
        CUSUM(k=cusum_k_sigma * ref_sigma, h=cusum_h_sigma * ref_sigma),
    ]


# --------------------------------------------------------------------------- #
# Scanning a residual stream
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DriftScan:
    """Result of running one detector over a residual stream."""

    detector_name: str
    n_samples: int
    fire_indices: list[int]

    @property
    def n_detections(self) -> int:
        return len(self.fire_indices)

    def first_fire_at_or_after(self, boundary: int) -> int | None:
        """Index of the first detection at or after a known boundary, else None."""
        for i in self.fire_indices:
            if i >= boundary:
                return i
        return None

    def detection_latency(self, boundary: int) -> int | None:
        """Samples between a known change boundary and the first fire after it."""
        first = self.first_fire_at_or_after(boundary)
        return None if first is None else first - boundary


def scan(
    residuals: Iterable[float],
    detector: DriftDetector,
    cooldown: int = 0,
) -> DriftScan:
    """Stream residuals through a detector, recording every detection index.

    The detector is reset first so the scan is independent of prior use.

    Args:
        residuals: The stream to monitor.
        detector: A uniform DriftDetector.
        cooldown: Refractory period in samples. After a recorded detection,
            further detections within ``cooldown`` samples are suppressed. This
            collapses the flood a sustained shift would otherwise produce
            (every post-reset sample re-firing) into distinct TRIGGER events --
            which is the operationally meaningful unit, since in deployment a
            detection triggers a recalibration that clears the condition.
            Default 0 = faithful (record every algorithmic detection).
    """
    if cooldown < 0:
        raise ValueError(f"cooldown must be >= 0, got {cooldown}")
    detector.reset()
    fires: list[int] = []
    last_fire: int | None = None
    n = 0
    for i, value in enumerate(residuals):
        n = i + 1
        if detector.update(float(value)) and (last_fire is None or (i - last_fire) > cooldown):
            fires.append(i)
            last_fire = i
    return DriftScan(detector.name, n, fires)


# --------------------------------------------------------------------------- #
# Out-of-sample residual stream on the SAME blocked-CV backbone
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FoldResiduals:
    """Held-out predictions for one forward-chaining CV fold."""

    fold: int
    y_true: np.ndarray
    y_pred: np.ndarray

    @property
    def residuals(self) -> np.ndarray:
        return self.y_true - self.y_pred

    @property
    def r2(self) -> float:
        return float(r2_score(self.y_true, self.y_pred))


def blocked_cv_residuals(
    df: pd.DataFrame,
    make_estimator: Callable[[], Estimator],
    max_lag: int,
    n_splits: int = 5,
    input_cols: Sequence[str] = DEFAULT_INPUT_COLS,
    target_col: str = DEFAULT_TARGET_COL,
    feature_builder: FeatureBuilder | None = None,
) -> list[FoldResiduals]:
    """Per-fold held-out residuals under forward-chaining time-series CV.

    Mirrors ``blocked_cv_r2`` fold mechanics EXACTLY (same TimeSeriesSplit, same
    per-fold leakage-safe build, same train-only scaling, fresh estimator per
    fold) but returns the held-out (y_true, y_pred) per fold instead of only the
    R^2. ``test_blocked_cv_residuals_matches_r2`` pins ``FoldResiduals.r2`` to
    ``blocked_cv_r2`` so the two cannot silently diverge.

    Concatenate the per-fold ``residuals`` in fold order to obtain the honest
    cross-regime residual stream the detectors should monitor.

    Returns:
        One FoldResiduals per fold (length n_splits).

    Raises:
        ValueError: If any fold segment is too short for the requested max_lag.
    """
    build: FeatureBuilder = feature_builder or (
        lambda seg: make_lagged_features(seg, max_lag, input_cols, target_col)
    )
    n = len(df)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    out: list[FoldResiduals] = []
    for fold, (train_idx, test_idx) in enumerate(tscv.split(np.arange(n))):
        seg_tr = df.iloc[train_idx].reset_index(drop=True)
        seg_te = df.iloc[test_idx].reset_index(drop=True)
        if len(seg_tr) <= max_lag or len(seg_te) <= max_lag:
            raise ValueError(
                f"Fold segment too short for max_lag={max_lag}: "
                f"train={len(seg_tr)}, test={len(seg_te)}."
            )
        X_tr, y_tr = build(seg_tr)
        X_te, y_te = build(seg_te)
        scaler = StandardScaler().fit(X_tr)
        est = make_estimator()
        est.fit(scaler.transform(X_tr), y_tr)
        pred = np.asarray(est.predict(scaler.transform(X_te))).ravel()
        out.append(
            FoldResiduals(
                fold=fold,
                y_true=np.asarray(y_te, dtype=float).ravel(),
                y_pred=pred,
            )
        )
    return out


def concat_residual_stream(folds: Sequence[FoldResiduals]) -> np.ndarray:
    """Concatenate per-fold held-out residuals in fold order into one stream."""
    if not folds:
        return np.asarray([], dtype=float)
    return np.concatenate([f.residuals for f in folds])
