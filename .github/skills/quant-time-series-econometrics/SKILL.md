---
name: quant-time-series-econometrics
description: 'Time-series econometrics toolkit for rates RV series - unit-root/ADF and fractional differencing, autocorrelation and Ljung-Box, ARMA/AR forecasts vs naive persistence, HAC / Newey-West t-stats for overlapping returns, level-vs-change regressions, structural-break tests (Chow, CUSUM, Bai-Perron, SADF), GARCH/EWMA volatility, VAR/IRF and Kalman state-space. Use when asked unit-root/ADF mechanics for a spread, fly, curve or basis, whether a t-stat or backtest is significant given overlapping or autocorrelated data, how to forecast or scale volatility (GARCH, EWMA, bp vol), how a shock propagates (VAR, impulse response), or which window or model to trust before a mean-reversion or hedge-ratio trade. Triggers - ADF, unit root, ARIMA, GARCH, Newey-West, HAC, autocorrelation, VAR, Kalman, frac-diff, heteroskedasticity, spurious regression. Half-life and entry bands: quant-mean-reversion-ou; multi-leg weights: quant-cointegration; regime gates: quant-regime-detection.'
---

# Time-series econometrics for rates series

Rates RV signals are statistics on persistent, heteroskedastic, regime-prone series. This skill is the gatekeeper:
it decides which series can be modelled in levels or must be differenced, whether a t-stat survives overlapping
and autocorrelated data, whether a relationship is stable or has broken, and what volatility to scale by. It does not
generate trade ideas; it says how much a statistic is worth. Mean-reversion fitting (OU, half-life, entry bands)
lives in [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md); cointegration in
[quant-cointegration](../quant-cointegration/SKILL.md); this skill supplies the tests and error bars they rely on.

## When to use
- "Is this 2s5s10s fly / swap spread / basis stationary or a random walk?" (ADF + KPSS-style cross-check, power caveat).
- "Is this t-stat / hit rate real?" with overlapping h-day changes, rolling windows or autocorrelated residuals (HAC).
- "Did the relationship change?" before trusting a z-score, regression hedge or mean-reversion fit (Chow, CUSUM, Bai-Perron).
- "What vol should I scale by / is vol clustering?" (EWMA, GARCH(1,1), GJR, level dependence of bp vol).
- "How does a shock to inflation/growth/risk move the curve over time?" (VAR, Cholesky IRF, sign-restricted BVAR).
- "Which model beats persistence?" (AR/ARMA, walk-forward, AIC/BIC) and "level or change regression?".
- Time-varying beta or latent level/trend (Kalman, local level) at the concept level; the hedge-ratio application is in
  [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap/OIS rates or govt par yields, one tenor or a built spread/fly | `curve_par` | daily, one `snap`, >= 3y (>= 1000 obs for GARCH) | `par_rate_pct`; convert changes to bp (x100). Filter ONE `curve_id, start, tenor, snap`; never mix snaps |
| Bond yields, futures, STIR prices | `bond_quotes`, `fut_quotes`, `stir_quotes` | daily | futures: roll-stitched specific contracts via `roll_map`; STIR `rate_pct` = 100 - price |
| Swap / asset-swap spreads | `swap_spreads` | daily | carry `sign_convention`; state it |
| Normal vols | `vol_surface`, `opt_quotes` | daily | `nvol_bp`; model vol in bp, not lognormal |
| Macro factors for VAR / state-space | `macro_series` | weekly-monthly, as-of vintage | use first release; consensus column for surprises |
| Output signals | `signals` | per date | signal at t uses data known at t, trade from t+1 |

Series must pass the checks in [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md)
(stale quotes, roll jumps, `data_ok = false`) first: a stale run or a roll jump is a fake structural break and fake
autocorrelation. Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If a series is
missing or too short for the test, say so; never pad or invent history.

## Method

### 0. Triage: pick the test from the question
| Question | First tool | Decision |
|---|---|---|
| Can I model this in levels? | ADF (+ residual ACF), section 2 | unit root not rejected -> work in changes, or use a cointegrating spread |
| Is the t-stat honest? | Ljung-Box on residuals, HAC t, section 4 | HAC t < 2 while OLS t > 2 -> not significant |
| Is the relationship stable? | rolling beta, Chow, CUSUM, section 5 | break -> re-estimate on post-break window, or do not trade the fit |
| What is tomorrow's risk? | EWMA / GARCH, section 6 | scale positions by forecast bp vol |
| What does a shock do over time? | VAR + IRF, section 7 | report cumulative IRF with ordering bounds |
| Time-varying beta or level? | Kalman, section 8 | tune Q so the hedge does not chase noise |

### 1. Prepare the series
1. Work in bp. Level `y_t` in bp; change `dy_t = y_t - y_{t-1}` in bp. Curve A-B = yield(longer) - yield(shorter) (2s10s = 10y - 2y);
   fly 2s5s10s = 2*y5 - y2 - y10. DV01-weight legs before testing a package; a test on an unweighted spread tests the
   wrong object.
2. Never take logs of yields or spreads that can be zero or negative (EUR, CHF, JPY, SEK all went below zero). Logs are for
   prices (bond or futures prices) and for strictly positive indices.
3. One snap, one vintage, business-day index. Use only data available on the date (no full-sample z-scores or
   full-sample fits: they are look-ahead). Signal at t, trade from t+1.
4. Check the effective sample size. Overlapping h-day changes from T days carry about T/h independent observations
   (Ross, Introduction to Probability Models, 10th ed., 2010: the average of k+1 uncorrelated values has lag-m autocovariance (k+1-m) sigma^2/(k+1)^2 for m <= k, zero beyond).
5. Test on the object you will trade (the DV01-weighted fly or the residual), not on its inputs.

### 2. Stationarity and unit roots
**ADF regression** (Tsay, Analysis of Financial Time Series, 3rd ed., 2010; Hamilton, Time Series Analysis, 1994):
`dx_t = c + b*x_{t-1} + sum_{i=1}^{p-1} phi_i dx_{t-i} + e_t`, H0: b = 0 (unit root). The t-ratio has a Dickey-Fuller
(not Student) distribution.
- Default: constant, no trend, for a rate or spread level. 5% critical value about -2.86 (large T; -2.89 at T = 164, Hamilton).
  With a linear trend about -3.41 (-3.44 at T = 164). Use the case that matches your null and alternative (Hamilton Ch.17; tables B.5-B.6).
- Lag length: start at an upper bound and drop the last lagged difference while its t-stat is insignificant
  (the lagged-difference coefficients are asymptotically normal, so ordinary t and F tests are valid for this step; Hamilton).
  Daily rates: start at 5-10 lags (monthly data: at least 12). Check the residual ACF is white afterwards.
- Two statistics exist: the rho-statistic `T(rho_hat - 1)/(1 - sum zeta_hat)` and the t-statistic with no serial-correlation
  correction; compare each with its own table.
- **Power**: unit-root tests have low power near rho = 1 and size distortions with large negative MA roots. Fail-to-reject is not
  acceptance; reject is not proof of useful mean reversion. Treat ADF as a screen, then ask whether the half-life
  `-ln2/ln(phi)` is short enough to trade (below).
- Cross-check with a stationarity-null test (KPSS: H0 stationary). Both tests agree -> act; they disagree -> treat as "ambiguous, short-memory at best".
- Rule of thumb (Wooldridge, Introductory Econometrics, 2nd ed.): many economists difference when the first autocorrelation of the level exceeds 0.9 (some at 0.8).
- Bid-ask bounce (negative lag-1 autocovariance) can make a random-walk price look stationary in unit-root tests; clean or model it before testing traded prices; Roll: `gamma_1 = -c^2`, effective spread `2c = 2 sqrt(-gamma_1)` (Hasbrouck, Empirical Market Microstructure teaching notes, 2004).
- Engle-Granger residual tests need Davidson-MacKinnon critical values (no trend: 1% -3.90, 5% -3.34, 10% -3.04; with trend:
  -4.32, -3.78, -3.50), not DF tables (Wooldridge). The cointegration workflow itself is in [quant-cointegration](../quant-cointegration/SKILL.md).

**Half-life** from an AR(1) coefficient per step: `tau = -ln2/ln(phi)`, `phi = 2^(-1/tau)` (Lopez de Prado, Advances in Financial
Machine Learning, 2018, Ch.13). Phi in (-1, 1) is stationary. A half-life in the same order as the sample length is a random walk in practice.

**Fractional differencing** (Lopez de Prado 2018, Ch.5). Integer differencing (d = 1) makes a series stationary but erases memory;
the question is the smallest d that passes the test.
- Weights: `w_0 = 1`, `w_k = -w_{k-1} (d - k + 1)/k`. d = 1 gives {1, -1, 0, ...}; 0 < d < 1 gives -1 < w_k < 0.
- Use the fixed-width window (FFD): drop weights once `|w_k| < tau` and apply one weight vector to every date (no drift, unlike the expanding window).
  Defaults: log prices for price series, plain levels for yields; tau = 1e-5 (window about 600-2300 obs for d = 0.6-0.3; needs a much longer series) or 1e-2 (window about 10; use this on 1000-3000 obs).
- Search d on `linspace(0, 1, 11)`; ADF with constant and few lags; report the smallest d that passes and the correlation with the original series.
- **Calibrate against a random walk of the same length.** In this skill's own simulation (n = 1000-5000, pure random walks, tau 1e-2 to 1e-5) the minimum d
  that "passes" was 0.0-0.6, typically 0.2-0.3: ADF has little power against d just below 1, so a rates series with d* of 0.5-0.6 (the book's rates-futures rows
  sit at 0.2-0.6, Lopez de Prado 2018 Table 5.1) is not evidence of memory beyond a unit root. Use FFD as a feature transform (stationary, correlated with levels), not as a
  memory test, unless d* is clearly above the simulated random-walk d*. The script's `min_d` runs the search.

### 3. Autocorrelation, ARMA and forecasting
1. **Ljung-Box** `Q' = T(T+2) sum_{j=1}^{m} r_j^2/(T-j)`, chi-square with `m - (fitted ARMA params)` d.o.f. (Greene, Econometric Analysis, 8th ed., 2018). Preferred to Box-Pierce (`T sum r^2`).
   Use m = 10 and 20 daily (m around ln T is a common default). Run it on changes AND on squared changes (squares test ARCH).
   Do not use Durbin-Watson with a lagged dependent variable (biased toward 2); Breusch-Godfrey `T R^2 ~ chi2(P)` is valid there. DW checks lag 1 only.
2. **Daily rate changes** are usually close to white noise in the mean with autocorrelated squares (reader inference; check with the script). Fit
   mean models only if Ljung-Box rejects, and benchmark every model against (a) zero/last-value persistence and (b) a linear AR.
   On daily single-stock data, i.i.d. beat AR(1), MA(1) and ARMA(1,1) on test MSE (0.000754 vs 0.000793, 0.000805, 0.000914) (Palomar, Portfolio Optimization, 2025).
   An AR(5) matched an RNN's out-of-sample R^2 (0.41 vs 0.42) with 16 vs 205 parameters (James et al., ISLP, Python ed.).
   US 10y swap daily bp changes (student study, train to 2007, test 2008): buy-and-hold Sharpe 0.25, rolling-OLS AR(3) 0.23 scaled but 0 unscaled, Burg AR(4) 0.9 - the estimator and scaling choice moved the result more than the AR idea, so treat a single fit as fragile (Burton, Dektor and Wheeler, c.2008).
3. **Order selection**: AIC (`L - k`) for forecasting, BIC (`L - (k ln n)/2`) for the true order; higher orders overfit; compare on walk-forward error, never in-sample R^2.
   Chronological split only; k-fold on time data leaks (Palomar 2025; Lopez de Prado 2018).
4. MA(1) `x_t = e_t + theta e_{t-1}`: `gamma_0 = (1+theta^2) s^2`, `gamma_1 = theta s^2`, invertible root |theta| < 1 of `gamma_1 th^2 - gamma_0 th + gamma_1 = 0`.
   AR(1) `x_t = phi x_{t-1} + z_t`: `gamma_m = s^2 phi^m/(1-phi^2)` (Ross 2010).
5. Multi-step forecasts of a stable AR decay to the mean at `phi^s`; the forecast of a spread beyond about 4-5 half-lives (under 6% of the gap left) is the unconditional mean. Mean forecasts of
   changes at horizon above a few days are not better than zero for rates unless a macro/fair-value input exists
   ([macro-fair-value-models](../macro-fair-value-models/SKILL.md)).
6. A sample mean is a poor estimate at small T (error above 100% at N = 100, T = 500, Palomar 2025): default to zero mean for changes.

### 4. Inference with serial correlation (HAC)
**When**: any regression or mean test on overlapping returns, rolling-window outputs, or residuals with significant Ljung-Box.
`Cov_HAC(beta) = (X'X)^-1 C (X'X)^-1`, `C = sum_t e_t^2 x_t x_t' + sum_{j=1}^{l} w_j sum_{t>j} (x_t e_t e_{t-j} x_{t-j}' + x_{t-j} e_{t-j} e_t x_t')`,
Bartlett weights `w_j = 1 - j/(l+1)` (Newey-West). White/HC0 is the `j = 0` term only (Tsay 2010, s2.10).
- **Lag l**: `int(4 (T/100)^(2/9))` (Tsay: T = 250 -> 4, 1000 -> 6, 5000 -> 9) or about `T^(1/4)` (Greene). State which.
- **Overlapping h-day changes** (h > 1): errors are MA(h-1) by construction, so OLS and HC t-stats are inflated by about `sqrt(h)` (2.2x at h = 5, 4.6x at h = 21)
  regardless of the economics. This skill's derivation (iid data, tested in `--selftest`): true long-run variance = `h^2` per unit variance, so
  `se(mean) = h/sqrt(n)`. Bartlett with `l = h-1` recovers only about 81% of that se (h = 5: 0.825; h = 21: 0.81); `l = 2h` about 0.92; `l = 4h` about 0.95; the uniform
  (Hansen-Hodrick) kernel with `l = h-1` is exact for iid data but can return a negative variance. **Rule**: use Newey-West with `l >= 2h`, cross-check with Hansen-Hodrick at `l = h-1`,
  and call a result significant only if both say |t| > 2 and a non-overlapping subsample (every h-th day) has the same sign. The script prints both.
- Naive-vs-HAC magnitude (Tsay 2010): t-ratio in a regression of one UST yield change on another, 107.9 (OLS), 48.4 (HC), 39.9 (HAC): the naive t was inflated by more than 2.5x. Correlated errors understate standard errors and overstate significance (James et al., ISLP).
- **Levels vs changes.** Level model `y = a + b x + e`; change model `dy = b dx + de`. If the assumptions hold for one, the other stays consistent but is inefficient with serially correlated errors (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022, Ch.6).
  Regressing one random walk on another "is virtually certain to suggest a significant relationship" (Greene 2018); a 96.5% R^2 level regression of the 3y on the 1y UST yield (slope 0.930) had strongly serially correlated residuals, with a change beta of about 0.79 weekly 1962-2009 (Tsay 2010).
  Hedge ratios: regress CHANGES; read a level regression only through its residual (is it stationary? ADF on the residual with EG critical values).
- Explicit residual dynamics for a convergence model: `e_t = rho e_{t-1} + nu_t`; with rho = 75% a -4% error decays to -3% on average in one step (Tuckman and Serrat 2022). Require evidence that
  convergence has started before trading a persistent residual.
- Heteroskedasticity: HC0/HC1 for cross-sectional scatter; HAC when autocorrelation also present; WLS with `w = 1/sigma_i^2` if you can model the variance; GLS needs a parametric autocovariance (Shalizi, The Truth about Linear Regression, 2025).
- Collinearity: condition number > 20 matters (Greene 2018); dropping a collinear regressor trades variance for bias.
- Inference after selection: with n = 200 and 100 pure-noise predictors, 4 pass p < 0.05 and the refit overall F has p = 0.031; select on one half, infer on the other (Shalizi 2025). 20 tries give a 64% chance (1 - 0.95^20) of a t >= 2 fluke (Grinold and Kahn, Active Portfolio Management, 2nd ed., 1999).
- Sharpe-ratio error: `SE(SR) = sqrt((1 + SR^2/2)/T)` for iid returns (Paleologo, The Elements of Quantitative Investing, 2025). Annual SR 0.5 on 5 years: SE = sqrt(1.125/5) = 0.47, so t = 1.05.

### 5. Structural breaks and regime shifts
Test for breaks BEFORE trusting a mean-reversion or hedge regression; regime change is an identifiable macro event, not a 10-sigma shock (Lehman Brothers, LMR Quarterly 2003-Q3, Oct 2003).
| Test | Use | Core formula / threshold | Caveat |
|---|---|---|---|
| Chow | known date (policy shift, QE start, YCC change) | `F[K, n-2K] = ((SSR_p - SSR_1 - SSR_2)/K)/((SSR_1+SSR_2)/(n-2K))` (Greene 2018) | assumes equal variances; Wald if not |
| Brown-Durbin-Evans CUSUM | unknown date, intercept-type shift | recursive residuals `w_t = (y_t - b_{t-1}'x_t)/sqrt(1 + x_t'(X'X)^-1 x_t)`, `S_t = sum w/s_w`; 5% boundary `+-0.948(sqrt(n) + 2t/sqrt(n))` (external: Brown, Durbin, Evans, 1975) | depends on the burn-in start; low power vs a slope break on a zero-mean regressor |
| Chu-Stinchcombe-White CUSUM (log levels) | drift change in a price | `S_{n,t} = (y_t - y_n)/(s_t sqrt(t-n))`, 5% critical value `sqrt(4.6 + ln(t-n))`; take `sup_n` (Lopez de Prado 2018, Ch.17) | reference point matters; use sup |
| Bai-Perron | multiple unknown breaks | break dates minimise total SSE across regimes with regime-specific coefficients (Bai and Perron 2003); Tuckman used about 10y of changes of the 5y swap on the third Eurodollar futures contract, the 2y and the 10y swap (Lehman 2003) | needs trimming and enough obs per regime |
| SADF / QADF / CADF | explosive (bubble) behaviour | `SADF_t = sup_{t0} ADF_{t0,t}`, log prices; QADF = q-quantile (more robust), CADF = tail mean (typ. q = 0.95) (Lopez de Prado 2018, Ch.17) | O(n^2); supremum is outlier-sensitive |
Procedure: (1) rolling 1y beta/mean/vol plot, look for a level shift; (2) Chow at every candidate policy/market date and BDE CUSUM as an unknown-date screen; (3) if a break
is found, re-estimate on the post-break window only and compare half-life and beta; (4) if the post-break window is shorter than about 3 half-lives, the fit is unusable for sizing.
- Two regime-shift types seen in curve relationships: a change in the perceived speed of recovery and a change in curvature of the vol curve (Lehman 2003). Regime shifts put mean-reversion trades offside systematically,
  and all the desk's trades share the exposure: hedge at book level, not trade by trade.
- Stylised trap: fly means of 15, 35 and 25bp in three regimes; the mean-reversion trader buys at the new higher equilibrium (misread as cheap), sells at the next, "nearly always off sides" (Lehman 2003).
- Window choice has no clean answer: check sub-periods; results can hinge on one episode (the 1979-82 period dominates the rate-vol results in Salomon Brothers, Understanding the Yield Curve Part 7, Feb 1996).
- Persistence varies by era: VARs on 1950-69, 1970-89, 1990-2009 and 2010-19 give different inflation-shock persistence; a credible inflation targeter reverses shocks within 12-18 months (During, Fixed Income Trading and Risk Management, 2021).

### 6. Volatility
Model volatility of changes in **bp** (normal vol), the unit of `nvol_bp` (per year: daily bp vol = `nvol_bp/sqrt(252)`); a lognormal or percentage vol gives a level-dependent number that drifts with the rate level.
- **EWMA**: `s2_t = a e2_{t-1} + (1-a) s2_{t-1}`. Daily default `a = 0.06` (decay 0.94, weights halve in about 11 days); a of 0.10-0.33 reacts faster (Palomar 2025). No mean reversion in vol.
- **GARCH(1,1)**: `s2_t = w + a e2_{t-1} + b s2_{t-1}`; stationary if `a + b < 1`; long-run variance `w/(1 - a - b)`; EWMA is the `w = 0, b = 1 - a` case.
  h-step forecast: `s2(h) = w(1 - p^(h-1))/(1-p) + p^(h-1) s2(1)`, `p = a + b` (Dunis et al., Applied Quantitative Methods for Trading and Investment, 2003).
  Shock half-life `ln0.5/ln p`: p = 0.89 -> 5.9 days; 0.98 -> 34 days; 0.95 -> 13.5 days.
  Kurtosis (not excess): `3(1 - p^2)/(1 - p^2 - 2a^2) > 3`: a = 0.08, b = 0.90 -> 4.43, i.e. excess 1.43 (Paleologo 2025).
- **GJR**: add `g*S_{t-1} e2_{t-1}`, S = 1 if e < 0; constraint `a + b + g/2 < 1`; long-run `w/(1 - a - b - g/2)`; start g near 0.01 (Dunis 2003). In rates the leverage effect is state-dependent (selloff vs rally); test g, do not assume the sign.
- **Data hunger**: with `w = 0, a = 0.07, b = 0.925` and T = 1000 the estimates scatter about 0.1 (Palomar 2025). Fit on >= 1000 daily obs, standardise the data before optimising (the script does), restart from several (a, b) starts, and
  distrust `a -> 0, b -> 1` solutions (no ARCH effect: use a simple rolling or EWMA sd). Sample GARCH quality check: Ljung-Box on squared standardised residuals should pass.
- **Level dependence (CKLS)**: `dr = k(l - r)dt + s r^gamma dz`. gamma = 0 Vasicek (bp vol level-independent), 0.5 CIR, about 1 lognormal-like (BDT). Daily 3m bill changes: gamma = 1.44 (1977-94), 0.71 (1983-94); with GARCH 0.37 and 0.17; GARCH persistence 0.87 and 0.95 on lagged variance, 0.02 and 0.03 on the lagged squared change (Salomon Brothers, Feb 1996). Since 1983 vol has been much less tied to level than in 1979-82; in zero-bound regimes (JPY, CHF, EUR, SEK) bp vol is regime-specific (reader inference): never scale a different-level regime by a full-sample bp vol.
- **Other estimators**: Parkinson high-low `E[(ln H/L)^2] = 4 ln2 s^2` (`k2 = sqrt(8/pi)` for the mean log range); realised variance `sum r^2` (uncentred, bias alpha^2/n, variance about `2 s^4/n`);
  stochastic-vol via Kalman on `ln(e_t^2) = -1.27 + h_t + xi_t`, `var(xi) = pi^2/2` gives a smoother envelope than GARCH (Palomar 2025; Lopez de Prado 2018; Paleologo 2025).
- **Loss functions** for vol forecasts: QLIKE `r^2/s^2 - ln(r^2/s^2) - 1` and MSE on variance; both are robust to a noisy unbiased proxy; QLIKE penalises under-forecast more (Paleologo 2025).
- Square-root-of-time scaling to h days holds only for a zero-drift IGARCH; with GARCH use `sum_{k=1}^{h} s2(k)`. Normal VaR understates fat tails (Tsay 2010).
- Markov-switching vol: expected duration `1/(1 - p_ii)`; the likelihood-ratio chi-square does not select the number of regimes (see [quant-regime-detection](../quant-regime-detection/SKILL.md)).

### 7. VAR, VECM and impulse responses
1. `y_t = c + A_1 y_{t-1} + ... + A_p y_{t-p} + e_t`, `Sigma = Var(e)`. Estimate by equation-wise OLS; choose p by BIC (AIC if p is too short); check the residual ACF.
   VAR in differences of non-cointegrated I(1) series; with cointegration use a VECM `dy_t = Pi y_{t-1} + sum G_i dy_{t-i} + e_t` (a VAR in differences is then mis-specified; Hasbrouck 2004).
2. **IRF**: `Theta_0 = I`, `Theta_h = sum_{i=1}^{min(h,p)} A_i Theta_{h-i}` (an AR(2) with 0.5, 0.2 gives 1, 0.5, 0.45, 0.325). Orthogonalise with the Cholesky factor of Sigma: the VARIABLE ORDER is the identifying
   assumption (the first variable is not hit contemporaneously). Report min/max over orderings; report the cumulative IRF for integrated series; judge a VAR by its IRFs, not single coefficients (Hasbrouck 2004).
3. **Sign restrictions (Bayesian VAR)** avoid an arbitrary ordering. 10y yield shock decomposition uses 10y yield, 5y5y inflation, a real exchange-rate measure and a valuation variable with restrictions
   (inflation shock: inflation +, 10y +, valuation -; monetary shock: inflation -, 10y +, FX +, valuation -; demand shock: inflation -, 10y -, FX -, valuation -; risk shock: 10y -, FX +, valuation -)
   (BofA Global Research, US Rates Primer: UST RV Primer, May 2022). Priors rule out non-economic solutions (BofA, Monthly rates models, Aug 2025).
4. Parameter drift matters as much as the data: a roll of the sample can change persistence materially; re-estimate on rolling windows and report IRF stability.
5. Example (During 2021, GDP and deflator VARs 1980-2019, 1% shock): GDP shock lifts front par yields about 0.8%, decaying to about 0 within about 3 years (moves slope); deflator shock lifts about 3.2% at the front, still about 1% by 2029 (moves the whole curve). Observed daily UST moves are mostly parallel, so IRF shape is a model statement, not market truth.
6. **Cointegrated prices** (error correction): `dp_t = phi(L) dp_t + [g1; g2](p1 - p2)_{t-1} + e_t`; g1 < 0 means p1 moves toward p2. Threshold ECM: no adjustment inside the transaction-cost band (Hasbrouck 2004; Tsay 2010).
   Johansen's trace and max-eigenvalue tests can disagree (Hamilton: PPP Engle-Granger said no, Johansen trace 38.85 vs 29.5 said yes): report both.

### 8. State-space models and the Kalman filter
State `xi_{t+1} = F xi_t + v`, `Var v = Q`; observation `y_t = A'x_t + H'xi_t + w`, `Var w = R` (Hamilton 1994, Ch.13).
- Predict: `xi_{t+1|t} = F xi_{t|t}`, `P_{t+1|t} = F P_{t|t} F' + Q`. Update: `xi_{t|t} = xi_{t|t-1} + P H (H'PH + R)^-1 (y_t - A'x_t - H'xi_{t|t-1})`, `P_{t|t} = P - P H (H'PH + R)^-1 H'P`.
  `P` and the gain do not depend on the data. Likelihood: sum of normal log densities of the one-step errors (prediction-error decomposition). Initialise `vec(P_1) = (I - F kron F)^-1 vec(Q)` if F is stable, else a large diagonal P.
- Uses: local level `y = a_t + e`, `a_t = a_{t-1} + e_a` (replaces a rolling mean with no look-back); recursive least squares is a Kalman filter with a constant state (`F = I, Q = 0`, `H_t = x_t`); `Q > 0` gives a drifting hedge ratio (Murphy, Machine Learning: A Probabilistic Perspective, 2012).
  Dynamic factor models: `y_it = mu_i + gamma_i C_t + chi_it` (Stock-Watson); global-yield fair value as a state-space model with residual z-scores (BofA, Aug 2025).
- **Q controls everything**: too small - lags a changing beta; too large - the hedge chases noise and spread variance shrinks until profit < costs; short rolling-LS windows are noisy, long ones are slow (Palomar 2025). Choose Q by walk-forward hedged-spread variance net of turnover cost.
- Pitfalls: singular Hessian = unidentified (e.g. `y = e_1 + e_2` identifies only `s1^2 + s2^2`); MA(1) theta and 1/theta give the same likelihood; parameterise covariances by Cholesky; use sandwich standard errors for non-Gaussian errors;
  smoothed states use future data (look-ahead), so only filtered states may drive signals; add parameter uncertainty to the filtered MSE (Hamilton 1994).
- Short-rate model fits can be badly behaved: two near-identical likelihood optima with very different parameters; fix by averaging mean and reversion speed, then re-fitting the start point and variance only (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed., 2024). Model-based fair values: [curve-term-structure-models](../curve-term-structure-models/SKILL.md).

### 9. Seasonal decomposition (series with calendar structure)
Seasonal factor of a month = average over years of (actual - smoothed) as % of trend, smoothed by an HP filter (simple; revises history with new data) or X-12-ARIMA (movable feasts). Japan CPI ex fresh food has seasonal variability "well in excess" of trend inflation (During 2021):
estimate the seasonal before reading a trend. Details and calendar effects: [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md).

### 10. Validate the model itself
1. Out-of-sample walk-forward, non-anticipative; `E[test MSE] = E[train MSE] + (2/n) sum Cov(Y_i, m_i)`, which for a linear model equals `(2/n) s^2 (p+1)`: in-sample R^2 always picks too large a model (Shalizi 2025).
2. Known-answer tests: run the method on (a) pure noise and (b) simulated data with a known relation; it must find nothing in (a) and recover (b) (Grinold and Kahn 1999). This skill's script is tested this way.
3. Posterior-predictive style check for a fitted OU/spread model: simulate from it and compare tail extremes, run counts and autocorrelation with the data (Gelman et al., Bayesian Data Analysis, 3rd ed., 2014).
4. Statistics identify candidates; they are not the rationale. A change regression cannot give a fair value ("moved more than predicted" is not a reason to fade) (swapsball.net, Regression in finance: friend or foe?, Oct 2017).
5. Costs: in a US swap study a 1bp bid-ask neutralised the out-of-sample edge of sparse mean-reverting baskets; compare out-of-sample range in bp with costs before trusting any basket (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008).

## Worked examples
All numbers are from the cited source unless labelled "derived" (checked in `scripts/ts_diagnostics.py --selftest`).
1. **ADF on log GNP** (Hamilton 1994, Ch.17; T = 164, case 4, p = 4): `rho_hat = 0.94969`, `ADF rho = 164/(1 - 0.329 - 0.209 + 0.084 + 0.075) x (0.94969 - 1) = -13.3`
   vs 5% critical -21.0, ADF t = -2.60 vs -3.44: unit root not rejected. T-bill 1948-89: `rho_hat = 0.96904`, ADF t = -1.66 vs -2.89 at 5%. Lesson: near-unit-root rates look non-stationary on 40 years of data; the 0.969 per-quarter coefficient still implies a half-life of `ln0.5/ln0.969` = 22 quarters (about 5.5 years), a trading-relevant statement the ADF cannot make.
2. **Short-rate spread, fast reverter** (Wooldridge 2nd ed.): 6m vs 3m T-bill spread, DF t = -7.71, `rho = 0.33` per quarter (half-life `ln0.5/ln0.33 = 0.63` quarter, under one quarter), error-correction speed -0.84 per quarter. A stationary spread so fast it is gone before execution; a failed counter-example: residual ADF -2.43 vs 10% critical -3.50 (no cointegration).
3. **HAC for overlapping changes** (derived, iid unit noise, h = 5, n = 60,000): naive se = 0.45 x truth, Bartlett `l = 4` = 0.82, Newey-West `l = 10` = 0.92, `l = 20` = 0.96, uniform `l = 4` = 1.00. A strategy t-stat of 4.5 from 5-day overlapping returns is about t = 2 after correction.
4. **GARCH half-life and forecast** (derived from the formulas above): `a = 0.08, b = 0.90`, long-run sd 4bp/day, today's one-step sd 6bp. `p = 0.98`; 20-day-ahead variance `16 + 0.98^19 x (36 - 16) = 29.6`, sd 5.4bp; the shock has decayed by only 1 - 0.98^19 = 32% after 19 days. Rule: vol-target to the 1-day forecast, but size a 20-day trade on the average forecast variance over the horizon.
5. **Regime trap** (Lehman 2003): fly means 15 / 35 / 25bp across three regimes; any rolling z-score with a window shorter than a regime fades the first regime change wrongly.
6. **Regression hedge** (Tuckman and Serrat 2022, Ch.6): long 100mm 20y, short 79.44mm 10y and 50.69mm 30y (risk weights 46.5% and 66.9%, total 113.4%, only 100% under parallel shifts); residual se 1.15bp in-sample, 0.70bp out-of-sample. A hedge calibrated on the last 122 days and tested on the next 122 (swapsball.net 2017) is the same discipline.
7. **Box-Tiao / predictability** (d'Aspremont 2008, US swaps 1Y-30Y, 100 days): mean reversion `lambda` rises 0.58 -> 238 across 8 portfolios ordered by predictability while portfolio volatility ends at 0.07 (from 0.21); `lambda = 238` is a half-life about 1 day and statistically insignificant on daily data. Most of the reversion is captured with 3-5 legs (3Y/4Y/5Y weights -0.288, 0.806, -0.517).
8. **Nowcast benchmarking** (Barclays Research, Global Rates Weekly, 2 Oct 2026): an AR(1) on lagged ISM prices-paid forecast about 70, the augmented model (diesel and commodity returns) 75.1, actual 77.9, consensus 73.0; the preferred specification was selected by expanding-window out-of-sample RMSE, and model and survey had similar historical accuracy.
More cases (ADF cases and critical values, GARCH variants, SADF family, Kalman embeddings, microstructure identities, per-currency parameter-instability evidence): [references/estimators-and-g10-notes.md](references/estimators-and-g10-notes.md).

## Signals & interpretation
| Diagnostic | Reading | Action |
|---|---|---|
| ADF fails, KPSS rejects | unit root | difference, or cointegrate; do not fit OU on levels |
| ADF rejects, half-life < 2-3 days | statistically stationary, economically untradable after costs | skip or trade only with low-cost instruments |
| ADF rejects, half-life > 1/3 of the sample | likely sampling artefact | require a longer sample or a structural reason |
| Ljung-Box (squares) p < 0.01 | vol clustering | use GARCH/EWMA vol, not constant sd, in z-scores and sizing |
| OLS t > 2, HAC t < 2 | autocorrelation artefact | reject the signal |
| HAC t > 2 only on overlapping data, not on h-spaced subsample | overlap artefact | reject |
| BDE max abs W / boundary > 1 or Chow p < 0.01 | relationship changed | re-estimate post-break; no trade from the old fit |
| GARCH `a + b > 0.995` | integrated vol (EWMA-like) | use EWMA; do not extrapolate long-run vol |
| Sharpe t = SR/SE(SR) < 2 | indistinguishable from noise | needs more years or more independent bets |
| VAR IRFs flip sign across orderings | identification driven by order | use sign restrictions or report both |
| In-sample beat naive, out-of-sample does not | overfit | drop the model |
Confirmation: any "significant" finding must hold in (1) the HAC test, (2) a sub-period split, (3) a walk-forward out-of-sample window, and (4) after realistic costs.

## Pitfalls
- Level regressions of two near-unit-root series give high R^2 and a significant t that mean nothing; read the residual ACF first (Tsay 2010; Greene 2018).
- Differencing both sides removes the long-run relation; with cointegration use a VECM, otherwise a change regression is correct for hedges but gives no fair value.
- Unit-root and cointegration tests disagree and lose power; cointegration found in sample often disappears out of sample (a pair passed 4 of 6 tests); correlation of changes is not cointegration (Palomar 2025).
- Using full-sample statistics (z-scores, GARCH fit, smoothed Kalman states, Kim smoother) is look-ahead.
- Overlapping horizons with plain OLS: t inflated by about `sqrt(h)`; Bartlett `l = h-1` still understates.
- Stale quotes, roll jumps and snap mixing produce autocorrelation and fake breaks; clean first.
- A fit that worked on one window fails at a regime change (a Bobl asset-swap fit on 2013-14 data worked briefly, then broke once a QE-driven trend began; swapsball.net 2017). Non-economic buying (QE, foreign official buying) breaks VARs and fair values; include balance-sheet and global-yield terms (BofA, UST macro framework, Oct 2024).
- GARCH with fewer than about 1000 observations, or `a` near 0: parameters are noise. Gaussian likelihood on fat-tailed data gives quasi-ML estimates: keep them, use sandwich errors.
- Logs of yields near or below zero; HP-filter seasonal revision; Durbin-Watson with lagged dependent variable.
- Data-driven lag, window or threshold choice without correction for the number of trials (20 tries = 64% chance of a fluke).
- Constant-vol OU overstates Sharpe at extreme entry points; a vol-regime change within the sample invalidates the fit (Huggins and Schaller 2024).
- Entry/exit grids fitted to a near-random-walk spread (half-life long vs the sample) are overfitting: the optimum goes flat (Lopez de Prado 2018, Ch.13).
- Treating `p`-values of data-mined candidates as if tested once (see [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md)).

## Output
Return a diagnostics table and a verdict per series or model:
| Series / model | n, window | Test | Statistic | Threshold / p | Verdict | Action |
|---|---|---|---|---|---|---|
Required rows (when applicable): ADF (lags, case, stat, critical) and half-life with a CI from simulation; Ljung-Box on levels-changes and squares (m = 10, 20); the HAC t beside the OLS t with kernel and lag stated;
break test (date, statistic, post-break parameters); vol model (parameters, persistence, last and long-run bp vol); out-of-sample comparison against persistence. Plus a one-line statement of what was NOT testable (short sample, missing data).
Charts: rolling parameter plot with break markers, ACF of changes and squares, CUSUM path with boundary, IRF with ordering bounds ([eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md)).
Hand-off: a significance and stability statement into [rv-composite-scoring](../rv-composite-scoring/SKILL.md) and [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (what was tested, what survived, the window used).

## Scripts
- [`scripts/ts_diagnostics.py`](scripts/ts_diagnostics.py): autocorrelation and Ljung-Box, OLS with classical / White / Newey-West / Hansen-Hodrick standard errors and an overlapping-sum helper, Chow F test, BDE recursive-residual CUSUM,
  ADF t-statistic, fixed-width fractional differencing and minimum-d search, GARCH(1,1) MLE with kurtosis and multi-step forecast, VAR(p) by OLS with Cholesky and plain IRFs.
  `python scripts/ts_diagnostics.py --csv curve_par.csv --filter curve_id=USD-SOFR --filter start=0D --filter tenor=10Y --filter snap=eod_ny --horizon 5` prints the report for one canonical series (changes in bp);
  `--selftest` checks analytic and simulated known answers (white noise vs AR(1), HAC se `sqrt(LRV/T)`, overlap `h/sqrt(n)`, Chow F under H0, CUSUM size and power, FFD weights, GARCH recovery, VAR/IRF recovery) and exits non-zero on failure.
  It agrees with an independent statsmodels implementation for ADF, HAC, HC0, Ljung-Box, VAR and IRF.

## Related skills
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): OU fit, half-life, entry bands once stationarity is accepted
- [quant-cointegration](../quant-cointegration/SKILL.md): Engle-Granger, Johansen, spread construction
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): hedge regressions, rolling and Kalman betas, residual diagnostics
- [quant-regime-detection](../quant-regime-detection/SKILL.md): Markov switching, HMM, change points beyond the break tests here
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): EWMA/shrinkage covariances (multivariate counterpart of section 6)
- [quant-lead-lag](../quant-lead-lag/SKILL.md): Granger causality and cross-market transmission using VARs
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-scores that should use the vol and window chosen here
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): seasonal factors and calendar structure
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): AR/trend signals that must beat the persistence benchmark here
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): vol targeting from the forecasts in section 6
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro regressions whose errors need HAC and break checks
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): frac-diff as a feature, leakage, labeling
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): multiple testing, walk-forward, deflated Sharpe
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): clean series before any test
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used as inputs
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinkage, priors and Bayesian updating.

## References
- Hamilton - Time Series Analysis (Princeton University Press, 1994): ADF cases and numeric examples (GNP, T-bill), Kalman filter, Johansen, regime switching
- Tsay - Analysis of Financial Time Series (3rd ed., Wiley, 2010): ADF, HC and HAC formulas, OLS vs HAC rate-regression example, cointegration bands
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): fractional differencing, OU half-life, CUSUM, Chow-DF and SADF family, Parkinson constants
- Tuckman and Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): level vs change regression, AR(1) residuals, regression hedges and risk weights
- Greene - Econometric Analysis (8th ed., Pearson, 2018): Chow, Breusch-Godfrey, Ljung-Box, Durbin-Watson limits, spurious regression
- Wooldridge - Introductory Econometrics: A Modern Approach (2nd ed.): Engle-Granger critical values, T-bill error correction, differencing rule of thumb
- Lehman Brothers, Fixed Income Liquid Markets Research - LMR Quarterly 2003-Q3: Macro-Awareness in Relative Value Trading (B. Tuckman, Oct 2003): Bai-Perron on curve relationships, regime-shift trap
- Salomon Brothers - Understanding the Yield Curve, Part 7: The Dynamics of the Shape of the Yield Curve (A. Ilmanen, R. Iwanowski, Feb 1996): CKLS and GARCH on rate vol, level dependence
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): OU/MVOU estimation, simulation-based error, short-rate fit pitfalls
- Dunis, Laws and Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003): GARCH forecasts, GJR, Markov-switching vol, Kalman betas
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): EWMA/GARCH/SV, Kalman mean models, MSE comparisons, GARCH data needs
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): GARCH(1,1) kurtosis, realised vol, Sharpe standard error, vol loss functions
- Hasbrouck - Empirical Market Microstructure, teaching notes (NYU Stern, 2004): MA/Wold, Roll, VAR/VECM/IRF, Cholesky bounds
- Bishop - Pattern Recognition and Machine Learning (Springer, 2006) and Murphy - Machine Learning: A Probabilistic Perspective (MIT Press, 2012): linear dynamical systems, RLS as Kalman, structural time series
- BofA Global Research - US Rates Primer: UST RV Primer (Zhang, Braizinha, Axel, 2 May 2022) and US Rates Watch: Monthly rates models (Braizinha, Craig, Apr and Aug 2025): sign-restricted BVAR, state-space fair value; US Rates Viewpoint: new UST macro framework (Oct 2024): dynamic factor model
- During - Fixed Income Trading and Risk Management (Wiley Finance, 2021): VAR impulse responses by era, seasonal extraction
- d'Aspremont - Identifying Small Mean Reverting Portfolios (arXiv, 2008): predictability portfolios, out-of-sample cost hurdle
- swapsball.net - Regression in finance: friend or foe? (Oct 2017): level vs change, hedge calibration and validation
- Burton, Dektor and Wheeler - Time Series Prediction of US Swap Rates (Stanford University student project paper, c.2008): AR, rolling-OLS and PCA-residual Sharpe ratios on US swap changes
- Barclays Research - Global Rates Weekly: The urgency question (2 Oct 2026): AR benchmark nowcast with out-of-sample RMSE
- Grinold and Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999); James, Witten, Hastie, Tibshirani, Taylor - ISLP (Python ed.); Shalizi - The Truth about Linear Regression (draft, Oct 2025); Gelman et al. - Bayesian Data Analysis (3rd ed., 2014); Ross - Introduction to Probability Models (10th ed., 2010): data-mining arithmetic, correlated errors, optimism and selection, posterior predictive checks, overlap autocovariance
- Brown, Durbin and Evans - Techniques for testing the constancy of regression relationships over time (J. Royal Statistical Society B, 1975) (external): CUSUM boundary constants
- Bai and Perron - Computation and analysis of multiple structural change models (J. Applied Econometrics, 2003) (external): multiple break dating
- Newey and West - A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix (Econometrica, 1987) (external): Bartlett-kernel HAC
