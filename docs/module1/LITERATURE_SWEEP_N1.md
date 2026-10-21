# N1 literature sweep: falsification check F4 (2026-09-28)

Purpose: test whether the N1 claim is already published before six to ten weeks are spent
on it. Web searches only; a Scopus, Web of Science and Google Scholar repeat is mandatory
immediately before submission (THESIS_STANDARDS L7).

| # | Query or source | Key hits | Bearing on N1 |
|---|---|---|---|
| 1 | online conformal prediction, delayed feedback labels, ACI delay | El Halabi and Brandt, arXiv 2609.07251 (7 Sep 2026); Wang, Zecchin and Simeone, IM-OCP (IEEE SPL 2025); corrupted-feedback OCP (arXiv 2605.20515) | Delayed-feedback coverage theory exists; intermittent feedback exists |
| 2 | arXiv 2609.07251, full text read | Recursion alpha_{t+tau} = alpha_t + gamma(alpha - err_t): tau interleaved chains; long-run and marginal bounds; delay-to-memory ratio; queued (set, level) pairs; Fig. 18 selects gamma* per delay empirically | Their recursion avoids dead-time feedback; the single-state recursion is not analysed |
| 3 | conformal prediction with Smith predictor or dead-time compensation | Classical process-control Smith-predictor work only | No conformal dead-time compensation found |
| 4 | ACI step size, oscillation, feedback delay, stability | Gibbs and Candes 2021 S2.1 (large gamma makes the level volatile; gamma = 0.005 chosen empirically); Angelopoulos, Barber and Bates 2024 (decaying step sizes); arXiv 2511.04275 (oscillation noted qualitatively); arXiv 2607.05882 (projected ACI on [0.01, 0.50] with delayed feedback events) | Qualitative instability known; no delay-dependent quantitative analysis found |
| 5 | conformal prediction, soft sensor, industrial, prediction interval, laboratory delay | Prediction-interval soft sensors (CILS 2019, fuzzy granulation and ELM); Bayesian soft sensor for delayed and integrated measurements (IEEE TIM 2022); moving-window calibration on the debutanizer with delayed updates (arXiv 1710.11595) | No conformal soft sensor under laboratory delay found; industrial relevance of lab delay confirmed |

## Verdict

F4 does not fire. The N1 contribution that survives the sweep is quantitative and specific:
the single-state delayed recursion analysed as a stochastically driven integral loop with dead
time; a noise-gain model that predicts level volatility and the share of infinite intervals;
an analytical, delay-dependent step-size rule; the demonstration that marginal coverage
cannot see the failure; validation on process soft sensors at industrial delays.

## Constraints the manuscript must respect

- P1. Cite Gibbs and Candes (2021) for the qualitative volatility; do not claim it.
- P2. Cite El Halabi and Brandt (2026) for delayed-feedback coverage and for empirical
  per-delay step-size selection; claim only the analytical single-state rule.
- P3. Include the baselines a reviewer will ask for: projected ACI, decaying step sizes,
  phase-interleaved tau-DACI; DtACI if feasible.
- P4. Cite the delayed-feedback online-learning literature for the regret view. Candidate
  references from general knowledge, NOT yet verified: Joulani, Gyorgy and Szepesvari (ICML
  2013); Quanrud and Khashabi (NeurIPS 2015). Verify before citing.

## Update sweep, 2026-10-09 (web only; M1 session)

| # | Query or source | Key hits | Bearing on N1 |
|---|---|---|---|
| 6 | adaptive conformal inference, delayed feedback, step size, stability (extended search) | arXiv 2609.07251 still at v1 (7 Sep 2026); no citing or follow-up work listed (pith.science record) | No single-state dead-time analysis found |
| 7 | conformal prediction, soft sensor, delayed laboratory labels, online calibration | Only items already known (arXiv 1710.11595; online soft-sensor calibration tools) | No conformal soft sensor under laboratory delay found |
| 8 | online conformal, delayed labels, dead time, integral controller | Classical control results only | No conformal dead-time analysis found |
| 9 | label delay or delayed labels, conformal prediction, time series, 2026 | arXiv 2609.07251; Gauthier, Bach and Jordan, "Adaptive Coverage Policies in Conformal Prediction" (PMLR vol. 300, 2026; arXiv 2510.04318): abstract read, per-example coverage levels via e-values, batch calibration | Unrelated: no delay, no step size, no streaming |
| 10 | conformal calibration, industrial analyzer delay, soft-sensor prediction intervals, 2026 | arXiv 2512.23602 (distribution-free process monitoring; in the project library); arXiv 2602.21478 read and found unrelated (inference after adaptive experiments); Zenodo record 19114006 (preprint, 2026-03-29) NOT read: the fetch was rate-limited. Read 2026-10-20: Simm, Hoose and Beucler (KIT and Lausanne), "Calibrated Conformal Prediction Intervals for Microphysical Process Rates", v1.0, a software record (data and code, 2.9 GB) for a manuscript tied to Climate Informatics 2026. The record has no abstract; its title and description mention no delayed labels, soft sensors, online updates, step sizes or time series | Unrelated on its title and description; the manuscript itself is not on the record. The database sweep would catch it if it were relevant |

Verdict: on the web evidence, F4 still does not fire. The Scopus, Web of Science and Google
Scholar sweep (institutional access, owner-side) remains mandatory before submission, and must
include the unread Zenodo record above (read on 2026-10-20 and found unrelated; row 10).

Program-internal overlap, checked the same day. Module 5 (never submitted; draft in the private
repo) also runs delayed-label ACI, with stored pairing. Its dead-time figure reports only the
S_k validity rate and marginal interval coverage, at gamma = 0.02 for label delays of 0 to 8
cycles (`docs/module5/spec.md`). It does not analyse the single-state dead-time loop, so it does
not pre-empt N1. However, it reports exactly the statistics N1 shows to be blind. Flagged for the
M5 session as OI-17 in `docs/OPEN_ITEMS.md`.

## Update sweep, 2026-10-13 (web only; for the proposed claim N1'')

| # | Query or source | Key hits | Bearing on N1'' |
|---|---|---|---|
| 11 | Conformal PID, full text (Angelopoulos, Candes and Tibshirani, NeurIPS 2023; arXiv 2307.16895), re-read after the independent check | Quantile tracking, an integrator and a "scorecaster". The scorecaster forecasts the quantile of the next score; in the COVID experiment, the quantile of the score at t + 4 from data available at t, matching the 4-week horizon (Sec. 1.2, App. E). The paper does not say whether the quantile-tracking update waits for the delayed outcome, and does not discuss delayed feedback, dead time or stability. Learning rate eta = 0.1 B_t, a fraction of the trailing maximum score; "extremely high learning rates result in volatile sets" (Sec. 2.1). Code: github.com/aangelopoulos/conformal-time-series | Forecasting at the label horizon is prior art. N1'' does not claim it. Required baseline (PHASE1_PREREGISTRATION Sec. 5.3) |
| 12 | Sequential predictive conformal inference, full text (Xu and Xie, ICML 2023, PMLR 202; arXiv 2212.03463), re-read after the independent check | Predicts conditional quantiles of the future residual from the past w residuals with a quantile random forest (sklearn-quantile); builds on EnbPI. Multi-step version (Sec. 5.2, App. B.3, Algorithm 3): one forest per horizon, labels revealed only every S steps. Coverage: finite-sample under exchangeability (split variant), asymptotic conditional coverage under stated assumptions otherwise. The experiments do not report w or the forest settings | A residual-dynamics method at the label horizon, without a feedback loop, step size or width bound. It is the conditional EnbPI R4.9 asked for: required baseline at horizon theta + 1 |
| 13 | Conformal time-series benchmark (Sabashvili, arXiv 2601.18509, Jan 2026) | Groups methods into relaxed-exchangeability, multi-series, residual-dynamics and online-learning families; benchmarks with AutoARIMA | No delayed-feedback treatment |
| 14 | Minimum-variance (Harris) benchmark applied to soft sensors or prediction intervals under laboratory delay | Industrial blog posts and patents on analyzers in control loops; Mojto et al. (arXiv 2106.13503) on refinery inferential sensors, without delays or intervals | No delay-limited bound on interval width found |
| 15 | (2026-10-17) Tennessee Eastman simulator random-number generator: period, repetition, seeds and independent runs (two web searches) | Bathelt, Ricker and Jelali (2015; in the project library) revised the random-number generation to separate the disturbance and noise states, for solver independence, and do not mention precision or period. Also found, not read: Reinartz et al. (2021, an extended TEP data set) and Capaci et al. (2019, the revised TEP as a testbed for SPC and DoE) | No report found of TESUB7 losing precision in double arithmetic or of its short, shared cycles (PHASE1_PREREGISTRATION Sec. 3D). To be checked in the systematic sweep before any claim of novelty |

Correction, 2026-10-13: as first written, row 11 left out that conformal PID's scorecaster
forecasts at the 4-week label horizon, and asserted an update timing that the paper does not
state; row 12 described SPCI as one-step only. An independent check found these errors, and both
rows were rewritten after the full texts were read again. The claim was narrowed accordingly
(PHASE1_PREREGISTRATION Section 4): N1'' does not claim forecasting at the label horizon.

Verdict: on the web evidence, F4 does not fire for N1'' as narrowed. The Scopus, Web of Science
and Google Scholar sweep must add these queries:
- "conformal" with "Smith predictor", "minimum variance", "Harris" or "dead time";
- "conformal" or "prediction interval" with "width bound" and "autocorrelation";
- "prediction interval width" with "forecast horizon" and "forecast error variance";
- "conformal" with "scorecaster" or "residual forecast" and "delayed feedback", "step size" or
  "local coverage" (F4 item iii: claim 2);
- "soft sensor" with "prediction interval" and "analyzer delay";
- forward citations of conformal PID and of SPCI;
- "Tennessee Eastman" with "random number generator", "seed", "period" or "independent runs".

## Code reading, 2026-10-20 (for the baseline configurations, PHASE1_PREREGISTRATION Appendix A)

| # | Source | Finding | Bearing on N1'' |
|---|---|---|---|
| 16 | aangelopoulos/conformal-time-series, commit b729c3f, `core/methods.py` | With `ahead` = h, the update that sets the quantile for sample t + 1 uses the coverage error of sample t + 1 - h (lines 216-222). The quantile tracker is then the single-state loop with dead time theta = h - 1, in quantile space. The paper's 4-week COVID experiment runs it with ahead = 4. Neither the code nor the paper analyses its stability, its step size or its share of uninformative sets under the delay | F4 (i) does not fire. The loop N1' analyses is the one the reference implementation of a leading method runs at a 4-step horizon, which supports the relevance of claim 1. Usable in the introduction, cited to the commit |
| 17 | Same file, lines 229-235 | The Theta scorecaster adds to q_{t+1} a forecast of the score of sample t, made without it, at ahead = 1. At ahead >= 2 it stops with "setting an array element with a sequence". Aligned as the paper describes, and with the integrator and learning-rate window of Appendix A.2, it halves the median set size on the paper's Table 2 data (0.178 to 0.085, coverage 0.900 in both; `docs/paper/evidence/baseline_reproduction.json`; 0.084 under the first version of Appendix A) | The baseline is run aligned (Appendix A), its stronger form. A reproducibility note, not a claim |
| 18 | hamrel-cxu/SPCI-code, commit d598dd3, `SPCI_class.py` | The residual window w is 300 for the electric and wind data, 200 for solar and 500 for the simulations, none of which the paper reports. The forest has 10 trees of depth 2. For stride S > 1, beta-hat is chosen at the window that ends S - 1 steps before the query | Settings for Appendix A |
| 19 | Conformal PID paper, Sec. 1.2, Table 1 and App. F (NeurIPS version), read with row 16 | The COVID experiment ran quantile tracking whose feedback the code delays by 3 steps (ahead = 4), with a quantile-regression scorecaster ahead of it. Table 1 reports a longest error run of 2 against 6 for the uncalibrated base forecaster. The paper does not mention the delay and does not run the loop without the scorecaster | F4 (iii) screened, does not fire: Table 1 compares conformal PID with the base forecaster, not a delayed loop with and without a forecaster, and gives no analysis of miss persistence, step size or local coverage against the delay. Section 4's "without delays" is corrected in PHASE1_PREREGISTRATION Appendix A.6. Added 2026-10-20 (second check): Sec. 3.3, "The effect of scorecasting", credits scorecasting with "significant improvement in coverage and set sizes" (Figs. 2 and 3) and "similar benefits" on COVID (App. F); Figs. 2, 9 and 10 plot 10-week trailing coverage of conformal PID against the base forecaster at the 4-week horizon. Still no ablation of the scorecaster, no recognition or variation of the delay, and no step-size or persistence analysis, so the verdict stands with a narrower margin; the manuscript cites Sec. 3.3 and these figures (Appendix A.6) |
| 20 | Same paper, App. F, and the authors' notebook `tests/datasets/covid-ts-proc/statewide/death-forecasting-perstate-lasso-qr.ipynb` | The scorecaster is `QuantileRegressor(quantile=0.9, alpha=10, solver="highs")` on lags 4, 5 and 6 of the score, trained on the 10 most recent points. A penalty of 10 sets every slope to zero at score scales from 1e-5 to 1 (checked on AR residuals), so in effect it is a quantile of recent scores | Appendix A's scorecaster (a) keeps the model class, the level and the lags, without the penalty |

Correction, 2026-10-20: rows 11 and 12 cite appendix letters of the arXiv versions. In the NeurIPS
version of the conformal PID paper the COVID details are in App. F (arXiv v1: App. E). SPCI's
Algorithm 3 is printed in App. C of arXiv v3, and App. B.3 refers to it.

## Database sweep protocol, 2026-10-20 (Scopus and Web of Science; owner-side)

Issued to Bien on 2026-10-20 after the ratification of D-P1.7 to D-P1.9. The strings below are
the ones issued, verbatim; a string the database rejects is corrected here, with the date, before
it is run. Each query is run once and its hit count recorded with the run date. Its records are
exported (Scopus: CSV with citation information, abstract and keywords; WoS: Excel, Full
Record). Every title and abstract is screened against F4 (i) to (iii)
(`PHASE1_PREREGISTRATION.md`, Section 6) and against the TEP random-number finding (Section 3D).
A record that may bear on either is read in full, and its verdict is entered as a numbered row
below. The syntax follows the databases' advanced-search rules as known on 2026-10-20; the strings
were not test-run before issue.

It implements the 2026-10-13 list above:
- Smith predictor, minimum variance, Harris, dead time: S1, S3, S7; W1, W3, W7.
- Width with autocorrelation or forecast horizon: S3, S4; W3, W4.
- Scorecaster or residual forecast with delay, step size or local coverage: S5; W5.
- Soft sensor with intervals and analyzer delay: S6; W6.
- Forward citations of conformal PID and SPCI: S9, S10; W9, W10.
- TEP random numbers: S8; W8.

It adds:
- step size and stability of the adaptive loop: S2; W2;
- forward citations of delayed-feedback conformal work and of ACI with delay terms: S11, S12.

Google Scholar is not covered here and remains due before submission (THESIS_STANDARDS L7).

### Scopus (Advanced search)

S1, F4 (i): delayed feedback in conformal methods
```
TITLE-ABS-KEY ( ( conformal W/2 ( predict* OR inference OR calibrat* OR interval* ) ) AND ( ( delay* W/1 ( feedback OR label* OR observation* OR outcome* OR measurement* OR response* ) ) OR "dead time" OR deadtime OR latency ) ) AND PUBYEAR > 2004
```
S2, F4 (i): step size and stability of the adaptive loop
```
TITLE-ABS-KEY ( ( "adaptive conformal" OR "online conformal" OR "conformal PID" OR "quantile tracking" OR ( conformal W/3 ( online OR adaptive OR sequential ) ) ) AND ( "step size*" OR "learning rate*" OR stabilit* OR oscillat* OR "limit cycle*" OR ( integral W/2 control* ) OR "control theoretic" ) ) AND PUBYEAR > 2004
```
S3, F4 (ii): minimum-variance or forecast-error bound
```
TITLE-ABS-KEY ( ( conformal OR "prediction interval*" OR "predictive interval*" ) AND ( "minimum variance" OR "Harris index" OR "control performance assessment" OR "forecast error variance" OR "prediction error variance" ) AND ( delay* OR "dead time" OR horizon* ) )
```
S4, F4 (ii): interval width against autocorrelation, horizon or analyzer delay
```
TITLE-ABS-KEY ( ( ( "prediction interval*" OR conformal ) W/10 width ) AND ( autocorrelat* OR "forecast horizon*" OR ( analy?er W/2 ( delay* OR speed OR cycle ) ) ) AND ( bound* OR limit* OR achievable OR minimum ) )
```
S5, F4 (iii): a forecaster ahead of an online conformal loop
```
TITLE-ABS-KEY ( conformal AND ( scorecaster* OR ( ( score OR residual* OR quantile* ) W/2 ( forecast* OR predict* OR model* ) ) ) AND ( online OR adaptive OR sequential OR "time series" ) AND ( delay* OR "multi-step" OR multistep OR horizon* OR "local coverage" OR "conditional coverage" OR "step size" OR "learning rate" ) ) AND PUBYEAR > 2004
```
S6, process domain: soft sensors with intervals under delayed or irregular labels
```
TITLE-ABS-KEY ( ( "soft sensor*" OR "soft-sensor*" OR "inferential sensor*" OR "virtual sensor*" OR "virtual metrology" ) AND ( conformal OR "prediction interval*" OR "uncertainty quantification" OR "predictive uncertainty" ) AND ( ( delay* W/2 ( analy?er OR laborator* OR measurement* OR label* OR sampling ) ) OR "dead time" OR infrequent OR irregular* ) )
```
S7, process domain: dead-time compensation of intervals
```
TITLE-ABS-KEY ( ( conformal OR "prediction interval*" OR "uncertainty quantification" ) AND ( "Smith predictor*" OR ( ( "dead time" OR "dead-time" OR deadtime OR "time delay" OR "time-delay" ) W/2 compensat* ) ) )
```
S8, TEP random numbers
```
TITLE-ABS-KEY ( "Tennessee Eastman" AND ( "random number*" OR pseudorandom OR "pseudo-random" OR "random seed*" OR ( seed* W/3 ( independen* OR replicat* OR repeat* OR period* ) ) OR ( noise W/2 generat* ) ) )
```
S9 to S12, forward citations (REF searches reference lists)
```
REF ( angelopoulos AND "conformal PID" )
```
```
REF ( "sequential predictive conformal inference" )
```
```
REF ( conformal AND "delayed feedback" )
```
```
REF ( gibbs AND candes AND "adaptive conformal inference" ) AND TITLE-ABS-KEY ( delay* OR "dead time" OR latency OR "step size" OR "learning rate" )
```

### Web of Science Core Collection (Advanced search)

W1 to W8 mirror S1 to S8.
```
TS=((conformal NEAR/2 (predict* OR inference OR calibrat* OR interval*)) AND ((delay* NEAR/1 (feedback OR label* OR observation* OR outcome* OR measurement* OR response*)) OR "dead time" OR deadtime OR latency)) AND PY=(2005-2026)
```
```
TS=(("adaptive conformal" OR "online conformal" OR "conformal PID" OR "quantile tracking" OR (conformal NEAR/3 (online OR adaptive OR sequential))) AND ("step size" OR "step sizes" OR "learning rate" OR stabilit* OR oscillat* OR "limit cycle" OR "limit cycles" OR (integral NEAR/2 control*) OR "control theoretic")) AND PY=(2005-2026)
```
```
TS=((conformal OR "prediction interval" OR "prediction intervals" OR "predictive interval" OR "predictive intervals") AND ("minimum variance" OR "Harris index" OR "control performance assessment" OR "forecast error variance" OR "prediction error variance") AND (delay* OR "dead time" OR horizon*))
```
```
TS=((predict* NEAR/2 interval*) AND width AND (autocorrelat* OR "forecast horizon" OR analyzer OR analyser) AND (bound* OR limit* OR achievable OR minimum))
```
```
TS=(conformal AND (scorecaster* OR ((score OR residual* OR quantile*) NEAR/2 (forecast* OR predict* OR model*))) AND (online OR adaptive OR sequential OR "time series") AND (delay* OR "multi-step" OR multistep OR horizon* OR "local coverage" OR "conditional coverage" OR "step size" OR "learning rate")) AND PY=(2005-2026)
```
```
TS=(("soft sensor" OR "soft sensors" OR "soft-sensor" OR "inferential sensor" OR "inferential sensors" OR "virtual sensor" OR "virtual sensors" OR "virtual metrology") AND (conformal OR "prediction interval" OR "prediction intervals" OR "uncertainty quantification" OR "predictive uncertainty") AND ((delay* NEAR/2 (analy?er OR laborator* OR measurement* OR label* OR sampling)) OR "dead time" OR infrequent OR irregular*))
```
```
TS=((conformal OR "prediction interval" OR "prediction intervals" OR "uncertainty quantification") AND ("Smith predictor" OR "Smith predictors" OR "dead time compensation" OR "dead-time compensation" OR "time delay compensation" OR "time-delay compensation"))
```
```
TS=("Tennessee Eastman" AND ("random number" OR "random numbers" OR pseudorandom OR "pseudo-random" OR "random seed" OR "random seeds" OR (seed* NEAR/3 (independen* OR replicat* OR repeat* OR period*)) OR (noise NEAR/2 generat*)))
```
W9 and W10, forward citations through Cited Reference Search (WoS Advanced search has no
reference-list field):
- W9: Cited Author `Angelopoulos A*`, Cited Year `2023`; select the entries for "Conformal PID
  control for time series prediction".
- W10: Cited Author `Xu C*`, Cited Year `2022-2023`; select the entries for "Sequential predictive
  conformal inference for time series".
- On each citing set: Refine, Search within results,
  `delay* OR "dead time" OR latency OR "step size" OR "learning rate"`.

### Results (to be filled from the exports)

| ID | Run date | Hits | Exported file | Screened | Read in full | Bearing on F4 or Section 3D |
|---|---|---|---|---|---|---|
| S1 to S12 | | | | | | |
| W1 to W10 | | | | | | |
