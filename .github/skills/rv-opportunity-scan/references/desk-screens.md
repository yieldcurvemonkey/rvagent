# How research desks run RV screens (what to copy, what to avoid)

Detail behind the "Method" of [SKILL.md](../SKILL.md). Every number is from the cited note. Desk screens are
backward-looking and illustrative: the most attractive rows are "not necessarily trades that we would recommend" (Citi, Rates Vol Lab,
12 Jun 2023). Use them as templates for columns and filters, not as a source of ideas.

## 1. Trade radar (Citi, Global Macro Trade Ideas Radar, 13 Aug 2026)
A radar is a standing list of open ideas with a uniform record: entry level, target, stop, current level, mark-to-market,
rationale, risks. Rules visible in the note:
- Inclusion: liquid and executable; minimum 100k DV01 in DM rates (40k in EM); risk/reward above about 1.5:1.
- Risk normalisation per idea: historical VaR and implied VaR (labelled 5Y5D, 95%), in USD thousands, plus "units of risk"
  normalised by HVaR. Example: AUD 1y-forward 2s5s10s fly on -100k / +100k / -100k DV01 legs, HVaR 801k, IVaR -356k.
- Reward/risk arithmetic from the entries (levels in bp):

  | Idea | Entry | Target | Stop | Gain | Risk | R:R |
  |---|---|---|---|---|---|---|
  | Receive AUD 1y-fwd 2s5s10s fly | 9 | -11 | 16 | 20 | 7 | 2.9 |
  | 1y-fwd 5s30s steepener (50k DV01) | 75.5 | +45 move | -30 move | 45 | 30 | 1.5 |
  | Receive 6s 20y5y/25y5y (Nordea, Aug 2025) | -9 | -15 | -7 | 6 | 2 | 3.0 |
  | Receive 6s 1y2y/3y2y/5y2y fly (Nordea, Jan 2024) | -8 | -25 + roll | +5 | 17 | 13 | 1.3 + roll |

- Closed-trade log with the lesson for each loser (e.g. a received December-2027 SOFR-futures outright -$240k; 10y OAT credit fly -9bp against a
  stop at 69; pay 6m-forward GBP 5s30s -113k after the bull steepening failed). A stop breach (33bp flattening against a
  30bp stop) is an exit, not a re-underwrite.
- Positioning can override valuation and an exogenous shock can overtake the thesis: the radar carries a risk line per idea.

## 2. Scorecard with attractive quadrants (Goldman Sachs, Global Rates Best Trade Report, 30 Sep 2026; desk material)
Per candidate (outright forwards, curves, flies, per currency and across G10):
- Carry (ex-ante Sharpe) = implied 3m carry and roll / 3m realised vol, annualised. Check: Sharpe ~ 2 x 3m carry / printed vol;
  USD 10y5y/15y5y/20y5y fly carry 1.8bp, vol 3.0 -> 1.2; CHF 1y1y/2y1y 7.7bp on 12.3 -> 1.25 (printed 1.26).
- Entry z = (level - 5y average) / 5y standard deviation; also min/max, 25th/75th percentile, level 3m ago.
- Trend = vol-adjusted 2-week change (USD 1y10y +34.5bp in two weeks, trend +14.06).
- R = correlation with outright rates; Carry/R = Sharpe / (1 + |R|): USD outright forwards sit at R 0.85-1.0 (the note shows Carry/R
  near 0 for them); USD 10y5y/15y5y/20y5y Sharpe 1.20, R 0.26, Carry/R 0.95 = 1.20/1.26. The formula only halves a Sharpe at |R| = 1, so also
  filter on |R| itself (Step 4 item 6 of SKILL.md).
- Quadrants (payer perspective): "Receive" = carry < 0 and z > 0 (top-left of Carry-vs-Entry); "Pay" = carry > 0 and z < 0.
  A candidate needs the pairs to agree: carry and trend of the same sign, trend and entry opposing in the right way.
  CAD 1y1y/2y1y/3y1y: top carry 1.47 but entry +0.86 and trend +8.85 conflict -> excluded by construction.
- Composite = distance from the origin of the orthogonal projection of the point onto a plane (or line) fitted by least squares
  to ATTRACTIVE trades only; refit per screen. Scores are rankings: EUR 10y2y/12y3y/15y5y scores 2.64 in the EUR screen and 1.99
  in the global screen. Do not compare across screens or dates. A high score can come from entry and trend with tiny carry.
- Top global rows (Carry / Entry / Trend / Score): EUR 5y5y/10y5y/15y5y fly 0.04 / -0.95 / +14.10 / 2.69; JPY 1y1y/2y1y/3y1y fly
  +1.20 / -0.71 / +7.66 / 2.60; AUD 1y 2s5s10s -1.09 / +1.01 / -2.74 / 2.33 (receive).
- Desk tables do not disclose weights: rebuild the package yourself before acting.

## 3. Normalised-move anomaly grid (Goldman Sachs, Market Movers, 30 Sep 2026)
- Grid: outrights 2y 5y 10y 30y and forwards 2y3y 5y5y 10y20y; spreads 2s5s 2s10s 2s30s 5s10s 5s30s 10s30s and forward spreads;
  flies 2s5s10s 2s10s30s 5s10s30s; 10y vs Germany (EUR: Italy minus Germany); 10y breakeven; 10y real yield; 10y swap spread
  (EUR: Bund ASW); 2y xccy basis.
- Normalised move = change over horizon / std of changes over the same horizon. 1d and 1w use 62 days; 1m uses 252. Cells flag
  beyond +/-2. Each cell also shows the 1y min/max, quartiles, start-of-horizon level and current level.
- Trap shown in the note: EUR 10y swap spread +4bp printed 5.7 sd because the 62-day window was low-vol. Always print the bp move
  beside the sd move and the window.
- Same note, 1w: USD 10y20y +32bp (4.6 sd), USD 5y5y +29bp (4.5 sd); 1m: USD 5y +60bp (4.0 sd), EUR 2y3y/10y20y -45bp (2.8 sd).

## 4. Bond-level monitors (RiskVal, Overview 201, 12 Nov 2021; Goldman Sachs, US Treasury Relative Value, 25 Sep 2026)
- Roll sheet: on-the-run / front and back CTD / when-issued colour codes, outstanding, central-bank holdings, free float as true
  liquidity, daily change and z.
- Screener over all spreads and flies: filters on maturity, coupon, minimum expected return, mean-reversion return, carry+roll,
  spread length. Expected return = mean-reversion return (bp to the 3m mean) + 3m carry and roll. Diagnostics: MR frequency (times
  the series crossed its mean in 3m) and "1 SD MR frequency". Not all spreads mean-revert: check before trusting the return.
- Worked trade: buy a bond 2 SD cheap to a fitted constant-maturity curve against a bond 0.2 SD rich; C+R 9.9bp vs 9.8bp. The
  fitted-curve RV was 2.7 SD cheap but the direct yield spread only 1.8 SD cheap, and because the fitted spread is theoretical the
  note trades the yield spread. Always confirm a fitted residual with the quoted spread.
- UST layout: scatter of ASW vs maturity coloured by original tenor; sector views 0-1.5y, 1.5-3.5y, 2.5-6y, 5-10y, 10-30y with CTDs
  flagged; each original tenor's ASW curve now vs one month ago; tables for on-the-runs and STRIPS. Flag rule: |3m z| >= 2.
  Matched-maturity and proceeds ASW differ by tens of bp on deep-discount bonds (P-STRIP May-2050: 69.9 vs 122.6, a 52.7bp gap): choose and state one.

## 5. EUR RV monitor (Nordea Markets: EUR Rates Flash 23 May 2019; EUR rates 17 Jan 2024; 12 Aug 2025)
- Rows are forward points (1y1y ... 30y10y) or curve/fly packages; columns: rate, 50d range, 1y (or 3m/6m) carry and roll, convexity
  value, carry-and-roll / 36m realised vol, z, J = carry/vol + z, probability of finishing in the money after a year at 1/3/5/10y
  history, PCA misprice.
- J-score check on the 2019 table (receivers): 1y1y 0.18 + (-1.13) = -0.95; 4y1y 0.43 + (-0.76) = -0.33; 15y5y 0.04 + (-0.62) = -0.58.
  All twelve rows negative: the monitor said "no receivers", and the idea was to pay (belly of 10/20/30y). Weak PCA residuals
  (largest +1.1bp) agreed that nothing was mispriced vs the factors.
- Value of convexity by forward point, bp (2019): 1y1y 0.1, 3y1y 0.8, 5y2y 1.8, 10y2y 3.2, 15y5y 4.9, 20y5y 5.9, 30y10y 7.6.
  Long-end forwards carry mostly convexity, so carry/vol screens must add it back (convexity-adjusted C+R).
- 2024-25 dashboard: Rate, 50d range, carry+roll, convexity-adjusted (C+R)/vol, 50d z, PCA misprice. Carry annualised over 3m
  (3s) or 6m (6s); vol 50d. Mixed conventions are a trap: z is signed by trade direction, PCA misprice is unsigned (par minus fair).
- Carry-fly warning (Aug 2025): P 5y7y/12y8y/20y10y 6s (C+R 14.4, vol 17.0, ratio 0.85, 50d z -1.9, PCA -14.8) screened best
  for carry-to-vol but struggled because the paid 20y did not rise with the 10s30s steepening: positive 10s30s beta means the
  "carry" fly was partly a curve view.

## 6. Rates Vol Lab screens (Citi Research, 2017-2026)
- Convexity flattener screen (4 Dec 2019): per forward-curve pair, curve level, 1y z, 3y z, z since 2000, 1y carry, daily breakeven
  (BE), 1y realised vol (RV), BE/RV; three best marked per metric. Delta-hedged flatteners are long convexity, so LOW BE/RV is
  attractive. Close when carry worsens and BE/RV nears 1 even if the curve thesis holds.
- Forward steepener screen (8-9 Jun 2023) is the mirror image: net short convexity, carry is the income, so BE/RV "meaningfully above
  1" is attractive; plot BE/RV against the since-2000 z and pick the efficient frontier; break ties with the 3y z. The steepeners with
  the best carry usually have the worst entry level.
- Efficient frontier of forward-vol trades (Citi, Left-side vols' outperformance, 22 Jun 2021; Rates Vol Lab 12 Jun 2023): enumerate gamma-neutral calendar spreads and triangles, rank by ex-ante Sharpe
  (vol-adjusted roll), value = 1y z, show the top 20. Realised correlation (6m) stands in for implied: an approximation.
  Sanity-check outliers (a Sharpe of 4.17 in Mar 2020 was flagged for verification).
- Re-hedge a delta-hedged package every 20-25bp; hedge time of day changes realised vol (USD lowest at 9am, highest at 12pm).
- Watch-list rule: do not initiate an illiquid structure on an attractive screen alone (USD 15y5y/20y10y, Mar 2020: 1y z 4.21,
  carry +0.11, left on the watch list for illiquidity).
- Wait for the event before entering a long-end steepener (FOMC): a hawkish outcome can cause a knee-jerk bear flattening.

## 7. Dislocation indicator and back-test (BofA Merrill Lynch, Liquid Insight 2 Jun 2016; European Rates Viewpoint 21 Mar 2018)
- Swap-spread PCA: 2y, 5y, 10y, 30y spreads of one country; two PCs explain "the high 90% area"; residual = actual minus fitted;
  residual z over 250 days; DI = 10-day moving average of the root-mean-square of the four z's. Re-run daily on 1y of data. If DI is
  above a threshold, buy the cheapest and sell the richest by z, 1:1 in bp, exit when DI falls below.
- Results (cumulative bp / Sharpe / days in market / average hold): US threshold 1.0: 267 / 1.2 / 1750 / 32d; 2.0: 51 / 0.4 / 676 / 38d.
  Germany 1.0: 869 / 2.4 / 2278 / 43d; 2.0: 554 / 2.8 / 967 / 21d. Residual half-lives about 20 days. No costs, carry or stops.
- EGB version: 42 spreads (AT, NL, FR, BE, IT, ES, PT vs Bund, several tenors); residual of OLS on N PCs each day, positive = cheap;
  dislocation index = cross-sectional std of residuals, expanding-window z. Chosen spec 11 PCs, 5-day hold, 2x threshold: long hit
  rate 71-75%, short 50-71%; the cheap leg drives P&L. Extending the hold a week almost doubled the average tightening.

## 8. Issuer-curve screen (Citi Research, The High-Grade Beat, 19 Aug 2026; credit, template only)
A curve is flagged when its slope is more than 2.0 sigma steeper or flatter than its 120-day average; also show the bp distance.
Rules worth copying to rates: fixed sample, require 120 days of history, exclude issues younger than 120 days so roll-in does not
fake a signal; split the universe into deciles by equal market value to expose dispersion behind an average.

## 9. Calibration constants from active-management theory (Grinold and Kahn, Active Portfolio Management, 2nd ed., 1999)
| Quantity | Value | Use in a screen |
|---|---|---|
| IC (correlation of forecast and outcome) | good 0.05, great 0.10, world-class 0.15; above 0.20 suspect a faulty back-test | sanity-check any hit-rate claim |
| Direction hit rate to IC | IC = 2 x (correct/N) - 1; IC 0.02 = 51% right | a 55% hit rate is IC 0.10: great |
| IR | ~ IC x sqrt(breadth); breadth = (IR/IC)^2 | breadth counts independent bets only |
| t-stat of alpha | t > 2 ~ 5% chance of luck; 20 tries give a 64% chance of some t >= 2 | an 84-structure screen shows at least about 11 |z| >= 1.5 by chance if z were iid; persistent levels (random walk) give about 33% of days above 1.5 |
| IR quantiles before fees | 90th pct 1.0; 75th 0.5; median 0 | IR 0.5 is "good" |
| Alpha | volatility x IC x score | score = z; scale a signal to risk before comparing |
| Costs | annualised cost = round-trip cost / holding period (years); one day's volatility to trade one day's volume | amortise, and over-estimate |
Dependent signals masquerade as breadth: monthly rebalancing of one annual view is one bet. Overlapping curve structures sharing
legs are one bet; see "Pitfalls" in SKILL.md.
