# Long-end convexity: forward flatteners, breakeven vol and the straddle package

Detail behind section 6 of [SKILL.md](../SKILL.md). Conventions: S/L = rate(L) - rate(S); flattener = receive L, pay S,
DV01-neutral; bp; normal vol; carry in bp per year per bp of DV01 (positive = flattener earns if curve unchanged).

## 1. Why the embedded convexity is cheap (and when it is not)
- Zero-coupon maths: `P = exp(-yT)`, DV01 = `T*P`, convexity = `T^2*P`, so convexity per DV01 is proportional to T. If a 40y and a
  30y had equal yield, long 40y/short 30y DV01-neutral would earn on every parallel move; the 40y therefore yields less. It works
  less cleanly for 10s30s (10s move more than 30s) than for 30s/40s (parallel) (QF Stack Exchange, Why does the ultra long-end
  invert?, 2019).
- Expected return (bp of yield) = carry `(Y - F)*T/PVBP` + slide `(Y_M - Y_{M-T})` + convexity value `0.5*gamma*sigma^2*T/PVBP`.
  Convexity share of P&L under parallel shocks exceeds 20% for 50y at 100bp+ moves and is under 2% for the 2y (JPM, Valuing
  convexity in the long end, 9 Feb 2018).
- Why it stays cheap: no well-defined downside (unlike options); convexity per DV01 falls and curve vol rises as the trade ages,
  so close/roll after a few years; life/VA insurers receiving concentrated in 15-25y keep the >20y curve steeper than fair;
  ALM/LDI regulation ("a function of regulatory fiat") creates kinks arbitrageurs cannot lean against; pro-cyclical (falling
  long yields force more hedging). The strategy is "structurally long volatility unlike some popular systematic carry trades"
  (Citi, Trading long-dated convexity, 9 May 2019).
- Forward steepeners are the mirror: net negative convexity, positive carry, short-vol proxy; long-dated forward curve and implied
  vol normally move inversely (Citi, Forward steepener and vol divergence, 12 Jun 2023).

## 2. Screen columns (Citi grid) and how to compute them
Per pair: level (bp); 1y, 3y and since-2000 z; 1y carry (bp); **daily breakeven** = daily move whose convexity gain offsets the
negative daily carry (0 if carry positive); 1y realised vol (bp/day, later leg); BE/RV. Flag the top 3 per metric.
`sigma_BE_daily = sqrt(max(-carry,0) / (1e-4 * dGD)) / sqrt(252)` with `GD(A,B) = (2A+B+1)/2` reproduces the printed breakevens
(15y5y/20y10y 1.3; 10y10y/20y10y 2.6; 10y10y/25y10y 2.2).

USD screen, 8 May 2019 (curve bp / 1y z / 3y z / 1y carry / daily BE / 1y RV / BE/RV) (Citi, Trading long-dated convexity, 9 May 2019):

| Pair | Curve | 1y z | 3y z | Carry | BE | RV | BE/RV |
|---|---|---|---|---|---|---|---|
| 10y5y/15y15y | -10.1 | 2.50 | 0.19 | -2.91 | 3.5 | 3.2 | 1.07 |
| 10y10y/15y15y | -8.8 | 2.15 | 0.39 | -1.64 | 3.0 | 3.2 | 0.94 |
| 10y10y/20y10y | -13.2 | 1.87 | 0.53 | -1.75 | 2.6 | 3.1 | 0.84 |
| 10y10y/20y15y | -16.7 | 2.41 | 0.50 | -1.88 | 2.5 | 3.1 | 0.79 |
| 10y10y/25y10y | -20.1 | 2.38 | 0.55 | -1.83 | 2.2 | 3.0 | 0.72 |
| 15y5y/20y10y | -11.3 | 1.16 | 1.01 | -0.31 | 1.3 | 3.0 | 0.42 |
| 15y5y/20y15y | -15.2 | 1.62 | 0.99 | -0.44 | 1.3 | 3.0 | 0.45 |
| 20y5y/25y10y | -9.1 | 1.95 | 0.87 | +0.13 | 0.0 | 3.0 | 0.00 |

15y5y/20y10y was chosen over 15y5y/20y15y (0.45) and 20y5y/25y10y (positive carry but a thinner leg) for market depth.

Cross-market flatteners, 4 Dec 2019 (Citi, Taking profits, 5 Dec 2019): USD BE/RV 0.98, 1.09, 0.95, 0.85, 0.83, 0.77, 1.00, 0.80,
0.70, 0.66, 0.60, 0.49, 0.45, 0.00, 0.00 across 10y10y/15y15y ... 20y5y/25y10y (RV about 4.1-4.2bp/day); GBP 0.75 ... 0.18 then 0.00
with positive carry and since-2000 z 1.2-2.05: GBP flatteners better value than USD. Jan 2020 BE/RV ranges: GBP 0.00-0.89, USD
0.46-1.08, EUR 0.60-1.48, CAD 0.45-1.82, JPY 0.76-1.50; JPY realised vol only 2.4-3.1bp/day vs 3.9-4.7 elsewhere (Citi, In
search of cheap vol, 17 Jan 2020).

## 3. Backtest facts (delta-hedged, $100K DV01, yearly roll, 25bp hedge band)
Avg daily $K / daily vol $K / Sharpe (Citi, Trading long-dated convexity, 9 May 2019): 10y5y/15y15y 0.67/195/0.05; 10y10y/15y15y
1.15/142/0.13; 10y10y/20y10y 2.28/222/0.16; 10y10y/20y15y 3.20/209/0.24; **10y10y/25y10y 5.40/248/0.35 (best)**; 15y5y/20y10y
2.92/252/0.18; 15y5y/20y15y 3.79/242/0.25; 20y5y/25y10y 4.09/219/0.30. Monthly P&L correlation with 1y10y vol about 26%, daily
skew about 0, outperforms in vol spikes, flat since 2013; short delta-hedged 1m10y straddles had Sharpe about 0.84 but skew about
-3. One-way costs: 0.75-1.0bp initiation, 0.3-0.4bp hedge/roll.

JPM forward flatteners vs 1Yx30Y straddles (post-Jan 2009, daily entry, 1y horizon, premium = carry): 25Y/20Yx5Y vs 30s/50s: % of
days cheap curve gamma 100% vs 70%; hit rate 86% vs 56%; avg P/L 11.4 vs 10.4bp; carry +1.1 vs -100.6bp of notional; 5/95th
percentile -10/33 vs -140/128. Forward flatteners have lower carry cost and more consistent cheapness (JPM, An option by any other
name, 3 Feb 2017). P/L variance for 1y forward flatteners: convexity about 80% for 30s/50s, about 20% for 2s/5s (chart reads).
1-year breakeven parallel shift (chart reads, 2014 -> 2017): 2s/5s 560 -> 355bp; 5s/10s 350 -> 225; 10s/30s 175 -> 125; 30s/50s
85 -> 55: falls monotonically with tenor.

## 4. Curve-implied vol vs swaption vol (JPM method)
1. Take the implied terminal distribution from ATMF and OTM swaptions (1Yx30Y for a 1y horizon).
2. Multiply by the payoff of the aged flattener at the fixed coupon (coupons = 1y forwards, so carry is included), assuming
   parallel shifts. Positive expected payoff = curve is cheaper long gamma.
3. Curve-implied vol: the normal vol whose expected payoff is zero. If below ATMF swaption vol the curve is cheaper. The two measures
   are highly correlated.
4. Screen forward pairs on 1y expected payoff vs ex-ante 1y slide; the pick in Aug 2019 was pay 15Yx5Y (1.83%) $250mn vs receive
   35Yx5Y (1.49%) $357mn at -35.7bp, 1y slide -2bp (JPM, For cheap gamma look to the long end, 23 Aug 2019). Closed examples:
   30Y/10Yx10Y flattener (receive $185mn 30Yx10Y 1.70%, pay $125mn 10Yx10Y 2.09%, -39bp) +3.0bp; 15Y/25Yx15Y +4.1bp; 1Y5Y/5Y vs
   35Y/5Y +7.9bp (JPM, Renewed Formosa supply, 21 Feb 2020).
5. Assumes near-parallel moves; liquidity in very long forwards can bind; gamma is best sourced at the very long end.

Cross-market convexity value 2018: best value in forward pairs, esp. 20Y/40Yx10Y (high convexity value, positive ex-ante roll), tied
with 15Y/35Yx15Y in EUR; 30Y vol needs about a 20% decline vs 50Y to equate expected returns (JPM, 9 Feb 2018). JPY convexity
generally expensive (30s50s negative expected payoff); GBP swap convexity value exceeds gilts (vol, par vs fixed coupon, rolling vs
fixed maturity).

## 5. sigma_BE vs sigma_imp package (systematic spec)
Fwd curve vs straddle backtest spec (v0.4, Oct 2026):
- Side +1 = DV01-neutral flattener on a forward strip (receive later start l, pay s) + **sell a gamma-matched ATM straddle**;
  enter when `sigma_BE < sigma_imp`. Side -1 = steepener + buy straddle when `sigma_BE > sigma_imp`. `Edge(-1) = -Edge(+1)`.
- Gamma match: `Theta_opt = 1e-4*dD*sigma^2`, `Gamma_opt = 2*dD*1e-4`, premium `= 2e-4*dD*sigma^2*tau0`,
  `k/k_opt = sigma_BE^2/(2*sigma_imp^2)` (dD = start difference for equal tenors = the dGD of SKILL.md).
- Universe: all same-tenor pairs on the 5y strip (10) and 10y strip (6). Filters: dD >= 4.0; |sigma_BE| <= 300; no stale input in
  the last 3 days; backward-only z. Gates: G1 gamma sign `sigma_l/sigma_s >= theta*(1+0.02)`; G2 correlation >= 0.75; G3
  `side*z >= -2.5`; G4 `sigma_imp(t) - sigma_imp(t-10d) <= 8bp`; G7 (optional) persistence: share of last 252d with `sign(E) = side`
  <= 0.6.
- Findings (vs 1Y x 30Y, Oct 2015 - Oct 2026): 10y5y/15y5y and 10y10y/12y10y have `sigma_BE > sigma_imp` on 75-85% of days
  (structural, strip humps near 10y; sigma_BE about 129 on 17 Oct 2026, "mostly not convexity"); 10y5y/20y5y and 10y10y/15y10y 15-36%
  (transient, genuine RV); 20y5y/25y5y, 15y5y/30y5y, 20y5y/30y5y, 15y5y/25y5y, 15y10y/20y10y under 1% (long-end strip straight or
  convex); 10y10y/20y10y 92 vs 91 (dD about 9.9; 6m curve cost 4.2bp vs straddle decay 4.1bp; premium about 8.2bp). Implied vs
  realised on long forwards about 91 vs 61.
- Pitfalls: ratio z-scores that share a common sigma_imp factor are useless for cross-curve selection when vol moves; pooled IC can
  be spurious from cross-curve mean differences; one-sided roll derivatives at strip ends (30y5y, 20y10y) are noisier.

## 6. Delta-hedging and re-weighting
- Re-hedge the longer leg to DV01-neutral every 20bp (USD), 25bp (GBP), band 15-30bp (Citi, In search of cheap vol, 17 Jan 2020).
- Trader procedure: "recalc the delta every 25bp and resize the notionals back to DV01-neutral" (or about every 2 months), typically
  a 2-10mm adjustment on one leg, always at a gain vs initial strike; if you always decrease notionals, the delta hedging is
  eventually an exit; 5% delta hedges at the wings (Trader chat excerpt, strikeless vol, Jan 2026). JPY view: 10y10y/20y10y
  flattening with frequent hedges is the better long-run trade.
- Beta reweight when flows make the curve directional (steepening in rallies, flattening in sell-offs): scale 20y10y by 1.025 vs
  15y5y and keep hedging with the same beta (Citi, Reweighting, 16 Oct 2019). Insurer/VA risk: stocks-vs-curve correlation about
  -23%, monthly trade P&L vs S&P about 0.
- GBP 15y10y/25y10y: $50K DV01 at -11.2bp on 17 Jan 2020, 1y carry +0.52bp, BE 0.00, z since 2000 1.84, re-hedge every 25bp in
  25y10y; closed 26 Mar 2020 at -19bp, GBP 445K net (about 115K curve + 330K convexity); exit because QE-driven flattening could
  reverse on supply (Citi, In search of cheap vol, 17 Jan 2020; Taking profits on GBP 15y10y/25y10y flatteners, 26 Mar 2020).
- USD 15y5y/20y10y on 27 Mar 2020 (watch list, not initiated for liquidity): level -5.21bp; 1y z 4.21; 3y z 3.58; 1y carry +0.11bp;
  RV 6.40bp/day (Citi, Eat pay spend, 27 Mar 2020).
- Forward fly alternative: 10y10y/20y10y/30y10y 1x2x1 (receive 20y10y, beta-weighted slightly net long DV01) entered 16bp late Feb
  2020, unwound 15 Jun 2020 at 10bp offer for $360K; range Jun 2015 - Jun 2020 about -15 to +30bp. In dislocations peak mark-to-market
  on multi-leg long-end packages may be unrealisable (Citi, Taking profits on long end butterfly trade, 15 Jun 2020).

## 7. Forward steepener screens (short convexity)
USD close 8 Jun 2023 (curve / 3y z / z since 2000 / carry / BE / RV / BE/RV) (Citi, Forward steepener and vol divergence, 12 Jun 2023):
10y10y/15y15y -51.5/-0.91/-2.07/+6.89/6.18/5.30/1.17; 10y10y/20y5y -62.4/-0.91/-1.47/+10.31/7.22/5.24/1.38; 10y10y/20y10y
-76.1/-0.96/-1.96/+8.31/5.71/5.11/1.12; 10y10y/25y10y -105.6/-1.04/-2.56/+6.04/3.97/4.66/0.85; 15y5y/20y10y -64.5/-1.03/-1.87/
+3.93/4.59/5.11/0.90; 15y5y/25y10y -94.1/-1.11/-2.58/+1.66/2.29/4.66/0.49. Frontier with BE/RV well above 1: 10y10y/15y15y and
20y5y/10y10y (preferred on 3y z); wait until after the FOMC (a hawkish skip can bear-flatten with muted vol). Entry signal: a
"divergence" (forwards bear-flattened while 2y30y vol collapsed). Efficient frontier: BE/RV (y) vs since-2000 z (x); best carry
usually has worst entry.
Neutralising the received 5y leg removes the directional asymmetry: 15y5y/25y5y is less directional; the 20y5y/25y5y
micro-steepener is "broadly immune to higher rates" (Citi, Higher yields are here to stay, 24 Sep 2026). Spot 5s30s decomposed into
5y forward curves: the 3-week flattening of 4-24 Sep 2026 was -5.7, -8.8, -9.5, -8.8, -7.8bp across 5y5y-5y ... 25y5y-5y.

## 8. Second-order Sharpe for forward spreads (avoid first-order roll/vol)
Do not rank forward spreads by roll-down divided by spread vol: "a false lure ... considerably overestimating some of the ratios".
Include gamma, correlation and full P&L variance. Forward gamma `G ~ -(S/10000) * (h + i)` for a forward from year h to i with PV01 S
(improved: DF-weighted, within 0.5%; up to 10% for long tenors in high-rate regimes). EUR, Aug 2016, pay 2Y3Y/receive 5Y5Y: first-order
Sharpe 0.35 vs second-order 0.39; pay 10Y20Y/receive 2Y3Y falls from 0.25 to -0.01; pay 2Y3Y/receive 30Y20Y flips from -0.25 to +0.18.
Correlations: 2Y3Y-5Y5Y 0.87, 5Y5Y-10Y20Y 0.92, 10Y20Y-30Y20Y 0.96 (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd
ed., 2022, ch.23).
