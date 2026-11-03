"""LaTeX bodies (booktabs) of the N1 paper's tables, written from the Phase 1 evidence.

- n1_table_rules.tex: the decided rules F1 to F8 and their verdicts (phase1_verdicts.json).
- n1_table_t1_cells.tex: seven cells of T1 at theta = 4, means over the 15 runs, and the paired
  contrast of compensation (phase1_stageB_T1.json, `summary`).
- n1_table_baselines.tex: the four baselines against the compensated loop (F7).
Each body is the tabular environment only; the manuscript supplies caption and label. Widths: in
the T1 table, the median of the finite widths of a run (`width_median`); in the baselines table,
F7's run-median width, over all issued intervals with an infinite interval counted as infinitely
wide (`f7_median_width`, pre-registration Section 6). Both are means over the 15 runs. Negative
numbers are set with a math minus in the LaTeX bodies; the CSV copies keep plain text.
"""

from __future__ import annotations

import re
from pathlib import Path

from .style import FIGURE_DIR, load, save_csv


def pp(x: float, d: int = 2) -> str:
    return f"{100 * x:.{d}f}"


def ci(c: dict, scale: float = 100.0, d: int = 2) -> str:
    return f"[{scale * c['lo']:.{d}f}, {scale * c['hi']:.{d}f}]"


def tex_minus(cell: str) -> str:
    """A hyphen before a digit becomes a math minus."""
    return re.sub(r"(?<![\w$\\])-(?=\d)", "$-$", cell)


def tex_row(cells: list[str]) -> str:
    return " & ".join(tex_minus(c) for c in cells) + " \\\\"


def write(name: str, body: str, out_dir: Path | None = None) -> Path:
    d = out_dir or FIGURE_DIR
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.tex"
    p.write_text(body, encoding="utf-8", newline="\n")
    return p


def rules_table(v: dict) -> tuple[str, list[list[str]]]:
    dec = v["decided"]
    f2t, f2d = dec["F2"]["tep_T1_theta4"], dec["F2"]["debutanizer_theta3"]
    f3 = dec["F3"]["cells"]["tep_T1_theta4"]
    f6, f7, f8, f1 = dec["F6"], dec["F7"], dec["F8"], dec["F1"]
    n_pos = sum(x > 0 for x in f2t["diff_per_run"])
    n_neg = sum(x < 0 for x in f8["iact_diff_per_run"])
    valid = [f7[n] for n, _ in BASELINES if f7[n]["baseline"]["valid"]]
    closest = min(
        (r["coverage_matched_gaussian"] for r in valid), key=lambda g: g["width_change_pct"]
    )
    in_region = [c for c in f1["cells"].values() if c["in_region"]]
    esd = [c["err_sd"] for c in in_region]
    n_off = sum(bool(c["off_by_25pct"]) for c in in_region)
    rows = [
        [
            "F2",
            r"TEP T1, $\theta=4$ vs 0",
            rf"$\Delta U$ = {pp(f2t['ci975']['mean'])} pp, 97.5\,\% CI {ci(f2t['ci975'])}; "
            rf"{n_pos} of {len(f2t['diff_per_run'])} runs",
            "shown" if f2t["shows_increase"] else "not shown",
        ],
        [
            "F2",
            r"Debutanizer, $\theta=3$ vs 0",
            rf"$\Delta U$ = {pp(f2d['ci975']['mean'])} pp, 97.5\,\% CI {ci(f2d['ci975'])} "
            rf"({f2d['ci975']['blocks']} blocks)",
            "shown" if f2d["shows_increase"] else "not shown",
        ],
        [
            "F3",
            r"TEP T1, $\theta=4$",
            rf"coverage {f3['coverage']:.4f}, Wilson 95\,\% "
            rf"[{f3['wilson95'][0]:.4f}, {f3['wilson95'][1]:.4f}]",
            "fires" if dec["F3"]["fires"] else "does not fire",
        ],
        [
            "F5a",
            r"TEP T1, $\theta=4$, uncompensated",
            rf"mean $U$ = {pp(dec['F5a']['mean_u'])}\,\% (budget {pp(dec['F5a']['budget'], 0)}\,\%)",
            "fires" if dec["F5a"]["fires"] else "does not fire",
        ],
        [
            "F5b",
            r"TEP T1, $\theta=4$, compensated",
            rf"mean $U$ = {pp(dec['F5b']['mean_u'])}\,\% (budget {pp(dec['F5b']['budget'], 0)}\,\%)",
            "fires" if dec["F5b"]["fires"] else "does not fire",
        ],
        [
            "F6",
            "P3 at TEP T1, $\\theta=4$",
            rf"measured/predicted $-$ 1 = {100 * f6['mean_error']:.1f}\,\%, "
            rf"95\,\% CI {ci(f6['error_ci95'], 100, 1)}",
            "fires" if f6["fires"] else "does not fire",
        ],
        [
            "F7",
            "Four baselines",
            rf"none valid and narrower; closest valid {closest['width_change_pct']:+.1f}\,\% "
            rf"({closest['runs_narrower']} of 15 runs)",
            "fires" if f7["fires"] else "does not fire",
        ],
        [
            "F8",
            rf"TEP T1, $\theta=4$ (predicted ratio {f8['mean_predicted_ratio']:.3f}, "
            rf"gate {f8['gate']:g})",
            rf"$\Delta$IACT = {f8['ci95']['mean']:.2f}, 95\,\% CI {ci(f8['ci95'], 1, 2)}; "
            rf"lower in {n_neg} of {len(f8['iact_diff_per_run'])} runs",
            "fires" if f8["fires"] else "does not fire",
        ],
        [
            "F8",
            "Step size",
            rf"{', '.join(f'{g:g}' for g in f8['gamma_comp_by_regime'])} vs "
            rf"{', '.join(f'{g:g}' for g in f8['gamma_raw_by_regime'])}",
            "statement made" if f8["step_statement_made"] else "no statement",
        ],
        [
            "F1",
            f"{len(in_region)} cells in the design region",
            rf"sd($\alpha$) error {100 * min(esd):.0f} to {100 * max(esd):.0f}\,\%; "
            rf"{n_off} of {len(in_region)} off by more than 25\,\%",
            "fires" if f1["fires"] else "does not fire",
        ],
    ]
    body = [
        "\\begin{tabular}{@{}llll@{}}",
        "\\toprule",
        "Rule & Cell & Result & Verdict \\\\",
        "\\midrule",
    ]
    body += [tex_row(r) for r in rows]
    body += ["\\bottomrule", "\\end{tabular}", ""]
    return "\n".join(body), rows


T1_CELLS = (
    ("raw|none|-", "Uncompensated, loop off"),
    ("raw|sequential|blind", "Uncompensated, delay-blind"),
    ("raw|sequential|design", "Uncompensated, white-noise rule"),
    ("raw|sequential|aware_half", r"Uncompensated, replay to $\varepsilon/2$"),
    ("comp|none|-", "Compensated, loop off"),
    ("comp|sequential|blind", "Compensated, delay-blind"),
    ("comp|sequential|aware_half", r"Compensated, replay to $\varepsilon/2$"),
)
T1_METRICS = (
    ("u", 100.0, 2),
    ("coverage", 1.0, 4),
    ("width_median", 1.0, 3),
    ("local_cov_min", 1.0, 3),
    ("alpha_sd", 1.0, 4),
    ("iact", 1.0, 2),
)


def t1_table(b: dict) -> tuple[str, list[list[str]]]:
    cells = b["summary"]["cells"]
    rows = []
    for key, label in T1_CELLS:
        c = cells[f"theta=4|{key}|stored"]
        rows.append([label] + [f"{s * c[m]['mean']:.{d}f}" for m, s, d in T1_METRICS])
    x = b["summary"]["contrasts"]["comp_minus_raw"]["theta=4|sequential|aware_half|stored"]
    rows.append(
        [r"Compensated $-$ uncompensated, replay"]
        + [f"{s * x[m]['mean']:+.{d}f}" if m in x else "--" for m, s, d in T1_METRICS]
    )
    rows.append(
        ["\\quad 95\\,\\% CI"] + [ci(x[m], s, d) if m in x else "--" for m, s, d in T1_METRICS]
    )
    head = (
        "Cell & $U$ (\\%) & Coverage & Median width & Worst rolling coverage & "
        "sd($\\alpha$) & IACT \\\\"
    )
    body = ["\\begin{tabular}{@{}lrrrrrr@{}}", "\\toprule", head, "\\midrule"]
    body += [tex_row(r) for r in rows[:4]]
    body += ["\\addlinespace"] + [tex_row(r) for r in rows[4:7]]
    body += ["\\midrule"] + [tex_row(r) for r in rows[7:]]
    body += ["\\bottomrule", "\\end{tabular}", ""]
    return "\n".join(body), rows


BASELINES = (
    ("pid_qr", "Conformal PID, quantile scorecaster"),
    ("pid_theta", "Conformal PID, theta scorecaster"),
    ("pid_matched", "Conformal PID, matched scorecaster"),
    ("spci", "SPCI multi-step"),
)


def baselines_table(v: dict) -> tuple[str, list[list[str]]]:
    f7 = v["decided"]["F7"]
    loop = f7["spci"]["loop"]
    loop_w = f7["spci"]["coverage_matched_gaussian"]["loop_mean_width"]
    rows = [
        [
            "Compensated loop, replay to $\\varepsilon/2$",
            pp(loop["mean_u"]),
            f"{loop['mean_coverage']:.4f}",
            "yes" if loop["valid"] else "no",
            f"{loop_w:.3f}",
            "--",
            "--",
        ]
    ]
    for name, label in BASELINES:
        r = f7[name]
        g, u = r["coverage_matched_gaussian"], r["unscaled"]
        rows.append(
            [
                label,
                pp(r["baseline"]["mean_u"]),
                f"{r['baseline']['mean_coverage']:.4f}",
                "yes" if r["baseline"]["valid"] else "no",
                f"{u['mean_width']:.3f}",
                f"{g['width_change_pct']:+.1f}\\,\\% ({g['runs_narrower']}/15)",
                "yes" if r["fires"] else "no",
            ]
        )
    head = (
        "Method & $U$ (\\%) & Coverage & Valid & Run-median width & "
        "Coverage-matched width change & F7 fires \\\\"
    )
    body = ["\\begin{tabular}{@{}lrrcrrc@{}}", "\\toprule", head, "\\midrule"]
    body += [tex_row(r) for r in rows]
    body += ["\\bottomrule", "\\end{tabular}", ""]
    return "\n".join(body), rows


def render(in_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    v = load("phase1_verdicts", in_dir)
    b = load("phase1_stageB_T1", in_dir)
    paths = []
    for name, (tex, rows), header in (
        ("n1_table_rules", rules_table(v), ["rule", "cell", "result", "verdict"]),
        ("n1_table_t1_cells", t1_table(b), ["cell", *[m for m, _, _ in T1_METRICS]]),
        (
            "n1_table_baselines",
            baselines_table(v),
            ["method", "u_pct", "coverage", "valid", "median_width", "matched_change", "fires"],
        ),
    ):
        paths.append(write(name, tex, out_dir))
        paths.append(save_csv(rows, header, name, out_dir))
    return paths


if __name__ == "__main__":
    for p in render():
        print(p)
