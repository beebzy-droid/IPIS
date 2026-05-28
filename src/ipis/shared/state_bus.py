"""Operational state bus — the shared contract between IPIS modules.

All modules read from and write to this schema. This is the single
source of truth for inter-module data exchange.

See: docs/architecture/system-overview.md (section "The operational state bus")
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HealthFlag(StrEnum):
    """Equipment health flag levels."""

    OK = "ok"
    WARN = "warn"
    ALARM = "alarm"


class ModuleStatus(BaseModel):
    """Per-module operational status."""

    module_id: str = Field(..., description="e.g. 'm1', 'm2', 'm3'")
    healthy: bool = True
    drift_detected: bool = False
    latency_ms: float | None = None
    last_update: datetime | None = None
    error_message: str | None = None


class OperationalState(BaseModel):
    """Shared state vector consumed and produced by all IPIS modules.

    Modules MUST NOT add ad-hoc fields. Schema changes go through an ADR.
    """

    # ---- Timing ----
    timestamp: datetime
    sequence_id: int = Field(..., description="Monotonically increasing per cycle")

    # ---- Process conditions (raw measurements) ----
    process_conditions: dict[str, float] = Field(
        default_factory=dict,
        description="Raw measured process variables (T, P, F, etc.)",
    )

    # ---- Module 1 outputs: soft sensor ----
    quality_estimate: dict[str, float] = Field(
        default_factory=dict,
        description="Soft sensor predictions, keyed by quality variable name",
    )
    quality_confidence: dict[str, float] = Field(
        default_factory=dict,
        description="95% prediction interval half-width per quality variable",
    )

    # ---- Module 2 outputs: predictive maintenance ----
    equipment_health: dict[str, float] = Field(
        default_factory=dict,
        description="Health score (0.0–1.0) per equipment ID",
    )
    health_flags: dict[str, HealthFlag] = Field(
        default_factory=dict,
        description="Flag level per equipment ID",
    )
    remaining_useful_life: dict[str, float] = Field(
        default_factory=dict,
        description="RUL in hours per equipment ID (when available)",
    )

    # ---- Module 3 outputs: RTO ----
    setpoint_recommendations: dict[str, float] = Field(
        default_factory=dict,
        description="Recommended setpoint values from RTO",
    )
    active_constraints: list[str] = Field(
        default_factory=list,
        description="Constraints currently binding in the optimization",
    )

    # ---- Cross-module status ----
    module_status: dict[str, ModuleStatus] = Field(
        default_factory=dict,
        description="Per-module status: keyed by module_id",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2026-05-28T10:00:00Z",
                "sequence_id": 1,
                "process_conditions": {"T1": 350.0, "P1": 5.2, "F1": 120.0},
                "quality_estimate": {"C4_bottom": 0.0023},
                "quality_confidence": {"C4_bottom": 0.0004},
                "equipment_health": {"pump_P101": 0.92, "exchanger_E201": 0.85},
                "health_flags": {"pump_P101": "ok", "exchanger_E201": "warn"},
                "remaining_useful_life": {"pump_P101": 720.0},
                "setpoint_recommendations": {"feed_flow_setpoint": 118.5},
                "active_constraints": ["quality_spec_lower"],
                "module_status": {
                    "m1": {
                        "module_id": "m1",
                        "healthy": True,
                        "drift_detected": False,
                        "latency_ms": 12.4,
                    },
                },
            }
        }
    )
