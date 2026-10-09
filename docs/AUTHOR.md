# Canonical author details (all IPIS papers)

Every paper, cover letter, submission form and EM profile uses exactly these strings. Any session
writing front matter copies from this file, never from another paper, and runs the check at the
bottom before a submission or a proof is approved.

Decided by Bien on 2026-10-09. The affiliation evidence: the institution's website and the
encyclopedia entry both use the plural, "Colleges".

## The block

| Field | Value |
|---|---|
| Byline name | Bien Busico |
| Affiliation (Unicode) | Mapúa Malayan Colleges Mindanao, Davao City, Philippines |
| Affiliation (LaTeX) | `Map\'ua Malayan Colleges Mindanao, Davao City, Philippines` |
| Affiliation (ASCII fallback) | `Mapua Malayan Colleges Mindanao, Davao City, Philippines`, only in a form field that rejects diacritics |
| Corresponding e-mail | bienbusico@gmail.com |
| ORCID | 0009-0006-7755-2470 (https://orcid.org/0009-0006-7755-2470) |
| Authorship | sole author and corresponding author |

Rules:
- "Colleges", plural, always. "Malayan College Mindanao" (singular) is retired.
- "Davao City, Philippines". Do not add "Davao del Sur": Davao City is a highly urbanized city
  that is administratively independent of that province (general knowledge, not verified against
  a government source). Indexers match the string, so one form only.
- Keep the accent (Mapúa) wherever the system accepts it; the ASCII form is a fallback, not an
  alternative.
- The byline is "Bien Busico" on every IPIS paper (decided by Bien 2026-10-09). It is what the
  accepted M2 article (JRESS-D-26-04700R1) and M4 under review (CACE-D-26-01079) already carry, so
  no publisher correction is needed. "Bien Don Busico" is not used on IPIS papers, even though the
  ORCID record shows that full name; the ORCID iD links the papers either way.

## Ready-to-paste front matter

elsarticle (Elsevier: M1/N1, M2, M4, M5):
```latex
\author{Bien Busico}
\address{Map\'ua Malayan Colleges Mindanao, Davao City, Philippines}
\ead{bienbusico@gmail.com}
```

IEEEtran:
```latex
\author{Bien~Busico%
\thanks{B. Busico is with Map\'ua Malayan Colleges Mindanao, Davao City, Philippines
(e-mail: bienbusico@gmail.com).}}
```

Cover-letter sign-off:
```
Bien Busico
Mapúa Malayan Colleges Mindanao, Davao City, Philippines
bienbusico@gmail.com
ORCID 0009-0006-7755-2470
```

## Where the same details live outside the repo (Bien updates these; the repo cannot)

| Place | What to set | Why it matters |
|---|---|---|
| Elsevier EM profile, every journal site used (RESS, CACE, JPROCONT) | affiliation as above; ORCID linked | production takes the published affiliation and ORCID link from the profile and manuscript; M4 is under review with the singular form |
| ORCID record, Employment/Education | organization "Mapúa Malayan Colleges Mindanao" | Scopus and Crossref author matching |
| Wiley ReX / IEEE ScholarOne profiles (M3 venues) | same | next M3 submission |

## What is frozen and is not edited

Files that record what was actually sent keep the strings they were sent with:
every `paperN/` directory in this public repo (each one is a paper's frozen as-submitted copy, so
`paper3/` keeps the singular form and is excluded from the check; see `docs/PAPER_LIFECYCLE.md`),
`paper3/submission_R1/` in the private repo, dated entries in
`docs/HANDOFF.md`, `docs/CITATION_LEDGER.md` Section 6 and `docs/reviews/`, and any submitted
`.docx` (regenerated from its `.md` source at the next submission). Every live source (LaTeX, bib,
cover-letter `.md`, EM-flat variant, submission sheet) carries the canonical block.

## Check

```
python scripts/check_author_block.py
```

Exits 1 and lists file:line for any live source that uses a retired affiliation form, a retired
byline, or a different e-mail. It also runs in CI on every push (`.github/workflows/ci.yml`) and as a local pre-commit hook.
