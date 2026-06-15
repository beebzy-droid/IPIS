# Cover letter — Journal of Process Control

> Fill the bracketed fields, then paste the letter body into the submission portal.
> Suggested reviewers go in their own portal fields, not the letter.

---

[Your name]
[Affiliation]
[Address]
[Email]

[Date]

Dear Editors of the *Journal of Process Control*,

Please consider the enclosed manuscript, "The conformal selection effect in real-time
optimisation: why marginally valid back-offs over-violate and conditional calibration
restores safety," for publication as a research article in the *Journal of Process
Control*.

Real-time optimisation must protect a quality constraint it cannot measure online by
subtracting a back-off from the specification, and conformal prediction is the natural
distribution-free way to size that margin from operating data. The manuscript shows that
this natural choice is unsafe. An optimiser pressing on a marginally valid conformal
back-off, including a locally adaptive one, behaves as a selection mechanism that drives
the operating point to where the margin under-covers the conditional constraint quantile;
on a rigorous Peng–Robinson debutaniser twin the realised violation rate reaches roughly
five times the nominal level across the disturbance range. We name this the conformal
selection effect, confirm against an oracle that the failure lies in the back-off rather
than the chance-constrained formulation, and show that conditional validity is the
structural remedy: a conformalised-quantile-regression back-off with an a-posteriori
calibration step returns the realised violation to the oracle level at near-oracle profit
over the operationally realistic disturbance range. A regime map over disturbance
magnitude bounds where each margin controls violation and where the conditional method
itself runs out of calibration data, a boundary that its inflation factor signals in
advance.

We believe the work fits the journal's scope because it concerns constraint-violation
control inside an optimisation loop, a process-control problem, and because it engages
directly with the modifier-adaptation and chance-constrained real-time optimisation
literature the journal has long published. The contribution is deliberately framed as
calibrated safety rather than profit: at a well-controlled feed the constraint is barely
active and all methods earn within half a percent of the deterministic optimum, so the
value of the proposed method is the violation it removes, not any profit it adds. We have
tried to state the limitations plainly, including that the study uses a validated
simulation twin of a single binary system and that violation rates are reported with a
Monte-Carlo band.

The manuscript is original, has not been published previously, and is not under
consideration elsewhere. A companion paper from the same project, which develops the
physics-informed soft sensor referenced here as the source of the model-based composition
estimate, is currently under review at *Computers & Chemical Engineering* (CACE-D-26-00944);
the present manuscript is self-contained and does not overlap with it in contribution. All
data, the chance-constrained optimisation implementation, and the figure scripts are
available for the reviewers, and every result regenerates from a single fixed seed.

Thank you for considering our submission. We look forward to the reviewers' comments.

Sincerely,
[Your name], on behalf of the authors

---

## Suggested reviewers (for the portal fields)

JPC typically asks for three to five. All are active in RTO under uncertainty, conformal
prediction, or stochastic process control. Check each for a conflict of interest (no shared
recent publications or institutions with the author) before listing, and adjust to the
portal's required count.

1. **Benoît Chachuat**, Imperial College London — modifier adaptation and real-time
   optimisation under uncertainty; can assess the RTO framing and the back-off comparison.
2. **Ali Mesbah**, University of California, Berkeley — stochastic and learning-based MPC,
   uncertainty quantification in process control; well placed to judge the constraint-
   violation argument and the closed-loop outlook.
3. **Victor M. Zavala**, University of Wisconsin–Madison — optimisation under uncertainty
   and chance constraints in process systems engineering.
4. **Lars Lindemann**, University of Southern California — conformal prediction inside
   optimisation and control (conformal predictive programming); can evaluate the selection-
   effect claim and the a-posteriori calibration.
5. **Pu Li**, Technische Universität Ilmenau — chance-constrained programming for process
   optimisation; can assess the chance-constraint formulation and feasibility analysis.

Note on a possible sixth: **Ehecatl Antonio del Río Chanona** (Imperial College London) is
the closest prior art (Gaussian-process modifier adaptation). He is an authoritative
referee, but because the manuscript positions itself partly against that line, you may
prefer to list him as an alternative rather than a primary suggestion. No reviewers are
opposed.
