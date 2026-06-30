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

Last updated: 2026-06-30 (M2 SCC -> JRESS-D-26-04700; propagation switched to pull-based via the repo, prompt handoff retired; M4/M5 bib + HANDOFF sync pending in Section 6; M2-owned surfaces synced).

## 1. Canonical ledger

| bibkey | Module | Canonical title | Venue | Manuscript ID | Status | Source dir |
|---|---|---|---|---|---|---|
| `busico_m1` | M1 soft sensor | When does a calibrated soft sensor keep its promise? A negative-control study of validity without accuracy under drift and delayed labels | Journal of Process Control (transfer from CACE) | JPROCONT-D-26-00618 (orig. CACE-D-26-00944) | under review | `paper/` |
| `busico_m2` | M2 prognostics (SCC) | Similarity-Calibrated Conformal prediction: data-free coverage guarantees for remaining-useful-life intervals under operating-regime transfer | Reliability Engineering & System Safety | JRESS-D-26-04700 (resub. of JRESS-D-26-04509) | under review (deliverable-first restructure) | `paper3/` |
| `busico_m3` | M3 RTO | Conditionally calibrated conformal back-offs for chance-constrained real-time optimisation under unmeasured disturbances | Computers & Chemical Engineering | CACE-D-26-01040 | under review | `paper2/` |
| `busico_m4` | M4 integration | A composed coverage certificate for closed-loop process operation: unifying conformal soft sensing, calibrated prognostics, and health-constrained real-time optimization | Industrial & Engineering Chemistry Research | ie-2026-03342s | submitted | `paper4/` |
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
  title={{Conditionally calibrated conformal back-offs for chance-constrained real-time optimisation under unmeasured disturbances}},
  author={Busico, Bien}, year={2026}, note={Manuscript CACE-D-26-01040, submitted to Computers \& Chemical Engineering}}

@misc{busico_m4,
  title={{A composed coverage certificate for closed-loop process operation: unifying conformal soft sensing, calibrated prognostics, and health-constrained real-time optimization}},
  author={Busico, Bien}, year={2026}, note={Manuscript ie-2026-03342s, submitted to Industrial \& Engineering Chemistry Research}}
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

- **M2 (SCC) RESTRUCTURED + RESUBMITTED to RESS (2026-06-30): new ID JRESS-D-26-04700**
  (was JRESS-D-26-04509). Deliverable-first restructure (proofs to Appendix A, engineering
  narrative, workflow figure); no results changed. Ledger Section 1 + Section 3 now canonical.
  DOWNSTREAM SYNC PENDING (busico_m2 blast radius = M4, M5):
  `paper4/references.bib` needs the ID 04509 -> 04700 (its title is already current);
  `paper5/references.bib` needs BOTH the ID 04509 -> 04700 AND title old -> canonical.
  M4 and M5 sessions read this ledger on their next run and sync busico_m2 in their
  references.bib per Section 4 (paper4 = ID only; paper5 = ID + title).
  M2-owned surfaces SYNCED this pass (2026-06-30): README.md, PROJECT_STRUCTURE.md,
  docs/module2/spec.md (ID 04509 -> 04700) and the two internal drafts above. STILL PENDING
  (downstream-owned, pull from this ledger): `paper4/references.bib` (M4); `paper5/references.bib`
  (M5); `docs/HANDOFF.md` current-state M2 rows (M5 session - update the papers table, the
  Module 2 baseline line, and the status line to 04700; KEEP the dated changelog entries that
  mention 04509 as history).

- **M1 RETITLED + venue change (2026-06-29), now IN REVIEW at JPC as
  JPROCONT-D-26-00618.** RESOLVED this pass: `paper4/references.bib`,
  `paper5/references.bib`, and `README.md` updated to the canonical M1 title/venue (the
  M4/M5 bib `@misc` blocks now match Section 3; README M1 entry shows the JPC number).
  No stale M1 title remains on main. If the M4/M5 papers carry the old title in PROSE
  drafts (not just bib), refresh in those sessions, but the cross-citation metadata is
  synced.

- `docs/module2/scc/scc_paper_outline.md` and `docs/module2/scc/scc_theory.tex` titles RESOLVED
  (2026-06-30): refreshed to the canonical M2 title and pushed.
- Affiliation STANDARDIZED to "Mapua Malayan College Mindanao, Davao City, Philippines"
  (M1 done 2026-06-29; matches EM record for JPROCONT-D-26-00618). M2-M5 front matter
  should adopt the same string in their sessions; not a citation field, so no domino.
