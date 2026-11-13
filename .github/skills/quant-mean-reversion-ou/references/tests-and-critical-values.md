# Stationarity and mean-reversion tests: specs, critical values, power

Detail for the "Is it mean-reverting?" step of [SKILL.md](../SKILL.md). Code: `adf`, `kpss`, `hurst_std`, `variance_ratio` in
[`scripts/ou_fit.py`](../scripts/ou_fit.py) (ADF and KPSS statistics agree with the statsmodels implementations to 1e-6 in the self-test).
Cointegration versions (Engle-Granger, Johansen) are in [quant-cointegration](../../quant-cointegration/SKILL.md);
the general toolbox is in [quant-time-series-econometrics](../../quant-time-series-econometrics/SKILL.md).

## 1. ADF (null: unit root)

Delta x_t = alpha + beta x_{t-1} + sum_{k=1..p} gamma_k Delta x_{t-k} + e_t, H0: beta = 0, H1: beta < 0. The t-ratio has a non-standard
limit; the normal -1.65 over-rejects. (Wooldridge, Introductory Econometrics; Hamilton, Time Series Analysis, 1994.)

| Case | 1% | 2.5% | 5% | 10% |
|---|---|---|---|---|
| constant, no trend (use for rates spreads, flies, residuals) | -3.43 | -3.12 | -2.86 | -2.57 |
| constant + trend | -3.96 | -3.66 | -3.41 | -3.12 |
| no constant | -2.58 | | -1.95 | |
| Engle-Granger residuals, no trend (stricter, OLS makes residuals look I(0)) | -3.90 | -3.59 | -3.34 | -3.04 |
| Engle-Granger residuals, trend | -4.32 | -4.03 | -3.78 | -3.50 |

Rho form: T (rho_hat - 1) 5% critical values about -13.8 (case 2) and -21.0 (case 4) at T about 164 (Hamilton). Lags: choose by AIC on a
common sample (default max = ceil(12 (n/100)^0.25)), or start at a generous p and t-test the last lag; lagged-difference t-stats are
approximately standard so they can choose the lag. Monthly data: at least 12 lags. Too many lags cut power; too few distort size.
Choose the deterministic case to match the question: for a spread with a stable mean use the constant case, not the trend case.
The ADF t needs no correction for the lagged-difference terms. Phillips-Perron is the non-parametric alternative (Newey-West
long-run variance, Bartlett weights); it over-rejects with a large negative MA root.

## 2. KPSS (null: stationary)

Regress on a constant, cumulate residuals E_t, KPSS = sum E_t^2 / (T^2 s^2) with a Newey-West long-run variance s^2 (lag about
12 (n/100)^0.25; Newey-West lag rule of thumb about T^(1/4)). 5% critical values 0.463 (level), 0.146 (trend); level: 10% 0.347,
2.5% 0.574, 1% 0.739. (Greene, Econometric Analysis, 8th ed.) Use ADF and KPSS together: ADF rejects and KPSS does not = stationary;
the reverse = unit root; both reject or neither rejects = inconclusive, treat as weak.
**Size distortion (simulation by this skill):** at n = 3,000 the 5% KPSS test rejects a true OU about 5-8% of the time when the half-life is
1.7 obs (kappa 0.4) but about 18-25% of the time when the half-life is 14 obs (kappa 0.05) (two simulation runs), because the truncation lag is short relative to
the persistence. So a KPSS rejection on a slow residual is a warning, not a verdict; the diagnose report counts it as one reason only.

## 3. Variance ratio and Hurst

- VR(q) = Var(x_{t+q} - x_t) / (q Var(x_{t+1} - x_t)). Random walk 1; below 1 = mean reversion; above 1 = trending. For an AR(1) in levels
  VR(q) = (1 - phi^q) / (q (1 - phi)) (used as the self-test known answer: phi = e^-0.05, q = 10 gives 0.807). Plot VR for q = 1..30. Use the
  heteroskedasticity-robust Lo-MacKinlay z*, mandatory when vol regimes shift (front-end flies change vol about 10x between zero-rate and
  hiking regimes). Intuition: perfect trend two-period variance 4 r^2, perfect reversion 0, random mix 2 r^2. The statistic is not reliable unless
  q is much smaller than T. Weaknesses: no rule for choosing q; offsetting autocorrelations can read VR about 1. (Hamilton; Dunis, Laws and Naim, 2003, ch.2; Hasbrouck, 2004.)
- Two-horizon form V_{M,N} = [Var(x_t - x_{t-M})/M] / [Var(x_t - x_{t-N})/N]; microstructure noise gives V > 1 for M < N.
- Front-end gauge: ratio of 3-month realised vol from daily changes vs from monthly changes divided by sqrt(21), compared across
  contract packs and dates. (J.P. Morgan, US Fixed Income Markets Weekly, 3 Aug 2018.)
- Hurst (standard-deviation method): H = slope of log std(x_{t+l} - x_t) against log l, l from 2 to about n/4 (cap 100). Random walk 0.5; below 0.5
  mean-reverting; above 0.5 trending. A previous implementation that returned 2 x slope read H = 1.035 on a random walk: always run a
  random walk through any Hurst/VR code first. A pure drift cancels in differences only after detrending.
- Citi (2015) front-of-curve gauge: MR = |1-month change in rate (forward-adjusted)| / stdev of rate levels over the month; lower = more mean-reverting;
  window 4 weeks. Realised vol from overlapping 1/2/3/4-day changes: lower at longer horizons means reversion.

## 4. Power and the practical reading

- Unit-root tests have low power near rho = 1: US T-bill (quarterly, 1948-89, T = 164) rho_hat = 0.969, ADF t = -1.66 vs -2.89, ADF rho -5.74 vs -13.8:
  unit root not rejected even with 41 years of data. At rho = 0.9 the 10-period autocorrelation is about 0.35 yet small samples cannot tell 0.9 from 1.
  A fail-to-reject is not acceptance; "the goal of unit root tests is to find a parsimonious representation that gives a reasonable approximation".
  (Hamilton 1994; Wooldridge.) Real-rate example: rho_hat 0.97124, ADF t -2.04, PP Z_rho -6.35; the impulse response at lag 36 is 0.27, i.e. 27%
  of a shock remains after 3 years: use the IRF to describe how long a deviation persists.
- OLS AR(1) coefficient is biased downward near 1 and superconsistent under a unit root; the conventional t rejects gamma = 1 too often (Greene).
- Informal I(1) rule: first-order autocorrelation above 0.9 (some use 0.8) suggests differencing (Wooldridge). For a residual that you want to
  fade, the opposite use: phi below about 0.95 per day is the region where reversion is observable in a year of data.
- Small-sample half-life bias (simulation by this skill, n = 250 daily obs, 300 draws, true half-life -> median estimate, 10-90% range):
  5 -> 4.7 (3.4-6.2); 11 -> 9.1 (5.8-13.7); 20 -> 14.0 (8.2-25.3); 40 -> 20.9 (10.9-43.8); 60 -> 24.0 (11.9-58.6). Slow reversion is read as faster than it is.
  Do not trust a half-life above about n/6 from one fit; use the CI and rolling stability.
- Tests disagree: a pair passed 4 of 6 unit-root tests (ADF p 0.0049, PP 0.0058 but ERSD 0.531, SPR 0.384; Palomar 2025); residual-based Engle-Granger
  and Johansen can conflict on the same data (Hamilton). Never rely on one test. Correlation is not cointegration: two series with return correlation
  0.66 were not cointegrated (half-life 70 days, ADF p 0.27).
- Level regressions on autocorrelated series are meaningless (two independent random walks give high R^2; 1y vs 3y Treasury levels R^2 96.5% but not
  cointegrated; naive t 107.9 falls to 39.9 with HAC errors). Use Ljung-Box, not Durbin-Watson, and HAC t-stats. (Tsay, Analysis of Financial Time Series, 2010.)

## 5. Contaminants that fake or hide reversion

- Bid-ask bounce gives negative lag-1 autocovariance, inflates short-horizon variance, pushes VR above 1 at short horizons and can make a random walk look
  stationary when costs are large relative to vol. Clean or model before testing traded prices. (Hasbrouck, 2004.)
- Over-differencing: a stationary series differenced "to be safe" has a non-invertible MA root; ADF on log price -0.34 vs returns -46.9 (95% critical -2.86)
  but the fractionally differenced series crossing the critical value near d = 0.35 keeps correlation 0.995 with the original vs 0.03 for returns.
  Test levels first; use the minimum fractional d if a series is mildly non-stationary. (Lopez de Prado, Advances in Financial Machine Learning, 2018.)
- Overnight / cross-session gaps: do not chain them into one model; treat each session separately. Cross-time-zone legs need a common snap or weekly closes.
- Structural breaks reset everything: CUSUM on recursive residuals, Chu-Stinchcombe-White CUSUM on levels (critical value sqrt(b + log(t-n)), b = 4.6 at 5%),
  supremum ADF (SADF) of rolling-start ADF with H1 beta > 0 (explosive), robust variants QADF/CADF when the supremum is outlier driven. A break from
  reversion to momentum "offers some of the best risk/rewards" but only if you are on the right side. Re-estimate only on the post-break sample.
