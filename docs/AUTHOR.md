# Canonical author details (all IPIS papers)

Every paper, cover letter, submission form and EM profile uses exactly these strings. Any session
writing front matter copies from this file, never from another paper, and runs the check at the
bottom before a submission or a proof is approved.

There are two dated blocks. **The block of 2026-11-18 is used on N1 and on every paper submitted
from that date.** Decided by Bien on 2026-11-18 (N1 session); the corrected N1 presubmission email
of 7 November was already signed with this block (the first, of 4 November, named the same
university with another city). The block of 2026-10-09 stays on
everything published or submitted with it (M2 as published, RESS 113634) and on live sources of
papers not yet resubmitted; Bien decides per paper at its next submission.

## The block of 2026-11-18 (current)

| Field | Value |
|---|---|
| Byline name | Bien Don Busico |
| Affiliation | University of the Philippines Diliman, Quezon City, Philippines |
| Affiliation (LaTeX) | `University of the Philippines Diliman, Quezon City, Philippines` |
| Corresponding e-mail | bienbusico@gmail.com |
| ORCID | 0009-0006-7755-2470 (https://orcid.org/0009-0006-7755-2470) |
| Authorship | sole author and corresponding author |

Rules:
- The byline is the full name, "Bien Don Busico", as on the ORCID record and the Editorial Manager
  profile. The IEEE short form is "B. D. Busico".
- "University of the Philippines Diliman, Quezon City, Philippines": the Diliman campus is in
  Quezon City (general knowledge, not checked against a university source). Indexers match the
  string, so one form only.

## The block of 2026-10-09 (superseded for new submissions)

| Field | Value |
|---|---|
| Byline name | Bien Busico |
| Affiliation (Unicode) | Mapúa Malayan Colleges Mindanao, Davao City, Philippines |
| Affiliation (LaTeX) | `Map\'ua Malayan Colleges Mindanao, Davao City, Philippines` |
| Affiliation (ASCII fallback) | `Mapua Malayan Colleges Mindanao, Davao City, Philippines`, only in a form field that rejects diacritics |

Its rules still hold wherever it is used: "Colleges", plural ("Malayan College Mindanao" is
retired); "Davao City, Philippines" without "Davao del Sur"; the accent kept (Mapúa) wherever the
system accepts it. Decided by Bien on 2026-10-09; the evidence for the plural was the
institution's website and the encyclopedia entry.

## Ready-to-paste front matter (block of 2026-11-18)

elsarticle (Elsevier: N1, and M2, M4, M5 when resubmitted with this block):
```latex
\author{Bien Don Busico}
\address{University of the Philippines Diliman, Quezon City, Philippines}
\ead{bienbusico@gmail.com}
```

IEEEtran:
```latex
\author{Bien~Don~Busico%
\thanks{B. D. Busico is with the University of the Philippines Diliman, Quezon City, Philippines
(e-mail: bienbusico@gmail.com).}}
```

Cover-letter sign-off:
```
Bien Don Busico
University of the Philippines Diliman, Quezon City, Philippines
bienbusico@gmail.com
ORCID 0009-0006-7755-2470
```

## Where the same details live outside the repo (Bien updates these; the repo cannot)

| Place | What to set | Why it matters |
|---|---|---|
| Elsevier EM profile at JPROCONT, and every journal used next | name "Bien Don Busico"; affiliation as in the 2026-11-18 block; ORCID linked | production takes the published affiliation and ORCID link from the profile and the manuscript |
| ORCID record, Education/Employment | "University of the Philippines Diliman" | Scopus and Crossref author matching |
| Wiley ReX / IEEE ScholarOne profiles (M3 venues) | same | next M3 submission |

## What is frozen and is not edited

Files that record what was actually sent keep the strings they were sent with:
every `paperN/` directory in this public repo (each one is a paper's frozen as-submitted copy, so
`paper3/` keeps the singular form and is excluded from the check; see `docs/PAPER_LIFECYCLE.md`),
`paper3/submission_R1/` in the private repo, N1's records of what was sent
(`paper/N1_PRESUBMISSION_JPC.md`) and its outline, dated entries in `docs/HANDOFF.md`,
`docs/CITATION_LEDGER.md` Section 6 and `docs/reviews/`, and any submitted `.docx`
(regenerated from its `.md` source at the next submission). Every live source (LaTeX, bib,
cover-letter `.md`, EM-flat variant, submission sheet) carries one of the two dated blocks, and
N1's sources carry the block of 2026-11-18.

## Check

```
python scripts/check_author_block.py
```

From the private repo: `python ../IPIS/scripts/check_author_block.py`. Exits 1 and lists
file:line for any live source that uses a retired affiliation form, a different e-mail, an
`\address` that is neither dated block's, a byline of one block with the other block's address,
or, in the private repo, an N1 source (`paper/`) with the block of 2026-10-09. It also runs in CI
on every push (`.github/workflows/ci.yml`) and as a local pre-commit hook.
