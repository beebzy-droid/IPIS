"""Shared pytest fixtures for IPIS tests."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from ipis.shared.state_bus import HealthFlag, ModuleStatus, OperationalState


@pytest.fixture
def rng() -> np.random.Generator:
    """Reproducible numpy random generator."""
    return np.random.default_rng(seed=42)


@pytest.fixture
def sample_process_conditions() -> dict[str, float]:
    """A representative set of process measurements."""
    return {
        "T1": 350.0,
        "P1": 5.2,
        "F1": 120.0,
        "L1": 75.0,
    }


@pytest.fixture
def sample_operational_state(sample_process_conditions: dict[str, float]) -> OperationalState:
    """A populated OperationalState for tests."""
    return OperationalState(
        timestamp=datetime(2026, 5, 28, 10, 0, 0),
        sequence_id=1,
        process_conditions=sample_process_conditions,
        quality_estimate={"C4_bottom": 0.0023},
        quality_confidence={"C4_bottom": 0.0004},
        equipment_health={"pump_P101": 0.92},
        health_flags={"pump_P101": HealthFlag.OK},
        remaining_useful_life={"pump_P101": 720.0},
        setpoint_recommendations={},
        active_constraints=[],
        module_status={
            "m1": ModuleStatus(
                module_id="m1",
                healthy=True,
                drift_detected=False,
                latency_ms=12.4,
                last_update=datetime(2026, 5, 28, 10, 0, 0),
            ),
        },
    )
