# N1 as submitted to the Journal of Process Control, 25 November 2026

"When the laboratory is late: dead-time analysis and compensation of conformal soft-sensor
intervals", Bien Don Busico. Manuscript **JPROCONT-D-26-01273**, received by Editorial Manager on
25 November 2026 (13:17 Manila time), handled by Professor Martin Guay.

**Frozen. Do not edit any file in this directory**, including the author block, a typo or a
LaTeX warning: `docs/PAPER_LIFECYCLE.md`, Section 2, rule 1. The publisher's policy allows the
submitted version to be public only as submitted, and it "should not be added to or enhanced in
any way". Corrections belong to the next submitted version, in the private `ipis-papers` repo,
where `paper/` is the working copy.

This is the second JPC submission of Module 1 and a new manuscript, not a revision. Its
predecessor, JPROCONT-D-26-00618 ("When does a calibrated soft sensor keep its promise?"), was
declined in August 2026 after four reviews; its own frozen copy is the parent directory, `paper/`
(submitted 12 June 2026 to CACE as CACE-D-26-00944), and its preprint is public at
doi:10.2139/ssrn.7181724.

## What is here

| Path | Content |
|---|---|
| `main.tex`, `01_introduction.tex` to `07_conclusion.tex`, `abstract.tex`, `supplement.tex`, `references.bib` | the LaTeX master the submission was built from (elsarticle, 5p, 12 pages) |
| `highlights.md` | the five highlights |
| `submission_v1/` | the files uploaded to Editorial Manager: `N1_manuscript.docx` (28 pages, double spaced, line numbers, Word equations, figures and tables in the text), `N1_supplementary_material.docx`, `N1_highlights.docx`, `Fig1.png` to `Fig6.png` (600 dpi), and the three supplementary CSV files |
| `submission_v1/MD5SUMS.txt` | the digests of every uploaded file, as uploaded |

The Word files were generated from the LaTeX master by `scripts/n1_make_docx.py` in the private
repo, and checked against the LaTeX build word by word.

## What is deliberately not here

- `N1_cover_letter.docx` and its markdown source. The letter is correspondence: it names the
  journal's editors and recounts a presubmission exchange. It stays in the private repo with the
  rest of the correspondence. `MD5SUMS.txt` still lists its digest, so the uploaded set remains
  verifiable.
- The presubmission inquiry, the submission sheet with the Editorial Manager form answers, and
  the working outline. Private repo, `paper/`.
- The evidence, the code and the 15 Tennessee Eastman runs. They are public already: this
  repository holds the code and the records, and the deposit at
  [doi:10.5281/zenodo.24357752](https://doi.org/10.5281/zenodo.24357752) archives the study's
  files at tag `n1-jpc-submission` together with the runs.

## Reproducing the numbers

Nothing in this directory is needed to reproduce the study. `docs/module1/PHASE1_RUNNER.md` gives
the run commands, `docs/module1/PHASE1_PREREGISTRATION.md` (frozen at tag `n1-phase1-freeze`,
29 October 2026) is the protocol, and `python -m scripts.paper_n1.make_all` rewrites every figure
and table in `docs/paper/figures/n1/` from the records in `docs/paper/evidence/`.
