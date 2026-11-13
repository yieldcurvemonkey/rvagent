---
name: quant-bayesian-methods
description: Priors, shrinkage, hierarchical (partial) pooling and Bayesian updating for rates RV - shrink noisy per-market or per-instrument estimates (betas, IC, hit rates, mean-reversion speeds, risk premia) toward a pool, update a prior with new data (normal-normal, Bayesian regression, Kalman), blend views with an equilibrium (Black-Litterman), infer an unobserved or illiquid market's move from correlated markets, and turn structural analysis into event probabilities. Use when asked about Bayesian, prior, winner's curse, regularisation, posterior, shrinkage, James-Stein, empirical Bayes, ridge, partial pooling, how much to trust a thin-history or small-sample estimate, Black-Litterman views, tau, conjugate update, credible interval, predictive band, calibration, base rate, or estimating a price that has not printed yet.
---

# Bayesian methods: priors, shrinkage, pooling, updating

RV signals are estimated from short, noisy, overlapping histories: a fly's reversion speed in NOK, a hedge beta over 2 years,
an IC from 36 months. Raw estimates (MLE/OLS) are unbiased but have large variance, and the extreme-looking ones are the ones
the screen picks (winner's curse). Bayesian shrinkage trades a little bias for a large variance cut: estimate = precision-weighted
average of the data and a prior or pool. The same algebra gives the standard update when new data arrive, and the
posterior predictive band that includes parameter uncertainty. Use it whenever the number being acted on is an estimate with a
standard error, not a market price.

All results are in the unit of the input (bp, bp per year, correlation, probability). Precision = 1/variance in that unit squared.

## When to use
- "Is this country's estimate real or noise?" (per-market beta, IC, half-life, hit rate, seasonal, carry premium).
- A thin-history instrument (NOK, NZD, SEK, CHF, a new bond line) needs an estimate: borrow strength from peers.
- Update a prior or a running estimate with one new observation or a new print (sequential/Kalman logic).
- Prediction band for a regression fair-value residual that should include parameter uncertainty.
- Combine a model/equilibrium with discretionary views (Black-Litterman) or size a view from implied return.
- Infer where an illiquid or not-yet-open market should trade from correlated markets that have moved.
- Turn a structural/political analysis into a probability, compare it with a market-implied probability, update it.
- Choosing ridge/regularisation strength, prior width, or deciding whether a "regularised" fit is credible.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Estimates to shrink: `est`, `se` (same unit), optional `n` and `group` per id | derived from `signals`, `pnl`, `curve_par`, `bond_quotes` | one row per market/instrument/strategy | `se` must be a real standard error (HAC/overlap-adjusted for overlapping returns), not the residual sd |
| Time series for regression priors and Kalman updates | `curve_par`, `curve_zero`, `bond_quotes`, `swap_spreads` | daily, >= 3y (>= 6y for global PCA-type panels) | standardise regressors (mean 0, sd 1) before applying a zero-centred prior |
| Cross-market moves for unobserved-price inference | `curve_par`, `bond_quotes` at two snaps | same-tenor moves since a common reference time | needs a covariance of moves (see quant-covariance-estimation) |
| Event probabilities (market-implied) | `events_probs`, `cb_meetings`, `macro_series` | per event | `prob` 0..1; update with a fixed rule, store the prior |

If an `se`, covariance or history is missing, ask for it or hand off to the data adapter. Never invent a standard error.
Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

## Method

### 1. Choose the tool
| Situation | Tool | Section |
|---|---|---|
| One quantity, Gaussian prior, new observation | normal-normal update | 2 |
| Many similar units (markets, bonds, strategies), each noisy | partial pooling / empirical Bayes | 3 |
| Regression coefficient or hedge ratio with a sensible prior | Bayesian regression = ridge to a prior | 4 |
| Signal quality (IC) or mean forecasts from short samples | IC / Jorion shrinkage | 5 |
| Running estimate updated every day | Kalman = sequential Bayes | 6 |
| Equilibrium plus views | Black-Litterman | 7 |
| A market has not printed; neighbours have | conditional inference | 8 |
| One-off event, no usable sample | structural prior then update | 9 |

### 2. Normal-normal update (known noise variance)
Prior theta ~ N(mu0, tau0^2); n observations with mean ybar and noise sd sigma:

```
precision_post = 1/tau0^2 + n/sigma^2          posterior sd = precision_post^-1/2
mu_post = (mu0/tau0^2 + n*ybar/sigma^2) / precision_post
        = mu0 + w*(ybar - mu0),   w = (n/sigma^2) / precision_post     (weight on data)
```
- Limits: tau0 -> 0 returns the prior; sigma -> 0 returns the data. A tight prior (small tau0) pulls hard: check tau0 before
  trusting a shrunk number. With unit noise variance and prior variance s2: weight on data = s2/(1+s2) (Ross).
- Sequential: today's posterior is tomorrow's prior; batch and sequential give identical answers.
- Posterior predictive for a new observation: N(mu_post, sigma^2 + sd_post^2). Use this, not residual sd alone, for bands.
- Variance prior as pseudo-data: sigma^2 ~ Inv-chi2(n0, s0^2) acts as n0 prior observations; posterior scale
  (n0*s0^2 + n*s^2)/(n0 + n) (Gelman). Prior as pseudo-rows: append y* = beta0 with row I and weight 1/prior_var to a WLS fit.
- Prior-data conflict check: marginally ybar ~ N(mu0, sigma^2/n + tau0^2). If |ybar - mu0| / sqrt(sigma^2/n + tau0^2) > 2.5,
  the prior is probably wrong, not the data: revisit it before updating.

### 3. Partial pooling across markets / instruments (the workhorse)
Setup: unit j has estimate ybar_j with known se_j; true values theta_j ~ N(mu, tau^2). Three estimators: no pooling
(theta_j = ybar_j, tau = inf, "a model with amnesia"), complete pooling (precision-weighted grand mean, tau = 0, underfits),
partial pooling:
```
B_j      = se_j^2 / (se_j^2 + tau^2)               weight on the pool (0..1)
theta_j  = (1 - B_j)*ybar_j + B_j*mu               posterior mean
var_j    = (1 - B_j)*se_j^2 + B_j^2 * Var(mu)       posterior variance (mu uncertainty included)
mu       = sum(ybar_j/(se_j^2+tau^2)) / sum(1/(se_j^2+tau^2))
```
Higher se_j (short history, noisy market) means more shrinkage; units with tiny se_j keep their own estimate.
- **Estimate tau, but do not plug in a point.** Moment estimate tau^2 = max(0, var(ybar) - mean(se^2)) is quick (empirical Bayes) but
  can hit 0, which says "everything identical" - too strong a claim; it ignores uncertainty in tau. Default: integrate over tau on a
  grid, posterior p(tau|y) proportional to p(tau) * Var(mu)^1/2 * prod (se_j^2+tau^2)^-1/2 * exp(-(ybar_j-mu_hat)^2 / (2(se_j^2+tau^2))).
- **Hyperprior for tau** (Gelman): uniform on tau is the default for J >= 8 units (needs J >= 3 to be proper); half-Cauchy(0, A) when
  J is small (A of the order of the plausible spread; 25 was used for estimates with sd about 10). Never uniform on log tau
  (improper) and never inverse-gamma(eps, eps) on tau^2 (not noninformative: results depend on eps when small tau is plausible).
- **Exchangeability is a judgement.** Pool units that you would a priori treat as interchangeable. G10 practice: pool within sensible
  blocks (EGB core vs periphery; commodity-linked AUD/CAD/NOK; JPY and CHF have long regimes of yield-curve control / negative
  rates), or add a group-level mean (two-level model) rather than forcing one pool. If pooling shrinks a market toward peers
  with a structural difference, you are injecting bias.
- Use the standard-error scale, not raw units: if estimates are proportions or correlations, transform first (arcsine for
  proportions; Fisher z = atanh(r), se = 1/sqrt(T-3) for correlations) so the normal model is reasonable (Murphy: arcsine transform then
  shrink toward the global mean gave over 3x lower MSE than raw MLEs in the baseball example).
- James-Stein: for N >= 4 units with equal known sampling variance, shrinking toward the grand mean dominates the MLE in total squared error (with unequal se_j use the B_j form above, not a common factor).

### 4. Regression coefficients and hedge ratios
- Prior w ~ N(m0, S0): posterior SN^-1 = S0^-1 + beta*X'X, mN = SN (S0^-1 m0 + beta X'y) (beta = noise precision). Matrix-weighted
  average of prior and OLS by inverse variance. Prior N(0, I/alpha) gives ridge with lambda = alpha/beta (= sigma^2/tau^2); lasso is
  the posterior mode under a Laplace prior (not the mean).
- **Predictive variance** at x: 1/beta + x' SN x (data noise + parameter uncertainty). Falls with N, never to zero. Use for the
  band on a fair-value residual before calling a residual a signal.
- **Set prior strength by evidence or cross-validation, not in-sample fit** (minimising regularised error over lambda gives lambda = 0).
  Evidence loop: gamma = sum lambda_i/(alpha+lambda_i) (effective parameters), alpha = gamma/(mN'mN), 1/beta = sum(t-mN'x)^2/(N-gamma),
  iterate; directions with lambda_i >> alpha are data-determined, lambda_i << alpha are shrunk to zero. `bayes_linreg(evidence=True)`.
- Defaults (McElreath): standardise x (and y, so slopes are in sd units); slope prior N(0,1) (5% mass beyond +/-2), tighter N(0,0.5)/N(0,0.2) when predictors are many
  and collinear; tune by train/test. Too tight underfits; too loose overfits. Small-sample: prior dominates; large: data dominate.
- Hedge-type regressions (y on x): residual sd given correlation rho is sigma_y*sqrt(1-rho^2) (bivariate normal). A prior does not fix a shift in
  Var[X]: if the true P(Y|X) is not exactly linear (or x is measured with error) the best linear slope moves when the regressor's variance regime
  changes even though P(Y|X) does not - re-estimate then (Shalizi).
- Collinear regressors (many tenors): ridge with small lambda (demo values 0.006 by CV; 0.01 in a 49-regressor example; lambda is scale-dependent, so standardise first) shrinks correlated
  coefficients together and stabilises the spread weights. For inference after choosing lambda by CV, split the data (one half
  picks lambda, the other estimates).

### 5. Signal quality and mean forecasts from short samples
- **IC shrinkage** (Grinold-Kahn Table 11.4): the sampling sd of an IC estimate from T independent periods is about 1/sqrt(T) (T = effective independent observations: divide by the overlap if the signal horizon exceeds the sampling interval). With prior
  sd s for the true IC: weight on data w = T*s^2/(1+T*s^2). Using s = the estimated IC itself (a heuristic, not an independent prior; pass `prior_sd` from peer-signal dispersion if available) reproduces the book factors:
  IC 0.05 / 0.10 at T = 36: 0.08 / 0.26; T = 60: 0.13 / 0.38; T = 120: 0.23 / 0.55; T = 240: 0.38 / 0.71 (IC 0 gives 0).
  So a 36-month IC of 0.10 should be used as roughly 0.026. IC above 0.20 usually signals a faulty backtest. `shrink_ic`.
- **Refined forecast** (regression as posterior mean): alpha = vol * IC * score, score z = (g - E[g])/sd(g); E[r|g] = E[r] + Cov(r,g)Var(g)^-1 (g - E[g]).
  Use shrunk IC here. Constraints silently reduce effective IC (62% in one example): shrink explicitly.
- **Mean shrinkage (Jorion)**: mu_sh = (1-rho) mu_hat + rho * target; rho = (N+2) / ((N+2) + T*(mu_hat-target)' Sigma^-1 (mu_hat-target)) (mu_hat and Sigma per period, T = number of periods).
  Targets: zero, grand mean, or vol-weighted grand mean (1'Sigma^-1 mu_hat / 1'Sigma^-1 1). rho falls automatically as T grows or the
  target disagrees with the data. Means are the bottleneck of optimisation (errors > 100% at N=100, T=500): shrink hard or use
  mean-free (risk-based) sizing. Covariance shrinkage helps less; see [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md).
- Estimates compared on one screen (top 3 of 30 z-scores) are selected for being extreme: shrink before ranking, and rank on
  the posterior mean or on the posterior probability the effect exceeds a hurdle, not on the raw value.

### 6. Sequential updating and Kalman
Kalman filter = Bayes with Gaussian prior, linear observation. State x_t, y_t = H'x_t + e (var R), x_t = F x_{t-1} + w (var Q):
```
predict: x_t|t-1 = F x_t-1|t-1 ;  P_t|t-1 = F P F' + Q
update : K = P_t|t-1 H (H'P_t|t-1 H + R)^-1 ;  x_t|t = x_t|t-1 + K (y_t - H'x_t|t-1) ;  P_t|t = P_t|t-1 - K H' P_t|t-1
```
- Gain depends on Q/R only, not on data. Local level (random-walk state): weight on a new observation about 1/(1+kappa), kappa = sd(noise)/sd(state
  shock) when kappa >> 1; exactly K = p/(1+p), p = (q + sqrt(q^2+4q))/2, q = 1/kappa^2 (kappa = 10 gives K = 0.095). EWMA with weight K is its steady state. Mean-reverting state gives smaller K.
- Initialise diffuse: P0 = 1e5 * I, s0 = 0 (alternatives discouraged by the source); estimate Q, R by maximising the
  prediction-error likelihood -T/2 ln 2pi - 1/2 sum ln f_t - 1/2 sum e_t^2/f_t. Parameterise covariances by Cholesky; a singular Hessian
  means unidentified parameters. Total MSE = filter MSE + parameter uncertainty (add by Monte Carlo over theta ~ N(theta_hat, I^-1/T)).
- Volatility (log-variance, Harvey-Shephard): filter log r^2 - gamma with gamma = E log xi^2 about -1.27 (sd 2.22), sigma = exp(x_hat/2).
- Time-varying coefficient prior (Doan-Litterman-Sims): own lag 1 mean 1, others 0; own lag-s variance gamma^2/s with gamma^2 = 0.07;
  cross-variable weight w^2 = 1/74; coefficient drift persistence 0.999. Multi-step forecasts by feeding back one-step forecasts are approximate.
- Dynamic hedge ratios and TVP betas are implemented in [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md).
- Sign-restricted Bayesian VAR priors (10y yield, 5y5y inflation, USD real FX, equity valuation) keep the fair value from implying
  non-economic signs (yields falling when growth rises); if most posterior draws are rejected by the restrictions, the data contradict the model.

### 7. Black-Litterman (views on top of an equilibrium)
```
mu_BL = pi + tau*S*P' (tau*P*S*P' + Omega)^-1 (v - P*pi)       Cov(mu_BL) = ((tau*S)^-1 + P'Omega^-1 P)^-1
```
pi equilibrium/model returns (or carry-adjusted drift), P view-picking matrix (rows = trades, e.g. 2s10s flattener in DV01 units), v view
sizes, Omega view uncertainty. tau = 0 returns pi, tau -> inf makes the views hold exactly (P*mu_BL = v). Default tau = 1/T (T = sample size of the covariance)
or by cross-validation. Qualitative views (Meucci): v_i = (P pi)_i + eta_i * sqrt((P S P')_ii), eta in {-2, -1, +1, +2} (very bearish ...
very bullish), Omega = (1/c) P S P' with confidence c. Reverse optimisation sizes a view: calibrate risk aversion from a reference
portfolio, solve the return needed to justify a weight (1% BTC needs about 12%/yr, 5% just under 25% in a 59/40/1 reference; Willer
and Saunders, Trading Global Macro Markets, 2026). `black_litterman`. Sizing: [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).

### 8. Inferring an unobserved market (stale or not yet open)
Moves dR ~ N(0, Q), Q = covariance of same-horizon moves. With a unit-diagonal Q (correlations, as in the book example) raw bp moves imply equal vols in all markets; otherwise use the covariance, or
standardise x by each market's vol and multiply Y by the unknown market's vol.
Partition into known x and unknown Y; the most likely Y solves (Q^-1)_YY * Y = -(Q^-1)_Yx * x, identical to the conditional mean
Y = Q_Yx Q_xx^-1 x. Conditional sd = sqrt(1/(Q^-1)_YY): report it, it is the confidence of the inference. Rule: whenever the opaque market
prints, reset the reference point of measured moves in all markets to that time. Assumes multivariate normality and stable
correlations; weaker where the opaque market's benchmark is thinly contributed (NOK) than where it is liquid (EUR).
`infer_unobserved`.

### 9. Event probabilities: structural prior, then update
- Preference vs constraint (Papic): P(outcome) = sum_Z p(action | Z) p(outcome | action, Z) p(Z) over constraint states Z. Weight outcomes by the
  binding ("fulcrum") constraint, not by rhetoric; the two models coincide only if constraints have no influence. Do not assume a 1:1
  link from one constraint to a policy outcome.
- Where the sample of comparable events is tiny or dissimilar, reject a frequentist base rate (Brexit "10%") in favour of a structured subjective
  prior, then update on named data streams (polls, statements, prices): prior -> new data -> posterior -> new prior.
- Compare with the market-implied probability (`events_probs`); the trade is the gap, only if constraints explain why the market is wrong.
- Base-rate odds for central-bank calendars: if a meeting type carries a share of hikes, odds = (share/number of such meetings)
  : ((1-share)/number of others). RBA 61% of hikes in 4 forecast months of 11 meetings: 15.3% vs 5.6% per meeting (shares of all hikes, i.e. given a hike), about 2.7:1 (source rounds to 3:1); ECB 45% in 4
  projection meetings of about 12: 11.3% vs 6.9%, about 1.6:1 (swapsball.net, Central bank decisions and inflation forecasts, 8 Mar 2018). 2018 calendars: recompute with the current one (RBA now meets 8 times a year).
- Calibration: fewer than 95% of stated 95% intervals contain the outcome; widen, but do not overcorrect (Jane Street, Probability & Markets).
- A fill is information: before accepting an easy fill on a hard-to-value package ask "conditional on being filled, what do I think the EV
  is?" (adverse selection); price-insensitive counterparties (real money, central banks) are benign, EV-motivated ones are not.
  Timing of when a narrative normalises is not forecastable by this framework.

## Worked examples
**A. Eight schools (partial pooling vs the extremes)** (Gelman et al., Bayesian Data Analysis, 3rd ed., 2014). Estimates y = (28, 8, -3, 7, -1, 1, 18, 12), se = (15, 10, 16, 11, 9, 11, 10, 18).
Complete pooling: 7.7 +/- 4.1 (chi2 about 4.6-4.7 on 7 df, moment tau^2 negative). Setting tau = its mode 0 gives every school 7.7 +/- 4.1: "too much pulling
together". Integrating over tau (bundled script, uniform prior on tau, posterior mean tau about 6.6): posterior means 11.4, 7.9, 6.1, 7.6, 5.1, 6.1, 10.7, 8.5 with
sds 6-8; the top school falls from 28 to about 11. Pr(theta_A > 28) is under 10% under the hierarchical model vs about 50% from separate estimates. WAIC 68.2 no pooling /
61.2 complete / 61.8 hierarchical; hierarchical is the safe default. Transpose: schools = markets, y = a per-market estimated edge in bp, se = its standard error.

**B. Thin-history market, normal-normal (illustrative numbers, not market data).** Peer pool says a reversion coefficient is 0.40 with between-market sd 0.10; the NOK
estimate is 0.80 with se 0.30. Weight on data = (1/0.09)/(1/0.01 + 1/0.09) = 0.10; posterior mean 0.44, sd 0.095. Prior-data check: |0.80-0.40|/sqrt(0.09+0.01) = 1.3 (< 2.5, no conflict). Act on 0.44, not 0.80.

**C. IC shrinkage** (Grinold and Kahn, Active Portfolio Management, 2nd ed., 1999). 36 months, estimated IC 0.10: w = 36*0.01/(1.36) = 0.265, use IC about 0.026. Two signals with the same IC and
correlation gamma combine to IC*sqrt(2/(1+gamma)): gamma = 0.5, IC 0.0816 each gives 0.0942 (gamma = 0 gives IC*sqrt2).

**D. Opaque-market inference** (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ex. 19.6). Previous closes 2Y: USD 2.20%, EUR 0.43%, GBP 1.54%, NOK 2.02%. Before NOK opens, moves
x = [+2.0, +1.0, +2.0] bp (USD, EUR, GBP). Correlations: USD-EUR 0.80, USD-GBP 0.85, EUR-GBP 0.87; NOK vs USD/EUR/GBP 0.75/0.84/0.82. Solving gives Y = +1.294 bp, NOK 2Y indicated 2.0329%
(NOK then printed 2.0275%, reset reference to that print; unit-diagonal Q, so equal vols are assumed and the conditional sd is 0.51 in units of NOK vol). 45 minutes later x = [+0.5, -1.5, 0.0] gives Y = -0.710 bp, inferred 2.0204%. Reproduced exactly by the selftest.

**E. Kelly with parameter uncertainty** (Paleologo, The Elements of Quantitative Investing, 2025). Optimal fraction x* is about mu/(mu^2 + sigma^2 + tau^2), tau = parameter sd. mu 0.08, sigma 0.19: 1.88 with no uncertainty;
mean uncertainty tau 0.04: 1.81; vol uncertainty tau 0.10: 1.52. Parameter uncertainty always lowers the optimal fraction; use a fraction of Kelly (a mis-estimated SR can be fatal: vol 19% and SR 0.84 imply Kelly 4.4x).

**F. Macro fair value with Bayesian priors** (BofA Global Research, US Rates Watch: Monthly rates models, Apr 2025). 10yT model fair value about 4.20-4.25%, about 25bp rich (about 1 sigma); a global state-space version gave 4.40% (about 40bp rich); DM 10y residual table: Canada -62.6bp (z -3.0, richest), Japan +54.9bp (z +2.7, cheapest). Fair-value models fail in
non-economic buying (QE, official demand): add balance-sheet and global-factor terms or sign priors. UST BVAR steady state about 2% (calibrated since 2012) with deviations from about 100bp cheap (late 2018) to about 125bp rich (1Q20) (BofA, UST RV Primer, 2 May 2022).

More cases and derivations: [references/formulas-and-cases.md](references/formulas-and-cases.md).

## Signals & interpretation
- **Shrinkage fraction B_j** (weight on the pool). B > 0.8: the unit's own estimate is mostly noise, act on the pool value or skip. B < 0.3: own data dominate.
  Report both raw and posterior values; the trade case must survive on the posterior.
- **Posterior probability beats z-scores for thin data**: P(theta_j > hurdle) from the posterior mean and sd. Require > 0.8-0.9 for an actionable model-driven edge (judgement defaults; tune with bt-validation).
- **tau posterior near 0 and J small**: data cannot separate "all equal" from "modest differences". Say so; use a half-Cauchy prior and widen bands.
- **Prior-data conflict > 2.5 sd**: revisit the prior (regime break) before updating; for regressions re-estimate if the regressor variance regime shifted.
- **Predictive band** = sqrt(sigma^2 + posterior variance). A residual inside this band is not a signal even if |z| from residual sd alone is > 2.
- **Sensitivity**: recompute with prior sd x0.5 and x2. If the conclusion flips, the data do not decide it; say so.
- **Overconfidence**: stated intervals narrower than realised; widen by the observed miss rate.

## Pitfalls
- Plugging in tau = 0 (or the posterior mode) as truth. Boundary estimates are not evidence of no heterogeneity.
- Pooling non-exchangeable units (post-regime JPY with others, CHF in negative-rate years, a new auction line with seasoned ones).
- Using a regression residual sd as `se`; overlapping returns need HAC/overlap-corrected se, otherwise shrinkage is too weak.
- Tight priors that "fit": choose strength by CV or evidence, not in-sample fit; AIC/BIC ignore parameter uncertainty and prefer over-simple models.
- Inverse-gamma(eps, eps) on a variance; uniform on log tau; Gaussian priors on a quantity bounded in [0,1] (use transformed scale).
- Treating likelihood as probability; it can exceed 1 and does not integrate to 1.
- Shrinking the result and then also applying a haircut for the same reason (double counting); shrink once and say how.
- Re-using a hold-out after peeking turns it into in-sample data. Simulate with known parameters and verify the estimator recovers them before applying to real data (selftest does this).
- Black-Litterman: tau and Omega are free parameters people tune until the answer looks right; document them and show a tau sweep.
- Opaque-market inference with a stale covariance or a benchmark with few contributors; forgetting to reset the reference after the print.
- Macro/regularised fair values break in non-economic buying; a prior does not fix a structural break.
- Kalman: diffuse P0 too small suppresses early learning; Q too large makes the "dynamic" beta noise; always show filter sd.
- Source flag: a Greene beta-binomial example states 0.3357 for a = b = 2, D = 8, N = 25, but (D+a)/(N+a+b) = 10/29 = 0.345; do not quote the book figure.

## Output
Return, per estimate:
| id | raw est | se | prior/pool mean | tau (post. mean) | B (weight on pool) | posterior mean | posterior sd | 90% interval | P(> hurdle) |
Units as the input (bp, bp/yr, ratio). Plus: prior used and why (data source, width), hyperprior, a sensitivity line (prior x0.5, x2), conflict flag,
and a one-line statement of which units were shrunk most. For event priors: prior, data streams, current posterior, market-implied probability, gap.
Hand off shrunk numbers to [rv-composite-scoring](../rv-composite-scoring/SKILL.md) and the narrative to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
- [`scripts/shrinkage.py`](scripts/shrinkage.py): `normal_normal`, `eb_shrink`, `hier_normal` (grid over tau, uniform or half-Cauchy), `jorion_shrink`, `shrink_ic`, `bayes_linreg` (with evidence), `black_litterman`, `infer_unobserved`.
  CLI: `python scripts/shrinkage.py hier --csv est.csv --id-col id --est-col est --se-col se [--prior halfcauchy]`. `python -I scripts/shrinkage.py --selftest` checks closed forms, the eight-schools numbers, the
  Grinold table, ridge equivalence, BL limits, the Darbyshire example and a simulation with known truth (EB mse about 0.55 vs MLE 1.0); exits non-zero on failure.

## Related skills
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): Kalman/TVP betas, ridge and TLS hedge ratios
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): Ledoit-Wolf, eigenvalue shrinkage, factor covariance (the Sigma used here)
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC/IR, combining signals, refinement
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores to shrink before ranking
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): OU parameters whose estimates are noisy and benefit from pooling
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC standard errors for `se`, VAR/state-space background
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): pool seasonal estimates across markets
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): leakage-safe cross-validation for prior strength
- [quant-regime-detection](../quant-regime-detection/SKILL.md): regime-dependent priors, change points
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): holdouts, multiple-testing, selection bias
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): Bayesian-regularised fair values and BVAR priors
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event probabilities versus market-implied
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): constraint-based priors
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting-level probabilities and base rates
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): Kelly fraction under parameter uncertainty, sizing a view
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): Black-Litterman and mean shrinkage in optimisation
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag and transmission between markets.

## References
- Gelman, Carlin, Stern, Dunson, Vehtari, Rubin - Bayesian Data Analysis (3rd ed., CRC Press, 2014): normal-normal update, hierarchical partial pooling, hyperprior for tau, eight schools, prior as pseudo-data
- McElreath - Statistical Rethinking (1st ed., CRC Press, 2016): regularising priors, partial vs no/complete pooling, ponds simulation
- Bishop - Pattern Recognition and Machine Learning (Springer, 2006): Bayesian linear regression, predictive variance, evidence approximation
- Murphy - Machine Learning: A Probabilistic Perspective (MIT Press, 2012): empirical-Bayes Gaussian shrinkage, James-Stein, variance-stabilising transform
- Hastie, Tibshirani, Friedman - The Elements of Statistical Learning (2nd ed., Springer, 2009): ridge and lasso as priors, effective degrees of freedom
- Grinold, Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): IC shrinkage table, regression as posterior mean, alpha = vol x IC x score
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): Jorion shrinkage, shrinkage targets, Black-Litterman, mean-error warning
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): Kalman/EWMA, Harvey-Shephard filter, spiked-covariance shrinkage, Kelly with parameter uncertainty
- Hamilton - Time Series Analysis (Princeton University Press, 1994): Kalman recursions, parameter-uncertainty Monte Carlo, Doan-Litterman-Sims prior, Bayesian unit roots
- Dunis, Laws, Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003): diffuse-prior Kalman, ridge-regularised cointegration
- Greene - Econometric Analysis (8th ed., Pearson, 2018): Bayesian regression with informative normal prior, Bayesian model averaging
- Shalizi - The Truth about Linear Regression (CMU lecture notes, 20 Oct 2025): ridge with CV-chosen lambda, regime dependence of the optimal slope
- Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): Ledoit-Wolf shrinkage and bias/variance
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): Bayesian inference of an opaque market's moves (Ex. 19.6); inferring flow from request size
- O'Hara - Market Microstructure Theory (Blackwell, 1995): Glosten-Milgrom Bayesian quotes, Kyle learning step
- Papic - Geopolitical Alpha (Wiley, 2021): constraint model, net assessment as subjective prior, event-probability cases
- Ross - A First Course in Probability (8th ed., Pearson, 2010): normal-normal posterior, best linear predictor
- Jane Street - Probability & Markets (interview primer, undated): conditional probability, calibration, adverse selection of fills
- Hakim (U. Washington) - Probability & Statistics Primer (v2.0, 2 Jan 2009): Bayes rule, likelihood vs probability, bivariate Gaussian conditional
- BofA Global Research - US Rates Watch: Monthly rates models (Braizinha, Craig; Apr 2025 and Aug 2025): state-space fair value, Bayesian sign-restricted VAR, DM residual table
- BofA Global Research - US Rates Primer: UST RV Primer (Zhang, Braizinha, Axel; 2 May 2022): BVAR steady state and deviation range
- Willer, Saunders - Trading Global Macro Markets (Wiley, 2026): Black-Litterman reverse optimisation for sizing
- swapsball.net - Central bank decisions and inflation forecasts (8 Mar 2018): base-rate odds by meeting type
- Black, Litterman - Global Portfolio Optimization (Financial Analysts Journal, 1992) (external): original Black-Litterman model
- Efron, Morris - Stein's Paradox in Statistics (Scientific American, 1977) (external): empirical-Bayes shrinkage intuition
