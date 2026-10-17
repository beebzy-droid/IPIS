"""Numerical check of Proposition P2 (pre-registration Sec. 4), library-based.

P2: for any sequence of positive scores, the level of the single-state delayed loop stays in
[-gamma (theta + 1), 1 + gamma (theta + 1)], and the realised miscoverage of the T labelled samples
satisfies |mean(err) - alpha*| <= (1 + 2 gamma (theta + 1)) / (gamma T).

36 adversarial cases: theta in {0, 3, 20, 60}, gamma in {0.005, 0.05, 0.2}, and three positive
score laws (persistent |AR(1)| with phi = 0.99, level steps by factors of 10, and 5 % spikes of
100 times). Prints any violation and the largest ratio of deviation to bound.

Run from the repository root (under a minute):
    set PYTHONPATH=src
    python scripts\\pilots\\p2_bound_check.py
"""

from __future__ import annotations

import math

import numpy as np

from ipis.module1_soft_sensor.evaluation import delayed_aci as d

ALPHA, T = 0.10, 20_000


def scores(kind: str, rng: np.random.Generator) -> np.ndarray:
    if kind == "persistent":
        x = np.zeros(T)
        e = rng.standard_normal(T)
        for t in range(1, T):
            x[t] = 0.99 * x[t - 1] + math.sqrt(1 - 0.99**2) * e[t]
        return np.abs(x)
    if kind == "steps":
        return np.abs(rng.standard_normal(T)) * np.repeat(rng.choice([0.1, 1, 10], T // 500), 500)
    s = np.abs(rng.standard_normal(T))
    s[rng.random(T) < 0.05] *= 100
    return s


def main() -> int:
    rng = np.random.default_rng(0)
    worst, violations = 0.0, 0
    for theta in (0, 3, 20, 60):
        for gamma in (0.005, 0.05, 0.2):
            for kind in ("persistent", "steps", "spikes"):
                s = scores(kind, rng)
                res = d.run_delayed_aci(
                    s, theta, init_scores=np.abs(rng.standard_normal(200)), alpha=ALPHA, gamma=gamma
                )
                a, err = res["alpha"], 1.0 - res["covered"]
                n_lab = T - theta  # samples whose labels have arrived by the end
                dev = abs(err[:n_lab].mean() - ALPHA)
                bound = (1 + 2 * gamma * (theta + 1)) / (gamma * n_lab)
                inside = a.min() >= -gamma * (theta + 1) - 1e-12
                inside &= a.max() <= 1 + gamma * (theta + 1) + 1e-12
                worst = max(worst, dev / bound)
                if not inside or dev > bound:
                    violations += 1
                    print("VIOLATION", theta, gamma, kind, a.min(), a.max(), dev, bound)
    print(f"cases: 36; violations: {violations}; largest deviation / bound: {worst:.3f}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
