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
| 10 | conformal calibration, industrial analyzer delay, soft-sensor prediction intervals, 2026 | arXiv 2512.23602 (distribution-free process monitoring; in the project library); arXiv 2602.21478 read and found unrelated (inference after adaptive experiments); Zenodo record 19114006 (preprint, 2026-03-29) NOT read: the fetch was rate-limited | Zenodo 19114006 is to be read in the systematic sweep |

Verdict: on the web evidence, F4 still does not fire. The Scopus, Web of Science and Google
Scholar sweep (institutional access, owner-side) remains mandatory before submission, and must
include the unread Zenodo record above.

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
