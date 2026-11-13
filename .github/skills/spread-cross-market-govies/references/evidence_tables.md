# Evidence tables for cross-market government bond spreads

Numbers as published; all backtests are gross of costs unless stated. Use them to calibrate expectations, not as
forecasts. Orientation: IR = information ratio; residual = actual - model (positive = cheap).

## 1. Global 10y RV with a state-space factor model (BofA, US Rates Watch: Monthly rates models)
Model: state x_t = B x_{t-1} + w_t, observation y_t = Z x_t + v_t, w ~ N(0,Q), v ~ N(0,R); factors fixed a priori, Z
constrained so factors read as Global and DM blocs; fitted to 22 DM/EM 10y yields. `z = (residual - average residual) / SD`.

| Market | Actual % | Model % | Resid bp | z | Residual SD bp (where given) |
|---|---|---|---|---|---|
| US | 4.24 | 4.45 | -21.7 | -0.7 | |
| UK | 4.53 | 4.23 | 29.6 | 0.9 | |
| Canada | 3.40 | 3.51 | -10.8 | -0.5 | |
| Japan | 1.55 | 0.77 | 78.1 | 3.3 | |
| Australia | 4.32 | 4.14 | 17.1 | 0.5 | |
| Switzerland | 0.33 | 0.67 | -33.8 | -1.8 | |
| Germany | 2.68 | 2.53 | 15.0 | 1.0 | 15.4 |
| France | 3.35 | 3.23 | 11.4 | 1.0 | |
| Italy | 3.51 | 4.08 | -56.9 | -1.1 | 46.1 |
| Spain | 3.26 | 3.27 | -1.5 | 0.1 | |
| Greece | 3.35 | 3.36 | -0.8 | 0.2 | 149.7 |

(BofA, Monthly rates models Aug 2025 edition, 4 Aug 2025; Austria -1.2, Netherlands 0.1, Belgium -0.2, Ireland -0.1,
Portugal 0.4 z.) Earlier snapshots: Apr 2025 Canada -3.0, Japan +2.7, Switzerland -1.5; May 2025 Japan +3.4, UK +1.5,
Canada -1.5, Switzerland -1.8 (BofA editions of 7 Apr and 12 May 2025). Takeaways: the same markets (Japan, UK, France, Germany
cheap; Canada, Switzerland, US rich) stayed extreme for months, so these are tilts with slow reversion. Because
residual SDs range from 15bp (DE) to 150bp (Greece), rank by z, not bp. Late cycle, USTs should trade fair to rich vs global
yields; a material sell-off needs global bearish momentum or US decoupling (same series). 10yT macro fair value about 4.2-4.25% vs global fair value about 4.40% in Apr 2025.

## 2. Systematic cross-market signals (long-short pairs on currency-hedged 10y)
| Source | Signal | Universe / start | IR or result |
|---|---|---|---|
| JPM, Investment Strategies 15 (Mar 2006) | 10y - 1m carry, long highest / short lowest, monthly | 8 markets (US, UK, CA, AU, DE, JP, DK, SE) from 1988 | IR 0.78 (1 pair), 0.58 (2 pairs), 0.69 (3); 88-95 only 0.33-0.50; 2000+ 1.47; total 5.0% p.a. = carry 3.2 + capital 1.8; correlation to equal-weight hedged portfolio 0.05 |
| JPM, Investment Strategies 31 (Jan 2007) | pair carry-to-risk, risk target 100bp per trade | 8 markets x 5 maturities (2,5,7,10,30y) from 1989 | cross-market only 0.83 / 0.93 / 0.94 / 0.91 (1-4 trades); curve only 0.64-1.08; 50/50 cross-market + curve (2 each) 1.33 vs best-of-both 1.06; return correlation curve vs cross-market 0.06; constant risk target (0.94) beats scaling by carry/risk (0.60) |
| JPM, Rule-based Fixed Income (Nov 2012) | pooled regression, variables demeaned cross-sectionally, 7 markets from 2003 | carry coef 2.6 (t 4.1); change in 10y-1y slope 7.4 (t 4.2); real yield 2.2 (t 3.6); adj R2 0.05 | top-2 vs bottom-2 real yield, costs 4bp/pair: return 2.1%, vol 3.2%, IR 0.65 (ex-Japan IR 0.73, beta ~0) |
| JPM, Systematic fixed income (Apr 2015) | five signals on 10Y swaps | 10 markets from 1996 (real yield 2004) | carry 0.56, carry-to-risk 0.65, change in slope 0.48, real yield 0.39, unemployment 0.24; signal correlations low (carry vs carry-to-risk 0.59) so offsetting pairs arise |
| JPM, rule-based updates (Feb 2017 to Jan 2018) | same five signals, 10 markets | annual return / IR since 1996: carry 2.7% / 0.66; carry-to-risk 2.3% / 0.61; slope 1.8% / 0.46; real yield 1.4% / 0.44; unemployment 0.5% / 0.13 | 2017: carry 2.3% (IR 1.1), carry-to-risk 3.5% (1.8), real yield 3.8% (1.6); December 2017 carry and carry-to-risk -1.0% each (carry stays long into sell-offs) |

Rules of use: carry rules are modestly directional (better in bull markets: IR 1.10 bull vs 0.41 bear for the 2006
rule); performance is concentrated after 2000; failures were vol spikes and crowded unwinds (flat 1999-2002, recessions) even
though carry was not low; use the rolling 12m beta of fixed-income-arbitrage / global-macro hedge-fund returns to the
strategy as a crowding kill signal. Diversify curve and cross-market carry; going from 1 to 2 trades helps, more does not.
JPY under yield-curve control: substitute the next-lowest-carry market (GBP in Jul 2017, USD in Jan 2018).

## 3. Hedged-pickup percentile rules (Willer and Saunders, Trading Global Macro Markets, 2026, figure columns)
Duration-matched futures, FX-hedged, "vol matched by yield pickup". Return / vol / max drawdown / active IR.

| Rule | 10th pct | 90th pct | Long/short | Unconditional |
|---|---|---|---|---|
| UST vs Bund (EUR investor pickup) | -0.87% / 2.39% / -22.95% / IR -0.79 | 0.83% / 2.72% / -7.10% / IR 0.60 | 1.70% / 3.62% / -7.21% / IR 0.69 | -0.67% / 5.30% / -29.84% (R:R -0.13) |
| UST vs gilt | -0.73% / 2.85% / -30.28% / IR -0.56 | 0.90% / 2.71% / -6.22% / IR 0.70 | 1.62% / 3.93% / -10.04% / IR 0.63 | 0.39% / 5.83% / -22.59% (R:R 0.07) |
| JGB vs UST (trailing 12m percentile) | -1.88% / 4.50% / -50.41% / IR -0.81 | 0.97% / 3.73% / -11.91% / IR 0.59 | 2.85% / 5.84% / -12.46% / IR 0.72 | -1.33% / 8.34% / -48.42% (IR -0.16) |

Caveats: the text and tables swap columns in places (the text quotes 0.63 and 0.72 as "top" results, which are the long/short
columns); percentile windows for the first two rules are not stated; no costs; no out-of-sample split; carry-factor
behaviour: flat in bear markets (UST-Bund sideways since 2020). Conditioning rule, JGB duration only when US rates are below their
55-day average: return 2.02%, vol 3.21%, IR 0.90, max DD -10.38%, on 48.98% of days; above: 0.56%, IR 0.28; unconditional 2.58%, IR 0.60.
Periphery data-surprise rule (Italian spread returns): DE- / IT+ IR 1.21 (return 1.11%, vol 2.28%, max DD -8.30%, on 16.4%),
DE+ / IT+ 0.76, DE+ / IT- 0.19, DE- / IT- -0.38; buy-and-hold 0.30 (1.42%, 6.04%, max DD -20.21%).

## 4. PCA-residual dislocation backtest (BofA, Many EGBs, one simple value tool, Mar 2018)
- Spec chosen: 11 PCs, 5-day hold, 2x threshold on the dislocation z; no costs. Search: PCs 1-15, holds 1/3/5/7/9 days, thresholds 0.5x-3x.
- Long (cheap) leg hit ratio 56% at 0.5x rising to 71% at 3x; rich leg about 50%.
- By year, long legs / short legs total spread change and hit ratio: 2015 (14 trades) -108bp / +64bp, 71% / 71%; 2016 (33) -110 / -4, 73% / 55%; 2017 (16) -60 / -12, 75% / 50%.
- Average 5-day move fell from about 8bp to 4bp; extending the hold a week almost doubled the average tightening. Best holds 5-9 days (links to supply/coupon/redemption concessions).

## 5. Auction-cycle effect on adjusted spreads (JPM, Follow the cash flow, Sep 2015)
Pre-auction (T-5 to T-1): 1330 trades, 3.4bp average, 67% success, IR 2.5; post (T-1 to T+4): 1.5bp, 60%, IR 1.1; coupon/redemption
dates: 0.4bp, 51%, IR 0.6. Adjusted-spread hedge 3.4bp / IR 2.5 vs non-adjusted vs Germany 2.6 / 1.2 vs outright 2.3 / 1.1 (outrights flattered by the yield downtrend). By country pre-auction IR:
BE 3.0, IT 3.6, FR 2.8, ES 2.4, AT 2.1, NL 1.9, FI 0.7. Year effect: 2011-12 about 6-7bp vs 2014 0.5bp. Italy-Spain switch
since 2014: T-1 IR 1.1, T-2 IR 3.0. Effects are gross of costs, weakened after 2013 and drift in timing, so retest; trade design lives in [bond-supply-and-cashflow-trading](../../bond-supply-and-cashflow-trading/SKILL.md).

## 6. Front-end cross-market residuals (JPM, Talk is Cheap, 30 May 2024)
Model: matched-maturity swap yield spreads to the US regressed on the same global regressors (global central-bank-speak
factors, with the home score replaced by Fed minus own). The Fed-minus-own term was "not particularly influential" after the global inputs:
spreads are governed mostly by the markets' betas to global factors. 1Yx1Y cheapness vs model (R2 / residual bp / z):
USD 0.840 / 186.3 / 2.80; EUR 0.826 / 141.8 / 2.12; CAD 0.846 / 145.6 / 2.54; GBP 0.834 / 192.1 / 2.48; SEK 0.833 / 134.3 / 2.18; NOK 0.814 / 141.6 / 2.46;
AUD 0.862 / 193.8 / 3.15; NZD 0.886 / 174.5 / 2.73; JPY 0.512 / 52.7 / 3.82. All above +2 (a year earlier mildly negative), i.e. the whole
G10 front end screened cheap together, a reminder that a common-factor residual is not cross-market RV.
Related calibration: a 10-point rise in a hawkish-score gap moves the 90-day change in 1y sovereign yields by about +12 to +14bp with a one-week lead, useful up to about 8 weeks and gone by about 13 (JPM, Welcome to the machine, Apr 2023); see [macro-central-bank-nlp](../../macro-central-bank-nlp/SKILL.md).

## 7. Correlations and relative vol
- Weekly yield-change correlation with the US (Willer and Saunders 2026): 2y CAD 0.59, DEM 0.51, GBP 0.43, JPY 0.18; 10y CAD 0.79, DEM 0.71, GBP 0.66, JPY 0.28; DEM-GBP 0.79 at 10y and 0.55 at 2y.
- 5y IRS receiver monthly returns, DM, 1999-2018 (Macrosynergy): mostly 0.5-0.8 (EUR-GBP, EUR-CHF, EUR-SEK, CAD-USD, AUD-NZD 0.8); NOK-NZD, NOK-USD, NZD-USD 0.5; JPY 0.2-0.3 with everyone. Annualised vol: USD highest DM (3.5%), JPY lowest (~1%).
- Out-of-sample risk-basket hedging cut 3M absolute correlation 0.23 to 0.12 (outright) and 0.25 to 0.13 (relative) but did not lower the SD of hedged returns; active vol targeting (11-day EWMA, monthly) raised excess kurtosis 2.4 to 2.9.
- Cross-market STIR correlations were 0.956-0.987 (Jan 2008-Sep 2011) but -0.821 to 0.338 in Jan-Sep 2011 when the ECB hiked and others did not (Aikin, STIR Futures, 2nd ed, 2012). Non-standard policy suppresses cross-market PC1 correlation (Düring, Fixed Income Trading and Risk Management, 2021).
- Rolling-PCA factor anchor, AUD/NZD (Citi, Asia FX and Rates, 13 Aug 2026): full-period PC1 46.4%, R2 on USD 0.592; R2 about 0.47 before 2023 vs 0.76 after (structural break); without the pegged HKD it fell 0.59 to 0.24 (pegs inflate the USD anchor). Thresholds used: R2 0.70 strong, 0.50 moderate, < 0.10 weak; incremental R2 0.03 "meaningful"; t-stats vs 1.65/1.96.

## 8. Cross-market forecasts and levels cited (context only; verify against current data)
- 10y OAT-Bund beyond 150bp then 140bp, last seen late 2011 (GS, Global Rates Trader, 2 Oct 2026); Citi forecast 95bp 4Q26 avg, 110bp 1H27; BTP 85, Bono 35, Belgium 60, Austria 18, Finland 30, Portugal 35, Greece 73bp (4Q26).
- Gilt-Bund 10y 181bp (Aug 2026), Citi 4Q26 forecast 200bp (Citi, Latest views, 20 Aug 2026); about 175bp in Sep 2026 with a path to under 150bp mid-2027 on net-supply metrics (Citi, European Rates Weekly, 24 Sep 2026). A buy-30y-gilts-vs-Bunds trade stopped at -21bp (181 -> 202).
- A 10y UST at 5.5-6.0% maps to 10y JGB 3.2-3.5% (Citi, Japan Rates Weekly, 2 Oct 2026).
- $ASW vs SOFR, Dec 2024, bp, JP / US / DE / FR / ES / IT: 2y 38 / 20 / 8 / 21 / 21 / 43; 5y 50 / 34 / 7 / 51 / 49 / 76; 10y 70 / 50 / 9 / 91 / 81 / 130; 30y 120 / 82 / 34 / 161 / 172 / 229 (Citi, FX Basis Quarterly, 13 Dec 2024).
- SOFR-ASW of basis-swapped bonds, 17 Oct 2023 (chart reads, bp), 1y / 5y / 10y / 20y: Bunds -21 / -24 / -22 / -3; USTs +1 / +25 / +29 / +64; gilts -31 / -5 / +35 / +84. All curves upward-sloping (CDS curves, haircut schedules); long-end Bunds looked excessively rich (Huggins and Schaller 2024).
