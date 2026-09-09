"""R1.1: does the result depend on the complexity of the base predictor?

Reviewer 1: SCC is claimed to be a drop-in modification for any pre-trained predictor, but the
case study only used extrapolation from a simple nominal rate model. With a strongly non-linear
learner the interpolation and extrapolation errors across operating regimes become more
complicated, and the dimensionless scale sigma(theta) alone might not absorb the resulting
shift in the score distribution. The conservatism of the a-priori bound should be evaluated
against base-model complexity.

Four predictors of increasing capacity are trained ON THE SOURCE CONDITION ONLY and deployed on
the target condition, which is the transfer setting the paper claims:

  physics   closed-form extrapolation from the nominal rate (as published)
  linear    ridge regression
  forest    random forest
  mlp       multi-layer perceptron

Calibration is unit-level throughout (one score per unit) per the R1.5 resolution.

Run:  PYTHONPATH=src python3 scripts/r11_base_model.py
"""

from __future__ import annotations

import itertools
import json
import warnings

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from ipis.module2_pdm.scc.conformal import nominal_rate, one_sided_quantile
from ipis.module2_pdm.scc.deactivation import A_FAIL, simulate_condition

warnings.filterwarnings("ignore")

E1, A1 = 80e3, 5e3
E2, A2 = 110e3, 4e5
TEMPS = [600.0, 650.0, 700.0]
FRACS = [0.3, 0.5, 0.7]
ALPHA, TARGET = 0.10, 0.90
N_UNITS, SEEDS = 400, 3
ETAS = [0.0, 0.5, 1.0, 2.0]


def snapshots(temp, eta, seed, rng):
    """One snapshot per unit: observed activity, elapsed time, true RUL."""
    runs = simulate_condition(temp, N_UNITS, A1, E1, a2=A2, e2=E2, eta=eta, seed=seed)
    picks = rng.integers(0, len(FRACS), size=len(runs))
    a_obs, t_el, rul = [], [], []
    for i, run in enumerate(runs):
        idx = min(int(np.searchsorted(run.t, FRACS[picks[i]] * run.life)), len(run.t) - 1)
        a_obs.append(run.a_obs[idx])
        t_el.append(run.t[idx])
        rul.append(run.life - run.t[idx])
    return np.array(a_obs), np.array(t_el), np.array(rul)


def make(model):
    if model == "linear":
        return Ridge(alpha=1.0)
    if model == "forest":
        return RandomForestRegressor(n_estimators=80, min_samples_leaf=8, random_state=0, n_jobs=-1)
    return MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=600, random_state=0)


def fit_predict(model, xtr, ytr, xte):
    m = make(model)
    sc = StandardScaler().fit(xtr)
    m.fit(sc.transform(xtr), ytr)
    return m.predict(sc.transform(xte))


def scores_for_pair(model, src, tgt, data):
    """Raw-coordinate scores (naive) and dimensionless-coordinate scores (SCC).

    Naive: the base model is trained on the source condition in RAW coordinates.
    SCC:   the same model class is trained in DIMENSIONLESS coordinates, which is exactly the
           paper's prescription applied to a learned predictor rather than a closed form.
    """
    a_s, t_s, y_s = data[src]
    a_t, t_t, y_t = data[tgt]
    k_s, k_t = nominal_rate(src, E1, A1), nominal_rate(tgt, E1, A1)

    if model == "physics":
        # closed-form extrapolation; each unit uses its OWN condition's rate constant
        p_s = np.array([max(np.log(max(a, 1e-3) / A_FAIL), 0.0) / k_s for a in a_s])
        p_t = np.array([max(np.log(max(a, 1e-3) / A_FAIL), 0.0) / k_t for a in a_t])
        v_s_raw, v_t_raw = p_s - y_s, p_t - y_t
        return v_s_raw, v_t_raw, v_s_raw * k_s, v_t_raw * k_t

    # naive: raw features and raw target, trained on source, applied to target
    xs_raw = np.column_stack([a_s, t_s])
    xt_raw = np.column_stack([a_t, t_t])
    v_s_raw = fit_predict(model, xs_raw, y_s, xs_raw) - y_s
    v_t_raw = fit_predict(model, xs_raw, y_s, xt_raw) - y_t

    # SCC: dimensionless features and dimensionless target
    xs_dim = np.column_stack([a_s, t_s * k_s])
    xt_dim = np.column_stack([a_t, t_t * k_t])
    v_s_dim = fit_predict(model, xs_dim, y_s * k_s, xs_dim) - y_s * k_s
    v_t_dim = fit_predict(model, xs_dim, y_s * k_s, xt_dim) - y_t * k_t
    return v_s_raw, v_t_raw, v_s_dim, v_t_dim


def run(model):
    rows = []
    for eta in ETAS:
        pair_vals = {}
        for s in range(SEEDS):
            rng = np.random.default_rng(s * 977 + 11)
            data = {t: snapshots(t, eta, s * 17 + i, rng) for i, t in enumerate(TEMPS)}
            for src, tgt in itertools.permutations(TEMPS, 2):
                v_sr, v_tr, v_sd, v_td = scores_for_pair(model, src, tgt, data)
                qn = one_sided_quantile(v_sr, ALPHA)
                qs = one_sided_quantile(v_sd, ALPHA)
                cov_n = float(np.mean(v_tr <= qn))
                cov_s = float(np.mean(v_td <= qs))
                pair_vals.setdefault((src, tgt), []).append(
                    [max(0.0, TARGET - cov_n), max(0.0, TARGET - cov_s)]
                )
        for pair, v in pair_vals.items():
            m = np.mean(v, axis=0)
            rows.append({"eta": eta, "pair": str(pair), "naive": m[0], "scc": m[1]})
    return rows


def main():
    out = {}
    print("Coverage gap (target 0.90), predictor trained on the SOURCE condition only.")
    print(f"{'model':>9}{'eta':>7}{'naive gap':>11}{'SCC gap':>10}")
    for model in ["physics", "linear", "forest", "mlp"]:
        rows = run(model)
        for eta in ETAS:
            sub = [r for r in rows if r["eta"] == eta]
            ng = float(np.mean([r["naive"] for r in sub]))
            sg = float(np.mean([r["scc"] for r in sub]))
            out[f"{model}|{eta}"] = {"naive": ng, "scc": sg}
            print(f"{model:>9}{eta:>7.2f}{ng:>11.3f}{sg:>10.3f}")
        print()

    print("Conservatism check: SCC gap at eta=0 by model capacity")
    for model in ["physics", "linear", "forest", "mlp"]:
        print(f"  {model:>9}: {out[f'{model}|0.0']['scc']:.3f}")

    with open("out/r11_base_model.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote out/r11_base_model.json")


if __name__ == "__main__":
    main()
