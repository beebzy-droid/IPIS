# IPIS program charter

The governing document for the IPIS paper series and the PhD thesis it becomes. It sets
the standard every paper is held to and the end-goals that standard serves. It binds with
`docs/THESIS_STANDARDS.md` (the how) and `docs/CITATION_LEDGER.md` (the cross-paper
mechanics). Where this charter and a convenient shortcut conflict, the charter wins.

## 0. The mandate (on record)

Every paper and the thesis in the IPIS program must be:
- **MIT/Harvard thesis grade** in rigor and prose: organized around one falsifiable
  claim, defended by reproducible evidence, written so a skeptical expert reads it once
  and cannot misunderstand it.
- **Highest defensible novelty**: a methodological contribution that opens a tool others
  adopt, not an incremental application. Novelty is claimed only to the exact extent the
  paper's own evidence defends it (see THESIS_STANDARDS S2).
- **Aimed at a genuine breakthrough in process systems engineering and manufacturing**:
  the work must matter to a plant, not only to a benchmark.
- **Maximized for acceptance**: correct journal fit, correct format, honest framing,
  the rejection-history owned rather than hidden.

The PM (Claude, acting as a process-systems-engineering PhD advisor) holds the author to
this on every deliverable, flags overclaiming before a reviewer does, and refuses to
manufacture novelty the evidence will not carry. Driving toward the goal does not mean
inflating the claim; it means doing the work that earns the claim.

## 1. The end-goals, in order of nearness

1. **The five-paper program + thesis.** M1->M5: calibrated soft sensing, transferable
   prognostics, health-constrained RTO, a composed coverage certificate, horizon-wide
   guarantees. The thesis is the program, not any one paper. Each paper must stand alone
   AND advance the composition.
2. **Industry relevance and application.** The certificate must run on a real plant's
   DCS data, not only DWSIM/TEP. The roadmap's plantwide generalization and real-plant
   validation are the credibility capstone; treat them as required, not optional.
3. **A book.** The program, once complete, is a monograph: "distribution-free guarantees
   for process operation." A book is what converts five papers into a field's reference.
   Structure the papers so their union is a book outline (each module = a part).
4. **Field-defining work / Nobel-trajectory thinking.** Not a paper to write now; a
   direction to keep open. The honest path: a method others adopt as standard practice,
   then a breakthrough that changes what plants can guarantee about their own safety and
   efficiency. The PM's job is to notice, at each step, which results are tool-shaped
   (others will build on them) versus one-time, and to steer toward the former.

## 2. What "breakthrough" means here (so it is not a slogan)

A breakthrough in this program is a result that changes what a process engineer can
*guarantee*, not merely predict. The unifying thread is distribution-free, finite-sample
safety guarantees that survive the conditions real plants have and benchmarks do not:
drift, delayed and infrequent labels, regime change, and equipment degradation. The
negative-control habit (THESIS_STANDARDS S3) is the engine: each paper should isolate
*why* its guarantee holds by exhibiting the case where the causal ingredient is removed
and the guarantee fails. A guarantee whose source is proven is adoptable; a correlation
that happens to work is not.

## 3. Per-paper gate (every paper passes all before submission)

1. One-sentence falsifiable claim stated; the experiment that would refute it named.
2. Novelty swept against the literature at headline strength; every "first/novel/optimal"
   cashable against a specific result; no claim a reviewer can refute with one citation.
3. A negative control or an equivalent attribution argument present.
4. Every number regenerates from a single command; pipeline reproduced on a second
   machine; limits reported as results.
5. Journal fit confirmed against the target's aims AND last two issues; manuscript built
   in the target's production format within its page cap.
6. Industry-relevance sentence: what a plant does differently because of this result.
7. Program-fit sentence: how this paper advances the M1->M5 composition and the book.
8. Cross-paper metadata synced via CITATION_LEDGER before submission.

## 4. The PM's standing instructions

- Hold every deliverable against THESIS_STANDARDS.md and this charter without being asked.
- Option-scale decisions, recommend, let the author ratify; never inflate to please.
- Verify before load-bearing (repo state via raw URLs; journal scope via live search).
- Catch the overclaim, the stale citation, the format trap, the wrong-venue risk early.
- Treat every landed reviewer objection as a permanent addition to the standards.
- Keep the long game visible: at each result, ask "is this tool-shaped, and does it move
  the plant?" Steer accordingly.

---
*Charter adopted 2026-06-29. Author: Bien Busico. PM: Claude (process-systems-engineering
advisor mode). Revisit at each module boundary and after each review cycle.*
