# Indicator recipes, sourced cases and G10 notes

Companion to [SKILL.md](../SKILL.md). Figures are as printed in the cited source. Lines marked **(check)** are
recomputed from printed numbers. Lines marked **(heuristic)** are practitioner convention with no source attached.
Lengths are trading days unless stated. `P` is a price index (futures settle, total-return index). `Y` is a yield in
bp. Convert percent to bp with `Y_bp = 100 * Y_pct` before any yield-based rule.

## 1. Recipes: formula, default, why

| Tool | Formula | Default | Why this default |
|---|---|---|---|
| SMA | `SMA_n = mean(x_{t-n+1..t})` | 55 (trend), 200 (regime), 21 and 252 (1m / 12m consensus) | 55 sits about 2.5 months: it turns within weeks and ignores daily noise. 21/252 mirror the 1m/12m pair in the JPM duration rule. |
| EMA | `EMA_t = (1-a) EMA_{t-1} + a x_t`, `a = 2/(d+1)`; equivalently `mu = 1 - 2/(d+1)` | span 12/26 for MACD; span 49 gives mu = 0.96 | Dunis, Laws & Naim (2003) write the recursion with mu. mu = 0.96 is the 50-day EMA. |
| RSI (Wilder) | `RS = avgGain / avgLoss` (Wilder smoothing, alpha = 1/14); `RSI = 100 - 100/(1+RS)` | 14; bands 70 / 30 | Wilder (1978). Equal average up and down moves give 50. |
| MACD | `line = EMA12 - EMA26`; `signal = EMA9(line)`; `hist = line - signal` | 12/26/9 | The zero-line cross equals an EMA cross, so it is a lagged version of the trend, not new information. |
| Bollinger | `mid = SMA20`; `upper/lower = mid +/- 2 sample SD20`; `%B = (x - lower)/(upper - lower)` | 20, 2.0 | Bollinger (external). Band narrowing is read as a precursor of larger moves (Aikin, STIR Futures, 2012). |
| True range | `TR = max(H-L, abs(H-prevC), abs(L-prevC))` | n/a | Close-only series: use `abs(dP)`. |
| ATR | simple mean of TR over n bars (Wilder's original smooths with alpha = 1/n) | 14 | Wilder (1978). Expresses a move in volatility units, for stops and filters. A close-only ATR (`|dP|`) is about half the OHLC value: double it before using a k x ATR stop set on OHLC data. |
| ADX | DI = 100 smooth(DM)/smooth(TR); `DX = 100 abs(+DI - -DI)/(+DI + -DI)`; ADX = Wilder smooth of DX | 14; below 20 range, above 30 trend | Aikin (2012), Wilder (1978). Needs high and low: on closes only it reduces to a smoothed `abs(2 RSI - 100)` and the thresholds mean nothing. |
| EWMA sigma move | `sigma_t = r_t / sqrt(v_{t-1})`, `v_t = lam v_{t-1} + (1-lam) r_t^2` | lam = 0.97 | Decay 0.97 is about a 23-day half-life (ln 0.5 / ln 0.97). The 2012 JPM duration study used the same decay for carry-to-risk. |
| Momentum consensus | `+1` if `P` above both SMA21 and SMA252; `-1` if below both; else `0` | 21 / 252 | JPM (2012). Neutral when the horizons disagree, which delays turns. |
| Yield momentum dummy | `+1` if `Y < MA_n(Y) - 5bp`; `-1` if `Y > MA_n(Y) + 5bp`; else `0` | n = six months (126 daily, 6 monthly); band +/-5bp | Salomon Brothers (1995): a 5 bp break from a six-month average, with a 10 bp neutral range in total. |
| Event study | for each signal `s_t != 0`: `s_t (x_{t+h} - x_t)`; report n, mean, hit rate | h = 5, 20, 45, 80 | Heuristic: a spread of weekly to quarterly horizons. Report all of them, not the best one. |
| Expected trend return (Acar) | `E(r) = sqrt(2/pi) sigma rho exp(-mu_f^2/(2 sigma_f^2)) + mu (1 - 2 Phi(-mu_f/sigma_f))` | no drift: `E(r) = sqrt(2/pi) sigma rho` | Dunis, Laws & Naim (2003), ch. 11, after Acar (1994). `rho` is the correlation between next-period return and the trend forecast. |

Worked numbers for the recipes:
- **RSI, illustrative (computed):** average gain 0.80bp, average loss 0.60bp, so RS = 1.333 and RSI = 57.1. Above 50 means the
  recent average move is up.
- **Consensus, illustrative (computed):** a 10y price index at 100.0, with SMA21 98.0 and SMA252 95.0 → `+1` (long duration).
- **Momentum dummy, illustrative (computed):** 10y yield 4.25% = 425 bp, six-month average 412 bp. Deviation +13 bp
  is above +5 bp, so the dummy is `-1` (yields high, bond bearish).
- **Acar, illustrative (computed):** daily sigma 5 bp, correlation rho 0.05, no drift: `E(r) = 0.798 x 5 x 0.05 = 0.20 bp` per
  day. A trend rule with a weak correlation earns a small fraction of one sigma per day.
- **Sigma move, illustrative (computed):** a 3 bp move after EWMA sigma 1 bp gives sigma = 3. Event rules in section 2.3 use
  2 sigma (heuristic: the threshold the sources use for "large") of the prior 21 daily changes, today excluded.

## 2. Sourced evidence by technique

### 2.1 Trend and momentum on bond indices

- **10y total-return index, moving-average rules (Willer & Saunders, 2026).** On a 7-10y US index, daily data:
  - 55-day MA: return 2.41%, vol 4.68%, return/vol 0.52, max drawdown -13.35%, time in market 57%.
  - 200-day MA: return 2.21%, vol 4.84%, return/vol 0.46, max drawdown -19.05%.
  - 252-day MA: return 1.84%, vol 4.91%, max drawdown -19.19%. On the source's reader check it only broke even against buy-and-hold.
  - Buy and hold: return 2.59%, vol 6.29%, return/vol 0.41, max drawdown -27.48%.
  - The 55-day rule gave a lower return than holding but about 25% less vol and 14 points less drawdown. The gain is risk, not return.
- **Momentum consensus (J.P. Morgan, 2012).** Long bonds if the index is above both its 1m and 12m average, short if below both,
  neutral otherwise. Single-horizon information ratios by market (US, JP, EA, UK, combined): 1m 0.51 / 0.48 / 0.20 / 0.00 / 0.41;
  12m 0.42 / 0.53 / 0.52 / 0.42 / 0.62. The 12m single-horizon rule was long 77% of the time in the bull market (bond momentum about 80%), so compare any IR with
  "always long" before crediting skill.
- **Rebalance-day sensitivity (J.P. Morgan, 2012).** The 3m momentum IR moved from 0.3 to 0.7 depending on which working day of the
  month the signal was rebalanced. Any single specification is a noisy estimate. Report a range over the rebalance day.
- **Yield momentum dummy (Salomon Brothers, 1995).** A 1965-95 monthly regression. Coefficient 0.34 (t 2.02) alongside term spread,
  real yield and inverse wealth. The out-of-sample figures below are for the four-predictor forecast (expanding window from Jan 1955, first forecast 1965,
  re-estimated monthly to Jul 1995), not for the dummy alone: correct sign in 61% of months; correlation with
  the next 12-month excess return 0.57. A 1/0 strategy on it (20y bond if the forecast is positive, else cash) averaged 4.16% excess return, vol 7.92%, Sharpe 0.53, against 0.06 for always holding the bond
  and for bond-cash. The term-spread-only variant gave 3.87% scaled excess return out of sample against 11.15% in sample for the full scaled model, a gap the authors attribute to data snooping; forecasts were wrong in about 40% of months.
- **Carry-to-risk as a duration signal (J.P. Morgan, Mar 2017 to Jan 2018).** Combined duration composite since 1998: IR 1.2 with max drawdown -1.8%.
  Carry-to-risk alone had IR about 0.4 to 0.6 (edition-dependent) and max drawdown -13.5%. In 2017 the combined signal lost 1.2%, the first loss since 2012,
  and carry-to-risk lost in December because it stayed long into a sell-off. A trend signal can be right on average and still give
  back its gains in a fast reversal.
- **Cyclicals versus defensives (Willer & Saunders, 2026).** Long the 10y future (1-day lag) when cyclicals-over-defensives returns are
  below their 55-day MA. Return 2.45%, vol 4.21%, max drawdown -13.43%, active IR 0.85 against 0.48 for the 10y alone, in the market
  47.6% of the time. The gain came mainly from lower vol. The rule fails in inflation shocks (2022), so it is switched off then.

### 2.2 Trend-following overlays and cross-asset trend

- **Donchian breakout (Narang, Inside the Black Box, 3rd ed. 2024).** Buy above the 2-week highest close, sell below the 2-week lowest
  close. Successful trend followers earn under one point of return per point of downside, and under 40% of trades win. Expect a low
  hit rate and fat right tails.
- **Trend on own P&L (Tulchinsky et al., Finding Alphas, 2015).** Enter at a new high of accumulated strategy P&L; exit when P&L falls
  more than a set amount from its all-time high. A lag warning from the same book: simple moving averages add lag, and "lag in trading
  can be extremely unprofitable". Use a lower-lag filter if the trend signal is the trigger.
- **Moving average blend (Willer & Saunders, 2026).** Price against x-day MAs, vol-adjusted, across 18 contracts with a 10% vol target:
  Sharpe 0.74.
- **200-day allocation rule (Willer & Saunders, 2026).** Hold equities if above their 200-day; else hold bonds if above their 200-day
  (risk-scaled to equity risk); else bills. IR 0.59, max drawdown -28.4%, against 60/40 at 0.53 and -33.5%.
- **Trend by spread (Willer & Saunders, 2026).** A EURUSD signal fed by a 5y UST-Bund spread vs its 55-day MA (2-day lag). Return/vol 0.44 (the text prints 0.40).
  Macro-conditioned MA, so it is not a pure technical signal.
- **Rates-conditioned MA overlay (Willer & Saunders, 2026).** Long Japanese government bonds only when US 10y yields are below their
  55-day MA: IR 0.90, against 0.28 above.
- **CTA counter-indicator (Willer & Saunders, 2026).** A proxy using the sign of price vs the 22-, 66-, 200- and 252-day MAs (sum from
  -4 to +4). The book concludes that the value of CTA positioning as a counter-indicator is "really extremely limited" and that
  investors are better off going with the trend. Do not fade CTA positioning by default.

### 2.3 Event and cycle timing triggers

- **Peaks after 10y sell-offs (Willer & Saunders, 2026).** Sell-offs of more than 70bp since 2000: range 70 to 214bp, median 120bp over
  about 135 days. Calling peaks paid better than calling troughs. Median leading signs of a 10y peak: 2y breakevens fell about a month
  before the peak; 5s30s flattened and peaked before 10s; 2s10s peaked with 10s; oil had risen more than 20% in the 3 months before the
  median peak. The sample is about 20 episodes, so treat the medians as a checklist, not a rule.
- **Inversion-to-cut (Willer & Saunders, 2026).** After an inversion of at least 12.5bp in the 6m2s spread, a cut came within 12 months
  73.7% of the time. Median across the ten curve measures tested (3m10s, 6m10s, 6m2s, 6m5s, 2s5s, 2s10s, 2s30s, 5s10s, 5s30s, 10s30s): 6m 43.8%, 12m 65.0%, 24m 93.3%. 6m2s is among the best of the ten at 12m (2s5s 73.3%, 10s30s 72.2%), so 73.7% carries selection bias. The 2s10s measure scored poorly (12m 57.1%). The
  strongest 10y rally followed a 6m/2y inversion; back-end inversions were followed by no rally.
- **Fed funds futures "no more hikes" rule (Willer & Saunders, 2026).** When the 6-month-ahead minus 1-month-ahead spread is below
  -12.5bp (at least half a 25bp cut priced), the book reads "no more hikes or cuts coming". It failed in March 2023, when inflation was
  above 5% and the Fed raised 75bp over six months. Do not use it in high-inflation regimes.
- **FOMC day rule (Willer & Saunders, 2026).** Score a meeting by the 2y move on the day, not by the statement. After a move of at least
  2 standard deviations of trailing one-month data, receive after a dovish move or pay after a hawkish one. Dovish 2-sigma moves had a
  positive, persistent median return; even the 10th percentile was not losing 20 days later. Hawkish samples are small (n = 2 in easing cycles).
- **Payrolls day rule (Willer & Saunders, 2026).** A 2-sigma or larger 10y move on payrolls day triggers a 10y position. After bullish
  3-sigma events the median return over 20 sessions was above 1%. Bearish prints were not a good signal to pay, even in hiking cycles.
- **Economic surprise trend (Willer & Saunders, 2026).** Receive 5y swaps when the economic surprise index is below -25; pay above +75.
  Return/vol 0.53 (1.26% over 2.40%) against 0.26 for the 5y swap alone (1.20% over 4.57%); active IR 1.01; in the market 27.5% of the time. A counter-indicator (fading the extremes) failed.
- **Skew change as a positioning proxy (Citi Research, 12 Jan 2017).** 3-month change in the 3m10y 25bp risk reversal (payer minus receiver normal vol), bucketed by
  historical percentile (monthly, 2006-2016; full-sample percentiles, so use an expanding window in live testing). Next-month change in the 10y yield:
  - below 25th percentile: average -11.5bp, median -5.0bp, rises 36% of the time
  - 25th-50th: average -2.1bp, median -1.1bp
  - 50th-75th: average +0.2bp, median -4.2bp
  - above 75th: average +8.8bp, median +11.1bp, rises 69% of the time
  The relationship is not monotonic; the edge is in the tails. Use it as a tactical warning alongside positioning.
- **2026 implementation of the skew signal (Morgan Stanley, 2 Jul 2026).** A 21-day change in skew mapped to a duration position, scaled
  as a fraction of maximum allocation; it flipped to long duration at 15% of maximum allocation.

### 2.4 Technical levels and pattern reads (case material)

These are dated illustrations of how the tools were applied. They are not current levels.

- **EUR 10y swap, Feb 2020 (Nordea Markets, 5 Feb 2020).** 14-day RSI 36.93 on the 70/30 bands, neutral. Key support -6.5bp; a climb
  above 0bp was flagged as a return to the 0-23bp range.
- **EUR 10y swap, May 2019 (Nordea Markets, 23 May 2019).** Downtrend with support at 40-42bp, a break opening the way to all-time lows
  near 23bp; resistance at 53bp (trendline) and 60bp (March-April highs). The short end was "technically overreceived (RSI)".
  "Trade the trend": do not react to daily fixings.
- **Outright receiver near a stop, Sep 2025 (Nordea Markets, 26 Sep 2025).** The note cites overbought RSI and crowding. Its rule: re-underwrite a
  receiver near its stop when a forecast changes (a 2027 ECB hike was added and the 2y1y receiver neared its 2.25% stop).
- **UST 10y, Feb 2020 (J.P. Morgan, 25 Feb 2020).** Yield 1.33%, at the 0th percentile of its 3-month range. Resistance (lower yields)
  at 1.28% (near the 1.285% pattern objective), 1.255% (Elliott fifth-wave objective), 1.22% (0.618 swing objective). Support (higher
  yields) at 1.43% (September low), 1.47% (February bull gap). Bullish bias while trading richer than 1.43-1.47%.
- **Curve regime (J.P. Morgan, 25 Feb 2020).** A two-month regression of 2s10s (bp) on the 2y yield (%) gave y = 52.361x - 55.756, R^2 75.8%: the curve was
  positively directional, flattening in rallies. A bull-steepening day broke that pattern; the note read a persistent bull-steepening regime as Fed-easing dynamics
  rather than flight to quality, and added that one day does not make a trend. Treat any such fit as a description of one window.
- **Scorecard (J.P. Morgan, 21-22 Aug 2026).** Each market's signals (policy forecasts vs pricing, fair-value residuals, positioning,
  a trend mimic) mapped to -5..+5 by percentile rank within that signal's own history (2y lookback). Scores are not comparable across markets.
- **Desk screen (Goldman Sachs, 30 Sep 2026).** Entry z = (level - 5y average) / 5y SD. Trend = 2-week change in bp divided by 3m vol,
  annualised, so a rising level gives a positive trend. Carry = ex-ante Sharpe (3m carry / 3m vol, annualised). Check:
  Sharpe is about 2 x (3m carry) / printed vol. Trend check: about 13 x (2w change) / printed vol. Outright forwards had 3m vol of
  25-55bp, curves 2-23bp, flies 2-18bp, so the same bp move means very different risk units across structures.
- **Regime model (Citi Research, 12 Aug 2026).** A blended MA trend in a regime model. The note flags that index histories were partly
  backfilled (live 2015-2023, history 1999-2008), so headline Sharpe ratios are optimistic.

## 3. Market-specific notes

- **USD.** A trend rule on the 7-10y index beat buy-and-hold on drawdown (section 2.1). The index drawdowns since 1973 were eight above
  5%, and they tracked hiking cycles (median -9.0%) (Willer & Saunders, 2026). Expect trend to be most useful in easing or stable-policy
  regimes. The 6m-ahead minus 1m-ahead fed funds rule and the FOMC day rule are USD-specific and need the meeting calendar.
- **EUR.** Use the Bund and Bobl futures and the EUR swap curve for trend, and Euribor futures for STIR technicals. Aikin (2012) describes
  10-day/30-day SMA crosses that caught a Euribor uptrend with one false signal. EUR RSI readings in the sources were from the 10y swap.
  Periphery spreads are a trend candidate, but the sources here give no quantitative rule for them.
- **GBP.** The sources here give a 30y-10y trend example only. No rule with out-of-sample support is given. Treat long-end technicals
  as a screen, not a signal.
- **JPY.** Under yield-curve control the price of the yield is set by policy. A mechanical trend or carry signal on JGB yields can be
  wrong for long periods. J.P. Morgan (Feb 2017) replaced JPY with the next-lowest-carry market in its basket. The 55-day MA rule (JGB only
  when US 10y is below its 55-day MA) is the usable overlay in Willer & Saunders (2026).
- **CAD, AUD, NZD, CHF, SEK, NOK.** The sources give no rates-specific technical test for these markets. Apply the same tools to their
  own curves and test them on local data before use. Do not transfer USD thresholds without a test.

## 4. Pitfalls to check each time

- **Yield versus price sign.** A golden cross on a bond price means lower yields. The same cross on a yield series means higher yields.
  Always say which one you are reading.
- **Lonely-peak parameters.** A rule that works only at one lookback is an artefact. Compare its neighbours. Never refit after an
  out-of-sample test (Narang, 2024).
- **Late and extreme signals.** The largest moves often come late or at dislocations, so the largest signals can be adverse selection.
  Cap, winsorise or equal-weight.
- **Transaction costs.** Most published trend results ignore costs. Re-run any rule with the costs of the instrument, including roll.
- **Event samples.** Many event results rest on fewer than 25 episodes. Report n, and compare the conditional hit rate with the
  unconditional base rate.
- **Rebalance day and horizon.** Momentum IRs move with the day of the month and the lookback. Report a range, not a point.
- **Overlapping forward windows.** Daily signals with h = 20 to 80 share most of their window: n overstates the evidence by about h. Quote n / h and use block bootstrap or HAC errors.
- **Execution lag.** A signal on the close of t is traded at t+1. Measuring from x_t flatters every trend rule.
- **Overlap in signals.** Consensus, trend and carry-to-risk can all be long duration in one bull market. Check correlation before
  adding them.
