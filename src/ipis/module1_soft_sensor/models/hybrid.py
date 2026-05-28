"""Path B residual hybrid soft sensor model.

ŷ_hybrid(t) = ŷ_physics(u(t), θ) + ŷ_ML(features(t))

Where ŷ_physics is from the first-principles model and ŷ_ML learns the
residual r(t) = y_true(t) − ŷ_physics(t) with physics-informed loss
regularization.

If the PINN regularization destabilizes training, λ_physics → 0 and the
model degrades gracefully to a standard residual ML learner.

See: docs/architecture/decisions/001-path-b-pinn.md
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class PhysicsModel(Protocol):
    """First-principles model interface."""

    def predict(self, inputs: np.ndarray) -> np.ndarray:
        """Predict ŷ_physics from process inputs."""
        ...


class ResidualHybridSoftSensor:
    """Path B residual hybrid soft sensor.

    Composes a first-principles physics model with a neural network residual
    learner regularized by physics-informed loss terms.
    """

    def __init__(
        self,
        physics_model: PhysicsModel,
        lambda_data: float = 1.0,
        lambda_physics: float = 0.1,
        lambda_smooth: float = 0.01,
    ) -> None:
        """Initialize the hybrid model.

        Args:
            physics_model: First-principles model producing ŷ_physics.
            lambda_data: Weight on data-fitting loss term.
            lambda_physics: Weight on physics-violation loss term.
            lambda_smooth: Weight on residual smoothness penalty.
        """
        self.physics_model = physics_model
        self.lambda_data = lambda_data
        self.lambda_physics = lambda_physics
        self.lambda_smooth = lambda_smooth
        self._fallback_active = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ResidualHybridSoftSensor":
        """Train the residual learner with physics-informed regularization.

        Args:
            X: Process features, shape (n_samples, n_features).
            y: True quality variable, shape (n_samples,).

        Returns:
            Self, for chaining.

        Raises:
            NotImplementedError: Placeholder until Phase 1A.
        """
        raise NotImplementedError("Implement in Phase 1A. See docs/module1/spec.md")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict ŷ_hybrid = ŷ_physics + ŷ_ML.

        Args:
            X: Process features, shape (n_samples, n_features).

        Returns:
            Predictions, shape (n_samples,).

        Raises:
            NotImplementedError: Placeholder until Phase 1A.
        """
        raise NotImplementedError("Implement in Phase 1A. See docs/module1/spec.md")

    @property
    def is_fallback_active(self) -> bool:
        """Whether the model fell back to standard ML residual (no physics loss)."""
        return self._fallback_active
