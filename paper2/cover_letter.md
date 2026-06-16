# Cover letter — Journal of Process Control

Dear Editor,

Please consider the enclosed manuscript, "The conformal selection effect in real-time
optimisation: why marginally valid back-offs over-violate and conditional calibration
restores safety," for publication in the *Journal of Process Control* as a research
article.

Real-time optimisation protects a quality constraint it cannot measure online by
subtracting a back-off from the specification, and conformal prediction is the natural
distribution-free way to size that margin from data. The manuscript shows that the
natural choice is unsafe. An optimiser pressing on a marginally valid conformal back-off,
even a locally adaptive one, behaves as a selection mechanism that drives the operating
point to where the margin under-covers the conditional constraint quantile; on a rigorous
Peng–Robinson debutaniser twin the realised violation rate reaches roughly five times the
nominal level across the disturbance range. The paper names this the conformal selection
effect, confirms against an oracle that the failure lies in the back-off and not in the
chance-constrained formulation, and shows that conditional validity is the structural
remedy: a conformalised-quantile-regression back-off with an a-posteriori calibration step
returns the realised violation to the oracle level at near-oracle profit over the
operationally realistic disturbance range. A regime map over disturbance magnitude bounds
where each margin controls violation and where the conditional estimate runs out of data, a
boundary its inflation factor signals in advance.

Two properties distinguish the contribution. First, it is framed as calibrated safety, not
profit: at a well-controlled feed the constraint is barely active and every method earns
within half a percent of the deterministic optimum, so the value of the proposed method is
the violation it removes, not any profit it adds. Second, the limits are stated as results,
not hedges, including the data-starvation boundary at which even the conditional method can
no longer certify the target. The mechanism is general: any conformal interval used as a
hard optimisation constraint is exposed to the same selection effect.

The manuscript is approximately 7,000 words with seven figures and one table. It is the
author's original work, is not under consideration elsewhere, and the sole author meets all
CRediT criteria. A companion paper developing the physics-informed soft sensor referenced
here is under review at *Computers & Chemical Engineering* (CACE-D-26-00944); the present
manuscript is self-contained. Every quantitative claim regenerates from a single fixed seed
against the public repository. Suggested reviewer expertise: real-time optimisation under
uncertainty, chance-constrained process optimisation, and conformal prediction in
optimisation and control.

Thank you for your consideration.

Bien Busico
Chemical Engineer, Quezon City, Philippines
bienbusico@gmail.com

---

Suggested reviewers (for the portal fields): Benoît Chachuat (Imperial College London) —
modifier adaptation and RTO under uncertainty; Ali Mesbah (UC Berkeley) — stochastic and
learning-based MPC; Victor M. Zavala (UW–Madison) — optimisation under uncertainty in PSE;
Lars Lindemann (USC) — conformal prediction in optimisation and control; Pu Li (TU Ilmenau)
— chance-constrained process optimisation. Ehecatl Antonio del Río Chanona (Imperial) is the
closest prior art and an authoritative alternative. No reviewers opposed.
