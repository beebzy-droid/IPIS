# Claims-to-evidence table (Paper 2 — Module 3 RTO)

Audit rule: a claim enters the paper only if this table maps it to a number in
`docs/module3/results.md` (canonical run on the committed twin data), a runnable
artifact, and (where visual) a figure with a source script. **Gap** column = what
must exist before the claim is submittable.

Status legend: ✅ evidence + artifact in repo | 🟡 evidence in repo, figure/script
missing | 🔴 claim needs new measurement or must be cut.

| # | Claim (paper wording, condensed) | Evidence (numbers, canonical run) | Artifact | Figure (planned) | ADR | Status / gap |
|---|---|---|---|---|---|---|
| C1 | The conformal **selection effect**: a marginally-valid back-off (fixed *or* normalized/adaptive) loses its coverage guarantee under RTO optimization | naive-adaptive realized violation 0.43–0.50 vs 0.10 target (~5×) across σ_z; naive-fixed 0.17–0.19 then INFEASIBLE ≥0.015 (results §3B regime map) | `module3_rto/chance_rto.py` (`normalized_backoff`,`fixed_backoff`,`solve_chance_rto`), `scripts/run_3b3_regime_map.py` | F3 (violation vs σ_z, 4 methods) | 014 | 🟡 numbers frozen-able; F3 script to write |
| C2 | An **oracle** conditional back-off realizes ≈α by construction, confirming the chance-constraint machinery is correct (the failure in C1 is selection, not a broken formulation) | oracle realized violation 0.079–0.106 across all σ_z (results §3B) | `chance_rto.py::oracle_backoff` (monotone-in-z quantile shortcut) | F3 | 014 | ✅ (carried by F3) |
| C3 | **Conditional calibration restores control**: CQR + CPP a-posteriori tracks the oracle (violation within ≈0.01) at near-oracle profit, σ_z up to ≈3× realistic | cqr+apost 0.063–0.105, profit within a few $/h of oracle, σ_z≤0.020; infeasible only at 0.025 (results §3B) | `chance_rto.py::cqr_backoff`,`aposteriori_tighten` | F3, F5 | 014 | 🟡 figures to write |
| C4 | **The mechanism**: the optimizer selects toward operating points where the marginal back-off under-covers the conditional quantile; the conditional back-off removes the exploitable gap | naive-adapt optimum R≈2.83/D≈33.7 (low-D corner, small σ̂); oracle/CQR at higher D (34.3–36.6) as σ_z grows (results §3B R*/D* columns) | `chance_rto.py` back-off fields | F4 (back-off heatmaps C(R,D) + selected optima) | 014 | 🟡 F4 script to write |
| C5 | **Data-starvation boundary**: even the conditional method runs out of calibration data as the disturbance widens — the a-posteriori inflation κ climbs and eventually no feasible-compliant κ exists | κ 1.0–1.5 (σ_z≤0.010) → 5.78 (σ_z=0.015) → infeasible (0.025); n_cal scaled with σ_z (results §3B) | `aposteriori_tighten`; n_cal scaling in `run_3b3_regime_map.py` | F7 (κ vs σ_z, optional) | 014 | 🟡 optional figure |
| C6 | **Safety, not profit**: at realistic disturbance the chance constraint is barely active — every method is within 0.5% of the deterministic optimum, so the contribution is calibrated violation control | profit spread <0.5% (all ~$5374–5394) vs deterministic ~$5393 at σ_z=0.006 (results §3B) | `run_3b3_regime_map.py`, `economics.py` | F5 (profit vs σ_z) | 014 | 🟡 figure to write |
| C7 | **Validated rigorous twin**: PR DWSIM debutanizer; GP truth surface interpolates the disturbance (leave-one-z-out) | leave-z=0.375-out R²=0.917, MAE 0.0053 (n=15) (results §3B audit-F) | `surrogate.py::fit_truth_surface_3d`, `run_3b3_regime_map.py::_leave_z_out_r2` | F2 (twin schematic), F6 (validation scatter) | 013, 014 | 🟡 figures to write |
| C8 | **Physical infeasibility limit**: the spec is unachievable for z≳0.38 within the D-bounds (distillate-flow limited), so the operational disturbance must be tight — consistent with the σ_z≈0.006 anchor | min xB at z=0.40 is ~0.048 > spec 0.02; 9.2× monotone xB–z response confirms z propagation (results §3B; campaign integrity scan) | feed-z campaign CSV; `run_zvaried_sweep.py` | — (textual / T2 note) | 013 | ✅ (textual) |
| C9 | **Honest precision accounting**: realized violation rates are Monte-Carlo estimates with a ±0.01–0.02 cross-platform band; the truth-surface MAE (~0.005 xB) is the precision floor on any violation number | sandbox vs canonical run differ ≤0.02 on viol; oracle at 0.08–0.11 not exactly 0.10 reflects the MAE floor (results §3B note) | seeded `run_3b3_regime_map.py` (SEED=20260614) | — (textual) | 014 | 🟡 optional: quantify band via multi-seed std |

## Cross-cutting gaps (must clear before submission)

1. **Frozen evidence + figure scripts.** The canonical regime-map numbers live in
   `results.md` from Bien's run on the committed twin data. To render figures
   deterministically (and match Paper 1's frozen-evidence pattern,
   `efficiency_tep.json`), add a `--save-json` flag to `run_3b3_regime_map.py` that
   writes `docs/module3/paper/evidence/regime_map.json`, then build
   `scripts/paper2_figures/` (F3–F7) to render from that JSON. F1/F2 are schematics
   (drawn, not data-rendered). **Status: JSON freeze + 5 figure scripts to write.**
2. **Monte-Carlo band (C9).** Optional hardening: run the regime map under a few
   seeds to report the violation-rate std, turning "±0.01–0.02" from an estimate into
   a measured band. Not blocking; strengthens the honesty claim.
3. **References.** del Río Chanona 2021 (JPC); Lindemann CPP; Romano-Patterson-Candès
   CQR; Gibbs-Cherian-Candès conditional coverage; Marchetti-Chachuat-Bonvin modifier
   adaptation; Li-Arellano-Garcia-Wozny 2008 chance-constrained; Lei et al. normalized
   conformal; Barber beyond-exchangeability; Fortuna et al. 2007 (Debutanizer);
   Downs & Vogel / Bathelt (TEP — only if the twin lineage is cited); DWSIM (Medeiros).
   Most are in the project PDF set; assemble `references.md`. **Status: to assemble.**
4. **Profit-as-secondary framing.** Guardrail, not a gap: every results/abstract
   mention of profit must be subordinate to violation control (C6). Do **not** phrase
   any result as a profit win.
5. **Reproducibility statement.** Repo private; decide public release vs
   "available on request" at submission (inherited from Paper 1).
