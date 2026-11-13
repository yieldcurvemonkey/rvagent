# Source scoring schemes (detail for rv-composite-scoring)

Each scheme as published or as reconstructed, with what to borrow and what to avoid. Numbers are as printed in the cited document.

## 1. Nordea J-score / P-score (additive carry/vol + value)
Columns of the forward-swap monitor (Nordea Markets, EUR Rates Flash, 23 May 2019): rate; 1d/5d/1m change each with a sigma
(move / vol); 5d vs 50d average; RSI 14d (highlighted when overbought/oversold, e.g. 1y = 17, 1y1y = 26); 1y carry & roll (a); value of
convexity (b); conv-adj carry & roll = (a)+(b); carry/vol; conv-adj carry/vol (c); z-score (d); **J-score = (c)+(d)**; in-the-money probability vs
history over 1y/3y/5y/10y.
- Universe: 1y, 1y1y, 2y1y, 3y1y, 4y1y, 5y2y, 7y3y, 10y2y, 12y3y, 15y5y, 20y5y, 25y5y, 30y10y.
- Footnotes: receiver swaps, 1y holding period; the value of convexity is added to the current rate and compared with the historical rates of the
  shorter forward (4y1y vs history of 3y1y); 36-month realised vol for carry/vol, z and J; vol averaged over the points spanned in the hold.
- 2024 trade box (Nordea Markets, EUR rates: Pushing back, 17 Jan 2024) adds P-score = 2.34 for 1.70 + 0.64: consistent with c + Z, not defined in the text.
- Borrow: one monitor, one formula, convexity-adjusted carry, vol averaged over the hold. Avoid: reading J across currencies or with a different vol window.

## 2. Goldman projection score (Goldman Sachs FICC and Equities, Global Rates Best Trade Report, 30 Sep 2026)
- 3-factor (Carry, Entry, Trend): "distance from the origin of the orthogonal projection of trade coordinates on the regression plane", plane from least squares on
  attractive trades only (positive carry / negative z / positive trend, or the reverse).
- 2-factor: Carry & Entry uses positive carry / negative z or the reverse; Entry & Trend uses negative z / positive trend or the reverse. The Carry vs Entry chart is a line
  through the origin with negative slope across the receive/pay quadrants.
- Refit per currency and again for the G10 tables: same trade, different score.
- Implementation notes: regress the last coordinate on the others through the origin; score = norm of the projection; unattractive trades unscored. Standardise the
  axes (carry/vol, z, trend z) first or the projection is dominated by the largest-scale axis.

## 3. Percentile scorecard (J.P. Morgan, Global Fixed Income Markets Weekly, 21-22 Aug 2026)
Per market, for the 10y yield and 2s/10s: hawk-dove bias (house 1y-ahead policy forecast vs market pricing), fair-value residuals (vs front-end OIS, balance sheets, vol, past 1y),
positioning (client surveys + active bond fund positioning; long investor positioning = short signal), momentum (trend-following mimic; -20..+20 rescaled /4). Each signal
mapped to -5..+5 by percentile rank in its own history (fair-value models: the standard lookback; others: 2y). Percentile-based and not comparable across markets.
`pctile_to_scorecard` in `scripts/score.py` is `10 x percentile - 5`.

## 4. Rank-and-scorecard models (BofA Merrill Lynch, FX Quant Primer, 1 Oct 2018; method transfer from FX)
- OCTAVE: rank = sum over 4 factors of (1y z-score + scorecard value read off the factor's cross-sectional rank); long the top 3, short the bottom 3. Scorecards by rank 1..10,
  e.g. carry level 4, 3, 3, 0, 0, 0, 0, -3, -3, -4 and rates momentum 3, 2, 1, 0, 0, 0, 0, -1, -2, -3; contrarian factor included only when |z| > 1.
- FORTE: non-parametric two-step sort (equity momentum rank, then a filter score = equity scorecard + sum of 3 z-scores inside the top-4 / bottom-4 baskets).
- Borrow: the cross-sectional rank-to-points table makes the score robust to outliers and lets an extreme value earn no more than a capped number of points; the z term adds
  intensity. Avoid copying the weights: they were fitted to FX.

## 5. Carry/vol hurdle and expected Sharpe
- Barclays (Swap spreads: The Bright Spot in US rates, 30 Sep 2026): carry/vol by tenor and the widening to the 0.25 hurdle (2y 1.15, 3y 1.00, 5y 0.76, 7y 0.52, 10y 0.40, 20y 0.26, 30y 0.24;
  implied spreads -1, -4, -8, -15, -23, -62, -69; widening 13, 17, 20, 19, 15, 1, none shown for 30y).
- Citi (A Holistic Approach to Convexity Across Fixed Income, Jun 2022): ES = expected return / sigma lets swaps, bonds and options sit in one CAPM-type optimisation; historical charts
  are misleading when there is a structural convexity bias (realised history is still useful alongside), so score on ex-ante carry + roll + convexity.
- Huggins and Schaller (2nd ed., 2024): pipeline of fitted curves -> constant-maturity series -> PCA -> one OU per PC (first three PCs) -> flag when the expected Sharpe passes a preset
  threshold -> bond selection -> execution rules (target about half way to the mean, 2-sigma-band stops, scaling). Testing targets and stops in the model can roughly double the expected Sharpe
  of the same trade. Constant-variance OU overstates Sharpe at extreme entries (the bucketing method shows higher variance there).

## 6. Sizing consistency (Willer and Saunders, Trading Global Macro Markets, 2026)
If you rank on carry/vol you must also size by vol, or you do not earn the carry of the low-vol names: global carry ranked and sized by vol scored IR 0.89, ranked on carry/vol
but equal-sized 0.66, simple carry 0.74. Beta-neutral, carry/vol-sized curve carry in commodities had IR 2.04 vs 1.04 for the standard version: the same logic as beta-weighted curve trades in rates.
