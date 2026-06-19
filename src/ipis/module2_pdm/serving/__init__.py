"""Module 2 serving layer (Phase 2D): PdM service, fitted-artifact loader, API.

Composes the 2A health index and the 2B similarity RUL into the OperationalState
fields the IPIS state bus contracts (equipment_health, health_flags,
remaining_useful_life).
"""

from __future__ import annotations

from ipis.module2_pdm.serving.api import create_app
from ipis.module2_pdm.serving.loader import PdMArtifact, load_artifact, save_artifact
from ipis.module2_pdm.serving.service import PdMService

__all__ = [
    "PdMArtifact",
    "PdMService",
    "create_app",
    "load_artifact",
    "save_artifact",
]
