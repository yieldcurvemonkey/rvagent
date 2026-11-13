# Market-specific notes: skew and tail hedging across G10

Coverage in the source library is heavily USD and EUR with some GBP and JPY; the other G10 markets have no skew/tail material, so
the notes for them are structural guidance only, flagged as such. Method is in [SKILL.md](../SKILL.md); conventions behind strikes and
vol quoting are in [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md).

## USD
- Skew convention: 25bp OTM for 3m, 50bp for 6m-2y, 100bp for 3y+ in older Citi monitors; 2023-26 USD tables use 25bp throughout with the 5y-expiry RR-vs-model chart at 100bp out; BofA uses delta (25-delta receiver and the OTM payer labelled "75-delta" in receiver-delta terms, i.e. payer delta 25%) and costless-ladder BE widths. JPM quotes a 200bp-wide 3Yx10Y RR (ATMF+100 payer minus ATMF-100 receiver). Check before comparing issues.
- Structural drivers: mortgage/MSR hedging (skew flips at the convexity point), CMS-cap dealer hedging, structured-note vega, insurer
  buy-and-hold (5y20y), fiscal-tail hedgers in the long end, dealer gamma amplification of payer skew into selloffs. The mortgage "refinancing stack"
  concentrates realized then implied vol at specific rate levels: share of 30y pass-throughs whose coupon exceeds the current coupon by 140bp
  (90bp origination/servicing spread + 50bp refi incentive); a kink marks concentration; own options near the concentration, sell further away
  (Credit Suisse, The Convexity Vortex, 6 Mar 2013); see [flow-mbs-convexity-hedging](../../flow-mbs-convexity-hedging/SKILL.md).
- Instruments: swaption normal vols (expiry x tail x strike), bond-futures options (Board) with CTD-matched swaption mapping, SOFR-future options
  (skew nadir strike for cheap call spreads; straddle breakevens to FOMC outcomes), CMS cap/floor ladders on 10s/2s and 30s/2s. Meaningful SOFR option
  trading only from Feb 2022; jump-diffusion needed for consistent futures + options valuation.
- ZLB history: normal vol and receiver skew compress near zero; much of normal skew is flat in yield-vol terms; model choice matters
  (Credit Suisse, Wall Street Babylon, Nov 2011; JPM, Feb 2020).
- 3m2y is the most policy-path-sensitive skew sector (Rhodes, Oct 2025).

## EUR (DE/FR/IT/ES/NL ...)
- OTM convention 25bp (3m), 50bp (6m-2y), 100bp (3y+) (Citi, Feb 2023, Sep 2026). Shifted SABR / shifted lognormal needed where rates can be
  negative (shift h > 0, always state it) (Tuckman & Serrat, 2022).
- 2026 hiking regime: payer skew rich vs receiver at 3m1y; costless 1x2 payer spreads and 1x1.5 payer spreads used to sell it; balance-of-risk
  gauge P - R (see worked examples). EUR 2y10y RR 2 sigma cheap on 1y (Jun 2023); 10y-tail RRs rich via cheap receivers (Oct 2026).
- Long-end 30y: payer skew above receiver (2021) read as no near-term bear-flattening; delta-hedged long low-strike 30y receiver vs short high-strike
  payer hedges bull-flattening and the "scramble for hedges" (Dutch pension DC transition, Solvency II) (BNP Paribas, May 2021).
- Structural negative forward-spot roll at the long end means steepeners are effectively short payer skew.
- Vol-curve coupling: when the curve trades as a one-factor function of vol, conditional bull flatteners/bear steepeners become expensive as top-left
  vol cheapens relative to other vols.

## GBP
- SONIA options (May 2026): ~25-30% chance of Bank Rate back at 5.25%; cut distribution cheap; skew bid for puts to Mar-27, calls richer beyond;
  largest risk unchanged-pin trades through June and September (JWS Macro, May 2026). No swaption skew tables in the sources.

## JPY
- USDJPY put spreads funded by selling USD 10y payers when rates vol is rich to FX vol and USDJPY put skew rich (Citi, Jan 2020): cross-asset tail hedge.
- Citi considered long the H28-H30 OIS area and selling a risk reversal there (strip capped ~2.5% on belief the BoJ will not fall behind the curve);
  considered, not recommended. JPY vega low vs realized. Yield-curve-control precedent: JPY 1y2y/1y10y vol collapsed when the BoJ targeted the curve
  to 10y in 2016. Barclays: 2y2y 1x2 payer spread for gradual BoJ hikes (Oct 2026). Unshifted lognormal vols exceed 100% at low rates: use normal or
  shifted vols.

## CAD, AUD, NZD, CHF, SEK, NOK
- No skew or tail-hedging material in the sources. Do not assume USD/EUR skew behaviour transfers. Guidance:
  1. Use the delta or BE-width metrics (not fixed bp) and re-derive OTM distances from the market's own vol level.
  2. Expect thin, wide-bid/offer wings and sparse expiry/tail coverage; `vol_surface` may hold only a few strikes - the BE-width solver returns
     NaN rather than extrapolating, so report coverage gaps.
  3. Where the swaption market is illiquid, listed short-rate futures options (where they exist) or cross-asset hedges (FX options on the
     USD cross) may be the practical tail hedge; verify liquidity with [bt-transaction-costs-and-liquidity](../../bt-transaction-costs-and-liquidity/SKILL.md).
  4. Confirm index and day-count conventions in [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md) before quoting any strike.
