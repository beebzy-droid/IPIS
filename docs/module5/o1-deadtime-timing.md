# O1 under deadtime — causal timing and the selection penalty

This is the Module 5 re-verification of open item O1 (the M4 selection-penalty argument)
under analyzer/lab deadtime. Result: deadtime preserves `Delta_sel = 0`; its cost moves
into the ACI coverage *rate*, not the certificate's *validity*. Confirmed empirically.

## Setup

One decision cycle `k`: the setpoint `u_k = (R_k, D_k)` is computed at the end of cycle
`k-1`, held across the RTO interval (`steps_per_cycle` plant steps), and the realized
end-of-cycle truth `x_k` (with noise `eps_k`) follows. The lab/analyzer reports the quality
for cycle `k` only `D_a` DECISION cycles later, where `D_a = ceil(analyzer_delay / RTO_interval)`.
That delayed label is what drives the ACI miscoverage update.

```
cycle:        k-D_a-1     ...        k-1          k          k+1   ...   k+D_a
              -----------------------------------------------------------------
decision u:                          u_{k}        u_{k+1}
realize x:                                         x_k  (eps_k)
M1 interval:                                        C_k = [yhat_k +/- q(alpha_t^(k))]
label for k:                                        (emitted)  ------------>  applied here
ACI uses:     s_{k-D_a-1} is the NEWEST score available when C_k is formed
```

`alpha_t^(k)` (the ACI level used to form `C_k`) reflects every label applied through the
end of cycle `k-1`. A label for cycle `j` is applied at cycle `j + D_a`. Hence the scores
influencing `alpha_t^(k)` are exactly `{ s_j : j <= k - 1 - D_a }`.

## Claim: Delta_sel = 0 is preserved

`C_k` is a deterministic function of `alpha_t^(k)`, which depends only on
`{ s_j : j <= k - 1 - D_a }`. For any `D_a >= 0` this set excludes `s_k` (and `x_k`, `eps_k`):

    k  >  k - 1 - D_a    for all D_a >= 0.

So the cycle-`k` interval `C_k` is formed WITHOUT reference to cycle-`k`'s own outcome.
Combined with the M4 causal-timing property — `u_k` is fixed before `eps_k`, so `u_k` is
independent of `eps_k` given the regime (`docs/module4/formalization-spike.md` §4) — the
quantity selected at cycle `k` does not condition on the realization it is scored against.
The conformal selection penalty therefore vanishes:

    Delta_sel = 0,

and the per-cycle composed SCC certificate (M4 Theorem 1) applies cycle by cycle exactly as
in the quasi-static case. Deadtime does not re-open the co-selection window.

What deadtime DOES change: `alpha_t^(k)` is built from scores no newer than `k - 1 - D_a`,
i.e. it is STALE by `D_a` cycles relative to the no-delay case (`j <= k - 1`). This is the
standard delayed-feedback ACI regime.

## Where the cost goes: the coverage rate, not validity

ACI's long-run coverage guarantee (Gibbs & Candes 2021) bounds the time-averaged miscoverage
`|(1/T) sum_t (alpha - err_t)|` by an `O(1 / (gamma T))` term that is INDEPENDENT of the
data-generating dependence. Delayed feedback re-indexes the `err_t` stream by `D_a`; the same
telescoping/averaging argument leaves the long-run average coverage at the target up to an
additive `O(D_a / T)` boundary term that vanishes as `T -> infinity`. So:

  * long-run / horizon coverage: HOLDS (validity), and
  * the finite-horizon deviation carries a transient that grows with `D_a` (the rate).

The full deadtime sweep (coverage vs `D_a`, demonstrating graceful degradation of the
transient) is increment 2b.

## Empirical confirmation (increment 2a)

In-sandbox dynamic loop (`tests/unit/test_dynamic_orchestrator.py`), `D_a = 2` decision
cycles of label delay, analyzer deadtime ~5 min within the cycle, `tau_proc ~ 30 min`,
`alpha_1 = alpha_2 = 0.10`, `eps = 0.05` (certified floor `0.75`):

  * M1 ACI interval coverage of `x_k` over a 400-cycle campaign: **0.900** (target
    `1 - alpha_1 = 0.90`) — coverage maintained on target despite the delay and the
    feedback-induced dependence; `alpha_t` stays bounded (range ~[0.05, 0.37], no divergence).
  * joint event `S_k = {x_k <= x_spec} and {rho_k >= rho_min}` over a 3 x 120-cycle sweep:
    coverage **1.000**, Wilson 95% CI lower bound **0.989** >= floor **0.750** — `meets_floor`.

The selection-free argument is therefore confirmed both analytically and in the running loop.
The remaining 2b work characterizes the rate (deadtime and gamma sweeps), not the validity.
