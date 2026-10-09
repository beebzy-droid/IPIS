"""Build Zenodo v1.0.1 of the SCC code deposit once the article has its DOI.

v1.0.0 (doi:10.5281/zenodo.23211276) was deposited on 2026-10-07 and is cited in the accepted
article. Its README says the paper is "submitted to" RESS. v1.0.1 changes exactly one thing, the
README citation, so the deposit points at the published article. Everything else must stay
byte-identical, because the article cites what the reviewers could run.

So this script does not re-collect files from the repo (which may have moved on since). It opens
the frozen v1.0.0 archive in `paper3/submission_R1/scc-code.zip`, rewrites the citation in
`scc-code/README.md`, copies every other member unchanged, and then verifies that claim member by
member before writing anything.

Usage (at proof stage, values from the proof or the article page):

    python scripts/zenodo_scc_v101.py --article-doi 10.1016/j.ress.2026.112345 \
        --volume 266 --article-number 112345 --year 2026

Output: `scc-code-v1.0.1.zip` in the current directory, plus the Zenodo fields to enter.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

FROZEN = Path("paper3/submission_R1/scc-code.zip")
FROZEN_MD5 = "4850f5676e3dce5a876bf5d90fc01c8e"
README = "scc-code/README.md"
TITLE = (
    "Similarity-Calibrated Conformal prediction: data-free coverage guarantees for "
    "remaining-useful-life intervals under operating-regime transfer"
)
OLD_CITATION = re.compile(r"> B\. Busico, \"Similarity-Calibrated.*?\(JRESS-D-26-04700\)\.", re.S)


def citation(doi: str, volume: str, number: str, year: str, author: str) -> str:
    return (
        f'> {author}, "{TITLE}",\n'
        f"> *Reliability Engineering & System Safety* {volume} ({year}) {number}.\n"
        f"> https://doi.org/{doi}"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--article-doi", required=True, help="e.g. 10.1016/j.ress.2026.112345")
    p.add_argument("--volume", required=True)
    p.add_argument("--article-number", required=True, help="Elsevier article number (e-locator)")
    p.add_argument("--year", required=True)
    p.add_argument("--out", type=Path, default=Path("scc-code-v1.0.1.zip"))
    p.add_argument(
        "--author",
        default="B. D. Busico",
        help="author as printed in the published article (proof correction C8 adds the D.)",
    )
    a = p.parse_args()

    if not re.fullmatch(r"10\.1016/j\.ress\.\d{4}\.\d+", a.article_doi):
        sys.exit(
            f"refusing: '{a.article_doi}' does not look like a RESS DOI (10.1016/j.ress.YYYY.N)"
        )
    if hashlib.md5(FROZEN.read_bytes()).hexdigest() != FROZEN_MD5:
        sys.exit(f"refusing: {FROZEN} is not the frozen v1.0.0 deposit (MD5 mismatch)")

    src = zipfile.ZipFile(FROZEN)
    readme = src.read(README).decode("utf-8")
    if len(OLD_CITATION.findall(readme)) != 1:
        sys.exit("refusing: the v1.0.0 citation block was not found exactly once in the README")
    new_readme = OLD_CITATION.sub(
        lambda _: citation(a.article_doi, a.volume, a.article_number, a.year, a.author), readme
    ).replace("Code accompanying the manuscript:", "Code accompanying the article:")

    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = new_readme.encode("utf-8") if info.filename == README else src.read(info)
            # fresh ZipInfo: writestr mutates the one it is given, which would corrupt `src`
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr, zi.create_system = info.external_attr, info.create_system
            dst.writestr(zi, data)

    # verify: same members, same bytes, except the README
    out = zipfile.ZipFile(a.out)
    names_in, names_out = [i.filename for i in src.infolist()], [i.filename for i in out.infolist()]
    if names_in != names_out:
        sys.exit("verification failed: member list changed")
    changed = [n for n in names_in if src.read(n) != out.read(n)]
    if changed != [README]:
        sys.exit(f"verification failed: changed members {changed}, expected only {README}")

    print(f"wrote {a.out}: {len(names_out)} members, only {README} changed (verified)")
    print(
        "\nNew citation block:\n"
        + citation(a.article_doi, a.volume, a.article_number, a.year, a.author)
    )
    print(
        "\nZenodo: open doi:10.5281/zenodo.23211276 -> New version -> replace the file with "
        f"{a.out.name} -> Version 1.0.1 -> Related works: {a.article_doi}, relation "
        '"Is supplement to", resource type Journal article -> Publish.'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
