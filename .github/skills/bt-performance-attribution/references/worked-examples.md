# Additional worked examples and G10 notes

Companion to [SKILL.md](../SKILL.md). Every number is cited to its source; sign convention as in SKILL.md.

## A. Bucket and transformed-move explains (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022)

1. **Bucket explain.** `S` = (5Y +2,000, 10Y -3,000, 30Y +6,000) per bp in the book's payer-positive sign; `dr` = (+3, +2, +1)bp;
   `dP ~ S.dr = 6,000 - 6,000 + 6,000 = 6,000`.
2. **One trade, three risk models** (pay EUR 300mm 4.25Y IRS, analytic delta 122,115). Numeric strips 1Y..9Y: log-linear DF
   concentrates in 4Y/5Y (86,663 / 35,453); log-cubic spreads across all buckets (-231 ... 197); linear par-zero (92,015 /
   30,132). All sum to 122,115. With the curve on log-cubic, the day's moves (+1.1 ... +1.3bp) gave an estimate of EUR 1,179
   versus official 1,178 (unexplained EUR 1); the other two models would have left 1,328 and 784 unexplained. Use the risk model
   with the same interpolation as the curve.
3. **Transformed moves** (Ex 10.6): A = log-linear DF 1Y..4Y, B = 1Y and 4Y only; `S_A = (5, 7, 8, 4)`, `dr_A = (2.0, 2.0, 2.2, 3.0)`,
   true `dP = 53.6`. `S*_B = (8.2, 15.8)`. Reverse transform moves (2.0, 3.0) -> 63.8 (wrong); pseudo-inverse moves
   (1.9, 2.6) -> 56.7 as printed from rounded moves (about 55.5 unrounded; closer). The pseudo-inverse moves are not the actual 1Y/4Y moves: they are adjusted for the omitted 2Y/3Y.
4. **Trader-model explain** (Ex 16.8): par moves (+1.1, +1.4, +1.5, +1.6, +0.6, +0.2) give P&L (-88, 126, -68, 32, -24, 10), total -12;
   model moves (2Y +1.1, 2s3s4s +0.2, 3s4s5s 0, 2s5s10s +1.9, 5s7s10s -0.6, 10Y +0.2) give (-39, 9, 0, 0, 12, 6), total -12. The
   loss came mainly from 2Y moving while 10Y did not.
5. **Trader summary with VaR** (Ex 16.9, 16.12): model rows 2Y 41 risk x +1.3 = 54; 7s8s9s 114 x +0.6 = 69; 3s4s5s -165 x -0.2 = 33; total 175.
   7s8s9s made about 40% of the day's P&L on an unusually large move and contributed ~0 VaR: close and bank it. 2s5s10s is
   directional (paying it correlates with paying outright).
6. **PC attribution** (Ex 15.5): `S = (2Y -250, 5Y 150, 10Y 100, 30Y 60)`, `S~ = (-17, 166, 38, 263)`; non-centralised `dr = (+4.1, +5.2,
   +6.2, +2.0)`, `h = (+8.8, +2.5, -0.9, +1.0)`. By tenor -1,025 / +780 / +620 / +120 = 495; by PC -150 / +411 / -35 / +269 = 495. Level lost,
   PC2 (2s10s / 2s30s steepening) made most, PC4 (2s5s steepening) contributed; VaR 296 split 6 / 48 / 2 / 44% by PC. The par view only says "rates up with
   net positive risk, plus some steepening".
7. **Residual tracking of a PC1-neutral 2s5s10s** (Ex 23.2): `S = [-1.07, 1.94, -1.05, 0]`, 10-day `dr = [17.2, 18.1, 12.5, 8.1]`, `S.dr = $3.70`;
   PC1-only reconstruction `[18.7, 17.1, 12.7, 5.7]`; residual `xi = [-1.48, 0.97, -0.22, 2.45]`, `S.xi = $3.70`.
8. **Cross-gamma grid** (Ex 22.7): sub-grid P&L Ds/Ds 2.4, Ds/Dz -10, Ds/Dr -20, Dz/Dz 0, Dz/Dr 147, Dr/Dr 1,035; total 1,271 (off-diagonal blocks count twice: 2.4 + 2 x (-10 - 20 + 147) + 1,035 = 1,271). Rate/rate dominates; the
   forecasting-basis cross term also contributes.
9. **Risk bleed** (Ex 9.10): pay 11.5Y hedged 25% 10Y / 75% 12Y under log-linear DF, zero risk on (8Y, 9Y, 10Y, 12Y). After 1.5 years untouched: (-12.50, -12.50,
   +43.75, -18.75).
10. **Gamma of a date mismatch** (Ex 21.6): customised USD 1bn 30Y IRS paying 5 business days late: raw forward discounting risk $0.034 pv01, `sigma = 4bp`,
    expected gamma P&L `0.034 * 16 * 0.5 = $0.272/day`, x 63 days x 7,260 periods = $124,436 undiscounted, $62,218 at DF 0.50. Gamma is a priced item, not noise.
11. **Swaption explain units** (Ex 20.8): USD 100mm 1Y10Y 1.3% payer, normal vol 50bp, pv01 $93,200: delta $32,115 pv01, gamma $686 pv01/bp. Printed vega
    and theta look 100x too small (unit conversion from rate-percent to bp; about $34,300 per bp vol and -$3,400/day). State the price unit and calendar vs
    business-day time (31 days with Easter: 31/365 = 0.0849 vs 19/252 = 0.0754).

## B. Daily ledger (Darbyshire, ch.5, Ex 5.2; USD 000s)

| Day | A1 | B1 | B2 | C1 | C2 | D1 | D2 | E1 | E3 | F2 market | F3 new | G1 total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 80,000 | -2 | 5,000 | 2 | 965 | -256 | 354 | 75,711 | -1,063 | 965 | 98 | **1,063** |
| 2 | 75,711 | -2 | -1,000 | 2 | -110 | 33 | -10 | 76,636 | 87 | -110 | 23 | **-87** |
| 3 | 76,635 | -2 | 7,000 | 2 | 30 | 612 | -432 | 70,279 | -210 | 30 | 180 | **210** |

Day 3 opens at 76,635 while day 2 closes at 76,636 (as printed). `F1 = B1 + C1 = 0` each day: interest on cash equals carry.
Zero-PV example: pay USD 100mm 1Y semi-semi IRS at 1.0%; first 6M RFR 1.1% gives a net +$50,000 received; second 6M at 0.8996% costs $50,200; the $200 gap
is recouped by interest at an attainable 0.8% on the $50,000. Cash profile: 0, +50,000 at 6M, about 50,100 at 9M, 0 at 1Y.

## C. Bond, basis and return examples

- **Long CTD basis as option** (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005): buy 7-5/8% 11/22 basis at 18.09 with carry 13.56, i.e. 4.53/32
  paid for the options; unchanged yields about -3/32, -60bp about +7/32, +60bp about +19.5/32. Short-basis mirror makes at most about +3/32 with unlimited
  loss. 10y CTD short basis: 23 of 25 winners, kept 4.9/32 of 6.7/32 sold, stress case 17/32.
- **Carry example**: 7-1/4% of 8/15/22, full price 120.8764, term repo 4.54%, DC 181, 84 days: coupon income 1.68232, financing 1.280484, carry 0.401836 per
  100 = $4,018.36 per $1mm = 12.9/32.
- **Convexity P&L** (Tuckman & Serrat, 4th ed., 2022): century bond (duration 24.1, convexity 1,101) at -100bp: duration only 24.1%, plus `0.5*1,101*0.01^2` = 5.5%
  gives 29.6%, actual 30.978%. Long $100mm vs short $121mm of a DV01-matched 2050 Treasury: +$30.96mm vs $27.7mm, net positive both ways but it bleeds if rates do not move.
- **Salomon 30y bond 1980-94** (Understanding the Yield Curve Part 5, Sep 1995): total 10.34% = yield 9.41 + duration -0.49 + convexity 1.48 + residual -0.06; vol
  12.84 with 99% from duration. Convexity contribution by subperiod 2.83 / 1.44 / 1.65 / 0.80 / 0.67. **5s/30s barbell minus bullet**: total -1.05% = yield -0.95 +
  reshaping -0.36 + convexity +0.30 + residual -0.04; the bullet beat the barbell in 4 of 5 subperiods; reshaping exceeded convexity in absolute size in every subperiod.
- **Expected 1y returns, 1 Sep 1995** (Salomon, Part 5): 10y par 6.94 rolling yield + 0.27 convexity = 7.21; 30y par 6.67 + 0.88 = 7.55; 30y zero 5.93 + 2.53 = 8.46
  (convexity about 30% of expected return). 1y+30y barbell vs 10y bullet: gives up 71bp of rolling yield, still 51bp behind after convexity; breakevens 11bp of 10s30s
  flattening or a 138bp parallel shift (flattening of at least 11bp occurred in 30% of years vs 17% for moves above 138bp).
- **Three-month expected return, 26 Sep 1995** (Salomon, Part 6): 10y line 1.499 = yield income 1.568 + rolldown 0.108 + convexity 0.082 + duration impact of view
  -0.284 + local rich/cheap 0.025; the barbell trails the duration-matched bullet on every measure.
- **Cross-market carry** (JPM, Investment Strategies No. 15, 9 Mar 2006): 1 pair 5.0% = carry 3.2 + capital gains 1.8; 2 pairs 3.0 = 2.7 + 0.4; 3 pairs 3.1 = 2.1 + 0.9.
  **Spread carry/risk, best 2** (No. 31, 11 Jan 2007): total / carry / capital gains: All 1.81 / 1.34 / 0.47; curve + cross-market 1.44 / 1.24 / 0.19; about a quarter or less from
  capital gains; correlation with a global bond index 0.16, beta 0.12; the 50/50 curve + cross-market IR 1.33 vs 1.06 for the best across both themes.
- **EGB auction trades 2010-15, before costs** (JPM, Follow the cash flow, 15 Sep 2015): pre-auction T-5 to T-1 1,330 trades, 3.4bp, 67% hit, IR 2.5; post-auction
  1,342 trades, 1.5bp, 60%, IR 1.1; adjusted-versus-DE hedge 3.4bp (IR 2.5) vs outright 2.3bp (IR 1.1). Post-auction outright looked best only because the index yield fell from about 3.75% to 1.30%.
- **Systematic duration signals since 1999** (JPM, Systematic rule based strategies, 6 Mar 2017): carry-to-risk 2.2% return, 4.5% vol, IR 0.6, max DD -13.5%, success
  55% vs combined 2.0% / 1.7% / 1.2 / -1.8% / 63%: the combination's higher IR came from lower vol and a much smaller drawdown. EUR 3Mx10Y gamma rules since 2000 (bp of notional/yr, IR):
  always short 94 / 0.98; vol momentum 180 / 1.90; carry 159 / 1.68; combined 147 / 2.45; fading extremes -37 / -0.3 (JPM, Update on systematic rule based strategies, 6 Feb 2017).
- **IRS receivers** (Macrosynergy, Interest rate swap returns: empirical lessons, data to Feb 2018): 5y receivers 2000-Feb 2018 averaged 19bp of notional per month
  (about 2.3% a year); monthly SD 126bp (CHF 45 to BRL 273); average excess kurtosis 2.6; IQR 131bp vs average max/min 509 / -437bp.

## D. Convexity-RV trade attribution

- **Variance split of 1y forward flatteners** (JPM, An option by any other name, 3 Feb 2017, approximate chart read): 30s/50s convexity about 80% of P&L variance; 2s/5s
  about 20%; 5s/10s, 5s/30s and 10s/30s small (curve dominates). Backtest (flattener + 1Yx30Y ATMF straddles sized so premium equals 1y carry, daily from Jan 2009): 25Y/20Yx5Y
  vs 30s/50s: hit rate 86% vs 56%, average P/L 11.4 vs 10.4bp of notional, carry 1.1 vs -100.6, 5th/95th percentile -10/33 vs -140/128.
- **Factor-regression shares of P&L** (Internal convexity-RV research handover, undated): convexity 171.5% (10Yx10Y/20Yx10Y), 142.2% (30Y/50Y), 123.8%, 54.7%; 5Y/30Y slope 259.6%
  (t = 39.5), convexity 16.5%, carry -147.9%; a convexity-adjustment leg had R^2 0.150 and 186% of P&L in the intercept; the fly hedge leg lost $606k with level 65.8%, slope -40.6%.
  PCA basis PC1 88.34%, PC2 10.71%, PC3 0.73%. The fitted convexity coefficient landed within about 45% of the computed payoff-profile gamma.
- **GBP delta-hedged flattener** (Citi, Taking profits on GBP 15y10y/25y10y flatteners, 26 Mar 2020): 50K DV01 entered Jan 2020 and closed 26 Mar 2020 for GBP 445K net of costs
  = 115K curve move + 330K convexity: about three quarters from convexity in a vol spike.
- **EUR fly** (Citi, Holistic Approach to Convexity, Jun 2022): pay EUR 5y5y-15y5y-25y5y fly expected return +34bp, risk 50bp, expected Sharpe +0.7; weekly-rolled cumulative P&L since 2007 about
  430-470 with a steadily rising carry line and a small, persistently positive convexity line; delta large in 2008-11 and about 0 later. Selling EUR 1x2 wedges: structurally negative.
- **Delta-hedged EUR straddles** (Nordea, Bonds & bold, 5 Nov 2021): monthly roll Jan 2005-Nov 2021: convexity minus (theta + funding) monotone increasing except mid-2016 to 2019; no
  relation between entry vol and return; conclusions hold for long expiries only (not 3m10y or 1y10y).

## E. Desk scorecards and trade logs (units as quoted)

- 48 closed trades, 35 winners, 78% hit rate (JPM, Zen and the art of gamma maintenance, 9 Mar 2018). US IRD closed trades: 60 trades, 35 winners, 58% (JPM, Near, far, wherever yields are,
  2 Oct 2026). 2026 YTD by desk (trades / hit / average P/L): Euro options 10 / 90% / +6; Scandi 12 / 92% / +8; Euro swaps and spreads 33 / 56% / -1; UK ex-options 17 / 50% / -3 (JPM, Global FI Markets Weekly, 21-22 Aug 2026).
- 229 macro trades since 2023, 51% in profit; full sample +24.8% of $100mm, trailing 12m +5.2%, YTD +1.93% (Citi, Macro tapas, 7 Aug 2026). Closed rates trades in $ at stated DV01: pay NOK 12x15 FRA vs receive SEK
  12x15 FRA 15k +$580k; Feb-Mar ECB OIS flattener 87k EUR DV01 -$637k.

## F. G10 notes

- **USD**: futures P&L is price change only; term repo ACT/360 vs coupon on actual days; reverse repo typically 10-25bp below repo. Stock-bond correlation regression `corr = 7.43 x core CPI - 0.23`
  (R^2 0.22): the fit crosses zero near 3.1% core CPI (0.23/7.43; the authors' rule of thumb is about 2.5%), above which the correlation is positive, so duration stops hedging equities and bond P&L attributed to risk-off changes sign (Willer & Saunders, 2026). 30y Treasury
  convexity added about 148bp/yr over 1980-94, about half that in the 1990s (Salomon, Part 5).
- **EUR**: EGB spreads quoted versus Bunds; CCP basis is a valuation line (Eurex/LCH 2Y 0.70bp, 5Y 1.60bp, 10Y 2.70bp; CME/LCH 0.10 / 0.20 / 0.35bp; use LCH as the truth curve for EUR RFR; Darbyshire, Ex 6.1).
  Auction-concession edge weak in 2013-14; NL quarterly pre-announcement diluted pre-auction P&L.
- **GBP**: collateral choice is a P&L line: a GBP 100mm liability cost GBP 2,055 a day posting cash, 2,182 with a 3Y gilt and 1,999 with a 15Y gilt (as printed; Darbyshire, Ex 5.5).
- **JPY**: least correlated DM swap market (0.2-0.3) and lowest DM vol (about 1%); DM monthly 5y IRS correlations mostly 0.5-0.8; daily betas understate cross-market correlation through
  time-zone non-overlap, so blend in weekly estimates (Macrosynergy).
- **CAD, AUD, NZD, CHF, SEK, NOK**: no market-specific attribution theory in the sources; apply the same buckets, with local-currency explain then conversion (EUR/SEK example). SOFR and SARON are
  secured RFRs while SONIA, TONAR and EUR STR are unsecured: choose the funding benchmark accordingly (Tuckman & Serrat, 4th ed.).
- **Post-IBOR**: single self-discounted RFR curves make discount/forecast-basis cross-gamma vanish in USD, EUR and GBP, so only rate/rate cross-gamma matters in new explains; basis blocks
  remain relevant for legacy IBOR books (Darbyshire, 3rd ed.).
