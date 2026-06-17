"""Health index for bearing condition monitoring (Module 2, Phase 2A — Option C).

A Hotelling T^2 (squared Mahalanobis distance) model fit on a healthy baseline of
the combined feature vector (time-domain + fault-band ratios). It produces the
three quantities the operational state bus contracts:

  * health_score in [0,1]  -> OperationalState.equipment_health  (1.0 = healthy)
  * flag OK/WARN/ALARM      -> OperationalState.health_flags
  * t2 (unbounded)          -> the monotone degradation magnitude that feeds the
                               FEMTO RUL regressor in Phase 2B.

Control limits use the chi-square quantiles of T^2 at n_features degrees of
freedom (the standard SPC approximation for a known/large-sample baseline; for
small baselines the exact limit is a scaled F, a refinement noted in spec.md).
The [0,1] health score is anchored so that a sample at the healthy expectation
(T^2 ~ n_features) scores 1.0:  health = 1 / (1 + max(0, T^2 - n_features)/n_features).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import chi2

from ipis.shared.state_bus import HealthFlag


@dataclass(frozen=True)
class HealthIndexModel:
    """Fitted Hotelling T^2 health model over a named feature vector."""

    feature_names: tuple[str, ...]
    mean: np.ndarray
    precision: np.ndarray  # inverse of the (ridge-regularized) baseline covariance
    warn_t2: float
    alarm_t2: float

    @property
    def n_features(self) -> int:
        return self.mean.size

    @classmethod
    def fit(
        cls,
        x_healthy: np.ndarray,
        feature_names: tuple[str, ...],
        warn_q: float = 0.95,
        alarm_q: float = 0.99,
        ridge: float = 1e-6,
    ) -> HealthIndexModel:
        """Fit mean/precision on healthy feature vectors; set chi-square limits.

        `x_healthy` is (n_samples, n_features). A ridge term stabilizes the
        covariance inverse when samples are limited relative to dimensions.
        """
        x = np.atleast_2d(np.asarray(x_healthy, dtype=float))
        if x.shape[0] < 2:
            raise ValueError("need >= 2 healthy samples to estimate covariance")
        if x.shape[1] != len(feature_names):
            raise ValueError("feature count != len(feature_names)")
        mean = x.mean(axis=0)
        cov = np.cov(x, rowvar=False)
        cov = np.atleast_2d(cov) + ridge * np.eye(x.shape[1])
        precision = np.linalg.inv(cov)
        df = x.shape[1]
        return cls(
            feature_names=tuple(feature_names),
            mean=mean,
            precision=precision,
            warn_t2=float(chi2.ppf(warn_q, df)),
            alarm_t2=float(chi2.ppf(alarm_q, df)),
        )

    def t2(self, x: np.ndarray) -> float:
        """Hotelling T^2 (squared Mahalanobis distance) for one feature vector."""
        d = np.asarray(x, dtype=float).ravel() - self.mean
        return float(d @ self.precision @ d)

    def health_score(self, x: np.ndarray) -> float:
        """Map T^2 to [0,1] health, anchored so healthy (T^2 ~ df) -> 1.0."""
        t2 = self.t2(x)
        excess = max(0.0, t2 - self.n_features)
        return 1.0 / (1.0 + excess / self.n_features)

    def flag(self, x: np.ndarray) -> HealthFlag:
        """OK/WARN/ALARM from T^2 against the chi-square control limits."""
        t2 = self.t2(x)
        if t2 >= self.alarm_t2:
            return HealthFlag.ALARM
        if t2 >= self.warn_t2:
            return HealthFlag.WARN
        return HealthFlag.OK

    def assess(self, x: np.ndarray) -> dict[str, object]:
        """Convenience: all three contracted outputs plus raw T^2 for one sample."""
        t2 = self.t2(x)
        excess = max(0.0, t2 - self.n_features)
        return {
            "t2": t2,
            "health_score": 1.0 / (1.0 + excess / self.n_features),
            "flag": self.flag(x),
        }
