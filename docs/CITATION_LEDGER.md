# Citation ledger and cross-paper propagation protocol

**This file is the single source of truth for cross-paper citation metadata** (bibkey, title,
venue, manuscript ID, status) for the IPIS paper series. Every paper's self-citations
(`busico_mN`) in its own `references.bib` must match the canonical entry below. When an upstream
paper changes its title, venue, or ID during review, update THIS file once, then propagate
downstream using the protocol in this document.

Why this exists: the papers cite each other, all are under review, and a reviewer-driven change to
one paper (title reframe, venue transfer, new ID) silently invalidates the self-citations in every
downstream paper. Chasing those by hand across `references.bib`, `README.md`, status docs, and
working drafts is lossy and token-expensive. This ledger plus the protocol makes propagation
mechanical and one-directional.

Last updated: 2026-10-09 (affiliation decided, canonical author block `docs/AUTHOR.md`; open items per session in `docs/OPEN_ITEMS.md`. Earlier the same day: M2 ACCEPTED at RESS as JRESS-D-26-04700R1: `busico_m2` -> `@article`, in press, synced into paper4/paper5; M1 status corrected to rejected-after-review per the 2026-09-28 review register; open items for M1 and M5 owners in Section 6).

## 1. Canonical ledger

| bibkey | Module | Canonical title | Venue | Manuscript ID | Status | Source dir |
|---|---|---|---|---|---|---|
| `busico_m1` | M1 soft sensor | When does a calibrated soft sensor keep its promise? A negative-control study of validity without accuracy under drift and delayed labels | Journal of Process Control (transfer from CACE) | JPROCONT-D-26-00618 (orig. CACE-D-26-00944) | rejected after peer review (decision on or before 2026-09-28); in revision as N1 | `paper/` |
| `busico_m2` | M2 prognostics (SCC) | Similarity-Calibrated Conformal prediction: data-free coverage guarantees for remaining-useful-life intervals under operating-regime transfer | Reliability Engineering & System Safety | JRESS-D-26-04700R1 (resub. of JRESS-D-26-04509) | **accepted 2026-10-09**; in production, proof pending | `paper3/` |
| `busico_m3` | M3 RTO | Safe real-time optimization of a distillation column under feed-composition uncertainty: a comparative study of distribution-free constraint back-offs | none (paused) | none (rejected: CJCE 1404930, TCST 26-0876, CACE-D-26-01040, JPROCONT-D-26-00565) | paused; Wiley Transfer Desk offer pending | `paper2/cjce/` |
| `busico_m4` | M4 integration | A composed coverage certificate for closed-loop process operation: certified joint product-quality and equipment-survival guarantees under feedback | Computers & Chemical Engineering | CACE-D-26-01079 | under review | `paper4/` |
| `busico_m5` | M5 dynamic / horizon | Horizon-wide safety guarantees for closed-loop process operation via adaptive conformal calibration | IEEE Trans. Control Systems Technology (target; retargeted from CACE per 2026-07-04 de-risk) | none (in prep) | `paper5/` |

Note the directory quirk: `paperN/` is numbered by authoring order, so `paper2/` = Module 3 (RTO)
and `paper3/` = Module 2 (SCC). The Module column above is authoritative.

## 2. Dependency map (who cites whom)

Citation is strictly downstream: a paper cites only EARLIER modules, never later ones. So a change
to module N can only affect modules > N. This is what makes the domino safe and finite.

| Changed paper | Downstream papers that cite it (blast radius) |
|---|---|
| `busico_m1` | `busico_m4`, `busico_m5` |
| `busico_m2` | `busico_m4`, `busico_m5` |
| `busico_m3` | `busico_m4`, `busico_m5` |
| `busico_m4` | `busico_m5` |
| `busico_m5` | none (terminal) |

Propagation order: **M1 -> M2 -> M3 -> M4 -> M5.**

## 3. Canonical .bib entries (copy-paste source)

Downstream `references.bib` files must contain exactly these for the keys they cite.

```bibtex
@misc{busico_m1,
  title={{When does a calibrated soft sensor keep its promise? A negative-control study of validity without accuracy under drift and delayed labels}},
  author={Busico, Bien Don}, year={2026}, note={Manuscript JPROCONT-D-26-00618, Journal of Process Control (transfer from CACE-D-26-00944); reframed as a negative-control study}}

@article{busico_m2,
  title={{Similarity-Calibrated Conformal prediction: data-free coverage guarantees for remaining-useful-life intervals under operating-regime transfer}},
  author={Busico, Bien Don}, journal={Reliability Engineering \& System Safety}, year={2026}, note={In press}}

@misc{busico_m3,
  title={{Safe real-time optimization of a distillation column under feed-composition uncertainty: a comparative study of distribution-free constraint back-offs}},
  author={Busico, Bien Don}, year={2026}, note={Unpublished manuscript}}

@misc{busico_m4,
  title={{A composed coverage certificate for closed-loop process operation: certified joint product-quality and equipment-survival guarantees under feedback}},
  author={Busico, Bien Don}, year={2026}, note={Manuscript CACE-D-26-01079, submitted to Computers \& Chemical Engineering}}
```

(Double braces around the title preserve capitalization under achemso/elsarticle bst. Keep them.)

## 4. The propagation protocol (the domino)

Propagation is pull-based and runs through the repo: this ledger is the single signal. The upstream
session records the change here and pushes; each downstream session, on its next run, reads this ledger
directly from the repo and reconciles its own files. No prompt is passed between sessions.

When a reviewer-driven change to paper N alters its title, venue, or manuscript ID:

**Upstream session (the paper that changed), as its LAST step after the change is committed:**
1. Update this ledger: the row in Section 1 and the `@misc` block in Section 3 for `busico_mN`.
2. Update paper N's own front matter / status / internal drafts as needed (its own concern).
3. Add an entry to Section 6 (open propagation debt) naming the blast radius from Section 2, then
   commit and push. The pushed ledger is the signal; nothing is sent to other sessions.

**Downstream session (each paper in the blast radius), on its next run:**
1. Read this ledger (verify-before-load-bearing via raw.githubusercontent.com); check Section 6 for
   open debt naming this paper.
2. Copy the canonical `@misc` entry for the changed key from Section 3 into the local `references.bib`
   (replace the stale one). Change nothing else in the entry.
3. Grep the paper's prose and drafts for the OLD title / venue / ID strings; fix any literal occurrences.
4. Recompile; confirm 0 errors and that the References list renders the new metadata.
5. Clear the Section 6 debt for this paper once synced and pushed; record a one-line changelog entry.

**Invariant:** titles/venues/IDs live in the ledger. Other documents (README, status files) should
reference module names, not re-type titles, so there is exactly one place to change. Where a title
must appear verbatim (a paper's `references.bib`, the README publications list), it is a controlled
copy of the ledger and is synced via this protocol.

## 5. (Retired) prompt-based handoff

Earlier the upstream session emitted a fill-in sync prompt for the next session. That mechanism is
retired: sessions now read this ledger directly from the repo and self-sync per Section 4. The
canonical metadata in Sections 1 and 3, plus the open-debt list in Section 6, are the only signal; no
prompt is passed between sessions.

## 6. Open propagation debt (fix in the owning session)

**2026-10-09 third pass (author name).** Bien decided on the byline "Bien Don Busico", the name on
his ORCID record. Every canonical entry in Section 3 now reads `author={Busico, Bien Don}`, which
renders as "B.D. Busico" or "B.~D. Busico". It is synced to `paper2/` (three bibs, key
`companion2026`), `paper4/references.bib`, `paper5/references.bib`, and the bibitems inlined in
`paper4/em/main_EM.tex` (regenerated by bibtex and matched entry by entry). `busico_m2` depends on
proof correction C8 being accepted; if it is declined, set `busico_m2` back to `{Busico, Bien}`
to match the published record.

**2026-10-09 later pass (author block; open items moved).** The open items below are now tracked
per session in `docs/OPEN_ITEMS.md` (OI-01 for `busico_m1`, OI-10 for `busico_m5`), which is
what each session reads first. Corrections to the flags in the earlier 2026-10-09 entry:
- Affiliation: **resolved.** Bien decided on the plural "Mapúa Malayan Colleges Mindanao, Davao City,
  Philippines". It is canonical in `docs/AUTHOR.md` and applied to every live source (CI check
  `scripts/check_author_block.py`). It is not a citation field, so there is no domino.
- `paper5/` figures: **not missing.** `main_EM.tex` is the flat EM variant and is figure-less by
  design; the PNGs are in `docs/module5/figures/`. Both variants build with 0 errors once the
  figures are on the path (OPEN_ITEMS OI-11).
- `busico_m1`: the dead ID also reaches M3 under the key `companion2026` (three `paper2/` bibs),
  which the earlier entry missed. Grep by author, not by key (rule from the 2026-06-30 pass).

**2026-10-09 pass (M2 accepted at RESS).** Upstream change: `busico_m2` is accepted, so it is
cited as a journal article in press. The manuscript ID is dropped from the canonical entry,
because a published reference cites the journal, not the Editorial Manager number; the ID stays in
Section 1 for traceability.

Resolved this pass:
- Ledger Section 1 (M2 row) and Section 3 (`busico_m2` -> `@article`, `note={In press}`).
- `paper4/references.bib`, `paper5/references.bib`: `busico_m2` synced. `paper4/em/main_EM.tex`:
  its inlined `busico_m2` bibitem regenerated by bibtex from the new entry. Both papers rebuilt;
  the reference renders as "... Reliability Engineering & System Safety (2026). In press."
- Status surfaces: `README.md` (M1 and M2 rows and publications), `PROJECT_STRUCTURE.md`,
  `docs/module2/spec.md`, `docs/HANDOFF.md` (Section 0.5 banner, papers table now with a Status
  column, Paper 3 notes, module list, changelog), `docs/module1/VENUE_STRATEGY_N1.md` (dated
  addendum), `docs/reviews/REVIEW_LOG.md` and `REVIEW_REGISTER.csv` (M2 events and comments).

Next M2 domino, at proof: when the proof assigns volume, article number and DOI, replace the
`busico_m2` entry in Section 3 with the full reference and re-sync paper4 and paper5. Blast radius
unchanged: M4, M5.

Flagged for the owning sessions, NOT changed this pass:
- `busico_m1` canonical note still names JPROCONT-D-26-00618, which was rejected after review, so
  M4 and M5 currently cite a dead manuscript ID. The M1 session should replace it ("Unpublished
  manuscript", as done for `busico_m3`, or the N1 title once settled) and propagate.
- `busico_m5` row reads "IEEE TCST target, in prep"; project memory has said "submitted to CACE";
  HANDOFF entries from July flag the same conflict. The M5 session should confirm and correct.
- `paper5/` does not build clean from the repo: `fig1_two_arm.png`, `fig2_deadtime.png` and
  `fig3_gamma_union.png` are referenced but not committed (pre-existing, unrelated to this pass;
  the bibliography renders correctly).
- Affiliation: every paper's front matter reads "Mapua Malayan College Mindanao". The
  institution's own website brands itself "Mapua Malayan Colleges Mindanao" (plural; its footer
  uses the singular) and the encyclopedia entry uses the plural. One program-wide decision is
  needed; for M2 the proof is the last chance to change it.


**Status after the 2026-06-30 full hygiene pass: cross-citation debt CLEARED.** Every paper's
self-citations and every status surface match Sections 1 and 3 as of this date, verified by a
repo-wide audit (all `references.bib`, both cover letters, paper prose, README, HANDOFF, ADR-016,
the module-4 spike).

Resolved this pass (M4 received CACE-D-26-01079):
- Ledger Sections 1 and 3: `busico_m4` -> CACE-D-26-01079, under review.
- `paper5/references.bib`: `busico_m4` -> new title + CACE + CACE-D-26-01079; `busico_m2` ->
  canonical title + JRESS-D-26-04700 (both had been stale).
- `paper5/cover_letter.md`: companion list refreshed (M1 -> JPROCONT-D-26-00618/JPC; M2 -> 04700;
  M4 -> CACE-D-26-01079, under review at this journal).
- `paper2/references.bib` `@unpublished{companion2026}` (M3's cite to M1): refreshed to the current
  M1 title + Journal of Process Control + JPROCONT-D-26-00618. This key is NOT `busico_m1`, which is
  why earlier `busico_*` sweeps missed it. **Future audits must grep self-cites by author, not key.**
- `README.md`, `docs/HANDOFF.md` papers table: M4 -> CACE-D-26-01079/under review; M1 row -> JPC/
  JPROCONT-D-26-00618; M2 row -> JRESS-D-26-04700.
- `docs/module4/formalization-spike.md`, `docs/architecture/decisions/ADR-016-*.md`: cross-ref IDs
  refreshed (M1 -> JPROCONT-D-26-00618, M2 -> JRESS-D-26-04700).

Citation invariants verified clean:
- M1 (`paper/`): cites no earlier module; own title canonical.
- M2 (`paper3/scc_refs.bib`): cites no earlier module.
- M3 (`paper2/`): cites M1 via `companion2026` (now current).
- M4 (`paper4/`): cites M1/M2/M3 via `busico_m1/m2/m3` (all current).
- M5 (`paper5/`): cites M1/M2/M3/M4 via `busico_m1..m4` (all current).

Historical strings intentionally retained (NOT debt): transfer notes reading "(transfer from
CACE-D-26-00944)" / "(resub. of JRESS-D-26-04509)"; dated HANDOFF changelog entries; the cover-letter
sentences that own the IECR transfer history. These cite prior IDs as history and are correct.

Still open (non-citation, no domino):
- Affiliation string: STANDARDISED this pass to "Mapua Malayan College Mindanao, Davao City,
  Philippines" across all paper front matter (M1/M2 already; M3/M4/M5 updated), all cover-letter
  sign-offs, both EM-flat variants, and the M2 outline note. M3 (CACE-D-26-01040) and M4
  (CACE-D-26-01079) are under review under the old "Quezon City" string, so update the affiliation in
  their EM author-metadata field (carries to revision); the repo now holds the corrected version. Not
  a citation field.

Reminder: when M5 receives a manuscript ID, update `busico_m5` (Sections 1 and 3). Its blast radius
is empty (terminal), so no downstream sync follows.
