"""Tables 1 and 2 of Angelopoulos, Candes and Tibshirani (NeurIPS 2023), run with the authors' code.

Repository aangelopoulos/conformal-time-series at commit b729c3f. The base forecasts are the cached
ones in the repository, so darts is not needed. Sets are built as tests/base_test.py builds them
(signed or CQR-asymmetric score, alpha / 2 per side, minsize 0) and the table metrics are those of
tests/inset_plot.py, at the settings of tests/make_plots.sh:
- Table 1: ca-COVID-deaths-4wk, "Quantile" at lr 0 (the base forecaster) and
  "Quantile+Integrator (log)+Scorecaster" at lr 0.1, coverage_average_burnin 0;
- Table 2: elec2-intermittent, AR forecaster, "ACI" at lr 0.1 and the full method at lr 0.1,
  coverage_average_burnin 50.
The q sequences are written out for cpid_ipis.py.

Run from <conformal-time-series>/tests (see README.md):
    python -I cpid_authors.py OUT.json
"""

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(1, os.path.join(os.getcwd(), ".."))

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from core.methods import aci, quantile, quantile_integrator_log_scorecaster  # noqa: E402
from datasets import load_dataset  # noqa: E402
from plotting_utils import longest_true_sequence  # noqa: E402

FNS = {
    "ACI": aci,
    "Quantile": quantile,
    "Quantile+Integrator (log)+Scorecaster": quantile_integrator_log_scorecaster,
}


def table_metrics(lo, hi, y, burn_in, coverage_average_burnin):
    """tests/inset_plot.py, applied to sets already passed through the minsize step."""
    lo = lo[burn_in + 1 :][coverage_average_burnin:]
    hi = hi[burn_in + 1 :][coverage_average_burnin:]
    y = y[burn_in + 1 :][coverage_average_burnin:]
    sizes = hi - lo
    sizes_inf = np.nan_to_num(sizes, nan=np.inf)
    return {
        "Marginal coverage": float(((y >= lo) & (y <= hi)).mean()),
        "Longest err sequence": int(longest_true_sequence((y < lo) | (y > hi))),
        "Average set size": float(np.mean(sizes)) if not np.any(np.isinf(sizes)) else "Inf",
        "Median set size": float(np.median(sizes_inf)),
        "75% quantile set size": float(np.quantile(sizes_inf, 0.75)),
        "90% quantile set size": float(np.quantile(sizes_inf, 0.9)),
        "95% quantile set size": float(np.quantile(sizes_inf, 0.95)),
    }


def run(config_name, model_name, runs, coverage_average_burnin):
    with open(f"configs/{config_name}.yaml") as f:
        args = yaml.safe_load(f)
    data = load_dataset(args["sequences"][0]["dataset"])
    ahead = args.get("ahead", 1)
    if "forecasts" not in data.columns:
        data["forecasts"] = np.load(f"./datasets/proc/{config_name}/{model_name}.npz")["forecasts"]
    name = args["score_function_name"]
    if name == "signed-residual":
        data["scores"] = [
            np.array([f - y, y - f]) for y, f in zip(data["y"], data["forecasts"], strict=True)
        ]

        def set_function(forecast, q):
            return np.array([forecast - q[0], forecast + q[1]])

    elif name == "cqr-asymmetric":

        def set_function(forecast, q):
            return np.array([forecast[0] - q[0], forecast[-1] + q[1]])

    else:
        raise ValueError(name)
    out = {}
    for method, lr in runs:
        kwargs = dict(args["methods"][method])
        kwargs.pop("lrs", None)
        kwargs.update(
            T_burnin=args["T_burnin"],
            data=data,
            seasonal_period=args.get("seasonal_period"),
            config_name=f"{config_name}_{model_name}_{lr}",
            ahead=ahead,
        )
        stacked = np.stack(data["scores"].to_list())
        t0 = time.time()
        kwargs["upper"] = False
        q0 = FNS[method](stacked[:, 0], args["alpha"] / 2, lr, **kwargs)["q"]
        kwargs["upper"] = True
        q1 = FNS[method](stacked[:, 1], args["alpha"] / 2, lr, **kwargs)["q"]
        fc = data["forecasts"].interpolate().to_numpy()
        sets = [set_function(fc[i], np.array([q0[i], q1[i]])) for i in range(len(q0))]
        sets = np.stack([np.array([np.minimum(s[0], s[1]), np.maximum(s[1], s[0])]) for s in sets])
        y = data["y"].to_numpy().astype(float)
        entry = table_metrics(sets[:, 0], sets[:, 1], y, args["T_burnin"], coverage_average_burnin)
        entry.update(
            seconds=round(time.time() - t0, 1),
            q_lower=[float(v) for v in q0],
            q_upper=[float(v) for v in q1],
        )
        out[f"{method} lr={lr}"] = entry
    return out


if __name__ == "__main__":
    shutil.rmtree("./.cache/scorecaster", ignore_errors=True)  # scorecasts are refitted, not reused
    result = {
        "table1_ca_covid": run(
            "ca-COVID-deaths-4wk",
            "CDC Forecaster",
            [("Quantile", 0), ("Quantile+Integrator (log)+Scorecaster", 0.1)],
            coverage_average_burnin=0,
        ),
        "table2_elec2_intermittent_ar": run(
            "elec2-intermittent",
            "ar",
            [("ACI", 0.1), ("Quantile+Integrator (log)+Scorecaster", 0.1)],
            coverage_average_burnin=50,
        ),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with open(sys.argv[1], "w") as f:
        json.dump(result, f, indent=1)
    for key, val in result.items():
        if key == "script_sha256":
            continue
        for m, r in val.items():
            print(key, m, {k: v for k, v in r.items() if not k.startswith("q_")})
