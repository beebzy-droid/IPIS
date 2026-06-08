"""ASGI entrypoint for the soft-sensor service (Phase 1D.2c).

Serve with::

    set PYTHONPATH=src
    uvicorn ipis.module1_soft_sensor.serving.main:app --host 0.0.0.0 --port 8000

``load_service`` resolves the model bundle from ``IPIS_MODEL_BUNDLE`` /
``IPIS_MLFLOW_MODEL`` / the committed fixture (see loader). Set ``IPIS_SNAPSHOT`` to a
path to make the running service restart-safe (state restored on startup, saved on
shutdown by the FastAPI lifespan).
"""

from __future__ import annotations

import os

from ipis.module1_soft_sensor.serving.api import create_app
from ipis.module1_soft_sensor.serving.loader import load_service


def get_app():
    """Factory form (for ``uvicorn --factory ...:get_app``)."""
    return create_app(load_service(snapshot_path=os.environ.get("IPIS_SNAPSHOT")))


app = get_app()
