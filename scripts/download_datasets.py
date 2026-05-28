"""Download IPIS Module 1 datasets.

Usage:
    python scripts/download_datasets.py --all
    python scripts/download_datasets.py --dataset debutanizer
    python scripts/download_datasets.py --dataset tep
    python scripts/download_datasets.py --dataset secom
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ipis.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)

DATA_ROOT = Path(__file__).parent.parent / "data" / "raw"

DATASETS = {
    "debutanizer": {
        "description": "Fortuna et al. (2007) — French refinery debutanizer column",
        "instructions": (
            "Manual download required. The Debutanizer dataset is distributed with the\n"
            "Fortuna et al. (2007) book 'Soft Sensors for Monitoring and Control of\n"
            "Industrial Processes' and is available in multiple academic mirrors.\n"
            "\n"
            "Recommended sources:\n"
            "  1. Search 'debutanizer.dat Fortuna soft sensor' on Google Scholar\n"
            "  2. DTU course materials (search 'DTU debutanizer dataset')\n"
            "  3. Several GitHub repos hosting the dataset for academic use\n"
            "\n"
            "Place the file at: data/raw/debutanizer/debutanizer.dat"
        ),
    },
    "tep": {
        "description": "Tennessee Eastman Process — Downs & Vogel (1993)",
        "instructions": (
            "Clone the TEP dataset repository:\n"
            "\n"
            "  cd data/raw/tep\n"
            "  git clone https://github.com/camaramm/tennessee-eastman-profBraatz.git .\n"
            "\n"
            "Alternative: Rieth et al. (2017) extended TEP dataset is available on Harvard Dataverse.\n"
            "Search 'Tennessee Eastman extended Rieth Harvard Dataverse'."
        ),
    },
    "secom": {
        "description": "SECOM Semiconductor — UCI ML Repository",
        "instructions": (
            "Download from UCI ML Repository:\n"
            "\n"
            "  cd data/raw/secom\n"
            "  wget https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom.data\n"
            "  wget https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom_labels.data\n"
            "  wget https://archive.ics.uci.edu/ml/machine-learning-databases/secom/secom.names\n"
            "\n"
            "If wget is unavailable, download manually from:\n"
            "  https://archive.ics.uci.edu/ml/datasets/SECOM"
        ),
    },
}


def show_instructions(dataset_name: str) -> None:
    """Print download instructions for a dataset."""
    info = DATASETS[dataset_name]
    target_dir = DATA_ROOT / dataset_name
    target_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "dataset_download_instructions",
        dataset=dataset_name,
        description=info["description"],
        target_directory=str(target_dir),
    )
    print(f"\n{'=' * 70}")
    print(f"  {dataset_name.upper()}")
    print(f"  {info['description']}")
    print(f"{'=' * 70}")
    print(info["instructions"])
    print(f"\n  Target directory: {target_dir}")
    print(f"{'=' * 70}\n")


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Download IPIS Module 1 datasets")
    parser.add_argument("--all", action="store_true", help="Show instructions for all datasets")
    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()),
        help="Show instructions for a specific dataset",
    )
    args = parser.parse_args()

    configure_logging(json_format=False)

    if not args.all and not args.dataset:
        parser.print_help()
        return 1

    datasets_to_show = list(DATASETS.keys()) if args.all else [args.dataset]
    for dataset in datasets_to_show:
        show_instructions(dataset)

    return 0


if __name__ == "__main__":
    sys.exit(main())
