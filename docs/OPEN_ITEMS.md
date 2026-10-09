# Open items by owning session

Cross-session register. **Every session reads its own section before starting work** (pointer
in `docs/HANDOFF.md` §0 and at the top of each module's `spec.md`). When you close an item, change
its status, give the commit and the evidence, and leave the row in place, so the next session
can see it was done.

Opened 2026-10-09 by the M2 session. File:line references are as of the 2026-10-09 author-block commit ("Canonical author block
..."); commit SHAs are not cited here because a history rewrite would change them.

## M1 / N1 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-01 | `busico_m1` still cites JPROCONT-D-26-00618, which was **rejected after review**, so three downstream papers cite a dead manuscript ID | Canonical entry `docs/CITATION_LEDGER.md` §3 (line 52); copies in `paper4/references.bib:68`, `paper4/em/main_EM.tex:872` (bibitem inlined from the .bbl), `paper5/references.bib:7`; M3 cites M1 under a **different key**, `companion2026`, in `paper2/references.bib:198`, `paper2/cjce/references.bib:198` and `paper2/tcst/references.bib:198`; prose in `paper4/cover_letter.md:34` and `paper5/cover_letter.md:34` | The entry is replaced with "Unpublished manuscript" (as was done for `busico_m3`) or with the N1 title and new ID once they exist. It is propagated to every file listed, `.bbl`-inlined copies regenerated, and `git grep -n 00618 -- paper paper2 paper4 paper5` returns only history notes. M4 is under review, so the `paper4/` change rides along with the M4 revision; CACE's copy stays as submitted. | open |
| OI-02 | `paper/main.tex` has 1 LaTeX error: `\tightlist` undefined at l.45 (pandoc residue) | Build log 2026-10-09; the error is pre-existing (present before the 2026-10-09 passes) | `\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}` in the preamble, or the list rewritten; 0 errors | open (minor; N1 will rewrite the file) |

## M2 session (proof stage)

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-03 | Proof corrections C1 to C7, sent in one batch when the proof arrives | `docs/module2/proof/PROOF_CHECKLIST.md`; `scripts/proof_check.py` already FLAGs C1, C6, C7 and the table renumbering (P7) against the marked-up PDF | Proof approved with C1 to C7 applied and `proof_check.py` clean apart from the expected decisions | waiting for Elsevier |
| OI-04 | After publication: Zenodo v1.0.1, ledger domino (full `busico_m2` reference into paper4 and paper5), source made to match the published article | PROOF_CHECKLIST §4; `scripts/zenodo_scc_v101.py` | All four §4 steps done and recorded in `paper3/submission_R1/EM_SUBMISSION_RECORD.md` | waiting for the article DOI |
| OI-05 | Two FEMTO probe scripts sat at the repo root | Committed by accident in b8bc355 (2026-06-30, an M1 commit) | Moved to `scripts/probe_femto_eol.py` and `scripts/probe_femto_fpt.py`; usage lines updated | **closed 2026-10-09** |

## M3 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-06 | Byline and affiliation in `paper2/` brought to the canonical block (`docs/AUTHOR.md`) on 2026-10-09: "Bien Don Busico" became "Bien Busico", "Mapua" became "Mapúa"/`Map\'ua`, and "Davao del Sur" was dropped. The generated `paper2/cjce/Cover_Letter_CJCE.docx` still carries the old strings | `python scripts/check_author_block.py` is clean on the sources; `.docx` files are not scanned | Regenerate every `.docx` from its source before the next M3 submission, and update the ReX/ScholarOne profile | open (at next submission) |
| (see OI-01) | M3's `companion2026` is one of the stale M1 cites | above | closed by OI-01 | open |

## M4 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-07 | M4 is under review at CACE (CACE-D-26-01079) with the singular "College". The repo now carries the plural | `paper4/main.tex:33`, `paper4/em/main_EM.tex:34` and `paper4/cover_letter.md:44` were updated 2026-10-09; the submitted `paper4/cover_letter.docx` is the record | The CACE EM profile and the revision's front matter carry the canonical block; if the paper is accepted first, request the change at proof | open |
| OI-08 | Stray `twin_coverage.png` at the repo root, MD5 `ea267f7a…`, which **differs** from the canonical `paper4/figures/twin_coverage.png` = `docs/module4/twin_coverage.png` (`9830e9c6…`) | Committed in b8bc355 (2026-06-30). `scripts/run_twin_coverage.py` defaults `--fig` to the current directory, which is how it gets written to the root | Confirm it is an older render, `git rm` it, and default `--fig` to `docs/module4/twin_coverage.png` | open (left for the owner because the content differs) |
| OI-09 | `paper4/em/main_EM.tex` reports 3 missing-figure errors when built in place | It is flat by design (EM upload); the figures are in `paper4/figures/` | Not a defect. To build it: copy `paper4/figures/*.png` beside it (verified 2026-10-09: 0 errors, 27 pp) | closed (by design) |

## M5 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-10 | **Venue conflict for M5.** `docs/CITATION_LEDGER.md:25` and HANDOFF l.1359 say "retargeted CACE -> IEEE TCST", but `paper5/main.tex:13` and `main_EM.tex:15` are elsarticle with `\journal{Computers \& Chemical Engineering}`, HANDOFF l.131 and l.189 say CACE, and project memory has said "submitted to CACE". No M5 manuscript ID exists anywhere in the repo | lines cited | One venue and one status in the ledger (§1 and §3), README, HANDOFF and `paper5/` (class plus `\journal`), with an ID if it was ever submitted | open |
| OI-11 | `paper5/main_EM.tex` reports 3 missing-figure errors (`fig1_two_arm.png`, `fig2_deadtime.png`, `fig3_gamma_union.png`) | The figures are **not missing**: they are in `docs/module5/figures/` (committed 2026-06-30). `paper5/main.tex` builds with 0 errors (19 pp); `main_EM.tex` is flat by design and builds with 0 errors (23 pp) once the figures are on the path | Not a defect. For the EM upload, copy the three PNGs beside `main_EM.tex` | closed (by design; the 2026-10-09 ledger flag was wrong) |

## Bien (external; the repo cannot do these)

| ID | Item | Done when | Status |
|---|---|---|---|
| OI-12 | M2 rights form: subscription or open access. This sets how much of the M2 manuscript may stay public on GitHub and therefore the scope of OI-13 (see `docs/reviews/HISTORY_REWRITE.md`, "When") | Form submitted; choice recorded in PROOF_CHECKLIST §0 | waiting for Elsevier |
| OI-13 | Remove the verbatim response letter from public history (rewrites 89263d2 to the tip; keeps all 222 earlier commits). Runbook tested 2026-10-09 | Run once after OI-12; GitHub Support asked to drop cached views; date recorded in HANDOFF | prepared, not run |
| OI-14 | Author details outside the repo: Elsevier EM profiles (RESS, CACE, JPROCONT) with the plural affiliation and ORCID linked; ORCID employment record; Wiley ReX and IEEE profiles | Each profile reads exactly as `docs/AUTHOR.md` | open |
| OI-15 | Byline | **Decided 2026-10-09: "Bien Busico" on every IPIS paper**, as already in all sources and in the accepted M2; no proof correction | **closed 2026-10-09** |
