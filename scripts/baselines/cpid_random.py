"""Randomised check of ``conformal_pid_side(mode="code")`` against the authors'
``quantile_integrator_log_scorecaster`` (aangelopoulos/conformal-time-series, commit b729c3f).

Tables 1 and 2 exercise only two non-trivial q sequences each and never saturate the integrator.
This check draws 600 side-runs over the settings those tables leave out:
- ahead 1 to 7, with precomputed scorecasts or none;
- proportional learning rate on and off, lr including 0, K_I including 0;
- C_sat from 0.01 to 2, so that the integrator saturates to +-inf in part of the runs.
It adds 12 runs of the in-loop Theta scorecaster at ahead 1 (period 1 and 4), and confirms that
the authors' Theta path stops at ahead 2 and 3. Every q sequence must agree exactly.

Run from <conformal-time-series> (see README.md):
    python -I cpid_random.py IPIS_SRC OUT.json
"""

import hashlib
import json
import os
import shutil
import sys
import warnings
from pathlib import Path

sys.path.insert(0, os.getcwd())
sys.path.insert(1, sys.argv[1])
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from core.methods import quantile_integrator_log_scorecaster as authors  # noqa: E402

from ipis.module1_soft_sensor.evaluation import baselines as b  # noqa: E402

CACHE = "./.cache/scorecaster"


def main() -> None:
    rng = np.random.default_rng(20261020)
    runs, mismatches, with_inf = 0, 0, 0
    for _ in range(600):
        T = int(rng.integers(30, 400))
        ahead = int(rng.integers(1, 8))
        burn = int(rng.integers(1, 60))  # the authors' code needs T_burnin >= 1
        alpha = float(rng.choice([0.05, 0.1]))
        lr = float(rng.choice([0.0, 0.01, 0.1, 0.5, 1.0]))
        k_i = float(rng.choice([0.0, 1.0, 10.0, 200.0]))
        c_sat = float(rng.choice([0.01, 0.1, 0.55, 2.0]))
        prop = bool(rng.integers(0, 2))
        use_sc = bool(rng.integers(0, 2))
        scores = rng.standard_normal(T).cumsum() * 0.1 + rng.standard_normal(T)
        sc = rng.standard_normal(T) * 0.3
        data = pd.DataFrame({"scorecasts": [np.array([v, v]) for v in sc]})
        theirs = authors(
            scores,
            alpha,
            lr,
            data,
            burn,
            c_sat,
            k_i,
            True,
            ahead,
            proportional_lr=prop,
            scorecast=use_sc,
        )["q"]
        mine = b.conformal_pid_side(
            scores,
            alpha,
            lr,
            ahead,
            window=burn,
            k_i=k_i,
            c_sat=c_sat,
            scorecasts=sc if use_sc else None,
            mode="code",
            proportional_lr=prop,
        )["q"]
        runs += 1
        mismatches += not np.array_equal(theirs, mine, equal_nan=True)
        with_inf += bool(np.isinf(theirs).any())
    theta_runs, theta_mismatches = 0, 0
    for period in (1, 4):
        for k in range(6):
            T, burn = int(rng.integers(60, 140)), int(rng.integers(20, 40))
            scores = rng.standard_normal(T).cumsum() * 0.1 + rng.standard_normal(T)
            shutil.rmtree(CACHE, ignore_errors=True)
            theirs = authors(
                scores,
                0.05,
                0.1,
                pd.DataFrame({"y": scores}),
                burn,
                1.0,
                10.0,
                True,
                1,
                seasonal_period=period,
                config_name=f"random_{period}_{k}",
            )["q"]
            table = b.theta_forecast_table(scores, burn, 1, period)
            mine = b.conformal_pid_side(
                scores,
                0.05,
                0.1,
                1,
                window=burn,
                k_i=10.0,
                c_sat=1.0,
                scorecasts=b.pid_scorecasts(table, 1, burn, "code"),
                mode="code",
            )["q"]
            theta_runs += 1
            theta_mismatches += not np.array_equal(theirs, mine)
    stops = {}
    for ahead in (2, 3):
        shutil.rmtree(CACHE, ignore_errors=True)
        scores = rng.standard_normal(80)
        try:
            authors(
                scores,
                0.05,
                0.1,
                pd.DataFrame({"y": scores}),
                20,
                1.0,
                10.0,
                True,
                ahead,
                config_name=f"random_ahead_{ahead}",
            )
            stops[str(ahead)] = "ran"
        except ValueError as err:
            stops[str(ahead)] = f"ValueError: {err}"
    shutil.rmtree(CACHE, ignore_errors=True)
    out = {
        "precomputed_or_none": {
            "runs": runs,
            "mismatches": mismatches,
            "runs_with_inf_q": with_inf,
        },
        "theta_ahead_1": {"runs": theta_runs, "mismatches": theta_mismatches},
        "theta_ahead_2_3": stops,
        "sources_sha256": b.source_sha256(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with open(sys.argv[2], "w") as f:
        json.dump(out, f, indent=1)
    print(out)


if __name__ == "__main__":
    main()
