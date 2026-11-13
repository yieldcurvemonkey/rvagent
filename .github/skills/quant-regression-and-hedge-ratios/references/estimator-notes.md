# Estimator notes: formulas and derivations

Companion to [SKILL.md](../SKILL.md). Notation: y = target change, x = hedge change (bp or price), n = observations,
sxx, syy, sxy = demeaned second moments, rho = correlation, DV01 positive for long duration.

## 1. OLS is the minimum-variance hedge
- Hedged P&L = -DV01_y dy - DV01_x dx. Minimising its variance gives DV01_x = -DV01_y sxy/sxx = -beta DV01_y.
  Residual variance = DV01_y^2 sd_y^2 (1 - rho^2) = DV01_y^2 sd_resid^2 (Tuckman and Serrat, Fixed Income Securities 4th
  ed, 2022, Appendix A6).
- Several hedge instruments: minimising sd(dV_P + sum beta_i dV_i) gives exactly the coefficients of the regression
  dV_P = -sum beta_i dV_i + e (Golub and Tilman, Risk Management: Approaches for Fixed Income Markets, 2000).
- Zero-expected-return hedge: x_h = -rho (sd_c / sd_h) x_c = -beta x_c; variance (1 - rho^2) sd_c^2 x_c^2 and the Sharpe
  ratio of the hedged position improves by 1/sqrt(1 - rho^2) (Paleologo, The Elements of Quantitative Investing, 2025).
- Sampling variance of the slope on centred data: Var(beta_hat) = s_e^2 / (n s_x^2); Var(alpha_hat) = s_e^2 / n
  (Palomar, Portfolio Optimization, 2025). Re-estimate on a rolling window because both drift.
- Best linear predictor: slope cov(X,Y)/var(X), no linearity or Gaussianity needed; changing the distribution of X
  changes the optimal slope even if P(Y|X) is unchanged (Shalizi, The Truth about Linear Regression, 2025).
- Yield beta decomposition: hedge ratio HR = (PVBP_t / PVBP_h) x B_t with B_t the regression slope of target yield change
  on hedge yield change; with the yield value of a 1/32 the ratio inverts. Ratio of durations is not the hedge ratio; use
  full-price dollar durations (Salomon Brothers, Understanding Duration and Volatility, Sep 1985).
- Price-regression hedge for instruments with no yield: dP2 = beta dP1 (Duering, Fixed Income Trading and Risk
  Management, 2021, Ch.36). Forward/TBA prices must be carry-adjusted before regressing.
- Market value form: M2 = -M1 beta D1*/D2* (real money thinks in market value, desks in nominal).

## 2. TLS / Deming
- Model: x = x* + eta, y = beta x* + eps, delta = var(eps)/var(eta) (Deming 1943, external). Closed form in SKILL.md.
  Limits: delta -> infinity: OLS (x noise-free); delta = syy/sxx: sign(sxy) sd_y/sd_x; delta = 1: orthogonal regression.
- Orthogonal regression is the first eigenvector of the 2x2 covariance: lambda+- = (sxx + syy)/2 +- sqrt(((sxx + syy)/2)^2
  - sxx syy + sxy^2); eigenvector (1, (lambda+ - sxx)/sxy); slope (lambda+ - sxx)/sxy, intercept ybar - slope xbar
  (Duering 2021, Ch.33). Symmetric under x <-> y. It is not scale invariant: change units of one leg and the slope
  changes beyond rescaling, which is why delta must be justified.
- Attenuation: OLS slope = beta var(x*) / (var(x*) + var(eta)). Example in the self-test: beta 1.5, var(x*) 1,
  var(eta) 0.25 gives OLS 1.2; Deming with delta = 4 gives 1.5.
- Mark-noise delta (this skill's derivation): if the observed level is truth + iid mark noise nu_t, a daily change is
  d(true) + nu_t - nu_(t-1), whose lag-1 autocovariance is -var(nu). Hence delta = cov1(dy)/cov1(dx). Needs both
  autocovariances negative and n large (the estimate is noisy); a bid-offer based estimate is an alternative.
- Ordering of regression legs matters for any levels cointegrating regression too: y on x and x on y give different
  vectors unless R-squared = 1 (Hamilton, Time Series Analysis, 1994; Palomar 2025). Johansen avoids it.
- PCA is not a regression (the first factor is not the regression line) and does not depend on which variable is
  dependent; "ephemeral correlation between factors is the main pitfall" (Huggins and Schaller, Fixed Income Relative
  Value Analysis 2nd ed, 2024, Ch.3).

## 3. Treasury Bond Basis hedge ratios and futures
- Hedging the long bond (L) with a shorter bond (S), sigma = sd of yield changes, rho = correlation (Burghardt et al,
  The Treasury Bond Basis 3rd ed, 2005, Appendix to Ch.5):
  - Conventional = DV01_L / DV01_S.
  - Yield beta = DV01_L / (DV01_S sigma_S/sigma_L).
  - Yield delta = DV01_L / (DV01_S (sigma_S/sigma_L) rho): regression slope of dy_S on dy_L is beta x rho, so this hedge
    has zero expected P&L.
  - Minimum variance = DV01_L rho / (DV01_S sigma_S/sigma_L).
- Futures: DV01_fut = DV01_CTD / CF; N = DV01_portfolio / DV01_fut; yield-beta form
  HR_i = DV01_i beta_i / (DV01_fut beta_CTD) with betas against one reference yield, beta adjustment on both sides.
- Vol-duration beta fit (weekly yield-change sd on modified duration, 1990 to date): y = -0.0002 x + 0.0111, R-squared
  0.81, valid for durations 2 to 12.5; beta = ratio of fitted sds relative to the on-the-run long bond.
- Option-adjusted DV01: central difference of theoretical futures prices across yield shifts (the rule-of-thumb DV01
  jumps at CTD crossovers). Repo DV01 is a separate factor: dF/dR = (S + AI) n/360 without a coupon; report it negative.
- Cash-futures conversion (Duering 2021, Ch.28): lambda = c_CTD (N/N_F) (PVBP_bond / PVBP_CTD). After delivery
  notification the 1bp P&L switches from converted CTD DV01 to the delivered bond's DV01; the hedge becomes 1:1 par per
  contract after the last trading day.
- Tailing: forward and futures hedges scale by 1/(1 + r d/360) (Tuckman and Serrat 2022, Ch.11).
- STIR sensitivity-matrix hedges: unknowns = start level + FOMC jumps; contracts weight x exposure BPV / contract BPV (41.67
  one-month, 25 three-month); the system is overdetermined, avoid contracts with few post-meeting days (Huggins and
  Schaller, SOFR Futures and Options, 2022, Ch.2).

## 4. Kalman filter details
- General form (Hamilton 1994): xi_(t+1) = F xi_t + v, y_t = A'x_t + H'xi_t + w, Q = Var(v), R = Var(w).
  Update: xi_(t|t) = xi_(t|t-1) + P H (H'PH + R)^-1 (y - A'x - H'xi_(t|t-1)); P_(t|t) = P - PH(H'PH + R)^-1 H'P;
  predict xi_(t+1|t) = F xi_(t|t), P_(t+1|t) = F P F' + Q. P and K do not depend on the data. Initialisation for stable F:
  vec(P_1|0) = (I - F kron F)^-1 vec(Q); otherwise a diffuse guess (bigger P = more uncertainty).
- Time-varying coefficient regression: y_t = x_t' beta_t + w_t; random-walk beta is F = I. One-step forecast MSE
  x_t' P_(t|t-1) x_t + sigma^2; log-likelihood -(T/2) ln 2pi - 0.5 sum ln f_t - 0.5 sum e_t^2/f_t.
- Dunis et al (Applied Quantitative Methods for Trading and Investment, 2003): scalar gain k_t = P x^2 / (P x^2 + R) in
  [0,1]; k = 0 when Q = 0, k = 1 when R = 0; Q = 0 with a diffuse prior reproduces OLS. Q/R knob: 1 fast and noisy, 0.1
  smooth, 0.02 misses a jump. Intervention analysis: raise Q at a known event (set to 50 at the level shift) to re-adapt;
  raise R to ignore an irrelevant event; only to inject genuine prior knowledge. Diffuse prior P0 = kappa I with kappa
  large (100,000 there); hyperparameters by maximising the prediction-error likelihood (quasi-Newton). Random-trend
  beta: beta_t = beta_(t-1) + delta_(t-1) + eta1, delta_t = delta_(t-1) + eta2.
- Pairs recipe on price levels (Palomar 2025, eq 15.3): observation y1 = mu + gamma y2 + eps; state (mu, gamma) random
  walk; spread z = (y1 - gamma_(t|t-1) y2 - mu_(t|t-1)) / (1 + gamma_(t|t-1)); initialise from a training LS fit on T_LS
  samples: s_eps^2 = Var(eps_LS); mu_1 ~ N(mu_LS, Var(eps_LS)/T_LS); gamma_1 ~ N(gamma_LS, Var(eps_LS)/(T_LS Var(y2)));
  s_mu^2 = alpha Var(eps_LS); s_gamma^2 = alpha Var(eps_LS)/Var(y2); alpha = 1e-5 basic, 1e-6 for the momentum model.
  Momentum extension: state (mu, gamma, gamma-dot) with transition [[1,0,0],[0,1,1],[0,0,1]]: less noisy gamma. Partial
  cointegration: add an AR state with transition diag(1, 1, rho), |rho| < 1.
  The skill's script uses the same Q structure (q_ratio = alpha) but defaults to 1e-4 for daily bp changes and applies it
  in change space; tune by likelihood on a burn-in and freeze.
- Time-varying alpha/beta template (Tsay, Analysis of Financial Time Series 3rd ed, 2010): r_t = alpha_t + beta_t r_M,t
  + e_t with both random walks, illustrative (sigma_eta, sigma_eps, sigma_e) = (0.02, 0.04, 0.1), diffuse start.
- Local level = EWMA: mu_(t+1|t) = mu_(t|t-1) + K v_t with K = Sigma/V. Muth: kappa = noise ratio; for kappa >> 1 the new
  data weight is about 1/(1 + kappa) (long half-life); a mean-reverting state gives a smaller K (Paleologo 2025).
- Filtering vs smoothing: smoothed states use future data (RTS backward recursion J_t = P_(t|t) F' P_(t+1|t)^-1);
  signals and backtests use filtered states.
- Parameter uncertainty: total MSE = filter uncertainty + parameter uncertainty; draw theta ~ N(theta_hat, I^-1/T) about
  2000 times (Hamilton 1994). Identification problems show up as a singular Hessian; parameterise covariances by Cholesky.
- Calibration hygiene: fit any filter half-life or Q on a burn-in (for example 252 days) and freeze it; refitting each
  day makes the filter time-varying, a full-sample fit is look-ahead.

## 5. EWMA and rolling
- EWMA beta = sum_i w_i y_i x_i / sum_i w_i x_i^2 with w_i = lambda^(age), lambda = 0.5^(1/half-life). Half-life 20, 30,
  60, 120 days gives lambda 0.966, 0.977, 0.989, 0.994.
- Rolling pathologies (Dunis et al 2003): window choice is a bias-variance trade-off; adjacent windows share (n - p)/n of
  data so the beta path is autocorrelated by construction; a 5-day spike in a 20-day window peaks and persists 15 more
  days ("ghost" effect); estimates lag. WLS with linear or exponential decay reduces lag and ghosts but uses one decay
  rate for all coefficients.
- Recursive least squares accuracy is governed by the smallest eigenvalue of X'X (Shafer and Vovk, Game-Theoretic
  Foundations for Probability and Finance, 2019): a nearly collinear design keeps the estimate noisy however long the
  sample.

## 6. HAC / robust standard errors
- Newey-West (Bartlett): C = sum e_t^2 x_t x_t' + sum_(j=1..L) w_j sum_t (x_t e_t e_(t-j) x_(t-j)' + transpose), w_j =
  1 - j/(L+1); sandwich (X'X)^-1 C (X'X)^-1; L = int(4 (n/100)^(2/9)) (Tsay 2010) or about n^(1/4) (Greene, Econometric
  Analysis 8th ed, 2018). Monthly data 12 to 24 lags, quarterly 4 to 8 (Wooldridge, Introductory Econometrics 2nd ed).
  Poor in small samples with strong serial correlation; Newey and West (1987, external).
- Single coefficient version: sum e_t^2 v_t^2 / (sum v_t^2)^2 with v the residual of x_j on the other regressors.
- Newey-West SEs for a 5-lag quarterly regression moved 0.04738 to 0.07806 (Greene 2018).
- Use Ljung-Box (and Wald tests, not Chow, when variances differ across regimes) rather than Durbin-Watson with lagged
  dependents.
- Heteroskedastic OLS example: reported slope SE 0.22 vs simulated true 0.49 (Shalizi 2025). Case bootstrap CI
  (1.45, 3.84) vs analytic (1.10, 4.17) there. Residual bootstrap is wrong under heteroskedasticity; all of these assume
  independent rows, so use moving blocks on rates data.

## 7. Covariance-based and regression-equivalent hedges
Source: Darbyshire, Pricing and Trading Interest Rate Derivatives (3rd ed., 2022).
- CoVaR multiplier c = sqrt(S'QS) with S the DV01 strip and Q the covariance of bp changes (never levels);
  VaR 5% = 1.644 c, 1% = 2.326 c. Single-instrument minimiser S_trade = -(1/q_ii) c dc/dS; multi-instrument on subset M:
  S_trade = -Q_MM^-1 Q_M S, i.e. np.linalg.solve(Q[M,M], -Q[M,:] @ S). It equals the multivariate regression of portfolio
  risk on the subset. Several single trades at full size can raise VaR: trade about 50% and re-run.
- MLSR directionality hedge: y = dr_c S_ini, X = dr_c [x1 : x2], beta = (X'X)^-1 X'y, S = S_ini - [x1 : x2] beta. Regressing
  on every bucket makes the residual identically zero. Regressing on PC1 loadings reproduces the PCA hedge.
- PCA minimal-adjustment hedge: min 0.5 |x|^2 s.t. e_i'(S_ini + x) = 0, closed form x = -E_H E_H' S_ini. Freeze buckets with
  constraints, not by sub-selecting the covariance (that changes the eigenvectors). With 3 instruments, neutralising PC1
  and PC2 leaves only a multiple of PC3.
- Example (2s5s10s, S_ini = [-1, 2, -1, 0]): naive PC1 divide about [-0.89, 1.94, -1.30]; minimal adjustment
  [-1.07, 1.94, -1.05]; MLSR on 5y only [-1.17, 1.94, -1.17]; MLSR on 2y and 10y [-1.43, 1.94, -0.37] (lowest VaR, furthest
  from the classic fly).

## 8. Fly regression weights and the four-method comparison
- Convention: fly = 2 y5 - y2 - y10 (positive = belly cheap), slope = y10 - y2. Regress fly = a + b1 slope + b2 y5 + e.
  Algebra: e = (b1 - 1) y2 + (2 - b2) y5 - (1 + b1) y10, so the yield weights are (-(1 - b1), 2 - b2, -(1 + b1)). Another
  source writes fly with opposite sign (2s - 2 x 5s + 10s), so re-derive under your own convention. OLS residuals are
  orthogonal to the regressors by construction (checked in the self-test).
- PCA divide-by-PC1: positions / PC1 loadings; needs risks summing to zero; fails for slope-shaped PC1 ([-1, 0, 1] gives
  weights [1, inf, -1]). Loadings (0.660, 0.604, 0.447): (-1, 2, -1) / loadings = (-1.51, 3.31, -2.24), rescaled
  (-0.91, 2, -1.35).
- KKT minimum change: x = -e1 e1' t, so t + x = (I - e1 e1') t (Quantitative Finance Stack Exchange, Hedging a trade for
  PCA component neutrality, Nov 2019). Worked: (-1.1002, 2, -1.0780).
- Minimum-VaR wings with belly fixed at 2: w_wings = -Sigma_ww^-1 Sigma_w5 x 2, giving (-1.48, 2, -0.38) on the same
  covariance: the 2y is overweighted because it correlates more with the 5y.
- Risk mapping across instrument sets (swaps to bonds/futures): S2 = A S1; the Jacobian is entirely a design choice
  across different discount curves; start with a (multi) linear regression (Quantitative Finance Stack Exchange,
  Projecting swap risk on bonds and futures, Oct 2024). Univariate-beta Jacobians ignore collinearity among liquid points.

## 9. Shrinkage and robust fits
- Ridge: beta = (X'X + lambda I)^-1 X'y; centre variables, standardise non-comparable units, do not penalise the
  intercept; orthonormal inputs give OLS/(1 + lambda); df(lambda) = sum d_j^2 / (d_j^2 + lambda) (Hastie, Tibshirani,
  Friedman, The Elements of Statistical Learning 2nd ed, 2009). Elastic net keeps correlated tenors together; choose
  lambda by CV (one-standard-error rule), never by training error (Murphy, Machine Learning: A Probabilistic
  Perspective, 2012). Illustration: lambda 0.01 cut residual variance 67% vs a market hedge 2%; lambda 0 sum|w| 404%,
  0.1 only 46% reduction (Dunis et al 2003).
- Prior as pseudo-data: prior beta ~ N(beta0, tau^2) is one extra row y* = beta0, x* = 1 with variance tau^2, then WLS
  (Gelman et al, Bayesian Data Analysis 3rd ed, 2014).
- Robust: t-error regression by EM/IRLS with weights w_i = (nu + 1)/(nu sigma^2 + e_i^2); Huber loss r^2/2 for |r| <= delta,
  delta |r| - delta^2/2 beyond; robust fits handle heavy tails, not nonlinearity or correlated noise. Hat values
  H_ii = (1/n)(1 + (x_i - xbar)^2/s_x^2), Cook's D = e_i^2 H_ii / ((p + 1) s^2 (1 - H_ii)^2) (Shalizi 2025): a big residual
  at high leverage is the red flag.
- Sparse hedge baskets: l0 or reweighted-l1 tracking, lambda very sensitive (1e-8 to 1e-6 gave very different
  cardinalities); two-step select-then-refit is suboptimal (Palomar 2025).
- Collinearity: Var(beta_hat) = sigma^2 (X'X)^-1; condition number > 20 (columns scaled to unit length) matters;
  collinearity among three or more variables can be invisible pairwise, so inspect eigenvalues of Var(X).

## 10. Cointegrating hedge ratios (levels)
- Engle-Granger: OLS of y on x consistent; residual DF test with Davidson-MacKinnon critical values (no trend: 1% -3.90,
  5% -3.34, 10% -3.04; with trend 5% -3.78). OLS t-statistics are invalid; use DOLS (2 leads and lags of dx) for a valid
  t on beta (Wooldridge 2nd ed: T-bill 6m on 3m beta 1.038, se 0.0081, t for beta = 1 is 4.69).
- Maximum-OU-likelihood hedge ratio: choose the beta whose spread has the best OU fit (grid search on the likelihood), not
  the OLS beta (Leung and Li, Optimal Mean Reversion Trading, 2016). Hedge ratio choice changes the OU parameters and so
  the optimal thresholds.
- Train/test: hedge ratio from the first 252 days only; z from training moments; entry |z| >= 2, exit <= 1 (Chan,
  Quantitative Trading, 2009). See [quant-cointegration](../../quant-cointegration/SKILL.md).
