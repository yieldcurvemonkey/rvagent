# CTA positioning, COT extremes and price confirmation: tables and worked numbers

Longer material behind SKILL.md sections 6g (CTA positioning and impact) and 6i (COT extremes and price/positioning
divergence). Sign convention throughout: positive = net long (long duration for rates). Every statistic below is the
source's, on its own sample and normalisation: re-estimate before relying on it.

## 1. Top-down CTA replication (BofA, CTAs impact on the rates market, 18 Aug 2020)

Target: an equal-weighted index of 20 large CTAs open to new investment. Recipe:

| Step | Rule | Why |
|---|---|---|
| 1. Asset sets | equities, longer-duration bonds, shorter-duration bonds, metals, energy, FX; hierarchical clustering picks a representative set per class (equity clusters: US-fundamentals, broad DM, EM-biased) | assets in one cluster carry overlapping information; broad benchmarks hide long/short bias and have their own rebalancing rules |
| 2. Feature | first principal component of each set only | higher eigenvectors are unstable and would destabilise the betas; fewer features need less data and react faster |
| 3. Regression | rolling OLS of the CTA index return on the 6 features, 2-month window; project feature betas back to single assets through the inverse PC1 transform | the window lets betas respond quickly without too much noise |
| Variant | replace the FX feature with the dollar index (already close to an eigenportfolio) | average R^2 66% on 2-month windows since 2015, better than the FX-PC version |

Reading the betas (betas are on price or return features, so positive = long the asset set):

| Beta | Reads as |
|---|---|
| long-duration beta | long or short duration bias; the more stable of the two |
| long-duration beta minus short-duration beta | curve bias: long the long-duration feature and short the short-duration feature is a flattener (curve spread = long - short falls) |
| short-duration beta | volatile and policy-path dependent |
| week-on-week (or bi-weekly) change in beta | the flow signal; duration is first order, curve second order |
| beta z-score vs the average 3-month beta | over or underweight; an aggregate index across single-asset betas reaches +1 or -1 when every asset is over or underweight by 1.5 sd |

Validation reported by the source:
- Against a multi-crossover momentum signal (several crossovers with different decays; parameters not given): significant
  correlation for S&P, the 10y UST future and WTI; lower for gold (the metals feature mixes base and precious metals); lowest
  for the dollar (its momentum is already inside the other features). Maximum correlation at a 15 to 20 day lead or lag.
- Against CFTC: the 10y beta trend correlates about 60% with net non-reportable 10y futures positions and only 20% with
  other reportables; commercial, non-commercial, institutional and leveraged-fund series were also tested and did worse.
  Absolute levels and long/short implications do not match, so use the beta for direction and flow, not as a CFTC level.

History the source reads from the betas:

| Period | Read |
|---|---|
| 2016 | long duration plus flatteners (Fed tightening while neutral-rate expectations were cut); after the November election a shift to steepeners (fiscal and regulatory easing) |
| 2019 | flattening bias (neutral-rate downgrade, "bullish inversion") |
| early 2020 | betas decayed in the late-1Q dash for cash (Treasuries and gold sold): evidence for the short 2-month window |
| Aug 2020 | long-duration bias since February; last meaningful build in the week of 10 July; longs lightened in early August. Curve bias switched in late March from bull steepening (Fed easing) to a slight flattening bias that peaked on 24 July and was trimmed from early August |

Limits: the index has survivorship bias; models are increasingly diverse, so one average CTA captures less; a bottom-up
build (trend rules of different lengths) is more granular but rests on approximations. Context in 2020: CTA assets peaked
near $360bn in 2013 and fell below $300bn in 2020, about 95% systematic.

## 2. Bottom-up CTA ensemble and stop-count rule (BofA, Systematic Flows Monitor, 2 Jun 2025)

| Parameter | Setting that tracked the benchmark |
|---|---|
| universe | broad futures: equity index, sovereign bond, interest rate, commodity, currency |
| trend lookback | short = MA crosses from 21 to 100 days; long = crosses from 50 to 252 days; medium = equal weight of short and long |
| sizing | risk parity; maximum 10% allocation per asset in the model; output published as a z-score per market |
| risk management | a prescribed loss from the high-water mark closes the position; the stop level hardly changes long-run performance (stops are rare, trends reverse anyway) |
| ensemble | 3 lookbacks x 4 stop thresholds = 12 models (thresholds not published) |
| correlations | EWMA with lambda = 0.97, 31 Dec 1999 to 29 May 2025 |

Benchmark behaviour: before 2013 the short-term model correlated best with the benchmark; since then the long-term model
is more stable, i.e. CTAs moved to longer trends. The medium model is the highest and most stable overall. On 3 Apr 2025
(the day after the tariff announcement) long-term correlation rose, short and medium fell, and the average pairwise model
correlation was the second lowest on record. Listed-fund screen (US-listed, USD, managed futures, data since start-2015,
correlation to the benchmark of at least 0.7): 14 funds, about $13bn; each correlated at least 0.68 with one model, and 10
of 14 (71%) were closest to the medium model. CTA hedge-fund assets $339.4bn at 2024 Q4, gross notional often above 3x assets.

Sigma move = daily return / prior-day EWMA realised vol (lambda 0.97, daily). `scripts/flow_positioning.py` has
`sigma_move`.

Stop counts on the 15 largest one-day S&P 500 future sigma declines since 2010 (models stopped out of 12; the pairing of
date and count is read off a chart):

| Stops | Dates (count of the 15) |
|---|---|
| 9 | 10 Oct 2018 |
| 7 | 24 Jun 2016 |
| 6 | 2 Feb 2018, 5 Feb 2018, 24 Feb 2020 |
| 5 | 5 Aug 2019 |
| 3 | 4 Aug 2011, 18 Dec 2024 |
| 2 | 24 Aug 2015 |
| 0 | 8 Aug 2011, 27 Feb 2020, 9 Mar 2020, 12 Mar 2020, 3 Apr 2025, 4 Apr 2025 |

Own checks: 9 of the 15 dates show at least one stop (the "9 of 15 coincided with stop waves" statement), and 6 show four
or more. The zero-stop dates are fundamental stress (the Aug 2011 downgrade, the early 2020 pandemic dates, the April 2025
tariff shock). In the source, the three largest declines coincided with consensus longs stopped out across models.

Rule: on days with 4 or more of 12 models stopped, the absolute sigma move exceeded its full-sample average and the market
usually moved beyond the stop triggers. Three stops come with large moves but not reliably. The same monotone pattern
(more stops, bigger absolute sigma) holds for the 10y UST future and the Bund future, 2010 to May 2025.

Worked reading, EURO STOXX 50 on 30 May 2025 (equity example of the method): CTAs were long across models, largest from the
medium model; unwind levels ran from 5200 down to 4963 within the forecast range; in the bearish path 3 of 12 models (2
medium, 1 short) stop out. Three stops is below the 4-stop threshold, so read it as a fragile level, not a forecast of an
above-average move. Paths: bear, median and bull are the 2.5th, 50th and 97.5th percentiles of historical 5-day return
paths at current vol, and unwind levels are shown only if they sit inside that 5-day range. The same read applies to TY and
RX with their own prices and vols.

Consensus diagnostic: average pairwise EWMA correlation among short, medium and long models. Low means dispersion in
trend-follower positioning (small collective impact); the largest risk is when all three lookbacks are similarly
positioned and stretched. Impact from unwinds exceeds impact from accumulation.

## 3. COT extremes and price/positioning divergence (BofA, Technicals Explained, 14 Jan 2025)

Report categories and the ones the authors use for reversal warnings:

| Report | Categories | Used for warnings |
|---|---|---|
| Legacy | commercial (hedgers), non-commercial (speculators) | net non-commercial % OI |
| Disaggregated | producer, swap dealer, managed money, other reportable | managed money (CTAs, CPOs, funds) |
| Financial (TFF) | dealer, asset manager, leveraged funds, other reportable | asset manager (mutual funds, institutions) and leveraged funds (hedge funds, CTAs, CPOs) |

Why those groups: they are large or build positions quickly in a trend, so an adverse surprise forces fast exits and sharp
reversals. Data cover markets where 20 or more traders hold positions at or above the CFTC reporting level. As-of Tuesday,
released Friday 15:30 New York, shifted by holidays.

Rule: net position as a % of OI, with its mean and +/-2 sd bands. Beyond +2 sd the extreme long is bearish; beyond -2 sd
the extreme short is bullish (contrarian default). Combine with the price trend and technical indicators. A divergence
between the price trend and the positioning trend can flag a trend change.

Worked example (gold, not rates): in Dec 2015 gold bottomed with positioning the shortest in many years, then broke out of
a range from just below 1100 to 1400 while positioning stretched long. After a two-year range, positioning was shorter than
in 2015 at higher prices: a positive divergence which, with a large rounded base, the authors read as significant upside.

Mirror caution for rates: AM longs and LF shorts mirror each other (Method 4, test 1), so an AM extreme and an LF extreme in
one contract are one signal, not two. Other evidence in this skill is mixed on sign (follow-through for bonds in Willer and
Saunders; follower for fund-return regressions and modest contrarian for CFTC non-commercial in BofA, Mar 2025), so test the
contrarian sign on the contract and window first.

Price-trend state as a confirmation filter (BofA, Technicals Explained, 14 Jan 2025; weekly 13, 26, 40 and 200-week MAs,
slope matters more than the side of the MA; shown on equities, generic):

| State | Definition | Reading |
|---|---|---|
| bullish | close above a rising MA | buy dips |
| bullish at risk | close below a rising MA | watch the long |
| bearish | close below a falling MA | sell rallies |
| bearish at risk | close above a falling MA | watch the short |

Own default pairing: a long-positioning extreme matters as crowded-long risk when the price state moves to "bullish at
risk" or worse; with price still "bullish" and above a rising MA, the extreme alone is not a fade signal. Mirror for shorts.
Apply the states to the contract's price or yield with the sign made explicit (a bond-future price MA and a yield MA point
opposite ways), and to spread or fly series for relative-value legs. Indicator definitions (RSI bands, MACD, TD Sequential,
Ichimoku, Market Profile levels) belong to [macro-technical-analysis](../../macro-technical-analysis/SKILL.md).

Conditioning matters: in the primer's golden-cross event studies, conditioning on the 200-day slope changed results a lot and
sometimes reversed them (oil), with sample sizes often 14 to 17 signals, and the primer calls such crosses "good for context,
not necessarily entry AND exit strategy". Condition a positioning extreme on trend the same way and compare the conditional
hit rate with the unconditional base rate, which the primer's tables do not print.
