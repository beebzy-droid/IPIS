# Abstract

> Draft status: 1F.3 v1. ~190 words; CACE limit permitting, keep under 250.

Industrial soft sensors fail through recurring mechanisms: model selection becomes a
lottery under autocorrelation and regime shift, calibration drifts between delayed and
infrequent laboratory analyses, confidence statistics inherit an exchangeability
assumption that drift destroys, and new operating regimes lack training data. We
present an integrated framework that addresses each with a deliberately simple,
auditable core — physics-derived features on a linear estimator, blocked time-series
cross-validation with a one-standard-error rule, an open-loop bias update at the
documented label delay, adaptive conformal intervals computed on the corrected
residuals, and functional scale-bias migration composed with the online layer — and a
serving architecture that scores delayed labels against the interval stored at
prediction time. On the Tennessee Eastman process the framework delivers
regime-uniform empirical coverage of 0.897–0.903 against a 0.90 target where a static
conformal baseline swings between 0.847 and 0.957, and 10.0× data efficiency in regime
migration. A deliberately hostile negative control (SECOM: 590 anonymized features,
no physics) shows the decomposition: the point sensor fails (R² = −1.84), yet coverage
holds at 0.910–0.915 with 37% narrower intervals than the static baseline. Validity is
model-agnostic; accuracy is what physics anchors buy.
