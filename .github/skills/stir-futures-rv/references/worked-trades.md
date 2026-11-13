# Worked examples and trade log (cited)

Loaded from [SKILL.md](../SKILL.md). Numbers are as printed in the cited documents; chart reads are marked. They illustrate
sizes, levels and outcomes. They are not current market data.

## A. Strip shape, kinks, microflies

**Spline kink table, ED close 2 Feb 2017** (Citi Research, US Rates Weekly: Going nuclear (on the curve), 3 Feb 2017). Fit: piecewise
monotonic cubic spline through the first 24 contracts, nine nodes (denser in Whites/Reds), fitted to settled prices since 2013.
Signal printed as "+ = contract cheap"; read it as futures rate − fitted forward (a high futures rate is a low price = cheap; the source's wording "fitted − futures" has the opposite algebraic sign). Spread bp by contract (Mar/Jun/Sep/Dec of 2017, 2018, 2019, 2020): 2017 −0.19, 0.78, −1.40, 1.30; 2018 −0.27, −0.34, −0.75, 1.50; 2019 −0.21, −0.79, −0.46, 1.51; 2020 −0.14, −0.13, −1.33, 0.85. 1y z: Dec-18 3.22, Dec-19 2.88, Sep-20 −3.1, Sep-17 −2.7. Decembers
consistently cheap, Septembers rich; Dec-19 widest since 2013. Open-interest driver: regressing the weekly change of the Sep-19/Dec-19/Mar-20 fly's
spread-to-fit on the change in Dec-19 OI vs Sep-19/Mar-20 OI gave R² = 0.37 (weekly 7 Nov 2016-2 Feb 2017): the fly cheapens as Dec-19 OI rises.

**Euribor microfly carry screen** (Clarus Financial Technology, A Dummies Guide to Trading Interest Rate Swaps, 19 Jun 2024). Prices 1st-12th:
96.44, 96.70, 96.94, 97.135, 97.285, 97.39, 97.46, 97.50, 97.525, 97.545, 97.55, 97.56. Source microfly = 2×belly − wings in price bp
(2nd +2.0, 3rd 4.5, 4th 4.5, 5th 4.5, 6th 3.5, 7th 3.0, 8th 1.5, 9th 0.5, 10th 1.5, 11th −0.5), i.e. the negative of the rate-space fly used here.
Long-belly roll (fly rate-space level[i] − level[i−1]): 3rd −2.5, 6th +1.0, 8th +1.5, 9th +1.0, 10th −1.0, 11th +2.0. The source buys the
9th and 11th (11th most attractive) and sells the 3rd and 10th (3rd most attractive); the pure-roll ranking also puts the 8th (+1.5) ahead of the 9th, so
the source evidently also weights level and z-score. Execution: when the Schatz bid/offer is crossed, the Schatz spread can jump a full futures tick
(0.25-0.5bp vs a swap tick of 0.1bp) → post bids in preferred Euribor contracts and leg one contract at a time. "Not an arbitrage" and edge is
eaten by bid/offer: leg in, do not buy the whole fly each time. Sit out central bank and inflation releases.
Same logic on ED (Clarus, Mechanics and Definitions of Carry in Swap Markets, 16 Jan 2019; price-space long-belly values): Sep19-Dec19-Mar20 fly −9bp rolls to the Jun19-Sep19-Dec19 fly +1.5 → buying earns 10.5bp
over 3m; selling Dec19-Mar20-Jun20 at +4.5 earns 13.5bp.

**ING Euribor PC1-neutral fly** (ING Global Markets Research, EUR crisis trades: let's get tactical, 3 Mar 2020; March ECB: taking out the ECB put, 12 Mar 2020).
PC1 residual band method on the generic 1st-20th Euribor contracts (1y lookback in a fast market, limit to 1st-16th); roll-down vs 1y PC1 residual scatter over the 5th-20th has no frontier
(R² 0.0003). Rejected the most tempting 2-9 flattener as too directional. Buy belly of Sep-20/Sep-21/Dec-23 (generic 2-6-15), weights −1.64/+2/−0.51,
entry 3.5bp (incl 0.25bp charge), target −8, stop +10, carry 0, roll +4.2bp/3m; 12 Mar: −3.3, P&L +7.8. Factor screen R²: 2y swap 0.03 (direction-neutral),
iTraxx Senior Financials 0.27, EUR 1y1y normal vol 0.36, S&P P/E 0.65. Sell Euribor Sep-20 vs buy Jun-21 (2nd vs 5th), DV01-weighted: entry −1.25bp, target −8, stop +3,
carry+roll +6.5bp/3m; risk an intermeeting cut. In crisis, "only the simplest trades stand a chance": DV01 weights, simple spreads.

**JPM USD front-end flies and midcurves** (J.P. Morgan, Interest Rate Derivatives: The long and short of it, 3 Aug 2018; Issuance, pensions, and long-end spreads, 14 Sep 2018).
Variance-ratio mean-reversion gauge by pack (3m realised vol from daily changes vs monthly changes ÷ √21): front end, especially Reds, became more mean-reverting as the hiking cycle
neared neutral. Equal-weight Sep-19/Dec-19/Mar-20 ED fly: 6,000 belly at +2.5bp; sold 4,000 Dec-19 at 96.96 vs selling Dec-18 x Reds midcurve puts (96.875, 10bp); took profit at +2.98bp (P&L +1.5bp); exit
rule: take profit on flies once the market can price the policy structure into the contracts.

**Fly fading practice** (Aikin, Welcome to STIR futures, forum posts 2006-2014). Deferred red/green flies may range 2-3 ticks a year. A fly at 1.5 for a week closes at 2.0 while adjacent flies moved: sell it at 2.0-2.5 and buy adjacent flies on the bid. Needs
patience, inventory and rebates. "Fly trading is all about bid/offering."

## B. Packs vs swaps: convexity trades

Structure: buy a pack (equal contracts across 4 quarterlies), pay the matched-maturity CME IMM quarterly swap, hedge the vol with an
ED/SOFR curve position sized by regression of the model CA on curve factors (Citi Research, North America Rates Trade Idea notes, 9 Feb 2017, 6 Jun 2017;
US Rates Vol Lab: Value in Greens convexity, 15 May 2017).
- **Sell Blues CA (9 Feb 2017)**: buy 2000 each of the Mar-20..Dec-20 contracts, pay USD 2bn matched swap at 8.8bp; hedge pay belly of the 2s5s10s swap fly 147mm/−85.6mm/20.89mm
  (0.705/−1/0.465 DV01) at −18.2bp. CA ~4bp (~2σ) wide to model and ~3bp wide to the fly. Target +600k, stop −350k; carry ~+380k/3m; CA roll ~+1.3bp/3m. Closed 6 Jun 2017
  CA 6.6bp, fly −16.5bp: +500k. Regression: Blues CA (bp) = 10.2 + 21.4 × (−0.70·2y + 5y − 0.46·10y) with the fly in % (e.g. −0.182 at entry gives a model CA of ~6.3bp vs 8.8bp traded).
- **Sell Greens CA (15 May 2017)**: buy 1,000 Jun-19..Mar-20 packs, pay USD 1bn Jun-19 to Jun-20 quarterly swap at ~4.5bp; hedge sell 167 Jun-19 contracts at 98.065, buy 141 Jun-18 contracts at 98.41; roll ~0.88bp/3m.
  CA monitor 12 May: CA 4.91bp, vs model +3.43 (3m z 0.82, 1y z 1.48), roll 0.81, CA-implied vol 125.6 vs realised 73.7 (1.7×), cap vol implied/realised 0.9. Greens rerun 6 Jun 2017 at 4.3bp:
  3,000 packs, USD 3bn swap, hedge sell 500 Jun-19/buy 424 Jun-18 contracts; MTM at 3.35bp on 13 Jul +285k (0.95bp × 3,000 × 4 × 25); closed 8 Aug 2017 at 2.65bp for +476k because the dislocation was no longer extreme (Jackson Hole
  risk ahead; Citi Alerts 13 Jul and 8 Aug 2017). Hedge removed (+70.5k) once bearish on gamma.
- **Blues outright (Apr 2018)**: 7.2bp mid, Blues preferred to Golds for liquidity, both ~2σ wide to model; alternate hedge 6th/16th-contract Eurodollar steepener (0.74/−1). That hedge fails at the ZLB: exclude ZLB data (1996-2008, 2017) from vol-vs-rate regressions.
- **Sell SOFR Blues CA (17 Feb 2023)**: buy 1000 packs of the Mar-26..Dec-26 SR3 contracts, pay USD 1.17bn CME fwd swap Mar-26 to Mar-27 at 12.7bp (ATMF 3.14%, 100k DV01); carry +1.5bp/3m; target 4bp tightening, stop 2.5bp widening. Pack table (CA / vs model / 3m roll / CA-implied vol / realised):
  Mar24-Dec24 2.67/0.46/−0.54/155.2/168.1; Dec24-Sep25 6.21/1.48/1.16/158.2/149.9; Mar25-Dec25 8.45/3.28/2.24/166.1/144.8; Mar26-Dec26 (Blues) 13.09/3.65/1.53/147.6/134.9 (model 9.44); Mar27-Dec27 (Golds) 21.24/7.37/1.87 (model 13.87).
  Golds most overvalued but more persistent; Blues already normalising → pick the pack already normalising. Prior leg: sell Blues CA Jun-Dec 2021 7.9→3.4bp, +389k (Citi Research, US Rates Weekly: Time for moderation, 17 Feb 2023; Rates Vol Lab: Short Blues convexity via futures/swaps, 21 Feb 2023).
- **Long SOFR Blues CA vs short EUR 6m1y vol (9 Oct 2026)**: sell 1000 Dec-29..Sep-30 packs, receive USD 1.19bn swap at 5bp spread vs sell EUR 300mm 6m1y straddles (vega −16k); size by realised beta "100k/bp of CA ≈ 16k EUR 6m1y vega"; delta-hedge beyond net 25 delta; target +300k, stop −200k
  (Citi Research, US Rates Weekly: Pension plan for 20s?, 9 Oct 2026).
- **Gamma-based sanity check** (Quantitative Finance Stack Exchange, Why are FRA/futures convexity adjustments necessary?, 27 Jul 2023): receive Jun-25 swap N 1.134bn (25k/bp), hedged short 1,000 contracts; swap gamma 12.2/bp; vol 139.38bp; ½·(140·√2)²·12.2 ≈ 240k = 9.6bp; with gamma decaying linearly (12.2 → ~7.0 after 1y) ≈ 150k ≈ 6bp. Constant gamma overstates CA.
- **Convexity bias disappears with cross-margining** (Aikin, The disappearing convexity bias, 16 Dec 2013): 6th ED minus 6th IMM FRA ranged −0.03 to +0.04% in 2007-10, ±0.01% after 2011; the EUR bias went slightly negative in 2013 (Liffe margin not nettable with SwapClear).
- **Model sizes**: Ho-Lee CA = σ²·T1·T2/2 (BSIC, Understanding Convexity Bias in STIR Futures Markets, 29 Mar 2026: 1st Euribor contract ≈ 0 to 12th ~5-6bp, cap vol 105.86bp). SONIA HW 65bp vol, 3% mean reversion: ~1bp (early 2020), 2 (2021), 3.3 (2022), 5 (2023), 7.3 (early 2024) (Henrard, 2018). SOFR 3m CA ~4-4.5bp for the 2024 contracts, 1m ~0-0.07bp (Rosen, FINCAD, 2019).

## C. SOFR-FF futures basis (SR1 − FF)

Sign trap: futures basis (price space) = (100 − SOFR) − (100 − FF) = −(SOFR − FF). Realised SOFR 10bp above EFFR shows as −10bp in futures; a positive futures basis means SOFR priced below EFFR (easier funding). Analysts use "tighten/widen" inconsistently for it: always state price space or rate space and the direction in funding terms (Conks, Money Market Blindspot II, 12 Feb 2025; Conks, Takeoff Begins, 6 Oct 2025).

- Construction: 1m SOFR future minus 30-day FF future for the same month (SERFF); calendar spread of the basis = difference between months. Jul basis 20bp vs Sep 10bp → rate-space Jul/Sep +10bp; futures basis spread −10bp (market expects tighter funding in July) (Conks, SOFR/FF primer, 10 Jun 2026).
- Path model vs futures (Citi Research, Short-End Notes: SOFR/FF to go negative in Q3/Q4, 13 Jun 2025; SOFR/FF spiking into quarter-end, 27 Jun 2025): regress SOFR/FF on reserves and bills (post-Sep-24) with month-end effects; apply betas to projected bills/reserves; overlay average change in the week around the date. Weekly betas per 100bn: SOFR/FF 2021-25 reserves 0.38 (t 2.3), bills −0.07, bills−reserves −0.32 (t −2.1); the bills-minus-reserves composite is significant, bills alone is not. December futures "too optimistic".
- Regime-weighted projection (BofA Global Research, US repo sensitivity: higher than expected, 8 May 2025): log-linear SOFR−IORB on Liquidity/GDP by regime (weights 30/10/30/30%), break at the ON RRP cut.
- Calendar reading (Conks, Swifter Injections, 4 Dec 2025; The Post-QT Era, 24 Nov 2025): SOFR-FF calendar rising = less tight later; Jan/Mar'26 tightening → earlier reserve-management purchases priced; a negative near-dated calendar spread implies an implausible year-end injection and mean-reverted each time. Failed call: Nov'25 target 8bp.
- 2026: front half "flat as a pancake" ~3bp; back half Sep/Oct/Nov ~4.5, Dec ~5.5bp on a "Warsh fears" premium → narrowing view (Conks, 1 Mar 2026). Realised path (chart reads): May'25 −2.5bp, Sep ~7, Oct ~11, Nov'25 peak ~12, Dec ~6, Jan'26 ~3, Apr'26 ~0.5 (Conks, 4 May 2026).
- Short SOFR/FF basis for August expiry on the debt-limit/bill-flood/RRP-drain chain (Conks, 2 Jun 2025): had "yet to materialize" by 9 Jun. Catalyst timing (X-date, tax dates, reserve-management pace) drives which expiry.
- JPM long May-20 1m SOFR vs May-20 FF (50k/bp each at 0.5bp; −4.0bp by 6 Mar 2020) on dealer net short 1m SOFR futures hedging GC term exposure (J.P. Morgan, 26 Feb, 6 Mar 2020). Don't read every SOFR spike as stress; check GC/tri-party, bills/OIS and short coupons.
- Regression fair value of the secured-unsecured basis (ED era): SR3:ED (bp) = 4.825 + 2.322 × SOFR(%) − 0.394 × 2Y JPY CCBS(bp), R² 0.67; residual OU half-life 2.6-3.7 weeks (Huggins & Schaller, 2022). After 2023 re-run on SR1:FF (cleanest and cheapest instrument for basis exposure) and SR3:FF.

## D. Meeting spreads and curve trades in futures

- **G10 meeting-spread views, Aug 2026 (Citi Markets, STIRT Weekly, 7/14/21 Aug 2026)**: EUR 21bp/84% Sep hike, 36bp to year-end, 41bp/57bp cumulative to end-26/27, prefer to trade from the paid side (pay Nov/Dec in single digits, Sep/Dec ~12bp; "little downside" paying Sep/Nov ~+4.75bp). GBP Sep 28% (3.7bp), Sep/Nov 12.25bp, Dec/Feb 10.45bp; SONIA underperformed on a gas headline (Dec-27 −9.5bp in a day).
  AUD pay Sep/Nov RBA into rallies (+8.0bp); BBSW +8.5-10bp over OIS. JPY Sep 16-20bp, Sep+Oct ~24-28bp cumulative. SEK: receiving Dec-26 into the meeting captured the Sep SWESTR repricing from 50% to <35% hike probability; the desk then preferred paying the Sep/Dec SWESTR spread. NOK ~50% Sep: receive front meetings vs pay later. CAD ~35bp priced to Jan-27, ~93bp to end-27; in-house next move a cut → receive.
- **AUD Dec-26/Sep-27 bank-bill flattener** (Goldman Sachs, Global Rates Trader: Reaching Limits, 2 Oct 2026): entry 13bp, target −5bp, stop 25bp; RBA revealed preference not to delay; ~35bp of hikes priced over a year (least in G10). Trade table inconsistent with text; verify levels.
- **Euribor** (JWS Macro Substack #3, Global Rates Outlook #5/#6, Update #7, Central Casting #6.1, 2026; Barclays Research, Global Rates Weekly: The urgency question, 2 Oct 2026): Dec-26/Dec-27 forward-forward from +12.5bp inverted to −12.5bp (target hit); "CS v P structures across the entire Euribor strip" crowded and stopped; prefer the Sep-26/Sep-27/Sep-28 fly (pay the Sep-27 belly), fair ~50bp, reached 40bp;
  Dec-26 price range 97.10/97.40; Sep-26/Jun-27 spread bounded 0-37bp; Sept meeting gap 12-17bp, July gap 6-12bp ("floor 6 = ~1bp/week theta"); Dec-27/Dec-28 flattener closed −13 → 0 (traded through stop). "You never fade at fair value. You fade a deep ... value."
- **SOFR** (JWS Macro, USD & Global Rates Thoughts #2, 13 Nov 2025; #8, 23 Aug 2026): Dec/Apr/Sep fly (Dec/Apr gap −26, Apr/Sep −30), Jun-27/Dec-28 flattener at ~0 preferred to outright long ("more ways to win"); gap/kink trades are short vol (you sell the tail of a sudden stop). Dec-25/Dec-26 steepener/flattener themes in 2025 (Conks, 2 Jun 2025, 1 Feb 2025): no levels. Dec-26/Dec-27 flatteners crowded by 2026 → vulnerable if the Fed drags its heels.
  Goldman closed a Dec-26/Dec-27 SOFR steepener +6 and a long Sep-26 SONIA +7 per unit of duration risk (2 Oct 2026). Citi (9 Oct 2026): Mar-27/Mar-29 SOFR bear flattener via puts; Dec-26/Dec-27 flattener at −8bp hedged long FF Aug26 (−1.4m; risk: a full 2027 hiking cycle repriced).
- **SONIA** (BofA Global Research, UK Rates Viewpoint: Back to school, 5 Sep 2024): sell Jun-29 vs Jun-26 SONIA (2s5s disinversion) entry −19.5bp, target 10, stop −35; seasonals are a tailwind, not a signal. Citi (14 Aug 2026): SONIA Dec-26/Dec-27 steepest of EUR/UK/US; SONIA 96.70/97.00/97.10/97.30 call condor as a static pin trade.
- **Conditional bull flattener with options** (Nomura, Conditional Euribor bull flatteners, 19 Jun 2014): sell 5000 White calls 99.875 / buy 5000 2y-midcurve Green calls 99.375 for 15.5 ticks net debit (EUR 1.937mn); 3m carry 1.79 ticks, non-linear 1.79/4.4/7.6 over successive 3m blocks; short gamma/theta at inception; see [curve-conditional-trades](../../curve-conditional-trades/SKILL.md).

## E. Futures against swaps, bonds and other futures

- **Strip vs swap**: Aikin (2012): strip zero 2.167% vs swap zero 2.564% → "cheap in rate terms" but 3s6s basis ~0.25% in Nov 2011 negated the profit; futures-implied vs theoretical forwards differed by up to ~0.6% (post-2007 IBOR forwards embed counterparty/term risk). Liquidity crossover: swaps to 3y are better priced off the futures curve than a pure IRS curve (Clarus Financial Technology, CME-LCH Basis: Convexity in Eurodollar Futures, 1 Jul 2015). Futures carry little information past the Reds; use futures at the front and IRS after (Quantitative Finance Stack Exchange, STIR Futures convexity adjustment, Jun 2025).
- **Strip vs Treasury** (Huggins & Schaller, 2022): UST 1.5% 30 Sep 2021 hedged with an SR3 strip from 2 Jan 2020; on 18 Mar 2020 the strip lost 1.96mm vs the note +1.63mm (net −328k, ~20% of the move; the asset-swap spread widened). Buy bond/sell strip at 328,268; returned 315,169 by 31 Mar 2020. CMT − SOFR strip ~+1..+3bp (1Y), +3.5..+7bp (2Y), negative during SOFR spikes. Works only while Treasury ASW vs SOFR is stable. See [spread-swap-spreads-and-asw](../../spread-swap-spreads-and-asw/SKILL.md).
- **Term TED** (Aikin, 2012): bond-future implied yield (CTD price F × CF, yield at delivery date) vs strip yield. 11 Jan 2012: Euribor Mar-12..Dec-13 strip 0.92% vs Schatz Mar-12 110.405 × CF 0.906868 = 100.123, yield 0.18% → TED 0.74%. Pairs: 2y T-note vs ED 2y bundle; Schatz vs Euribor 2y bundle; Bobl vs 5y bundle; bundles replicate best, stacks easiest to execute; avoid the front month; "go to the point of least liquidity first". Term TEDs are essentially credit spreads, like swap spreads. See [fut-invoice-spreads](../../fut-invoice-spreads/SKILL.md).
- **FF vs ED overlap**: FF BPV 41.67; allocate by overlap days: 1,000 Mar-2012 ED (25,000 BPV) vs 600 FF = Mar 67 (10/90), Apr 200 (30/90), May 207, Jun 127 (Aikin, 2012). Backward-looking 3m FF OIS for June covers the same period as forward-looking March ED → trade 1:1.
- **Cross-currency STIR spreads** replicate a forward-starting FX swap without the currency basis: ED − Short Sterling tracked better (76%) than ED − Euribor (37%).

## F. Hedging mechanics checks
- **Tailing** (Tuckman & Serrat, 2022): N_tailed = N/(1 + R0·D/360); USD 10mm for 98 days = 10.89 contracts, tailed 10.84 = 10.89/(1 + 0.65% × 250/360), D = 250 days to the futures' expiry, not the 98-day loan. Splitting a 98-day borrowing 15 Apr-22 Jul: March contract covers 61 days ≈ 7 contracts, June 37 days ≈ 4.
- **Date mismatches dominate hedge error** (Huggins & Schaller, 2022): matched Dec-19 SR3 hedge within USD 413 of target; deposit 2 Dec-28 Feb vs a Dec SR3 over-hedged >100% (futures gain 15,575 vs shortfall 6,743); an SR1 strip hedge left 4.3% error. Close the hedge at the end of the exposure period.
- **Day-overlap proxy** (Clarus, Mechanics of FRA Risks, 4 Sep 2018): a 3m FRA fixing 4 Sep 2018 shares 86% of its days with the Sep18 contract (good hedge); one fixing 25 Sep shares 9% with Dec18 (91% stub) with the FOMC on 26 Sep → trade only a small Dec hedge.
