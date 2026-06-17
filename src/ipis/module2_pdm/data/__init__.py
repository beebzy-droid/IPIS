"""Module 2 data loaders and dataset manifests."""

from ipis.module2_pdm.data.cwru_loader import CWRURecord, load_cwru_mat
from ipis.module2_pdm.data.cwru_manifest import (
    BENCHMARK_FILES,
    SMITH_RANDALL_DE_EXCLUDE,
    defect_for_class,
    normal_baseline_files,
    usable_de_files,
)
from ipis.module2_pdm.data.femto_loader import (
    FEMTO_FS,
    FEMTO_SNAPSHOT_INTERVAL_S,
    FEMTOBearing,
    load_femto_bearing,
    load_femto_snapshot,
)

__all__ = [
    "CWRURecord",
    "load_cwru_mat",
    "BENCHMARK_FILES",
    "SMITH_RANDALL_DE_EXCLUDE",
    "usable_de_files",
    "normal_baseline_files",
    "defect_for_class",
    "FEMTOBearing",
    "load_femto_bearing",
    "load_femto_snapshot",
    "FEMTO_FS",
    "FEMTO_SNAPSHOT_INTERVAL_S",
]
