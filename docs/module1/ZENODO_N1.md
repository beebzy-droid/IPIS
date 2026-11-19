# N1: the Zenodo deposit of the evidence

Status, 2026-11-19: prepared; Bien uploads it and reserves the DOI (decided 2026-11-18: "Zenodo DOI
first"). The manuscript cites the deposit as a dataset (`busico2026data`, in the private
manuscript's bibliography), and its Data and code availability statement points to it. The DOI
goes into that record before the final PDF is built; the private repository's flattening script
for the submission copy refuses to run while the placeholder `XXXXXXX` remains.

## 1. What is deposited

Four files, written by `scripts/paper_n1/zenodo_package.py` to `dist/zenodo/` (gitignored):

| File | Content | Size (expected) |
|---|---|---|
| `IPIS-<tag>.zip` | `git archive` of the tagged commit: code, pre-registration, runner records, evidence (`docs/paper/evidence/phase1_*.json`), figure and table generators, figures and the supplementary tables | about 11 MB |
| `tep_phase1_runs.zip` | The 15 Tennessee Eastman runs of the study, each checked first against the SHA-256 in `docs/paper/evidence/tep_seed_qualification.json`, with `SHA256SUMS.txt` | tens of MB |
| `README.md` | What the deposit holds, how to reproduce the study, the debutanizer source and digest, licences | 3 kB |
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
   editor and the reviewers. A published record's files cannot be replaced; a correction becomes
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
   > any result of the study existed. The deposit holds the repository at the submission tag (code,
   > pre-registration, the records of both stages of the run, figure and table generators) and
   > the 15 simulated Tennessee Eastman runs; README.md explains how to reproduce the study. The
   > debutanizer data are not redistributed (Fortuna et al., Soft Sensors for Monitoring and
   > Control of Industrial Processes, Springer, 2007).

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
