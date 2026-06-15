# References — Paper 2 (conditionally-valid conformal back-offs for RTO)

> Every in-text citation in `sections/` resolves to an entry below. Tag [corpus] = the
> source PDF is in the project set (bibliographic details from its title page); [standard]
> = foundational reference from general knowledge, confirm page/venue at LaTeX time; ⚠️ =
> one detail to verify before submission. Human-readable now; convert to elsarticle BibTeX
> at the LaTeX sub-phase. Ordering alphabetical by first author within theme.

## Real-time optimization under uncertainty

- **Bradford, E., Imsland, L., & del Río-Chanona, E. A. (2019).** Nonlinear model
  predictive control with explicit back-offs for Gaussian process state space models.
  *Proc. 58th IEEE Conference on Decision and Control (CDC)*, 4747–4754.
  — *GP-posterior explicit back-offs in MPC; cited in §2.1 as the back-off analogue in control.*
- **Bradford, E., Imsland, L., Zhang, D., & del Río-Chanona, E. A. (2020).** Stochastic
  data-driven model predictive control using Gaussian processes. *Computers & Chemical
  Engineering*, 139, 106844.
  — *GP stochastic MPC; §2.1.*
- **Chachuat, B., Srinivasan, B., & Bonvin, D. (2009).** Adaptation strategies for
  real-time optimization. *Computers & Chemical Engineering*, 33(10), 1557–1567. [corpus]
  — *MA/RTO adaptation review; §2.1.*
- **del Río-Chanona, E. A., Alves Graciano, J. E., Bradford, E., & Chachuat, B. (2019).**
  Modifier-adaptation schemes employing Gaussian processes and trust regions for real-time
  optimization. *IFAC-PapersOnLine*, 52(1), 52–57.
  — *GP modifiers + trust regions; §2.1.*
- **del Río Chanona, E. A., Petsagkourakis, P., Bradford, E., Alves Graciano, J. E., &
  Chachuat, B. (2021).** Real-time optimization meets Bayesian optimization and
  derivative-free optimization: A tale of modifier adaptation. *Computers & Chemical
  Engineering*, 147, 107249. [corpus]
  — *Closest GP-based RTO neighbour; constraint handling via GP-mean modifiers + trust
  regions, GP variance for excitation. The §2.1 wedge: no distribution-free coverage guarantee.*
- **Li, P., Arellano-Garcia, H., & Wozny, G. (2008).** Chance constrained programming
  approach to process optimization under uncertainty. *Computers & Chemical Engineering*,
  32(1–2), 25–45. [corpus]
  — *Classical chance-constrained programming in ChemE under assumed (normal) law; the
  formulation we adopt distribution-free. §2.1.*
- **Marchetti, A., Chachuat, B., & Bonvin, D. (2009).** Modifier-adaptation methodology for
  real-time optimization. *Industrial & Engineering Chemistry Research*, 48(13), 6022–6033.
  [corpus]
  — *KKT-matching modifier adaptation; the §2.1 baseline RTO paradigm.* ⚠️ page span.

## Conformal prediction: foundations and conditional validity

- **Angelopoulos, A. N., & Bates, S. (2023).** A gentle introduction to conformal
  prediction and distribution-free uncertainty quantification. *Foundations and Trends in
  Machine Learning*, 16(4), 494–591. [corpus]
  — *Conformal primer; §2.2.*
- **Barber, R. F., Candès, E. J., Ramdas, A., & Tibshirani, R. J. (2023).** Conformal
  prediction beyond exchangeability. *Annals of Statistics*, 51(2), 816–845. [corpus]
  — *Non-exchangeable conformal; §2.2 (dependent data / shift).*
- **Gibbs, I., & Candès, E. J. (2021).** Adaptive conformal inference under distribution
  shift. *Advances in Neural Information Processing Systems*, 34. [corpus — extended version
  "Conformal inference for online prediction with arbitrary distribution shifts" in set]
  — *ACI; §2.2. Relevant to closed-loop/temporal calibration (§6.4).* ⚠️ cite ACI 2021 vs JMLR extension.
- **Gibbs, I., Cherian, J. J., & Candès, E. J. (2023).** Conformal prediction with
  conditional guarantees. *arXiv:2305.12616*. [corpus]
  — *Marginal-vs-conditional coverage theory; the §2.2 / §3.3 backbone.* ⚠️ final venue/year.
- **Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R. J., & Wasserman, L. (2018).**
  Distribution-free predictive inference for regression. *Journal of the American
  Statistical Association*, 113(523), 1094–1111. [corpus]
  — *Split + locally-weighted (normalized) conformal; the baseline back-off in §3.2.*
- **Lei, J., & Wasserman, L. (2014).** Distribution-free prediction bands for
  non-parametric regression. *Journal of the Royal Statistical Society: Series B*, 76(1),
  71–96. [standard]
  — *Conditional-coverage impossibility; §2.2.*
- **Romano, Y., Patterson, E., & Candès, E. J. (2019).** Conformalized quantile regression.
  *Advances in Neural Information Processing Systems*, 32. [corpus]
  — *CQR; the conditional back-off in §3.2 (the proposed construction).*
- **Tibshirani, R. J., Foygel Barber, R., Candès, E. J., & Ramdas, A. (2019).** Conformal
  prediction under covariate shift. *Advances in Neural Information Processing Systems*, 32.
  [standard]
  — *Weighted conformal under shift; §2.2.*
- **Vovk, V. (2012).** Conditional validity of inductive conformal predictors. *Asian
  Conference on Machine Learning*, PMLR 25, 475–490. [standard]
  — *Conditional-validity limits; §2.2.*
- **Vovk, V., Gammerman, A., & Shafer, G. (2005).** *Algorithmic Learning in a Random
  World.* Springer. [standard]
  — *Conformal prediction foundation; §2.2.*

## Conformal prediction inside optimization and control

- **Zhang, et al. (2024).** Bayesian optimization with formal safety guarantees via online
  conformal prediction. [corpus] ⚠️ **authors + venue** to confirm from PDF title page.
  — *Conformal safety in BO; §2.3.*
- **Zhao, Y., Yu, X., Sesia, M., Deshmukh, J. V., & Lindemann, L. (2024).** Conformal
  predictive programming for chance constrained optimization. [corpus] ⚠️ venue
  (arXiv / Automatica submission).
  — *CPP: quantile reformulation of CCO + a-posteriori calibration; names the
  loss-of-independence-under-optimization. Supplies the §3.4 a-posteriori step; the §2.3 anchor.*

## Process model and thermodynamics

- **Peng, D.-Y., & Robinson, D. B. (1976).** A new two-constant equation of state.
  *Industrial & Engineering Chemistry Fundamentals*, 15(1), 59–64. [standard]
  — *PR EOS used by the twin; §3.5.*
- **DWSIM — Medeiros, D. W. G.** DWSIM: open-source chemical process simulator (v9.0.5).
  ⚠️ **software citation form** (manual/Zenodo DOI) to finalize.
  — *The rigorous twin; §3.5, §4.1.*

## Companion

- **[Busico, B., et al.] (2026).** [Paper 1 — physics-informed conformal soft sensor].
  Under review, *Computers & Chemical Engineering*, CACE-D-26-00944. ⚠️ **self-citation**
  details at submission.
  — *Supplies the model-based estimate of the unmeasured constraint; §3.1, §6.4.*

---

### Citation-consistency log (this pass)
- CPP standardized to first-author **Zhao et al. (2024)** in §3 methods (was "Lindemann et
  al.") and §2 related work — now consistent.
- Unverifiable **Ferreira et al. (2018)** sub-citation folded into the verified GP-modifier
  line (del Río-Chanona et al., 2019) in §2.
- Remaining ⚠️ items are venue/page/author confirmations at LaTeX time, not missing entries:
  every in-text cite resolves here.
