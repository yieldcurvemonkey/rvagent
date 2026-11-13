# Fair-value regressions, screens and drivers (inflation)

Reference for [SKILL.md](../SKILL.md). These are published examples, not parameters to copy: refit on your own
history (see [macro-fair-value-models](../../macro-fair-value-models/SKILL.md) for estimation hygiene) and re-check
betas before sizing, because partial betas swing with regime.

## Regression catalogue (variables, fit, reading)

| Target | Regressors / window | Fit | Reading |
|---|---|---|---|
| US 5y BE | Michigan 1y-ahead inflation expectations, % change 1st-to-12th oil future (curve shape), USDCAD, growth index. Rolling 2y weekly | not quoted | actual 1.76 vs FV 1.91 (Citi, US Rates Weekly: Deal or no deal, 10 May 2019) |
| EUR 5y5y HICP | 0.00 x equity index + 0.40 x 5y HICP + 0.012, 1y | R2 89% | residual about 0, no dislocation. Wait for at least a modest residual (Citi, European Rates Weekly: A narrative shift looms, 17 Mar 2022) |
| EUR 1Yx1Y HICP | 0.85 + 0.465 x 1Yx1Y estr + 0.001 x front Brent, 3M | R2 50% | "screens modestly cheap". TTF gas insignificant alongside oil and dropped (JPM, Monthly Inflation Outlook, 13 Aug 2026) |
| 10Yx10Y (HICP minus US CPI) on 5Yx5Y (same spread) | 6M, y = 0.71x + 17.7 | R2 68% | view sits in 5Yx5Y but expressed in 10Yx10Y because that spread was near 0bp, top of its range (JPM, same) |
| UK 1Yx1Y RPI | 0.3 x 1Yx1Y SONIA - 0.0001 x front Brent + 0.004 x UK gas + 1.94, 12M | R2 87%, SE 8bp | fair |
| UK 5Yx5Y RPI | -0.02 x 5Yx5Y SONIA + 0.003 x front Brent + 0.02 x trade-weighted GBP - 0.008 x GDP-based financial risk index + 1.09, 12M | R2 74%, SE 3bp | about 5bp cheap. Oil beta since the conflict began +3bp per 10 USD/bbl |
| UK 10Y real swap | 0.6 x 2Yx1Y + 0.55 x (1Yx1M/2Yx1M SONIA slope) + 0.0005 x 60d MA of central-bank APF outstanding - 1.6 | R2 71%, SE 7bp | modestly cheap |
| US 30Y ZCIS | daily, 7y: commodity index and its square; 3Mx3M/15Mx3M OIS slope; VIX; (economists minus CPI-implied expectations) = SPF 10Y CPI - (0.908 + 0.277 x 2Y CPI swap + 0.388 x 10Y CPI swap) | R2 87.2%, SE 9.31 | more than 1 SD cheap |
| US 10y BE macro model | f(inflation expectations, inflation risk premium, inflation liquidity premium); real-yield FV derived from the nominal and BE models | | 7 Apr 2025: BE FV about 210bp, market about 10bp wide; RY FV about 2%, market 15-20bp rich. 12 May 2025: BE FV about 215bp, market 10-15bp wide; RY fair. 4 Aug 2025: BE FV 220-225bp, market 5-10bp wide (BofA, Monthly rates models, 2025 editions). Stagflation is hard to capture |
| 2y1y nominal on 2y1y HICPxT (EUR) | separate lines 2010 to Feb 2020, Feb 2020-2021, 2023 onward | | 19 Jun 2025: HICPxT 187bp vs nominal 224bp on the 2023 line. 2y1y is the market-implied neutral policy rate (Nordea, EUR rates: Risk/reward favours receiving ECB meetings, 19 Jun 2025) |

Rules that came with them: drop a driver that adds no R2 or residual change; refit when directionality flips; macro BE
and real-yield models break under non-economic buying (QE, foreign official demand), so include the central-bank balance
sheet and a global PC1, or use sign priors; report model values net of desk charges.

## Global breakeven structure

- PCA of 10y BEs (US, UK, AU, JP, EU, CA; 6y+ history): PC1 about 85% of variance and tracks oil; PC2 about 9% and tracks
  financial stress and the Fed real-rate term premium; together about 94% (BofA, Monthly rates models, Apr and Aug 2025).
- Directionality: bear-wide/bull-tight moves of 10y BEs against the 10y nominal ("orthodox") are 75-80% of moves
  historically. Apr 2025: expansion/slowdown regime odds 14%/86%, current orthodox share 79% vs 75% history (std 19).
  May 2025: 34/66, current 88%, model confidence 77% (BofA, same). Use the share as a context flag for how "normal"
  the BE/nominal co-movement is; the source gives no trade rule from it.
- Real/BE shares of nominal moves: early cycle about 50/50; late cycle real yields are 70-80% of the nominal move
  (BofA, To everything there is a season, 23 Jan 2022).

## Cross-sectional real-yield signal (currency-hedged 10y swaps, 7 markets since 2003)

Variables demeaned cross-sectionally. Real yield = 10y swap minus 10y consensus inflation forecast: coefficient 2.2
(t 3.6), so 100bp more real yield predicts 2.2bp/month of outperformance. Carry 2.6 (t 4.1); change in slope 7.4 (t 4.2);
adjusted R2 0.05. Long top-2 vs short bottom-2 real yields, monthly, 4bp costs: all 7 markets return 2.1%, vol 3.2%, IR
0.65, hit 55%, beta 0.4; excluding Japan 2.2%/3.0%/0.73/59%/beta 0.0. Real yields fail as an outright duration signal
(secular downtrend) but work cross-sectionally; a single low-vol, low-real-yield market (Japan) injects a directional
bias (JPM, Rule-based Fixed Income Monthly, 2 Nov 2012).

## Screens

- Auction/linker dashboard: 3m z-scores of real yield, BEI (with 1w change), "vs surrounds" (fly against the
  neighbouring linkers) and the spread to nominals. Buckets: below -2 rich; (-2,-1]; (-1,0]; (0,1]; (1,2]; above +2 cheap
  (Citi, Morning Call, 12 and 19 Aug 2026).
- IOTA screen: each euro linker's z-spread IOTA and its z-score against the 3M range. Directionality check: regress IOTAs
  on matching nominal par spreads vs Germany over 1M/3M/6M. Small, choppy betas and weak R2 mean IOTAs trade on linker
  supply/demand, not risk (JPM, Monthly Inflation Outlook, 13 Aug 2026).
- TIPS asset-swap screen: front-end TIPS ASW with 3m and 1y z-scores next to the same-maturity nominal ASW. Look for
  TIPS that cheapened more than the nominal (Citi, US Rates Weekly: All it takes is a little push, 4 Oct 2019).
- Carry table: RY and BE carry per forward month from CPI forecasts and repo, plus carry-adjusted weekly changes and the
  ZC swap minus BE spread, for TIPS, EUR and UK linkers (Citi, European Rates Weekly, 17 Mar 2022).

## Cycle and driver facts (US)

- BEs fall into deep recessions then rebound fast; rise before the first hike and early in it; fall once hikes are
  in earnest; widen in soft-landing easing cycles (2024). In stress real yields spike while nominals rally, which
  depresses BEs (last 2008 cut, 2020), so short-BE helps into hard-landing cuts. 2y BEs started falling about 1 month before
  the 10y yield peak (median); oil had rallied more than 20% in the 3m into the median peak (Willer & Saunders, Trading
  Global Macro Markets, 2026, ch.5-6).
- Overweight TIPS vs nominal index only when copper is above its 55dma (IR 0.81, return 1.96%, vol 2.42%, maxDD -4.73%)
  or oil above its 55dma lagged 1 day (IR 0.63) vs unconditional IR 0.23 (return 0.86%, vol 3.67%, maxDD -19.09%). At
  TIPS-index duration (about 4.5-5y) the business-cycle effect (copper) dominates oil's direct effect, which matters more at
  the short end (Willer & Saunders, same).
- 252d rolling correlation of daily changes in 5y CPI swaps vs the S&P 500 was the most negative in two decades: BEs can
  fall with risk assets if a real-yield overshoot hits financial conditions (Barclays, Global Rates Weekly: The urgency
  question, 2 Oct 2026).
- A TIPS index return is more volatile than the nominal index despite lower duration (2.57% return, 5.47% vol since
  inception vs 1.71%, 4.75%), and TIPS gave back their gains through the 2022 hikes (cumulative since Jan 2021: +2.7% to Mar 2022,
  +0.1% to Jul 2022) (Willer & Saunders, same).
