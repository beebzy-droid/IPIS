# FEMTO-PRONOSTIA (IEEE PHM 2012) — acquisition note

**Role:** Module 2 **primary** dataset (health index + RUL). See `docs/module2/spec.md`
(D2) and ADR-015.

**This directory is gitignored** (`data/raw/*`). Only this README is tracked. The raw
data is reproduced locally per the steps below; it is never committed.

## Source

- Repository: https://github.com/wkzs111/phm-ieee-2012-data-challenge-dataset
- Dataset paper (Tier-1, in project library): Nectoux et al. (2012), *PRONOSTIA: An
  experimental platform for bearings accelerated degradation tests*, IEEE Int. Conf. on PHM.

## Download (Windows cmd)

```cmd
cd %USERPROFILE%\Downloads
git clone https://github.com/wkzs111/phm-ieee-2012-data-challenge-dataset.git
```
(or browser → Code → Download ZIP → extract). Then:
```cmd
cd Projects\IPIS
mkdir data\raw\femto
xcopy /E /I "%USERPROFILE%\Downloads\phm-ieee-2012-data-challenge-dataset\Learning_set"  "data\raw\femto\Learning_set"
xcopy /E /I "%USERPROFILE%\Downloads\phm-ieee-2012-data-challenge-dataset\Test_set"       "data\raw\femto\Test_set"
xcopy /E /I "%USERPROFILE%\Downloads\phm-ieee-2012-data-challenge-dataset\Full_Test_Set"  "data\raw\femto\Full_Test_Set"
```

## Validated structure (confirmed in-sandbox 2026-06-16)

```
data/raw/femto/
  Learning_set/    6 bearings  : Bearing1_1, 1_2, 2_1, 2_2, 3_1, 3_2   (training)
  Test_set/        11 bearings : truncated runs (challenge test inputs)
  Full_Test_Set/   11 bearings : full run-to-failure (RUL ground truth)
```

- Operating conditions: cond 1 = 1800 rpm / 4000 N (Bearing1_*); cond 2 = 1650 rpm /
  4200 N (Bearing2_*); cond 3 = 1500 rpm / 5000 N (Bearing3_*).
- Per bearing: a time-ordered sequence of `acc_NNNNN.csv` snapshots, recorded every 10 s.
- Each `acc_*.csv`: **2560 rows × 6 columns**, no header =
  `hour, minute, second, 0.1ms_tick, accel_horizontal_g, accel_vertical_g`.
  2560 samples = 25.6 kHz × 0.1 s snapshot.
- `temp_*.csv` files exist for some bearings (sparse, ~10 Hz) — optional, not used by the
  baseline pipeline.
- End-of-life: experiment stopped when vibration amplitude exceeds **20 g**; the snapshot
  count to that point defines true RUL.
- Bundled in the repo root: `IEEEPHM2012-Challenge-Details.pdf` (the official challenge
  document) and `README.md`.

## Integrity check (match these)

- `Learning_set` = 6 folders; `Test_set` = 11; `Full_Test_Set` = 11.
- `Bearing1_1` contains 2803 `acc_*.csv` files.
- Any `acc_*.csv` has exactly 2560 lines.

## Split (IEEE PHM 2012 convention)

Train on the 6 `Learning_set` bearings (2 per condition); predict RUL for the 11 test
bearings. RUL ground truth comes from `Full_Test_Set`. Headline metric = PHM-2012 Score
(asymmetric; see `docs/module2/spec.md` D5).
