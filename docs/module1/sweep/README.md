# N1 database sweep: screening log

The protocol and the verdicts are in `../LITERATURE_SWEEP_N1.md` ("Database sweep protocol,
2026-10-20" and the sections after it).

| File | Contents |
|---|---|
| `N1_database_screening_2026-10-22.csv` | One row per unique record of the Scopus and Web of Science exports: those of 2026-10-22, the S4 export of 2026-10-27 and the citing sets of W9 and W10 of 2026-10-28 (382 rows) |
| `N1_database_screening_2026-10-22_summary.json` | Counts per query and per code; the check that each export meets its search string, with a note on the searches it cannot check; the export dates; the SHA-256 of every file read; what the second batch's W9 and W10 files hold; how many records of each citing set the refinement string matches |
| `N1_scholar_screening_2026-10-27.csv` | One row per unique Google Scholar result of the first pass, 2026-10-27 (48 rows); screened by hand |

The first two files are written by `scripts/sweep/n1_screening.py` from the raw exports. The log
keeps the name of its first batch. The exports are not in the repository, because the database
terms restrict redistribution and the abstracts belong to the publishers. Keep each batch in its
own folder, `private/sweep/2026-10-22`, `private/sweep/2026-10-27` and
`private/sweep/2026-10-28` (excluded by `.gitignore`), under the names the script lists. The
second batch also holds the Google Scholar result pages. The SHA-256 in the summary identify
every file. The full texts read for the verdicts stay outside the repository too.

Columns of the database log:
- `uid`: R001 to R382, in the order the exports are read;
- `key`: the DOI, or else the Scopus EID or WoS UT;
- `databases`, `queries`: where the record was found (S1 to S12, W1 to W10; W9 and W10 are the
  citing sets of the third batch);
- `year`, `first_author`, `title`, `source`;
- `code`: the screening decision (below);
- `item`: the F4 item or topic it was screened against (i, ii, iii, P2, 3D, process);
- `note`: the reason, for records with a decision other than the default.

Columns of the Google Scholar log: `gid` (G001 to G048, in the order of the result pages);
`queries` (G1 to G4); `year`, `first_author`, `title` and `venue` as Scholar lists them;
`identifier` (arXiv, DOI or SSRN number, where known); `code` and `item` as above; `basis`, what
the code rests on (`record` for a result already in the sweep, `full text`, `main text`,
`abstract` or `snippet`); and `note`. X4 there means already in rows 1 to 32 or the database log.

| Code | Meaning |
|---|---|
| X1 | "conformal" appears only in another sense (coatings, antennas, meshes, physics) |
| X2 | no conformal or prediction-interval method in the title or abstract |
| X3 | a conformal or interval method that bears on none of F4 (i) to (iii) or Section 3D |
| X4 | already in the sweep record (rows 1 to 20) or the project library |
| X5 | uses Tennessee Eastman data or the simulator; nothing on its random-number generator |
| X6 | classical dead-time compensation, without intervals |
| F | may bear; read in full (verdicts in rows 22 to 24, 26 to 30, 33 to 37 and 39 to 44) |
| A | may bear; full text not reached from the workspace; to read before submission (none since 2026-10-28, when rows 31 and 38 were read as rows 39 to 43) |
