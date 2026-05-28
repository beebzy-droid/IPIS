"""End-to-end training pipeline for Module 1 (Hydra entry point).

Usage:
    python -m ipis.module1_soft_sensor.pipelines.train \
        +dataset=debutanizer +model=hybrid_pathb
"""

from __future__ import annotations

import hydra
from omegaconf import DictConfig

from ipis.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)


@hydra.main(version_base=None, config_path="../../../../configs", config_name="config")
def train(cfg: DictConfig) -> None:
    """Hydra-composed training entry point.

    Args:
        cfg: Composed Hydra configuration. See configs/config.yaml.

    Raises:
        NotImplementedError: Placeholder until Phase 1A.
    """
    configure_logging(level=cfg.get("log_level", "INFO"), json_format=False)
    logger.info(
        "training_run_starting",
        dataset=cfg.dataset.name,
        model=cfg.model.name,
        seed=cfg.seed,
    )

    raise NotImplementedError("Implement in Phase 1A. See docs/module1/spec.md")


if __name__ == "__main__":
    train()
