# ADR 001 — Path B PINN Strategy (Residual Hybrid, Not Pure PINN)

**Status:** Accepted
**Date:** 2026-05-28
**Decision owner:** Bien Busico

## Context

For the Module 1 soft sensor, the question was whether to use:

- **Path A** — a pure Physics-Informed Neural Network (PINN) where the network learns the entire mapping with physics encoded as a loss penalty
- **Path B** — a residual hybrid model where a first-principles model produces a baseline prediction, and an ML model with physics-loss regularization learns only the residual

Both approaches embed physics into the model. They differ in *how much* the ML component is asked to do.

## Decision

**Use Path B for Module 1.**

The first-principles model (DWSIM Debutanizer column, analytical fallback) produces ŷ_physics. A neural network with physics-informed loss terms learns the residual r = y_true − ŷ_physics. Final prediction is ŷ_hybrid = ŷ_physics + ŷ_ML.

If the physics-loss term destabilizes training, λ_physics → 0 and the model degrades gracefully to a standard ML residual learner (Von Stosch hybrid baseline). The model ships either way.

## Rationale

### Why Path B over Path A

1. **PINN convergence is notoriously unstable.** Loss balancing between data and physics terms is an open research problem. Multiple published PINN papers do not reproduce.
2. **Stiff dynamics break PINNs.** Process systems mix fast (reactions) and slow (accumulation) timescales. Standard PINNs choke on stiff ODEs/PDEs.
3. **Residual hybrid is the established applied baseline.** Von Stosch et al. (2014) hybrid modeling is the standard reference. Recent PINN-for-soft-sensor papers (2023–2025) frequently fall back to grey-box / residual formulations in practice.
4. **Smaller learning problem.** ML only learns model mismatch (unmeasured disturbances, parameter drift), not the full input-output mapping. Less data needed, better generalization.
5. **Diagnostic information for Path A later.** Path B output (residual magnitude, error structure, physics-loss behavior in isolation) is exactly what's needed to set up Path A correctly in future work.

### What Path A would have required

- Solving PINN loss balancing (NTK-PINN, SA-PINN, or extensive hyperparameter sweeps)
- Custom collocation point sampling strategies
- 2–3x longer development time per dataset
- High risk of "doesn't converge, project blocked"

## Consequences

### Positive

- Lower technical risk on the critical path
- Graceful fallback to standard ML residual learner if PINN regularization fails
- Reusable architecture pattern for Module 2 (PdM) and Module 3 (RTO surrogate)
- Generates diagnostic data for a potential Path A follow-up paper

### Negative

- Less algorithmically novel than a successful pure PINN
- Two models to maintain (first-principles + residual learner) instead of one
- First-principles model quality bottlenecks overall accuracy

### Neutral

- Path A is retained as private future work, not externally promised. After Module 1 ships, Path A becomes a potential follow-up paper *using* Path B's diagnostic outputs.

## Revisit triggers

This decision will be revisited if:

- Path B residual learner consistently fails to improve on pure ML baseline (suggests physics model is wrong and Path A wouldn't help either)
- A breakthrough in PINN training stability (e.g., a new optimizer or architecture) makes Path A's risk profile comparable to Path B
- Module 1 ships and a publishable follow-up requires the algorithmic novelty of pure PINN

## References

- Von Stosch et al. (2014), "Hybrid semi-parametric modeling in process systems engineering," *Computers & Chemical Engineering*.
- Raissi et al. (2019), "Physics-informed neural networks," *Journal of Computational Physics*.
- CPINN-AIC (2023) — PDE discovery for soft sensors.
- Perera et al. (2025), "Machine learning enhanced grey box soft sensor for melt viscosity prediction in polymer extrusion," *Scientific Reports*.
