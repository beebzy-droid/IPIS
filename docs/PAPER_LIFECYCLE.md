# Paper lifecycle: which repo holds which version

**Read this before touching any manuscript.** It is the protocol that keeps the public IPIS repo
compliant with the publishers' agreements while the papers are worked on. It also tells each
module session where its paper lives and how the two repos stay in step.

Adopted 2026-10-09 by Bien, after signing the subscription Journal Publishing Agreement for M2
(RESS 113634). The compliance reading below is ours, not legal advice.

## 1. The two repositories

| Repo | Visibility | Holds | Path on Bien's machine |
|---|---|---|---|
| `beebzy-droid/ipis` | **public** | code, tests, docs, evidence, figures, and a frozen copy of each manuscript **as first submitted** | `C:\Users\yubyu\Projects\IPIS` |
| `beebzy-droid/ipis-papers` | **private** | every manuscript's working copy: revisions, accepted versions, proofs, response letters, decision letters, publisher correspondence | `C:\Users\yubyu\Projects\ipis-papers` |

Clone them as siblings. Some scripts in IPIS take paths into `..\ipis-papers`, and the proof tools
are run with one repo as the working directory and the other as an argument.

## 2. The rule

| Version of a paper | Public IPIS | Private ipis-papers | Why |
|---|---|---|---|
| **As first submitted** (a "preprint": the author's version before peer review) | **yes, permanently** | yes (working copy) | Elsevier's agreement: "Publicly share the Preprint anywhere, at any time." Once published, link it to the article DOI |
| Revisions, response letters, reviewer reports, decision letters | no | yes | Peer-review material is confidential; a revision is no longer the preprint |
| **Accepted manuscript** (post-review, pre-typesetting) | **no** | yes | Immediate public sharing is limited to a non-commercial personal homepage or blog, or an arXiv/RePEc preprint update. After the embargo it extends to non-commercial platforms and to commercial sites holding an Elsevier hosting agreement. GitHub is neither. For M2 the embargo is **24 months** |
| Proof, published article | no | yes | The published article may only be shared privately (teaching, conferences, known colleagues) |
| Code, evidence JSONs, figure generators, the Zenodo deposit | **yes** | no | The agreement leaves the author all rights in Supplemental Materials and Research Data and takes only a non-exclusive licence |

**Reading older entries.** Dated entries in `docs/HANDOFF.md`, `docs/CITATION_LEDGER.md` and
`docs/reviews/` predate this split. Any `paperN/...` or `docs/module2/{revision,proof}/...` path in
them means that file in the private `ipis-papers` repo, unless it is one of this repo's frozen
preprints. Those entries are history and are not rewritten.

Two hard rules:

1. **Never edit a frozen preprint in IPIS.** The policy allows the preprint to be public only as
   submitted; it "should not be added to or enhanced in any way". Fixes, including the author block,
   belong to the next submitted version, not to the frozen copy. `paper3/` therefore still reads
   "Mapúa Malayan College Mindanao" (singular) and is excluded from
   `scripts/check_author_block.py`.
2. **Never copy restricted text into IPIS**, in any file: verbatim reviewer comments, response-letter
   text, accepted or published manuscript prose, or long quotations of a revised section. Paraphrase
   in `docs/reviews/REVIEW_REGISTER.csv` instead. Short technical phrases inside code and docstrings
   are fine.

## 3. Where each paper stands (2026-10-09)

| Paper | Module | Status | Frozen preprint in IPIS | Working copy in ipis-papers |
|---|---|---|---|---|
| 1 | M1 soft sensor | rejected after review at JPC; in revision as N1 | `paper/` (submitted 2026-06-12) | `paper/`, where all N1 work goes |
| 2 | M3 RTO | paused after four desk rejections | `paper2/` (CJCE and TCST packages) | `paper2/` |
| 3 | M2 SCC | **accepted at RESS 2026-10-09**, in production | `paper3/` (submitted 2026-06-30, 18 files) | `paper3/` with `submission_R1/`, plus `docs/module2/revision/` and `docs/module2/proof/` |
| 4 | M4 integration | under review at CACE | `paper4/` (submitted 2026-06-30) | `paper4/`, where the revision goes |
| 5 | M5 dynamic / horizon | drafting, never submitted | **none yet** | `paper5/`; it returns to IPIS when it is submitted |

## 4. What each session does

**Starting work on a paper:** open `ipis-papers`, not IPIS. Read `docs/OPEN_ITEMS.md` and
`docs/AUTHOR.md` in IPIS first; they stay public because they contain no manuscript text.

**At each lifecycle event:**

| Event | Action |
|---|---|
| **New submission** (first time, or a paper resubmitted to a new venue after rejection) | Copy the submitted package from `ipis-papers` into IPIS under its `paperN/` directory, commit it there as the frozen preprint, and note the date in `docs/CITATION_LEDGER.md`. From that moment the IPIS copy is read-only |
| **Revision requested** | Work only in `ipis-papers`. Nothing goes into IPIS except paraphrased register rows and status lines |
| **Accepted** | Freeze the upload set in `ipis-papers` under `paperN/submission_R*/`. Update status in IPIS: README, `PROJECT_STRUCTURE.md`, `docs/HANDOFF.md`, `docs/CITATION_LEDGER.md`, the module spec |
| **Proof** | Run the proof tools (section 5) against the accepted manuscript in `ipis-papers`. The checklist lives at `ipis-papers/docs/module2/proof/PROOF_CHECKLIST.md` |
| **Published** | Put the full reference in `docs/CITATION_LEDGER.md` and run its propagation domino. Add the DOI to the frozen preprint's entry in the ledger, so the public preprint is linked to the article. Do **not** add the published text to IPIS |
| **Embargo ends** (M2: 2028-10, 24 months from publication) | The accepted manuscript may then go into an institutional repository, still not onto GitHub |

**Rejected without a revision:** the paper reverts to preprint status, so the IPIS copy may stay and
be updated when it is resubmitted elsewhere.

## 5. Tools that span both repos

Canonical copies live in `IPIS/scripts/`. Run them from the private repo when they read a manuscript:

```
cd C:\Users\yubyu\Projects\ipis-papers
python ../IPIS/scripts/proof_check.py --accepted paper3/submission_R1/scc_paper.docx --proof proof.pdf
python ../IPIS/scripts/zenodo_scc_v101.py --article-doi 10.1016/j.ress.2026.113634 --volume NNN --article-number 113634 --year 2026 --frozen paper3/submission_R1/scc-code.zip
python ../IPIS/scripts/check_author_block.py
python scripts/r13_terminology_sweep.py --audit        # this one lives in ipis-papers
```

`r13_terminology_sweep.py` moved into `ipis-papers/scripts/` on 2026-10-09: it holds the exact
revised sentences it enforces, which is accepted-manuscript prose and must not be public.

`check_author_block.py` works in either repo: it scans whatever repo is the working directory.

## 6. What stays public, and why that matters

The code, the tests, the evidence JSONs, the figure generators and the Zenodo deposit
(doi:10.5281/zenodo.23211276) are all public and unaffected. Anyone can reproduce every figure and
table. The published article is reachable by DOI, and the version as first submitted is in this
repo. That is a complete open-science record within what the agreements permit.
