"""Module 2 data loaders and dataset manifests."""

from ipis.module2_pdm.data.cwru_loader import CWRURecord, load_cwru_mat
from ipis.module2_pdm.data.cwru_manifest import (
    BENCHMARK_FILES,
    SMITH_RANDALL_DE_EXCLUDE,
    defect_for_class,
    normal_baseline_files,
    usable_de_files,
)

__all__ = [
    "CWRURecord",
    "load_cwru_mat",
    "BENCHMARK_FILES",
    "SMITH_RANDALL_DE_EXCLUDE",
    "usable_de_files",
    "normal_baseline_files",
    "defect_for_class",
]
