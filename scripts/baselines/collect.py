"""Merge the baseline reproduction checks into one evidence record (pre-registration Appendix A).

Compares the reproduced tables with the values printed in the papers (transcribed below), adds
the versions, the authors' commits and the SHA-256 of the IPIS modules (the facade, the PID and
the SPCI module) and of these scripts. Each result file carries the SHA-256 of the script that
wrote it and, on the IPIS side, of the modules it ran with (``baselines.source_sha256``);
``results_from_these_modules`` and ``results_from_these_scripts`` say, per result, whether that
is the code hashed here, and ``all_results_from_this_code`` must be true.

    python -I collect.py --cpid-authors A.json --cpid-ipis B.json --cpid-random R.json --qrf C.json \
        --spci RUN.json [RUN.json ...] --cpid-repo DIR --spci-repo DIR --ipis-src DIR --out OUT.json
"""

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
METRICS = (
    "Marginal coverage",
    "Longest err sequence",
    "Average set size",
    "Median set size",
    "75% quantile set size",
    "90% quantile set size",
    "95% quantile set size",
)
# Printed with "{:.3g}" (tests/inset_plot.py); "Inf" for infinite values.
PAPER_CPID = {
    "table1_ca_covid": {
        "Quantile lr=0": ["0.82", "6", "625", "512", "754", "1.12e+03", "1.45e+03"],
        "Quantile+Integrator (log)+Scorecaster lr=0.1": [
            "0.86",
            "2",
            "858",
            "688",
            "1.01e+03",
            "1.47e+03",
            "1.8e+03",
        ],
    },
    "table2_elec2_intermittent_ar": {
        "ACI lr=0.1": ["0.899", "3", "Inf", "0.406", "0.484", "0.672", "Inf"],
        "Quantile+Integrator (log)+Scorecaster lr=0.1": [
            "0.9",
            "2",
            "0.177",
            "0.178",
            "0.21",
            "0.236",
            "0.252",
        ],
    },
}
# Xu and Xie (2023), Table 3, electric data set, SPCI: mean (sd) over three trials.
PAPER_SPCI = {"coverage": 0.93, "coverage_sd": 4.79e-3, "width": 0.22, "width_sd": 1.68e-3}


def fmt(v):
    if v == "Inf" or (isinstance(v, float) and (np.isinf(v) or v >= 1e300)):
        return "Inf"
    return f"{v:.3g}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commit(repo: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in (
        "--cpid-authors",
        "--cpid-ipis",
        "--cpid-random",
        "--qrf",
        "--cpid-repo",
        "--spci-repo",
    ):
        ap.add_argument(name, required=True)
    ap.add_argument("--spci", nargs="+", required=True)
    ap.add_argument("--ipis-src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    authors, ipis, qrf = load(args.cpid_authors), load(args.cpid_ipis), load(args.qrf)
    randomised = load(args.cpid_random)
    tables = {}
    for table, methods in PAPER_CPID.items():
        rows = {}
        for method, printed in methods.items():
            got = [fmt(authors[table][method][m]) for m in METRICS]
            rows[method] = {
                "paper": printed,
                "authors_code": got,
                "matches_paper": got == printed,
            }
        tables[table] = rows
    ipis_cpid = {
        "table1_ca_covid": {
            k: {
                "q_lower_identical": v["q_lower"]["identical"],
                "q_upper_identical": v["q_upper"]["identical"],
            }
            for k, v in ipis["table1_ca_covid"].items()
        },
        "table2_code_mode": {
            "q_lower_identical": ipis["table2_elec2_intermittent_ar"]["code"]["q_lower"][
                "identical"
            ],
            "q_upper_identical": ipis["table2_elec2_intermittent_ar"]["code"]["q_upper"][
                "identical"
            ],
        },
        "table2_phase1_mode": ipis["table2_elec2_intermittent_ar"]["phase1"]["table"],
        "table2_code_mode_table": ipis["table2_elec2_intermittent_ar"]["code"]["table"],
    }
    spci_runs = [load(p) for p in args.spci]
    one_step = [r for r in spci_runs if r["stride"] == 1]
    cov = np.array([r["coverage"] for r in one_step])
    wid = np.array([r["width"] for r in one_step])
    spci = {
        "runs": spci_runs,
        "one_step_mean": {
            "coverage": float(cov.mean()),
            "coverage_sd": float(cov.std(ddof=1)) if cov.size > 1 else None,
            "width": float(wid.mean()),
            "width_sd": float(wid.std(ddof=1)) if wid.size > 1 else None,
            "trials": int(cov.size),
        },
        "paper_table3_electric": PAPER_SPCI,
        "matches_paper_two_decimals": bool(
            round(float(cov.mean()), 2) == PAPER_SPCI["coverage"]
            and round(float(wid.mean()), 2) == PAPER_SPCI["width"]
        ),
        "all_block_identical": all(r["block_identical"] for r in spci_runs),
        "rolling_identical": [
            r["rolling_identical"] for r in spci_runs if "rolling_identical" in r
        ],
    }
    evaluation = Path(args.ipis_src) / "ipis" / "module1_soft_sensor" / "evaluation"
    prefix = "src/ipis/module1_soft_sensor/evaluation/"
    current = {
        prefix + m: sha256(evaluation / m)
        for m in ("baselines.py", "baselines_pid.py", "baselines_spci.py")
    }
    # Every IPIS-side result must come from the modules hashed here: the facade and the module
    # whose code it runs (a change to the PID module leaves the SPCI results valid, and back).
    pid = (prefix + "baselines.py", prefix + "baselines_pid.py")
    spci_mods = (prefix + "baselines.py", prefix + "baselines_spci.py")
    produced_by = {
        "cpid_ipis": (ipis.get("sources_sha256"), pid),
        "cpid_random": (randomised.get("sources_sha256"), pid),
        "qrf_ipis": (qrf.get("sources_sha256"), spci_mods),
        **{
            f"spci_t{r['trial']}_s{r['stride']}": (r.get("sources_sha256"), spci_mods)
            for r in spci_runs
        },
    }
    sources_current = {
        k: bool(rec) and all(rec.get(m) == current[m] for m in mods)
        for k, (rec, mods) in produced_by.items()
    }
    # ... and from the scripts hashed here (the SPCI runs: both steps)
    script = {p.name: sha256(p) for p in HERE.glob("*.py")}
    scripts_current = {
        "cpid_authors": authors.get("script_sha256") == script["cpid_authors.py"],
        "cpid_ipis": ipis.get("script_sha256") == script["cpid_ipis.py"],
        "cpid_random": randomised.get("script_sha256") == script["cpid_random.py"],
        "qrf_ipis": qrf.get("script_sha256") == script["qrf_ipis.py"],
        **{
            f"spci_t{r['trial']}_s{r['stride']}": r.get("script_sha256")
            == r.get("authors_step_script_sha256")
            == script["spci_ipis.py"]
            for r in spci_runs
        },
    }
    packages = {}
    for name in ("numpy", "scipy", "pandas", "scikit-learn", "sklearn-quantile", "statsmodels"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    doc = {
        "_meta": {
            "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "python": platform.python_version(),
            "packages": packages,
            "sources": {
                "aangelopoulos/conformal-time-series": commit(args.cpid_repo),
                "hamrel-cxu/SPCI-code": commit(args.spci_repo),
            },
            "results_from_these_modules": sources_current,
            "results_from_these_scripts": scripts_current,
            "all_results_from_this_code": all(sources_current.values())
            and all(scripts_current.values()),
            "sha256": {
                **current,
                **{
                    f"scripts/baselines/{p.relative_to(HERE).as_posix()}": sha256(p)
                    for p in sorted(HERE.rglob("*.py"))
                },
            },
        },
        "conformal_pid": {
            "paper_tables_by_authors_code": tables,
            "ipis": ipis_cpid,
            "randomised_code_mode": randomised,
        },
        "quantile_forest_vs_sklearn_quantile": {k: v for k, v in qrf.items() if k != "detail"},
        "spci": spci,
    }
    with open(args.out, "w") as f:
        json.dump(doc, f, indent=1)
    print(json.dumps({k: v for k, v in doc.items() if k != "spci"}, indent=1)[:4000])
    print("SPCI:", {k: v for k, v in spci.items() if k != "runs"})


if __name__ == "__main__":
    main()
