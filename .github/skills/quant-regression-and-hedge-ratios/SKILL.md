---
name: quant-regression-and-hedge-ratios
description: "Estimate and validate hedge ratios and regression fair values for G10 rates RV: OLS/minimum-variance beta on yield changes with HAC errors, total least squares / Deming (errors-in-variables), vol-ratio and reverse-regression hedges, rolling and EWMA betas, Kalman-filter dynamic betas, ridge/robust fits, multi-leg regression weights for flies, bond and futures yield-beta hedges, out-of-sample tests and residual diagnostics (Ljung-Box, collinearity, leverage). Use when asked for a hedge ratio, a yield-beta or minimum-variance hedge, a beta-weighted or regression-weighted spread or fly, how many futures or swaps hedge a bond, whether DV01-neutral is right, rolling or dynamic beta, Kalman filter hedge, OLS vs TLS or PCA, reverse regression, R-squared, residual z-score, beta stability, window or half-life choice, or why a hedge leaked."
---

# Regression and hedge ratios

A hedge ratio is an estimate, not a definition. DV01-neutral is the special case beta = 1; every other ratio (minimum
variance, zero expected P&L, PCA-neutral, model-based) answers a different question and differs from it only because
legs are imperfectly correlated and have different vols. This skill picks the objective, estimates the ratio with the
right estimator and window, attaches an uncertainty, tests it out of sample, and says how to read the regression
residual. Hedge ratios come from **changes**. Levels regressions are for fair value only, and only with cointegration
support ([quant-cointegration](../quant-cointegration/SKILL.md)).

## When to use
- "How much of X do I sell against Y?", "is a DV01-neutral spread/fly really neutral?", "regression-weighted fly".
- Hedging a bond, swap, option strip or whole book with futures or swaps (yield beta, CTD, tailing).
- Choosing OLS vs TLS/Deming vs vol-ratio vs PCA, or a rolling window, EWMA half-life or Kalman setting.
- A hedge leaked: beta unstable, R-squared low, residual autocorrelated, regime changed.
- Reading a regression residual as rich/cheap (fair value) and deciding whether it is tradeable.
- Not here: PCA factor construction ([curve-pca-factor-model](../curve-pca-factor-model/SKILL.md)), fly and
  spread product mechanics ([curve-butterflies](../curve-butterflies/SKILL.md),
  [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md)), cointegration tests
  ([quant-cointegration](../quant-cointegration/SKILL.md)), macro fair-value specifications
  ([macro-fair-value-models](../macro-fair-value-models/SKILL.md)).

## Inputs (data-agnostic)
Tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap/OIS or constant-maturity govt yields by tenor | `curve_par` (`par_rate_pct`) | daily, one `snap`, one `start`, >= 250 changes (>= 100 absolute minimum) | convert pct to bp (x100). Never mix snaps |
| Bond yields or prices | `bond_quotes`, with DV01 from [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md) | daily | use fitted or constant-maturity yields across benchmark rolls |
| Futures prices, CTD, conversion factor | `fut_quotes`, `fut_static`, `fut_basket` | daily settle | same snap as the cash leg; price regressions need carry-adjusted prices |
| STIR futures / spreads | `stir_quotes` | daily settle | price = 100 - rate, so a price change is minus a rate change |
| Vol, spreads, basis | `vol_surface` (`nvol_bp`), `swap_spreads`, `basis_swaps` | daily | regress vol-point changes (abp) or spread changes (bp) |
| Drivers for fair-value regressions | `macro_series`, `positioning` | as released | point-in-time vintages only |

If an input is missing, ask for it or hand off to the data adapter. Never invent values.

## Method

### 1. Choose the objective first (they give different ratios)
Notation: y = target change (the leg whose size is fixed), x = hedge change, sd = standard deviation of changes,
rho = correlation. Hedge DV01 per unit target DV01 is the "risk weight" h; h = 1 is DV01-neutral.

| Objective | h | Reading | Source |
|---|---|---|---|
| DV01-neutral | 1 | zero net DV01; the quoted spread; assumes parallel shifts | all |
| Minimum variance = OLS (y on x) | rho sd_y / sd_x | lowest hedged variance; net directional if rho < 1 | (Tuckman and Serrat, Fixed Income Securities 4th ed, 2022) |
| Vol ratio ("yield beta") | sd_y / sd_x | scales for vol only, over-hedges when rho < 1 | (Burghardt et al, The Treasury Bond Basis 3rd ed, 2005) |
| Zero expected P&L ("yield delta") | sd_y / (rho sd_x) = 1 / slope of x on y | no expected P&L for a move in x; largest hedge | same |
| TLS / Deming | between OLS and the reverse hedge | symmetric in the two legs | (Duering, Fixed Income Trading and Risk Management, 2021) |
| Factor-neutral | PCA / multi-regressor weights | zero exposure to chosen PCs | [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md) |

For rho > 0: OLS <= TLS <= reverse. Default for sizing a hedge of a fixed position: **OLS with the fixed leg as y**.
Default for building a spread whose two legs are both free: DV01-neutral, or vol-ratio / TLS when the spread must be
neutral to the common factor. State which objective the number serves.

### 2. Build the sample
1. **Changes, not levels.** Daily changes in bp (or price changes for instruments without a yield). Two random walks
   give a high R-squared in levels; a levels beta can even have the opposite sign to the co-movement of changes.
   Spot yields vs term repo: levels R-squared up to 0.78, weekly-change R-squared at most 0.025 (Burghardt et al,
   The Treasury Bond Basis 3rd ed, 2005).
2. **Horizon = holding period, non-overlapping.** Daily for tactical hedges, weekly for multi-week holds. Betas differ
   by horizon (a daily beta of a basis on OIS was significant, a weekly one was not: JPM, Markets struggle to feed the
   convexity beast, 28 Feb 2020). Overlapping changes need HAC and still overstate precision.
3. **Same snap, clean series.** A 1-minute bar near the close vs an exchange settle, or a one-day misalignment, adds
   noise that attenuates the beta. Roll-stitch futures and use constant-maturity or fitted yields across benchmark
   rolls (a benchmark switch created a fake 2s5s steepening: Duering 2021).
   See [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md).
4. **Regime window.** Use the regime you will hold in. Exclude ZLB/ZIRP periods from vol-rate and
   curve-rate regressions (Citi, Rates Vol Lab, 17 Jan 2020), shorten 3y to 1y in fast markets (ING, Rates Strategy,
   4 Feb and 3 Mar 2020), and use a dummy plus interaction for a known break instead of one pooled fit.
5. Winsorise changes at 1%/99% only if you can name the data errors; otherwise use Huber (step 3).

### 3. Pick the estimator
| Situation | Estimator | Default and reason |
|---|---|---|
| Hedge a fixed position with one instrument | OLS of y on x, intercept included | minimum variance. Hedge DV01 = beta x target DV01; hedged vol = target DV01 x resid sd (Tuckman and Serrat 2022) |
| Spread of two free legs, both marks noisy | TLS / Deming of y on x | OLS shrinks beta toward 0 by var(x*)/(var(x*)+var(noise)); Deming slope below |
| Fly or several hedge legs | multivariate OLS, hedges x1..xk | weights = betas; collinear legs: check conditioning (step 5) |
| Heavy tails, event days | Huber or t-error regression, or WLS | down-weights outliers (Gelman et al, Bayesian Data Analysis 3rd ed, 2014) |
| Many collinear instruments | ridge, lambda by time-series CV | plain OLS blew gross notional to 404% of net vs 166% with mild ridge (Dunis et al, Applied Quantitative Methods, 2003) |
| Time-varying relationship | EWMA, rolling or Kalman (step 4) | |

**OLS.** beta = cov(x,y)/var(x) = rho sd_y/sd_x; alpha = mean(y) - beta mean(x). Hedged P&L per unit target is
y - beta x; keep alpha out of the hedge (it is carry/drift, not a hedge leg). Standard error of beta is roughly
sd_resid / (sd_x sqrt(n)); report the **Newey-West** SE with lag = int(4 (n/100)^(2/9)) (3 at n=60, 4 at n=250,
6 at n=1000) and the 95% CI beta +/- 1.96 se_hac (Newey and West, Econometrica, 1987 (external)).

**TLS / Deming.** With second moments sxx, syy, sxy (demeaned changes) and delta = var(noise in y) / var(noise in x):

    beta_D = ( syy - delta*sxx + sqrt( (syy - delta*sxx)^2 + 4*delta*sxy^2 ) ) / (2*sxy)

delta = 1 is orthogonal regression (first eigenvector of the 2x2 covariance, slope (lambda+ - sxx)/sxy: Duering 2021);
delta -> infinity gives OLS; delta = syy/sxx gives the vol-ratio hedge sign(rho) sd_y/sd_x (Deming, Statistical
Adjustment of Data, 1943 (external)). **delta = 1 is only meaningful when both legs are in the same units with
comparable noise.** Estimate delta from mark noise: with iid mark noise a daily change has lag-1 autocovariance
-var(noise), so delta = cov1(dy)/cov1(dx) (script `mark_noise_delta`; fall back to 1 if both legs are alike liquid
benchmarks). Use covariance, not correlation, so that vol differences along the curve are retained.

**Reverse-regression asymmetry.** Regressing x on y does not give 1/beta unless |rho| = 1. Neither is wrong: the
fixed-size leg sets the risk, so make it the dependent variable (Tuckman and Serrat 2022). Compare risk weights
(84.2% vs 108.6% in the example below), never dollar amounts from different dependents.

### 4. Time-varying betas
| Method | Formula | Default | Use |
|---|---|---|---|
| Rolling OLS | cov/var over window w | w = 63 days (3m), 52 weeks for cross-market weekly screens | monitoring; lags regime changes, "ghost" jumps when a spike leaves the window |
| EWMA beta | sum(w_t y x) / sum(w_t x x), w = lambda^age, lambda = 0.5^(1/halflife) | half-life 60 days (weight halves every ~3m, no cliff; effective sample about 170 days, so it adapts more slowly than a 63-day window) | default live hedge; lag with `shift(1)` |
| Kalman random-walk beta | state (a,b), F = I, R = s2, Q = q s2 diag(1, 1/var x), diffuse P0 | q = 1e-4 for daily bp changes (**this skill's default**, not a published number), tuned by prediction-error likelihood on a burn-in then frozen | when regime changes are frequent and you want an uncertainty band |

Kalman recursions per date t (Hamilton, Time Series Analysis, 1994; Dunis et al 2003): predict P = P + Q; innovation
e = y - h'th with h = (1, x_t); f = h'Ph + R; gain K = P h / f; th = th + K e; P = P - K h' P. Log-likelihood
-0.5 sum (ln 2 pi f + e^2/f). Facts to keep: with Q = 0 and a diffuse prior it is recursive OLS and its final estimate
equals batch OLS; q is the knob (Dunis et al: Q/R = 1 adapts fast but is noisy, 0.1 smoother, 0.02 misses a jump;
Palomar used alpha = 1e-5 and 1e-6 for price-level pair spreads, Portfolio Optimization, 2025); an over-adaptive
beta shrinks the spread variance until profit falls below costs. **Use only filtered estimates in signals and
backtests, never smoothed ones** (smoothing uses future data), and use `beta_pred` (known before the date) for P&L.

EWMA is the steady-state of a local-level filter, so its half-life is the Kalman noise ratio in disguise
(Paleologo, The Elements of Quantitative Investing, 2025). Blend frequencies when time zones do not overlap: daily
betas understate cross-market correlation, so average a weekly (26-week half-life) and a daily (63-day half-life)
estimate, parameters set a priori (Macrosynergy, Interest rate swap returns: empirical lessons, 2018 data).

**Asymmetric (conditional) betas.** Where the relationship depends on direction, estimate rally-only and selloff-only
betas separately (3m rolling, 10y vs 2y: JPM, The return of convexity hedging, 31 Jan 2020; 3m JPY OIS downside beta to
equities, about 2bp rally per 5% sell-off: Citi, Macro tapas, 7 Aug 2026) and size the hedge on the state you fear.

**Stability test.** Re-estimate monthly. If the 1y rolling beta moves by more than 30% of its level, or its
rolling-63d s.d. z-scored over 126d exceeds 3 (the red light in
[curve-butterflies](../curve-butterflies/SKILL.md)), the structure is not a stable hedge: use EWMA/Kalman, shrink to
DV01-neutral, or re-weight on a trigger. Re-weighting example: a 15y5y vs 20y10y flattener turned directional, so the
20y10y leg was scaled by the empirical beta 1.025 (81.97mn to 84mn) and delta-hedged every 20bp (Citi, Alert:
Reweighting delta-hedged 15y5y/20y10y flatteners, 16 Oct 2019).

### 5. Uncertainty, conditioning and shrinkage
1. **Test beta = 1.** If the HAC CI excludes 1, DV01-neutral is statistically wrong (corporate vs Treasury: CI
   0.740 to 0.944). Statistical rejection is not economic: size the P&L difference before changing the trade.
2. **Bootstrap** (script `boot_beta`, moving blocks of 5 to 10 rows) for the CI when residuals are heteroskedastic
   or serially dependent; case resampling does not need the linear model to be true (Shalizi, The Truth about Linear
   Regression, 2025).
3. **Collinearity** (flies on wings, many hedge legs): compute pairwise |corr| and the condition number of the
   column-scaled design. |corr| > 0.9 or condition number > 20 means individual betas are unstable (Greene,
   Econometric Analysis 8th ed, 2018). Remedies: drop one of a correlated pair, regress on slope+level combinations
   instead of raw tenors, ridge, or a PCA basis. VIF > 10 is folklore; the eigenvalues are the real test.
4. **Uncertain beta means hedge less.** A full hedge with noisy betas can raise risk; shrink toward the DV01-neutral
   or PCA-implied value, for example hedge ratio = w beta_hat + (1 - w) 1 with w = tau^2/(tau^2 + se^2) and tau the
   prior spread of true betas (pseudo-observation form in Gelman et al 2014;
   [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md)).
5. **Multi-leg weights for a fly** (y2, y5, y10; fly = 2 y5 - y2 - y10, positive = belly cheap). Regress
   fly = b1 (y10 - y2) + b2 y5 + e. Then the combination with yield weights (-(1 - b1), 2 - b2, -(1 + b1)) equals e:
   uncorrelated with slope and level by construction (Quantitative Finance Stack Exchange, How to adjust butterfly
   2s5s10s swaps trade for directionality?, Jun 2018). Trade it as receive the 5y belly, pay the wings. Rescale so the
   belly is 2 (the weights are DV01 weights, positive on the belly). See [curve-butterflies](../curve-butterflies/SKILL.md) for the PCA, min-variance and 50/50 menu.

### 6. From beta to a trade
- **Notional.** Hedge notional = -N_target x (DV01_target / DV01_hedge) x beta (DV01 per unit notional, minus sign =
  opposite side). Hedge DV01 magnitude = beta x target DV01; risk weight = beta. Use DV01 (dollar duration), never the
  ratio of durations: two bonds of similar duration needed a 0.79 ratio, not 1 (Salomon Brothers, Understanding Duration
  and Volatility, Sep 1985). Hedged vol per day = target DV01 x resid sd (bp/day). A risk weight need not be 100% and
  weights in a two-leg fly need not sum to 100% (113.4% in the 10s20s30s example) unless shifts are parallel.
- **Edge vs residual vol.** Expect residual vol sd_resid x DV01 per day. Earning 5bp over a day against 2bp/day
  residual vol is reasonable; 1.5bp over a week against the same vol ruins the trade (Tuckman and Serrat 2022).
- **Bond futures.** Futures DV01 = CTD DV01 / CF. Yield-beta hedge N = DV01_bond x beta_bond / (DV01_fut x beta_CTD),
  with both betas against one reference yield (Burghardt et al 2005). The rule-of-thumb DV01 jumps at CTD crossovers;
  re-size on a CTD switch (Buxl CF-adjusted DV01 +37%, OAT/BTP about 7-8%: JPM, Eurex CTDs wobble with higher yields,
  2 Oct 2026). Hedge repo separately: term repo and spot yields are almost uncorrelated week to week.
  See [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md) and
  [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md).
- **STIR cash hedges.** BPV ratio x regression beta x tailing factor 1/(1 + i (D_h/2 + D_b)/B), with i the short rate, D_h the hedge-period days, D_b the borrowing days,
  B the day-count basis (Aikin, STIR Futures, 2012); worked in example F.
- **Delta-rebalance band** for a beta-weighted package: 15 to 30bp, 20 to 25bp balances accuracy against cost (Citi,
  Rates Vol Lab, 17 Jan 2020).

### 7. Validate out of sample and read the residual
1. **Split.** Calibrate on one window, test on the next of equal length (122 + 122 days in a GBP 2s10s hedge). Compare
   OOS residual sd with in-sample: OOS > 1.3x in-sample = unstable coefficients (this skill's threshold). Tuckman's
   10s20s30s fit had OOS 0.70bp vs 1.15bp in-sample, "not always so fortunate". `oos_table` ranks unhedged, DV01,
   OLS, TLS, vol-ratio, EWMA and Kalman on the same split.
2. **Diagnostics on the residual:** Ljung-Box (10 lags) p < 0.05 means autocorrelation (omitted factor, drifting beta);
   plot residual vs time, vs fitted, and lag-1; use Ljung-Box, not Durbin-Watson (Tsay, Analysis of Financial Time
   Series 3rd ed, 2010). Residuals that grow with the observed move: missing variable or drifting beta. A residual
   hedge that is still directional: regress it on level and slope again.
3. **Levels regression for fair value (rich/cheap).** Allowed only with a mean-reverting force: first test the residual
   for stationarity and half-life (`half_life`; [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md)).
   Signal = residual in bp and z = residual / residual s.d. (negative = rich), with a regression plane or its
   prediction interval, not the narrower mean CI (Shalizi 2025). Exit when the residual is within one standard error of
   the model (JPM, IRD Strategy Update, 5 Nov 2025). A residual is a dislocation flag, not a timing signal.
4. **Low-R-squared fits** are direction-and-scale guides only. R-squared is not goodness of fit and is the same in
   both regression directions (Shalizi 2025). Keep them in a screen but flag them.

## Worked examples

**A. Regression vs DV01 hedge, corporate vs Treasury (Tuckman and Serrat, Fixed Income Securities 4th ed, 2022, Ch.6).**
Long $100mm JNJ 2.450s of 9/2060 (DV01 0.2124 per 100) against UST 1.625s of 11/2050 (DV01 0.1910). Daily changes,
29 Jan to 14 May 2021, 82 obs: beta = 0.842 (se 0.051, CI 0.740 to 0.944), alpha 0.060 (se 0.223), R-squared 77.5%,
resid sd 2.00bp/day. DV01-neutral: sell 100 x 0.2124/0.1910 = $111.2mm. Regression: sell $111.2mm x 0.842 = $93.6mm
(risk weight 84.2%). Hedged vol = $212,400 per bp x 2bp = $424,800/day. Check: UST -18.2bp predicts JNJ -15.3bp; actual
-11.1bp, residual +4.2bp. OOS (17 May to 19 Jul 2021) resid sd 1.5bp.

**B. Reverse regression of the same pair.** Regress UST on JNJ: beta 0.921, resid sd 2.09bp. Against the same $93.6mm
Treasuries the hedge is 93.6 x (0.1910/0.2124) x 0.921 = **$77.5mm** JNJ (the source prints $82.8mm, which does not
follow from its own formula; $77.5mm is consistent with the stated 108.6% risk weight and the scaled $106.37mm /
$88mm hedge). Risk weight 1/0.921 = 108.6% vs 84.2%. Vol $93.6mm x 0.1910/100 x 2.09 = $374k vs $425k. A scaled hedge
($106.37mm UST vs $88mm JNJ) has the same $425k vol: different trades, not a different truth. Fixed leg = dependent.

**C. Four hedges of a $100mm on-the-run 30y with the 5y (Burghardt et al, The Treasury Bond Basis 3rd ed, 2005, 1/12/98).**
Weekly yield changes 1990 to 1997: annualised sd 30y 81.7bp, 5y 101.9bp, rho 0.88; 30y DV01 $149,070 per bp per $100mm.
Short 5y ($mm); daily sd and DV01s in $ thousands (daily sd = annualised sd / sqrt(250) x DV01):

| Hedge | Short 5y $mm | Daily sd | Net DV01 | Net expected DV01 |
|---|---|---|---|---|
| Unhedged | 0 | 770.3 | 149.1 | 149.1 |
| Minimum variance (x rho x sd ratio) | 240.7 | 365.9 | 43.9 | 33.6 |
| Yield beta (x sd ratio) | 273.6 | 377.4 | 29.5 | 17.9 |
| Yield delta (/ rho) | 310.9 | 415.8 | 13.2 | 0 |
| Conventional DV01-neutral | 341.2 | 462.5 | 0 | -14.6 |

Minimum variance has the lowest sd but is the most net long. The script reproduces the first four ratios from
341.2 x 81.7/101.9 x (0.88, 1, 1/0.88). Futures: CTD 11-1/4% 2/15/15 (DV01 152.81, CF 1.2968, beta 1.128): futures
DV01 = 117.84; rule of thumb 149,070/117.84 = 1,265 contracts (about 12.8% too many); yield-beta hedge
149,070/(1.128 x 117.84) = 1,121. Betas fall with duration, about 1.31 at modified duration 2 to 1.00 at 12.5 (1990s
fit; re-estimate, and note that by year the 10y beta ranged 2.88 in 1991 to 0.46 in 1993).

**D. Fly weights, four methods, EUR 2016 (QFSE, How to adjust butterfly 2s5s10s swaps trade for directionality?, Jun 2018).**
Fit 1 Jan to 30 Jun 2016, test 1 Jul to 22 Dec 2016 (116 obs), belly = 2. Weights on (2y, 5y, 10y): PCA-ratio
(-2.215, 2, -0.648), min-VaR (-1.650, 2, -0.794), multivariate regression (-1.960, 2, -0.756). OOS sd of daily changes
(x100): raw 50/50 0.840, regression 0.761, min-VaR 0.763, PCA-ratio 0.869 (worse than unhedged). Moral: validate OOS;
no method dominates in-sample.

**E. Dynamic beta where static fails (Dunis et al, Applied Quantitative Methods for Trading and Investment, 2003).**
True beta rises linearly from -0.49 to 0.50 over 100 days. Full-sample OLS gives -0.04 (R-squared 2%), last-50 OLS
0.23, rolling OLS OOS R-squared 39.2%; the truth at t = 100 is 0.5, which is the case a Kalman/EWMA beta is built for. In a
pairs study with a 2y rolling OLS, gamma wandered 0.6 to 1.2 vs 0.55 to 0.65 for the Kalman filter (Palomar,
Portfolio Optimization, 2025; equity ETFs, shown only for the mechanics).

**F. STIR cash hedge with beta and tailing (Aikin, STIR Futures: Trading Euribor and Eurodollar Futures, 2012).**
EUR25m for 62 days: 25m x 0.01% x 62/360 = EUR430.56 per bp; /25 per futures contract = 17.22; x beta 1.05 = 18.08;
tailing 1/(1 + 0.03 x (60/2 + 62)/360) = 0.9924 gives 17.94: sell 18.

More published coefficients and a catalogue of regression specs by market:
[references/published-regressions.md](references/published-regressions.md). Derivations and formulas:
[references/estimator-notes.md](references/estimator-notes.md).

## Signals & interpretation
| Observation | Action |
|---|---|
| HAC CI of beta excludes 1 and the economic P&L gap is material | use the regression hedge; report the risk weight |
| rho > 0.95, tenors close | OLS, TLS, vol-ratio and DV01 agree within 5%: use DV01-neutral for transparency |
| rho < 0.8 | hedge variance is dominated by (1 - rho^2); state the residual vol and size on it, not on the beta |
| Hedge R-squared < 0.5 (or the hedge-to-target correlation is low) | a missing factor or new risk: add a regressor or do not hedge with this instrument |
| OLS << TLS ratio (more than 15% apart) | noisy marks or an unstable leg: use TLS with a noise-based delta, check data |
| 1y rolling beta drift > 30%, or red stability light | switch to EWMA/Kalman, shrink to DV01-neutral, re-weight on a trigger |
| Residual z beyond 2 with a stationary residual and half-life shorter than the horizon | rich/cheap candidate; confirm with a second method (PCA or a simple z) |
| Residual z beyond 2, level residual non-stationary | no trade: the level fit is spurious |
| OOS resid sd > 1.3x in-sample | coefficients unstable: shorten window or use dynamic beta |
| Regime changes mid-sample (policy break, benchmark switch, new facility) | re-estimate post-break only; use dummy and interaction for known events |

## G10 market notes
- **USD.** Treasury futures yield betas fall with duration (1990s fit above); re-estimate per CTD. Rolling 3m beta of
  swap-spread changes on yield changes was positive in 2019 (up to about 0.10 to 0.15, strongest at the long end), the
  convexity-hedging signature (JPM, Dynamic hedgers are long, banks are short, 13 Sep 2019). The 1s2s segment has
  near-zero correlation with other curve segments, so front-end hedge regressions are weak (Willer and Saunders,
  Trading Global Macro Markets, 2026). The standard 3 + 3 one-month contracts per 10 three-month contracts is not FOMC-neutral when a
  meeting is off-centre (3.1 + 2.9 in the worked case); re-solve from days-after-meeting fractions and re-estimate on
  post-Aug-2021 data (Huggins and Schaller, SOFR Futures and Options, 2022).
- **EUR.** A BPV-neutral Bund 5s10s is not PC1-neutral (5y +1bp goes with 10y +0.87bp: Huggins and Schaller 2024);
  rule-of-thumb Euribor-vs-Schatz/Bobl multiples are sample-specific, so regress or use PCA on clean synchronous data
  (Aikin, Welcome to STIR futures forum, 2006 to 2014 archive). Hedging Dutch bonds with German futures leaves a
  relative-slope residual (Duering 2021). Futures CF-adjusted DV01 jumps on a CTD switch (Buxl +37%, OAT/BTP 7-8%).
- **GBP.** Levels fits: 1y1y SONIA on 1y1y ESTR: beta 1.09, R-squared 95% (5m); 5y5y gilt on 5y5y UST beta 1.1, R-squared 75%
  (6m); the rolling 120-day R-squared of a curve fit fell from about 100% to about 60%, so a 12bp residual was not
  faded (JPM, Global Fixed Income Markets Weekly, 21-22 Aug 2026; levels fits, so fair-value guides, not hedge ratios). A front-end basis-vs-policy relation went from
  R-squared 67% to 0% in months (JPM, Cross currency basis 4Q24 Outlook, 26 Sep 2024).
- **JPY.** Swap history starts around 2011; JPY rates have the lowest vol and lowest cross-market correlation in DM
  (0.2 to 0.3: Macrosynergy), so do not import EUR betas. A rolling 2y fair-value fit for 10y JGB reached R-squared
  92.3%, s.e. 7bp (JPM, Japan Fixed Income Markets Weekly, 21 Feb 2025); 3m OIS had a downside beta to equities of
  about 2bp rally per 5% sell-off (Citi, Macro tapas, 7 Aug 2026).
- **AUD, NZD, CAD.** Condition on the driver's direction: rolling 1m betas of Australian 3y/10y yields to US 2y/10y on
  US rally days (JPM, Global Fixed Income Markets Weekly, Aug 2026). AUD-NZD swap returns correlate about 0.8
  (Macrosynergy), so a cross hedge there is cheap.
- **CHF.** Basis beta to the EUR basis shifted from 1.00 to 1.86 when the SNB balance sheet drove it (JPM, Drivers of
  cross currency basis, 11 Mar 2015): an unconditional beta hides the regime.
- **SEK, NOK.** Thin and stale marks attenuate OLS betas: prefer weekly changes or TLS, and for an illiquid open infer
  the move from correlated markets with a conditional-Gaussian regression (NOK 2y from USD/EUR/GBP: Darbyshire 2022).

## Pitfalls
- **Levels for hedges.** High R-squared on levels of rates is misleading; the residual ACF decays slowly (1y vs 3y
  CMT levels R-squared 96.5%, not cointegrated) while the changes beta is 0.792 (Tsay 2010). Difference both sides.
- **Naive t-stats.** On weekly 1y-to-3y CMT changes (2,467 obs) the OLS t-ratio was 107.9, HC 48.4, HAC 39.9, because residuals are heteroskedastic and autocorrelated (Tsay 2010); overlapping horizons make it worse.
- **Wrong dependent.** Reverse regression answers a different trade (example B).
- **Full-sample estimators leak the future.** Fit, z-score and Kalman-tune on a burn-in or rolling past only; smoothed
  Kalman states use future data; lag every beta and z-score by one day when used in a signal.
- **Estimate on one regime, hedge in another.** The optimal slope moves with the variance of x even if the
  conditional relationship does not (Shalizi 2025); betas flip sign across regimes (a basis beta to the policy
  differential in 2024: JPM, Cross currency basis 2H25 Outlook, 5 Jun 2025; the R-squared of the EM Asia 5y5y first
  factor on the USD anchor was about 0.47 before 2023 and 0.76 after: Citi, Decomposing Global Rate Drivers Across
  EM Asia 5y5y, 13 Aug 2026).
- **DV01-neutral is not factor-neutral and regression-neutral is not either.** Residual directionality remains after a
  regression weight; when one leg is pinned (2y before hikes) a 2s/x/y fly behaves like an x/y curve trade.
- **Asymmetric fly weights are a disguised slope trade**; dividing by PC1 loadings fails when PC1 is slope-shaped.
- **Variance-weighted hedges do not fix a missing factor.** Matching partial derivatives raised a high-yield hedge's
  vol from 6.82% to 8.51% while the minimum-variance ratio cut it to 6.01% (Golub and Tilman, Risk Management:
  Approaches for Fixed Income Markets, 2000).
- **Regression hedging lowers correlation, not necessarily volatility** (IRS vs a global risk basket: |corr| 0.23 to
  0.12, hedged-return sd not lower: Macrosynergy 2018).
- **Overfitting by selection.** In-sample R-squared or p-values choose too many regressors; 100 noise predictors yield
  4 passing p < 0.05 and a significant refit (Shalizi 2025). Select by time-series CV or AIC and split data for inference.
- **Collinear legs** inflate gross notional and make betas flip: check corr, condition number, sum |weights| vs net.
- **Hedge ratios age.** PVBP drifts, futures PVBP moves toward the next CTD, delivery notification changes the 1bp
  P&L; neutrality is instantaneous (Duering 2021). Re-estimate on a schedule and state the date and sample.
- **A residual is not a trade.** Structural causes (pension reform, supply, a CTD squeeze) keep a residual open; fade
  only after it stabilises, and prefer structures that hedge the rich leg with its co-moving factor.
- **Betas for thin markets** (NOK, NZD, SEK) are noisy and stale-mark-attenuated: use TLS or weekly changes, and
  check against a liquid proxy before sizing.

## Output
Return a hedge-ratio card per structure:
1. Objective used (DV01 / min-variance / zero-expected-P&L / TLS / factor-neutral) and which leg is dependent.
2. Sample: table, snap, tenors, window, horizon, n, regime exclusions, calibration date.
3. Estimates: beta (OLS, HAC CI), TLS beta with delta used, vol-ratio, EWMA (half-life) and Kalman (q) last values,
   alpha, R-squared, resid sd (bp/day), Ljung-Box p.
4. Trade: signed hedge notionals and DV01s, risk weight, hedged vol in currency/day, gross/net notional.
5. Validation: OOS resid sd vs in-sample, rolling-beta drift, stability flag, collinearity flags.
6. Residual signal if relevant: residual (bp), z, half-life, prediction-interval band, exit rule (within 1 se).
7. Re-estimation trigger and date. Hand the card to
   [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
- [`scripts/hedge_ratios.py`](scripts/hedge_ratios.py): OLS with Newey-West errors, Deming/TLS, vol-ratio and
  reverse-regression menu, mark-noise delta, rolling and EWMA beta, Kalman random-walk beta (filtered, tunable q),
  block bootstrap, Ljung-Box, OU half-life, `oos_table`. CLI reads a canonical `curve_par` table:
  `python scripts/hedge_ratios.py --curve-par curve_par.parquet --curve-id USD-SOFR --y 10Y --x 2Y --horizon 1`.
  `python scripts/hedge_ratios.py --selftest` checks known answers (exact Deming values, errors-in-variables
  simulation, the 1998 Treasury hedge table, Kalman q = 0 equals batch OLS, tracking of a drifting beta, HAC on
  overlapping data).

## Related skills
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weighting menu, fly residuals and stability light
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): beta-weighted spreads and directionality
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA-neutral hedges, loadings, residuals
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 inputs and risk transforms to hedge instruments
- [quant-cointegration](../quant-cointegration/SKILL.md): levels regressions, Engle-Granger, Johansen
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): residual half-life, ADF, entry/exit thresholds
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC, ARMA errors, structural breaks
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): EWMA and shrinkage covariances behind min-variance hedges
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinking a beta toward a prior
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scoring the residual
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD-aware futures hedges
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): futures vs swap hedges
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR futures packs and hedges
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread betas and fair-value regressions
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): vol-on-rates and vol-on-vol regressions
- [quant-regime-detection](../quant-regime-detection/SKILL.md): choosing the estimation window by regime
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): regression-weighted curve hedges of convexity adjustments
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro-factor regression fair values
- [bt-backtest-design](../bt-backtest-design/SKILL.md): lagging betas and point-in-time estimation in backtests
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): walk-forward and purged validation
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): snaps, roll stitching, stale marks
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag and transmission between markets.
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC, alpha decay and signal blending.

## References
- Tuckman and Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): single- and two-variable regression hedges, risk weights, hedged vol, reverse regression, OOS checks, OLS = minimum variance
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): conventional, yield-beta, yield-delta and minimum-variance hedges, futures yield beta, beta instability, levels vs changes
- Duering - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): OLS asymmetry, orthogonal (PCA) regression closed form, futures hedge ratio, window trade-off, hedge ageing
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): PCA vs regression hedges, regression betas in delivery option, WLS rich/cheap regression
- Quantitative Finance Stack Exchange - How to adjust butterfly 2s5s10s swaps trade for directionality? (Jun 2018, edited Oct 2021): regression, PCA, KKT and min-VaR fly weights with OOS test
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch and Dee, 2022): CoVaR hedges equal multivariate regression, MLSR directionality hedge, conditional-Gaussian inference
- Willer and Saunders - Trading Global Macro Markets (Wiley, 2026): segment correlations, front-end hedge regressions weak, rolling-beta sign flips, ridge on an expanding window
- Huggins and Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): sensitivity-matrix FOMC-neutral hedges, SOFR futures basis regressions
- Salomon Brothers - Understanding Duration and Volatility (Sep 1985): why duration ratios are not hedge ratios, PVBP hedge matrix
- Aikin - Welcome to STIR futures (forum Q&A archive, 2006 to 2014): rule-of-thumb futures ratios are sample-specific, clean synchronous data needed
- Hamilton - Time Series Analysis (Princeton University Press, 1994): Kalman recursions, time-varying coefficients, filtering vs smoothing, Engle-Granger normalisation
- Dunis, Laws, Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003): rolling and WLS pathologies, Kalman dynamic beta, Q/R tuning, ridge hedging metrics
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): LS hedge-ratio variance, Kalman hedge-ratio recipe and momentum extension, sparse baskets
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): minus-beta hedge and Sharpe gain, partial hedge under beta uncertainty, Muth/EWMA filter
- Tsay - Analysis of Financial Time Series (3rd ed., Wiley, 2010): levels vs changes, HC/HAC, Ljung-Box vs Durbin-Watson, local-level and time-varying beta filters
- Shalizi - The Truth about Linear Regression (draft notes, 20 Oct 2025, Carnegie Mellon): prediction intervals, R-squared myths, collinearity, leverage, bootstrap, model selection
- Greene - Econometric Analysis (8th ed., Pearson, 2018): Newey-West, condition number, spurious regression
- Golub and Tilman - Risk Management: Approaches for Fixed Income Markets (Wiley, 2000): minimum-variance = regression, swap-spread beta, hedge optimisation, failure of partial matching
- Gelman et al - Bayesian Data Analysis (3rd ed., CRC Press, 2014): prior as pseudo-data, shrinkage priors, t-error robust regression
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): BPV x beta x tailing hedge, regression-beta verification
- Macrosynergy - Interest rate swap returns: empirical lessons (data to Feb 2018): WLS/EWMA blended-frequency beta hedge and its limits
- Citi Research - US Rates Vol Lab and US Rates Weekly (Bikbov, Williams et al., 2016 to 2020): regression-weighted convexity-adjustment hedges, empirical-beta re-weighting, hedge bands
- J.P. Morgan - Interest Rate Derivatives weekly (Younger, Salem, St John, 2018 to 2020) and European Rates Strategy, A primer on Conditional Trades (26 May 2016): rolling directionality betas, multi-horizon beta t-stats, implied vs delivered beta
- Credit Suisse Fixed Income Research - PCA Unleashed (24 Oct 2012): PCA hedge-ratio formulas and factor neutralisation
- Lehman Brothers - Macro-Awareness in Relative Value Trading (Tuckman, Oct 2003): regression-weighted fly vs model weights and regime risk
- Citi Research - Decomposing Global Rate Drivers Across EM Asia 5y5y (13 Aug 2026): orthogonalised regressors, incremental R-squared, stability guards
- Other works cited in the reference files: Hastie, Tibshirani and Friedman, The Elements of Statistical Learning (2nd ed., Springer, 2009); Murphy, Machine Learning: A Probabilistic Perspective (MIT Press, 2012); Wooldridge, Introductory Econometrics (2nd ed.); Chan, Quantitative Trading (Wiley, 2009); Leung and Li, Optimal Mean Reversion Trading (World Scientific, 2016); Shafer and Vovk, Game-Theoretic Foundations for Probability and Finance (Wiley, 2019); Mixon and Onur, Risk Appetite and Intermediation by Swap Dealers (CFTC OCE, Apr 2020); Fleckenstein and Longstaff, Treasury Richness (Journal of Finance, 2023); BofA, ING, Barclays, Nordea and TBAC research notes listed with dates in references/published-regressions.md
- Newey and West - A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix (Econometrica, 1987) (external): HAC estimator
- Deming - Statistical Adjustment of Data (Wiley, 1943) (external): errors-in-variables regression and its slope formula
- Kalman - A new approach to linear filtering and prediction problems (Journal of Basic Engineering, 1960) (external): the filter
