# Open items by owning session

Cross-session register. **Manuscripts live in the private `ipis-papers` repo: read
`docs/PAPER_LIFECYCLE.md` before touching one.** Paths below that start with `paper`, or with
`docs/module2/revision` or `docs/module2/proof`, are in that private repo unless the row says
frozen. **Every session reads its own section before starting work** (pointer
in `docs/HANDOFF.md` §0 and at the top of each module's `spec.md`). When you close an item, change
its status, give the commit and the evidence, and leave the row in place, so the next session
can see it was done.

Opened 2026-10-09 by the M2 session. File:line references are as of the 2026-10-09 author-block commit ("Canonical author block
..."); commit SHAs are not cited here because a history rewrite would change them.

## M1 / N1 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-01 | `busico_m1` cited JPROCONT-D-26-00618, which was **rejected after review**, so three downstream papers cite a dead manuscript ID | Canonical entry `docs/CITATION_LEDGER.md` §3. Working copies in `ipis-papers`: `paper4/references.bib` and the bibitem inlined in `paper4/em/main_EM.tex`; `paper5/references.bib`; M3 cites M1 under a **different key**, `companion2026`, in `paper2/references.bib`, `paper2/cjce/references.bib` and `paper2/tcst/references.bib`; prose in `paper4/cover_letter.md` and `paper5/cover_letter.md` | Each working copy that cites M1 carries the §3 entry, cover-letter prose no longer names the dead ID, and `.bbl`-inlined copies are regenerated. The frozen preprints in IPIS keep the strings they were submitted with (PAPER_LIFECYCLE rule 1), so a public `git grep 00618` will keep finding them; that is expected | **canonical fixed 2026-10-09** (SSRN preprint, doi:10.2139/ssrn.7181724, verified from the SSRN and ORCID emails); downstream pulls open, each at that paper's next build or submission |
| OI-02 | `paper/main.tex` has 1 LaTeX error: `\tightlist` undefined at l.45 (pandoc residue) | Build log 2026-10-09; the error is pre-existing (present before the 2026-10-09 passes) | `\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}` in the preamble, or the list rewritten; 0 errors | **closed 2026-10-09, superseded**: `paper/` in IPIS is M1's frozen preprint and is never edited (PAPER_LIFECYCLE rule 1). N1 is written fresh in `ipis-papers/paper/`; if it reuses this preamble, add the `\providecommand` there |

## M2 session (proof stage)

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-03 | Proof corrections C1 to C7, sent in one batch when the proof arrives | `ipis-papers/docs/module2/proof/PROOF_CHECKLIST.md`; `scripts/proof_check.py` already FLAGs C1, C6, C7 and the table renumbering (P7) against the marked-up PDF | Proof approved with C1 to C7 applied and `proof_check.py` clean apart from the expected decisions | waiting for Elsevier |
| OI-04 | After publication: Zenodo v1.0.1, ledger domino (full `busico_m2` reference into paper4 and paper5), source made to match the published article | PROOF_CHECKLIST §4; `scripts/zenodo_scc_v101.py` | All four §4 steps done and recorded in `ipis-papers/paper3/submission_R1/EM_SUBMISSION_RECORD.md` | waiting for the article DOI |
| OI-05 | Two FEMTO probe scripts sat at the repo root | Committed by accident in b8bc355 (2026-06-30, an M1 commit) | Moved to `scripts/probe_femto_eol.py` and `scripts/probe_femto_fpt.py`; usage lines updated | **closed 2026-10-09** |

## M3 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-06 | Byline and affiliation in `paper2/` brought to the canonical block (`docs/AUTHOR.md`) on 2026-10-09: "Bien Don Busico" became "Bien Busico", "Mapua" became "Mapúa"/`Map\'ua`, and "Davao del Sur" was dropped. The generated `paper2/cjce/Cover_Letter_CJCE.docx` still carries the old strings | `python scripts/check_author_block.py` is clean on the sources; `.docx` files are not scanned | Regenerate every `.docx` from its source before the next M3 submission, and update the ReX/ScholarOne profile | open (at next submission) |
| (see OI-01) | M3's `companion2026` is one of the stale M1 cites | above | closed by OI-01 | open |

## M4 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-07 | M4 is under review at CACE (CACE-D-26-01079) with the singular "College". The repo now carries the plural | `paper4/main.tex:33`, `paper4/em/main_EM.tex:34` and `paper4/cover_letter.md:44` were updated 2026-10-09; the submitted `paper4/cover_letter.docx` is the record | The CACE EM profile and the revision's front matter carry the canonical block; if the paper is accepted first, request the change at proof | open; **premise wrong, see OI-16** (M4 is not under review, so the canonical block simply applies at M4's next submission) |
| OI-08 | Stray `twin_coverage.png` at the repo root, MD5 `ea267f7a…`, which **differs** from the canonical `paper4/figures/twin_coverage.png` = `docs/module4/twin_coverage.png` (`9830e9c6…`) | Committed in b8bc355 (2026-06-30). `scripts/run_twin_coverage.py` defaults `--fig` to the current directory, which is how it gets written to the root | Confirm it is an older render, `git rm` it, and default `--fig` to `docs/module4/twin_coverage.png` | open (left for the owner because the content differs) |
| OI-16 | **M4 is not under review.** CACE-D-26-01079 was rejected by the editor without external review on 2026-07-14 (07:02 UTC; reason given, paraphrased: within aims and scope, insufficient novelty). Only Elsevier transfer reminders followed (07-17, 07-28, 08-04); no appeal or resubmission exists | Author's Gmail, checked 2026-10-09 by the M1 session (decision email of 2026-07-14; a search for the M4 title after 2026-07-15 returns only transfer reminders). Live surfaces that still say "under review": `docs/PAPER_LIFECYCLE.md` §3, `docs/AUTHOR.md` l.30, `docs/CITATION_LEDGER.md` §1 (M4 row) and §3 (`busico_m4` note), `README.md` l.59 and l.80, `PROJECT_STRUCTURE.md` l.11, `docs/HANDOFF.md` l.46-47, l.77 and l.518, OI-07. Dated history entries are not rewritten | Status corrected on every live surface; `busico_m4` no longer names CACE-D-26-01079 (blast radius M5); M4 recorded as reverted to preprint status (frozen `paper4/` stays, per PAPER_LIFECYCLE "Rejected without a revision"); next venue decided by the owner, with the verified desk record in `docs/reviews/REVIEW_LOG.md` | open (M4 session) |
| OI-09 | `paper4/em/main_EM.tex` reports 3 missing-figure errors when built in place | It is flat by design (EM upload); the figures are in `paper4/figures/` | Not a defect. To build it: copy `paper4/figures/*.png` beside it (verified 2026-10-09: 0 errors, 27 pp) | closed (by design) |

## M5 session

| ID | Item | Evidence | Done when | Status |
|---|---|---|---|---|
| OI-10 | **Venue conflict for M5.** `docs/CITATION_LEDGER.md:25` and HANDOFF l.1359 say "retargeted CACE -> IEEE TCST", but `paper5/main.tex:13` and `main_EM.tex:15` are elsarticle with `\journal{Computers \& Chemical Engineering}`, HANDOFF l.131 and l.189 say CACE, and project memory has said "submitted to CACE". No M5 manuscript ID exists anywhere in the repo | lines cited | One venue and one status in the ledger (§1 and §3), README, HANDOFF and `paper5/` (class plus `\journal`), with an ID if it was ever submitted | open |
| (evidence for OI-10) | Was M5 ever submitted? **No.** The author's Gmail has no submission email for the M5 title from any journal (checked 2026-10-09 by the M1 session). `docs/PAPER_LIFECYCLE.md` §3 ("never submitted") is right; "submitted to CACE" was wrong | Gmail search for the M5 title | Settles the "with an ID if it was ever submitted" clause: no ID exists | evidence only; OI-10 stays with the M5 session |
| OI-11 | `paper5/main_EM.tex` reports 3 missing-figure errors (`fig1_two_arm.png`, `fig2_deadtime.png`, `fig3_gamma_union.png`) | The figures are **not missing**: they are in `docs/module5/figures/` (committed 2026-06-30). `paper5/main.tex` builds with 0 errors (19 pp); `main_EM.tex` is flat by design and builds with 0 errors (23 pp) once the figures are on the path | Not a defect. For the EM upload, copy the three PNGs beside `main_EM.tex` | closed (by design; the 2026-10-09 ledger flag was wrong) |

## Bien (external; the repo cannot do these)

| ID | Item | Done when | Status |
|---|---|---|---|
| OI-12 | M2 rights form: subscription or open access. This sets how much of the M2 manuscript may stay public on GitHub and therefore the scope of OI-13 (see `docs/reviews/HISTORY_REWRITE.md`, "When") | Form submitted; choice recorded in PROOF_CHECKLIST §0 | waiting for Elsevier |
| OI-13 | Remove the verbatim response letter from public history (rewrites 89263d2 to the tip; keeps all 222 earlier commits). Runbook tested 2026-10-09 | Run once after OI-12; GitHub Support asked to drop cached views; date recorded in HANDOFF | **executed 2026-10-09** (`docs/reviews/HISTORY_REWRITE.md`, execution record); GitHub Support ticket #4839390 open. Every clone must be reset before new work (same file, last section) |
| OI-14 | Author details outside the repo: Elsevier EM profiles (RESS, CACE, JPROCONT) with the plural affiliation and ORCID linked; ORCID employment record; Wiley ReX and IEEE profiles | Each profile reads exactly as `docs/AUTHOR.md` | open |
| OI-15 | Byline | **Decided 2026-10-09: "Bien Busico" on every IPIS paper**, as already in all sources and in the accepted M2; no proof correction | **closed 2026-10-09** |
