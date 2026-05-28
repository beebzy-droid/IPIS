"""Structured logging configuration for IPIS.

Uses structlog for JSON-formatted logs in production and human-readable
output in development.
"""

from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging(level: str | None = None, json_format: bool | None = None) -> None:
    """Configure structlog for the IPIS package.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to env LOG_LEVEL or INFO.
        json_format: If True, emit JSON logs. If False, human-readable. Defaults to env LOG_FORMAT.
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")
    if json_format is None:
        json_format = os.getenv("LOG_FORMAT", "json").lower() == "json"

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger for a given module name.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)
