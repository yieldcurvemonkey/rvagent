# Regime classification methods (detail)

Companion to `SKILL.md`. Every number is cited inline as (Publisher, Title, Date). Where a figure is the
note-writer's arithmetic or a house default, it is labelled as such.

## 1. Curve-move regimes (level and slope of each move)

Definition used by the bundled script (`curve_move_regime`):

- front move `d_f`, back move `d_b` in bp over the window (2y and 10y unless stated)
- level move `L = (d_f + d_b) / 2`, slope move `S = d_b - d_f`
- bull-steepening: L < 0 and S > 0; bear-flattening: L > 0 and S < 0
- bull-flattening: L < 0 and S < 0; bear-steepening: L > 0 and S > 0
- a move with max(|d_f|, |d_b|) below 2 bp is "below threshold" and excluded from shares

The 2bp floor follows the source practice of counting only moves above 2bp (Willer and Saunders,
Trading Global Macro Markets, 2026). Shares are taken over directional moves only, so the four shares sum to 1.

Window and reporting: 2-week, 1-month and 2-month windows, reported as shares of directional moves
(BofA, US Rates Viewpoint: Understanding the yield curve dynamic, 23 Jul 2025).

Mapping of the four regimes to drivers (BofA, Understanding the yield curve dynamic, 23 Jul 2025):

| Move type | Typical driver | Typical cycle phase |
|---|---|---|
| bull-steepening | front-end/Fed-led, pricing cuts or a hard landing | recession, front-loaded easing |
| bear-flattening | front-end/Fed-led, pricing hikes | reacceleration, hiking |
| bull-flattening | back-end/belly-led slowdown while the Fed is restrictive | late cycle |
| bear-steepening | back-end supply or early-cycle recovery with the Fed anchored | early cycle, supply pressure |

Derived gauges (same source):

- **Fed footprint** = share(bull-steepening) + share(bear-flattening). Lower share means fewer front-end-driven moves.
- **Tail proxies** count only "material" moves (daily move larger than the standard deviation of daily moves).
  Material bull-steepening frequency is a recession-likelihood proxy; material bear-flattening frequency is a
  reacceleration proxy. Three-month window.
- **Conviction gauge**: the source scales dispersion of the four shares from 0 (equal shares) to 1 (one type at
  100%) and gives no formula. The script uses 1 - H/ln(4), with H the Shannon entropy of the shares. This is a house
  default; it only fixes the endpoints. Low conviction means tactical, nimble positioning; high conviction means a
  structural stance.

Worked numbers (BofA, Understanding the yield curve dynamic, 23 Jul 2025). 2s10s move-type shares
(bull-steep / bear-flat / bull-flat / bear-steep):

| Window | Bull-steep | Bear-flat | Bull-flat | Bear-steep |
|---|---|---|---|---|
| 2 weeks | 11% | 13% | 32% | 44% |
| 1 month | 19% | 23% | 24% | 34% |
| 2 months | 23% | 18% | 33% | 27% |
| 3 months | 20% | 20% | 30% | 30% |

Same source: reacceleration probability near 15% and recession probability near 10% at that date. Over the
2 months, Fed footprint = 23% + 18% = 41%.

Historical share (US, 2y above 1%, Willer and Saunders, 2026): bear-flat 32.8%, bull-steep 31.4%, bear-steep 18.0%,
bull-flat 17.9%. About 36% of counted moves are "off-script" (bear-steep or bull-flat). The source classifies on the 2y move only and counts it
above 2bp, so the base rate is not like-for-like with the script's average-level rule. Use it as a rough base rate
before reading a shift in shares as a regime change.

Front-end linkage (Willer and Saunders, 2026): daily 10y changes regressed on a front-end rate (March 2022 to
March 2025) had beta 0.9 and R-squared just under 0.91. Hikes bear-flatten and easing bull-steepens. The 1s2s
spread is uncorrelated with the other spreads (correlation -0.17 to 0.01), so it is a separate risk, not a
proxy for the curve.

Daily diagnosis (GMM, STIR application process, 25 Feb 2026): ask where (front = meeting risk, belly =
uncertainty, long end = term premium), how (parallel, twist, belly vs wings) and why (policy-path repricing,
growth/inflation outlook, term premium/supply/positioning). Three recurring repricings: cuts removed (front end leads
a flattening, do not fade early), terminal higher (belly leads, aftershocks), duration grab (long end rallies most;
check whether real yields or breakevens drive it). Pick one invalidation condition.

## 2. Level regimes: 55-day moving average with a 1-day lag

House method in the cited book (Willer and Saunders, 2026): the driver is above or below its 55-day moving average,
the signal is lagged one day (two when a leg trades in another time zone), and the 200-day average is the slower
trend filter. The script's `above_ma_flags(x, window=55, lag=1)` implements the lag.

Two-year and ten-year levels vs their 55-day averages give a level regime (Citi, Messi Theory of Interest Rates, 31 Jul 2026).
Names used by the source: steepening, bear steepening, bull steepening, twist steepening. Twist steepening (2y
below and 10y above their averages) was about 6.6% of days in 1980-2026 by chart read, so its statistics rest on a
small sample. The source states the level regimes are concurrent, not predictive.

Do not mix the two definitions. A move regime says what the curve did over a window. A level regime says where the
yields sit against their trend. A bull-steepening move can happen inside a bear-steepening level regime.

Percentile thresholds must use rolling or expanding windows. The authors "avoid like the plague" full-sample
percentiles (Willer and Saunders, 2026). Examples in the source: 12 months for a yield pickup, 2 years for flows,
rolling 30 years for valuation.

## 3. Growth/inflation quadrants and their replacements

Quadrant definition (Citi, Quantitative Framework for Regime Investing, 29 Oct 2021):

- growth = year-on-year change in a leading indicator, averaged with the ISM manufacturing PMI (timely, not revised)
- inflation = G7 CPI year-on-year
- both z-scored over a rolling 10-year window; threshold z = 0
- low growth/low inflation = recession; low growth/high inflation = stagflation; high growth/low inflation = goldilocks;
  high growth/high inflation = overheating
- early vs late recession: growth below its 3-month average = early (classic risk-off; bonds outperform); above = late
  (equities and credit strongest)

Limits (Citi 2021; Willer and Saunders 2026):

- near-trend readings are classified almost at random, and the labels ignore transitions
- Aug 1996 had CPI z = -1.02 and leading indicator z = -0.03, which the quadrant calls recession. Its 60 nearest
  neighbours sit near the origin and straddle goldilocks (Citi 2021).
- hidden Markov models lose interpretability and "struggle to estimate out-of-sample or across training windows"
  (Willer and Saunders, 2026).

Replacements in the sources:

**K-nearest neighbours (analogs).** Seven variables: growth level, inflation level, financial conditions, risk appetite
(implied or realised vol), plus the changes in growth, inflation and financial conditions, all z-scored. Take the
Euclidean distance from today to each historical month, keep k = 60 nearest (five years of monthly data), and
average next-month returns across them. The sources give no kernel. House default: inverse-distance weights over
the 60 nearest, and always print the nearest dates so a human can check them. Compare with the unconditional Sharpe.
Analogs cluster in recent months, which biases the output toward regime stickiness (Citi 2021).

**Cluster model (10 clusters).** Inputs, all z-scored: G7 inflation, G7 leading indicators, G7 CPI 3-month change,
leading-indicator 3-month change, cross-asset vol, financial conditions, financial-conditions 3-month change
(Citi, Regime Model update, 13 Apr 2026). Clusters are persistent: a full recession moves next to stagflation or a
growth shock, while "normal" can move to many states. From a tightening-financial-conditions state, about 7% of
transitions go to stagflation and about 8% to a growth shock, where bonds outperform (same source). The
centroid table is in `references/scenario_examples.md`, section 6.

**Country upgrade (2026).** Inflation = headline CPI, lagged for publication delays, blended with 1y or 2y inflation
swaps or breakevens. Growth = manufacturing PMI (from 1992, OECD leading indicators as historical fill). Vol = blend
of equity realised vol, equity implied vol, oil vol, MOVE and FX vol. Financial conditions = a national financial
conditions index with its 3-month change. Equal weights, chosen for robustness (Citi, Regime Model update, 12 Aug 2026).

**Volatility-dispersion 2x2.** Vol score: an inverse-vol-weighted basket on 3-year vols, its 3-month realised vol,
log-transformed, z-scored against a rolling 5-year history. Dispersion score: each asset's daily return divided by its
3-year vol, the daily cross-sectional dispersion, smoothed with a 63-day EWMA, z-scored the same way. Four regimes
(high or low on each). The source applies it to commodities only (Citi, QIS Commodity Regimes, 20 Aug 2026). Its
use for rates (aggregate vol vs cross-tenor dispersion) is an extrapolation and must be tested. Most strategies were
weak in low-vol, high-dispersion states in that study.

## 4. Markov-switching models (Hamilton)

Model with N regimes (Hamilton, Time Series Analysis, 1994):

    y_t = c_{s_t} + phi_{s_t} * y_{t-1} + e_t,   e_t ~ N(0, sigma^2),   s_t a Markov chain with matrix P

Filter (row-stochastic P, P[i, j] = Pr(s_{t+1} = j | s_t = i)):

    xi_{t|t} = (xi_{t|t-1} * eta_t) / sum(xi_{t|t-1} * eta_t)
    xi_{t+1|t} = xi_{t|t} P           (m-step forecast: xi_{t|t} P^m)
    log L = sum_t log sum(xi_{t|t-1} * eta_t)

eta_t is the vector of regime densities; `*` is elementwise. Start from the stationary distribution of P, which the
script's `stationary()` computes.

Expected duration of regime j = 1 / (1 - p_jj) periods. Hamilton's U.S. real GNP example, 1952-84 (quarterly):
p11 = 0.90 and p22 = 0.75 give expected durations of 10 quarters (expansions) and 4 quarters (contractions). The
filtered probabilities matched NBER recession dates; the dates were not used in fitting.

Estimation: EM. The transition probability p_ij is expected i-to-j transitions over expected time in i. The smoother
(Kim) is xi_{t|T} = xi_{t|t} * {P [xi_{t+1|T} / xi_{t+1|t}]} with the row-stochastic P above (Hamilton's column-stochastic P gives P'), computed backward. It uses the full sample.

Pitfalls (Hamilton, 1994):

- the standard likelihood-ratio test cannot choose the number of regimes, because nuisance parameters are not
  identified under the null. Use Davies, Hansen or Andrews-Ploberger bounds, or out-of-sample checks.
- the likelihood is singular in some parameter regions. Restart from several starting values or impose priors.
- smoothed probabilities use future data, so they cannot drive a live signal. Use filtered probabilities.
- a permanent break is an absorbing state; the model still forecasts before the break, but the state never returns.

## 5. Regime-dependent relationships (what breaks and how to check)

- **Regime-split regressions.** 5y5y US CPI swap on Brent: 31 Jul 2023 to 27 Feb 2026, y = 0.8743x + 186.5
  (R-squared 0.64); 27 Feb 2026 to Aug 2026, y = 0.0832x + 232 (R-squared 0.08). Attributed to hawkish Fed
  communication anchoring forward inflation (JPMorgan, Monthly Inflation Outlook, 13 Aug 2026). The relationship did
  not survive a regime change, and the R-squared fell from 0.64 to 0.08.
- **Model regime breaks with dummies.** Model a break year with a dummy plus interaction terms instead of dropping
  it. Use long- and medium-window fits together (Citi, Japan FX: recent changes in USD/JPY price formation, 15 Jun 2026).
- **Stock-bond correlation.** Regression of one-year SPX-Treasury correlation on core CPI year-on-year: y = 7.43x -
  0.23, R-squared 0.22 (Willer and Saunders, 2026). The authors' rule is a 2.5% core CPI threshold: below it the
  correlation is mostly negative, above it mostly positive. The printed fit crosses zero near 3.1%, above the authors' 2.5%
  rule of thumb, so the threshold is a rounded judgement, not a fitted cut-off. The relation is "not as stable as we would like" (same source).
- **Equity-bond beta.** 3-month beta of the 10y yield to daily SPX percentage change: y = 257.09x - 0.51 (R-squared
  0.18), about 2.5bp per 1% SPX. Use the scenario as a rough mapping only (Citi, Deal or no deal, 10 May 2019).
- **Conditional volatility regressions (2y regime).** Regressing overlapping 3-month changes of 10y, 5s10s30s and
  5s30s on 3-month changes in 3m10y ATM vol, conditional on a 2y regime 0.5 standard deviations above (selloff) or below (rally) its historical mean over three months: R-squared mostly 0.05 to 0.48 (overlapping observations: t-statistics need HAC errors). Only the 5s10s30s fly was economically meaningful. Paying the fly was
  the best way to own vol in a selloff (Citi, A narrative shift looms, 17 Mar 2022). Implied betas from short windows
  (six weeks) are "hardly a template for the long run" (Citi, A narrative shift looms, 17 Mar 2022).
- **Correlation of steepeners with rates and vol.** One-month steepener P&L vs 1m change in 10y and 3m10y vol,
  conditioned on same-direction vs opposite-direction moves. For forward starts of 15 years or more, correlation is
  negative and mostly from same-direction regimes: "steepeners are more harmful in volatile selloff regimes than they
  are valuable in gradual rally regimes." The asymmetry largely disappears once the received 5y leg is hedged
  (Citi, Higher yields are here to stay, 24 Sep 2026).

## 6. Cycle and turning-point indicators

- **3m / 5y5y curve.** The 5y5y forward minus 3m rate is the preferred leading cycle indicator; inversion means
  over-tight policy. A recession model on it implied 37-45% probability of a cycle turn within 12 months (Mar 2019).
  In the three cycles then studied, a recession followed each time the model probability reached about 40%. From the
  first inversion to the first cut took up to 12 months; the curve reached 0bp in Mar 1989, Aug 2000 and Oct 2006
  (Citi, Vol cycle, steepeners and SOFR, 25 Mar 2019). MOVE was higher six months after the first inversion in all three
  episodes, and 2s10s was steeper one year later in all three (same source; Citi, Buying vol for less, 25 Sep 2019).
- **Eurodollar 1st-4th contract inversion.** Signal is the first date the 1st-4th contract slope turns negative in a
  tightening cycle. Event episodes May 1995, Dec 1997, Sep 2000, Mar 2006, Sep 2008. Four of five bull-steepened
  after the signal; 1y after the signal 2s10s was positive in four of five (Mar 2006 was -30bp). In Sep 2008 the 5s30s fell 52bp in three months.
  Cited: Citi, The rocky road to a steeper curve, 18 Jan 2019.
- **Inversion to first cut.** Willer and Saunders (2026): hit rates (cut within horizon) and average months to cut:

  | Inversion | 6m | 12m | 24m | Avg months |
  |---|---|---|---|---|
  | 3m10s | 39.1% | 52.2% | 100% | 10.3 |
  | 6m2s | 57.9% | 73.7% | 84.2% | 12.0 |
  | 2s5s | 53.3% | 73.3% | 93.3% | 7.7 |
  | 2s10s | 50.0% | 57.1% | 85.7% | 11.4 |
  | 10s30s | 55.6% | 72.2% | 94.4% | 8.4 |

  The source's pitfall: many results rest on fewer than 25 events. The source finds inversions forecast cuts more reliably than recessions.
- **Recession lead.** On average a recession is declared about 16 months after 2s10s inverts (Bassman, Dangerous Curves Ahead,
  15 Feb 2022; Sharp Curve Ahead, 25 Jan 2024). Since 1978 every 3m10y inversion was followed by a
  recession (Bassman, Never Different This Time, 29 Jan 2018). Use these as warnings, not timing tools.
- **Market-implied recession proxy.** Probability that the policy rate falls below 2.75% by June from STIR options,
  22% in August 2025 (JWS, USD Rates and Fed outlook, 21 Aug 2025). Stagflation caps the Fed's reaction to growth
  shocks, so the proxy can underprice recession.
- **Curve-percentile conditional returns.** Bucket 2s10s into deciles. In a daily study since 1971 restricted to
  days after a hike, the 0-10 decile preceded further flattening 10 to 20 weeks later in the 1989, 2000 and 2006
  cycles (Citi, What to expect when you're expecting a turn, 20 Apr 2018).
- **Fed cycle dating.** The dating algorithm (stated for the pre-1986 period) calls a hike (cut) month one where the rate is
  above (below) both prior months and the next quarter is higher (lower), excluding fine-tuning. Trading rules use post-1986
  cycles only, and the dating needs next-quarter data, so it cannot label the live cycle (Willer and Saunders, 2026). Post-1986: hiking median 12 months, eight hikes; easing
  median 8 months, four cuts (same source).
- **Final-hike micro-curve.** Systematic rolling steepener returns around the last five final hikes: "after the final
  rate hike the curve reaction generally flips with shorter-dated contracts flattening and longer-dated contracts
  steepening." The final hike is only known ex post, so this is a study, not a signal (Citi, Time for moderation, 17 Feb 2023).
- **Recession playbook timing.** Median 76 days from recession start to first cut; IG spreads widen about 124bp and HY
  about 785bp (median) in the same window (Willer and Saunders, 2026).

## 7. Macro fair value and cross-checks

Two-layer US framework (BofA, Introducing a new UST macro framework, 15 Oct 2024):

- Layer 1: dynamic factor model on 19 macro variables (inflation, growth, employment) gives four factors (broad,
  growth, inflation, employment). Claims, JOLTS and unemployment enter as minus z-scores. Calibrated over about 14
  years, weekly.
- Layer 2: regress the first two curve principal components on the four factors, the fed funds rate (cycle), the Fed
  balance sheet (non-economic buying) and the global yield (foreign demand). R-squared about 0.9 or higher. Rebuild
  2y, 5y, 10y, 30y from the fitted components. Residual standard deviation about 35bp at the front end and 20-25bp at
  the back end.
- Rich/cheap = residual in bp and in standard deviations; negative residual = rich.

Snapshot 11 Oct 2024 (same source): 2y residual about 20bp rich (-0.6 sigma), 5y about 15bp rich (-0.5 sigma), 10y
about 10bp rich (-0.3 sigma), 30y about 5bp cheap (+0.1 sigma). ISM/PMI sensitivity about 0.51-0.56% across 2y-30y (as
reported); inflation sensitivities fall with tenor, commodities rise with tenor.

Snapshot 22 Jul 2025 (BofA, Understanding the yield curve dynamic): 10y current 4.334%, fair value 4.31%, residual
+2.3bp, stdev 25.6bp, z 0.09; 30y current 4.901%, fair value 4.70%, residual +20.3bp, z 1.01. The 2s10s residual was
-3.8bp (z -0.16).

Rules for the model (same sources):

- a macro fair value model is linear and misses stress non-linearities. It is weaker during non-economic buying (QE,
  large FX-hedged foreign pickups). Pro-cyclical fiscal easing can show a larger supply beta than history.
- regressor choice and dimension reduction are critical; use 10-15 year windows; test PCA stability across 1m, 3m,
  6m, 12m windows.
- a +/-0.5 sigma residual is a tilt, not a signal.
- forwards are breakevens, not forecasts (Bassman, Sharp Curve Ahead, 2024): a forward 5s30s is not a predicted
  inversion.

Cross-checks (Nordea, EUR Rates Flash, 5 Feb 2020): PMI and equity-to-yield ratio fair values as a second opinion.
Do not use one fair value alone.

Four-predictor bond-return model (Salomon Brothers, Understanding the Yield Curve Pt 4, Aug 1995): term spread
(5y minus 3m), real yield (5y minus latest CPI), inverse wealth (equity-based risk aversion), momentum dummy.
In-sample R-squared 10.3% (1965-95 fit); monthly excess returns are about 90% unpredictable and forecasts are wrong
about 40% of months (same source). Use only as a prior.

## 8. Standard checks for any regime model

1. Point-in-time inputs. Revised leading indicators and publication lags change the answer; use release vintages
   (`macro_series` with `pub_ts_utc`).
2. Lag every signal one observation. Test sensitivity to a one-day lag. A rule that works contemporaneously but
   breaks with a one-day lag is not tradable (Willer and Saunders, 2026).
3. Rolling z-scores, checked over several windows (3 to 10 years). Expanding windows for forecasts.
4. Event studies drop overlapping triggers (a signal fired within the previous month is excluded). Standard holding
   period one month (22 trading days). Report sample size and hit rate in 20% steps.
5. Subsample by regime. A regime model that works in only one sub-sample is a regime bet.
6. Compare against the unconditional strategy with the same asset (active information ratio, computed over the days the
   rule is on, and % of time on).
