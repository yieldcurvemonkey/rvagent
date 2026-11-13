# Multiple testing, selection bias, model-selection tests and sequential evidence

Detail behind sections 7 and 11 of [SKILL.md](../SKILL.md). All p-values assume the test statistic is valid under dependence:
daily P&L of multi-week holds needs HAC or block-bootstrap statistics first (section 4 of the skill), otherwise every correction below
is applied to inflated t-stats.

## 1. Family-wise error and false discovery

Notation: `m` tests, `p_(1) <= ... <= p_(m)` sorted p-values, level `alpha` (0.05 default).

| Method | Rule | Controls | Use for |
|---|---|---|---|
| Independent-test FWER | `1 - (1 - alpha)^m` (m = 100: 0.994) | - | sizing the problem; positive dependence makes it smaller |
| Bonferroni | reject if `p_j < alpha/m` | FWER, any dependence | few, decisive tests; very conservative |
| Holm step-down | find the smallest `j` with `p_(j) > alpha/(m+1-j)`; reject all before it | FWER, any dependence | default when you must not make a single false claim; never worse than Bonferroni |
| Benjamini-Hochberg | `L = max{j : p_(j) <= alpha·j/m}`; reject `p_(1..L)` | FDR = E[false/rejected] (independence or positive dependence) | large screens where some false positives are acceptable |
| Permutation p-values | `p_j = (1/K) · #{k : |t_j^k| >= |t_j|}`, K = 1,000 label (or date) permutations | exact under exchangeability | small n, fat tails, doubtful null; shuffle in blocks for dependent data |
| Plug-in FDR | cutoff `C`; `FDR_hat = E[V]/R`, `E[V]` = mean count of permuted `|t| > C`, `R` = observed count | FDR | screens of hundreds of spreads/flies (Hastie, Tibshirani, Friedman, Elements of Statistical Learning, 2009) |

Worked examples
- **Holm vs Bonferroni** (5 fund managers, alpha 0.05, p = 0.006, 0.012, 0.601, 0.756, 0.918): Bonferroni threshold 0.01 rejects 1; Holm compares
  0.006 < 0.01, 0.012 < 0.0125, then 0.601 > 0.0167 and stops: rejects 2 (James, Witten, Hastie, Tibshirani, Introduction to Statistical Learning with Applications in Python).
  `scripts/validation.py` reproduces this in its selftest.
- **Large screen**: 12,625 features, 1,189 with `|t| >= 2` against 631.3 (sd 24.5) expected by chance; BH at alpha 0.15 keeps 11 (cutoff p = 0.00012, `|t| >= 4.1`);
  plug-in FDR 1.518 expected false of 11, about 14% (Hastie et al., 2009). RV reading: a screen of several hundred spread, fly and tenor
  combinations flags a handful by chance alone; compare the count flagged with `alpha·m` before looking at any one of them.
- **Seasonality screen**: test month-by-month with t-test (means) and Wilcoxon (medians) at alpha 10%, then compare the number of significant months with
  `alpha` x months. The t-test needs approximately normal monthly moves, Wilcoxon needs symmetry (swapsball.net, Testing for seasonality, 19 Nov 2017).
  See [quant-seasonality-and-calendar-effects](../../quant-seasonality-and-calendar-effects/SKILL.md).

**Selection-bias-adjusted p for the winner.** A winner picked from a sweep must be compared with the distribution of the family MAXIMUM of the statistic under
the null (bootstrap or sign-flip the whole panel with one shared resample index so cross-correlation is kept), not with a single-test null.
Standard tools: White's reality check and the Romano-Wolf stepdown (strong FWER control) (external; White, Econometrica, 2000; Romano and Wolf, Econometrica, 2005).
The deflated Sharpe ratio (skill section 4) is the closed-form version when only the trial Sharpes are known.

## 2. Wrong-way and right-way cross-validation
- Simulation: N = 50 samples, p = 5,000 pure-noise predictors; screening the 100 best by correlation with the label on ALL data and then running 1-NN with CV gave
  CV error 3% against a true 50%; selected predictors showed correlation about 0.28 in the held-out folds instead of about 0. The same problem, with
  refit of predictor choice and split point inside each fold, gave about 50% (correct) (Hastie et al., 2009).
- Rule: any supervised step (choose spreads, choose lookback, choose threshold, choose features) lives inside the training fold. Unsupervised screens
  (keep highest-variance series, ignoring the label) may precede CV.
- Report CV error with its standard error; differences smaller than about 1 SE are chance. Prefer the simplest model within 1 SE of the best
  (`se = sigma_hat/sqrt(N)` of per-sample losses) (Hastie et al., 2009; Murphy, Machine Learning: A Probabilistic Perspective, 2012).
- iid K-fold, bootstrap and information criteria assume exchangeable rows; with serial dependence use contiguous purged folds and block resampling
  (Gelman et al., Bayesian Data Analysis, 3rd ed., 2014; McElreath, Statistical Rethinking, 2016).
- Bootstrap error estimates: naive bootstrap prediction error is optimistic because a sample contains 63.2% of the observations; the leave-one-out bootstrap and
  the .632+ estimator correct this (Hastie et al., 2009). Under overlapping labels the bootstrap in-bag/out-of-bag split is nearly identical, so OOB scores are
  "grossly inflated" (López de Prado, Advances in Financial Machine Learning, 2018).

## 3. Post-selection inference and spurious significance
- p-values and CIs computed on the data that chose the model (including choosing lambda or dropping insignificant variables) are too optimistic; split the data,
  one half selects and the other estimates. A pure-noise post-selection F-test gave p = 0.031 (Shalizi, The Truth about Linear Regression, draft, 20 Oct 2025).
- p is a measure of sample size: any non-zero effect becomes significant as n grows; always give a CI. F-tests and R² do not validate a model (a clearly misspecified
  linear model gave F p about 1e-60, R² 0.79) (Shalizi, 2025).
- **Spurious regression**: regress one random walk on an independent one and a significant fit is almost certain. Granger-Newbold suggested a critical t of 11.2 rather
  than 1.96; Phillips: for T = 50 the appropriate critical value is close to 15; a 5% t-test rejected 66.2% of the time at n = 50 and 84.7% at n = 250 (Greene, Econometric Analysis, 8th ed., 2018; Wooldridge, Introductory Econometrics).
- **Engle-Granger residual tests need stricter critical values** because OLS makes the residual look stationary: no trend 1% -3.90, 2.5% -3.59, 5% -3.34, 10% -3.04; with trend -4.32, -4.03, -3.78, -3.50 (Wooldridge). See [quant-cointegration](../../quant-cointegration/SKILL.md).
- Correlated errors understate SEs; Newey-West lag about `T^(1/4)` as a floor (Greene, 2018). Levels regressions of rates give high R² without cointegration (96.5% for 1y vs 3y UST) (Tsay, Analysis of Financial Time Series, 2010).

## 4. Choosing complexity honestly
- Optimism: `E[out-of-sample MSE] = E[in-sample MSE] + (2/n)·sigma²·(p+1)` for linear models. Never pick complexity on in-sample R² or MSE; with p >= n, OLS fits any data perfectly and R² = 1 is no evidence
  (Shalizi, 2025; James et al.).
- Penalties: adjusted R² rises only if the added variable has `|t| > 1`; `AIC(K) = ln(e'e/n) + 2K/n`; `BIC(K) = ln(e'e/n) + K·ln(n)/n` (heavier, simpler models) (Greene, 2018).
  Simulation (true model quadratic, max degree 10, n = 20): R² always picks 10, Cp median 2, BIC mean 3.1, AIC mean 4.7; at n = 1,000 BIC mean 2.003 while AIC/Cp/LOOCV have about a 25% chance of
  too large a model (Shalizi, 2025). LOOCV/AIC predict better; BIC is more selection-consistent.
- Compare candidate models on exactly the same observations (automatic NA dropping silently changes n); judge information-criterion differences by the SE of the difference, not by overlapping bars; an
  Akaike weight is conditional on the set compared. Differences below about 1 in estimated prediction error are typically chance (McElreath, 2016; Gelman et al., 2014).
- Learning curves: error vs n plateaus at noise plus structural error; simple models converge faster. PCA reconstruction error always falls with more components, so choose the
  number of factors by scree/eigen-gap, not by CV, unless the components feed a supervised model (Murphy, 2012). Err toward more factors in a hedge/risk model: too few degrades Sharpe steeply, too many costs little (Paleologo, The Elements of Quantitative Investing, 2025).
- Constrain over-parameterised models a priori: a VAR/MVOU with m series has `m²` free parameters; adjacent-points-only influence cuts it to `3m-2`; "you are smarter than your data"
  (Huggins, Schaller, Fixed Income Relative Value Analysis, 2024).
- Shock-and-refit test for fitted curves: re-estimate after perturbing 5% of bonds with N(20, 5) noise and track the change in curvature (absolute second differences); curvature jumped between 15 and 20 knots, 12 was chosen
  (J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024). See [bond-rich-cheap-fitted-curve](../../bond-rich-cheap-fitted-curve/SKILL.md).

## 5. Sequential and betting-based evidence
| Tool | Statement | Use |
|---|---|---|
| Ville/Doob | non-negative martingale `L`, `L_0 = 1`: `P{sup_n L_n >= lambda} <= 1/lambda` | live tracking: stopping when capital multiplies is still valid |
| p-value calibrator `h` | valid iff `integral_0^1 h(p) dp <= 1`; `rt1(p) = p^(-1/2)` if `p <= 0.25` else 0; `rt2(p) = 2p^(-1/2)` if `p <= 0.0625` | a p-value whose cutoff was chosen after seeing data |
| Vovk-Sellke bound | `VS(p) = -1/(e·p·ln p)`, `p <= 1/e` | upper bound on the evidence a given p can carry |
| Lookback calibrator | valid iff `integral_1^inf H(v)/v² dv <= 1`; `RT1(v) = sqrt(v)` if `v >= 4`; `RT2(v) = 2·sqrt(v)` if `v >= 16` | evidence in the running maximum of a capital process; long-only non-negative capital (for long/short RV, treat the strategy equity as the asset) |
| Variance clock | accumulate variance `A` in blocks of `C`; the upper probability that the normalised cumulative excess exceeds `sqrt(C/delta)` is <= delta | test one strategy over time; measure time by variance, not calendar |

Evidence implied by a post-hoc p-value (`p`, `1/p`, `rt1`, `rt2`, `VS`): 0.05 gives 20, 4.5, 8.9, 2.5; 0.01 gives 100, 10, 20, 8.0; 0.005 gives 200, 14, 28, 14; 0.001 gives 1,000, 32, 63, 53;
0.0001 gives 10,000, 100, 200, 400. A p of 0.05 found by looking back is worth at most 2.5x (VS) to 4.5x (rt1), not 20x (Shafer, Vovk, Game-Theoretic Foundations for Probability and Finance, 2019).
Lookback calibrator values `v -> RT1 / RT2`: 10 -> 3 / 0; 100 -> 10 / 20; 1,000 -> 31 / 63; 10,000 -> 100 / 200 (same source).

Do not test efficiency by counting how many of many funds or strategies beat a threshold (they can be arbitrarily correlated); test one strategy
over successive variance-clock blocks. In an equity example over 3,671 days the bound held at alpha 1% (0.158%/day) and was violated at alpha 10% (0.095%/day)
(Shafer, Vovk, Probability and Finance: It's Only a Game!, 2001). No betting or selection system turns a subfair game into a profitable one: choosing when
to trade from past outcomes alone does not change i.i.d. outcomes (Billingsley, Probability and Measure, 1995).

Hypothesis-test trade-off: a threshold trades false alarms against misses, so evaluate both for several rules. A conservative CI for a hit rate is `p_hat +/- a/(2·sqrt(n))` with confidence at least `1 - 1/a²`;
to be within 0.1 at 96% you need `n >= 625` (Hajek, Probability with Engineering Applications, ECE 313 notes, Jan 2025).
