"""R1.3 terminology sweep and standing audit for JRESS-D-26-04700 (RESS major revision).

Reviewer 1, comment 3: FEMTO/PRONOSTIA is an accelerated laboratory testbed, so calling it a
"field benchmark" overstates the evidence. Rule adopted for the revision:

    "field" is RESERVED for genuinely operational, in-service data, which this work does not have.
    FEMTO is an accelerated laboratory test platform; the manuscript calls it an experimental
    benchmark. C-MAPSS, added at R2.1, is externally authored simulation, so it is not field data
    either and must never be described as such.

Two modes:

    --apply   one-shot: rewrite the six passages that mislabelled FEMTO. Each replacement is
              asserted to match exactly once, so a second run fails loudly instead of corrupting
              the source. Run once; the diff is the deliverable.
    --audit   idempotent guard: fail if a banned phrase reappears or an unqualified "field"
              is introduced. Re-run after every writing task for the rest of the revision.

Usage (from the repo root):

    python scripts/r13_terminology_sweep.py --audit

No numbers are touched here; the unit-level number sweep is a separate revision task.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

TARGETS = [
    "paper3/scc_paper.tex",
    "paper3/sections/01_introduction.tex",
    "paper3/sections/02_background.tex",
    "paper3/sections/03_method.tex",
    "paper3/sections/04_experimental_design.tex",
    "paper3/sections/05_results.tex",
    "paper3/sections/06_discussion.tex",
    "paper3/sections/07_conclusions.tex",
    "paper3/sections/08_appendix.tex",
]

# Phrases that mislabel laboratory or simulation evidence as field evidence.
BANNED = [
    "field benchmark",
    "field-data limit",
    "field data limit",
    "field dataset",
    "field testbed",
]

# A surviving "field" is acceptable only inside one of these qualified constructions.
QUALIFIED = [
    "operational field",
    "in-service field",
    "rather than field data",
    "not field data",
    "field data from an operating",
]

EDITS: list[tuple[str, str, str]] = [
    (
        "paper3/scc_paper.tex",
        "a-priori bound holds on 100\\% of held-out configurations. On the FEMTO bearing benchmark the\n"
        "diagnostic correctly places that dataset outside the method's envelope. Validation on adequately\n"
        "powered field data is the next step.",
        "a-priori bound holds on 100\\% of held-out configurations. On the FEMTO accelerated-laboratory\n"
        "bearing benchmark the diagnostic correctly places that dataset outside the method's envelope.\n"
        "Validation on adequately powered operational field data is the next step.",
    ),
    (
        "paper3/sections/01_introduction.tex",
        "real but is never assumed by the estimator; and the one field benchmark (FEMTO bearings) is\n"
        "correctly reported by the diagnostic as outside the method's envelope rather than forced into a\n"
        "positive result. Validation on adequately powered field data is the natural next step.",
        "real but is never assumed by the estimator; and the one experimental benchmark (FEMTO bearings,\n"
        "an accelerated laboratory test platform rather than in-service field data) is correctly reported\n"
        "by the diagnostic as outside the method's envelope rather than forced into a positive result.\n"
        "Validation on adequately powered operational field data is the natural next step.",
    ),
    (
        "paper3/sections/05_results.tex",
        "\\subsection{Knowing when not to trust the method: the diagnostic and a field-data limit}"
        "\\label{sec:res-diag}",
        "\\subsection{Knowing when not to trust the method: the diagnostic on a thin experimental "
        "benchmark}\\label{sec:res-diag}",
    ),
    (
        "paper3/sections/05_results.tex",
        "within-condition spread swamps the structural signal (Fig.~\\ref{fig:diag}). The FEMTO bearing\n"
        "benchmark~\\cite{nectoux2012pronostia} falls in the last category: with roughly six bearings per\n"
        "condition and a $7\\times$ within-condition life spread, the bootstrap CI on $g$ spans a factor of\n"
        "2.6--4.4, far too wide to resolve the $1.63\\times$ life ratio that L10 predicts between its"
        " load/speed\nconditions.",
        "within-condition spread swamps the structural signal (Fig.~\\ref{fig:diag}). The FEMTO bearing\n"
        "benchmark~\\cite{nectoux2012pronostia} is an accelerated laboratory test platform, not field data\n"
        "from an operating fleet, and it falls in the last category: with roughly six bearings per\n"
        "condition and a $7\\times$ within-condition life spread, the bootstrap CI on $g$ spans a factor of\n"
        "2.6--4.4, far too wide to resolve the $1.63\\times$ life ratio that L10 predicts between its"
        " load/speed\nconditions.",
    ),
    (
        "paper3/sections/06_discussion.tex",
        "incomplete similitude. (iii) Validation is on a controlled simulation, and the single field"
        " benchmark\nreturns \\emph{indeterminate} by design rather than a positive result. (iv) The bound"
        " is conservative.\nThe decisive next step is validation on adequately powered run-to-failure field"
        " data, where the\ndiagnostic returns \\emph{holds} and the certificate can be checked against"
        " measured cross-regime\ncoverage; such data is the goal of ongoing work on an operating industrial"
        " process.",
        "incomplete similitude. (iii) Validation is on a controlled simulation, and the single experimental"
        "\nbenchmark, an accelerated laboratory test platform rather than field data, returns\n"
        "\\emph{indeterminate} by design rather than a positive result. (iv) The bound is conservative.\n"
        "The decisive next step is validation on adequately powered run-to-failure data from an operating\n"
        "fleet, where the diagnostic returns \\emph{holds} and the certificate can be checked against\n"
        "measured cross-regime coverage; such data is the goal of ongoing work on an operating industrial\n"
        "process.",
    ),
    (
        "paper3/sections/07_conclusions.tex",
        "robust across the structure and magnitude of the departure and the coverage level. On the FEMTO\n"
        "benchmark the diagnostic correctly places that dataset outside the method's envelope, demonstrating"
        "\nthe intended fault-tolerant behaviour. The method is ready for the decisive test, validation on\n"
        "adequately powered run-to-failure field data from an operating process, which is the focus of\n"
        "continuing work.",
        "robust across the structure and magnitude of the departure and the coverage level. On the FEMTO\n"
        "experimental benchmark, an accelerated laboratory test platform rather than field data, the\n"
        "diagnostic correctly places that dataset outside the method's envelope, demonstrating the intended"
        "\nfault-tolerant behaviour. The method is ready for the decisive test, validation on adequately\n"
        "powered run-to-failure field data from an operating process, which is the focus of continuing"
        " work.",
    ),
]


def apply_edits() -> list[str]:
    """Apply every edit, requiring a unique match for each source string."""
    staged: dict[str, str] = {}
    for rel, old, new in EDITS:
        text = staged.get(rel) or (REPO / rel).read_text(encoding="utf-8")
        hits = text.count(old)
        if hits != 1:
            sys.exit(f"FAIL {rel}: expected exactly 1 match, found {hits}\n{old[:120]}...")
        staged[rel] = text.replace(old, new, 1)
    for rel, text in staged.items():
        (REPO / rel).write_text(text, encoding="utf-8")
    return sorted(staged)


def audit() -> list[str]:
    """Return a list of terminology violations across the manuscript source."""
    problems: list[str] = []
    for rel in TARGETS:
        path = REPO / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in BANNED:
            if token in text.lower():
                problems.append(f"{rel}: banned phrase '{token}'")
        for match in re.finditer(r"field", text, flags=re.I):
            window = text[max(0, match.start() - 90) : match.end() + 60].replace("\n", " ")
            if not any(key in window for key in QUALIFIED):
                problems.append(f"{rel}: unqualified 'field' -> ...{window.strip()}...")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--apply", action="store_true", help="apply the one-shot sweep")
    group.add_argument("--audit", action="store_true", help="check terminology only")
    args = parser.parse_args()

    if args.apply:
        for rel in apply_edits():
            print(f"edited {rel}")

    problems = audit()
    if problems:
        print(f"AUDIT FAILED ({len(problems)} problem(s)):")
        for line in problems:
            print(f"  {line}")
        return 1
    print("AUDIT CLEAN: no unqualified 'field' in paper3 source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
