"""The F-verdicts of N1 Phase 1 (pre-registration Sections 6 and 7) from the stage A and stage B
records.

Decided (Section 6):
- F2 on the two primary cells, the debutanizer at theta_doc = 3 and TEP T1 at theta = 4, on the
  N1' diagnosis: compensation off, the sequential loop, stored pairing, the delay-blind step size;
- F3 in each primary cell that meets F2's criterion, in the same cell;
- F5a, F5b, F6, F7 and F8 in TEP T1 at theta = 4;
- F1 (secondary) at the realistic delays, those Section 2 documents: the debutanizer at theta = 1,
  3, 7 and 12, T1 at 4 and T2 at 14 (T3's theta = 0 is documented too, but under deviation 1 T3
  is descriptive only), on the uncompensated sequential loop with stored pairing, at every policy
  whose step size lies in the design region.
Descriptive, and labelled so: the same quantities at every other cell, the debutanizer cells of
F5a, F5b, F6 and F7 (Section 6), the estimator-class check (T1 with gradient boosting), T2 and T3,
the analyzer-speed chart and the 2x2 of R4.9.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ipis.module1_soft_sensor.phase1 import data as dat
from ipis.module1_soft_sensor.phase1 import rules
from ipis.module1_soft_sensor.phase1.stages import (
    COMPS,
    EPS,
    POLICIES,
    cell_key,
    gamma_of,
)

DEB = "debutanizer"
DEB_KEY = "debutanizer/0"
F1_CELLS = {DEB: (1, 3, 7, 12), "T1": (4,), "T2": (14,)}


def flags(s: str) -> np.ndarray:
    """A string of 0 and 1 from the steps record, as floats."""
    return np.frombuffer(s.encode("ascii"), dtype=np.uint8).astype(np.float64) - 48.0


def _diag(theta: int) -> str:
    """The N1' diagnosis cell of F2 and F3."""
    return cell_key(theta, "raw", "sequential", "blind")


def _per_run(b: dict[str, Any], cell: str, metric: str) -> list[float]:
    return [float(b["cells"][cell][k][metric]) for k in b["streams"]]


def tep_rules(a: dict[str, Any], b: dict[str, Any], theta: int) -> dict[str, Any]:
    """F2, F3, F5a, F5b, F6 and F8 of one TEP unit at one theta, as Section 6 computes them."""
    keys = b["streams"]
    th = str(theta)
    out: dict[str, Any] = {"theta": theta, "runs": len(keys)}
    if theta > 0:
        out["F2"] = rules.f2_tep(_per_run(b, _diag(theta), "u"), _per_run(b, _diag(0), "u"))
    cell = b["cells"][_diag(theta)]
    out["F3"] = rules.f3(
        sum(int(cell[k]["covered_count"]) for k in keys), sum(int(cell[k]["n"]) for k in keys)
    )
    for name, comp in (("F5a", "raw"), ("F5b", "comp")):
        out[name] = rules.f5(
            _per_run(b, cell_key(theta, comp, "sequential", "aware_half"), "u"), EPS
        )
    out["F6"] = rules.f6(
        [float(b["measured_ratio"][th][k]) for k in keys],
        [float(a["predictions"][th]["per_stream"][k]) for k in keys],
    )
    ol = b["open_loop"][th]
    regimes = list(dict.fromkeys(b["regime_of"][k] for k in keys))
    gam = {
        comp: [gamma_of(a, g, theta, comp, "sequential", "aware_half") for g in regimes]
        for comp in COMPS
    }
    out["F8"] = rules.f8(
        [float(a["predictions"][th]["per_stream"][k]) for k in keys],
        [float(ol["comp"][k]["iact"]) for k in keys],
        [float(ol["raw"][k]["iact"]) for k in keys],
        gam["comp"],
        gam["raw"],
    ) | {
        "regimes": regimes,
        "beside": {
            m: rules.t_interval(
                [float(ol["comp"][k][m]) - float(ol["raw"][k][m]) for k in keys], 0.95
            )
            for m in ("acf1", "mean_miss_run", "miss_rate")
        },
    }
    return out


def deb_rules(
    a: dict[str, Any], b: dict[str, Any], steps: dict[str, Any], theta: int
) -> dict[str, Any]:
    """The same quantities on the single debutanizer stream: F2 by the paired block bootstrap
    (Section 7); the others for one run, with the block-bootstrap intervals of U."""
    th = str(theta)
    out: dict[str, Any] = {"theta": theta}
    if theta > 0:
        out["F2"] = rules.f2_debutanizer(
            flags(steps[_diag(theta)]["u"]), flags(steps[_diag(0)]["u"])
        )
    cell = b["cells"][_diag(theta)][DEB_KEY]
    out["F3"] = rules.f3(int(cell["covered_count"]), int(cell["n"]))
    for name, comp in (("F5a", "raw"), ("F5b", "comp")):
        k = cell_key(theta, comp, "sequential", "aware_half")
        out[name] = rules.f5([float(b["cells"][k][DEB_KEY]["u"])], EPS) | {
            "u_block_ci95": b["intervals"]["cells"][k]["all_rows"]["u"],
            "descriptive": True,
        }
    out["F6"] = rules.f6(
        [float(b["measured_ratio"][th][DEB_KEY])],
        [float(a["predictions"][th]["per_stream"][DEB_KEY])],
    ) | {"descriptive": True}
    ol = b["open_loop"][th]
    out["F8_measures"] = {comp: ol[comp][DEB_KEY] for comp in COMPS} | {
        "gamma_aware_half": {
            comp: gamma_of(a, DEB, theta, comp, "sequential", "aware_half") for comp in COMPS
        },
        "descriptive": True,
    }
    if "f7" in b and th in b["f7"]:
        out["F7"] = b["f7"][th] | {"descriptive": True}
    return out


def f1(stage_a: dict[str, Any], stage_b: dict[str, Any], comp: str) -> dict[str, Any]:
    """F1 at the realistic delays: the white model against the measured sd(alpha) and infinite
    share (means over the runs), at every policy inside the design region."""
    cells: dict[str, Any] = {}
    for unit, thetas in F1_CELLS.items():
        if unit not in stage_b:
            continue
        b = stage_b[unit]
        keys = b["streams"]
        for theta in thetas:
            for policy in POLICIES:
                k = cell_key(theta, comp, "sequential", policy)
                per = b["cells"][k]
                if any("not_run" in per[s] for s in keys):
                    continue
                gammas = {float(per[s]["gamma"]) for s in keys}
                for gamma in sorted(gammas):
                    runs = [s for s in keys if float(per[s]["gamma"]) == gamma]
                    sd = float(np.mean([per[s]["alpha_sd"] for s in runs]))
                    inf = float(np.mean([per[s]["infinite_share"] for s in runs]))
                    n = sum(int(per[s]["n"]) for s in runs)
                    label = f"{unit}|{k}|gamma={gamma}"
                    cells[label] = rules.f1_cell(gamma, theta, sd, inf, n) | {"runs": len(runs)}
    inside = {k: v for k, v in cells.items() if v["in_region"]}
    return {
        "units": [u for u in F1_CELLS if u in stage_b],
        "units_missing": [u for u in F1_CELLS if u not in stage_b],
        "cells": cells,
        "cells_in_region": len(inside),
        "cells_off_by_25pct": sorted(k for k, v in inside.items() if v["off_by_25pct"]),
        "fires": any(v["off_by_25pct"] for v in inside.values()),
    }


def analyzer_speed_chart(stage_a: dict[str, Any], stage_b: dict[str, Any]) -> dict[str, Any]:
    """Section 5.4: predicted (stage A) and measured (stage B) width ratio at every theta."""
    out: dict[str, Any] = {}
    for unit, b in stage_b.items():
        a = stage_a[unit]
        row = {}
        for th in map(str, b["thetas"]):
            pred = a["predictions"][th]["per_stream"]
            meas = b["measured_ratio"][th]
            row[th] = {
                "predicted_mean": float(np.mean(list(pred.values()))),
                "measured_mean": float(np.mean([meas[k] for k in pred])),
                "per_stream": {k: {"predicted": pred[k], "measured": meas[k]} for k in pred},
            }
        out[unit] = row
    return out


def two_by_two(b: dict[str, Any], theta: int) -> dict[str, Any]:
    """R4.9's 2x2 at one cell: compensation off or on, loop off (static split conformal) or on
    (sequential, stored, tuned to eps / 2): the run means of U, coverage, median width and worst
    local coverage."""
    out = {}
    for comp in COMPS:
        for loop, policy in (("none", "-"), ("sequential", "aware_half")):
            per = b["cells"][cell_key(theta, comp, loop, policy)]
            out[f"{comp}|{loop}"] = {
                m: float(np.mean([per[k][m] for k in b["streams"]]))
                for m in ("u", "coverage", "width_median", "local_cov_min")
            }
    return out


def verdicts(
    stage_a: dict[str, dict[str, Any]],
    stage_b: dict[str, dict[str, Any]],
    deb_steps: dict[str, Any],
) -> dict[str, Any]:
    """The decided rules and the descriptive cells, from the records of every unit."""
    for need in (DEB, "T1"):
        if need not in stage_b:
            raise ValueError(f"the verdicts need the {need} records")
    t1 = tep_rules(stage_a["T1"], stage_b["T1"], 4)
    deb3 = deb_rules(stage_a[DEB], stage_b[DEB], deb_steps, dat.DEBUT_PRIMARY)
    shows = {
        "debutanizer_theta3": bool(deb3["F2"]["shows_increase"]),
        "tep_T1_theta4": bool(t1["F2"]["shows_increase"]),
    }
    f3_cells = {
        "debutanizer_theta3": deb3["F3"] | {"f2_met": shows["debutanizer_theta3"]},
        "tep_T1_theta4": t1["F3"] | {"f2_met": shows["tep_T1_theta4"]},
    }
    f7 = stage_b["T1"]["f7"]["4"]
    pid_flags = {
        f"pid_{name}": {
            plant: stage_a["T1"]["pid"]["tuning"][plant]["4"][name]["flag"]
            for plant in stage_a["T1"]["pid"]["tuning"]
        }
        for name in ("qr", "theta", "matched")
    }
    decided = {
        "F2": {
            "debutanizer_theta3": deb3["F2"],
            "tep_T1_theta4": t1["F2"],
            **rules.f2_verdict(shows),
        },
        "F3": {
            "cells": f3_cells,
            "tested_in": [c for c, v in f3_cells.items() if v["f2_met"]],
            "fires": any(v["f2_met"] and v["nominal_outside"] for v in f3_cells.values()),
        },
        "F5a": t1["F5a"],
        "F5b": t1["F5b"],
        "F6": t1["F6"],
        "F7": {name: f7[name] for name in ("pid_qr", "pid_theta", "pid_matched", "spci")}
        | f7["verdict_if_decided_here"]
        | {"pid_tuning_flags": pid_flags},
        "F8": t1["F8"],
        "F1": f1(stage_a, stage_b, "raw"),
    }
    descriptive: dict[str, Any] = {
        "debutanizer": {
            str(th): deb_rules(stage_a[DEB], stage_b[DEB], deb_steps, th)
            for th in stage_b[DEB]["thetas"]
        },
        "T1": {str(th): tep_rules(stage_a["T1"], stage_b["T1"], th) for th in (0, 2)},
        "F1_compensated": f1(stage_a, stage_b, "comp"),
        "analyzer_speed_chart": analyzer_speed_chart(stage_a, stage_b),
        "r4_9_2x2": {
            "debutanizer_theta3": two_by_two(stage_b[DEB], 3),
            "tep_T1_theta4": two_by_two(stage_b["T1"], 4),
        },
    }
    for unit in ("T1_gb", "T2", "T3"):
        if unit in stage_b:
            descriptive[unit] = {
                str(th): tep_rules(stage_a[unit], stage_b[unit], th)
                for th in stage_b[unit]["thetas"]
            }
    summary = {
        "F2_fires": decided["F2"]["fires"],
        "F2_restricted_to": decided["F2"]["restricted_to"],
        "F3_fires": decided["F3"]["fires"],
        "F5a_fires": decided["F5a"]["fires"],
        "F5b_fires": decided["F5b"]["fires"],
        "F6_fires": decided["F6"]["fires"],
        "F7_fires": decided["F7"]["fires"],
        "F7_recommended": decided["F7"]["recommended"],
        "F8_tested": decided["F8"]["tested"],
        "F8_fires": decided["F8"]["fires"],
        "step_statement_made": decided["F8"]["step_statement_made"],
        "F1_fires": decided["F1"]["fires"],
    }
    return {
        "units": sorted(stage_b),
        "summary": summary,
        "decided": decided,
        "descriptive": descriptive,
    }
