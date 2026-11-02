"""Datasets, arms and segments of N1 Phase 1 (pre-registration Sections 5.1 and 5.2).

Debutanizer (Section 5.1): the public Fortuna et al. (2007) file, split in time order 70 / 15 / 15
(``time_ordered_split``): training rows 0-1674, then validation and test rows 1675-2393, the
evaluation stream. Stage A parses the training rows only.

TEP (Section 5.2): the 15 runs the qualification chose (``docs/paper/evidence/
tep_seed_qualification.json``), 100 h each, recorded every 60 s by ``generate_tep_modes.py
--streams`` (6000 rows: time, XMEAS 1-41, XMV 1-12; no header).
- Row i (from 0) is written at simulation second 60 (i + 1), its nominal minute i + 1. The
  driver writes it before that second's integration step, so its time column reads
  (60 (i + 1) - 1) s, in hours to five decimals. Segments use the nominal minute.
- The product analyzer updates XMEAS(40) at whole multiples of 0.25 h with the composition
  captured 0.25 h earlier (``teprob.f``, the TPROD block). The update happens in the integration
  step after the row written at that instant, so a new value first appears at minute 15k + 1 and
  is held for 15 rows (checked on a run of the extended generator, 2026-10-29).
The arms:
- T1, data cadence: the rows at whole multiples of 3 min (i = 2, 5, 8, ...; 2000 rows), the rows
  a 180-s recording writes. A new analyzer value first appears at T1 row j = 5k (minute 15k + 3)
  and is held for rows 5k to 5k + 4;
- T2, execution cadence: every 60-s row (6000 rows), held in blocks of 15;
- T3, event cadence: the T1 rows at which a new analyzer value appears, j = 5, 10, 15, ...
  (``t3_rows``). It uses the T1 point model's residuals at those rows.
Segments within a run, by nominal minute: training (0, 1800], calibration (1800, 4200] and
evaluation (4200, 6000], that is hours (0, 30], (30, 70] and (70, 100]. Stage A parses only the
rows up to 70 h (``max_rows``), so the evaluation rows of a run are never read before stage B.

Every TEP file is checked against the SHA-256 the qualification record holds for it before use.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ALPHA = 0.10  # 90 % intervals
EPS = 0.01  # the budget on the uninformative share (D-P1.5)
WINDOW = 200  # conformal window, and the seed rows of every replay (Section 5.3)

# Debutanizer (Section 5.1)
DEBUT_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")
DEBUT_LAG = 15  # D-P0.1: OLS of y_t on u5_{t-15}; the lag is in debutanizer_lag_scan.json
DEBUT_THETAS = (0, 1, 3, 7, 12)
DEBUT_PRIMARY = 3  # theta_doc (D-P1.2)
DEBUT_SECONDARY = 7
DEBUT_N_EV = 719  # validation plus test rows, 1675-2393

# TEP (Section 5.2)
TEP_DIR = Path("data/raw/tep/phase1")
TEP_RECORD = Path("docs/paper/evidence/tep_seed_qualification.json")
REGIMES = ("mode1", "mode2", "mode3")
TEP_ROWS_60S = 6000  # 100 h of 60-s rows
TEP_ROWS_STAGE_A = 4200  # the 60-s rows up to 70 h
TEP_COLUMNS = 54  # time, XMEAS 1-41, XMV 1-12
TEP_Y_COLUMN = 40  # XMEAS(40), G in the product (Downs and Vogel 1993, Table 5)
TEP_INPUT_COLUMNS = tuple(range(1, 23)) + tuple(range(42, 54))  # XMEAS 1-22 and XMV 1-12
TRAIN_END_MIN, CAL_END_MIN = 1800, 4200  # 30 h and 70 h
ANALYZER_MIN = 15  # XMEAS(40) sampling interval, 0.25 h
TIME_TOL_H = 2e-5  # the time column has five decimals of an hour


@dataclass(frozen=True)
class Arm:
    """One TEP arm: which 60-s rows it keeps, the label age in its rows, its dead times."""

    name: str
    stride: int  # keep the 60-s rows i with (i + 1) % stride == 0
    lag: int  # label age in the arm's rows: the inputs are lagged by it (D-P1.3)
    thetas: tuple[int, ...]
    primary: int
    window: int


ARMS = {
    "T1": Arm("T1", stride=3, lag=5, thetas=(0, 2, 4), primary=4, window=WINDOW),
    "T2": Arm("T2", stride=1, lag=15, thetas=(0, 4, 14), primary=14, window=WINDOW),
    # T3 keeps the T1 rows where a new analyzer value appears and uses the T1 point model. Its
    # window is 40 events, the 10 h that T1's 200 rows span: at the event cadence the calibration
    # hours hold only 160 labels (deviation 1, PHASE1_PREREGISTRATION Section 10).
    "T3": Arm("T3", stride=15, lag=5, thetas=(0,), primary=0, window=40),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tep_expected(record_path: Path = TEP_RECORD) -> dict[tuple[str, int], str]:
    """(regime, stream) -> SHA-256 of the run's CSV, for the 15 runs the record chose."""
    record = json.loads(Path(record_path).read_text())
    meta = record["_meta"]
    if (meta["hours"], meta["record_s"]) != (100, 60):
        raise ValueError("the record is not of 100-h runs recorded every 60 s")
    rows = {row["stream"]: row for row in record["log"]}
    out = {}
    for regime in REGIMES:
        streams = record["chosen"][regime]
        if len(streams) != 5:
            raise ValueError(f"{regime}: the record chose {len(streams)} runs, not 5")
        for stream in streams:
            out[(regime, int(stream))] = rows[stream][regime]["csv_sha256"]
    return out


def tep_file_name(regime: str, stream: int) -> str:
    """The generator's name for a run (``generate_tep_modes.output_name``)."""
    return f"tep_{regime}_stream{stream}_100h_60s.csv"


@dataclass(frozen=True)
class TepFile:
    regime: str
    stream: int
    path: Path
    sha256: str


def tep_files(data_dir: Path = TEP_DIR, record_path: Path = TEP_RECORD) -> list[TepFile]:
    """The 15 runs in regime order, each checked against the record's SHA-256."""
    files = []
    for (regime, stream), want in tep_expected(record_path).items():
        path = Path(data_dir) / tep_file_name(regime, stream)
        if not path.exists():
            raise FileNotFoundError(f"missing TEP run {path} (step 5: tep_phase1_runs.py)")
        got = sha256_file(path)
        if got != want:
            raise ValueError(f"{path.name}: SHA-256 {got} differs from the record's {want}")
        files.append(TepFile(regime, stream, path, got))
    return files


def tep_time_column(n: int) -> np.ndarray:
    """The time column the generator writes for rows 0..n-1: (60 (i + 1) - 1) s, in hours."""
    return (60.0 * (np.arange(n) + 1.0) - 1.0) / 3600.0


def load_tep_rows(path: Path, stage: str) -> np.ndarray:
    """The 60-s rows of one run: the first 4200 (up to 70 h) in stage A, all 6000 in stage B."""
    if stage not in ("A", "B"):
        raise ValueError("stage is 'A' or 'B'")
    n = TEP_ROWS_STAGE_A if stage == "A" else TEP_ROWS_60S
    d = np.loadtxt(path, delimiter=",", max_rows=n)
    if d.shape != (n, TEP_COLUMNS):
        raise ValueError(f"{Path(path).name}: shape {d.shape}, expected {(n, TEP_COLUMNS)}")
    if np.max(np.abs(d[:, 0] - tep_time_column(n))) > TIME_TOL_H:
        raise ValueError(f"{Path(path).name}: the time column is not the generator's 60-s grid")
    return d


@dataclass(frozen=True)
class ArmRows:
    """One run's rows in one arm: nominal minute, the label y = XMEAS(40) and the 34 inputs."""

    minute: np.ndarray
    y: np.ndarray
    X: np.ndarray
    n_train: int
    n_cal: int
    n_ev: int  # 0 in stage A


def segment_sizes(minute: np.ndarray) -> tuple[int, int, int]:
    """Rows in the training (0, 30], calibration (30, 70] and evaluation (70, 100] hours."""
    n_train = int(np.sum(minute <= TRAIN_END_MIN))
    n_cal = int(np.sum((minute > TRAIN_END_MIN) & (minute <= CAL_END_MIN)))
    n_ev = int(np.sum(minute > CAL_END_MIN))
    return n_train, n_cal, n_ev


def arm_rows(d60: np.ndarray, arm: Arm) -> ArmRows:
    """Select an arm's rows from the 60-s rows. T3 is built from T1 (``t3_rows``)."""
    if arm.name == "T3":
        raise ValueError("T3 is built from the T1 residuals (t3_rows)")
    minute = np.arange(1, d60.shape[0] + 1)
    keep = minute % arm.stride == 0
    d = d60[keep]
    n_train, n_cal, n_ev = segment_sizes(minute[keep])
    return ArmRows(
        minute=minute[keep],
        y=d[:, TEP_Y_COLUMN].copy(),
        X=d[:, list(TEP_INPUT_COLUMNS)].copy(),
        n_train=n_train,
        n_cal=n_cal,
        n_ev=n_ev,
    )


def label_hold(rows: ArmRows) -> dict[str, float | int]:
    """Check that the label is held in blocks of 15 min that start one row after each analyzer
    instant (minute 15k + 1 at 60 s, T1 row 5k at 3 min): constant within every block, and the
    share of blocks whose value differs from the previous block's. Raises if a block is not
    constant, which would mean the analyzer's phase is not the one ``t3_rows`` assumes."""
    step = int(rows.minute[1] - rows.minute[0])
    if ANALYZER_MIN % step or not np.all(np.diff(rows.minute) == step):
        raise ValueError("the arm's rows must be evenly spaced at an interval dividing 15 min")
    per = ANALYZER_MIN // step
    starts = np.flatnonzero((rows.minute - step) % ANALYZER_MIN == 0)  # minute 15k + step
    if not starts.size:
        raise ValueError("no row starts a 15-min block")
    first = int(starts[0])
    n = (rows.y.size - first) // per
    blocks = rows.y[first : first + n * per].reshape(n, per)
    constant = blocks == blocks[:, :1]
    if not np.all(constant):
        raise ValueError("the label is not held in the expected 15-min blocks")
    changed = blocks[1:, 0] != blocks[:-1, 0]
    return {
        "rows_per_block": int(per),
        "first_block_row": first,
        "blocks": int(n),
        "share_new_value_at_block_start": float(changed.mean()) if changed.size else 1.0,
    }


def t3_rows(t1_minute: np.ndarray) -> np.ndarray:
    """Indices of the T1 rows where a new analyzer value appears: minute 15k + 3 (k >= 1), that
    is j = 5, 10, 15, ... The row j = 0 holds the initial value, not a new one."""
    j = np.arange(t1_minute.size)
    idx = j[(t1_minute % ANALYZER_MIN == 3) & (t1_minute > ANALYZER_MIN)]
    if not np.array_equal(idx, np.arange(5, t1_minute.size, 5)):
        raise ValueError("the T1 rows are not the 3-min grid from minute 3")
    return idx


@dataclass(frozen=True)
class DebutanizerRows:
    """The debutanizer's u5 and y: the training rows, then, in stage B, the evaluation rows."""

    u5: np.ndarray
    y: np.ndarray
    n_train: int
    n_ev: int  # 0 in stage A


TRAIN_FRAC = 0.70  # time_ordered_split's training share


def _debutanizer_training_rows(path: Path) -> tuple[Any, int]:
    """Stage A: the training rows, parsed alone. The file's data rows are counted (as lines, none
    of their values parsed), the first 70 % are parsed by the loader's parser, and the rest are
    never parsed, so that no value of an evaluation row can reach stage A."""
    from io import StringIO

    import pandas as pd

    from ipis.module1_soft_sensor.data.loaders import (
        DEBUTANIZER_COLUMNS,
        DEBUTANIZER_N_COLUMNS,
        _find_data_start,
    )

    start = _find_data_start(Path(path), DEBUTANIZER_N_COLUMNS)
    with open(path) as f:
        lines = [line for i, line in enumerate(f) if i >= start and line.strip()]
    n_train = int(len(lines) * TRAIN_FRAC)
    df = pd.read_csv(
        StringIO("".join(lines[:n_train])),
        sep=r"\s+",
        names=DEBUTANIZER_COLUMNS,
        engine="python",
    )
    if df.shape != (n_train, DEBUTANIZER_N_COLUMNS) or df.isna().any().any():
        raise ValueError("the debutanizer training rows do not parse as 8 numeric columns")
    return df, len(lines)


def load_debutanizer(path: Path, stage: str) -> DebutanizerRows:
    """Training rows 0-1674 (stage A), or all 2394 rows (stage B), in time order.

    Stage B loads the file as ``scripts/phase1_precheck.py`` does (``DebutanizerLoader``, then
    ``time_ordered_split``). Stage A parses only the training rows
    (``_debutanizer_training_rows``); stage B checks that its training rows give stage A's
    residuals bit for bit.
    """
    from ipis.module1_soft_sensor.data.loaders import DebutanizerLoader
    from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split

    if stage not in ("A", "B"):
        raise ValueError("stage is 'A' or 'B'")
    if stage == "A":
        tr, n_rows = _debutanizer_training_rows(Path(path))
        if n_rows - len(tr) != DEBUT_N_EV:
            raise ValueError(f"the file holds {n_rows} data rows; the design needs 2394")
        return DebutanizerRows(
            u5=tr["u5"].to_numpy(float), y=tr["y"].to_numpy(float), n_train=len(tr), n_ev=0
        )
    split = time_ordered_split(DebutanizerLoader().load(Path(path)), train_frac=TRAIN_FRAC)
    tr = split.train
    ev_u5 = np.concatenate([split.val["u5"].to_numpy(float), split.test["u5"].to_numpy(float)])
    ev_y = np.concatenate([split.val["y"].to_numpy(float), split.test["y"].to_numpy(float)])
    if ev_y.size != DEBUT_N_EV:
        raise ValueError(f"the evaluation stream has {ev_y.size} rows, not {DEBUT_N_EV}")
    return DebutanizerRows(
        u5=np.concatenate([tr["u5"].to_numpy(float), ev_u5]),
        y=np.concatenate([tr["y"].to_numpy(float), ev_y]),
        n_train=len(tr),
        n_ev=int(ev_y.size),
    )
