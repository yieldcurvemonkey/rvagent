# CCP basis: additional worked examples

Cases from the cited documents; arithmetic restated so it can be reproduced. Illustrative, historical.

## A. Switch for IM only (small basis, June 2014)
(Clarus, LCH-CME Switch Trades and Margin Management, 30 Jun 2014)
- Dealer IM: CME $103mn, LCH $202mn. DV01 signs below are the source's (negative = net receiver, positive = net payer;
  opposite of this repo's receive-positive convention). LCH IM is driven by the six largest historical loss scenarios; the worst was 13 Nov 2008 at
  -$204mn. The 10Y bucket contributed $127mn at LCH (10Y DV01 1,700,000, a 63bp 10Y drop in that scenario) and $25mn at CME (DV01 -624,000).
- Switch $285mn 10Y (DV01 250k): pay at CME (-624k to -374k), receive at LCH (1.70mn to 1.45mn); net 10Y DV01 unchanged at 1,076,000.
  IM falls $38mn at LCH and $10mn at CME: $48mn, 16% of $305mn. Capacity remains for a further $425mn notional (374k DV01).
- Market structure then: standard 10Y size $50mn, block $170mn; $2.5bn 18M and $3bn 5Y switches in one week; a venue
  launched a weekly position-switch auction.
- Lesson: with a basis below 0.1bp the cost is negligible, so the decision is pure IM optimisation. Compute IM by scenario (which bucket drives the
  VaR-style IM) before choosing the tenor to switch.

## B. Split book, basis risk and switch (May 2015)
(Clarus, Hedging the CME-LCH Basis, 26 May 2015)
- DV01 signs in this example are the source's (negative = net receiver), opposite of this repo's receive-positive convention.
- Split book: CME IM $218m + LCH IM $262m = $480m gross vs probably $5-10m if all at one CCP.
- Parallel +1bp: CME -$5.8m, LCH +$5.8m, net -$20k. But the basis moves too: with CME 5Y DV01 -$1m and 5Y basis +1.2bp the
  5Y bucket loses $1m on that widening; across tenors $7.5m.
- Switch $1bn 5Y: receive LCH 1.65642 / pay CME 1.66842 (1.2bp; the article says about $600k ignoring bid/offer, but 1.2bp x
  the $450k DV01 moved is about $540k). LCH 5Y DV01 falls $450k; after the
  switch CME -$560k vs LCH $695k, so the 5Y basis risk roughly halves.
- Benefit: IM down $17m at each CCP ($34m). Funding at 50bp overnight: 0.50% x 1/360 x $34m = $472/day. Capitalised over the 5y
  annuity (about 4.6): $34m x 0.5% x 4.6 = $782k, halved for IM amortisation = $391k. Default fund: 8% of IM at 10% equity cost
  = $34m x 0.08 x 0.10 = $272k. Total about $670k as reported (391 + 272 = 663; the default-fund term is an annual cost booked once) vs cost about $0.55-0.6m. Marginal: do it if you also value the reduced basis risk.
- Dealer paying the basis outright in 30Y: pay CME 2.76734, receive LCH 2.74584 = 2.15bp (basis plus bid/offer) for life, about
  $100k on $25m or $1m on $250m (Clarus, CME-LCH Basis Spread, 20 May 2015). It showed as a PV loss until CME marked on its own observations.

## C. Client basis "arbitrage" cost stack (June 2015)
(Clarus, Pricing and Arbitraging the CME/LCH Basis, 22 Jun 2015)
- $100mm 5Y, pay LCH 1.86111%, receive CME 1.87361%: 1.25bp = $12,500/yr, $62,500 undiscounted over 5y (PV $60,447; $62,480 after 2 x $10 execution fees).
- DCO standard plan: booking CME $450 / LCH $405; maintenance CME $200 / LCH $300 per year. FCM: $1,000 booking per side, 10bp of
  IM maintenance (the author says 50bp is more realistic). Yearly cash flows net of fees: 5,411 / 8,615 / 9,413 / 10,291 / 11,312
  = $45,042, i.e. the $62,480 income less about $17.4k of fees (the article: "my $62,480 gain is now down to just over $45,000").
- Projected house IM (CME + LCH, $): day 1 3.87mm, then each year 3.43mm, 2.68mm, 1.76mm, 0.77mm, about 0.
- IM funded in 1y forward increments at 50/130/200/245/280bp costs about 19k / 45k / 53k / 43k / 21k = $181.6k over 5y.
- Breakeven basis **3.93bp**, about 3x the 1.25bp quote (undiscounted check: (181.6k + 17.4k) / $50k per bp = 3.98bp). The author calls his inputs aggressive (10bp FCM fee, client IM about 10% higher than house IM, mid execution, no minimums, VM ignored, zero tax, annual steps), so real breakeven is higher.
- Use the same structure with `breakeven_bp(notional, im_by_year, fund_spread_by_year, fees_by_year)`.

## D. EUR market-maker choice with a minority CCP (Eurex minus LCH 2bp)
(Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022, Ex 18.1)
- 10Y EUR IRS: LCH mid 1.00%, Eurex 1.02%. Delta Bank clears only at Eurex; Alpha, Bravo, Charlie clear at both. An uncleared
  client (RFR CSA) asks all four.
- If Delta prices off its Eurex curve it quotes 1.01 / 1.03% vs the others' 0.99 / 1.01% (LCH); Delta is always the highest bid, so
  it only ever pays fixed to clients and receives fixed at Eurex on hedges (pays 1.01, receives 1.02: positive carry) but builds a
  growing one-way Eurex position with rising margin and capital cost.
- If Delta prices off the LCH curve it gets about 25% hit likelihood and two-way flow; its Eurex exposure nets. Rule: align
  with the collective (LCH) curve unless the CCP-specific cost is understood and priced.
- Limits: tiny sample of one example; real market-makers also set margin and fee charges per trade (Darbyshire, section 18.2.3).

## E. Sell CME-based convexity adjustment (May 2017)
(JPM, A better way to sell vol: CME-based convexity adjustments are rich, 3 May 2017)
- Implied funding spread = excess CA / IM. LCH about 150-290bp/yr across Z7-Z9; CME rising to about 1,000bp/yr at M9 (peaking at early Greens), vs typical funding spread about 100bp.
  CME-based excess CA trades at about 80% of LCH-based (about 30% at Z7, about 85% at Z8/H9) though CME IM is 70-80% lower.
- Conclusion: CAs rich and CME/LCH basis too narrow. Trade: buy H9 and M9 Eurodollars vs pay CME-cleared FRAs (PVBP-weighted),
  front end chosen because the futures expire within about 2 years, so the mispricing can be realised.
- Profitable only if your actual collateral funding cost is below the implied funding spread. No CME margin estimates beyond Z9 FRAs.

## F. CA trades executed on CME-cleared swaps (venue choice examples)
(Citi, Sell Blues convexity adjustments, hedged, 9 Feb 2017; Rates Vol Lab 8 Jan 2018; Rates Vol Lab 21 Feb 2023)
- 9 Feb 2017: sell $200k DV01 Blues CA: buy 2,000 each H0-Z0, pay $2bn matched-maturity CME-cleared swap at 8.8bp; closed at 6.6bp (9 Feb to 6 Jun 2017), +$552k as reported (2.2bp x $200k DV01 = $440k, so the reported P&L includes something else or a different size; treat as unverified).
- 8 Jan 2018: sell $100k DV01: buy 1,000 H1-Z1 packs, pay $1bn CME-cleared swap at 6.5bp; CME chosen because the basis had "well
  retraced from its recent highs in December" and for netting.
- 21 Feb 2023: sell Blues CA: buy 1,000 Mar-26 to Dec-26 3M SOFR futures, pay $1.17bn CME-cleared swap at 12.7bp (ATMF 3.14%, $100k DV01).
- Takeaway: state and log the CCP of the swap leg with the trade.

## G. Detecting switch trades in trade data (March 2016)
(Clarus, Identifying CCP Basis Trades in the SDR, 30 Mar 2016)
- Sample: 851 spot-starting cleared USD 5y outrights and 1,282 10y trades in March 2016. Expected 10-20 basis trades in 5y and 10-15 in 10y.
- Pairs by timestamp alone: 24 in 5y and 20 in 10y. With venue-report cross-reference: 12 and 10. False positives equal true positives
  unless the basis price is used as a filter, which fails when the basis is tiny.
- A third CCP can be ruled out by volume (Eurex USD IRS $187m month-to-date, every day under $100m, while candidate pairs were $100m to $240m+).
- Venue-reported CCP-basis volume Dec 2015 to Mar 2016 was roughly 50k, 52k, 57k then about 23k in March (chart, no units).
- 5y basis package prices in March 2016: peak around 0.95bp (as expected), a "disappointingly large" cluster around 0.25bp, and a +1.7bp outlier;
  sample too small for a standard deviation to mean much.
- Counting rule (Clarus, CME-LCH Basis Spread, 20 May 2015): a $1bn switch between two dealers is $1bn single-counted, 2 trades at CME + 2 at LCH = $2bn across CCPs,
  $4bn across CCPs and accounts.

## H. Discounting / PAI switch (October 2020)
(CME Group, SOFR Discounting Transition Process for Cleared Swaps, 2 Jun 2020; Citi US Rates Weekly, 2 Aug 2019)
- CME moved discounting and price-alignment interest from EFFR to SOFR at COB 16 Oct 2020; LCH targeted about 17 Oct.
- Value transfer was compensated in cash plus mandatory at-the-money EFFR/SOFR basis swaps, bucketed by DV01 (2/5/10/15/20/30Y), booked at $0 NPV with no IM or VM,
  restoring the original discounting risk; they could be unwound in an optional Dutch-style auction. LCH let clients opt for cash-only and
  auctioned the unwanted basis risk, creating liquidity and imbalance risk in long-dated FF/SOFR basis.
- Lesson: a mandated one-directional re-hedge is a predictable flow; after the switch, broker spreadover screens quote a different instrument (Clarus, Spreadovers vs SOFR, 23 Sep 2020).
