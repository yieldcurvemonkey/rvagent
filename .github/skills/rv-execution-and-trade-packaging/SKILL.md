---
name: rv-execution-and-trade-packaging
description: Packages and executes G10 rates relative-value trades. Covers DV01-neutral spread, fly, condor and pascal legs; swap-vs-bond spreadovers and asset swaps; swap-vs-futures and invoice-spread packages; STIR pack, bundle and strip; CCP-basis switches; IMM and futures roll timing; unwinds, compression and re-couponing; venue, protocol and dealer-count choice (RFQ, CLOB, RFS); block sizing; bid/offer and impact by structure; leg risk; and trade-level risk versus NPV. Use when asked how to structure, size, hedge, time, venue or cost a steepener, flattener, 2s10s, 5s30s, butterfly, fly, condor, pascal, spreadover, asset swap or ASW, package, pack, bundle, SR3 or Euribor strip, invoice spread, CME-LCH switch, IMM roll, compression, DV01-matched unwind, partial DV01 hedge, proxy hedge, RFQ vs CLOB vs RFS, block size, bid/offer, leg risk, slippage or execution cost. Not for whether a structure is rich or cheap (curve-, spread-, stir- skills) or for cost and impact modelling (bt-transaction-costs-and-liquidity).
---

# RV execution and trade packaging

Turns an RV view into a tradable package: which legs, the DV01 on each, which instrument pair (swap, future, bond or
cash), which venue and quote type, what it costs, and when to trade. A package must carry the risk you intend and net
out the rest. Its all-in cost (bid/offer, impact, CCP and funding costs, carry) must be smaller than the edge.
Long formulas and worked numbers are in [package economics](references/package-economics.md) and
[venues, execution and timing](references/venues-execution-timing.md), which also holds the G10 differences table.

**Conventions.** DV01 positive = receive fixed = long duration. Spreads are longer minus shorter (2s10s = 10y − 2y);
fly 2s5s10s = 2 x 5y − 2y − 10y. Rates and spreads in bp; notional in $mm; PV01 = $ per bp per $1mm of notional. Some
desk texts flip the sign ("positive PV01 = paid fixed"). Convert before combining sources. Swap-vs-government sign: US
spreadover P = swap rate − Treasury yield; EGB and gilt asset-swap spread = bond yield − swap rate (positive = bond cheap),
so a matched-maturity ASW spread is about −P. State which one a number uses.

## When to use

- Build or size a steepener, flattener, fly, condor, pascal, spreadover, asset swap, swap-vs-futures hedge, invoice
  spread, STIR pack, bundle, strip or fly, UST inter-commodity spread, or CCP switch.
- Choose venue, protocol, quote type (par vs cash NPV), number of dealers, clearing house, or block route.
- Time the trade around an IMM roll, futures notice or roll, FOMC or ECB, data prints, auctions, month- or quarter-end.
- Choose a hedge: total vs partial DV01, proxy hedge, VaR-minimising trade, unwind, compression.
- Estimate all-in cost, bid/offer by structure, leg risk, or slippage against plan.

Not for: CTD choice, delivery options and switch value ([fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md));
finding the trade ([rv-opportunity-scan](../rv-opportunity-scan/SKILL.md)); writing it up
([rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md)); tracking it after the fill ([rv-trade-monitoring](../rv-trade-monitoring/SKILL.md)).

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Needed for |
|---|---|---|---|
| Par or OIS rates by tenor, spot start, one snap; annual tenors from 1Y to the longest leg (gaps are interpolated, and flagged) | `curve_par` | daily, fixed snap | annuity, PV01, par spread |
| Index and fixed-leg conventions (frequency, day count, calendar, cleared or bilateral) | `swap_conventions` | static | leg schedules, PV01 basis |
| Bond clean price, accrued, coupon, maturity; term repo | `bond_quotes`, `bond_static`, `repo_rates` | daily | spreadovers, ASW, carry |
| Futures and STIR prices, multiplier, expiry and delivery dates | `fut_quotes`, `fut_static`, `stir_quotes` | settle or close, never mixed | packs, bundles, strips, futures DV01, roll dates |
| CCP basis by tenor, both CCPs, orientation stated | `ccp_basis` | daily | switch economics, fair band |
| Swap-to-government spreads | `swap_spreads` | daily | spreadover benchmark |
| Auction calendar and results | `auctions` | results visible only after `results_ts_utc` | auction timing, tails |
| Central-bank meeting dates | `cb_meetings` | schedule only | event timing |
| Holiday and settlement calendars | `calendars` | static | roll, value and fixing dates |
| Own and peer fills with slippage | `trades` | per fill | cost calibration, block history |
| Positions and DV01 buckets | `positions` | daily | netting, risk vs NPV |

If an input is missing, ask for it or hand off to the data adapter. Never invent a value. Bid/offer by structure and
venue quote type is the canonical `bid_offer` table ([data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)).
If it is empty, take slippage from `trades` (`slippage_bp`) or ask the user rather than guessing.

## Method

### 1. Name the risk, then pick the package

Write the view as a single risk: outright DV01, slope, belly (fly), curvature, convexity, a basis (CCP, SOFR vs fed
funds, bond vs future), or a swap-vs-bond spread. The package should hedge everything except that risk. After sizing,
list every residual exposure: curve buckets, basis, convexity, roll, financing and fixing dates.

Choose instruments on one index or curve, in liquid tenors, with matched accrual and fixing dates. A non-matched leg is
an untraded basis. A US bond need not match the swap tenor exactly, because on-the-run refunding keeps the benchmark near
the tenor. It is still a relative bet on carry and curve (Clarus, Spreadovers, May 2015). A nearby cheap instrument can be traded instead
of the most liquid one, so the instrument choice can itself be the RV (Düring, 2021).

### 2. Size each leg by DV01

Core identity: DV01_i = N_i x PV01_i, with PV01_i = annuity_i x 1bp per unit notional. In $ per bp per $1mm,
PV01 = annuity x 100.

Receive-direction weights over ascending tenors, sum to zero, scaled so the largest-weight leg carries the target DV01:

| Structure | Scaled weights (ascending tenors) | Trade |
|---|---|---|
| Spread | -1, +1 | receive the longer leg, pay the shorter (a flattener; reverse for a steepener) |
| Fly (50/50 DV01 wings) | -1/2, +1, -1/2 | receive the belly, pay the wings |
| Condor | -1, +1, +1, -1 | receive the middle pair, pay the outer pair (a spread of spreads, Darbyshire) |
| Pascal | +1/3, -1, +1, -1/3 | receive the 6/7/8 fly, pay the 5/6/7 fly |

Notional N_i = w_i x T / PV01_i, where T is the DV01 of the largest-weight leg. The DV01s sum to zero by construction.
Equal notionals are wrong: N_short = N_long x PV01_long / PV01_short. A 10y DV01 is almost double a 5y DV01, so equal
notionals leave duration (Clarus, Spread and Butterfly Packages, Oct 2014).

Two-leg DV01 match for a swap vs bond, or for an unwind: N_other = N_known x u_known / u_other, with u the DV01 or PV01 per
unit of notional. Worked example in Worked examples, item 4. Use each leg's own PV01: a 50/50 fly is not 1:2:1 in notional.
Düring's four-leg "condor" alternates legs (long 2y, short 5y, long 10y, short 30y), which is two spreads and keeps slope risk.
State the weights you mean.

A spot-start 2s10s has its first floating period already fixed, which leaves an outright delta overlay and a common source of
unexplained P&L. Use forward-starting legs and size for the volatility-adjusted delta (Quantitative Finance Stack Exchange, 2s10s
steepener, Mar 2018).

The bundled script (`scripts/package_sizer.py`) derives PV01 from `curve_par` with annual fixed legs and unit accrual.
Production sizing uses the actual annuity: day count, calendar, stubs and payment lags.

### 3. Measure risk at the holding horizon

- Use forward PV01 matched to the holding period. Hedge ratios decay as the leg ages (Düring, 2021).
- Carry is forward-driven. A steepener (pay long, receive short) earns positive carry when the forward curve is flatter than spot,
  that is (forward − spot) is larger at the short leg than at the long leg. A flattener earns it when the forward curve is steeper.
  On a German curve in Sep 2018, the 6m forward minus spot was +4 to +6.5bp, largest in the belly and smallest at 30y, so belly-to-30y
  steepeners carried positively (Düring, 2021). Work out the sign tenor by tenor.
- Carry over three months: a spot 2s10s of 3.82bp against a 3m-forward 2s10s of 7.64bp. Receiving forward 2s10s (receive 10y, pay 2y) earns about
  4bp over three months if the curve is unchanged, with no short-end fixing risk until the start date (Clarus, Mechanics and
  Definitions of Carry in Swap Markets, Jan 2019).

### 4. Hedge ratios and partial DV01s

- Duration is not a hedge ratio. Convert to dollar volatility: HR = (PVBP_target / PVBP_hedge) x beta, with beta the yield
  beta. Worked: 0.08 target vs 0.06 hedge at beta 1 gives HR = 1.3333 (Kopprasch, Understanding Duration and Volatility, 1985).
- Hedge partial DV01s, not total DV01. A total-DV01 hedge leaves curve exposure. Par-swap partials make the hedge matrix
  diagonal, so hedges read as bond equivalents. Forward-rate partials suit futures and forward swaps (Coleman, A Guide to
  Duration, DV01, and Yield Curve Risk Transformations, 2011).
- Transform one set of hedge instruments into another with the Jacobian. It needs equal counts and an invertible square
  matrix (Coleman, 2011). Details are in [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md).

### 5. Choose the instrument pair

| Pair | Use when | Measure | Main leg risk | Cost and carry |
|---|---|---|---|---|
| Swap vs swap (steepener, fly, condor) | curve or fly view, cleared | cash NPV or par; coupons at market | convexity between tenors; 1:2:1 is not factor-neutral | bid/offer per structure; margin |
| Swap vs government bond (spreadover, ASW) | cash-vs-swap relative value | P = S - B in bp | repo specialness, benchmark switch, coupon-frequency mismatch | repo and haircut; bond bid/offer |
| Swap vs futures (SR3, Euribor, bond futures) | fast hedge or relative trade | futures DV01 fixed (SR3 $25/bp per $1mm); swap DV01 moves | convexity, roll, FOMC-date mismatch | exchange margin; futures fee |
| Futures vs cash (basis) | futures-cash basis view | gross and net basis | CTD switch, delivery option (see the fut skill), leg risk | term repo; EFP removes leg risk |
| Invoice spread (swap with effective = futures delivery, maturity = CTD maturity) | swap-vs-UST without cash | invoice spread | date mismatch with delivery or CTD change | swap bid/offer; SDR detection is a floor only |
| CCP switch (pay at one CCP, receive at the other, same swap) | initial-margin relief | CCP basis in bp | basis moves; VM as curves change | basis paid; IM funding |

Key formulas, with sources in the references:
- **Spreadover**: P(0,t) = S(0,t) - B(0,t). Swap coupon = B + P, so swap NPV = 0 at market. Direction is named from the
  bond leg: buy bond and pay fixed = widener; sell bond and receive fixed = tightener (Clarus, Spreadovers, May 2015).
- **Par/par asset swap spread**: s = [(r_fixed - p) A_fixed + (100 - B)/100] / A_float, with B the dirty price per 100 and
  p the market swap rate; r_fixed is the bond coupon (Burgess, Low Latency Interest Rate Markets, slides, undated).
  Worked: swap PV 98.34 against annuity 10.0096 gives Libor spread -32.7bp (J.P. Morgan, European Fixed Income Strategy:
  Asset Swaps, Feb 2006).
- **Swap vs futures hedge**: bump each contract by 1bp, reprice the swap at its original fixed rate, contracts_i = dPV_i / $25.
  Worked item 3 below (CME Group, Pricing and Hedging USD SOFR Swaps with SOFR Futures, Jun 2025).
- **Listed futures** have fixed $25/bp per $1mm DV01, but swap DV01 changes with rates. Receive fixed against short futures
  is long convexity; the swap rate sits below the futures-implied rate by about the option premium (CME Group, Jun 2025).
- **STIR pack, bundle and strip** formulas are in [package economics](references/package-economics.md#3-stir-and-futures-packages).

### 6. Venue, protocol and quote type

| Size and urgency | Route | Reason |
|---|---|---|
| Small, standard tenor, liquid | CLOB, or RFQ to 3 dealers | low leakage; price-time priority |
| Medium, liquid, time-sensitive | RFQ to 3 to 5 dealers | competition vs leakage; response about 90% |
| Above the block threshold (see Method 8) | block route, RFQ to 1 to 3 dealers | cap and leakage; a single dealer may be better for very large size |
| Off-the-run or illiquid bond | RFQ to as many dealers as possible if the order is uninformative; alternate competitive and single-dealer quotes if informative | non-transparent market; signalling |
| Multi-leg package (fly, condor, curve) | one package ticket; never leg a closing spread | leg risk; margin treats the package as one risk |

- **Protocol rule.** Choose voice over electronic iff q x s + (1 - q) x (pi - d) > 0. Here q = P(no dealer responds), s =
  leakage cost on failure, pi = dealer inventory premium and d = dealer markup. Leakage rises with size, so electronic wins
  small tickets and voice wins above a critical size (Hendershott and Madhavan, Click or Call?, Feb 2015). Use the rule to
  rank routes. The study's bp levels are for corporate bonds, not rates.
- **Dealer count.** Default 3 to 5 (index CDS, method only). Riggs et al. (Journal of Financial Economics, 2020) find a response
  rate near 90% with 3 to 5 dealers and near 80% with 6 or more. A standard size lowers RFQ probability by 18.3%. A client
  that queries more dealers faces a growing winner's-curse term, so the cost of extra dealers must be explicit.
- **Quote type.** Standard swaps on a venue quote par or spread over the benchmark; IMM and bespoke swaps quote cash NPV;
  MAC swaps round the coupon to 25bp so CCPs can compress and net them (Burgess, SSRN, May 2022; SEF rulebook, Chapter 9,
  Rule 901, undated). Compare like with like before choosing a venue.
- **Clearing.** Pay at one CCP and receive at the other only when the basis and IM relief beat the cost (see Signals). A
  futures-and-swap package at one CCP is margined on one VaR, so compare the portfolio-margin what-if with the separate totals.
- **Per-currency differences** (USD, EUR, GBP, JPY, AUD, CAD, SEK, NOK, NZD, CHF) that change execution are in
  [venues, execution and timing, section 6](references/venues-execution-timing.md#6-g10-differences-that-change-execution).

### 7. Timing

- **IMM roll.** Roll 3 to 4 sessions before the IMM expiry (3rd Wednesday of Mar, Jun, Sep and Dec). The Friday before expiry
  carried over 21% of IMM risk, and the four busiest sessions carried over 71% (Clarus, The IMM Roll for Swaps, Mar 2015).
  DV01 migrates from swaps to futures at the back and from futures to cash and FRAs at the front. The front stub is hard to hedge.
- **Futures roll and delivery.** Treasury futures: the second business day before the delivery month is the first position
  (intent) day, and the last business day before the month is first notice day. Older texts call the earlier date first notice
  day (Burghardt et al., The Treasury Bond Basis, 2005). Longs roll by the close before the first intent day to avoid early
  delivery. In the Sep/Dec 2026 roll the busiest days were 21 and 24 to 26 Aug (peak 26 Aug) against a 28 Aug first intent day,
  with about half rolled crossing 25 Aug (Citi Markets Futures Sales, Aug 2026). Check the current exchange calendar. The SR3 contract rolls from the second to the
  third listed contract, before its reference quarter starts. Rolling Dec-19 into Mar-20 cost 138bp at the end of the
  reference quarter vs 4bp at the start, an extreme case after a sharp fall in SOFR during the quarter (Huggins and Schaller,
  SOFR Futures and Options, 2022).
- **Scheduled events.** Depth thins and volatility rises around 8:30, 10:00, 13:00, the FOMC statement and 15:00 ET (Fleming,
  Mizrach and Nguyen, FRBNY Staff Report 381, Jul 2009; the FOMC statement was at 14:15 in its sample, check the current time).
  Post-FOMC 60-minute impact was higher for buys (+48 to 118%) and sells (+24 to 134%) in that study. The FOMC full-day price-impact
  slope was 0.83 against 0.58 on all days (J.P. Morgan, Drivers of price impact, Jan 2017).
- **EUR.** Liquidity runs about 08:00 to 19:00 CET, with a lunchtime lull and a 15-minute peak at 16:00 to 16:15 CET. Late
  repositioning came around the June 2014 ECB decision, with EUR 27.1m DV01 over the two day-after sessions against a daily
  average of EUR 10.1m (Clarus, ECB June Meeting, Jun 2014).
- **Fixings.** Date mismatch between the hedge and the exposure is the main hedge error in the STIR examples (Huggins and
  Schaller, 2022). EURIBOR fixes two TARGET business days before the effective date (SEF rulebook, Rule 901).
- **Month- and quarter-end, tax dates.** Repo specialness and funding spikes cluster at turns. Check the financing leg of a
  bond package before the turn (Tuckman and Serrat, Fixed Income Securities, 2022). Calendar and seasonality screens are in
  [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md).
- **Auctions.** Special premia cluster around auction dates. Specialness peaked about 156bp the day before a 10y reopening in
  one worked example (Tuckman and Serrat, 2022). A positive tail (stop above when-issued) signals weak demand. Results are visible
  only after the results timestamp. Supply timing is in [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md).
- **Thin sourcing.** The fixing, month-end and auction rules above rest on single sources and worked examples. Refresh them
  from your own `trades` and `repo_rates` history before relying on the thresholds.

### 8. Execution size, cost and leg risk

- **All-in cost per leg** = half of bid/offer x |DV01| + impact add-on + carry and funding + CCP costs + fees. Use one-way
  half-spreads per leg, not a single round-trip number.
- **Square-root impact.** Add-on for going from x1 to x2 in DV01 = (2/3) x alpha x (|x2|^1.5 - |x1|^1.5). Calibrate alpha on your
  own fills. Worked: alpha = 1/1000 with inventory going from 50,000 to 100,000 gives 13,628 (Darbyshire, Pricing and Trading IRD,
  3rd ed., 2022, Ch.19). The cost script is in [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/scripts/costs.py).
- **Venue split.** Divide a large order across venues in proportion to 1/lambda, where lambda is each venue's relative price
  impact, not equally (O'Hara, Market Microstructure Theory, 1995, sec 8.2).
- **Block thresholds.** House default: treat a trade above the 95th percentile of DV01 for its currency and tenor bucket (2 to 5,
  5 to 10, 10 to 30y; the FRBNY 557 definition of a large trade) as a block, and use the block route, not the CLOB or a
  standard RFQ. The G4 median trade is about $30 to 50k DV01 (Fleming, Jackson, Li, Sarkar and
  Zobel, FRBNY Staff Report 557, Mar 2012). In the SDR data studied, USD IRS notional is capped at about $110k DV01 per trade, and
  RFQ blocks typically run about twice that cap (Clarus, Identifying Customer Block Trades in the SDR Data, Oct 2015).
- **Off-the-run size.** Above $50mn, effective cost is far above indicative spreads: the 95th percentile was 12.4bp against 4.2bp
  indicative (duration-normalised yield bp, Federal Reserve Board, FEDS 2025-049). Budget size-conditional cost.
- **Dealer hedge and offset.** About 60% of large-trade DV01 is offset by dealers within 30 minutes (FRBNY Staff Report 557).
  Expect the dealer's hedge and your market impact to arrive in the first half hour.
- **Inventory.** A second same-direction trade is priced on the post-trade book. Negative add-ons must be floored at zero.
- **Leg risk.** Never leg a closing spread: "the first cut is always the cheapest" (Aikin, STIR Futures, 2012), so the second leg
  carries the cost. When opening a term spread, go to the least liquid point first. Auto-spreaders leg outrights and carry
  order-traffic penalties. Net matrix trades on paper first. Implied prices vanish when you need them.

### 9. Trade-level risk versus NPV

- **Risk, not notional.** Notional overstates risk. A 1y and a 30y with equal notional carry very different rate risk. Use DV01
  by bucket and entity, and balance-sheet terms (Tuckman and Serrat, 2022). Do not net 10y fixed against 6m floating as one DV01.
- **Unwinds.** Three forms (Tuckman and Serrat, 2022): tear-up for NPV (may pay less than fair value); an offsetting off-market
  swap (hard to find a taker); and the most common, an on-market DV01-matched swap. Worked item 4 below. Curve risk and both legs remain.
- **Compression and re-couponing.** Compression cycles net offsetting swaps into fewer swaps of the same risk. Re-couponing
  replaces an off-market swap with a par swap on the same dates. Both cut gross notional and margin. Strip them before reading
  SDR volume as positioning (Düring, Fixed Income Trading and Risk Management, 2021; Clarus, Compression in USD Swaps, Dec 2014).
- **VaR-minimising trade.** c = sqrt(S' Q S), where S is the DV01 strip by bucket and Q the covariance of bp changes. VaR_5% = 1.645c
  and VaR_1% = 2.326c for normal, zero-mean P&L. Single-instrument trade: S_trade(i) = -Q_ii^-1 Q_i S. Trade about half of each
  and re-run. Several full-size trades at once can raise VaR. Multi-instrument trade S_trade = -Q_hh^-1 Q_h S is always at least
  as good, but harder to execute (Darbyshire, 2022, Ch.14).
- **Proxy hedge.** When the direct hedge is illiquid, minimise VaR with a liquid proxy. Worked item 5 below. The residual stays. A
  best single hedge that cuts VaR by only about 15% points to RV or combination risk, not direction.
- **Cross-gamma.** Cross-gamma is symmetric. A hedge of a different product type can hedge first-order risk and leave gamma open.
  Check with grids or scenarios.
- **Balance sheet.** The leverage ratio binds on short-dated, high-notional activity; RWA and market-risk capital bind on long-dated
  IRD. When P&L and spot RWA are equal, prefer the earlier-maturing trade (Darbyshire, 2022, Ch.17).

## Worked examples

1. **50/50 fly sizing.** Belly DV01 50,000, PV01 per $1mm: 3y 274, 5y 482, 10y 903 (bquanttrading, Principal Component Analysis
   Part II, Jun 2015). Receive 103.7mm 5y, pay 91.2mm 3y and 27.7mm 10y. DV01 by leg +50,000 / -25,000 / -25,000.
2. **Pack and bundle (STIR).** Quarterlies at 97.49, 97.31, 97.21 and 97.16 give a pack yield of 2.735%. Adding the next four
   (97.10, 97.00, 96.90, 96.87) gives an annualised 2y bundle of 2.901% (Aikin, STIR Futures, 2012).
3. **Futures hedge of a swap.** A 100mm 2y receive hedged with 779 contracts across the strip. Bump-all dPV of $19,480.69 against
   779 x $25 = $19,475 (CME Group, Jun 2025). Hedge counts decline along the strip; use each contract's own bump.
4. **DV01-matched unwind.** Receive $100mm 25y (DV01 0.196) and pay 30y (DV01 0.225). Notional 100 x 0.196/0.225 = $87.1mm
   (Tuckman and Serrat, 2022). Curve risk and both legs remain.
5. **Proxy hedge.** A book with c = 133,153 hedged with 3M 10Y and 3M 30Y delta cut c to 101,958, about -23% (the source says about 25%). Residual risk stays
   (Darbyshire, 2022, Ch.20 to 22).
6. **CCP switch economics.** $1bn 5y at 1.2bp costs 1.2bp x $1bn x 5 = $600k undiscounted. IM relief $17m per CCP ($34m in total);
   funding saving 0.50% x (1/360) x $34m = $472 a day. Over 5y at 5y DV01 about $460 per $1mm that is 460 x 34 x 50 = $782k, halved to
   $391k because IM decays, plus about $270k default-fund saving (8% of IM at a 10% equity cost). Total about $661k, which the source
   rounds to $670k, against the $600k cost (Khwaja, Hedging the CME-LCH Basis, May 2015). The $600k is undiscounted; at DV01 $460k per
   bp the PV is nearer $550k.
7. **Indirect-client breakeven.** A 5Y at 1.25bp quoted basis needs a full-cost breakeven of 3.932bp, about three times the quote,
   once fees and IM funding are included (Skarecky, Pricing and Arbitraging the CME/LCH Basis, Jun 2015). For this client, do not trade.
8. **IMM roll volume.** 5y USD: $15.999bn traded on the March IMM against $13.25bn on the June IMM. The naive roll (double the smaller)
   gives $26.5bn. Across all tenors, the naive DV01 was $73.5m and the trade-by-trade estimate $39.9m (Clarus, The IMM Roll for Swaps, Mar 2015).
9. **Margin with impact (model inputs, not quotes).** A 100mm 5Y5Y margin rose from 33,405 (0.78bp of delta) to 46,252 (1.08bp) once
   impact was added (Darbyshire, 2022, Ch.19).

## Signals and interpretation

- **Net DV01 after sizing.** Default: residual DV01 of the package at or below 1% of the gross leg DV01. Reason: legs differ in
  convexity, so the package drifts; rebalance after a large move. This is a house default, not from a source.
- **CCP switch.** Trade only if the basis cost is below the PV of the IM funding saved (IM relief x funding rate x DV01 tenor
  factor x about 0.5 for IM decay) plus the default-fund saving, and below the full-cost breakeven for your own fee and funding
  stack. The Khwaja example clears by about $60k; a 1.25bp quote against a 3.9bp breakeven does not.
- **CCP basis band.** The fair band is set by the netting benefit (upper) and the funding cost of IM at both CCPs over about five
  years (lower). The band can be breached for long periods; the basis is not a quick convergence trade (J.P. Morgan, The law of one
  price vs. the law of unintended consequences, May 2016).
- **Block route.** A trade above the 95th percentile of DV01 for its currency and tenor bucket goes to the block route (Method 8).
- **Bid/offer budget.** Budget the half-spread per leg against the expected edge. Use the structure margins in
  [venues, execution and timing, section 3](references/venues-execution-timing.md#3-bidoffer-impact-and-margin-by-structure) as a
  shape check on your own fills, not as market levels. Refresh the historical bid/offer levels before use.
- **Event windows.** Default: no size crossing in the 60 minutes around a central-bank decision unless the trade is for the event
  itself. Reason: post-FOMC impact figures above.
- **RFQ response.** Cost falls as expected responses rise, and an unexpectedly low response is costlier than an expected one; in
  corporate bonds a failed auction followed by voice added 11.6bp (Hendershott and Madhavan, 2015, method only). Use 3 dealers as
  the working floor (the SEF RFQ minimum) and move to voice or a single dealer if fewer are expected.
- **Roll.** If the front contract is inside its reference period and the roll has not been done, the roll cost jumps. Roll before the
  reference quarter starts.

## Pitfalls

- **Sign conventions differ** across desk texts (positive PV01 = paid vs receive). The same fly reads with the opposite sign. State the
  convention once and convert.
- **Notional ratios are not DV01 ratios.** Equal notionals leave duration; use the PV01 ratio, not the notional ratio.
- **CCP basis orientation.** The schema is LCH minus CME. Most sources quote CME minus LCH as positive, and the trade that earns it is
  pay at LCH and receive at CME. In the schema orientation that trade earns when basis_bp is negative. Recompute before comparing.
- **MVA arithmetic.** One source's per-DV01 figures do not reconcile with its own DV01 (282,867 / 225,000 = 1.26bp, not the printed
  1.30bp; the LCH leg 443,678 / 225,000 = 1.97bp, not 2.10bp). Recompute any cost claim from its inputs (Skarecky, CME-LCH Basis For Dummies, Jun 2017).
- **Fixed-ratio ICS leave a tail.** A DV01-neutral fixed-ratio spread leaves a contract tail that grows with size. Recompute ratios from
  current CTD DV01s.
- **The 3+3 : 10 SR1:SR3 ratio is not FOMC-neutral** when meetings sit off-centre. Recompute from days after each meeting.
- **Date mismatch is the main hedge error.** Close the hedge at the end of the exposure, not after it (Huggins and Schaller, 2022).
- **Spreads and flies are directional.** A 1:2:1 fly carries slope and convexity. Check it against PCA or regression weights before
  calling it neutral (see [curve-butterflies](../curve-butterflies/SKILL.md)).
- **Implied prices vanish.** Lean against implieds; do not trade purely implied prices.
- **Capped notional and compression distort size.** SDR block sizes are capped; compression and re-couponing inflate volume. Do not
  read these as market size or positioning without adjustment.
- **Splitting a large order across dealers damages future quotes.** Dealers price in the information leakage from repeat large
  inquiries (Federal Reserve Board, FEDS 2025-049).
- **Winner's curse.** In a multi-dealer RFQ the winner gets the cover price and the others are told "were cover" (Düring, 2021).
- **Specials and financing.** A bond is special when its reverse RP is below GC; a short that fails to deliver pays the coupon and
  earns no RP, and specials have no floor. Overnight financing is
  cheaper on a positive curve but exposes the basis to slope.
- **Benchmark switches** make US swap-spread history jump. Use constant-maturity or spline yields for bond history (Düring, 2021).
- **Full-size VaR-minimising trades** can raise VaR. Trade a fraction and re-run.
- **Expect the dealer hedge.** About 60% of large DV01 is offset within 30 minutes. A late order in the same direction is priced on the
  post-trade book.

## Output

Return one package ticket per trade, with these fields:

- **Package**: structure, direction (receive or pay), curve or index, snap and trade date, the named risk (view), and the convention used.
- **Legs**: one row per leg with `instrument_id`, tenor or start, direction, signed notional ($mm), PV01 per $1mm, signed DV01 ($/bp),
  rate or price, quote type (par or cash NPV), clearing (CCP or bilateral), venue and protocol, number of dealers, and fixing or delivery dates.
- **Risk**: total DV01 (about zero for a DV01-neutral package), partial DV01s, forward DV01 at the holding horizon, and the list of
  residual exposures (curve, basis, convexity, roll, financing, fixing). For a hedge, VaR before and after.
- **Cost**: half-spread x |DV01| per leg, impact add-on, IM and funding cost, carry, and the breakeven edge against total cost.
- **Timing**: execution window, excluded events, roll or expiry dates, first notice or last trading day, and auction dates inside the holding period.
- **Execution plan**: protocol, dealer count, slice sizes, leg order, and an abort rule.
- **Hand-offs**: the view to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), the monitoring triggers to
  [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md), and the size to [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md).
- **Data gaps**: each missing input, named by canonical table. Never fill a gap with an invented value.

## Scripts

- [`scripts/package_sizer.py`](scripts/package_sizer.py): DV01-neutral legs for spread, fly, condor and pascal from PV01s; PV01 from a
  `curve_par` CSV or Parquet (annual bootstrap, linear interpolation of any missing annual years, flagged); STIR pack and bundle yields;
  DV01-match notional; CCP switch cost and breakeven. `python -I scripts/package_sizer.py --help`.
  `python -I scripts/package_sizer.py --selftest` checks known answers: a flat-curve annuity, interpolation on a linear curve, the
  condor and pascal leg signs, the cited pack 2.735% and bundle 2.901%, 1.2bp x $1bn x 5y = $600k, and the 87.1mm DV01 match.

For fly weights and PCA-neutral fly sizing, use [curve-butterflies](../curve-butterflies/scripts/fly_weights.py). For
partial-DV01 transforms and CoVaR, use [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/scripts/risk_transform.py).
For the impact add-on and cost by holding period, use [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/scripts/costs.py).

## Related skills

- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD switch, wildcard and end-of-month options; the delivery side this skill defers to.
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): invoice-spread valuation and CTD hedging.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): gross and net basis, implied repo, basis trade funding.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): calendar roll fair value and roll dynamics.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CCP basis as a signal and its fair-value band.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): spreadover, asset-swap and swap-spread valuation.
- [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md): basis swaps and index mismatch that a DV01 match does not hedge.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): cross-market government spreads and FX-hedged carry.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR spreads, flies, packs and bundles as signals.
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures vs FRA and OIS convexity before comparing forwards.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounded RFR settlement and fixing-risk ladders.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): repo specialness, quarter-end and funding turns.
- [curve-butterflies](../curve-butterflies/SKILL.md): fly weights, directionality and residuals.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): DV01 vs beta-weighted steepeners and regime behaviour.
- [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option-based conditional steepeners and flatteners.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-start packages and forward-space risk.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): partial DV01s, key-rate risk and risk transforms.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry and roll for swaps, bonds and futures.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): leverage, RWA and capital costs in package pricing.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA discounting and margin effects on swap fair value.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): bid/offer, impact and liquidity regimes used in cost estimates.
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): SDR fields, package detection and dealer direction.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): month-end, quarter-end and auction calendar effects.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auction timing, tails and issuance calendars.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): regression hedge ratios and their stability.
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): where the candidate trades come from.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): the note that carries the package ticket.
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): tracking the position and its triggers after the fill.
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): adversarial review of execution and crowding risk.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): how large the package should be.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): the canonical tables this skill reads.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-currency swap, bond and futures conventions.

## References

- Clarus Financial Technology blog, Mechanics and Definitions of Spread and Butterfly Swap Packages (Chris Barnes, 14 Oct 2014): steepener and fly price, DV01 sizing, coupon and direction conventions.
- Clarus Financial Technology blog, Mechanics and Definitions of Spreadovers (Swap Spreads) (Chris Barnes, 11 May 2015): spreadover price, DV01 match, widener and tightener, volumes.
- Clarus Financial Technology blog, Mechanics of Asset Swaps and Government Bond Swap Spreads (Chris Barnes, 18 May 2015): matched-maturity ASW, synthetic FRN, optical spreads, gilt reopenings.
- Clarus Financial Technology blog, The IMM Roll for Swaps (Chris Barnes, 31 Mar 2015): IMM roll timing, roll volume methods.
- Clarus Financial Technology blog, Mechanics and Definitions of Carry in Swap Markets (Chris Barnes, 16 Jan 2019): carry and the forward-starting measure.
- Clarus Financial Technology blog, Identifying Customer Block Trades in the SDR Data (Chris Barnes, 7 Oct 2015): capped notional and block rules.
- Clarus Financial Technology blog, ECB June Meeting: Were EUR Swaps Traders at Lunch? (Chris Barnes, 18 Jun 2014): EUR intraday DV01 profile and ECB repositioning.
- Clarus Financial Technology blog, CME-LCH Basis For Dummies (Tod Skarecky, 28 Jun 2017): MVA as funding cost of incremental IM.
- Clarus Financial Technology blog, Pricing and Arbitraging the CME/LCH Basis (Tod Skarecky, 22 Jun 2015): cost stack, breakeven basis, IM funding.
- Clarus Financial Technology blog, Hedging the CME-LCH Basis (Amir Khwaja, 26 May 2015): switch economics and hedge of a switch.
- Clarus Financial Technology blog, What's the Deal with Invoice Spreads and How Active Are They? (Tod Skarecky, 17 Sep 2014): invoice-spread forms and detection.
- CME Group, Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (Mark Rogerson, 4 Jun 2025): futures DV01 hedge, convexity, strip to IMM swap rate.
- CME Group, Short-Term Interest Rate futures inter-commodity spreads on Globex (Apr 2024) and U.S. Treasury Futures Inter-Commodity Spreads (Feb 2024): DV01 weights, ICS definitions and margin offsets.
- Burghardt, Belton, Lane and Papa, The Treasury Bond Basis: An In-Depth Analysis for Hedgers, Speculators and Arbitrageurs (3rd ed., McGraw-Hill, 2005): gross basis, carry, first notice day, delivery options, specials, EFP.
- Huggins and Schaller, SOFR Futures and Options: A Practitioner's Guide (Wiley Finance, 2022): SR3 and SR1 settlement, roll rules, FOMC-neutral ICS, date-mismatch hedge error.
- Darbyshire, Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch and Dee, 2022): package terminology, PV01 and margin model, VaR and proxy hedges, issuance swaps, RWA and benchmark profit.
- Düring, Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 2021): spread and fly packages, compression, re-couponing, winner's curse, liquidity hierarchy, benchmark switches.
- Tuckman and Serrat, Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): DV01-matched unwinds, futures tailing and LTD, repo haircuts, specialness, notional vs risk.
- Aikin, STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): implied pricing, packs, bundles, matrix additivity, execution rules.
- Kopprasch, Understanding Duration and Volatility (Salomon Brothers, Sep 1985): dollar-volatility hedge ratios.
- Fleming, Mizrach and Nguyen, The Microstructure of a U.S. Treasury ECN: The BrokerTec Platform (Federal Reserve Bank of New York Staff Report 381, Jul 2009, rev. Mar 2017): book mechanics, workups, impact and its overstatement, event timing.
- Fleming, Jackson, Li, Sarkar and Zobel, An Analysis of OTC Interest Rate Derivatives Transactions (Federal Reserve Bank of New York Staff Report 557, Mar 2012, rev. Oct 2012): block thresholds, DV01 offset ratios.
- Riggs, Onur, Reiffen and Zhu, Swap trading after Dodd-Frank: Evidence from index CDS (Journal of Financial Economics, 2020): RFQ protocol, dealer counts, response rates, winner's curse (method only).
- Hendershott and Madhavan, Click or Call? Auction versus Search in the Over-the-Counter Market (Journal of Finance, Feb 2015): venue-choice framework (method only; corporate bonds).
- Benos, Payne and Vasios, Centralized trading, transparency and interest rate swap market liquidity (Bank of England Staff Working Paper 580, Jul 2016): SEF protocols and RFQ minimums.
- J.P. Morgan (Younger, Sarkar and Salem), Drivers of price impact and the role of hidden liquidity (Jan 2017): square-root impact, FOMC slope, icebergs.
- J.P. Morgan (Younger, Iglesias and Sarkar), The law of one price vs. the law of unintended consequences (May 2016): CCP-basis fair band and IM netting.
- J.P. Morgan (Salford), European Fixed Income Strategy: Asset Swaps (Feb 2006): par/par asset-swap worked example.
- O'Hara, Market Microstructure Theory (Blackwell, 1995): venue splitting by relative impact, block and syndication mechanics.
- Burgess, Electronic Rates Markets and Low Latency Interest Rate Swap Calculations (SSRN, May 2022), and the companion slide deck Low Latency Interest Rate Markets (undated): quote types by venue, MAC swaps, bid/offer, swap PV01 and par/par asset swaps.
- Federal Reserve Board, Finance and Economics Discussion Series 2025-049, Trading Costs v. Indicative Liquidity in the Off-the-Run Treasury Market (Sokolinskiy, Jul 2025): execution cost metric and the cost of splitting large orders.
- Coleman, A Guide to Duration, DV01, and Yield Curve Risk Transformations (Close Mountain Advisors, 20 May 2011): partial DV01s, par-swap versus forward-rate partials, Jacobian transforms.
- Clarus Financial Technology blog, Compression in USD Swaps (Chris Barnes, 8 Dec 2014): compression identification and why to strip it from liquidity measures.
- Clarus Financial Technology blog, A Dummies Guide to Trading Interest Rate Swaps (Chris Barnes, 19 Jun 2024): microfly carry screen.
- CurveTrades LLC, Yield Curve Spread Trades: Opportunities and Applications (Andrew P. Shook, Jun 2013): UST inter-commodity spread ratios and the fixed-ratio tail.
- Citi Markets (Futures Sales), CBT Treasury Futures Sep/Dec Roll: 10 trading days until FND (Glenn Compton, 14 Aug 2026): roll calendar and first intent day.
- Quantitative Finance Stack Exchange, Different ways to express a 2s10s steepener? (asked Mar 2018): forward-start fix for the spot-start first-fixing delta.
- bquanttrading (asmquantmacro blog), Principal Component Analysis Part II (Jun 2015, updated Jan 2016): PCA-weighted fly and PV01 per $1mm by tenor.
- Tradeweb (DW SEF), SEF Rulebook Chapter 9: Swaps, Rule 901 Swap Specifications (undated): swap specifications, day counts, fixing and settlement rules.
- tpSEF Inc., Rulebook Appendix B: Swap Specifications (8 May 2021; LIBOR-era tables): minimum sizes and increments, FRA discounting.
