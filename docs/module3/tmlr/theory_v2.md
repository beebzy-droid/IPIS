# Module 3 theory v2 (TMLR reforge): certify-then-deploy

**Status:** Gate 1 PASSED, 2026-09-25. Supersedes Theorems 1-2 of `paper2/tcst/main.tex`
(IEEE TCST 26-0876, rejected out of scope 2026-08-28). Evidence:
`docs/module3/tmlr/evidence/gate1_validation.json`, produced by
`scripts/paper2_tmlr/gate1_validate_theory.py` (seed 20260925).

## 1. Audit of the TCST version

| Result | Verdict | Defect | Disposition |
|---|---|---|---|
| Thm 1: marginal validity vacuous at the optimum | Correct | Existence only; no mechanism for why data-driven back-offs fail systematically | Kept as Prop. 1; mechanism added as Prop. 2 |
| Thm 2(a): fresh-sample recalibration | Inequality correct; conclusion overstated | (i) "so M(u*) <= alpha" holds only in expectation over the fresh sample, not with high probability; (ii) coverage of the recalibrated interval implies the chance constraint only if g_hat(u*) + C'(u*) <= g_bar is re-checked, which the statement omits | Subsumed by Thm 3 (J = 1 case, PAC form, explicit check) |
| Thm 2(b): data reuse, uniform calibration, sqrt(d/n) | **Invalid** | The proof bounds a supremum over the back-off class of the empirical *marginal* miss, then asserts a supremum over decisions u of a *pointwise* miss. The empirical miss as defined does not depend on u, so pointwise conditional validity uniformly in u does not follow. Distribution-free pointwise conditional coverage is impossible in general (Foygel Barber et al., 2021) | Withdrawn; replaced by Thm 3 |
| Related work | Gap | No comparison to the scenario approach or sampling-and-discarding, which already give distribution-free guarantees on optimized decisions | Both added as baselines |

**Dependency check (2026-09-25).** `paper4` handles selection through its own causal-timing
assumption (`03_framework.tex` L147-155) and never invokes Thm 2(b), so the defect does not
propagate. Separate finding: `paper4/03_framework.tex` L102 attributes the similarity-calibrated
conformal certificate to `busico_m3`; SCC is Module 2, so the key is likely `busico_m2`. Fix at
M4's next revision. No M3 result numbers (0.429, 0.449, 0.488, "fivefold") appear in paper4 or
paper5, so TMLR's no-reuse rule is not triggered by results; the twin description must still be
written fresh.

## 2. Setting

- Decision u in U (any set; no convexity required); exogenous disturbance z ~ P, unknown;
  constrained quality g(u, z); specification g <= g_bar. Violation V(u) := P_z(g(u, z) > g_bar).
  Target: V <= alpha at the deployed decision.
- Upstream data D_n, used arbitrarily (model fitting, back-off construction, tuning, reuse).
  Nominal model g_hat, base back-off C_0 >= 0, optimizer
  u*(kappa) in argmax { pi(u) : g_hat(u) + kappa C_0(u) <= g_bar }.
- Certification sample z'_1, ..., z'_m i.i.d. from P, independent of D_n. g can be evaluated at
  candidate decisions (validated simulator or pilot operation). The guarantee is relative to that g.
- Miss of a back-off C: M(u) := P_z(g(u, z) > g_hat(u) + C(u)). C is marginally valid over a
  reference rho if E_{u~rho} M(u) <= alpha.

## 3. Results

**Proposition 1 (marginal validity does not transfer to the optimized decision).** For every
alpha in (0, 1) and nu in [alpha, 1] there is an instance and a back-off C, marginally valid at
level alpha over rho = Unif(U), whose optimized decision has V(u*) = nu.

*Proof.* Partition U = A u B with rho(A) = alpha/nu, on an instance where
P_z(g(u, z) > g_hat(u)) >= nu on A. M(u) decreases continuously in C(u) from that value to 0, so
choose C with M = nu on A and M = 0 on B; then E_rho M = alpha. Choose pi so that the
constrained maximizer lies in A with the constraint active, g_hat(u*) + C(u*) = g_bar. Then
V(u*) = M(u*) = nu. QED

**Proposition 2 (optimizer's curse on an estimated back-off).** Order candidates u_1, ..., u_K
by profit, pi(u_1) > ... > pi(u_K). Let c_k := Q_{1-alpha}[g(u_k, z) - g_hat(u_k)] be the exact
margin and s_k := g_bar - g_hat(u_k) - c_k the true slack, so u_k is safe iff s_k >= 0
(continuous distributions). The back-off is c_hat_k = c_k + e_k with independent errors e_k. Let
k_0 := min{k : s_k >= 0}; the optimizer selects k* := min{k : e_k <= s_k}. Then

    P(V(u*) > alpha) >= 1 - prod_{k < k_0} P(e_k > s_k).

If s_k >= -eta for all k < k_0 and P(e_k <= -eta) >= p > 0, then
P(V(u*) > alpha) >= 1 - (1 - p)^(k_0 - 1), which tends to 1 as the number of profitable but
unsafe candidates grows, **even when every error is unbiased**.

*Proof.* Every k < k_0 is unsafe, so selecting a safe decision requires e_k > s_k for all
k < k_0. By independence this event has probability prod_{k<k_0} P(e_k > s_k). QED

Reading: a continuous RTO behaves like many weakly dependent candidates along the estimated
boundary, and the optimizer finds the pocket where the back-off estimate is most optimistic.
Unbiasedness gives no protection; only post-selection certification does.

**Theorem 3 (certify-then-deploy).** Fix kappa_1 > kappa_2 > ... > kappa_J before the
certification sample is drawn (the list may depend on D_n). Let u_j := u*(kappa_j), dropping
infeasible kappa; N_j := sum_i 1{g(u_j, z'_i) > g_bar}; and UCB_j the one-sided Clopper-Pearson
(1 - delta) upper bound for V(u_j) from N_j ~ Bin(m, V(u_j)). Certify in order and stop at the
first failure: j_hat := max{j : UCB_1 <= alpha, ..., UCB_j <= alpha}, with j_hat = 0 meaning
abstain. Deploy u_{j_hat}. Then

    P(j_hat >= 1 and V(u_{j_hat}) > alpha) <= delta,

and with probability at least 1 - delta every certified decision u_1, ..., u_{j_hat} satisfies
V <= alpha simultaneously, so any further choice among them remains valid.

*Proof.* Condition on D_n. The u_j are then fixed, and by independence of the certification
sample N_j ~ Bin(m, V(u_j)), so P(UCB_j < V(u_j)) <= delta for each j (Clopper and Pearson,
1934). Let j_dag := min{j : V(u_j) > alpha}. Certifying any unsafe decision requires
j_hat >= j_dag, hence UCB_{j_dag} <= alpha < V(u_{j_dag}), an event of probability at most
delta. Integrate over D_n. QED

Remarks. (i) No assumption on g_hat, C_0, the optimizer, convexity, or how D_n was reused.
(ii) Monotonicity of V in kappa matters for power, not validity. (iii) The fixed sequence costs
no multiplicity correction; this is the fixed-sequence principle used for risk control in
Learn-then-Test (Angelopoulos et al.). (iv) The decision dimension d does not enter: the
certification sample size is dimension-free, whereas scenario sample sizes grow linearly in d.

**Corollary 4 (certification budget; abstention as the data-adequacy signal).** A decision with
true violation v < alpha is certified with probability P(N <= n_max(m)), N ~ Bin(m, v), where
n_max(m) is the largest N with Bin(m, alpha).cdf(N) <= delta. With zero observed violations,
certification at (alpha, delta) needs m >= ceil(ln delta / ln(1 - alpha)) = 29. The required m
grows like (alpha - v)^(-2), so a finite budget places the certified decision strictly inside the
safe set. The gap to the oracle margin and the abstention rate are the observable, guaranteed
replacement for the TCST paper's kappa* diagnostic.

## 4. Positioning

*Known and cited, not claimed:* marginal versus conditional coverage (Vovk, 2012; Lei and
Wasserman, 2014; Foygel Barber et al., 2021); the optimizer's curse (Smith and Winkler, 2006) and
the optimism bias of sample-average approximation (Mak, Morton and Wood, 1999); fixed-sequence
testing and Learn-then-Test; the scenario approach (Calafiore and Campi, 2006; Campi and Garatti,
2008) and sampling-and-discarding (Campi and Garatti, 2011); conformal uncertainty sets in robust
optimization (Johnstone and Cox, 2021; Patel, Rayan and Tewari, 2024); conformal decision theory
(Lekeufack et al., 2024); conformal predictive programming (Zhao et al., 2024).

*Claimed:* (1) the post-selection failure of conformal constraint back-offs in chance-constrained
optimization, with mechanism (Props. 1-2) and measured size; (2) certify-then-deploy for
optimized decisions, where the nesting of inflated back-offs makes fixed-sequence testing
lossless, giving an (alpha, delta) guarantee at the deployed decision that is distribution-free,
tolerates arbitrary upstream data reuse and non-convex models, wraps an existing nominal-model
RTO, and has a dimension-free certification cost; (3) the budget and abstention analysis as an
engineering design rule; (4) evidence on an exact-ground-truth synthetic family and a rigorous
DWSIM twin.

*Limits, stated up front:* certification needs evaluations of g at candidate decisions under
i.i.d. disturbance draws; the guarantee is relative to that g; autocorrelated or drifting
disturbances break the i.i.d. assumption (weighted or blocked certification is future work).

## 5. Gate-1 evidence

Synthetic family with exact ground truth: d = 2, Gamma(2, 1) disturbance, heteroscedastic
sensitivity rising in the profitable direction; 400 independent trials; alpha = 0.10,
delta = 0.05, certification budget m = 200. Oracle: V = 0.0999, profit 0.892.

| Method | Marginal miss | Mean V at deployed u | P(deploy unsafe) [95% CI] | Profit gap vs oracle |
|---|---|---|---|---|
| Fixed split-conformal margin | 0.100 | 0.180 | 1.000 [0.991, 1.000] | -3.0% (beyond safe set) |
| Normalized (locally adaptive) | 0.100 | 0.169 | 0.970 [0.948, 0.984] | -7.5% (beyond safe set) |
| Local CQR | 0.100 | 0.171 | 0.930 [0.900, 0.953] | -7.2% (beyond safe set) |
| Plug-in a-posteriori kappa (TCST v2 procedure) | n/a | 0.092 | 0.345 [0.298, 0.394] | 4.1% |
| **Certify-then-deploy (Thm 3)** | n/a | **0.055** | **0.015 [0.006, 0.032]** | **11.9%** |
| Scenario approach, N = 46 | n/a | 0.021 | 0.000 [0.000, 0.009] | 26.2% |
| Sampling-and-discarding, N = 200, k = 8 | n/a | 0.043 | 0.003 [0.000, 0.014] | 13.4% |

Findings:
- Marginal back-offs hit their marginal target exactly (0.100) and still deploy an unsafe
  decision in 93-100% of trials, at 1.7-1.8 times the target violation.
- The TCST v2 plug-in procedure is right on average (0.092) and wrong a third of the time
  (34.5%). It never carried an (alpha, delta) guarantee.
- Certify-then-deploy: 1.5% unsafe deployments, upper 95% bound 3.2%, inside delta = 5%.
- Price of the guarantee: 11.9% below oracle at m = 200; 8.3% at m = 800; 24.0% with 14%
  abstention at m = 30.
- At d = 2 the edge over sampling-and-discarding at equal budget is 1.5 points (11.9% vs
  13.4%). The dimension sweep in G2 decides whether it widens; claims will be sized to that.
- Optimizer's curse: normalized back-off unsafe deployments fall from 99.7% (kNN k = 5) to
  61.0% (k = 125) as estimation noise falls, and never approach delta.
- Budget m* for 80% certification power: v = 0 needs 29; 0.02 needs 61; 0.04 needs 116;
  0.06 needs 286; 0.08 needs 1290.

## 6. Gates to submission

- **G1** Theory audit and synthetic validation. DONE (this note).
- **G2** Evidence. (a) Dimension sweep d in {2, 5, 10, 20}: certified vs sampling-and-discarding
  vs scenario at matched budget. (b) DWSIM-twin re-run with certify-then-deploy and scenario
  baselines over repeated trials; needs the M3 campaign CSV from Bien's machine. (c) i.i.d. audit
  of the certification sample.
- **G3** Manuscript: unmodified TMLR style file, anonymized (no IPIS name, no identified repo
  link; anonymous code mirror), main text <= 12 pages, twin described in new text.
- **G4** Adversarial proof check and claims audit against the frozen evidence JSON.
- **G5** arXiv (preprint option of the style file) and OpenReview submission. Lead-time
  preconditions: OpenReview author profile; arXiv endorsement.

## References (verify volume and page details at G3)

- Angelopoulos, Bates, Candes, Jordan, Lei. Learn then test: calibrating predictive algorithms
  to achieve risk control. arXiv:2110.01052.
- Calafiore, Campi (2006). The scenario approach to robust control design. IEEE TAC 51(5).
- Campi, Garatti (2008). The exact feasibility of randomized solutions of uncertain convex
  programs. SIAM J. Optim. 19(3).
- Campi, Garatti (2011). A sampling-and-discarding approach to chance-constrained optimization:
  feasibility and optimality. JOTA 148(2).
- Clopper, Pearson (1934). The use of confidence or fiducial limits illustrated in the case of
  the binomial. Biometrika 26(4).
- Foygel Barber, Candes, Ramdas, Tibshirani (2021). The limits of distribution-free conditional
  predictive inference. Information and Inference 10(2).
- Johnstone, Cox (2021). Conformal uncertainty sets for robust optimization. PMLR 152.
- Lei, Wasserman (2014). Distribution-free prediction bands for non-parametric regression.
  JRSS-B 76(1).
- Lekeufack et al. (2024). Conformal decision theory: safe autonomous decisions from imperfect
  predictions. ICRA.
- Mak, Morton, Wood (1999). Monte Carlo bounding techniques for determining solution quality in
  stochastic programs. Oper. Res. Lett. 24.
- Patel, Rayan, Tewari (2024). Conformal contextual robust optimization. AISTATS.
- Smith, Winkler (2006). The optimizer's curse: skepticism and postdecision surprise in decision
  analysis. Management Science 52(3).
- Vovk (2012). Conditional validity of inductive conformal predictors. ACML, PMLR 25.
- Zhao et al. (2024). Conformal predictive programming for chance constrained optimization.
  arXiv:2402.07407.
