# Advanced covariance methods and extra worked examples

Detail moved out of [SKILL.md](../SKILL.md). Load it when the basic EWMA / shrinkage / PCA recipe is not enough:
horizon-dependent correlation, multivariate GARCH, heavy-tailed estimators, sparse and hierarchical structure, realised
(intraday) PCA, and the longer hedge examples.

## 1. Horizon-dependent correlation (mean-reverting vector model)

If spreads mean-revert toward each other, correlation depends on the horizon. Model dX = -Theta (X - mu) dt + S dB.
Off-diagonal S creates correlation by common shocks. Off-diagonal Theta creates correlation by attraction, and that
correlation is horizon-dependent (negative at 1 day, zero at 1 month, positive at 6 months is possible)
(Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).

- Conditional covariance over horizon tau: `vec(Sigma_tau) = (Theta (+) Theta)^-1 (I - exp(-(Theta (+) Theta) tau)) vec(S S')`,
  with Kronecker sum `A (+) B = A (x) I + I (x) B`. Use a matrix exponential through an eigendecomposition, never element-wise.
- Bivariate illustration: with diagonal S, correlation is about 0 at 1 day, 0.30 at 1 month, 0.6 at 3 months. With
  S = [[1, -0.2], [-0.2, 1]] it is -0.4 at 1 day and +0.4 at 3 months (sign flip) (same source).
- Practical test: compute correlation on non-overlapping 1d, 1w, 2w, 3w, 1m, 2m, 3m changes. If it moves by more than
  the sampling error (roughly 2/sqrt(n_obs) at that horizon), use the horizon-specific matrix for hedges at that horizon
  and consider a mean-reverting vector model (see `quant-mean-reversion-ou`). If it is flat, one covariance plus PCA is fine.
  Fly example: "Over short horizons, there is essentially no directionality in the butterfly spread. But over longer
  horizons, the butterfly exhibits considerable directionality" (same source).
- Initialising the fit: match the model's 1-day conditional covariance to the empirical 1-day covariance, match
  exp(-Theta tau) to the one-lag regression matrix, set the means to sample means. Three variables = 21 parameters.

## 2. Multivariate GARCH family (when a mean-reverting vol forecast matters)

(Bourgoin, in Dunis, Laws & Naim, Applied Quantitative Methods for Trading and Investment, 2003; Tsay, Analysis of
Financial Time Series, 3rd ed., 2010; Paleologo, Elements of Quantitative Investing, 2025)

| Model | Recursion | Parameters (bivariate) | Use |
|---|---|---|---|
| EWMA / RiskMetrics | `S_t = (1-l) e e' + l S_{t-1}`, one l | 1 | default; PD by construction if ONE l is used for all elements; no mean reversion, flat forecast term structure |
| GARCH(1,1) | `s2_t = w + a e2 + b s2_{t-1}`, long-run `w/(1-a-b)` | 3 per series | forecasts beyond one step; EWMA is `w=0, a+b=1` ("GARCH is EWMA with an offset") |
| Variance targeting | `w = s2_bar (1 - a - b)` | removes one | no loss of likelihood in the cited example |
| Scalar GARCH + targeting | one `a`, one `b` for all elements | 2 for any N | keeps mean reversion; likelihood below optimal-decay EWMA (-10,489.96 vs about -10,481) |
| Diagonal GARCH | element-wise `a_ij`, `b_ij` | 9 + 17 constraints | allow `w_12 < 0`, else long-run correlation is forced positive |
| "Fast GARCH" | fit univariate GARCH to an equal-weighted index, reuse `a, b` for every element | 2 | persistence is similar across components of one asset class |
| CCC / DCC | `S_t = D_t C D_t`; DCC `Q_t = a z z' + (1-a) Q_{t-1}` | few | recipe: mean model, univariate vols, standardise `z = D_t^-1 e`, then fixed or EWMA correlation of `z` |

- GJR adds `g * 1[e<0] * e2`, constraint `a + b + g/2 < 1`; start from the GARCH `a, b` with `g` about 0.01.
- Optimal EWMA decay by ML: maximise `sum(-0.5 ln s2_t - 0.5 r_t^2 / s2_t)` over lambda. Defaults when not fitted: 0.94 daily,
  0.97 monthly (Bourgoin). 0.94 puts half the weight on the last 11 observations (half-life 11.2); 0.98 on the last 34.
- Initialise every recursion at the sample (unconditional) variance. Fast GARCH and RiskMetrics both mis-state correlation in stress.
- Hang Seng / Nikkei 2006-2008 daily: fitted lambda 0.9305, "in the typical range" (Tsay).
- GARCH needs data (1000 observations still leave parameter error near 0.1); it works best on a few series, short horizons
  (days) and option-like books; apply it to the dominant factor of a risk model rather than to every instrument (Palomar,
  Portfolio Optimization, 2025; Grinold & Kahn, Active Portfolio Management, 2nd ed., 1999).
- Markov-switching vol is the alternative when vol has two clear states; expected duration of the high state = 1/(1-p00).
  USD/DEM 1995-98: high vol 0.635, low 0.249, p00 = 0.805, so 5.1 days (Roche-Rockinger, in Dunis et al., 2003). See `quant-regime-detection`.

## 3. Heavy-tailed and robust estimators

(Palomar, Portfolio Optimization: Theory and Application, 2025)
- Student-t MLE fixed point (nu about 4-5 for financial data): `w_t = (nu + N) / (nu + (x_t - mu)' S^-1 (x_t - mu))`,
  `mu = sum w_t x_t / sum w_t`, `S = (1/T) sum w_t (x_t - mu)(x_t - mu)'`. Iterate (3-5 passes at T=200, N=100, nu=4).
  Covariance = nu/(nu-2) * S. Needs T > N+1. Outliers get small weights.
- Tyler: `S = (1/T) sum (N x_t x_t') / (x_t' S^-1 x_t)`; needs T > N; scale is lost, so re-attach vols separately.
- Ranking in the source simulation: heavy-tailed MLE best, Tyler and spatial median close, Gaussian MLE worst. One outlier
  at T=10, N=2 ruins the sample covariance. Spatial median (argmin sum of Euclidean norms) is the robust location.
- Gerber statistic (see SKILL.md) is the rank-like alternative; it discards magnitude entirely. Use Student-t MLE when you
  want to keep magnitude information with down-weighted outliers.
- Model |u| rather than u2 for specific variances to limit outlier influence, then correct the bias (Grinold & Kahn, 1999).

## 4. Spiked-eigenvalue theory (how many factors, how much shrinkage)

(Paleologo, 2025)
- With gamma = N / T_eff, a true factor eigenvalue (on whitened data) above `1 + sqrt(gamma)` is detectable (BBP threshold).
  Below it the sample eigenvector has no information. Sample eigenvalues are biased up, so the factor variance of a
  portfolio is overstated by about gamma.
- Shrink spiked eigenvalues: `l(lambda) = k1 * lambda - k2`, `k1` in (0,1); offset-only shrinkage (`lambda - gamma`) fails
  under heavy tails (t5), proportional scaling works better.
- Choose the number of factors with: `lambda_k >= 1 + sqrt(gamma)`, scree / log-scree, maximum eigen-gap (Onatski), or
  the Bai-Ng penalty. Err toward MORE factors: too few understates risk and hurts Sharpe steeply, too many costs little.
- Two-stage weighted PCA (Procedure 7.1): fast half-life time-weights, first SVD with p (e.g. 5) PCs, idio proxy
  sigma_i^2 = mean residual^2, reweight by 1/sigma_i and a slow half-life, second SVD, shrink factor variances, idio variance =
  average of residual eigenvalues, unscale. With p=0 this is PCA on the correlation matrix.
- Normalise by idio vol before PCA to concentrate variance in the first PCs (50% variance needs 30 factors on raw returns,
  20 on total-vol z-scores, 10 on idio-vol z-scores for Russell 3000 2007-2017).
- Impute loadings for assets outside the estimation set by time-series regression on the factor returns.

## 5. Sparse and hierarchical structure

- Sparse inverse covariance (covariance selection): `max log det X - Tr(S X) - rho * sum |X_ij|`. Zeros in the inverse
  covariance = conditional independence. On US swaps (rho = 0.1) the graph clusters rates by maturity. If the penalised
  graph splits into clusters, optimal sparse baskets live inside one cluster (d'Aspremont, Identifying Small Mean Reverting
  Portfolios, 2008). 100 days of 1Y-30Y USD swaps: the greedy mean-reversion measure saturates at 3-5 legs
  (k=1..8: about 0, 35, 128, 178, 213, 247, 252, 252); k=3 gave a 3Y -0.288 / 4Y +0.806 / 5Y -0.517 fly. A 1bp bid/offer
  removed the convergence profit, so test any covariance-derived basket against costs.
- Hierarchical risk parity (Lopez de Prado, Advances in Financial Machine Learning, 2018): distance `d_ij = sqrt(0.5 (1 - rho_ij))`;
  single-linkage clustering; quasi-diagonalise; recursive bisection with inverse-variance weights inside each cluster and
  split `alpha = 1 - V1/(V1+V2)`. No matrix inversion. Numerical example (10 assets, condition number 150.9): out-of-sample variance
  critical-line optimiser 0.1157, inverse-variance 0.0928, HRP 0.0671. Use it for combining many correlated sleeves.
- Condition number `|lambda_max / lambda_min|` (Markowitz's curse): grows with correlated assets; above about 1e3 treat any
  inverse-based weight as unstable.
- N(N+1)/2 independent observations are needed for a non-singular N x N matrix (N=50 needs 5 years of daily IID data).

## 6. Realised (intraday) covariance and PCA

(Ait-Sahalia & Xiu, Principal Component Analysis of High-Frequency Data, 2019)
- Spot covariance per non-overlapping block, truncating jumps: `c = (1/(k dt)) sum dX dX' 1{||dX|| <= u}`, `u = 3 * sqrt(avg c_ii) * dt^0.47`.
- Hygiene: 1-minute sampling to limit microstructure noise and asynchronicity, drop overnight returns, one primary venue,
  fix eigenvector sign by forcing a chosen entry positive. Do not chain overnight and intraday returns (Hasbrouck, Empirical
  Market Microstructure, 2004).
- Integrated-covariance PCA is the wrong object if eigenvectors move inside the window. S&P 100 2003-2012: PC1 30-40% of
  variance, over 60% in crisis.
- Bid-ask bounce (negative lag-1 autocovariance) inflates short-horizon variance. Longer intervals converge to efficient-price variance.

## 7. Evaluating a covariance model (details)

(Paleologo, 2025; Grinold & Kahn, 1999)
- QLIKE `mean(r2/f - ln(r2/f) - 1)` and MSE of `r2` are robust to a noisy unbiased variance proxy; QLIKE punishes under-forecasts more.
- Multivariate: (a) re-run the production strategy under each candidate covariance; (b) random-portfolio realised variance;
  (c) minimum-variance portfolios under `b'w = 1`: the true covariance gives the lowest realised variance; (d) Mahalanobis test
  `var_t( (1/n) r_t' Omega^-1 r_t )`, lower is better, about 2/n is near-perfect up to scale; (e) QDIST `sum(r' Omega^-1 r + log|Omega|)`.
- Ancillary: turnover of the factor-mimicking portfolios `||P_t - P_{t-1}||`, beta error `sum ||beta_pred - beta_realised||^2`.
- R2 is not a model-selection tool (inflated by random factors; sign rotations leave it unchanged but break the factor covariance).
- Exceedance check: about 5% of realised outcomes beyond 2 sigma of the forecast. Kahn (1997), 29 funds: structural forecasts had
  0 three-sigma and 1 two-sigma (3%) events, trailing 3-year history 1 and 5 (17%) (Grinold & Kahn, 1999).

## 8. Extra hedge examples (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022)

**Four-bucket book.** Daily bp-change covariance from a 9-day simulated sample (2Y/5Y/10Y/30Y):
`Q = [[8.7,7.4,5.1,2.2],[7.4,7.3,4.7,2.2],[5.1,4.7,4.9,1.8],[2.2,2.2,1.8,1.9]]` bp2, eigenvalues 19.5 / 1.53 / 1.06 / 0.55,
PC1 = (0.65, 0.59, 0.44, 0.20). Strip S = (2Y -10,000; 5Y +2,500; 10Y +10,000; 30Y -4,000) per bp.
Published: c = 16,174; VaR 5% = 26,590; VaR 1% = 37,620. Single-instrument minimum-variance trades: 2Y +2,948 (cuts c by 15.6%),
5Y +2,304 (7.7%), 10Y -475 (0.2%), 30Y +3,373 (4.1%); best pair 2Y and 10Y +8,562 / -9,476 (cuts c just over 70%).
Only one single-instrument trade is valid at a time; doing several at full size can raise VaR, so trade about 50% of each and
re-run. The book is dominated by curve (RV) risk: the best single hedge cuts only 15%.
(Recomputing from the rounded Q printed above gives c = 16,402 and the 2Y hedge +3,023: rounding of Q, within 1.5%.)

**Desk aggregation.** Alpha (-180, -10, 180, 25) c = 336; Bravo (-50, -10, -50, -25) c = 291; combined (-230, -20, 130, 0)
c = 529 against the sum 627. Diversification from correlation is real but only as stable as Q.

**Basis versus delta proxy.** S = (3M10Y -4,000; 3M30Y -18,000; OIS10Y -110,000; OIS30Y -290,000), c = 133,153. Hedging the
basis book with 3M delta alone (+5,790; +19,838) cuts c by 25% to 101,958. Outright vols (s.d. about 7.0) dwarf basis vols
(about 0.9), so run SEPARATE PCAs / covariance blocks per risk type or the outright variance swamps the basis.

**Cash vs IMM-date interpolated rate.** `Z = a X1 + (1-a) X2`, `a = (D_3M - D_f)/D_3M`, `D_3M = 91` days:
`q_X1Z = a s1^2 + (1-a) rho s1 s2`; `q_ZZ = a^2 s1^2 + 2a(1-a) rho s1 s2 + (1-a)^2 s2^2`. With s1 = 1.0, s2 = 1.5, rho = 0.75 on 10 March:
q12 = 1.008, q22 = 1.021, S0 = +1,950 gives hedge -1,926 and c_min = 126.

**Correlation add-on to a margin.** `Q_model = A' Q A`; add `15% * (sqrt(x' Q_model x) - sqrt(x' diag(diag(Q_model)) x))` to
the zero-correlation margin. Negative correlations can cut the margin too far.

**Fly hedging with Q.** S_ini = [-1, 2, -1, 0]. Minimum variance on 5Y: [0, -0.344, 0, 0]; on 2Y and 10Y: [-0.476, 0, 0.616, 0]; regression
on unit vectors gives the identical result; regression on PC1 gives [-0.066, -0.061, -0.045, 0]. More hedge degrees of freedom lower
variance but move the trade away from its intended structure.

**EUR forward-rate correlations (Aug 2016).** 2Y3Y / 5Y5Y 0.87, 2Y3Y / 10Y20Y 0.81, 2Y3Y / 30Y20Y 0.81, 5Y5Y / 10Y20Y 0.92,
5Y5Y / 30Y20Y 0.89, 10Y20Y / 30Y20Y 0.96; annual normal vols 36.6, 58.6, 68.8, 67.3 bp.
