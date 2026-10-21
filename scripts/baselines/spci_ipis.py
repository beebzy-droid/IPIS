"""SPCI: the authors' pipeline on the electric data set, and IPIS against it.

hamrel-cxu/SPCI-code at commit d598dd3, as in its tutorial notebook: 80 % training data; an EnbPI
ensemble of 25 random forests (10 trees, depth 1, no bootstrap within a forest, random_state 1103)
gives leave-one-out training residuals and the test residuals; SPCI builds 90 % intervals with
past window w = 300. Torch is replaced by the numpy container shim in torch_shim/.

Two steps, each written to its own file so that an interrupted check resumes where it stopped:
- ``authors TRIAL STRIDE OUT.npz``: the ensemble (numpy seeded with TRIAL) and the authors' SPCI
  stage (compute_PIs_Ensemble_online, use_SPCI=True, numpy seeded with 1000 + 10 TRIAL + STRIDE);
  saves the residuals, the ensemble's centres and the interval bounds.
- ``ipis IN.npz OUT.json [rolling]``: ``baselines.spci_block`` from the same residuals and the same
  seed must give identical bounds (the centre plus each offset, as the authors add them); with
  ``rolling`` (stride 1 only), ``baselines.spci_rolling`` must too.

Run from <SPCI-code> (see README.md):
    python -I spci_ipis.py IPIS_SRC authors 0 1 t0_s1.npz
    python -I spci_ipis.py IPIS_SRC ipis t0_s1.npz t0_s1.json rolling
"""

import hashlib
import json
import os
import sys
import time
import warnings
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "torch_shim"))
sys.path.insert(1, os.getcwd())
sys.path.insert(2, sys.argv[1])
warnings.filterwarnings("ignore")
os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np  # noqa: E402

from ipis.module1_soft_sensor.evaluation import baselines as b  # noqa: E402

ALPHA, PAST_WINDOW, TRAIN_FRAC, B = 0.1, 300, 0.8, 25


def seed_of(trial: int, stride: int) -> int:
    return 1000 + 10 * trial + stride


def own_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def authors(trial: int, stride: int, out_path: str) -> None:
    import data
    import SPCI_class
    import torch  # the shim
    from sklearn.ensemble import RandomForestRegressor

    X_full, Y_full = data.real_data_loader().electric_dataset()
    X_full, Y_full = torch.from_numpy(X_full), torch.from_numpy(Y_full)
    N = int(X_full.shape[0] * TRAIN_FRAC)
    X_train, X_predict, Y_train, Y_predict = X_full[:N], X_full[N:], Y_full[:N], Y_full[N:]
    y_test = np.asarray(Y_predict)
    np.random.seed(trial)
    fit_func = RandomForestRegressor(
        n_estimators=10,
        max_depth=1,
        criterion="mse",
        bootstrap=False,
        n_jobs=-1,
        random_state=1103,
    )
    model = SPCI_class.SPCI_and_EnbPI(X_train, X_predict, Y_train, Y_predict, fit_func=fit_func)
    model.fit_bootstrap_models_online_multistep(B=B, fit_sigmaX=False, stride=1)
    resid = model.Ensemble_online_resid.copy()
    centers = model.Ensemble_pred_interval_centers.copy()
    np.random.seed(seed_of(trial, stride))
    t0 = time.time()
    model.compute_PIs_Ensemble_online(
        ALPHA,
        smallT=False,
        past_window=PAST_WINDOW,
        use_SPCI=True,
        quantile_regr=True,
        stride=stride,
    )
    seconds = time.time() - t0
    pis = model.PIs_Ensemble
    np.savez(
        out_path,
        trial=trial,
        stride=stride,
        n_train=N,
        resid=resid,
        centers=centers,
        lower=np.asarray(pis["lower"]),
        upper=np.asarray(pis["upper"]),
        y_test=y_test,
        seconds=seconds,
        script_sha256=own_sha256(),
    )


def ipis(in_path: str, out_path: str, rolling: bool) -> None:
    d = np.load(in_path)
    trial, stride, N = int(d["trial"]), int(d["stride"]), int(d["n_train"])
    lower, upper, y_test, centers = d["lower"], d["upper"], d["y_test"], d["centers"]
    run = {
        "trial": trial,
        "stride": stride,
        "n_train": N,
        "n_test": int(y_test.size),
        "seconds_authors": round(float(d["seconds"]), 1),
        "coverage": float(((lower <= y_test) & (upper >= y_test)).mean()),
        "width": float((upper - lower).mean()),
    }
    np.random.seed(seed_of(trial, stride))
    t0 = time.time()
    mine = b.spci_block(d["resid"], N, ALPHA, stride, w=PAST_WINDOW, random_state=None)
    run["seconds_ipis"] = round(time.time() - t0, 1)
    lo_m, hi_m = centers + mine["lo"], centers + mine["hi"]
    run["block_identical"] = bool(np.array_equal(lo_m, lower) and np.array_equal(hi_m, upper))
    run["block_max_abs_diff"] = float(
        max(np.max(np.abs(lo_m - lower)), np.max(np.abs(hi_m - upper)))
    )
    if rolling:
        if stride != 1:
            raise ValueError("the rolling check is defined at stride 1")
        np.random.seed(seed_of(trial, stride))
        roll = b.spci_rolling(
            d["resid"], N, ALPHA, 1, w=PAST_WINDOW, train_len=N, random_state=None
        )
        run["rolling_identical"] = bool(
            np.array_equal(centers + roll["lo"][N:], lower)
            and np.array_equal(centers + roll["hi"][N:], upper)
        )
    run["sources_sha256"] = b.source_sha256()
    run["script_sha256"] = own_sha256()
    run["authors_step_script_sha256"] = (
        str(d["script_sha256"]) if "script_sha256" in d.files else None
    )
    with open(out_path, "w") as f:
        json.dump(run, f, indent=1)
    print(run, flush=True)


if __name__ == "__main__":
    if sys.argv[2] == "authors":
        authors(int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif sys.argv[2] == "ipis":
        ipis(sys.argv[3], sys.argv[4], len(sys.argv) > 5 and sys.argv[5] == "rolling")
    else:
        raise SystemExit("usage: spci_ipis.py IPIS_SRC authors|ipis ...")
