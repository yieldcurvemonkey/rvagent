# Published rule backtests: designs, results, caveats

Companion to [SKILL.md](../SKILL.md). Use these as **base rates and design templates**, not as live expectations: most
are gross of costs, carry, stops or intraday moves, have no formal out-of-sample split, and several rest on fewer than 25
events (Willer & Saunders, Trading Global Macro Markets, 2026). "bp" = basis points; IR = information ratio.

## 1. Mean-reversion and residual rules

| Rule (source) | Design | Result | Caveat |
|---|---|---|---|
| PCA-residual swap-spread dislocation index (BofA, A simple framework for swap spread RV, 2 Jun 2016) | Daily PCA on 1y of 2y/5y/10y/30y spreads; residuals from first 2 PCs; z over 250d; `DI_t` = 10d MA of `sqrt(mean_i z_i^2)`; if DI > threshold buy cheapest, sell richest, 1:1 in bp; next-close marking; residual half-life ~20 days | US threshold 1.0: +267 bp cum, Sharpe 1.2, 1,750 days, avg hold 32d; threshold 2.0: 51 bp, 0.4. Germany 1.0: 869 bp, 2.4; 2.0: 554 bp, 2.8 | No costs, carry, stops, intraday moves; US Sharpe falls with threshold, German rises |
| Cross-sectional EGB residual rule (BofA, Many EGBs, one simple value tool, 21 Mar 2018) | 42 spreads (7 countries x 6 tenors) vs Germany; daily expanding-window PCA, OLS of each spread on N PCs; dislocation index = cross-sectional std of residuals, z on expanding window; buy cheapest/short richest, fixed hold. Search PCs 1-15, hold {1,3,5,7,9}d, threshold 0.5-3.0x; chosen 11 PCs, 5d, 2x | 2015: 14 trades, long hit 71%; 2016: 33 trades, 73%/55%; 2017: 16 trades, 75%/50%. Long hit ratio rises 56% (0.5x) -> 71% (3x); short (rich) signals ~50% | Expanding windows adapt slowly to regime change; the grid search is a trial-count issue |
| Hedged-fly weight comparison (QF Stack Exchange, 2s5s10s fly directionality, 2018) | Fit weights in-sample Jan-Jun 2016, evaluate Jul-Dec 2016: regression residual (no intercept), PCA divide-by-PC1, PCA minimal-change, min-VaR wings | OOS std: raw 0.840, regression 0.761, PCA 0.869, min-VaR 0.763 (n = 116). Weights PCA -2.215/2/-0.648; min-VaR -1.650/2/-0.794; regression -1.960/2/-0.756 | PCA-weighted had the highest OOS std; loadings change with regime |
| Simple fly threshold (Lehman, Macro-awareness in RV trading, Oct 2003) | Buy 5s when 2s5s10s fly > +5 bp, sell < -5 bp | Profitable Jun 1999-Mar 2001 (~5 bp or less per turn); same rule lost ~15 bp over 5 months from Mar 2001 as the fly trended to +20 bp | Regime change; level trends kill mean-reversion |
| Generic z state machine (Chan 2009; Brenndoerfer 2025) | Window 60 (or train on first 252d); enter 2, exit 0.5-1, stop 4; prior-day hedge ratio | Pair template: Sharpe 2.3 train / 1.5 test at 2/1; 2.9 / 2.1 at 1/0.5; no costs | Parameter choice is a hyper-parameter; test on a plateau |
| Optimal entry/exit bands (Leung & Li, Optimal Mean Reversion Trading, 2016) | Levels solved from OU parameters, costs, stop: faster reversion -> narrower band; higher vol -> wider; higher exit cost -> higher take-profit; stop at/above `L* = (mu theta + r c_s)/(mu + r)` makes immediate liquidation optimal; a holding-cost penalty q maps into entry cost `c_b + q/r` | Re-derive levels when implementing (the printed example is internally inconsistent) | Use as a calibration, not as a result |

## 2. Event and supply designs
- **Entry/exit lag grid** (BofA, UST auction primer, 8 Mar 2024): per cell average bp, SD, hit ratio, Sharpe = average/SD, Score = hit x Sharpe. Last 12 10y auctions: best 2s10s steepener entry -9 / exit -3 +3.5 bp; best flattener entry -3 / exit -1 Score 52%, +2.9 bp; 2s5s10s long belly entry -3 / exit -1 Score 49% (+2.1 bp). 2022 grid (BofA, UST RV primer, 2 May 2022): 2s10s steepeners mostly negative; short belly entry -8 / exit +10 +13.3 bp.
  Contrast with the last 6 months; "the expected dynamic is often overwhelmed by the macro context".
- **EGB supply (Jan 2010-Aug 2015, before costs; JPM, Follow the cash flow, 15 Sep 2015)**: pre-auction T-5 -> T-1: 1,330 trades, 3.4 bp, 67% hit, IR 2.5; post-auction T-1 -> T+4: 1,342, 1.5 bp, 60%, IR 1.1; coupon/redemption: 344, 0.4 bp, 51%, IR 0.6.
  Hedge type pre-auction: beta-adjusted vs Germany 3.4 bp / 67% / IR 2.5; non-adjusted 2.6 / 59% / 1.2; outright 2.3 / 56% / 1.1. IT-ES switch since 2014: T-1 0.7 bp IR 1.1 vs T-2 2.0 bp IR 3.0 (76 trades each). Robustness grid: holding window, hedge type, bucket, country, year; regress P&L on event size and bid/offer dummies.
  Alpha fades when liquidity normalises (2013-14); outright versions can reflect the yield trend only.
- **Forward-return event study** (BofA, Technicals Explained, 14 Jan 2025): forward % change at 5-80 trading days after each signal: up/down counts, average, median, min, max; condition on the 200d slope. Sample sizes 14-17. US1 golden cross since 1977: 34 signals, higher in 68% at 40-50 days, +1.44% at 45 days; with a rising 200d: 12 of 14, +2.49%; death crosses little relevance. "Good for context, not necessarily entry AND exit strategy."
- **Percentile-bucket forward moves** (BofA, US Rates Watch, 10 Mar 2025): bucket an indicator into 5y-percentile deciles; report the subsequent 1m-6m move of the target less the average, in bp and z; classify follower / contrarian / no signal. Aggregate fund PCA duration at the 80-90 percentile: 10y moves -17/-28/-43/-58/-65/-88 bp at 1m-6m (follower). CTA beta at 90-100: +6 to +58 bp but exhibit says no clear signal.
- **Carry bucket test** (JPM, Monthly Inflation Outlook, 13 Aug 2026): 5y breakeven widener when ex-ante 1M carry exceeds a threshold, hold 1 month; carry below -9 bp: 34 obs, hit 12%, avg -13.4 bp; above 9: 261 obs, 59%, +5.2 bp; overall "limited empirical evidence" that carry predicts.
- **Seasonal/calendar designs** (Chan 2009): enter on a fixed date, exit on another; roll to the next trading day at entry and previous trading day at exit on holidays; year-by-year P&L with intra-trade max drawdown. Intra-trade drawdowns can dwarf P&L in winning years.

## 3. Carry, duration and cross-market rules

| Rule (source) | Result |
|---|---|
| Cross-market 10y carry, monthly, buy highest 10y minus 1m slope / sell lowest, currency-hedged (JPM, Investment Strategies No. 15, 9 Mar 2006) | Since 1988 IR 0.78 / 0.58 / 0.69 for 1 / 2 / 3 pairs; since 1996 1.33 / 0.94 / 0.94; ~2/3 of return from carry |
| Spread carry-to-risk ranking, top 1-2 pairs, inverse-vol to 100 bp annualised risk, monthly (JPM, Investment Strategies No. 31, 11 Jan 2007) | IR 0.94-1.10 since 1989; 50/50 curve + cross-market IR 1.33; weekly rebalance no benefit (0.70-0.90); monthly vol data beat daily/weekly; constant risk target beat carry-scaled sizing |
| Duration overlay: PMI 15%, revisions 15%, bond momentum 20%, equity momentum 15%, carry-to-risk 35% (JPM, Simple rules to trade duration, 2 Oct 2012) | Equal-weight combo IR ~1 vs average single 0.6; in-sample optimised 1.07 (look-ahead) only slightly better; chosen weights since 1990: return 2.5%, vol 2.2%, IR 1.13, hit 65%, long 57% / short 43%, beta ~0. Rebalance day swings IR 0.3-0.7 |
| Rules update (JPM, Update on systematic rule based trading strategies, 10 Jul 2017) | Combined IR 1.20 since 1998; EUR 3Mx10Y gamma combination IR 2.50 vs always-short 1.04; fading z-score extremes IR -0.3. Carry rules break under yield-curve control; short-gamma rules lose when central-bank rhetoric shifts |
| Cross-market real-yield long-short, 2 highest vs 2 lowest monthly, 2 bp per currency (JPM, Rule-based FI Monthly, 2 Nov 2012) | 7 countries IR 0.65, beta 0.4; excluding Japan IR 0.73, beta 0.0. Survey inputs held constant between discrete updates |
| IRS receivers 2000-Feb 2018 (Macrosynergy) | See [pnl-recipes-and-market-notes.md](pnl-recipes-and-market-notes.md) section 3 |
| MA rules on a US 7-10y index (Willer & Saunders, 2026) | 55d: 2.41% return / 4.68% vol / return-to-risk 0.52 (active IR 0.68, 57% on) / max DD -13.35%; return-to-risk 22d 0.41; 200d 0.46; 252d 0.37; buy-and-hold 0.41 with -27.48% DD; a consistent 55d parametrisation limits overfitting |
| 55dma conditioning (Willer & Saunders, 2026) | Long JGBs only when UST yields below their 55dma: IR 0.90 vs 0.28 above; FX-hedged EM local rates on only when US 10y and DXY both below 55dma: IR 2.47 (both above -1.50). Report active IR and % on, against the unconditional IR |
| Expanding-window bond timing, 1965-95 (Salomon Brothers, Understanding the Yield Curve Part 4, Aug 1995) | 20y minus 1m bill, monthly: scaled 8.64% / Sharpe 0.68 vs 1/0 4.16% / 0.53 vs always-bond 0.67% / 0.06; in-sample scaled 11.15% (gap = data snooping); OOS sign correct 61% of months |

## 4. Convexity and volatility backtests

| Study (source) | Design | Result |
|---|---|---|
| Delta-hedged forward flattener, $100K DV01, yearly roll, 25 bp hedge (Citi, Trading long-dated convexity, 9 May 2019) | Costs one way 0.75-1.0 bp initiation, 0.3-0.4 bp hedge/roll | avg daily $K / daily vol $K / Sharpe: 10y5y/15y15y 0.67/195.3/0.05; 10y10y/20y15y 3.20/208.5/0.24; 10y10y/25y10y 5.40/247.6/0.35; 20y5y/25y10y 4.09/219.3/0.30. All profitable; Sharpe flat for 15-30 bp thresholds. The source gives two different sample start dates (2004 in text; 12/31/2013-5/7/2019 in figure notes) |
| 10y10y/25y10y vs vol (Citi, Deal or no deal, 10 May 2019) | monthly P&L vs 1y10y vol changes | correlation ~26%, skew ~0; contrast delta-hedged 1m10y straddle selling Sharpe ~0.84, skew ~-3 |
| Short-gamma 1997-2017 (Citi, The art of gamma hedging, 12 Mar 2018) | sell daily, hold to expiry | 1m10y Sharpe 0.48 daily-hedged, 0.84 at 25% delta threshold, 0.43 unhedged; 3m10y 0.71; 1m30y 0.40; 3m2y -0.59; 1m2y 0.08. Swap bid/offer assumption 1.6 bp (1995-H1 1998) to 0.3 bp (2017-18) |
| Flattener vs 1Yx30Y straddle after Jan 2009 (JPM, An option by any other name, 3 Feb 2017) | Enter flattener, sell straddles sized so premium = carry over 1y; daily initiation | 25Y/20Yx5Y vs 30s/50s: cheap-gamma 100% vs 70%, hit 86% vs 56%, avg +11.4 vs +10.4 bp, carry +1.1 vs -100.6 bp; 5th/95th pct -10/33 vs -140/128 |
| Delta-hedged straddle, EUR 10y10y, Jan 2005-Nov 2021 (Nordea, Bonds & bold, Nov 2021) | monthly roll, full vol grid | return split into convexity, vega, theta, funding; no relation to entry vol level; do not transfer to short expiries |
| Forward curve vs straddle spec calibration (Internal backtest spec v0.4, 23 Oct 2026) | gates G1-G7, defaults s_in 0.25, hysteresis 0.2, confirm 3d, cooldown 5d, max hold 63d, stop 1.5 | Parity anchors: breakeven vol of 10y10y/20y10y in [87, 97]; of 20y5y/25y5y < 25; three-way gamma-source test: signals disagree on only 1.59% of rows and nothing cleared the null; headline books break even at 1.21/1.63/1.35 bp per leg vs 0.25 bp charged |
| ML direction model on UST (JPM, Androids, 22 Nov 2017) | RF on 10y UST, 1-week/1-month holds, repo with specials, quarantine 2017 | Balanced RF Sharpe 1.35 vs 0.38 all-long; typical 10y bid/ask lowers Sharpe by just under 0.1 (~10%); residual Sharpe vs 3,000 shuffles of daily sizing |
| TradeRunner (JPM, 16 Aug 2018) | UST 2s/5s/10s/30s, 5-day hold, walk-forward with 5-day embargo, quarantine 2017-18 | CV Sharpe ~1.1-1.2 vs passive ~1.0; quarantine: 2y passive ~-2.0, classifiers ~-0.8; 2s widths ~0.4 bp, 5s/10s 0.2-0.3, 30s 0.1-0.2 |

## 5. Using these results
1. Copy the **design**, not the headline: lag, hedge type, hold, exits, costs charged.
2. Re-run on your data with the engine in [SKILL.md](../SKILL.md) and compare **after** costs; a published gross Sharpe that does not survive 1x costs is a no.
3. Check the direction: strip the outright trend and compare with always-on.
4. Re-test the best event timing and liquidity assumptions periodically; they drift.
