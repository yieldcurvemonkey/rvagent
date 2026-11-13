# Worked data for curve PCA (extra numbers)

Numbers are as published; read them as examples of magnitude and format, not as current market levels. Sign convention of this
skill: residual = actual - model, positive = yield above model = cheap (receive). Full method in [SKILL.md](../SKILL.md).

## A. UST PCA and residual z-scores across lookbacks (BofA, Understanding the yield curve dynamic, 23 Jul 2025)
PCA on yield levels, tenors 2y/3y/5y/7y/10y/30y, 6m window. PC1 explains 95%.

| | 2y | 3y | 5y | 7y | 10y | 30y |
|---|---|---|---|---|---|---|
| PC1 loading | 36% | 37% | 40% | 44% | 43% | 44% |
| PC2 loading | 46% | 41% | 25% | 0% | -24% | -71% |
| PC3 loading | -76% | 11% | 48% | 28% | 11% | -30% |
| residual z, 1m | -0.47 | 0.44 | -0.79 | 0.65 | -0.76 | 0.36 |
| residual z, 3m | 0.57 | -0.40 | -0.91 | 1.24 | 0.02 | -0.54 |
| residual z, 6m | -0.44 | 0.50 | -0.41 | 0.03 | -0.05 | 0.12 |
| residual z, 12m | -0.07 | 0.15 | -0.42 | 0.21 | 0.20 | -0.20 |

Reading: only a slight 7y cheapness and 5y richness persist across all four windows; nothing exceeds |z| = 1.3, so no trade.
Illustrative eigenvectors from the same house (2/3/5/7/10/30y): PC1 .22/.31/.43/.48/.48/.46 (eigenvalue 96.5, cum 90%); PC2
.47/.48/.29/.04/-.22/-.64 (98%); PC3 -.60/-.24/.35/.45/.15/-.49 (99%) (BofA, UST RV Primer, 2 May 2022). Smaller PC1 loading at 2-5y
reflects the Fed on hold suppressing front-end vol.

## B. PCA-weighted vs 50/50 flies (same note, 6m, USD swaps)
PCA fly on (2y, 5y, 10y): variance explained by PC1-3 = 88% / 99% / 100%; PC3 weights 2y +45%, 5y -76%, 10y +47%. Fly table
(PCA fly last / z || 50/50 fly last / z || R^2 of the 50/50 fly with the belly):
2s5s7s -102.6 / -1.3 || -18.7 / -1.6 || 49.4%; 2s5s10s -98.9 / -1.3 || -36.1 / -1.6 || 65.4%; 2s5s30s -34.4 / -0.9 || -62.5 / -1.6 || 68.7%;
3s5s7s -30.3 / -1.0 || -8.2 / -1.4 || 42.9%; 3s5s10s -20.6 / -0.9 || -25.6 / -1.5 || 64.0%; 3s5s30s 4.5 / -0.7 || -52.0 / -1.6 || 67.8%.
Reading: the 5y is generally rich vs the wings; the 50/50 fly is 43-69% explained by the belly outright, i.e. directional.

## C. Level-covariance PCA fly, sizing and OU (bquanttrading, PCA Part II, 2015)
USD 3s5s10s: PCA on the covariance of swap levels of the three legs (variances 7.1%/14.0%/17.5% as printed); PC3 = [0.63, -0.70, 0.32];
dividing by the belly -0.70 gives weights [-0.90, 1.00, -0.46]. PV01 per 1mm: 274 (3y), 482 (5y), 903 (10y). For 50k 5y PV01: pay 103.7mm 5y,
receive about 164mm 3y (50k x 0.90 / 274; the source prints 200, likely a typo) and 25.5mm 10y. Fly about -47 (range -36 to -50),
z = -2.15, OU half-life 11 business days, expected +5bp on reversion excluding carry, carry+roll 6.25bp/3m -> pay the belly.
Caveats: interbank trades 50:50 so dealers may quote wider on a PCA fly; a series built with today's weights has look-ahead.

## D. Citi PCA-weighted fly weights (PC3, 5y rolling window; belly = 1; Citi US Rates Weekly)
| Date | 2-5-10 | 5-10-30 | 10-20-30 | 2-3-5 | other |
|---|---|---|---|---|---|
| 3 Feb 2017 | -0.9:1:-0.7 | -0.5:1:-0.6 | | | many PCA flies at -1.2 to -2.0 z |
| 20 Apr 2018 | -0.52:1:-0.57 | -0.47:1:-0.63 | -0.24:1:-0.79 | -0.67:1:-0.38 | 2-10-15 -0.18:1:-0.88 |
| 18 Jan 2019 | -0.43:1:-0.62 | -0.44:1:-0.62 | -0.24:1:-0.79 | | 2-5-7 -0.28:1:-0.75 |
| 10 May 2019 | -0.39:1:-0.68 | -0.45:1:-0.62 | -0.24:1:-0.77 | | 15-20-30 -0.50:1:-0.51 |
| 4 Oct 2019 | -0.36:1:-0.72 | | | | level -22.6bp (1:2:1 2s5s10s -11.1bp) |
| 17 Feb 2023 | -0.32:1:-0.73 | -0.46:1:-0.57 | -0.40:1:-0.60 | | 2-10-30 -0.21:1:-0.87 |

Correlations: equal-weight 10-20-30 3m correlation to 5s30s 96% vs the PCA fly mostly low (34%) (18 Jan 2019); equal-weight 2-3-5 shows
-89% vs 2s10s, while PCA flies cut curve correlation but keep sizeable correlation to level (10s) (Citi, Eat, pay, spend, 27 Mar 2020).
Snapshot 16 Feb 2023: PCA 10-20-30 level 8.9bp, z (1m/3m/6m) -1.60/-2.58/-2.22; equal-weight 5.7bp, -1.61/-2.69/-1.60. Closed: long belly
10s20s30s PCA fly 57 -> 48 (+$220k) (Citi, Time for moderation, 17 Feb 2023). Receive-belly 5s10s30s flies behave like short vol: size as short gamma.

## E. Method comparison for the 2s5s10s fly (QF Stack Exchange, 2s5s10s directionality, 2018/2021)
Basis change [5Y, 2s10s, 2s5s10s] = A [2Y, 5Y, 10Y], A = [[0,1,0],[-1,0,1],[-1,2,-1]]; covariance transforms Q' = A Q A'. With PC1 = (0.660, 0.604, 0.447):
divide-by-PC1 -> (-0.91, 2, -1.35); minimal change (KKT, body 2) -> (-1.1002, 2, -1.0780) (unscaled projection about (-1.067, 1.939, -1.045));
min-VaR with 5Y fixed at 2 -> (-1.48, 2, -0.38); regression of the fly on 2s10s and 5y -> (-(1-b1), 2-b2, -(1+b1)).
EUR out-of-sample (Jul-Dec 2016, n = 116) stdev of daily changes: raw fly 0.8399, regression 0.7609, min-VaR 0.7628, PCA 0.8689.

## F. PCA fly versus fair value in EUR (Nordea, 2024-2025)
Structures are reported with PCA factor loadings (outright / curve / curvature): EUR 10s20s30s 6s -0.12/0.94/0.19; 2s5s 6s -0.12/0.77/0.49;
1y2y/3y2y/5y2y fly outright insignificant, curve 0.47, curvature 0.61 (Nordea, The quiet game, 12 Aug 2025; How about that outright receiving,
26 Sep 2025; Pushing back, 17 Jan 2024). 10s20s30s 6s par 26.2 vs PCA fair value 32.0: "the 20y point would normally have been 6bp higher".
Receive 2s5s 6s at 24bp, target 19, stop 30, 12m carry+roll 6.6bp, PCA mispricing 31.5bp near historical extremes. 1y2y/3y2y/5y2y fly: PCA par -7.3 vs
fair value -34.7, receive at -8bp, target -25bp + roll, stop +5bp, carry 79.2/12m, carry/vol 1.70. Nordea's dashboard fields: rate, 50d range,
carry+roll, convexity-adjusted carry/vol, 50d and 200d z, PCA mispricing, PCA fair value, correlations to 10y / 2y1y / 2s10s / 10s30s / 5s10s30s.
Factor z-scores end-Jul 2025 (approximately, from a chart): outright +1.4, curve 0.0, curvature -1.5. The residual z of 1y10y normal vol on the PCA outright
and curve factors is closely related to the curvature factor (2012-2025), a vol proxy for choosing carry flies.

## G. EUR forwards on a 1y window (Credit Suisse, PCA Unleashed, 24 Oct 2012)
Variance explained: PC1 > 80%, PC2 10.1%, PC3 4.3% (about 95% for three). EUR PC1 all positive, largest 1y1y-5y1y, smallest 10y2y-30y10y; PC2 negative front,
neutral belly, positive long end; PC3 positive wings, negative belly. PCA trades published on 22 Oct 2012: 2s5s steepeners in Netherlands and Spain;
receive EUR 1y-forward 1s2s3s fly; pay EUR 10y10y-20y10y-30y20y fly; GBP 30y10y-40y10y steepener (EUR-GBP spread residuals); buy GBP 1m gamma on 10s and 30s.
The 3y1y residual moved 16bp from positive to negative in July, so the 4y sector was then fair. Hedge formulas: min over gamma of Var(x - gamma y), with
PC1-only gamma = u1x / u1y and PC1+PC2 gamma = (u1x u1y v1 + u2x u2y v2)/((u1y)^2 v1 + (u2y)^2 v2), v_p = variance of PC p (the source writes lambda^2, with lambda as the sd).

## H. Cross-sectional and curve extensions (numbers)
- **Swap-spread curve PCA (BofA, A simple framework for swap spread relative value, 2 Jun 2016).** 2y/5y/10y/30y spreads per country, 250-day window, two PCs
  explain "high 90%". Dislocation indicator DI = 10-day MA of RMS of the four residual z-scores. Backtest 2001-2016 (threshold: cum bp, Sharpe, days):
  US 1.0: 267, 1.2, 1750; 2.0: 51, 0.4, 676; Germany 1.0: 869, 2.4, 2278; 2.0: 554, 2.8, 967. Costs, carry and stops excluded. Residual half-life about 20 days.
- **EGB spreads to Bunds (BofA, Many EGBs, one simple value tool, 21 Mar 2018).** 42 series (7 countries x 6 tenors); expanding-window daily PCA; chosen spec 11 PCs,
  5-day hold, 2x dislocation threshold; hit ratio of long signals 56% at 0.5x to 71% at 3x, short signals about 50%; costs excluded, expanding window adapts slowly.
- **10y OAT-Bund (BofA, Global Rates Weekly, 2 Oct 2026).** Spread 140bp; PCA residual about 33bp too wide; directionality residual about 42bp cheap; fair value 100-110bp;
  "the spread needs to stabilise first".
- **OIS/UST swap spreads (Citi, Short-End Notes, 21 Aug 2026).** PCA on 2y-30y spreads, 1y sample, residual to first 2 PCs, 3m z; residuals within +/-0.5bp (5y -0.5, z -0.8, slightly cheap).
- **Idiosyncratic EGB spread vs PC1 (Goldman Sachs, Global Rates Trader, 2 Oct 2026).** OAT idiosyncratic premium about +30bp: since 1 Sep 2026 FR 62 actual vs 28 PC1-predicted.
- **Citadel (Global Macro Strategy, 25 Aug 2026):** cross-asset PCA, PC1 = growth, PC2 = monetary policy; PC1 > 1.5 with PC2 < 0 tended to precede UST rallies.
