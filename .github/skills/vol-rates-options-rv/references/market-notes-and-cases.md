# G10 market notes, regime/event rules and a dated case ledger

Detail behind steps 8-9 of [SKILL.md](../SKILL.md). Levels quoted are historical illustrations from the cited notes, not current
data. Where a currency has no sourced vol material it says so; apply the method, but verify conventions and liquidity first
([fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md)).

## 1. Market by market

| Ccy | What the sources say that changes how you apply the method |
|---|---|
| USD | Richest data: full ATMF grid, macro-vol, Board vs swaption, midcurves, CMS. MBS hedging keeps USD vol structurally above other G7 (USD/EUR implied ratio ~1.58 long-run vs 1.55 realised); 3y10y = largest MBS vega bucket, 3m10y = gamma gauge; every $100mm of new MBS ~ $50mm 3y10y straddles bought (Bassman, The Largest Volatility Sale Ever, 23 Mar 2010). Callable (Formosa) supply sits in long expiries; 30y tails repeatedly cheap on models (2019, 2023) yet 30y gamma can be rich to 1m realised; 30y tails had the highest implied/realised (~1.5) on 2 Oct 2026. Cash-settled swaptions off a swap-curve annuity; LIBOR-era swaption vol exceeded bond-option vol because the unsecured basis widens as rates rise. Macro-vol fit must exclude ZIRP (USD 1996-2008 + 2017-19). |
| EUR | Macro-vol fit on the negative-rate era (2016+ or 2002+ in the 2026 version); intraday realised on London hours; 1m10y gamma structurally cheap vs 1m5y and 1m30y (price-insensitive systematic/QIS selling, "so many systematic trades have been fully harvested"); 5y/7y tails often rich on PCA; 10y10y long-expiry straddles historically underpriced vs realised (Jan 2005-Nov 2021 backtest; applies to long expiries only, not 3m10y/1y10y); Danish callables carry 5y and 10y expiry vol (5y20y proxy). Euribor/Liffe/Eurex futures options are margined (no discounting). Wedges (floorlets on the curve) structurally negative expected return. |
| GBP | 1m10y implied below delivered ahead of Nov 2012 MPC (cross-ccy PCA). GBP-EUR 3Mx10Y vol spread screened too narrow in Aug 2026 (divided MPC, term-premium betas, budget risk): long GBP vs short EUR gamma as a low-beta long-GBP-gamma proxy. 30s/50s convexity under-priced vs swaptions in USD and GBP (swap-implied vol < swaption vol; breakeven-vs-swaption method, see [vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md)). Cash-settled valuation same day (not T-2). Market fully moved LIBOR -> SONIA. |
| JPY | YCC collapsed 1y2y/1y10y vol after 2016 and holds forward vols low; JPY convexity generally expensive; realised 2.3-3.1bp/day vs ~3.9-4.7 elsewhere (Jan 2020). Aug 2026: realised up, implied "still low vs realised"; transmission from overseas rising (Citi, Japan Rates Weekly, 14 Aug 2026). Gamma/vega border tilted right (4y expiry for 1y tails). Realised/implied by underlying (Jun 2012): 2y 7/16, 5y 16/19, 10y 27/34 bp - implied above realised everywhere, least at 5y. JPY 10y bp vol exceeded USD in 2013 so lognormal vol was >2x. A "Japan Scenario" cuts rate options 30-40% (Bassman, 6 Sep 2012). BoJ communication anchors the short end: carry rules replace under YCC. |
| CAD, AUD, NZD, CHF, SEK, NOK | No vol-RV material in the knowledge base. Only conventions: cash-settlement valuation same day for CAD; AUD/NZD STIR futures are quoted in yield and valued via a synthetic bond price (affects options on futures); CHF Liffe margined options; NOK/NZD/DKK are not in the tpSEF swaption list (min sizes elsewhere: CAD 5mm, AUD 25mm, SEK 5mm, CHF 10mm, JPY 2.5bn); AUD/NZD cross-market vol spreads exist as cross-currency straddle switches (long USD 6Mx2Y vs AUD 6Mx2Y ATMF straddle, AUD 46.7c vs USD 65c, J.P. Morgan, A comprehensive look at convexity hedging in interest rates, 29 Mar 2019). Expect wide bid/offer and sparse grids: use fewer points, wider z thresholds, and say the quotes are indicative. |

## 2. Regime and event rules
- **Fed cycle**: rate vol is more predictable than FX/equity vol and is driven by the cycle phase: spikes around the first
  cut, the last cut, the first hike and when the Fed accelerates; quiet in late hiking cycles and in the pause between the last
  hike and the first cut (Willer & Saunders, Trading Global Macro Markets, 2026). "A more hawkish Fed has historically been a
  favourable environment for selling gamma"; "a flatter curve is typically a lower-vol environment" (Citi Rates Vol Lab: Year-Ahead,
  12 Dec 2016; The art of gamma hedging, 12 Mar 2018). Short gamma's success is "more dependent on central-bank predictability
  than on the point in the cycle" (BofA, US Vol Primer, 11 Mar 2024).
- **ZLB entry**: do not sell delta-hedged gamma right at ZLB onset. Mar 2020: 1m10y 103nv, 10y swap mid-to-bid ~0.6bp; selling
  hedged gamma did not pay consistently until months after the Fed went to zero and began QE. Sell VEGA (2y2y straddles at 55nv)
  instead; YCC collapses upper-left vol (Citi, 30 Mar 2020; Eat, pay, spend, 27 Mar 2020).
- **Rising rates + rising vol**: ratio payer spreads lose when rates and vol rise together (Barclays, Global Rates Weekly, 2 Oct
  2026); vol "is a plateau, not a peak": after a >25bp sell-off, retracement of implied vol was ~2% (2y), 36% (5y), 33% (10y)
  from the initial move and 55-69% from the peak; do not sell vol after a spike unless yields stabilise (Goldman Sachs, Global
  Rates Trader: Reaching Limits, 2 Oct 2026).
- **Vol regime stops**: stop out steepener/spread trades on a vol-regime shift; after a "lognormal shuffle" rally a shift to higher
  vol makes price action brittle (J.P. Morgan IRD, 6 Mar 2020). When MOVE reaches ~80 it usually "explodes to 125 or beyond" rather
  than reverting to 100; "buy at 80, sell at 120" is hard to execute because extremes coincide with calm/panic (Merrill Lynch RateLab,
  7 Oct 2008; Bassman, The Big 'O', 22 Aug 2023). MOVE ranged 100-140 since 2021 vs a post-GFC average of 65.9 (Bassman,
  Chekhov's Gun, 29 Apr 2025).
- **Events**: one-day swaption breakevens (premium of a 24h-expiry swaption / swap DV01, struck 11am the day before) priced FOMC
  and payrolls ~1-1.5bp richer than the broader surface (more premium in short tails), justified by realised; CPI ~fair. Depth:
  into payrolls top-3 UST depth falls to < 1/4 of base; recovery 15-30 min (worst days 1h+); FOMC days volume ~2x, price impact
  ~2x, realised ~2x (J.P. Morgan, When the going gets tough, the tough get going, 5 Nov 2019). Event-vol extraction: 1m-forward 1m10y
  = 94bp; referendum day 26.2bp/day (416bp annualised) vs 1.57bp/day otherwise (Darbyshire, 2022). FX analogue: 1-day event vol is
  priced at only ~50-60% of the expected move; selling a hedged straddle expiring just after the event, held to expiry, was
  positive in several emerging-market elections with the best entry ~4-5 weeks out (J.P. Morgan FX Markets Weekly, 21 Aug 2026).
  Elections: bond/FX vol rises 25-50 days before and unwinds after (Willer & Saunders, 2026). Hurricanes: 3Mx10Y straddles
  delta-hedged for 1m from landfall generally lost -> stay short upper-left gamma (J.P. Morgan IRD, 14 Sep 2018). Government
  shutdowns tend to be vol-negative (data delayed) (Citi, 1 May 2017).
- **Liquidity -> vol**: depth and HFT share are inversely related to implied vol; fast-flow share explains realised vol (a +10pp
  fast-flow share ~ −10abp realised in the fitted map); allow 15-60 min for depth to rebuild after top-tier releases (J.P. Morgan,
  Fast and furious, 20 Nov 2018; Far from the shallow now?, 12 Apr 2019). Inverted expiry curve (1Mx10Y > 1Yx10Y) is a stress
  gauge (J.P. Morgan, Are we there yet?, 1 Apr 2020).
- **Flow stories**: MBS hedgers (belly vega; mortgage demand for low strikes in rallies; peak MBS convexity ~100bp lower in rates),
  callable supply (bottom-right vol; empirical call probabilities ~2.5x lower than raw Bermudan), regulation-driven insurer
  buying (long-dated vol term premium positive even at high vol), VaR-limit pro-cyclicality (limits keyed to trailing realised
  vol expand as shocks roll out -> vol selling returns), dvega/drate hedging in sell-offs (cheapens 30y tails). Check whether a
  flow story is ALREADY priced; trade the second-order leg if the obvious one is (Formosa: 10y expiries priced, 30y vs 10y tails in
  short expiries not) (Citi, 9 Jan 2017). Deep dives: [vol-structured-flows-and-vega-supply](../../vol-structured-flows-and-vega-supply/SKILL.md),
  [flow-mbs-convexity-hedging](../../flow-mbs-convexity-hedging/SKILL.md).
- **Hedge timing** (affects realised, hence the RV you can capture): USD delta-hedged around 9am NY delivered among the lowest
  realised, 12pm-5pm the highest for 2y/10y (editions differ); EUR 7am London lowest for 10y, 2pm lowest in another edition, 8am
  highest; close-to-close realised can be inflated by algo events at the close (Citi, 14 Jan 2019; 9 May 2019; 21 Feb 2023;
  12 Jun 2023). Hedge band: re-hedge every 20-25bp (15-30bp sweet spot) in long-dated trades; with 10y swap bid/offer ~0.3bp daily
  hedging was optimal (2017-18); re-optimise when liquidity changes.

## 3. Case ledger (what happened, including losers)
| Date | Trade / view | Outcome or lesson | Source |
|---|---|---|---|
| Jan 2017 | Buy 10y10y delta-hedged straddles, $100mm at 72.2bp; target $680k, stop $440k; vol-adj roll-down 0.38, z −1.4 | 72.7 -> 66.25 by Dec 2017 = −$640k; cheap + roll-down is not a catalyst | Citi Vol Lab 17 Jan 2017 |
| Jan 2017 | Buy 2y30y vs sell 2y10y (1:0.8 vega); ratio 1.09, z 2.4 | Formosa effect already priced in 10y expiries; second-order leg | Citi Vol Lab 9 Jan 2017 |
| Mar 2018 | Sell 1m10y straddles hedged daily around noon; 1m10y residual 1.7 (z 0.1) "fair to rates"; implied/3m hourly realised 1.07 | Short tails avoided (1m3y +6.2, 1m5y +4.2 rich to rates) because of hawkish regime-shift risk | Citi 12 Mar 2018 |
| Jan 2019 | Short $100mn 3m10y straddles 9am hedge, 15% delta threshold; 66 -> 59 normals, still ~3 rich | Halved to $50mn at 59: scale down when the edge shrinks even if direction is unchanged | Citi 14 Jan 2019 |
| Mar 2019 | Long 3m30y/6m30y straddles at 50nv, ~5 normals cheap on macro-vol | Entered; outcome not reported | Citi 25 Mar 2019 |
| Mar 2020 | Sell USD 2y2y at 55nv; buy 10y10y USD vs EUR (59 vs 57.4) | Vega over gamma at ZLB; callable supply ~$5bn in March | Citi 30 Mar 2020 |
| Jul 2015 | Sell 1m10y / buy 3m10y calendar; avg 10y move 20 Jul-20 Aug ~27bp vs unhedged 1m10y straddle breakeven ~20.4bp | Seasonality gave no reason to short unhedged vol | Citi 17 Jul 2015 |
| 2018 | Scorecard: buy 3Mx10Y 25-delta strangles −20.0; Aug receiver vs Treasury-futures ATM straddles +18.3 | Mixed; P&L in annualised bp of vol | J.P. Morgan IRD 14 Sep 2018 |
| Mar 2020 | USD 3m30y 4 sd rich on macro-vol, 2.7 sd on PCA; USD 5y gamma cheap; EUR 1y10y ~5 sd rich on PCA | Screen outputs are backward-looking and "not necessarily trades we would recommend"; illiquid sectors excluded | Citi 30 Mar 2020 |
| Aug 2026 | Closed costless 3m2y 1x2 payer, $150mm ATMF vs $300mm 27bp OTM | +$430k | Citi US Rates Weekly 21 Aug 2026 |
| Aug 2026 | Long £100mn 3Mx10Y GBP straddles vs short €77.5mn EUR, implied spread ~1.35bp/day, gamma-neutral | Open | J.P. Morgan 21-22 Aug 2026 |
| 2026 (closed) | Short 3Mx1Y GBP straddles (4.55 vs 4.7bp/day entry) | −1.5bp | J.P. Morgan 21-22 Aug 2026 |
| Oct 2026 | Short 6Mx30Y vs vega-neutral long 1Yx30Y, delta-hedged ("soft bearish", sell richest implied/realised) | −1abp; also long 5Yx5Y vs short 5Yx2Y −0.8abp; long 6Mx2Y vs gamma-neutral short 6Mx30Y +11.7; stop on short 3Yx10Y 200bp risk reversal −8.2abp. "A stop is a stop even if still mispriced" | J.P. Morgan IRD 2 Oct 2026 |
| Oct 2026 | USD ratio payer spread 2y30y | Stopped out as rates and vol rose together | Barclays 2 Oct 2026 |
| 2026 closed | Goldman vol trades per unit duration risk: long 3m2y A−25 receiver vs short 3m10y A−25 receiver −2; 3m10y payer ladders −5; 3m3y receiver spreads −7; 6m1y receiver fly −5; short 3m30y straddles delta-hedged −4 | Closed at losses in a rising-vol, rising-rate tape | Goldman Sachs 2 Oct 2026 |
| 2005-2012 | EUR-GBP 5y5y vol spread OU, half-life 15.4d | Fast reversion; hold 1-3 weeks and recycle | Huggins & Schaller 2024 |
| 2013 | 3y10y vol 8% below long-run average after the taper: "Markets do not go from cheap to fair" | Cheap to history is not a timing signal | Bassman, The Economic Hunger Games, 12 Jun 2013 |
| Jun 2012 | JPY: buy 3M5Y vs sell 3M2Y straddles, both hedged; realised 5y-2y spread 6-27bp vs implied 3bp | Never matched in 5 years of history; "would have made ~10bp on average" - history, not a forecast; BoJ anchoring short end | Huggins & Schaller 2024 |

Systematic seasonality caution: gamma outperformed in 4 of the last 5 Mays and 7 of 10 (Citi, 1 May 2017); fits are in-sample.
