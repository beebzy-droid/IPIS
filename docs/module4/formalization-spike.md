# Formalization Spike — Composed Coverage for the IPIS Closed Loop

**Status:** Theory frozen for Paper 4 core. Build-blocking decisions resolved; open items flagged in §8.
**Scope of formal claim:** debutanizer / binary-key distillation (the dimensionless framework is the generalization vehicle, not a universal proof).
**Cross-refs:** Paper 1 / M1 (CACE-D-26-00944, soft sensor), Paper 2 / M2 (JRESS-D-26-04509, similarity-calibrated conformal prognostics), Paper 3 / M3 (JPROCONT-D-26-00565, conformal selection in RTO). ChemE grounding verified against Perry's 9th ed. (see `docs/module4/perry-verification.md`).

---

## 0. One-line result

A composed, per-cycle coverage certificate for the closed loop is **derivable as a theorem**, contains all three papers as distinct identifiable terms, and collapses into a single constraint added to the modifier-adaptation RTO NLP. The "feedback breaks exchangeability" risk is retired by a conditioning + causal-timing argument (§4). The honest limitation is Bonferroni conservatism (§7), a tightening lever, not a blocker.

---

## 1. The loop and the objects

At cycle `k`, the RTO sets decision `u_k = (R_k, D_k)` — reflux ratio and distillate rate (Module 3 variables). The plant (DWSIM twin under the unified-plant decision) yields tray temperatures `T_k` and a true, **unmeasured** quality `x_k` (C4 in bottoms). The reflux-pump health signal `h_k` corresponds to a true, unobserved `RUL_k = ρ_k`.

- **M1 (soft sensor):** conformal interval `Ĉ₁(T_k) = [x̂_k − w_k, x̂_k + w_k]`, nominal miscoverage `α₁`.
- **M2 (PdM):** one-sided lower bound `ρ_k^lo`, nominal miscoverage `α₂`, i.e. `P(ρ_k ≥ ρ_k^lo) ≥ 1 − α₂`.
- **M3 (RTO, modifier-adaptation):** `u_{k+1} = Π(x̂_k, ρ_k^lo, modifiers_k)`, enforcing the **surrogate** constraints
  - quality (backed off by the interval half-width): `x̂_k + w_k ≤ x^spec`
  - health floor (= next maintenance window): `ρ_k^lo ≥ ρ_min`

**System-safety event** (the quantity we actually certify):

```
S_k = { x_k ≤ x^spec }  ∩  { ρ_k ≥ ρ_min }.
```

The surrogate constraints act on *estimates*; safety is about *truths*. The bridge is coverage.

---

## 2. The similitude coordinate ψ (Perry's-verified)

The operating point lives in a dimensionless space spanned by three Perry's-confirmed quantities:

| Coordinate | Symbol | Perry's 9th |
|---|---|---|
| Relative volatility | `α(T)` | Eq. 13-33 (`α_i = K_i/K_r`) |
| Reflux (Gilliland coord.) | `Ψ_G = (R − R_min)/(R + 1)` | Eq. 13-30 (Molokanov fit), Fig. 13-29 |
| Stripping factor | `S = KV/L` | Eq. 13-44 (`A = L/KV`, `S = 1/A`) |

Let `σ` be the SCC characteristic scale (the normalizer that renders the *nominal* nonconformity-score distribution regime-invariant). The **residual similitude departure** is the part `σ` does not absorb:

```
Δψ₁,k = ψ₁(u_k) − ψ₁⋆        (M1, in normalized (α, R, S)-space; anchor ψ₁⋆ = Fortuna regime)
Δψ₂,k = ψ₂(u_k) − ψ₂⋆        (M2, in pump operating-condition space; anchor ψ₂⋆ = FEMTO conditions)
```

**The endogeneity link (why the RTO controls ψ).** Increasing `R = L/D` raises reflux flow `L`, which raises reflux-pump duty. The affinity laws (Perry's Table 10-13) give the operating-point → load map: `Q ∝ N`, `H ∝ N²`, `BHP ∝ N³`. Module 2's FEMTO-calibrated model gives the load → wear map. Their composition makes `ψ₂(u_k)` a function of the decision. Therefore **both** the separation departure (`Δψ₁`) and the degradation departure (`Δψ₂`) are functions of `u`, controlled by the optimizer. This is the structural fact Perry's secured: separation, efficiency, and pump degradation all live in one dimensionless / similitude framework, so ψ is built from standard coordinates, not invented ones.

---

## 3. Per-module SCC bound, applied per cycle

Within a cycle the regime is held fixed while the modules predict. The Paper-3 certificate therefore applies **conditionally on the cycle's own realized departure**:

```
P( x_k ∈ Ĉ₁(T_k) | Δψ₁,k )  ≥  1 − α₁ − 2·L₁·‖Δψ₁,k‖          (M1)
P( ρ_k ≥ ρ_k^lo   | Δψ₂,k )  ≥  1 − α₂ − 2·L₂·‖Δψ₂,k‖          (M2)
```

`L_j` is the Lipschitz constant of the score-quantile in ψ-space, estimated a priori from the calibration sweep (the robustness sweep in Paper 2 / M2 is the template; the M1 sweep is new — see open item O2).

**Connection to non-exchangeable conformal.** The term `2L‖Δψ‖` is a *structured, computable instance* of the Barber et al. (2023) non-exchangeability coverage gap, in which the abstract distributional distance is replaced by the physical similitude departure. SCC's contribution is making that distance computable a priori from physical parameters.

---

## 4. Why feedback does **not** break the certificate

`u_{k+1}` is a function of `(x̂_k, ρ_k^lo)`, so `{Δψ_j,k}` is an **endogenous, dependent, controlled** process, and the cycle-`k` test point is **not exchangeable** with the offline calibration set. Two-part resolution:

**(a) Conditioning.** The per-cycle bounds in §3 are conditional on `Δψ_j,k` and *agnostic to the mechanism* that produced the regime. Endogeneity makes `Δψ_j,k` random; it does not invalidate a statement already conditioned on it.

**(b) Causal timing.** Under standard two-step RTO timing — `u_k` is computed from cycle-`(k−1)` information, applied, and *then* the cycle-`k` measurement noise `ε_k` is realized — `u_k` is `σ(F_{k−1})`-measurable while `ε_k ⊥ F_{k−1}`. Hence conditioning on `Δψ_k` (a function of `u_k`) leaves `ε_k` at its nominal regime-conditional distribution:

```
u_k ⊥ ε_k | Δψ_k    ⟹    Δ_sel,k = 0.
```

**Where Paper 3 lives.** The conformal selection penalty `Δ_sel,k` is the residual term that is **nonzero only in the other configuration**: when the RTO co-selects `u_k` on a quantity computed from the *same sample* used for the coverage check. This delineates exactly when each paper's effect is active — under realistic causal plant timing the selection term vanishes, while the framework still names and bounds it. (Verifying that the specific M3 modifier-adaptation variant respects causal timing is open item **O1**.)

---

## 5. The composed certificate (theorem)

On the RTO-enforced surrogate, each coverage event **implies** its safety half:

```
{ x_k ∈ Ĉ₁ }   ⟹   x_k ≤ x̂_k + w_k ≤ x^spec
{ ρ_k ≥ ρ_k^lo } ⟹   ρ_k ≥ ρ_k^lo ≥ ρ_min
```

Hence `S_k ⊇ E₁,k ∩ E₂,k`. Bonferroni on the two miscoverage events gives the **conditional certificate**:

```
P( S_k | Δψ₁,k, Δψ₂,k )
      ≥ 1 − (α₁ + α₂) − 2·( L₁‖Δψ₁,k‖ + L₂‖Δψ₂,k‖ ) − Δ_sel,k
```

with `Δ_sel,k = 0` under causal timing (§4). Marginalizing over the endogenous regime:

```
P( S_k ) ≥ 1 − (α₁ + α₂) − 2·( L₁·E‖Δψ₁,k‖ + L₂·E‖Δψ₂,k‖ ).
```

**This inequality is the unification.** Its terms map one-to-one onto the three papers:

| Term | Origin |
|---|---|
| `α₁` (base coverage of `Ĉ₁`) | **Paper 1** — physics-anchored soft-sensor conformal interval |
| `α₂` + the one-sided RUL bound | **Paper 2 / M2** — calibrated lower-bound RUL |
| `2·L_j·‖Δψ_j,k‖` (similitude departure) | **Paper 2** — SCC certificate `≤ 2L‖Δψ‖`, now per-module-per-cycle |
| `Δ_sel,k` (selection penalty) | **Paper 3** — conformal selection effect, active iff the RTO co-selects on the test residual |

None of the three papers can state this alone; the composition is the contribution.

---

## 6. Actionable corollary — the ψ-budget RTO constraint

Because `Δψ_j,k = ψ_j(u_k) − ψ_j⋆` is a **known function of the decision `u`**, the coverage penalty is *controllable*. Impose, inside the modifier-adaptation NLP:

```
2·( L₁‖ψ₁(u) − ψ₁⋆‖ + L₂‖ψ₂(u) − ψ₂⋆‖ )  ≤  ε
```

Then by construction `P(S_k) ≥ 1 − (α₁ + α₂) − ε`. The RTO maximizes economic profit **subject to staying inside the similitude-departure budget that certifies its own coverage** — formally: *do not optimize so aggressively that you invalidate your own soft sensor and your own RUL guarantee.*

This **is** "conformal health-constrained RTO" (the narrow-paper Hooks 1+2), now *derived* rather than asserted. It tells the build exactly what new term the NLP carries: a convex-in-ψ trust-region penalty whose radius `ε` is the chosen coverage budget. **The flagship result (§5) and the floor result (§6) share one implementation.**

---

## 7. Scope and tightness (honest)

1. **Bonferroni is conservative.** Always valid (it is a lower bound); tight only when M1 and M2 failures are disjoint. Extreme regimes plausibly co-stress both ⟹ positive failure-correlation ⟹ true coverage *exceeds* the bound. Tightening requires a joint-failure model (open item O4); adjacent line to cite, not collide with: conformal–scenario "modular risk allocation" (2026).
2. **`L₁, L₂` are empirical** but a-priori computable from the calibration sweep.
3. **Per-cycle marginal, not full conditional.** Conditional-on-`T_k` coverage is impossible in general (Vovk; Barber et al.); the project already operates under marginal coverage. A **horizon** guarantee over `K` cycles needs either a `K`-union bound (linear degradation) or **online conformal** (ACI; Gibbs & Candès 2021) for long-run coverage under arbitrary dependence. ACI is already in the M1 serving stack ⟹ state both: per-cycle via SCC composition, long-run via ACI.
4. **Formal claim scoped to distillation / the debutanizer.**

---

## 8. Open items (resolve before drafting, not before building)

| ID | Item | Type | Blocks |
|---|---|---|---|
| **O1** | Confirm the specific M3 modifier-adaptation variant forms `u_k` strictly before the cycle-`k` residual (else `Δ_sel,k ≠ 0` and Paper 3's term re-activates). | Pure analysis | Drafted-claim sharpness (§4) |
| **O2** | M1 Lipschitz sweep `L₁` in ψ-space (new; P2 did `L₂` for M2). | Sandbox sweep | Numeric bound in §3/§5 |
| **O3** | Re-pin twin tray efficiency against O'Connell Eq. 14-138 + Table 14-12 at actual `α(T)`, `μ_L(T)` (CoolProp-verified). Sets the theoretical↔actual stage map that M1 sensor-stage AND M2 pump-load both depend on. | Sandbox + DWSIM | Integration fidelity |
| **O4** | Joint M1/M2 failure-correlation model to tighten Bonferroni. | Future work / empirical | Bound tightness (§7.1) |

---

## 9. References

- Barber, Candès, Ramdas, Tibshirani (2023). Conformal prediction beyond exchangeability. *Ann. Statist.*
- Gibbs, Candès (2021). Adaptive conformal inference under distribution shift. *NeurIPS.*
- Angelopoulos, Bates, et al. Conformal risk control.
- Marchetti, Chachuat, Bonvin. Modifier-adaptation methodology for real-time optimization.
- Vovk, Gammerman, Shafer. Algorithmic Learning in a Random World.
- Perry's Chemical Engineers' Handbook, 9th ed. (Green & Southard): Eqs. 13-30, 13-31/32, 13-33, 13-37/38, 13-42/43/44, 14-138; Table 10-13; Table 14-12; Example 13-1.
- IPIS Papers 1–3 (internal): Paper 1 = CACE-D-26-00944 (M1, soft sensor), Paper 2 = JRESS-D-26-04509 (M2, similarity-calibrated conformal prognostics), Paper 3 = JPROCONT-D-26-00565 (M3, conformal selection in RTO).
