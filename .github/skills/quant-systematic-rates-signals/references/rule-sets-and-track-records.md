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
