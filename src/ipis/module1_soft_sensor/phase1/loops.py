"""Calibration loops of N1 Phase 1 and their replay tuning (pre-registration Section 5.3).

Loops (Section 5.3; the sequential loop is primary):
- sequential, projected, phase and smith: ``delayed_aci.run_delayed_aci`` unchanged; the
  projected loop clips the level to [0.01, 0.5];
- decaying: the sequential update with the decaying step size of Angelopoulos, Barber and Bates
  (2024), gamma_n = c n^(-1/2 - eps0) with eps0 = 0.1, n the number of labels the loop has received
  in the run (checked on 2026-10-29 in the paper's body: Sec. 1.1, "eta_t proportional to
  t^(-1/2-epsilon), for some small epsilon in (0, 1/2)"; Sec. 4, "eta_t = t^(-1/2-epsilon) with
  epsilon = 0.1"). The paper's update moves a threshold in score space; here, as for every loop
  of Section 5.3, it moves the level of the conformal window. The constant c is tuned by the
  same replay as every loop ("Every loop is tuned by the same replay");
- none: static split conformal, the conformal quantile at 1 - alpha of the run's calibration
  scores, calibrated once (the loop-off arm of R4.9).

Tuning (Section 5.3): the grid of ``delayed_aci.TUNING_GRID``, searched upward and capped at
0.8 gamma_crit(theta); the largest value below the first one whose replayed uninformative share
exceeds the target; 0.001, flagged infeasible, if even that exceeds it. The first ``window`` rows
of each calibration segment seed the window and are not replayed; every replayed step counts.
Segments of a plant are pooled. ``replay_tune`` reproduces ``delayed_aci.replay_tune_pooled``
for the loops that function serves (checked in the tests) and adds the projected bounds and the
decaying loop, which it cannot run.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from ipis.module1_soft_sensor.evaluation import delayed_aci as d
from ipis.module1_soft_sensor.evaluation.conformal import conformal_quantile

LOOPS = ("sequential", "projected", "phase", "smith", "decaying", "none")
PROJECTED_BOUNDS = (0.01, 0.5)
DECAY_EPS = 0.1  # Angelopoulos, Barber and Bates (2024), Sec. 4: eta_t = t^(-1/2 - 0.1)


def run_decaying(
    scores: np.ndarray,
    theta: int,
    *,
    init_scores: np.ndarray,
    alpha: float,
    c: float,
    window: int,
    pairing: str = "stored",
    exponent: float = 0.5 + DECAY_EPS,
) -> dict[str, np.ndarray]:
    """The sequential loop of ``run_delayed_aci`` with the step c n^-exponent for the n-th label
    received. With exponent 0 it is the sequential loop at gamma = c (checked in the tests)."""
    if pairing not in d.PAIRINGS:
        raise ValueError(f"pairing in {d.PAIRINGS}")
    s = np.asarray(scores, dtype=np.float64)
    T = s.size
    win = deque(np.abs(np.asarray(init_scores, dtype=np.float64)).tolist(), maxlen=window)
    if not win:
        raise ValueError("init_scores must seed the window")
    arrivals: dict[int, list[int]] = {}
    for i in range(T):
        if i + theta < T:
            arrivals.setdefault(i + theta, []).append(i)
    h = np.empty(T)
    used = np.empty(T)
    covered = np.empty(T, dtype=bool)
    fed = np.full(T, np.nan)
    a, n = float(alpha), 0
    for t in range(T):
        h[t] = conformal_quantile(np.asarray(win), 1.0 - a)
        used[t], covered[t] = a, s[t] <= h[t]
        for i in arrivals.get(t, ()):
            e = float(s[i] > (h[i] if pairing == "stored" else h[t]))
            fed[i] = e
            n += 1
            a += c * n ** (-exponent) * (alpha - e)
            win.append(s[i])
    return {"h": h, "covered": covered, "alpha": used, "fed": fed}


def run_static(cal_scores: np.ndarray, scores: np.ndarray, alpha: float) -> dict[str, np.ndarray]:
    """Split conformal calibrated once on ``cal_scores``: one half-width for every step."""
    q = conformal_quantile(np.asarray(cal_scores, dtype=np.float64), 1.0 - alpha)
    s = np.asarray(scores, dtype=np.float64)
    h = np.full(s.size, q)
    return {
        "h": h,
        "covered": s <= h,
        "alpha": np.full(s.size, alpha),
        "fed": np.full(s.size, np.nan),
    }


def run_loop(
    scores: np.ndarray,
    theta: int,
    *,
    loop: str,
    init_scores: np.ndarray,
    gamma: float,
    alpha: float,
    window: int,
    pairing: str = "stored",
) -> dict[str, np.ndarray]:
    """One delayed calibration loop over ``scores`` (``loop`` of ``LOOPS`` other than 'none')."""
    if loop == "decaying":
        return run_decaying(
            scores,
            theta,
            init_scores=init_scores,
            alpha=alpha,
            c=gamma,
            window=window,
            pairing=pairing,
        )
    if loop not in d.LOOPS:
        raise ValueError(f"loop in {LOOPS[:-1]}")
    bounds = PROJECTED_BOUNDS if loop == "projected" else (0.0, 1.0)
    return d.run_delayed_aci(
        scores,
        theta,
        init_scores=init_scores,
        alpha=alpha,
        gamma=gamma,
        window=window,
        loop=loop,
        pairing=pairing,
        bounds=bounds,
    )


def replay_tune(
    segments: Sequence[tuple[np.ndarray, np.ndarray]],
    theta: int,
    *,
    loop: str,
    y_range: float,
    eps: float,
    alpha: float,
    window: int,
    grid: tuple[float, ...] = d.TUNING_GRID,
    runner: Callable[..., dict[str, np.ndarray]] = run_loop,
) -> dict[str, Any]:
    """Replay tuning of Section 5.3 for any loop of ``LOOPS`` except 'none'.

    ``segments``: (replayed scores, seed scores) per calibration segment. Returns the step size,
    whether it is feasible, the replay path [(gamma, pooled uninformative share)] and the cap.
    """
    cap = 0.8 * d.gamma_crit(theta)
    path: list[tuple[float, float]] = []
    chosen, feasible = None, True
    for g in grid:
        if g >= cap:
            break
        flags = []
        for scores, init_scores in segments:
            res = runner(
                scores,
                theta,
                loop=loop,
                init_scores=init_scores,
                gamma=g,
                alpha=alpha,
                window=window,
            )
            flags.append(d.uninformative(res["h"], y_range))
        share = float(np.mean(np.concatenate(flags)))
        path.append((float(g), share))
        if share > eps:
            break
        chosen = float(g)
    if chosen is None:
        chosen, feasible = float(grid[0]), False
    return {"gamma": chosen, "feasible": feasible, "path": path, "cap": cap}
