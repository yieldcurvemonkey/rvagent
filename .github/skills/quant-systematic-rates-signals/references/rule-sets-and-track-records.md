# Rule sets and track records (detail for `quant-systematic-rates-signals`)

All IRs are return / volatility of the rule's monthly P&L, annualised, in-sample unless stated, before any live
haircut. Sign convention: + = long duration / receive / overweight. Every table names its source; tag any number you
reuse with that source's universe, sample and publication date. Track records drift between vintages (see section 4).

## 1. Duration signals: lookback choice (G-4 10y bond futures: US, JP, EA, UK)

Source: J.P. Morgan, Investment Strategies No. 74 "Simple rules to trade duration" (Mac Gorain, 2 Oct 2012).
Costs: half a 32nd per trade in Treasury futures, 0.01% of par in Bund futures, 0.02% of par in gilt and JGB futures.
Columns are US / JP / EA / UK / Combined.

| Signal and lookback | IR | Note |
|---|---|---|
| PMI local, 1m / 2m / 3m change | -0.15/-0.19/0.39/0.39/0.22 ; 0.32/-0.02/0.43/0.73/0.58 ; 0.45/0.18/0.41/0.56/0.57 | since 1998 |
| PMI global, 1m / 2m / 3m | 0.37/0.15/0.61/0.45/0.49 ; 0.52/0.28/0.66/0.57/0.62 ; 0.39/0.03/0.51/0.45/0.44 | |
| PMI local AND global, 1m / **2m** / 3m | 0.13/0.01/0.55/0.52/0.42 ; **0.45/0.15/0.62/0.72/0.64** ; 0.43/0.12/0.46/0.56/0.53 | chosen: 2m, both |
| Revision ratio local AND global, 1m / 2m / **3m** | 0.24/-0.12/0.38/0.83/0.50 ; 0.34/0.00/0.37/0.72/0.50 ; **0.37/0.06/0.73/0.56/0.58** | since 1990; chosen: 3m |
| Bond momentum vs N-month average, 1m / 2m / 3m / 6m / 12m | 0.51/0.48/0.20/0.00/0.41 ; 0.43/0.54/0.40/-0.03/0.45 ; 0.33/0.62/0.30/0.41/0.58 ; 0.37/0.41/0.45/0.41/0.55 ; 0.42/0.53/0.52/0.42/0.62 | chosen: 1m AND 12m; 12m "best" because long 77% of the time |
| Equity momentum (contrarian), 1m / 2m / 3m / **6m** / 12m | -0.06/0.18/0.11/0.02/0.07 ; 0.25/0.17/0.37/0.25/0.36 ; 0.26/0.44/0.40/0.27/0.47 ; **0.21/0.42/0.55/0.18/0.45** ; 0.09/0.35/0.20/0.05/0.21 | chosen: 6m local |
| Carry, binary (above 10y average) | 0.26/0.34/0.05/0.30/0.41 | columns US/DE/JP/UK/Comb |
| Carry-to-risk, binary | 0.44/0.35/0.33/0.32/0.63 | |
| Carry, proportional (percentile rule) | 0.47/0.37/0.09/0.43/0.57 | |
| **Carry-to-risk, proportional** | **0.53/0.35/0.43/0.49/0.75** | chosen; about 0.7 since 1990 |

Other findings from the same paper:
- A fall in the global manufacturing PMI was followed by a further fall about 2/3 of the time. Country PMI changes
  correlated 0.49 with the prior month's global change and only 0.24 with their own prior change (past 5y).
- Revision ratio = (upgrades - downgrades) / firms with forecasts, released the Tuesday after the third Friday.
  It explains 58% of global GDP-growth variance (PMI: 66%) but arrives about 1.5 weeks earlier. Regression of the
  monthly PMI change on both: lagged PMI change 0.23 (t 3.26), revision-ratio change 0.46 (t 6.60), adj R^2 0.36.
- Carry quartiles vs the previous 10y: G-4 excess return about 8% annualised in the top quartile vs under 1% in the
  bottom. "The vast bulk of excess returns on long-term bonds have come when carry was above average."
- Since 1990, bond returns exceeded 6% annualised after the weakest quartile of 3m equity returns, about 0 after the
  strongest.
- Real yields were rejected as an outright signal because of the 30-year downtrend; they work cross-sectionally.

## 2. Signal correlations (duration signals, monthly returns)

| Pair | Mac Gorain 2012 (since 1998) | Inkinen & Bassi 2015 |
|---|---|---|
| PMI - revisions | 0.59 | 0.62 |
| PMI - bond momentum | 0.27 | 0.41 |
| PMI - equity momentum | 0.57 | 0.55 |
| PMI - carry-to-risk | -0.20 | -0.42 |
| Revisions - bond momentum | 0.06 | 0.21 |
| Revisions - equity momentum | 0.43 | 0.61 |
| Revisions - carry-to-risk | 0.01 | -0.19 |
| Bond momentum - equity momentum | 0.24 | 0.22 |
| Bond momentum - carry-to-risk | -0.01 | -0.21 |
| Equity momentum - carry-to-risk | -0.17 | -0.28 |

Read: the three macro/equity signals are one cluster (0.4-0.6); bond momentum is partly separate; carry-to-risk is
negatively correlated with everything, which is why it gets 35%.

## 3. Combined duration model: performance

| Statistic | Value | Source |
|---|---|---|
| Single signals, since 1998 (Bond mom / Eq mom / Revisions / PMI / C2R) | IR 0.50 / 0.61 / 0.68 / 0.64 / 0.58 | Mac Gorain, Oct 2012 |
| Equal-weight combination | IR 1.03 (US 0.94, JP 0.27, EA 1.07, UK 0.85) | Mac Gorain, Oct 2012 |
| In-sample optimised weights | IR 1.07 ("only a little" better, look-ahead) | Mac Gorain, Oct 2012 |
| Chosen 35/20/15/15/15, since 1990 | 2.5% return, 2.2% vol, IR 1.13, 65% of months positive | Mac Gorain, Oct 2012 |
| Long-only G-4 futures | IR 0.8; vol-weighted overlay of combo on long-only IR 1.3 | Mac Gorain, Oct 2012 |
| Without bond momentum (removes long bias) | IR 1.04 since 1990 | Mac Gorain, Oct 2012 |
| 10 markets on 10y swap TR indices | IR 1.3 vs 1.1 on G-4 futures; long G-4 0.84; long 10-country basket 0.6; about 1/3 the vol of an outright long | Inkinen & Bassi, Apr 2015 |
| Exhibit 3, since 1999: return / vol / IR / max DD / hit | PMI 2.7/4.0/0.7/-7.7/57; Revisions 3.3/4.5/0.8/-4.5/62; Bond mom 2.5/4.5/0.5/-4.4/55; Eq mom 3.7/5.2/0.7/-6.3/54; C2R 2.2/4.5/0.6/-13.5/55; **Combined 2.0/1.7/1.2/-1.8/63** (%) | Gupta, Inkinen, Vijay, Mar 2017 |

Loss years of the combination (about -1% y/y): 1991 and 1998 (low carry bearish while bonds rallied on weakness and
Russia/LTCM), 2002 (bonds out of line with PMI), 2010 (long momentum caught by the Q4 sell-off). The signals never all
lost at the same time (Mac Gorain, Oct 2012). 2017: -1.2%, the first annual loss since 2012, from longs in SEK and AUD
(Gupta, Inkinen, Vijay, Jan 2018).

## 4. Vintage drift of the combined since-1998 IR (same 10-market model)

| Publication | Combined IR since 1998 | Single-signal IRs (PMI / Rev / Bond mom / Eq mom / C2R) |
|---|---|---|
| Apr 2015 (Inkinen & Bassi) | 1.31 | 0.59 / 0.84 / 0.64 / 0.66 / 0.59 |
| Feb 2017 (Gupta, Inkinen, Vijay) | 1.26 | 0.68 / 0.77 / 0.56 / 0.73 / 0.55 |
| Jul 2017 | 1.20 | 0.64 / 0.74 / 0.51 / 0.69 / 0.56 |
| Jan 2018 | 1.17 | 0.49 / 0.52 / 0.52 / 0.56 / 0.42 |

## 5. Country snapshots (+ = long duration)

Order EA, JP, UK, US, AU, CA, SE, CH, NZ, NO.

| Date | Signal | Values | Aggregate |
|---|---|---|---|
| 1 Apr 2015 | PMI | -1,0,-1,0,0,0,0,0,-1,0 | -0.3 |
| | Revisions | 0,1,1,1,0,1,0,0,0,1 | 0.5 |
| | Bond mom | all +1 | 1.0 |
| | Equity mom | all -1 | -1.0 |
| | C2R | -1.5,-1.9,0.0,-0.1,0.2,-1.1,-1.3,-1.0,-0.6,-1.0 | -0.8 |
| | **Combined** | -0.6,-0.5,0.1,0.2,0.1,-0.2,-0.4,-0.3,-0.3,-0.1 | -0.2 |
| Jul 2017 | PMI | 0,1,1,0,1,1,1,0,0,0 | 0.5 |
| | Revisions | 1,1,1,0,1,1,0,1,0,1 | 0.7 |
| | Bond mom | all -1 | -1.0 |
| | Equity mom | -1,-1,-1,-1,1,1,-1,-1,-1,-1 | -0.6 |
| | C2R | 0.4,-1.4,-0.7,-0.4,1.6,-0.6,1.2,0.7,0.3,1.2 | 0.2 |
| | **Combined** | -0.1,-0.5,-0.3,-0.5,0.8,0.0,0.2,0.0,-0.2,0.2 | 0.0 |
| Mar 2017 | **Combined** | -0.5,-0.6,-0.3,-0.4,0.0,-0.4,-0.2,-0.6,-0.1,0.0 | -0.3 (prev -0.5) |
| Jan 2018 | **Combined** | -0.3,-1.0,-0.6,-1.1,0.0,-0.6,+0.4,-0.3,+0.1,0.0 | -0.3 (prev 0.0) |

`scripts/signals.py --selftest` reproduces the Jul 2017 combined row from the signal rows (to rounding).

G-4 snapshots (US, JP, EA, UK): Oct 2012 combined -0.3/+0.1/-0.5/0.0 (aggregate -0.2); Nov 2012 combined
US -0.5, JP -0.1, EA -0.4, UK 0 (aggregate -0.3). In Nov 2012 the UK was flat because its curve was steeper than its
own past average (C2R +0.7) (J.P. Morgan, Rule-based Fixed Income Monthly, Nov 2012).

## 6. Regime behaviour (Inkinen & Bassi, Apr 2015)

- Rally / sell-off month: average total return on G-4 10y swaps positive / negative.
- Bond momentum: good in rallies, about zero in sell-offs (1m AND 12m needs prolonged underperformance to flip short).
- Equity momentum: very good in sell-offs, slightly negative in rallies. Without equity momentum and revisions the
  combined IR would be slightly negative in sell-offs.
- Fed cycle: easing (hiking) regime runs from one month before the first cut (hike) to one month after the last;
  QE counts as easing. The combined signal tends to be long in easing, short in hiking, slightly long on hold. ECB
  and BoE cycles give similar results.
- Equity-bond correlation is negative in flight to safety and growth-driven moves, positive when monetary policy is
  the driver. That explains weak equity-momentum performance when easy policy lifted both.

## 7. Cross-market (country) signals

**Inkinen & Bassi, Apr 2015: 10y IRS, two long-short pairs (1st vs last, 2nd vs 2nd-last), IR since 1996.**

| Signal | Definition | IR | Basket on 1 Apr 2015 |
|---|---|---|---|
| Carry | 10y swap - 1m cash | 0.56 (2.3% p.a.) | USD/NZD; GBP/NOK |
| Carry-to-risk | carry / vol | 0.65 | USD/NZD; SEK/NOK |
| Change in slope | (10y - 1y) - 6m average | 0.48 (12m -6.6%) | CHF/USD; JPY/GBP |
| Real yield (since 2004) | 10y swap - consensus 10y inflation | 0.39 (12m +6.3%) | NZD/EUR; AUD/JPY |
| Unemployment change | U - 10m average | 0.24 | NOK/GBP; AUD/USD |

Return correlations: carry vs carry-to-risk 0.59; carry vs slope 0.18, vs real yield 0.06, vs unemployment 0.22;
carry-to-risk vs slope 0.00, vs real yield -0.11, vs unemployment 0.13; slope vs real yield 0.01, vs unemployment
0.07; real yield vs unemployment -0.01. Carry and real yield do well in rallies, less in sell-offs. On average USD
and EUR swaps were the most attractive carry markets.

**Mac Gorain, Rule-based Fixed Income Monthly, Nov 2012 (10y swaps, net of 2bp per currency, 4bp per pair).**
Pooled monthly regression since 2003 (CAD, CHF, EUR, GBP, JPY, SEK, USD; every variable demeaned cross-sectionally):
carry (10y-1m) 2.6 (t 4.1), change in 10y-1y slope 7.4 (t 4.2), real yield 2.2 (t 3.6); adj R^2 0.05. Units: bp per
month of relative yield decline per 100bp of the signal.

| Strategy | 1y: return / vol / IR / hit | 10y: return / vol / IR / hit |
|---|---|---|
| Duration | 0.3% / 0.9% / 0.39 / 50% | 2.2% / 2.0% / 1.10 / 63% |
| Cross-market carry | -0.3% / 3.0% / -0.10 / 50% | 1.9% / 3.7% / 0.51 / 53% |
| Cross-market mean reversion | 0.7% / 2.2% / 0.32 / 50% | 3.5% / 3.8% / 0.92 / 62% |

Real-yield long-short (top 2 vs bottom 2): 7 countries 2.1% / 3.2% / IR 0.65 / hit 55% / beta to market 0.4;
excluding Japan 2.2% / 3.0% / IR 0.73 / 59% / beta 0.0. Most of the return came in the 2 years after Lehman.

**Panigirtzoglou, Investment Strategies No. 15, Mar 2006 (10y bonds, 8 markets, currency-hedged, monthly).**
Carry = 10y yield - 1m cash. IR by number of pairs (1/2/3): since 1988 0.78/0.58/0.69; 1988-95 0.34/0.33/0.50;
since 1996 1.33/0.94/0.94; since 2000 1.47/0.94/0.88; since 2005 0.36/0.47/0.45. About 2/3 of the return is carry. Correlation with an
equal-weighted long portfolio 0.05; bull/bear-month IR 1.10/0.41. Replacing the 1m rate with the 1m rate 1y forward
(stripping near-term policy expectations) lowered IRs.

**Panigirtzoglou, Investment Strategies No. 31, Jan 2007 (40 bonds: 8 markets x 2/5/7/10/30y).**
- Spread carry = (long yield - cash) - duration-weighted (short yield - cash); risk = 12m rolling std of monthly
  returns of the spread itself (captures correlation); each trade scaled to 100bp annualised risk.
- IR (1/2/3/4 trades): all trades 0.94/1.10/1.00/0.93; curve only 0.64/1.05/1.08/1.00; cross-market only
  0.83/0.93/0.94/0.91; 50% curve + 50% cross-market (2 each) 1.33. Diversifying beat picking the best theme (1.06).
- Weekly rebalancing gave no benefit before costs. Monthly vol data beat daily or weekly for risk estimates
  (best 2 trades, all trades 0.87 vs 0.75/0.71), except for cross-market trades alone (monthly 0.94 vs daily 1.07,
  weekly 1.12).
- Scaling risk by the carry-to-risk level: 0.60/0.53/0.45 vs constant risk 0.94/1.10/1.00.
- Correlation with the global bond index 0.16, beta 0.12. At most 25% of the return is capital gains; in bear
  months capital losses eat about half the carry.
- Failures: flat 1999-2002 (post-LTCM unwinds), weak in recessions, hurt by rising bond vol. A high 12m beta of
  hedge-fund indices to the strategy preceded the LTCM and 2001 drawdowns and predicted weaker next-3m returns.

## 8. Alternative specifications from other sources

- **Regression timing model** (Salomon Brothers, Understanding the Yield Curve Part 4, Aug 1995): monthly 20y
  Treasury excess return on term spread (5y - 3m), real yield (5y - trailing CPI), inverse wealth (equity index
  vs its exponentially weighted past, weight 0.9) and a momentum dummy (+1 if the long yield is more than 5bp below
  its 6m moving average, -1 if more than 5bp above, 0 inside the 10bp band). Full sample 1965-95: coefficients
  0.37 / 0.20 / 9.85 / 0.34 (t 2.24 / 2.89 / 4.81 / 2.02), R^2 10.3%. Out of sample (expanding window): sign right
  61% of months; scaled strategy Sharpe 0.68 vs 0.06 for always-long. Implementation as duration targets around a
  4y benchmark: aggressive -2/1/4/7/10y, moderate 0/2/4/6/8y, conservative 3.0-5.0y for forecasts
  negative / low / average / high / very high.
- **Moving-average trend on a US 7-10y bond index** (Willer & Saunders, Trading Global Macro Markets, 2026):
  active IR 22d 0.55, 55d 0.68, 200d 0.58, 252d 0.47 vs buy-and-hold 0.42; in the market 55-62% of the time.
  "Higher rates are self-limiting", so shorter lookbacks suit bonds better than equities.
- **Ilmanen-style valuation regression** (same book): real yield, 2s10s, equities vs 200dma, momentum dummy;
  long/short active IR 0.70 but only 26% of the time in the market; verdict "use sparingly".
- **Data-surprise trend rule** (same book): receive 5y swaps when the data-surprise index is below -25, pay above
  +75; active IR 1.01 vs 0.26 for holding 5y swaps; in the market 27% of the time. The asymmetric thresholds capture
  the bond risk premium.
- **Scorecard format** (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026): each signal (hawk-dove
  bias, fair-value residual, positioning, momentum) mapped to -5..+5 by percentile rank within its own history
  (2y lookback except fair-value models); momentum raw -20..+20 divided by 4. Not comparable across markets.

## 9. Same approach for short-gamma timing (pointer only)

J.P. Morgan's updates also run rule-based 3Mx10Y EUR gamma signals (vol momentum, risk-adjusted-carry percentile,
PMI shock, liquidity; combined IR 2.5 since 2000 vs 1.0 always-short; fading implied-vol extremes alone IR -0.3).
Those belong in `vol-rates-options-rv`.

## 10. Trend rules and event studies on a bond index

Source: BofA Global Research, Technicals Explained primer (Ciana, Suttmeier, 14 Jan 2025). Sign convention: a golden
cross on a bond future price means lower yields (+ long duration); on a yield series it is the reverse. Build the
rule on the return index.

**Moving-average signals.** Four generic readings: price crosses the MA, the MA slope turns, a short MA crosses a
long one, price is far from the MA relative to its history. A fan of 20/50/100/150/200d averages gives 20 conditions;
a dispersed fan means a strong trend. The EMA stays closer to price and signals earlier than the SMA. The primer's
rule of thumb: rates mean-revert more often, commodities trend longer, equity indices drift up (no rates test is
given for the claim).

**Golden/death-cross event study (method).** For each signal, take the forward % change at 5-80 trading days, with
up/down counts, mean, median, min and max, and repeat conditioned on the 200d SMA slope. Verdict in the primer:
good for context, not necessarily entry and exit.

| Market and signal | Signals | Forward result |
|---|---|---|
| US long bond future, golden cross (since 1977) | 34 | higher 68% at 40-50d (23 of 34 per the table; the text says 31), average +1.44% at 45d |
| Same, with a rising 200d | 14 | higher 12 of 14 (86%) at 45-50d, average +2.49% at 45d and +2.54% at 50d; min/max at 45d -5.10% / +13.42% |
| Same, death cross | 34 | little relevance, down ratios 36-53% |
| Oil, golden cross with a rising 200d | n/a | bearish for the first 10d (up only 20-33%); with a falling 200d up 81% at 5d |

The oil row is the warning: conditioning on the 200d slope changed the sign of the result. Conditioned samples are
often 14-17 signals.

**Triple-MA score (TMAC, 10/20/30d).** 9 conditions: price vs each MA (3), each MA vs the others (3), slope of each
MA (3). The sum runs -9..+9. Example rule sets from the primer (no performance reported):
- long when the sum is above 0, short when below 0;
- buy at +9, add on down days that do not reduce the sum, reduce at 6, exit at 3 (mirror at -9/-6/-3);
- scale in by thirds at >=3, >=6 and =9, and scale out at 5, 2 and 0 (mirror for shorts).

Filter: trade only when the 200d slope agrees; less-trending markets may need a profit-target exit.

**Weekly MA trend states (13/26/40/200-week).** Slope matters more than the side of the MA. Bullish: close above a
rising MA (buy dips). Bullish-at-risk: close below a rising MA. Bearish: close below a falling MA (sell rallies).
Bearish-at-risk: close above a falling MA. Trends are strongest when all timeframes agree. The primer notes that
tops and bottoms in a relative (ratio) series often lead those in the absolute series, which carries to spread and
fly series.

**ADX regime classifier.** +DMI above -DMI means rising. ADX below 20 = range, 20-25 = transition, above 25 = trend.
ADXR is a moving average of ADX: a trend starts when ADX crosses above ADXR from below 20, and ends when a high ADX
(about 40) crosses below it.

**ATR and stops.** True range = max(H-L, |H - prev close|, |L - prev close|); ATR = simple or exponential average of it
(14 periods is the usual default). Trailing stops: long = prior low minus ATR, short = prior high plus ATR. A
trend-line break is confirmed by a close at least 1% beyond the line, above-average volume, consecutive closes
beyond it, failed retests on light volume, or a break larger than the ATR. Scale in and out by thirds.

## 11. Trend-follower replication and stop-out risk

**Bottom-up ensemble (BofA, Systematic Flows Monitor, 2 Jun 2025).**

| Parameter | Choice that tracked a CTA index best | Variants run |
|---|---|---|
| Universe | broad cross-asset futures (equity index, sovereign bond, interest rate, commodity, currency) | n/a |
| Trend lookback | medium = equal weight of short (MA crosses of 21 to 100d) and long (50 to 252d) | 3: short, medium, long |
| Sizing | risk parity; allocation published as a z-score, maximum 10% per asset | n/a |
| Risk management | moderately aggressive stop from the high-water mark, flattening the position | 4 stop levels (values not published) |

- 12 models = 3 lookbacks x 4 stops. Over the long run the stop level barely changes performance, because stops are
  rarely hit and positions unwind anyway as the trend reverses.
- Sigma move = daily return / prior day's prevailing realised vol (EWMA, lambda 0.97, de-annualised). Correlations
  to the benchmark are EWMA with lambda 0.97 (data 1999-2025).
- Consensus diagnostic: the average pairwise EWMA correlation among the short, medium and long models; low means
  dispersed positioning.
- Projection: bear / median / bull = 2.5th / 50th / 97.5th percentile of historical 5-day return paths at current
  vol; list a model's unwind trigger only if it lies inside the forecast path.
- Evidence: 9 of the 15 largest one-day sigma declines in S&P futures since 2010 coincided with stop-loss unwinds
  (the exceptions were fundamental stress such as Covid). On days with 4 or more of 12 models stopping out, the
  absolute sigma move exceeded the full-sample average. The same monotone pattern (more stops, larger absolute move)
  is shown for 10y Treasury and Bund futures and other markets over 2010 to May 2025. The 4-of-12 threshold itself
  was stated for the equity index; 3 stop-outs came with large moves but not reliably.
- Validation: of 14 US-listed managed-futures funds with correlation to the index of at least 0.7, each correlated at
  least 0.68 with one of the models and 10 were closest to the medium-term model. The short-term model was the
  closest tracker before 2013-14 and the long-term model has been more stable since, a sign that CTAs lengthened
  their trend horizon.
- Reading: risk is greatest when all three lookbacks are similarly positioned and stretched. Flows from unwinds can
  exceed flows from accumulation. Single-parameter models miss dispersion; the medium model alone may do for
  monitoring and consensus across all gives conviction. Real CTAs differ in universe, lookback, risk target and stop
  aggressiveness.

**Top-down regression (BofA, CTAs impact on the rates market, 18 Aug 2020).**
1. Target: an equal-weighted index of 20 large CTAs open to new investment (it has survivorship bias).
2. Pick representative assets per group by hierarchical clustering. Groups: equities, longer-duration bonds,
   shorter-duration bonds, metals, energy, FX. Broad benchmarks were rejected: too broad, rebalancing rules interfere,
   long/short bias is hidden.
3. Take only the first principal component of each group as the feature (higher eigenvectors are unstable and would
   destabilise the betas; low dimension reacts faster).
4. Rolling OLS of index returns on the 6 features over a 2-month window (fast response, limited noise). Project the
   betas back to single assets through the inverse PC1 transform. Replacing the FX feature with the dollar index
   gave average R^2 of 66% on 2-month windows since 2015 and was kept.
5. Read the rates view: the long-duration beta is the duration bias; the long-duration beta against the short-duration
   beta is the curve bias (long the long-duration feature and short the short-duration one = flattener). Long-duration
   betas are more stable; short-duration betas are volatile and follow the policy path. The flow signal is the
   week-on-week change in betas; duration is first order, curve second order. Z-score the betas against their average
   3-month level; a breadth index reaches +/-1 when all assets are over/underweight at 1.5 sigma.
6. Validation: the betas correlate significantly with a multi-crossover momentum signal for equities, the 10y
   Treasury and crude (lower for gold, lowest for the dollar), with a lead/lag of about 15-20 days at peak
   correlation. The 10y Treasury beta trend correlated about 60% with net non-reportable futures positions (other
   reportables 20%), but levels and long/short implications did not match.

Track record of the read (Aug 2020 note): 2016 long duration plus flatteners, shifting to steepeners after the
election; 2019 flattening bias (neutral-rate downgrade); betas decayed in the 1Q20 dash for cash, which supports the
2-month window. At publication: long-duration bias since February, last meaningful build the week of 10 July,
trimmed from early August; curve bias switched from bull steepening to slight flattening in late March, peaking on
24 July.

## 12. Cross-sectional scorecards and positioning proxies (FX evidence)

Source: BofA Merrill Lynch, FX Quant Primer (Iaralov, Leng, Vamvakidis, 1 Oct 2018). Universe: 10 G10 currencies,
weekly portfolios opened Monday 5pm New York and closed the next Monday, hypothetical and gross of costs. The rates
reader should take the construction, not the numbers. The authors also flag that factor relationships broke in 2011,
2013 and 2017, so recheck stability before use.

**Rank-to-score tables** (values for ranks 1 to 10, rank 1 = most favourable):

| Factor | Scores |
|---|---|
| Equity momentum | 4, 4, 2, 2, 0, 0, -2, -2, -4, -4 |
| Carry level | 4, 3, 3, 0, 0, 0, 0, -3, -3, -4 |
| Rates momentum | 3, 2, 1, 0, 0, 0, 0, -1, -2, -3 |
| Contrarian value | 2, 1, 0, 0, 0, 0, 0, 0, -1, -2 |

z-scores use a 1y window, `z = (x - mean) / s` with `s` the sample standard deviation (n - 1).

**Averaged scorecard (OCTAVE, live since 2012).** Rank = sum over 4 factors of (z + scorecard value), long the top 3
and short the bottom 3. Factors: carry level (swap-rate level), 2-month rates momentum (8-week % change in swap
rates), 2-month equity momentum (8-week % change), 2-month contrarian value (44-day average FX / spot, used only
when |z| > 1). Two of four factors are rates, so it works best when rates drive FX.

**Two-step filter sort (FORTE, live since 2014).** Step 1: rank on 12-month equity momentum, equity scorecard 3, 2, 1,
0.5, 0, 0, -0.5, -1, -2, -3. Step 2: re-sort the top-4 and bottom-4 baskets separately by filter score = equity
scorecard + z(carry level) + z(1-week rates momentum) + z(15-day average FX / spot). Long the 2 highest filter scores
in the top basket, short the 2 lowest in the bottom basket, ranks 5-6 neutral. The model can never sell a currency
with strong equities or buy one with weak equities. The authors call it non-parametric (two sorts, not a weighted
average).

| Model | Since inception | Last 12m | Long signals above funding |
|---|---|---|---|
| OCTAVE | 343 portfolios, 52.8% hit | 52 portfolios, 50.0% | 1.56 of 3 (12m 1.46) |
| FORTE | 237 portfolios, 54.0% hit | 52 portfolios, 53.8% | 1.03 of 2 (12m 1.00) |

Hit ratio = share of weekly portfolios with a positive combined long-short return. "Long signals above funding" =
number of long legs whose period change beats the equal-weighted basket of the shorts.

**Factor sensitivity.** Correlating the cross-sectional ranking of FX returns with each factor's ranking, equities
come first, then rates, terms of trade, inflation and unemployment. Rates peak at a horizon of about 2 months (average
about 40%); equities peak at 6 months (about 55%, currently about 47%). Factors show up at the
extremes (high against low), not pairwise.

**Moving-average aggregator (MAA).** Spot and its 5/10/20/30/50/100/200d averages give 8 series and C(8,2) = 28
pairwise comparisons; MAA is the % of pairs that are bullish (100% = all 28, 50% = 14). Uptrend if above 60,
downtrend if below 40. Breadth versions add +1 per pair in uptrend and -1 in downtrend across a currency group.

**Up/down vol.** Raw U/D = 100 - 100 / (1 + UP/DOWN), UP and DOWN being realised vol on up and down days over a common
rolling month; UD% = 100% - the 1y percentile of Raw U/D. Read with MAA: reversal likely when MAA and UD are above 80
in an uptrend (below 20 in a downtrend), unlikely when UD is below 50 in an uptrend (above 50 in a downtrend).

| Condition (G10 FX, one week ahead; vol direction per the UD measure) | Outcome |
|---|---|
| Extended uptrend (MAA above 60) | gains strength only about 44% of the time |
| Extended downtrend (MAA below 40) | bounces 55% of the time |
| Uptrend with up vol | gains strength 52% |
| Uptrend with down vol | gains strength 40% |
| Downtrend with up vol | bounces 60% |
| Downtrend with down vol | bounces 48% |

**Momentum persistence.** Sign of the spot change over 0.25-12 month lookbacks against the next 1-52 weeks, 9 USD
pairs since 2000 (about 40,000 daily observations, t-test against 50%). 52% of medium-term trends continued another
month. Trends of 4-6 months persisted for 1-4 weeks and began to mean-revert after about 2 months; the peak t-stat
was 8.9 (5-month lookback, 4 weeks ahead). The persistence is moderate and decays: a 4-month EURUSD trend had a 95%
confidence interval of 53.6-56.5% for continuing 4 weeks later.
