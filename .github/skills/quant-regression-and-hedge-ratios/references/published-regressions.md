# Published regression and hedge specifications (catalogue)

Companion to [SKILL.md](../SKILL.md). These show *specifications, windows and magnitudes* the sell-side and academic
literature actually use. Coefficients are dated; re-estimate before use and never trade them as constants. R-squared is
in-sample unless stated. Rates in %, spreads in bp, vols in normal bp, unless stated.

## A. Regression-derived hedge weights for convexity adjustments (STIR)
Idea: regress the model value of a non-linear exposure on tradable curve points; the coefficients are the DV01 weights of
the hedge. Packs, not single contracts: individual futures/FRA spreads are noisy (Citi, Buy long expiries, 17 Jan 2017).
- Blues convexity adjustment (CA) on a 2y/5y/10y swap fly, sample from about 2010 (Citi, Sell Blues convexity
  adjustments, hedged, 9 Feb 2017): CA = 9.7 + 20.6 x (-0.705 y2 + y5 - 0.465 y10); about 3bp (2 sigma) wide. Re-estimated
  in Jan 2017: 10.2 + 21.4 x (-0.73 y2 + y5 - 0.47 y10), 4bp / 2.5 sigma wide (Citi, Swearing in huge expectations,
  13 Jan 2017). Weights drift between re-estimations (0.705 vs 0.73), so state date and sample.
- 3y1y normal vol vs the DV01-weighted 2s5s10s fly, levels since 1999: vol = 59.7 + 60.5 x (-0.71 y2 + y5 - 0.18 y10),
  correlation 90% (same sources). A carry-efficient vol hedge.
- CA vs a futures steepener, calibrated pre-2008 because the vol-curve relation broke at the ZLB: CA = -0.65 + 0.044 x
  (ED16 - 0.74 ED6) (Citi, What to expect when you're expecting a turn, 20 Apr 2018). Greens CA vs two-contract steepener
  weights 1 / -1.18 (Citi, Turning Green from Blue on short convexity, 6 Jun 2017). The regression hedges are slightly
  short the market because short-tail vols and rates are positively directional.
- Realised-beta matching across expiries: $100k/bp of CA risk is about 16k vega of a 6m1y straddle (Citi, Pension plan
  for 20s?, 9 Oct 2026); disclose the mismatch.
- Basis package exposure targeting: forward FRA/OIS on spot 3m L/OIS 0.5646 x - 1.90 (R-squared 0.927); package
  0.3574 x - 3.53 (0.864); size an overlay so the package keeps about 35% exposure (Citi, Eat, pay, spend, 27 Mar 2020).
- Empirical beta re-weighting: 15y5y vs 20y10y beta 1.025, notional 81.97mn to 84mn (Citi, 16 Oct 2019).
- Calendar-spread hedge ratios (back contracts per 1000 front): ultra bond 974, bond 995, ultra 10y 960, 10y 950, 5y 932,
  2y 854 (JPM, For cheap gamma, look to the long end, 23 Aug 2019). Roll DV01 mismatch: CTD DV01 $166
  vs $252 per contract means an equal-DV01 roll needs 34.1% fewer of the back contract (Citi, The long end basket
  case, 4 Feb 2015).

## B. Curve, fly and cross-market betas
- Rolling 3m beta of weekly maturity-matched swap-spread changes on yield changes vs 10y-lookback median and 5/95
  percentiles (JPM, Is bank convexity hedging lying in wait?, 31 May 2019); conditional selloff-only / rally-only 3m
  betas of 10y vs 2y (JPM, The return of convexity hedging, 31 Jan 2020).
- Implied vs delivered directionality = 1 - sigma_S/sigma_L vs 1 - beta(Y_S on Y_L); equivalence: delivered - implied =
  beta of the weighted curve on the long yield; levels, 1d and 1w betas differ (JPM, A primer on Conditional Trades, 26 May
  2016). EUR exhibit: 2s10s implied 61% / delivered 72%; 3s20s regression 20y on 3y: y = 3.00 x + 1.08, R-squared 82%.
- EUR 10s30s steepener 3m P&L on the 10y change: unconditional y = -0.22 x + 4.13 (0.36); rate and vol same-sign
  subsample -0.24 x + 2.47 (0.47) (Citi, A QT revolution, 17 Sep 2026). Entry level and initial roll are weak predictors.
- Curve on its own level (12m): 2s10s on 2y over the last 2 months y = 52.361 x - 55.756, R-squared 75.8% (JPM, US
  Treasury Market Daily, 25 Feb 2020). "One day does not make a trend": confirm before re-weighting.
- Futures spread and fly monitor: regress each spread on its longer leg and each fly on its belly; PCA flies are built
  to have zero correlation and zero beta to the belly (Citi, OAT of the blue, 2 Oct 2026). Term-premium proxy: residual of
  5s30s regressed on the 5y over a rolling 5y window (Citi, The Messi Theory of Interest Rates, 31 Jul 2026).
- 50/50 fly R-squared with the belly (6m): 2s5s7s 49.4%, 2s5s10s 65.4%, 2s5s30s 68.7%, 3s5s7s 42.9%, 3s5s10s 64.0%,
  3s5s30s 67.8% (BofA, Understanding the yield curve dynamic, 23 Jul 2025): high values flag directionality.
- 10y daily yield change on the 5th SOFR future (Mar 2022 to Mar 2025): beta 0.9, R-squared about 91%; segment
  correlations of 2s10s with 2s5s 0.82, 2s30s 0.88, 5s10s 0.63, 5s30s 0.47; 1s2s about uncorrelated with all
  (Willer and Saunders, Trading Global Macro Markets, 2026).
- Cross-market 52-week weekly beta screens of local 10y and 2s10s on the US equivalents; 26-week rolling betas (Citi, Can
  back-end USTs derail EM risk?, 20 Aug 2026); 35-week beta to the dollar index for expected-vs-actual moves (JPM,
  Currencies amid long-end UST shenanigans, 21 Aug 2026).
- Intra-EMU spreads: 10y OAT-Bund on Bund yield, Bund ASW, financial conditions, equities, vol, rating-matched credit,
  daily since 2020; standardised residual = residual / its s.d. (Citi, What to do about OATs?, 1 Oct 2026). Pooled fiscal
  regression: core pool little effect, non-core 10pp debt/GDP adds 30 to 40bp, 1pp worse balance 20 to 30bp (Barclays,
  The urgency question, 2 Oct 2026). Two residuals can disagree; fade only once the spread stabilises (BofA, Start of
  rates bite, 2 Oct 2026).

## C. Swap-spread, funding and basis fair values
- 30y matched-maturity swap spread on 5s30s Treasury curve, deficit expectations, variable-annuity hedging flows and
  WAM; rolling 5y partial betas (the curve beta more than doubled): JPM, The long and short of it, 3 Aug 2018.
  Changes form, 6m changes over 10y: curve -0.419 (t -47.3), GC/OIS -0.25, WAM -0.39, VA -0.121, R-squared 71%, s.e. 6.4;
  actual -40bp vs FV -54bp (JPM, What about Bonds? SLR relief, 2 Apr 2020). 2y OIS spread model R-squared 39%, 30y
  LIBOR 61%; large residuals in 2015 and 2020 coincide with Basel III and the SLR exemption (TBAC, Charge: Swap
  Spreads, Feb 2021).
- Term funding premium: negative of the slope of a daily cross-sectional regression of maturity-matched swap spreads on
  modified duration (2y to 30y); fair-value model R-squared 83%, s.e. 0.3; exit when within one standard error (JPM,
  Buying back time, 19 Aug 2026; IRD Strategy Update, 5 Nov 2025). Treasury premia: 85.58% of monthly slopes negative,
  average -0.7567 bp/yr (Fleckenstein and Longstaff, Treasury Richness, Journal of Finance, 2023).
- Reserves and funding spreads: log-linear spread = a ln(reserves) + b with regime-specific fits (SOFR-IOER 2015 to 2019
  -42.29 ln x + 314.47, R-squared 0.60; Jun 2020 on -25.59 ln x + 202.56, 0.91); regime breaks at administered-rate
  changes; ensembles of regimes with explicit weights (BofA, Fed QT Beyond Taper and Funding Impact, 22 Oct 2021; Monthly
  rates models, Apr and May 2025). Weekly-change regressors entered separately by sub-sample; a composite (bills minus
  reserves) can be significant when its components are not (Citi, SOFR/FF spiking into quarter-end, 27 Jun 2025).
- Cross-currency basis: per-currency daily regressions on FRA/OIS and positioning with t-stats (R-squared 36 to 76%;
  persistent same-sign residuals flag omitted structural drivers: JPM, There is one market where USD funding stress
  could reemerge, 20 Feb 2020). 10y EURUSD basis = 0.64 x relative swap-spread + 17.79, R-squared 0.82 (BofA, Scope for
  10y EURUSD xccy basis tightening, 27 Mar 2025). Regression slope vs the no-arbitrage slope of 1 gives a residual term to
  attribute (Citi, FX Basis Quarterly, 13 Dec 2024). Regressor sign stability: replace a regressor whose beta is
  counterintuitive (JPM, Cross currency basis 2H25 Outlook, 5 Jun 2025).
- Three-month SOFR futures vs Eurodollar-type futures basis on SOFR level and 2y JPY cross-currency basis: 4.825 + 2.322 SOFR - 0.394 CCBS, R-squared 0.67; OU fit
  of the residual: half-life 2.6 to 3.7 weeks (Huggins and Schaller, SOFR Futures and Options, 2022, Ch.4).
- Bund fitted-curve regression with amount outstanding 0.025 per EUR bn and issue age 0.027, deliverable premia 2 to 4bp
  (Huggins and Schaller 2024, Ch.8).

## D. Vol fair values
- Macro-vol model: ATM normal vol on 3 PCs of the swap curve, plus breakevens in 2021 to 2023; ZLB excluded; samples
  spliced (1996 to 2008 with post-liftoff data); residual in normals and z (Citi, Fair value vs seasonality, 1 May 2017;
  Rates Vol Lab, 12 Jun 2023). "By design, this framework only yields relative value."
- Vol-on-vol: 10y30y = 0.51 x 2y30y + 26.06 (R-squared 0.80, 2010 to 2017); 2y30y = 0.78 x 2y10y + 13.30 (0.89) (Citi,
  Long Live Formosa, 9 Jan 2017). 3y10y vol = -0.992 x (15y15y - 10y10y) + 48.305 (0.904) (Citi, Fading vega dislocations,
  5 Oct 2026). Midcurve vol on its two vanilla vols over 3y. Vol ratio vs realised curve/rate beta, two stage:
  y = -0.6146 x + 0.9561 (0.625) (Citi, Left-side vols' outperformance, 22 Jun 2021).
- Vol-rate directionality: normal-model negative-rate probability, vol/strike ratio, front-end slope as regressors,
  R-squared 69%/66%/38% by tenor (JPM, Markets struggle to feed the convexity beast, 28 Feb 2020).
- De-directionalise a vol PCA residual: regress vol PCs on forward-curve PCs, map the fitted part back, trade the
  residual vs that rates-implied model (BofA, US Vol Primer, 11 Mar 2024).
- Implied vs realised beta in conditional curve screens: 3m 2y10y implied -0.39 vs realised -0.61 (Citi, 12 Jun 2023);
  "the implied beta of -0.4 is consistent with price action over the last 6 weeks, hardly a template for the long run"
  (Citi, A narrative shift looms, 17 Mar 2022).

## E. Macro and inflation fair values
- Two-layer macro fair value: regress curve PC1 and PC2 on macro factors, rebuild yields via the inverse PCA; residual in bp
  and sigma (rich negative); residual sd about 35bp front end, 20 to 25bp back end (BofA, Introducing a new UST macro
  framework, 15 Oct 2024); window 7 to 15y, add balance-sheet and global-PC1 terms (BofA, Monthly rates models, Aug 2025).
- Pension funded-status nowcaster over 3y: assets on 30y Treasury -3.5 (t -5.3), S&P 0.31, R-squared 90%; liabilities on
  30y -12.6 (t -22.2), R-squared 97% (JPM, Pension re-risking and long-end swap spreads, 3 Apr 2020).
- 5y5y OIS macro FV: USD = 0.18 inflation + 0.16 growth + 2.2 (R-squared 82%); EUR 0.27 / 0.12 / 1.0 (91%); GBP 0.28 / 0.05 /
  1.1 (93%) (JPM, Global Fixed Income Markets Weekly, 21-22 Aug 2026). 1y1y HICP on 1y1y estr and front Brent over 3M
  (R-squared 50%); drop a driver that adds no R-squared and does not move the residual (JPM, Monthly Inflation Outlook,
  13 Aug 2026). Regime-split lines by period rather than dropping years (Nordea, 19 Jun 2025; Citi Japan FX, 15 Jun 2026:
  dummy plus interaction terms for 2022).
- Central-bank text: statement score on speech score plus lagged statement; adding the lag roughly halves the effect;
  ZLB dummy and interaction needed (JPM, Welcome to the machine: NLP of central bank speak, 26 Apr 2023).
  Levels regression of 1y1y on text PCs, home score and macro factors with deliberate exclusions; compare betas across
  full, 10y and 5y windows (JPM, Talk is Cheap, 30 May 2024).

## F. Estimation-hygiene numbers worth reusing
- Significance and magnitude thresholds used in a factor study: rolling t versus 1.65 (90%) and 1.96 (95%); R-squared
  labels strong 0.70, moderate 0.50, weak < 0.10; incremental R-squared meaningful above 0.03; orthogonalise secondary
  anchors; track factors by bloc identity; drop pegged markets that inflate R-squared (Citi, Decomposing Global Rate
  Drivers Across EM Asia 5y5y, 13 Aug 2026).
- Excess-kurtosis regime filter: -log10 p of a kurtosis test on trailing 1m daily moves, 1.3 = the 95% threshold (JPM, Zen
  and the art of gamma maintenance, 9 Mar 2018).
- Variance-ratio gauge: 3m realised vol from daily vs monthly/sqrt(21) changes (JPM, The long and short of it,
  3 Aug 2018).
- A regression of a regression-weighted fly's own P&L on candidate factors shows hidden exposure (a PC1-neutral Euribor fly:
  R-squared 0.03 on the 2y swap, 0.65 on an equity valuation measure) (ING, EUR crisis trades: let's get tactical,
  3 Mar 2020).
- Dealer hedge ratios estimated from position data: aggregate beta to index swaps -0.96 (t -6.40), single-name -0.44,
  adjusted R-squared 43%; a 13-to-15-month swap hedged with short-dated futures at 0.5 to 0.6, below 1:1 because of
  imperfect correlation and lower long-dated vol (Mixon and Onur, Risk Appetite and Intermediation by Swap Dealers, CFTC OCE,
  Apr 2020).
