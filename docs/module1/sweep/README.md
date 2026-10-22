# N1 database sweep: screening log

The protocol and the verdicts are in `../LITERATURE_SWEEP_N1.md` ("Database sweep protocol,
2026-10-20" and the sections after it).

| File | Contents |
|---|---|
| `N1_database_screening_2026-10-22.csv` | One row per unique record of the Scopus and Web of Science exports of 2026-10-22 (377 rows) |
| `N1_database_screening_2026-10-22_summary.json` | Counts per query and per code; the check that each export meets its search string; the export dates; the SHA-256 of every export read |

Both files are written by `scripts/sweep/n1_screening.py` from the raw exports. The exports are
not in the repository, because the database terms restrict redistribution and the abstracts
belong to the publishers. Keep them under `private/sweep/` (excluded by `.gitignore`). The
SHA-256 in the summary identify them.

Columns of the log:
- `uid`: R001 to R377, in the order the exports are read;
- `key`: the DOI, or else the Scopus EID or WoS UT;
- `databases`, `queries`: where the record was found (S1 to S12, W1 to W8);
- `year`, `first_author`, `title`, `source`;
- `code`: the screening decision (below);
- `item`: the F4 item or topic it was screened against (i, ii, iii, P2, 3D, process);
- `note`: the reason, for records with a decision other than the default.

| Code | Meaning |
|---|---|
| X1 | "conformal" appears only in another sense (coatings, antennas, meshes, physics) |
| X2 | no conformal or prediction-interval method in the title or abstract |
| X3 | a conformal or interval method that bears on none of F4 (i) to (iii) or Section 3D |
| X4 | already in the sweep record (rows 1 to 20) or the project library |
| X5 | uses Tennessee Eastman data or the simulator; nothing on its random-number generator |
| X6 | classical dead-time compensation, without intervals |
| F | may bear; read in full (verdicts in rows 22 to 24 and 26 to 30) |
| A | may bear; full text not reached from the workspace (row 31); to read before submission |
