# Package economics: formulas, conventions and worked numbers

Companion to [SKILL.md](../SKILL.md). Conventions: DV01 positive = receive fixed; spreads = longer minus shorter;
rates in %, spreads and basis in bp; notional in $mm unless stated. Citations are in SKILL.md References.

## 1. Swap curve packages (spreads, flies, condors, pascals)

- Steepener price: S(t2) - S(t1), t2 > t1, quoted long minus short (Clarus, Spread and Butterfly Packages, Oct 2014).
  Fly price: 2 S(t2) - S(t1) - S(t3). Wings one way, belly the other, with equal and opposite risk.
- At-market coupons: set the package so NPV = 0 at inception. Steepener: S(t1) = S(t2) - P(t1,t2), where P is the
  forward-start price of the package. Fly: S(t1) = 2 S(t2) - S(t3) - P(t1,t2,t3) (Clarus, Oct 2014).
- Direction is fixed on the longest leg (spread) or the belly (fly). "Paying" a steepener = pay fixed on the long
  leg, receive on the short. A 5s10s held past 5y is an outright 5y swap.
- Equal notionals leave duration: a 10y DV01 is almost double a 5y DV01 (Clarus, Oct 2014). Use DV01-based notionals.
- A 1:2:1 fly is a convexity and slope trade, not pure curvature. Check the wing weights against PCA or regression
  weights before calling it neutral (see curve-butterflies).
- Keep all legs on one index. A spread across indices (OIS vs IBOR, or SOFR vs EFFR) carries basis that the DV01 match
  does not hedge (see spread-tenor-and-index-basis).

**Tenor-matched sizing examples (illustrative PV01 per $1mm: 3y 274, 5y 482, 10y 903; bquanttrading, PCA Part II,
Jun 2015):** a 50/50 fly with belly DV01 50,000 receives 103.7mm 5y, pays 91.2mm 3y and 27.7mm 10y. The wings each
carry 25,000 of DV01, so the sum is zero.

## 2. Spreadovers and asset swaps (swap vs government bond)

- Spreadover: P(0,t) = S(0,t) - B(0,t), where S is the swap rate and B the government yield, both in bp. Usually
  positive (credit premium), can be negative (Clarus, Spreadovers, May 2015). Asset-swap spreads for EGBs and gilts use the
  opposite sign (bond yield minus swap rate, positive = bond cheap), so a matched-maturity ASW spread is about -P.
- DV01 match: 0 = D_S(0,t) - D_B(0,t). Agree the bond notional and solve the swap notional, or the reverse. Convexity
  differs, so rebalance after large moves.
- Swap coupon = B + P, so the swap NPV is zero when the spread trades at market.
- Direction is always named from the bond leg. Buy bond and pay fixed = widener. Sell bond and receive fixed =
  tightener (Clarus, Spreadovers, May 2015; Clarus, Asset Swaps, May 2015).
- US swap spreads jump when a new benchmark is issued, by roughly the yield difference between the old and new
  benchmark, and different tenors switch on different dates (Düring, Fixed Income Trading and Risk Management, 2021).
  Use constant-maturity or spline yields for bond history.
- Matched-maturity asset swap: identical settlement, maturity, payment frequency and day count on both legs. A
  reopened "5y" gilt with 4.5y left splits liquidity and creates curve risk on a steep curve (Clarus, Asset Swaps,
  May 2015).
- Par/par asset swap spread (Burgess, Low Latency Interest Rate Markets, undated slide deck):
  s = [(r_fixed - p) A_fixed + (100 - B)/100] / A_float, with r_fixed the bond coupon, B the dirty price per 100 and p the market swap rate.
  Rule of thumb: s ~ (r - p) - (B - 100)/T, where (B - 100) is in points and T in years. The result is a percent
  spread, multiply by 100 for bp. Example from the source: r - p = 6bp and a premium of 4.58 points over 10y gives
  6 - 45.8 = -40bp.
- Worked par/par (J.P. Morgan, European Fixed Income: Asset Swaps, Feb 2006): swap PV 98.34 against annuity 10.0096.
  x = (98.34 - 100)/10.0096 = -0.166 (%). Libor spread = x * 2 * 360/365 = -0.327%, i.e. -32.7bp.
- Yield-yield vs par/par: a yield-yield swap is delta-neutral by construction and its notional differs from face;
  par/par pays the coupon and is not delta-neutral. The choice changes the hedge (Darbyshire, 3rd ed., 2022, Ch.4).
- Issuance swap adjustments: a bp on one leg is not a bp on the other. The source example (7y, T+5) lands at
  RFR + 38.1bp = 37.5 standard + 0.3 convention - 0.2 make-to-par + 0.5 dealer margin (Darbyshire, 3rd ed., 2022, Ex 4.2).
- Splines ignore specialness. A spread to a spline is relative to a hedge, not an absolute value. The interpolated
  swap spread is a weak measure of relative value between two bonds; par ASW is better when the curves are close.
- EUR coupon-frequency trap: EUR swaps pay annual fixed and match EGBs, except BTPs (semi-annual). A BTP-vs-swap par
  spread on annual fixed is misleading (Düring, 2021).
- Box trades: a swap receive 5s10s hedged by buy 5y and sell 10y Treasuries is "buy 5y spread" in some desks and
  "sell 10y spread" in others. Always state each leg: which swap tenor pays or receives, which bond is bought or sold.

## 3. STIR and futures packages

**SR3 and SR1 mechanics (Huggins and Schaller, SOFR Futures and Options, 2022):**
- SR3 settles on compounded SOFR over the reference quarter: R = [prod_i (1 + SOFR_i d_i/360) - 1] x (360/D) x 100,
  price = 100 - R, with D = sum of d_i, the calendar days each fixing applies (a Friday covers 3 days).
- SR1 = arithmetic average of SOFR over the calendar days of the delivery month.
- Strip (annualised), with a front stub R_unknown and forward periods j:
  S = (1 + R_unknown D_unknown/360) x prod_j (1 + R_j D_j/360). Annualise by solving
  S = (1 + S_ann x 365/360)^N x (1 + S_ann x F/360).
- Roll SR3 from the second to the third listed contract, before its reference quarter begins. Do not roll front to back.
  Worked cost: rolling Dec-19 into Mar-20 cost 138bp at the end of the reference quarter vs 4bp at its start. The source calls it a
  relatively extreme case (a sharp fall in SOFR during the quarter), but rolling early was better in almost every past case.
- DV01 per contract: SR3 and 3M ESTR 25 (contract currency) per bp (about 1mm notional); SR1, 1M SOFR and fed funds $41.67/bp (about $5mm
  notional). Hedge counts must use the contract's own DV01 (CME Group, STIR Inter-Commodity Spreads, Apr 2024).
- ICS (SR1:SR3): a 3+3 : 10 ratio gives 250.02 vs 250.00 per bp. It is not FOMC-neutral when meetings are off-centre.
  FOMC-neutral example (Mar-22 SR3 vs Apr and May SR1, meeting 4 May 2022): sell 3.1 May and 2.9 Apr SR1 per 10 SR3,
  not the standard 3 + 3 (Huggins and Schaller, 2022).
- Futures DV01 hedge of a swap: bump each contract by 1bp in turn, reprice the swap at its original fixed rate, and set
  contracts_i = dPV_i / $25. Worked: 100mm 2y receive hedged with 779 contracts across M5..H7. The bump-all dPV of
  $19,480.69 against 779 x 25 = $19,475 (CME Group, Pricing and Hedging USD SOFR Swaps with SOFR Futures, Jun 2025).
- Convexity: listed futures have fixed $25/bp; swap DV01 changes with rates. Receive fixed against short futures is
  long convexity, and the swap rate must sit below the futures-implied rate by about the option premium (CME, Jun 2025).
- Strip hedges break when an FOMC date falls between term end and strip end. Use FOMC jumps or interpolation.
- Term-rate hedge (3M Term SOFR, $100m 2y, Jan 2022): net 45 SR1 and 25 SR3. A stress of +25bp on all forwards after
  the first fixing left a 0.7% miss (Huggins and Schaller, 2022).
- Packs and bundles (Aikin, STIR Futures, 2nd ed., 2012):
  pack yield = [prod_{i=1..4}(1 + (100 - P_i)% x 0.25)] - 1, forward-start from the first expiry.
  Worked: quarterlies at 97.49 / 97.31 / 97.21 / 97.16 give a pack yield of 2.735%.
  Bundle annualised = [prod_{i=1..4N}(1 + r_i x 0.25)]^(1/N) - 1. Adding the next four quarters (97.10, 97.00, 96.90, 96.87)
  gives 2.901% for the 2y bundle.
  Liffe quotes total change (0.005 steps); CME quotes annualised average (0.0025 steps). Check the convention before
  comparing.
- Pack vs stack: a 4:1 pack-stack trade (sell the pack, buy four of a middle month) is a fly plus a 6m spread. It is
  used for price improvement when legs diverge.
- Matrix additivity: H2H3 = H2M2 + M2U2 + U2Z2 + Z2H3. A spread can be built from longer spreads by columns or rows.
  Implied prices appear only at the top of the book and can vanish at the moment they are needed (Aikin, 2012).
- Microfly carry: carry = current fly level minus the level of the fly one slot shorter. Buy the belly with the most
  positive carry, and leg one contract at a time (Clarus, A Dummies Guide to Trading Interest Rate Swaps, Jun 2024).
- OIS futures: CME 3m Fed funds OIS = 100 minus daily-compounded EFFR (backward-looking). Futures lock in through the
  delivery month absent an FOMC meeting. 30-day fed funds = 100 minus the monthly average (Aikin, 2012).

**Bond futures (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022; Burghardt et al., The Treasury Bond Basis,
3rd ed., 2005):**
- Contracts = face x CF / 100,000. $100mm at CF 0.8338 gives 834 contracts.
- Gross basis GB = spot - CF x futures price. Net basis NB = forward - CF x futures. Carry = spot - forward.
  Forward price = spot plus term repo (synthetic).
- Tailing: N_fut = N_fwd / (1 + r d/360), for a d-day term repo at rate r. The effect is small for note and bond futures.
- Post-last-trading-day (LTD): the futures freeze, so switch to a face-matched hedge. Worked: $1bn long basis, 8,338
  futures short before LTD. After LTD the unhedged (1 - CF) x face adds 1,662 contracts, for 10,000 in total.
- Basis risk is funding risk: overnight vs term repo, and funding withdrawal or haircut rises that force deleveraging
  (Tuckman and Serrat, 2022). Cash-futures legs are not nettable at most venues and use balance-sheet capacity.
- Do not use the front STIR contract as a spread partner for a bond future; it locks to cash fixings (Aikin, 2012).
- EFP (exchange for physicals) quotes the basis and removes leg risk. Legging leaves the basis as a residual.
- UST inter-commodity spreads: fixed ratios are a historical convention. Recompute from current CTD DV01s. A DV01-neutral
  ratio (242 vs 100 in one older example) against a fixed 2:1 ratio (200 vs 100) left a 42-contract tail, so a fixed-ratio ICS
  plus a small outright on one leg is a common way to manage the tail (CurveTrades, Yield Curve Spread Trades, Jun 2013).
  Margin: total IM = larger leg IM - offset% x smaller leg IM (CME Group, U.S. Treasury Futures Inter-Commodity Spreads, Feb 2024).

**Invoice spreads (Clarus, What's the Deal with Invoice Spreads, Sep 2014):**
- Three ways to trade UST vs swap: (1) spread over Treasuries with a spot-start standard swap (inter-dealer standard);
  (2) matched-maturity bond vs swap, spot or IMM start (hedge-fund standard); (3) invoice spread: swap effective date =
  the futures delivery date, maturity = CTD maturity.
- Detection in SDR data: drop "Previous"-start trades (compression-like), keep trades whose effective and maturity dates
  match a futures delivery and CTD pair. The count is a floor, not market size.
- Aug 2014 example: 744 matches out of 22,219 USD swap trades (just over 3%). Strict matching is a floor only.

## 4. CCP basis and switch economics

**Orientation.** Schema orientation is LCH minus CME (basis_bp = 100 x (rate_LCH - rate_CME)). Most sources quote
CME minus LCH as positive. Under the source orientation, the trade that earns the basis is pay fixed at LCH and receive
fixed at CME. State the orientation beside every number, and convert before combining sources.

- Basis levels, 5y: 1.25bp in the worked example (pay LCH 1.86111%, receive CME 1.87361%). On $100mm that is $12,500 a
  year, $62,500 undiscounted over 5y, PV about $60,447 (Skarecky, Pricing and Arbitraging the CME/LCH Basis, Jun 2015).
- Indicative tenor curve (CME minus LCH, bp, 17 Jun 2015): 1Y 0.25, 2Y 0.35, 5Y 1.25, 10Y 1.85, 15Y 2.05, 20Y 2.20,
  30Y 2.40 (Skarecky, Jun 2015). The basis moves over time, so use dated snaps.
- Switch cost, $1bn 5Y at 1.2bp: 1.2bp x $1bn x 5 = $600k undiscounted (Khwaja, Hedging the CME-LCH Basis, May 2015).
- Switch benefit (same source): initial-margin relief of $17m per CCP ($34m in total). Funding saving:
  0.50% x (1/360) x $34m = $472 a day. Over 5y at about $460 per $1mm of 5y DV01: 460 x 34 x 50 = $782k, halved to $391k because IM decays. Default fund
  (about 8% of IM at 10% equity cost) about $270k. Total $661k, rounded to $670k in the source, against $600k cost. The $600k is
  undiscounted (1.2bp x $1bn x 5); at DV01 of $460k per bp the PV is nearer $550k. The source notes the benefit depends on
  the firm's own funding and portfolio.
- Full-cost breakeven for an indirect client: set NPV(proceeds - all fees - IM funding) = 0 and solve for the basis.
  Costs: execution, DCO fees, FCM fees (about $1,000 per ticket), IM funding (the largest term; it depends on the
  forecast IM path), and variation margin if modelled. Worked: a 5Y at 1.25bp needs a breakeven of 3.932bp, about
  three times the quote (Skarecky, Jun 2015). The source assumes 10bp of FCM IM fees, the low end of the 10 to 100bp
  it reports, so the breakeven is a floor.
- Hedge of a switch: a single-curve PV of the switch equals the locked-in basis. The two legs mark on their own CCP
  curves, so VM moves with the basis. Once CCPs publish CCP-specific curves, the switch MTM goes to zero if the basis
  is unchanged (Khwaja, Hedging the CME-LCH Basis, May 2015).
- Fair-value band, 30y (J.P. Morgan, Law of One Price vs Unintended Consequences, May 2016): upper bound = netting benefit
  of clearing pay-fixed against Treasury futures at CME; lower bound = dealer funding cost of posting IM at both CCPs
  over about 5 years. The band can be breached for long periods.
- Persistence: CCP basis can persist for more than a year. Track the CME share of volume and open interest as the
  mechanism for mean reversion. It is not a quick convergence trade.
- MVA: funding cost of the incremental IM profile. MVA in bp = total / trade DV01 (Skarecky, CME-LCH Basis For Dummies,
  Jun 2017). Pitfall: one source's per-DV01 numbers do not reconcile with its own DV01 (282,867 / 225,000 = 1.26bp,
  not the printed 1.30bp). Recompute before using.
- Portfolio margining: futures and swaps at one CCP are margined in one VaR-based IM. Without it, the two sit apart with no
  offset. Savings depend on the portfolio and on each CCP's risk model, and study-level figures are
  hypothetical maxima. Use the CCP's pre-trade what-if margin to size the benefit.

## 5. Unwinds, compression and re-couponing

- Three unwinds (Tuckman and Serrat, 2022): (1) tear-up for NPV, which may pay less than fair value; (2) offsetting
  off-market swap, hard to find a taker and both trades remain; (3) most common, an on-market DV01-matched swap with
  any counterparty.
- DV01 match, worked: receive $100mm 25y (DV01 0.196) and pay 30y (DV01 0.225). Notional = 100 x 0.196/0.225 = $87.1mm.
  Curve risk remains, and both legs stay on the books.
- Do not net 10y fixed against 6m floating as one DV01. Hedge the buckets separately.
- Compression: a clearing mandate lets CCP cycles net member risk into fewer swaps of the same risk. Compression
  packages are economically different from market trades (margin efficiency, operations), so strip them before judging
  liquidity (Clarus, Compression in USD Swaps, Dec 2014).
- Compression identification in SDR data: seasoned swaps, identical timestamps, large notionals in few trades (Clarus, Dec 2014).
- Re-couponing: terminate an off-market swap and replace it with a par swap on the same dates. It cuts margin and
  balance-sheet use, deterred by tax crystallisation and non-standard clearing. It can dominate observed volume, so
  check before reading SDR volume as positioning (Düring, 2021).
- IMM swaps start on the next IMM date and fix on a futures expiry, so they are easier to hedge (Düring, 2021).
- Notional overstates risk. Use DV01-scaled 5y-equivalents and entity netting. Tuckman and Serrat (2022) cite an estimate
  that 60 to 80% of IRS volume is standardised.

## 6. Repo, haircuts and funding that change package economics

- Specials: a bond is special if its reverse RP is below GC. A failed short pays coupon and earns no RP. Reverse RP on
  readily available collateral is typically 10 to 25bp below RP. Specials have no floor (Burghardt et al., 2005).
- Term vs overnight financing: overnight is cheaper on a positive curve but exposes the basis to slope.
- Haircuts: MF Global's peripheral-bond carry against about 0.70% repo was wiped out as haircuts rose from 3% to 80%.
  A package sized for that haircut "might have profited rather than have been destroyed" (Tuckman and Serrat, 2022).
- Clearing mandates raise fees and capital for levered basis financing. Include repo and clearing costs in the package.
- Balance-sheet: the leverage ratio binds on short-dated, high-notional activity, while RWA and market-risk capital bind
  on long-dated IRDs. Benchmark profit = Profit Factor x ((spot start + spot end)/2 + lifetime end - lifetime start)
  (Darbyshire, 3rd ed., 2022, Ch.17).
