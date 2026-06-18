"""FEMTO RUL evaluation: trajectory-similarity (Option B) vs regression baseline.

Consumes femto_hi_*.csv (from build_femto_hi_trend.py). Per bearing: degradation
index DI = cummax(EMA(t2)), matching variable hi = log1p(DI), onset FPT, post-FPT
arc. Bearing3_1 excluded by default (non-monotone: degrades mid-life then quiets --
life peak 41 g, EOL peak 7 g -- poisoning RUL; flagged atypical-failure).

Scored leave-one-bearing-out at truncation-point fractions (40..95% of the arc),
per the PHM-2012 protocol (not the degenerate RUL->0 tail). Lower bounds via
CROSS-conformal (each library bearing predicted by the rest -> pooled residuals).
Three methods compared so the real data picks the read-off:
  similarity-phase : rate-invariant time-scaling (RUL from the test's own clock).
  similarity-abs   : library RUL read-off at the matched phase.
  regression       : global log1p(DI)->RUL baseline (absolute DI spans ~16,000x).

    set PYTHONPATH=src
    python scripts/run_femto_rul.py
"""

from __future__ import annotations

import csv
import glob
from pathlib import Path

import numpy as np

from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile
from ipis.module2_pdm.rul.degradation import degradation_index, first_prediction_time
from ipis.module2_pdm.rul.rul_model import RULModel, lower_bound_coverage, phm2012_score
from ipis.module2_pdm.rul.similarity import SimilarityRUL

WARN_LIMIT_DF9 = 16.92  # chi2.ppf(0.95, df=9)
EXCLUDE = {"Bearing3_1"}
FRACS = np.arange(0.40, 0.96, 0.05)
ALPHA = 0.1
INTERVAL_S = 10.0


def _load(path: Path):
    t2, rul, fpt = [], [], -1
    with path.open() as f:
        for row in csv.DictReader(f):
            t2.append(float(row["t2"]))
            rul.append(float(row["rul_s"]))
            if "fpt" in row:
                fpt = int(row["fpt"])
    return path.stem.replace("femto_hi_", ""), np.asarray(t2), np.asarray(rul), fpt


def _arc(t2, rul, fpt):
    di = degradation_index(t2, alpha=0.05)
    if fpt is None or fpt < 0:  # legacy CSV without fpt column -> recompute
        fpt = first_prediction_time(t2, warn_limit=WARN_LIMIT_DF9, persist=3) or 0
    return di[fpt:], np.log1p(di[fpt:]), rul[fpt:], fpt


def _tp(n):
    return [min(n - 1, max(1, int(f * n))) for f in FRACS]


def eval_similarity(bearings, names, mode):
    per_phm, all_true, all_lower = {}, [], []
    for test in names:
        lib = [n for n in names if n != test]
        tb = bearings[test]
        tp = _tp(len(tb["hi"]))
        true = np.array([tb["rul"][j] for j in tp])
        resid = []
        for c in lib:
            sub = [bearings[n] for n in lib if n != c]
            mc = SimilarityRUL([(s["hi"], s["rul"]) for s in sub], interval=INTERVAL_S, mode=mode)
            cb = bearings[c]
            resid += [mc.predict_one(cb["hi"][:j]) - cb["rul"][j] for j in _tp(len(cb["hi"]))]
        q = conformal_quantile(np.array(resid), 1.0 - ALPHA)
        m = SimilarityRUL(
            [(bearings[n]["hi"], bearings[n]["rul"]) for n in lib], interval=INTERVAL_S, mode=mode
        )
        pred = np.array([m.predict_one(tb["hi"][:j]) for j in tp])
        lower = np.maximum(pred - q, 0.0)
        per_phm[test] = phm2012_score(pred, true)
        all_true.append(true)
        all_lower.append(lower)
    pooled = lower_bound_coverage(np.concatenate(all_true), np.concatenate(all_lower))
    return per_phm, float(np.mean(list(per_phm.values()))), pooled


def eval_regression(bearings, names):
    per_phm, all_true, all_lower = {}, [], []
    for test in names:
        lib = [n for n in names if n != test]
        tb = bearings[test]
        tp = _tp(len(tb["di"]))
        true = np.array([tb["rul"][j] for j in tp])
        resid = []
        for c in lib:
            sub_di = np.concatenate([bearings[n]["di"] for n in lib if n != c])
            sub_rul = np.concatenate([bearings[n]["rul"] for n in lib if n != c])
            rc = RULModel.fit(sub_di, sub_rul, alpha=ALPHA)
            cb = bearings[c]
            pc = rc.predict(cb["di"])
            resid += [pc[j] - cb["rul"][j] for j in _tp(len(cb["di"]))]
        q = conformal_quantile(np.array(resid), 1.0 - ALPHA)
        di_fit = np.concatenate([bearings[n]["di"] for n in lib])
        rul_fit = np.concatenate([bearings[n]["rul"] for n in lib])
        m = RULModel.fit(di_fit, rul_fit, alpha=ALPHA)
        pred_full = m.predict(tb["di"])
        pred = np.array([pred_full[j] for j in tp])
        lower = np.maximum(pred - q, 0.0)
        per_phm[test] = phm2012_score(pred, true)
        all_true.append(true)
        all_lower.append(lower)
    pooled = lower_bound_coverage(np.concatenate(all_true), np.concatenate(all_lower))
    return per_phm, float(np.mean(list(per_phm.values()))), pooled


def main() -> int:
    bearings = {}
    for fp in sorted(glob.glob("data/processed/femto_hi_*.csv")):
        name, t2, rul, fpt_meta = _load(Path(fp))
        if name in EXCLUDE:
            print(f"[excluded] {name}: non-monotone / atypical failure (flagged separately)")
            continue
        di_arc, hi_arc, rul_arc, fpt = _arc(t2, rul, fpt_meta)
        bearings[name] = {"di": di_arc, "hi": hi_arc, "rul": rul_arc, "fpt": fpt, "n": len(t2)}

    if len(bearings) < 3:
        print(f"[ERROR] need >= 3 usable bearings (have {len(bearings)}).")
        return 1

    names = sorted(bearings)
    print(f"\nUsable: {', '.join(names)}  (FRACS {FRACS[0]:.2f}-{FRACS[-1]:.2f}, alpha={ALPHA})")
    print(f"{'bearing':<14}{'FPT':>6}{'arc':>7}{'EOL min':>9}")
    for n in names:
        b = bearings[n]
        print(f"{n:<14}{b['fpt']:>6}{len(b['hi']):>7}{(b['rul'][0] / 60):>9.1f}")
    print()

    sp, sp_m, sp_c = eval_similarity(bearings, names, "phase")
    sa, sa_m, sa_c = eval_similarity(bearings, names, "absolute")
    rp, rp_m, rp_c = eval_regression(bearings, names)

    print(f"{'held-out':<14}{'sim-phase':>11}{'sim-abs':>10}{'regress':>10}")
    for n in names:
        print(f"{n:<14}{sp[n]:>11.3f}{sa[n]:>10.3f}{rp[n]:>10.3f}")
    print()
    print(f"{'METHOD':<18}{'mean PHM':>10}{'pooled cov':>12}  (target cov >= {1 - ALPHA:.2f})")
    print(f"{'similarity-phase':<18}{sp_m:>10.3f}{sp_c:>12.3f}")
    print(f"{'similarity-abs':<18}{sa_m:>10.3f}{sa_c:>12.3f}")
    print(f"{'regression':<18}{rp_m:>10.3f}{rp_c:>12.3f}")
    print(
        "\nFEMTO RUL is hard (PHM-2012 challenge winners ~0.3-0.5); the headline is "
        "calibrated coverage as much as point accuracy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
