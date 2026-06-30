# Cover letter - Computers & Chemical Engineering

Dear Editor,

Please consider the enclosed manuscript, "Horizon-wide safety guarantees for closed-loop
process operation via adaptive conformal calibration," for publication in Computers & Chemical
Engineering as a research article.

A process operated under a data-driven controller is safe only if it stays within its quality
and equipment-health limits across an entire campaign, not merely at one decision. A per-cycle
certificate for this joint event exists, but it assumes the calibration residuals are
exchangeable and that the loop reports its labels promptly, and a real closed loop satisfies
neither: feedback couples successive cycles, and laboratory or analyser measurements arrive
several cycles late. The contribution of this paper is a horizon-wide version of the guarantee
that an engineer can deploy, obtained by lifting the per-cycle certificate with adaptive
conformal inference on a dynamically realised debutaniser loop, together with the evidence that
the obvious union-bound alternative cannot serve. On a Peng-Robinson twin the conformal
health-constrained loop holds the joint safety event at its certified floor of 0.75 with a 95%
Wilson lower bound of 0.992 across a campaign, whereas a health-blind optimiser stays in
specification on essentially every cycle yet over-refluxes until projected remaining useful life
collapses, dropping the joint event to 0.008. We show the guarantee is invariant to measurement
dead time, because the conformal selection penalty stays zero under arbitrary label delay so
dead time enters only the coverage rate, and that adaptive calibration retains a finite interval
at target coverage across horizons at which the naive Bonferroni union bound is already vacuous.

The work is framed as calibrated safety rather than profit: the value of the health-constrained
loop is the equipment degradation and the horizon-scale violations it removes, not a higher
economic optimum. The result is general, since any per-cycle conformal certificate placed inside
a feedback loop faces the same horizon question, and it gives process systems engineers a
portable construction for turning a certified stack of components into a certified operating
campaign and a runtime safety monitor.

The manuscript is the author's original work and is not under consideration elsewhere. It is the
realisation layer of a series whose companion papers develop the soft sensor (JPROCONT-D-26-00618,
under review at the Journal of Process Control), the prognostic certificate (JRESS-D-26-04700,
under review), and the conformal real-time optimiser (CACE-D-26-01040, under review at this
journal); the per-cycle composed certificate that the present work lifts to a horizon is a further
companion under review at this journal (CACE-D-26-01079). The present manuscript is
self-contained and does not overlap with these in contribution.

The dynamic plant, the closed-loop orchestrator, the adaptive-conformal read-off, and the figure
scripts are available, and every quantitative claim regenerates from a single fixed seed.
Suggested reviewer expertise: adaptive and online conformal prediction, real-time optimisation
under uncertainty, and process monitoring and predictive maintenance.

Thank you for your consideration.

Bien Busico
Chemical Engineer, Quezon City, Philippines
bienbusico@gmail.com
