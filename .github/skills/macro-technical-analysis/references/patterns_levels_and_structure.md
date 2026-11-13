# Patterns, levels, structure and profile reads

Companion to [SKILL.md](../SKILL.md). Source for every section unless marked: (BofA, Technicals Explained, 14 Jan 2025).
Lines marked **(adaptation)** are this skill's reading of how to use the tool on rates, not the authors' statement.
Charts are drawn in price terms. On a yield chart write each level as a yield and mirror the direction: a bullish price
pattern is a fall in yield. Percent targets on a price index become bp on a yield or a spread.

## 1. Support, resistance and trend lines

**Support and resistance.** Support is demand, resistance is supply. Higher highs and higher lows define an uptrend; lower
highs and lower lows a downtrend. Role reversal: broken resistance becomes support ("sell rallies" turns into "buy dips"),
and the reverse. Zone strength rests on four things:
- time: monthly and weekly levels beat daily ones; old levels fade as their participants leave;
- number of tests;
- depth: a zone 3-4% wide is stronger than one 1% wide (on a yield use the same relative width or an ATR multiple);
- volume (futures volume, where the adapter supplies it).

**Trend lines.** A good line has multiple touches spaced in time, some age (the primer's example is over four years old with 11
tests) and a slope of about 30 to 50 degrees. If the price is more than 30% from the line's start, also draw it on a log chart,
where the break can come earlier. A break is confirmed by any of:
- a close at least 1% beyond the line (on a price index);
- above-average volume;
- consecutive closes beyond the line;
- failed retests on light volume;
- a break larger than one ATR (the primer's example: 5-week ATR about 0.90 on an FX pair, so a close 0.90 beyond the line confirms).

Targets: the measured move is the height of the prior move above the line, subtracted from the breakdown point (FX example, shown for
the arithmetic: about -5.05%); or a Fibonacci extension of the largest height above the line, where the 38.2% and 50% levels
lined up with prior horizontal levels and lows. The "0.5 x ATR" filter in SKILL.md Method 5 is this skill's scaling, not the primer's.

## 2. Reversal and continuation patterns

**Outside reversal (engulfing).**
- Bullish version needs a prior downtrend. Bar 1 is a small range closing down. Bar 2 opens lower, makes a new low, then reverses to a higher high.
- Bearish version ideally closes below the prior bar's low, or at least below its open.
- Strengtheners: the pullback happens above a rising 200-period SMA, or with the 50 above the 200; the pattern forms at trend-line, MA or Fibonacci
  support; RSI is oversold or at recent lows; bar 1 has low volume and bar 2 high volume. A doji that is then engulfed also counts.
- Case, US 30y yield, July 2016 (all-time yield low): prior weekly closing low 2.0936%; the week traded down to 2.0882% and then engulfed the prior
  week. The outside bar opened at 2.1003 against a prior close of 2.0983, a 0.0020 gap the wrong way: not ideal, accepted. A pennant followed, and a later outside week formed the
  left-shoulder low of a 2017 head-and-shoulders base.

**Candles (reference list).**
- Doji variants: dragonfly, gravestone, long-legged, doji star. A gap into a doji makes it stronger.
- Hammer: lower shadow 2 to 3 times the body, more bullish than a dragonfly. An inverted hammer forms only at a peak.
- Harami (bullish and bearish).
- Piercing line and dark cloud cover: the close reaches about 50% into the first candle.
- Morning and evening star: the third candle closes at least 50% into the first.
- Three soldiers.
Candle patterns are one-bar to three-bar reads: use them only at a level and with the regime in agreement.

**Head and shoulders (top; mirror for a bottom).**
- A prior trend must exist. Three peaks and two troughs with the head highest. The neckline is flat or slightly rising (for a top).
- The right shoulder is lower than the head and no bigger than the left. A decisive neckline break on above-average volume. A neckline retest on light volume is a second entry.
- Stop at the right-shoulder high.
- Volume profile: light into the head, rising on the decline to the second trough, light into the right shoulder, heavy on the break.
- Target: the head-to-neckline height subtracted from the breakdown point, annotated as Fibonacci extension levels. Fibonacci retracement of the prior uptrend gives confluence:
  "high conviction" is the 50% and 61.8% levels both reached; "probable" is 61.8% and 100%.
- Confirmations: polarity of long MAs or trend lines (the 200-week SMA), candles at the peaks and troughs, momentum divergence (RSI, stochastics, MACD histogram), a MACD or Ichimoku cross, TD 9 or 13 at the head.
- Cases: an early-1980s monthly head-and-shoulders top on the US 10y yield marked the start of the secular bond bull market; a 2019-2022 head-and-shoulders bottom marked its end, confirmed in 2022.

**Double tops and bottoms.**
- Target: the pattern height projected from the trough (top) or the peak (bottom).
- Scale in by thirds: one third speculative after the second turn from an equal high, one third on the confirmed breakdown, one third on a retest of the breakdown point a few days later.
- Cases, US 10y yield: a double bottom at 1.15% tested twice in summer 2021, confirmed by a break above the intervening peak; a double top over an August-November uptrend confirmed in mid-November (year not stated in the source).
  A 200-month SMA capped the 2016-18 bear market in yield at about 3.25%, a double top in 4Q18 (the average had not been tested since 1989).

**Cup and handle.**
- The handle retraces no more than 38.2-50% of the cup rally (a deep handle can reach 61.8%). Volume falls in the handle and rises on the breakout.
- Target = breakout point plus (breakout minus cup low).
- Entries: buy the handle pullback at 38.2-50% with a stop under the handle low; buy the break of the handle downtrend line; or buy a close below then back above a rising 40-week MA with the stop below that week's low.
- The pattern is from O'Neil (1988). Equity example in the primer: a breakout above 4600 projecting about 5700.

**Island reversal.** An exhaustion gap and a breakaway gap that overlap, on higher volume. The exhaustion gap is the most likely to be filled; the breakaway gap the least likely.
**(adaptation)** Gaps are rare in swap and yield series; the pattern matters mainly for futures contracts and for roll-adjusted series where the gap is real, not a roll artefact.

## 3. Fibonacci levels, extensions and time

- Key ratios: 61.8% (89/144), 38.2% (55/144), 50%, plus 23.6% and 76.4%. Draw them from major turning points only; they are reference levels, not forecasts.
- Retracement from the top of an up-leg: `level = High - r x (High - Low)`. From a bottom: `level = Low + r x (High - Low)`.
- Worked numbers (index and FX, as printed): `0.618 x (1576.09 - 666.79) + 666.79 = 1228` against a prior high of 1220; `1370.58 - 0.382 x (1370.58 - 666.79) = 1101.73` against a low of 1101.54;
  `1.0341 + 0.382 x 0.5697 = 1.2517`, the 2018 peak of an FX pair, with the 61.8% retracement of 1.3993-1.0341 at 1.2598.
- Projections: 100%, 161.8%, 300% and 361.8% of the pattern height.
- Time projection: pattern width (38 weeks in the example) times 161.8% or 200% estimates when a target may be reached. Fibonacci arcs combine price and time.
- Confluence matters more than any single level: look for a retracement, a trend line, an MA and a prior horizontal level inside the same zone.

## 4. Elliott wave (structure vocabulary)

- Five waves with the trend, then an a-b-c correction.
- Rules: wave 2 does not go below the start of wave 1; wave 3 is not the shortest; wave 4 does not overlap wave 1 (with leniency in futures and leveraged markets).
- Typical sizes: wave 2 retraces about 61.8% of wave 1; wave 3 is often 161.8% of wave 1; wave 4 retraces 23.6-38.2% of wave 3 (the text prints "26.4", read as a typo for 23.6; both are recorded). Corrections alternate in depth.
- Corrective patterns: flat (3-3-5), zig-zag (5-3-5, deeper), triangle (a-b-c-d-e), double corrections joined by an X wave, and the ending-diagonal wedge (3-3-3-3-3).
- Use: a labelled objective, as in the 25 Feb 2020 US 10y case in [indicator_recipes_and_cases.md](indicator_recipes_and_cases.md) (fifth-wave objective at 1.255%). Wave counts are subjective: require the rules above and a level that agrees.

## 5. Market Profile levels

Market Profile shows the distribution of prices over time. It rests on the principle that markets move slowly through time when range-bound and fast through price when trending.

**Construction.** Each letter (a time-price opportunity) marks a period's high-low range. A letter can stand for a set number of minutes, a day, a week or a month: in the primer's example A is the first day of the
month and each profile covers one month. The profile is a bar chart collapsed to the left. It needs period high and low prices, or intraday data for finer letters; ask the data adapter.

**Key levels.**
- Point of control (POC): the longest horizontal row, the price reached most often. It measures frequency, or time at price, not volume at price. Historical POCs act as support, resistance and trend targets.
- Value area: the band holding 70% of the distribution.
- Initial balance: the first two periods (letters A and B).
- Open, midpoint and close (or last price) of each profile are also read as levels.

**Signals.**
- Trading above the initial balance or the value-area high suggests an uptrend may start; below either, a downtrend.
- Four distribution types: down trend, up trend, double distribution (a gap where sellers pushed price down and buyers bid it up) and normal.
- Trade breakouts from current or historical POCs, value areas, initial-balance lines, highs, lows, closes and midpoints in the direction of the move.
- In a double distribution expect the gap to fill, with targets at that distribution's value area and POCs.
- When price moves too far too fast and meets support or resistance at a key level, trade the reversion (the single-print-tail or retracement trade).
- Split and join profiles to separate trending from range-bound action. Look across, say, 10 distributions for overlapping POCs and value-area levels: overlap is confluence.

**Worked examples (no instrument is named in the source; do not assume a bond future).**
1. Two profiles share a lower value-area edge at 119.30, which is support, so a break below 119.30 is bearish. Joined, they form a double distribution with POC 120.20. A decisive move above the POC and midpoint is bullish, with target T1 at the top of the value area and T2 at the longest row of the upper distribution.
2. A 6-month joined double distribution has POC 120 and a value area of 119.30 to 123.40. The current month broke above its value-area high and its initial-balance high of 120.50, which suggests a new trend. The target is 123.40, a rally to fill the distribution gap.
3. Split the trending top off the middle profile, then join the left pair and the right pair. The joined result is normal and range-bound: below the value area is bearish, above it is bullish, otherwise expect reversion to the POC. When a new distribution starts, use the most recent normal distribution's POC and value-area lines as key levels.

Credit: Steidlmayer, J. P., Steidlmayer on Markets: Trading with Market Profile (2002). **(adaptation)** Build profiles on the contract being traded (a futures price), not on a spread, and re-draw after a roll.

## 6. Dated level cases

- **US 10y range from scenario levels (BofA, 10y rates and the Monty Hall problem, 6 Aug 2024).** The note set a 10y range from scenario levels, not from a chart. Four scenarios (hard landing about 3%, soft landing 4-4.25%,
  no landing up to 5-5.25%, reacceleration up to 5.5-5.75%) carried market-implied likelihoods; a new fact (the first Fed cut pulled forward to September) was inconsistent with the last two, so their probability mass moved to the remaining scenarios.
  The new range took its top at the soft-landing level (4-4.25%) and its bottom at the midpoint between the hard-landing level (3%) and the soft-landing level, about 3.5%. Read: buy dips in the lower part of 3.5-4.25%, and treat a break below 3.5% as needing a hard-landing baseline.
  Earlier in the year the midpoint of the 4-5% range (about 4.4-4.5%) had split periods biased to expansion from periods biased to slowdown. The Sahm indicator read about 0.53, a level that historically coincides with recession periods.
  Data in the early stages of a hard landing can look like a soft landing, which supports a bullish bias inside a range rather than calling the hard landing. The scenario framework itself sits in macro-regime-and-scenario-analysis; the technical use is the level arithmetic (top at one scenario, bottom at a midpoint) and the re-draw after new information.
- **US 10y yield, 2016-18 (200-month SMA).** Capped at about 3.25% with a double top in 4Q18 (section 2).
- **Dollar index, 2018-19.** Found support at the 200-month SMA and resistance at the 200-quarter SMA: long-timeframe averages as levels.
