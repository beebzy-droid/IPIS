# Canonical author details (all IPIS papers)

Every paper, cover letter, submission form and EM profile uses exactly these strings. Any session
writing front matter copies from this file, never from another paper, and runs the check at the
bottom before a submission or a proof is approved.

Decided by Bien on 2026-10-09 (affiliation; byline "Bien Don Busico" to match his ORCID record).
The affiliation evidence: the institution's website and the
encyclopedia entry both use the plural, "Colleges".

## The block

| Field | Value |
|---|---|
| Byline name | Bien Don Busico |
| Name parts (for publisher forms and XML) | given names "Bien Don"; family name "Busico" |
| Initials in reference lists | B.D. Busico (Elsevier), B. D. Busico (IEEE); BibTeX `author={Busico, Bien Don}` |
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
- The byline is "Bien Don Busico", the name on Bien's ORCID record. "Bien Busico" is retired.
- "Don" is a given name, not the Spanish honorific and not part of the surname. Every form that
  splits the name (EM profile, CRediT form, proof corrections, Zenodo creators) must put "Bien
  Don" in given names and "Busico" in family name; otherwise indexers file the papers under
  "Don Busico" or drop the D.
- Accepted M2 (JRESS-D-26-04700R1) and M4 under review (CACE-D-26-01079) were submitted as "Bien
  Busico": M2 is corrected at proof (PROOF_CHECKLIST C8), M4 in its revision or proof.

## Ready-to-paste front matter

elsarticle (Elsevier: M1/N1, M2, M4, M5):
```latex
\author{Bien Don Busico}
\address{Map\'ua Malayan Colleges Mindanao, Davao City, Philippines}
\ead{bienbusico@gmail.com}
```

IEEEtran:
```latex
\author{Bien~Don~Busico%
\thanks{B. D. Busico is with Map\'ua Malayan Colleges Mindanao, Davao City, Philippines
(e-mail: bienbusico@gmail.com).}}
```

Cover-letter sign-off:
```
Bien Don Busico
Mapúa Malayan Colleges Mindanao, Davao City, Philippines
bienbusico@gmail.com
ORCID 0009-0006-7755-2470
```

## Where the same details live outside the repo (Bien updates these; the repo cannot)

| Place | What to set | Why it matters |
|---|---|---|
| Elsevier EM profile, every journal site used (RESS, CACE, JPROCONT) | first name "Bien Don", last name "Busico"; affiliation as above; ORCID linked | production takes the published affiliation and ORCID link from the profile and manuscript; M4 is under review with the singular form and "Bien Busico" |
| ORCID record, Employment/Education | name already "Bien Don Busico" (Bien, 2026-10-09); organization "Mapúa Malayan Colleges Mindanao" | Scopus and Crossref author matching |
| Wiley ReX / IEEE ScholarOne profiles (M3 venues) | same | next M3 submission |
| Zenodo record 10.5281/zenodo.23211276, creator field | "Busico, Bien Don" (metadata edits do not need a new version) | the deposit is cited by the article |

## What is frozen and is not edited

Files that record what was actually sent keep the strings they were sent with:
`paper3/submission_R1/` (the accepted M2 upload set, singular form), dated entries in
`docs/HANDOFF.md`, `docs/CITATION_LEDGER.md` Section 6 and `docs/reviews/`, and any submitted
`.docx` (regenerated from its `.md` source at the next submission). Every live source (LaTeX, bib,
cover-letter `.md`, EM-flat variant, submission sheet) carries the canonical block.

## Check

```
python scripts/check_author_block.py
```

Exits 1 and lists file:line for any live source that uses a retired affiliation form, a retired
byline, or a different e-mail. It also runs in CI on every push (`.github/workflows/ci.yml`) and as a local pre-commit hook.
