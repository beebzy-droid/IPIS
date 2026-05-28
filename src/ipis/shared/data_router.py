"""Data router — directs raw process inputs to the right module's feature extractor.

The router is a thin coordinator that knows which module wants which raw signals,
and applies the per-module feature extraction. It does NOT do heavy preprocessing
itself; that's the responsibility of each module's data submodule.
"""

from __future__ import annotations

from typing import Protocol


class FeatureExtractor(Protocol):
    """Protocol for module-specific feature extractors."""

    def extract(self, raw_inputs: dict[str, float]) -> dict[str, float]:
        """Transform raw process inputs into module-ready features."""
        ...


class DataRouter:
    """Routes raw process inputs to registered module feature extractors."""

    def __init__(self) -> None:
        self._extractors: dict[str, FeatureExtractor] = {}

    def register(self, module_id: str, extractor: FeatureExtractor) -> None:
        """Register a feature extractor for a module.

        Args:
            module_id: Module identifier (e.g., 'm1', 'm2', 'm3').
            extractor: Object implementing the FeatureExtractor protocol.
        """
        self._extractors[module_id] = extractor

    def route(self, module_id: str, raw_inputs: dict[str, float]) -> dict[str, float]:
        """Route raw inputs to a specific module's feature extractor.

        Args:
            module_id: Module identifier.
            raw_inputs: Raw process measurements.

        Returns:
            Feature dictionary ready for module consumption.

        Raises:
            KeyError: If no extractor is registered for the module_id.
        """
        if module_id not in self._extractors:
            raise KeyError(f"No feature extractor registered for module '{module_id}'")
        return self._extractors[module_id].extract(raw_inputs)

    def route_all(
        self, raw_inputs: dict[str, float]
    ) -> dict[str, dict[str, float]]:
        """Route raw inputs to all registered extractors in parallel.

        Args:
            raw_inputs: Raw process measurements.

        Returns:
            Dict keyed by module_id, with each value being that module's features.
        """
        return {
            module_id: extractor.extract(raw_inputs)
            for module_id, extractor in self._extractors.items()
        }

    @property
    def registered_modules(self) -> list[str]:
        """List of module IDs with registered extractors."""
        return list(self._extractors.keys())
