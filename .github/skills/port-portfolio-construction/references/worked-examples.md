# Worked examples: risk decomposition, VaR-minimising trades, factor neutralisation

All risk numbers use the source's sign convention (paid fixed = positive) unless noted. The skill's convention is the opposite
(receive fixed = positive DV01): flip signs when reusing a source's vector. Linear operations (projection, VaR) are unaffected.
`scripts/portfolio.py --selftest` reproduces the structure of these cases with a rounded covariance matrix.

## 1. Four-bucket book: VaR, allocation, minimising trades
(Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022, Ch 14.)

Buckets 2y, 5y, 10y, 30y. Daily bp-change covariance (from 9 days, a toy sample) Q = [[8.7, 7.4, 5.1, 2.2], [7.4, 7.3, 4.7, 2.2], [5.1, 4.7, 4.9, 1.8], [2.2, 2.2, 1.8, 1.9]].

Desk aggregation: sleeve "spread" (-180, -10, 180, 25) c = 336; sleeve "outright" (-50, -10, -50, -25) c = 291; collective (-230, -20, 130, 0) c = 529 against a sum of 627 and an uncorrelated sqrt(336^2 + 291^2) = 445: implied sleeve correlation about 0.4, so only modest diversification (the source says the risks offset somewhat; with the rounded Q here the three figures are 342, 291, 533).

Book S = (-10,000, +2,500, +10,000, -4,000) DV01:
- c = sqrt(S'QS) = 16,174 (printed code 16,171.64); VaR_5% = 1.644c = 26,590; VaR_1% = 2.326c = 37,620. The script on the rounded Q printed above gives c = 16,402, a 1.4% difference from rounding the source's matrix.
- Euler allocation (1/c) diag(S) Q S = (15,787; -2,602; 1,437; 1,552), sum 16,174. The 5y bucket is a diversifier: reducing it would add risk.
- Single-instrument VaR-minimising trades T_i = -(QS)_i/q_ii and the resulting cut:

| Bucket | S | T | change in c | % of c |
|---|---|---|---|---|
| 2y | -10,000 | +2,948 | -2,524 | 15.6% |
| 5y | 2,500 | +2,304 | -1,247 | 7.7% |
| 10y | 10,000 | -475 | -34 | 0.2% |
| 30y | -4,000 | +3,373 | -688 | 4.1% |

  The best single trade cuts only 15.6%, so risk is dominated by RV (combination) positions, not outright direction. Only one of these may be done at a time.
- Dual trades (subset hedge): 2y&5y (+7,042, -4,812) change -3,410; **2y&10y (+8,562, -9,476) change -11,600 (just over 70%)**; 2y&30y -2,514; 5y&10y (+6,979, -7,234) -4,892; 5y&30y -1,286; 10y&30y (-2,574, +5,800) -1,369. The 2y and 10y pair are the two largest buckets, 2y the most volatile, 10y midway.

## 2. Trader-model book (spreads and flies) and the 50% rule
(Darbyshire, 2022, Ch 16.) Book over 1y..10y, c = 259, VaR_5% 425, VaR_1% 602.
- Par-model VaR-minimising trades are all receives (1y -96 cuts 26%, 2y -61 22%, 5y -38 23%, 7y -33 20%): they only offset direction.
- Trader-model trades: 2y -61 (22%), 2s5s10s -73 (25%; the position is directional: paying it correlates with paying outright), 3s4s5s +98 (10%), 5s7s10s -69 (11%), 7s8s9s -10 (0%). The 7s8s9s position made about 40% of that day's P&L with no VaR contribution, a take-profit candidate.
- Partial multi-trade: receive 30k 2y, 35k 2s5s10s and 35k 5s7s10s (about 50% of each suggestion): c 259 -> 175 (-33%), VaR_5% 287, VaR_1% 406; residual dominated by 3s4s5s (next suggestion +120 for a further 38%).
- Simplified portfolio (compression onto 2y, 5y, 10y): trade (-56, -98, +94) so S_simple = (56, 98, -94); risk falls only ~36% because the book's risks are micro. PCA of the par risk: PC1 33%, PC2 19%, PC3 1% of c.
- PC P&L attribution (Ex 15.5): total 495 = PC2 +411, PC4 +269, PC1 -150, PC3 -35; VaR c = 296 split 6% / 48% / 2% / 44%.
- Rejected PCA-residual trade (Ex 15.4): residuals (-0.7, +0.7, +0.5, -0.9) bp suggested receive 2s5s / pay 10s30s. Rejected because: 9 days of data, PC3+PC4 carry 24%, multipliers (-0.8, +1.2) inside everyday ranges, possible reversal of a prior outlier. Checklist: meaningful covariance, non-trivial neglected-PC dominance, residuals outside normal ranges, a reason why the market moved.

## 3. PC1-neutral 2s5s10s
(Darbyshire, 2022, Ch 23; mirrors the Quantitative Finance Stack Exchange thread "Hedging a trade for PCA component neutrality", Nov 2019.)
PC1 (2y, 5y, 10y, 30y) = (0.65, 0.59, 0.44, 0.20). The source prints S = (-1, +2, -1, 0) with paid = positive, a pay-belly fly. Read in this skill's convention (receive = positive) the same numbers are the receive-belly fly t = (-1, +2, -1, 0), so the table applies as printed to the receive-belly trade; flip every sign for pay-belly. Either way e1't = +/-0.09: DV01-neutral but not PC1-neutral.

| Method | Adjusted vector (belly 1.94) |
|---|---|
| Naive PCA, divide by loadings | (-0.89, 1.94, -1.30, 0) |
| Minimal-adjustment PCA, 30y fixed | (-1.07, 1.94, -1.05, 0), closest to the original weights |
| VaR-minimise 5y only | (-1.17, 1.94, -1.17, 0) |
| VaR-minimise 2y and 10y | (-1.43, 1.94, -0.37, 0): less VaR, but far from a 2s5s10s |
| Multivariate regression on PC1 | (-1.07, 1.94, -1.04, 0), about equal to minimal-adjustment PCA |

Residual attribution: a 10-day move (+17.2, +18.1, +12.5, +8.1) bp gives S.dr about 3.70 equal to S.xi because the PC1 risk is zero. Two PC1-neutral hedge ratios from Huggins & Schaller (Fixed Income Relative Value Analysis, 2024): core EUR sovereign CDS trade of 1.4 Austrian per French from the first eigenvector (profit potential 42bp), and a BTP 2y-5y steepener sized about 5:3 from first-factor sensitivities (potential 73bp).

## 4. Hedge optimisation with costs and a view
(Golub & Tilman, Risk Management: Approaches for Fixed Income Markets, 2000.)
Objective: min alpha x IntRR (or global VaR) + beta x dPDur^2 + tau x TCost - eta x TotRet, with dPDur^2 = sum (hedged partial duration - target)^2 (prevents large offsetting exposures to similar factors), TCost = sum |notional traded| / NAV, TotRet = -sum pdur_i x dF_i under the user's view shock.
- Mortgage 7% 30y $100mm, alpha = beta = 1, tau = 0.01, eta = 0, OAD = 0: short 60 TU, 165 FV, 160 TY and 27 US futures; interest-rate risk 257 -> 75bp/yr; the objective split ~45% IntRR, ~50% key-rate duration, ~5% costs; adding on-the-run Treasuries gives 18bp/yr.
- Benchmark tracking error 51bp; futures-only hedge 17bp; constrained 29bp; with on-the-run Treasuries 6bp. Tilting eta from 0 to -0.05 toward a steepener view moved tracking error 6 -> 10bp and scenario return -2bp -> +3bp, showing the unhedged gap was positioned for a flattener.
- Stepwise VaR at 12/31/98: global VaR 10.63%/yr; US rates alone 9.90%; adding UK rates (stand-alone 1.08%) adds 0.57%; adding the US basis reduces it by 0.45% (negative correlation with rates).
- Exposure targeting with costs (BlackRock's Guide to Fixed-Income Risk Management, 2023): T-cost(w - w0) = sum [a_i |dw_i| + b_i (|dw_i| PV/ADV_i)^q |dw_i|]; minimise T-cost subject to tracking-to-target <= epsilon, so the portfolio only trades when the band is breached. A 22bp tracking-error allowance cut a 96bp inflation-stress loss by 16bp on 10 equal-weight bond ETFs (ex-ante risk 303bp).

## 5. Second-order Sharpe and a diversified three-spread book
(Darbyshire, 2022, Ch 23.) E[P] = S'mu + 0.5 tr(GQ) + 0.5 mu'G mu; Var[P] = S'QS + 0.5 tr(GQGQ) + mu'GQG mu + 2 S'QG mu (G = cross-gamma grid, symmetric; delta ~ N(mu, Q)). Sharpe = E[P]/sqrt(Var[P]) with no risk-free term; > 1.0 "reasonably attractive". Gamma per 10,000 DV01 for EUR 2y3y / 5y5y / 10y20y / 30y20y: 8 / 11 / 41 / 81, so long-end receivers gain most. The first-order roll-down/vol-of-spread matrix is a "false lure" that overstates ratios.

EUR IRS forward spreads (Aug 2016 data): normal vols 36.6 / 58.6 / 68.8 / 67.3 bp; correlations 2y3y-5y5y 0.87, 5y5y-10y20y 0.92, 10y20y-30y20y 0.96, 2y3y vs 10y20y / 30y20y 0.81, 5y5y-30y20y 0.89. First-order pay 10y20y / receive 5y5y +0.80 versus second order +0.42; paying 10y20y / receiving 2y3y falls from +0.25 to -0.01 and paying 2y3y / receiving 30y20y rises from -0.25 to +0.18.
Efficient-frontier optimum over four instruments with -1 <= S_i <= 1 found a Sharpe of precisely 1.0. Diversified three-spread portfolio: weights 50-100-50% retuned to 42-100-86% gave overall Sharpe +0.78; paying 5y5y/10y20y diversifies a book receiving the other two because curves usually steepen and flatten together.
Strategy selection under a capital charge: five independent strategies each c = $100k, VaR_5% $164k, convictions 50-90%, E[P&L] 0 / 15,960 / 31,920 / 47,870 / 63,830; total c = sqrt(5) x 100k = 223.6k. Dropping strategies 1-2 and allocating a carry charge of 9,470 each to 3-5 gives c 173.2k, E[P&L] 115,210.

## 6. Risk decomposition tables
(BlackRock's Guide to Fixed-Income Risk Management, 2023.) Sample portfolio risk 480bp vs sum of stand-alone risks 797bp; rates block CTR 581bp offset by high-yield -77 and investment grade -25; rates stand-alone 909bp; implied rates-HY correlation -242/sqrt(909 x 127) = -0.71. Risk-change attribution for a global HY book, Dec 2018 -> Oct 2019: 607 -> 275bp, of the -332bp change -266 "economy" (covariance) and -66 "exposure" (positions).
Do not demean returns for risk covariance; a static EWMA lags vol spikes; overly responsive risk matrices used for limits force selling at the worst time. PC shapes change with regime, and in crises all spot rates move in the same direction, scaled by their historical vols.

## 7. Return-space PCA and ranking multi-factor models
(Golub & Tilman, 2000.) Scale each factor's vol by the portfolio's partial dollar duration, form the covariance of one-sd dollar exposures, then run PCA: the components are the dominant drivers of *this portfolio's* P&L. Ordinary PCA in one example: PC1 49.7%, first two 83.9%; return-space: 77% and 88%. Treasury PC1 typically 85-95%, first two 93-99%. For duration-neutral curve books the first two components are equally powerful systematic factors, and one-factor risk misstates them badly.
Meucci-style concentration H = 1 - (1/N) exp(-sum theta_i ln theta_i) from PCA risk shares theta; its exponential is the effective number of bets used in `SKILL.md` (Lopez de Prado, Advances in Financial Machine Learning, 2018).
