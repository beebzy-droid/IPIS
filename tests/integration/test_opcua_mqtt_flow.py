"""Integration tests for OPC-UA → MQTT data flow.

These tests require a running MQTT broker and OPC-UA server.
Marked as `integration` so they're skipped by default unit-test runs.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestOPCUAMQTTFlow:
    """End-to-end OPC-UA → preprocessing → MQTT integration tests."""

    @pytest.mark.skip(reason="Not implemented yet — Phase 1D")
    def test_opcua_publish_to_mqtt(self) -> None:
        """OPC-UA tag update should produce an MQTT message."""
        # TODO: Implement in Phase 1D
        raise NotImplementedError

    @pytest.mark.skip(reason="Not implemented yet — Phase 1D")
    def test_end_to_end_latency_under_budget(self) -> None:
        """Total OPC-UA → prediction → MQTT latency must be < 500ms."""
        # TODO: Implement in Phase 1D
        raise NotImplementedError
