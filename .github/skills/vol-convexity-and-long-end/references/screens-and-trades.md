# Screen tables, backtests and trade lifecycles (long-end convexity)

Loaded from [SKILL.md](../SKILL.md). Every number is as printed in the cited note; the dates matter, because the screens
are snapshots of different regimes. Curve = later forward minus earlier forward (bp); flattener = receive later / pay earlier,
DV01-neutral. "1y carry" bp/yr per unit curve DV01; BE = daily breakeven (bp/day), 0 when carry is positive; RV = 1y realised daily vol of the long leg (bp/day).

## 1. USD flattener screen, 8 May 2019 (Citi, Trading long-dated convexity, May 2019)

| Pair | Curve | 1y z | 3y z | 1y carry | BE | RV | BE/RV |
|---|---|---|---|---|---|---|---|
| 10y5y/15y15y | -10.1 | 2.50 | 0.19 | -2.91 | 3.5 | 3.2 | 1.07 |
| 10y10y/15y15y | -8.8 | 2.15 | 0.39 | -1.64 | 3.0 | 3.2 | 0.94 |
| 10y10y/20y10y | -13.2 | 1.87 | 0.53 | -1.75 | 2.6 | 3.1 | 0.84 |
| 10y10y/20y15y | -16.7 | 2.41 | 0.50 | -1.88 | 2.5 | 3.1 | 0.79 |
| 10y10y/25y10y | -20.1 | 2.38 | 0.55 | -1.83 | 2.2 | 3.0 | 0.72 |
| 15y5y/20y10y | -11.3 | 1.16 | 1.01 | -0.31 | 1.3 | 3.0 | 0.42 |
| 15y5y/20y15y | -15.2 | 1.62 | 0.99 | -0.44 | 1.3 | 3.0 | 0.45 |
| 20y5y/25y10y | -9.1 | 1.95 | 0.87 | +0.13 | 0.0 | 3.0 | 0.00 |

Check with the formula: carry -1.75bp/yr with dD ~ 9.9 gives sigma_BE = sqrt(1.75e4/9.9) = 42bp/yr = 2.65bp/day (printed 2.6).
15y5y/20y10y: dD ~ 7.3 and carry -0.31 gives 20.6bp/yr = 1.3bp/day (printed 1.3). Both tie out, so the script and the screen use the same definition even though the source does not state its conversion.

Chosen trade: 15y5y/20y10y (receive 20y10y, pay 15y5y), -11.3bp at the upper bound of the range since 2002, carry -0.31 (text says about -0.44), BE 1.3 vs 20y10y realised 3.0 (1y) / 2.8 (3m); picked over 15y5y/20y15y and 20y5y/25y10y for tighter market.

## 2. Backtests

- Citi ($100k DV01, yearly roll, 25bp delta hedge; avg daily P&L $K / daily P&L vol $K / Sharpe): 10y5y/15y15y 0.67/195.3/0.05; 10y10y/15y15y 1.15/142.4/0.13; 10y10y/20y10y 2.28/222.1/0.16; 10y10y/20y15y 3.20/208.5/0.24; 10y10y/25y10y 5.40/247.6/0.35; 15y5y/20y10y 2.92/251.5/0.18; 15y5y/20y15y 3.79/241.7/0.25; 20y5y/25y10y 4.09/219.3/0.30. 10y10y/25y10y: monthly P&L correlation with change in 1y10y vol ~26%, daily skew ~0, outperformed in vol spikes, flat since 2013 although 1y10y vol fell ~50 normals; versus short delta-hedged 1m10y straddles Sharpe ~0.84 but skew ~ -3 (Citi, Trading long-dated convexity, May 2019).
- Costs (one way, mid to bid/offer, bp): initiation 0.75 for liquid pairs (10y10y/20y10y, 15y5y/20y10y), 1.0 otherwise; delta-hedge/roll 0.3-0.4 (same note). Mar 2020 stress: ~0.6bp on 10y swaps and multi-leg long-end bid/offer far wider.
- Low Sharpe (0.16-0.35) is not a reason to reject: the book is structurally long vol and diversifies carry/short-gamma books (same note).
- JPM curve-vs-swaption backtest (daily from Jan 2009, 1y horizon; when expected payoff > 0 put on the flattener and sell 1Yx30Y ATMF straddles sized so premium = 1y carry; reverse when negative) for 25Y/20Yx5Y vs 30s/50s: % days curve gamma cheap 100% vs 70%; hit rate 86% vs 56%; average P/L 11.4 vs 10.4bp of notional; carry +1.1 vs -100.6bp; 5th/95th percentile -10/33 vs -140/128 (JPM, An option by any other name, Feb 2017). A later independent replication (SOFR, 2019-2026, monthly cohorts, $100k DV01, 1y hold) did not reproduce the -100.6bp carry (+1.36bp/yr for 30Y/50Y) and found the curve cheaper than 1Yx30Y ATMF on 97.3% of days: the signal is permanently on and only the choice of pair carries information. Net P&L/ann. Sharpe: 30Y/50Y +$35.4M/1.05; 20Yx5Y/25Yx5Y +$46.8M/2.95 (carry 0.000); 10Yx10Y/20Yx10Y +$48.8M/0.85 (carry -0.52); 5Y/30Y +$86.7M/0.72 (carry -5.44). 76 overlapping 1y cohorts are about 7.6 independent years (internal replication note, 2026).
- Variance decomposition of 1y forward flatteners held to spot (JPM Feb 2017): convexity (= total - carry - spot curve change) is ~80% of 30s/50s P&L variance, ~20% for 2s/5s.
- 1y breakeven parallel shift needed to offset carry (chart read), 30 Sep 2014 to 2 Feb 2017: 2s5s ~560 to ~355bp; 5s10s ~350 to ~225; 5s30s ~235 to ~155; 10s30s ~175 to ~125; 30s50s ~85 to ~55.
- Systematic long-expiry straddle (EUR, Jan 2005 to Nov 2021, buy ATMF straddle, hedge, roll monthly): convexity minus (theta + funding) rose steadily except 2016-19; entry vol had no relation to return, so there was no risk premium for being short long-expiry convexity. Long expiries only; source is marketing material (Nordea, Bonds & bold, Nov 2021, partial read).

## 3. Cross-market screens (Citi Rates Vol Lab, 2019-2020)

- Jan 2020 BE/RV ranges: GBP 0.00-0.89 (15y5y/20y10y 0.29); USD 0.46-1.08; EUR 0.60-1.48; CAD 0.45-1.82; JPY 0.76-1.50. JPY realised 2.4-3.1bp/day vs ~3.9-4.7 elsewhere (Citi, In search of cheap vol, Jan 2020).
- 24 Sep 2019: USD 15y10y/25y10y 1y z 2.06, carry -0.99, BE 1.88, BE/RV 0.50; EUR 10y10y/15y15y curve -15.29, carry -6.31, BE 6.05, BE/RV 1.44 (expensive); CAD 15y5y/20y5y BE/RV 2.00 (most expensive); JPY curves positively sloped (Citi, Buying vol for less, Sep 2019).
- 4 Dec 2019: USD BE/RV 0.45-1.09 (0 for 20y5y pairs), carry -4.16 to +0.43, RV ~4.1-4.2; GBP BE/RV 0.18-0.84 then 0.00, carry -2.45 to +0.89, since-2000 z 1.20-2.05 (Citi, Taking profits on 15y5y/20y10y flatteners, Dec 2019).
- JPM Feb 2018: 30s/50s convexity underpriced in USD and GBP (swap-implied vol below swaption vol); EUR and JPY need higher breakeven vol than swaptions (negative expected payoff). Forward-starting structures best in all four; 20Y/40Yx10Y the winner in USD/GBP (JPM, Valuing convexity in the long end, Feb 2018). EUR 1y value of convexity 10/20/30/40/50y: 1.2/2.3/3.3/3.9/4.5bp vs averages 2.5/4.4/6.1/7.4/8.6 (z -1.3 to -0.7); GBP 2.0/3.5/4.9/6.1/7.3 vs 3.1/4.9/6.2/7.6/8.8.
- Jul 2026 30s50s: EUR -28.8bp, USD -26.6, GBP +16.8; EUR flattest despite lowest implied vols, GBP least inverted despite highest implied vols. Idea (relayed hedge-fund sales view, not research): pay EUR 30s50s steepener and buy 5y10y straddles to orthogonalise to vol; 5y10y vol expected return ~ -2bp-vol/yr against ~ +1bp/yr curve carry; 1-2y expiries implied/realised >100% "punitive", 7-10y expiries ~ zero net carry (Citi Markets, EUR 30s50s steepener vs 5y10y vol, Jul 2026; sizings in the note do not reconcile).
- EUR forward value of convexity, 22 May 2019 (bp, 1y): 4y1y 1.4, 10y2y 3.2, 15y5y 4.9, 20y5y 5.9, 25y5y 6.7, 30y10y 7.6; 1y carry&roll for long forwards negative (15y5y -2.6, 20y5y -4.3, 25y5y -3.5) and offset by convexity (Nordea, EUR Rates Flash, May 2019). EUR 6s value-of-convexity grid, 12 Aug 2025: 20y fwd 10y 9.8bp, 30y fwd 1y 13.1bp (vol input not stated). Receive EUR 20y5y/25y5y at -9bp (target -15, stop -7, 12m roll 3.4bp, ratio 0.30) as a hedge for consensus steepeners (Nordea, The quiet game, Aug 2025).
- Fixed-income note on JPY: JGB 20s30s predictably bear-flattens/bull-steepens when life insurers buy on a cap; YCC to 10y in 2016 collapsed 1y2y/1y10y vol (Düring 2021; Citi Mar 2020).

## 4. Forward steepeners as short vol (USD, 8 Jun 2023; Citi, Forward steepener and vol divergence, Jun 2023)

Curve / 3y z / since-2000 z / 1y carry / BE / RV / BE/RV: 10y10y/15y15y -51.5 / -0.91 / -2.07 / 6.89 / 6.18 / 5.30 / 1.17;
10y10y/20y5y -62.4 / -0.91 / -1.47 / 10.31 / 7.22 / 5.24 / 1.38; 10y10y/20y10y -76.1 / -0.96 / -1.96 / 8.31 / 5.71 / 5.11 / 1.12;
15y5y/20y10y -64.5 / -1.03 / -1.87 / 3.93 / 4.59 / 5.11 / 0.90; 15y5y/25y10y -94.1 / -1.11 / -2.58 / 1.66 / 2.29 / 4.66 / 0.49.
Reading for steepeners (short convexity) is inverted: BE/RV above 1 means the carry pays more than realised moves would cost. Preferred 20y5y-10y10y (BE/RV 1.38, better carry vs entry z); wait for FOMC (hawkish skip could bear-flatten with muted vol). Divergence signal: 2y30y vol vs the 20y5y-10y10y spread. Best carry usually has the worst entry level, so rank on carry/BE and both z-scores.

## 5. Trade lifecycles

- USD 15y5y/20y10y: $50K DV01 entered 9 May 2019 at -11.8bp ($148.8mn 15y5y vs $90.3mn 20y10y), re-hedged every 20bp, MTM +$105K on 16 Oct 2019 despite ~2bp steepening, 20y10y notional reweighted $81.97mn to $84mn (beta 1.025), closed 5 Dec 2019 at -12.5bp mid, ~$187K at mid / +$155K net (Citi, Reweighting and Taking profits alerts, Oct-Dec 2019). Stock/curve correlation ~ -23% but monthly P&L vs equities ~0.
- GBP 15y10y/25y10y: watch list Sep 2019 at -3.3bp (z 2.10/2.35/2.44, carry +0.91, BE 0), opened 17 Jan 2020 at about -11bp (50K DV01, carry +0.52, BE 0.00, "effectively free convexity"), hedged every 25bp in the 25y10y, closed 26 Mar 2020 at about -19bp as BoE QE flattened the curve: GBP 445K net = ~115K curve + ~330K convexity (Citi, Taking profits on GBP flatteners, Mar 2020). The weekly of the same date quotes +$542K (ratio 1.22 to 445K: plausibly GBP vs USD, not confirmed). Convexity was ~3/4 of P&L in the vol spike.
- USD 15y5y/20y10y, 26 Mar 2020: -5.21bp, 1y z 4.21, carry +0.11, BE 0, RV 6.40; "effectively a free convexity buy" but not initiated because bid/offer was wide (Citi, Liquidity, vega, and convexity, Mar 2020; partial read).
- Long-end fly instead of steepener: receive 20y10y vs pay 10y10y and 30y10y (1x2x1, beta-adjusted), entered Feb 2020 at 16bp, unwound at 10bp on 15 Jun 2020 once bid/offer normalised to ~3bp: $360K (Citi, Taking profits on long end butterfly, Jun 2020).
- JPM forward flatteners (USD): receive $185mn 30Yx10Y (1.70%) / pay $125mn 10Yx10Y (2.09%) at -39bp, slide -4bp/1y; pay $250mn 15Yx5Y / receive $357mn 35Yx5Y at -35.7bp, slide -2bp; receive $250mn 25Yx15Y / pay $191mn 15Yx15Y at -16.9bp, slide -0.6bp, closed +4.1bp (JPM weeklies Aug 2019 - Feb 2020). 6m 10s/20s/30s payer fly: buy $100mn 25-delta 6Mx20Y payers vs sell $93mn 6Mx10Y and $35.6mn 6Mx30Y, premium neutral, for 20s underperformance in a sell-off as VA hedging reverses (JPM, For cheap gamma, look to the long end, Aug 2019). 10s/20s/30s swap fly fair value regression on 10s30s and VA liability duration: R² 98%, std error 0.5bp (same note).
- Vol-side relatives: short $30mm 3y10y ATMF straddles ($2.89mm) vs $54mm 10y10y/15y15y flattener (net curve DV01 $26k, net vega -$28k, target +$400k, stop -$250k; +$67K after one week, Oct 2026; Citi Rates Vol Lab and US Rates Weekly, Oct 2026). Fit: 3y10y vol = -0.992 x (15y15y - 10y10y, bp) + 48.3, R² 0.90 over 3y of levels; residual is the signal (3y10y ~14 normals too high, Oct 2026). Re-fit before using the coefficients.
