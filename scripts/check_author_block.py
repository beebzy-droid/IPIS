"""Check that every live source carries the canonical author block in docs/AUTHOR.md.

Scans the tracked text files and reports file:line for each of these:
- a retired affiliation form: singular "Malayan College Mindanao", unaccented "Mapua", or an
  added "Davao del Sur";
- a retired byline: "Bien Don Busico" or "B. D. Busico";
- an author e-mail other than bienbusico@gmail.com;
- an elsarticle `\\address{...}` that is not exactly the canonical one.

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

CANONICAL_ADDRESS = r"\address{Map\'ua Malayan Colleges Mindanao, Davao City, Philippines}"
EMAIL = "bienbusico@gmail.com"

# Records of what was sent, and documents that discuss the retired forms on purpose.
# paper3/ in the public repo is the frozen 2026-06-30 preprint, which the publisher's policy
# allows to be public only as submitted; it keeps the singular affiliation on purpose
# (docs/PAPER_LIFECYCLE.md). In the private ipis-papers repo it is the working copy and IS checked.
FROZEN = (
    "paper3/scc_paper.tex",
    "paper3/scc_refs.bib",
    "paper3/sections/",
    "paper3/README.txt",
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
)
TEXT = re.compile(r"\.(tex|bib|md|txt|csv|py|yaml|yml|toml|cff)$")

RULES = [
    ("singular affiliation", re.compile(r"Malayan\s+College\s+Mindanao")),
    ("unaccented Mapua", re.compile(r"\bMapua\b")),
    ("Davao del Sur added", re.compile(r"Davao del Sur")),
    ("retired byline", re.compile(r"Bien[~\s]+Don[~\s]+Busico|\bB\.~?\s*D\.~?\s*Busico")),
    (
        "other author e-mail",
        re.compile(r"[\w.+-]*busico[\w.+-]*@[\w.-]+|[\w.+-]*@[\w.-]*busico[\w.-]*", re.I),
    ),
    ("non-canonical \\address", re.compile(r"\\address\{[^}]*\}")),
]


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if TEXT.search(f) and not f.startswith(FROZEN)]


def findings(path: str) -> list[tuple[int, str, str]]:
    found = []
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rule in RULES:
            for m in rule.finditer(line):
                hit = m.group(0)
                if name == "other author e-mail" and hit.lower() == EMAIL:
                    continue
                if name == "non-canonical \\address" and hit == CANONICAL_ADDRESS:
                    continue
                found.append((lineno, name, hit))
    return found


def main() -> int:
    total = 0
    for path in tracked():
        for lineno, name, hit in findings(path):
            total += 1
            print(f"{path}:{lineno}: {name}: {hit}")
    print(
        f"{total} finding(s); canonical block in docs/AUTHOR.md" if total else "author block: clean"
    )
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
