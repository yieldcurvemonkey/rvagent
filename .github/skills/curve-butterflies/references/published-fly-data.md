# Published fly numbers: weights, diagnostics, regime tables, trades

Sign: fly = 2*belly - wings in bp, positive = belly cheap, quoted for receiving the belly (Citi convention) unless a row says
otherwise. Scale caveats: Citi's 2017-23 monitor rows (sections 1 and 3) are defined on -0.5:1:-0.5 weights, i.e. half the 2*belly - wings figure
(the 2010 trade note in section 4 uses the full scale); Clarus microfly values (section 5) are 2*belly - wings in price, i.e. minus our sign. All numbers are historical and illustrative, not recommendations; rebuild weights and re-test before use.
Main text: [SKILL.md](../SKILL.md). Methods: [weighting-methods](weighting-methods.md).

## 1. How PCA-fly weights drifted (USD swaps, wing : belly : wing, 5y rolling window of the 3 legs)
| Fly | Published weights (date) |
|---|---|
| 2s5s10s | -0.9:1:-0.7 (Feb 2017); -0.52:1:-0.57 (Apr 2018); -0.43:1:-0.62 (Jan 2019); -0.39:1:-0.68 (May 2019); -0.36:1:-0.72 (Oct 2019); -0.32:1:-0.73 (Feb 2023) |
| 5s10s30s | -0.5:1:-0.6 (2017); -0.47:1:-0.63 (Apr 2018); -0.44:1:-0.62 (Jan 2019); -0.45:1:-0.62 (May 2019); -0.46:1:-0.57 (Feb 2023) |
| 10s20s30s | -0.2:1:-0.8 (Jan 2017); -0.24:1:-0.79 (2018/19); -0.24:1:-0.77 (May 2019); -0.40:1:-0.60 (Feb 2023) |
| 2s3s5s | -0.8:1:-0.4 (Jan 2017); -0.67:1:-0.38 (Apr 2018) |
| 2s5s7s | -0.28:1:-0.75 (Jan 2019); -0.25:1:-0.79 (May 2019) |
| 2s10s15s | -0.18:1:-0.88 (Apr 2018); -0.13:1:-0.92 (May 2019) |
| 2s10s30s | -0.21:1:-0.87 (Feb 2023) |
| 15s20s30s | -0.50:1:-0.51 (May 2019) |
Sources: Citi US Rates Weekly of 13 Jan 2017, 3 Feb 2017, 20 Apr 2018, 18 Jan 2019, 10 May 2019, 17 May 2019, 4 Oct 2019, 17 Feb 2023
(Mathai et al.). Three-year-apart snapshots of the same fly differ by up to 0.5 in a wing weight: always re-estimate.
Weights do not sum to -1 (not DV01-neutral), and none was forced to a "wings negative" sign.

Citi correlation facts: equal-weight 10-20-30 had 96% 3m correlation to 5s30s while the PCA version was mostly low (34%);
2-3-5 equal-weight -89% to 2s10s; PCA flies can retain sizeable correlation to 10s, so check both slope and level.
Citi monitor columns: level, 3m carry+roll (3m rolldown for forwards), 3m high/low, 1m/3m/6m z (12m for forwards),
3m correlation with 10s, 2s10s and 5s30s; 28 flies from 2-3-5 to 15-20-30, spot and 1y/2y/3y forward.

## 2. PCA vs 50/50 diagnostics (UST, BofA)
Format: PCA fly min/max/mean/sd/last/Z || 50/50 mean/sd/last/Z || R^2 vs belly || residual/Z. 6m window (BofA, Understanding the yield
curve dynamic, 23 Jul 2025):
| Fly | PCA fly (min/max/mean/sd/last/Z) | 50/50 (mean/sd/last/Z) | R^2 | Resid/Z |
|---|---|---|---|---|
| 2s5s7s | -103.9/-89.5/-98.1/3.4/-102.6/-1.3 | -11.4/4.6/-18.7/-1.6 | 49.4% | -4.0/-1.2 |
| 2s5s10s | -101.2/-75.9/-91.8/5.5/-98.9/-1.3 | -21.5/9.2/-36.1/-1.6 | 65.4% | -7.3/-1.3 |
| 2s5s30s | -40.6/-5.4/-28.1/6.6/-34.4/-0.9 | -28.3/20.9/-62.5/-1.6 | 68.7% | -17.0/-1.5 |
| 3s5s7s | -31.6/-23.4/-28.6/1.8/-30.3/-1.0 | -4.9/2.3/-8.2/-1.4 | 42.9% | -1.8/-1.0 |
| 3s5s10s | -22.6/-8.5/-18.1/2.8/-20.6/-0.9 | -14.9/7.1/-25.6/-1.5 | 64.0% | -5.0/-1.2 |
| 3s5s30s | 1.2/20.4/7.1/3.5/4.5/-0.7 | -21.8/18.9/-52.0/-1.6 | 67.8% | -14.7/-1.4 |
3m window, 2022 (BofA, UST RV Primer, 2 May 2022), PCA mean/SD/last/Z | 50/50 mean/SD/last/Z | R^2 | residual/Z:
2y/3y/5y -7.5/2.5/-15.3/-3.1 | 9.4/5.5/8.7/-0.1 | 80.8% | -8.0/-3.3; 2y/3y/10y PCA Z -2.8, R^2 89.1%, residual Z -3.7;
5y/10y/30y -19.2/2.9/-15.1/1.4 | Z 2.6 | R^2 3.0% | 7.3/2.3. PCA RV needs stable eigenvectors out of sample: check 1m/3m/6m/12m.

## 3. Fly snapshots and monitor rows (USD swaps, receive-belly sign)
- 3 Feb 2017: 2-7-10 25.3bp (6m z 1.06, 3m hi/lo 30.2/10.8); 2-10-15 36.3; 5-20-30 30.6; 5-7-12 -4.4 (1m z -1.72). Many PCA flies
  at -1.2 to -2.0 z together (Citi, Going nuclear, 3 Feb 2017).
- 3 Oct 2019: 1:2:1 2s5s10s -11.1bp (carry+roll 1.6, z 1m/3m/6m -0.33/0.38/0.46, 3m range -9.5 to -13.7); PCA 2s5s10s (-0.36:1:-0.72)
  -22.6bp; 1:2:1 5s20s30s +12.3 (z 2.03/-0.15/-0.63) (Citi, All it takes is a little push, 4 Oct 2019 edition).
- May 2019: PCA 2-5-10 -28.6bp (richest since 2013), advice: steepen via 2s10s/2s30s not 5s10s/5s30s (Citi, Trade worries linger, 17 May 2019).
  Mar 2019: 2s5s10s lowest since 2013 (ZLB) and 2s10s30s richest since 2006 (Citi, Vol cycle, steepeners, and SOFR, 25 Mar 2019).
- 16 Feb 2023: equal-weight 10-20-30 5.7bp (z -1.61/-2.69/-1.60), PCA 10-20-30 8.9 (z -1.60/-2.58/-2.22): 20y rich; 2-3-5 belly cheap
  (z 1.92/2.20/0.39) (Citi, Time for moderation, 17 Feb 2023).
- UST forward fly levels 29 Jan 2015, spot / 6m forward (bp): 2-5-10 29.2/33.1; 2-5-30 -27.4/-19.3; 2-10-30 66.8/69.5; 5-10-30
  -9.5/-7.9 (J.P. Morgan, Forward Treasury, Asset Swap and Funding Report, 29 Jan 2015). Forward minus spot = breakeven implied by carry.
- Screened moves (30 Sep 2026): 1w 2s10s30s +9bp EUR (3.2 sd), +7bp GBP (3.6 sd), +12bp USD (3.1 sd); 1m 5s10s30s EUR +16bp (3.5 sd),
  GBP +7bp (4.4 sd). Short windows inflate: a 62-day window flagged a 4bp move at 5.7 sd (Goldman Sachs, GS Market Movers, 30 Sep 2026).

## 4. Regime-conditional fair value (Citi, Flying Too High, 20 Dec 2010)
Regime averages (USD swaps, bp) 2s5s / 5s10s / 10s30s / 2s5s10s / 5s10s30s: on hold after cut 129/93/69/36/24; start of hiking 106/74/63/32/10;
6m into hiking 69/55/49/14/6. Market-implied hike-start probabilities (30% 2011, 42% 2012, 28% 2013) weight the regimes:
`9%*6 + 21%*10 + 70%*24 = 19.4bp` predicted 1y-forward 5s10s30s vs 48bp traded. Table for spot / 1y forward / predicted:
2s5s 132/129/119; 5s10s 126/94/85; 10s30s 73/46/66; 2s5s10s 6/35/33; 5s10s30s 53/48/19. Convexity: 1y-forward 10s30s steepener costs 11bp/a
at 120bp/a realised vol vs 8bp/a for the 5s10s30s fly; carry -5bp/a (fly) vs +27bp/a (steepener); the fly was chosen for lower convexity
cost and less directionality than the forward steepener. Cycle pattern from (Citi, All it takes is a little push, 4 Oct 2019): the belly
cheapens in full easing cycles; at the ZLB (5y5y OIS at 1-1.2%) 5s richen, so compare the forward-implied fly with the fly-vs-level scatter.
Macro-path levels for 50/50 2s5s10s: ~2bp (5 Feb 2001, flat expectations), ~22bp (4 Sep 2001, quick recovery), ~4bp (23 Mar 2003, slow
recovery); model hedge ratios wings/5s, 10s/wings 105%/72%, 108%/72%, 112%/50% (Lehman, Tuckman, Oct 2003). Fast recovery expected: more weight on 10s.

## 5. EUR fly episodes
- **BNP 5s10s30s (25 May 2021)**: model put the 10y ~6bp expensive on 7 Apr 2021; pay 5s10s30s at -5bp, +1.5bp later, targets +3/4bp and +8bp, stop -4bp,
  carry+roll +0.8bp/month. Episode study (residual < -5bp for > 1 week, 7 episodes since 2013): start -> fair 3.1 months average, fair -> +5bp overshoot 2.7
  months, overshoot in 6 of 7 (Feb13/Jun13/Jul13; Oct13/Nov13/Dec13; Jun14/Feb15/Mar15; Nov15/Dec15/none; Jan16/Feb16/Feb16; Jan17/Apr17/Nov17;
  Mar19/Aug19/Mar20). Normalisation came with a flatter 10s30s 6/7 times. Risk-off hedge: fly changes in episodes (VIX in brackets): Oct-14 -20 to
  -12bp (12->23%), Aug-15 +5 to +14 (12->41), Jun-16 -4 to +7 (13->26), Jan-Feb 18 -4 to +13 (9->37), Dec-18 +2 to +7 (20->36), Feb-Mar 20 -16 to +26
  (14->83); average rise 15bp.
- **ING PC-neutral receive-belly 2s5s10s (9 Mar 2020)**: weights -2.41 / +2 / -0.66, entry 49.5bp (incl. 0.5bp charge), target 20, stop 65, carry+roll 4.7bp/3m,
  half size (higher vol); the 1-2-1 version regression fair value R^2 0.69, SE 5.2, "10bp too high". On 12 Mar 2020 they preferred the DV01-neutral version.
  Pay-belly PC1-neutral 2s7s10s (entry 71, target 101, stop 86) with front-end receiving "did not work" while receive-belly flies premised on disappointed cut
  expectations did (ING, March ECB: QE or bust 9 Mar 2020; taking out the ECB put 12 Mar 2020).
- **ING forward fly (15 Jan 2020)**: pay 1F1Y-6F1Y-9F1Y direction-neutral, belly 23bp too expensive, carry -2bp/3m so reversion over 36 months would be needed to lose;
  spot equivalent pay PC1-neutral 2s7s10s entry 71, target 91, stop 61, carry -2.5 + roll 3.2 = +0.7bp/3m, 9bp from the 3y mean. Rejected: 1F1Y-10F1Y steepener
  (14bp too flat but rolls -15.5bp/3m, breakeven only if it closes in < 2.6 months). Value vs carry regression on a direction-neutral basis `y = -2.696x + 38.023`,
  R^2 0.8638 (frontier slope doubled from -1.27 once PC1 sensitivity was removed) (ING, Deconstructing the EUR yield curve, 15 Jan 2020).
- **ING multi-factor Euribor fly (3 Mar 2020)**: 2-6-15 fly (weights -1.64/+2/-0.51) regressed on 2Y swap, iTraxx senior financials, 1Y1Y normal vol and S&P P/E: R^2 0.55,
  SE 2.1, ~9bp mispricing; single-factor R^2: 2Y swap 0.029 (direction-neutral), financials 0.27, vol 0.36, P/E 0.65.
- **Nordea forward carry flies (17 Jan 2024; 12 Aug 2025)**: receive 1y2y/3y2y/5y2y 6s fly at -8bp, target -25 + roll, stop +5, carry/12m 79.2, 1y realised vol 46.5bp, carry/vol 1.70,
  1y correlations 0.42 to 5s10s30s fly, empirical in-the-money rates 100/59/75/76% vs prior 1y/3y/5y/10y, PCA par -7.3 vs fair -34.7. Strategy table (annualised carry+roll, 50d vol):
  2s5s10s 6s -41.3 / 62.4 / 2.6 / ...; 10s20s30s 20.7 / 1.7 / 0.2; 5s10s30s 23.0 / 16.6 / 0.9. Paid 20y did not rise as expected when 10s30s steepened and two paid-belly flies
  struggled (opened 7 May 2025 @ 45.5, target 60, stop 35). Select carry flies with opposite-sign correlations to curvature and 10s30s.
  PCA residuals of ~1bp are "very moderate/weak" (Nordea, EUR Rates Flash, 23 May 2019).
- **Euribor microflies** (Clarus sign: 2*belly price - wings, positive = belly rich; buying = long belly) (rows 2nd-11th): 2.00, 4.50, 4.50, 4.50, 3.50, 3.00, 1.50, 0.50, 1.50, -0.50bp; buy cheap 9th/11th, sell rich 3rd/10th; buying all cheap and selling all rich
  pays away the edge in bid/offer; sit on hands around central bank and inflation releases (Clarus, A Dummies Guide to Trading IRS, 19 Jun 2024).
- **Fly vs vol (EUR)**: conditional daily correlations with vol (vol-up / vol-down since early March): 2s5s10s +0.09/~0; 2s5s30s +0.54/+0.65; 2s10s30s +0.16/+0.17; 5s10s30s +0.56/+0.65;
  "only the relationship between vol and the 5s10s30s fly has been economically meaningful in our post-GFC sample" (Citi, European Rates Morning Call, 12 Aug 2026; European Rates Weekly, 17 Mar 2022).
  Receive 3m-forward 5s10s30s EUR fly at 41bp, target 20, stop 50; a 2y-forward version stopped 22.3 -> 26.

## 6. Other fly records
- **USD 2s5s10s fly as a hedge for short Blues convexity (Citi, 9 Feb 2017; closed 6 Jun 2017)**: regress the target on swap rates and read the fitted combination as a weighted fly:
  `CA = 9.7 + 20.6*(-0.705*2y + 5y - 0.465*10y)`; earlier (13 Jan 2017) 10.2 + 21.4*(-0.73*2y + 5y - 0.47*10y), later (6 Jun 2017) 10.2 + 21.4*(-0.70*2y + 5y - 0.46*10y). Pay the belly notionals $147mm / -$85.6mm / $20.89mm at -18.2bp,
  closed at -16.5bp with CA 8.8 -> 6.6bp, ~+$500k net. The CA-vs-steepener hedge breaks down at the ZLB. Size the hedge from the regression, not from DV01 neutrality.
- **Receive 3m-forward 5s7s12s (Jan 2017)**: -7.2bp -> -8.3bp (2 Feb) -> closed -9.3bp, +$310k; "one of the cheapest" flies, 1m z -1.72; risk bear flattener (Citi, Going nuclear; Swearing in huge expectations).
- **UST 10s vs 7s/30s (buy 10s)**: -18.6bp open, -10bp on 17 Jan 2019; 10y had cheapened ~27bp on the fly since Sep 2017 vs ~30bp in the 2013 taper tantrum (Citi, The rocky road to a steeper curve; What to expect when you're expecting a turn).
- **USD 10s20s30s**: closed long-belly PCA fly 57 -> 48 (+$220k); open equal-weight cash fly 30k DV01 at 56bp, target 35, stop 70 (Citi, 17 Feb 2023); cash flies stopped twice -$166k, -$190k later.
  Flow regression R^2 98%, SE 0.5bp, 20s rich; conditional-payer-fly expression premium-neutral, 50% risk vs belly (J.P. Morgan, For cheap gamma, look to the long end, 23 Aug 2019).
- **USD long-end forward fly (Citi, 15 Jun 2020)**: receive 20y10y vs pay 10y10y/30y10y to fade 30y cheapness vs 40y; entered late Feb 2020 at 16bp; max P&L in the March 2020 dislocation but could not exit; unwound at 10bp
  when costs returned to ~3bp for $360k; preferred over a long-end steepener for smaller convexity risk.
- **USD 3y-forward 5s10s30s** (long belly, 20k DV01): 26.9bp -> 15bp, target 12, stop 37, +$165k; biggest risk further 10s30s flattening; behaves as short vol (Citi, US Rates Weekly, 2 Oct 2026).
  Barclays: pay belly of 5s10s30s SOFR 1:2:1 on Treasury long-end purchases reallocating term premium into the 10y (Global Rates Weekly, 2 Oct 2026).
- **AUD 1y-forward 2s5s10s**: receive at 9bp, target -11, stop 16 (Citi, Global Macro Trade Ideas Radar, 13 Aug 2026); leg sizes as published in DV01 terms (-100k/+100k/-100k).
- **OAT credit fly**: short 10y OAT vs OLO and DSL at 76.5bp, target 91.5, stop 69: -9bp; positioning overrode valuation (Citi, Radar, 13 Aug 2026).
- **SONIA 3s5s7s fly (pay belly, 5 Sep 2024)**: entry -12bp, target +10, stop -21, carry -1.4bp/3m vs a steepener; driver mortgage paying vs bank structural-hedge receiving.
  UKTi 2032/36/47 barbell long wings: pick-up 14.8bp, target 5, stop 20 (BofA, UK Rates Viewpoint, 5 Sep 2024).
- **Bond flies, closed UST (12M)**: 50:50 2s/5s/10s belly-cheapening +4.9 and +3.7bp; 64:11 3s/10s/30s -18.3; 88:25 3s/5s/20s -7.9; open: long Bund Aug52 vs Aug46/Aug54 (50/100/50) hedged with a 33% 10s/30s steepener;
  short OLO Jun36 vs OAT Nov35 and Bund Feb36 (50:100:50) at 20.3bp (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026). Regression-weighted UST cash fly 11/2021-2/2025-11/2027 showed the 2/2025 CTD cheap vs neighbours (Credit Suisse, UST Futures Focus, 28 Sep 2009).
- **UST auction grids** (BofA, US Treasury auction primer, 8 Mar 2024): matrix of entry lag (-9..+7 days) x exit lag (-7..+9), cell = average bp, SD, hit ratio, Sharpe = average/SD, Score = hit ratio x Sharpe; long-belly 2s5s10s
  entry -9 days average +1.9 to +4.8bp, hit up to 67-75%, best Score 49% at entry -3/exit -1. 12 observations per cell, regime-sensitive.
- **Inflation fly (ZCIS 5s/10s/30s)**: long 5Y 50% risk, long 30Y 50%, short 10Y 100% risk; combined with a 5Yx5Y long equals a 30Y long; "low-beta medium-term expression". Fly regressed on belly level (6M, EUR HICP): 2s5s10s beta -56.62, R^2 0.78,
  residual 8bp (z 1.4): 5y belly 8bp rich (inflation usage: a high breakeven is "rich", the opposite naming to a nominal yield) (J.P. Morgan, Monthly Inflation Outlook, 13 Aug 2026).
- **Sparse basket** (US swaps 1998-2005, 200-day windows re-estimated every 50 days): k=3 weights 3Y -0.288 / 4Y 0.806 / 5Y -0.517; mean-reversion half-life ~1 day not significant (d'Aspremont).
- **Residual-fly results** (USD swaps, PCA residual pattern, n = 750, p = 4): Sharpe by tenor 2y 0.4, 3y 1.4, 5y 1.2, 7y 2.2, 10y 0.8; the 7y residual mean-reverts on mortgage-servicer hedging; ex-post, no costs (Burton, Dektor, Wheeler, c.2008).
- **Curvature measures** (Salomon, Ilmanen and Iwanowski, Part 7, Feb 1996): Curvature A = 3y zero yield - duration-matched barbell 0.5 x 3m zero + 0.5 x 5.75y zero; Curvature B = 10y OTR - duration-weighted 2y/30y OTR barbell.
  1968-95 returns: bullets beat barbells (4y bullet 9.14% vs 3y/5y barbell 9.05%, 2y/6y 9.00%, 1y/7y 8.87%): the risk-premium curve is concave in duration.
  1 Sep 1995: sell 10y par (6.94%) vs 30y (6.67%) + 1y (5.73%), weights 0.53/0.47, yield give-up 71bp; convexity-adjusted 51bp; breakeven an 11bp 10s30s narrowing or a 138bp parallel shift (Part 5, Sep 1995).
  Break-even changes implied by forwards are a cheapness indicator; a flattener in a concave curve carries negatively and can lose even when the direction is right.

## 7. Conditional-fly diagnostics that also apply to linear flies (structuring in curve-conditional-trades)
- Weights wing/belly/wing in notional, wings struck ATM, belly strike solved for zero cost: USD 3m 2y10y30y 220.1/100/22.2 (2023); 3m 3y10y30y 159.3/100/19.6; 3m 10y20y30y 92.1/100/36.1; EUR 3m 2y10y30y 250.3/100/17.5; EUR
  10y20y30y 80.1/100/40.7 (2026) (Citi, Rates Vol Lab, Forward steepener and vol divergence, 12 Jun 2023; Fading vega dislocations, 5 Oct 2026).
- Metrics: forward fly vs belly correlation (3m changes, 1y levels; e.g. 5s10s30s 34% in changes, 92% in levels), rich/cheap from a 1y levels regression (bp, z), percentile since 1990, belly OTM distance, curve/vol/total pick-up, 3m roll
  (Citi, Buying vol for less, 25 Sep 2019). Rates-fly/rates decorrelation is the main risk of trades built on fly-vs-belly correlation.
- Implied directionality = `1 - 0.5*(sigma_L + sigma_R)/sigma_body`; delivered = 3M beta of the 50:50 fly vs the body; weighted version body weight `(sigma_L + sigma_R)/(2*sigma_body)`. EUR examples: 2s5s10s implied -4%, delivered 5%,
  body weight 104%; 10s20s30s implied 6%, delivered 12%, 94%; 2s10s30s implied 16%, delivered 21%, 84%. The closed-form strike shift is exact only with zero skew (J.P. Morgan, A primer on Conditional Trades, 26 May 2016).
- Option BPV weights (underlying BPV x delta) not PCA weights, because directionality is wanted; screen R^2 of the directionality regression against premium pick-up; in JPY only 7s10s20s (R^2 ~0.84, +0.5bp) and 5s10s20s (~0.55, +1.3bp) had positive pick-up (Huggins and Schaller, 2024, Ch.19).
- Vol fly (1x2x1 across tails at fixed expiry): 3y vols 80.4/70.1/63.3 -> `2*70.1 - 80.4 - 63.3 = -3.5` (table -4.0, unrounded vols), z -1.9 since 1999, forward-curve model fair +5 normals; trade sell $230mn 3y2y / buy $100mn 3y10y / sell $21mn 3y30y straddles, vega-neutral
  (Citi, Gamma and Vega RV, 14 Jan 2019). Fair value is pushed to extremes by funding-driven curve flattening (late 2008).
