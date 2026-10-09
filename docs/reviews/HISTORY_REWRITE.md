# Runbook: the 2026-10-09 public history rewrite (EXECUTED)

Status: **executed 2026-10-09**, after the subscription rights form was signed. Kept as the record
of what was removed and what GitHub may still hold. The scope grew beyond the response letter: the
manuscripts moved to the private `ipis-papers` repo at the same time (`docs/PAPER_LIFECYCLE.md`),
so the rewrite also removed the accepted M2 manuscript, its revision and proof documents from
public history. Commits from 2026-09-07 onward were rewritten; the 205 before that were untouched.

## Why

The repo is public (confirmed by Bien, 2026-10-09). `paper3/response_to_reviewers.tex` and `.pdf`
quote both RESS reviewers verbatim. They were removed from tracking on 2026-10-09, but git history
still serves them. Peer-review reports are conventionally confidential (general
publication-ethics practice, not verified as a specific RESS rule).

Measured on a full clone of the public repo (236 commits, all refs) by counting 8-word runs shared
with the private decision letters:

| File | Verbatim 8-word runs | Where |
|---|---|---|
| `paper3/response_to_reviewers.tex` | 1038 | history only (added 89263d2, 2026-09-18; edited dddbf87, 2026-09-27; removed 2026-10-09 in the "M2 SCC ACCEPTED" commit) |
| any other file, any version | at most 4 beyond the paper's own title | short phrases in `REVISION_LOG.md` and `REVISION_HANDOFF.md`, and the reviewer quoting our abstract; not reproductions |

Only `main` contains the letter. `wip/canonical-tep` and the read-only `refs/pull/1/head` end on
2026-06-12, before the letter existed. No tracked file or the Zenodo deposit refers to any of the
commits that would be rewritten.

## What it changes (tested)

| Quantity | Value |
|---|---|
| Commits rewritten | every commit from 89263d2 to the tip (14 when tested; it grows by one per later commit) |
| Commits kept byte-identical | the 222 commits before 89263d2, all of them |
| Tree at the tip | unchanged (the files are already gone from HEAD) |
| `git fsck` after | clean |

Why `--refs`: a plain run also strips the GitHub signature from the 2026-06-12 merge of PR #1, which
changes that commit's hash and every hash after it. In the test, a plain run kept 74 of 236 SHAs and
the `--refs` run kept 222. Limiting the rewrite to the range that contains the letter keeps every
earlier commit and its signature.

## When

Wait for the rights form, then run once. If M2 goes **subscription**, Elsevier's sharing policy
allows the accepted manuscript to be posted publicly right away only on a non-commercial personal
homepage or blog, or by updating an arXiv/RePEc preprint. After the embargo it may go on
non-commercial hosting platforms or on commercial sites that have an agreement with Elsevier. The
policy page does not name GitHub. On that reading (ours, not legal advice; confirm with Elsevier if
in doubt), the accepted manuscript (the files in
`paper3/submission_R1/`, plus the revised LaTeX) would also have to leave the public repo and its
history, and the rewrite would grow to cover those paths too. If M2 goes **open access**, scope A
below is all that is needed. Doing the rewrite once instead of twice matters because every rewrite
changes every later SHA and forces every clone to be reset.

## Scope A: letter only (Windows cmd)

Prerequisites: everything committed and pushed; `pip install git-filter-repo` (version 2.47 or
later, for `--sensitive-data-removal`).

```
cd /d C:\Users\yubyu\Projects
git clone https://github.com/beebzy-droid/ipis ipis_rewrite
cd ipis_rewrite
git rev-parse "HEAD^{tree}"
python -m git_filter_repo --sensitive-data-removal --refs 89263d2~1..main --invert-paths --path paper3/response_to_reviewers.tex --path paper3/response_to_reviewers.pdf
```

Check before pushing (all three must hold):
```
git log main --format= --name-only | findstr response_to_reviewers
git rev-parse "HEAD^{tree}"
git rev-list --count main
```
The first prints nothing, the second prints the same tree as before, and the third prints the same
count as before. If your git is too old for `--sensitive-data-removal`, drop that flag. The
`--refs`/`--invert-paths` part is what removes the files, and it was tested both with and without
the flag. (`~1` is used instead of `^` because cmd treats `^` as an escape character.)

Push, then reset your working clone to match:
```
git push --force-with-lease origin main
type .git\filter-repo\first-changed-commits
cd /d C:\Users\yubyu\Projects\IPIS
git status
git fetch origin
git reset --hard origin/main
```
`git status` must be clean before the reset. `private/` is git-ignored, so the reset does not touch
it. Afterwards, delete the `ipis_rewrite` folder.

## What the rewrite cannot remove (GitHub documentation)

- Existing clones and forks keep the old history. Check the fork count on the repo page; GitHub
  cannot contact fork owners for you.
- Old commits stay reachable by SHA in GitHub's cached views until GitHub Support removes those
  views and garbage-collects. Request it through the Support portal, giving the repository name and
  the first changed commit printed above. GitHub says it helps only where the risk cannot be
  mitigated by rotating credentials; a confidential document qualifies on that reading, but the
  decision is theirs.

## Every session after the rewrite

Old SHAs from 2026-09-18 onward no longer exist. Re-clone, or run `git fetch origin` and
`git reset --hard origin/main`, before working. Record the date of the rewrite in
`docs/HANDOFF.md`.
