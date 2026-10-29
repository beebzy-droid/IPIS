#!/usr/bin/env python3
"""Screening log of the N1 database sweep (Scopus and Web of Science).

Protocol: docs/module1/LITERATURE_SWEEP_N1.md, "Database sweep protocol, 2026-10-20".

The raw exports are not in the repository. Database terms restrict their redistribution, and
the abstracts are the publishers'. They are kept outside git (for example in private/sweep/,
which .gitignore excludes). The summary JSON records the SHA-256 of every file read, so the
log can be traced to the exports without publishing them.

The exports came in three batches, each kept in its own folder under the names it was received
with (the 8-character prefixes the upload added may stay):
- 2026-10-22: the 20 files of FILE_TO_QUERY;
- 2026-10-27: the files of BATCH2. The S4 export is screened with the first batch. W9's file
  is the cited-reference list, not the citing set, and W10's is the record of SPCI itself, so
  both are summarised, not screened. The Google Scholar pages are hashed only; they are
  screened by hand in docs/module1/sweep/N1_scholar_screening_2026-10-27.csv;
- 2026-10-28: the files of BATCH3, the citing sets of W9 and W10 (full records), screened.
Run, from the repository root:
    python3 scripts/sweep/n1_screening.py private/sweep/2026-10-22 private/sweep/2026-10-27
        private/sweep/2026-10-28
Requires xlrd >= 2 for the Web of Science .xls files.

It writes docs/module1/sweep/N1_database_screening_2026-10-22.csv, with titles and
identifiers but no abstracts, and a JSON summary beside it. The log keeps the name of its first
batch. It also prints, for every export, how many of its records satisfy each search string as
issued (an approximate check, see satisfies()). That check is how each file was matched to its
query.

Screening codes:
  X1  'conformal' appears only in another sense (geometry, coatings, antennas, physics)
  X2  no conformal or prediction-interval method in the title or abstract (a reference-list
      or keyword match)
  X3  a conformal or interval method that bears on none of F4 (i) to (iii) or Section 3D:
      no analysis of an online loop under delayed feedback, of its step size or stability,
      of a forecaster ahead of a delayed loop, or of a width bound
  X4  already in the sweep record (rows 1 to 20) or the project library
  X5  uses Tennessee Eastman data or the simulator; nothing on its random-number generator
  X6  classical dead-time compensation, without intervals
  F   read in full; the verdict is in LITERATURE_SWEEP_N1.md (rows 21 on)
  A   may bear, but the full text was not reached from the workspace; abstract-level verdict,
      to be read before submission
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10**9)

OUT_CSV = "docs/module1/sweep/N1_database_screening_2026-10-22.csv"
OUT_JSON = "docs/module1/sweep/N1_database_screening_2026-10-22_summary.json"

# Exported file -> query. Confirmed by satisfies(): every record of each file meets its string.
FILE_TO_QUERY = {
    "Claim_i_delayed_feedback_in_conformal_methods.csv": "S1",
    "Claim_i_step_size_and_stability_of_the_adaptive_loop.csv": "S2",
    "Claim_ii_delay-limited_width_bound_1.csv": "S3",
    "Claim_ii_delay-limited_width_bound_2.csv": "S3",  # byte-identical to _1; S4 came later
    "Claim_iii_a_forecaster_ahead_of_an_online_conformal_loop.csv": "S5",
    "Process_domain_1.csv": "S6",
    "Process_domain_2.csv": "S7",
    "TEP_random-number_defect.csv": "S8",
    "Forward_citations_REF_searches_reference_lists_1.csv": "S9",
    "Forward_citations_REF_searches_reference_lists_2.csv": "S10",
    "Forward_citations_REF_searches_reference_lists_3.csv": "S11",
    "Forward_citations_REF_searches_reference_lists_4.csv": "S12",
    "savedrecs.xls": "W1",
    "savedrecs_1.xls": "W2",
    "savedrecs_2.xls": "W3",
    "savedrecs_3.xls": "W4",
    "savedrecs_4.xls": "W5",
    "savedrecs_5.xls": "W6",
    "savedrecs_6.xls": "W7",
    "savedrecs_7.xls": "W8",
}

# Second batch, received 2026-10-27, in a folder of its own: its S4 export has the name of a
# first-batch file. File -> role. Only the S4 export is screened; every file is hashed.
BATCH2 = {
    "Claim_ii_delay-limited_width_bound_2.csv": "S4",
    "Conformal_PID.xlsx": "W9",
    "SPCI.xls": "W10",
    "Search_1_-__quote_online_conformal_unquote___quote_multi-step_unquote___quote_forecast_errors_unquote_.txt": "G1",
    "Search_2_-__quote_online_conformal_prediction_unquote___quote_multi-horizon_unquote__forecasting.txt": "G2",
    "Search_3_-__quote_adaptive_conformal_prediction_unquote___quote_delayed_labels_unquote__forecasting.txt": "G3",
    "Search_4_-_debutanizer__quote_soft_sensor_unquote___quote_conformal_prediction_unquote__PID.txt": "G4",
}
BATCH2_TAG = "2026-10-27/"

# Third batch, received 2026-10-28: the citing sets of W9 (conformal PID, from the 28 variants)
# and W10 (SPCI, by the narrowed cited-reference search), Web of Science full records.
BATCH3 = {"W9.xls": "W9", "W10.xls": "W10"}
BATCH3_TAG = "2026-10-28/"
# The protocol's refinement of each citing set ("Search within results")
REFINE = ("delay*", "dead time", "latency", "step size", "learning rate")

# Decisions that differ from the default for the record's group, keyed by DOI, else by the
# Scopus EID or the WoS UT. (code, F4 item or topic, note)
DECISIONS = {
    # Read in full (rows 21 on of LITERATURE_SWEEP_N1.md)
    "2-s2.0-85172902769": (
        "F",
        "i",
        "Dixit et al. 2023: tau-step ACP updated with the error of the prediction made tau steps earlier; guarantee for one step only; no delay-dependent analysis",
    ),
    "2-s2.0-85209625972": (
        "F",
        "i",
        "Szabadvary 2024: per-step ACI with delayed errors; suggests larger step sizes for later steps; instability noted from a figure, not analysed",
    ),
    "2-s2.0-85163089038": (
        "F",
        "i",
        "Zaffran et al. 2022: theta = 0; Thm 3.1 (exchangeable) and 3.2 (AR(1) residuals) on the step size and efficiency; large steps give many infinite intervals; no delay",
    ),
    "2-s2.0-105013965330": (
        "F",
        "P2",
        "Retzlaff et al. 2025: VaR backtests; ACI passes marginal tests and fails independence tests for up to 88 of 98 stocks; no delay",
    ),
    "10.1609/aaai.v39i17.34029": (
        "F",
        "iii",
        "Li and Rodriguez 2025 (NCC): neural controller, horizons 1-4; delay not analysed; no ablation of the auxiliary forecasts under delay",
    ),
    "10.1109/ccta53793.2025.11151402": (
        "F",
        "-",
        "offline split conformal for driver warnings; the delay compensator acts on control commands",
    ),
    "10.3390/pr14193119": (
        "F",
        "i",
        "per-horizon controllers with an event queue; reports premature feedback in its own earlier evaluation; no stability or step-size analysis",
    ),
    "10.1016/j.apenergy.2025.126412": (
        "F",
        "i",
        "conformal PI control on day-ahead prices; delay not discussed; no sensitivity analysis",
    ),
    "2-s2.0-105050548379": (
        "F",
        "i",
        "online multiple testing with delayed feedback (FDR control); no interval loop",
    ),
    "10.1609/aaai.v39i16.33915": (
        "F",
        "i",
        "online P control of trajectory uncertainty; no delay handling or analysis",
    ),
    "10.1109/cdc57313.2025.11312645": (
        "F",
        "i",
        "per-step ACP with lagged feedback inside MPC; no stability or step-size analysis; no compensation",
    ),
    "10.1145/3744255.3798116": (
        "F",
        "iii",
        "conformal controller driven by a temporal-difference proxy for a delayed value; one-step lag; no delay analysis",
    ),
    "10.22266/ijies2026.0831.28": (
        "F",
        "i",
        "ACI window from lag-1 autocorrelation under AR(1); step size set separately; label delay tested only empirically",
    ),
    "10.3390/en19194741": (
        "F",
        "i",
        "per-horizon signed ACI updated once labels arrive; fixed step size; no delay analysis",
    ),
    "10.1016/j.orl.2026.107409": (
        "F",
        "i",
        "integral-type gain on the stockout count; no lead time, so no delayed feedback",
    ),
    "10.1016/j.ijforecast.2017.08.006": (
        "F",
        "ii",
        "Knuppel 2018: SUR estimator of h-step forecast-error variance (Wold form); no intervals or bound",
    ),
    # Read 2026-10-28 (rows 39 to 44); coded A before, with the full text not reached
    "10.1109/tte.2026.3734462": (
        "F",
        "iii",
        "read 2026-10-28 (row 40): adaptive CP tracking a radius on delayed indicators, d = 6 (Eq. 12), its step size raised by a label-free uncertainty signal (MIAD, Eq. 13); marginal PICP and PINAW only; nothing analysed in d",
    ),
    "10.1016/j.measurement.2026.122647": (
        "F",
        "process",
        "read 2026-10-28 (row 39): PID-guided conformal soft sensor on the sulfur recovery unit and a cooling load; labels used at once; Thm 1 bounds the miss run without delay",
    ),
    "10.1109/access.2026.3709868": (
        "F",
        "i",
        "read 2026-10-28 (row 42): graph-weighted ACI; a reference label enters after its interval is issued, with no delay length; eta tuned on a calibration segment",
    ),
    "10.1016/j.ast.2026.113895": (
        "F",
        "i",
        "read 2026-10-28 (row 42): projected quantile tracking fed by delayed truth (Eq. 20); eta = 0.01 fixed; no stability or step-size analysis",
    ),
    "10.1007/s11227-026-08865-z": (
        "F",
        "i",
        "read 2026-10-28 (row 42): split conformal on a past-only residual queue, appended when the h-step label arrives; no level recursion or step size",
    ),
    "10.3390/en19174093": (
        "F",
        "i",
        "read 2026-10-27: per-lead ACI with a projection (Eq. 15), fed h periods late; step size discussed qualitatively; no analysis of the lag",
    ),
    "10.1007/978-3-031-88036-0_16": (
        "F",
        "i",
        "read 2026-10-28 (row 43) in the 2024 master's thesis, the chapter not reached: ACI with a learning rate set from past steps; long-run coverage under a constant error law; no delay",
    ),
    # Third batch (citing sets of W9 and W10), 2026-10-28
    "WOS:001669603900061": (
        "F",
        "iii",
        "read 2026-10-28 (row 44), ICML 2025: quantile tracking linear in past scores (LQT), fixed and decaying learning rates; its gain grows with the scores' lag-1 autocorrelation; no delayed feedback",
    ),
    "10.1016/j.jii.2026.101218": (
        "X3",
        "process",
        "water virtual sensors: residual limits calibrated on earlier residuals, and change points, offline; no loop or delay",
    ),
    # Already known
    "2-s2.0-85187772172": ("X4", "iii", "conformal PID (rows 11, 16, 19, 20)"),
    "2-s2.0-85174420062": ("X4", "iii", "SPCI (rows 12, 18)"),
    "10.48550/arxiv.2208.08401": ("X4", "i", "Gibbs and Candes 2024, DtACI (project library)"),
    "2-s2.0-85203810313": ("X4", "i", "decaying step sizes (row 4)"),
    "10.1109/lsp.2025.3588085": ("X4", "i", "IM-OCP, intermittent feedback (row 1)"),
    "2-s2.0-85164726646": ("X4", "-", "Schlembach et al. 2022 (project library)"),
    # Off-claim, noted for the manuscript
    "2-s2.0-85203807872": ("X3", "i", "ACI by betting: parameter-free, no step size; no delay"),
    "2-s2.0-85203810289": (
        "X3",
        "i",
        "discounted adaptive online learning applied to online CP; no delay",
    ),
    "2-s2.0-105010275412": (
        "X3",
        "i",
        "ECI: continuous feedback in place of the miss indicator; no delay",
    ),
    "2-s2.0-105010223251": ("X3", "iii", "KOWCPI, an SPCI successor; no delay"),
    "2-s2.0-105010247101": (
        "X3",
        "i",
        "intermittent quantile tracking: intermittent, not delayed, labels",
    ),
    "10.1109/jsait.2026.3668947": (
        "X3",
        "i",
        "online CP over erasure channels: lost, not delayed, feedback",
    ),
    "10.1109/jsyst.2026.3710557": (
        "X3",
        "-",
        "conformal PID used in attack detection; no delay or step-size analysis",
    ),
    "10.1016/j.conengprac.2026.107078": (
        "X3",
        "-",
        "windowed coverage tracking for battery fault detection; no delay",
    ),
    "10.1016/j.rineng.2026.109806": (
        "X3",
        "process",
        "furnace: phase-aware conformal calibration, horizons 1-10 min; no online loop analysis",
    ),
    "10.1109/ai4im69129.2026.11558210": (
        "X3",
        "process",
        "soft-sensor review naming conformal prediction as an emerging direction",
    ),
    "10.1016/j.asoc.2024.112246": (
        "X3",
        "process",
        "interval soft sensor (Takagi-Sugeno) under scarce, irregular labels; not conformal",
    ),
    "10.3390/s26165157": (
        "X3",
        "process",
        "soft sensor with MC-dropout intervals under delayed, sparse assays; not conformal",
    ),
    "10.5194/hess-28-4099-2024": (
        "X3",
        "-",
        "hydrology: recent information helps even with gaps between updates; no loop",
    ),
    "2-s2.0-105039454602": (
        "X3",
        "ii",
        "Barber and Pananjady: split-CP coverage under beta-mixing; no width bound",
    ),
    "10.1016/j.seta.2026.105403": (
        "X3",
        "P2",
        "aggregate coverage hides daylight under-coverage; split CP",
    ),
    "10.1057/s41283-026-00243-6": (
        "X3",
        "i",
        "multi-speed aggregation (DtACI family) for VaR intervals; no delay",
    ),
    "10.3390/a19080704": (
        "X3",
        "i",
        "ACI matches on coverage only when its step size is tuned; no delay analysis",
    ),
    "10.1016/j.egyai.2025.100571": ("X3", "-", "EnbPI and SPCI on electricity prices"),
    "10.1007/978-3-031-77066-1_1": ("X3", "-", "EnbPI and SPCI on electricity prices"),
    "10.1109/tste.2026.3727059": (
        "X3",
        "-",
        "control conformal inference for multi-site wind; no delay analysis",
    ),
    "10.1007/s10489-018-1335-7": (
        "X3",
        "i",
        "quantile tracking with a step proportional to the error; no delay",
    ),
    "2-s2.0-105000558182": ("X3", "-", "localized adaptive risk control; no delay"),
    "2-s2.0-105032509150": ("X3", "i", "gradient equilibrium with constant step sizes; no delay"),
    "2-s2.0-105000223708": ("X3", "-", "calibrated forecasts by approachability; no delay"),
    "10.1007/s10115-026-02845-8": (
        "X3",
        "-",
        "stream interval post-calibration from observed coverage; no delay",
    ),
    # 2026-10-28, from the third pass of the check: interval methods without the word
    # "conformal", which the default for the reference-list searches coded X2
    "10.1016/j.aei.2025.103979": (
        "X3",
        "-",
        "interval prediction (PICP, PINAW) by frequency-domain learning and fuzzy rules; no loop",
    ),
    "10.1145/3744255.3798120": (
        "X3",
        "-",
        "carbon-intensity forecasts with 95 % prediction intervals; no loop",
    ),
    "10.1145/3690624.3709286": (
        "X3",
        "-",
        "distribution-free probabilistic inference for regression and forecasting; no loop",
    ),
    "10.1016/j.epidem.2025.100820": (
        "X3",
        "-",
        "quantile autoregressive forecasts scored by weighted interval score; no loop",
    ),
    "10.1186/s41182-025-00723-7": (
        "X3",
        "-",
        "forecasting methods compared on their uncertainty intervals; no loop",
    ),
}

STAT_SENSE = re.compile(
    r"conformal(i[sz]ed|i[sz]ing|i[sz]e|i[sz]ation)?[\s\-]+(predict|inference|calibrat|risk|interval|"
    r"quantile|regress|band|set|score|method|framework|PID|control|decision|filter|reliab|recover|"
    r"selection|screen|lyapunov|anomaly|bound|guarantee|uncertain|approach|procedure|learn|perception|"
    r"state|imputation|counterfactual|online|time|policy|compression|forecast|classif|test|threshold|"
    r"machine|correct|layer|bayes|joint|technique|tool|algorithm|weight|gating|safety|wrapper|"
    r"mechanism|model|aggregat|adjust|module|step|calibrator)"
    r"|conformali[sz]|nonconformity|non-conformity|split[\s\-]+conformal|online[\s\-]+conformal|"
    r"adaptive[\s\-]+conformal|conformal[\s\-]+(and|or)[\s\-]+",
    re.I,
)


def _base(path: str) -> str:
    b = os.path.basename(path)
    return re.sub(r"^[0-9a-f]{8}-", "", b)


def norm_doi(d: str) -> str:
    d = (d or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def norm_title(t: str) -> str:
    t = re.sub(r"\[[^\]]*\]", " ", (t or "").lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def find(folder: str, names) -> dict[str, str]:
    """Base name -> path for every name, the upload prefix allowed; other files are ignored."""
    found: dict[str, str] = {}
    for f in glob.glob(os.path.join(folder, "*")):
        b = _base(f)
        if b in names:
            if b in found:
                raise SystemExit(f"{folder}: {b} is there twice")
            found[b] = f
    missing = sorted(set(names) - set(found))
    if missing:
        raise SystemExit(f"{folder}: missing {missing}")
    return dict(sorted(found.items()))


def _scopus(path: str, name: str) -> list[dict]:
    recs = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            recs.append(
                {
                    "db": "Scopus",
                    "file": name,
                    "row": i + 1,
                    "id": r.get("EID", ""),
                    "title": r.get("Title", ""),
                    "authors": r.get("Authors", ""),
                    "year": r.get("Year", ""),
                    "source": r.get("Source title", ""),
                    "doi": norm_doi(r.get("DOI", "")),
                    "abstract": r.get("Abstract", ""),
                    "kw": r.get("Author Keywords", ""),
                    "ikw": r.get("Index Keywords", ""),
                    "exported": "",
                }
            )
    return recs


def _xls_rows(path: str) -> list[dict]:
    import xlrd  # noqa: PLC0415

    sh = xlrd.open_workbook(path).sheet_by_index(0)
    head = sh.row_values(0)

    def cell(x) -> str:
        return str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)

    return [dict(zip(head, map(cell, sh.row_values(i)), strict=True)) for i in range(1, sh.nrows)]


def _wos(path: str, name: str) -> list[dict]:
    return [
        {
            "db": "WoS",
            "file": name,
            "row": i + 1,
            "id": g["UT (Unique WOS ID)"],
            "title": g["Article Title"],
            "authors": g["Authors"],
            "year": g["Publication Year"],
            "source": g["Source Title"],
            "doi": norm_doi(g["DOI"]),
            "abstract": g["Abstract"],
            "kw": g["Author Keywords"],
            "ikw": g["Keywords Plus"],
            "exported": g["Date of Export"],
        }
        for i, g in enumerate(_xls_rows(path))
    ]


def _xlsx_rows(path: str) -> list[dict]:
    """First sheet of an .xlsx file, read with the standard library. (W9's file declares its
    extent as the single cell A1, which readers that trust the declaration take literally.)"""
    import zipfile  # noqa: PLC0415
    from xml.etree import ElementTree  # noqa: PLC0415

    m = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(m + "t")) for si in root.iter(m + "si")]
        sheet = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml"))
    table = []
    for row in sheet.iter(m + "row"):
        cells = {}
        for c in row.iter(m + "c"):
            col = re.match(r"[A-Z]+", c.get("r")).group()
            if c.get("t") == "inlineStr":
                cells[col] = "".join(t.text or "" for t in c.iter(m + "t"))
            else:
                v = c.find(m + "v")
                x = "" if v is None else (v.text or "")
                cells[col] = shared[int(x)] if c.get("t") == "s" else x
        table.append(cells)
    head = table[0]
    return [{head[k]: r.get(k, "") for k in head} for r in table[1:]]


def load(raw: str, raw2: str, raw3: str) -> tuple[list[dict], dict, dict, dict]:
    """Records of the three batches, in a fixed order: the first batch's Scopus files, then its
    WoS files, each by name; then the second batch's S4 export; then the third batch's files by
    name. The order sets the uid."""
    f1 = find(raw, FILE_TO_QUERY)
    f2 = find(raw2, BATCH2)
    f3 = find(raw3, BATCH3)
    recs = []
    for name, path in f1.items():
        if name.endswith(".csv"):
            recs += _scopus(path, name)
    for name, path in f1.items():
        if name.endswith(".xls"):
            recs += _wos(path, name)
    for r in recs:
        r["query"] = FILE_TO_QUERY[r["file"]]
    for name, path in f2.items():
        if BATCH2[name] == "S4":
            for r in _scopus(path, BATCH2_TAG + name):
                recs.append({**r, "query": "S4"})
    for name, path in f3.items():
        recs += [{**r, "query": BATCH3[name]} for r in _wos(path, BATCH3_TAG + name)]
    for r in recs:
        r["tkey"] = norm_title(r["title"])
    return recs, f1, f2, f3


def w9_summary(path: str) -> dict:
    """W9 as received: the cited-reference list of the search (Cited Author Angelopoulos A*,
    Cited Year 2023), not the citing records. Counts the variants of the conformal PID paper
    and the citing links they carry. Variants are matched on title or cited work, letters only,
    so that "Con- formal PID control" is caught."""
    rows = _xlsx_rows(path)
    var = [
        r
        for r in rows
        if "conformalpidcontrol" in re.sub(r"[^a-z]", "", (r["TI"] + r["SO"]).lower())
    ]
    return {
        "file": BATCH2_TAG + _base(path),
        "rows": len(rows),
        "cited_years": sorted({r["PY"] for r in rows}),
        "conformal_pid_variants": len(var),
        "citing_links": int(sum(float(r["TC"] or 0) for r in var)),
        "note": "the cited-reference list; the citing set of these variants is W9.xls of 2026-10-28",
    }


def w10_summary(path: str) -> dict:
    """W10 as received: SPCI's own Web of Science record, found by its title."""
    (g,) = _xls_rows(path)
    return {
        "file": BATCH2_TAG + _base(path),
        "ut": g["UT (Unique WOS ID)"],
        "title": g["Article Title"],
        "source": g["Source Title"],
        "times_cited_core": int(g["Times Cited, WoS Core"]),
        "times_cited_all": int(g["Times Cited, All Databases"]),
        "exported": g["Date of Export"],
        "note": "no citing record is linked to it; the narrowed cited-reference search is W10.xls of 2026-10-28",
    }


# ---- approximate evaluation of the issued strings (mapping check only) ----
def _toks(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower().replace("-", " "))


def _rx(term: str) -> re.Pattern:
    t = re.escape(term.lower()).replace(r"\*", "[a-z0-9]*").replace(r"\?", "[a-z0-9]")
    return re.compile(rf"^{t}(s|es)?$")


def _pos(tok: list[str], phrase: str) -> list[int]:
    rxs = [_rx(p) for p in re.split(r"[\s\-]+", phrase.strip()) if p]
    n = len(rxs)
    return [i for i in range(len(tok) - n + 1) if all(rxs[k].match(tok[i + k]) for k in range(n))]


def _any(tok, *ph):
    return sorted({i for p in ph for i in _pos(tok, p)})


def _near(a, b, n):
    return any(abs(i - j) <= n + 1 for i in a for j in b)


def satisfies(r: dict, q: str) -> bool:
    tok = _toks(" ".join([r["title"], r["abstract"], r["kw"], r["ikw"]]))
    has = lambda *ph: bool(_any(tok, *ph))  # noqa: E731
    c = _pos(tok, "conformal")
    if q in ("S1", "W1"):
        return _near(c, _any(tok, "predict*", "inference", "calibrat*", "interval*"), 2) and (
            _near(
                _pos(tok, "delay*"),
                _any(
                    tok,
                    "feedback",
                    "label*",
                    "observation*",
                    "outcome*",
                    "measurement*",
                    "response*",
                ),
                1,
            )
            or has("dead time", "deadtime", "latency")
        )
    if q in ("S2", "W2"):
        return (
            has("adaptive conformal", "online conformal", "conformal PID", "quantile tracking")
            or _near(c, _any(tok, "online", "adaptive", "sequential"), 3)
        ) and (
            has(
                "step size*",
                "learning rate*",
                "stabilit*",
                "oscillat*",
                "limit cycle*",
                "control theoretic",
            )
            or _near(_pos(tok, "integral"), _pos(tok, "control*"), 2)
        )
    if q in ("S3", "W3"):
        return (
            (bool(c) or has("prediction interval*", "predictive interval*"))
            and has(
                "minimum variance",
                "Harris index",
                "control performance assessment",
                "forecast error variance",
                "prediction error variance",
            )
            and has("delay*", "dead time", "horizon*")
        )
    if q == "S4":
        return (
            _near(_any(tok, "prediction interval*", "conformal"), _pos(tok, "width"), 10)
            and (
                has("autocorrelat*", "forecast horizon*")
                or _near(_pos(tok, "analy?er"), _any(tok, "delay*", "speed", "cycle"), 2)
            )
            and has("bound*", "limit*", "achievable", "minimum")
        )
    if q == "W4":
        return (
            _near(_pos(tok, "predict*"), _pos(tok, "interval*"), 2)
            and has("width")
            and has("autocorrelat*", "forecast horizon", "analyzer", "analyser")
            and has("bound*", "limit*", "achievable", "minimum")
        )
    if q in ("S5", "W5"):
        return (
            bool(c)
            and (
                has("scorecaster*")
                or _near(
                    _any(tok, "score", "residual*", "quantile*"),
                    _any(tok, "forecast*", "predict*", "model*"),
                    2,
                )
            )
            and has("online", "adaptive", "sequential", "time series")
            and has(
                "delay*",
                "multi-step",
                "multistep",
                "horizon*",
                "local coverage",
                "conditional coverage",
                "step size",
                "learning rate",
            )
        )
    if q in ("S6", "W6"):
        return (
            has("soft sensor*", "inferential sensor*", "virtual sensor*", "virtual metrology")
            and (
                bool(c)
                or has(
                    "prediction interval*", "uncertainty quantification", "predictive uncertainty"
                )
            )
            and (
                _near(
                    _pos(tok, "delay*"),
                    _any(tok, "analy?er", "laborator*", "measurement*", "label*", "sampling"),
                    2,
                )
                or has("dead time", "infrequent", "irregular*")
            )
        )
    if q in ("S7", "W7"):
        return (bool(c) or has("prediction interval*", "uncertainty quantification")) and (
            has("Smith predictor*")
            or _near(_any(tok, "dead time", "deadtime", "time delay"), _pos(tok, "compensat*"), 2)
        )
    if q in ("S8", "W8"):
        return has("Tennessee Eastman") and (
            has("random number*", "pseudorandom", "pseudo random", "random seed*")
            or _near(
                _pos(tok, "seed*"), _any(tok, "independen*", "replicat*", "repeat*", "period*"), 3
            )
            or _near(_pos(tok, "noise"), _pos(tok, "generat*"), 2)
        )
    if q == "S12":  # the TITLE-ABS-KEY part only; REF() cannot be checked from the export
        return has("delay*", "dead time", "latency", "step size", "learning rate")
    # S9 to S11 (REF() searches) and the citing sets W9 and W10, whose exports carry no cited
    # references: not checkable from the export
    return True


def dedupe(recs: list[dict]) -> list[dict]:
    uniq, by_doi, by_title = [], {}, {}
    for r in recs:
        k = by_doi.get(r["doi"]) if r["doi"] else None
        if k is None:
            k = by_title.get(r["tkey"])
        if k is None:
            k = len(uniq)
            keep = ("title", "authors", "year", "source", "doi", "abstract", "kw", "ikw", "tkey")
            uniq.append({**{f: r[f] for f in keep}, "hits": [], "ids": {}})
        u = uniq[k]
        if (r["db"], r["query"]) not in u["hits"]:
            u["hits"].append((r["db"], r["query"]))
        u["ids"].setdefault(r["db"], r["id"])
        if len(r["abstract"]) > len(u["abstract"]):
            u["abstract"] = r["abstract"]
        if not u["doi"] and r["doi"]:
            u["doi"] = r["doi"]
        if u["doi"]:
            by_doi[u["doi"]] = k
        by_title[u["tkey"]] = k
        by_title[r["tkey"]] = k
    for i, u in enumerate(uniq):
        u["uid"] = f"R{i + 1:03d}"
        u["key"] = u["doi"] or u["ids"].get("Scopus") or u["ids"].get("WoS")
    return uniq


def decide(u: dict) -> tuple[str, str, str]:
    if u["key"] in DECISIONS:
        return DECISIONS[u["key"]]
    text = " ".join([u["title"], u["abstract"], u["kw"], u["ikw"]])
    qs = {q for _, q in u["hits"]}
    if STAT_SENSE.search(text):
        return ("X3", "-", "")
    if re.search("conformal", text, re.I):
        return ("X1", "-", "")
    if qs & {"S8", "W8"}:
        return ("X5", "3D", "")
    if qs & {"S7", "W7"}:
        return ("X6", "-", "")
    # strings that admit interval methods other than conformal ones
    if qs & {"S3", "W3", "S4", "W4", "S6", "W6"}:
        return ("X3", "-", "")
    return ("X2", "-", "")


def _qsort(q: str) -> tuple:
    return (q[0], int(q[1:]))


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: n1_screening.py FOLDER_2026-10-22 FOLDER_2026-10-27 FOLDER_2026-10-28"
        )
    raw, raw2, raw3 = sys.argv[1], sys.argv[2], sys.argv[3]
    recs, f1, f2, f3 = load(raw, raw2, raw3)

    def sha(path: str) -> str:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    manifest = {name: sha(path) for name, path in f1.items()}
    manifest.update({BATCH2_TAG + name: sha(path) for name, path in f2.items()})
    manifest.update({BATCH3_TAG + name: sha(path) for name, path in f3.items()})
    by_role = {role: f2[name] for name, role in BATCH2.items()}
    # mapping check
    print("export".ljust(62), "query", "records", "satisfy its string")
    check = {}
    for f in sorted({r["file"] for r in recs}):
        rs = [r for r in recs if r["file"] == f]
        q = rs[0]["query"]
        k = sum(satisfies(r, q) for r in rs)
        check[f] = {"query": q, "records": len(rs), "satisfy": k}
        print(f.ljust(62), q.ljust(5), str(len(rs)).rjust(7), f"{k}/{len(rs)}")
    uniq = dedupe(recs)
    rows = []
    for u in uniq:
        code, item, note = decide(u)
        dbs = sorted({d for d, _ in u["hits"]})
        qs = sorted({q for _, q in u["hits"]}, key=_qsort)
        first = (u["authors"].split(";")[0] or "").strip()
        rows.append(
            {
                "uid": u["uid"],
                "key": u["key"],
                "databases": "+".join(dbs),
                "queries": " ".join(qs),
                "year": u["year"],
                "first_author": first,
                "title": u["title"],
                "source": u["source"],
                "code": code,
                "item": item,
                "note": note,
            }
        )
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    # LF line ends, so that the files are byte-identical on Windows and Linux
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    per_query = defaultdict(lambda: {"rows": 0, "unique": 0, "F": 0, "A": 0})
    for r in recs:
        per_query[r["query"]]["rows"] += 1
    for row in rows:
        for q in row["queries"].split():
            per_query[q]["unique"] += 1
            if row["code"] in ("F", "A"):
                per_query[q][row["code"]] += 1
    # S3 was received twice; count its rows once
    per_query["S3"]["rows"] //= 2
    summary = {
        "records_received": len(recs),
        "records_counting_S3_once": len(recs) - per_query["S3"]["rows"],
        "unique": len(uniq),
        "in_scopus": sum("Scopus" in r["databases"] for r in rows),
        "in_wos": sum("WoS" in r["databases"] for r in rows),
        "in_both": sum(r["databases"] == "Scopus+WoS" for r in rows),
        "codes": dict(sorted(Counter(r["code"] for r in rows).items())),
        "per_query": {q: per_query[q] for q in sorted(per_query, key=_qsort)},
        "mapping_check": check,
        "mapping_check_note": (
            "S9 to S11 (REF() searches) and the citing sets W9 and W10 cannot be checked from"
            " their exports, so their 'satisfy' counts equal their records by construction"
        ),
        "raw_sha256": manifest,
        "wos_export_dates": sorted({r["exported"] for r in recs if r["db"] == "WoS"}),
        "w9_cited_reference_list": w9_summary(by_role["W9"]),
        "w10_source_record": w10_summary(by_role["W10"]),
        "citing_sets_refined": {
            q: sum(
                bool(_any(_toks(" ".join([r["title"], r["abstract"], r["kw"], r["ikw"]])), *REFINE))
                for r in recs
                if r["file"].startswith(BATCH3_TAG) and r["query"] == q
            )
            for q in sorted(set(BATCH3.values()), key=_qsort)
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(summary, fh, indent=1)
        fh.write("\n")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "records_received",
                    "records_counting_S3_once",
                    "unique",
                    "in_scopus",
                    "in_wos",
                    "in_both",
                    "codes",
                    "w9_cited_reference_list",
                    "w10_source_record",
                    "citing_sets_refined",
                )
            },
            indent=1,
        )
    )
    for q, v in summary["per_query"].items():
        print(q, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
