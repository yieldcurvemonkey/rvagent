---
name: quant-systematic-rates-signals
description: "Builds rule-based systematic signals for outright duration timing and cross-market (country) allocation in G10 rates (USD EUR GBP JPY CAD AUD NZD CHF SEK NOK 10y swaps, bond futures): carry-to-risk (10y-3m slope over EWMA vol, percentile-scaled), bond price momentum (1m and 12m trend), contrarian equity momentum, macro momentum (manufacturing PMI, earnings revisions, unemployment), slope reversal and real-yield ranking, combined into a fixed-weight duration score that scales a risk budget or overlays an RV book. Use when asked for a systematic or rules-based duration call, 'long or short duration?', tactical duration, a duration overlay, trend following, golden/death-cross trend scores, CTA positioning and stop-out risk, time-series momentum (TSMOM) in yields, carry-to-risk, value and momentum in bonds, macro or PMI momentum for bonds, a cross-market 10y swap long-short, country allocation, real-yield or slope-reversal pairs, a duration scorecard, or how to tilt the residual beta of RV trades."
---

# Systematic rates signals: duration timing and cross-market allocation

A small set of simple, slow rules predicts the sign of 10y excess returns a little better than a coin: value
(carry-to-risk), price momentum, contrarian equity momentum and economic momentum (PMI, earnings revisions). Each
rule alone has an IR of about 0.4-0.7. Because they are weakly or negatively correlated, a fixed-weight blend
reaches an IR of about 1.0-1.3 at one third of the vol of a long-only bond position (J.P. Morgan, Simple rules to
trade duration, Oct 2012; J.P. Morgan, Systematic fixed income trading strategies, Apr 2015). The same ingredients
ranked across countries (carry, slope reversal, real yield, unemployment change) give market-neutral 10y swap pairs.
In an RV book the combined score is a directional overlay: it sizes a deliberate duration tilt and tells you which
side of a beta-carrying RV trade the market tide is on.

## When to use
- "Should we be long or short duration in X?" when the answer must be systematic and back-testable, not a narrative.
- Build or refresh a G10 duration scorecard (per market and aggregate) for the morning meeting or a risk scalar.
- Choose cross-market 10y swap or bond longs and shorts (carry, real yield, slope catch-up, macro momentum).
- An RV trade (steepener, fly, spread) carries residual beta and you must decide whether to keep, hedge or flip it.
- Check whether a directional idea fights trend, carry or macro momentum before it goes to
  [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Conventions
- **Sign:** every signal and score is + = long duration / receive fixed / overweight that market's 10y. A rule
  phrased "short duration if PMI rose" is stored as -1.
- **Units:** rates and slopes in bp in tables (pct in canonical inputs; bp = pct x 100). Excess returns in % of
  notional. Carry-to-risk is dimensionless (pct per year over pct per year).
- **Score:** the combined score is a fraction of the duration risk limit: -0.2 = short 20% of the limit
  (J.P. Morgan, Update on systematic rule based trading strategies, Feb 2017). It can reach +/-1.35 because C2R
  runs to +/-2; cap the position at the limit.
- **Cross-market pairs:** "long A vs B" = receive A, pay B, DV01s set so both legs carry equal bp-vol risk.
- **Timing:** a signal dated t uses data published by the t snap; positions start at t+1.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Par swap rates 10Y, 1Y, 3M, 1M per market (or govt CM yields under `<CCY>-GOVT-<issuer>`) | `curve_par` | daily close, one snap, >= 13y for a full 10y percentile window (the script emits a shorter-window percentile from 3y; flag it) | `start = 0D`; drop `data_ok = false`. RFR curves (SOFR, €STR, SONIA, CORRA...) are too short: splice the legacy IBOR curve before the RFR start at a fixed spread measured at the join and say so, or use govt curves |
| Floating-index fixing for carry (3M OIS, or the IBOR the swap references) | `rate_fixings`, `rate_indices` | daily | gate on `pub_ts_utc` |
| 10y bond futures settlement prices (alternative return series) | `fut_quotes`, `roll_map` | daily | roll-adjusted (see [fut-calendar-roll](../fut-calendar-roll/SKILL.md)) |
| Manufacturing PMI, local and global | `macro_series` | monthly, all vintages | `pub_ts_utc` decides the month it is usable |
| Equity earnings revision ratio (upgrades - downgrades) / total, local and global | `macro_series` | monthly | released the Tuesday after the third Friday |
| Local equity index (total return, net of cash) | `macro_series` (`<CC>-EQ-<INDEX>-TR`, unit `index`) | daily | `pub_ts_utc` = snap instant |
| Unemployment rate | `macro_series` | monthly, vintages | cross-market signal |
| Consensus 10y average inflation forecast | `macro_series` (`<CC>-CPI-FCST-10Y-AVG`, unit `pct`) | semi-annual survey (Apr/Oct in the source) | real-yield signal |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values. Schemas:
[data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

**Carry leg by market.** Use the floating index each swap actually references. That is OIS for USD SOFR, EUR €STR,
GBP SONIA, JPY TONA, CHF SARON and CAD CORRA. AUD (BBSW 3M/6M), NZD (BKBM 3M), SEK (STIBOR 3M) and NOK (NIBOR 6M)
swaps are still IBOR-referenced. EUR 6M-Euribor swaps carry against Euribor. A common OIS proxy misstates carry by
the tenor basis. The sources used 3M (duration) and 1M (cross-market) Libor. Conventions:
[fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md).

## Method

### 1. Return series per market
Build a constant-maturity 10y receiver excess-return index (or use roll-adjusted 10y futures):

`r_t = (y10_{t-1} - yS_{t-1}) * dt - D_{t-1} * (y10_t - y10_{t-1})`, with `dt = 1/252` and
`D = (1 - (1+y)^-10) / y` (annual-pay par annuity, y in decimals). `I_t = sum of r`.

This leaves out roll-down and convexity. Use [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md) when the
carry level itself is the trade.

### 2. Duration (time-series) signal library
| Signal | Rule (+ = long duration) | Default and why | Weight |
|---|---|---|---|
| **Carry-to-risk (value)** | `C2R = (y10 - y3M) / sigma`, `sigma^2_t = 0.97 sigma^2_{t-1} + 0.03 r_t^2`, annualised x sqrt(252). `p` = percentile of C2R in its trailing 10y (0 = low, 1 = high). **Position `= 4 (p - 0.5)`**, in [-2, +2], mean absolute value about 1 | Investors extend duration for yield when vol is low. Scaling by vol avoids a false short in "Japanised" flat, low-vol curves. The proportional rule beat the binary one: IR 0.75 vs 0.63 (G-4) | 35% |
| **Bond price momentum** | +1 if `I_t` > its 1m mean AND > its 12m mean; -1 if below both; 0 if mixed | Comparing the level to a past average avoids base effects. Two horizons cut whipsaw. Neutral when they disagree, which delays turns | 20% |
| **Equity momentum (contrarian)** | +1 if the local equity index is below its 6m mean, -1 if above | Weak equities = rising risk aversion = bond-friendly. Needs negative bond-equity correlation | 15% |
| **PMI momentum** | +1 if local AND global manufacturing PMI fell over 2 months; -1 if both rose; else 0 | PMI changes are serially correlated, and the global PMI leads local ones (corr 0.49 vs 0.24 own lag) | 15% |
| **Revision-ratio momentum** | +1 if local AND global earnings revision ratio fell over 3 months; -1 if both rose; else 0 | Arrives about 1.5 weeks before the PMI, with similar information | 15% |

Defaults are from J.P. Morgan, Simple rules to trade duration, Oct 2012, kept unchanged in every later update.
Lookback-by-lookback IRs are in [rule-sets-and-track-records](references/rule-sets-and-track-records.md).

**Trend variants for the momentum slot** (tables and rule sets: sections 10-11 of the same reference). Build every
trend rule on the return index, so + = long duration: a golden cross on a bond price is a death cross on the yield.
- **Graded MA score (TMAC):** three moving averages (10/20/30d) give 9 conditions (price vs each MA, each MA vs the
  others, slope of each), summed to -9..+9. Go long above 0 and short below 0, or scale in by thirds at >=3, >=6 and
  =9. Trade only when the 200d slope agrees (BofA, Technicals Explained, 14 Jan 2025). The primer reports no
  performance for these rule sets.
- **Condition crosses on the 200d slope.** On the long bond future (since 1977) 34 golden crosses were followed by
  higher prices 68% of the time at 40-50 days, but 12 of 14 (86%, average +2.5% at 45 days) when the 200d average was
  also rising. Death crosses had little edge (down 36-53%). Use them as context, not as a stand-alone entry and
  exit (BofA, Technicals Explained, 14 Jan 2025).
- **Regime gate:** ADX below 20 = range, above 25 = trend. Give the trend variants weight only in trend regimes
  and test a reversion rule in range regimes. The primer's rule of thumb is that rates mean-revert more often than
  commodities or equity indices, so choose lookbacks and the MA type (EMA reacts earlier) per market rather than
  copying equity defaults (BofA, Technicals Explained, 14 Jan 2025).

### 3. Combine
`Score_m = 0.35 C2R + 0.20 Mom + 0.15 (PMI + Rev + Eq)` per market, where C2R is the position
`4 (p - 0.5)` from the table above, not the raw ratio. The G10 aggregate is the simple average
across markets.
- **Why these weights:** equal weights gave IR 1.03 and in-sample optimised weights 1.07 (look-ahead), so
  optimising barely helps. Carry-to-risk gets 35% because it is the only value signal and its correlation with the
  others is near zero or negative (+0.01 to -0.42), which balances value against four momentum-type signals.
- **Correlation is the lever:** two signals of equal IC with correlation g combine to IC x sqrt(2/(1+g)), so a
  negatively correlated value signal adds more than a fifth momentum signal (Grinold and Kahn, Active Portfolio
  Management, 1999). A linear blend is the default; the alternative is a conditional blend (value counts only when momentum
  agrees, otherwise 0) (Narang, Inside the Black Box, 2024).
- **Missing signal:** renormalise over the signals present (the script does this). Say so in the output. With
  only C2R and momentum the score is (0.35 C2R + 0.20 Mom)/0.55, range +/-1.64 (+/-1 on momentum alone while the
  C2R percentile warms up). That is not a fraction of the limit; rescale it before using the bands below.
- **Rebalance monthly,** on the 2nd working day, one day after the global PMI. Revisions update the day after their
  release. Weekly rebalancing added nothing before costs (J.P. Morgan, Exploiting carry with cross-market and curve
  bond trades, Jan 2007).

### 4. Cross-market (country) signals on 10y swaps
| Signal | Value (overweight = receive the highest) | Rationale |
|---|---|---|
| Carry | `y10 - y1M` (own float index) | forwards over-predict future rates; steep curves embed term premium |
| Carry-to-risk | slope / (D x bp-vol of the 10y), as in the duration C2R | removes the "high carry = high vol" trap |
| Slope reversal | `(y10 - y1Y)_t - mean_6m(y10 - y1Y)`: receive where the curve steepened most | transient divergences between economies reverse |
| Real yield | `y10 - consensus 10y average inflation` | capital chases real yield if FX and short rates do not eat it |
| Unemployment change | `U_t - mean_10m(U)`: receive where unemployment rose most | macro momentum |

Rank the markets each month and trade two pairs (1st vs last, 2nd vs 2nd-last), vol-matched:
`DV01_long / DV01_short = sigma_short / sigma_long` (bp vols, trailing 6-12m; J.P. Morgan, Jan 2007 sized spread
trades on 12m rolling vol of monthly returns, which beat daily and weekly vol for curve trades but not for
cross-market ones). Cost assumption is 2bp per currency
(4bp per pair) (J.P. Morgan, Rule-based Fixed Income Monthly, Nov 2012). Do not net signals mechanically; pairs can
offset. The source practice is to combine carry and real yield by dropping offsetting positions (J.P. Morgan, Update
on systematic rule based trading strategies, Feb 2017).

Pooled cross-sectional regression, every variable demeaned across 7 markets, since 2003: relative yield decline in
bp per month = 2.6 x carry + 7.4 x change in slope + 2.2 x real yield (per 100bp; t = 4.1 / 4.2 / 3.6; adj R^2 0.05)
(J.P. Morgan, Rule-based Fixed Income Monthly, Nov 2012). Use it to translate a signal gap into an expected bp
drift, not as a fitted model to trade.

**Rank-to-score and filter sorts.** Instead of a pure rank, map each factor's rank to a fixed score (for example
carry level, 10 ranks: 4, 3, 3, 0, 0, 0, 0, -3, -3, -4), add the 1y z-score and sum across factors. A two-step sort
first ranks on a slow driver, then re-sorts the top and bottom groups on faster scores, so no trade fights the slow
driver. This is a conditional blend. Both come from weekly G10 FX models (hypothetical, gross of costs) and are
untested in rates here; treat them as patterns (BofA, FX Quant Primer, 1 Oct 2018; scorecards and track records in
section 12 of the reference).

Alternative specifications (the Salomon regression timing model with its duration-target mapping, moving-average
trend on a bond index, the data-surprise rule, scorecard format) are in section 8 of
[rule-sets-and-track-records](references/rule-sets-and-track-records.md).

### 5. Size it and use it as an overlay
1. **Standalone duration sleeve:** target DV01_m = Score_m x (vol-targeted DV01 budget of market m). The source
   used equal country weights. Overweight the liquid G-4 in practice.
2. **Overlay on an RV book:** measure the book's residual level beta in 10y-equivalent DV01 (or PC1 exposure, see
   [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md)). Then:
   - |Score| < 0.2: neutralise the beta and run the RV trade pure;
   - beta has the same sign as the score: keep it, capped at |Score| x overlay budget;
   - beta has the opposite sign and 0.2 <= |Score| < 0.5: halve it;
   - beta has the opposite sign and |Score| >= 0.5: hedge it out (PCA-neutral weights).
   These thresholds are defaults, not from the sources. They are anchored on the fact that one 15% signal flipping
   sign moves the score by 0.30.
3. **Expression choice:** when a curve or spread trade can be put on bull- or bear-weighted, pick the side whose
   beta matches the score (see [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md)).
4. **Constant risk per trade.** Scaling a carry book (all curve and cross-market spread trades) by the level of
   carry-to-risk lowered IR from 0.94 to 0.60 (one trade) (J.P. Morgan, Exploiting carry with cross-market and curve bond trades, Jan 2007). Proportional
   sizing inside the C2R signal is fine; levering the whole book on signal strength is not.
5. Book-level sizing and stops: [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).

### 6. Diagnostics before trusting a backtest
- **Long bias:** % of months long, and IR against simply being long. The G-4 combination was long 57% of the time,
  all of the bias from bond momentum; without it the IR was 1.04, against 0.8 for long-only futures (J.P. Morgan,
  Simple rules to trade duration, Oct 2012). In the 10-market version bond momentum alone was long about 80% of the
  time (J.P. Morgan, Systematic fixed income trading strategies, Apr 2015).
- **Regime split:** rally vs sell-off months (sign of the average G-4 10y return) and central-bank cycle (easing
  from one month before the first cut to one month after the last). Bond momentum earns in rallies and about zero
  in sell-offs. Equity momentum earns in sell-offs (J.P. Morgan, Systematic fixed income trading strategies,
  Apr 2015).
- **Spec noise:** rerun with the rebalance day shifted 1-20 days. 3m momentum IR ranged 0.3-0.7 on that choice
  alone. Report the range, not the best day.
- **Hit counts for pairs:** besides the hit ratio (share of periods with a positive long-short return), count how
  many long legs beat the equal-weighted basket of the short legs: longs +3% and +0.5% against shorts of +0.5% each
  score 1 of 2 (BofA, FX Quant Primer, 1 Oct 2018).
- **Out-of-sample:** expanding-window only; see [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).

## Worked examples

**A. Reproducing a published combined score** (J.P. Morgan, Simple rules to trade duration, Oct 2012).

| Market | PMI | Rev | Bond mom | Eq mom | C2R | 0.15(PMI+Rev+Eq) + 0.20 Mom + 0.35 C2R | Published |
|---|---|---|---|---|---|---|---|
| US | -1 | -1 | +1 | -1 | -0.2 | -0.45 + 0.20 - 0.07 = **-0.32** | -0.3 |
| JP | -1 | 0 | +1 | +1 | -0.4 | 0 + 0.20 - 0.14 = **+0.06** | +0.1 |
| EA | -1 | 0 | +1 | -1 | -1.1 | -0.30 + 0.20 - 0.385 = **-0.485** | -0.5 |
| UK | -1 | 0 | +1 | -1 | +0.4 | -0.30 + 0.20 + 0.14 = **+0.04** | 0.0 |

The aggregate is about -0.2, a small short of about 20% of the risk limit. Bond momentum (+1 everywhere) was
outvoted by rising PMIs (signal -1) and strong equities. The same arithmetic reproduces the Jul 2017 ten-market row: AUD
0.15 + 0.15 - 0.20 + 0.15 + 0.35 x 1.6 = +0.81, published +0.8 (J.P. Morgan, Update on systematic rule based
trading strategies, Jul 2017). `--selftest` checks both tables.

**B. Carry-to-risk position (illustrative numbers).** 10y-3M slope 150bp = 1.50%/yr. Yield vol 80bp/yr x
duration 8.5 = 6.8%/yr return vol, so C2R = 1.50 / 6.8 = 0.22. If 0.22 sits at the 85th percentile of the past
10y, the position is 4 x (0.85 - 0.5) = **+1.4**, contributing 0.35 x 1.4 = +0.49 to the score.

**C. How a regime turn shows up** (J.P. Morgan, Update on systematic rule based trading strategies, Jan 2018).
The aggregate went from 0.0 to -0.3, net short for the first time since May 2017, because bond momentum flipped
from long to short or neutral everywhere except NZ. US -1.1, JP -1.0, SE +0.4. The 2017 return was -1.2%, the
first annual loss since 2012, from longs in SEK and AUD. Carry-to-risk was the best signal of 2017 but lost in
December by staying long into the sell-off.

**D. Cross-market carry pair** (J.P. Morgan, A cross-market bond carry strategy, Mar 2006). Each month, receive
the 10y of the market with the steepest 10y-1M curve and pay the flattest, currency-hedged, 8 markets since 1988:
IR 0.78 with one pair, about 2/3 of the return from carry, correlation 0.05 with a long-bond portfolio. The IR was
only 0.34 in 1988-95 against 1.47 after 2000 and 0.36 since 2005, so the edge is episodic.

**E. Real-yield pair, removing a hidden duration bet** (J.P. Morgan, Rule-based Fixed Income Monthly, Nov 2012).
Receive the 2 highest vs pay the 2 lowest real-yield markets: IR 0.65 with beta 0.4 to the market. Japan was
permanently lowest and low-vol, so the pair was structurally long duration. Excluding Japan gave IR 0.73 and
beta 0.0.

## Signals & interpretation
- **Score bands (default, not from sources):** |Score| < 0.2 neutral; 0.2-0.5 moderate tilt; >= 0.5 strong.
  Observed per-market range -1.1 to +0.8; the aggregate usually sits within +/-0.5 (published snapshots 2012-2018).
- **Value vs momentum disagreement** is the normal state: C2R correlates -0.01 to -0.21 with bond momentum. A
  near-zero score with large opposite components means "no edge", not "no risk". Report the components. Desk
  screens act only where carry, entry and trend line up (Goldman Sachs FICC and Equities, Global Rates Best Trade
  Report, Sep 2026).
- **Bond momentum drives most month-to-month changes** (weight 0.20 on a +/-1 signal). Flag a flip explicitly.
- **Cross-market pairs:** a signal gap of 100bp in carry or real yield is worth roughly 2.2-2.6bp per month of
  relative yield move. That is about 30bp a year, so check it against costs (4bp per pair per trade) and the
  pair's bp vol before calling it a trade.
- **Crowding check:** when trend followers are already at an extreme in the signal's direction, the asymmetry is
  against adding. Long-end CTA positioning at -2.28 sigma implied little extra selling and a sharp short cover
  on a rally (Citadel Securities, Out of the Woods? A More Constructive Outlook for Fixed Income, Aug 2026). See
  [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md).
- **Estimating trend-follower positioning.** Bottom-up: run moving-average crosses over a fast family (21-100d) and
  a slow one (50-252d), medium = equal blend, risk-parity sizing, and a stop from the high-water mark; 3 lookbacks x 4
  stop levels = 12 models. Biggest flows come from unwinds, not accumulation, and the risk is greatest when all
  three lookbacks are similarly positioned and stretched. On days when 4 or more of the 12 models stopped out, S&P
  futures moved more than average, and the same monotone pattern (more stop-outs, larger moves) held for 10y
  Treasury and Bund futures; the 4-of-12 cut-off itself was stated for equities, and the stop levels are not
  published (BofA, Systematic Flows Monitor, 2 Jun 2025). Top-down: a rolling 2-month regression of a CTA index on
  the first principal component of each asset group; the long-duration beta is the duration bias and long minus
  short-duration beta the curve bias, read through week-on-week changes (BofA, CTAs impact on the rates market,
  18 Aug 2020). Both are proxies of the average CTA. Details: section 11 of the reference.
- **Trend maturity.** The share of the 28 pairwise crosses among spot and 5/10/20/30/50/100/200d averages that are
  bullish (MAA) labels a trend (above 60 up, below 40 down). In G10 FX an extended uptrend gained strength a week
  later only 44% of the time and an extended downtrend bounced 55%; stretched trends held when the direction of
  vol agreed. Apply it to the return index as a stretch flag, not a signal (FX evidence; BofA, FX Quant Primer,
  1 Oct 2018; section 12 of the reference).
- **Scorecard display:** map each component to -5..+5 by percentile rank within its own history (2y, except
  fair-value models) (J.P. Morgan,
  Global Fixed Income Markets Weekly, Aug 2026). Rank-based displays are not comparable across markets; never
  rank countries on them.
- **Exit logic:** momentum-type positions exit when the signal turns (that is the stop). Value positions (C2R,
  real yield) should not carry tight stops; exit on the signal or the holding period (Ernest Chan's rule for reversal models: a stop just
  re-enters the same-sign signal; Quantitative Trading, 2009).

## Pitfalls
- **Secular-bull bias.** Backtests since 1990 sit in a 30-year rally: 12m momentum looked best because it was long
  77% of the time. Always show IR minus long-only IR and % time long.
- **Bond-equity correlation sign.** Contrarian equity momentum assumes negative correlation (true since the late
  1990s). When policy or inflation drives both assets the correlation turns positive and the signal loses. Default
  (not from source): halve its weight while the rolling 1y correlation of daily 10y bond (receiver) returns and
  equity returns is above 0. Use bond returns, not yields: the yield-equity correlation has the opposite sign.
- **Trend crosses as a black box.** Golden and death crosses give back much of the trend when used as entry and
  exit, the event samples are small (14-17 signals once conditioned on the 200d slope), and conditioning can reverse
  the sign of a result (it did for oil). Report the count with every hit rate. Exit trend positions with an ATR
  trailing stop (long: prior low minus ATR; short: prior high plus ATR) or on the signal; a trend-line break needs a
  filter such as a close 1% beyond the line or a break larger than the ATR (BofA, Technicals Explained, 14 Jan 2025).
- **Range-bound and sell-off markets** defeat 1m-and-12m momentum (it needs prolonged weakness to turn short).
  Post-crisis policy-driven whipsaws hurt it. A neutral band (for example +/-5bp around a 6m moving average of the
  yield) cuts flips (Salomon Brothers, Understanding the Yield Curve Part 4, Aug 1995).
- **Duration carry-to-risk misfires at turns.** In 1991 and 1998 a flat curve kept it short while bonds rallied on
  weakness (a carry-level failure). In Dec 2017 it stayed long into a sell-off (J.P. Morgan, Simple rules to trade
  duration, Oct 2012; Update on systematic rule based trading strategies, Jan 2018).
- **Cross-market spread carry fails on vol and crowding, not on the carry level:** flat 1999-2002 after LTCM, weak
  in recessions and when bond vol rises. A high 12m hedge-fund beta to the strategy preceded the LTCM and 2001
  drawdowns; use it as a crowding flag (J.P. Morgan, Exploiting carry with cross-market and curve bond trades,
  Jan 2007).
- **Look-ahead in macro inputs.** PMIs, unemployment and revision ratios are revised, and survey inflation updates
  twice a year. Use first-release vintages by `pub_ts_utc`. Rebalancing on the 2nd working day exists because of
  the PMI release date.
- **Pinned markets.** Under BoJ yield-curve control the source replaced JPY with the next-lowest-carry market
  (Feb 2017). Treat any market with a policy cap or peg on 10y the same way. JGB signals
  were weak (IR about 0.3) even before YCC.
- **Hidden duration in cross-market pairs.** Low-yield, low-vol markets (JPY, CHF) sit permanently at the bottom
  of the real-yield ranking (the pay leg) and high-beta markets (AUD, NZD) near the top (the receive leg), so the
  pair is structurally long duration: beta 0.4 with Japan, 0.0 without (J.P. Morgan, Nov 2012). Vol-match the
  DV01s and check the pair's beta to the G10 average 10y.
- **Track records decay.** The combined since-1998 IR went 1.31 (Apr 2015), 1.26 (Feb 2017), 1.20 (Jul 2017),
  1.17 (Jan 2018). Haircut published IRs by at least a third for live use (default).
- **Equal country weights** ignore liquidity: NZD and NOK count as much as USD. Cap small markets.
- **The return proxy has no roll-down.** On a steep curve that understates long-duration carry; for futures use
  roll-adjusted returns, never price-level splices.
- **Narrative override.** The sources apply discretion (they discounted a US unemployment fall far from FOMC-relevant
  levels). Log every override next to the systematic value so the rule's live record stays clean.

## Output
1. **Duration scorecard** (one row per market plus G10 aggregate): `market, instrument, slope_bp, c2r, c2r_pos,
   mom, pmi, revisions, equity, score, score_prev_month, signals_missing, dv01_target_ccy`. All signed + = long
   duration. Name any renormalised score.
2. **Cross-market table:** `signal, long_1, short_1, long_2, short_2, raw values, bp-vol ratio, DV01 ratio,
   expected drift bp/month (pooled-regression coefficients), cost bp`.
3. **Diagnostics:** % time long, IR vs long-only, rally vs sell-off IR, last-12m return per signal, signal
   correlations, rebalance-day range.
4. **Overlay verdict for the RV book:** current residual beta (10y-eq DV01), score, action (keep / cap / hedge),
   and the hedge instrument.
5. Hand a proposed cross-market pair or a deliberate duration tilt to
   [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md). Hand per-signal series to
   [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md) if the weights are being
   revisited.

## Scripts
- [`scripts/signals.py`](scripts/signals.py): reads `curve_par` and builds the 10y excess-return index, EWMA
  carry-to-risk and its percentile position, 1m-and-12m momentum, cross-sectional carry / C2R / slope-reversal pair
  signals, and the renormalised composite. Macro and equity signals computed from `macro_series` go in with
  `--extra` (long CSV `date, curve_id, signal, value`; signal names `pmi`, `revisions`, `equity`; `date` = the first date the value was publicly known, never the reference month).
  `macro_momentum()` and `equity_contrarian()` build them, `monthly_hold(sig, nth)` samples the nth row of each
  month (-1 = month-end default; `nth=1` = the source's 2nd working day) and trades from the next row, and `--out`
  writes the canonical `signals` long format. Gaps of up to 5 rows per curve are forward-filled so a move across a
  local holiday is not lost. Unknown `--extra` signal names get no weight (the CLI warns).
  `python scripts/signals.py --curve-par data/curve_par.parquet --snap eod_ldn --curves USD-SOFR,EUR-ESTR,GBP-SONIA,JPY-TONA,AUD-BBSW,CAD-CORRA`
  (two pairs need at least 4 markets; use `--n-pairs 1` for 2-3). The script's `xs_carry` uses `--short-tenor`
  (3M default); pass `--short-tenor 1M` to match the cross-market carry definition above.
  `--selftest` checks the par annuity, the excess return (carry and duration terms), gap handling, EWMA vol, the
  +2/-2/0 percentile rule, the momentum, macro and equity signs, both published J.P. Morgan combined tables, pair
  ranking, truncation invariance (no look-ahead), the rebalance day and a CLI run on a synthetic `curve_par`.
  Each core formula was mutation-tested: flipping or dropping it makes the selftest fail.

## Related skills
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): carry + entry (z-score) + trend scoring of individual RV packages
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): percentile and z-score mapping, lookbacks, cross-sectional ranking
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): IC/IR, correlation-aware weights, horizon and turnover
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): moving-average, breakout and oscillator overlays on single series
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): FX-hedged cross-market spreads and betas for the pair legs
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): exact carry and roll-down behind the carry signals
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): CTA and real-money positioning as a crowding check
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): regime labels for the rally / sell-off and cycle splits
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): the same rule-based approach for short-gamma timing
- [bt-backtest-design](../bt-backtest-design/SKILL.md): point-in-time data, monthly rebalancing and cost modelling for the backtest
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): combining the overlay with RV sleeves
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): vol-targeted DV01 budgets and stops
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): expanding-window and multiple-testing checks before trusting these IRs
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PC1 exposure of the RV book for the overlay
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): calendar and seasonal effects.
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): unit roots, HAC and time-series tools.

## References
- J.P. Morgan (Seamus Mac Gorain) - Investment Strategies No. 74: Simple rules to trade duration (2 Oct 2012): the five duration signals, lookback tests, carry-to-risk percentile rule, 35/20/15/15/15 weights, long-bias and loss-episode analysis
- J.P. Morgan (Mika Inkinen, Fabio Bassi) - Systematic fixed income trading strategies (13 Apr 2015): extension to 10 markets on 10y swaps, five cross-market signals, signal correlations, rally/sell-off and Fed-cycle regime splits
- J.P. Morgan (Seamus Mac Gorain) - Rule-based Fixed Income Monthly (Nov 2012): cross-market signals on 10y swaps, pooled regression coefficients, real-yield pair with and without Japan, track records net of costs
- J.P. Morgan (Khagendra Gupta, Mika Inkinen, Sampath Vijay) - Update on systematic rule based trading strategies (6 Feb 2017, 6 Mar 2017, 10 Jul 2017, 8 Jan 2018 editions): risk-limit reading of the score, country snapshots, vintage IRs, JPY/YCC override, 2017 loss
- J.P. Morgan (Nikolaos Panigirtzoglou) - Investment Strategies No. 15: A cross-market bond carry strategy (9 Mar 2006): 10y carry pairs across 8 markets, IR by period, return split, directionality
- J.P. Morgan (Nikolaos Panigirtzoglou) - Investment Strategies No. 31: Exploiting carry with cross-market and curve bond trades (11 Jan 2007): spread carry-to-risk, constant vs variable risk, rebalancing frequency, crowding via hedge-fund beta
- Salomon Brothers - Understanding the Yield Curve, Part 4: Forecasting U.S. Bond Returns (Aug 1995): term spread, real yield, inverse wealth and momentum-dummy regression; out-of-sample protocol; duration-target mapping
- Dirk Willer, Alex Saunders - Trading Global Macro Markets (Wiley, 2026): moving-average trend rules on a bond index, valuation regression verdict, data-surprise trend rule, vol targeting
- J.P. Morgan (Francis Diamond et al.) - Global Fixed Income Markets Weekly (21-22 Aug 2026): percentile-rank scorecard of macro, fair-value, positioning and momentum signals for 10y and 2s10s
- Citadel Securities (Frank Flight) - Out of the Woods? A More Constructive Outlook for Fixed Income (25 Aug 2026): CTA positioning simulation and the asymmetry it implies
- BofA Global Research - Systematic Flows Monitor: More CTA Models = Better Impact Estimates (2 Jun 2025): trend lookback families (21-100d, 50-252d), 12-model lookback-by-stop ensemble, sigma-move definition, stop-out count vs size of move
- BofA CTA research: "US Rates: CTAs impact on the rates market" (Bruno Braizinha, 18 Aug 2020): top-down CTA replication by rolling regression on principal-component features, duration and curve bias from betas, validation against momentum and positioning data
- BofA Global Research - Technicals Explained: In 2025, get to know technical strategy (Primer) (Paul Ciana, Stephen Suttmeier, 14 Jan 2025): golden/death-cross event study on the long bond future, 10/20/30d triple-MA score, ADX regime gate, weekly MA trend states, ATR stops
- BofA Merrill Lynch - Global Rates and FX Primer: FX Quant Primer (Vadim Iaralov, Alice Leng, Athanasios Vamvakidis, 1 Oct 2018): rank-to-score scorecard and two-step filter sort, moving-average aggregator and up/down-vol positioning proxies, momentum persistence (FX evidence)
- Goldman Sachs FICC and Equities (IRP Market Strats, desk material) - Global Rates Best Trade Report (30 Sep 2026): carry / entry / trend screen and quadrant logic for combining value with momentum
- Richard Grinold, Ronald Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): combining correlated signals, IC_com = IC sqrt(2/(1+gamma)), time-series vs cross-sectional scores
- Rishi K. Narang - Inside the Black Box (3rd ed., Wiley, 2024): linear vs conditional alpha blending, trend-follower hit rates
- Ernest P. Chan - Quantitative Trading (Wiley, 2009): exits and stops for momentum vs mean-reversion signals
- Asness, Moskowitz, Pedersen - Value and Momentum Everywhere (Journal of Finance, 2013) (external): value and momentum across asset classes including government bonds
- Moskowitz, Ooi, Pedersen - Time Series Momentum (Journal of Financial Economics, 2012) (external): time-series momentum in bond futures
- Koijen, Moskowitz, Pedersen, Vrugt - Carry (Journal of Financial Economics, 2018) (external): carry as a cross-asset return predictor, including bonds
- Antti Ilmanen - Time-Varying Expected Returns in International Bond Markets (Journal of Finance, 1995) (external): term spread, real yield and inverse wealth as global bond return predictors
