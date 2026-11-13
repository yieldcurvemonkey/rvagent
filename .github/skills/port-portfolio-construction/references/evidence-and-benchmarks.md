# Evidence and benchmarks for combining RV trades

Numbers behind the rules in `SKILL.md`. Each block names its source (publisher, title, date). Back-tests are historical
and gross unless stated; use them for *relative* comparisons (equal vs optimised, one theme vs two), not as forecasts.

## 1. Breadth and diversification across carry themes
(J.P. Morgan, Investment Strategies No. 31: Exploiting carry with cross-market and curve bond trades, 11 Jan 2007; monthly since 1989.)

| Universe | IR with 1 / 2 / 3 / 4 trades | Note |
|---|---|---|
| Outright bonds | 0.89 / 1.01 / 0.97 / 0.97 | |
| Outright FX | 1.11 / 1.06 / 1.09 / 1.06 | |
| All possible spread trades | 0.94 / 1.10 / 1.00 / 0.93 | 2 trades chosen by optimising combined carry-to-risk: 1.00 |
| Curve + cross-market pooled | 0.75 / 1.00 / 1.04 / 1.06 | optimised 2nd trade: 0.88 |
| Curve only | 0.64 / 1.05 / 1.08 / 1.00 | optimised: 0.65 |
| Cross-market only | 0.83 / 0.93 / 0.94 / 0.91 | optimised: 1.03 |
| 50/50 curve + cross-market, equal risk | 1.01 (1 each), **1.33 (2 each)** | correlation between themes 0.06 (0.10 for 2 trades) |

- Going from 1 to 2 trades helps; more adds little. Optimising the second trade does not help.
- Constant risk (100bp annualised per trade) beats variable risk: 0.94 / 1.10 / 1.00 vs 0.60 / 0.53 / 0.45 when scaled by carry-to-risk level, and 0.84 / 1.01 / 0.95 when scaled by proportional change. Weekly rebalancing gave no benefit (0.70 / 0.87 / 0.90).
- Vol input frequency changes the answer: best-2 carry-to-risk IR 0.87 with monthly vol data (all trades) vs 0.75 daily and 0.71 weekly. Match the vol window to the holding horizon.
- Correlation to global bond index 0.16, beta 0.12 (R^2 0.03). Return split (all trades) 1.81 total: 1.34 carry and 0.47 capital gains; in bear markets capital gains (-0.79) eat about half the carry.
- Crowding: a high 12-month rolling beta of hedge-fund indices to the strategy preceded the LTCM and 2001 drawdowns and had a significant negative effect on next-3-month returns.

## 2. Combining signals (equal vs optimised)
(J.P. Morgan, Investment Strategies No. 74: Simple rules to trade duration, 2 Oct 2012; J.P. Morgan, Systematic fixed income trading strategies, 13 Apr 2015.)

Signal-return correlations, duration signals (4 markets, since 1998): PMI-Revision 0.59, PMI-BondMom 0.27, PMI-EqMom 0.57, PMI-Carry -0.20,
Revision-BondMom 0.06, Revision-EqMom 0.43, Revision-Carry 0.01, BondMom-EqMom 0.24, BondMom-Carry -0.01, EqMom-Carry -0.17.
Single-signal combined-country IRs 0.50-0.68; equal-weight combination 1.03 (US 0.94, JP 0.27, EA 1.07, UK 0.85); optimised in-sample 1.07.
Chosen weights: carry-to-risk 35%, bond momentum 20%, PMI 15%, earnings revision 15%, equity momentum 15%. Final model since 1990: return 2.5%, vol 2.2%, IR 1.13, hit rate 65%; long-only G-4 futures IR 0.8; a vol-weighted overlay IR 1.3.
Position rule (carry-to-risk): 4 x (percentile over 10y - 0.5), range +2..-2, average |position| about 1.
Direction check: long 57% / short 43%, beta to bond market about 0; the long bias came entirely from bond momentum (excluding it, IR 1.04 since 1990).

10-market version (2015): bond momentum vs equity momentum 0.22, vs PMI 0.41, vs revision 0.21, vs carry -0.21; equity momentum vs PMI 0.55, vs revision 0.61, vs carry -0.28; PMI vs revision 0.62, vs carry -0.42; revision vs carry -0.19.
IRs: PMI 0.59, revision 0.84, bond momentum 0.64, equity momentum 0.66, carry-to-risk 0.59, combined 1.31. Momentum and value are typically negatively correlated.

(J.P. Morgan, Update on systematic rule based trading strategies, 6 Mar 2017; since 1999.)

| Strategy | Return | Vol | IR | Max DD | Hit |
|---|---|---|---|---|---|
| PMI | 2.7% | 4.0% | 0.7 | -7.7% | 57% |
| Revision | 3.3% | 4.5% | 0.8 | -4.5% | 62% |
| Bond momentum | 2.5% | 4.5% | 0.5 | -4.4% | 55% |
| Equity momentum | 3.7% | 5.2% | 0.7 | -6.3% | 54% |
| Carry-to-risk | 2.2% | 4.5% | 0.6 | -13.5% | 55% |
| **Combined** | 2.0% | 1.7% | **1.2** | -1.8% | 63% |

Volatility signals (EUR 3Mx10Y gamma, IR since 2000; J.P. Morgan, 10 Jul 2017): always short 1.04; vol momentum 1.94; carry 1.72; liquidity 1.43; PMI 1.59; combined 2.50.
Cross-market track records net of 4bp per pair (J.P. Morgan, Rule-based Fixed Income Monthly, 2 Nov 2012): 10y duration IR 1.10; cross-market carry 0.51; cross-market mean reversion 0.92; real-yield long-short IR 0.65 (0.73 ex-Japan, beta 0.0).

Composite aggregation (Willer & Saunders, Trading Global Macro Markets, 2026): four +/-1 EUR sub-models with IR 0.42-0.70: "all agree" IR 1.75 (vol 3.6%), "sum" IR 1.17. Baskets beat single pairs. FX five-factor combination: individual R/R 0.55-0.89, combined 1.20 with max drawdown -2.6%.

## 3. Fundamental Law and construction benchmarks
(Grinold & Kahn, Active Portfolio Management, 1999.)
- IR benchmark distribution before fees: 90th pct 1.0, 75th 0.5, median 0.0; "good" 0.5, "very good" 0.75, "exceptional" 1.0. US active bond funds: 90th pct 1.14 (mutual), 1.81 (institutional).
- Ex-post IR for IC 0.1 (law predicts 2.24): equal-weight top-N screen 0.86, improved screen 1.10, stratified 1.27, QP 1.88 (std 0.40, min 0.98).
- Law check: 200 names, semiannual, IC 0.0577 -> 1.154 (strategy simulation 0.8179 x sqrt 2 = 1.157). With ~100%/yr turnover and 0.80% round-trip cost IR falls to 0.70.
- Optimal aggressiveness omega* = IR/(2 lambda): lambda 0.05/0.10/0.15 -> IR 1.0: 10/5/3.33%; IR 0.75: 7.5/3.75/2.5%; IR 0.5: 5/2.5/1.67%.
- Turnover frontier, % of the unconstrained value added kept at 10/20/.../90% of its turnover: 39/59/71/80/87/92/96/98/99.5; implied round-trip cost at those points 8.7/5.1/3.4/2.5/1.9/1.4/1.0/0.7/0.3%.
- Mixing "now" and "lagged" scores (IR 1.5 and 1.2, gamma 0.8): rho 0.7 -> 81.5%/18.5%; rho 0.5 -> 67%/33%, IR 1.59; rho 0.8 -> no gain.
- Timing a single directional bet: expected value added over T independent periods = T x IC^2/(4 lambda); IC 0.10, annual, 4.2bp only. Low breadth means tiny value added unless the bets are frequent and independent. Implement with futures.
- Covariance error: with a true vol of 17%, errors within 1% are harmless and over 3% significant; underestimating at 12% gives negative value added.

## 4. Risk-based portfolios: HRP vs CLA vs inverse-variance
(Lopez de Prado, Advances in Financial Machine Learning, 2018.) 10 assets with 5 noisy copies (condition number 150.9): critical-line puts 92.66% in the top 5 and zero in 3 assets (HRP 62.57%). Out-of-sample Monte Carlo (520 obs, 260 lookback, rebalance every 22 days, 10,000 runs): variance CLA 0.1157, inverse-variance 0.0928, **HRP 0.0671**.
HRP distance worked example: rho = [[1, .7, .2], [.7, 1, -.2], [.2, -.2, 1]] gives D = [[0, .3873, .6325], [.3873, 0, .7746], [.6325, .7746, 0]] and distance-of-distance [[0, .5659, .9747], [.5659, 0, 1.1225], [.9747, 1.1225, 0]]; first cluster = assets 1 and 2 (checked in the script self-test).
A non-singular N x N covariance needs at least N(N+1)/2 IID observations. Averaging M models with correlation rho: variance = sigma^2 (rho + (1 - rho)/M), which tends to sigma^2 as rho -> 1.

## 5. Cross-market correlation and vol (for pairing and basket construction)
(Macrosynergy, Interest rate swap returns: empirical lessons, 2025; monthly 5y receiver returns 1999-2018.)
- Most DM pairs 0.5-0.8: EUR-GBP, EUR-CHF, EUR-SEK, CAD-USD and AUD-NZD about 0.8; NOK-NZD, NOK-USD, NZD-USD about 0.5; NOK-SEK 0.7. JPY only 0.2-0.3 with everyone.
- Return vol: USD ~3.5% annualised (highest DM); JPY ~1%. Relative SD vs USD: JPY ~0.3, AUD 0.8-0.9, NZD 0.6-0.7. Normalising to USD cut the max/min SD ratio across markets from 4.5 to 2.9.
- Active vol targeting (11-day EWMA, monthly) raised excess kurtosis from 2.4 to 2.9; relative vol-normalised returns have fatter tails than outright ones.
- Beta hedge to a risk basket (equities, CDS, carry/EM FX): out-of-sample 3-month absolute correlation fell from 0.23 to 0.12 (outright) and 0.25 to 0.13 (relative); hedged SD did not fall.
- Correlation regimes: S&P-Nikkei rolling 1-year correlation ranged 0.01-0.66 (Narang, Inside the Black Box, 2024); in the Aug 2007 crowded unwind correlations went from 0.1-0.3 to 0.7-0.95 (Brenndoerfer, Dec 2025).

## 6. EUR front-to-back diversification, late 2025
(Nordea Markets, EUR rates: The quiet game, 12 Aug 2025, and How about that outright receiving, 26 Sep 2025.)
- Receive EUR 20y5y/25y5y 6s at -9bp (target -15, stop -7), 12m roll 3.4bp, vol 11.9, carry+roll/vol 0.30; correlations 10s30s 0.62, 5s10s30s -0.54.
- Paid carry flies: 5y7y/12y8y/20y10y carry+roll 14.4, vol 17.0, ratio 0.85, 10s30s correlation 0.34, 5s10s30s -0.44; 9y3y/12y8y/25y5y 13.2, 18.3, 0.73, -0.36 and 0.13. Opposite signs against 10s30s let the pair hedge a vol/curvature view; both struggled because the paid 20y did not rise as 10s30s steepened.
- Complement to steepeners: receive 2s5s 6s at 24bp (target 19, stop 30), 12m carry+roll 6.6bp (carry 3.2, roll 3.5), vol 22.3, ratio 0.30; correlations 10y 0.71, 2y1y 0.52, 2s10s 0.88, 10s30s -0.06. Rejected alternative: receive 2y1y 3s (10s30s correlation -0.54, vol 75.7, ratio 0.35).
- Seasonality and crowding: year-end Dutch pension receiving can hit steepeners and outright positions at once.

## 7. Stock-bond and regime inputs to the diversification assumption
(Willer & Saunders, 2026.) 1-year equity/bond correlation regressed on core CPI: y = 7.43x - 0.23, R^2 0.22; core CPI < 2.5% implies mostly negative correlation, > 2.5% mostly positive (not stable). Risk parity 6.21% return / 10.53% vol / 0.59 return-to-risk vs 60/40 5.15% / 10.51% / 0.49 over the sample; it underperformed after 2020. Ex-post max-Sharpe weights swing to corners (corporate bonds at 100% in some 1970s windows).
A regime-conditional mean-variance objective (BofA Global Research, US Rates Viewpoint: To everything there is a season, 23 Jan 2022) sets w x vol - (1 - w) x return, with w = 0 risk-seeking and 1 risk-averse, and conditions returns on the curve regime (bear-flatteners over the last four hiking cycles).
