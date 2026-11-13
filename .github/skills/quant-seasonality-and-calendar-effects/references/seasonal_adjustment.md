# Seasonal factors, seasonally adjusted linkers, residual seasonality in data

Companion to [SKILL.md](../SKILL.md). Linker mechanics and breakeven trading are in
[infl-breakevens-and-linkers](../../infl-breakevens-and-linkers/SKILL.md); this file keeps the seasonal-factor
estimation and the adjustment formulas that other skills should call.

## 1. Estimating monthly seasonal factors

Table: `infl_seasonals` (percent deviation of the NSA index from trend, 12 values, sum about 0; read only sets whose
`valid_from` precedes the as-of date).

1. Smooth the NSA index with a trend filter. Factor for month m = average over years of (actual - trend) as % of trend, then demean so the 12 factors sum to 0. `seasonal_factors()` in `scripts/seasonality.py` does this with a centred 2x12 moving average (ratio to moving average).
2. Filter choice: Hodrick-Prescott is simple but new data revises the past filtered values; X-12/X-13-ARIMA handles movable feasts such as Easter and is the more realistic choice. A short window lets one-off events (strikes, transport disruption) survive in the factors; a long window hides drifting patterns (example: Black Friday) (Düring, Fixed Income Trading and Risk Management, 2021).
3. State-space alternative with time-varying factors: seasonal component c_t = -sum_{s=1..S-1} c_{t-s} + noise, so S periods sum to zero in expectation; combine with a local level (y_t = a_t + e, a_t = a_{t-1} + e_a) or local linear trend (Murphy, Machine Learning: A Probabilistic Perspective, 2012).
4. Size: the seasonal swing is the same order of magnitude as trend inflation, so over active horizons linker inflation returns are driven by seasonality, not trend (Düring, 2021). Approximate visual reads of the published factors, % of trend: euro area ex-tobacco HICP Jan -0.7, Feb -0.5, Mar +0.1, Apr-Jun +0.35 to +0.4, Jul-Aug slightly negative, Sep-Oct +0.1, Nov -0.1, Dec 0; US CPI NSA Jan -0.55, Feb -0.35, Apr-Jun +0.3 to +0.4, Jul-Sep +0.2 to +0.3, Nov -0.3, Dec -0.7 (Düring, 2021, figure reads).
5. Validate: a cyclical cubic smoothing spline on clean prices of each linker, each rebased to 100 at the start of each year, shows the market prices index seasonality into clean real prices (US about 10y, 81,500 observations; Germany about 7y, 8,500) (Düring, 2021). Japan CPI ex fresh food has seasonal variability "well in excess" of trend; consumption-tax hikes (2014, 2019) are known index jumps, handled by the time-varying projection below.
6. Residual seasonality remains after official adjustment and adjustment over-compensates after large shocks (financial crisis, pandemic) (Willer and Saunders, Trading Global Macro Markets, 2026).

## 2. Index projection and real curve

- Simple projection: I_f = I_t x (s_f / s_t) x exp(iota (f - t)); s = monthly seasonal factors (index form, centred on 1), iota = zero-coupon breakeven. Specify on monthly prints, then apply each bond's reference lag and interpolation.
- Time-varying: I_f = I_t x (s_f/s_t) x exp((f - t) x (iota_0 + iota_l x ((f-t)/tau) / (1 + (f-t)/tau))); iota_0 = latest annual print, iota_0 + iota_l = long-run rate, tau = convergence timescale (the source's figures use tau = 3; it is irrelevant when |iota_l| is small). Avoids a jump in overnight inflation.
- Real discount factor: R_f(t) = D_f(t) x (s_t/s_0) x exp(iota t); linker price P = (I/I_0) x sum R_f(t_i) x C_i. Nominal spline with the inflation model and seasonality stacked on top; fit iota (or iota_l and tau) to linker prices. The linear price form holds only without a floor or with a far out-of-the-money floor; a near-the-money deflation floor raises cash flows above the linear value (Düring, 2021).
- Seasonally adjusted price: SAP = P x S_v / S_m, with P the real clean price (strictly the dirty price), S_v the seasonal index at the value date and S_m at the maturity reference month, lagged and interpolated like reference values. Compute yield from SAP; the seasonally adjusted breakeven follows. Exclude issues under 1y (BofA Global Research, Welcome to the real world: Global inflation-linked primer, 22 Jul 2025). `sa_price()` in the script.
- US Treasury inflation-protected par curve: BLS monthly multiplicative factors linearly interpolated to daily (J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024). Inflation swap valuation: 12 monthly multiplicative factors, remarked monthly (Deutsche Bank Index Quant, DBIQ Interest Rate Curve Creation Process, 2 Feb 2023).
- Index-curve seasonality in a curve library: a seasonality curve with higher (lower) index rates for one period then lower (higher), so the impact nets out, composited with the index curve (Darbyshire, Coding Interest Rates, c. 2024).

## 3. Breakeven distortion and rich/cheap

- Breakeven = average index growth between settlement and maturity reference dates. Settling on a seasonally low index raises the breakeven; maturing on one lowers it; any non-integer-year span is distorted, shrinking with maturity. An exact IRR breakeven without adjustment has "somewhat illusory" precision (Düring, 2021).
- Value sits in the months that set the maturity reference value. Toy case: all inflation in April gives a saw-tooth real curve; sine seasonality on a 2% trend gives an 18-month holding a 5% uplift, i.e. 1.05^(1/1.5) - 1 = 3.3% annualised (BofA, Welcome to the real world, 22 Jul 2025).
- Aged swaps need adjustment: a strong first six months can leave a 4.5y rate below the 5y on an unchanged curve. Do not linearly interpolate whole-year quotes.
- New linker issues come in January/February, April and July with their own seasonality; compare rich/cheap only on the same spline, or seasonally adjust and compare Z-spreads (BofA Global Research, UST RV Primer, 2 May 2022).
- Illustrative adjustment (US figures above, not a quote): value date in January (S_v = 0.9945), maturity referenced to April CPI (S_m = 1.0035). SAP = 100 x 0.9945 / 1.0035 = 99.10: an April-maturity bond that looks 0.90 rich on NSA prices is fair after adjustment. Naive spline residuals for July-maturity TIPS look rich (they pay on seasonally high April CPI) and April maturities look cheap (they pay on January CPI): naive short-maturity spreads of about -30 to +13 bp fall to within a few bp after adjusting (Düring, 2021, figure reads). Remaining residuals come from the parsimonious model, the unmodelled deflation-floor value of new issues, and consensus seasonality differing from the filter estimate.
- Zero-coupon inflation swaps at integer years and the 5y5y forward show a seasonal pattern tracking the inverted linker price pattern; in theory neither should (Düring, 2021).
- Euro: German breakeven trades very close to French breakeven once seasonality-adjusted; the German price swing is much larger than HICP seasonality would justify.

## 4. Seasonal adjustment of macro data used as signals

- Compare each weekly print with the same week in earlier years; read continuing claims year on year (J.P. Morgan, US: Jobless claims continue to deliver positive labor signal, 13 Aug 2026).
- Initial claims rise every mid-August (residual seasonality) and are revised up consistently (Citi Research, The resilient narrative of US resilience, 21 Aug 2026). Seasonal adjustment can flatter a print (late-July claims low).
- Existing home sales carry large residual seasonality (big winter declines): use price trends and the sales-to-new-listings ratio (Citi Research, Canada Economics Weekly: Data lull comes to an end, 13 Aug 2026).
- Promotion timing distorts seasonally adjusted retail sales: average across affected months (June-July) and use a 3-month annualised pace (J.P. Morgan, United States weekly, 14 Aug 2026).
- Use year-on-year changes to remove seasonality in level-based signals, and point-in-time data: aligning January data with revised January data is look-ahead (Tulchinsky et al., Finding Alphas, 2015). For sets of seasonal factors use the `valid_from` rule above.

## 5. Seasonal RV on bond futures (a tested template)

Ten-year rolling seasonals on US, Canada, UK, Japan and euro-area bond futures (Willer and Saunders, 2026):
- Absolute version: long/short each market by whether the current month's median return is above or below the median across the 12 months; gross leverage 100%. Added no value.
- Relative-value version: long markets with higher seasonal medians, underweight those with lower ones; total leverage 100%. Added modest value (reward-to-risk 0.66 vs 0.52 long-only across G7 futures).
- Equity rules from the same source for contrast: Halloween (hold 31 Oct to 30 Apr) had active IR 0.71 vs 0.48 out of sample since 1990; the November-December rule (long if January-October return > 8%) was used out of sample for more than 5 years; the December effect has faded since 2005.
- Lesson: the cross-sectional (relative) seasonal survives better than the absolute one; use it as a tilt inside an RV book, never as the book.
