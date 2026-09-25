"""IPIS M3 (TMLR reforge), Gate 2b: DWSIM-twin re-run with certify-then-deploy.

Reuses the frozen 3B pipeline (ipis.module3_rto) on the DWSIM campaign CSVs. Every deployed
decision is scored with the EXACT violation probability of the truth surface: x_B is monotone
in z, so V(u) = P(z > z*(u)) with z*(u) the spec-crossing composition (computed once on a dense
z grid). Repeated independent trials per disturbance level sigma_z.

Methods: fixed split-conformal margin; CQR (plug-in); TCST v2 a-posteriori kappa search
(faithful: kappa >= 1, 6000 validation draws, tolerance 0.01); certify-then-deploy (Thm 3,
fixed-sequence Clopper-Pearson) at budgets m; scenario approach (Campi-Garatti N, d = 2);
sampling-and-discarding at N = m; oracle (exact conditional quantile).

Usage (repo root):  python scripts/paper2_tmlr/gate2_twin_certified.py \
    --nominal data/raw/dwsim/twin_runs.csv --zvaried data/raw/dwsim/twin_runs_zvaried.csv
"""

from __future__ import annotations

import argparse
import json
import time
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
from ipis.module3_rto import chance_rto as crto
from ipis.module3_rto.economics import EconomicsAnchor
from ipis.module3_rto.surrogate import _fit, fit_gpr_from_csv, fit_truth_surface_3d
from scipy import stats
from scipy.stats import truncnorm

ALPHA, DELTA, SPEC = 0.10, 0.05, 0.02
REALISTIC = 0.006
Z_LO, Z_HI, Z0 = 0.30, 0.40, 0.35
KAPPAS = np.round(np.arange(6.0, 0.45, -0.05), 2)  # most conservative first
SEED = 20260926


def setup(nominal: str, zvaried: str):
    econ = EconomicsAnchor()
    xb_nom, _ = fit_gpr_from_csv(nominal)
    dfn = pd.read_csv(nominal)
    xd_nom = _fit(dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["xd_c4"], log_target=False)
    q_nom = _fit(
        dfn["reflux_ratio"], dfn["distillate_kmol_h"], dfn["reboiler_duty_kW"], log_target=False
    )
    truth = fit_truth_surface_3d(zvaried)
    grid = crto.build_decision_grid(xb_nom, xd_nom, q_nom, econ)
    return xb_nom, truth, grid


def spec_crossing(truth, grid, nz: int = 201) -> tuple[np.ndarray, float]:
    """z*(u): smallest z with x_B(u, z) > SPEC (+inf if never, -inf if always) + monotone share."""
    zs = np.linspace(Z_LO, Z_HI, nz)
    x = np.column_stack(
        [np.clip(crto._grid3d(truth, grid.r, grid.d, np.full(grid.n, z)), 0, 1) for z in zs]
    )
    mono = float(np.mean(np.all(np.diff(x, axis=1) >= -1e-9, axis=1)))
    above = x > SPEC
    k = np.argmax(above, axis=1)
    zstar = np.full(grid.n, np.inf)
    has = above.any(axis=1)
    zstar[has & (k == 0)] = -np.inf
    mid = has & (k > 0)
    i = np.flatnonzero(mid)
    x0, x1 = x[i, k[i] - 1], x[i, k[i]]
    zstar[i] = zs[k[i] - 1] + (SPEC - x0) * (zs[1] - zs[0]) / np.maximum(x1 - x0, 1e-12)
    return zstar, mono


def v_exact(zstar: np.ndarray, sigma: float) -> np.ndarray:
    a, b = (Z_LO - Z0) / sigma, (Z_HI - Z0) / sigma
    return truncnorm.sf(zstar, a, b, loc=Z0, scale=sigma)


def cp_ucb(n_viol: int, m: int) -> float:
    return 1.0 if n_viol >= m else float(stats.beta.ppf(1 - DELTA, n_viol + 1, m - n_viol))


def scenario_n(eps: float, beta: float, d: int) -> int:
    n = d
    while stats.binom.cdf(d - 1, n, eps) > beta:
        n += 1
    return n


def discard_k(n: int, eps: float, beta: float, d: int) -> int:
    k = -1
    while comb(k + d, k + 1) * stats.binom.cdf(k + d, n, eps) <= beta:
        k += 1
    return k


N_SC = scenario_n(ALPHA, DELTA, 2)


def argmax_feasible(profit: np.ndarray, mask: np.ndarray) -> int | None:
    idx = np.flatnonzero(mask)
    return None if idx.size == 0 else int(idx[np.argmax(profit[idx])])


def one_trial(rng, sigma, xb_nom, truth, grid, zstar, v, m_list, kd) -> dict:
    dist = crto.DisturbanceModel(sigma=sigma)
    cal = crto.sample_calibration(
        xb_nom, truth, dist, rng, n=int(1500 * max(1.0, sigma / REALISTIC))
    )
    out: dict = {}

    def rec(name: str, i: int | None) -> None:
        out[name] = None if i is None else (float(v[i]), float(grid.profit[i]))

    rec("fixed", crto._solve_index(grid, crto.fixed_backoff(cal, ALPHA), SPEC))
    c_cqr = crto.cqr_backoff(cal, grid, ALPHA)
    rec("cqr", crto._solve_index(grid, c_cqr, SPEC))
    kap_i = [(k, crto._solve_index(grid, k * c_cqr, SPEC)) for k in KAPPAS]
    kap_i = [(k, i) for k, i in kap_i if i is not None]

    zval = dist.draw(6000, rng)  # TCST v2 procedure, faithful settings
    plug = None
    for k, i in kap_i:
        if k >= 1.0 and float(np.mean(zval > zstar[i])) <= ALPHA + 0.01:
            plug = i  # descending kappa: last pass is the smallest compliant kappa
    rec("tcst_v2_aposteriori", plug)

    for m in m_list:
        zc = np.sort(dist.draw(m, rng))
        cert = None
        for _, i in kap_i:
            n_viol = m - int(np.searchsorted(zc, zstar[i], side="right"))
            if cp_ucb(n_viol, m) <= ALPHA:
                cert = i
            else:
                break
        rec(f"certified_m{m}", cert)
        zd = np.sort(dist.draw(m, rng))
        rec(f"discard_N{m}", argmax_feasible(grid.profit, zstar >= zd[m - 1 - kd[m]]))
    zs = dist.draw(N_SC, rng)
    rec("scenario_N46", argmax_feasible(grid.profit, zstar >= zs.max()))
    return out


def summarize(rows: list[dict], name: str, pi_orc: float) -> dict:
    vals = [r[name] for r in rows]
    dep = [x for x in vals if x is not None]
    n = len(vals)
    viol = np.array([x for x, _ in dep])
    prof = np.array([p for _, p in dep])
    unsafe = int((viol > ALPHA + 1e-12).sum()) if dep else 0
    lo = 0.0 if unsafe == 0 else float(stats.beta.ppf(0.025, unsafe, n - unsafe + 1))
    hi = 1.0 if unsafe == n else float(stats.beta.ppf(0.975, unsafe + 1, n - unsafe))
    return {
        "deploy_rate": len(dep) / n,
        "mean_violation": float(viol.mean()) if dep else None,
        "P_deploy_unsafe": unsafe / n,
        "P_deploy_unsafe_CI95": [lo, hi],
        "mean_profit_usd_h": float(prof.mean()) if dep else None,
        "profit_gap_vs_oracle_usd_h": float(pi_orc - prof.mean()) if dep else None,
        "profit_gap_vs_oracle_pct": float((1 - prof.mean() / pi_orc) * 100) if dep else None,
    }


def _names(m_list: list[int]) -> list[str]:
    names = ["fixed", "cqr", "tcst_v2_aposteriori", "scenario_N46"]
    return names + [f"certified_m{m}" for m in m_list] + [f"discard_N{m}" for m in m_list]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nominal", required=True)
    ap.add_argument("--zvaried", required=True)
    ap.add_argument("--sigma", type=float, help="run one disturbance level (chunk mode)")
    ap.add_argument("--t0", type=int, default=0)
    ap.add_argument("--t1", type=int, default=200)
    ap.add_argument("--m", type=int, nargs="+", default=[200, 1000])
    ap.add_argument("--chunks", default="/tmp/g2_chunks")
    ap.add_argument("--merge", action="store_true", help="merge chunk files into the evidence JSON")
    ap.add_argument("--out", default="docs/module3/tmlr/evidence/gate2_twin.json")
    args = ap.parse_args()

    xb_nom, truth, grid = setup(args.nominal, args.zvaried)
    zstar, mono = spec_crossing(truth, grid)
    kd = {m: discard_k(m, ALPHA, DELTA, 2) for m in args.m}
    chunks = Path(args.chunks)
    chunks.mkdir(parents=True, exist_ok=True)

    if not args.merge:  # chunk mode: deterministic per-trial seeds, independent of chunking
        t0 = time.time()
        v = v_exact(zstar, args.sigma)
        rows = []
        for t in range(args.t0, args.t1):
            rng = np.random.default_rng([SEED, round(args.sigma * 1e5), t])
            rows.append(one_trial(rng, args.sigma, xb_nom, truth, grid, zstar, v, args.m, kd))
        f = chunks / f"s{args.sigma:.3f}_t{args.t0}-{args.t1}.json"
        f.write_text(json.dumps(rows))
        print(f"sigma={args.sigma:.3f} trials {args.t0}-{args.t1} ({time.time() - t0:.0f}s)")
        return

    by_sigma: dict[str, list] = {}
    for f in sorted(chunks.glob("s*_t*.json")):
        by_sigma.setdefault(f.name[1:6], []).extend(json.loads(f.read_text()))
    result = {
        "config": {
            "alpha": ALPHA,
            "delta": DELTA,
            "spec_xb": SPEC,
            "m": args.m,
            "discard_k": kd,
            "scenario_N": N_SC,
            "kappa_grid": [float(KAPPAS[0]), float(KAPPAS[-1]), 0.05],
            "grid_points": int(grid.n),
            "monotone_in_z_share": mono,
            "n_cal_rule": "int(1500 * max(1, sigma_z / 0.006))",
            "seed": SEED,
        },
        "by_sigma": {},
    }
    for key in sorted(by_sigma):
        sigma = float(key)
        rows = by_sigma[key]
        v = v_exact(zstar, sigma)
        i_orc = argmax_feasible(grid.profit, v <= ALPHA)
        pi_orc = float(grid.profit[i_orc])
        result["by_sigma"][key] = {
            "trials": len(rows),
            "oracle": {
                "violation": float(v[i_orc]),
                "profit_usd_h": pi_orc,
                "R": float(grid.r[i_orc]),
                "D": float(grid.d[i_orc]),
            },
            "methods": {nm: summarize(rows, nm, pi_orc) for nm in _names(args.m)},
        }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"merged {sum(len(r) for r in by_sigma.values())} trials -> {args.out}")


if __name__ == "__main__":
    main()
