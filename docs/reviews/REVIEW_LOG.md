# Review and correspondence log (IPIS program)

Public, factual record of every editorial event. Verbatim correspondence is kept out of
this public repository in the git-ignored `private/correspondence/`, because peer-review
reports are conventionally treated as confidential (general publication-ethics practice;
not verified as a specific journal rule). Each comment is captured as paraphrased,
structured data in `REVIEW_REGISTER.csv`.

Resolved 2026-10-09: the M2 response letter, which quotes both RESS reviewers verbatim, was
tracked from 2026-09-18 to 2026-10-09 and was removed from public git history by the rewrite
recorded in `HISTORY_REWRITE.md`. All peer-review material now lives in the private `ipis-papers`
repo (`docs/PAPER_LIFECYCLE.md`).

## Timeline

Evidence levels: EMAIL (the email that carried the event; its header timestamp in UTC, written
MM-DD HH:MMZ), RECORDED (a dated repo or chat record), EM (an Editorial Manager status line pasted by
the author). The Date column is the Manila calendar date (UTC+8): the author's calendar and the
timezone of the repo's commits, so it can differ by one day from the UTC date in the Evidence column.
On 2026-10-09 the M1 session replaced every BOUND row with its email-header date from the author's
Gmail and added the M3 and M4 events this log was missing (THESIS_STANDARDS L10, L11).

| Date (Manila) | Evidence | Paper | Venue / ID | Event | Outcome |
|---|---|---|---|---|---|
| 2026-06-12 | EMAIL 06-12 09:26Z | M1 | CACE-D-26-00944 | Submitted | |
| 2026-06-16 | EMAIL 06-16 07:35Z | M3 | JPROCONT-D-26-00565 | Submitted | |
| 2026-06-17 | EMAIL 06-17 04:20Z | M3 | JPROCONT-D-26-00565 | Technical send-back | 12-15 pp cap in the Elsevier template |
| 2026-06-20 | EMAIL 06-20 13:22Z | M2 | JRESS-D-26-04509 | Submitted | |
| 2026-06-22 | EMAIL 06-22 14:13Z | M2 | JRESS-D-26-04509 | Technical return before review | Single-column format required; reformatted and resent |
| 2026-06-24 | EMAIL 06-23 21:01Z | M3 | JPROCONT-D-26-00565 | Desk decision | Rejected on significance, no reviewers; transferred to CACE |
| 2026-06-25 | EMAIL 06-25 04:46Z | M3 | CACE-D-26-01040 | Submitted (Elsevier transfer) | |
| 2026-06-26 | EMAIL 06-26 07:05Z | M2 | JRESS-D-26-04509 | Desk decision | Rejected without review. Reason given (paraphrase): a theorem-proof structure that does not suit the journal's engineering readership; a restructured resubmission was invited |
| 2026-06-26 | EMAIL 06-26 09:35Z | M4 | IECR ie-2026-03342s | Submitted | |
| 2026-06-28 | EMAIL 06-27 17:19Z | M1 | CACE-D-26-00944 | Desk decision | Rejected without review (scope, novelty); Elsevier transfer offered |
| 2026-06-30 | EMAIL 06-30 01:33Z | M1 | JPROCONT-D-26-00618 | Transfer submitted (reframed, 13 pp) | Under review (EM lists 2026-06-29 on its own clock) |
| 2026-06-30 | EMAIL 06-30 07:42Z | M4 | IECR ie-2026-03342s | Desk decision | Declined by the editor (paraphrase): sound, but not a fit for the journal's broad readership; ACS Omega transfer offered, not taken |
| 2026-06-30 | RECORDED | M2 | JRESS-D-26-04700 | Resubmitted after deliverable-first restructure | Under review |
| 2026-07-01 | EMAIL 06-30 19:13Z | M4 | CACE-D-26-01079 | Submitted (reframed after IECR) | |
| 2026-07-01 | EMAIL 07-01 10:04Z | M3 | CACE-D-26-01040 | Desk decision | Rejected without external review (paraphrase): within aims and scope, insufficient novelty |
| 2026-07-04 | EMAIL 07-04 15:29Z | M3 | IEEE TCST 26-0876 | Submitted | |
| 2026-07-14 | EMAIL 07-14 07:02Z | M4 | CACE-D-26-01079 | Desk decision | Rejected without external review (paraphrase): within aims and scope, insufficient novelty. Transfer reminders followed to 08-04; no appeal or resubmission |
| 2026-07-14 | EMAIL 07-14 10:09Z | M3 | IEEE TCST 26-0876 | Returned to author (v1) | Author list and figure labels to fix; one resubmission allowed |
| 2026-07-23 | EMAIL 07-23 14:03Z | M3 | IEEE TCST 26-0876 | Revised version (v2) received | |
| 2026-07-25 | EM | M1 | JPROCONT-D-26-00618 | Status date | Under review |
| 2026-07-26 | EMAIL 07-25 20:49Z | M1 | SSRN 7181724 | Preprint registered through the journal's preprint service | doi:10.2139/ssrn.7181724; added to the author's ORCID record 2026-07-26 |
| 2026-07-27 | EMAIL 07-27 09:19Z | M1 | n/a | Unsolicited invitation (sender domain researchnexis.com; journal ISSN 2998-8713), two days after the SSRN listing | Not engaged (THESIS_STANDARDS S6) |
| 2026-08-09 | EMAIL 08-08 22:13Z | M2 | JRESS-D-26-04700 | Decision after review, 2 reviewers | Major revision (9 major + 3 minor comments) |
| 2026-08-11 | EMAIL 08-10 18:27Z | M1 | JPROCONT-D-26-00618 | Decision after review, 4 reviewers | Rejected; R1 major revision, 3 reject |
| 2026-08-11 | EMAIL 08-10 18:28Z | M1 | JPROCONT-D-26-00618 | Elsevier transfer offer for the rejected manuscript; reminders to 2026-09-01 | Not exercised: N1 is a new manuscript, not a transfer |
| 2026-08-29 | EMAIL 08-28 22:34Z | M3 | IEEE TCST 26-0876 | Decision (v2) after preliminary evaluation by the Editor-in-Chief | Prescreened-rejected, out of scope; final |
| 2026-09-07 | RECORDED | external | arXiv 2609.07251 | El Halabi and Brandt, delayed-feedback ACI | Removes one candidate contribution |
| 2026-09-28 | RECORDED | M1 | n/a | Audit A1-A12 closed; register; N1 ratified; Phase 0 code-ready | Phase 0 in progress |
| 2026-09-28 | EMAIL 09-28 06:24Z | M3 | CJCE 1404930 | Submitted | |
| 2026-09-29 | EMAIL 09-28 16:34Z | M3 | CJCE 1404930 | Desk decision, about 10 h after submission | Not considered for publication; no reasons stated; Wiley Transfer Desk offered |
| 2026-10-07 | RECORDED | M2 | JRESS-D-26-04700 | R1 submitted (Word manuscript, marked-up PDF, response letter) | |
| 2026-10-09 | RECORDED | M2 | JRESS-D-26-04700R1 | Decision | **Accepted**, no further revisions; to production |
| 2026-10-09 | RECORDED | M1 | n/a | Phase 0 closed: lag provenance frozen as evidence (R4.5 closed), delayed-ACI library reproduced on Windows (11 tests) | Phase 1 pre-registration drafted and independently checked. A pre-data pilot shows the white-noise loop model misses the infinite-interval share at every persistence level and sd(alpha) at autocorrelation 0.9 or more, so a claim amendment (D-P1.1) awaits ratification |

## Program decision record (verified 2026-10-09 from email headers)

| Outcome | Submissions |
|---|---|
| Decided at the desk, no external reviewers | 8: M1 CACE-D-26-00944; M2 JRESS-D-26-04509; M3 JPROCONT-D-26-00565, CACE-D-26-01040, IEEE TCST 26-0876, CJCE 1404930; M4 IECR ie-2026-03342s, CACE-D-26-01079 |
| Reached reviewers | 2: M1 JPROCONT-D-26-00618 (rejected after 4 reviews, 41.7 days to decision); M2 JRESS-D-26-04700 (major revision after about 40 days, then accepted) |

Desk decisions took a median of 6.9 days (range 0.4 to 55.3; the TCST figure includes a return for
author-list and figure fixes). Reasons given at the desk, paraphrased: novelty or significance 4
(M1 CACE, M3 JPC, M3 CACE, M4 CACE); scope, fit or readership 3 (M1 CACE, M3 TCST, M4 IECR); the
manuscript's structure 1 (M2 04509); none stated 1 (M3 CJCE). M1's CACE letter gave two reasons, so
the counts sum to 9. By venue: CACE 3 submissions and 3 desk rejections, twice in the same terms
(within aims and scope, insufficient novelty); JPC 2 (1 desk, 1 reviewed); RESS 2 (1 desk,
1 accepted). M5 has never been submitted: no journal sent a submission email for its title.

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
evidence trail is `docs/module2/revision/REVISION_LOG.md` in the private `ipis-papers` repo.

## How to use the register

- A comment closes only when `evidence_artifact` points to a committed file (figure,
  evidence JSON, or manuscript section) that answers it.
- RESCOPE is a disposition, not an escape: the reason is recorded, and the component may
  return in a later paper with the comment addressed.
- The next submission's cover letter and any response document are generated from this
  register, so no comment is answered from memory.
