# Surface rich/cheap models: macro-vol, PCA/HPCA, switches, flies, regressions

Detail behind steps 3-4 of [SKILL.md](../SKILL.md). Use [`scripts/bachelier.py`](../scripts/bachelier.py)
`rate_pcs` + `grid_residuals` for the mechanics. All published fits below are STARTING HYPOTHESES from the cited
sample; refit on the user's data and regime before trading on them.

## 1. Macro-vol (rich/cheap to rates): level view

Regress each ATMF normal-vol point (expiry × tail) on the first 3 principal components of the swap curve (levels,
demeaned). Residual = actual − fitted in normal bp; report with a z-score of the residual over the fit window. A
positive residual is rich. Variants:
- Inflation-augmented: add 3 PCs of the breakeven curve (TIPS breakevens for USD, inflation swaps for EUR); USD fit
  2021-02-01 to 2022-02-28, out of sample from 2022-03-01; EUR fit 2021-06-01 to 2022-06-30, OOS from 2022-07-01
  (Citi Research, Rates Vol Lab: Short Blues convexity via futures/swaps, 21 Feb 2023; Forward steepener and vol
  divergence, 12 Jun 2023).
- Simple short-dated model: 3m10y normal vol on the 10y rate level and 2s10s. Rationale: a steeper curve = more uncertainty
  about the policy path = higher vol, and vol is directional with rates near zero (Citi Rates Vol Lab: Year-Ahead,
  12 Dec 2016; Fair value vs seasonality, 1 May 2017). Forecast = model value from rate forecasts + average recent premium.
  Dec 2016: model 3m10y ~80 vs market ~6 normals rich; forecasts 85-90 (H1) and 70-75 (H2) vs ~76 average.
- Regime-matched calibration windows used by the same desk: USD 1996-2008 spliced with 2017-2019 (excludes the
  near-zero-policy-rate regime; the model "is broken with Fed funds <= 50bp"); EUR 2016 onward (negative-rate regime) or
  2002+ in the 2026 version; USD 2009-2015 (the zero-rate regime) when the market is in that regime (Citi Rates Vol Lab:
  In search of cheap vol, 17 Jan 2020; Left-side vols' outperformance, 22 Jun 2021; Fading vega dislocations, 5 Oct 2026).
  Rule used here: fit on the regime the market is in now; never pool zero-bound and non-zero-bound samples.
- Betas flip: the 10y10y vol/rate beta flipped sign in 2025 (Citi, 5 Oct 2026); recheck rolling betas before using a
  fitted level.
- Single-point fit example: 6m regression of 5y2y vol on the 5y2y forward rate: vol = 24.284 × rate(%) + 24.734,
  R² 0.906; residual +5.7 normals after FOMC; dislocations can close through the RATE, not the vol (Citi, 22 Jun 2021).

## 2. Surface PCA: relative value only
- 3 PCs on the ATMF grid, 2y window (3y in some issues); residual z-score. "By design this framework only yields relative
  value" (Citi, 17 Jan 2020). It cannot say the whole surface is cheap. A last-cycle-calibrated variant (Jan 2004-Jan 2008
  spliced with 2017+) is used as a vega fair value (Citi Rates Vol Lab: Gamma and Vega RV, 14 Jan 2019).
- De-directionalise first: since sigma_N ~ F·sigma_B, regress vol on rate PCs, or add yield-curve PCs, before reading
  surface residuals (BofA, Understanding Principal Components, 21 Aug 2020; BofA US Vol Primer, 11 Mar 2024).
- Grid: 11 expiries (1M..30Y) × 7 tails (1Y..30Y) = 77 points; information content << points, so few PCs suffice;
  trade-offs: directionality, responsiveness vs estimation error, interpretability (BofA, 21 Aug 2020).
- Hierarchical PCA (HPCA): five static clusters - ULC (1m-1y expiry × 1-3y tail), URC (1m-1y × 5-30y), LLC (2y+ × 1-3y),
  IV intermediate vega (2-4y × 5-30y), LRC (5y+ × 5-30y). HPC1 = parallel level (loadings 5-14%, lowest on the 30y
  expiry row); HPC2 = gamma vs vega rotation (vol term-structure slope; trade via calendars/forward vol); HPC3 = left vs
  right of the grid (short vs long tails; trade via vol-curve trades, directional with curve PC2). HPCs are less noisy and
  suit risk decomposition (BofA 21 Aug 2020; BofA 11 Mar 2024).
- Vega-sector factors (JPY example): F1 level (risk appetite: corr with equity index -0.73, VIX 0.52), F2 expiry slope
  (linked to the swap-rate level, corr -0.75), F3 tenor slope. F1 and F2 mean-revert slowly (macro) and are correlated;
  F3 (fast mean reversion, low correlation) is "the only good RV factor". An F3 trade needs three instruments. Hedge
  against all factors of LOWER order than the exposure wanted. On a 2-D surface eigenvalues 2 and 3 are often close, so
  eigenvectors 2/3 can swap and PCA-hedged trades destabilise (Huggins & Schaller, Fixed Income RV Analysis, 2024).
- A PCA "skew factor" on a cube mostly reflects the model that fills illiquid OTM data (Huggins & Schaller, 2024).

## 3. Switch ratios and vol flies
- Expiry switches: 1m/3m, 3m/6m, 6m/1y, 1y/3y, 3y/5y, 5y/10y. Tail switches: 1y/2y, 1y/3y, 2y/5y, 2y/10y, 5y/10y,
  5y/30y, 10y/30y. Each with a 3m z-score (Citi Rates Vol Lab: Long Live Formosa, 9 Jan 2017; Citi, 17 Jan 2020).
- Tenor vol fly 1x2x1 at one expiry: fly = 2·belly − wing_short − wing_long (wings 2y and 30y, belly 5y or 10y; z since
  1999). Sign check on 3y vols 80.4/70.1/63.3: 2×70.1 − 80.4 − 63.3 = −3.5 (source table −4.0): low = cheap belly. Weight
  by vega, not notional: sell $230mn 3y2y, buy $100mn 3y10y, sell $21mn 3y30y straddles, take-in $240k, carry ~+0.75
  normals over 1y (Citi, 14 Jan 2019). Fair value depends on forward-curve slope.
- Vol-vs-vol betas for vega weights: 10y30y = 0.51×2y30y + 26.06 (R² 0.80, 2010-17); 2y30y = 0.78×2y10y + 13.30 (R² 0.89,
  2016); 3y30y = 0.69×3y10y + 18.68 (R² 0.78, 2016) (Citi US Rates Weekly: Swearing in huge expectations, 13 Jan 2017;
  Going nuclear, 3 Feb 2017). Example: buy 2y30y vs sell 2y10y at 1:0.8 vega ($53mn vs $100mn).
- Term-structure slope vs level: 3y10y − 1y10y = −0.2929 × 1y10y + 25.726 (R² 0.885, 3y window): long expiries
  underperform as vol rises. Illustration: at 1y10y = 100nv the model slope is −3.6; observed 5.5 normals steeper, i.e. 3y10y
  ~14 normals "too high" relative to rates -> short 3y10y vs a 10y10y/15y15y flattener (Citi, 5 Oct 2026). Upper-right:
  9m30y − 3m30y = −0.2493 × 3m30y + 23.239 (R² 0.73) (Citi US Rates Weekly, 21 Aug 2026).
- Calendar ratio vs mean reversion: 3m/1m vol ratio across tenors 2y-30y regressed on a mean-reversion measure (|1m rate
  change adjusted for forwards| / stdev of rate levels in the month): ratio = 0.6087×MR + 0.6217, R² 0.70; the 10y belly
  is most mean-reverting, best for calendars (Citi US Rates Weekly: Summer lull, 17 Jul 2015).
- Tail-ratio vs curve directionality: 1y5y/1y30y vol ratio tracks the 1m beta of the 1y-forward 5s30s curve to the 1y5y
  rate: beta = −0.6146×ratio + 0.9561, R² 0.62 since 2006; negative beta (bear flattening/bull steepening) -> 5y tail vol
  should outperform 30y (Citi, 22 Jun 2021).
- Expiry-ratio regression (gamma supply): 3Mx10Y/2Yx10Y ATMF ratio regressed on the average of the two vols, a programmatic
  gamma-supply estimate and VIX over 2y; Mar 2018 output "well below 90%" with extra supply worth ~5% (J.P. Morgan,
  Zen and the art of gamma maintenance, 9 Mar 2018). Ratio range Mar 2016-Mar 2018 ~0.75-1.05.
- Term-structure mean reversion: regress (3y10y − 3m10y) on 3y10y (3m, 9m, 3y windows); residual = rich/cheap. Feb 2007:
  spread fell 21 -> 7 normals in a falling-vol market (Merrill Lynch RateLab, Professional Javelin Catching, 16 Feb 2007).

## 4. Rate-vol linkages (use as lenses, each can disagree)
- Curve slope vs implied vol: steeper/more inverted = bigger spot-forward gap = more uncertainty = higher vol. Short-end
  ratio |spot 1y swap − 1y1y fwd| / 1y1y normal vol: Jan 2010 132bp/120nv = 110%, +1.4 sd (Bassman, Paying Nickels for
  Dimes, 21 Jan 2010). Jul 2014: 10y−2y 203bp (~+1 sd vs 124bp average) while 1y10y 73nv was −1.67 sd (Bassman, Your Ace
  in the Hole, 16 Jul 2014).
- Upper-left vol vs expected rate change: 6m1y vol tracks |6m1y forward − spot 1y| (US and EUR); cross-market vol
  differential should track the policy-rate differential; EUR 6m1y ~6 bp-vol too high vs |fwd−spot| (Citi US Rates Weekly:
  Pension plan for 20s?, 9 Oct 2026). EUR 1y10y vs the range |max − min| of the 1m ESTR forward curve to 3y: tracks 2012-25
  "not in any way perfectly" (Nordea, EUR rates: The quiet game, 12 Aug 2025).
- Vol vs outright rate by regime (EUR 1y10y vs 10y rate 2011-2025): when vol is low for the level, the last time was
  at rates >1pp lower (Nordea, 12 Aug 2025).
- Vol-rate directionality ("lognormal shuffle" model): dependent variable = rolling 3m beta of 5-day changes in ATMF
  normal vol on the strike; regressors: P(rate<0) implied by Normal(F, sigma) minus the zero-strike receiver delta (floored
  at 0), ATMF vol scaled to expiry / strike, and the 1Yx1M vs 1M OIS slope. 1Yx1Y: R² 69%, current −0.26 vs fair −0.09.
  Read: directionality too negative vs fair -> vol should underperform into a rally once a soft lower bound is enforced
  (J.P. Morgan IRD, Markets struggle to feed the convexity beast, 28 Feb 2020). Near zero the directionality can flip positive
  (J.P. Morgan, Did US rates markets just experience a mini Flash Rally?, 5 Mar 2020).
- Vol-rate beta (1M windows): 6Mx2Y 2.13, 6Mx10Y 2.23, 6Mx30Y 2.44, 2Yx10Y 1.30; on a flight-to-quality day betas flipped
  negative (6Mx30Y −3.13) (J.P. Morgan IRD, Near, far, wherever yields are, 2 Oct 2026). Hedges sized on recent beta fail
  on such days.
- Vol and curve co-movement: higher-vol days flatten curves and underperform the belly (2s10s corr −0.35/−0.52 on vol
  up/down days; 5s30s −0.61/−0.68; 5s10s30s +0.56/+0.65) (Citi European Rates Morning Call, 12 Aug 2026). Multi-factor
  view: implied vol should co-move with curve slope, credit spreads and realised 2y-10y correlation (Merrill Lynch RateLab,
  16 Feb 2007).
- Carry vs vol screen: scatter normal vol vs 3m roll-down across forwards; receive where carry is high and vol low. EUR
  2y-15y forwards: roll = 5.6208 × vol − 25.893, R² 0.97; the 20y-30y forwards fall off the line (ING Rates Strategy:
  Deconstructing the EUR yield curve, 15 Jan 2020).

## 5. Cross-market and cross-currency vol RV
- Swaption-gamma PCA across EUR/USD/GBP (1m/3m on 2y/5y/10y/30y plus listed): PC1 level, PC2 (~5%) currency factor, PC3
  tenor slope; residuals flagged UK gamma cheap in Oct 2012 (Credit Suisse, PCA Unleashed, 24 Oct 2012).
- 3Mx10Y GBP−EUR implied spread = 0.26×GBP 3Mx10Y + 0.02×(SONIA−Euribor 10y spread) − 2.44, R² 84%, 9m window; spread "too
  narrow" -> long GBP vs short EUR gamma (J.P. Morgan Global Fixed Income Markets Weekly, 21-22 Aug 2026).
- 10y10y USD 59nv vs EUR 57.4nv (27 Mar 2020; 5y5y inflation ~2% US vs 0.92% EUR): buy the USD leg on inflation
  anchoring and policy ammunition (Citi, 30 Mar 2020; Citi US Rates Weekly: Eat, pay, spend, 27 Mar 2020).
- USD vs EUR long-run implied ratio ~1.58 vs realised 1.55: MBS hedging keeps USD vol structurally higher; selling USD
  vs EUR vol lost historically when MBS hedging swamped other flows (Bassman, The Largest Volatility Sale Ever, 23 Mar 2010).
- EUR-GBP 5y5y implied spread is mean-reverting: OU half-life 15.4 days (2005-2012); see
  [forward-vol-and-calendars.md](forward-vol-and-calendars.md) section 6.

## 6. Systematic short-gamma rules (EUR 3Mx10Y; backtest to Jan 2018, since 2000, information ratio)
Always short: IR ~1.0. Vol-return momentum 1.9; carry 1.7; PMI shock 1.5-1.6; liquidity 1.4; equal-weight combination
2.45-2.50; ECB-regime rule 0.9-1.0 (look-ahead risk); implied/delivered rule (long <66%, short >125%) 0.8-0.9; "fade
extremes" (buy 1y z < −1.5, sell > +1.5) −0.3. Lesson: fading implied extremes ALONE loses; filters on momentum, carry and
macro shocks are what work (J.P. Morgan European Rates Strategy, Rules based strategies for trading duration and Euro area
rates volatility, 6 Feb 2017, 6 Mar 2017, 10 Jul 2017, 8 Jan 2018). Kurtosis regime: significance = −log10(p) of a
non-normal-kurtosis test on trailing 1m daily changes of the 1Mx10Y rate; 1.3 = 95%; high kurtosis favoured selling 3Mx10Y
delta-hedged ATMF held 1m over 1Mx10Y held to expiry (J.P. Morgan, 9 Mar 2018).
