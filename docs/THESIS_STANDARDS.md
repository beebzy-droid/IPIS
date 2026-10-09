# Publication and thesis standards (IPIS program)

The operating standard for every paper in the IPIS series and for the PhD thesis it
becomes. Written after M1's two desk-rejections (CACE scope, JPC format) and the
negative-control reframe. The principle behind all of it: **a top-tier paper is not a
well-executed paper that is also novel; it is a paper organized around a single claim
that could have been false and was tested.** Everything below serves that.

## 1. The claim test (apply before writing a single section)

- State the paper's thesis as one sentence containing a claim that could be **wrong**.
  "We integrate X, Y, Z into a framework" is not a claim; it is an inventory, and
  editors desk-reject inventories as incremental (this is exactly why CACE rejected M1
  v1). "Distribution-free validity is model-agnostic while accuracy is bought by the
  physics" is a claim, because a negative control could have refuted it.
- If you cannot name the experiment that would falsify the thesis, you do not yet have
  a thesis. Find it before drafting.
- The integration/engineering is the **apparatus**, never the contribution. Demote it
  in the prose to "what makes the test interpretable."

## 2. Novelty is fixed at design time, not inflatable in revision

- Novelty is a property of the contribution, decided when the work was done. Revision
  can *reveal* and *sharpen* it; revision cannot *manufacture* it. Do not let an
  ambitious goal (a PhD, a prize) push the prose past what the evidence carries.
- Before claiming "first to," run a literature sweep at headline strength. If a
  reviewer can refute the claim with one citation, the claim is a liability, not an
  asset. M1's "first delayed-feedback conformal" claim was refuted in two searches;
  the defensible claim (the negative-control attribution) survived because the evidence
  backs it. **Claim only what your own evidence defends.**
- Strong epistemic words (novel, first, optimal, guarantee, falsify, negative control)
  are earned, not decorative. Each must be cashable against a specific result.

## 3. The negative-control habit (the rarest, highest-value move)

- A positive result shows your method works. A **negative control** shows *why* it
  works, by exhibiting the case where the causal ingredient is removed and the effect
  vanishes. It is standard in experimental science and almost absent in data-driven
  modeling, which is precisely why deploying one is a differentiator.
- For every claim of the form "A causes B," ask: what is the dataset/condition where A
  is absent and B should therefore fail? Build it. If B survives anyway, your causal
  story is wrong and you have learned something more valuable than another positive.
- Frame the obvious objection as a *designed limitation*, not a hole. M1 concedes a
  nonlinear model might rescue SECOM accuracy; that concession converts the
  linear-scope "weakness" into the instrument of the central claim.

## 4. Evidence discipline (non-negotiable, already in the repo)

- Every number in the paper regenerates from a single command against a
  provenance-stamped artifact. No number is typed from memory or restated at a
  different precision than its source (transcribe, never paraphrase a figure).
- Reproduce the full pipeline on an independent machine before submission.
- Report limits as results, not hedges. An analytical + empirical demonstration of
  where a method *fails* (e.g. linear-source migration degeneracy) is a contribution.

## 5. Journal fit and format (the two desk-rejection lessons)

- **Scope before submission.** Read the target journal's aims and its last two issues.
  Confirm the journal *publishes your kind of contribution*, not merely your topic.
  Position the cover letter against the journal's actual scope language and cite the
  fact that its community publishes your lineage. (CACE rejected M1 on scope; JPC,
  whose top authors are the soft-sensor lineage M1 builds on, is the right home.)
- **Format to the template before approval, not after acceptance.** Compile in the
  journal's production class (for Elsevier process journals: elsarticle
  `final,5p,times,twocolumn`), not the review class, when a page cap is stated. Wide
  tables and figures span columns (`table*`, `figure*`). A page cap is almost always a
  format problem masquerading as a length problem: measure in the production format
  before cutting content.
- A cover letter that owns an unfavorable history (a transfer, a desk-reject) reads as
  confidence. State it plainly.

## 6. Venue integrity: one submission at a time, and how to vet an invitation

Added in 2026, after an unsolicited invitation (sender domain researchnexis.com, journal
ISSN 2998-8713) arrived on 2026-07-27 while M1 was under active review at JPC, two days after
the journal's preprint service listed M1 on SSRN. An earlier version of this paragraph named a
publisher and a founding year taken from a web-search match; neither appears in the email, so
both were removed on 2026-10-09 (L10). The lesson has two parts: an absolute rule that admits no exceptions, and a filter for judging any venue
that approaches you.

### 6.1 The absolute rule (no exceptions, no judgment calls)

**A manuscript is submitted to exactly one journal at a time.** While a paper is under
review anywhere, it may not be submitted, offered, or promised to any other venue, no
matter how attractive the offer or how slow the current review. Simultaneous submission
is research misconduct under COPE guidance and under Elsevier, Springer, Wiley, IEEE,
and ACS policy. Consequences escalate from immediate rejection to retraction to an
author-level flag that follows you across a publisher's entire editorial system.

Corollaries worth stating so they are never re-litigated under pressure:
- A desk-rejection releases the paper; a "revise and resubmit" does not.
- Withdrawing is a formal act, done in the submission system and confirmed by the
  editorial office, before any new submission. Silence is not withdrawal.
- A preprint (SSRN, arXiv) is not a prior publication and does not block submission to
  the journals that permit preprints, which includes Elsevier process journals. Verify
  per venue, but preprinting is compatible with the rule above.
- Republishing work already published elsewhere, even in a low-quality venue, is prior
  publication. Publishing once in a predatory journal can permanently disqualify the
  work from a legitimate one. This is why a bad venue is worse than no venue.

### 6.2 Recognizing a predatory or low-value solicitation

None of these signals is conclusive alone. Three or more together is a decision.

- **It came to you unsolicited**, praising work it has not read, often quoting only your
  title. Reputable journals do not recruit manuscripts by cold email. Legitimate special
  issue invitations exist, but come from a named guest editor with a verifiable academic
  affiliation, reference specific relevant work, and name the journal's indexing.
- **Scope mismatch.** The venue's stated field does not contain your paper. A chemical
  process control manuscript solicited by a general "data analytics and decision making"
  journal is being harvested, not selected.
- **Youth without pedigree.** Volume 1 in the last two or three years, no society or
  university backing, no recognizable editorial board.
- **Fee prominence.** An article-processing charge advertised as a primary navigation
  item rather than disclosed in author guidelines. Legitimate open access charges exist
  and are often high; the tell is prominence and eagerness, not existence.
- **Language and register.** Generic flattery, grammatical irregularity in official
  correspondence, phrases that invert the relationship ("help us improve our journal"),
  promises of rapid publication, guaranteed acceptance, or a named turnaround measured
  in days for peer review.
- **Unverifiable people.** Managing editors with no institutional email, no ORCID, no
  publication record; editorial boards listing scholars who never agreed to serve.
- **Metrics that do not exist.** Invented indices ("Global Impact Factor," "Journal
  Influence Score") standing in for Clarivate Impact Factor or Scopus CiteScore.
- **Hijacked identity.** A cloned site imitating a legitimate indexed journal, often
  differing by one character in the domain. Check the Retraction Watch Hijacked Journal
  Checker before trusting a familiar-sounding name reached through an emailed link.

### 6.3 Positive verification checklist (run before any submission, including invited)

Verify the venue, never the email. Navigate to sources independently; do not follow
links supplied in the solicitation.

1. **Indexing, the primary filter.** Confirm the exact title and ISSN appear in Scopus
   (Elsevier source list) and/or Web of Science (Clarivate Master Journal List). Also
   check Scopus's discontinued-sources list: removal for quality reasons is a serious
   negative signal that a current listing can hide.
2. **ISSN record.** portal.issn.org confirms the registered publisher, country, and
   first issue. This is how the 2024 founding date and publisher identity were
   established in the case that prompted this section.
3. **DOAJ**, for open access venues: inclusion signals vetted editorial practice.
4. **COPE membership** for the publisher, and whether stated ethics policies exist and
   are specific rather than boilerplate.
5. **Editorial board spot-check.** Pick two board members, find their institutional
   pages, confirm the affiliation is real and, where possible, that the appointment is
   acknowledged.
6. **Read the last two issues.** Does the journal publish work of the kind and quality
   you intend to submit? This doubles as the scope-fit check from Section 5.
7. **Archiving and DOIs.** Registered DOIs (Crossref) and a preservation arrangement
   (CLOCKSS, Portico, or a national library deposit) indicate permanence.
8. **Think.Check.Submit.** The standing community checklist; use it as the final pass.

A venue that fails filter 1 requires an affirmative reason to proceed. New,
society-backed journals with credible boards can be worth supporting before indexing
arrives, but that is a deliberate choice, not a default.

### 6.4 Standing procedure when an invitation arrives

1. Note whether the paper named is under review elsewhere. If yes, the answer is no,
   and no further evaluation is needed.
2. Do not reply. A reply confirms a live address and multiplies future volume. Do not
   click unsubscribe links in suspect mail.
3. If the venue is plausibly legitimate and the paper is genuinely free, run 6.3 before
   any response.
4. Record the outcome. One line in the citation ledger or handoff is enough, so the same
   solicitation is not re-evaluated in six months.

### 6.5 Why this matters specifically for the IPIS program

- **Preprint scraping is the expected cost of a deliberate choice.** IPIS posts preprints
  (SSRN via Elsevier) for the DOI, the priority date, and early citation. Predatory
  publishers harvest preprint servers, so solicitation volume will rise as M2 through M5
  appear. Observed once already: SSRN registered M1 on 2026-07-25 and the invitation arrived on
  2026-07-27, quoting the title in SSRN's title case. This is noise to filter, not a reason to
  stop preprinting.
- **The program's targets are indexed venues.** JPC, CACE, RESS, IECR, ChemEngSci and
  their peers. Every IPIS paper belongs in a venue that a PhD committee, a hiring panel,
  and a future book publisher all recognize without explanation.
- **A predatory listing is a permanent liability**, not a neutral extra line: it burns the
  manuscript for legitimate publication, and on a CV aimed at a US doctoral program it
  invites questions about judgment that no amount of good science later erases.
- **Volume is not the goal.** The charter's mandate is field-defining work, and that is
  measured by what other researchers build on, never by publication count. A paper placed
  in a venue no practitioner reads has, for program purposes, not been published.

## 7. Prose register (MIT/Harvard standard = clarity, not ornament)

- Lead every section with its point; the reader should never hunt for the claim.
- No em-dashes as a stylistic tic (they read as machine-generated); use the punctuation
  the sentence wants. No filler intensifiers (precisely, crucially, deliberately as
  reflex). Vary sentence rhythm. The goal is a sentence that a skeptical expert reads
  once and cannot misunderstand.
- Define the technical term, then explain it; never skip the grounding to sound
  accessible, never hide behind jargon to sound rigorous.
- Tables and figures are self-contained: a reader skimming only the captions should get
  the argument.

## 8. The program view (the actual path to field-defining work)

- No single paper is field-defining; a *program* is. IPIS M1->M5 plus the plantwide
  generalization is the unit that matters. Each paper must earn its novelty the way M1
  finally did: a specific, falsifiable, demonstrated claim. Hold every one to it.
- A paper that opens a method others adopt outweighs a paper with a larger one-time
  result. Optimize for the contribution that becomes other people's tool.

## 9. Lessons from peer review (derived from `docs/reviews/REVIEW_REGISTER.csv`)

Each line is a failure that reached a reviewer, stated as the rule that would have stopped it.

- **L1. Write methods from the code, never from memory.** Diff every protocol description
  against its implementation before submission. (A3: S3.2 described leave-one-block-out;
  the code ran forward-chaining TimeSeriesSplit.)
- **L2. Identification needs matched controls.** Vary exactly one factor on the same
  process, target, estimator and split. A cross-dataset contrast illustrates; it does not
  identify. (A12: three of four reviewers, independently.)
- **L3. Apply your own stated rules to your own tables before a reviewer does.** (A1: the
  one-SE rule selected k = 1; the paper deployed k = 4.)
- **L4. Do the sample-size arithmetic before writing a precision claim.** (A5: a 0.006
  coverage spread at n = 300 is 0.35 binomial standard errors.)
- **L5. Every data-dependent choice is made on the training partition only**: lags,
  targets, thresholds, screens that consult labels. (A9.)
- **L6. A property the paper claims must be exercised by the experiment that produces the
  reported numbers.** Correct software is not evidence. (A2: the pairing rule lived in
  `service.py`; Table 3 came from a loop that never used it.)
- **L7. Re-sweep the literature immediately before submission.** In fast fields directly
  relevant work can appear within weeks (arXiv 2609.07251 appeared three weeks before the
  planned resubmission and removed one candidate contribution).
- **L8. Marginal metrics can hide dynamics.** Report distributional and local diagnostics
  beside every marginal number. (Pilot: marginal coverage 0.900 with 55 % infinite
  intervals.)
- **L9. A pilot's simplification must not manufacture its effect.** Check the mechanism
  against the production implementation before interpreting. (Pilot: a nominal-scale
  quantile created artifactual infinite intervals under drift.)
- **L10. Stamp only dates you can verify.** Record "TBC" rather than an inferred date.
- **L11. Take a paper's status from the editorial email, never from a status table or memory.**
  M4 was desk-rejected on 2026-07-14 and stayed "under review" in the ledger, README and two
  governance documents for 87 days. Re-derive every status from the publisher's emails at each
  session start that touches it, and record the email's timestamp.

---
*Standard adopted 2026-06-29. Amended 2026 (Section 6, venue integrity); 2026-09-28 (Section 9, peer-review lessons).
Revisit after each review cycle; every reviewer objection that lands, and every
solicitation that tests the rules, is a gap in this list to close.*
