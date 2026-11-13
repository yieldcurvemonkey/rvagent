---
name: macro-technical-analysis
description: Technical, trend, momentum and event-timing overlays for G10 rates relative value (govvies, swaps, STIR and bond futures, curve and fly spreads; USD EUR GBP JPY CAD AUD NZD CHF SEK NOK). Covers moving-average trend and crosses (55d, 200d, golden or death cross, TMAC, weekly MA states), 1m/12m momentum consensus, RSI, MACD, Bollinger, stochastics, ADX regime, ATR stops, Ichimoku, TD Sequential, Market Profile, chart patterns, support, resistance, Fibonacci and Elliott levels, yield momentum dummy, CTA stop-out flows, positioning triad (MAA), COT extremes, skew-change timing and rule-based timing after sell-offs, inversions, FOMC and payrolls. Use when the user asks about trend, momentum, overbought or oversold, RSI, MACD, moving average, golden cross, breakout, head and shoulders, Ichimoku, TD Sequential, Market Profile, support or resistance, chart levels, technical entry or exit, is the trend intact, stop placement, CTA flows, or whether a rates trade is technically confirmed.
---

# Macro technical analysis for G10 rates RV

Technical tools in rates behave differently from equity technicals. Bond yields mean-revert more often and trend less
than commodities or equities (BofA, Technicals Explained, 14 Jan 2025), and the tools are only as good as the sign convention and regime they are applied in. This
skill turns the tools into testable overlays: a trend or momentum read to confirm, size or time an RV idea that another
skill has already found. It is not a stand-alone signal. Most published rules for rates show modest information ratios,
large sensitivity to parameters, and gains that come mainly from lower volatility rather than higher return.

## When to use
- A trader asks whether a rate, curve, fly or swap-spread trade is "technically confirmed", or whether the trend is still intact.
- RSI, MACD, Bollinger, ADX, ATR, moving-average crosses, golden or death crosses, breakouts, support or resistance,
  Fibonacci levels, or "where is the stop" for a rates position.
- Timing an entry or exit after a sell-off, an inversion, a policy meeting or a payrolls print.
- Whether trend-following (CTA) flows or stop-outs could push a level through a technical support or resistance.
- Choosing between a trend rule, a mean-reversion rule and no technical overlay for a given market regime.
- Chart patterns (head and shoulders, double top, cup and handle), Ichimoku, TD Sequential exhaustion counts, Market Profile levels,
  or a golden or death cross read together with the slope of the 200-day average.

## Inputs (data-agnostic)

| Input | Canonical table | Granularity and history | Notes |
|---|---|---|---|
| Futures settlement prices, continuous and back-adjusted at rolls | `fut_quotes` (bond futures) or `stir_quotes` (price = 100 - rate) with `fut_static`; continuous via `roll_map` | daily settle, at least 300 days for the 252-day consensus | `price_px` in decimal price per 100; back-adjust additively (price differences) with the roll rule in fut-calendar-roll, never splice raw contracts. A STIR price rises when the rate falls (price basis = long duration). Yield-quoted contracts leave `price_px` null: they are a yield series, so apply the yield sign and no percentage filters |
| Daily high and low (for ATR and ADX) | not in the canonical tables | daily | ask the data adapter for OHLC (also needed for Ichimoku, TD Sequential and Market Profile: period highs and lows, intraday for finer profiles); without it use the close-only fallbacks in Method 1 and 5 |
| Par swap rates by tenor | `curve_par` (`start = 0D`) | daily EOD, at least 300 days | `par_rate_pct` is percent; convert to bp (x100) before any bp rule |
| Zero rates and discount factors | `curve_zero` | daily, same snap as `curve_par` | use `zero_rate_pct` for zero-rate triggers |
| Spreads and flies | built from `curve_par` or read from `swap_spreads` | daily | state the spread sign convention in the output (section Method 0) |
| Policy meetings and event calendar | `cb_meetings`, `calendars` | scheduled dates with decision timestamp | the event-day rules need the decision timestamp, not the date |
| Macro releases with consensus | `macro_series` (`value`, `consensus`, `pub_ts_utc`) | one row per release vintage | use the first release for event-surprise rules |
| Implied and normal vol | `vol_surface`, `opt_quotes` | daily, `nvol_bp` | for vol-scaled stops; the 25bp risk reversal is `nvol_bp` at `strike_offset_bp` +25 (payer) minus -25 (receiver), expiry 3M, tenor 10Y |
| Positioning | `positioning` | weekly | used only as a confirmer (including CFTC-style extremes), see section Method 7; the release time, not the position date, is the signal time |

If a series is missing, short or unadjusted at rolls, ask for it or hand off to the data adapter. Never fill in numbers.
The -25 and +75 economic-surprise thresholds are in the units of the index used in the source; rescale them to the index you hold before use. Every signal is computed on data up to the close of day t and traded at t+1 or later.
Minimum history: 252 trading days for the 1m/12m consensus, 200 days for the 200-day MA, 5 years for any level z-score,
and at least 25 episodes before an event rule is reported as evidence.

## Method

**0. Fix the sign and unit before any rule.** Every signal must say which series it reads.
- Price index (futures settle, total-return index): `+1` means bullish price = yields falling = long duration (receive).
- Yield series in bp: a raw rule on the yield (above its average, RSI high) reads yields up = bearish price, so invert it before using a price-based rule. The yield momentum dummy (Method 3) is already in duration terms: `+1` = yield below its MA = bullish price.
- Spread series `A - B` (for example 2s10s = 10y - 2y, bp): a rising spread is a steepening. A trend long is "receive
  the short leg, pay the long leg" only if the trade is defined that way. Do not mix directions across the same chart.
- Fly `2 x mid - wing1 - wing2` (for example 2s5s10s = 2 x 5y - 2y - 10y): positive means the belly is cheap (high yield).
- Units: yields and spreads in bp; MA and oscillator values in the series' own units; ATR in the same unit as the series.

**1. Regime first.** Decide whether the series is trending, range-bound or stretched, then choose the tools. Trend rules
are the tools for a trend, oscillators for a range. Using a trend tool in a range, or the reverse, is a common error.
- Wilder ADX(14) (Wilder, 1978): below 20 = trendless (use range tools, RSI and Bollinger); above 30 = trending (use MA
  trend rules). The 20-30 band is a transition: no rule, reduce size (Aikin, 2012 for the 20 and 30 thresholds; the 20-30 band is heuristic).
  ADX needs daily high and low. On close-only data it degenerates to a smoothed `|2 RSI - 100|` and the thresholds do not apply
  (simulated pure random walk: above 30 about 10% of the time), so for a close-only series classify the regime with a variance
  ratio or Hurst test (quant-mean-reversion-ou) or quant-regime-detection.
- ADX is a lagging classifier. In Aikin's 2011 Euribor example, ADX flagged the end of a trend better than moving averages
  did. Use it to classify the regime, and confirm any exit with the MA slope, not with ADX alone.
- Confluence: a signal counts when price, the trend horizon and the event context agree. Several indicators on the same
  price are one piece of evidence, not several.
- Regime-to-tool map (BofA, Technicals Explained, 14 Jan 2025): trending markets take moving averages, Ichimoku, MACD and ADX; range-bound markets take RSI and stochastics;
  parabolic or stretched markets take candles, TD Sequential, long-term trend lines, divergences and log charts. The primer reads ADX below 20 as range,
  20-25 as transition and above 25 as trending, with ADXR (a moving average of ADX): a trend starts when ADX below 20 crosses above ADXR and ends when ADX
  at about 40 crosses below it. That set differs from the 20 and 30 cut-offs above only at the upper end: state which one you use. Because rates mean-revert more
  often, range tools carry more weight on rates than on commodities. Full map in [references/trend_momentum_systems.md](references/trend_momentum_systems.md).

**2. Trend and moving averages.**
- Default lengths: 55-day MA for the medium trend (about 2.5 months); 200-day MA for the regime. The 55-day rule on a
  7-10y index beat buy-and-hold on drawdown (Willer & Saunders, 2026). 50/200 is the standard cross: 50-day above 200-day is
  a "golden cross" on a price series, and the reverse on a yield series.
- Trend rule: long duration (`+1`) if price is above a rising 55-day MA; short (`-1`) if below a falling one; flat if the
  slope disagrees with the price. The slope condition is a common whipsaw filter (heuristic); test it with and without.
- Short MAs load on autocorrelation; long MAs load on drift. Expected return of a trend rule with no drift:
  `E(r) = sqrt(2/pi) x sigma x rho`, where `rho` is the correlation between next-period return and the trend forecast
  (Dunis, Laws & Naim, 2003, after Acar, 1994). With daily sigma 5bp and rho 0.05, expected gain is 0.20bp a day. Compare
  any trend result to this, not to zero.
- A total-return index embeds carry and rolldown, so it drifts up and sits above its MA more often than the same bond's yield or an
  additively back-adjusted futures series. The 55-day result in example 1 is for a TR index; do not assume it transfers to a futures series.
- Vol filter (Dunis, Laws & Naim, 2003): an EMA(50) trend rule switched off when a two-state Markov-switching filtered vol exceeds a threshold
  turned -4.9% into +15.4% after costs and cut max drawdown from 19.4% to 10.4%, at 253 trades against 65 (one FX sample, USD/DEM 1995-98). Time-series momentum is documented across asset classes at
  1 to 12 month horizons (Moskowitz, Ooi and Pedersen, 2012, external).
- Use EMA when speed matters: `EMA_t = (1 - a) EMA_{t-1} + a x_t`, `a = 2/(span+1)`. Span 49 is the 50-day EMA (mu = 0.96).
- The trend is a regime filter, not a timing tool. Crosses are useful context; as a stand-alone entry and exit they
  give back much of the trend (BofA, Technicals Explained, 14 Jan 2025: good for context, not necessarily an entry and exit strategy).

**2b. Cross conditioning, TMAC and weekly states** (BofA, Technicals Explained, 14 Jan 2025).
- Condition every golden or death cross on the slope of the 200-day. On a long bond future (price, from 1977), 34 golden crosses were higher 68% of the time at 40-50 days
  (average +1.44% at 45 days); with a rising 200-day (14 signals) 12 of 14 (86%) were up at 45-50 days, average +2.49% at 45 days. The 34 death crosses had down ratios of only 36-53%:
  no stand-alone short signal. A dollar-index golden cross with a rising 200-day was up 21 of 23 (91%) at 45 days; in oil the slope conditioning reversed the result. Tables, small samples
  and the source's own inconsistencies are in [references/trend_momentum_systems.md](references/trend_momentum_systems.md).
- TMAC (10, 20 and 30-day): nine conditions scored +1 or -1 (price against each MA, each MA against the others, each slope), sum -9 to +9. Long above 0 and short below 0; or scale in thirds at a sum of at least 3,
  6 and 9 and out at 5, 2 and 0, trading only when the 200-day slope agrees. Ties score 0, so the printed thresholds can occur (`tmac_sum`).
- Weekly MA states (13, 26, 40 and 200 weeks): slope matters more than position. Close above a rising MA is bullish (buy dips); below a rising MA bullish-at-risk; below a falling MA bearish (sell rallies);
  above a falling MA bearish-at-risk. Trends are strongest when all timeframes agree. The primer shows it on equities: test it on the rates series.
- Long-horizon averages are levels too: the 200-month SMA capped the 2016-18 US 10y yield bear market at about 3.25%. An MA fan (20, 50, 100, 150, 200) gives 20 conditions and a fanned-out set means a strong trend;
  the EMA signals earlier than the SMA, so test the type per asset class.

**3. Momentum consensus and yield momentum dummy.**
- Consensus on a price index (JPM, 2012): `+1` if above both SMA21 and SMA252; `-1` if below both; `0` otherwise.
  In a secular bull market bond momentum was long about 80% of the time, and the 12m single-horizon rule 77%: that is the baseline to
  beat, so an IR from such a rule has little skill content on its own (J.P. Morgan, 2012 and 2015).
- Yield momentum dummy (Salomon Brothers, 1995): on a yield in bp, `+1` if the yield is more than 5bp below its six-month
  MA, `-1` if more than 5bp above, `0` inside the 10bp range around the MA. The 10bp neutral range is the whipsaw filter.
  The source sampled month-end (six-month MA, n = 6). The 5bp band is in level space, so on daily data (126-day MA) it is tiny against
  the typical deviation and no longer filters whipsaw: prefer month-end sampling or scale the band to the series' vol (heuristic).
- The dummy was one of four predictors (with term spread, real yield, inverse wealth). The out-of-sample figures belong to the
  four-predictor forecast, not to the dummy alone: correct sign in 61% of months (expanding window from 1955, first forecast 1965) and correlation 0.57 with the next 12-month excess return.
  In-sample the dummy coefficient had t 2.02, marginal. The authors attribute the gap between in-sample and out-of-sample returns to data snooping.

**4. Oscillators, for range regimes or as confirmation.**
- RSI(14) (Wilder): `RSI = 100 - 100/(1 + avgGain/avgLoss)`, Wilder smoothing alpha = 1/14. Standard bands 70/30.
  Applied to a yield series, a low RSI means yields have fallen fast and the receive is crowded ("over-received"); a high RSI
  means the reverse. A 2019 EUR note called the short end "technically overreceived" on RSI; a 2020 EUR 10y reading of 36.93
  was neutral (Nordea Markets, 2019 and 2020).
- In a trend, shift the bands (BofA, Technicals Explained, 14 Jan 2025): 40-80 in an uptrend, 20-60 in a downtrend. A pullback that
  holds above the lower band is trend continuation, not a sell signal. RSI failing at 60 in a downtrend (40 in an uptrend) means the trend is intact; breaking it suggests the trend is ending.
- Divergence: a three-trough bullish or three-peak bearish divergence in RSI, stochastics or the MACD histogram is the preferred signal; a two-trough divergence is often premature (BofA, Technicals Explained, 14 Jan 2025).
- Stochastics (%K, %D; 75 and 25) and Williams %R (above -20 overbought, below -80 oversold; the authors prefer 28 periods) are range tools: act on the exit from the zone, not the entry (BofA, Technicals Explained, 14 Jan 2025).
- Overbought is not an exit. Nordea (26 Sep 2025) cited overbought RSI and crowding for a receiver, and its rule was to
  re-underwrite a position near its stop when the forecast changes. RSI alone is not the reason to close.
- MACD: `line = EMA12 - EMA26`, `signal = EMA9(line)`. The zero-line cross equals an EMA cross, so it adds no information
  beyond the trend. Use the histogram only as a momentum-turn flag.
- Bollinger(20, 2): mid = SMA20, bands = mid +/- 2 sample SD20. Narrow bandwidth followed by a close outside a band is a
  breakout candidate (Aikin, 2012 notes bands narrowing before large moves). Exit at the mean is late (BofA, Technicals Explained, 14 Jan 2025); use the opposite band
  or a time stop. %B above 1 is outside the upper band, 0.5-1 between mean and upper, 0-0.5 between mean and lower, below 0 outside the lower band.

**5. Levels, patterns and stops.**
- Support is prior demand, resistance is prior supply. Labels are in price terms; sources disagree on yield charts (one calls lower yields
  "resistance", another "support"), so write the level as a yield and say which side is the rally. Levels with more tests, on a longer timeframe and in a wider zone
  matter more (BofA, Technicals Explained, 14 Jan 2025: time, number of tests, depth (a 3-4% zone beats 1%) and volume; broken resistance becomes support). Use the pattern objective or a Fibonacci extension as the target and a level
  just beyond the last swing as the stop.
- Trend-line break needs a filter, because a single close through a line is often noise (BofA, Technicals Explained, 14 Jan 2025). Require any of: a
  close beyond the line by 1% (price index) or by more than one ATR, above-average volume, two consecutive closes
  beyond, or a failed retest on lighter volume. A good line has several touches spaced in time and a slope of about 30 to 50 degrees; draw it on a log chart
  if price is more than 30% from the start. A fraction of an ATR (for example 0.5 x ATR in bp) is a tighter heuristic of this skill, not the primer's.
- Measured move: subtract the height of the prior move from the breakout point (BofA, Technicals Explained, 14 Jan 2025).
- Fibonacci retracements (38.2%, 50%, 61.8%) of the last major swing, drawn only from major turning points. Ratios 23.6, 38.2, 50, 61.8 and 76.4%: from a top `level = High - r x (High - Low)`, from a bottom `Low + r x (High - Low)`; extensions 100, 161.8, 300 and 361.8% of the pattern height (BofA, Technicals Explained, 14 Jan 2025). They are
  reference levels, not forecasts (no quantitative test in the sources).
- Stops: `stop = entry - k x ATR14` for a long and `entry + k x ATR14` for a short of the SERIES TRADED (`k` = 2 is a common default,
  heuristic). On a yield series a receive is long price, so its stop is the entry yield `+ k x ATR` and a pay's is `-`. ATR: `TR = max(H-L, |H - prevC|, |L - prevC|)`.
  For a close-only series `TR = |dP|`, which is only about half the OHLC value (0.8 vs 1.6 sigma): double it, or use `k` = 4. A stop at a
  structural level is preferred when it is tighter than the ATR stop.
- Futures levels are contract-specific: a CTD switch changes the futures price-yield map, so a level read on one contract or basket does not carry across a roll or switch (During, 2021). Technical analysis has no systematic false-positive analysis and can be self-fulfilling, so treat levels as places other participants watch, not as forecasts.
- Sizing and scale-in: scale in and out by thirds, using structural levels as stops, not the mean (BofA, Technicals Explained, 14 Jan 2025).
- ATR trailing stops (BofA, Technicals Explained, 14 Jan 2025): long stop = prior low - ATR, short stop = prior high + ATR, raised or lowered as the trend moves; a spike in ATR above its own 2-SD band or an ATR divergence can mark a turn.

**5b. Pattern reads** (BofA, Technicals Explained, 14 Jan 2025); rules, targets and cases in [references/patterns_levels_and_structure.md](references/patterns_levels_and_structure.md).
- Head and shoulders needs a prior trend, three peaks with the head highest, a flat or slightly sloping neckline, a right shoulder no bigger than the left and a decisive neckline break. The retest on light volume is the second
  entry, the stop is the right-shoulder high, the target is the head-to-neckline height from the break. Both the 50% and 61.8% retracements reached is "high conviction". On the US 10y yield an early-1980s monthly top
  marked the start of the secular bond bull market and a 2019-2022 bottom its end (confirmed in 2022).
- Double top or bottom: target is the pattern height; scale in by thirds (speculative after the second turn, on the confirmed break, on the retest). Cup and handle: the handle retraces 38.2-50% (at most 61.8%) of the
  cup rally and the target is the breakout plus the cup depth.
- Outside reversal (engulfing) needs a prior trend and is stronger above a rising 200-day or at a level, with RSI stretched and volume rising on bar 2. Candles (doji, hammer, harami, piercing line, stars) only
  confirm a level. An island reversal is an exhaustion gap plus a breakaway gap.
- Patterns are drawn in price terms: on a yield chart mirror them and write levels as yields. On a futures series a roll gap is not a pattern gap.

**5c. Exhaustion and trend-state systems** (BofA, Technicals Explained, 14 Jan 2025); formulas in [references/trend_momentum_systems.md](references/trend_momentum_systems.md) and [references/patterns_levels_and_structure.md](references/patterns_levels_and_structure.md).
- Ichimoku: conversion line = 9-period midpoint, base line = 26-period midpoint; leading spans = their average and the 52-period midpoint, shifted forward 25 periods to form the cloud; the lagging line is shifted back 25.
  Signals: price leaving the cloud, span and conversion/base crosses, cloud thickness as support or resistance. Needs high and low.
- TD Sequential: setup 9 = nine closes beyond the close four bars earlier (a pause of one to four bars); countdown 13 = twelve bars with the close beyond the extreme two bars earlier, with bar 13 beyond countdown bar 8.
  TDST lines and the TD risk level give stops. A 9 near a 13, or signals on daily and weekly together, are stronger. Use it to tighten a stop or stop adding, not as a stand-alone fade.
- Trender (an EMA of the midpoint offset by a fraction of ATR) works as a trailing stop. TrendStall (rate of change of ADX; above 15 is a strong trend, a falling rate of change above 15 flags a stall) marked four stalls on the long bond
  future in the 2021-22 sell-off.
- Elliott: five waves with the trend then a-b-c; wave 2 stays above the start of wave 1, wave 3 is not the shortest, wave 4 does not overlap wave 1 (futures are lenient). Use a wave objective only with a level that agrees.
- Relative price and confirmation: tops and bottoms in a relative (spread or ratio) price often lead the absolute price, and Dow-style confirmation signals come late by design.

**5d. Market Profile levels** (BofA, Technicals Explained, 14 Jan 2025); examples in [references/patterns_levels_and_structure.md](references/patterns_levels_and_structure.md).
- A distribution of price over time: markets move slowly through time when range-bound and fast through price when trending. The point of control (POC) is the price reached most often (time at price, not volume);
  the value area holds 70% of the distribution; the initial balance is the first two periods.
- Trading above the initial balance or the value-area high suggests an uptrend may start, below suggests a downtrend. A double distribution tends to fill its gap, with targets at the value areas and POCs. Overlapping POCs
  and value-area edges across about ten profiles mark confluence. Price moving too far too fast into a key level is a reversion trade. Build profiles on the traded futures contract and re-draw after a roll.

**6. Event and cycle timing (rule-based; compute the statistic, do not eyeball it).**
- Sigma on an event day: the move divided by the standard deviation of the previous 21 daily changes, today excluded (`sigma_move_rolling`; the EWMA
  `sigma_move` is a smoother stand-in). Trade the next session, never the print itself.
- FOMC: score the meeting by the 2y move on the day, not by the statement. A 2-sigma move versus the trailing one-month
  distribution is the trigger (Willer & Saunders, 2026). Dovish 2-sigma moves had a positive, persistent median return.
- Payrolls: a 2-sigma or larger 10y move on the day is the trigger. Bullish 3-sigma events had a median 20-session return above 1%.
  Bearish prints were not a reliable signal to pay, even in hiking cycles.
- Sell-offs: a 10y sell-off of more than 70bp since 2000 had a median size of 120bp over about 135 days. Calling peaks paid
  better than calling troughs. A 2y breakeven decline about a month before the peak and a 5s30s flattening were the
  leading signs in that study. Use these as a checklist (sample about 20 episodes).
- Inversion-to-cut: inversion = longer minus shorter yield at or below -12.5bp (6m2s: `2y - 6m <= -12.5bp`). After a 6m2s inversion a cut came within 12 months
  73.7% of the time (Willer & Saunders, 2026). The source tests ten curve measures (3m10s to 10s30s): the median across the ten is 65.0% within 12 months and 93.3% within 24 months, and
  2s10s scored poorly (57.1%). 6m2s is one of the best of ten measures, so its 73.7% is selection-inflated; 2s5s (73.3%) and 10s30s (72.2%) were as good. Small samples: a prior, not a trigger.
- "No more hikes" or "no more cuts": 6m-ahead minus 1m-ahead policy-rate spread below -12.5bp (at least half a 25bp cut priced
  six months out). It failed in March 2023, when inflation was above 5% and the Fed raised 75bp over six months.
- Skew change (Citi Research, 2017): 3-month change in the 3m10y 25bp risk reversal (payer minus receiver normal vol), bucketed by its percentile
  (the source used full-sample percentiles, 2006-2016: in live use compute them on an expanding window, otherwise the buckets look ahead). Above the
  75th percentile the next month's 10y yield change averaged +8.8bp (median +11.1bp); below the 25th averaged -11.5bp.
  The edge is in the tails. Use it as a warning, alongside positioning (see vol-skew-and-tail-hedging).
- Economic surprise trend (Willer & Saunders, 2026): receive 5y when the surprise index is below -25, pay above +75; return/vol 0.53 against
  0.26 for the 5y swap alone, active IR 1.01, in the market 27.5% of the time. Counter-indicator fading the extremes failed.
- Hiking-cycle timing (Willer & Saunders, 2026): 2y returns turned poor about 55 to 75 trading days before the first hike; pay the 2y about three months before it;
  press receivers about three months before the first cut. Cycle dating belongs to macro-central-bank-reaction-functions.
- Calendar priors (BofA, Technicals Explained, 14 Jan 2025): on the US 10y yield since 1963, a January rise was followed by higher yields in February-March 70% of the time (average +34bp), but February-March was up in 66% of all years (computed),
  so the edge over the base rate is small; after a rise in the first five days yields tended to fall in the rest of January. The January, first-five-day, presidential-cycle and dollar-index tables are in
  [references/positioning_flow_and_calendar.md](references/positioning_flow_and_calendar.md). Treat them as a soft prior: no significance tests, small samples, and the primer shows the S&P 500 January barometer decaying from 80-90% before 2000 to 50-60% since.

**7. Flow and positioning overlay (confirmer only).** Trend-follower flows are largest when many trend models share a signal and an
unwind trips stops together.
- Stop-out ensemble: a twelve-model ensemble (three lookbacks x four stop thresholds; short-term = MA crosses of 21 to 100 days, long-term = crosses of 50 to 252 days, medium = equal weight; risk-parity sizing; a stop is a prescribed loss
  from a high-water mark). Days on which at least 4 of 12 models stopped out had above-average absolute sigma moves across equity index, Treasury, Bund, commodity and FX futures, 2010 to May 2025
  (BofA, Systematic Flows Monitor, 2 Jun 2025). The largest flows come from unwinds, not accumulation. The models are proxies of real CTAs, and the benchmark index has survivorship bias. Check the positioning
  table and the level where trend models would change sign.
- Top-down CTA positioning (BofA, CTAs impact on the rates market, 18 Aug 2020): regress a benchmark CTA index's returns on the first principal component of each asset set (equities, longer bonds, shorter bonds, metals,
  energy, FX or the dollar index) over a rolling 2-month window. The long-duration beta is the duration bias; long-duration beta against short-duration beta is the curve bias (long the long feature and short the short is a flattener).
  The week-on-week change in beta is the flow signal. Cross-checks: a 15 to 20 day lead-lag against a multi-crossover momentum signal, and about 60% correlation with CFTC net non-reportable 10y futures positions.
- Positioning triad (BofA, FX Quant Primer, 1 Oct 2018; FX-derived, untested on rates): MAA = share of the 28 pairwise cross signals that are bullish among the price and its 5, 10, 20, 30, 50, 100 and 200-day averages (`ma_aggregator`);
  uptrend above 60, downtrend below 40. With the percentiles of up/down vol (UD) and residual skew (RS), a reversal is likely when all three are above 80 in an uptrend or below 20 in a downtrend, and unlikely when UD and RS are
  below 50 (uptrend) or above 50 (downtrend). Stretched trends hold when the direction of vol agrees with the trend. A rates version of the skew leg uses the 25bp risk reversal from `vol_surface` against yield changes (adaptation).
- CFTC extremes (BofA, Technicals Explained, 14 Jan 2025): the speculative net position as a share of open interest beyond 2 standard deviations of its mean is a contrarian flag, used only with price-trend confirmation; a divergence between the price trend and
  the positioning trend can flag a turn.
Do not fade trend-follower positioning on its own. The flow mechanics belong to flow-positioning-cftc-and-surveys. Model definitions, validation and statistics are in [references/positioning_flow_and_calendar.md](references/positioning_flow_and_calendar.md).

**8. Test before reporting.** A technical overlay is accepted only after this test.
- Event study: for each signal `s_t != 0`, compute `s_t (x_{t+1+h} - x_{t+1})` (entry one session after the signal) at h = 5, 20, 45, 80 days; on a yield series with a
  duration-sign signal flip the sign of the change. Report n, the mean signed change in bp, and the hit rate. Compare to the always-long or always-short base rate, not zero.
- Overlap: consecutive daily signals share most of their forward window, so n counts overlapping windows. Independent evidence is about n / h; use that, a block bootstrap or HAC errors
  for any t-statistic, and never read a hit rate at h = 80 on 300 overlapping days as 300 trials.
- Information ratio of the signal against being always long (or the unconditional base rate). A high IR that is just
  "long most of the time" is not skill.
- Rebalance-day and parameter sensitivity: report a range across neighbouring lookbacks and rebalance days. Momentum IR moved
  from 0.3 to 0.7 across rebalance days in one study.
- Costs and roll: re-run after costs of the instrument, including roll for futures.
- Out of sample: fix the rule before the test window. Never re-fit after seeing the out-of-sample result.

**9. Hand-off.** A technical overlay answers "confirm, neutral or against" for an idea and a timing or stop level. The
idea itself comes from an RV screen. Pass the result to rv-composite-scoring (as one input, not a double count),
rv-devils-advocate (what would make the trade wrong) and rv-trade-idea-writeup.

## Worked examples

Figures are as printed in the cited source unless marked "computed".

1. **Trend rule on a 7-10y index (Willer & Saunders, 2026).** 55-day MA: return 2.41%, vol 4.68%, return/vol 0.52, max drawdown
   -13.35%, in market 57%. Buy and hold: 2.59%, 6.29%, 0.41, -27.48%. The rule earned about the same return with about 25% less
   vol and half the drawdown. The 252-day MA only broke even with buy and hold.
2. **Momentum consensus by horizon (J.P. Morgan, 2012).** Information ratios by market (US, JP, EA, UK, combined):
   1m 0.51 / 0.48 / 0.20 / 0.00 / 0.41; 12m 0.42 / 0.53 / 0.52 / 0.42 / 0.62. The 12m horizon was long 77% of the time, so the IR
   must be read against "always long". The 3m IR moved between 0.3 and 0.7 with the rebalance day.
3. **Yield momentum dummy (Salomon Brothers, 1995).** Coefficient 0.34 (t 2.02) in a 1965-95 regression alongside term spread,
   real yield and inverse wealth. The four-predictor forecast, not the dummy alone, was correct in sign in 61% of months out of sample, and a 1/0 strategy
   on it (hold the 20y bond if the forecast is positive, else cash) had Sharpe 0.53 against 0.06 for always holding the bond.
4. **RSI reading on a yield (Nordea Markets, 5 Feb 2020).** EUR 10y RSI 36.93 on 70/30 bands: neutral, not oversold. The note's
   support was -6.5bp and a close above 0bp was a return to a 0-23bp range. Read: no RSI signal, use the level.
5. **Sigma move on a 10y yield (computed).** A 3bp day after EWMA sigma 1bp (lambda 0.97) gives sigma = 3. Treat any day above
   2 sigma as an event-rule candidate, not a trend signal.
6. **Momentum dummy (computed).** 10y yield 425bp, six-month average 412bp: deviation +13bp, above +5bp, so the dummy is `-1`
   (bearish price) even though the yield is only 13bp above its average.
7. **Expected return of a trend rule (computed).** Daily sigma 5bp, rho 0.05, no drift: E(r) = 0.798 x 5 x 0.05 = 0.20bp per day.
8. **Event-study sign (computed).** A 10y yield falls 1bp a day and a duration signal is +1. Over h = 5 the signed change must be +5bp (`x_is_yield`), hit rate 1. Without the flip
   the same signal shows -5bp and a hit rate of 0: the usual symptom of a yield read as a price.
9. **Golden cross with a rising 200-day (BofA, Technicals Explained, 14 Jan 2025).** Long bond future, 14 signals: up 12 of 14 (86%) at 45-50 days, average +2.49% at 45 days, against +1.44% over all 34 golden crosses. The always-long base rate is not printed:
   read the result as a context filter.
10. **TMAC sum (computed, windows shortened to 2, 3 and 4 for hand arithmetic).** Series 1, 2, 3, 4, 6, 5: price 5 is below MA2 5.5 (-1), equal to MA3 5.0 (0) and above MA4 4.5 (+1); MA2 > MA3 > MA4 (+3); all three MAs rising (+3). Sum = +6.
11. **MAA (computed).** 25 of the 28 pairs bullish gives MAA 89%, above 60: an uptrend. With UD at the 85th and RS at the 90th percentile all three are above 80, so a reversal is likely and a long needs a tighter stop.
12. **Fibonacci bounce (computed).** A 10y yield falls from 4.50% to 3.50%. The 38.2% bounce is 3.50 + 0.382 x 1.00 = 3.882% and the 61.8% bounce is 4.118%: yield levels where a rally would be tested.
13. **Calendar base rate (computed).** US 10y yield, 61 Januarys: a rise in January was followed by a rise in February-March in 23 of 33 cases (70%), but February-March rose in (23 + 17) / 61 = 66% of all years, so the edge over the base is about 4 points.
14. **Range from scenario levels (BofA, 10y rates and the Monty Hall problem, 6 Aug 2024).** Range top at the soft-landing level (4-4.25%), bottom at the midpoint between the hard-landing level (3%) and the soft-landing level: about 3.5%.
    The top and bottom are re-drawn when a new fact removes scenarios (here an early first Fed cut). Scenario likelihoods belong to macro-regime-and-scenario-analysis.

## Signals & interpretation

| Read | Threshold or condition | Action |
|---|---|---|
| Consensus (price) | +1 (above SMA21 and SMA252) | confirms a long-duration or receive idea |
| Consensus (price) | 0 (horizons disagree) | neutral; do not add; expect late turns |
| 55d / 200d trend | price above rising MA (price basis) | trend confirms long duration |
| Yield momentum dummy | +1 / -1 / 0 at +/-5bp of six-month MA (month-end data) | +1 bullish price; -1 bearish price; 0 no view |
| ADX(14), needs high and low | below 20 / above 30 / between | range tools / trend tools / no rule, cut size |
| RSI(14) on yield | below 30 | over-received (yields fell fast): a pay idea needs a level or event confirmation |
| RSI(14) on yield | above 70 | over-paid (yields rose fast): a receive idea needs a level or event confirmation |
| Bollinger bandwidth | narrowest in 6 months, then a close outside | breakout candidate, confirm with trend |
| Inversion (6m2s) | `2y - 6m` at or below -12.5bp | prior for a cut within 12 months (65% median of ten measures, 74% for the best) |
| FOMC day move | 2y move at least 2 trailing sigma | receive after dovish, pay after hawkish, backtest first |
| Payrolls day move | 10y move at least 2 sigma | triggers a 10y position after bullish, not bearish, prints |
| 10y sell-off | more than 70bp from the low | run the peak checklist (breakevens, 5s30s, oil); no timing rule is given |
| Skew change percentile | above 75th / below 25th | payers richening (yields up next month) / flattening (yields down); tail-edge warning only |
| Economic surprise index | below -25 / above +75 | receive / pay 5y (with IR and time-in-market caveats) |
| Golden cross, price series | 50d above 200d, 200d rising | long-duration context (long bond future: 86% up at 45-50d); not an exit rule |
| Death cross, price series | 50d below 200d | no stand-alone edge on a bond future (down ratios 36-53%); condition on the 200d slope |
| TMAC sum | above 0 / below 0; extremes at +9 / -9 | trend long / short; scale by thirds; the 200d slope must agree |
| Weekly MA state | close above or below a rising or falling MA | bullish / bullish-at-risk / bearish / bearish-at-risk; buy dips or sell rallies by state |
| MAA with UD and RS (FX-derived) | all above 80 in an uptrend, all below 20 in a downtrend | reversal risk; UD and RS below 50 in an uptrend means the trend is likely to continue |
| Net speculative position, share of open interest | beyond +/-2 SD of its mean | contrarian flag, needs price-trend confirmation |
| Trend-model stop-outs (12-model ensemble) | 4 or more stopped out | above-average sigma moves: flow-driven unwind risk; review stops |
| TD Sequential | setup 9, countdown 13 | tighten the stop or stop adding; not a stand-alone fade |
| Market Profile | price above initial balance or value-area high / below | an uptrend may start / a downtrend may start; POC and value area are the targets |

Interpretation rules: a technical signal confirms only when it agrees with the RV signal's direction and horizon. A signal
that disagrees is a reason to reduce size or wait, not to flip the trade, unless a stop has been hit.

## Pitfalls
- **Sign and series errors.** A golden cross on a price is bullish duration; on a yield it is bearish duration. Always say
  which one. Mixing a spread direction with a price direction reverses the trade.
- **Regime errors.** Trend rules that work in easing cycles fail in hiking cycles and in inflation shocks (the cyclicals rule
  failed in 2022). Switch off or re-test the rule in the regime.
- **Overbought is not an exit.** RSI and Bollinger extremes can persist for long periods in a trend. Use them for range trades only.
- **Base rates.** A 75% hit rate in a bull market can be "long most of the time". Compare with always-long and with the
  unconditional base rate.
- **Parameter fragility.** Momentum IR moved from 0.3 to 0.7 with the rebalance day. Report a range and avoid a lonely peak.
- **Small event samples.** Inversion, sell-off and FOMC rules rest on 2 to 20 episodes. Quote n every time. Overlapping forward windows inflate n; quote n / h.
- **Selection and in-sample percentiles.** The best of ten curve measures, full-sample percentile buckets and a threshold picked after seeing the data all overstate the edge.
- **Costs and roll.** Most published trend results ignore costs. A futures series that is not back-adjusted at rolls
  creates false signals at each roll date; re-run after costs and roll.
- **Lag.** Simple moving averages add lag; a stop at a moving average is late. Lower-lag filters or ATR stops are better for exits.
- **Yield targeting and policy caps.** Under yield-curve control, a mechanical carry or trend signal on the controlled yield can
  be wrong for long periods. Substitute the next-lowest-carry market in the basket (J.P. Morgan, 2017).
- **Backfill and survivorship.** Index histories are often partly backfilled; the regime model note flagged this. Ask for the
  point-in-time series before trusting a long Sharpe.
- **Data snooping.** Out-of-sample results should be fixed before the test. Never re-fit after seeing the out-of-sample result. The Salomon authors attribute the gap between in-sample and out-of-sample returns to snooping, and their forecasts were wrong in about 40% of months.
- **Re-underwriting.** A receiver near its stop is re-underwritten when the forecast changes, not held by default.
- **Crosses as entry and exit.** Golden and death crosses give back much of the trend when used for both; the death cross on a bond future showed no edge, and conditioning on the 200-day slope can reverse a result (oil).
- **Premature divergence.** A two-trough or two-peak divergence is often early: wait for the third or a level confirmation.
- **Time at price is not volume.** The Market Profile POC measures frequency at a price. Do not read it as a volume profile.
- **FX statistics.** The MAA, up/down vol, residual skew and momentum-persistence numbers are FX: port the construction, not the thresholds, until tested on the rates series.
- **Calendar priors.** The primer's US 10y and dollar-index tables have no significance tests and small samples, and they decay. Compare each conditional rate with its unconditional rate before using it.

## G10 market notes
- **USD.** Trend on the 7-10y index worked on risk, not return. Drawdowns in the long history tracked hiking cycles (median -9.0%).
  The FOMC-day and fed-funds rules are USD-specific and need the meeting calendar (`cb_meetings`).
- **EUR.** Use Bund, Bobl and Schatz futures and the swap curve for trend, and Euribor futures (or the other STIR contracts in `stir_quotes`) for STIR technicals. EUR RSI
  readings in the sources came from the 10y swap. Periphery spreads are a trend candidate, but no quantitative rule is given here.
- **GBP.** The sources give a 30y-10y trend example only, with no out-of-sample support. Treat long-end technicals as a screen.
- **JPY.** While yield-curve control capped JGB yields (to 2024), mechanical trend and carry on them broke; the same applies to any capped or targeted yield (AUD 3y 2020-21). The usable overlay is the 55-day MA
  rule: JGB exposure only when the US 10y yield is below its 55-day MA (IR 0.90 vs 0.28 above, Willer & Saunders, 2026).
- **CAD, AUD, NZD, CHF, SEK, NOK.** No rates-specific technical test is in the sources for these markets. Apply the same
  tools to their own curves, test locally, and do not transfer USD thresholds without a test.
- **Calendar effects.** General January, month-end and seasonal screens are owned by quant-seasonality-and-calendar-effects. This skill carries only the primer's US 10y January, first-five-day and presidential-cycle
  tables as soft priors (Method 6) and does not extend them to other calendar effects.

Detail, the full recipe table, sourced cases and extra pitfalls are in
[references/indicator_recipes_and_cases.md](references/indicator_recipes_and_cases.md).
Longer tables and rules: [references/patterns_levels_and_structure.md](references/patterns_levels_and_structure.md) (support and resistance, patterns, Fibonacci, Elliott, Market Profile),
[references/trend_momentum_systems.md](references/trend_momentum_systems.md) (cross event tables, TMAC, weekly states, oscillators, Ichimoku, TD Sequential) and
[references/positioning_flow_and_calendar.md](references/positioning_flow_and_calendar.md) (CTA models, positioning triad, CFTC rule, calendar tables).

## Output
For each candidate idea, return one row per series or structure:

| Field | Content |
|---|---|
| Structure and sign | e.g. "2s10s, rising = steepening, price basis N/A, bp" |
| Regime | ADX(14) value and band (range, transition, trending) |
| Trend read | 55d and 200d MA position in bp and ATR units; slope; consensus value |
| Oscillator read | RSI(14) on the yield or spread, with band; Bollinger %B if used |
| Event context | last FOMC, payrolls or sell-off trigger and its sigma or bp size |
| Event study | h, n, mean signed bp, hit rate, base rate, for h = 5, 20, 45, 80 |
| Verdict | confirm / neutral / against the RV signal, with one sentence of reason |
| Level and stop | stop level (structural or entry plus k x ATR), target (pattern objective or extension) |
| Caveats | n below 25, costs not included, parameter range tested, data gaps |

Hand the table to rv-trade-idea-writeup for the trade note, and to rv-devils-advocate for the case against the trade.
A verdict of "against" is a stop-or-wait instruction, not a reversal.

## Scripts
- [`scripts/tech_indicators.py`](scripts/tech_indicators.py): SMA, EMA, Wilder RSI, MACD, Bollinger, true range, ATR, ADX (needs high and low),
  momentum consensus, yield momentum dummy, TMAC sum and moving-average aggregator (MAA), EWMA and rolling sigma moves, Fibonacci levels, Acar expected trend return, and a
  signal-forward event study (one-session entry lag, yield sign flip, n / h, always-long base). `python -I scripts/tech_indicators.py --selftest` checks hand-computed answers
  (RSI by hand, MACD against a reference recursion, Bollinger, ATR, ADX, TMAC and MAA by hand, consensus including ties and a mixed case, dummy both signs, sigma move, Acar drift and exponential terms,
  event-study lag and sign) and that no indicator changes when later data are appended.
  The CLI reads one series with a `date` column and a value column; `--yield-pct` marks a yield in percent, adds the bp dummy and reads the consensus on the negated yield.
  The CLI does not roll futures or build spreads: do that upstream with the tables above.

## Related skills
- [quant-regime-detection](../quant-regime-detection/SKILL.md): formal regime classification to complement the ADX read.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): mean-reversion tests on spreads, versus the trend tools here.
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): where trend and momentum sit in a full systematic rates model.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): level z-scores that pair with the trend read.
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): combining this overlay with other signals without double counting.
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): positioning and trend-follower flow mechanics.
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): skew measures and the skew-change signal in full.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): policy context for the FOMC and inversion rules.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): regime framing when a technical rule is switched off.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): calendar overlays, kept out of this skill.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): out-of-sample design and parameter-fragility tests.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): costs and roll for any trend rule.
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): combining the technical read with RV scores.
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): the case against a technically confirmed trade.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): where the verdict and stop go in the trade note.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): back-adjusted continuous futures series for any trend rule.
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): gaps, stale prints and point-in-time series before computing indicators.
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): inference with overlapping observations (HAC, block bootstrap).
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): policy-rate pricing behind the inversion and "no more hikes" rules.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event calendar and risk around FOMC and payrolls.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used under Inputs.

## References
- Willer, D. and Saunders, A. - Trading Global Macro Markets (Wiley Finance, 2026): 55-day and 200-day trend rules, cyclicals versus defensives, 10y sell-off peaks, inversion-to-cut, FOMC and payrolls rules, economic surprise trend, CTA counter-indicator, JGB overlay.
- J.P. Morgan, Global Asset Allocation - Simple rules to trade duration, Investment Strategies No. 74 (Mac Gorain, 2 Oct 2012): 1m and 12m bond momentum consensus, horizon IR table, rebalance-day sensitivity.
- J.P. Morgan, European Rates Strategy - Update on systematic rule based trading strategies (Gupta, Inkinen, Vijay; 6 Feb, 6 Mar and 10 Jul 2017 and 8 Jan 2018): combined composite (IR 1.2, max drawdown -1.8%), carry-to-risk drawdown, 2017 loss, substitution under yield targeting.
- J.P. Morgan, Global Asset Allocation / European Rates Strategy - Systematic fixed income trading strategies (Inkinen, Bassi, 13 Apr 2015): bond momentum long about 80% of the time.
- Salomon Brothers - Understanding the Yield Curve, Part 4: Forecasting U.S. Bond Returns (Aug 1995): yield momentum dummy with 5bp band and 10bp neutral range, out-of-sample sign accuracy.
- Dunis, C., Laws, J. and Naim, P. (eds.) - Applied Quantitative Methods for Trading and Investment (Wiley Finance, 2003): EMA recursion, Acar expected trend return, Markov vol-filtered trend rule.
- Aikin, S. - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): RSI, ADX thresholds, Bollinger and ATR use, decision-support caveat.
- BofA Global Research - Systematic Flows Monitor: More CTA Models = Better Impact Estimates (Kotecha et al., 2 Jun 2025): CTA ensemble, lookback and stop definitions, stop-out count versus sigma move, unwind triggers.
- BofA Global Research - Technicals Explained: In 2025, get to know technical strategy (Primer) (Paul Ciana, Stephen Suttmeier, 14 Jan 2025): regime-to-tool map, support and resistance, trend lines, patterns, golden and death cross event tables, TMAC, weekly MA states, oscillators, Ichimoku, TD Sequential, Fibonacci, Elliott, Market Profile, CFTC contrarian rule, US 10y and dollar-index calendar tables.
- BofA Merrill Lynch - Global Rates and FX Primer: FX Quant Primer (Vadim Iaralov, Alice Leng, Athanasios Vamvakidis, 1 Oct 2018): moving-average aggregator, up/down vol, residual skew, momentum persistence (FX-derived).
- BofA Global Research - US Rates: CTAs impact on the rates market (Bruno Braizinha, 18 Aug 2020): top-down CTA duration and curve positioning from principal-component betas, validation against momentum and CFTC data.
- BofA Global Research - US Rates Watch: 10y rates and the Monty Hall problem (Bruno Braizinha, 6 Aug 2024): trading range set from scenario levels and re-drawn when scenarios are ruled out.
- During, A. - Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 2021): technical-analysis caveats (false positives, CTD switches, self-fulfilling levels).
- Nordea Markets (Vainikainen) - EUR Rates Flash (23 May 2019): RSI screen and "trade the trend" caveat.
- Nordea Markets (Vainikainen) - EUR Rates Flash (5 Feb 2020): 14-day RSI 36.93 reading and range levels on the 10y swap.
- Nordea Markets (Svendsen) - EUR rates: How about that outright receiving (26 Sep 2025): overbought RSI with crowding, re-underwriting near a stop.
- J.P. Morgan, North America Fixed Income Strategy - US Treasury Market Daily: Canary in a coal mine (Barry et al., 25 Feb 2020): support and resistance, pattern objectives, curve-regime read.
- J.P. Morgan, Global Markets Strategy - Global Fixed Income Markets Weekly (Diamond et al., 21-22 Aug 2026): percentile-scaled signal scorecard.
- Narang, R. K. - Inside the Black Box (3rd ed., Wiley, 2024): Donchian breakout, trend-follower hit rates, lonely-peak and late-signal pitfalls (partial read).
- Tulchinsky, I. et al. - Finding Alphas (Wiley, 2015): trend on accumulated P&L, lag warning on moving averages.
- Citi Research (Bikbov) - North America Rates Focus: Flatter skew is a warning signal for duration shorts (12 Jan 2017): skew-change percentile buckets.
- Morgan Stanley (Zhou, Hornbach, Tobias, Singh, Carter) - Investors Are Paying for Protection Against 6% Rates (2 Jul 2026): 21-day skew change mapped to a duration position.
- Goldman Sachs (FICC and Equities, IRP Market Strats) - Global Rates Best Trade Report (desk material, 30 Sep 2026): entry z-score, two-week vol-adjusted trend, ex-ante carry Sharpe definitions.
- Citi Research (Saunders, Vo) - Quantitative Global Macro Strategy: Regime Model update (12 Aug 2026): blended MA trend and the backfill caveat.
- Wilder, J. W. - New Concepts in Technical Trading Systems (1978) (external): RSI, ATR and ADX definitions.
- Bollinger, J. - Bollinger on Bollinger Bands (McGraw-Hill, 2001) (external): band construction and use.
- Moskowitz, T., Ooi, Y. H. and Pedersen, L. H. - Time Series Momentum, Journal of Financial Economics (2012) (external): time-series momentum as a cross-asset baseline (Method 2).
