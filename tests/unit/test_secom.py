"""Tests for the SECOM loader + screening + VM target selection (Phase 1E.1).

Data-free: a small synthetic dataset in the exact UCI SECOM file format (space-
separated features with literal ``NaN`` tokens; ``label "dd/mm/yyyy HH:MM:SS"`` with the
quoted datetime) is written to tmp_path, with planted pathologies the screen and the
target selector must find.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ipis.module1_soft_sensor.data.secom_loader import (
    N_FEATURES,
    SECOMLoader,
    select_vm_target,
    unsupervised_screen,
)

N_ROWS = 120


@pytest.fixture
def secom_files(tmp_path):
    """Synthetic SECOM-format files with planted structure.

    - x0: heavily missing (60%)            -> screen must drop (missingness)
    - x1: constant                          -> screen must drop (near-zero variance)
    - x2: strongly fail-associated          -> select_vm_target must pick
    - x3: weakly associated, 2% missing     -> a normal survivor
    - x4..: noise
    Timestamps are monotonic with one duplicated stamp (the canonical file has 33).
    """
    rng = np.random.default_rng(42)
    fail = rng.random(N_ROWS) < 0.25
    x = rng.normal(0.0, 1.0, (N_ROWS, N_FEATURES))
    x[:, 1] = 7.0  # constant
    x[:, 2] = 3.0 * fail.astype(float) + rng.normal(0.0, 0.3, N_ROWS)  # strong signal
    x[:, 3] = 0.3 * fail.astype(float) + rng.normal(0.0, 1.0, N_ROWS)  # weak signal
    miss0 = rng.random(N_ROWS) < 0.60
    x[miss0, 0] = np.nan
    x[rng.random(N_ROWS) < 0.02, 3] = np.nan

    def fmt(v: float) -> str:
        return "NaN" if np.isnan(v) else f"{v:.4f}"

    feat_lines = [" ".join(fmt(v) for v in row) for row in x]
    (tmp_path / "secom.data").write_text("\n".join(feat_lines) + "\n")

    t0 = pd.Timestamp("2008-07-19 11:55:00")
    stamps = [t0 + pd.Timedelta(minutes=30 * i) for i in range(N_ROWS)]
    stamps[10] = stamps[9]  # duplicate timestamp, order preserved
    lab_lines = [
        f"{1 if f else -1} \"{ts.strftime('%d/%m/%Y %H:%M:%S')}\""
        for f, ts in zip(fail, stamps, strict=True)
    ]
    (tmp_path / "secom_labels.data").write_text("\n".join(lab_lines) + "\n")
    return tmp_path / "secom.data", tmp_path / "secom_labels.data", fail


# --------------------------------------------------------------------------- #
# loader                                                                      #
# --------------------------------------------------------------------------- #
def test_loader_shape_and_columns(secom_files):
    fp, lp, fail = secom_files
    df = SECOMLoader().load(fp, lp)
    assert df.shape == (N_ROWS, N_FEATURES + 2)  # features + fail + timestamp
    assert df["fail"].sum() == fail.sum()
    assert df["fail"].dtype == bool


def test_loader_parses_quoted_timestamps_and_keeps_order(secom_files):
    fp, lp, _ = secom_files
    df = SECOMLoader().load(fp, lp)
    ts = df["timestamp"]
    assert ts.notna().all()
    assert bool(ts.is_monotonic_increasing)  # duplicates allowed, order preserved
    assert (ts == ts.iloc[10]).sum() == 2  # the planted duplicate survived


def test_loader_rejects_wrong_width(tmp_path, secom_files):
    _, lp, _ = secom_files
    bad = tmp_path / "bad.data"
    bad.write_text("1.0 2.0 3.0\n" * N_ROWS)
    with pytest.raises(ValueError, match="feature columns"):
        SECOMLoader().load(bad, lp)


def test_loader_rejects_row_mismatch(tmp_path, secom_files):
    fp, _, _ = secom_files
    bad = tmp_path / "bad_labels.data"
    bad.write_text('-1 "19/07/2008 11:55:00"\n')
    with pytest.raises(ValueError, match="label rows"):
        SECOMLoader().load(fp, bad)


# --------------------------------------------------------------------------- #
# unsupervised screen                                                         #
# --------------------------------------------------------------------------- #
def test_screen_drops_planted_pathologies(secom_files):
    fp, lp, _ = secom_files
    df = SECOMLoader().load(fp, lp)
    res = unsupervised_screen(df)
    assert "x0" in res.dropped_missing  # 60% missing
    assert "x1" in res.dropped_constant  # constant
    assert "x2" in res.kept and "x3" in res.kept
    assert "fail" not in res.kept and "timestamp" not in res.kept


def test_screen_is_label_free(secom_files):
    fp, lp, _ = secom_files
    df = SECOMLoader().load(fp, lp)
    shuffled = df.copy()
    shuffled["fail"] = np.random.default_rng(0).permutation(shuffled["fail"].to_numpy())
    a = unsupervised_screen(df)
    b = unsupervised_screen(shuffled)
    assert a.kept == b.kept  # identical regardless of the label


# --------------------------------------------------------------------------- #
# VM target selection                                                         #
# --------------------------------------------------------------------------- #
def test_target_selection_picks_planted_signal(secom_files):
    fp, lp, _ = secom_files
    df = SECOMLoader().load(fp, lp)
    res = unsupervised_screen(df)
    sel = select_vm_target(df, res.kept)
    assert sel.target == "x2"  # the strongly fail-associated measurement
    assert {"feature", "missing_frac", "std", "abs_r_fail"} <= set(sel.audit.columns)
    assert sel.audit["abs_r_fail"].is_monotonic_decreasing


def test_target_selection_respects_missingness_gate(secom_files):
    fp, lp, _ = secom_files
    df = SECOMLoader().load(fp, lp)
    res = unsupervised_screen(df)
    # gate tighter than x3's 2% missingness: x3 must vanish from the audit
    sel = select_vm_target(df, res.kept, max_missing=0.01)
    assert "x3" not in sel.audit["feature"].tolist()
    assert sel.target == "x2"


def test_target_selection_raises_when_no_candidate(secom_files):
    fp, lp, _ = secom_files
    df = SECOMLoader().load(fp, lp)
    with pytest.raises(ValueError, match="no candidate"):
        select_vm_target(df, ["x0"])  # only the 60%-missing column offered
