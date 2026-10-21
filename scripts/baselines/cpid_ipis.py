"""IPIS conformal PID against the authors' code, on Tables 1 and 2 of the paper.

Reads the q sequences written by cpid_authors.py and recomputes them with
``ipis.module1_soft_sensor.evaluation.baselines``:
- mode "code" must reproduce them exactly: Table 1 (California COVID deaths, horizon 4, the
  repository's precomputed scorecasts), both the base forecaster (lr 0) and conformal PID
  (lr 0.1, K_I 1000, C_sat 2); Table 2 (elec2, AR forecaster, horizon 1, Theta scorecaster with
  period 48 refitted every step, lr 0.1, K_I 10, C_sat 5);
- mode "phase1" on Table 2 shows the effect of the Appendix A changes at horizon 1, where only the
  scorecaster's alignment differs.

Run from <conformal-time-series>/tests (see README.md):
    python -I cpid_ipis.py AUTHORS.json IPIS_SRC OUT.json
"""

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.join(os.getcwd(), ".."))
sys.path.insert(2, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(3, sys.argv[2])

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from cpid_authors import table_metrics  # noqa: E402
from datasets import load_dataset  # noqa: E402

from ipis.module1_soft_sensor.evaluation import baselines as b  # noqa: E402


def compare(mine, theirs):
    a, t = np.asarray(mine, dtype=float), np.asarray(theirs, dtype=float)
    finite = np.isfinite(a) & np.isfinite(t)
    return {
        "identical": bool(np.array_equal(a, t, equal_nan=True)),
        "max_abs_diff_finite": (
            float(np.max(np.abs(a[finite] - t[finite]))) if finite.any() else 0.0
        ),
        "n": int(a.size),
    }


def reflected(lo, hi):
    """The minsize = 0 step of tests/base_test.py: an inverted set is reflected, not emptied."""
    return np.minimum(lo, hi), np.maximum(hi, lo)


def main() -> None:
    with open(sys.argv[1]) as f:
        authors = json.load(f)
    out = {}

    with open("configs/ca-COVID-deaths-4wk.yaml") as f:
        args = yaml.safe_load(f)
    data = load_dataset("ca-COVID-deaths-4wk")
    scores = np.stack(data["scores"].to_list())
    scorecasts = np.stack([np.asarray(s) for s in data["scorecasts"]])
    fc = np.stack([np.asarray(v) for v in data["forecasts"]])
    y = data["y"].to_numpy().astype(float)
    m = args["methods"]["Quantile+Integrator (log)+Scorecaster"]
    res = {}
    for lr, key, use_sc, k_i, c_sat in (
        (0, "Quantile lr=0", False, 0, 1.0),
        (0.1, "Quantile+Integrator (log)+Scorecaster lr=0.1", True, m["KI"], m["Csat"]),
    ):
        qs = [
            b.conformal_pid_side(
                scores[:, side],
                args["alpha"] / 2,
                lr,
                args["ahead"],
                window=args["T_burnin"],
                k_i=k_i,
                c_sat=c_sat,
                scorecasts=scorecasts[:, side] if use_sc else None,
                mode="code",
            )["q"]
            for side in (0, 1)
        ]
        lo, hi = reflected(fc[:, 0] - qs[0], fc[:, -1] + qs[1])
        res[key] = {
            "q_lower": compare(qs[0], authors["table1_ca_covid"][key]["q_lower"]),
            "q_upper": compare(qs[1], authors["table1_ca_covid"][key]["q_upper"]),
            "table": table_metrics(lo, hi, y, args["T_burnin"], 0),
        }
    out["table1_ca_covid"] = res

    with open("configs/elec2-intermittent.yaml") as f:
        args = yaml.safe_load(f)
    data = load_dataset("elec2")
    f_ar = np.load("./datasets/proc/elec2-intermittent/ar.npz")["forecasts"]
    y = data["y"].to_numpy().astype(float)
    scores = np.stack([f_ar - y, y - f_ar], axis=1)
    m = args["methods"]["Quantile+Integrator (log)+Scorecaster"]
    burn, period = args["T_burnin"], args["seasonal_period"]
    tables = [b.theta_forecast_table(scores[:, k], burn, 1, period) for k in (0, 1)]
    key = "Quantile+Integrator (log)+Scorecaster lr=0.1"
    res = {}
    for mode in b.MODES:
        qs = [
            b.conformal_pid_side(
                scores[:, k],
                args["alpha"] / 2,
                0.1,
                1,
                window=burn,
                k_i=m["KI"],
                c_sat=m["Csat"],
                scorecasts=b.pid_scorecasts(tables[k], 1, burn, mode),
                mode=mode,
            )["q"]
            for k in (0, 1)
        ]
        lo, hi = reflected(f_ar - qs[0], f_ar + qs[1])
        entry = {"table": table_metrics(lo, hi, y, burn, 50)}
        if mode == "code":
            auth = authors["table2_elec2_intermittent_ar"][key]
            entry["q_lower"] = compare(qs[0], auth["q_lower"])
            entry["q_upper"] = compare(qs[1], auth["q_upper"])
        res[mode] = entry
    out["table2_elec2_intermittent_ar"] = res
    out["sources_sha256"] = b.source_sha256()
    out["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    with open(sys.argv[3], "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
