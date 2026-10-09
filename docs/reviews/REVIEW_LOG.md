# Review and correspondence log (IPIS program)

Public, factual record of every editorial event. Verbatim correspondence is kept out of
this public repository in the git-ignored `private/correspondence/`, because peer-review
reports are conventionally treated as confidential (general publication-ethics practice;
not verified as a specific journal rule). Each comment is captured as paraphrased,
structured data in `REVIEW_REGISTER.csv`.

Known exception (2026-10-09): the M2 response letter, which quotes both RESS reviewers verbatim,
was tracked from 2026-09-18 to 2026-10-09 and is still in public git history. A tested rewrite
that removes it is in `HISTORY_REWRITE.md`; it will run once, after the M2 rights form.

## Timeline

Evidence levels: RECORDED (written in a dated repo or chat record), EM (Editorial Manager
status line pasted by the author), BOUND (interval fixed by recorded events on either side).
Exact email-header dates replace BOUND entries when available; nothing is inferred beyond the
stated bound (THESIS_STANDARDS L10).

| Date | Level | Paper | Venue / ID | Event | Outcome |
|---|---|---|---|---|---|
| 2026-06-12 | RECORDED | M1 | CACE-D-26-00944 | Submitted | |
| 2026-06-20 | RECORDED | M2 | JRESS-D-26-04509 | Submitted | |
| 2026-06-22 | RECORDED | M2 | JRESS-D-26-04509 | Technical return before review | Single-column format required; reformatted and resent |
| 2026-06-30 | RECORDED | M2 | JRESS-D-26-04700 | Resubmitted after deliverable-first restructure | Under review |
| after 06-12, on or before 06-29 | BOUND | M1 | CACE-D-26-00944 | Desk decision | Rejected without review (scope, novelty); transfer offered |
| on or before 2026-06-23 | BOUND | M3 | JPROCONT-D-26-00565 | Technical send-back | 12-15 pp cap in Elsevier template |
| on or before 2026-06-23 | RECORDED | M3 | JPROCONT-D-26-00565 | Desk decision | Rejected on significance, no reviewers; M3 moved to CACE-D-26-01040 |
| 2026-06-29 | EM | M1 | JPROCONT-D-26-00618 | Transfer submitted (reframed, 13 pp) | Under review |
| 2026-07-25 | EM | M1 | JPROCONT-D-26-00618 | Status date | Under review |
| after 06-29, pasted on or after 07-25 | BOUND | M1 | n/a | Unsolicited invitation, predatory indicators | Not engaged (THESIS_STANDARDS S6) |
| after 07-25, on or before 09-28 | BOUND | M1 | JPROCONT-D-26-00618 | Decision after review, 4 reviewers | Rejected; R1 major revision, 3 reject |
| on or before 2026-09-07 | BOUND | M2 | JRESS-D-26-04700 | Decision after review, 2 reviewers | Major revision (9 major + 3 minor comments); bound set by the first revision commit |
| 2026-09-07 | RECORDED | external | arXiv 2609.07251 | El Halabi and Brandt, delayed-feedback ACI | Removes one candidate contribution |
| 2026-09-28 | RECORDED | M1 | n/a | Audit A1-A12 closed; register; N1 ratified; Phase 0 code-ready | Phase 0 in progress |
| 2026-10-07 | RECORDED | M2 | JRESS-D-26-04700 | R1 submitted (Word manuscript, marked-up PDF, response letter) | |
| 2026-10-09 | RECORDED | M2 | JRESS-D-26-04700R1 | Decision | **Accepted**, no further revisions; to production |

## Register summary (JPROCONT-D-26-00618 plus CACE)

42 records: 11 critical, 23 major, 7 minor, plus the editor decision.
Proposed dispositions under N1: 13 FIX, 10 RESCOPE, 6 REWRITE, 5 REPORT, 5 EXPERIMENT,
1 CLARIFY. Status of every record is `open` until its evidence artifact is committed.

## Register summary (JRESS-D-26-04700, M2)

Two editorial decisions (major revision; accept) and 12 reviewer comments (R1: 5; R2: 4 major and
3 minor), rows `M2.*` in the register. All 12 were answered in R1 and the paper was accepted, so
every M2 row is `closed-accepted`. For M2 rows the `proposed_disposition_N1` column records the
disposition actually taken in R1 (it was named for M1's N1 plan) and `evidence_artifact` names the
script or section that carries the answer. Disposition mix: 7 EXPERIMENT (one with RESCOPE, one with
FIX), 4 REWRITE, 1 REPORT. Two comments rated critical by us: R1.5 (within-unit dependence),
which invalidated every number in Section 5 and was answered by recomputing all of it, and R2.M1
(no externally authored dataset), answered with the C-MAPSS case study.

What the M2 record adds to the program evidence: a paper that reached reviewers was accepted after
one round, and the response letter volunteered two errors found during the revision. The full
evidence trail is `docs/module2/revision/REVISION_LOG.md`.

## How to use the register

- A comment closes only when `evidence_artifact` points to a committed file (figure,
  evidence JSON, or manuscript section) that answers it.
- RESCOPE is a disposition, not an escape: the reason is recorded, and the component may
  return in a later paper with the comment addressed.
- The next submission's cover letter and any response document are generated from this
  register, so no comment is answered from memory.
