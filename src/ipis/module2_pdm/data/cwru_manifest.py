"""CWRU 12 kHz Drive-End benchmark manifest, pinned to Smith & Randall (2015).

The 40-file benchmark set (Normal + IR/Ball/OR centred x 0.007/0.014/0.021 in. x
loads 0-3 HP) and the records that must be DROPPED for drive-end (DE) analysis
because Smith & Randall found them non-diagnosable or corrupted:

  - Table 6 (not diagnosable with any standard method, DE channel):
      Ball 0.007 in.: 118, 119, 120 (120DE)
      Ball 0.021 in.: 224 (224DE), 225 (225DE)
      OR 0.014 in.:   200
  - Table 3 (clipped in sections, DE channel): 236DE, 237DE  (OR 0.021 in.)
  - The 0.028 in. IR faults (3001-3004) use an equivalent NTN bearing with
    DIFFERENT geometry (Smith & Randall, Table 2 footnote) -> excluded entirely;
    they are not part of the 0.007/0.014/0.021 in. SKF-6205 benchmark anyway.

Verify-before-load-bearing: numbers above are transcribed from Smith & Randall
(2015) Tables 3 and 6. Channels other than DE (FE/BA) have their own exclusions
in those tables; this manifest is scoped to the DE fault-bearing signal used in
Phase 2A.
"""

from __future__ import annotations

# fault_class -> {motor_load_hp: file_number} for the 12 kHz DE benchmark.
BENCHMARK_FILES: dict[str, dict[int, int]] = {
    "normal": {0: 97, 1: 98, 2: 99, 3: 100},
    "ir_007": {0: 105, 1: 106, 2: 107, 3: 108},
    "ir_014": {0: 169, 1: 170, 2: 171, 3: 172},
    "ir_021": {0: 209, 1: 210, 2: 211, 3: 212},
    "ball_007": {0: 118, 1: 119, 2: 120, 3: 121},
    "ball_014": {0: 185, 1: 186, 2: 187, 3: 188},
    "ball_021": {0: 222, 1: 223, 2: 224, 3: 225},
    "or_007": {0: 130, 1: 131, 2: 132, 3: 133},
    "or_014": {0: 197, 1: 198, 2: 199, 3: 200},
    "or_021": {0: 234, 1: 235, 2: 236, 3: 237},
}

# DE records to drop (Smith & Randall Tables 3 & 6); see module docstring.
SMITH_RANDALL_DE_EXCLUDE: frozenset[int] = frozenset({118, 119, 120, 200, 224, 225, 236, 237})

# 0.028 in. IR faults: different (NTN) bearing geometry; never use with the 6205 physics.
NTN_028_FILES: frozenset[int] = frozenset({3001, 3002, 3003, 3004})

# Faults whose physics signature is the named defect frequency (for validation/labels).
FAULT_TO_DEFECT: dict[str, str] = {
    "ir_007": "bpfi",
    "ir_014": "bpfi",
    "ir_021": "bpfi",
    "ball_007": "bsf",
    "ball_014": "bsf",
    "ball_021": "bsf",
    "or_007": "bpfo",
    "or_014": "bpfo",
    "or_021": "bpfo",
}


def usable_de_files(include_normal: bool = True) -> dict[str, list[int]]:
    """Benchmark file numbers per class with the S&R DE exclusions removed."""
    out: dict[str, list[int]] = {}
    for cls, loads in BENCHMARK_FILES.items():
        if cls == "normal" and not include_normal:
            continue
        keep = [f for f in loads.values() if f not in SMITH_RANDALL_DE_EXCLUDE]
        if keep:
            out[cls] = keep
    return out


def normal_baseline_files() -> list[int]:
    """The healthy baseline file numbers (for fitting the health index)."""
    return list(BENCHMARK_FILES["normal"].values())


def defect_for_class(fault_class: str) -> str | None:
    """The expected defect frequency key ('bpfo'|'bpfi'|'bsf') for a fault class."""
    return FAULT_TO_DEFECT.get(fault_class)
