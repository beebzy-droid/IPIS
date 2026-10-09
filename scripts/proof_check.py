"""Proof check: compare a typeset journal proof against the accepted manuscript.

Built for JRESS-D-26-04700R1 (M2, SCC) but paper-agnostic. The accepted manuscript is the Word
file that was submitted and accepted; the proof is the PDF the publisher returns. Typesetting may
reflow, renumber pages and restyle references, but it must not lose or alter a number, drop a
reference, lose an equation symbol, or change the title. This script checks exactly those things
and prints a FLAG for each discrepancy.

Checks
------
1. numbers     every decimal in the accepted text must appear at least as often in the proof
               (catches a changed table cell, a dropped result, a mistyped value)
2. references  same count; each first-author surname and year present in the proof
3. floats      number of distinct Table and Figure captions
4. symbols     Greek and math symbol counts; a large drop means equations failed to typeset
5. strings     title, Zenodo DOI, byline, canonical affiliation (docs/AUTHOR.md), e-mail, no monorepo URL

Usage
-----
    cd ../ipis-papers        # the accepted manuscript lives in the private repo
    python ../IPIS/scripts/proof_check.py --accepted paper3/submission_R1/scc_paper.docx --proof proof.pdf

Exit status is 1 if any check FLAGs, so the result can gate a commit. Requires `pdftotext`
(poppler) or the `pypdf` package for the proof.
"""

from __future__ import annotations

import argparse
import collections
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

TITLE = (
    "Similarity-Calibrated Conformal prediction: data-free coverage guarantees for "
    "remaining-useful-life intervals under operating-regime transfer"
)
ZENODO = "10.5281/zenodo.23211276"
AFFILIATION = "Malayan Colleges Mindanao"  # canonical, docs/AUTHOR.md (decided 2026-10-09)
RETIRED_AFFILIATION = "Malayan College Mindanao"  # singular; the accepted Word file carries it
EMAIL = "bienbusico@gmail.com"
BYLINE = "Bien Busico"  # docs/AUTHOR.md (decided 2026-10-09)
SYMBOLS = "ψΨηδΔσαθκρΠπΣ∥√≤≥×"
DECIMAL = re.compile(r"(?<![\d.])\d+\.\d+(?![\d.])")


def normalise(text: str) -> str:
    """Undo typesetting artefacts so the two texts compare on content."""
    text = unicodedata.normalize("NFKC", text)  # ligatures (fi, fl) and compatibility forms
    for dash in ("−", "–", "—", "‐", "‑"):
        text = text.replace(dash, "-")
    # math fonts extract as look-alike code points: INCREMENT for Delta, DOUBLE VERTICAL LINE for norm
    text = text.replace("\u2206", "\u0394").replace("\u2016", "\u2225")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # words hyphenated across lines
    return re.sub(r"[ \t]+", " ", text)


def docx_text(path: Path) -> str:
    """All visible text of a .docx, including Office Math runs, in document order."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    runs = re.findall(r"<(?:w|m):t(?:\s[^>]*)?>([^<]*)</(?:w|m):t>|(\n)", xml)
    text = "".join(t or nl for t, nl in runs)
    for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(ent, ch)
    return text


def pdf_text(path: Path) -> str:
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True)
        return out.stdout
    from pypdf import PdfReader  # noqa: PLC0415  (optional dependency)

    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def references(text: str) -> list[tuple[str, str]]:
    """(first-author surname, year) for each numbered entry after the References heading."""
    idx = text.rfind("References")
    body = text[idx:] if idx >= 0 else text
    entries = re.split(r"\n\s*\[\d+\]\s*", "\n" + body)[1:]
    out = []
    for entry in entries:
        head = re.sub(r"\s+", " ", entry[:300])
        author = re.match(
            r"(?:[A-Z][a-z]*\.?[-\s~]*)+?([A-Z][\w'\-]+(?:\s[A-Z][\w'\-]+)?)[,.]", head
        )
        year = re.search(r"\b(19|20)\d{2}\b", head)
        if not author:  # corporate author, e.g. "International Organization for Standardization"
            author = re.match(r"([A-Z][\w'\-]+)", head)
        if author and year:
            out.append((author.group(1).split()[-1], year.group(0)))
    return out


def captions(text: str, kind: str) -> set[str]:
    pattern = r"\bTable\s+([A-Z]?\.?\d+)" if kind == "table" else r"\bFig(?:ure|\.)\s+(\d+)"
    return set(re.findall(pattern, text))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--accepted", type=Path, required=True, help="accepted manuscript (.docx)")
    parser.add_argument("--proof", type=Path, required=True, help="publisher proof (.pdf)")
    parser.add_argument("--show", type=int, default=25, help="max items listed per check")
    args = parser.parse_args()

    accepted = normalise(docx_text(args.accepted))
    proof = normalise(pdf_text(args.proof))
    flags = 0

    def report(name: str, ok: bool, detail: str) -> None:
        nonlocal flags
        flags += not ok
        print(f"[{'PASS' if ok else 'FLAG'}] {name}: {detail}")

    # 1. numbers -------------------------------------------------------------------------
    acc_n = collections.Counter(DECIMAL.findall(accepted))
    prf_n = collections.Counter(DECIMAL.findall(proof))
    lost = {n: c - prf_n[n] for n, c in acc_n.items() if prf_n[n] < c}
    report(
        "numbers",
        not lost,
        f"{sum(acc_n.values())} decimals in the accepted text ({len(acc_n)} distinct); "
        f"{sum(lost.values())} occurrence(s) missing or altered in the proof",
    )
    for n, deficit in sorted(lost.items(), key=lambda kv: -kv[1])[: args.show]:
        ctx = re.search(r".{0,50}" + re.escape(n) + r".{0,30}", accepted.replace("\n", " "))
        print(f"        {n:>10}  x{deficit}   e.g. ...{ctx.group(0).strip() if ctx else ''}...")
    new = {n: c - acc_n[n] for n, c in prf_n.items() if c > acc_n[n] and len(n.split(".")[1]) >= 2}
    if new:
        print(
            f"        (info) decimals new in the proof, 2+ places: {dict(list(new.items())[:12])}"
        )

    # 2. references ------------------------------------------------------------------------
    acc_r, prf_r = references(accepted), references(proof)
    tail = proof[proof.rfind("References") :] if "References" in proof else proof
    missing = [(a, y) for a, y in acc_r if a not in tail or y not in tail]
    report(
        "references",
        len(acc_r) == len(prf_r) and not missing,
        f"accepted {len(acc_r)}, proof {len(prf_r)}; "
        f"{len(missing)} accepted entr(ies) not found in the proof reference list",
    )
    for a, y in missing[: args.show]:
        print(f"        missing: {a} ({y})")

    # 3. floats ----------------------------------------------------------------------------
    for kind in ("table", "figure"):
        a, p = captions(accepted, kind), captions(proof, kind)
        report(f"{kind}s", a <= p, f"accepted {sorted(a)}, proof {sorted(p)}")

    # 4. symbols ---------------------------------------------------------------------------
    drops = []
    for ch in SYMBOLS:
        a, p = accepted.count(ch), proof.count(ch)
        if a >= 3 and p < 0.5 * a:
            drops.append(f"{ch} {a}->{p}")
    report(
        "symbols",
        not drops,
        (
            "no symbol lost more than half its occurrences"
            if not drops
            else "large drops (equations may not have typeset): " + ", ".join(drops)
        ),
    )

    # 5. strings ---------------------------------------------------------------------------
    flat = re.sub(r"\s+", " ", proof)
    report(
        "title",
        TITLE.lower() in flat.lower(),
        "exact title present" if TITLE.lower() in flat.lower() else "title differs",
    )
    report("zenodo doi", ZENODO in flat, ZENODO + (" present" if ZENODO in flat else " NOT found"))
    plural, singular = AFFILIATION in flat, RETIRED_AFFILIATION in flat
    report(
        "affiliation",
        plural and not singular,
        (
            "canonical 'Mapua Malayan Colleges Mindanao'"
            if plural and not singular
            else (
                "proof carries the singular 'College' (correction C6)"
                if singular
                else "affiliation not found"
            )
        ),
    )
    report(
        "byline",
        BYLINE in flat,
        BYLINE
        + (" present" if BYLINE in flat else " NOT found (byline changed by the typesetter)"),
    )
    report(
        "e-mail",
        EMAIL in flat,
        EMAIL + (" present" if EMAIL in flat else " NOT found (correction C7)"),
    )
    github = "github.com/beebzy-droid/IPIS" in flat
    report(
        "data statement",
        not github,
        (
            "monorepo URL absent"
            if not github
            else "proof still cites the GitHub monorepo (correction C1)"
        ),
    )

    print(f"\n{flags} FLAG(s).")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())
