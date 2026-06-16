# IPIS — Project structure

A one-page map of the repository. For *why* things are the way they are and what to do
next, read `docs/HANDOFF.md` (§0.5 is the live resume pointer).

**IPIS (Integrated Process Intelligence System)** — a hybrid, digital-twin-backed framework
on a first-principles physics layer, in three modules: **Module 1 — Soft Sensor** (complete;
paper under review, CACE-D-26-00944), **Module 2 — Predictive Maintenance** (next), and
**Module 3 — Real-Time Optimization** (complete; paper under review, JPROCONT-D-26-00565).

```
IPIS/
├── README.md                     Project overview + status table + publications
├── LICENSE
├── pyproject.toml                Package config, deps, ruff/black settings (src layout)
├── requirements-serving.txt      Lean runtime deps for the serving Docker image
├── Dockerfile  .dockerignore     Serving image (Module 1 FastAPI)
├── .pre-commit-config.yaml       black + ruff hooks
├── .gitignore  .env.example      Repo-wide ignores (data, secrets, models, LaTeX aux)
│
├── src/ipis/                     The package (importable; PYTHONPATH=src)
│   ├── module1_soft_sensor/      Soft sensor: physics features, blocked CV, drift +
│   │   │                           Shardt bias-update, conformal (ACI/EnbPI/split),
│   │   │                           migration (OSBC/Luo/Yan), FastAPI/Streamlit serving
│   │   ├── evaluation/  features/  physics_bridge/  migration/  data/  serving/
│   ├── module3_rto/              RTO: economics, column_model, rto_nlp, surrogate,
│   │                               rto_surface, chance_rto (conformal back-offs)
│   └── shared/                   config, state_bus (cross-module wiring)
│
├── tests/                        unit/ + integration/ (~280 tests; CI runs these)
│
├── scripts/                      Runnable analyses & pipelines (NOT CI-tested)
│   ├── paper_figures/            Paper 1 figure emitters (frozen-evidence → figures)
│   ├── paper2_figures/           Paper 2 figure emitters (regime map, schematics)
│   └── run_*, validate_*, tep_*, secom_*, diagnose_*, …
│
├── paper/                        PAPER 1 submission (elsarticle) — house standard
│   ├── main.tex  abstract.tex  01_intro.tex … 07_conclusion.tex
│   ├── references.bib  highlights.md  cover_letter.md  .gitignore
│
├── paper2/                       PAPER 2 submission — mirrors paper/ exactly
│   ├── main.tex  abstract.tex  01_intro.tex … 07_conclusion.tex
│   ├── references.bib  highlights.md  cover_letter.md  .gitignore
│
├── docs/
│   ├── HANDOFF.md                Single source of truth for resuming work (read first)
│   ├── architecture/
│   │   ├── system-overview.md
│   │   └── decisions/            ADRs 001–006 (bare) + ADR-007…014 (prefixed) + TEMPLATE
│   ├── module1/                  spec, results, lessons-learned
│   ├── module3/                  twin spec, walkthroughs, results, scoping, literature
│   │   └── paper/                Paper 2 working copy: outline, claims, sections/,
│   │                               evidence/ (frozen regime_map.json), figures/ (F1–F7)
│   ├── paper/                    Paper 1 working copy: outline, claims, sections/,
│   │                               evidence/, figures/
│   └── sources/source-map.md     Tier-0/1 reference index (verify-before-load-bearing)
│
├── configs/                      Hydra configs
├── data/                         raw/{debutanizer,tep,secom} — contents gitignored,
│                                   .gitkeep tracked; partner/confidential never committed
├── models/                       fixture bundle tracked; checkpoints/production gitignored
├── notebooks/   docker/          exploration; docker-compose dev stack
└── .github/workflows/            ci.yml (lint + unit tests) + docker-build.yml
```

## Conventions

- **Source layout** `src=["src"]`; conda env `ipis` (Python 3.11). Quality gates before every
  commit: `black src tests scripts`, `ruff check src tests`, `pytest tests/unit -q`. CI lints
  `src tests` and runs unit tests; `scripts/` are not CI-tested (they need gitignored data).
- **Two papers, two layouts each.** `paper/` and `paper2/` hold the LaTeX submission packages
  (identical structure). The markdown working copies, figures, and frozen evidence live under
  `docs/paper/` and `docs/module3/paper/`. LaTeX `\graphicspath` points at the `docs/.../figures/`.
- **ADRs** are the decision log: bare `001`–`006`, prefixed `ADR-007`…`ADR-014`; next id is **015**.
- **Never committed:** dataset contents, model checkpoints, secrets/`.env`, `tennessee-eastman-dataset/`,
  LaTeX build artifacts. See `.gitignore`.
- **Discipline:** verify every load-bearing number against a primary source at the moment of use;
  deliberate at option-scale before writing code; lead with quantified results.
```
