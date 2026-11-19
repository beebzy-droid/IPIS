"""Check that every live source carries one of the dated author blocks in docs/AUTHOR.md.

Two blocks are valid. The block of 2026-11-18 (byline "Bien Don Busico", University of the
Philippines Diliman, Quezon City) is used on N1 and on every paper submitted from that date; the
block of 2026-10-09 (byline "Bien Busico", Mapua Malayan Colleges Mindanao, Davao City, with the
accent) stays on what was published or submitted with it. Scans the tracked text files and reports
file:line for each of these:
- a retired affiliation form: singular "Malayan College Mindanao", unaccented "Mapua", or an
  added "Davao del Sur";
- an author e-mail other than bienbusico@gmail.com;
- an elsarticle `\\address{...}` that is not exactly one of the two canonical ones;
- a file that mixes the two blocks (one block's byline with the other block's address);
- in the private repo, a source of N1 (`paper/`) that carries the superseded 2026-10-09 block.

Files that record what was actually sent (the frozen M2 upload set, dated logs, review records)
are excluded, because they must keep the strings they were sent with. Standard library only, so
it runs in CI and in pre-commit without extra dependencies.

    python scripts/check_author_block.py        # exit 1 on any finding
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# The two dated blocks of docs/AUTHOR.md: (byline in \\author{...}, \\address{...}).
BLOCK_2026_11_18 = (
    r"\author{Bien Don Busico}",
    r"\address{University of the Philippines Diliman, Quezon City, Philippines}",
)
BLOCK_2026_10_09 = (
    r"\author{Bien Busico}",
    r"\address{Map\'ua Malayan Colleges Mindanao, Davao City, Philippines}",
)
CANONICAL_ADDRESSES = (BLOCK_2026_11_18[1], BLOCK_2026_10_09[1])
EMAIL = "bienbusico@gmail.com"
# In the private repo, paper/ holds N1's working copy, which must carry the 2026-11-18 block.
# (In the public repo paper/ is M1's frozen preprint and is not touched by this rule.)
N1_SOURCES = "paper/"

# Records of what was sent, and documents that discuss the retired forms on purpose.
# paper3/ in the public repo is the frozen 2026-06-30 preprint, which the publisher's policy
# allows to be public only as submitted; it keeps the singular affiliation on purpose
# (docs/PAPER_LIFECYCLE.md). In the private ipis-papers repo (recognised by paper3/submission_R1/)
# paper3/ is the live working copy, so those sources are checked there.
PREPRINT_SOURCES = (
    "paper3/scc_paper.tex",
    "paper3/scc_refs.bib",
    "paper3/sections/",
    "paper3/README.txt",
)
FROZEN = (
    "paper3/submission_R1/",
    "docs/reviews/",
    "docs/module2/revision/",
    "docs/HANDOFF.md",
    "docs/CITATION_LEDGER.md",
    "docs/AUTHOR.md",
    "docs/OPEN_ITEMS.md",
    "docs/PAPER_LIFECYCLE.md",
    "docs/module2/proof/PROOF_CHECKLIST.md",
    "scripts/check_author_block.py",
    "scripts/proof_check.py",
    "paper/N1_OUTLINE.md",
    "paper/N1_PRESUBMISSION_JPC.md",
)
TEXT = re.compile(r"\.(tex|bib|md|txt|csv|py|yaml|yml|toml|cff)$")

RULES = [
    ("singular affiliation", re.compile(r"Malayan\s+College\s+Mindanao")),
    ("unaccented Mapua", re.compile(r"\bMapua\b")),
    ("Davao del Sur added", re.compile(r"Davao del Sur")),
    (
        "other author e-mail",
        re.compile(r"[\w.+-]*busico[\w.+-]*@[\w.-]+|[\w.+-]*@[\w.-]*busico[\w.-]*", re.I),
    ),
    ("non-canonical \\address", re.compile(r"\\address\{[^}]*\}")),
]


def private_repo() -> bool:
    return Path("paper3/submission_R1").is_dir()


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    skip = FROZEN if private_repo() else FROZEN + PREPRINT_SOURCES
    return [f for f in out.splitlines() if TEXT.search(f) and not f.startswith(skip)]


def findings(path: str, n1_source: bool = False) -> list[tuple[int, str, str]]:
    found = []
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rule in RULES:
            for m in rule.finditer(line):
                hit = m.group(0)
                if name == "other author e-mail" and hit.lower() == EMAIL:
                    continue
                if name == "non-canonical \\address" and hit in CANONICAL_ADDRESSES:
                    continue
                found.append((lineno, name, hit))
        for old in BLOCK_2026_10_09:
            if n1_source and old in line:
                found.append((lineno, "superseded block in an N1 source", old))
    # One block per file: a byline and an address from different dated blocks.
    for byline, address in (
        (BLOCK_2026_11_18[0], BLOCK_2026_10_09[1]),
        (BLOCK_2026_10_09[0], BLOCK_2026_11_18[1]),
    ):
        if byline in text and address in text:
            found.append((0, "mixed author blocks", f"{byline} with {address}"))
    return found


def main() -> int:
    total = 0
    in_private = private_repo()
    for path in tracked():
        n1_source = in_private and path.startswith(N1_SOURCES)
        for lineno, name, hit in findings(path, n1_source):
            total += 1
            print(f"{path}:{lineno}: {name}: {hit}")
    print(
        f"{total} finding(s); canonical blocks in docs/AUTHOR.md"
        if total
        else "author block: clean"
    )
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
