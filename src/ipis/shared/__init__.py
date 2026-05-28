"""Shared infrastructure for IPIS modules.

- state_bus: OperationalState schema (the inter-module contract)
- data_router: Routes raw inputs to module-specific feature extractors
- config: Pydantic-settings configuration loader
- logging: structlog-based logging setup
"""

from ipis.shared.state_bus import HealthFlag, ModuleStatus, OperationalState

__all__ = ["HealthFlag", "ModuleStatus", "OperationalState"]
