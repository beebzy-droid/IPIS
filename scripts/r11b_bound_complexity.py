"""R1.1, second half: how does the CONSERVATISM OF THE A-PRIORI BOUND change with base-model
complexity?

`r11_base_model.py` answers the first half, how coverage behaves as the predictor gets more
flexible. Reviewer 1 also asks specifically about the bound: if a strongly non-linear learner
complicates the score distribution, the certificate fitted from source-side data could become
looser, or could stop holding. This script fits the certificate separately for each base model,
using the same machinery as `r15b_certificate.py` so the numbers are comparable to Section 5.3.

For each predictor class, over all (ordered pair, eta) configurations:
  delta  physical departure, as in r15b_certificate.departure
  gap    SCC coverage gap with that predictor, unit-level calibration
  dTV    total-variation distance between the dimensionless score laws of source and target

then a + L*delta is fit on 60% of configurations and the bound 2(a + L*delta) is checked on the
held-out 40%, exactly as in Section 5.3.

Run:  PYTHONPATH=src python3 scripts/r11b_bound_complexity.py
"""

from __future__ import annotations

import itertools
import json
import warnings

import numpy as np
from r11_base_model import ALPHA, ETAS, SEEDS, TARGET, TEMPS, scores_for_pair, snapshots
from r15b_certificate import certificate, departure

from ipis.module2_pdm.scc.conformal import one_sided_quantile, tv_distance

warnings.filterwarnings("ignore")

MODELS = ["physics", "linear", "forest", "mlp"]


def rows_for(model: str) -> np.ndarray:
    """(delta, scc_gap, dTV, naive_gap) per (eta, ordered pair), averaged over seeds."""
    rows = []
    for eta in ETAS:
        per_pair: dict[tuple, list[list[float]]] = {}
        for s in range(SEEDS):
            rng = np.random.default_rng(s * 977 + 11)
            data = {t: snapshots(t, eta, s * 17 + i, rng) for i, t in enumerate(TEMPS)}
            for src, tgt in itertools.permutations(TEMPS, 2):
                v_sr, v_tr, v_sd, v_td = scores_for_pair(model, src, tgt, data)
                qn = one_sided_quantile(v_sr, ALPHA)
                qs = one_sided_quantile(v_sd, ALPHA)
                per_pair.setdefault((src, tgt), []).append(
                    [
                        max(0.0, TARGET - float(np.mean(v_tr <= qn))),
                        max(0.0, TARGET - float(np.mean(v_td <= qs))),
                        tv_distance(v_sd, v_td),
                    ]
                )
        for (src, tgt), v in per_pair.items():
            m = np.mean(v, axis=0)
            rows.append([departure(src, tgt, eta), m[1], m[2], m[0]])
    return np.array(rows)


def main() -> None:
    out = {}
    print("A-priori certificate fitted separately for each base predictor, unit-level calibration.")
    print("gap, bound and margin are means over held-out configurations (60/40 split).\n")
    print(
        f"{'model':>9}{'a':>8}{'L':>8}{'R^2':>8}{'gap':>8}{'bound':>8}"
        f"{'margin':>9}{'factor':>8}{'holds':>8}"
    )
    for model in MODELS:
        cert = certificate(rows_for(model), seed=1)
        factor = cert["bound_mean"] / max(cert["gap_mean"], 1e-9)
        out[model] = {**cert, "conservatism_factor": float(factor)}
        print(
            f"{model:>9}{cert['a']:>8.3f}{cert['L']:>8.3f}{cert['r2']:>8.3f}"
            f"{cert['gap_mean']:>8.3f}{cert['bound_mean']:>8.3f}{cert['margin_mean']:>9.3f}"
            f"{factor:>8.1f}{cert['holds'] * 100:>7.0f}%"
        )

    span = [out[m]["margin_mean"] for m in MODELS]
    print(
        f"\nmargin spans {min(span):.3f} to {max(span):.3f} across four predictor classes; "
        f"the bound holds on {min(out[m]['holds'] for m in MODELS) * 100:.0f}% or more everywhere."
    )
    with open("out/r11b_bound_complexity.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("wrote out/r11b_bound_complexity.json")


if __name__ == "__main__":
    main()
