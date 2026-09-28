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
