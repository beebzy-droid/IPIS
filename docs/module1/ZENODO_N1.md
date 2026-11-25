# N1: the Zenodo deposit of the evidence

Status, 2026-11-25: built by Bien from tag `n1-jpc-submission` (commit 13f602f); DOI
**10.5281/zenodo.24357752** reserved and the record published. The first build archived the whole
repository, other modules and papers included; its files are replaced by the N1-only build within
Zenodo's period for editing a published record's files, so the DOI does not change (Section 5).
The manuscript cites the deposit as a dataset (`busico2026data`, in the private manuscript's
bibliography, with the DOI), and its Data and code availability statement points to it.

## 1. What is deposited

Four files, written by `scripts/paper_n1/zenodo_package.py` to `dist/zenodo/` (gitignored):

| File | Content | Size (expected) |
|---|---|---|
| `IPIS-<tag>.zip` | `git archive` of the tagged commit, limited to the N1 study's files (`N1_PATHS` in the script): code and tests, pre-registration and decision record, runner records, evidence (`docs/paper/evidence/phase1_*.json` and the pilots' records), figure and table generators, figures and the supplementary tables. The other modules and papers stay on GitHub | 3.4 MB, 161 files (the whole repository: 11.0 MB, 624 files) |
| `tep_phase1_runs.zip` | The 15 Tennessee Eastman runs of the study, each checked first against the SHA-256 in `docs/paper/evidence/tep_seed_qualification.json`, with `SHA256SUMS.txt` | tens of MB |
| `README.md` | What the deposit holds, how to reproduce the study, the debutanizer source and digest, licences, and the archived paths | 9 kB |
| `SHA256SUMS.txt` | Digests of the three files above | |

Not deposited: the debutanizer data (Fortuna et al. 2007; redistribution not cleared). The README
gives its source and the SHA-256 of the file the study read
(`03ce599a6bac1239558cb475f6e81a26e431981ac7ece3c1825c7bdaf53471d8`).

## 2. Order of work

1. Commit the N1 bundle (the supplement generator, its tables, this file) and push.
2. Tag the commit `n1-jpc-submission` and push the tag. The tag fixes what the deposit archives;
   the deposit is built from the tag, not from the working tree.
3. Build the deposit on the machine that holds the 15 runs in `data\raw\tep\phase1`:
   `set PYTHONPATH=src`, then `python -m scripts.paper_n1.zenodo_package --tag n1-jpc-submission`.
   It stops if a run's SHA-256 differs from the record.
4. Upload to Zenodo and reserve the DOI (Section 3). Send the DOI to the N1 session.
5. The DOI goes into the manuscript; the final PDF is built and checked.
6. Publish the Zenodo record before the manuscript is submitted, so that the DOI resolves for the
   editor and the reviewers. Within 30 days of publication the owner can still change the
   record's files ("Edit", then "Edit published files"; the draft must be published within 45
   days of the first publication, and the DOI does not change). After that, a correction becomes
   a new version with its own DOI.

## 3. Zenodo, step by step (zenodo.org, signed in with ORCID or GitHub)

1. "New upload".
2. Files: drag in the four files from `dist\zenodo`.
3. "Digital Object Identifier": answer "No" to "Do you already have a DOI?", then "Get a DOI now!".
   Copy the reserved DOI (`10.5281/zenodo.` followed by digits).
4. Resource type: Dataset.
5. Title: `Evidence, code and pre-registration for "When the laboratory is late: dead-time analysis and compensation of conformal soft-sensor intervals"`.
6. Creators: Busico, Bien Don; ORCID 0009-0006-7755-2470; affiliation University of the
   Philippines Diliman.
7. Description (paste):

   > Evidence, code and pre-registration of a study of adaptive conformal prediction intervals
   > for soft sensors whose laboratory or analyzer labels arrive late. The study analyses the
   > interval calibrator as an integral loop with dead time and tests two remedies, tuning the
   > step by replaying past residuals through the delayed loop and compensating the predictable
   > residual over the dead time, on 15 Tennessee Eastman runs and the debutanizer data. The
   > protocol was frozen at tag n1-phase1-freeze (29 October 2026) of the IPIS repository before
   > any result of the study existed. The deposit holds the study's files of the repository at the
   > submission tag (code and tests, pre-registration, the records of both stages of the run, the
   > pilots' records, figure and table generators, figures) and the 15 simulated Tennessee
   > Eastman runs; README.md explains how to reproduce the study and lists the archived paths.
   > The repository's other modules and papers are not part of the study and are not included.
   > The debutanizer data are not redistributed (Fortuna et al., Soft Sensors for Monitoring and
   > Control of Industrial Processes, Springer, 2007). Files revised on 25 November 2026: the
   > first upload archived the whole repository.

8. Licences (Rights): Creative Commons Attribution 4.0 International, for the simulated runs; add
   MIT for the repository archive, code and documents (the repository's `LICENSE`), as `README.md`
   states. If the form takes only one, choose CC BY 4.0: `README.md` states the archive's MIT
   licence.
9. Keywords: soft sensor; conformal prediction; delayed labels; dead time; adaptive calibration;
   Tennessee Eastman process; debutanizer; pre-registration.
10. Version: `n1-jpc-submission`. Language: English. Publication date: the day it is published.
11. Related works: "Is derived from", URL, `https://github.com/beebzy-droid/IPIS`. After the
    article is accepted, add "Is supplement to" with the article's DOI (a new version is not
    needed for metadata).
12. "Save draft". Do not publish until the DOI is in the manuscript and the final PDF is checked
    (Section 2, step 6).

## 4. Checks after publishing

- The record's files tab lists an MD5 for each file. The SHA-256 values in `SHA256SUMS.txt` are
  the ones to keep; copy them into the submission record (private repository).
- `https://doi.org/<DOI>` resolves to the record.

## 5. 2026-11-25: the files replaced by the N1-only build

What happened: the first build (`zenodo_package.py` at the tag) archived the whole repository at
the tag, 624 files in 11.0 MB, so the published record also held the other papers (`paper/` to
`paper4/`), the other modules' code and documents, and the program documents. Nothing private
was exposed: every file is public on GitHub at the tag. The fault was the deposit's scope, and the design of the script (a `git
archive` of the whole tag) caused it.

The fix, in the script (committed after the tag; the archive is still built from the tag):
`N1_PATHS` lists the study's files, 161 of them, 3.4 MB. The script stops if a path selects
nothing at the tag, if the archive does not hold exactly the selected files, or if the script
itself is not committed (the deposit's README names the commit that wrote it). Left out on
purpose: `data/README.md` (the whole project's data guide), `tests/unit/test_loaders.py` and its
fixture `tests/fixtures/debutanizer_sample.txt` (rows in the debutanizer file's format; the
deposit does not redistribute the debutanizer data), this file and the packaging script itself
(they describe the deposit, not the study).

Checked on 2026-11-25 by unpacking the archive alone (Linux, Python 3.13.18, numpy 2.5.3, scipy
1.18.1, pandas 3.0.5, scikit-learn 1.9.1, statsmodels 0.15.0, matplotlib 3.11.2): `python -m
pytest tests/unit` passes 159 of 159 tests; `python -m scripts.paper_n1.make_all` rewrites the 31
figure and table files, and 20 of the 21 CSV and LaTeX files are byte-identical to the archived
ones. In the 21st, `n1_speed_chart.csv`, 14 interval bounds differ by at most 3.3e-14 (floating
point, another platform).

Steps (Bien, zenodo.org):
1. Commit the new script and push; then build: `set PYTHONPATH=src`, `python -m
   scripts.paper_n1.zenodo_package --tag n1-jpc-submission`. Expect `IPIS-n1-jpc-submission.zip:
   3.4 MB` and `161 files of the N1 study archived`.
2. Open the record (https://doi.org/10.5281/zenodo.24357752), "Edit", open "Edit files", click
   "Edit published files" and complete the dialog.
3. Delete the four files of the first upload; upload the four new files from `dist\zenodo`
   (`tep_phase1_runs.zip` holds the same 15 runs, but its own `SHA256SUMS.txt` member is new, so
   it is replaced too).
4. Replace the description with the one in Section 3, step 7. Nothing else changes.
5. "Publish". The DOI stays 10.5281/zenodo.24357752.
6. Check: the files tab lists `IPIS-n1-jpc-submission.zip` at about 3.4 MB; download it and
   confirm that no `paper/` folder is in it; `README.md` ends with the archived paths.
