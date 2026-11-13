# ML for rates: case studies and numbers

Reference tables for [ml-models-for-rates](../SKILL.md). All figures are as printed in the cited sources. Most are USD
and pre- or low-cost. Use them to calibrate expectations, not as benchmarks for another market.

## 1. Direction and sizing models on US Treasuries (J.P. Morgan)

### Do androids dream of electric bonds? (Salem, Younger, Zhao et al., 22 Nov 2017)
- Setup: about 1,250 raw features; 1-week or 1-month hold; a new trade daily. Instruments: 10y on-the-run Treasury,
  10y matched-maturity swap spread, 1M x 10Y at-the-money-forward straddle. CV from mid-2008 to 2016, quarantine 2017.
- Shuffle threshold, 10y, 1-week hold, 2010-16 (3,000 shuffles at a fixed sell fraction): median about 0.6 for
  all-long, 0.0 at 50/50, -0.6 all-short; the maximum over trials peaks near a 20% sell fraction at just under 0.95.
- Random forest CV Sharpe above 1.2; 10y bid/ask lowers Sharpe by just under 0.1 (about 10%).
- Quarantine 2017: balanced RF 1.35 versus 0.38 all-long. RF and RBF-SVM beat the 95th and 99th shuffled percentiles;
  other classical models did not. Best ANN 1.72, but the other four ANNs were about all-long and one negative.
- Swap spreads: RF incrementally beat the narrowers in CV and roughly matched the wideners in 2017 (confidence
  "tepid"). Unweighted RF converged to a systematic short-gamma position in the vol application.

### TradeRunner (Salem, Younger, Huang, 16 Aug 2018)
- Daily OTR decision, 5-day hold, `S = 2P - 1`. Walk-forward: train from mid-2008, test from 2009, first 5 days dropped,
  expanded 4 times to 30 Dec 2016; quarantine 2017-18.
- CV 10y: best GBM Sharpe about 1.1-1.2 (about 10% above RF at about 1.0); frontier never above 1.2. RF returns 10-20bp
  a year; some GBM 50bp+.
- Sell fraction rises along the curve: 2y 30-35%, 10y/30y about 45%. Balanced GBM sells a majority ahead of >10bp selloffs.
- Quarantine 2017-18: 2y passive Sharpe about -2.0 (with costs), classifiers about -0.8 while selling 30-35%; 5y/10y GBM
  about flat; 30y about 0.5. Confidence of outperformance about 70% (2y, 10y) to about 95% (5y).
- Costs (time-weighted top-of-book width): about 0.4bp 2y; 0.2-0.3bp 5y/10y; 0.1-0.2bp 30y.

### #SquadGoals (Salem, Younger, Huang, 21 Sep 2018)
- Stacking: CV Sharpe up 10-20% over the best balanced solo GBM, similar sell fraction, average return nearly double.
  Quarantine: stacks avoided a negative average return while passive buying lost; inclusive stacks (balanced plus unbalanced
  constituents) had Sharpe approaching 0.5. Quarantine shuffle significance: best solo GBM 79%, stacks above 99%.
- Soft voting: 175 pairings of the top-5 balanced GBMs with other learners. Only the decision-tree pairing was
  significant in CV, and no meaningful quarantine outperformance. Linear-SVM partners hurt.

### Retraining (Is bank convexity hedging lying in wait?, 31 May 2019)
- Original model (trained to end-2016): Sharpe 1.1 selling about 35% of days, about 0.5 above the random benchmark.
  Retrained through 3Q18 with no hyper-parameter or feature change: Sharpe 1.27 selling about half of days, beyond 95%.
- Hit rate: retrained above 70% at conviction above 90%; original below 50% only below 60% conviction. Passive long
  Sharpe 2.5 over the same 8 months; the original lost in selloffs (long bias).

### Auction tail model (Citi Research, US Rates Weekly: Learning on the job, 2 Aug 2019)
- OLS, tail on the previous three auctions' average foreign takedown: `y = -12.19x + 2.6219` (R2 0.22); on contemporaneous
  takedown: `y = -11.482x + 2.7495` (R2 0.48); sample since 2010. A foreign takedown of 15.5% versus about 20% average in
  2018 predicts a tail.
- Logistic on the 3-month average of 10y foreign takedown, 1m change in the yen cross and 1m change in a global surprise
  index; trained 2010-2017; out of sample from 2018: 4 of 6 correct; full-sample accuracy 64% (76% of tails, 55% of throughs).
  Recent yield changes had almost no predictive power.

### Callable-bond call probability (Taiwanese demand for US fixed income, 10 Jan 2020)
- One observation per annual call date (about 2,000); features: Bermudan-implied call probability, log issue size, issuer type.
- 2020 redemptions: about $85bn up for call; empirical model about $30bn expected versus $78bn from the raw option model.
  Quarterly empirical/raw ratio: Q1 47%, Q2-Q3 about 32%, Q4 24%. Observed call efficiency for bonds with more than 80% model
  call odds: about 50%; issues of at least $300mn about 70%; smaller 20-40%.

## 2. Linear and shrinkage models

### Classic yield regression (Salomon Brothers, Understanding the Yield Curve Part 4, Aug 1995)
- Expected 20y excess return `= -10.15 + 0.37 TermSpread + 0.20 RealYield + 9.85 InverseWealth + 0.34 Momentum`
  (1965-95; t-stats -4.98, 2.24, 2.89, 4.81, 2.02; R2 10.3%). Out of sample: correct sign 61% of months; scaled strategy
  Sharpe 0.68 versus 0.06 always-bond. Protocol: data from 1955, first forecast 1965, monthly re-estimation, expanding window.

### Prostate data (Hastie et al., 2009, Tables 3.3 and Sec 3.4-3.6)
- Test error (SE): LS 0.521 (0.179); best subset 0.492 (0.143); ridge 0.492 (0.165); lasso 0.479 (0.164); PCR 0.449 (0.105);
  PLS 0.528 (0.152). CV chose ridge df 5.0, lasso `s` about 0.36 (four coefficients zero), PCR 7 terms, PLS M = 2.

### Model-selection simulation (Shalizi, 2025, Ch.19)
Quadratic truth, maximum degree 10, 1,000 repetitions. n = 20: R2 always picks 10; adjusted R2 median 6; Cp median 2 (mean
3.46); LOOCV mean 2.77; AIC mean 4.67; BIC mean 3.08. n = 1,000: adjusted R2 mean 5.18; Cp, LOOCV, AIC about 2.77 with about 25%
chance of a model too big; BIC mean 2.003.

### Heteroskedasticity (Shalizi, 2025, Ch.21)
`y = 3 - 2x`, sd `= 1 + x^2/2`, n = 150: OLS slope SE reported 0.22 versus 0.49 simulated truth. WLS with the right weights gives
SEs 0.3 and 0.19, matching the simulation.

### Equity-credit ridge model (Willer, Saunders, Trading Global Macro Markets, 2026, Ch.15)
Ridge on an expanding window; positions proportional to the forecast percentile. IG credit versus equities: return 1.16%,
vol 1.24%, return/risk 0.94, max drawdown -2.83%. CDX versus equities: 0.43%, 1.35%, 0.32, -4.32% ("likely too low to
trade"). Features: equity and bond vol, credit spread level and change, equity momentum, curve shape, recent 2y changes,
inflation; spread changes were subsumed by equity moves.

### AR versus nets (James et al., ISLP, Sec 10.5.2)
NYSE daily data 1962-86 (T = 6,051): chronological split at 2 Jan 1980 (4,281 train sequences, 1,770 test). Test R2: persistence
0.18; AR(5) on three series 0.41; RNN (12 hidden units, 205 parameters, versus 16 for AR) 0.42; feedforward net on lagged inputs
0.42. Day-of-week dummies helped all models.

## 3. Analog, correlation and sparse models (2008 swap studies)

### Leela correlation analog and PCA residuals (Burton, Dektor, Wheeler, c.2008)
- Rolling OLS on lagged daily changes (`n` from 63 to 1500; `p` 3-5): poor. Burg AR on 10y changes, `n = 502, p = 4`: Sharpe 0.9. Benchmarks: 10y buy-and-hold 0.25 (0.27 vol-scaled); rolling OLS 0.23 with row-norm scaling (`p = 3, n = 251`), 0.0 without.
- Residual-PCA prefilter: `D` = daily bp changes for 2, 3, 5, 7, 10y over 63 days; SVD singular values 211, 33.6, 12.4, 7.2, 2.4;
  keep 2 PCs; next-day weights `w = (F'F)^-1 F'd_{t+1}`; residual (predicted minus actual) fed to the analog model.
- Leela on residuals (n = 750, p = 4), Sharpe by tenor: 2y 0.4, 3y 1.4, 5y 1.2, 7y 2.2, 10y 0.8. Single 10y Leela typically below
  1.2; multi-swap peak near a 500-day window, Sharpe above 1.5; PCA variant peak above 2. Train about 1994 to late 2007, test late
  2007 to late 2008. The window peaks are training-period sweeps (window picked to maximise Sharpe) and costs are ignored. A residual
  is not tradable outright (7y outright Sharpe near zero): trade it as a fly with weights in the null space of the two-PC loadings.
- Context for the 7y: mortgage servicers hedge with 7y instruments and the residual mean-reverts.

### Sparse mean-reverting baskets (d'Aspremont, 2008)
- US swaps 1y-30y, 100 days: Box-Tiao `lambda` 0.58, 8.61, 16.48, 38.59, 84.55, 174.82, 184.83, 238.11. A `lambda` of 238 implies a
  half-life of about 1 day (insignificant on daily data).
- Greedy sparse, `k = 1` to 8: lambda about 0, 35, 128, 178, 213, 247, 252, 252, so most mean reversion comes with 3-5 legs.
  `k = 3` weights: 3y -0.288, 4y 0.806, 5y -0.517 (a 3s4s5s fly); `k = 4`: 1y -0.041, 3y 0.433, 4y -0.803, 5y 0.408.
- Out of sample (200-day estimation, re-estimated every 50 days): a 1bp bid/offer completely neutralises the inefficiencies.

### Top-down CTA replication (BofA, US Rates: CTAs impact on the rates market, 18 Aug 2020)
- Target: equal-weight index of 20 large CTAs. Six features from the first PC of clustered asset sets; rolling OLS on a 2-month
  window; feature betas projected to assets by the inverse PC1 transform. Average R2 66% on 2-month windows since 2015 (after
  replacing the FX feature with the dollar index).
- Reading betas: long-duration beta = duration bias; long-duration minus short-duration beta = curve bias (flattener when long
  the long-duration feature and short the short-duration feature). Trend in the 10y beta correlated about 60% with CFTC net
  non-reportable 10y positions (about 20% for other reportables). Duration bias since Feb 2020; flattening bias peaked 24 Jul 2020.

## 4. Regime clusters and nearest-neighbour regimes (Citi Research)

Backtest, 1974-2021 before costs (Saunders, Willer, 29 Oct 2021): mean-variance 0.58 return/vol; Black-Litterman 0.67; equal-weight
0.50; 60/40 0.49; long-short 0.51 with max drawdown -13.62%. BL and long-short turnover about 30% a month.

Ten-cluster model (Saunders, Vo, 13 Apr 2026). Centroid z-scores: G7 inflation | G7 leading index | cross-asset vol | financial
conditions.

| Cluster | n months | Inflation | LEI | Vol | Fin. cond. |
|---|---|---|---|---|---|
| 1 Normal | 162 | 0.27 | 0.26 | -0.68 | -0.60 |
| 2 Recovery | 128 | -1.09 | -0.33 | -0.39 | -0.85 |
| 3 Goldilocks | 113 | -1.19 | 1.35 | 0.21 | -0.39 |
| 4 Growth shock | 63 | -0.23 | -1.44 | 0.22 | 0.09 |
| 5 Tightening financial conditions | 58 | 0.49 | -0.37 | 0.28 | 1.22 |
| 6 Stagflation, no Fed | 27 | 2.43 | -0.86 | 1.73 | 0.32 |
| 7 Stagflation with tightening | 24 | 2.35 | -1.30 | 1.63 | 3.39 |
| 8 Inflationary boom | 24 | 3.14 | 0.90 | 0.05 | 0.13 |
| 9 Recession | 17 | -2.25 | -0.67 | 1.40 | 1.16 |
| 10 Market shock | 15 | -1.08 | 0.98 | 3.72 | -0.12 |

From "tightening financial conditions": about 7% to stagflation, about 8% to a growth shock. Aug 2026 reading (Saunders, Vo, 12 Aug 2026):
regime "Normal"; KNN analogs 1976-77, late 1989, 1996-97, 2013-14; hedged duration had the highest forecast Sharpe; UK bonds most
favoured, FX-hedged JGBs had the highest carry. A different, earlier seven-variable version (Willer and Saunders, 2026, Ch.15) uses
k-means with 10 clusters on z-scored growth level and change, inflation level and change, risk appetite, financial conditions and
their change; for example Stagflation (loose) n = 23 and Recession n = 48. The two versions differ in variables and counts, so
do not mix their centroids.

Regime-analog IC horse race (Saunders, Willer, 29 Oct 2021; monthly, 1979-2018 rolling): IC and long-short IR by specification: levels 0.0448 / 0.29; changes 0.0545 / 0.33; levels + changes 0.0495 / 0.35; plus risk-aversion variables (equity vol, credit spreads) 0.0758 / 0.53, described as a 70% IC improvement. Portfolio tests lag the regime variables one month, use an expanding window, monthly rebalance, an 18-month half-life covariance.

Stock-bond correlation (Willer and Saunders, 2026, Ch.15): `corr = 7.43 x core CPI - 0.23` (R2 0.22), zero crossing about 3.1% core
on this fit; the authors' rule of thumb is 2.5%.

## 5. Information-ratio arithmetic (Grinold and Kahn, 1999; Tulchinsky et al., 2015)
- `IR = IC x sqrt(BR)`. A 200-stock semiannual manager with IC 0.04: IR 0.8. Adding 100 semiannual IC 0.03 names gives `IR^2` 0.82
  (+28% of value added). With the same IC, trading 4x more often gives about 2x the IR if the bets are independent.
- Signal combination with decay: diversify with the older score if `IC_2 > rho IC_1`; hedge with it if `IC_2 < rho IC_1`.
- 20 tries gives a 64% chance of at least one `t >= 2`. IR above 2 on public information is usually an error. IC of 0.10 is right
  about 55% of the time.

## 6. Central-bank text classifiers (J.P. Morgan, 26 Apr 2023 and 2 Jul 2024)
Detail is in [macro-central-bank-nlp](../../macro-central-bank-nlp/SKILL.md). Model-side numbers: relevance model 83% OOS; hawk-dove
80% on dovish (1-2) versus hawkish (4-5), 48% exact five-class (2023). RoBERTa ensemble (2024): 2-class accuracy 0.90, 5-class
0.58, log loss 1.01, windowed log loss 0.21, ranked probability score 0.09; the old BERT 0.80 / 0.49 / 1.24. Log loss fell from
about 0.75 at 1,000 labels to about 0.56 at 3,800 (target at least 4,000 per central bank). Frozen large models with a small head
performed about as well as BERT with one unfrozen layer; few-shot chat prompting was far worse (2-class 0.66).
