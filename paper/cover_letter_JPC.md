# Cover letter — Journal of Process Control (transfer submission)

To the Editors, Journal of Process Control

Dear Editors,

I am submitting the manuscript "When does a calibrated soft sensor keep its promise? A
negative-control study of validity without accuracy under drift and delayed labels" for
consideration as a full-length article in the Journal of Process Control.

In the interest of full transparency: this manuscript was first submitted to Computers
& Chemical Engineering (CACE-D-26-00944), where the editor declined it without review on
the grounds that its subject sat outside that journal's core priorities, and recommended
transfer to a journal whose scope better matches soft sensing for process operation. I
have used the opportunity to substantially reframe the contribution, not merely relabel
it, and I believe the Journal of Process Control is its correct home: soft sensing,
online calibration, and their interaction with real-time process operation are central
to the journal's scope, and the methodological lineage the paper builds on (Kalman and
data-fusion estimation under delayed and infrequent measurements; model migration across
operating regimes) is work published by members of this journal's own community.

The paper makes a contribution that is methodological rather than incremental. A soft
sensor that reports an uncertainty interval makes two separable promises: that its point
estimate is accurate, and that its interval is valid. Practice conflates them. The paper
separates them by construction and then tests the separation with a negative control: a
deliberately physics-free process (the SECOM semiconductor dataset) on which the
point model is engineered to fail. It does, with held-out R-squared of -1.84, yet the
conformal intervals retain 0.910 to 0.915 empirical coverage against a 0.90 target, at
37 percent narrower width than a static baseline. Accuracy collapses while validity
survives. This dissociation is the central evidence, and it licenses a claim no positive
result alone could support: that distribution-free validity is model-agnostic, whereas
point accuracy is what the process physics buys. A designed negative control is the
standard instrument for attributing an effect to its cause; it is uncommon in
data-driven process modeling, and supplying one is the paper's primary methodological
contribution.

The framework that makes the control interpretable is itself fully developed and
validated on two process columns. On a debutanizer benchmark, held-out R-squared rises
from +0.476 to +0.857 once an open-loop bias update corrects drift at the documented
laboratory delay; on Tennessee Eastman regimes, adaptive conformal intervals built on
the corrected residual hold 0.897 to 0.903 coverage where a static construction swings
between 0.847 and 0.957. The paper also identifies and corrects a real-time
implementation hazard specific to delayed laboratory feedback: the coverage indicator
for a late result must be scored against the interval issued when the sample was
measured, not the interval the adapted calibration would issue when the result arrives.
The implementation runs two orders of magnitude inside a typical analyzer cycle.

Every quantitative result in the paper regenerates from a single command against
provenance-stamped evidence artifacts in a public repository, and the full pipeline has
been reproduced on two independent machines. The limits of the methods are reported as
results rather than hedged, including an analytical and empirical demonstration that a
published migration method degenerates to from-scratch regression for linear source
models.

The manuscript is approximately 7,000 words with seven figures and four tables. It is my
original work, is not under consideration at any other journal, and I am the sole author.
I have no competing interests to declare. Reviewers with expertise in soft sensing,
conformal prediction for time series, and process model migration would be well placed to
assess it.

Thank you for considering this work.

Sincerely,

Bien Busico
Mapúa Malayan College Mindanao, Davao City, Philippines
bienbusico@gmail.com
