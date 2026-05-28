"""Unit tests for the data router."""

from __future__ import annotations

import pytest

from ipis.shared.data_router import DataRouter


class _PassThroughExtractor:
    """Test extractor: returns inputs as-is with a prefix."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def extract(self, raw_inputs: dict[str, float]) -> dict[str, float]:
        return {f"{self.prefix}_{k}": v for k, v in raw_inputs.items()}


class TestDataRouter:
    """Tests for DataRouter routing logic."""

    def test_empty_router_has_no_modules(self) -> None:
        router = DataRouter()
        assert router.registered_modules == []

    def test_register_and_route(self, sample_process_conditions: dict[str, float]) -> None:
        router = DataRouter()
        router.register("m1", _PassThroughExtractor(prefix="m1"))

        result = router.route("m1", sample_process_conditions)
        assert "m1_T1" in result
        assert result["m1_T1"] == 350.0

    def test_route_unknown_module_raises(self) -> None:
        router = DataRouter()
        with pytest.raises(KeyError, match="m99"):
            router.route("m99", {"T1": 1.0})

    def test_route_all_dispatches_to_every_extractor(
        self, sample_process_conditions: dict[str, float]
    ) -> None:
        router = DataRouter()
        router.register("m1", _PassThroughExtractor(prefix="m1"))
        router.register("m2", _PassThroughExtractor(prefix="m2"))

        results = router.route_all(sample_process_conditions)
        assert set(results.keys()) == {"m1", "m2"}
        assert "m1_T1" in results["m1"]
        assert "m2_T1" in results["m2"]

    def test_registered_modules_lists_all(self) -> None:
        router = DataRouter()
        router.register("m1", _PassThroughExtractor(prefix="m1"))
        router.register("m2", _PassThroughExtractor(prefix="m2"))
        assert set(router.registered_modules) == {"m1", "m2"}
