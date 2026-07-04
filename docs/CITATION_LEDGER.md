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

Last updated: 2026-06-30 (M4 received CACE-D-26-01079; FULL downstream hygiene pass: busico_m4 + busico_m2 propagated into paper5 bib/cover letter, paper2 companion2026 -> JPC M1, README/HANDOFF tables + spike + ADR-016 refreshed, Section 6 cleared).

## 1. Canonical ledger

| bibkey | Module | Canonical title | Venue | Manuscript ID | Status | Source dir |
|---|---|---|---|---|---|---|
| `busico_m1` | M1 soft sensor | When does a calibrated soft sensor keep its promise? A negative-control study of validity without accuracy under drift and delayed labels | Journal of Process Control (transfer from CACE) | JPROCONT-D-26-00618 (orig. CACE-D-26-00944) | under review | `paper/` |
| `busico_m2` | M2 prognostics (SCC) | Similarity-Calibrated Conformal prediction: data-free coverage guarantees for remaining-useful-life intervals under operating-regime transfer | Reliability Engineering & System Safety | JRESS-D-26-04700 (resub. of JRESS-D-26-04509) | under review (deliverable-first restructure) | `paper3/` |
| `busico_m3` | M3 RTO | Safe real-time optimization under unmeasured disturbances: a finite-sample, distribution-free constraint-satisfaction guarantee | IEEE Trans. Control Systems Technology | 26-0876 | Received (prescreen) | `paper2/tcst/` |
| `busico_m4` | M4 integration | A composed coverage certificate for closed-loop process operation: certified joint product-quality and equipment-survival guarantees under feedback | Computers & Chemical Engineering | CACE-D-26-01079 | under review | `paper4/` |
| `busico_m5` | M5 dynamic / horizon | Horizon-wide safety guarantees for closed-loop process operation via adaptive conformal calibration | Computers & Chemical Engineering (target) | none (in prep) | `paper5/` |

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
  author={Busico, Bien}, year={2026}, note={Manuscript JPROCONT-D-26-00618, Journal of Process Control (transfer from CACE-D-26-00944); reframed as a negative-control study}}

@misc{busico_m2,
  title={{Similarity-Calibrated Conformal prediction: data-free coverage guarantees for remaining-useful-life intervals under operating-regime transfer}},
  author={Busico, Bien}, year={2026}, note={Manuscript JRESS-D-26-04700, submitted to Reliability Engineering \& System Safety}}

@misc{busico_m3,
  title={{Safe real-time optimization under unmeasured disturbances: a finite-sample, distribution-free constraint-satisfaction guarantee}},
  author={Busico, Bien}, year={2026}, note={Manuscript 26-0876, submitted to IEEE Transactions on Control Systems Technology; earlier version desk-rejected as CACE-D-26-01040}}

@misc{busico_m4,
  title={{A composed coverage certificate for closed-loop process operation: certified joint product-quality and equipment-survival guarantees under feedback}},
  author={Busico, Bien}, year={2026}, note={Manuscript CACE-D-26-01079, submitted to Computers \& Chemical Engineering}}
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
