# IPIS submission spec (cross-session reference)

Single source of truth for Elsevier Editorial Manager fields, so re-submissions never
re-derive them. Update the venue/format rows per paper.

## M1 — submission of record

- Manuscript no.: CACE-D-26-00944 (origin), transferred to Journal of Process Control
- Journal / EM: Journal of Process Control, editorialmanager.com/jprocont
- Article type: Full Length Article
- Title: When does a calibrated soft sensor keep its promise? A negative-control study
  of validity without accuracy under drift and delayed labels
- Author: Bien Busico (sole). Affiliation: Mapua Malayan College Mindanao, Davao City,
  Philippines. Email: bienbusico@gmail.com
- Format: elsarticle final,5p,times,twocolumn ; no linenumbers ; 13 pp ; wide tables
  table* , wide figures figure* . Page cap 12-15 (met).

## Required uploads (Attach Files; tag each with its Item Type)

- Manuscript  ->  IPIS_M1_JPC_13pp.pdf
- Highlights  ->  highlights.docx (5 bullets, <=85 chars each)
- Declaration of Competing Interests  ->  declaration_competing_interests.docx
- (optional) Cover Letter  ->  cover_letter_JPC.docx
- (optional) Source  ->  .tex bundle + references.bib + 7 figure PDFs

## Fixed step answers

CLASSIFICATIONS (3-5): 26 Soft Sensor ; 22 Process Monitoring ; 101 Uncertainty
Modeling ; 7 Sensor ; 48 Distillation Column.
  AVOID 37 Machine Learning and 8 Data Driven Computing (route to ML reviewers who
  attack the conformal-novelty angle we did not headline).

KEYWORDS: soft sensor ; conformal prediction ; label delay ; drift ; model migration ;
physics-informed features ; Tennessee Eastman process.

DATA/CODE AVAILABILITY: select "Other". Field has a 200-CHARACTER LIMIT. Paste exactly
(172 chars):
  The implementation, evaluation scripts, and provenance-stamped artifacts that
  regenerate every figure and table are openly available at
  https://github.com/beebzy-droid/IPIS
  (Single line, no break, when pasting. Dataset attributions live in the reference
  list, so they are intentionally omitted here to fit the cap.)

PREPRINT (SSRN): YES (free, DOI + priority date, no effect on editorial outcome).

COMMENTS TO PUBLICATION OFFICE:
  This manuscript was transferred from Computers & Chemical Engineering
  (CACE-D-26-00944) on the handling editor's scope recommendation, and has been
  substantially reframed and formatted to the Journal of Process Control template
  (13 pages, two-column production format) for this submission.

COMPETING INTERESTS: none. FUNDING: none. SOLE AUTHOR.

## Declaration of Competing Interests — canonical text
The author declares that he has no known competing financial interests or personal
relationships that could have appeared to influence the work reported in this paper.

## Other
- Abstract source: paper/abstract.tex (negative-control version; paste plain text).
- Suggested-reviewer expertise: soft sensing ; conformal prediction for time series ;
  process model migration.
- FINAL GATE: after Attach Files -> "Build PDF for my Approval" -> view -> Approve.
  NOT submitted to the editor until the built PDF is approved.

---
Adopted 2026-06-29. New venue -> copy this block, update venue + classifications +
format rows, keep the rest.
