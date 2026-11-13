# Cross-currency basis: parity, instruments, pricing and hedged-return arithmetic

Companion to [SKILL.md](../SKILL.md). Notation: S = spot (USD per 1 unit of the non-USD currency), F = outright
forward, d = days from spot value date to forward value date, r = simple RFR-implied rate over the window, b = basis
(bp on the non-USD leg), tilde/star = non-USD leg, v = USD discount factor under a USD-collateral CSA, w* = non-USD
discount factor under the same USD CSA (the basis-adjusted curve).

## 1. Covered interest parity with and without basis
- Classical (no basis): F = S x (1 + r_usd d/dc_usd) / (1 + r_ccy d/dc_ccy). Approximation F - S = S x (r_usd - r_ccy) d/B,
  which is why STIR futures spreads (which can be subtracted but not divided) map linearly onto forward points.
  (Aikin, STIR Futures 2nd ed., 2012)
- With basis (RFR era, USD-based investor): F/S = (1 + r_usd d/dc_usd) / (1 + (r_ccy + b) d/dc_ccy). Convention: b is
  added to the non-USD leg. b < 0 means the forward is richer in the non-USD currency than interest differentials
  imply, i.e. USD is scarce. (BofA, FX-Sofr primer, 31 Oct 2023)
- Worked (Aikin, EUR/USD, 23 Jan 2012): S 1.2960, 92 days, EUR 1.12%, USD 0.56%. Theoretical F = 1.2942 (-18.49 pips;
  the approximation gives -18.55). With a 3m basis of -75bp: F = 1.2960 x (1 + 0.0056 x 92/360) / (1 + (0.0112 - 0.0075)
  x 92/360) = 1.2966, +6 pips, which matched the market quote. The same note: normal basis about -2bp; about -100bp in
  2007/8 and 2010/11. (Aikin, STIR Futures 2nd ed., 2012)
- Overnight illustration (Darbyshire, Pricing and Trading IR Derivatives, 3rd ed., 2022, Ex 7.1/7.2): EURUSD 1.20, EUR 5%,
  USD 1%: classical f1 = 1.19987. With an overnight basis of -100bp: 1.19990. The EUR depositor earns the extra EUR27.78
  that classical CIP ignores.
- Use the immediate (T+0) FX rate in discount-factor formulas, not the screen spot (T+2; USDCAD T+1). (same book)
- Forward FX is invariant to the CSA the swap is traded under: f_i = (w*_i / v_i) F0 = (v*_i / w_i) F0, where the
  discount factor w* is the one bent to reprice cross-currency swaps. A cross-CSA build giving different forwards is
  internally inconsistent. FX swap points set forwards at short tenors (xccy swaps barely trade there) and xccy swaps
  set them at long tenors; implied short-dated xccy prices come from FX swaps. (same book)
- Swap-derived rates are not default-free: classical IRP with swap rates overstates implied spot. Basis-adjusted form
  F = S (1+Y)^T / (1+Y~)^T x [1 + PV(X)], with PV(X) the PV of a quarterly annuity paying X (annual rate). X is the spread
  that makes USD 3M Libor + X fair against foreign 3M Libor, i.e. on the USD leg, so X = -b in this skill's convention
  (a negative non-USD-leg basis raises F).
  (Lehman, Interest Rate Parity, Money Market Basis Swaps and Cross-Currency Basis Swaps, Jun 2003)

## 2. Instruments
- **FX swap** = spot (or near-leg) exchange plus reversing forward exchange at an agreed point difference; no FX
  exposure; to about 1Y. Equivalent to a single-period fixed-fixed xccy swap with one fixed rate at 0%. Swap points p
  are the risk-bearing parameter; end-user platforms often use equal domestic notionals, interdealer uses split
  notionals (domestic notional grown by domestic rates). Example: 1M EUR100mm EURUSD at -20 points = 1.2500 then 1.2480.
  (Darbyshire, Pricing and Trading IR Derivatives, 2022; Darbyshire, Coding Interest Rates)
- **Cross-currency basis swap (CCBS)**: floating-for-floating in two currencies plus principal exchange at both ends.
  All CCBS have a USD leg: ESTR-TONAR is executed as ESTR-SOFR plus SOFR-TONAR. Trade it float/float with any fixed
  leg in a separate swap. After the RFR transition the legs are compounded SOFR vs compounded foreign RFR (AUD 3M
  BBSW and NZD 90-day BKBM remain term bank-bill legs). (Huggins & Schaller, FIRVA, 2024; BofA, FX-Sofr primer, 2023)
- **MTM vs non-MTM.** Non-MTM: same notionals at start and end at the initial FX; PV is dominated by FX moves and the
  structure is capital-intensive; corporates use it for cash-flow hedge accounting. MTM (interbank standard): one leg
  (normally USD) resets each period to the prevailing FX, with interim notional exchanges. Reset rule: N_i = N_alt x
  f_(i-1); the notional exchanged at the start of period i is N_i - N_(i-1). Example: EUR100mm alt notional, FX
  1.10 / 1.11 / 1.12: N1 = USD110mm, N2 = USD111mm, interim exchange +USD1mm, final -USD111mm; the last fixing (1.12) is
  not needed. First FX agreed bilaterally on trade date, later ones from a scheduled fixing. (Darbyshire, Coding Interest
  Rates)
- Quote fields to pin down: currencies, indices, start/end, frequencies, fixed or floating per leg, roll date, stub,
  MTM or non-MTM, collateral currency, which leg carries the spread. "EUR/USD 5Y non-MTM" implies float/float ESTR/SOFR.
- Valuation (multi-curve): only one leg can be at par; the spread goes on one leg; the collateral currency defines the
  RFR for discounting, so with SOFR collateral the SOFR leg is at par. (Tuckman & Serrat, Fixed Income Securities, 4th
  ed., 2022) The PV formulas for the payer of the spread are printed with an internally inconsistent sign in one textbook:
  derive the sign from the cash flows (receive non-USD floating + spread = long the basis) instead of copying it.
- Mid-market spread under the simplifying assumptions (PV zero, F0 = f0, identical schedules, USD forecast and
  discount off one curve): Z* = [sum_i w*_(i-1) - sum_i (1 + r*_i d*_i) w*_i] / sum_i d*_i w*_i, i.e. it depends on the
  non-USD forecast curve and the basis-adjusted discount curve only. (Darbyshire, Pricing and Trading IR Derivatives, 2022)
- Bootstrapping the non-USD discount factors under a USD cash CSA: from FX swaps w*_i = (1 + z_fx,i / f_(i-1)) (v_i/v_(i-1))
  w*_(i-1); from single-period xccy swaps w*_i = [(1 + r_i d_i) / (1 + (r*_i + z*_i) d*_i)] (v_i/v_(i-1)) w*_(i-1). The
  system is cyclic (basis, discount factors, forward FX): refresh forwards after each curve update. Details of curve
  construction: [fi-curve-construction](../../fi-curve-construction/SKILL.md).
- Solving the spread: PV is not linear in the spread under compounded RFR legs; use a second-order Taylor and the
  quadratic root, falling back to linear if the second derivative is zero (spread solve for +15mm PV: 362.2bp simple,
  357.7bp ISDA compounding). (Darbyshire, Coding Interest Rates)

## 3. Risk and P&L
- **Basis risk (CB01)** = P&L per 1bp move in the spread, expressed in USD, usually on the non-USD leg. About N x annuity
  x 0.0001 where the annuity is the non-USD leg's discounted accrual sum, close to the tenor in years at low rates. Example order
  of magnitude (own arithmetic, illustrative): USD25k per bp on a 10Y needs roughly USD 29mm notional (annuity about 8.5). Position P&L = (basis_now -
  basis_entry) x CB01 x direction (+1 long basis = pay in market jargon).
- Risk view for a package (USD per bp): received fixed on a USD 10Y 50,000, paid basis on a EUR/USD 10Y 25,000, paid
  fixed on a EUR 10Y 40,000 shows as USD RFR -50,000, xccy +25,000, EUR RFR +40,000 (Darbyshire, Pricing and Trading IR
  Derivatives, 2022, Ex 13.1). Darbyshire signs risk as the P&L gain per bp RISE, so long duration is negative there; in
  this repo's DV01 convention (positive = long duration, receive fixed) the same book is USD +50,000, EUR -40,000, and
  the "paid basis" line is Darbyshire's long-basis sign (+25,000 CB01, gains when the basis rises).
- Discounting risk migrates to the basis under a USD cash CSA: a received EUR100mm 10Y swap, PV EUR5mm, EUR discounting
  sensitivity EUR2,500 per bp (USD3,000 at 1.20), shows USD3,000 of xccy and USD discounting risk under a USD-only CSA
  (zero xccy risk under a EUR CSA).
  Multi-currency eligible collateral makes the poster's choice an option on funding spreads in different currencies;
  intrinsic risk is to the cheapest-to-deliver currency, and sharp risk boundaries at the switch tenor mislead when two
  currencies are almost equally cheap. Full treatment: [fi-collateral-csa-and-xva](../../fi-collateral-csa-and-xva/SKILL.md).
- Cross-gamma: hedging a non-MTM client xccy swap with interbank MTM swaps under different CSAs, or a local swap under a
  local CSA, leaves FX/delta and FX/basis cross-gamma. Compute P&L in the local currency and convert at the FX rate
  afterwards: Taylor-expanding converted PV, delta and gamma gave more than 5% error. (Darbyshire, Pricing and Trading IR
  Derivatives, 2022; Darbyshire, Coding Interest Rates)
- Balance sheet: a CCBS grows the balance sheet one for one (principal exchange); an IRS does not. EUR/USD CCBS widened
  from about 0 to below -40bp in 2008-12 partly because US banks were reluctant to add EUR exposure.
  (Huggins & Schaller, FIRVA, 2024)

## 4. Basis-swapped bonds: USD ASW and the CDS bound
- USD ASW = (ASW_foreign - CCBS) / CF, CF = BPV_usd / BPV_foreign, BPVs of the swap rates at the bond's maturity.
  Foreign cash flow = foreign reference rate + ASW; in the CCBS you pay the foreign rate + CCBS and receive SOFR, leaving
  (ASW - CCBS) in foreign currency, converted by CF. Par bonds assumed. If the local ASW reference differs from the CCBS
  leg (JGB ASW on TIBOR vs CCBS on TONA), add the interest-rate basis swap first. (Huggins & Schaller, FIRVA, 2024, Ch.16)
- Equilibrium USDASW = ASW/CF - CCBS/CF: one term must absorb a shock in another, but the identity does not say which.
  Low-risk issuers (Bunds): USD ASW is stable, local ASW volatility is absorbed by the CCBS (a more negative CCBS goes with
  a lower EUR ASW; the 5Y Bund and UST USD ASW correlate 0.73 weekly 2000-12). High-risk issuers (JGBs): the local ASW is
  stable (domestic holders), so the USD ASW mirrors the JPY CCBS and tracks CDS (5Y correlation 0.78, 2009-12).
- No-arbitrage bound: CDS >= adjusted CDS ~ USD ASW. Local-currency CDS trades at 30-60% of USD CDS; adjusted CDS =
  0.45 x CDS (FX effect only, cash settled) or 0.39 x CDS (FX plus delivery option, physical). Run scenarios of
  adjusted CDS at 30/45/60% of the quote. Trade only violations where USD ASW exceeds CDS; the other side needs a hedge
  for currency weakening after default. Violation threshold rose from about transaction costs to several tens of bp after
  2008 (capital charges): violation size is a proxy for scarcity of arbitrage capital. Credit side:
  [spread-sovereign-cds-and-basis](../../spread-sovereign-cds-and-basis/SKILL.md).
- Worked (23 Sep 2012, Libor era): 10Y JGB 6M ASW -1bp plus 3M/6M basis 12bp = 11bp; CCBS -64.5bp; CF 0.95; USD ASW =
  (11 + 64.5)/0.95 = 79.5bp vs 10Y Japan CDS about 130bp. Korea 2008-09: KRW ASW forced wider and the CCBS highly
  negative, USD ASW exceeded CDS by over 100bp at times. (Huggins & Schaller, FIRVA, 2024)
- Cash-flow matching for an asset-and-basis-swap package: CCBS notional = principal at maturity; par asset swap with upfront
  = par - dirty; identical settlement on all legs (T+2); spread added to the compounded rate, not daily rates; convert
  spreads between currencies by CF. Synthetic GBP UST (17 Oct 2023): UST 3.375% May 2033, dirty 90.37 (clean 88.94,
  accrued 1.43), upfront 9.63, SOFR + 30; CCBS notional GBP 81.97 at FX 1.22, 10Y SOFR-SONIA basis -19: net SONIA + 11bp;
  reverse-ASW coupon 4.46% GBP vs the 4.83% USD yield. (Huggins & Schaller, FIRVA, 2024, Ch.17)
- Global RV route: express every bond as fixed cash flows in one currency using ASW, interest-rate basis and CCBS, fit a
  benchmark curve and measure rich/cheap against it ([bond-rich-cheap-fitted-curve](../../bond-rich-cheap-fitted-curve/SKILL.md));
  or asset- and basis-swap every bond into a SOFR FRN (advisable only in USD).

## 5. Hedged-return arithmetic
- Hedged yield (home currency) = asset yield + annualised (F/S - 1), F and S in home per asset, at the hedge tenor,
  compared with the local alternative of equal duration and credit. Hedge carry = interest differential + basis, so a
  negative USD basis lifts hedged returns of USD investors in foreign assets and cuts hedged returns of foreign
  investors in USTs (relative to the pure interest differential).
- Rolling 3M versus maturity-matched hedge: EA investors in USTs over Bunds, rolling 3M pickup 2Y 17, 5Y 24, 10Y 18,
  30Y 29bp; maturity-matched 24, 35, 33, 56bp. Rolling hedges carry roll (basis and rate) risk. (JPM, 4Q24 Outlook)
- A hedged buyer is running a carry trade: a 30bp pickup on a 1y hedge is wiped out by 30bp of underperformance.
  (BofA, UST RV Primer, 2 May 2022)
- Aug 2026 (1y USDJPY hedge 2.68%): USD A-and-better 7-10y 5.42% hedged = 2.74% and 10-20y 5.83% = 3.15%, both below the
  30y JGB at 4.03%; Europe USD IG 7-10y 5.57% less 1.36% = 4.21% vs EUR corporates 4.04%. (Citi, High-Grade Beat, 19 Aug 2026)
- Japanese-investor 10y pickups with a 3m rolling hedge vs 10y JGB (Mar 2025): UST -1.42%, Bund -0.91%, OAT -0.20%, BTP
  +0.21%, gilt -1.12%, CGB -0.92%; a year earlier UST -2.40%. Japan still bought USTs with deeply negative pickup in 2019
  and 2023: flows follow the Fed cycle and capital-gain expectations, except at extreme carry. (BofA, US Rates Watch, 10
  Mar 2025; Willer & Saunders, Trading Global Macro Markets, 2026)
- Tenor choice for the hedge: onshore FX-swap hedges vs offshore forwards can differ by about 200bp of basis (TWD, Jan
  2020); a very inverted hedge-tenor term structure shows lifers extending hedge tenor. (JPM, Taiwanese demand, 10 Jan 2020)
- Cross-market pickup matrices (2y/5y/10y/30y by 3m hedge with 6m z-scores) and spread-to-hedged-yield rules are covered
  in [spread-cross-market-govies](../../spread-cross-market-govies/SKILL.md).

## 6. Issuer arbitrage
All-in cost of swapped issuance = home IRS rate + USD credit spread + xccy basis. Darbyshire's EUR corporate (Ex 4.1):
home 1% + 40bp = 1.4%; USD issuance swapped back: 1% + 50bp USD spread - 30bp basis = 1.2%, cheaper although USD credit
spreads are higher. Pressure: a EUR issuer raising USD and swapping back lends USD and borrows EUR (narrows the basis);
a US issuer raising EUR lends EUR and borrows USD (widens it); investors' swaps push the same way as the matching
issuers', so issuer and investor flow reinforce each other.
Compare spread vs the USD 3s curve with the EUR 6s curve after the 3s6s and xccy adjustments; negative = USD issuance
better. (Darbyshire, Pricing and Trading IR Derivatives, 2022; JPM, Stretched EUR/USD valuations, 27 Mar 2015)
Block prints near a pricing time show the hedge: a $3bn 3Y SSA deal is about EUR700k DV01, roughly one day of EUR/USD
basis volume, and block reporting caps basis at about EUR70k DV01, so size is understated.
(Clarus Financial Technology, A Voyeur's Delight, 24 Jun 2014)
