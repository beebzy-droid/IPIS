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

### Results (exports received 2026-10-22)

Bien sent 12 Scopus CSV files and 8 Web of Science Excel files on 2026-10-22: 533 records.
- **Which file is which query.** Each file was matched to its query by applying the issued
  strings to its records (`scripts/sweep/n1_screening.py`). Every record of every file meets its
  string, so the strings ran as issued. The one exception is an S2 record whose match turns on how
  Scopus tokenises "Al2O3". The REF() strings of S9 to S11 cannot be checked from an export.
- **Hits** are the records exported. No export reached a database limit.
- **Run date.** Every WoS record carries its export date, 2026-10-22. The Scopus files carry none
  and arrived the same day.
- **Not received:**
  - S4: the two "Claim ii" files are byte-identical copies of the S3 export;
  - W9 and W10, the cited-reference searches.

| ID | Run date | Hits | Exported file | Screened | Read in full (not reached) | Bearing on F4 or Section 3D |
|---|---|---|---|---|---|---|
| S1 | 2026-10-22 | 56 | Claim_i_delayed_feedback_in_conformal_methods.csv | 56 | 3 (4) | Rows 22, 30, 31; none fires. Most hits use "latency" as a system metric |
| S2 | 2026-10-22 | 39 | Claim_i_step_size_and_stability_of_the_adaptive_loop.csv | 39 | 2 (1) | Rows 23, 24, 31 |
| S3 | 2026-10-22 | 2 | Claim_ii_delay-limited_width_bound_1.csv (_2 identical) | 2 | 0 | Both use "conformal" in another sense (a LiDAR transformation, an acoustic array) |
| S4 | | | Not received | | | To run and export |
| S5 | 2026-10-22 | 18 | Claim_iii_a_forecaster_ahead_of_an_online_conformal_loop.csv | 18 | 1 (1) | Rows 27, 31 |
| S6 | 2026-10-22 | 3 | Process_domain_1.csv | 3 | 0 | Two interval soft sensors under scarce or delayed laboratory labels, neither conformal (Blazic et al. 2024, Appl. Soft Comput.; Ma et al. 2026, Sensors) |
| S7 | 2026-10-22 | 7 | Process_domain_2.csv | 7 | 0 | Classical Smith predictors; no interval method |
| S8 | 2026-10-22 | 10 | TEP_random-number_defect.csv | 10 | 0 | Row 32 |
| S9 | 2026-10-22 | 129 (128 unique) | Forward_citations_REF_searches_reference_lists_1.csv | 128 | 7 (2) | Rows 23, 26, 30, 31 |
| S10 | 2026-10-22 | 72 | Forward_citations_REF_searches_reference_lists_2.csv | 72 | 2 | Rows 26, 30 |
| S11 | 2026-10-22 | 54 | Forward_citations_REF_searches_reference_lists_3.csv | 54 | 0 | 52 match only on reference lists in physics and queueing theory |
| S12 | 2026-10-22 | 33 | Forward_citations_REF_searches_reference_lists_4.csv | 33 | 5 (4) | Rows 22 to 24, 30, 31 |
| W1 | 2026-10-22 | 40 | savedrecs.xls | 40 | 4 (3) | Rows 22, 29 to 31 |
| W2 | 2026-10-22 | 30 | savedrecs_1.xls | 30 | 1 | Row 24 |
| W3 | 2026-10-22 | 3 | savedrecs_2.xls | 3 | 1 | Row 28 |
| W4 | 2026-10-22 | 4 | savedrecs_3.xls | 4 | 0 | Empirical interval widths (solar forecasting, biomass); no bound |
| W5 | 2026-10-22 | 15 | savedrecs_4.xls | 15 | 1 (1) | Rows 27, 31 |
| W6 | 2026-10-22 | 3 | savedrecs_5.xls | 3 | 0 | As S6 |
| W7 | 2026-10-22 | 2 | savedrecs_6.xls | 2 | 0 | As S7 |
| W8 | 2026-10-22 | 11 | savedrecs_7.xls | 11 | 0 | Row 32 |
| W9, W10 | | | Not received | | | To run and export |

**Screening.** The 533 records (531 with S3 counted once) reduce to 377 unique ones:
- 362 are in Scopus and 105 in WoS, 90 in both. WoS adds 15 records that Scopus lacks.
- Every title and abstract was screened. The log
  (`docs/module1/sweep/N1_database_screening_2026-10-22.csv`) gives each record a code:

| Code | Meaning | Records |
|---|---|---|
| X1 | "conformal" only in another sense (coatings, antennas, meshes, physics) | 25 |
| X2 | no conformal or interval method in the title or abstract (a reference-list or keyword match) | 108 |
| X3 | a conformal or interval method that bears on none of F4 (i) to (iii) or Section 3D | 201 |
| X4 | already in this record or the project library | 6 |
| X5 | uses TEP data or the simulator; nothing on its random-number generator | 11 |
| X6 | classical dead-time compensation, without intervals | 3 |
| F | may bear; read in full (rows 22 to 24 and 26 to 30) | 16 |
| A | may bear; full text not reached from the workspace (row 31) | 7 |

The raw exports stay out of git: the database terms restrict redistribution, and the abstracts
belong to the publishers. The summary beside the log records each file's SHA-256.

Scopus and WoS do not index arXiv. A web search on 2026-10-22 therefore looked for the same three
ideas in preprints. It found the paper of row 21, the two preprints of row 25 and the TEP source
of row 32. None of these four is in either database.

## Database sweep: full-text reads, 2026-10-22

| # | Source | Finding | Bearing on N1'' |
|---|---|---|---|
| 21 | Wang and Hyndman, "Online conformal inference for multi-step time series forecasting", arXiv 2410.13115 (v1 17 Oct 2024, v2 Feb 2026; Monash EBS working paper 20/2024; R package conformalForecast). Not in Scopus or WoS; found by web search; full text read | **The loop.** Multi-step conformal PID (MPID) and AcMCP, q_{t+h\|t} = q_{t+h-1\|t-1} + eta (err_{t\|t-h} - alpha) + r_t(sum of past errors) + e~_{t+h\|t} (Eq. 8). Sec. 3.4: "The "P" control shows an h-period delay in updating the quantile estimate". **The forecaster.** e~ combines an MA(h - 1) model fitted to the h-step errors observed by t with a regression on shorter-horizon errors (Sec. 4.2). **Theory.** Cor. 1 bounds the coverage gap of the plain delayed iteration by (b + eta h) / (eta (T - h)). Prop. 3: "increasing the forecast horizon h amplifies in-sample deviations from the target coverage". **The ablation.** AcMCP is compared with the same loop without e~ (MPI). On local coverage the comparison is one figure, on the electricity data: Fig. 8 plots coverage over rolling windows of 100 for MPI, MPID and AcMCP, and Sec. 5.3 says "MPI and AcMCP display similar coverage pattern, AcMCP is capable of constructing narrower intervals than MPI". Elsewhere MPI appears only in interval bounds (Fig. 4, AR(2)) and in full-sample coverage per horizon (Fig. 11, eating out: "compared to MPI, AcMCP exhibits slightly less deviation from the desired coverage across most forecast horizons"). Table 1 gives the minimum and maximum local coverage of MACP and AcMCP only. **Not analysed.** The step size is eta = 0.01 B_t at every horizon, and the paper says "our methodology does not incorporate an automated procedure for tuning the learning-rate parameter". It counts no miss runs and gives no width bound | **(i) does not fire**: there is no stability limit, noise gain, infinite share or step-size rule. Cor. 1 is, however, the analogue of P2's bound for the same single-state delayed recursion, in quantile space, and it predates N1''. P2's origin is corrected (PHASE1_PREREGISTRATION Section 4). **(ii) does not fire.** **(iii) fires on its local-coverage clause.** This is a residual forecast ahead of a delayed online conformal loop, compared with the loop without it, on local coverage. That meets two of the three conditions of PHASE1_PREREGISTRATION A.6: the forecaster is isolated, and the delay is recognised and varied. The third, an analysis of step size or miss persistence, is absent. The evidence is thin (one dataset, one figure, a finding of no difference), and a lenient reading would not fire. The strict reading is taken, because it can only make N1'' claim less. For claim 2, see the verdict below and D-P1.12 |
| 22 | Dixit, Lindemann, Wei, Cleaveland, Pappas and Burdick, "Adaptive conformal prediction for motion planning among dynamic agents", L4DC 2023, PMLR 211 (S1, S12, W1); full text read | The tau-step ACP uses "the tau step-ahead prediction error that was made tau time steps ago" (Eq. 4). Coverage is proved for one step only: "only the one step-ahead prediction errors are relevant" (Thm 3). MPC infeasibility "arises during sudden changes in the size of the uncertainty sets when the learning rate gamma is chosen too large" (Sec. 5) | (i) Does not fire: the delayed update is run, not analysed. It is the earliest delayed-feedback ACI found; to cite |
| 23 | Hallberg Szabadvary, "Adaptive conformal inference for multi-step ahead time-series forecasting online", COPA 2024, PMLR 230 (S2, S9, S12); full text read | One ACI per step, each updated with its own step's error once that error is observed (Eq. 6 to 8). The ACI bound is restated per step (Eq. 9, 10). Sec. 3: "it would therefore seem natural to set the learning rates successively larger the further ahead we predict". Sec. 4.3: "If the learning rates are chosen too high, there is a risk of loosing stability", seen in one figure. Its one per-step learning-rate example changes the target error at the same time | (i) Does not fire. The heuristic runs against P1, whose stability limit 2 sin(pi / (4 theta + 2)) falls as the delay grows; the manuscript can say so |
| 24 | Zaffran, Feron, Goude, Josse and Dieuleveut, "Adaptive conformal predictions for time series", ICML 2022, PMLR 162 (S2, S12, W2); full text read | Theta = 0 only. Thm 3.1, exchangeable scores: the average length grows linearly with gamma. Thm 3.2, AR(1) residuals: (alpha_t, eps_{t-1}) is a Markov chain with a unique stationary law; the efficient gamma is found numerically and is not monotone in phi (Fig. 2). Sec. 3.2: "very large gamma cause the algorithm to be less stable and produce numerous infinite intervals" | (i) Does not fire. It is prior art for the step-size trade-off on autocorrelated residuals without delay, which the noise-gain discussion (O2) cites. N1 claims only the dependence on the delay |
| 25 | Web search, 2026-10-22, for preprints. (a) Li, Menacho and Rodriguez, "Optimization-based online conformal prediction for multi-step forecasting", arXiv 2508.13362. (b) Skalse, Pona, Simeone and Paoletti, "Online conformal prediction beyond feedback", arXiv 2608.07139 (Aug 2026). Both read | (a) Per-horizon updates wait for their feedback ("Let tau = t - h, and observe y_t for the horizon-h prediction issued at tau", Alg. 1), with long-run coverage. Its Lemma 1 states a level bound of [-gamma, 1 + gamma]; P2 gives [-gamma(theta + 1), 1 + gamma(theta + 1)] for the delayed recursion (to check before citing). (b) Rounds have no label unless the learner queries one | (i) Neither fires: no stability, step-size or persistence analysis |
| 26 | Li and Rodriguez, "Neural conformal control for time series forecasting", AAAI 2025 (S9, S10); full text read | A network replaces quantile tracking, at horizons of 1 to 4 weeks. In training, errors not yet observed are padded with ones. Outcome delay is not analysed, and no ablation of the auxiliary data under delay is run | (iii) Does not fire |
| 27 | Retzlaff, Schlembach, Bams and Dreesen, "Testing marginal and conditional coverage in conformal prediction for non-stationary time series via Value-at-Risk backtesting", COPA 2025, PMLR 266 (S5, W5); full text read | Binomial tests (Kupiec 1995), independence and conditional-coverage tests (Christoffersen 1998; a dynamic binary test; a geometric test on the gaps between misses), applied to split CP, CQR, ACI and NexCP. On 98 stocks, ACI passes the two-sided binomial test on 97 and the geometric independence test on 10: it "secures stable coverage but misses local structures". No delay | Not an F4 item. It bears on P2 and the blindness claim (O4): that marginal coverage hides clustered misses in ACI is already shown, empirically and without delay. N1 claims the mechanism under delay and the uninformative share. Its geometric test is a ready statistic for miss persistence |
| 28 | Knuppel, "Forecast-error-based estimation of forecast uncertainty when the horizon is increased", Int. J. Forecasting 34 (2018) (W3); Bundesbank DP 40/2014 read | Estimates the h-step forecast-error variance, sigma^2 sum_{i<h} b_i^2 in Wold form, jointly across horizons by SUR. No intervals, no conformal method, no bound | (ii) Does not fire. P3 rests on the classical identity (Box and Jenkins; Harris 1989), cited as such |
| 29 | "Online multiscale conformal calibration for response-defined wind-ramp groups", Processes 14 (2026) 3119 (W1); read | Per-horizon controllers with an event queue, so that feedback "becomes eligible only when v_i <= t at a subsequent issuance"; "Target-time sorting alone does not enforce this rule". A post-review audit found premature feedback in the paper's own earlier evaluation, which was then reanalysed. Thm 1 bounds group miscoverage, with a term that pending feedback can leave positive. No stability or step-size analysis | (i) Does not fire. A published instance of the evaluation error that the delay convention prevents; usable in the introduction |
| 30 | Nine applications read in full (S1, S9, S10, S12, W1). Delay-compensated teleoperation (CCTA 2025): offline split CP; the compensator acts on control commands. ConformIDS (IJIES 2026): ACI window W* = L*(1 + rho_1) / (1 - rho_1) under AR(1), with the step size set separately and label delay tested only empirically. Certified inventory control (Oper. Res. Lett. 2026): no lead time. Conformal control of storage arbitrage (e-Energy 2026): a temporal-difference proxy for a delayed value, with a one-step lag. CUQDS (AAAI 2025): no delay handling. On-line conformalized ensembles for day-ahead prices (Appl. Energy 2025): conformal PI control; delay not discussed. Egocentric CP in MPC (CDC 2025): per-step ACP with lagged feedback. Feedback-enhanced online multiple testing (JMLR 2026): FDR control, no interval loop. Signed ACI for multi-horizon wind (Energies 2026): per-horizon updates once labels arrive, eta fixed at 0.02 | None analyses a delayed loop's stability or step size, or a forecaster's effect on miss persistence | (i) and (iii) do not fire |
| 31 | Seven records that may bear; full text not reached from the workspace (paywall or rate limit). (a) Qiu et al., sensitivity-aware proactive conformal prediction for PEMFC prognostics, IEEE Trans. Transp. Electrif. 2026: the abstract says ACP's "dependence on delayed label feedback" is met by a proactive proxy. (b) Meng et al., a soft sensor with "PID-guided conformal inference", Measurement 2026: two processes, label delay not stated. (c) Five applications with delayed feedback: IEEE Access 2026; Aerosp. Sci. Technol. 2027; J. Supercomput. 2026; Energies 2026; LNCS 2025 | No abstract states an analysis of a delayed loop | Abstract-level verdict: none fires. To read before submission, (a) and (b) first. (a) is the abstract closest to claim 2. If (b) runs conformal PID on the debutanizer, Section 5.3's conformal PID baseline has a process precedent, and the positioning in rows 5 and 7 changes |
| 32 | Section 3D. Databases: S8 (10 records) and W8 (11). Web, 2026-10-22: Kitchin, tep-rust, a Rust port of the TEP simulator (github.com/jkitchin/tep-rust, HEAD 0735ad3 of 2026-10-20; LOG.org and the book read) | **Databases.** No record mentions TEP's generator. All use the simulator or its data, several with "N random seeds" for their own training. **tep-rust** reproduces TESUB7 bit for bit. Its log records three things. G * 9228907 exceeds 2^53 on 0.7716 of draws, so "rounding is part of the algorithm" (B-0005, 2026-08-10). 27 of the 54 dataset seeds in teprob.f are even, so "those runs have a shorter period and low bits that never move" (B-0047a, 2026-08-28). And a cycle search found "no return to the starting state within 2e9 states" (2026-08-29) | **The precision loss is reported** (Kitchin 2026). **The defect of Section 3D is not.** Rounding adds trailing zero bits to every seed's state until G = 2^k m. After that the stream cycles with period 2^(30 - k) draws, 0.55 to 141 h, and seeds share the cycles. A search for a return to the starting state cannot see such a cycle, because the state never returns to its start. Section 3D is corrected to cite Kitchin |

## Verdict of the database sweep, 2026-10-22

- **F4 (i) does not fire.**
  - The closest are El Halabi and Brandt (row 2), Wang and Hyndman's Cor. 1 (row 21), Dixit et
    al. (row 22), Szabadvary (row 23) and Zaffran et al. (row 24).
  - None gives the stability limit, the noise gain, the infinite share or a delay-dependent
    step-size rule of the single-state loop.
  - P2's bound is not new: Wang and Hyndman's Cor. 1 is its analogue in quantile space.
- **F4 (ii) does not fire** (rows 21, 28; W4 holds only empirical widths).
- **F4 (iii) fires on its local-coverage clause** (row 21).
  - Wang and Hyndman compare a delayed P + I loop with and without a residual forecast on
    coverage over rolling windows (electricity, Fig. 8), and find a "similar coverage pattern".
  - They do not analyse the step size, which is fixed, or the persistence of misses.
  - The evidence is thin, and the strict reading is taken because it can only claim less.
  - As ratified, claim 2 leaves the claims. D-P1.12 proposes to keep a narrowed claim 2':
    persistence and step size, with the delay varied at a fixed predictor. Local coverage is
    then reported, not claimed. Bien decides (PHASE1_PREREGISTRATION Section 9).
- **Section 3D**: the precision loss is Kitchin's (2026). The eventual short cycles and their
  sharing across seeds remain unreported (row 32).
- **Process positioning.** "No conformal soft sensor under laboratory delay" (rows 5 and 7)
  still holds in both databases, subject to row 31 (b).

Constraints added to the list at the top:
- P5. Cite Wang and Hyndman (2024) for the multi-step delayed loop, its coverage bound (Cor. 1)
  and the forecaster ahead of it (AcMCP against MPI). Claim none of the three.
- P6. Cite Zaffran et al. (2022) for the step-size trade-off and the infinite intervals on AR(1)
  residuals without delay.
- P7. Cite Dixit et al. (2023) and Szabadvary (2024) for delayed-feedback ACI. State that the
  stability limit falls with the delay, against the latter's heuristic.
- P8. Cite Retzlaff et al. (2025) for marginal coverage hiding clustered misses. P2 is the
  mechanism under delay.
- P9. Cite Kitchin (2026) for TESUB7's precision loss. Claim only the eventual short cycles and
  their sharing across seeds.
- P10. Appendix A's matched conformal PID has AcMCP's structure, and the manuscript says so.

Still due before submission:
- S4, W9 and W10: run, record the hit counts and export.
- Google Scholar (THESIS_STANDARDS L7), which also reaches arXiv. Add the family of terms that
  missed row 21: "multi-step" or "multi-horizon" with "online conformal" and "forecast errors".
- Row 31: read the seven records, (a) and (b) first.
