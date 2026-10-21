"""IPIS QuantileForest against sklearn-quantile 0.0.29 RandomForestQuantileRegressor.

With the settings SPCI uses (10 trees, depth 2, criterion "mse", the ten levels of its beta grid)
and the same global random state, both must give the same trees and bit-identical quantiles.
40 random cases, n from 40 to 1500 and w from 1 to 60; every fourth case rounds the targets to
two decimals, which creates ties in the sort.

    python -I qrf_ipis.py IPIS_SRC OUT.json
"""

import hashlib
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, sys.argv[1])
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
from sklearn_quantile import RandomForestQuantileRegressor  # noqa: E402

from ipis.module1_soft_sensor.evaluation import baselines as b  # noqa: E402


def main() -> None:
    _, levels = b.spci_quantile_levels(0.1)
    cases = []
    for case in range(40):
        rng = np.random.default_rng(case)
        n = int(rng.integers(40, 1500))
        w = int(rng.integers(1, 60))
        X = rng.standard_normal((n, w))
        y = np.round(X[:, 0] * 0.7 + rng.standard_normal(n), 2 if case % 4 == 0 else 12)
        Xq = rng.standard_normal((3, w))
        np.random.seed(case)
        ref = RandomForestQuantileRegressor(
            n_estimators=10, max_depth=2, criterion="mse", n_jobs=-1, q=levels
        ).fit(X, y)
        theirs = ref.predict(Xq)
        np.random.seed(case)
        mine = b.QuantileForest(random_state=None).fit(X, y).predict(Xq, levels)
        cases.append(
            {
                "case": case,
                "n": n,
                "w": w,
                "identical": bool(np.array_equal(theirs, mine)),
                "max_abs_diff": float(np.max(np.abs(theirs.astype(float) - mine.astype(float)))),
            }
        )
    summary = {
        "cases": len(cases),
        "identical": sum(c["identical"] for c in cases),
        "max_abs_diff": max(c["max_abs_diff"] for c in cases),
        "detail": cases,
        "sources_sha256": b.source_sha256(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    with open(sys.argv[2], "w") as f:
        json.dump(summary, f, indent=1)
    print({k: v for k, v in summary.items() if k != "detail"})


if __name__ == "__main__":
    main()
