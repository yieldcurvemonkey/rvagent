# Positioning, trend-follower flows and calendar priors

Companion to [SKILL.md](../SKILL.md), Method 7 and Method 6. Lines marked **(adaptation)** are this skill's reading, not the
authors'; **(computed)** lines are arithmetic on printed numbers. Source is named in each section.
Signs: the US 10y calendar tables are bp changes of a YIELD, so up = bearish duration. The dollar-index tables are % changes of a price. FX-derived statistics are
untested on rates; they are method templates and priors, not rates evidence.

## 1. Replicating CTA duration and curve positioning (BofA, CTAs impact on the rates market, 18 Aug 2020)

Target: a benchmark CTA index (an equal-weighted index of 20 large CTAs open to new investment). The index has survivorship bias.

Method (top-down rolling regression on principal-component features):
1. Cluster assets hierarchically and pick a representative set per asset class (equity clusters: US fundamentals, broad DM, EM-biased). Assets in one cluster carry overlapping information.
   Sets: equities, longer-duration bonds, shorter-duration bonds, metals, energy, FX. Broad benchmarks are rejected: too broad, their rebalancing rules interfere, and they hide long/short bias.
2. Take only the first principal component of each set as the feature. Higher eigenvectors are unstable and would destabilise the betas; a low dimension needs less data, so the features react faster.
3. Rolling OLS of CTA index returns on the six features over a 2-month window (fast betas without too much noise). Project the feature betas back to individual assets through the inverse PC1 transform.
   Variant: replace the FX feature with the dollar index (already to some extent an eigenportfolio); average R-squared was 66% on 2-month windows since 2015, better than the FX-PC version, so it was used.

Reading rates positioning from the betas:
- The long-duration beta gives the long/short duration bias.
- Long-duration beta against short-duration beta gives the steepener/flattener bias: long the long-duration feature and short the short-duration feature is a flattener.
- Long-duration betas are more stable; short-duration betas are more volatile and depend on the policy path.
- Flow signal: week-on-week (the chart uses bi-weekly) changes in the betas. Duration is first order, the curve second order.
- Beta z-scores: over/underweight against the average 3-month beta. An index of significance across the individual-asset betas reads +1 or -1 when all assets are over/underweight at 1.5 sigma.

Validation:
- Against a multi-crossover momentum signal (several crossovers with different time decays; parameters not given): significant correlation for equities, the 10y Treasury and crude oil; lower for gold (the metals feature mixes base and precious metals); lowest for the dollar index (dollar momentum is already in the other features). Lead-lag about 15-20 days at maximum correlation.
- Against CFTC data: the 10y beta trend correlates about 60% with net non-reportable 10y futures positions; next is other reportable at only 20% (commercial, non-commercial, institutional and leveraged funds were also tested). Absolute levels and long/short implications do not match.

Dated reads: 2016 long duration plus flatteners (Fed tightening while neutral-rate expectations were being cut), then a shift to steepeners after the election (fiscal and regulatory easing); 2019 flattening bias captured (neutral-rate downgrade, bullish inversion).
Early 2020: the betas decayed in the late-1Q dash for cash (Treasuries and gold sold), which supports the short 2-month window. At publication (Aug 2020): long-duration bias since February, last meaningful build of longs the week of 10 July, longs lightening in early August;
curve bias switched from bull steepening to a slight flattening in late March, peaked 24 July and was trimmed from early August. CTA AUM peaked at about $360bn in 2013 and fell below $300bn in 2020, about 95% of it systematic.
Limits: increasingly diverse quant models limit how much a top-down average CTA can capture; bottom-up replication (a set of trend rules of different lengths) gives more detail but depends on approximations.

## 2. Trend-follower stop-out ensemble (BofA, Systematic Flows Monitor, 2 Jun 2025)

Four parameters matter most for a CTA proxy: the investment universe, the trend lookback, position sizing or risk budget, and risk management including stop-loss rules. The benchmark index was tracked well with a broad cross-asset futures universe, a medium-term lookback, risk-parity sizing and a moderately aggressive stop-loss.

| Block | Definition |
|---|---|
| Short-term trend | a collection of moving-average crosses from 21 to 100 trading days |
| Long-term trend | crosses between 50 and 252 trading days |
| Medium-term | equal weighting of the short and long windows |
| Output | an allocation in z-score terms per market (maximum 10% per asset in the model), not an absolute allocation |
| Stop-loss | a prescribed loss from a high-water mark stops the position out entirely; over the long run the stop level hardly changes performance (stops are rare, positions unwind anyway as the trend reverses) |
| Ensemble | 3 lookbacks x 4 stop thresholds = 12 models (the four threshold values are not given) |
| Correlation | EWMA with lambda 0.97, data from 31 Dec 1999 to 29 May 2025 |
| Sigma move | daily return divided by the prior day's prevailing realised vol (de-annualised); vol = EWMA, lambda 0.97 |

Rules and diagnostics:
- The impact is greatest when the average allocation across models is high and similarly positioned, and a reversal trips many stop thresholds at once. The potential flow is larger from unwinds than from accumulation.
- Rule: on days when at least 4 of the 12 models stopped out, the absolute sigma move was above the full-sample average, and the market typically moved beyond the stop-out triggers. The monotone pattern (more stops, larger absolute sigma move) held for the 10y Treasury future and the Bund future as well as equity index, commodity and FX futures, 2010 to May 2025. Three stop-outs can come with large moves but not reliably; four is the empirical threshold (shown for the S&P 500 future).
  Equity-index evidence: of the 15 largest one-day sigma declines since 2010, 9 coincided with CTA stop-loss unwinds; fundamental-stress days (the Aug-2011 downgrade, the Feb-Mar 2020 Covid sell-off, Apr 2025) were the exceptions.
- Model-consensus diagnostic: the average pairwise EWMA correlation among short, medium and long models; low means dispersion in trend-follower positioning (it hit the second-lowest on record the day after the 3 Apr 2025 tariff shock).
- Speed shift: around 2013-14 the correlations of the short-term and long-term models to the benchmark flipped. Before 2013 the short-term model was more correlated; since then the long-term model has been more stable: CTAs shifted to longer trends. The medium-term model is the most stable overall.
- Listed-fund validation: US-listed CTA funds with data back to start-2015 and correlation to the benchmark of at least 0.7 gave 14 funds (about $13bn AUM); each correlated at least 0.68 with at least one model, and 10 of 14 were most often closest to the medium-term model.
- Projected paths and unwind triggers: bear, median and bull paths are the 2.5th, 50th and 97.5th percentile historical 5-day return paths at current vol; the 12 trigger levels are shown as a range, only if they fall inside the forecast 5-day path.
- Context: CTA hedge-fund AUM was $339.4bn at 2024-Q4, with leverage often above 3x AUM in gross notional.
- Limits: real CTAs differ in universe, lookback, risk target and stop aggressiveness, so outputs are proxies; monitor a range of lookbacks and stops. A medium model alone may suffice for monitoring, consensus across all gives conviction.
- **(adaptation)** Use as a level overlay: find the price where the long-lookback and medium-lookback models change sign and where stop thresholds cluster, and treat the stretch between them as the unwind-risk zone for the futures contract. Do not fade positioning by default (see SKILL.md Method 7).

## 3. Commitments of Traders as a contrarian and trend-change flag (BofA, Technicals Explained, 14 Jan 2025)

- Data: the weekly breakdown of Tuesday open interest, for markets where 20 or more traders hold positions at or above the reporting level; released Friday 15:30 New York for the Tuesday data, later around holidays (`positioning`: `date` is the position date, `pub_ts_utc` the release). A signal needs the release time, a three-day lag.
- Legacy report: commercial = hedgers, non-commercial = speculators. Signal: speculators' net position as a percentage of open interest. Extreme readings, the example being beyond 2 standard deviations from the mean, are contrarian: an extreme long is bearish and an extreme short is bullish.
- Combine with the price trend and technical indicators. A divergence between the price trend and the positioning trend can flag a coming trend change ("when market participants get too long or short, there is a greater risk of a correction or trend change").
- Categories the authors find most useful for warning of reversals: net non-commercial, plus managed money in the disaggregated commodity report, and asset manager and leveraged funds in the financial-futures report. These groups are large or build positions quickly in a trend, so adverse surprises force fast exits and strong reversals.
- Worked example (gold, not rates): in Dec 2015 gold bottomed with positioning the shortest in many years, then broke out from just below 1100 to 1400 while positioning stretched long. After a two-year range, positioning was even shorter than in 2015 but at higher prices: a positive divergence that, with a large rounded base, suggested significant upside.
- Rule for this skill: positioning extremes are best used with price-trend confirmation, not alone (see flow-positioning-cftc-and-surveys for the Treasury and Bund series).

## 4. Positioning triad: moving-average aggregator, up/down vol, residual skew (BofA, FX Quant Primer, 1 Oct 2018)

FX-derived. The statistics below are FX; the construction ports to a futures price. The rates version of the skew leg is **(adaptation)**.

**MAA (moving-average aggregator).** The percentage of 28 binary MA-cross signals that are bullish.
- Eight series (the price and its 5, 10, 20, 30, 50, 100 and 200-day moving averages), compared in all C(8,2) = 28 pairs. 100% means all 28 bullish; 50% means 14 of 28.
- Trend labels: uptrend if MAA above 60, downtrend if below 40. The authors say it measures trend maturity and correlates closely with speculative CFTC positioning.
- `ma_aggregator` in `scripts/tech_indicators.py` counts a pair as bullish when the shorter-horizon series is above the longer-horizon one (ties are not bullish): an implementation choice.
- Breadth versions add +1 per pair in uptrend and -1 per pair in downtrend: the dollar against 9 G10 pairs (range -9 to +9), against EM, the yen against G10, and a monthly dollar against 29 majors with overbought and oversold lines near +/-29.
  **(adaptation)** For rates, the breadth version is the number of markets or tenors in uptrend against downtrend (for example 2y, 5y, 10y and 30y futures, or the G10 10y yields in price terms).

**Up/down vol (UD).** The spread of realised vol between up days and down days over the past month.
- `Raw U/D = 100 - 100 / (1 + UP/DOWN)`, with UP and DOWN the realised vol on up days and on down days over a common rolling 1-month window.
- `UD% = 100% - (1-year percentile of Raw U/D)`. The inversion makes low values mean light positioning.

**Residual skew (RS).** Regress weekly changes in the 1-month 25-delta risk reversal (as % of at-the-money vol) on weekly spot changes over a 6-month rolling window; take the normalised cumulative sum of the residuals over the last month and its 1-year percentile.
Low = light positioning, excess call demand; high = excess put demand, stretched longs. The authors say RS is "not systematic".
**(adaptation)** For a rates future use the 25bp risk reversal from `vol_surface` (`nvol_bp` payer minus receiver, expiry 3M, tenor 10Y, as in SKILL.md Inputs) against weekly changes in the yield, and keep the sign: payers (yield-up demand) rising faster than the yield explains is bearish-price positioning.

**Combined reading.** High (low) UD and/or RS together with high (low) MAA means positioning is affecting price and a reversal is likely.

| Trend | Reversal likely | Reversal unlikely |
|---|---|---|
| Uptrend | MAA, UD and RS all above 80 | UD and RS below 50 |
| Downtrend | MAA, UD and RS all below 20 | UD and RS above 50 |

Statistics (FX, 9 G10 USD pairs, one week ahead unless stated; the wording of the UD lines is as extracted and is not fully clear):
- Extended uptrends (MAA above 60) gain strength a week later only about 44% of the time; extended downtrends (MAA below 40) bounce 55% of the time.
- UD with 80% and 20% cut-offs: the bullish UD bounces 55% of the time and the bearish UD 42% (the text also prints 58% for the bearish side).
- Uptrend with up vol: 52% gain strength, against 44% with the trend alone. Uptrend with down vol: 40%. Downtrend with up vol: 60% bounce. Downtrend with down vol: only a 48% bounce chance.
- The authors' summary: stretched trends tend to be supported when the direction of volatility agrees with the trend, and to revert otherwise.
- FX cases: 21 Aug 2018, a cross with MAA 4% and UD and RS at the 0th percentile, read as a bullish reversal; 31 Jul 2018, a bearish continuation with elevated RS; a pair in uptrend with MAA 96, UD 90 and RS 11, read as medium reversal risk.

**Momentum persistence (FX).** The sign of the spot change over lookbacks of 0.25 to 12 months against the direction over the next 1 to 52 weeks; 9 G10 USD pairs since 2000, about 40,000 daily observations, t-test against a 50% null.
52% of medium-term G10 trends continued another month; a 4-month EURUSD trend persisted 4 more weeks 54% of the time (95% interval 53.6% to 56.5%, midpoint 55%). Trends from 4 to 6 months back persist for 1 to 4 weeks and start to mean-revert after about 2 months; the peak t-statistic is 8.9 (5-month lookback, 4 weeks ahead).
Momentum is moderate and decays; extended positions are more sensitive to opposite shocks.

## 5. US 10y yield and dollar index calendar priors (BofA, Technicals Explained, 14 Jan 2025)

General calendar and seasonality screens belong to quant-seasonality-and-calendar-effects. These are the primer's own tables, kept here as soft priors for timing. The primer's tables have no significance tests and no unconditional base rates; one observation per year; 61 years for the 10y.

**US 10y yield, bp changes (since 1963, 61 Januarys).**

| Test | Cells (count, share, averages in bp) |
|---|---|
| January change | up 33 times (54%), average +20, median +13; down 28 times (46%), average -23, median -18; all Januarys average 0, median +1 |
| January, then Feb-Mar | up then up 23 (70%): Jan +20, Feb-Mar +34, Q1 +54. Up then down 10 (30%): +19 / -36 / -17. Down then up 17 (61%): -21 / +33 / +13. Down then down 11 (39%): -27 / -34 / -61 |
| January, then Feb to year-end | up then up 20 (61%): Jan +22, Feb-YE +83, year +105. Up then down 13 (39%): +17 / -94 / -78. Down then up 12 (43%): -23 / +85 / +63. Down then down 16 (57%): -23 / -89 / -112 |
| First 5 days | up 34 times (56%), average +13, median +8; down 27 times (44%), average -9, median -7; all years average +3, median +3 |
| First 5 days, then rest of January | up then down 22 of 34 (65%): first-5 +12, rest -17. Up then up 12 (35%): +13 / +23. Down then up 14 (52%), down then down 13 (48%) |
| First 5 days, then rest of Q1 | up then up 21 (62%), average +42; up then down 13 (38%), -50; down then up 14 (54%), +41; down then down 12 (46%), -29 |
| First 5 days, then rest of year | up then up 18 (55%), +76; up then down 15 (45%), -130; down then up 17 (63%), +79; down then down 10 (37%), -95 |

Reading and base rates:
- The primer: after a January yield rise, Feb-Mar was higher 70% of the time and the 10y had a slight tendency to be higher by year-end (61%). After a rise in the first five days, yields tended to fall for the rest of January (a short-term mean reversion) and then rise into the end of Q1. It says the first five days "does not appear to have much correlation with the trend for the full year".
- **(computed)** Feb-Mar was up in (23 + 17) / 61 = 66% of all years, and still 61% after a down January: the conditional edge is about 70% against 61-66%, which is weak. Feb-to-year-end up: 61% after a January rise against 43% after a fall, unconditional (20 + 12) / 61 = 52%: a larger gap. Rest-of-January down unconditionally (22 + 13) / 61 = 57%.
- Source inconsistencies, recorded so neither number is trusted blindly: conditional counts often sum to one less than the total (first-5 up is 34 but 18 + 15 = 33 in the rest-of-year cell), probably because the incomplete current year is excluded; the introduction to the first-five-days study says "30y" but the section analyses the 10y.

**Seasonal path of the US 10y yield.** Since 1963 the average trend is up into May and down into year-end; February is the most likely up month (63%). Since 1999: up into May, down through September, a bounce in October-November, down in December; the strongest up-ratio is a November rise and the strongest down-ratio is July.
Last 10 years (2015-24): choppy first half, a peak in May, a low in early August, a rise into November (November up 10 of 10), a dip into year-end. Year 1 of the presidential cycle: rises in January-February, falls in April, bounces in May, falls in June, rises in July-August, falls through November, bounces into year-end.
No significance is shown for rates: a soft prior only.

**US 10y yield and the presidential cycle (since 1964, 15 terms, average bp change; medians where printed).**

| Group | Year 1 | Year 2 | Year 3 | Year 4 | Full term |
|---|---|---|---|---|---|
| All terms, average | +23 (60% up) | -23 | +6 | -3 | +2 (40% up) |
| All terms, median | +44 | -1 | +10 | -1 | -45 |
| Republican, average | +1 | -84 | +5 | -41 | -119 |
| Democrat, average | +48 | +47 | +7 | +40 | +141 (100% up, n = 7) |

First-term full-term averages: Democrat +210, Republican -111. The text says the average full term was a "lower yield", yet the table prints +2 for all terms, and the median is -45: do not trust either reading alone. Year 1 summary: the dollar index rose 62% of the time by 1.01%, the 10y yield rose 60% by 23bp, oil rose 60% by 13.4%.
The splits rest on small samples (15 terms in all, 7 in the Democrat split).

**Dollar index, % changes of the price (about 50 years).**

| Test | Cells |
|---|---|
| January | up 33 times (66%), average +2.39%, median +2.03%; down 17 times (34%), -1.69% and -1.57%; all years +1.00% and +0.89% |
| January, then Feb-Mar | up then up 20 (61%): Jan +2.50%, Feb-Mar +2.52%, Q1 +5.07%. Up then down 13 (39%). Down then up 8 (47%). Down then down 9 (53%): Q1 -4.36% |
| January, then Feb to year-end | up then up 21 (64%): Feb-YE +6.00%, year +8.79%. Up then down 12 (36%): Feb-YE -8.46%. Down then up 8 (47%). Down then down 9 (53%): year -10.24% |
| First 5 days (51 years) | up 31 (61%), average +1.12%, median +0.82%. After up: rest of January up 16 of 30 (53%), rest of Q1 16 of 30 (53%), rest of year 12 of 30 (40%). After down: rest of January up 12 of 20 (60%), rest of Q1 13 of 20 (65%, +4.48%), rest of year 13 of 20 (65%, +6.93%) |
| Presidential cycle (13 terms) | Year 1 +1.01%, Year 2 -2.93%, Year 3 -0.74%, Year 4 +4.17% (77% up), full term +2.99%; Republican full term -2.03%, Democrat +8.84% |

**(computed)** January-up then Feb-Mar-up is 61% against an unconditional (20 + 8) / 50 = 56%; January-up then Feb-to-year-end up is 64% against (21 + 8) / 50 = 58%. The primer's text gives 19 of 33 (58%) and 20 of 33 (61%) for the same cells, against 20 (61%) and 21 (64%) in the tables.
Its own conclusion: a weak start to the year has been a mildly contrarian bullish signal for the dollar.

**Decay.** For the S&P 500 the primer shows the January barometer's success rate in calling the year falling from 90% in the 1950s and about 80% from the 1940s to the 1990s to 60% in the 2000s, 50% in the 2010s and 60% in 2020-24. Expect calendar priors to decay, and to be weaker out of sample than in the tables.
