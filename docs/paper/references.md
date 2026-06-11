# References — IPIS soft-sensor framework paper

> Phase 1F.4. Bibliographic details below were extracted from the title pages of the
> project-source PDFs (verified by rasterizing/extracting each first page) and from the
> 1F.4 literature sweep. Items flagged ⚠️ need one confirmation at LaTeX time (page
> numbers / final venue). Format here is human-readable; convert to elsarticle BibTeX in
> 1F.5. Ordering is alphabetical by first author for now; numbered IEEE-style or
> author-year per CACE house style at conversion.

## Soft sensing under delayed / infrequent / irregular measurements

- **Guo, Y., Zhao, Y., & Huang, B. (2014).** Development of soft sensor by incorporating
  the delayed, infrequent and irregular measurements. *Journal of Process Control*,
  24(8), 1733–1739. https://doi.org/10.1016/j.jprocont.2014.09.006
  — *Univ. of Alberta. Kalman-filter / data-fusion online estimation; §2.1.*

- **Shardt, Y. A. W., & Yang, X. (2016).** Development of soft sensors for the case where
  the time delay is random. *IFAC-PapersOnLine*, 49(7), 1193–1198.
  https://doi.org/10.1016/j.ifacol.2016.07.371
  — *IFAC ADCHEM 2016. Open-/closed-loop bias-update design under random-but-known
  delay; the §3.3 backbone. (Note: extends Shardt & Huang 2012, the constant-delay
  framework.)*

- **Wang, W., Yang, C., Han, J., Li, W., & Li, Y. (2021).** A soft sensor modeling method
  with dynamic time-delay estimation and its application in wastewater treatment plant.
  *Biochemical Engineering Journal*, 172, 108048.
  https://doi.org/10.1016/j.bej.2021.108048
  — *Central South Univ. SD-DU + weighted RVM (DTDE-WRVM); the dynamic-delay
  counterpart to our static lag diagnosis; §2.1.*

## Process model migration

- **Lu, J., & Gao, F. (2008a).** Process modeling based on process similarity.
  *Industrial & Engineering Chemistry Research*, 47(6), 1967–1974.
  https://doi.org/10.1021/ie0704851
  — *HKUST. Foundational process-similarity / migration concept; §2.2.*

- **Lu, J., & Gao, F. (2008b).** Model migration with inclusive similarity for development
  of a new process model. *Industrial & Engineering Chemistry Research*, 47(23),
  9508–9516. https://doi.org/10.1021/ie800595a
  — *HKUST. Bagging-aggregated migration under inclusive similarity; §2.2.*

- **Lu, J., Yao, K., & Gao, F. (2009).** Process similarity and developing new process
  models through migration. *AIChE Journal*, 55(9), 2318–2328.
  https://doi.org/10.1002/aic.11822
  — *HKUST. Output-side scale-bias migration methodology; §2.2.*

- **Yan, W., Hu, S., Yang, Y., Gao, F., & Chen, T. (2011).** Bayesian migration of
  Gaussian process regression for rapid process modeling and optimization. *Chemical
  Engineering Journal*, 166(3), 1095–1103. https://doi.org/10.1016/j.cej.2010.11.097
  — *NTU Singapore + HKUST. FUNCTIONAL scale-bias correction (input-dependent scale +
  zero-mean GP bias) with posterior intervals; the 10.0× migration result, §3.5 / §5.4.*

- **Luo, L., Yao, Y., & Gao, F. (2015).** Bayesian improved model migration methodology
  for fast process modeling by incorporating prior information. *Chemical Engineering
  Science*, 134, 23–35. https://doi.org/10.1016/j.ces.2015.04.045
  — *HKUST + NTHU. Per-input affine re-scaling via normal-inverse-gamma priors + MCMC;
  the linear-source degeneracy of §5.4 is specific to this method.*

## Conformal prediction

- **Papadopoulos, H., Proedrou, K., Vovk, V., & Gammerman, A. (2002).** Inductive
  confidence machines for regression. In *Machine Learning: ECML 2002*, LNCS 2430,
  pp. 345–356. Springer. https://doi.org/10.1007/3-540-36755-1_29
  — *Royal Holloway. Inductive (split) conformal prediction; §2.3 / §3.4.*
  ⚠️ Confirm LNCS volume/page span at 1F.5 (title page gives authors/affiliation only;
  ECML-2002 / LNCS 2430 from the published proceedings).

- **Barber, R. F., Candès, E. J., Ramdas, A., & Tibshirani, R. J. (2021).** Predictive
  inference with the jackknife+. *The Annals of Statistics*, 49(1), 486–507.
  https://doi.org/10.1214/20-AOS1965
  — *Jackknife+ / weaker-than-exchangeability inference; §2.3.*

- **Xu, C., & Xie, Y. (2021).** Conformal prediction for time series. *(arXiv:2010.09107;
  IEEE TPAMI 2023 in final form.)* EnbPI — FIFO residual-ensemble intervals without
  exchangeability; the §3.4 / §5.3 comparator.
  ⚠️ At 1F.5 decide whether to cite the ICML-2021 version (EnbPI, "Conformal prediction
  interval for dynamic time-series") or the extended TPAMI 2023 journal version; the
  project PDF is the arXiv extended manuscript.

- **Gibbs, I., & Candès, E. (2021).** Adaptive conformal inference under distribution
  shift. *Advances in Neural Information Processing Systems (NeurIPS)* 34.
  — *ACI, the §3.4 primary. (Project PDF "Conformal inference for online prediction with
  arbitrary distribution shifts", arXiv:2208.08401, is the 2022/2023 follow-on; cite
  whichever ACI form the final text leans on — the original 2021 ACI for the update rule,
  the 2022 paper for the arbitrary-shift guarantee.)*
  ⚠️ Resolve the 2021-vs-2022 citation at 1F.5 against which α-update equation §3.4 states.

### Conformal prediction under imperfect / delayed feedback (1F.4 sweep additions)

- **Wang, B., Zecchin, M., & Simeone, O. (2025).** Mirror online conformal prediction with
  intermittent feedback. *IEEE Signal Processing Letters*, 32, 2888–2892.
  arXiv:2503.10345.
  — *IM-OCP; §2.3 prior work for intermittent feedback.*
  ⚠️ PAGE CONFLICT: author CV + corrupted-feedback paper's reference list give
  2888–2892; an ADS/arXiv listing shows 2649–2653. Verify on IEEE Xplore by DOI.

- **Wang, B., Zecchin, M., & Simeone, O. (2026).** Online conformal prediction with
  corrupted feedback. *(arXiv:2605.20515; preprint.)* §2.3.
  ⚠️ Confirm final venue/year before submission.

- **Hou, J., Park, S., Zecchin, M., Cai, Y., Yu, G., & Simeone, O. (2025).** Online
  conformal probabilistic numerics via adaptive edge-cloud offloading.
  *(arXiv:2503.14453.)* Sporadic-feedback online CP; §2.3.
  ⚠️ Confirm author list and final venue at 1F.5.

## Tennessee Eastman process

- **Downs, J. J., & Vogel, E. F. (1993).** A plant-wide industrial process control
  problem. *Computers & Chemical Engineering*, 17(3), 245–255.
  https://doi.org/10.1016/0098-1354(93)80018-I
  — *The canonical TEP; §4.2. (Venue from the standard citation; project PDF is the
  scanned original.)*

- **Bathelt, A., Ricker, N. L., & Jelali, M. (2015).** Revision of the Tennessee Eastman
  process model. *IFAC-PapersOnLine*, 48(8), 309–314.
  https://doi.org/10.1016/j.ifacol.2015.08.199
  — *FH Köln + UW. The revised/repeatable simulation code lineage used for the regime
  data; §4.2.*

- **Vosloo, J., Uren, K. R., & van Schoor, G. (2025).** A complete and open Simulink model
  of the Tennessee Eastman process (COSTEP). *SoftwareX*, 31, 102217.
  https://doi.org/10.1016/j.softx.2025.102217
  — *North-West Univ. The open Simulink reimplementation abandoned on a reproducibility
  gate (§4.2 footnote); MIT-licensed, github.com/kennyuren/COSTEP.*

## Drift detection

- **Bifet, A., & Gavaldà, R. (2007).** Learning from time-changing data with adaptive
  windowing. In *Proceedings of the 2007 SIAM International Conference on Data Mining
  (SDM)*, pp. 443–448. https://doi.org/10.1137/1.9781611972771.42
  — *ADWIN, the §3.3 drift detector on the corrected residual.*

## External (not in project sources — confirm editions at 1F.5)

- **Fortuna, L., Graziani, S., Rizzo, A., & Xibilia, M. G. (2007).** *Soft Sensors for
  Monitoring and Control of Industrial Processes.* Springer. — *Debutanizer benchmark
  dataset; §4.1.*

- **Hastie, T., Tibshirani, R., & Friedman, J. (2009).** *The Elements of Statistical
  Learning* (2nd ed.). Springer. — *One-standard-error rule; §3.2.* ⚠️ cite the specific
  section for the 1-SE rule.

- **McCann, M., & Johnston, A. (2008).** *SECOM Data Set.* UCI Machine Learning
  Repository. https://archive.ics.uci.edu/dataset/179/secom — *§4.3 negative control.*

- **Smith, J. M., Van Ness, H. C., Abbott, M. M., & Swihart, M. T. (2018).**
  *Introduction to Chemical Engineering Thermodynamics* (9th ed.). McGraw-Hill.
  — *Bubble-point / VLE basis for the §3.1 physics features (Ch. 13).* ⚠️ confirm
  edition/chapter at 1F.5.

---

### Open items for 1F.5 (collected)

1. IM-OCP page span (2888–2892 vs 2649–2653) — IEEE Xplore DOI lookup.
2. Corrupted-feedback (2605.20515) + Hou (2503.14453) final venues.
3. Papadopoulos LNCS 2430 page span.
4. Xu & Xie — ICML-2021 vs TPAMI-2023 version choice.
5. Gibbs & Candès — 2021 ACI vs 2022 arbitrary-shift paper, matched to the §3.4 equation.
6. Hastie 1-SE section number; Smith VLE chapter; Fortuna dataset citation form.
7. CACE house style: numbered vs author–year; convert to elsarticle .bib accordingly.
8. NORMALIZE in-text citation keys (audit found inconsistent forms across sections):
   - Lu: §2.2 uses "Lu & Gao 2008a/b" and "Lu et al. 2009" (correct); ensure no bare
     "Lu 2008" remains ambiguous between the two 2008 papers.
   - "Luo 2015" → "Luo et al. 2015"; "Yan 2011" → "Yan et al. 2011";
     "Shardt 2016" → "Shardt & Yang 2016"; "Papadopoulos 2002" → "Papadopoulos et al.
     2002". (All resolve to single entries; this is key-string hygiene for BibTeX.)
