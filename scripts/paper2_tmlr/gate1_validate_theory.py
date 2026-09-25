"""IPIS M3 (TMLR reforge), Gate 1: numerical validation of the corrected theory.

Synthetic chance-constrained RTO with EXACT ground truth (closed-form violation probability).
Over repeated independent trials it checks:
  P1/P2   back-offs that are marginally valid (fixed, normalized, local CQR) over-violate at the
          optimized decision (optimizer's curse acting on the back-off estimate);
  TCSTv2  the a-posteriori plug-in kappa search is accurate on average but carries no
          (alpha, delta) guarantee;
  T3      certify-then-deploy (fixed-sequence Clopper-Pearson over a nested kappa family) keeps
          P(deploy an unsafe decision) <= delta despite selection over u and over kappa;
  base    oracle margin; scenario approach (Campi-Garatti N for d=2); sampling-and-discarding
          at the same sample budget m;
  C4      certification budget m* at (alpha, delta) = (0.10, 0.05).
Seed-fixed. Writes docs/module3/tmlr/evidence/gate1_validation.json.
"""

from __future__ import annotations

import json
import math
from math import comb
from pathlib import Path

import numpy as np
from scipy import stats

ALPHA, DELTA, GBAR = 0.10, 0.05, 0.90
ZD = stats.gamma(a=2.0, scale=1.0)  # skewed exogenous disturbance, unknown to every method
Z0 = float(ZD.median())
N_CAL, N_TR = 500, 250  # calibration campaign; first half trains the local estimators
K_NRM, K_CQR = 15, 40
M_CERT = 200
KAPPAS = np.round(np.arange(4.0, 0.24, -0.1), 2)  # most conservative first (fixed sequence)
R_TRIALS = 400
SEED = 20260925
D_DEC = 2
OUT = Path("docs/module3/tmlr/evidence/gate1_validation.json")

_G = 61
_g1, _g2 = np.meshgrid(np.linspace(0, 1, _G), np.linspace(0, 1, _G), indexing="ij")
UG = np.column_stack([_g1.ravel(), _g2.ravel()])


def a_fn(u: np.ndarray) -> np.ndarray:
    return 0.30 + 0.45 * u[:, 0] + 0.25 * u[:, 1]


def b_fn(u: np.ndarray) -> np.ndarray:
    return 0.03 + 0.12 * u[:, 0] ** 2 + 0.03 * u[:, 1]


A, B = a_fn(UG), b_fn(UG)
PI = UG[:, 0] + 0.5 * UG[:, 1]
ZTH = Z0 + (GBAR - A) / B  # g(u, z) > GBAR  <=>  z > ZTH(u), since b > 0
V = ZD.sf(ZTH)  # exact violation probability of every grid decision
_SAFE = V <= ALPHA
I_ORC = int(np.flatnonzero(_SAFE)[np.argmax(PI[_SAFE])])
PI_ORC = float(PI[I_ORC])


def argmax_feasible(mask: np.ndarray) -> int | None:
    idx = np.flatnonzero(mask)
    return None if idx.size == 0 else int(idx[np.argmax(PI[idx])])


def conf_q(scores: np.ndarray) -> float:
    n = scores.size
    k = math.ceil((n + 1) * (1 - ALPHA))
    return math.inf if k > n else float(np.partition(scores, k - 1)[k - 1])


def knn(xq: np.ndarray, xt: np.ndarray, k: int) -> np.ndarray:
    d2 = ((xq[:, None, :] - xt[None, :, :]) ** 2).sum(-1)
    return np.argpartition(d2, k - 1, axis=1)[:, :k]


def cp_ucb(n_viol: int, m: int) -> float:
    return 1.0 if n_viol >= m else float(stats.beta.ppf(1 - DELTA, n_viol + 1, m - n_viol))


def scenario_n(eps: float, beta: float, d: int) -> int:
    """Smallest N with sum_{i<d} C(N,i) eps^i (1-eps)^(N-i) <= beta (Campi-Garatti 2008)."""
    n = d
    while stats.binom.cdf(d - 1, n, eps) > beta:
        n += 1
    return n


def discard_k(n: int, eps: float, beta: float, d: int) -> int:
    """Largest k with C(k+d-1,k) * Binom(n,eps).cdf(k+d-1) <= beta (Campi-Garatti 2011)."""
    k = -1
    while comb(k + d, k + 1) * stats.binom.cdf(k + d, n, eps) <= beta:
        k += 1
    return k


N_SC = scenario_n(ALPHA, DELTA, D_DEC)
_KD: dict[int, int] = {}


def one_trial(rng: np.random.Generator, m_cert: int, mode: str, k_nrm: int = K_NRM) -> dict:
    uc = rng.random((N_CAL, 2))
    zc = ZD.rvs(size=N_CAL, random_state=rng)
    r = b_fn(uc) * (zc - Z0)  # residual of the fixed nominal model g_hat(u) = a(u)
    ut, rt, uk, rk = uc[:N_TR], r[:N_TR], uc[N_TR:], r[N_TR:]
    out: dict = {}

    def deploy(name: str, i: int | None) -> None:
        out[name] = None if i is None else (float(V[i]), float(PI[i]))

    if mode in ("full", "nrm"):
        s_g = np.abs(rt)[knn(UG, ut, k_nrm)].mean(1)
        s_k = np.abs(rt)[knn(uk, ut, k_nrm)].mean(1)
        c_nrm = np.maximum(conf_q(rk / s_k) * s_g, 0.0)
        deploy("normalized", argmax_feasible(A + c_nrm <= GBAR))
        if mode == "nrm":
            return out
    q_g = np.quantile(rt[knn(UG, ut, K_CQR)], 1 - ALPHA, axis=1)
    q_k = np.quantile(rt[knn(uk, ut, K_CQR)], 1 - ALPHA, axis=1)
    c_cqr = np.maximum(q_g + conf_q(rk - q_k), 0.0)

    seq = [i for kap in KAPPAS if (i := argmax_feasible(A + kap * c_cqr <= GBAR)) is not None]
    zcert = np.sort(ZD.rvs(size=m_cert, random_state=rng))  # independent of calibration data
    nviol = [m_cert - int(np.searchsorted(zcert, ZTH[i], side="right")) for i in seq]
    cert = None
    for i, n in zip(seq, nviol):  # fixed sequence: stop at the first failed certification
        if cp_ucb(n, m_cert) <= ALPHA:
            cert = i
        else:
            break
    deploy("certified", cert)
    if mode == "cert":
        return out

    plug = None
    for i, n in zip(seq, nviol):  # TCST v2 procedure: smallest kappa passing the plug-in test
        if n / m_cert <= ALPHA:
            plug = i
    deploy("plugin_aposteriori", plug)
    c_fix = max(conf_q(r), 0.0)
    deploy("fixed", argmax_feasible(A + c_fix <= GBAR))
    deploy("cqr", argmax_feasible(A + c_cqr <= GBAR))
    for name, c in (("fixed", np.full_like(A, c_fix)), ("normalized", c_nrm), ("cqr", c_cqr)):
        out["marg_" + name] = float(ZD.sf(Z0 + c / B).mean())  # exact miss averaged over u
    zs = ZD.rvs(size=N_SC, random_state=rng)
    deploy("scenario", argmax_feasible(A + B * (zs.max() - Z0) <= GBAR))
    kd = _KD.setdefault(m_cert, discard_k(m_cert, ALPHA, DELTA, D_DEC))
    zd = np.sort(ZD.rvs(size=m_cert, random_state=rng))
    deploy("scenario_discard", argmax_feasible(A + B * (zd[m_cert - 1 - kd] - Z0) <= GBAR))
    return out


def cp_two_sided(x: int, n: int) -> tuple[float, float]:
    lo = 0.0 if x == 0 else float(stats.beta.ppf(0.025, x, n - x + 1))
    hi = 1.0 if x == n else float(stats.beta.ppf(0.975, x + 1, n - x))
    return lo, hi


def summarize(rows: list[dict], name: str) -> dict:
    vals = [row[name] for row in rows]
    dep = [v for v in vals if v is not None]
    n = len(vals)
    viol = np.array([v for v, _ in dep])
    prof = np.array([p for _, p in dep])
    unsafe = int((viol > ALPHA + 1e-12).sum()) if dep else 0
    return {
        "trials": n,
        "deploy_rate": len(dep) / n,
        "mean_violation": float(viol.mean()) if dep else None,
        "p90_violation": float(np.quantile(viol, 0.9)) if dep else None,
        "P_deploy_unsafe": unsafe / n,
        "P_deploy_unsafe_CI95": cp_two_sided(unsafe, n),
        "profit_gap_vs_oracle_pct": float((1 - prof.mean() / PI_ORC) * 100) if dep else None,
    }


def budget_table(vs=(0.0, 0.02, 0.04, 0.06, 0.08), power=0.8, m_max=20000) -> dict:
    ms = np.arange(1, m_max + 1)
    nmax = stats.binom.ppf(DELTA, ms, ALPHA).astype(int)
    nmax = np.where(stats.binom.cdf(nmax, ms, ALPHA) > DELTA, nmax - 1, nmax)
    res = {}
    for v in vs:
        pw = np.where(nmax >= 0, stats.binom.cdf(np.maximum(nmax, 0), ms, v), 0.0)
        hit = np.flatnonzero(pw >= power)
        res[f"{v:.2f}"] = int(ms[hit[0]]) if hit.size else None
    return {"power": power, "m_star_by_true_violation": res}


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = [one_trial(rng, M_CERT, "full") for _ in range(R_TRIALS)]
    methods = [
        "fixed",
        "normalized",
        "cqr",
        "plugin_aposteriori",
        "certified",
        "scenario",
        "scenario_discard",
    ]
    main_tab = {m: summarize(rows, m) for m in methods}
    for m in ("fixed", "normalized", "cqr"):
        main_tab[m]["marginal_miss_mean"] = float(np.mean([row["marg_" + m] for row in rows]))
    budget_sweep = {}
    for m in (30, 50, 100, 200, 400, 800):
        rr = [one_trial(rng, m, "cert") for _ in range(200)]
        budget_sweep[str(m)] = summarize(rr, "certified")
    curse_sweep = {}
    for k in (5, 15, 45, 125):
        rr = [one_trial(rng, M_CERT, "nrm", k_nrm=k) for _ in range(300)]
        curse_sweep[str(k)] = summarize(rr, "normalized")
    out = {
        "config": {
            "alpha": ALPHA,
            "delta": DELTA,
            "gbar": GBAR,
            "disturbance": "Gamma(shape=2, scale=1)",
            "n_cal": N_CAL,
            "m_cert": M_CERT,
            "trials": R_TRIALS,
            "seed": SEED,
            "grid": _G * _G,
            "scenario_N": N_SC,
            "discard_k_at_m_cert": _KD.get(M_CERT),
        },
        "oracle": {"violation": float(V[I_ORC]), "profit": PI_ORC},
        "methods": main_tab,
        "certified_budget_sweep": budget_sweep,
        "optimizers_curse_sweep_normalized_knn_k": curse_sweep,
        "certification_budget": budget_table(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
