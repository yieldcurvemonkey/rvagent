# Worked examples (carry and roll-down)

Receiver / long positive, curve unchanged unless stated. Every number carries its source. Examples A-E in
[SKILL.md](../SKILL.md) are not repeated here.

## 1. Carry-roll-down attribution on a cash bond (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022, ch. 3)
UST 7.625s 11/15/22, 13 Nov 2020 to 14 May 2021, realised-forwards scenario, financing ignored.

| Step | Price | Component |
|---|---|---|
| Start, spread -1.16bp to curve | 114.87654 | |
| Reprice at realised-forward curve, spread unchanged | 111.11555 | carry-roll-down **-3.76099** (-3.2739%), pull to par on a high coupon |
| Reprice at actual end curve | 111.29847 | rates +0.18292 (+0.1592%) |
| Reprice at actual end spread (-7.27bp) | 111.39690 | spread +0.09843 (+0.0857%) |
| Coupons received | | cash carry **+3.81250** (+3.3188%) |
| Total | | +0.33286 (+0.2898%) |

Check: cash carry + carry-roll-down = 0.0449% = (0.1013% - 0.0116%)/2, i.e. short rate (6m forward) less the bond's
own spread for half a year. Financing the full price at 0.05% costs $287 on $1.15mm, net 0.2648%; 98% repo with 2%
capital gives 13.27% return on capital at 50x leverage. Yield is not return: 2.375s 5/15/51 at 100.6875 (2.343%) returns
2.343% only if coupons reinvest at 2.343%; at 0% it is 1.778%/yr, at 5% 3.207%/yr.

## 2. Ilmanen forward-rate tables (Understanding the Yield Curve Pt 1-2, May-Jun 1995)
Hypothetical curve, par / spot / 1y forward (%): 1y 6.00/6.00/6.00; 2y 8.00/8.08/10.20; 3y 9.50/9.72/13.07; 4y 10.50/10.86/14.36;
5y 11.00/11.44/13.77; 10y 11.50/11.89/11.93. The 2y zero (6%, 8.08%) costs 85.61 and sells at 90.74 at f(1,2) = 10.20%:
a 6% return, so the 1y rate must rise more than 420bp before the 2y underperforms.
Linear curve 6% (1y) to 10.50% (10y), 50bp/yr: the 10y zero earns 10.50 + 9 x 0.50 = 15% = its 1y forward; the 9y spot
must rise 100bp to wipe out the 9% rolling-yield advantage; a parallel +100bp makes every bond earn 6%.
Rule: break-even yield change ~ yield spread / duration at horizon; f(1,3) - s3 ~ (s3 - s1)/Dur(2).
2 Jan 1990: par curve within 25bp of flat but 3m forwards spanned about 200bp, so high-forward sectors (6y, 12y) were
cheap and low-forward sectors (4y, 9y) rich; the cheap sector richened over the next 3m. Dec 1994: forwards implied a 2s30s
inversion; the bullet beat the duration-matched barbell, the front end flattened 108bp and the long end steepened 45bp.

## 3. Barbell vs bullet, convexity-adjusted (Ilmanen, Understanding the Yield Curve Pt 5, Sep 1995)
1 Sep 1995, 1y expected returns (rolling yield, value of convexity, convexity-adjusted E[r]): 5y 6.31/0.09/6.40; 10y
6.94/0.27/7.21; 30y par 6.67/0.88/7.55; 30y zero 5.93/2.53/8.46; 1y+30y barbell 6.23/0.47/6.70. Barbell vs 10y bullet gives up
71bp of rolling yield (0.53 x 6.67 + 0.47 x 5.73 - 6.94), 51bp after convexity. Break-evens: 11bp of 10s30s narrowing or a
138bp parallel move; history: 30% of years saw >=11bp narrowing, 17% a >138bp move in the 10y. 1980-94 backtest: barbell minus
bullet -1.05% = yield -0.95 + reshaping -0.36 + convexity +0.30 + residual -0.04; 99% of variance from reshaping.

## 4. UST forward breakevens in cash (BofA, Rates basics: spot vs forward, 15 Feb 2024; Bassman, 2024)
- 9 Feb 2024: 5y spot 4.15%, 1y forward 3.93% (-22bp); 30y 4.38% vs 4.35%; o/n SOFR 5.31%, 1y SOFR 4.91%; 5s30s spot 23bp,
  forward 42bp (+19bp). Breakeven as a share of 1-sigma (1y 5y implied vol 65bp): 5y about a third, 30y about 6%.
- Fully margined 2y (Bassman, The Cost of Carry, 5 Mar 2024): $10,000 of 2y 4.45% at 100 financed at 5.00% for 1y: coupon
  $445 - financing $500 = -$55; price must be 100.55 in 1y = 3.90% yield, so 1y1y = 3.90%, i.e. 110bp below the 5.00% financing rate (forward minus 1y rate = -110bp).
- 2y 4.53% vs 10y 4.18% (-35bp), $430 of 2y per $100 of 10y: must steepen 58bp to +23bp in a year; about $390,000 per month
  per $100mm. At -20bp (2y 4.35%, 10y 4.15%) it needs 60bp of steepening, "similar to the theta of owning a short-dated
  option" (Bassman, Sharp Curve Ahead, 25 Jan 2024).

## 5. Nordea EUR forward-carry monitor (EUR Rates Flash, 22-23 May 2019)
point: rate % / 1y C&R bp / value of convexity bp / conv-adj C&R per vol / z / % of last 1y-10y history in the money.
1y1y -0.228/3.4/0.1/0.18/-1.13; 4y1y 0.303/20.9/1.4/0.43/-0.76/26-14%; 5y2y 0.616/20.7/1.8/0.43; 15y5y 1.532/-2.6/4.9/0.04/-0.62/1-8%;
20y5y 1.317/-4.3/5.9/0.03; 30y10y 1.008/-1.5/7.6/0.13. Convexity value rises monotonically with expiry/tenor: 0.0 (1y), 0.8
(3y1y), 3.8 (12y3y), 6.7 (25y5y). View: pay the belly of 10/20/30y for carry plus high empirical payer in-the-money probability.
Empirical ITM = breakeven after 1y (current forward + convexity) vs the historical distribution of the point it rolls into.
Template (Nordea, EUR rates: Pushing back, 17 Jan 2024): receive 1y2y/3y2y/5y2y 6s fly at -8bp, target -25bp plus roll,
stop +5: carry/12m 79.2, 1y realised vol 46.5, carry/vol 1.70, in-the-money after 1y vs prior 1y/3y/5y/10y 100/59/75/76%, z 0.64.
Strategy table the same day (all received, C+R annualised, 50d vol): 2s5s 83.5bp, ratio 2.8; 2s5s10s 62.4, 2.6; 1y1y -88.6, -0.9;
1y basis -77.6, -7.9: in a cutting cycle receiving front outrights and basis bleeds while curves and front flies earn.

## 6. Swap-spread carry (Barclays, 30 Sep 2026; NY Fed Economic Policy Review, Negative Swap Spreads, Oct 2018; BofA, 6 Oct 2020)
USD swap-spread carry/vol, tenor: spread / carry / vol / C/V / spread at the 0.25 hurdle / widening room: 2y -14/11/10/1.15/-1/13;
5y -27/7/10/0.76/-8/20; 7y -34/6/12/0.52/-15/19; 10y -38/5/13/0.40/-23/15; 30y -66/4/17/0.24/-69/none. Belly has most room.
10y spread trade, $10mm, 1y, fall 2015 (NY Fed): initial margin 3.9% = $390k at 0.5% = -$1,950; receive 3m LIBOR 0.6% = +$60,000;
Treasury repo 0.3% on $9.72mm = -$29,160; haircut 2.8% = $280k at 0.5% = -$1,400; subtotal $27,490; spread -10bp = +$10,000; net carry
**$37,490**; ROE 35% at 1% SLR vs 6% at 6% SLR. The spread is not free carry: balance sheet (about 10-20bp), repo-vs-SOFR vol buffer
(2-3bp) and crisis illiquidity add to 13-25bp, all rising with maturity (BofA). Detail: [spread-swap-spreads-and-asw](../../spread-swap-spreads-and-asw/SKILL.md).

## 7. ING EUR trades with explicit carry/roll (Deconstructing the EUR yield curve, 15 Jan 2020; No rise in rates, 4 Feb 2020; EUR crisis trades, 3 Mar 2020)
- Pay 2s7s10s direction-neutral fly at 71bp (target 91, stop 61): carry -2.5bp + roll +3.2bp = +0.7bp/3m.
- Rejected 1F1Y-10F1Y steepener: 14bp too flat but roll -15.5bp/3m, breakeven in under 2.6 months. Forward fly 1F1Y-6F1Y-9F1Y: belly 23bp rich,
  carry -2bp/3m, carry erases the profit only after 36 months (months-to-breakeven = mispricing / bleed).
- 4Y-30Y PC1-neutral steepener 2.1:1 at 103.75 (target 123.75, stop 93.75): carry +0.7 + roll +0.8 = +1.5bp/3m; half cut 3 Mar at 102.75;
  hit the stop on 9 Mar (85.0). Positive carry did not save a trade into a vol event.
- Euribor Sep20-Sep21-Dec23 fly, buy the belly at 3.5bp (weights -1.64/+2/-0.51): carry 0, roll +4.2bp/3m. Sep20/Jun21 flattener at -1.25bp:
  roll +6.5bp/3m, all roll.

## 8. Fixed-vs-float and roll mechanics (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, ch. 23)
Static curve (0M3M 0.80, 1M3M 0.98, 2M3M 1.12, 3M3M 1.22, 4M3M 1.30, 5M3M 1.34, 6M3M 1.35%): 3M3M rolls 10bp after 1m, 24bp after
2m, 42bp after 3m. Receiver roll: 3m on the 5M3M = 1.34 - 1.12 = 22bp; 5m on the 6M3M = 37bp; 1m on the 6M3M = 1bp (not linear in h).
3M roll of a 2Y swap: 3M21M rolls 17bp (2.45% vs 2.28%), 0M3M rolls 5bp using 1d 0.70% held 3m compounding to 0.75%; combine by
analytic delta: (173/197) x 17 + (24/197) x 5 = 15.5bp.
Second-order carry/vol (EUR, Aug 2016): first-order roll/vol of spread said "receive 2Y3Y / pay 5Y5Y 0.35, pay 5Y5Y / receive 10Y20Y -0.80, pay 10Y20Y / receive
30Y20Y 0.02"; with gamma, pay 10Y20Y / receive 30Y20Y became +0.36 and pay 2Y3Y / receive 30Y20Y flipped from -0.25 to +0.18. The best
frontier portfolio reached a Sharpe of about 1.0.

## 9. Clarus: forward-start curve carry and short-end flies (Mechanics and Definitions of Carry in Swap Markets, 16 Jan 2019)
USD fwd 2s10s (Jan 2019): spot 2y 2.696%, 10y 2.73%, spread 3.82bp; 3m-forward 3m2y 2.662%, 3m10y 2.738%, spread 7.64bp: receiving
forward 2s10s earns about 3.82bp over 3m (1.3bp/month) with no short-end fixing risk. EUR 10y (15 Jan 2019, EUR 10m): 3m10y 0.8452% vs
spot 0.7944%, about +5bp over 3m; spot 10y cash carry = 0.7944% - (-0.24%) = 1.03% of notional cushions only about 10bp of rise on the
remaining 9y. Microfly (3 Mar quarterly IMM contracts, belly x2): Sep19-Dec19-Mar20 at -9bp rolls to +1.5bp, so buying earns 10.5bp
over 3m; consecutive flies mean-revert to zero "in a normal rate cycle". Not arbitrage: buying all cheap and selling all rich pays the
edge away in bid/offer.

## 10. Repo, specialness and futures carry in detail
- UST 10y OTR special spread cycle (51 notes, Nov 2008-Jul 2021; Tuckman 2022, ch. 10): peaks **156bp** the day before the first
  reopening (2-sigma band 116-196bp), **48bp** before the second, under 20bp before the next new issue. Overnight special spreads
  27 May 2021 (OTR, bp) 2y/3y/5y/7y/10y/20y/30y: 5/1/13/9/3/2/4.
- Repo stress: 99th percentile repo minus SOFR typically 10-11bp (Feb 2020), 20-50bp on several March days, **174bp on 16 Mar 2020**.
- Long TUH3 financed at "special" 3.79% vs GC 4.56% (Bassman, Leverage is NOT a four-letter word, 26 Jan 2023): linked 2y at 4.21%,
  carry 0.42%; at 4.8x leverage 2.02% plus 4.39% on T-bill collateral = 6.41%/yr (1.60% per 90d). Carry is per quarter.
- Futures carry inputs: bond-specific term repo to delivery, e.g. 4.0028% (Dec-26), 4.2051% (Mar-27), 4.3716% (Jun-27), with when-issued
  issues higher (J.P. Morgan, Basis Scenario Analysis Report, 28 Oct 2026).
- TYU1 CTD carry by coupon (Tuckman Table 11.8, 17 May-30 Sep 2021, ticks): 3.125s 11/28 36.8; 2.875s 5/28 33.8; 2.625s 2/29 31.2; 1.5s 2/30 17.8;
  0.625s 5/30 7.2: carry scales with coupon vs repo.
- Burghardt long basis, 7-1/2% 11/16, $10mm, 4/5-4/19/01, repo 4.5%: basis change -$1,562.50, carry +$7,381.29 (coupon +$29,005.52, repo
  -$21,624.23), total +$5,818.80. Special repo, May-Jun 2000: short $10mm 11/04 basis (reverse 6%) +$14,211; short 5/05 basis (reverse 5.48%)
  -$14,276, nearly $11,000 of it from the lower reverse repo.
- Bobl futures ASW (swapsball.net, Dec 2017): spot ASW 53.1bp 3m before delivery, futures ASW 53.7bp: carry 0.6bp/3m; OBL Oct22 rolls toward
  OBL Apr22 55.8 -> 53.7 over 6m = 1.0bp/3m. AUD 3y EFP: swap-leg C&R -5.1bp, futures carry +0.5bp, roll +3.5bp: total -1.1bp/3m.

## 11. Linker carry in cash (BofA, Global inflation-linked primer, 22 Jul 2025; Duering 2021 ch. 23)
TIPS 0.125% (3 Jul 2025, 3m): dirty cash = (97.85938 + 0.125%/2 x 79/183) x 1.13891 = 111.48340; forward cash = 111.48340 x 1.044^(3/12)
(repo 4.4%) = 112.71173; forward real dirty 98.11752 (horizon index ratio 1.14874); forward real clean 98.05911; forward real yield 1.40896% vs
spot 1.34569%: **carry = 6.3bp**. Real forward price ~ P0 x (1 + (r - i) x DCF), r - i = nominal repo minus lagged index inflation. Positive carry is
not positive return: the market prices the predictable carry (prints, seasonals). See [infl-breakevens-and-linkers](../../infl-breakevens-and-linkers/SKILL.md).

## 12. Cross-market carry rules (rule performance, for scale only)
10y carry (10y minus 1m, FX-hedged) long top / short bottom, monthly: IR 0.78 full sample, 0.34-0.50 for 1988-95, 0.88-1.47 from 2000 (J.P. Morgan,
Investment Strategies No. 15, 9 Mar 2006). Spread carry-to-risk, since 1989, IR 0.93-1.10 for 1-4 trades; at most 25% of return from capital
gains; constant 100bp risk beat scaling by carry level (IR 1.10 vs 0.53; Investment Strategies No. 31). Duration carry-to-risk, G4, top carry
quartile about 8% excess return vs under 1% bottom; IR 0.41 binary carry vs 0.63 carry-to-risk vs 0.75 proportional (Investment Strategies No. 74).
FX-hedged UST vs Bund yield pickup deciles: top decile long UST/short Bund IR 0.60, bottom -0.79, long-short 0.69, unconditional -0.13
(Willer and Saunders, Trading Global Macro Markets, 2026, ch. 7). Implementation: [quant-systematic-rates-signals](../../quant-systematic-rates-signals/SKILL.md).

## 13. Long-end forward flatteners: carry vs convexity (Citi Rates Vol Lab, 9 May 2019; 5 Dec 2019; 12 Jun 2023)
Daily breakeven = the daily move in rates whose convexity gain offsets a negative daily carry (set to 0 if carry is positive); compare with 1y realised
vol. USD 5 Aug 2019 15y5y/20y10y flattener: level -11.3bp (1y z 1.16), 1y carry -0.31bp, daily BE 1.3bp vs 1y RV 3.0bp, BE/RV 0.42. Exit on 5 Dec 2019: carry
worsened to as low as -2bp/yr and BE/RV rose to 0.8, booking +$155K net. Forward steepeners, 6 Aug 2023: 10y10y/20y5y 1y carry +10.31bp, BE 7.22, RV 5.24,
BE/RV 1.38 (carry pays more than recent moves would cost); best carry came with the worst entry. Do not initiate in an illiquid market even when the screen says
"free convexity" (USD 15y5y/20y10y, 27 Mar 2020: carry +0.11bp, BE 0, 1y RV 6.4bp). Method and thresholds: [vol-convexity-and-long-end](../../vol-convexity-and-long-end/SKILL.md).
