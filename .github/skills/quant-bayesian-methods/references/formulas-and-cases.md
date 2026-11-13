# Bayesian methods: extra formulas and cases

Detail moved out of [SKILL.md](../SKILL.md). Units follow the main skill (bp for rates and spreads, probabilities 0..1).

## 1. Hierarchical normal model, full conditionals (Gelman et al., Bayesian Data Analysis, 3rd ed., 2014, Sec 5.4)
Group j: ybar_j ~ N(theta_j, s_j^2), s_j known; theta_j ~ N(mu, tau^2).
- theta_j | mu, tau, y ~ N(that_j, V_j): that_j = (ybar_j/s_j^2 + mu/tau^2)/(1/s_j^2 + 1/tau^2), V_j = 1/(1/s_j^2 + 1/tau^2).
- Marginal: ybar_j | mu, tau ~ N(mu, s_j^2 + tau^2). mu | tau, y ~ N(mu_hat, V_mu), mu_hat = sum(ybar_j/(s_j^2+tau^2)) / sum(1/(s_j^2+tau^2)), V_mu^-1 = sum(1/(s_j^2+tau^2)).
- p(tau | y) proportional to p(tau) V_mu^(1/2) prod_j (s_j^2 + tau^2)^(-1/2) exp(-(ybar_j - mu_hat)^2 / (2(s_j^2 + tau^2))).
- Computation: grid over tau, then draw mu, then theta_j. Integrating mu out analytically: posterior mean of theta_j given tau is (1-B_j) ybar_j + B_j mu_hat,
  variance (1-B_j) s_j^2 + B_j^2 V_mu, with B_j = s_j^2/(s_j^2+tau^2). The bundled `hier_normal` does this and mixes over the tau grid.
- Moment (empirical-Bayes) version (Murphy, Machine Learning: A Probabilistic Perspective, 2012): mu_hat = mean(ybar), tau^2_hat = max(0, s^2 - sigma^2), s^2 = sample variance of group means. Quick, but boundary at 0.
- Hyperpriors: uniform on tau (default, J >= 3 for a proper posterior, J about 8 comfortable); half-Cauchy(0, A) broad peak at 0 with gentle tails for small J; uniform on tau^2 needs J >= 4 and is not recommended;
  uniform on log tau is improper; inverse-gamma(eps, eps) on tau^2 is very sensitive to eps.
- Model comparison: "cross-validation and information criteria are an approach for understanding fitted models rather than for choosing among them" (Gelman); prefer CV, WAIC as the fast alternative.
- Simulation sanity (McElreath, Statistical Rethinking, 2016, Sec 12.2): 60 ponds, true intercept 1.4, sd 1.5, sizes 5/10/25/35 (15 each); fitted 1.13 and 1.59; partial-pooling absolute error below no-pooling in every size group, with the biggest gain in the smallest clusters; truly extreme clusters get shrunk too much.
  Priors are "epistemology, not ontology".

## 2. Bayesian linear regression and ridge
- Posterior: SN^-1 = S0^-1 + beta Phi'Phi; mN = SN (S0^-1 m0 + beta Phi't). N = 0 returns the prior; alpha -> 0 gives OLS; zero-mean isotropic prior gives ridge with lambda = alpha/beta (Bishop, Pattern Recognition and Machine Learning, 2006).
- Greene (Econometric Analysis, 8th ed., 2018) form with known sigma^2: E[beta|data] = F beta0 + (I-F) b, F = {Sigma0^-1 + [sigma^2 (X'X)^-1]^-1} Sigma0^-1 (matrix-weighted average of prior and OLS); posterior variance {Sigma0^-1 + [sigma^2 (X'X)^-1]^-1}^-1.
  Normal-gamma prior gives a multivariate-t posterior. Beta-binomial: posterior mean (D + a)/(N + a + b).
- Effective degrees of freedom of ridge: df(lambda) = sum_j d_j^2/(d_j^2 + lambda) (Hastie, Tibshirani, Friedman, Elements of Statistical Learning, 2009). Lasso = Laplace prior, posterior mode only.
- Inequality constraints (sign, monotonicity): simulate without them and discard violating draws; if most are discarded, the data contradict the model.
- Bayesian model averaging: posterior model probability proportional to P(y|m) p_m; equal-weight averaging of many forecasts was a strong benchmark for inflation forecasts (Greene, citing Stock and Watson).
- Unit roots: with a diffuse or normal-gamma prior the posterior of AR coefficients is multivariate t whether or not the process is stationary, so ordinary t/F statistics are valid for a Bayesian (Hamilton, Time Series Analysis, 1994).

## 3. Kalman, VAR priors, state space
- Local-level/Muth: x_{t+1} = x_t + tau_eps*eps; y = x + tau_eta*eta; kappa = tau_eta/tau_eps; stationary gain K a function of kappa, K about 1/(1+kappa) for kappa >> 1 (Paleologo, The Elements of Quantitative Investing, 2025).
- Litterman/Doan-Litterman-Sims prior (Hamilton): prior mean (0,1,0,...,0)'; own lag s variance gamma^2/s; other variables N(0, w^2 gamma^2 tau_1^2/(s tau_j^2)), tau_j^2 = AR(p) residual variance of series j; gamma^2 = 0.07, w^2 = 1/74, g = 630 for the constant;
  coefficient dynamics beta_{t+1} = pi_8 beta_t + (1-pi_8) beta_bar + v, pi_8 = 0.999; Q = pi_7 * diag(P_1|0), pi_7 = 1e-7; R = 0.9 tau_1^2.
- Global yield state space (BofA Global Research, US Rates Watch: Monthly rates models, Apr 2025): x(t) = B x(t-1) + w(t), y(t) = Z x(t) + v(t); Z can be constrained for interpretability and picks up trends PCA misses.
- Sign-restricted BVAR (BofA Global Research, US Rates Watch Aug 2025; UST RV Primer, May 2022): variables 10y yield, 5y5y inflation, USD real/nominal effective FX, CAPE. Restrictions by shock: inflation (inflation +, 10y +, CAPE -); monetary (inflation -, 10y +, FX +, CAPE -);
  demand (all four -); risk (10y -, FX +, CAPE -, inflation free). Purpose: avoid non-economic solutions such as yields negatively correlated with growth.
- Global 10y breakeven PCA (US, UK, AU, JP, EU, CAD; >= 6 years): PC1 85% (oil), PC2 9% (financial stress), together 94%.
- Regime-weighted regressions: SOFR-IORB fits per regime, equal-weighted, R^2 only 0.06-0.17 in recent regimes (BofA, Apr 2025): treat regime weights as a prior over models.

## 4. Mean and covariance shrinkage (Palomar, Portfolio Optimization, 2025; Golub, BlackRock's Guide to Fixed-Income Risk Management, 2023)
- theta_sh = (1-rho) theta_hat + rho theta_target; MSE = Var + Bias^2; oracle covariance rho = E||S_hat - S||_F^2 / E||S_hat - S_target||_F^2.
- Mean targets: 0; grand mean; vol-weighted grand mean. Gaussian simulation: shrink-to-zero best (consistent with efficient markets). Covariance targets: scaled identity, diagonal, equal-correlation. Gains for covariance modest, for means clear.
- Spiked covariance: with gamma = n/T a population spike is detectable only above 1 + sqrt(gamma); sample eigenvalues biased up; shrinkage l(lambda) = lambda - gamma (operator-norm optimal), proportional/linear shrinkage for heavy tails (Paleologo). Use an informative covariance prior when D/N > about 0.1 (Murphy).
- Naive mean-variance loses 10-50% of Sharpe from parameter error; higher correlation is worse (Paleologo). Black-Litterman: tau = 0 gives pi; Sigma_BL = (1+tau) Sigma - tau^2 Sigma P'(tau P Sigma P' + Omega)^-1 P Sigma.

## 5. Event-probability cases (Papic, Geopolitical Alpha, 2021)
- Brexit (Mar 2016): author about 50% vs about 30% priced by currency and betting markets; forecast Remain narrowly but recommended positioning (GBP, gilts, UK equities) that paid on Leave.
- Trump 2016: about 40% (BCA, 1 Nov 2016) vs FiveThirtyEight 29%, NYT Upshot 15%, Princeton Election Consortium 7%, HuffPost 2%.
- No-deal Brexit 2019: constraints put no-deal below 10%; "investors should have gone long the pound in the summer of 2019"; GBP return 1 Aug to year-end about 9%.
- French election 2017: markets priced Le Pen above Brexit/Trump at the same horizon despite a roughly 30pt Macron lead; Le Pen support was seen as the near-inverse of French support for the euro (fulcrum). Long EURUSD calls (EUR bottom 20 Dec 2016, +21% to 1.250 on 25 Jan 2018).
- Euro crisis: TARGET2 imbalance EUR 0.3tn (2010) to about EUR 1.5tn (2020) read as a constraint binding the union, not a break-up signal. Constraints tend to force crisis-ending policy.
- Non-G10 illustration: long MXNBRL (14 Dec 2018, +11.2% to end-2019); short oil spikes after Gulf events. Used only as prior-vs-market examples.
- Constraint example: binary case where the stated preference is to fight but the binding constraint (teammates present) removes the option gives P = 0: stated preference can be anti-correlated with the outcome.
- Discipline: "all preferences are subject to constraints - not just those of the actors, but those of the analyst as well." Beware doom narratives built on acronyms (confirmation bias).

## 6. Market-microstructure Bayes (O'Hara, Market Microstructure Theory, 1995; Darbyshire, 2022)
- Glosten-Milgrom: ask a = E[V | buy] = V_low Pr(V_low | buy) + V_high Pr(V_high | buy); bid b = E[V | sell]; Pr(V_low | sell) = Pr(V_low) Pr(sell | V_low) / [Pr(V_low) Pr(sell | V_low) + Pr(V_high) Pr(sell | V_high)]. Quotes are regret-free conditional expectations, so the spread is the price of adverse selection.
  Pr(sale) = (1-mu) gamma_S + (1-theta) mu; Pr(buy) = (1-mu) gamma_B + theta mu (theta = P(good news), mu = P(informed)); buys and sells are not equally likely when information exists.
- Kyle (1985) learning step: p1 = [p0/Sigma0 + Z beta^2/sigma_mu^2] / [1/Sigma0 + beta^2/sigma_mu^2]; at the equilibrium beta this is p1 = (p0 + Z)/2, Sigma1 = Sigma0/2: half the information is revealed each round.
- Dealer inference from size (Darbyshire, sterling anecdote, about 2012): a 200mm 10Y GBP request (typical 25-50mm) at mid 1.30% quoted 1.2875/1.3125%; the 10Y mid then moved about 2bp; the dealer inferred the fund was trading in several places at 2-3x stated volume and quoted later requests 1.75bp from mid.
  Use: an unusually large or repeated request is evidence about total size; widen accordingly.
- Opaque-market example liquidity note: EUR benchmark IRS is very liquid across many venues, NOK benchmark IRS has few contributors and periods of no trading, so an inferred NOK level is a weaker prior than an inferred EUR level.

## 7. Probability and prediction primitives (Hakim; Ross; Jane Street)
- Bayes: P(A|B) = P(B|A) P(A)/P(B). Likelihood is not a probability (can exceed 1). Coin: after one head the MLE of P(H) is 1; after HH, L(0.5) = 0.25.
- Bivariate normal: y | x has mean rho x sigma_y/sigma_x and sd sigma_y sqrt(1-rho^2), independent of x: the residual vol of a regression hedge. Linear combos: x ~ N(mu, B) implies Ax ~ N(A mu, A B A').
- Best linear predictor b = rho sigma_y/sigma_x, MSE sigma_y^2 (1-rho^2); for a bivariate normal it is globally optimal.
- Jane Street primer checks: E[d6 | roll >= 4] = 5; P[5 | roll >= 4] = 1/3; P[2 heads | at least 1 tail in 3 flips] = 3/7; P[sum = 7 on two dice] = 1/6. Linearity of expectation always holds; E[XY] = E[X]E[Y] only under independence.
- Bet paying x on a win and y on a loss: expected payout y + (x-y)P[A].
