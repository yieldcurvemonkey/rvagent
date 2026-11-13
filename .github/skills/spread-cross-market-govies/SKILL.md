---
name: spread-cross-market-govies
description: 'Relative value between government bond markets: UST vs Bund, gilt vs Bund, JGB/ACGB/NZGB/Canada/Swiss/Swedish/Norwegian vs US, and EGB spreads to Germany (OAT, BTP, Bono, OLO, Dutch, Austrian, Finnish, Portuguese vs Bund). Covers spread definition and orientation, DV01/vol/beta sizing, cross-market beta and R2 to the US, intra-EMU fair value (PCA residual, macro/fiscal regression, spread-vs-spread, standardised residual), FX-hedged yield pickup and hedged carry, USD asset-swap yardstick for foreign bonds, systematic cross-market carry, and when not to fade a blow-out. Use when asked about Bund-UST, gilt-Bund, OAT-Bund, BTP-Bund, Bono/SPGB-Bund, JGB vs UST, periphery or semi-core spread widener/tightener, ''is Italy cheap vs France'', FX-hedged pickup or hedged carry for a Japanese or euro investor, cross-market carry, beta to Treasuries, global 10y RV table, EGB dispersion, spread z-score, ''receive Europe vs pay US''. Cross-currency basis level and drivers: xccy-basis.'
---

# Cross-market government bond spreads

Relative value between sovereign curves: one country against another (UST-Bund, gilt-Bund, JGB-UST), the euro-area
sovereign spread block against Germany, and the same trade expressed FX-hedged for a foreign investor. Spreads exist
because curves share a global factor (the US back end sets the tone) but differ in policy path, credit/fiscal
premium, supply, investor base and hedging cost. The trade pays when a spread that is stretched on a *measured*
fair value also has a catalyst or a carry reason to revert. A large residual alone is not a timing signal.

## When to use
- "Is 10y OAT-Bund / BTP-Bund / Bono-Bund / gilt-Bund / UST-Bund cheap, and what is fair value?"
- "Which EGB is cheapest to Germany right now?" (cross-sectional screen) or "BTP vs OAT, which is mispriced?"
- "What is the FX-hedged pickup of UST over Bunds for a euro investor / JGBs for a USD investor?"
- Size a cross-market pair (DV01, vol, beta), or ask how much of a local sell-off is US-driven.
- Choose the short leg of a "long Europe vs short US" type view, or check whether a spread blow-out is idiosyncratic.
- Not here: swap spreads / ASW mechanics ([spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)), CDS-bond basis and adjusted CDS
  ([spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md)), auction-cycle trade statistics
  ([bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md)), swap-curve cross-market forwards
  ([curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md)).

## Conventions (state the order in every output)
- **Spread A-B = yield(A) - yield(B), in bp.** Positive = A cheaper (higher yield) than B. "Wider" = A cheapens vs B.
  EGB spread = country minus Germany. Sources quote UST-Bund both ways (one house prints a long-Bund/short-UST
  spread at -146.6bp, i.e. Bund minus UST; another prints 142 -> 200bp for UST minus Bund). Never copy a level
  without its orientation.
- **Trade labels.** "Widener" = short A / long B (pay A, receive B), profits if A-B rises. "Tightener" = long A / short B.
  DV01 is currency per bp, positive for a long bond; "receive" = long duration.
- **Residual = actual - fitted** (bp). Positive = spread cheap/wide vs model; negative = rich/tight.
- **FX-hedged pickup = hedged foreign yield - home yield**, bp, from the named *investor's* home currency. Negative =
  hedge cost exceeds the yield advantage. Always state home currency, hedge tenor (rolling 3M default) and sector.
- **Compounding before differencing.** Yields come in each market's own convention (UST/gilt street semi-annual, EGB
  annual, JGB simple). Semi-annual vs annual differs by about y^2/4 (5bp at 4.5%), the same size as many residuals, so
  convert both legs to one basis first (`to_annual` in the script; details in [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md)).
- **Schema signs** (`swap_spreads`): `asw_*` stored `govt_minus_swap` (bond cheap to swaps = positive); `spread_*`
  stored `swap_minus_govt` (US convention). Do not mix them inside one comparison; see [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md).
- Yields in pct, spreads and betas' inputs in bp. Betas are of *changes* (bp on bp). FX quotes: `pair` = BASEQUOTE =
  quote currency per 1 base; the script converts to home-per-foreign.

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Constant-maturity government par yields per issuer (US, DE, FR, IT, ES, NL, AT, BE, FI, PT, GB, JP, CA, AU, NZ, CH, SE, NO) at 2/5/7/10/15/30y | `curve_par` with `<CCY>-GOVT-<issuer>` | daily, one snap, >= 3y (5y for PCA) | Fitted or interpolated par, not on-the-run, so maturity is matched |
| Bond-level yields, clean/dirty, coupons, issue size | `bond_quotes`, `bond_static` | daily | For individual-bond switches, coupon and issue-size effects |
| FX spot and forwards (3M default, 6M/1Y optional) | `fx_rates` | daily, same snap as yields | `value_date` gives actual hedge days |
| Cross-currency basis (home leg vs foreign leg) | `basis_swaps` (`basis_type=xccy`) | daily | `leg_a` carries the spread; flip sign if you need the other leg |
| Asset-swap spreads of the bonds | `swap_spreads` (`asw_parpar`) | daily | `govt_minus_swap`, same reference rate as the CCBS foreign leg |
| Money-market rates for the hedge tenor | `rate_fixings` / `curve_par` (OIS) | daily | Rate-differential form of the pickup |
| Policy path and meetings; debt/deficit projections; surprise indices | `cb_meetings`, `macro_series` | per release | Slow-moving fiscal inputs update about twice a year |
| Supply and auction calendar | `auctions` | event-level | Supply context only; trade stats live in the supply skill |

If an input is missing, ask for it or hand off to the `rv-data-engineer` agent. Never invent values. Do not mix
snaps (an Asia vs US close mismatch fakes lead-lag and distorts betas).

## Method

### 1. Pick the spread measure
1. **Yield spread** = y(A) - y(B). Weakness: a maturity mismatch mixes term spread with credit, and it inherits the
   coupon effect, so it does not by itself say rich or cheap (Tuckman and Serrat, Fixed Income Securities 4th ed, 2022).
   Match maturity with fitted constant-maturity par yields (see [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md)).
2. **Bond spread (forward-curve spread)**: s solves `Price = sum_t CF_t / prod_{i<=t} (1 + (f_i + s)/2)`, f_i = benchmark
   6m forwards (semi-annual form; use annual periods for annual-pay EGB cash flows); s < 0 = rich. Read it as extra return over the benchmark curve if rates stay unchanged. Use it for
   EGB vs Bund and for bonds against swaps (same source).
3. **Cross-currency comparison**: use one yardstick, not raw yield gaps (section 5): hedged pickup, or USD asset-swap
   spread of basis-swapped bonds, or (EUR OIS - Bund) vs (SOFR OIS - UST) minus the 10y xccy basis (Citi, Latest views, Aug 2026).
4. **Expected return** of a spread = mean-reversion bp (if it reverts to its 3M mean) + 3M carry and roll. Check that it
   mean-reverts: count crossings of the 3M mean and of "1 SD back to mean" in the last 3M. Not every spread does.

### 2. Size the legs
- **DV01-neutral**: `F_B = -F_A * DV01_A * fx_{B per A} / DV01_B`, DV01 = -(1/10000) dP/dy by +/-1bp central difference,
  each per unit face in its own currency. Higher-DV01 bond trades smaller. Assumes parallel shifts and constant spread
  to the base curve; spread risk remains (Tuckman and Serrat 2022). `dv01_hedge_notional` in the script.
- **Vol-matched**: pick the short so both legs have similar vol, e.g. long EUR 10y vs short CAD 10y (JPM, Rule-based Fixed
  Income, Nov 2012). Alternatively divide each leg's size by its relative SD = SD(local receiver returns) / SD(USD receiver returns)
  (so a low-vol market gets more DV01), EWMA with an 11-day half-life; this cut the most-to-least volatile ratio from 4.5
  to 2.9 (Macrosynergy, IRS returns).
  Approximate relative SD to USD: JPY 0.3, CHF 0.5, EUR/GBP/SEK/NZD 0.6-0.7, AUD/CAD 0.8-0.9 (same source, chart read).
- **Beta-weighted**: regress leg changes (weekly, section 3); h = beta. Daily-data betas understate cross-market
  correlation through time-zone non-overlap; blend with weekly estimates. Regression hedging reduces risk
  correlation, not volatility, and vol-normalisation can raise directionality (same source). Treat betas as
  regime-dependent and re-estimate before sizing.
- **Risk budget**: capital at risk = stop loss; set DV01 so (distance to stop) x DV01 = budget (Citi, EM Strategy Weekly, 20 Aug 2026).
  Full sizing mechanics in [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md) and [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md).

### 3. Cross-market beta and driver map
1. **Beta screen**: regress weekly changes in the local 10y yield on weekly changes in the US 10y; 52-week window
   (default). Use **weekly Wednesday closes** (removes Asia/US T/T+1 lag, avoids payroll Fridays). Repeat for 2s10s
   slope changes vs US 2s10s. Combine with a relative-level check: high beta plus a stretched level is stronger than either
   (Citi, EM Strategy Weekly, 20 Aug 2026; Citi, Asia FX and Rates, 13 Aug 2026). `rolling_beta` returns beta, R2, residual, residual z.
2. **Weekly correlation of yield changes with the US** (Willer and Saunders, Trading Global Macro Markets, 2026): 10y CAD 0.79,
   DEM 0.71, GBP 0.66, JPY 0.28; 2y CAD 0.59, DEM 0.51, GBP 0.43, JPY 0.18. Back ends are more correlated than front
   ends: front ends carry local policy divergence, back ends carry the spread to USTs (flows, term premium).
3. **Regime check**: compare past-1M vs previous-3M betas and R2 (JPM GFIMW, 21 Aug 2026: EUR 10y vs JPY R2 rose from
   about 0 to 20-50%); 60-day rolling pairwise 10y correlations for US/UK/JP/DE. A rising R2 to a new driver means the
   global driver has changed; do not size off a 3y beta.
4. **Beta-implied vs actual**: local move minus beta x US move over the same dates = idiosyncratic repricing (BofA, UK
   Rates Viewpoint, 5 Sep 2024). If the residual is persistent, treat it as a term-premium or fiscal reassessment, not noise.
5. **Shock source**: a heteroskedasticity-based decomposition (Rigobon 2003) separates domestic from foreign shocks in
   G4 10y yields (Goldman Sachs, Global Rates Trader, 2 Oct 2026). Watch for "global shocks in a trench coat": a local shock in a large economy
   that goes global with a lag (Willer and Saunders 2026).
6. **Opaque market from transparent ones** (e.g. NOK from USD/EUR/GBP): with moves ~ N(mu, Q) split into known x and
   unknown Y, the MLE of Y solves `(Q^-1)_YY (Y - mu_Y) = -(Q^-1)_Yx (x - mu_x)`; reset the reference point whenever the
   opaque market prints (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed, 2022).
7. **Implied vs delivered directionality** of a cross-market spread (JPM, Conditional Trades, May 2016): implied = 1 - (EUR vol / USD vol);
   delivered = 1 - 6M beta of EUR on USD changes; exposure is to the vol-weighted spread (EUR implied / USD implied) x USD yield - EUR
   yield, so an unweighted spread carries hidden directionality when delivered differs from implied. Use ECB-event dummies.

### 4. Intra-EMU spreads to Germany: fair value and screens
Use several methods; they answer different questions. Convert every result to a **standardised residual =
residual / SD(residual)** so countries are comparable (DE residual SD 15bp, IT 46bp, Greece 150bp in one global model;
bp are not comparable, z is) (Citi, European Rates Weekly, 1 Oct 2026; BofA, Monthly rates models, Aug 2025).

1. **Cross-sectional PCA-residual dislocation screen** (BofA, Many EGBs one simple value tool, Mar 2018; `dislocation_index`):
   - Panel: spreads to Germany for AT, NL, FR, BE, IT, ES, PT x 2/5/7/10/15/25y = 42 series (FI/IE dropped for data).
   - Each day, PCA on backward-looking data (expanding window, first year as burn-in), keep N PCs, OLS each spread on the PCs;
     residual = actual - fitted, positive = cheap.
   - **Dislocation index** = cross-sectional SD of the 42 residuals, expanding z-score. Trade only when z > threshold:
     buy the cheapest-residual EGB vs Germany, hold a fixed period (the day-t residual uses day-t data, so enter at t+1). Source's choice: **11 PCs, 5-day hold, 2x threshold**; best
     holds 5-9 days, best #PCs 9-13. Long-leg hit ratio rose from 56% (0.5x) to 71% (3x); the rich leg is a coin flip, so
     trade the cheap leg only. No costs in the backtest, so low-threshold hit ratios are inflated. With a smaller
     panel use fewer PCs and pick N out of sample.
2. **Macro/financial regression** (Citi): 10y constant-maturity spread on Bund yield, Bund ASW, euro-area financial
   conditions, equities, vol and a rating-matched credit spread; daily since 2020; same specification for every 10y
   spread. A large positive residual can be a political/fiscal premium, not a fade signal.
   **PCA fair value** for 10y spreads (BofA, Global Rates Weekly, 2 Oct 2026): residual after the first two PCs of 10y spreads (FR, NL, AT, FI, IT) over 5 years.
3. **Directionality regression** (BofA, Global Rates Weekly, 2 Oct 2026): residual of the 10y OAT-Bund spread vs 1y1y EUR OIS
   over the last 3 months (spread beta to ECB pricing).
4. **Fiscal pooled panel** (Barclays, Global Rates Weekly, 2 Oct 2026): spreads on 5y-ahead debt/GDP projections plus a credit-index
   risk proxy, fitted separately for core/low-debt (DE, NL, FI, AT) and non-core/high-debt (IT, ES, PT, BE, FR), France excluded
   from estimation. Non-core: +10pp debt/GDP = +30-40bp, 1pp worse balance = +20-30bp; core: little effect. Read *which
   regime* the spread trades near. Goldman Sachs puts OAT-Bund at about 10bp per 1pt of GDP of 1y-ahead deficit expectations and the cross-country
   spread-to-OIS beta to debt/GDP at 1-3bp per ppt; a 50bp widening would need roughly 15-17ppt of debt/GDP repricing at
   3bp/ppt, so most of the move was risk premium (GS, Global Rates Trader, 2 Oct 2026).
5. **Spread-vs-spread**: regress one spread on another over 6M (e.g. 10y Italy-Germany on France-Germany); the residual
   says the pair is stretched, not which leg is wrong (check which leg moved and the reverse regression); **credit-curve vs level**: regress country 3s10s on the 10y spread, report R2, beta,
   residual z and 3M carry+slide for the flattener. 10s30s relationships were weak (R2 mostly < 15%) (JPM GFIMW, 21 Aug 2026).
6. **Idiosyncratic spread vs PC1 of sovereign spreads**: regress each spread change on PC1, track the 1m rolling residual,
   scatter actual vs PC1-predicted (above the diagonal = idiosyncratic widening) (GS 2 Oct 2026).
7. **Fragmentation monitor**: split the change in the GDP-weighted euro-area 10y yield into an OIS contribution plus
   country ASW contributions; fragmentation = falling OIS share with rising FR/IT/ES contributions (Citi, 1 Oct 2026).
8. **Adjusted spread to Germany** (JPM, Follow the cash flow, Sep 2015): `adj = (y_bond - y_DE,mm par) - Beta x (size-weighted
   euro-area maturity-matched spread to Germany in that sector)`, `Beta = (y_bond - y_DE,mm) / (weighted EA spread)`. Beta is a
   ratio, not a regression beta. Freeze it at the window start so adj starts near 0 and later changes are bond-specific
   (my reading of the source). Use it to isolate bond-specific effects from EMU-wide spread trends and Bund moves.
9. **Data-surprise rule for BTP-Bund** (Willer and Saunders 2026): trade Italy from the long side when German surprise indices are
   negative and Italian positive. Active IR of Italian spread returns by regime: DE- / IT+ 1.21, DE+ / IT+ 0.76, DE+ / IT- 0.19,
   DE- / IT- -0.38, vs buy-and-hold 0.30. Both-positive is also described as historically the worst regime for Bunds (Citi, House
   Views, Aug 2026). The source reports no costs and no out-of-sample split; test it before use.
10. **BTP ASW vs credit**: BTP ASW above the BBB corporate Z-spread = cheap; near A/AA Z-spread = expensive. Spikes can
    trigger ECB action (Willer and Saunders 2026).

### 5. FX-hedged pickup and the USD yardstick
1. **Forward form** (`hedged_pickup_bp`): investor buys the foreign bond and sells the foreign currency forward.
   `hedge carry (% p.a.) = (F/S - 1) x (365 or 360)/days x 100` (day-count denominator, not the xccy basis), F and S in home-per-foreign; `pickup = y_foreign + hedge carry -
   y_home`. Default: rolling **3M** hedge (matches how real money hedges; 1M-3M typical, so rollover risk exists). Match the denominator to the yields' convention: 365 vs 360 alone is ~4bp on a 300bp differential.
2. **Rate-differential form** (`hedged_pickup_rates_bp`): `pickup = (y_f - r_f) - (y_h - r_h) + basis`. r = money-market
   rate for the hedge tenor; basis = xccy basis on the *home* leg vs foreign leg flat. Equals the forward form up to
   compounding by covered parity (the self-test builds F from the same differential and checks equality, plus a hand-computed basis case: a negative home-leg basis lowers the pickup). The hedge removes front-end carry, so the UST-vs-Bund hedged pickup is roughly symmetric around 0
   (about -2% to +2%) (Willer and Saunders 2026). AUD and NZD hedge references are term bank bills, not overnight rates (BofA, FX-Sofr primer, Oct 2023).
3. **Rolling vs maturity-matched hedge**: compute both. For a euro investor in USTs vs Bunds, maturity-matched hedging
   gave a larger pickup than rolling 3M at every tenor (JPM, Cross currency basis 4Q24 Outlook, 26 Sep 2024).
4. **USD ASW of a basis-swapped foreign bond** (Huggins and Schaller, Fixed Income Relative Value Analysis, 2nd ed, 2024; `usd_asw_foreign_bp`):
   `USD ASW = (ASW_foreign - CCBS) / CF`, `CF = BPV_USD / BPV_foreign`. ASW_foreign is `govt_minus_swap` on the reference rate
   of the CCBS foreign leg (add the index basis first if not, e.g. 6M ASW + 3M/6M basis); CCBS is the spread on the foreign
   leg vs USD flat (more negative = "wider"). Assumes par bonds. "USD SOFR par ASW of basis-swapped bonds is a universal
   rich/cheap yardstick": cheap basis-swapped Bunds vs SOFR draw flows out of USTs and richen Bunds vs EURIBOR as well, so never
   analyse one market's spreads or basis in isolation. SOFR-ASW excludes capital-cost terms that pollute EURIBOR/OIS-ASW
   (unsecured-vs-secured spread ~ g x q x d: cost of equity x risk weight x capital ratio, e.g. 10% x 20% x 8% = 16bp); details and CDS bounds in [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md) and [xccy-basis](../xccy-basis/SKILL.md).
5. **Cash-flow matching for a synthetic bond**: CCBS notional = principal at maturity; pair with a *par* asset swap
   (upfront = par - dirty); identical settlement on all legs (T+0 vs T+2 mismatch leaves a 2-day gap); trade float/float
   CCBS plus a separate fixed/float swap.
6. **Foreign-demand check**: hedged pickup tracks non-economic foreign demand. Limited or negative pickups = weak bid;
   large pickups reduce macro fair-value model fit (BofA, UST macro framework, Oct 2024). A foreign buyer on a 1y hedge runs a carry trade: a 30bp pickup is wiped out by 30bp of UST underperformance vs the home yield (BofA, UST RV Primer, May 2022). But Japanese UST flows follow the
   Fed cycle and capital-gain expectations more than pickup, except at extremes (Willer and Saunders 2026). Do not model demand from pickup alone.

### 6. Systematic cross-market signals (overview; statistics in [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md))
- **Carry** = 10y yield (or swap) - 1m rate; buy the highest, sell the lowest, currency-hedged, two long-short pairs.
  **Carry-to-risk** = carry / vol. **Reversal** = change in 10y-1y slope vs its 6M average. **Real yield** = 10y -
  consensus 10y inflation forecast. **Unemployment** = current - 10m average (JPM, Systematic fixed income strategies, Apr 2015).
- **Pair carry** (`pair_carry_bp`) = (long yield - cash) - duration-weighted (short yield - cash), each leg financed in
  its own currency; risk = 12m rolling SD of non-overlapping monthly returns of the combined position; rank by
  carry/risk, take the top 1-2, scale each to a **100bp annualised risk target** (JPM, Investment Strategies No. 31, Jan 2007).
- **Hedged-pickup percentile rules** (Willer and Saunders 2026, table columns): FX-hedged pickup of UST over Bunds (EUR investor), futures,
  duration-matched. Top decile: long UST/short Bund, active IR 0.60; bottom decile IR -0.79; long/short 0.69; unconditional
  -0.13. UST vs gilt: long/short 0.63, 90th pct 0.70, 10th pct -0.56. JGB vs UST (12m trailing percentile): long/short 0.72, 90th
  0.59, 10th -0.81, unconditional -0.16. These are carry factors: they go sideways in bond bear markets (UST-Bund flat since 2020).
  Percentile window (full-sample vs rolling) is not stated for the first two, and no costs: assume look-ahead risk.
- Signals fail in vol spikes and crowded unwinds; BoJ yield-curve control breaks mechanical carry (replace JPY with the next
  lowest-carry market) (JPM systematic update, Jul 2017). Check long-duration bias: regime-split rally vs sell-off. Full numbers: [evidence tables](references/evidence_tables.md).

### 7. Policy-cycle overlay
- **Front-end spreads follow relative policy and the back end follows the front end**: the 10y UST-Bund spread turns ahead
  of peak policy divergence. In the 2015-19 UST-gilt cycle: pay the US-UK spread slightly before relative Fed tightening, stay paid
  until just before the last differential hike, then switch (Willer and Saunders 2026). Link: [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md).
- **When the Fed starts cutting, chase the leaders** (markets already pricing cuts), not laggards; a Fed cycle alone is not
  a reason to receive the rest of the world (Willer and Saunders 2026, 1y rate changes, not receiver P&L).
- **Neighbour pairs** (SEK/NOK, AUD/NZD, CAD/US): trigger = 5y spread at its most extreme over 1,000 days; reversal is weak and
  slow (AUD/NZD stabilises then reverses; the others run about 2 more months). Use as an alert and wait for a catalyst.
- **BoJ cycle** is traded at the front end (less subject to US rates); JGB duration only when US rates are below their 55-day
  average (return 2.02%, IR 0.90 vs unconditional IR 0.60) (Willer and Saunders 2026).
- **Choosing the cross-market short**: the market least likely to get supply support with the most hawkish central bank; rank also by oil/energy
  sensitivity (ECB arguably the most sensitive G4 bank, US among the least) (Citi, House Views, Aug 2026).

## Worked examples
**A. Yield spread (BTP-Bund, May 2021).** 10y BTP 0.60% Aug 2031 at 95.502 = 1.066% minus Bund 0% Feb 2031 at 101.300 =
-0.132%: spread = 1.066 - (-0.132) = 119.8bp (Tuckman and Serrat, 4th ed, 2022). Note the 6-month maturity mismatch and 0.6% vs 0% coupons: this
is a yield spread, not rich/cheap.

**B. Hedged pickup arithmetic.** A Japanese lifer buying USD A-or-better 7-10y credit at 5.42% and 10-20y at 5.83%
hedges with a 2.68% 1y USDJPY cost: 2.74% and 3.15% hedged, both below the 4.03% 30y JGB. A European buyer of 7-10y USD IG at
5.57% less 1.36% hedge = 4.21% vs 4.04% for euro corporates, +17bp (Citi, High-Grade Beat, 19 Aug 2026). Rolling vs
maturity-matched (euro investor, UST over Bund, 26 Sep 2024): rolling 3M pickup 2y 17 / 5y 24 / 10y 18 / 30y 29bp vs
maturity-matched 24 / 35 / 33 / 56bp (JPM, Cross currency basis 4Q24 Outlook). In percent for a JPY investor on 18 Apr 2024 (rolling 3M hedge, pickup vs 10y JGB):
10y UST -1.78%, Bund -2.35%, OAT -1.85%, BTP -0.94% (BofA, US Rates Watch, 22 Apr 2024). All negative: JPY investors
were not paid to hedge, yet kept buying, so pickup is not a flow model.

**C. USD ASW of a JGB (23 Sep 2012, LIBOR era).** 6M JPY ASW -1bp + 3M/6M basis 12bp = 11bp; CCBS -64.5bp; CF 0.95:
`(11 - (-64.5)) / 0.95 = 79.5bp` over USD LIBOR (source rounds to 79bp). Against 10y Japan CDS at 130bp that leaves about 51bp
before the no-arbitrage bound binds; adjusted CDS (FX part removed) is 30-60% of USD CDS, so scenario-test the bound (Huggins and Schaller 2024). Synthetic
UST in GBP (17 Oct 2023): UST 3.375% May 2033, clean 88.94 + 1.43 accrued = 90.37 dirty; par ASW SOFR + 30bp, CCBS (SOFR vs
SONIA) -19bp, CF about 1: net SONIA + 11bp; a 4.83% USD yield becomes a 4.46% synthetic GBP yield (same book).

**D. OAT-Bund triangulation (Oct 2026), 10y spread ~140bp after +28-30bp in a week.** BofA: fair value 100-110bp; PCA
residual says 33bp too wide, directionality regression 42bp cheap. Citi: regression residual about +50bp, FV ~90bp, forecast 95bp 4Q26. Barclays: spread was near
the core-implied fiscal FV, now at the non-core-implied FV, so "not cheap if the move to periphery-like is complete". GS: widening is
risk premium beyond fiscal repricing. Read: all say cheap, but every desk says wait ("needs to stabilise first"; "catching a falling knife"; supply and
ECB timing). Action: no fade until realised spread vol stops rising and a backstop (supply cut, domestic buying, ECB
communication) appears; express relief via cross-sectional trades (long OAT vs BTP was the contrarian idea) or hold the wait.

**E. PCA dislocation snapshot (19 Mar 2018).** Dislocation z -0.7: no trade. Cheapest residuals NL 10y +2.4bp, ES 5y +2.1, FR 2y/5y +1.7;
richest FR 15y -2.3, IT 2y -1.9. Backtest: long-leg total spread change 2015 (14 trades) -108bp, 2016 (33) -110bp, 2017 (16)
-60bp, hit 71-75%; short legs 50-71%; average 5-day move fell from about 8bp to 4bp; no costs (BofA, Many EGBs, Mar 2018).

**F. Beta (JPM GFIMW, 21 Aug 2026).** 1Yx1Y SONIA on 1Yx1Y ESTR: y = 1.09x + 1.4, R2 95% (5M); 5Yx5Y gilt on 5Yx5Y UST: y = 1.1x + 0.4, R2 75%
(6M): the UK intermediate sell-off was mainly US-driven. A "too steep" SONIA 12bp residual was not traded because rolling 120-day R2 fell from about 100% to 60%
and the driver was global term premium: stopped out on discipline.

**G. Sizing (illustrative numbers, not from a source).** Long EUR 100m Bund (DV01 0.085 per 100 face) vs short USTs (DV01 0.079 per
100 face) at 1.17 USD per EUR: short USD face = 100m x 0.085 x 1.17 / 0.079 = 125.9m. A published trade of this type pairs EUR 100m
Bund Feb 2036 with $121.2mn UST May 2036 at -146.6bp (Bund minus UST), 3M carry -0.5bp, slide +1.1bp; the sizing rule is not stated in the source (JPM GFIMW).

More tables (global 10y RV z-scores, front-end residuals, carry backtests, auction effect): [evidence tables](references/evidence_tables.md).

## Signals & interpretation
| Observation | Reading / action |
|---|---|
| Standardised residual >= +2 on several independent methods | Candidate tightener (buy cheap, sell Bund or the rich neighbour); also require stabilisation and a catalyst |
| Standardised residual +-0.5 to 1 | A tilt, not a signal (BofA UST framework: +-0.5 sigma residuals are tilts) |
| PCA dislocation z > 2 | Screen is "on": trade the cheapest 1-2 residuals vs Germany, 5-9 day hold, take profit once it works |
| Rich-leg residual (negative) | Weak (~50% hit); do not short rich legs on the screen alone |
| Methods disagree (PCA cheap, fiscal at non-core FV) | Regime question: which fair value applies? Size small or skip |
| R2 of beta regression < 0.5, or rolling R2 decaying | Beta unreliable; spread driven by something else; do not size off it |
| Hedged pickup in top decile (trailing 12m) | Long the high-pickup market vs low-pickup, duration-matched; carry factor, expect it to stall in bear markets |
| Realised daily spread vol doubles (e.g. 1.2 -> >2bp) | De-risk; overlay swap spreads or switch to same-issuer liquid pairs (Astor Ridge, Trade Radar, Mar 2022) |
| Widening is idiosyncratic (residual vs PC1 large) and the investor base is price-sensitive foreign | Spillover beta to other EGBs stays elevated until an anchor appears (GS 2 Oct 2026) |
| One leg drove the move | Decompose: EU-OAT tightened because the OAT weakened, not because EU strengthened (Citi, EU RV, 19 Aug 2026) |

**Confirmations before a fade**: (1) which leg moved; (2) driver class: global/US beta, fiscal/political, supply/technical (futures CTD, month-end,
stops), funding/hedging flow; (3) backstop present (supply cut, domestic buying, ECB tools: communication first, then
TPI/OMT for disorderly moves; the ECB's pain threshold is higher than the market's); (4) 3M carry and slide not
punitive; (5) stop distance consistent with the DV01 budget. OAT blow-out driver checklist: stops on longs (3-5y, futures), negative-convexity flows around CTD
changes, month-end shifts, supply worries, politics, secular technical trend (BofA, 2 Oct 2026).

## G10 differences that change the trade
| Market | What matters for the cross-market view |
|---|---|
| USD | Sets the tone for all back ends; UST foreign share fell from 57% post-GFC to 32% end-2025; supply pressure shows more in swap spreads than curve shape |
| EUR | Bund is the base; periphery spreads = credit + hedging + ECB backstop; France is a "hedging name" in stress; supply/redemption calendars differ by country (IT coupons coincide with supply) |
| GBP | Gilts more sensitive to the UST long end and energy than Bunds; QT and a retreating domestic LDI/insurer base; sell-offs mostly US-driven (see F) |
| JPY | Domestic holder base, low vol (relative SD ~0.3), correlation with USTs only 0.28 at 10y; front end lags US; BoJ cycle at the front end; YCC/MoF issuance distort carry rules |
| CAD, AUD, NZD | CAD highest US correlation (10y 0.79); AUD/NZD neighbour pair and policy-cycle differences; AUD/NZD FX-swap references are bank bills |
| CHF, SEK, NOK | CHF benefits vs EUR from OAT political premium; SEK/NOK neighbour pair; small markets, weekly data and wider costs |

Details per market, with seasonals caveats: [G10 market notes](references/g10_market_notes.md).

## Pitfalls
- **Orientation and sign errors** between sources (UST-Bund vs Bund-UST; ASW govt-minus-swap vs swap-minus-govt; CCBS on which leg). Fix one convention at the top of every analysis.
- **A large residual is not a timing signal.** Fiscal models do not bound widening; political shocks cause overshoot; pooled betas ignore country
  factors and time variation; fiscal forecasts update about twice a year; the credit-index proxy is partly endogenous; sample 2010-2026 is small.
- **Regressions on spread levels** (fair-value regressions, spread-vs-spread, credit-curve vs level) have autocorrelated residuals and trending inputs: R2 and z are overstated and the fit can be spurious. Require a stationary residual (unit-root test, half-life of weeks to months) before reading z as a reversion signal ([quant-cointegration](../quant-cointegration/SKILL.md)).
- **PCA and expanding windows are price-based** and adapt slowly to regime change (e.g. end of ECB reinvestments); cheap single bonds drive the
  dislocation index; no-cost hit ratios are inflated; loadings shift with regime on a 1y window.
- **Macro/global fair-value models fail under non-economic buying** (QE, foreign official demand, global yield chase): include the central-bank balance sheet and a global factor.
- **Yield-level z-scores are imprecise**: use several metrics plus carry and a macro reason before switching (BofA, UST RV Primer, May 2022).
- **DV01 hedges leave spread risk**; vol-normalised pairs retain directionality vs global risk, with fatter tails; low-yield receivers act as risk hedges, high-yield ones correlate with risk.
- **Specialness and benchmark status create false outliers** in cross-market rich/cheap; adjust for them and ask why a bond is rich before fading it.
- **Hedge-cost mechanics**: rolling 1M-3M hedges versus a long asset create rollover risk; debt-limit or reserve drains can widen hedge costs temporarily; check which basis a series represents.
- **Positioning and crowding**: long RoW / short US and steepeners were the crowded RV legs; a back-end stabiliser hits both. Swap-spread longs cracked when EGB spreads stopped out (GS Macro, 3 Oct 2026). Fragmentation acts as a global VaR shock and bull-steepens USTs.
- **Carry-based rules** break in bond bear markets and under yield-curve control; backtests through the secular rally have long-duration bias.
- **Seasonals** rest on tiny samples (n=20, Japan 10); a 70% up-ratio on 10 observations is weak evidence; use as a tailwind only.
- **Slippage**: replicating published model portfolios incurs costs and publication delay; size by liquidity (a 20y OAT fly was too illiquid for size).
- **Supply measured in gross EUR** hides DV01 and net cash needs; measure DV01 and net-of-redemption.

## Output
Return (and pass to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) / [rv-devils-advocate](../rv-devils-advocate/SKILL.md)):
1. **Pair table**: spread (A minus B, order stated), level, 1w/1m/3m change, 3M carry and slide, and the leg that moved.
2. **Fair-value table** per method: model, sample, residual bp, standardised residual, R2; agreement count across methods.
3. **Beta/driver table**: beta to US (weekly, 52w), R2, past-1M vs 3M change, idiosyncratic share of the move.
4. **Hedged pickup** (if cross-currency): home currency, tenor, forward vs rate-differential form, rolling vs maturity-matched, 6M z-score or trailing percentile, USD ASW if used.
5. **Trade spec**: legs and sizing (DV01 per leg in a common currency, FX used), entry, target, stop, DV01-based capital at risk, expected return = mean-reversion + carry and roll, holding period, catalyst, backstop, kill criteria.
6. **Chart**: spread history with FV band; residual z history; rolling beta and R2.
State data gaps explicitly; never fill them with remembered numbers.

## Scripts
- [`scripts/cross_market_spreads.py`](scripts/cross_market_spreads.py): hedged pickup (forward-point and rate-differential forms, rolling hedge), USD ASW of a foreign bond, DV01 hedge notional with FX, pair carry, rolling beta/R2/z, and the expanding PCA-residual dislocation index. `python scripts/cross_market_spreads.py --help`; subcommands `pickup`, `beta`, `dislocation` read `curve_par` / `fx_rates` (CSV or Parquet); `--selftest` checks known cases (hedge arithmetic, covered-parity equivalence, JGB USD ASW, simulated beta and an injected PCA dislocation).

## Related skills
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): ASW mechanics and USD/EGB swap-spread conventions.
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): CDS-bond basis, adjusted CDS, redenomination risk in EGB spreads.
- [xccy-basis](../xccy-basis/SKILL.md): cross-currency basis behind hedged pickups and USD ASW.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auction-cycle and coupon/redemption trades vs Germany.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): constant-maturity fitted yields and individual-bond switches.
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA mechanics and residual conventions.
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): intra-country curve legs of cross-market spread-of-curves trades.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md) and [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): global-factor and fiscal fair values.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md) and [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): policy-divergence inputs.
- [quant-cointegration](../quant-cointegration/SKILL.md) and [quant-lead-lag](../quant-lead-lag/SKILL.md): stationarity of spread residuals; Asia/Europe/US time-zone lead-lag in cross-market betas.
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): carry/value signal statistics; [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): beta and hedge regressions; [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score conventions.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md), [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md), [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): conventions, DV01, carry and sizing.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): lifer/pension and foreign-demand flows.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables.

## References
- Doug Huggins, Christian Schaller - Fixed Income Relative Value Analysis (2nd ed, Wiley, 2024): USD ASW of foreign bonds, SOFR-ASW yardstick, CCBS and CDS bounds, cash-flow-matched synthetic bonds, horizon-dependent directionality.
- Dirk Willer, Alex Saunders - Trading Global Macro Markets (Wiley, 2026): cross-market correlations, hedged-pickup percentile rules, policy-cycle and neighbour-pair rules, periphery data-surprise rule.
- BofA Merrill Lynch - European Rates Viewpoint: Many EGBs, one simple value tool (E. Satko, 21 Mar 2018): PCA-residual dislocation screen and backtest.
- J.P. Morgan - European Rates Strategy: Follow the cash flow (G. Salford, A. Chordia, 15 Sep 2015): adjusted spread to Germany.
- Citi Research - European Rates Weekly: What to do about OATs? (J. Searle et al., 1 Oct 2026): standardised-residual regression FV, fragmentation decomposition, EGB trade book.
- BofA Global Research - Global Rates Weekly: Start of rates bite (M. Cabana et al., 2 Oct 2026): OAT-Bund PCA and directionality FV, blow-out drivers and backstops.
- Barclays Research - Global Rates Weekly: The urgency question (A. Pradhan et al., 2 Oct 2026): fiscal pooled-panel fair value, core vs non-core regimes.
- Goldman Sachs - Global Rates Trader: Reaching Limits (G. Cole et al., 2 Oct 2026): fiscal betas, PC1-residual idiosyncratic spreads, Rigobon spillover decomposition, cross-market trade log.
- J.P. Morgan - Global Fixed Income Markets Weekly (F. Diamond et al., 21 Aug 2026): spillover beta table, BTP-OAT and credit-curve regressions, UK/AU betas.
- BofA Global Research - US Rates Watch: Monthly rates models, Apr, May and Aug 2025 editions (B. Braizinha et al.): global state-space 10y RV table and z-scores.
- BofA Global Research - Global Rates Viewpoint: FX-Sofr and xccy, tightening themes (R. Man, 3 Jun 2025) and FX-Sofr primer (31 Oct 2023): hedged-pickup definition, investor hedging behaviour, reference rates.
- J.P. Morgan - Global Rates Strategy: Cross currency basis 4Q24 Outlook (F. Bassi et al., 26 Sep 2024): rolling vs maturity-matched hedged pickup.
- BofA Global Research - US Rates Watch: Mixed UST positioning picture (M. Swiber, A. Zhang, 22 Apr 2024; partial) and Long UST outflows & dealer holding highs (10 Mar 2025): hedged pickup tables for JPY investors.
- Citi Research - FX Basis Quarterly: Paying the basis (again) into 2025 (J. Williams et al., 13 Dec 2024): USD ASW cross-country table, EGB dispersion index.
- Bruce Tuckman, Angel Serrat - Fixed Income Securities (4th ed, Wiley, 2022): yield spread vs bond spread, DV01 hedging, ECB QE constraints.
- J.P. Morgan - Investment Strategies No. 15: A cross-market bond carry strategy (N. Panigirtzoglou, 9 Mar 2006) and No. 31: Exploiting carry with cross-market and curve bond trades (11 Jan 2007): carry rules, carry-to-risk, risk-target sizing.
- J.P. Morgan - Systematic fixed income trading strategies (M. Inkinen, F. Bassi, 13 Apr 2015) and Update on systematic rule based trading strategies (K. Gupta et al., Feb 2017-Jan 2018): five cross-market 10y swap signals, YCC override.
- J.P. Morgan - Rule-based Fixed Income Monthly (S. Mac Gorain, 2 Nov 2012): real-yield cross-section, vol-matched pairing.
- Macrosynergy - Interest rate swap returns: empirical lessons (R. Sueppel): relative vol normalisation, DM swap correlations, risk-beta hedging pitfalls.
- Citi Research - EM Strategy Weekly: Can back-end USTs derail EM risk? (L. Costa et al., 20 Aug 2026) and Asia FX and Rates Strategy (G. Goh, R. Garg, 13 Aug 2026): 52-week weekly beta screen, rolling PCA with orthogonalised anchors.
- Citi Research - European Rates: Latest views, summer updates (20 Aug 2026), European Rates Weekly (24 Sep 2026) and Morning Call, EU: Improved RV (19 Aug 2026): hedged cross-market swap-spread comparison, SSA-vs-EGB monitor, decomposing which leg moved.
- Goldman Sachs FICC - GS Macro, cuRated (3 Oct 2026): EGB ASW stress spilling into USD swap spreads.
- BofA Global Research - UST macro framework (B. Braizinha, 15 Oct 2024) and UST RV Primer (A. Zhang et al., 2 May 2022): global yield term, hedged pickup as foreign-demand check, state-space model, z-score caveats.
- Citi Research - Global Asset Allocation: House Views August 2026 (D. Willer et al., 21 Aug 2026): choosing the cross-market short, oil sensitivity.
- J.P. Morgan - Talk is Cheap: Valuing DM Rates Markets with Central Bank Speak (B. Jarman, F. Bassi, 30 May 2024): cross-market front-end residuals; spreads governed mostly by betas to global factors.
- BofA Global Research - UK Rates Viewpoint: Back to school (A. Stengeryte, M. Capleton, 5 Sep 2024): beta-implied vs actual UK repricing, gilt-Bund checklist.
- Credit Suisse - PCA Unleashed (M. Pelata et al., 24 Oct 2012): PCA on EGB curves, cross-market residuals.
- Astor Ridge - Trade Radar: Trades & Fades (Mar 2022): intra-EMU switches, France as hedging name, vol-triggered de-risking.
- J.P. Morgan - A primer on Conditional Trades (K. Gupta et al., 26 May 2016): implied vs delivered directionality in cross-market spreads.
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed, Aitch & Dee, 2022): MLE of an opaque market's moves from transparent ones.
- Alexander Düring - Fixed Income Trading and Risk Management (Wiley, 2021): sovereign CACs, cross-market PC1 correlation regimes, composite spread curves.
- Stephen Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed, Harriman House, 2012): cross-market correlation instability.
- BofA Securities - Global Rates and FX Primer: Bond market seasonality explained (P. Ciana et al., 6 Jun 2022; partial): cross-market spread seasonals.
- BofA Global Research - US Rates Viewpoint: UST supply & demand in '25 (M. Swiber, 26 Nov 2024): foreign official and private demand drivers.
- BofA Global Research - Global Economic Weekly: The fog of war (C. Irigoyen et al., 2 Oct 2026): ECB reaction-function ladder (TPI/OMT) for spreads.
- Citi Research - The High-Grade Beat: The path forward for hyperscalers (D. Sorid, M. Jacob, 19 Aug 2026): hedged USD credit vs local yields for Japanese and European buyers.
- Citi Research - Global Economic Outlook & Strategy: Global Resilience (N. Sheets et al., 20 Aug 2026): gilt-Bund forecast, Bund as relative safe haven.
- Citi Research - Japan Rates Weekly (T. Fujiki, 14 Aug 2026 and 2 Oct 2026): US-Japan policy-spread yardstick, UST-to-JGB beta mapping.
- Citi Research - US Rates Weekly (J. Williams et al., 21 Aug 2026 and 2 Oct 2026, OAT of the blue; partial): hedged-pickup matrix, UST-Bund closed trade, fragmentation as a VaR shock.
- Citi Research - Foreign Exchange Forecasts: August 2026 (D. Tobon et al., 20 Aug 2026): CHF vs EUR on OAT risk premium, gilt foreign inflows.
- Financial Times - Unhedged Chart of the Week: Who owns government bonds? (D. MacFadden, Aug 2026) and US long-term bonds slide as the Treasury secretary's intervention fails to soothe investors (20 Aug 2026): investor-base composition, buyback signal half-life.
- JWS Macro (Substack) - Duration Is Diseased: What Can Stop the Rot? (4 Sep 2025): BoJ share of JGBs.
- J.P. Morgan - Global Rates Strategy: Drivers of cross currency basis in EUR, GBP, JPY, AUD & CHF (F. Bassi et al., 11 Mar 2015): synthetic AUD bond via JGB and AUD/JPY basis.
- J.P. Morgan - Welcome to the machine: NLP of central bank speak (J. Lupton et al., 26 Apr 2023): hawkishness-gap calibration.
- RiskVal Financial Solutions - RiskVal Overview 201: Cash and Futures (12 Nov 2021): expected return of a spread = mean-reversion + carry and roll, mean-crossing diagnostics.
- Rigobon, R. (2003), Identification through heteroskedasticity, Review of Economics and Statistics (external): basis of the shock decomposition used by Goldman Sachs.
