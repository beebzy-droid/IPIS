"""Unit tests for the operational state bus schema."""

from __future__ import annotations

from datetime import datetime

import pytest

from ipis.shared.state_bus import HealthFlag, ModuleStatus, OperationalState


class TestOperationalState:
    """Tests for OperationalState schema validation."""

    def test_minimal_state_validates(self) -> None:
        """A state with only required fields should validate."""
        state = OperationalState(
            timestamp=datetime(2026, 5, 28),
            sequence_id=1,
        )
        assert state.sequence_id == 1
        assert state.process_conditions == {}
        assert state.active_constraints == []

    def test_full_state_validates(self, sample_operational_state: OperationalState) -> None:
        """A fully populated state should validate."""
        assert sample_operational_state.sequence_id == 1
        assert sample_operational_state.process_conditions["T1"] == 350.0
        assert sample_operational_state.health_flags["pump_P101"] == HealthFlag.OK

    def test_health_flag_enum_values(self) -> None:
        """HealthFlag enum should have exactly three levels."""
        assert HealthFlag.OK.value == "ok"
        assert HealthFlag.WARN.value == "warn"
        assert HealthFlag.ALARM.value == "alarm"

    def test_state_serializes_to_json(self, sample_operational_state: OperationalState) -> None:
        """State should serialize and round-trip via JSON."""
        json_str = sample_operational_state.model_dump_json()
        restored = OperationalState.model_validate_json(json_str)
        assert restored.sequence_id == sample_operational_state.sequence_id
        assert restored.process_conditions == sample_operational_state.process_conditions

    def test_invalid_health_flag_rejected(self) -> None:
        """Unknown health flag values should raise validation error."""
        with pytest.raises(ValueError):
            OperationalState(
                timestamp=datetime(2026, 5, 28),
                sequence_id=1,
                health_flags={"pump": "exploded"},  # not a valid HealthFlag value
            )


class TestModuleStatus:
    """Tests for ModuleStatus."""

    def test_minimal_module_status(self) -> None:
        """ModuleStatus requires only module_id."""
        status = ModuleStatus(module_id="m1")
        assert status.healthy is True
        assert status.drift_detected is False
        assert status.latency_ms is None
