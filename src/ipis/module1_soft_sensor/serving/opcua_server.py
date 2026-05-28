"""Simulated OPC-UA server for Module 1.

Replays benchmark datasets (Debutanizer, TEP) as if they were live process
data streaming from a real plant's PLC/DCS.

Tag namespace: configurable via OPCUA_NAMESPACE env var (default: 'ipis').
Tags are named per the dataset's input variables (see configs/dataset/*.yaml).
"""

from __future__ import annotations

import asyncio

from ipis.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def serve(endpoint: str, namespace: str, dataset_name: str) -> None:
    """Start the simulated OPC-UA server.

    Args:
        endpoint: OPC-UA endpoint URL (e.g., opc.tcp://0.0.0.0:4840).
        namespace: OPC-UA namespace URI (e.g., 'ipis').
        dataset_name: Which benchmark dataset to replay.

    Raises:
        NotImplementedError: Placeholder until Phase 1D.
    """
    raise NotImplementedError("Implement in Phase 1D using asyncua. See docs/module1/spec.md")


def main() -> None:
    """Entry point for the OPC-UA server."""
    configure_logging(json_format=False)
    logger.info(
        "opcua_server_starting",
        message="OPC-UA simulator placeholder — implement in Phase 1D",
    )

    try:
        asyncio.run(serve("opc.tcp://0.0.0.0:4840", "ipis", "debutanizer"))
    except NotImplementedError as exc:
        logger.error("not_implemented", message=str(exc))


if __name__ == "__main__":
    main()
