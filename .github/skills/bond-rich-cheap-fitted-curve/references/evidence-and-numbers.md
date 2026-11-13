# Evidence, benchmarks and worked numbers (reference)

Linked from [SKILL.md](../SKILL.md). Every number is a published observation, not a current market level. Use them to
sanity-check your own fit (is my RMSE in the right range, is my OTR spread plausible) and never as live inputs. "Chart read" =
read off a chart by the note-taker, so approximate.

## 1. Fit quality and curve dispersion (RMSE)

RMSE of yields to the fitted par curve is the standard dispersion / liquidity gauge (J.P. Morgan, Times like these, 10 Feb 2016).

| Observation | Number | Source |
|---|---|---|
| Normal range, UST par-curve RMSE 2010-16 | ~1-3.5bp; crisis peak ~16bp | J.P. Morgan, 10 Feb 2016 |
| New par-curve model, off-the-run RMSE (Jul 2013-Jul 2018) | ~0.7-2.3bp | J.P. Morgan, 16 Jul 2018 |
| Removing very-low-free-float bonds | YTD avg RMSE 3.8bp to 2bp; std 0.66 to 0.21bp | J.P. Morgan, 23 Jul 2024 |
| Benchmark-maturity knots | -0.2bp RMSE, std -0.08bp | J.P. Morgan, 23 Jul 2024 |
| 6 to 12 knots | about -0.5bp RMSE | J.P. Morgan, 23 Jul 2024 |
| Net change vs legacy | avg RMSE -2.5bp (-65%), std -0.56bp (-85%) | J.P. Morgan, 23 Jul 2024 |
| Mean absolute residual, Bund fit 7 Dec 2012 (cubic spline, 13 knots) | 0.9bp (9 cents); extremes +2.3 / -2.2bp | Huggins & Schaller 2024, Ch.8 |
| Spline liquidity indicator, UST 7-15y (chart read) | typically 1-2bp; 4-5.5bp in 2010-11; ~9bp spike 2019; ~4.5bp Mar 2020 | Düring 2021, Ch.18 |

RMSE by maturity bucket, new model, last / average / percentile / std (J.P. Morgan, 23 Jul 2024): 0-2y 0.9/1.2/13%/0.3;
2-3y 0.8/1.1/27%/0.3; 3-5y 1.1/0.9/63%/0.2; 5-7y 2.1/2.3/17%/0.2; 7-10y 1.6/2.3/20%/0.6; 10-20y 1.5/1.4/71%/0.5; 20-30y 1.3/1.1/92%/0.1.
The legacy model showed 12.4bp last at 0-2y (average 23.1): a basket artefact, not market stress.

Knot-count overfitting test: shock 5% of bonds with N(20,5) price noise, re-estimate, measure the % change in curvature
(absolute second differences at maturity points). Curvature jumps between 15 and 20 knots (J.P. Morgan 2024).

Drivers of UST RMSE (weekly regression, last 4y, R² 76.9%): `RMSE = -0.0033·|PD positions $bn| - 0.0016·depth($mn) - 0.0005·ΔCB balance sheet 6m ($bn) + 0.02·GCF/OIS spread (bp) + 2.35`.
A $100bn drop in dealer inventory adds about 0.3bp to RMSE (J.P. Morgan 2016). Bid-offer can look fine while spline dispersion
deteriorates: treat the divergence as information (Düring 2021, Ch.18). The UST 7-15y bid-offer has an effective floor around
0.04bp from 1/256 price ticks; euro bonds use 1/1000 steps.

Sector RMSE (10-15y, 15-20y, 20-25y, 25-30y) is where buyback benefits show up, not in outright yields; stylised buyback score =
1y z-score mix of offer-to-max ratio, sector spline RMSE and the off-the-run discount (J.P. Morgan GFIMW, 21-22 Aug 2026;
Barclays, Swap spreads: the Bright Spot in US rates, 30 Sep 2026). Aug 2026: 10-20y -0.8, 20-30y +0.4, near 1y averages.

## 2. Law-of-one-price rich/cheap and replication

Tuckman & Serrat (Fixed Income Securities, 4th ed., 2022, Ch.1), UST 14 May 2021, T+1 full ask prices. Discount factors:
d(0.5)=0.999923, d(1)=0.999419, d(1.5)=0.998504, d(2)=0.997041, d(2.5)=0.994558, d(3)=0.990195, d(3.5)=0.984742.
Rich(+)/cheap(−) per 100 face = market price − PV:

| Bond | Rich(+)/cheap(−) |
|---|---|
| 2.0s Nov-21 | +0.0030 |
| 8.0s Nov-21 (issued 1991) | +0.0984 |
| 1.75s May-22 | +0.0017 |
| 7.625s Nov-22 (issued 1992) | +0.1172 |
| 1.75s May-23 | −0.0026 |
| 2.75s Nov-23 | −0.0123 |
| 2.5s May-24 | +0.0508 |
| 7.5s Nov-24 | +0.2314 (< 0.2% of price) |

Old high-coupon bonds were rich (investors paying up for income at low rates), the reverse of the older "old = illiquid = cheap"
pattern. Replication arbitrage for the 7.625s 11/15/22: short 100 face at 111.3969, buy 2.90281 of the 2.875s 11/15/21,
2.94454 of the 2.125s 5/15/22 and 102.97582 of the 1.625s 11/15/22 (cost 111.2797). Cash flows match on each date (3.8125, 3.8125,
then 103.8125). Net 0.1172 per 100 = $586,000 on $500mm before bid-ask (screens show asks), repo or borrow cost and idiosyncratic
demand. **Not an arbitrage in practice.** Bond spread of that bond: −7.27bp (forwards 0.0154%, 0.1008%, 0.1833% give PV 111.2797);
high-coupon Treasuries were rich by −0.8 to −18.9bp on bond spread. P&L attribution 13 Nov 2020 to 14 May 2021 (realised forwards,
no financing): start 114.87654 at spread −1.16bp; carry-roll-down −3.76099; rates +0.18292; spread −1.16 to −7.27bp worth +0.09843;
cash carry +3.81250; total +0.33286 (0.2898%).

STRIPS: C-STRIPS are fungible across bonds, P-STRIPS can only reconstitute their own bond, so P-STRIPS inherit the parent's
richness. All maturing 15 May 2030: C-STRIP 85.9453, P-STRIP of the 0.625s 86.8549, P-STRIP of the 6.25s 87.0412; P−C up to 1.91 per
100 at 18.5y (Tuckman & Serrat 2022, Ch.1).

## 3. Regression-based fit: Bund, 7 Dec 2012 (Huggins & Schaller 2024, Ch.8)

Universe: coupon Bunds, OBLs, Schatze, excluding < 1y. Cubic-spline knots 0, 0.5, 1, 1.5, 2, 5, 7, 10, 12, 15, 20, 30, 35y.
Regressors: time since issuance, issue size, deliverability into Mar-2013 Schatz/Bobl/Bund/Buxl. Results: size +2.5 cents per extra
EUR 1bn; age −2.7 cents per year (older cheapens); deliverability premium Schatz 3.6bp, Bobl 2.8bp, Bund 2.1bp, Buxl 2.4bp
(deliverables yield 2-4bp less; Schatz largest because Schatz deliverables have small BPVs). One residual below −2bp, two above +2bp.
10y Bund ESTR-ASW fair value = −16bp (unsecured-secured basis) + 15bp (adjusted German CDS) − 6bp (average specialness) = −7bp.
Expected specialness premium by maturity (German, chart read): ~0.1bp 1y, 0.3 2y, 0.7 3-4y, ~3.0 5y (Bobl deliverable), ~5.9 10y
(Bund deliverable); Italian ~2-2.5 at 5-10y; French ~1.0-1.3; Dutch ~0.6-0.8; Spanish ~0-0.5 (Huggins & Schaller 2024, Ch.12).

Global fitted-curve RV 17 Oct 2023 (bonds asset- and basis-swapped into EUR, annual coupons, fitted through Bunds only): USTs pick up
about 20bp at 1y and 45bp at 5y over Bunds; Gilts roughly −24 to +37bp; Bunds ±5bp around zero (chart read). Idea: sell long
Bunds vs buy USTs or Gilts, both asset-swapped vs SOFR, if the imbalance is judged ephemeral (Huggins & Schaller 2024, Ch.17).

## 4. On-the-run / off-the-run (US)

Yield-error spread vs the nearest on-the-run (avg 2016 / 2014-16 / 2010-16, bp; old, 2x-old, 3x-old), positive = off-the-run cheap
(J.P. Morgan 10 Feb 2016):
2y 1.5/0.8/0.6; 2.7/1.0/0.9; 3.4/1.2/1.1. 3y 1.0/1.0/0.6; 2.2/1.4/0.9; 2.4/1.9/1.3. 5y 0.4/1.2/0.6; 1.7/1.9/1.1; 2.3/2.4/1.5.
7y −0.1/0.4/0.2; 0.5/0.8/0.4; 0.6/1.1/0.6. 10y 2.0/1.6/1.9; 2.6/2.3/2.9; 3.0/2.7/3.5. 30y 0.7/0.7/0.6; 1.3/1.3/1.1; 0.7/1.5/1.3.

Roll cycle (5y, avg of last 12 cycles): OTR outperforms the old 5y by ~0.8bp in the 2 weeks after auction, then cheapens ~0.7bp in
the 2 weeks into the next auction. Monthly 2/3/5/7y issues cheapen most off-the-run; 10s/30s opposite (reopenings dilute the OTR
premium). Roll trading ranges (max−min over the cycle; 5y avg / 2y avg bp): 2y 1.62/2.46; 3y 1.34/1.51; 5y 1.21/1.54; 7y 0.97/0.93;
10y 1.79/1.57; 30y 0.94/0.72. May 2000 to May 2002, four semiannual cycles: the OTR 5y cheapened about 5bp vs the old 5y in the 1.5
months before the next auction (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005, Ch.6).

Convenience-premium evidence, 1997-2022 (Fleckenstein & Longstaff, Treasury Richness, J. Finance, 2023): average premium 8.21bp;
bills 24.51; ≤1y 17.22; 30Y bonds −2.12; 20-30y bucket −10.06; 20Y bonds in the 10-20y bucket −38.53 (structurally cheap); 5Y 12.61;
10Y 12.20; 36.86% of estimates negative; richest security a bill in 59.29% of months, cheapest a 30Y bond in 54.49%. OTR spread
1997-2007 vs 2008-2022: 2Y 1.742 to 0.660; 5Y 3.394 to 0.609; 10Y 4.613 to 1.705; 30Y 7.506 to 0.279; all 3.725 to 0.610. So the OTR
premium largely disappeared after 2008 (10y the exception). Maturity-crossing: premium falls significantly when notes age through
2Y (−0.339, t −2.98), 5Y (−0.420), 7Y (−0.541), 9Y (−0.571), 10Y (−0.839) remaining maturity; interpreted as fund-mandate buckets.
Age effects: 2Y notes cheapen in year one; 5Y cheapen then richen after ~1y; 10Y richen ~2 years after issue. Money-market-fund
eligibility (max maturity 397 days; WAM limit 60 days since 30 Jun 2010) drives a jump around 13 months: 2M bucket 29.29bp vs 13M 6.68bp.
Shocks (VIX, funding, NFCI) show no reliable pattern; changes mean-revert within a month.

Off-the-run trading costs (Federal Reserve FEDS 2025-049, 7 Jul 2025; Jan 2018 to Jun 2024; effective bid-ask EBA = 2|P_trade − P_fair| / dollar
duration): median 0.37bp vs indicative 0.68bp; 95th percentile 6.22 vs 4.16. Trades < $50mm median 0.32; > $50mm median 0.62, 95th
percentile 12.41. A just-off-the-run bond: 1bp indicative spread ≈ 0.73bp effective. Indicative spreads overstate costs of
seasoned bonds, so liquidity premia built on them are inflated.

Specialness cycle (10y OTR, 51 notes, Nov 2008 to Jul 2021, Tuckman & Serrat 2022, Ch.10): special spread (GC − special repo) peaks at
156bp the day before the first reopening (2-sd band 116-196bp; 85bp at 13 days before), 48bp before the second reopening, < 20bp
before the next new issue; March 2020 saw negative specials. Overnight specials 27 May 2021 (bp, 2y/3y/5y/7y/10y/20y/30y): OTR
5/1/13/9/3/2/4; old 2/2/2/1/11/2/12; double-old 2/10/6/8/10/2/3; triple-old 2/12/2/3/3/2/2. Fails charge since May 2009 =
max(0, 3% − fed funds). Unscheduled reopening of a matching old issue: modest richening of the old off-the-run, less special risk
(BofA, US Treasury auction primer, 8 Mar 2024).

Leveraged on/off-the-run (Conks, Demystifying the Repo Market III, 28 May 2024): long $100m OTR financed at 5.75%, short $100m
off-the-run at 5.55% reverse repo (20bp to the dealer), closed after about a week, ~$2m banked; zero haircut means no cash, 2% haircut
means $4m on $200m gross.

## 5. Futures / CTD and basket effects

- Bonds richen when they become CTD and cheapen when they fall out of the basket; years-from-CTD bonds are bought vs matched swaps
  (BofA, US Treasury futures and basis primer, 10 Jul 2025).
- CTD premium vs fitted curve: expected 0.6-1.2bp (median vs mean); CTD usually starts rich and cheapens through the roll; a note
  nearer first notice day is less rich (Citi, Fixing the plumbing, 30 Sep 2019: Nov-26s and Feb-27s about 1.25bp rich with ~100 days to
  roll; no formal trade). Two-year CTD 8 May 2019: current CTD ~1.3bp rich vs fitted, next ~0.3bp rich (Citi, Deal or no deal, 10 May 2019).
  CTD-slope regression on 1s2s: R² 0.155 (Citi, Futures roll Sep26-Dec26, 18 Aug 2026). CTDs often trade at negative OAS to the
  fitted Treasury curve (Treasury Borrowing Advisory Committee, 30 Jan 2024).
- Basket exit (Citi, The long end basket case, 4 Feb 2015): CME removed the 5.375% Feb-31 (free float $16bn), the CTD jumped from the 6.25% May-30
  to the 4.5% Feb-36; the 2/36 vs 5/30 ASW differential moved ~12bp; May-30 was 3.9 sd cheap to a regression on the 10s30s ASW slope
  (R² 0.648), a sector-versus-idiosyncratic test. The Fed held ~51% of May-30s (small float).
- CTD richness in stress, 2020: yield spread of a comparable non-deliverable minus the CTD, low and stable until early March then
  volatile (axis −2 to 18bp): CTDs inherit the liquidity of their future (Tuckman & Serrat 2022, Ch.11).
- JGB: structurally rich futures; the 7y CTD was the most expensive NS-spline point 2009-13 (mean about −2.5 to −3bp); after 2015 the CTD
  spread vs bonds 1y either side was mostly −2.5 to −5bp (chart read) (Düring 2021, Ch.28).
- A rich bond is a crowded, squeezable short: 1986 squeeze of the 9-1/4% 2/15/2016 traded 25-40bp through the 12% 2013-08 in April and
  over 100bp in May; the basis widened about 6 points ($60,000 per $1mm) (Burghardt et al. 2005, Ch.6).

## 6. Screens and trades quoted in research (illustrative, not recommendations)

- US screen (Goldman Sachs, US Treasury RV Report, 25 Sep 2026): flag fitted-curve spread with 3m z |z| > 2 (z < −2 rich, z > 2 cheap).
  Examples: 7y CTD fitted −0.8bp (z −2.2, rich); 20y CTD +2.1 (z 2.9, cheap); 10y 3.875 Aug-33 z −4.1 (rich); long P-STRIPS fitted
  −7 to −11bp but z only −0.5 to −1.3 (persistently rich: level matters less than z). ASW definition gap: P-STRIP MMS 69.9 vs proceeds
  ASW 122.6; 1.25% May-50 MMS 69.6 vs proceeds 91.6.
- Treasury RV monitor (Citi US Rates Weekly 2015-2020): per maturity bucket, the 3 richest/cheapest issues by coupon-adjusted spread
  to the fitted curve and separately by ASW, each with 3m median and 3m percentile (e.g. 2.25% Aug-46 ASW 17.8bp vs 3m median 8.3,
  100th percentile, 18 Jan 2019).
- Euro auction dashboard (Citi, European Rates Morning Call, 12 Aug 2026): 3m z of yield, vs fitted curve, vs surrounds (fly against
  neighbours), vs closest-rated peer, and ASW-type spread. 11 Aug 2026: DBR 1% May-38 vs fitted −1.45 (rich), vs surrounds −0.96;
  DBR 1.8% Aug-53 vs fitted +1.05 (cheap).
- Euro benchmark discount (J.P. Morgan GFIMW, 21-22 Aug 2026): benchmark discount = benchmark yield − yield interpolated from
  surrounding bonds (z-spread); benchmark roll = z-spread pick-up over the off-the-run benchmark; judge vs 12M or since-issue average.
  OLO Aug-31 0.9bp vs 12M avg ~1.6 (dear); Schatz Sep-28 5.1 vs ~3.3 (cheap); new 10Y BTPs historically in line or modestly cheaper
  than the OTR discount. 15y German sector dear on fly regression `10s/15s/30s = −0.11·(10s/30s) − 2.92·15Y + 20.90` (R² 86%, 2y).
- BTP fitted-curve anomaly screen (Astor Ridge, Trade Radar, Mar 2022): buckets by coupon (high/low/medium) with max bond age 2y;
  "sell the old Jul-28 BTP to buy the cheap CTD"; Italy fly −Jul28/+Apr31/−Dec31 weighted 0.4/2/1.6 at 6.35 (from about −3 to 9.5); cross-issuer
  switch FRTR 0.5% 2040 into BGB 4.25% 2041: spread 12.87 vs mean 0.26, sd 2.16 (5.84 sd, 99.2 percentile), daily vol had spiked.
- JGB macro fair value (J.P. Morgan Japan FI Weekly, 21 Feb 2025): 10y JGB on 3Mx3M OIS, 10y UST and BoJ share of the three newest 10y
  JGBs, 2y rolling, R² 92.3%, SE 7.0bp. Residual +10bp (cheap), peak ~+15bp mid-2024. Not faded because expectations were repricing,
  long-end flatteners pressured the belly, positioning was light and event risk asymmetric.
- Gilt low/high coupon switch (BofA, Liquid Insight 10 Nov 2022; UK Rates Alpha 5 Aug 2024; UK Rates Viewpoint 5 Sep 2024): sell UKT 4.125% 2027 /
  buy UKT 0.125% 2028 as spread of OIS z-spreads (low minus high), entry +1.8bp, target −25bp, stop +12bp, closed −25.4bp (target hit,
  Aug 2024). The 0.125% 2028 had the highest net yield (3.40%) after 40% tax (5bp tax on a 12.5bp coupon, equal to a 5.7% gross
  deposit rate). Scarcity: four 1/8% gilts at entry, two by Aug 2024; the BoE's 29 Jul 2024 short-gilt sale bought GBP606mn of 0.125%
  2028 out of GBP800mn. Next (5 Sep 2024): sell 4.5% 2028 / buy 0.5% 2029 on z-spread, entry −8bp, target −20bp, stop +4bp. Gilt sub-6y
  z-spreads span −60bp (0.25% 2025) to +20bp (4.125% 2029): low coupons sit far lower. Risk: new issue accrues benchmark premium,
  change in retail tax. UK retail holdings are tiny (GBP4.6bn end-Q2 2022, ~0.2% of the market; GBP3.1bn Q1 2024), so scarcity, not
  retail demand, is the better explanation.
- Seasonal linker richness (BofA, 22 Jul 2025): April-2032 TIPS looked rich on seasonally adjusted real yield at 6.75y because the
  issue is tiny ($5bn, never reopened): "we would not regard this richness as an RV opportunity". TII 2.5% Jan-2029 z-spread +31.2bp
  (cash dirty 156.247 vs PV 157.893 at flat SOFR). UK linker barbell 2032-36-47 weights +43.8%/−100%/+56.2%, pick-up 14.8bp,
  target 5bp, stop 20bp.
- Expected-return table, 26 Sep 1995, 3m horizon (Salomon, Understanding the Yield Curve Part 6): OTR yields 3y 5.978, 10y 6.261 vs
  model par 6.011, 6.408; financing advantage 0.038 (3y) and 0.463 (10y); spread to par curve −0.008 and −0.037 (÷4); expected
  cheapening −0.068 and −0.401. Local rich/cheap: 3m bill −0.015, 3y −0.039, 10y +0.025; total expected return 1.334/1.456/1.499
  (bill/3y/10y). The 10y's repo advantage outweighs its richness and expected cheapening.
- Forward-rate cheapness (Salomon, Understanding the Yield Curve Part 1, May 1995): 2 Jan 1990 par yields within 25bp but 3m forwards
  spanning ~200bp; 6y and 12y cheap (high forwards), 4y and 9y rich; buy 12y / sell 9y; the cheap sector richened over three months.
  Low long-end forwards reflect convexity bias, so adjust before calling a long sector expensive.
- Cross-sectional level regression for rich/cheap from PCA on changes (QF Stack Exchange #18301, Jun 2015): PCA on changes, cumulate
  factors, regress levels on cumulated factors, test residual stationarity, buy the most positive residuals. Alternative: level PCA for
  rich/cheap, change PCA for risk (see [curve-pca-factor-model](../../curve-pca-factor-model/SKILL.md)).
- Two-bond CMT trade (RiskVal 2021): buy 0.375 Nov-25 (2 SD cheap to the CMT curve), sell 2.75 Aug-25 (0.5bp cheap, 0.2 SD rich); carry+roll
  9.9bp vs 9.8bp; CMT residual spread 2.7 SD cheap, direct yield spread 1.8 SD cheap: "trade the yield spread", the residual is theoretical.
