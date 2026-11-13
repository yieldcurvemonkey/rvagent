# Trend and momentum systems: crosses, TMAC, weekly states, oscillators, Ichimoku, TD Sequential

Companion to [SKILL.md](../SKILL.md). Source for every section unless marked: (BofA, Technicals Explained, 14 Jan 2025).
Lines marked **(adaptation)** are this skill's reading, not the authors' statement; **(computed)** lines are arithmetic on printed numbers.
Signs: the cross tables below are % changes of a PRICE (futures settle, index), so up = long duration for a bond future. A yield series reads the other way: a
golden cross on a yield is bearish duration.

## 1. Regime to tool map

| State | Tools the primer pairs with it |
|---|---|
| Trending | moving averages, Ichimoku, MACD, ADX |
| Range-bound | RSI, stochastics |
| Parabolic or stretched | candles, TD Sequential, long-term trend lines, divergences, log charts |

Order of work: (1) trending, range-bound, leading or lagging, or overextended; (2) key levels (MAs, trend lines, Fibonacci) across several timeframes; (3) what strategies have worked and their odds;
(4) intermarket ratios, correlations and regressions; (5) flows and breadth; (6) sentiment and positioning (CFTC, surveys, put-call); (7) compare with the fundamental view; (8) make the call with one chart, key levels and risk-reward.
The authors' rule: "first discipline, then conviction": process rules take priority over current conviction, so losers get cut.
Rule of thumb in the primer: rates tend to mean-revert more often, commodities tend to trend longer and stock indices tend to go up, so the oscillator and range tools get more weight on rates than a pure trend system would give, and the MA type should be tested per asset class.

## 2. Moving-average conventions

- 50 and 200 (and 100 and 150) are popular because they were easy to compute by hand. Short-horizon traders use 5, 10, 15, 20, 30, 50. Fibonacci users use 5, 8, 13, 21, 34, 55, 89, 144, 233. Futures traders drop one day from a length for the roll.
- Four generic MA signals: price crosses the MA; the MA's slope turns; a short MA crosses a long one; price is too far from the MA relative to its own history.
- MA fan (20, 50, 100, 150, 200): 20 conditions (5 price-versus-MA, 10 MA-versus-MA pairs, 5 slopes; **(computed)** 5 + 10 + 5). A dispersed, fanned-out set means a strong trend.
- SMA against EMA: the EMA stays closer to price and signals earlier; the primer suggests EMAs may suit commodities better. Test the type for rates.
- Golden cross = 50-day above 200-day; death cross = 50-day below 200-day. A golden cross on an equity-volatility index, a bond future or a JPY cross can imply a bearish risk tone: always say which series.
- Multi-timeframe 200-period averages (hourly, daily, weekly, monthly, quarterly): the US 10y yield's 2016-18 bear market was capped by the 200-month SMA (untested since 1989, double top at 3.25% in 4Q18); the dollar index found support at its 200-month and resistance at its 200-quarter average in 2018-19.
- **(adaptation)** The same four signals can be run on a spread, fly or ratio series. The primer's relative-chart point supports it: tops and bottoms in the relative price often lead tops and bottoms in the absolute price.

## 3. Golden and death cross event studies

Method: the forward % change at 5 to 80 trading days after the signal, with up and down counts, average, median, minimum and maximum, then conditioned on the 200-day SMA slope.
The primer's conclusion: good for context, not necessarily an entry AND exit strategy: used as a black-box entry and exit it gives back much of the trend.
Slope definition used in the source is not given; SKILL.md scripts use `MA_t - MA_{t-1}` (an implementation choice).

| Market (price series, % change) | Signal | Sample | Result |
|---|---|---|---|
| Long bond future, continuous (1977-) | golden cross | 34 signals | higher 68% of the time at 40-50 days (23 of 34 in the table; the text says "23 out of 31"); average +1.44% at 45 days |
| same | golden cross, 200-day rising | 14 signals | up 12 of 14 (86%) at 45-50 days; average +2.49% at 45 days, +2.54% at 50 days; min / max at 45 days -5.10% / +13.42% |
| same | death cross | 34 signals | "little relevance": down ratios 36-53% |
| Dollar index (1979-) | golden cross | 31 signals | up 68-84% at 25-80 days, best at 45 days (84%, 26 up and 5 down) |
| same | golden cross, 200-day rising | 23 signals | up 21 of 23 (91%) at 45 days |
| same | death cross | all | no edge alone |
| same | death cross, 200-day falling | 15 signals | down 73% at 20 and 45 days |
| Crude oil | golden cross | all | up 69% at 45-50 days |
| same | golden cross, 200-day rising | - | bearish for the first 10 days (up only 20-33%) |
| same | golden cross, 200-day falling | - | better: up 81% at 5 days |
| same | death cross, 200-day falling | - | higher 71% at 45 days: the opposite of the signal's intent |
| S&P 500 (1927-) | golden cross | 49 signals | up 59-73% at 10-80 days; 200-day rising: up 76% at 25 days |
| same | death cross | - | not significant; with the 200-day falling, lower at 15-20 days and a rebound around 60 days |

Dated dollar-index sequence (as printed): golden cross on 20 Oct 2016 at 98.31, up to +5.6% at the high; death cross on 26 May 2017 at 97.44 (-0.89% against the golden-cross entry, **(computed)** 97.44/98.31 - 1);
the price then fell as much as 9.43% (Feb 2018). The golden cross on 7 Jun 2018 at 93.43 closed the short with a 4.10% gain, leaving about half the move behind.

Reading: (1) the long bond future golden cross is a usable long-duration context, much better with a rising 200-day; (2) the death cross on that future carries no edge, so do not use it as a stand-alone short;
(3) conditioning on the 200-day slope can reverse the result (oil), and the conditioned samples are small (14 to 23 signals), so quote n; (4) none of the tables gives a significance test or the unconditional base rate: compare with the always-long rate before crediting the signal.

## 4. TMAC (triple moving-average cross, 10, 20 and 30 days)

Nine conditions, each scored +1 (bullish) or -1 (bearish): price against each of the three MAs (3); each MA against each other (3 pairs, shorter above longer is bullish); the slope of each MA (3).
TMAC sum ranges from -9 to +9. **(computed)** With every term at +1 or -1 the sum is odd; the printed thresholds at 6, 2 and 0 only occur if ties score 0, so score a tie as 0 and read thresholds as inequalities.
Example rule sets from the primer:
- Long when the sum is above 0, short when below 0.
- Buy at +9 and add on down days that do not reduce the sum; reduce at 6; exit at 3 (mirror for shorts at -9 and -6; the text says "exit if equals 3", read as "at or below 3").
- Scale in one third at sum >= 3, >= 6 and = 9, and scale out at 5, 2 and 0 (mirror for shorts).
- Filter: trade only when the 200-day slope agrees. Markets that trend less may need a profit-target exit.
`tmac_sum` in `scripts/tech_indicators.py` computes the sum (windows and slope definition are arguments or documented choices).

## 5. Weekly MA states (13, 26, 40 and 200 weeks)

Slope matters more than whether price is above or below the MA. Four states:

| State | Condition | Reading |
|---|---|---|
| Bullish | close above a rising MA | buy dips |
| Bullish-at-risk | close below a rising MA | watch the long |
| Bearish | close below a falling MA | sell rallies |
| Bearish-at-risk | close above a falling MA | watch the short |

Trends are strongest when all timeframes agree. "Trend reversion" is buying dips into rising 26- and 40-week MAs, or re-crosses above the 13- and 26-week MAs while the 40-week trend is bullish (mirror for bearish).
Relative charts against a benchmark: tops and bottoms in the relative price often lead tops and bottoms in the absolute price. **(adaptation)** On a spread or fly series read the state from the series' own MAs and say which side is the receive.
The authors present this for equities; the rates version is untested here.

## 6. Oscillators and divergences

- **RSI.** Ratio of average up-move to average down-move over 14 periods, normalised to 0-100; overbought above 70, oversold below 30. In trends use 40-80 in uptrends and 20-60 in downtrends.
  RSI failing at 60 means the downtrend is intact; breaking above 60 suggests it is ending (mirror at 40). In a range, sell at the top when RSI is at or below prior peaks. A breakout without RSI confirmation is suspect; price and RSI breaking out together signals a new trend.
  Preferred signals are three-troughed bullish and three-peaked bearish divergences, combined with a TD 13 at the third peak and a head-and-shoulders. Overbought or oversold is not by itself a reason to exit.
- **MACD.** Line = EMA12 - EMA26; signal = 9-period MA of the line; histogram = line - signal. A bullish cross below zero and a bearish cross above zero are the signals; a zero-line cross equals the underlying EMA cross.
  Divergences: the three-trough version was the final end of a downtrend, two-trough setups lacked confirmation. A histogram divergence warns of an approaching cross but can be only a short-term counter-trend move.
- **Bollinger.** Bands = 20-period MA +/- 2 standard deviations. Bandwidth = upper - lower, compared with its own MA to label narrow against wide. %B above 1 is above the upper band, 0.5-1 between mean and upper, 0-0.5 between mean and lower, below 0 below the lower band.
  Range regime: trade between the bands. Narrow bandwidth followed by a close outside a band is a breakout trade. Exits: bands excessively wide, price back inside the bands or back at the MA; exiting at the mean often results in a late exit.
  In the primer's example, 7 breaks gave 5 winners and 2 losers, and false breaks occurred even with narrow bands.
- **Stochastics.** %K with %D = MA of %K; overbought 75, oversold 25. A %K/%D cross in the stretched zone is the signal, plus divergences. Example: a slow-stochastic bearish divergence on the long bond future, Jul-Aug 2020.
- **Williams %R.** Range 0 to -100; above -20 overbought, below -80 oversold. Default 14; the authors prefer 28. Act on the exit from the zone; use divergences; on weekly or monthly charts persistent overbought or oversold means do not fight the tape.
  `%R = -100 x (HH - C) / (HH - LL)` over the lookback **(standard formula, not printed in the source)**.
- **DMI and ADX.** +DMI above -DMI means rising. The primer reads ADX below 20 as range, 20-25 as transition and above 25 as trending (SKILL.md Method 1 uses the 20 and 30 thresholds from Aikin; the two sets differ in the upper cut-off, so state which you use).
  ADXR is a moving average of ADX: a trend is starting when ADX below 20 crosses above ADXR, and ending when ADX at a high (about 40) crosses below ADXR.
- **TrendStall.** Rate of change of ADX with an MA and a threshold of 15: above 15 is a strong trend; a declining rate of change while above 15 flags a stall. Example: four stall points on the long bond future during the 2021-22 sell-off.
- **Trender.** An EMA of the midpoint offset by a fraction of ATR, with sensitivity 1 to 10 (default 3). It works as a trailing stop.
- **Fear and Greed indicator.** Spread of two weighted averages of true range, default setting 5; read divergences.

## 7. ATR bands and trailing stops

- True range = max(H-L, |H - previous close|, |L - previous close|); ATR = simple or exponential MA of TR.
- ATR with 2-standard-deviation bands: a spike above the upper band, or an ATR divergence, can mark a turn (the primer's examples are in crude oil).
- ATR trailing stops: short stop = prior high + ATR; long stop = prior low - ATR. Long-horizon holders can use these lines to add to or trim a core position.
- On a yield series the receive is long price: its stop is on the yield side (SKILL.md Method 5).

## 8. Ichimoku

- Conversion line = midpoint of the high and low over 9 periods; base line = midpoint over 26 periods.
- Leading span 1 = (conversion + base) / 2; leading span 2 = midpoint over 52 periods. Both are shifted forward 25 periods to form the cloud; the lagging line (close) is shifted back 25.
- Signals: price leaving the cloud; span crosses; cloud thickness (strength of support or resistance); conversion/base crosses above or below the cloud; the lagging line against price and cloud.
- Needs daily high and low. Use it as a trend-regime tool (SKILL.md Method 1 map) and treat a thick cloud as a level, not a forecast.

## 9. TD Sequential

- Setup "9": nine consecutive closes above (sell) or below (buy) the close four bars earlier. It implies a pause of one to four bars.
- Countdown "13": starts after the setup; 12 bars (not necessarily consecutive) with the close below the low two bars earlier (buy; mirror for sell); bar 13's low must be below the low of countdown bar 8. It warns of a trend change within 12 bars.
- TDST lines: from the setup's highest true high or lowest true low. TD risk level: countdown extreme +/- the largest true range in the countdown.
- Perfection (arrows): for a sell, the high of bar 8 or 9 is at least the high of bars 6 and 7.
- Recycle "R": an extended 22-bar setup. A plus sign delays the 13.
- A 9 near a 13, or signals on both daily and weekly charts, are stronger. The authors pair it with parabolic markets, not with ranges.
- Cap: a counter-trend exhaustion marker is a reason to tighten a stop or not add, not to fade a trend by itself (SKILL.md pitfalls).

## 9b. Relative rotation (RRG)

x-axis = relative-strength ratio (relative trend), y-axis = relative-strength momentum, each centred at 100. Quadrants: Leading (both above 100), Weakening (ratio above, momentum below), Lagging (both below), Improving (ratio below, momentum above); the rotation is clockwise.
Shown with a 12-week trail; the authors weight relative trend above momentum. **(adaptation)** Apply to a set of tenors or curves against a benchmark curve to see which leg is rotating; the source gives no formula for the ratio, so test any construction locally.

## 10. Intermarket confirmation (Dow theory)

Primary, secondary and minor trends; secondary corrections last three weeks to a quarter and retrace one-third to two-thirds. Phases: accumulation, participation, excess, then distribution, participation, panic.
Averages must confirm each other; non-confirmation is a divergence. It is a confirmation signal, not an early one. **(adaptation, not the authors')** The same idea applied to rates is cross-market confirmation, for example whether a Treasury high is confirmed by a Bund high.
