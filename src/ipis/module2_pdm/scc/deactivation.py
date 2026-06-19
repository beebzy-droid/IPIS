"""Stochastic catalyst-deactivation simulator for Similarity-Calibrated Conformal (SCC).

A controlled physical testbed where dynamic similitude is *genuine* (not assumed by
the estimator), used to validate the SCC coverage certificate non-circularly.

Physics (Levenspiel, *Chemical Reaction Engineering*; Perry's 8th/9th Sec. 7):
first-order catalyst deactivation of activity ``a`` (a(0)=1, failure at ``a<=A_FAIL``)

    da/dt = -k_eff(T) a,     a(t) = exp(-k_eff(T) t),

with an Arrhenius primary channel ``k1(T) = A1 exp(-E1/RT)`` and an optional secondary
channel ``k2(T) = A2 exp(-E2/RT)`` of weight ``eta`` (the *controlled departure* from
single-group similitude; active only when ``E2 != E1`` and ``eta > 0``). Unit-to-unit
variability enters as a lognormal pre-exponential ``A1`` (aleatoric); the monitored
signal carries additive measurement noise.

Under ``eta = 0`` the dimensionless clock ``tau = t * k1(T)`` yields the universal
curve ``a(tau) = exp(-tau)`` for *every* temperature: exact dynamic similitude. The
characteristic life scale is ``T_L(T) = 1 / k1(T)``; conditions differ only through it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

R = 8.314  # universal gas constant, J/(mol K)
A_FAIL = 0.30  # activity at end of life


@dataclass(frozen=True)
class DeactivationRun:
    """A single run-to-failure trajectory under one operating condition."""

    temperature: float  # K
    t: np.ndarray  # time grid, s
    a_obs: np.ndarray  # observed (noisy) activity
    a_true: np.ndarray  # noise-free activity
    life: float  # time to a = A_FAIL, s
    k_eff: float  # effective deactivation rate, 1/s


def effective_rate(
    temperature: float, a1: float, e1: float, a2: float, e2: float, eta: float
) -> float:
    """Effective first-order deactivation rate k_eff(T) = k1 + eta*k2 (Arrhenius)."""
    k1 = a1 * np.exp(-e1 / (R * temperature))
    k2 = a2 * np.exp(-e2 / (R * temperature)) if eta > 0 else 0.0
    return float(k1 + eta * k2)


def life_at(
    temperature: float, a1: float, e1: float, a2: float = 0.0, e2: float = 0.0, eta: float = 0.0
) -> tuple[float, float]:
    """Return (life, k_eff): time to a=A_FAIL for a(t)=exp(-k_eff t)."""
    k_eff = effective_rate(temperature, a1, e1, a2, e2, eta)
    life = float(np.log(1.0 / A_FAIL) / k_eff)
    return life, k_eff


def simulate_condition(
    temperature: float,
    n_units: int,
    a1_nom: float,
    e1: float,
    *,
    sigma_lna: float = 0.25,
    noise: float = 0.02,
    a2: float = 0.0,
    e2: float = 0.0,
    eta: float = 0.0,
    dt_frac: float = 0.01,
    seed: int = 0,
) -> list[DeactivationRun]:
    """Simulate ``n_units`` run-to-failure trajectories at one temperature.

    Unit variability is a lognormal multiplier on the pre-exponential ``a1_nom``
    (geometric sigma ``sigma_lna``); ``noise`` is additive Gaussian on the activity
    signal. ``a2, e2, eta`` activate the unmodeled secondary channel.
    """
    rng = np.random.default_rng(seed)
    runs: list[DeactivationRun] = []
    for _ in range(n_units):
        a1 = a1_nom * np.exp(rng.normal(0.0, sigma_lna))
        life, k_eff = life_at(temperature, a1, e1, a2, e2, eta)
        dt = life * dt_frac
        t = np.arange(0.0, life * 1.05, dt)
        a_true = np.exp(-k_eff * t)
        a_obs = np.clip(a_true + rng.normal(0.0, noise, t.shape), 1e-3, 1.2)
        runs.append(DeactivationRun(temperature, t, a_obs, a_true, life, k_eff))
    return runs
