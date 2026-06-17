"""Tests for the CWRU benchmark manifest (Smith & Randall Tables 3 & 6)."""

from __future__ import annotations

from ipis.module2_pdm.data.cwru_manifest import (
    BENCHMARK_FILES,
    NTN_028_FILES,
    SMITH_RANDALL_DE_EXCLUDE,
    defect_for_class,
    normal_baseline_files,
    usable_de_files,
)


def test_benchmark_has_40_files():
    n = sum(len(v) for v in BENCHMARK_FILES.values())
    assert n == 40  # normal(4) + 9 fault classes x 4 loads


def test_normal_baseline():
    assert normal_baseline_files() == [97, 98, 99, 100]


def test_excludes_are_dropped():
    usable = usable_de_files()
    flat = {f for files in usable.values() for f in files}
    assert flat.isdisjoint(SMITH_RANDALL_DE_EXCLUDE)
    # spot-check specific Smith & Randall drops
    assert 118 not in flat and 119 not in flat and 120 not in flat  # ball_007 DE
    assert 200 not in flat  # or_014 DE
    assert 224 not in flat and 225 not in flat  # ball_021 DE
    assert 236 not in flat and 237 not in flat  # or_021 DE clipped


def test_kept_files_survive():
    usable = usable_de_files()
    assert 121 in usable["ball_007"]  # only 121BA was bad; 121DE kept
    assert 222 in usable["ball_021"] and 223 in usable["ball_021"]
    assert usable["ir_007"] == [105, 106, 107, 108]  # IR set fully clean
    assert usable["or_007"] == [130, 131, 132, 133]


def test_ntn_028_not_in_benchmark():
    flat = {f for loads in BENCHMARK_FILES.values() for f in loads.values()}
    assert flat.isdisjoint(NTN_028_FILES)


def test_defect_mapping():
    assert defect_for_class("ir_021") == "bpfi"
    assert defect_for_class("ball_007") == "bsf"
    assert defect_for_class("or_014") == "bpfo"
    assert defect_for_class("normal") is None


def test_exclude_include_normal_toggle():
    assert "normal" in usable_de_files(include_normal=True)
    assert "normal" not in usable_de_files(include_normal=False)
