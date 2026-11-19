"""Supplementary tables of the N1 paper: every cell, contrast and baseline of Phase 1.

Written from the stage B evidence to docs/paper/figures/n1/:
- n1_supp_cells.csv: every loop cell of every unit (T1, T1_gb, T2, T3, debutanizer) with its
  key fields, the step size per regime and the Section 5.4 metrics. TEP units: the mean over the
  15 runs, with the 95 % t interval where the stage B summary holds one, and run means of the
  width percentiles. Debutanizer: the single stream's values, with the 95 % circular block
  bootstrap interval of U and coverage over all evaluation rows (stage B `intervals`).
- n1_supp_contrasts.csv: every paired contrast (TEP: mean and 95 % t interval over the runs;
  debutanizer: block bootstrap over all evaluation rows).
- n1_supp_baselines.csv: the four baselines at every theta of the units that ran them (T1 and the
  debutanizer; pre-registration Appendix A).
- n1_supp_primary_<unit>.tex: the sequential loop with stored pairing, under every step-size
  policy and with the loop off, uncompensated and compensated, at every theta of the unit.
- n1_supp_loops.tex: every loop and policy at T1, theta = 4.
- n1_supp_baselines.tex: the four baselines beside the compensated loop (replay to eps / 2) at
  every theta of T1 and the debutanizer.
Each .tex file is a tabular body; the supplement supplies caption and label. Nothing is computed
that the evidence does not hold, except run means of per-run values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .style import load, save_csv
from .tables import tex_row, write

TEP_UNITS = ("T1", "T1_gb", "T2", "T3")
UNITS = (*TEP_UNITS, "debutanizer")
COMPS = (("raw", "uncompensated"), ("comp", "compensated"))
POLICIES = (
    ("none|-", "loop off (split conformal)"),
    ("sequential|fixed_0.005", "fixed step 0.005"),
    ("sequential|fixed_0.05", "fixed step 0.05"),
    ("sequential|blind", "delay-blind"),
    ("sequential|aware_eps", r"replay to $\varepsilon$"),
    ("sequential|aware_half", r"replay to $\varepsilon/2$"),
    ("sequential|design", "white-noise rule"),
)
LOOPS = (
    ("sequential", "sequential"),
    ("projected", "projected"),
    ("phase", "interleaved"),
    ("smith", "Smith form"),
    ("decaying", "decaying"),
)
LOOP_POLICIES = (
    ("fixed_0.005", "0.005"),
    ("fixed_0.05", "0.05"),
    ("blind", "delay-blind"),
    ("aware_eps", r"replay $\varepsilon$"),
    ("aware_half", r"replay $\varepsilon/2$"),
    ("design", "white-noise"),
)
BASELINES = ("pid_qr", "pid_theta", "pid_matched", "spci")
METRICS = (
    "u",
    "infinite_share",
    "coverage",
    "width_median",
    "width_p90",
    "width_p99",
    "f7_median_width",
    "local_cov_min",
    "alpha_sd",
    "iact",
    "acf1",
    "mean_miss_run",
)
CELL_HEADER = [
    "unit",
    "theta",
    "comp",
    "loop",
    "policy",
    "pairing",
    "runs",
    "gamma_by_regime",
    "tuning_feasible_by_regime",
    *[f"{m}_{s}" for m in METRICS for s in ("mean", "lo95", "hi95")],
]


def parse_key(key: str) -> dict[str, Any]:
    """'theta=4|raw|sequential|aware_half|stored' (the loop-off cell has policy '-')."""
    parts = key.split("|")
    out = {"theta": int(parts[0].split("=")[1]), "comp": parts[1], "loop": parts[2]}
    out["policy"] = parts[3]
    out["pairing"] = parts[4] if len(parts) > 4 else "stored"
    return out


def fmt(x: Any, d: int = 6) -> str:
    if x is None:
        return ""
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int | float):
        return f"{x:.{d}g}"
    return str(x)


def by_regime(runs: dict[str, dict], regime_of: dict[str, str], field: str) -> str:
    """One value per regime (the five runs of a regime share their tuning)."""
    seen: dict[str, Any] = {}
    for stream, m in runs.items():
        reg = regime_of.get(stream, stream)
        if field in m and reg not in seen:
            seen[reg] = m[field]
    return "; ".join(f"{r}: {fmt(v)}" for r, v in sorted(seen.items()))


def run_mean(runs: dict[str, dict], field: str) -> float | None:
    vals = [m[field] for m in runs.values() if field in m and m[field] is not None]
    return sum(vals) / len(vals) if vals else None


def tep_cells(unit: str, b: dict) -> list[list[str]]:
    rows = []
    summ = b["summary"]["cells"]
    for key, runs in b["cells"].items():
        if any("not_run" in m for m in runs.values()):
            continue
        k = parse_key(key)
        s = summ.get(key, {})
        row = [unit, k["theta"], k["comp"], k["loop"], k["policy"], k["pairing"], len(runs)]
        row += [by_regime(runs, b["regime_of"], "gamma")]
        row += [by_regime(runs, b["regime_of"], "tuning_feasible")]
        for m in METRICS:
            if m in s and isinstance(s[m], dict):
                row += [fmt(s[m]["mean"]), fmt(s[m]["lo"]), fmt(s[m]["hi"])]
            else:
                row += [fmt(run_mean(runs, m)), "", ""]
        rows.append([fmt(x) for x in row])
    return rows


def debutanizer_cells(b: dict) -> list[list[str]]:
    rows = []
    iv = b["intervals"]["cells"]
    for key, runs in b["cells"].items():
        m = runs["debutanizer/0"]
        if "not_run" in m:
            continue
        k = parse_key(key)
        ci = iv.get(key, {}).get("all_rows", {})
        row = [
            "debutanizer",
            k["theta"],
            k["comp"],
            k["loop"],
            k["policy"],
            k["pairing"],
            1,
            fmt(m.get("gamma")),
            fmt(m.get("tuning_feasible")),
        ]
        for name in METRICS:
            boot = {"u": ci.get("u"), "infinite_share": ci.get("inf"), "coverage": ci.get("cov")}
            c = boot.get(name)
            row += [fmt(m.get(name)), fmt(c["lo"]) if c else "", fmt(c["hi"]) if c else ""]
        rows.append([fmt(x) for x in row])
    return rows


def contrasts(unit: str, b: dict) -> list[list[str]]:
    rows = []
    if unit == "debutanizer":
        for ctype, entries in b["intervals"]["contrasts"].items():
            for key, v in entries.items():
                cell, metric = key.rsplit("|", 1)
                c = v["all_rows"]
                rows.append([unit, ctype, cell, metric, fmt(c["mean"]), fmt(c["lo"]), fmt(c["hi"])])
        return rows
    for ctype, entries in b["summary"]["contrasts"].items():
        for cell, metrics in entries.items():
            for metric, c in metrics.items():
                rows.append([unit, ctype, cell, metric, fmt(c["mean"]), fmt(c["lo"]), fmt(c["hi"])])
    return rows


def baselines(unit: str, b: dict) -> list[list[str]]:
    rows = []
    if unit == "debutanizer":
        for theta, per in b["baselines"].items():
            for name in BASELINES:
                m = per[name]["debutanizer/0"]
                rows.append([unit, theta, name, *[fmt(m.get(x)) for x in METRICS]])
        return rows
    for theta, per in b["summary"].get("baselines", {}).items():
        for name in BASELINES:
            s = per[name]
            rows.append(
                [unit, theta, name, *[fmt(s[x]["mean"]) if x in s else "" for x in METRICS]]
            )
    return rows


def value(unit: str, b: dict, key: str, metric: str) -> float | None:
    if unit == "debutanizer":
        m = b["cells"].get(key, {}).get("debutanizer/0", {})
        return m.get(metric)
    s = b["summary"]["cells"].get(key, {})
    return s[metric]["mean"] if metric in s else None


def steps(unit: str, b: dict, key: str) -> str:
    """The step size, one per regime for TEP (modes 1/2/3), to three significant digits."""
    runs = b["cells"].get(key, {})
    if unit == "debutanizer":
        g = runs.get("debutanizer/0", {}).get("gamma")
        return "--" if g is None else f"{g:.3g}"
    seen: dict[str, float] = {}
    for stream, m in runs.items():
        seen.setdefault(b["regime_of"][stream], m.get("gamma"))
    if not seen or any(g is None for g in seen.values()):
        return "--"
    return "/".join(f"{seen[r]:.3g}" for r in sorted(seen))


def num(x: float | None, d: int, scale: float = 1.0) -> str:
    return "--" if x is None else f"{scale * x:.{d}f}"


def primary_table(unit: str, b: dict) -> str:
    lines = [
        r"\begin{tabular}{@{}rllrrrrrr@{}}",
        r"\toprule",
        r"$\theta$ & & Policy & Step & $U$ (\%) & Coverage & Median width & "
        r"Worst rolling & IACT \\",
        r"\midrule",
    ]
    thetas = sorted(int(t) for t in b["thetas"])
    for i, th in enumerate(thetas):
        if i:
            lines.append(r"\addlinespace")
        for comp, comp_name in COMPS:
            for j, (pol, pol_name) in enumerate(POLICIES):
                key = f"theta={th}|{comp}|{pol}|stored"
                if key not in b["cells"]:
                    continue
                first = j == 0
                cells = [
                    str(th) if first and comp == "raw" else "",
                    comp_name if first else "",
                    pol_name,
                    steps(unit, b, key) if pol != "none|-" else "--",
                    num(value(unit, b, key, "u"), 2, 100.0),
                    num(value(unit, b, key, "coverage"), 4),
                    num(value(unit, b, key, "width_median"), 3),
                    num(value(unit, b, key, "local_cov_min"), 3),
                    num(value(unit, b, key, "iact"), 2),
                ]
                lines.append(tex_row(cells))
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    return "\n".join(lines)


def loops_table(b: dict) -> str:
    lines = [
        r"\begin{tabular}{@{}llrrrrrr@{}}",
        r"\toprule",
        r"Loop & Policy & $U$ (\%) & Coverage & Median width & Worst rolling & IACT & "
        r"$U$ (\%), compensated \\",
        r"\midrule",
    ]
    for i, (loop, loop_name) in enumerate(LOOPS):
        if i:
            lines.append(r"\addlinespace")
        for j, (pol, pol_name) in enumerate(LOOP_POLICIES):
            raw = f"theta=4|raw|{loop}|{pol}|stored"
            comp = f"theta=4|comp|{loop}|{pol}|stored"
            if raw not in b["cells"]:
                continue
            cells = [
                loop_name if j == 0 else "",
                pol_name,
                num(value("T1", b, raw, "u"), 2, 100.0),
                num(value("T1", b, raw, "coverage"), 4),
                num(value("T1", b, raw, "width_median"), 3),
                num(value("T1", b, raw, "local_cov_min"), 3),
                num(value("T1", b, raw, "iact"), 2),
                num(value("T1", b, comp, "u"), 2, 100.0),
            ]
            lines.append(tex_row(cells))
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    return "\n".join(lines)


BASELINE_NAMES = (
    ("pid_qr", "conformal PID, quantile scorecaster"),
    ("pid_theta", "conformal PID, Theta scorecaster"),
    ("pid_matched", "conformal PID, matched scorecaster"),
    ("spci", "SPCI multi-step"),
)


def baselines_table(units: dict[str, dict]) -> str:
    """The baselines beside the compensated loop tuned by replay to eps / 2 (means over the runs
    for T1; the single stream for the debutanizer). Width: F7's median over all issued intervals."""
    lines = [
        r"\begin{tabular}{@{}lrlrrr@{}}",
        r"\toprule",
        r"Unit & $\theta$ & Method & $U$ (\%) & Coverage & F7 width \\",
        r"\midrule",
    ]
    first_unit = True
    for unit, b in units.items():
        thetas = sorted(int(t) for t in b["thetas"])
        for th in thetas:
            if not first_unit:
                lines.append(r"\addlinespace")
            first_unit = False
            key = f"theta={th}|comp|sequential|aware_half|stored"
            rows = [
                (
                    "compensated loop",
                    value(unit, b, key, "u"),
                    value(unit, b, key, "coverage"),
                    value(unit, b, key, "f7_median_width"),
                )
            ]
            for name, label in BASELINE_NAMES:
                if unit == "debutanizer":
                    m = b["baselines"][str(th)][name]["debutanizer/0"]
                    rows.append((label, m["u"], m["coverage"], m["f7_median_width"]))
                else:
                    m = b["summary"]["baselines"][str(th)][name]
                    rows.append(
                        (
                            label,
                            m["u"]["mean"],
                            m["coverage"]["mean"],
                            m["f7_median_width"]["mean"],
                        )
                    )
            for j, (label, u, cov, w) in enumerate(rows):
                cells = [
                    unit if j == 0 and th == thetas[0] else "",
                    str(th) if j == 0 else "",
                    label,
                    num(u, 2, 100.0),
                    num(cov, 4),
                    num(w, 3),
                ]
                lines.append(tex_row(cells))
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    return "\n".join(lines)


def render(in_dir: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    cell_rows: list[list[str]] = []
    contrast_rows: list[list[str]] = []
    baseline_rows: list[list[str]] = []
    paths: list[Path] = []
    with_baselines: dict[str, dict] = {}
    for unit in UNITS:
        b = load(f"phase1_stageB_{unit}", in_dir)
        if unit in ("T1", "debutanizer"):
            with_baselines[unit] = b
        cell_rows += debutanizer_cells(b) if unit == "debutanizer" else tep_cells(unit, b)
        contrast_rows += contrasts(unit, b)
        baseline_rows += baselines(unit, b)
        paths.append(write(f"n1_supp_primary_{unit}", primary_table(unit, b), out_dir))
        if unit == "T1":
            paths.append(write("n1_supp_loops", loops_table(b), out_dir))
    paths.append(write("n1_supp_baselines", baselines_table(with_baselines), out_dir))
    paths.append(save_csv(cell_rows, CELL_HEADER, "n1_supp_cells", out_dir))
    paths.append(
        save_csv(
            contrast_rows,
            ["unit", "contrast", "cell", "metric", "mean", "lo95", "hi95"],
            "n1_supp_contrasts",
            out_dir,
        )
    )
    paths.append(
        save_csv(
            baseline_rows, ["unit", "theta", "baseline", *METRICS], "n1_supp_baselines", out_dir
        )
    )
    return paths
