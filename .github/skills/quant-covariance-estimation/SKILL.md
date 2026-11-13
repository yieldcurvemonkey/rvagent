---
name: quant-covariance-estimation
description: Estimate and sanity-check covariance and correlation matrices of rate, spread, fly, futures, STIR and vol changes for hedging, PCA, VaR and portfolio sizing - EWMA (half-life, lambda), fast-vol/slow-correlation, Ledoit-Wolf and PCA/factor shrinkage, robust Gerber and Student-t estimators, correlation smoothing, window and sampling-frequency choice, asynchronous/time-zone and overlap fixes, horizon-dependent correlation, QLIKE model tests, and min-variance hedges and Jacobian transforms from the matrix. Use when asked for covariance matrix, risk matrix, realised vol, correlation matrix, EWMA vol, half-life, shrinkage, Ledoit-Wolf, Gerber, robust correlation, condition number, positive definite, rolling vs exponential window, vol estimate for a trade, correlation between markets or curves, min-variance hedge ratio, VaR multiplier, or why a correlation or hedge ratio is unstable.
---

# Covariance estimation for rates RV

Every RV sizing decision (DV01-neutral vs beta-weighted spreads, PCA-neutral flies, VaR, cross-market legs, trade-level
risk budgets) rests on a matrix of co-movement estimated from changes. The matrix is noisy, regime-dependent and often
estimated from too little history. This skill fixes the estimator choice: what to difference, whether to demean, how to
weight time, when to shrink or impose factor structure, when to go robust, how to match horizon, and how to test the result.

## When to use
- Build or refresh the covariance behind a hedge ratio, fly weight, PCA, VaR multiplier, risk limit or optimiser.
- "What vol/half-life/window should I use?", "Is this correlation stable?", "Is the matrix singular or ill-conditioned?"
- Cross-market legs (e.g. 10y UST vs Bund vs gilt) need relative-vol or correlation estimates; time zones differ.
- A hedge ratio flipped sign or an optimiser produced extreme weights: diagnose the matrix first.
- Transform a covariance to another basis (spreads, flies, forwards) or aggregate desks.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap / govt yields by tenor | `curve_par` (`par_rate_pct`) | daily, same snap every day (`snap`), >= 2y; 3y default | change in bp = 100 x diff(par_rate_pct); constant-maturity or fitted yields, not bond-level yields, so ageing does not contaminate the history |
| Spreads (swap spread, ASW) | `swap_spreads` (`value_bp`) | daily | keep one `sign_convention` through the whole sample; diff of the bp value |
| Futures / STIR prices | `fut_quotes`, `stir_quotes` | daily settle, rolled series | use roll-adjusted changes, never the raw jump at the roll; STIR rate-index prices: bp change = 100 x diff(price) (see `data-quality-and-timeseries-hygiene`) |
| Normal vol | `vol_surface` (`nvol_bp`) | daily | covariance of vol changes in bp/yr; implied vs realised see `vol-correlation-and-curve-options` |
| Exposures to weight with | `positions` / DV01 vector | as of today | currency per bp, positive = long duration |

Rules for the panel: differences (bp) for rates and spreads; log or percent returns for prices (futures, indices);
**never levels**. If a series is missing or stale, ask the data adapter; do not forward-fill more than a day or two (see
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)).

## Method

### 1. Prepare the panel
1. Build changes at the frequency that matches the horizon you will hold or hedge over (daily for 1-5 day risk, weekly or
   non-overlapping 2-4 week for RV holding periods; JPM found monthly vol data gave the best carry-to-risk IRs, 0.87-0.97
   vs 0.51-0.83 daily/weekly, except cross-market trades where daily/weekly were as good or better) (J.P. Morgan, Investment Strategies No. 31, 11 Jan 2007).
2. Units: rates and spreads in bp; Q in bp2 per period. Annualise variance by 252/q (q = days per period); vol by sqrt(252) daily,
   sqrt(52) weekly, sqrt(12) monthly. Exposures in currency per bp, so `c = sqrt(S'QS)` is in currency (Darbyshire, Pricing and Trading
   Interest Rate Derivatives, 3rd ed., 2022).
3. **Why changes**: covariance of levels is dominated by the earliest changes and is invalid for pricing and hedging
   (Darbyshire, 2022); level regressions have serially correlated errors (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022). Levels and
   changes give the same eigenvectors only if the levels are stationary (Düring, Fixed Income Trading and Risk Management, 2021).
4. **Do not demean for risk** (divisor T, mean not subtracted): demeaning in trending markets biases variance severely down, and
   demeaning overlapping returns makes vol spuriously low (Golub, BlackRock's Guide to Fixed-Income Risk Management, 2023). Mean error also
   exceeds the mean itself at daily frequency (SE of mean 0.000685 vs true 0.000274 in the cited example), so zero is the better estimator
   (Hasbrouck, Empirical Market Microstructure, 2004). Demean only for a statistical (PCA / mean-reversion) model that needs the centred object.
5. **Covariance, not correlation, for hedges and PCA on curves**: you want hedges to adapt to the vol differences along the curve. Use
   correlation only when scales are artefacts (index levels, different units), or to avoid one high-vol block swamping another
   (Düring, 2021; Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024).
6. Winsorise nothing silently. Flag event days (central-bank, payrolls) and decide explicitly: event days carry real risk (a day with twice the
   normal vol adds 4x variance: weekly N(0, 16+16+16+16+4x16) = N(0,128), 95% bound 18.6bp; Darbyshire, 2022) and belong in a risk matrix,
   but can dominate a correlation or beta used for RV.

### 2. Pick the estimator by data richness
Let `N` = instruments, `T_eff` = effective observations (EWMA: `(1+l)/(1-l)`, see section 3; overlapped: `3TL/(2L^2+1)`).

| `T_eff / N` | Estimator | Why |
|---|---|---|
| >= 10 | EWMA or sample, no shrinkage | rule of thumb T ~ 10N (Palomar, Portfolio Optimization, 2025) |
| 3 - 10 | EWMA + PCA/factor structure (k = 3 for a curve) or Ledoit-Wolf | Murphy: an informative prior is "necessary" when D/N > 0.1 (Machine Learning: A Probabilistic Perspective, 2012) |
| 1 - 3 | factor/shrunk matrix only; no precision-matrix use | sample is near-singular |
| <= 1 | do not estimate; singular (rank <= T-1) | some positions look riskless (Grinold & Kahn, Active Portfolio Management, 2nd ed., 1999) |

Heuristics from the book: at least 100 observations per instrument, or at least as many observations as instruments; the sample period
should resemble the regime you expect (Darbyshire, 2022). N(N+1)/2 IID observations are needed for a non-singular matrix
(Lopez de Prado, Advances in Financial Machine Learning, 2018). A 19-tenor ladder estimated on under 190 observations is already D/N > 0.1.
These bands are the practitioner reading of those rules: apply them to `T_eff`, not to calendar length.

### 3. EWMA (default for a risk matrix)
`Sigma = sum_s w_s x_s x_s'`, `w_s = (1-l) l^s / (1 - l^T)` (newest s = 0), zero mean. Half-life `h = ln(0.5)/ln(l)`;
effective sample `t_eff = (1+l)/(1-l)` for `T >> h` (Golub, 2023).

| Half-life (days) | lambda | t_eff | Use |
|---|---|---|---|
| 11 | 0.94 | 32 | RiskMetrics daily default (0.94; 0.97 for monthly data) (Bourgoin, in Dunis et al., Applied Quantitative Methods for Trading and Investment, 2003) |
| 21 | 0.9675 | 61 | fast vol; RV research default, tuned over {10, 21, 42, 63} |
| 40 | 0.983 | 115 | best short-horizon forecaster on daily data (Golub, 2023); also gives a 99%-weight window of ~266d |
| 63-126 | 0.989-0.995 | 182-364 | stable; hedge ratios and risk limits (126d is "more stable but less responsive", Golub, 2023) |

A portfolio-construction backtest used a much slower 18-month half-life (about 380 trading days) with monthly rebalancing (Citi, Quantitative Framework for Regime Investing, 29 Oct 2021).
An 8-day half-life in a 252-day window is only about 23 effective points (Golub, 2023): a short half-life buys responsiveness with a
smaller sample, so shrink or factor-structure the matrix (section 4).
- **Choose lambda by out-of-sample QLIKE** (script `halflife-scan`), or by ML `max sum(-0.5 ln s2_t - 0.5 r_t^2/s2_t)` (Bourgoin, 2003). It is
  not a universal constant: vol-switching data wants about 5-20d, stable data wants 250d+ (the self-test checks both directions).
- Use **one lambda for every element** so the matrix stays positive definite (Bourgoin, 2003). Initialise at the sample variance.
- Prefer exponential weights to rolling windows: a rolling 3M/6M window produces an artificial drop (or jump) when a spike enters or leaves.
  In March 2009 realised 10Y JPY vol was 24bp or 45bp depending on the window (Huggins & Schaller, 2024; Huggins & Schaller, SOFR Futures and
  Options, 2022). "The choice of function and decay matters much less than the rolling-window artefacts."
- EWMA has no mean reversion: flat forecast term structure, too persistent after a shock and too low in calm periods. Beyond one step use
  GARCH with variance targeting, see [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md) and
  [references](references/advanced-methods.md).
- Sqrt-time scaling is valid only for zero-drift IGARCH / random walk. Do not scale a 1-day matrix to a month for a mean-reverting spread; estimate at the horizon.

### 4. Fast vols, slow correlations, regimes
- `Sigma = V Omega V`: vols with a short half-life (about 21d), correlations with a long one (about 126d) (Golub, 2023; Paleologo, The Elements
  of Quantitative Investing, 2025). Vols move fast, correlation structure slowly.
- **Cross-sectional gamma scaling**: `gamma = sum_i s_i(t-1) s_i^EWMA / sum_i (s_i^EWMA)^2`; multiply the EWMA vols by gamma when recent realised vols
  diverge from the EWMA forecast (Golub, 2023).
- Static EWMA lags a vol spike. For stress, estimate on stressed-regime windows or overweight historical periods like the scenario; matrix date and
  speed change scenario rankings (a "Fed Tapering" ruler read 2.5 vs 4.0 vs 3.4 for slow 5y-weekly, fast 1y-weekly and a Dec 2017 matrix; Golub, 2023).
  See [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md).
- Use-case matrix: optimisation needs an accurate precision matrix (shrink); risk limits want stability, because an over-responsive matrix forces selling
  into spikes; when understating risk is costly use a conservative bias (Golub, 2023).
- Correlation regimes are driven by the shock type: inflation or policy shocks give positive cross-market correlations, growth and financial shocks
  negative (Macrosynergy, Interest rate swap returns: empirical lessons, 2018 data). Stock-bond correlation is negative when core CPI < 2.5%,
  mostly positive above (Willer & Saunders, Trading Global Macro Markets, 2026). Condition on the regime via
  [quant-regime-detection](../quant-regime-detection/SKILL.md) instead of averaging across it.

### 5. Shrinkage and factor structure
- **Linear shrinkage** `S* = (1-d) S + d F`. Targets: scaled identity `(tr S/N) I` (Ledoit-Wolf), `diag(S)` (keeps vols, multiplies correlation by `1-d`),
  constant correlation. Ledoit-Wolf picks `d` in closed form; choose by CV or closed form, never on training error (Murphy, 2012). Script: `ledoit_wolf`.
  Trace is preserved. Gains in covariance MSE are modest, constraints (no-short, caps, l2) already act as shrinkage, and Σ+γI in the GMV solve is the
  same thing (Palomar, 2025).
- **Curves need a factor target.** An identity target shrinks correlations toward zero, which destroys the PC1 structure that makes curve
  hedges work (judgement; check by comparing the shrunk and EWMA PC1 shape).
  Use PCA with noise averaging: keep k top eigenpairs, set the trailing N-k eigenvalues to their mean `kappa`
  (`pca_factor_cov`). Always PD and trace-preserving (Palomar, 2025). Wrong k can be drastic: k=1 when the truth is 3 is far worse than the sample matrix, while the
  right k is only slightly better. Err toward more factors (Paleologo, 2025). For curves k = 3 explains more than 99% beyond 3y but only 74.5% of the
  1y point, so the front end needs more (Tuckman & Serrat, 2022).
- **Smoothing a correlation matrix** (Darbyshire, 2022): PCA on the CORRELATION matrix, keep k PCs, rescale the diagonal back to 1, then re-apply
  separately smoothed vols (`smooth_corr`). Effective and easy, not necessarily best. It removes information: similar instruments get higher-than-usual
  correlations, so it usually LOWERS VaR for books with large oscillating bucket risk. Use it for stable margins and day-to-day consistency, not for min-variance hedges.
- Eigenvalues above `1 + sqrt(N/T_eff)` (on whitened data) are signal, below it noise; sample eigenvalues are biased up. See [references](references/advanced-methods.md) section 4.
- Individual bonds age, so their historical covariance is "fairly meaningless": use constant-maturity or bucket series (Düring, 2021).
- Separate covariance blocks per risk type. One PCA across outright and basis is dominated by outright variance (3M PC1 s.d. 7.0 vs 3M/OIS 0.9)
  (Darbyshire, 2022).

### 6. Robust estimators and the Gerber statistic
- A single outlier can ruin a sample covariance; heavy-tailed MLE (Student-t, nu about 4-5), Tyler and the spatial median beat Gaussian MLE
  (Palomar, 2025); details in [references](references/advanced-methods.md). IRS monthly return excess kurtosis averages 2.6; PC scores 1.2 (PC1) up to 141 (higher PCs) (Macrosynergy; Musaelian, Nagarajan & Villani, PCA: invariant risk metrics, 2016).
- **Gerber statistic** (Gerber, Markowitz, Ernst & Miao, 2022, external): threshold `h_k = c * s_k`, `c = 0.5`. Per pair and day, +1 if both moves exceed
  `+h` or both below `-h` (concordant), -1 if one exceeds `+h` and the other is below `-h` (discordant), 0 if either sits inside its band.
  `G_ij = (U - D)/(U + D)`, with U = number of concordant days and D = number of discordant days. Gerber covariance = `s_i s_j G_ij`. Small noisy moves and magnitudes drop out.
  This is the variant implemented here (days where only one series breaches its band are ignored); check the denominator convention before comparing with published Gerber numbers.
  Script: `gerber_corr`, `gerber_cov`.
  - Known answers (self-tested): for bivariate normal data `c = 0` gives `G = (2/pi) arcsin(rho)`, so rho 0.6 reads 0.41; with `c = 0.5` rho 0.6 reads 0.75. `G` is
    not Pearson on the same scale: compare Gerber to Gerber, or map through the orthant-probability formula.
  - Not guaranteed PSD: clip negative eigenvalues (`nearest_psd`) and rescale the diagonal.
  - The std in the threshold is itself outlier-sensitive: with 1% gross (40-sigma) outliers the plain threshold collapsed G from 0.75 to 0.00 in the
    test; a MAD scale (`robust_scale`) restored 0.72. Pass robust vols when the sample has gross prints.
  - Use for: correlation of fat-tailed flows or event-polluted samples, a cross-check on a Pearson/EWMA correlation. If Gerber and Pearson disagree by more
    than the mapping explains, inspect outliers. Do NOT use for DV01 hedge ratios straight away: Gerber discards magnitude, so take vols from EWMA and
    compare the resulting beta with the EWMA beta before use. No published result in the sources tests it on rates hedges; treat as a diagnostic first.

### 7. Horizon, asynchronicity, overlap
- **Epps effect**: correlation is lower at higher sampling frequency, so a hedge calibrated on daily data is less effective over short horizons than
  over longer ones. No industry-standard frequency: match the hedge horizon. Short horizon: hedge idiosyncratic risk (same or near-identical
  instruments). Long horizon: hedge factor risk, especially level (QF Stack Exchange, "Calculating PCA hedge ratio for 3-leg spread", 11 Apr 2016).
- **Test for horizon dependence**: compute correlation on non-overlapping 1d, 1w, 2w, 1m, 3m changes (Huggins & Schaller, 2024). If it moves, use the
  matrix at the holding horizon; see [references](references/advanced-methods.md) section 1.
- **Time zones and stale prices** bias vol and correlation down. Daily betas understate cross-market correlation (AUD/NZD/JPY close before
  Europe/US); blend them with weekly estimates (Macrosynergy, 2018 data). Fixes: lower frequency; overlapping returns with overlap L (L = 5 gives weekly
  returns updated daily, `t_eff ~ 3TL/(2L^2+1)`: T=250, L=5 gives 73.5, about 50% more than 49 non-overlapping weekly points); or Newey-West
  `Sigma = Omega_0 + sum_l (1 - l/L)(Omega_l + Omega_l')` (Golub, 2023). Do not demean overlapped returns.
- **Spread / pair risk is the risk of the combined position**, not the sum of leg vols: JPM measured 12-month rolling std of the combined long-short monthly
  return, 100bp risk per trade. Constant 100bp risk beat carry-to-risk scaling (IR 0.94/1.10/1.00 for 1/2/3 trades vs 0.60/0.53/0.45)
  (J.P. Morgan, 2007).
- Cross-market relative sizing: relative SD = `SD(local)/SD(USD)` (EWMA half-life 11d); normalise each local leg by dividing its return (equivalently its
  notional) by relative SD so every leg carries USD-like risk. This cut the most-to-least volatile market SD ratio from 4.5 to 2.9, but the normalised
  returns had much fatter tails and kept their exposure to global risk (Macrosynergy, 2018 data). JPY about 0.3 of USD vol, CHF 0.5, EUR/GBP/SEK/NZD 0.6-0.7, AUD/CAD 0.8-0.9 (Macrosynergy, 2018 data).

### 8. Evaluate before use
1. **QLIKE** `mean(r^2/f - ln(r^2/f) - 1)` (f = forecast variance made with data to t-1) per instrument and for a few fixed portfolios, across candidate half-lives. QLIKE
   punishes under-forecasts harder. R2 is not a model-selection tool (Paleologo, 2025).
2. **Exceedance**: about 5% of outcomes beyond 2 sigma of forecast; 0.3% beyond 3 sigma for a normal. Kahn (1997): structural forecasts 3% beyond 2 sigma, trailing
   history 17% (Grinold & Kahn, 1999).
3. **Min-variance test**: build min-variance portfolios from each candidate Sigma; realised variance should be lowest for the best matrix.
4. Diagnostics to log: `T_eff/N`, condition number (above 1e3: do not invert), smallest eigenvalue (near zero: collinear, check eigenvectors), PC1-3 share,
   loading stability (sign-align; Procrustes if PC attribution must be stable).
5. Test the estimator on simulated data with a known answer before trusting it on real data (Grinold & Kahn, 1999) - the bundled self-test does this.

### 9. Use the matrix
- **VaR multiplier** `c = sqrt(S'QS)`; VaR 95% = 1.645c, VaR 99% = 2.326c; VaR 99% about equals ES 2.5% under normality (2.326 vs 2.338). Linear: ignores gamma
  and fat tails, so pair with stress tests (Darbyshire, 2022; Golub & Tilman, Risk Management: Approaches for Fixed Income Markets, 2000).
- **Min-variance hedge in buckets M**: `trade = -Q_MM^-1 Q_M. S` (solve, do not invert). Two-bucket: `S_f = -S_0 q12/q22`, `c_min = |S_0| sqrt(q11 - q12^2/q22)`.
  Script: `min_var_hedge`. Fly 2s5s10s wings with the body fixed at 2: `wings = -2 Sigma_ww^-1 Sigma_w5`.
- **Two-asset hedge**: `x_h = -rho (s_c/s_h) x_c`; residual variance `(1-rho^2) s_c^2 x_c^2`. An uncertain beta means hedge less (Paleologo, 2025). Regression betas: see
  [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md).
- **Basis change**: if `P2 = A P1` then `Q2 = A Q1 A'`. For `[5Y, 2s10s, 2s5s10s]` from `[2Y, 5Y, 10Y]`: `A = [[0,1,0],[-1,0,1],[-1,2,-1]]` (QF Stack Exchange,
  "How to adjust butterfly 2s5s10s swaps trade for directionality?", 2018). Transformed instruments are still correlated (5s6s7s vs 5s10s about 5%; QF Stack Exchange, "Can PCA be used to transform a ladder of interest rate risk?", Sep 2023): a large
  position in a weakly correlated instrument is material. Transform complex to simple, never the reverse; today's Jacobian on historical Q is an approximation (Darbyshire, 2022).
- **Forward vol from par vols and correlation**: with `L = A_1Y10Y / A_1Y5Y5Y`, `s_fwd = sqrt(((1-L) s_a)^2 + 2(1-L) L rho s_a s_b + (L s_b)^2)`, `s_a` the 1Y5Y and `s_b` the 1Y10Y par vol (Darbyshire, 2022).
  See [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md).
- Portfolio vol from key rates: `sigma_P = sqrt(sum_ij KR_i KR_j rho_ij s_i s_j)` (Tuckman & Serrat, 2022). Equal-weight basket of N with common correlation:
  `s_P = s sqrt((1 + (N-1) rho)/N)`; invert to back out average correlation (Grinold & Kahn, 1999).

## Worked examples
1. **Four-bucket VaR and hedge** (Darbyshire, 2022). `Q` (bp2) = [[8.7,7.4,5.1,2.2],[7.4,7.3,4.7,2.2],[5.1,4.7,4.9,1.8],[2.2,2.2,1.8,1.9]];
   S = (2Y -10,000; 5Y +2,500; 10Y +10,000; 30Y -4,000) per bp. `c` = 16,174, VaR 5% = 26,590. Best single 2Y trade +2,948 cuts `c` by 15.6%; best pair
   2Y/10Y (+8,562 / -9,476) cuts it just over 70%. The 9-day sample is statistically meaningless, so only the method transfers. Reproduced by the self-test
   within 1.5% using the rounded Q.
2. **Fly weights, three estimators** (QF Stack Exchange, 2018): covariance-based weights for 2Y/5Y/10Y (body 2): raw 50/50 -1/2/-1; PC1-divided -0.91/2/-1.35; PCA minimal
   change -1.10/2/-1.08; **min-variance -1.48/2.00/-0.38**. EUR swaps 2016 (in-sample Jan-Jun, 116 out-of-sample daily changes): out-of-sample std raw 0.8399, MVLSR 0.7609,
   PCA 0.8689, min-VaR 0.7628. The PCA-weighted fly was WORSE than raw out of sample; min-variance is lowest in-sample by construction.
3. **Forward vol sensitivity** (Darbyshire, 2022): 1Y5Y vol 39bp, 1Y10Y vol 59bp, L = 2.10. 1Y5Y5Y vol = 84bp at rho = 0.95, about 167bp at rho = -1, 81bp at rho = +1
   (recomputed from the formula): very sensitive to rho, and a plain average of par vols is wrong.
4. **EWMA lags a regime break** (Golub & Tilman, 2000): the 19-20 Aug 1998 swap-spread widening of 7bp was a 5.5 sd move. With EWMA vol estimated on 31 Jul 1998 (calm) the whole
   fall-1998 widening was a 7-10 sd event, against about 3 sd on 10-year history. A 10y window would have overstated risk through the calm years, so neither is right: use EWMA for
   limits and stress it with a stressed-regime matrix.
5. **Vol targeting failed** (Macrosynergy): 5y IRS receiver targeted at 10% annual SD using an 11d half-life EWMA, rebalanced monthly, raised excess kurtosis from 2.4 to 2.9 and made
   outliers larger. The estimator lags the shock; do not assume EWMA targeting tames tails.
6. **Correlations flip** (Aikin, STIR Futures, 2nd ed., 2012): daily-change correlations among Euribor, Eurodollar, short sterling and Euroswiss futures of 0.96-0.99 in Jan 2008-Sep 2011 fell
   to -0.82 to +0.34 in Jan-Sep 2011 when the ECB hiked and others did not. A single sample correlation is a regime statement.
7. **Average correlation backout** (Grinold & Kahn, 1999): 20 stocks average risk 27.8%, equal-weight portfolio risk 20.4% gives average correlation about 0.51-0.52.

More worked material (desk aggregation, basis vs delta proxy hedge, cash/IMM covariance, EUR forward-rate correlations) is in [references](references/advanced-methods.md).

## Signals & interpretation
- Rule of thumb outputs: `T_eff/N >= 10` accept; `3-10` shrink/factor; `< 3` do not use for optimisation or inversion.
- Condition number `> 1e3`, or smallest eigenvalue `< 1e-3` of the largest: inversion is error-prone; use a factor/shrunk matrix, `solve` not `inv`, or HRP for sleeves.
- PC1 explanatory power should exceed 95% before a one-factor curve risk is used (Golub, 2023); one-factor (PC1) risk misstates duration-neutral curve trades, use >= 2 PCs (Golub & Tilman, 2000).
  Curve complexity monitor: Herfindahl `H = sum(e_i^2)/(sum e_i)^2` of rolling-PCA eigenvalues (90 business days); high H = one hedge instrument suffices, a fall in H = more instruments needed (Düring, 2021).
- Hedge-ratio stability: if the hedge ratio from the 63d and 252d matrices differ by more than 30%, or the best single hedge reduces `c` by under about 15%, the book is
  curve/RV-dominated: hedge in a spread or fly representation, not outright (Darbyshire, 2022; the 30% trigger is a practical default).
- Hedge with a PC1 duration / covariance-based weight rather than OAD where curve moves are non-parallel; PC1-neutral beat OAD-neutral ahead of high-vol events (Golub & Tilman, 2000).
- A hedge whose own correlation with the portfolio is low is a red flag; exact key-rate matching is unstable and ignores t-costs (Golub & Tilman, 2000; Golub, 2023).
- Correlations used as a cross-market screen (60d rolling, DM 10y pairs) are state variables, not relationships: compare to the 1y level (the 60d screen is from Citi Research, Emerging Markets Strategy Weekly, 20 Aug 2026; the 1y comparison is judgement).
- Five-year IRS monthly return correlations (1999-2018): mostly 0.5-0.8; EUR-GBP, EUR-CHF, EUR-SEK, CAD-USD, AUD-NZD about 0.8; NOK-NZD, NOK-USD, NZD-USD about 0.5; JPY only 0.2-0.3 with everyone
  (Macrosynergy). Use as priors for shrinkage targets, not as live values.

## Pitfalls
- Using levels, demeaning risk covariances, or demeaning overlapped data (see Method 1).
- Rolling windows that jump when a spike exits: use exponential weights. A responsive matrix for limits forces selling into vol spikes; a stable matrix for stress understates.
- Short half-life + many instruments: `T_eff` collapses (8d = 23 points). Report `T_eff`, not calendar length.
- Stale, illiquid or non-synchronous series understate correlation and vol and attract allocation (Golub, 2023). Mixed `snap` times across markets are the usual cause in G10 work.
- Mixing different lambdas per element breaks positive definiteness. Gerber and some smoothed matrices are not PSD: repair before inverting.
- Min-variance weights are in-sample optimal by construction: re-test out of sample and with t-costs. In the EUR 2016 test min-variance and regression flies cut std about 9% vs raw,
  while the PCA-divided fly was worse than raw (Worked example 2). Minimum variance is the SMALLEST eigenvalue direction, not the largest (QF Stack Exchange, PCA step-by-step, 2014).
- When one leg is pinned (e.g. a front end anchored before hikes), no covariance weighting neutralises level and slope: the fly behaves like a curve trade (QF Stack Exchange, 2018).
- Maximally mean-reverting covariance-derived baskets may vary only inside the bid/offer: check the out-of-sample range in bp against costs (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008).
- A 9-day or 30-day covariance is not significant; minor PCs change with the sample and instrument set; do not trade PCA residuals off it (Darbyshire, 2022).
- "Ephemeral correlation between factors is the main pitfall of PCA" (Huggins & Schaller, 2024). PC shapes change with regime (pre-GFC hump vs ZLB; Jan vs Mar 2020).
- Normal VaR understates fat tails; PC-score tails are fat and calm periods shrink PC vols, giving false comfort in delta-gamma risk (Musaelian et al., 2016). Pair with stress tests.
- Do not let return views rewrite correlations: a forecast of divergence barely changes risk (sigma_post = sigma_prior sqrt(1 - IC^2); IC 0.25 moves 18% to 17.43%) (Grinold & Kahn, 1999). Keep the risk model independent of alpha.
- Mean-variance with an inverted sample covariance is unstable; even 1/N beats it out of sample (DeMiguel et al. 2009, quoted by Lopez de Prado, 2018). Prefer HRP or shrinkage for many correlated sleeves.
  The bottleneck is the mean, not Sigma (Palomar, 2025).
- Near-collinear inputs may not show up pairwise; inspect eigenvalues of the covariance.
- Rolling regression/beta "measures an effect that may have long disappeared" (Bentz, in Dunis et al., 2003): re-estimate when the regressor variance regime shifts (the OLS slope Cov/Var changes with the distribution of X even if the relationship does not; Shalizi, 2025).
- Swap-spread betas and hedge ratios are unstable (on-the-run specialness, supply hedging): use short windows plus judgement (Golub & Tilman, 2000).
- Many-leg hedge baskets overfit: a ridge penalty (lambda added to the diagonal, chosen by CV) cut a stock hedge's residual variance 67% vs 53% for OLS in the cited test, but some single-name hedges still lost out of sample (Burgess, in Dunis et al., 2003).
- Normal (bp) vol for rates, not lognormal, which breaks near zero and across levels (Huggins & Schaller, 2024).

## Output
Return, for each matrix produced:
1. A header table: instruments (ordered by tenor), sample window, frequency, unit (bp / bp2 per day), method and parameters (half-life, k, delta, c), `T_eff`, `N`, `T_eff/N`, condition number, smallest eigenvalue, PC1-3 share.
2. Annualised vol table (bp/yr, `sqrt(252)` x daily bp s.d.) with the previous-window values, and the correlation matrix (lower triangle) with a flag on pairs whose correlation moved more than 0.15 vs a slower window.
3. If used for sizing: the exposure vector, `c`, VaR 95/99, and the min-variance hedge trade with `c` before/after, and the stability check (63d vs 252d).
4. The diagnostic result (QLIKE by half-life, exceedance count) and any recommendation to shrink, change half-life or use a stressed window.
Hand the matrix and the stated horizon to [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md), [curve-butterflies](../curve-butterflies/SKILL.md),
[port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md) or [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md). State the covariance assumptions in the trade note.

## Scripts
- [`scripts/covariance.py`](scripts/covariance.py): `ewma_cov`, `ewma_weights`, `effective_obs`, `overlap_eff_obs`, `fast_vol_slow_corr`, `sample_cov`, `ledoit_wolf`, `shrink_to_diag`,
  `pca_factor_cov`, `smooth_corr`, `gerber_corr`, `gerber_cov`, `robust_scale`, `nearest_psd`, `var_multiplier`, `min_var_hedge`, `qlike`, `halflife_scan`.
  CLI: `python scripts/covariance.py cov <file> --method ewma|lw|gerber|pca|fastslow|sample`, `halflife-scan <file>`, `hedge <file> --risk 2Y=-10000 10Y=10000 --hedges 5Y 30Y`. The file is a wide table of changes or a long
  `curve_par` table (converted to bp changes). `--selftest` checks EWMA identities, Ledoit-Wolf vs scikit-learn, Gerber vs the orthant-probability formula, PCA shrinkage on a simulated 2-factor world,
  min-variance hedges against closed forms and the published book, and QLIKE half-life scans.

## Related skills
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA on this matrix, loadings, neutral hedges
- [curve-butterflies](../curve-butterflies/SKILL.md): covariance-weighted fly weights
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): betas and dynamic hedge ratios built on these moments
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): GARCH, HAC, structural breaks
- [quant-regime-detection](../quant-regime-detection/SKILL.md): regime-conditioned correlation
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinkage as a prior
- [quant-cointegration](../quant-cointegration/SKILL.md): when common stochastic trends make covariance of levels meaningless
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): robust scale and z-scores
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): exposure vectors and Jacobians
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): optimisation, HRP, risk parity on the matrix
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): vol targeting and DV01 budgets
- [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md): stressed-regime matrices
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): implied vs realised correlation
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): beta-weighted vs DV01-neutral curve trades
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-market legs, relative vol, time-zone effects
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale data, roll stitching, outliers
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): out-of-sample tests of hedges and matrices
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag and transmission between markets.
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC, alpha decay and signal blending.

## References
- Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): no-demean covariance, EWMA half-life rules, effective observations, gamma scaling, fast-vol/slow-correlation, asynchronicity, Newey-West, factor covariance.
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): changes not levels, VaR multiplier, min-variance hedges, PCA correlation smoothing, Jacobian transforms, forward vol, worked 4-bucket book.
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): EWMA = GARCH, QLIKE and risk-model tests, spiked eigenvalue shrinkage, factor count, two-stage PCA.
- Palomar - Portfolio Optimization: Theory and Application (Cambridge UP, 2025): T ~ 10N, Student-t / Tyler estimators, shrinkage targets, PCA covariance estimator, constraints as shrinkage.
- Grinold & Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): sample-covariance rank limits, structural factor models, risk-model validation, return views vs risk.
- Düring - Fixed Income Trading and Risk Management (Wiley, 2021): covariance vs correlation, changes vs levels, window trade-off, factor-model dimension reduction, rolling-PCA Herfindahl.
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): exponential weights vs rolling windows, horizon-dependent correlation (MVOU), normal vol, PCA instability.
- Huggins & Schaller - SOFR Futures and Options (Wiley, 2022): rolling-window jump artefact; use exponential decay.
- Tuckman & Serrat - Fixed Income Securities (4th ed., Wiley, 2022): key-rate portfolio vol, front-end PCA explained variance, regime-dependent PCs.
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): condition number, HRP, N(N+1)/2 rule, time-decay weights.
- Dunis, Laws & Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003), Ch. 10 Bourgoin: EWMA defaults, optimal decay, GARCH/GJR, variance targeting, multivariate GARCH, positive definiteness; Ch. 2 Burgess: ridge hedge baskets; Ch. 6 Roche-Rockinger: Markov-switching vol; Ch. 7 Bentz: rolling-beta caveat.
- Macrosynergy - Interest rate swap returns: empirical lessons (research article, data through Feb 2018): EWMA vol targeting result, relative SD normalisation, DM correlation matrix, time-zone caveat.
- J.P. Morgan - Investment Strategies No. 31: Exploiting carry with cross-market and curve bond trades (Panigirtzoglou, 11 Jan 2007): spread risk from the combined position, vol-data frequency test.
- Golub & Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000): EWMA vs long-history crisis sigmas, PC1 vs OAD, instability of key-rate matching.
- Musaelian, Nagarajan & Villani - PCA: invariant risk metrics and representation of residuals for bond returns (SSRN, 2016): PC covariance via SVD, fat-tailed PC scores.
- d'Aspremont - Identifying Small Mean Reverting Portfolios (arXiv, 2008): sparse inverse covariance, cluster-then-search, costs vs small baskets.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): cross-market STIR correlation instability.
- Quantitative Finance Stack Exchange - "How to adjust butterfly 2s5s10s swaps trade for directionality?" (Jun 2018, edited Oct 2021): covariance basis transform, min-variance fly weights, EUR 2016 out-of-sample test.
- Quantitative Finance Stack Exchange - "Calculating PCA hedge ratio for 3-leg spread" (Apr 2016): changes not levels, sampling frequency, Epps effect.
- Quantitative Finance Stack Exchange - "Can PCA be used to transform a ladder of interest rate risk?" (Sep 2023): correlation between Jacobian-transformed instruments, VaR minimisation for compression.
- Quantitative Finance Stack Exchange - "Step-by-Step PCA algorithm (checking correctness without math packages)" (2014): minimum variance is the smallest eigenvalue.
- Shalizi - The Truth about Linear Regression (draft lecture notes, 20 Oct 2025): slope Cov/Var depends on the regressor distribution; ridge; eigenvalue collinearity diagnostic.
- Citi Research - Emerging Markets Strategy Weekly: Can back-end USTs derail EM risk? (Costa et al., 20 Aug 2026): 60-day rolling DM 10y correlation screen.
- Murphy - Machine Learning: A Probabilistic Perspective (MIT Press, 2012): shrinkage covariance, D/N > 0.1 rule, cross-validated lambda.
- Tsay - Analysis of Financial Time Series (3rd ed., Wiley, 2010): RiskMetrics IGARCH, EWMA covariance recursion.
- Hasbrouck - Empirical Market Microstructure (NYU Stern teaching notes, 2004): zero-mean second moments, bid-ask bounce, overnight hygiene.
- Ait-Sahalia & Xiu - Principal Component Analysis of High-Frequency Data (Journal of the American Statistical Association, 2019): realised PCA, jump truncation, integrated vs spot.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): stock-bond correlation regime vs core CPI.
- Citi Research - Quantitative Framework for Regime Investing (Saunders & Willer, 29 Oct 2021): 18-month exponentially weighted risk covariance in a monthly-rebalanced backtest.
- Gerber, Markowitz, Ernst & Miao - The Gerber Statistic: A Robust Co-Movement Measure for Portfolio Optimization (Journal of Portfolio Management, 2022) (external): definition and use of the Gerber statistic.
- Ledoit & Wolf - A well-conditioned estimator for large-dimensional covariance matrices (Journal of Multivariate Analysis, 2004) (external): closed-form shrinkage to a scaled identity.
- Patton - Volatility forecast comparison using imperfect volatility proxies (Journal of Econometrics, 2011) (external): QLIKE and MSE as robust loss functions.
