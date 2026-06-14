# Phase 3B — Literature map and positioning

> Curated 2026-06-13 to (a) anchor the 3B contribution in BOTH the chemical-
> engineering RTO tradition and the conformal-prediction tradition, and (b)
> surface concrete upgrades. Target venues (Comput. Chem. Eng. / J. Process
> Control) require positioning against modifier adaptation, not only against the
> ML literature. Items marked **[UPGRADE]** are actionable changes to the build.

## The one-sentence position

3B sits at an intersection that, from this search, appears under-occupied:
**measurement-based RTO where the constrained quantity is not measured but
INFERRED by a soft sensor, and the constraint back-off is that sensor's
distribution-free, heteroscedastic conformal interval.** The two adjacent
literatures each cover one half:

- ChemE RTO-under-uncertainty handles the back-off, but sizes it from model
  posteriors or modifier-adaptation gradients — not calibrated sensor intervals.
- Conformal-for-optimization handles calibrated constraint tightening, but
  assumes the constraint function can be sampled directly, not inferred.

## A. Chemical-engineering RTO under uncertainty (position against these)

- **François & Bonvin, "Measurement-based RTO of chemical processes"** and
  **Marchetti, Chachuat & Bonvin, modifier-adaptation series** (IECR 2009; J.
  Proc. Control 2010+). The dominant paradigm: measurements reduce the
  conservatism that constraint back-offs introduce; modifier adaptation adds
  measured constraint/gradient *modifiers* and re-solves. **3B framing:** the
  sensor-driven back-off C(operating point) IS a measurement-based constraint
  modifier — but informed by a *calibrated uncertainty* rather than a
  plant-model gradient mismatch. State this connection explicitly; it is how the
  ChemE audience will read the contribution.
- **Chachuat, Marchetti & Bonvin (2008)** — the canonical statement that
  measurements let you shrink constraint back-offs and recover performance. This
  is the exact lever 3B pulls; cite as the back-off-reduction precedent.
- **Li, Arellano-Garcia & Wozny (2008), "Chance constrained programming approach
  to process optimization under uncertainty"** (Comput. Chem. Eng. 32:25-45).
  The classical ChemE chance-constraint reference; cite for the CC formulation.
- **del Rio Chanona et al., "RTO meets Bayesian optimization and DFO: a tale of
  modifier adaptation"** (J. Proc. Control 2021). **THE CLOSEST PRIOR ART:** a
  GP surrogate of the offline model whose *posterior uncertainty* tightens joint
  chance constraints under plant-model mismatch, benchmarked vs NMPC.
  **Differentiator for 3B (the novelty wedge):** they tighten using the GP's own
  Gaussian posterior variance, which can be miscalibrated; 3B tightens using a
  *distribution-free, finite-sample-valid* conformal interval of a soft-sensor
  estimate. The advantage of conformal over GP-posterior is precisely
  CALIBRATION — which is exactly the tier-1 ("calibrated risk control") headline
  the 3B.3 design finding pushed us toward. The closest prior art therefore
  reinforces, rather than threatens, the reframed contribution.

## B. Conformal foundations — heteroscedastic and adaptive

- **Romano, Patterson & Candès (2019), Conformalized Quantile Regression (CQR).**
  Standard conformal forms intervals of constant/weakly-varying width and is
  "unnecessarily conservative" under heteroscedasticity; CQR fits conditional
  quantiles and conformalizes them for valid, *fully adaptive* intervals.
  **[UPGRADE]** Our `TwinSoftSensor` currently does mean-GP + scale-GP normalized
  conformal (Lei-style). CQR is the field-standard alternative: fit the
  conditional (1-alpha) quantile of xB given tray-6 T directly, then apply the
  one-sided conformal correction. Likely tighter and more directly calibrated for
  the one-sided upper bound; worth A/B-ing against the current normalized variant
  once real data lands. (Romano et al. is already implied by our MAPIE stack.)
- **Gibbs, Cherian & Candès (2025), "Conformal prediction with conditional
  guarantees"** (JRSS-B 87(4)). **Directly explains the 3B.3 finding** that the
  conformal level alpha does not equal the realized violation rate at the
  *selected* setpoint: marginal coverage is not conditional coverage, and
  optimization-driven selection exploits the gap. **[UPGRADE]** if a per-setpoint
  guarantee is wanted, this is the route (conditional/Mondrian conformal over
  operating-regime bins). Cite to pre-empt the reviewer who asks "is your 90%
  conditional on the chosen setpoint?"
- **Barber, Candès, Ramdas & Tibshirani (2023), "Conformal prediction beyond
  exchangeability"** (Ann. Statist. 51:816-845). The RTO induces distribution
  shift as it moves the operating point; this and the project's existing
  Gibbs & Candès ACI reference are the rigorous basis for coverage under that
  shift. Already partly in the Module-1 stack (ACI).

## C. Conformal prediction FOR optimization / control (the bridge)

- **Zhao, Yu, Sesia, Deshmukh & Lindemann, "Conformal Predictive Programming
  (CPP) for Chance Constrained Optimization"** (arXiv 2402.07407, 2024-25). **The
  formal backbone:** transform a chance-constrained program into a deterministic
  *quantile-reformulated* program via the conformal quantile lemma; supports
  robust CPP (distribution shift) and Mondrian CPP (conditional), with tractable
  CPP-KKT / CPP-MIP reformulations, benchmarked vs the scenario approach.
  **3B relationship:** CPP assumes you can *sample the constraint function*
  xB(R,D,z) directly. 3B's distinctive case is that xB is *not* directly
  available online — it is inferred by a soft sensor — so the back-off is the
  sensor's conformal interval. Position 3B as the soft-sensor-driven instance/
  complement of CPP; cite CPP for the quantile-reformulation guarantees and as
  the general framework. **[UPGRADE]** the 3B.3 truth-side violation evaluation
  is already CPP-style sampling over z; we could additionally offer a CPP-style
  *sample-based* RTO constraint as a second formulation and compare it to the
  soft-sensor-interval formulation — strengthens the paper's rigor.
- **Zhang, Cohen et al. (KCLIP), "Bayesian Optimization with Formal Safety
  Guarantees via Online Conformal Prediction" (Safe-BOCP)** (IEEE J-STSP 2024).
  GP surrogates for objective AND constraint, with a *caution-increasing
  back-off* calibrated online by conformal prediction, allowing any non-zero
  target violation level without RKHS assumptions. **Very close in spirit to 3B**
  (GP surrogate + conformal back-off for constrained optimization). Differentiator:
  Safe-BOCP is sequential black-box BO; 3B is steady-state RTO with a physics-
  anchored *soft-sensor* feature and a rigorous DWSIM twin. Cite as the safe-
  optimization analogue and adopt its "any target violation level" framing.
- **Multi-variable conformal for chance-constrained scheduling** (arXiv
  2510.04053, 2025; 24/7 carbon-free data centers). Empirically shows that
  *covariate-aware (contextual) conformal* uncertainty sets feeding a CC program
  cut cost vs CVaR and box-robust baselines. **Supports tier-2:** the profit win
  is real *when covariate/contextual information makes the set adaptive* — i.e.
  exactly our heteroscedastic σ̂(x). Useful evidence that adaptivity beats
  one-size sets in a real CC application.

## D. Conformal in process / industrial settings (domain precedent)

- **"Distribution-Free Process Monitoring with Conformal Prediction"** (arXiv
  2512.23602, 2025) — CP for SPC; surveys CP in semiconductor, surface-defect,
  recycling, farming. Domain precedent that CP is being adopted in manufacturing.
- **"Intrinsically Calibrated UQ in Industrial Data-Driven Models via Diffusion
  Sampler"** (arXiv 2604.01870, 2026) — UQ benchmarked on a Raman phenylacetic-
  acid *soft sensor* and an ammonia-synthesis case. Recent industrial-soft-sensor
  UQ baseline to compare calibration against.
- **Fortuna, Graziani, Rizzo & Xibilia (2007), "Soft sensors for monitoring and
  control of industrial processes"** (Springer) — the standard soft-sensor
  reference; cite for the soft-sensor setup.

## E. Recommendations for 3B (actionable)

1. **[UPGRADE] A/B the interval engine: normalized-residual vs CQR.** CQR
   (Romano 2019) is the field-standard heteroscedastic method; fit the conditional
   one-sided quantile of xB|tray-6 T and conformalize. Keep the current normalized
   variant as the baseline; report both widths/coverage. Low effort, strengthens
   the methods section.
2. **Lead with calibrated risk control (tier 1); cite del Rio Chanona (2021) as
   the GP-posterior approach 3B improves on via calibration.** The closest prior
   art makes the calibration framing the natural, defensible headline.
3. **Position the back-off as a measurement-based constraint modifier** (Bonvin/
   François lineage) for the ChemE audience, and as a *soft-sensor instance of
   CPP* (Lindemann lineage) for the controls audience. Bridging both communities
   is the paper's distinctive value.
4. **Pre-empt the conditional-coverage question** (Gibbs/Cherian/Candès 2025):
   acknowledge marginal != conditional, explain the alpha-vs-realized-violation
   gap as a selection effect, and (optionally) add Mondrian/regime-binned
   conformal for an approximate per-setpoint guarantee.
5. **Optional second formulation:** a CPP-style sample-based RTO constraint
   (sample z, conformal-quantile the constraint) alongside the soft-sensor-
   interval formulation — lets the paper compare "tighten by sensor interval" vs
   "tighten by disturbance samples," which is itself a novel comparison.
