"""The N1 paper's figure and table generators (scripts/paper_n1).

The committed outputs in docs/paper/figures/n1/ must be what the generators make from the
committed Phase 1 evidence. Every table (LaTeX and CSV) and every figure's CSV of plotted numbers
is regenerated into a temporary directory and compared with the committed copy: text exactly,
numbers to a relative 1e-12. The PDF and PNG bytes depend on the matplotlib version, so only their
presence is checked. The figures need matplotlib (the test skips without it); rendering them also
runs the generators' own checks against the evidence (rolling coverage against the stage B
record, open-loop IACT against F8).
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest
from scripts.paper_n1 import style, tables

FIGURES = ("n1_stability", "n1_diagnosis", "n1_speed_chart", "n1_persistence", "n1_debutanizer")
TABLES = ("n1_table_rules", "n1_table_t1_cells", "n1_table_baselines")


def _rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def _same(a: str, b: str) -> bool:
    try:
        x, y = float(a), float(b)
    except ValueError:
        return a == b
    if math.isnan(x) or math.isnan(y):
        return math.isnan(x) and math.isnan(y)
    return math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-15)


def _assert_same_csv(new: Path, old: Path) -> None:
    a, b = _rows(new), _rows(old)
    assert len(a) == len(b), f"{new.name}: {len(a)} rows, committed {len(b)}"
    for i, (ra, rb) in enumerate(zip(a, b, strict=True)):
        assert len(ra) == len(rb), f"{new.name}, row {i}: {ra} against {rb}"
        assert all(
            _same(x, y) for x, y in zip(ra, rb, strict=True)
        ), f"{new.name}, row {i}: {ra} against {rb}"


def test_tables_match_the_committed_copies(tmp_path: Path) -> None:
    paths = tables.render(out_dir=tmp_path)
    assert sorted(p.name for p in paths) == sorted(
        f"{t}.{e}" for t in TABLES for e in ("tex", "csv")
    )
    for p in paths:
        old = style.FIGURE_DIR / p.name
        if p.suffix == ".tex":
            # read_text translates line endings, so a CRLF checkout compares equal
            assert p.read_text(encoding="utf-8") == old.read_text(encoding="utf-8"), p.name
        else:
            _assert_same_csv(p, old)


def test_figures_render_and_match_the_committed_numbers(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    from scripts.paper_n1 import make_all

    paths = [p for render in make_all.PARTS.values() for p in render(None, tmp_path)]
    expected = {f"{f}.{e}" for f in FIGURES for e in ("pdf", "png", "csv")}
    expected |= {f"{t}.{e}" for t in TABLES for e in ("tex", "csv")}
    assert {p.name for p in paths} == expected
    for f in FIGURES:
        _assert_same_csv(tmp_path / f"{f}.csv", style.FIGURE_DIR / f"{f}.csv")
        for e in ("pdf", "png"):
            assert (tmp_path / f"{f}.{e}").stat().st_size > 5_000, f"{f}.{e}"
