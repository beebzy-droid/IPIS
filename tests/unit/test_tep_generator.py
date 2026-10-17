"""Unit tests for the TEP generator helpers and the run qualification rule (N1 Phase 1, D-P1.8).

``scripts/generate_tep_modes.py`` and ``scripts/tep_seed_qualification.py`` need the Fortran
sources only to run the simulator; the helpers tested here work on synthetic arrays, on small
stand-in source files and on the pure-Python MRG32k3a reference.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
try:
    gen = importlib.import_module("generate_tep_modes")
    qual = importlib.import_module("tep_seed_qualification")  # imports generate_tep_modes
finally:
    sys.path.remove(str(_SCRIPTS))


def _run(n: int = 200, freeze_at: int | None = None, seed: int = 0) -> np.ndarray:
    """Synthetic simulator output: time (h), then 53 noisy columns; frozen from ``freeze_at``."""
    rng = np.random.default_rng(seed)
    d = np.column_stack([np.arange(n) / 60.0, 2800.0 + rng.normal(0, 5, (n, 53))])
    d[:, 9] = 120.0 + rng.normal(0, 0.1, n)  # reactor temperature, XMEAS(9)
    if freeze_at is not None:
        d[freeze_at:, 1:] = d[freeze_at, 1:]
    return d


# --------------------------------------------------------------------------- shutdown detection
def test_shutdown_time_none_in_normal_operation() -> None:
    assert gen.shutdown_time(_run()) is None


def test_shutdown_time_detects_a_freeze_below_the_limits() -> None:
    d = _run(freeze_at=120)
    assert d[:, 7].max() < 3000.0
    assert gen.shutdown_time(d) == pytest.approx(d[120, 0])


def test_shutdown_time_detects_a_freeze_in_the_last_rows() -> None:
    d = _run(freeze_at=198)  # rows 198 and 199 equal: shorter than ``still``
    assert gen.shutdown_time(d) == pytest.approx(d[198, 0])


def test_written_limit_is_a_diagnostic_not_a_shutdown() -> None:
    d = _run()
    d[150, 7] = 3000.0  # a noisy reading at the limit, without a freeze
    assert gen.shutdown_time(d) is None
    assert gen.limit_time(d) == pytest.approx(d[150, 0])
    assert gen.limit_time(_run()) is None


def test_shutdown_time_ignores_a_short_repeat() -> None:
    d = _run()
    d[50:52, 1:23] = d[49, 1:23]  # two unchanged rows mid-run: shorter than ``still``
    assert gen.shutdown_time(d) is None


# --------------------------------------------------------------------------- sources and names
def test_output_names() -> None:
    assert gen.output_name("mode1", None, 100, 180) == "tep_mode1.csv"
    assert gen.output_name("mode2", 1234567890, 100, 60) == "tep_mode2_seed1234567890_100h_60s.csv"
    assert gen.output_name("mode3", None, 100, 60, 7) == "tep_mode3_stream7_100h_60s.csv"


def _fake_driver() -> str:
    """The anchors ``_driver_source`` edits, in the layout of temain_mod.f."""
    return (
        "      NPTS = 172800\n"
        "      DO 100 I = 1, 20\n          IDV(I) = 0\n 100  CONTINUE\n"
        "         IF (I.GE.SSPTS) THEN\n                 IDV(12)=1\n          ENDIF\n"
        "      SETPT(14)=6.8820\n      SETPT(15)=18.776\n"
        "\tOPEN(UNIT=111,FILE='~/TE_data_inc.dat',STATUS='new')\n"
        "\tOPEN(UNIT=2121,FILE='~/TE_data_me11.dat',STATUS='new')\n"
        " \tTEST4=MOD(I,180)\t\n\tIF (TEST4.EQ.0) THEN\n\t\tCALL OUTPUT\n"
        "      \t\tWRITE(111,111) I\n 111  \t\tFORMAT(1X,I6)\n     \tENDIF\n"
        " \tCLOSE(UNIT=111)\n\tCLOSE(UNIT=2121)\n"
    )


def test_driver_writes_only_the_csv(tmp_path: Path) -> None:
    (tmp_path / "temain_mod.f").write_text(_fake_driver())
    out = gen._driver_source("mode2", 7.6, 17.6, src_dir=tmp_path, hours=100, record_s=60)
    assert "CALL OUTPUT" not in out  # no per-variable data files (units 1111-2121)
    assert "OPEN(UNIT=111," not in out and "OPEN(UNIT=50,FILE='tepout.csv'" in out
    assert "NPTS = 360000" in out and "MOD(I,60)" in out and "WRITE(50,500)" in out
    assert all(f"IDV({k}) = 1" in out for k in gen.EXCITATION_IDVS)


def test_plant_source_replaces_the_seed_or_the_generator(tmp_path: Path) -> None:
    (tmp_path / "teprob.f").write_text(
        "C  d01: G=1089278833.D0\n" + gen.SEED_LINE + "\n" + gen.TESUB7_SOURCE
    )
    seeded = gen._plant_source(1234567890, src_dir=tmp_path)
    assert "       G=1234567890.D0" in seeded and gen.TESUB7_SOURCE in seeded
    streamed = gen._plant_source(None, stream=3, src_dir=tmp_path)
    assert gen.TESUB7_SOURCE not in streamed and "MRG32k3a" in streamed
    assert all(len(line) <= 72 for line in streamed.splitlines())  # fixed-form Fortran
    assert gen._plant_source(None, src_dir=tmp_path) == (tmp_path / "teprob.f").read_text()
    for bad in (0, -5, 2**53):
        with pytest.raises(ValueError):
            gen._plant_source(bad, src_dir=tmp_path)
    with pytest.raises(ValueError):
        gen._plant_source(5, stream=1, src_dir=tmp_path)


# --------------------------------------------------------------------------- random numbers
def test_mrg32k3a_reference_values_and_jumps() -> None:
    u, state = gen.mrg_uniforms(gen.MRG_DEFAULT, 1000)
    assert u[0] == pytest.approx(0.12701112204657714, abs=1e-16)  # L'Ecuyer (1999), seed 12345
    assert all(0.0 < x < 1.0 for x in u)
    assert gen.mrg_advance(gen.MRG_DEFAULT, 1000) == state  # matrix powers = iteration
    assert gen.mrg_stream_state(2) == gen.mrg_advance(gen.mrg_stream_state(1), 2**127)
    with pytest.raises(ValueError):
        gen.mrg_stream_state(0)


def test_stream_jump_matches_the_rngstreams_constants() -> None:
    # A1^(2^127) mod m1 and A2^(2^127) mod m2 as published with RngStreams (L'Ecuyer et al. 2002)
    a1p127 = (
        (2427906178, 3580155704, 949770784),
        (226153695, 1230515664, 3580155704),
        (1988835001, 986791581, 1230515664),
    )
    a2p127 = (
        (1464411153, 277697599, 1610723613),
        (32183930, 1464411153, 1022607788),
        (2824425944, 32183930, 2093834863),
    )
    assert gen._matpow(gen.MRG_A1, 2**127, gen.MRG_M1) == a1p127
    assert gen._matpow(gen.MRG_A2, 2**127, gen.MRG_M2) == a2p127
    # stream 19 (a chosen mode1 run), as the independent mrg32k3a package gives it
    assert gen.mrg_stream_state(19) == (
        3984477137,
        1267973573,
        3770063761,
        216527865,
        1568537936,
        1200352663,
    )


def test_legacy_generator_settles_into_short_cycles() -> None:
    assert gen.legacy_cycle(4651207995) == (3, 2**27)  # the source's own seed
    assert gen.legacy_cycle(2132432423) == (5, 2**25)
    assert gen.legacy_cycle(1234567890) == (4, 2**26)


# --------------------------------------------------------------------------- qualification rule
def _row(stream: int, trips: dict[str, float | None]) -> dict:
    return {"stream": stream, **{tag: {"shutdown_h": trips.get(tag)} for tag in qual.REGIMES}}


def test_selection_deals_candidates_in_rotation_and_never_shares_a_stream() -> None:
    log = [
        _row(1, {}),  # mode1: qualifies
        _row(2, {"mode2": 30.0}),  # mode2: trips, rejected
        _row(3, {"mode1": 10.0}),  # mode3: qualifies; its mode1 trip is irrelevant
        _row(4, {}),  # mode1: qualifies
        _row(5, {}),  # mode2: qualifies
        _row(6, {}),  # mode3: qualifies
        _row(7, {}),  # mode1: already full, skipped
    ]
    chosen = qual.select(log, per_regime=2)
    assert chosen == {"mode1": [1, 4], "mode2": [5], "mode3": [3, 6]}
    assert not qual.complete(chosen, 2)
    assert qual.complete(qual.select([*log, _row(8, {})], per_regime=2), 2)  # 8 goes to mode2


def _files(tmp_path: Path, stem: str) -> list[Path]:
    return [tmp_path / name for name in (f"te_{stem}.f", f"teprob_{stem}.f", f"te_{stem}")]


def test_run_status_reads_trip_status_and_deletes_every_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gen, "HERE", tmp_path)
    stem = gen.output_name("mode1", None, 100, 60, 7).removesuffix(".csv")

    def fake_generate(tag: str, *, stream: int, hours: int, record_s: int, src_dir: Path) -> Path:
        d = _run(freeze_at=120)
        d[119, 7] = 3000.2  # a noisy reading crosses the limit a row before the freeze
        for f in _files(tmp_path, stem):
            f.write_text("build file")
        path = tmp_path / f"{stem}.csv"
        np.savetxt(path, d, delimiter=",")
        return path

    monkeypatch.setattr(gen, "generate", fake_generate)
    out = qual.run_status("mode1", 7, 100, 60)
    assert out["shutdown_h"] == pytest.approx(120 / 60.0)
    assert out["limit_h"] == pytest.approx(119 / 60.0)
    assert out["pressure_kpa"] < 3000.0  # the frozen row, not the noisy limit row
    assert list(tmp_path.iterdir()) == []


def test_run_status_cleans_up_when_the_run_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gen, "HERE", tmp_path)
    stem = gen.output_name("mode2", None, 100, 60, 3).removesuffix(".csv")

    def failing_generate(
        tag: str, *, stream: int, hours: int, record_s: int, src_dir: Path
    ) -> Path:
        for f in [*_files(tmp_path, stem), tmp_path / "tepout.csv"]:
            f.write_text("partial")
        raise RuntimeError("compiler failed")

    monkeypatch.setattr(gen, "generate", failing_generate)
    with pytest.raises(RuntimeError):
        qual.run_status("mode2", 3, 100, 60)
    assert list(tmp_path.iterdir()) == []


def test_extend_stops_at_the_completing_candidate() -> None:
    rows = [_row(k, {}) for k in range(1, 9)]  # every candidate qualifies
    log: list[dict] = []
    added = qual.extend(log, rows[:4], per_regime=1)  # 1, 2, 3 complete the selection
    assert [r["stream"] for r in added] == [1, 2, 3] and len(log) == 3
    assert qual.extend(log, rows[4:], per_regime=1) == []  # later batches add nothing
    assert qual.select(log, 1) == {"mode1": [1], "mode2": [2], "mode3": [3]}


def test_verify_compares_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in qual.SOURCES:
        (tmp_path / name).write_text("source")
    monkeypatch.setattr(gen, "HERE", tmp_path)
    record = {
        "_meta": {"hours": 100, "record_s": 60},
        "chosen": {"mode1": [1], "mode2": [2], "mode3": [3]},
        "log": [
            {"stream": s, **{t: {"csv_sha256": f"h{s}"} for t in qual.REGIMES}} for s in (1, 2, 3)
        ],
    }

    def fake_status(tag: str, stream: int, hours: int, record_s: int, work: Path) -> dict:
        return {"csv_sha256": f"h{stream}"}

    monkeypatch.setattr(qual, "run_status", fake_status)
    assert qual.verify(record) == 0
    record["log"][1]["mode2"]["csv_sha256"] = "other"
    assert qual.verify(record) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(qual.SOURCES)  # work dir removed
