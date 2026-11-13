# Worked tables for z-score and percentile screens

Extra numbers behind [SKILL.md](../SKILL.md). All figures are from the cited documents (sell-side screens are
backward-looking and illustrative, "not necessarily trades that we would recommend"). Sign: z > 0 = level high vs its
own history unless a row says otherwise.

## 1. Long-dated forward-curve screens: multi-lookback z, carry and BE/RV
Columns: curve (bp) / 1y z / 3y z / since-2000 z / 1y carry (bp) / daily breakeven (bp) / BE/RV. BE = daily move in
rates whose convexity gain offsets negative daily carry (0 if carry positive); RV = 1y realised daily vol; for a
long-convexity flattener a *low* BE/RV is cheap convexity, for a short-convexity steepener you want BE/RV well above 1.

| Close | Curve | Curve | 1y z | 3y z | 2000 z | Carry | BE | BE/RV | Source |
|---|---|---|---|---|---|---|---|---|---|
| 8 May 2019 | USD 10y5y/15y15y | -10.1 | 2.50 | 0.19 | - | -2.91 | 3.5 | 1.07 | Citi, Trading long-dated convexity, May 2019 |
| 8 May 2019 | USD 15y5y/20y10y | -11.3 | 1.16 | 1.01 | - | -0.31 | 1.3 | 0.42 | same |
| 8 May 2019 | USD 20y5y/25y10y | -9.1 | 1.95 | 0.87 | - | +0.13 | 0.0 | 0.00 | same |
| 4 Dec 2019 | USD 15y5y/20y10y | -12.54 | -0.91 | 0.70 | 0.64 | -2.09 | 3.33 | 0.80 | Citi, Taking profits on 15y5y/20y10y flatteners, Dec 2019 |
| 4 Dec 2019 | GBP 15y10y/25y5y | - | 0.78 | 1.61 | 1.86 | +0.54 | 0.00 | - | same |
| 24 Sep 2019 | GBP 15y10y/25y10y | -3.32 | 2.10 | 2.35 | 2.44 | +0.91 | 0.00 | - | Citi, Buying vol for less, Sep 2019 |
| 26 Mar 2020 | USD 15y5y/20y10y | -5.21 | 4.21 | 3.58 | 1.02 | +0.11 | 0.00 | - | Citi, Liquidity, vega, and convexity, Mar 2020 |
| 17 Jan 2020 | GBP 15y10y/25y10y | - | -0.01 | 1.15 | 1.84 | +0.52 | 0.00 | - | Citi, In search of cheap vol, Jan 2020 |
| 8 Jun 2023 | USD 10y10y/15y15y (steepener) | -51.5 | - | -0.91 | -2.07 | 6.89 | 6.18 | 1.17 | Citi, Forward steepener and vol divergence, Jun 2023 |
| 8 Jun 2023 | USD 15y5y/25y10y (steepener) | -94.1 | - | -1.11 | -2.58 | 1.66 | 2.29 | 0.49 | same |

Reading: in Jun 2023 the best-carry steepeners had the worst entry level; BE/RV 0.49 is too low for a short-convexity
steepener, so 10y10y/15y15y and 20y5y-10y10y were the frontier picks (20y5y preferred on 3y z). Cross-market BE/RV
ranges (Jan 2020): GBP 0.00-0.89, USD 0.46-1.08, EUR 0.60-1.48, CAD 0.45-1.82, JPY 0.76-1.50. Always divide BE by *each
market's own* realised vol: JPY realised 2.4-3.1bp/day vs ~3.9-4.7 elsewhere (Citi, In search of cheap vol, Jan 2020).
Backtest Sharpe by pair (yearly roll, 25bp delta hedge): 0.05 to 0.35 (10y10y/25y10y best): screens rank cheapness,
not realised returns (Citi, Trading long-dated convexity, May 2019).

## 2. Percentile-bucket forward-outcome tables
| Signal and outcome | Bucket results | Source |
|---|---|---|
| 3m change in 3m10y 25bp RR; next 1m change in 10y (2006-2016) | <25th: avg -11.5bp / median -5.0 / 36% up; 25-50: -2.1/-1.1/48%; 50-75: +0.2/-4.2/45%; >75th: +8.8/+11.1/69% | Citi, Flatter skew warning, Jan 2017 |
| 6-week-ahead projected supply (DV01) terciles; next 1w change in 10y (median/avg/% rally) | 0-33rd -3.3/-2.1/63%; 33-66th +1.4/+1.6/47%; 66-100th +1.5/+1.2/46%. Next 2w: -2.3/-1.1/61%; -0.4/+0.8/52%; +1.8/+1.3/46% | Citi, What to expect when you're expecting a turn, Apr 2018 |
| 2s10s decile (Apr 1988/89-Apr 2017), flattener hit ratio | bucket 30-40 (~50bp): 0.66 (6m) / 0.74 (1y); median 13bp / 54bp. Bucket 70-80: 0.82 (6m), 0.73 (1y) | same |
| Fund PCA duration beta percentile, next 1m..6m 10y change less average (5y) | 80-90th pct: -17/-28/-43/-58/-65/-88bp (rally = follower); 10-20th: +19/+37/+43/+36/+35/+41 | BofA, Long UST outflows & dealer holding highs, Mar 2025 |
| Leveraged-fund percentile, next 1w..16w 10y change | 0-10: -1,-1,-1,-1,-2; 10-20: +4,+4,+5,+5,+5; 80-90: +2,+4,+4,+4,+5; 90-100: -1,-2,-1,0,0: noisy, not monotonic | BofA, Mixed UST positioning picture, Apr 2024 |

Rules that follow: use extremes, not middle buckets (mean and median disagree in the middle); say whether the indicator
is a *follower* (rates move with stretched positioning) or *contrarian*, bucket by bucket and separately for duration
and curve; tabulate against the unconditional average ("less the average move"); bonds show follow-through at positioning
extremes while equities mean-revert (Willer and Saunders, 2026).

## 3. Positioning z and percentile (decompose before reading)
CFTC non-commercial 5y z, 25 Feb 2020 (000s of 10y-equivalents): ED 616 (mean -326, sd 540, z 1.7; check
(616+326)/540 = 1.74); TU -91 (z -0.6); FV -145 (0.1); TY -306 (-0.7); US -126 (-1.1); WN -1891 (-594, 433, -3.0);
total -2056 (-1267, 920, -0.9). The aggregate -0.9 masks front-end longs vs record WN shorts that are a 25s/30s RV leg
(JPM, Canary in a coal mine, Feb 2020). Futures-roll positioning table: TY net longs 2595k vs 3y mean 1782k, sd 412,
z 2.0, 99th pct -> bearish roll; UXY 96th pct z 1.5 -> only mildly bearish; TU 28th pct z -0.5 (JPM, Bond Futures
Rollover Outlook, Sep/Dec 2026). Percentile does not map one-to-one to a call. Equity-style rule: asset-manager z < -2
IR 0.9 vs 0.5 unconditional (Willer and Saunders, 2026). COT data are as of Tuesday, published Friday: model the lag.

## 4. Swap-fly tables (Citi layout)
Equal-weight fly `-0.5 : 1 : -0.5` (receive the belly; positive = belly cheap) vs PCA-weight fly using the 3rd-PC loadings
over a 5y rolling window (e.g. 2-5-10 -0.43 : 1 : -0.62 in Jan 2019; 10-20-30 -0.24 : 1 : -0.79). Columns: level, 3m
carry+roll, 3m high/low, 1m/3m/6m z (12m for forwards), 3m correlation with 10s, 2s10s, 5s30s. 16 Feb 2023: equal-weight
10-20-30 level 5.7bp, z -1.61/-2.69/-1.60 (1m/3m/6m); PCA 10-20-30 8.9bp, z -1.60/-2.58/-2.22; 2-3-5 z 1.92/2.20/0.39
(Citi, Time for moderation, Feb 2023). Always read the correlation columns: equal-weight 10-20-30 (1:2:1) had 96% 3m
correlation to 5s30s vs 34% for the PCA version; equal-weight 2-3-5 was -89% correlated with 2s10s (Citi, The rocky road
to a steeper curve, Jan 2019; Citi, Eat, pay, spend, Mar 2020). Correlate *changes*, not levels: 34% in changes vs 92%
in levels for a forward fly vs its belly (Citi, Buying vol for less, Sep 2019). 6m PCA fly z -1.3 vs 50/50 fly -1.6 with
R2 to the belly of 65.4% (BofA, Understanding the yield curve dynamic, Jul 2025).

## 5. Residual z by lookback (persistence test)
UST PCA residual z for 2y/3y/5y/7y/10y/30y (BofA, Jul 2025): 1m -0.47/0.44/-0.79/0.65/-0.76/0.36; 3m 0.57/-0.40/-0.91/
1.24/0.02/-0.54; 6m -0.44/0.50/-0.41/0.03/-0.05/0.12; 12m -0.07/0.15/-0.42/0.21/0.20/-0.20. Only the 7y (cheap) and 5y
(rich) keep their sign across windows: trade those, ignore the rest. Swap-spread PCA (Citi, Short-End Notes, Aug 2026):
residuals within +/-0.5bp, 5y -0.5bp z -0.8 "slightly cheap" - weak. BofA swap-spread dislocation indicator: Germany DI 1.13,
UK/JP ~0.6, US ~0.3 at publication; backtest 2001-2016 no costs: Germany threshold 1.0 Sharpe 2.4, threshold 2.0 Sharpe
2.8; US 1.0 Sharpe 1.2, 2.0 Sharpe 0.4 (threshold behaviour differs by market) (BofA, A simple framework for swap spread
RV, Jun 2016). EGB dislocation (7 countries x 6 tenors, 11 PCs, 5-day hold, 2x threshold): cheap-leg (long) hit ratios 71%, 73%, 75% in
2015-2017 vs rich-leg (short) 71%, 55%, 50%; trade the cheap leg (BofA, Many EGBs, one simple value tool, Mar 2018).

## 6. Vol and convexity z grids
CA screen (Citi, Short Blues convexity, Feb 2023): H6-Z6 Blues CA 13.09bp, 3m z 0.99, 1y z 0.46; model 9.44; CA minus
model 3.65 with 3m z 1.27, 1y z 1.26. Jan 2017: Blues H0-Z0 CA 10.02bp, +4.61bp vs model, 3m z 2.66 (~3 sigma). The signal
is the z of the *model dislocation*, not the CA level (Citi, Swearing in huge expectations, Jan 2017). Switch ratios with
3m z: 6m10y/1y10y 0.95 (z -2.1); 3m2y/3m5y 0.71 (+2.1); 5y2y/5y10y 1.04 (-2.9) (Citi, Fair value vs seasonality, May 2017);
3m2y/3m5y and 3m2y/3m10y +4.3 and +4.0 3m z ("extreme") (Citi, Left-side vols' outperformance, Jun 2021). Vol PCA residual
3y2y/3y10y/3y30y fly -4.0 normals, z -1.9 since 1999 vs macro-model fair +5 (Citi, Gamma and Vega RV, Jan 2019).
Forward-vol frontier rows (vol-adjusted roll vs 1y z): 3m3m20y fwd vol 74.1nv, roll 29.75nv, Sharpe 4.17, 1y z 2.1 -> sell
(Mar 2020). Forward vols beyond a 1y start at 5y-window z -1.5 to -2.4 in Sep 2019 were not bought: cheapness was
justified (ELB, callable supply) (Citi, Fixing the plumbing, Sep 2019). Skew decile: 3m2y +/-50bp skew -23 abpvs at the
10-20% decile of 1y history (Rhodes, USD 3m2y Payer Skew Steepener, Oct 2025). Realised-vol window changes the
implied/realised read: a 1m window included the post-election spike (Citi, Year-Ahead: Bumpy road for vol, Dec 2016).

## 7. Cross-sectional scorecards
**FORTE** (10 G10 currencies, two-step sort): rank on 12m equity momentum (scorecard 3, 2, 1, 0.5, 0, 0, -0.5, -1, -2, -3);
re-sort top-4 and bottom-4 separately by `filter = equity score + sum of three 1y z-scores` (carry level, 1-week rates
momentum, 15-day contrarian value); long 2 highest of top-4, short 2 lowest of bottom-4. **OCTAVE**: `rank score = sum over
4 factors of (z_i + s_i)`, z = 1y z, s = rank scorecard; long top 3, short bottom 3. Track records are gross, hypothetical
(FORTE 54.0% hit, OCTAVE 52.8%). Factor relationships break (2011, 2013, 2017); rates-FX rank correlation peaks ~2 months
(BofA, FX Quant Primer, Oct 2018). **JPM FX multi-factor**: signals z-scored cross-sectionally, trimmed at +/-2, weekly
rebalance, hold top 5/bottom 5 (JPM, FX Markets Weekly, Aug 2026). **Duration/country rank**: overweight top-2 vs bottom-2
of 7 countries monthly on carry (IR 0.66-0.71), carry-to-risk (0.61-0.63), slope reversal (0.44-0.46), real yield
(0.44-0.48), unemployment (0.13) (JPM, Update on systematic rule based trading strategies, Feb and Jul 2017).
Carry-to-risk percentile position rule: `position = 4 x (pct_10y - 0.5)`; carry-to-risk = (10y - 3m) / EWMA vol (decay 0.97):
proportional IR 0.53/0.35/0.43/0.49/0.75 (US/DE/JP/UK/combined) vs binary 0.26/0.34/0.05/0.30/0.41 (JPM, Simple rules to
trade duration, Oct 2012).

## 8. Auction and RV colour-bucket dashboards
EGB auction RV: every metric as a 3m z with buckets below -2 (rich), (-2,-1], (-1,0], (0,1], (1,2], above +2 (cheap);
metrics yield, vs fitted curve, vs surrounds (fly vs neighbours), vs closest-rated EGB, CAS; linkers: real yield, vs
surrounds, CAS spread to nominals, BEI. Examples: DBR 1% May38 vs fitted -1.45 (rich); DBR 1.8% Aug53 vs fitted +1.05, vs
NETHER +1.25 (cheap) (Citi, European Rates Morning Call, 12 Aug 2026). UST report: red if z < -2, green if > 2 on
matched-maturity swap spread, proceeds ASW and fitted spread (GS, Treasury RV Report, Sep 2026). Nordea overview panel:
carry-and-roll / realised vol ratio, 50-day and 200-day z and ranges, correlation with 10y and 2s10s, PCA mispricing; short-
and long-window z can disagree in sign (e.g. 1y1y/2y1y EUR OIS spread: 50-d z -1.7, 200-d z +0.83) (Nordea, EUR rates:
Risk/reward favours receiving ECB meetings, 19 Jun 2025).

## 9. Seasonality-style hit-rate tables (see quant-seasonality-and-calendar-effects)
Up-ratio screen: flag >= 70% (strong) / <= 30% (weak) of years up in a calendar month; US 10y up only 30% of Julys and 35% of
Augusts (BofA, Bond market seasonality explained, Jun 2022). Test with trimmed means/medians, Student-t and Wilcoxon at
10%, and count flagged months against alpha: Bund ASW Jan/Sep seasonality (p 0.750 and 0.136) was not significant
(swapsball.net, Testing for seasonality, Nov 2017). Conditioning example: US 10y January up -> Feb-Mar up 70% (23 of 33)
vs base ~54%, but small n and decayed edge (BofA, Technicals Explained, Jan 2025).

## 10. Statistical hygiene numbers
- Inclusive-window cap on |z|: (L-1)/sqrt(L): L=21 4.36, 63 7.81, 126 11.1, 252 15.8, 756 27.5 (arithmetic; script self-test).
- Normal tail frequency: |z| >= 2 once per ~22 days (57 in 1260), |z| >= 3 once per ~370 (3.4 in 1260) (Barclays, Global Rates
  Weekly, Oct 2026). Chebyshev worst case: 25% / 11% / 6% at 2 / 3 / 4 sigma (Hajek, 2025).
- SE of a Sharpe ratio: sqrt((1 + SR^2/2)/T) (iid) (Paleologo, The Elements of Quantitative Investing, 2025).
- 20 independent tries: 64% chance of a t >= 2 fluke; seven configurations are enough to find a 2y backtest with Sharpe
  > 1 whose expected out-of-sample Sharpe is 0 (Grinold and Kahn, 1999; Tulchinsky et al., 2015).
- FWER = 1 - (1-alpha)^M: M = 100, alpha = 0.05 gives 0.994. BH example: alpha 0.15 gave 11 rejections of 12,625 tests
  (Hastie et al., ESL; James et al., ISLP).
- Post-hoc p = 0.05 is worth ~2.5-4.5x evidence (calibrators), not 20x (Shafer and Vovk, Game-Theoretic Foundations for
  Probability and Finance, 2019).
