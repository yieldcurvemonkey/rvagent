# EGB auction-concession and cash-flow reinvestment: backtest tables

Source for every number below: J.P. Morgan, European Rates Strategy, "Follow the cash flow - Trading strategies around
supply, redemptions and coupon payments in Euro government bond markets" (Salford, Chordia, 15 Sep 2015). Sample Jan 2010
to Aug 2015, euro-area (AT, BE, FI, FR, DE, IT, NL, ES; IE/PT/GR excluded as aid-programme countries), conventional bonds,
close-of-business levels, **before transaction costs**. Columns: average P&L per trade in bp / success rate / annualised
information ratio (IR). Use these as priors and as a design template for your own backtest, not as live expectations: the
sample is a falling-yield, high-liquidity-premium period.

Conventions used here (restated, the source quotes spread-vs-Germany in its own terms):
- T = auction date (trade-date basis). Pre-auction = short the tapped bond (or, for a new line, the closest shorter
  maturity) at close of T-5, exit at close of T-1. Post-auction = long at close of T-1, exit at close of T+4.
- "Adjusted" hedge = curve-adjusted spread vs Germany: `(ASW_c - ASW_DE) - beta x EA_mm_spread`, with
  `beta = (bond_yield - mm_German_par_yield) / weighted_EA_maturity_matched_spread_to_Germany` (a ratio, not a regression
  beta). "Non-adjusted" = plain ASW spread vs Germany. "Outright" = the bond yield alone.

## Headline

| Strategy | Trades | Avg P&L (bp) | Success | IR |
|---|---|---|---|---|
| Pre-auction short, T-5 to T-1 | 1330 | 3.4 | 67% | 2.5 |
| Post-auction long, T-1 to T+4 | 1342 | 1.5 | 60% | 1.1 |
| Coupon/redemption long (5Y), T-1 to T+3 | 344 | 0.4 | 51% | 0.6 |

## Holding window

| Window | P&L | Success | IR |
|---|---|---|---|
| Pre T-5 to T-1 | 3.4 | 67% | 2.5 |
| Pre T-4 to T-1 | 2.3 | 63% | 2.2 |
| Pre T-3 to T-1 | 1.3 | 59% | 1.7 |
| Post T-1 to T+3 | 1.3 | 60% | 1.0 |
| Post T-1 to T+4 | 1.5 | 60% | 1.1 |
| Post T-1 to T+5 | 1.5 | 60% | 0.9 |
| Redemption/coupon T-2 to T | 0.1 | 54% | 0.4 |
| Redemption/coupon T-1 to T | 0.2 | 53% | 1.1 |
| Redemption/coupon T-1 to T+1 | 0.2 | 53% | 0.5 |
| Redemption/coupon T-1 to T+2 | 0.3 | 53% | 0.5 |
| Redemption/coupon T-1 to T+3 | 0.4 | 51% | 0.6 |

Reading: the pre-auction edge accumulates through the whole T-5..T-1 window (longer = better); the post-auction rally is
a smaller reversal of it. Cash-flow reinvestment is a different animal: tiny, close to a coin-flip.

## Hedge construction

| Hedge | Pre-auction P&L / success / IR | Post-auction P&L / success / IR |
|---|---|---|
| Curve-adjusted vs DE | 3.4 / 67% / 2.5 | 1.5 / 60% / 1.1 |
| Non-adjusted vs DE | 2.6 / 59% / 1.2 | 1.9 / 57% / 0.7 |
| Outright | 2.3 / 56% / 1.1 | 2.9 / 60% / 1.0 |

The outright post-auction figure (2.9bp) reflects the EMU index yield falling from ~3.75% (2010) to ~1.30%; it is trend,
not concession. Reinvestment, 5Y: adjusted 0.4/51%/0.61, non-adjusted 1.1/52%/0.57, outright 1.4/56%/0.81; 10Y: adjusted
0.5/59%/0.84, non-adjusted 0.4/54%/0.28, outright 0.8/57%/0.54.

## By maturity (pre P&L/success/IR ; post P&L/success/IR)

| Maturity | Pre-auction | Post-auction |
|---|---|---|
| 2Y | 3.9 / 68% / 2.4 | 2.0 / 61% / 1.3 |
| 5Y | 3.7 / 66% / 2.3 | 1.8 / 58% / 1.1 |
| 10Y | 3.0 / 66% / 2.7 | 1.2 / 59% / 1.0 |
| 10Y+ | 2.8 / 71% / 2.7 | 1.2 / 61% / 1.0 |

## By country (pre-auction P&L / success / IR; post-auction P&L, IR)

| Country | Pre | Post |
|---|---|---|
| AT | 2.1 / 56% / 2.1 | 1.0, 0.9 |
| BE | 4.0 / 68% / 3.0 | 3.4, 1.8 |
| FI | 0.3 / 52% / 0.7 | -0.6 |
| FR | 2.3 / 73% / 2.8 | 1.1, 1.4 |
| IT | 4.3 / 67% / 3.6 | 2.2, 1.4 |
| NL | 0.9 / 59% / 1.9 | 1.2, 1.9 |
| ES | 5.1 / 67% / 2.4 | 1.1, 0.6 |

FI and NL are small samples; NL pre-announces a quarterly calendar, which spreads the concession over a longer period.
Concession is strongest where the bond is illiquid/supply-heavy (ES, IT, BE).

## By year (pre-auction P&L / IR)

2010 2.7/3.3; 2011 5.8/3.4; 2012 7.2/3.2; 2013 1.1/1.9; 2014 0.5/1.3; 2015 (to Aug) 1.3/2.7. Post-auction 2014: 0.1bp, IR
0.2. The edge roughly doubled in 2011-12 (illiquidity) but costs rose by more; it faded when liquidity normalised.

## Size does not matter

Regression, pre-auction: avg P&L = -317.1 x auction size (% of outstanding) + country intercepts (AT 1.8, BE 2.0, FI 1.4,
FR 0.9, IT 2.1, NL 0.4, ES 2.1) + 1.3; R2 6.3%. Reinvestment: P&L = 21.2 x payment size (% of outstanding) + country terms
- 1.0; R2 9.8%. Neither is a usable size signal: do not scale up for bigger auctions or bigger cash flows.

## Italy-Spain auction-cycle switch (10Y benchmark sub-indices, since 2014, 76 trades each)

Short the country that auctions next, flip before its auction.

| Exit | Total | Per trade | IR | Success |
|---|---|---|---|---|
| T-1 | 66bp | 0.7bp | 1.1 | 58% |
| T-2 | 164bp | 2.0bp | 3.0 | 62% |

Across all countries T-5 to T-2 vs T-5 to T-1 is not significantly different; 2015 IR 3.9 (T-2) vs 2.7 (T-1) with P&L
1.2 vs 1.3bp. Re-test the best exit day periodically: the optimum drifted from T-1 to T-2.

## Reinvestment by country (5Y)

AT 0.2bp/48%/IR 0.4; BE 2.4bp/76%/IR 3.0 (21 trades); FI -0.4; FR 0.9/IR 1.7; IT -0.2/47% (redemption and coupon dates
coincide with supply there, so the auction cycle dominates); NL 1.2/IR 3.5 (16 trades); ES 1.8/IR 1.9. Best year 2012:
2.5bp, IR 2.4; 2013-14 flat or negative. Use T on a **trade-date** basis: the date whose trades settle on the payment
date, so received cash can fund the purchase.

## Cross-checks from other sources

- Large April redemptions were expected to tighten the French front end and Spanish 5y vs Germany; Dutch 10y cheapness
  was attributed to supply overhang from a EUR5.8bn new 10y (BofA Merrill Lynch, European Rates Viewpoint: Many EGBs, one
  simple value tool, 21 Mar 2018).
- German 2s10s tends to flatten in March/May on late-April coupon and redemption reinvestment by quasi-passive investors
  moving out the curve towards a ~10y WAM, plus month-end index extension (BofA Securities, Bond market seasonality
  explained, 6 Jun 2022).
