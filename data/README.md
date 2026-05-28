# Data Directory

This directory holds all datasets. **Contents are gitignored** — datasets must be downloaded locally.

## Structure

```
data/
├── raw/          ← Untouched downloads, never modified
│   ├── debutanizer/
│   ├── tep/
│   └── secom/
├── interim/      ← Cleaned but not yet feature-engineered
├── processed/    ← Model-ready (train/val/test splits)
└── external/     ← Industrial partner data (e.g., Coca-Cola)
                    ALWAYS gitignored, no exceptions
```

## Datasets

### 1. Debutanizer Column (Primary)

- **Source:** Fortuna, Graziani, Rizzo, Xibilia (2007), *Soft Sensors for Monitoring and Control of Industrial Processes*
- **Size:** 2,205 hourly samples, 7 input variables, 1 quality output (C4 bottom composition)
- **Origin:** Real French refinery
- **License:** Academic use
- **Download:** Mirrors available via DTU, ResearchGate, and several UCI archives
- **Save to:** `data/raw/debutanizer/`

### 2. Tennessee Eastman Process (Secondary)

- **Source:** Downs & Vogel (1993), *A plant-wide industrial process control problem*, Computers & Chemical Engineering
- **Size:** 52 measurements, 41 manipulated variables, 21 fault types
- **Origin:** Simulated chemical plant benchmark
- **License:** Public domain
- **Download:** [github.com/camaramm/tennessee-eastman-profBraatz](https://github.com/camaramm/tennessee-eastman-profBraatz)
- **Save to:** `data/raw/tep/`

### 3. SECOM (Supplementary)

- **Source:** UCI Machine Learning Repository
- **Size:** 1,567 samples, 590 features, binary pass/fail
- **Origin:** Real semiconductor manufacturing fab
- **License:** UCI ML Repository terms
- **Download:** [archive.ics.uci.edu/ml/datasets/SECOM](https://archive.ics.uci.edu/ml/datasets/SECOM)
- **Save to:** `data/raw/secom/`

## Automated download

Use the provided script:

```bash
python scripts/download_datasets.py --all
# or selectively:
python scripts/download_datasets.py --dataset debutanizer
python scripts/download_datasets.py --dataset tep
python scripts/download_datasets.py --dataset secom
```

## Industrial partner data

If industrial partner data is acquired (e.g., anonymized Coca-Cola carbonation data):

- **Save to:** `data/external/`
- **Never commit** — `.gitignore` excludes this directory entirely
- **Document the dataset** in a private `data/external/README.partner.md` (also gitignored)
- **Encrypt at rest** if storing on a shared machine

## Data hygiene rules

1. **Never modify `raw/`** — it is the source of truth. All transformations live in `interim/` or `processed/`.
2. **Document every transformation** — preprocessing steps must be reproducible from raw data via a documented pipeline.
3. **Version your splits** — train/val/test splits go in `processed/` with a manifest file listing sample IDs.
4. **Never commit large files** — anything >5 MB is questioned by the pre-commit hook.
