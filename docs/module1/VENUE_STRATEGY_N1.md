# N1 venue strategy (2026-09-28; decision record verified 2026-10-09)

## 1. The program's binding constraint is the editor's desk

Recorded outcomes across IPIS (sources: project memory; `docs/reviews/REVIEW_REGISTER.csv`):

| Paper | Venue / ID | Outcome | Reached reviewers? |
|---|---|---|---|
| M1 | CACE-D-26-00944 | Desk reject (scope, novelty) | No |
| M1 | JPROCONT-D-26-00618 | Reject after review (R1: major revision, "core idea is novel") | Yes |
| M2 | RESS, first two submissions | Desk rejects | No |
| M2 | JRESS-D-26-04700 | Major revision | Yes |
| M3 | JPROCONT-D-26-00565 | Desk reject (significance) | No |
| M3 | CACE-D-26-01040 | Reject | No |
| M3 | IEEE TCST 26-0876 | Prescreen reject, out of scope | No |
| M3 | fourth recorded rejection (ID not in memory) | Reject | No |
| M4 | ie-2026-03342s (IECR) | Desk reject (scope) | No |

9 rejections, 8 of them without a single reviewer. Both times a paper reached reviewers it
drew substantive, partly favourable engagement. The science is not what fails first; fit and
significance framing at the desk are. N1's venue choice is therefore designed against desk
rejection before anything else.

**Update 2026-10-09 (M2 session).** M2 (JRESS-D-26-04700) was accepted after one major revision
(R1 submitted 2026-10-07, accepted 2026-10-09 with no further changes). Of the two papers that have
reached reviewers, one is now accepted. The table above is left as recorded on 2026-09-28.

**Verified record, 2026-10-09 (M1 session, from the author's email).** The table above came from
project memory and has three errors: M4's CACE-D-26-01079 was desk-rejected on 2026-07-14 and is not
under review; M2 had one desk rejection (JRESS-D-26-04509, for the manuscript's structure), not two;
the unnamed fourth M3 rejection is CJCE 1404930 (2026-09-29, about 10 h after submission, no reasons
given). Corrected counts: 10 submissions decided, 8 at the desk (80 %), 2 reached reviewers (M1
rejected, M2 accepted). Dates, reasons and timings: `docs/reviews/REVIEW_LOG.md`, section "Program
decision record".

What the verified record changes for N1:
- **Form is a desk criterion, and fixing it worked.** The one desk rejection whose stated reason
  was presentational (M2: a theorem-proof structure judged wrong for an engineering readership) was
  fixed by restructuring, and that paper is the program's only acceptance. N1's core is an analysis
  (a dead-time loop, its stability limit, a noise-gain model), so it must be written
  engineering-first: the plant problem and what it costs, the tuning chart, validation on process
  data, with the analysis as the instrument rather than a theorem-led exposition.
- **Novelty or significance is the commonest desk reason** (4 of 8 desk decisions). The
  presubmission inquiry (Section 4) must state the one new result in a sentence and the plant
  decision it changes.
- **CACE: 0 of 3**, twice in identical terms (within aims and scope, insufficient novelty). Already
  excluded; now a firm rule for N1.
- **CJChE: a desk decision in about 10 h with no reasons** (M3). Removed as the N1 fallback
  (Sections 3 and 4) until a reason is known.
- **JPC stays first.** Apart from RESS it is the only venue whose editor sent an IPIS paper to
  review, and its four reviewers produced the register that N1 answers.

## 2. Rules

1. Evidence of fit, not topic similarity: the target must have published, in its last 24
   months, work on soft sensors with delayed or infrequent laboratory measurements, online
   calibration or uncertainty of soft sensors, or dead-time loops. Counted in Phase 5.
2. Presubmission inquiry before formatting: a short email to the handling or chief editor
   with title, a 150-word abstract and the fit rationale, asking whether the journal would
   consider it. General editorial practice, not a verified procedure of any specific journal.
3. Scopus or Web of Science Q1, subscription route with no publication charge, and the
   highest acceptance probability that satisfies both (M3's choice of CJChE shows the
   zero-cost criterion is the author's standing preference).
4. The decision waits for Phase 1: if F1 to F3 fire on process data, the paper's shape and
   venue change.

## 3. Shortlist (fit judged from general knowledge; metrics verified in Phase 5 from each
journal's own pages, never aggregators)

| Journal | Fit to N1 | Risk | Program history |
|---|---|---|---|
| Journal of Process Control | Highest: soft sensors, laboratory delay, dead time; the cited lineage | Rejected the predecessor; requires disclosure and the editor's agreement to treat N1 as new work | M1 reviewed-reject; M3 desk reject |
| Control Engineering Practice | High: applied control, dead-time compensation, industrial tuning chart | None recorded | None |
| ISA Transactions | Good: dead-time compensation, process automation | None recorded | None |
| Canadian Journal of Chemical Engineering | Good: process systems and soft sensing; no charge | Desk decision in about 10 h, no reasons given | M3 desk reject (1404930, 2026-09-29); not recommended for N1 |
| IEEE TCST | Control-theoretic | M3 prescreened out of scope | Avoid |
| Computers & Chemical Engineering | Methods | Same desk wording twice: within scope, insufficient novelty | M1, M3 and M4 all desk-rejected (0 of 3); avoid for N1 |

## 4. Recommended sequence (after Phase 1 passes)

1. Presubmission inquiry to JPC, disclosing JPROCONT-D-26-00618 and stating that the new
   manuscript is a different claim that implements its reviewers' requested experiments
   (event-queue pairing comparison, matched controls, binomial intervals). Wait 14 days.
2. If declined or unanswered: presubmission inquiry to Control Engineering Practice.
3. Fallback: ISA Transactions (dead-time compensation, process automation), subject to the Phase 5
   checks. CJChE was removed on 2026-10-09 (Section 1, verified record).
