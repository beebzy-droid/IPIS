# Cover letter - Computers & Chemical Engineering

Dear Editor,

Please consider the enclosed manuscript, "Conditionally calibrated conformal back-offs for
chance-constrained real-time optimisation under unmeasured disturbances," for publication in
Computers & Chemical Engineering as a research article.

Real-time optimisation must protect a product-quality constraint it cannot measure online by
subtracting a back-off from the specification, and sizing that margin from operating data with
conformal prediction is attractive because it is distribution-free and needs no model of the
disturbance. The contribution of this paper is a back-off that an engineer can actually deploy
for this purpose, together with the evidence that the obvious alternative cannot be. On a
rigorous Peng-Robinson debutaniser twin we show that an optimiser respecting a marginally
valid conformal back-off, including a locally adaptive one, realises a constraint-violation
rate of roughly five times the nominal target, because it settles at the operating point where
the margin is least conservative relative to the local risk. We verify against an oracle that
the failure lies in the back-off and not in the chance-constrained formulation, and we propose
a back-off built from conformalised quantile regression with an a-posteriori calibration that
returns the realised violation to the oracle level at near-oracle profit, degrading only when
the disturbance widens several-fold and announcing that limit through a calibration inflation
factor an operator can read as a data-adequacy diagnostic.

The work is framed honestly as calibrated safety rather than profit: at a well-controlled feed
the constraint is barely active and every method earns within half a percent of the
deterministic optimum, so the value of the proposed method is the violation it removes. The
result is general, since any conformal interval used as a hard optimisation constraint is
exposed to the same mechanism, and it gives a portable design rule for process systems
engineers building data-driven RTO.

The manuscript is the author's original work and is not under consideration elsewhere. A
companion paper that develops the physics-informed soft sensor providing the model-based
composition estimate is under review at this journal (CACE-D-26-00944); the present manuscript
is self-contained and does not overlap with it in contribution. All data, the
chance-constrained optimisation implementation, and the figure scripts are available, and every
quantitative claim regenerates from a single fixed seed. Suggested reviewer expertise:
real-time optimisation under uncertainty, chance-constrained process optimisation, and
conformal prediction in optimisation and control.

Thank you for your consideration.

Bien Busico
Mapúa Malayan College Mindanao, Davao City, Philippines
bienbusico@gmail.com
