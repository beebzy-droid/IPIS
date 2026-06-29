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
  format problem masquerading as a length problem — measure in the production format
  before cutting content.
- A cover letter that owns an unfavorable history (a transfer, a desk-reject) reads as
  confidence. State it plainly.

## 6. Prose register (MIT/Harvard standard = clarity, not ornament)

- Lead every section with its point; the reader should never hunt for the claim.
- No em-dashes as a stylistic tic (they read as machine-generated); use the punctuation
  the sentence wants. No filler intensifiers (precisely, crucially, deliberately as
  reflex). Vary sentence rhythm. The goal is a sentence that a skeptical expert reads
  once and cannot misunderstand.
- Define the technical term, then explain it; never skip the grounding to sound
  accessible, never hide behind jargon to sound rigorous.
- Tables and figures are self-contained: a reader skimming only the captions should get
  the argument.

## 7. The program view (the actual path to field-defining work)

- No single paper is field-defining; a *program* is. IPIS M1->M5 plus the plantwide
  generalization is the unit that matters. Each paper must earn its novelty the way M1
  finally did: a specific, falsifiable, demonstrated claim. Hold every one to it.
- A paper that opens a method others adopt outweighs a paper with a larger one-time
  result. Optimize for the contribution that becomes other people's tool.

---
*Standard adopted 2026-06-29. Revisit after each review cycle; every reviewer objection
that lands is a gap in this list to close.*
