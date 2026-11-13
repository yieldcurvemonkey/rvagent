# Pricing, units, conventions and marking (rates options)

Detail behind step 1 of [SKILL.md](../SKILL.md). Every formula below is also implemented and self-tested in
[`scripts/bachelier.py`](../scripts/bachelier.py). Sources are cited inline; full list in SKILL.md.

## 1. Payoff, numeraire, Bachelier and Black

Swaption: PV of payoff = PV01(Tx; x,y) · N · [w (S_xy(Tx) − K)]+, w = +1 payer (pay fixed), −1 receiver. Use the forward
swap annuity as numeraire; the forward par swap rate is a martingale under it (BofA, US Vol Primer, 11 Mar 2024).
A TxTau receiver is a put on the tau-year forward par rate (Tuckman & Serrat, Fixed Income Securities 4th ed., 2022).

With F = forward swap rate, K = strike, T = years to expiry, v = sigma·sqrt(T), Phi/phi = normal cdf/pdf:

| Model | Payer price per unit annuity | ATM payer | Quote unit |
|---|---|---|---|
| Normal (Bachelier) | (F−K)·Phi(d) + v·phi(d), d = (F−K)/v | sigma_N·sqrt(T/2pi) | bp per sqrt(yr) |
| Black (lognormal) | F·Phi(d1) − K·Phi(d2), d1,2 = [ln(F/K) ± v²/2]/v | F·[2·Phi(v/2) − 1] | % of rate per sqrt(yr) |
| Shifted Black | Black with F+s, K+s | | % and the shift s (state it) |

Receiver = payer − (F − K) (put-call parity; Darbyshire, Pricing and Trading Interest Rate Derivatives 3rd ed., 2022).
Straddle = payer + receiver at the same K; ATMF straddle = 2·sigma·sqrt(T/2pi) and has ~zero delta, which is why a
vol quoted without a strike ("1y10y", "2y5y5y") always means the ATMF straddle.

Money: premium(bp) × PV01-per-bp of the forward swap (= annuity × notional × 1e-4). Check: 100m 1y10y ATM at 110nv:
premium 43.9bp, underlying PV01 ~77.8k per bp -> ~3.4m, vega ~ sqrt(T)·0.3989·PV01 = ~31k per 1bp of vol (BofA US
Vol Primer: NPV 3.432m, vega 31,203, 23 Feb 2024). Printed theta/vega in some textbooks are off by 100x; always
cross-check vega against sqrt(T)·0.399·PV01 (Darbyshire, 2022).

ATM greeks (annuity = 1): delta 0.5 (payer); gamma = 1/(sigma·sqrt(2pi·T)); vega = sqrt(T/2pi) per 1bp of vol; theta
= −0.5·sigma²·gamma per year (undiscounted, no roll). Locally at ATMF, vega P&L = gamma P&L:
Vega·(sigma_r − sigma_i) = sqrt(T/2pi)·(sigma_r − sigma_i) per unit annuity in the normal model (Quantitative Finance
Stack Exchange, "Option: link between Vega and Gamma", 2024, shown there for Black); the equality fails away from ATM or for large vol gaps. Full gamma/vega P&L
accounting lives in [vol-gamma-vega-pnl](../../vol-gamma-vega-pnl/SKILL.md).

Implied-vol solve: Brent (bracket 1e-9..5000bp) or Newton from 20bp, 2-4 iterations, tolerance 1e-4bp; fail loudly if
the price is below intrinsic (Darbyshire, 2022).

## 2. Day-count and daily units
- Annual normal vol -> daily: sigma/sqrt(252) (~ /15.9; 122nv = 7.7bp/day; 71.6nv = 4.5bp/day) (Credit Suisse, The FVA,
  27 Aug 2013). Use 252 consistently for implied AND realised; state it.
- Hedged-gamma breakeven: gamma P&L 0.5·Gamma·dS² offsets theta when the RMS move dS = sqrt(2·theta·dt/Gamma) = sigma/sqrt(252)
  (the 1-sd daily move). Darbyshire's "daily breakeven" is the same thing as a mean ABSOLUTE move for normal moves:
  sqrt(2/pi)·sigma/sqrt(252) = 0.798 × the 1-sd daily move (2022; Quantitative Finance Stack Exchange, "Gamma PnL Formula and
  Break-Even volatility"). State which one you quote.
- Calendar vs business-day time to expiry is subjective and material for short expiries: 31 calendar days incl. Easter
  gives 31/365 = 0.0849y vs ~19/252 = 0.0754y (Darbyshire, 2022). Fix one convention per book.
- MOVE (blended 1m ATM normal vol of Treasury options): 217 ~ 14bp/day ~ +-50bp over a month (Merrill Lynch RateLab,
  Implied Volatility: A Measurement of Fear, 7 Oct 2008).

## 3. Normal vs lognormal
- Normal vol = lognormal vol × forward rate: 22% at 5% = 110bp, 1-sd range 3.90-6.10% (Bassman, Wall Street Babylon,
  28 Nov 2011). bp vol = relative vol × yield; the stable-relative-vol assumption has failed in the US since 1982
  (Salomon Brothers, Convexity Bias and the Yield Curve, Sep 1995).
- Exact ATM equivalence: sigma_N = F·(2·Phi(v/2) − 1)·sqrt(2pi)/sqrt(T) (`normal_from_black`). Series: sigma_N ≈
  F·sigma_B·(1 − sigma_B²·T/24) (Darbyshire, 2022; one broker primer prints the denominator form 1/(1 + T sigma²/24),
  same to first order). Check: 15.68% × 2.00% = 31.36bp vs 31.33bp from the straddle (Darbyshire Ex 20.4).
- Split a normal-vol move into forward and logVol: at constant forwards the logVol change explains part of it. 1y10y logVol
  18.1% -> 20.7% explained ~11bp of a 21bp normal-vol rise in a month; the rest was the forward move (BofA, Global Rates
  Weekly, 2 Oct 2026). Normal vol can rise purely because forwards rose -> spurious directionality in vol signals.
- Near zero, log vol explodes (a 0.2% rate needs 100% log vol for 20bp); shift all rates by a constant (+30bp -> 40%,
  +80bp -> 20%) or just stay in normal vol (Darbyshire, 2022). Traders mark normal vol DOWN as rates approach zero
  (Bassman, Wall Street Babylon, 2011).
- Infer the market's regime by tracking both: if log vol is stable and normal vol moves with rates, the market prices
  lognormally; if normal vol is stable the market prices normally (Darbyshire, 2022). Level-dependence (CKLS gamma):
  1979-82 dominates estimates; GARCH + level gives gamma ~0.2 post-1983 (~0.4 from 1977) (Salomon Brothers, Understanding the Yield
  Curve Part 7, Feb 1996).
- "Be bilingual": check rich/cheap in both bases, then let implied-vs-realised arbitrate (Bassman, 2011). Nov 2011 example:
  blended 1m normal vol 102 vs 18y average 106 (cheap) but lognormal 56.4% vs 24.8% lifetime average (+2.0 sd, rich).

## 4. Listed futures options: units by root
- STIR futures options: normal vol of the rate in bp = normal vol of the futures price in points × 100. Futures-style
  margined options (Euribor, SONIA-type, Eurex) have no discounting and no early-exercise value; call on price = put on
  rate = receiver; put on price = payer (Tuckman & Serrat, 2022; Henrard, OpenGamma, Interest Rate Futures and their
  Options, 23 Feb 2012). Premium-style American options (CME) are valued as European when early exercise is negligible
  (deep ITM only); SOFR 3M options stop trading before the reference quarter, 1M options become arithmetic-average
  Asians inside the reference month with no closed form (Huggins & Schaller, SOFR Futures and Options, 2022).
- Bond-futures options are quoted in lognormal PRICE vol. Normal yield vol (bp) = 1e4 × price vol (fraction) / modified
  duration of the CTD; price vol in points = normal yield vol × futures DV01 per bp (Tuckman & Serrat, 2022; Merrill Lynch
  RateLab, 7 Oct 2008). Never pool vols across roots without converting; constant-maturity listed series are not
  tradeable (the front expiry rolls, CTD and notional coupon change).
- Mid-curve and long-dated listed options need the futures convexity adjustment in the underlying (Henrard, 2012); HW1F
  futures convexity at 5y is ~3bp / 12-13bp / 45bp for sigma = 0.5% / 1% / 2%. See
  [stir-convexity-adjustment](../../stir-convexity-adjustment/SKILL.md).

## 5. Surface and cube handling
- Axes: expiry 1m,3m,6m,1y,2y,3y,5y,7y,10y,(15y,20y,30y) × tail 1y,2y,(3y),5y,(7y),10y,(20y),30y; third axis strike offset
  from ATMF in bp (cube; wings usually 50bp steps). Corners: top-left short/short, top-right short expiry/long tail,
  bottom-left long expiry/short tail, bottom-right long/long (Darbyshire, 2022). Calibrating a cube needs 1000-2000
  parameters against 10-50 interbank prices: gaps are "educated guesswork" and non-transparency widens bid/offer.
- Mark each position at ITS OWN remaining expiry and current moneyness, never at a constant-maturity slot: differencing
  constant-maturity series books vol roll-down as P&L. Interpolate linearly in total variance sigma²·T with flat
  extrapolation; carry skew as a spread to the node ATM in strike-offset space (sticky in bp offset).
- Aged swaptions are no longer ATMF and need skew; a 5y5y receiver one month later is a 4y11m×5y, 14bp OTM when forwards
  rose 14bp (Tuckman & Serrat, 2022).
- Gamma vs vega sector: gamma sector = expiries <= 6m (sometimes 1y), vega sector = >= 3y, 2y grey; the border tilts
  right for short tails (JPY: ~4y expiry for 1y tails, 3y for 2y, 2y for 5y) (Huggins & Schaller, Fixed Income Relative
  Value Analysis 2nd ed., 2024). Gamma sector = delta-hedge and compare to realised; vega sector = statistical series.
- Walk vol: an option held to expiry delivers the vol of each shorter expiry it rolls through. walk_vol = sqrt(sum w_i
  vol_i² / sum w_i), time weights. Example 1y1y with 3m-delivered vols 87.5/101.8/113.8/122.8/141.5/143.8/142.8 and weights
  .0417/.0833/.0833/.1667/.25/.25/.125 -> 132.3 vs 142.8 plain (BofA, 11 Mar 2024). Implied/walk-vol is "more realistic"
  than implied/delivered for long expiries.
- Risk-neutral density: second strike derivative of price, g(K) ~ [O(K−d) − 2·O(K) + O(K+d)]/d² (Darbyshire, 2022);
  too-steep smiles are arbitrageable. See [stir-options-implied-distributions](../../stir-options-implied-distributions/SKILL.md).
- Cap vol is a flat vol on a strip; caplet vols are stripped with a strike adjustment; flat cap vol is a cumulative
  average with a hump near 1y (West, Interest Rate Derivatives lecture notes, 2010).

## 6. Settlement, fixings and date conventions that move PV
- Physical: the IRS is booked at the strike. Cash: PV difference to the prevailing mid is paid using an annuity built
  from the expiry-time fixing; cash and physical swaptions have different PVs and risk (Darbyshire, 2022). IBOR->RFR
  transition has reduced the difference.
- Cash settlement valuation date is 2 business days before exercise except same day for CAD and GBP (tpSEF Inc. Rulebook,
  Appendix B: Swap Specifications, May 2021; LIBOR/EONIA era, re-check). Settlement methods: cash price, collateralised
  cash price, par yield curve adjusted/unadjusted, zero coupon yield adjusted; fixings sources differ by currency
  (ISDA swap rate sources for USD/EUR/GBP/JPY/CHF/SEK/AUD/NZD/CAD).
- "1y1y" is ambiguous: swaps-aligned (2y = 1y + 1y1y), swaption-expiry (expiry + spot lag), swaptions-aligned. Over 262
  business days of 2024 the three agreed on 73%; a 1y1y IRS hedge of a 1y1y swaption carried date/roll mismatches on ~27%
  of days (Darbyshire, Coding Interest Rates). Pin eval date, calendar, modifier before hedging (see
  [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md)).
- Normal-model price is used to interpolate and delta-hedge, not to rank option richness; "no BSM-style model can
  describe the entire volatility cube" (Tuckman & Serrat, 2022).
