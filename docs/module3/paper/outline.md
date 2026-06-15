# Paper 2 outline (Module 3 — RTO)

> Companion to Paper 1 (Module 1 soft sensor, submitted CACE-D-26-00944). Paper 2
> is a single sharp contribution, not a five-part framework — keep it tight.

**Working title (primary, selected):**
*The conformal selection effect in real-time optimisation: why marginally valid
back-offs over-violate and conditional calibration restores safety*

Alternates:
- *When conformal prediction is unsafe for real-time optimisation: the constraint
  selection effect and a conditionally-calibrated remedy*
- *Conditional validity is necessary for conformal constraint back-offs in real-time
  optimisation: evidence from a distillation twin*
- *Distribution-free constraint back-offs for real-time distillation optimisation
  under an unmeasured feed disturbance*

**Venue (RECOMMENDATION — your call):** **Journal of Process Control** (primary);
Computers & Chemical Engineering (fallback). Reasoning: the contribution is a
constraint-violation-control result inside an optimization loop — a control/safety
result more than a computational-methods one; the selection effect is a
feedback-flavored phenomenon JPC readers will value; the closest prior art (del
Río Chanona 2021; Marchetti modifier-adaptation) sits in JPC; and diversifying
venues across the two papers reduces self-overlap. CACE remains a clean fit (PSE
scope, optimization-under-uncertainty, the rigorous twin) and was Paper 1's home,
so continuity is the argument the other way. Structure below is ~90% venue-
independent; CACE would only shift emphasis (more computational framing, elsarticle
template either way).

**Format:** markdown drafts in `docs/module3/paper/sections/`, LaTeX (elsarticle)
as a late sub-phase. Target **~8,000–10,000 words + 6–7 figures + 2–3 tables**
(tighter than Paper 1's 9–11k/8/3).

---

## Contribution statement (the paragraph reviewers quote back)

Real-time optimization (RTO) drives a process toward a quality constraint it cannot
measure directly, so it must subtract a back-off — a safety margin — from the spec.
Conformal prediction is the natural distribution-free way to size that back-off from
data. We show that this natural choice is unsafe. An RTO that optimizes against a
marginally-valid conformal back-off — even a locally adaptive one — is itself a
selection mechanism: it drives the operating point to exactly where the margin
under-covers the *conditional* constraint quantile, so the realized constraint-
violation rate reaches roughly five times the nominal level across the entire
disturbance range. We identify this as the conformal selection effect — the loss of
marginal validity under optimization — demonstrate it on a rigorous DWSIM
debutanizer twin over a swept feed-composition disturbance, and verify against an
oracle that the underlying chance-constraint machinery is correct. Restoring safety
requires *conditional* validity: a conformalized-quantile-regression back-off plus
an a-posteriori calibration step at the selected setpoint returns the realized
violation to the oracle (true-conditional-quantile) level at near-oracle profit,
over the operationally realistic disturbance range, degrading only when the
conditional estimate runs out of calibration data at disturbances several times
larger than realistic. The negative result is the contribution's spine: it
identifies a failure mode that the direct application of conformal prediction to
optimization invites, and supplies the minimal calibration that closes it.

## Numbered contributions

- **R1 — The conformal selection effect in RTO (the finding).** A marginally-valid
  conformal back-off (fixed *or* normalized/adaptive) loses its coverage guarantee
  under optimization; realized violation ≈0.43–0.50 vs a 0.10 target (~5×) across
  the swept disturbance, while an oracle conditional back-off holds ≈α — confirming
  the failure is the selection effect, not a broken formulation. [regime map, all σ_z]
- **R2 — Conditional calibration restores violation control (the fix).** A
  conformalized-quantile-regression (CQR) back-off plus a CPP a-posteriori
  tightening step at the selected setpoint tracks the oracle (violation within
  ≈0.01) at near-oracle profit for disturbances up to ≈3× realistic. [cqr+apost row]
- **R3 — A disturbance-magnitude regime map (the characterization).** Where each
  back-off controls violation, where the constant margin becomes infeasible, and
  where even the conditional method runs out of calibration data (the a-posteriori
  inflation κ climbing from ≈1.5 to ≈5.8). The robust headline is *violation
  control*: at realistic disturbance every method's profit is within 0.5% of the
  deterministic optimum, so the contribution is calibrated safety, not profit. [full table]

Supporting methodology (not headline claims): a PR DWSIM debutanizer twin with a
leave-one-disturbance-out-validated GP truth surface (R²≈0.92), and honest precision
accounting — violation rates reported with a Monte-Carlo band and a truth-surface
precision floor.

## Positioning (the novelty wedge) — refresh of literature-3b.md

- **del Río Chanona et al. 2021 (closest prior art).** GP-posterior variance
  tightens joint chance constraints under plant–model mismatch. Wedge: their
  Gaussian posterior is *marginally* calibrated in the same sense ours is — the
  selection-effect critique applies to any marginally-calibrated tightening,
  including theirs — and we replace it with a distribution-free, finite-sample
  conditional back-off plus the a-posteriori guarantee.
- **CPP / Lindemann et al. (conformal predictive programming).** Provides the
  a-posteriori calibration idea for chance-constrained programs. Wedge: we surface
  the *selection effect* as the reason that step is necessary in RTO, demonstrate it
  on a process, and make conditional validity (CQR) the load-bearing ingredient
  rather than only the a-posteriori patch.
- **Gibbs, Cherian & Candès (conditional coverage).** The theory of why marginal ≠
  conditional. Wedge: we instantiate it as a control-relevant failure (RTO
  constraint violation) and quantify it on a real process.
- **Modifier adaptation (Marchetti, Chachuat, François–Bonvin) + chance-constrained
  ChemE (Li, Arellano-Garcia & Wozny 2008).** The RTO-under-uncertainty tradition.
  Wedge: the back-off is a calibrated, distribution-free interval, not a model-
  gradient modifier or a Gaussian-assumption chance constraint.

Gap sentence: *no existing treatment surfaces the optimizer-induced selection effect
on conformal constraint back-offs in RTO, nor the conditional calibration that
closes it.*

---

## Section map (targets; evidence keys → claims_evidence.md, to be written next)

1. **Introduction** (~900 w) — RTO must back off an unmeasured constraint; conformal
   is the natural tool; the surprising failure under optimization; R1–R3; paper map.
   *Write last.*
2. **Related work** (~1,100 w) — three threads (RTO-under-uncertainty + modifier
   adaptation + chance-constrained ChemE; GP/Bayesian constraint tightening, del Río
   Chanona; conformal prediction — split/normalized/CQR/conditional coverage/CPP/
   beyond-exchangeability). The gap sentence above.
3. **Problem formulation & methods** (~2,500 w) — 3.1 chance-constrained RTO over an
   unmeasured feed-z disturbance; the oracle (monotone-in-z conditional quantile).
   3.2 conformal back-offs: fixed, normalized (baseline), CQR (conditional). 3.3 the
   selection effect — why marginal validity fails under argmax (the conceptual core;
   conditional-coverage argument). 3.4 CPP a-posteriori calibration at the selected
   setpoint (κ-search, feasibility window, held-out validation/test draws). 3.5 the
   DWSIM twin, GP surrogates, economics anchor.
4. **Case-study design** (~700 w) — binary nC4/nC6 debutanizer, PR, 9 stages; the
   feed-z campaign; truncnorm disturbance with the realistic σ_z≈0.006 anchor; spec
   xB≤0.02, α=0.10; metrics (realized violation primary, profit secondary); the
   physical infeasibility limit (spec unreachable for z≳0.38).
5. **Results** (~2,200 w) — 5.1 the selection effect (headline figure F3); 5.2 the
   oracle confirms the framework; 5.3 the conditional fix tracks the oracle (regime
   map, T1); 5.4 the κ-climb / data-starvation at large σ_z; 5.5 profit is muted
   (safety not profit); 5.6 surrogate validation + precision accounting.
6. **Discussion** (~1,100 w) — the selection effect as a general caution for
   conformal-in-the-loop; conditional validity as the requirement; limitations
   plainly (simulation twin, single binary system, MC band, oracle needs the truth,
   data-starvation at large σ_z, muted profit); bridges to closed-loop feedback (3C)
   and plant data as future work; relation to the Paper 1 soft-sensor framework
   without over-claiming the sensor integration.
7. **Conclusion** (~350 w).
Appendices: A — reproducibility (seed 20260614, the regime-map script, unit tests,
CI scope); B — ADR-014 → section mapping.

## Figure & table inventory (scripts under `scripts/paper2_figures/`; single entry point)

- **F1** Chance-constrained RTO schematic: decision (R,D) → twin → unmeasured xB →
  conformal back-off → tightened constraint. Conceptual.
- **F2** Debutanizer twin schematic: column, streams, sensor stage, the feed-z
  disturbance entering the feed.
- **F3 (headline)** Realized violation vs σ_z for the four methods (oracle,
  CQR+a-posteriori, naive-fixed, naive-adaptive), α target line + MC band. The
  selection-effect figure.
- **F4 (the "why")** Back-off field heatmaps C(R,D) for naive-adaptive vs CQR, with
  each method's selected optimum overlaid — shows *where* the optimizer exploits the
  marginal-vs-conditional gap.
- **F5** Profit vs σ_z at controlled violation, with the fixed-margin infeasibility
  onset — the muted-profit / safety-not-profit point.
- **F6** Surrogate leave-z-out validation (predicted vs actual xB at held-out
  z=0.375) and the monotone xB(R,D,z) response.
- **F7 (optional)** a-posteriori inflation κ vs σ_z (the data-starvation signature).
- **T1** The regime map table (canonical numbers from results.md).
- **T2** Twin specification + economics anchors.
- **T3 (optional)** Back-off method definitions (one-line each).

---

## OPEN FORKS (need your call before section drafting)

1. **Venue:** JPC (recommended) vs CACE. Affects emphasis/template only.
2. **Framing:** negative-result hook (selection effect) + conditional fix + regime
   map (recommended). Confirm, or steer toward a pure method-paper framing.
3. **Scope:** Paper 2 = the 3B static chance-constrained RTO result, standalone, with
   3C (closed-loop feedback) as future work (recommended). Confirm.
4. **Title:** primary above, or pick/revise an alternate.

Next artifacts after sign-off: `claims_evidence.md` (every claim → script/result, Paper-1
style), then sections drafted in dependency order (3 methods → 4 design → 5 results →
2 related work → 6 discussion → 1 intro → 0 abstract → 7 conclusion).
