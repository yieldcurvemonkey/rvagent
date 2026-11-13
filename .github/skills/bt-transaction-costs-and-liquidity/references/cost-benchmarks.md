# Cost benchmarks by instrument and market (sourced priors, not live quotes)

Use these only when no bid/offer data exist, and replace them with dealer quotes or measured spreads as soon as
possible. Every number is dated: costs are regime-dependent (a 2018 swap b/o is not a 2020 one). Read the unit
column before using a number: sources mix one-way (mid to bid/offer), full width, price points, yield bp, ticks and
normal-vol bp. "b/o" = bid/offer. One-way = half the full width.

Conversions used below (price DV01 per 100 face per bp = ModDur x Price / 10000):
- price-point cost to yield bp: `bp = pts / (ModDur x Price / 10000)`. A 1/256 tick on a 10y (ModDur 8, price 100) is
  0.0039 / 0.08 = 0.049bp, consistent with the ~0.04bp floor reported for 7-15y USTs (Alexander Duering, 2021).
- futures: 3M SOFR-type contracts quote 100 minus rate with tick 0.005 = 0.5bp (about 12.5 per tick per 1mm 3M contract,
  25 per bp); listed calendar, fly and condor differentials quote directly in bp, not index points (reading a
  one-tick fly as index points makes it look 50bp wide).

## 1. Swaps (OIS/IRS), rate bp

| Item | Value | Unit and convention | Source |
|---|---|---|---|
| USD 2y/5y/10y swap b/o, history | 1995-H1 1998 1.6; then 2.0; then 1.4; 2000-04 1.2; 2005-07 0.6; 2008-09 1.2; 2010-12 0.7; 2013-16 0.4; 2017-18 0.3; 30y roughly 0.1-0.6 wider | bp as quoted (width convention not stated; the study charges it per trade). Authors call the history "best estimates" | Citi Research, US Rates Vol Lab: The art of gamma hedging, 12 Mar 2018 |
| USD 10y swap, Mar 2020 | about 0.6 mid-to-b/o (with 1m10y at 103 normal vol) | one-way, bp | Citi Research, Rates Vol Lab: Liquidity, vega, and convexity, 30 Mar 2020 |
| USD 5y swap, 2000 | quoted 1.5 wide, executed about 0.75, as tight as 1/5 | full width, bp | Golub and Tilman, Risk Management: Approaches for Fixed Income Markets, 2000 |
| Long-dated USD forward curve packages, initiation | 0.75 for 10y5y/15y15y, 10y10y/15y15y, 10y10y/20y10y, 15y5y/20y10y; 1.0 for 10y10y/20y15y, 10y10y/25y10y, 15y5y/20y15y, 20y5y/25y10y | one-way mid-to-b/o, bp of the package | Citi Research, US Rates Vol Lab: Trading long-dated convexity, 9 May 2019 |
| Same packages, delta-hedge or roll trade | 0.3 (first group), 0.4 (second group) | one-way, bp. Cheaper than initiation because smaller and less dealer risk | Citi, Trading long-dated convexity, 9 May 2019; US Rates Weekly: Deal or no deal, 10 May 2019 |
| Dealer margin template (illustrative defaults) | outrights 2Y 0.4, 5Y 0.5, 10Y 0.5, 30Y 0.6; spreads 2s5s 0.25, 2s10s 0.45, 2s30s 0.85, 5s10s 0.25, 5s30s 0.7, 10s30s 0.55; flies 2s5s10s 0.5, 5s10s30s 0.6 | bp of the DV01 of each hedge instrument. A spread's margin must be strictly below the sum of its component spreads (2s10s < 2s5s + 5s10s) | Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ch.19 |
| Same template applied: receive 100mm 5Y5Y | core 0.78bp of delta (33,405 on the 100mm); with the square-root add-on (alpha 1/1000) 1.08bp (46,252) | bp of delta | Darbyshire, 2022, Ex 19.9 |
| CMT/CMS swaps | 3-4 wide | full width, bp, year 2000 | Golub and Tilman, 2000 |
| GBP 10Y block | typical size 25-50mm; a 200mm request was quoted 1.25bp from mid, then the mid moved about 2bp; later requests from the same client were quoted 1.75bp from mid and did not trade | bp from mid, about 2012 | Darbyshire, 2022, Ex 18.3 |
| SEK 5Y, 50mm, 5 dealers | best aggregate market 0.75 wide | full width, bp | Darbyshire, 2022, Ex 18.2 |
| NOK benchmark IRS | few contributors, wide markets, periods with no trading; infer the price from USD/EUR/GBP moves via correlation, reset when NOK prints | qualitative | Darbyshire, 2022, Ch.19 |
| EUR benchmark IRS | very liquid, many venues, minimal valuation uncertainty | qualitative | Darbyshire, 2022, Ch.19 |

Level labels (Darbyshire): Level 1 directly tradable with observable b/o (exchange-traded, liquid bonds, mandated
IRS); Level 2 derived from Level 1 (bespoke IRS via curves, swaptions); Level 3 hard to price. Cost uncertainty rises
with the level.

## 2. Swaptions and caps, normal vol bp

| Item | Value | Source |
|---|---|---|
| USD swaption b/o in normal vol, 2018 | 1m straddle 1.5 (1m10y 1.0); 1m 25-delta strangle 2 (1m10y 1.25); 3m straddle 1 (3m10y 0.5); 3m 25-delta strangle 1.5 (3m10y 0.75) | Citi, The art of gamma hedging, 12 Mar 2018 |
| History scale | option b/o scaled by a factor running from 2.7x down to 1x over 1994-2018 | same |
| 13Y2Y 5mm receiver | price from mid 1.55bp: 0.7 non-transparency (vol cube needs 1000-2000 parameters, only 10-50 interbank prices exist) + 0.75 minimum increment + hedge cost; stated as 50% wider than the underlying IRS b/o | Darbyshire, 2022 |
| Skew arbitrage | with 0.2 vol-point b/o per leg, unwinding and restarting a gamma-neutral risk reversal daily wipes out the P&L | Quantitative Finance Stack Exchange, Bergomi: Skew arbitrage, 2020-25 |

## 3. Government bonds

| Item | Value | Source |
|---|---|---|
| UST on-the-run CLOB inside spread, 2010-11 (ticks) | 2y 1.03, 3y 1.14, 5y 1.18, 7y 1.33, 10y 1.15, 30y 2.66. The 2y sits at one tick about 97% of the time. Tick sizes differ by tenor | FRBNY Staff Reports No. 381, The Microstructure of a U.S. Treasury ECN: the BrokerTec Platform, 2009 rev. 2017 |
| First-tier depth, $mm bid/ask | 2y 308/300; 3y 77/77; 5y 31/31; 7y 37/36; 10y 26/26; 30y 3/3. First five tiers: 2y 1,561/1,538; 5y 278/275; 10y 213/211; 30y 28/28 | same |
| Permanent impact per $1mm signed volume (256ths) | 2y 0.0055; 3y 0.0166; 5y 0.0276; 7y 0.0780; 10y 0.0658; 30y 0.4476 (so about $363mm moves the 2y one tick and $8.9mm the 30y). Ignoring limit-order flow overstates trade impact by 20-50% | same |
| BrokerTec top-of-book width, running average | about 0.4bp in 2y, 0.2-0.3 in 5y/10y, 0.1-0.2 in 30y (yearly averages 2008-18) | J.P. Morgan, TradeRunner, 16 Aug 2018 |
| 7-15y UST b/o floor | about 0.04bp (1/256 pricing); European bonds price in 1/1000 steps | Duering, Fixed Income Trading and Risk Management, 2021 |
| Off-the-run dealer-to-client effective spread (EBA, full-spread scale), Jan 2018-Jun 2024 | median 0.37bp vs indicative (IBA) median 0.68; 95th percentile 6.22 vs 4.16. Under $50mm: median 0.32, 95th 4.29. Over $50mm: median 0.62, 90th 6.27, 95th 12.41 vs IBA 95th 4.15. Mean 1.51, kurtosis 2188 | Federal Reserve Board, FEDS 2025-049, Trading Costs v. Indicative Liquidity in the Off-the-Run Treasury Market, 7 Jul 2025 |
| Mapping indicative to effective | for a just-off-the-run bond 1bp indicative is about 0.73bp effective; the scale factor rises with the on-the-run benchmark's own illiquidity (a poor on-the-run makes the same indicative spread cost more) | same |
| Off-the-run yield-error premium over on-the-run, bp (2016 / 2014-16 / 2010-16 averages) | 2y olds 1.5/0.8/0.6, double-olds 2.7/1.0/0.9, triple-olds 3.4/1.2/1.1; 5y 0.4/1.2/0.6, 1.7/1.9/1.1, 2.3/2.4/1.5; 10y 2.0/1.6/1.9, 2.6/2.3/2.9, 3.0/2.7/3.5 | J.P. Morgan, U.S. Rates Strategy: Times like these, 10 Feb 2016 |
| Stress | small UST trades cost about 10x normal in March 2020; about two-thirds of 30y interdealer volume filled wider than the minimum increment on 9 Mar 2020 (vs about 50% the prior Friday) while optical depth looked comparable to earlier episodes | Yadav and Younger, Central Clearing the U.S. Treasury Market, Univ. of Chicago Law Review 92, 2025; J.P. Morgan, When market risk meets operational risk, 10 Mar 2020 |
| EGB 10y b/o ranking | tightest NL, then FR; widest IT and ES (BE, AT, FI between). Regression coefficients FR 0.9, NL 0.4, IT 2.1, ES 2.1, BE 2.0, AT 1.8, FI 1.4, units not stated: use for ranking only | J.P. Morgan, European Rates Strategy: Follow the cash flow, 15 Sep 2015 |
| Benchmark premium | persistent on-the-run premium in USTs; little or none in Germany and Japan because price discovery and duration hedging happen in futures and the CTD is the most liquid bond | Duering, 2021 |

## 4. Bond and STIR futures

| Item | Value | Source |
|---|---|---|
| Cost assumed in a duration-timing backtest (monthly rebalance) | UST futures half a 32nd per trade; Bund futures 0.01% of par; gilt and JGB futures 0.02% of par. Convert to bp with the contract DV01 before charging | J.P. Morgan, Investment Strategies No. 74: Simple rules to trade duration, 2 Oct 2012 |
| STIR exchange costs (LIBOR-era, indicative) | exchange GBP 0.25 + clearing 0.03 + commission 0.03-0.25 per lot; liquidity-provider schemes cut deferred-month fees by up to 0.10 / 0.15 / 0.20 per lot; CME non-member Eurodollar fee 1.19 falling to 0.44 per lot with an incentive programme. Multi-leg strategies (flies 4 legs, matrix 8 lots) are viable only with rebates | Aikin, STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed., 2012 |
| STIR curve liquidity | concentrated in the 2nd and 3rd quarterlies, not the expiring front; liquid to about 3-5y; beyond that prices may be largely implied. 3m and 12m calendars are the most liquid; implied prices can vanish | Aikin, 2012; Aikin, Welcome to STIR futures forum posts, 2006-14 |
| Legging a fly vs a listed fly | 4 contracts (+1, -2, +1) x half a 0.5bp tick (0.25bp) = 1.0bp one way, 2.0bp round trip when legged at half-tick markets (illustrative); a listed fly pays its own quoted spread once | arithmetic; legging risk and execution order from Aikin, 2012 |
| Volume is not liquidity | futures volume is inflated by liquidity providers recycling risk; compare with the change in open interest. ADV since Mar 2016: Euribor $509bn, Short Sterling $391bn, EuroSwissy $21bn | Clarus Financial Technology, Mechanics and Definitions of Short Term Interest Rate Futures, 6 Jul 2016 |

## 5. Size and flow references (for capacity and block-size judgement)

| Item | Value | Source |
|---|---|---|
| G4 IRS/OIS/FRA trade size, USD mm, median / 95th | 0-1m 2,544/12,175; 1-3m 903/3,778; 3-6m 500/2,039; 6-12m 254/1,579; 1-2y 167/770; 2-5y 100/416; 5-10y 51/257; 10-30y 30/183; over 30y 32/141. Non-G4 currencies far smaller (2-5y median 22, 5-10y 13). Median DV01 per trade roughly constant at $30-50k | FRBNY Staff Reports No. 557, An Analysis of OTC Interest Rate Derivatives Transactions, 2012 |
| Dealer offset of large trades | about 60% of large-trade DV01 offset within 30 minutes. Offsetting ratio at 30m/1h/4h/8h: USD 0.5/0.5/0.7/0.7; EUR 0.7/0.7/0.6/0.5; GBP 0.6/0.6/0.5/0.5; JPY 0.7/0.6/0.4/0.3. Large trades per day: USD 3.8, EUR 3.2, GBP 0.7, JPY 1.5 | same |
| USD IRS block cap | capped notional about $110k DV01 per trade; RFQ blocks about 2x the cap | Clarus Financial Technology, Identifying Customer Block Trades in the SDR Data, 7 Oct 2015 |
| Swap DV01 by tenor, June 2014 | total USD $1,133m vs EUR $321m; 10y 25.7% USD / 23.6% EUR; 5y 22.9% / 18.4%; 5/10/30y together 62-64%; under 5y only 17-18% (hedging concentrates in 10y, 5s10s, 5s10s30s) | Clarus, The Principals of Swap Trading, 1 Jul 2014 |
| EUR swap intraday | average 15-minute slot EUR 172k DV01; peak 16:00-16:15 CET above 3x average; on ECB-meeting days volume peaks late in the day and the day after (27.1m DV01 over two days vs 10.1m daily average) | Clarus, ECB June Meeting: Were EUR Swaps Traders at Lunch?, 18 Jun 2014 |
| Admin flow in volume | compression was 13.1% of trades and 13.8% of notional in Nov 2014; IMM rolls about 40% of March 5y risk, over 71% in the busiest four sessions | Clarus, Compression in USD Swaps, 8 Dec 2014; The IMM Roll for Swaps, 31 Mar 2015 |
| Electronic share | US governments about 65%, EUR governments about 80% | MIT OpenCourseWare 18.642, Lecture 7: Linear Rates Models, 2024 |
| UST market structure | ADV Treasuries $651.8bn in 4Q21; 65% of trades electronic over Feb 2019-May 2020; interdealer volume Apr-Dec 2019 split 48% principal trading firms / 48% dealers | Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022 |

## 6. Coverage by G10 currency

| Currency | What the sources give | What to do |
|---|---|---|
| USD | most complete: swaps, packages, UST cash, futures, options | use the tables above, time-varying |
| EUR | EGB ranking, Bund futures cost, benchmark IRS very liquid, intraday DV01 map, little benchmark premium | measure from quotes; Bund/Bobl futures are the liquidity proxy |
| GBP | gilt futures cost, 10Y block example, trade-size and offset ratios | measure; expect block-size sensitivity |
| JPY | JGB futures cost, futures-dominated liquidity, offset ratio decays 0.7 to 0.3 over 8h | measure from futures; Tokyo-hours depth thin |
| SEK, NOK | one SEK quote example, qualitative NOK | ask dealers; treat NOK as Level 2-3 |
| CAD, AUD, NZD, CHF | no sourced cost numbers | measure from `bond_quotes`, `fut_quotes`, `stir_quotes` bid/ask, or ask the user for dealer quotes. Never fill from memory |
