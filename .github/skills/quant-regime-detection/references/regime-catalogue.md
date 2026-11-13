# Published regime definitions, transition matrices and thresholds

Detail for [quant-regime-detection](../SKILL.md). Numbers are as printed in the cited documents. Where a value
was read off a chart, it is marked approximate. Transition matrices use rows = from state, columns = to state.

## 1. Transition matrices (persistence and expected duration)

Expected duration of state j = 1 / (1 - p_jj) periods.

**Citi growth/inflation quadrants, monthly** (Citi Research, Quantitative Framework for Regime Investing, 29 Oct 2021).
Some printed rows do not sum to 1. They are transcribed as printed.

| from \ to (levels) | Overheat | Goldilocks | Stagflation | Recession | duration (months) |
|---|---|---|---|---|---|
| Overheat | 0.88 | 0.06 | 0.01 | 0.01 | 8.3 |
| Goldilocks | 0.07 | 0.92 | 0.00 | 0.05 | 12.5 |
| Stagflation | 0.04 | 0.00 | 0.88 | 0.03 | 8.3 |
| Recession | 0.00 | 0.02 | 0.11 | 0.92 | 12.5 |

The 3-month-change quadrants have diagonals of 0.73 to 0.76, which is about 4 months. Off-diagonal values:
RG/RI to RG/FI 0.22; RG/FI to RG/RI 0.13 and to FG/FI 0.09; FG/RI to FG/FI 0.17 and to RG/RI 0.09; FG/FI to FG/RI
0.22 (G = growth, I = inflation, R = rising, F = falling). The authors' summary is that persistence is about 90%
for levels and about 75% for changes.

**BofA 4-state allocation framework (--, -, +, ++), next 1-2 quarters** (BofA Global Research, US Rates Watch:
Monthly rates models, 4 Aug 2025). Probabilities in %:

| from \ to | -- | - | + | ++ |
|---|---|---|---|---|
| -- | 21 | 7 | 21 | 50 |
| - | 18 | 21 | 46 | 14 |
| + | 12 | 32 | 48 | 8 |
| ++ | 0 | 25 | 55 | 20 |

The extreme states are not persistent at this horizon. "--" goes to "++" half the time, and "++" never goes
straight to "--".

**Citi k-means macro clusters, monthly** (Citi Research, Model update: A tale of two horizons, 8 Apr 2025; Regime
Model update, 12 Aug 2026). The clusters are persistent. A full recession always moves to stagflation or a growth
shock. "Normal" can move to many states. From "tightening financial conditions" the chain moves to stagflation about
7% of the time and to a growth shock about 8% of the time, and bonds outperform in the growth shock.

**Markov-switching estimates**

| Source | Series | Parameters | Durations |
|---|---|---|---|
| Hamilton, Time Series Analysis (1994), Table 22.1 | US real GNP, quarterly | mu_1 = 1.16, mu_2 = -0.36 %/qtr; p_11 = 0.90, p_22 = 0.75 | 10 and 4 quarters |
| Roche & Rockinger, in Dunis, Laws & Naim (eds) (2003) | USD/DEM daily, Oct 1995 - Oct 1998, 775 obs | sigma_high 0.6351, sigma_low 0.2486; p_00 = 0.8049 (high), p_11 = 0.6348 | 5.13 and 2.74 days |

The two-state persistence eigenvalue is lambda_2 = p_11 + p_22 - 1. It is 0.65 for GNP and 0.44 for USD/DEM. The
USD/DEM states flip within days, so they are a timing filter, not a regime for multi-week trades.

## 2. Rule-based regime definitions

| Definition | Recipe | Source |
|---|---|---|
| High-vol regime for UST futures | rolling 2y z-score of realised daily vol of the 30y on-the-run | J.P. Morgan, For cheap gamma, look to the long end, 23 Aug 2019 |
| Vol score | inverse-vol basket (3y vol window); current 3m realised vol; log; z-score vs rolling 5y | Citi, QIS Corner: Aggregate commodity regime indicators, 20 Aug 2026 |
| Dispersion score | each return / its 3y vol; daily cross-sectional dispersion; 63d EWMA; z-score vs rolling 5y | same |
| Vol x dispersion 2x2 | HighVol/HighDisp, HighVol/LowDisp, LowVol/HighDisp, LowVol/LowDisp | same |
| Trend regime | driver above or below its 55-day MA, signal lagged 1 day (2 days across time zones); 200dma as the slow filter | Willer & Saunders, Trading Global Macro Markets, 2026 |
| UST curve regime | 2y and 10y each vs its own 55dma. Bear steepening = both above. Twist steepening (implied) = 2y below, 10y above | Citi, The Messi Theory of Interest Rates, 31 Jul 2026 |
| Curve directionality indices | over rolling 6m, share of bp moves that are bull-steep, bear-flat, bull-flat, bear-steep; bear-flat + bull-steep = front-led | BofA, UST RV Primer, 2 May 2022 |
| Curve complexity | H = sum(e_i^2) / (sum e_i)^2 on eigenvalues of a rolling PCA of yield changes; 90 business-day window | Düring, Fixed Income Trading and Risk Management, 2021 |
| Early vs late recession | in the low-growth quadrant, growth indicator below its 3-month MA = early (bonds best), above = late | Willer & Saunders, 2026 |

Measured time shares and results:

- Citi UST curve regimes (approximate, read off a small chart): steepening ~45.5% of days, bull steepening ~21.4%,
  bear steepening ~17.3%, twist steepening ~6.6%.
- Düring's H ran roughly 0.57-0.95 for US and German spline yields over 2014-2020, and German H fell after the 2020
  Covid outbreak, so that curve became less single-factor. Across Japanese issuer curves at 5y and 10y, H ran
  roughly 0.3-0.95.
- Citi QIS: most strategies are weak in LowVol/HighDisp. Vol and dispersion are positively correlated, so that state
  is rare. The lesson for rates: aggregate vol can look normal while cross-market or cross-tenor dispersion stays high.
  The rates application is the note-taker's extension. The note itself covers commodities only.
- Willer & Saunders: US Treasury Sharpe by regime is about 1.8 in early recession, against about 0.15 in overheat
  (approximate, read off a chart). Bonds are weakest in "tightening financial conditions", where stocks, bonds and
  credit fall together. Core CPI above about 2.5% goes with a positive stock-bond correlation.

## 3. Factor-anchor regime (rolling PCA + regression)

Citi Research, Decomposing Global Rate Drivers Across EM Asia 5y5y (13 Aug 2026). Weekly Wednesday closes, a
rolling 52-week window, PCs signed so that each bloc's mean loading is positive, and fixed full-period loadings used
for the headline R² to avoid rank swaps.

- Chart thresholds (approximate): R²(bloc on USD) "strong" 0.70, "moderate" 0.50, "weak" < 0.10. R²(SGD/KRW on
  JPY) "meaningful" 0.30, "modest" 0.10, "weak" < 0.05. Incremental R² for CNY "meaningful" 0.03. Rolling t-stats are
  compared with 1.65 and 1.96.
- Jan 2023 break: R²(PC1 ~ USD 5y5y) was about 0.47 before and about 0.76 after. The full-period value of 0.59 hides
  both.
- Dropping the pegged HKD cut R²(USD) from 0.59 to 0.24. A mechanically linked series inflates the regime statistic.

## 4. Regime-conditional relationships in rates

- Citi Research, European Rates Weekly: Higher yields are here to stay (24 Sep 2026). EUR forward steepeners,
  factor correlation of 1m P&L by regime, received leg 5y5y vs paid 10y5y / 15y5y / 20y5y / 25y5y:
  - cheapening duration with rising vol: -0.60 / -0.66 / -0.62 / -0.58
  - richening duration with falling vol: -0.14 / -0.42 / -0.53 / -0.57

  The asymmetry is in the received 5y5y leg. "Steepeners are more harmful in volatile selloff regimes than they are
  valuable in gradual rally regimes."
- Citi Research, European Rates Weekly: A QT revolution (17 Sep 2026): "the well-documented inverse level/slope
  relationship is mostly a function of higher vol regimes".
- BofA Global Research, Global Rates Weekly: Start of rates bite (2 Oct 2026): a rates-vol spike "is causing a
  breakdown in some recent RV relationships & de-risking", seen as sharp swap-spread tightening against ASW wideners.
- J.P. Morgan, Impossible to walk in this muck (6 Mar 2020): stop out spread or steepener trades when vol
  regime-shifts, even if the thesis still holds. After a rally that suppresses implieds, a shift to higher vol makes
  price action brittle.
- Tuckman (Lehman, Oct 2003): 10y swap vol inside 45-day windows centred on estimated breaks was 7.3bp/day, against
  5.2bp/day outside. Fly hedge ratios themselves moved with the regime: the model's wings/belly DV01 ratio was 105%
  (Feb 2001), 108% (Sep 2001) and 112% (May 2003), and the 10s share of the wing DV01 was 72%, 72% and 50%.

## 5. Regime filters that changed a strategy's result

| Filter | Result | Source |
|---|---|---|
| EMA(50d) trend rule, position reversed when MS-filtered vol > threshold | 5.1% vs -1.6% p.a.; max DD 10.4% vs 19.4%; 253 vs 65 trades (incl. costs) | Roche & Rockinger in Dunis, Laws & Naim (eds), 2003 |
| QIS strategies by vol x dispersion regime | e.g. market-neutral curve carry IR 2.33 / 2.86 / 0.04 / 1.31 vs 1.90 unconditional (HH / HL / LH / LL; approximate) | Citi QIS Corner, 20 Aug 2026 |
| Headline sensitivity before vs after Apr-May 2025 | IQR of the 30-min 2y range about 6x larger in the first two months than later | J.P. Morgan, Comfortably numb, 24 Jul 2026 |

Evaluation convention (Willer & Saunders 2026): report the conditioned strategy's information ratio next to the
unconditional, always-on IR of the same asset, plus "% on", the share of time the filter is active. Thresholds come
from rolling windows. The authors "avoid like the plague" full-sample percentiles.
