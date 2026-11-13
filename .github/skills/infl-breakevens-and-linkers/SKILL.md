---
name: infl-breakevens-and-linkers
description: 'Prices and screens inflation-linked relative value across G10 - index ratio and reference index (lag, interpolation, floors), real yield, breakeven (BE) and its premia, zero-coupon and forward inflation (5y5y), inflation swap vs bond basis, IOTA and linker asset-swap and z-spread, linker carry (real-yield and BE carry), CPI/HICP/RPI seasonality and seasonally adjusted real yield, fixings-implied CPI path, synthetic real rates, linker curve and fair-value regressions. Use when asked about breakevens, BEI, TIPS, OATei, BTPei, UKTi, JGBi, ILBs, inflation-linked or index-linked bonds, linkers, real yield, 5y5y inflation, ZC or YoY inflation swaps, CPI swaps, CPI fixings, inflation basis, IOTA, linker ASW, seasonal adjustment, linker carry, RPI-CPI wedge, "is the BE cheap", long/short inflation, long/short BE, energy-hedged BE. Oil and energy to CPI nowcasts: macro-inflation-and-energy-drivers.'
---

# Breakevens, real yields and linkers

A linker pays a real coupon and principal scaled by an index ratio, so it trades a real rate; a nominal bond minus a
matched linker is a breakeven; a zero-coupon inflation swap (ZCIS) trades the index directly. RV exists because the same
inflation exposure is priced in three places (cash BE, swaps, fixings) with different lags, seasonal exposure, liquidity
premia, balance-sheet cost and a structural bias of pensions/LDI to receive inflation. This skill turns published
indices, linker and swap quotes into like-for-like measures (seasonally adjusted, lag-matched, carry-adjusted), then
into rich/cheap calls and trades. Treat a BE as expectations plus an inflation risk premium minus a linker illiquidity
premium, never as a pure forecast (risk premium: Tuckman & Serrat, Fixed Income Securities, 2022; Düring, Fixed Income Trading and Risk
Management, 2021; liquidity premium: BofA, Welcome to the real world, 22 Jul 2025).

## When to use
- "Is the 10y BE / 5y5y / UKTi 2036 / OATei 2032 cheap or rich?", "who is driving this sell-off, real yields or BEs?"
- Comparing cash BE with the ZC swap (inflation basis), linker ASW vs nominal ASW (IOTA), or linker z-spreads.
- Linker carry, roll and "what does 3m carry look like with the market-implied index path".
- Seasonality: why July-maturity TIPS look rich, aged-swap valuation, seasonally adjusted BE.
- Reading CPI fixings: market-implied monthly CPI vs economists, implied core, energy-hedged BE trades.
- Building a synthetic real rate (nominal OIS minus inflation swap), market-implied r*, forward real policy path.
- Not here: energy/commodity pass-through and CPI/PCE methodology are in
  [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md); generic ASW mechanics in
  [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md).

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Linker static: `index_id`, `index_lag_months`, `base_index_level`, `has_deflation_floor`, coupon, maturity | `bond_static` (`bond_type = linker`) | point-in-time | If the lag or interpolation rule is not stored, ask: it differs by market ([conventions](references/g10-linker-conventions.md)) |
| Linker and nominal clean price, accrued, `ytm_pct` (real yield for linkers) | `bond_quotes` | daily snap, 3m+ for z-scores, 1y+ for regressions | Use one snap per series. Real price, not index-adjusted |
| Published NSA index by month, all vintages | `infl_fixings` | monthly, first release (`pub_ts_utc`) | Swaps and linkers usually reference first release. Never overwrite revisions |
| ZC inflation swap rates `zc_rate_pct` by `start`, `tenor`, lag, `base_month` | `infl_swaps` | daily snap | % per annum, compounded. Forward-start rows for 5y5y if the desk quotes them |
| Seasonal factors (additive %, 12 values, sum about 0) | `infl_seasonals` | refit annually, point-in-time via `valid_from` | If absent, estimate (script) and label the method |
| Nominal OIS/swap curve, repo | `curve_par`, `curve_zero`, `repo_rates` | daily | Discounting for z-spread, synthetic reals, carry |
| Swap spreads / ASW | `swap_spreads` (`asw_*` = bond minus swap) | daily | IOTA needs both the linker and the nominal comparator |
| Index definitions | `rate_indices` (family `CPI`) | static | Use canonical ids (`EUR-HICPXT`, `GBP-RPI`) |
| Economist/CB projections, fuel prices | `macro_series` | monthly | For fixings comparison only |

If an input is missing, ask the user or hand off to the data adapter. Never invent an index print, a lag or a seasonal.
Future reference values beyond the published CPI are assumptions: always state which path (market-implied or economists).

## Conventions (state them in every output)
- BE and every spread in bp; real yield, nominal yield, ZC rate in %. BE = nominal yield minus real yield at matched maturity.
- "Long BE" = long linker, short DV01-matched nominal (wins when BE widens). "Long/receive inflation" on a ZCIS =
  receive the index leg, pay the fixed rate. Avoid payer/receiver wording: it is ambiguous.
- Real-yield carry = forward real yield minus spot real yield. Positive = good for a long linker funded at repo (it can
  lose that much real yield before losing money). **Long-BE carry = BE_spot minus BE_forward = RY carry minus nominal carry**
  (nominal carry defined the same way). High index accrual in the window lowers the forward BE, which is positive carry for a
  long BE. A "BE carry" number without this sign statement is not usable.
- Inflation basis = ZC swap rate minus cash BE (matched maturity and lag). Positive = cash BE cheap to swaps. Long basis
  = receive inflation in the swap, sell the cash BE.
- IOTA = linker ASW spread minus nominal ASW spread; ASW as bond minus swap (positive = bond cheap), so positive IOTA = linker
  cheap to its nominal comparator.
- z-spread (linker) positive = cheap to the discount curve. Real-yield z-scores: below -2 rich, above +2 cheap.
- DV01 positive for a long position, currency per bp. A real-rate DV01 and a nominal DV01 differ; a BE trade is hedged in DV01 terms
  or by the stated ratio, never by notional. Cash DV01 of a linker = real DV01 per 100 x index ratio x face (index-adjusted, not face alone).

## Method

### 1. Index mechanics: reference index, index ratio, cash flows
1. Reference index for date d in month m with lag L: `RV = A[m-L] + (d-1)/ND_m x (A[m-L+1] - A[m-L])`, A = published NSA
   index, ND_m = days in the month. For L = 3 a July date uses April and May. Without interpolation `RV = A[m-L]`.
   Lag and interpolation are parameters per instrument, never defaults: US 3m interpolated; EUR bonds standard but EUR/French
   CPI swaps 3m *not* interpolated; UK swaps 2m not interpolated; AUD bonds 6m; JGBi takes the index of 3 months prior on the
   10th (not the 1st). See [conventions](references/g10-linker-conventions.md).
2. `IR = RV(settle) / base`, base = reference value at issue (Sweden: most bonds share one base). Cash = real amount x IR for
   coupon, redemption and accrued. Apply the deflation floor to redemption only where the bond has one (`has_deflation_floor`):
   `max(IR, 1)`. French practice: truncate RV and IR to 6dp, round to 5dp.
3. Price and yield stay in real space with the nominal-bond convention of the market. Nominal cash flows need an index
   projection first. Never mix a bond, an index curve and fixings that use different lags (treat it as an error).
4. A reference value is known only once the later of the two months it needs has been published. Past the last known value,
   run two index paths and compare: (a) market-implied (inflation swaps/linkers), (b) economists' monthly forecasts.

### 2. Real yield, breakeven and attribution
1. `BE_fisher = y_nominal - y_real` (market practice). `BE_fx = (1+y_n)/(1+y_r) - 1` assumes a 1y horizon. The exact BE (iterate
   until the projected nominal cash flows have IRR = nominal yield) is "illusory" precision unless seasonality is modelled
   (Düring, 2021, Ch.23). Default: Fisher, with the comparator nominal yield interpolated to the linker maturity.
2. Attribute every nominal move: `d(nominal) = d(real) + d(BE)`. BE unchanged while nominals sell off = real-yield-led.
   Flat ASW (not cash-led) plus stable BEs (not inflation-led) also points to a real-yield-led move (JWS Macro, Duration Is Diseased, 4 Sep 2025).
   If a bullish view comes from the nominal leg, trade nominals, not reals (JPM, Monthly Inflation Outlook, 13 Aug 2026).
3. Regime matrix (BofA, Welcome to the real world, 22 Jul 2025): real up/BE up = growth, linkers outperform; real up/BE down =
   hawkish CB, nominals outperform; real down/BE up = stagflation, linkers outperform; real down/BE down = recession, nominals
   outperform. Owning a linker is not owning inflation: duration swamped indexation in 2022. To isolate inflation hold the BE.
   Analogy: the index ratio acts like an FX rate into a constant-purchasing-power currency and the real yield like its local yield,
   so a linker carries cross-gamma between rates and the index (Düring, 2021, Ch.23).
4. Interpret with the five-part decomposition: nominal = real expectations + real term premium + inflation expectations +
   inflation risk premium + liquidity premium. Higher linker liquidity premium widens real yields and compresses BE (largest in
   stress: 2008, 2020). The split is model-dependent and unobservable: report it as an interpretation, not a measurement.
5. 5y5y: `fwd = ((1+z_10)^10 / (1+z_5)^5)^(1/5) - 1` from ZC rates (market convention, no convexity adjustment). Treat it
   as a credibility gauge; a falling 5y5y can mean the CB *will* hike, and calling it "anchored" is a fool's game (JWS Macro,
   Global Rates Outlook #4/#5, Apr/May 2026). It is not clean of seasonality or short-term carry.

### 3. Inflation swaps and synthetic reals
1. ZCIS: fixed leg `N x ((1+K)^T - 1)`; inflation leg `N x (I_end/I_start - 1)` using the swap's own lag/interpolation. ZC
   swaps are quoted as an IRR; solve par rates in simple (period-rate) space and convert, because the IRR delta is non-linear
   (Darbyshire, Coding Interest Rates, c.2024). The index leg has no fixed-rate delta: its risk is in the index curve and discounting.
2. Synthetic real (swap space): `real fwd = nominal OIS fwd - inflation swap fwd`, e.g. 5Yx5Y real = 5Yx5Y OIS - 5Yx5Y HICP
   (JPM, 13 Aug 2026). Prefer real-rate swaps over cash real yields when swap-spread distortions or linker redemptions
   distort cash (Barclays, Global Rates Weekly: The urgency question, 2 Oct 2026; BofA, UK Rates Viewpoint, 5 Sep 2024).
3. Market-implied r* = 2y1y nominal swap - 2y1y inflation swap (about 0 in Jan 2024, about +250bp in 2007-08, about -200bp
   in 2021) (Nordea, EUR rates: Pushing back, 17 Jan 2024). Market-implied 5y5y real policy rate = 5y5y OIS - 5y5y BE; rule: above
   3% receive 5y5y OIS and go long 5y5y BE (Credit Suisse, Basis Points, 18 Feb 2010; dated, check the equilibrium band).
4. Forward real policy path from fixings: forward real rate for a month = OIS/futures-implied policy rate for that month minus
   the inflation fixing for the same month. A forward real rate that rises because priced cuts lag falling inflation = room
   for more cuts (JWS Macro, USD & Global Rates Thoughts #2, 13 Nov 2025).
5. Aged or odd-maturity swaps need seasonal adjustment: if the first 6 months are seasonally strong, a 4.5y rate sits below the
   5y on an unchanged curve. Never linearly interpolate whole-year quotes; build a monthly fair curve.

### 4. Seasonality
1. Estimate: ratio of log(NSA) to a centred 2x12 moving average (script `seasonal_factors`), average by calendar month, demean.
   HP filter is simpler but revises past values; X-12 style handles Easter. Short windows do not average out one-offs
   (strikes), long windows hide evolving patterns (Black Friday) (Düring, 2021, Ch.23). Default here: at least 3 full
   years, ideally 8-10, refit annually and store point-in-time (`infl_seasonals.valid_from`).
2. Size: the seasonal swing is the same order as trend inflation (for Japanese CPI ex fresh food it is well above trend, so
   JGBi inflation return over any active horizon is driven by seasonality) (Düring, same). Its bp value decays with duration.
3. BE distortion: BE measures index growth between the settlement and maturity reference dates. Settling on a seasonally low
   index pushes BE up; maturing on a seasonally low index pushes BE down; non-integer spans distort. The effect is a fixed level
   shift amortised over life, so it shrinks with maturity. The maturity-month seasonal matters more for value than near-term carry.
4. Seasonally adjusted real yield (SARY): seasonal index centred on 1 (multiplicative `S = 1 + seasonal_pct/100`), lagged and
   interpolated exactly like the reference index and projected for each future year. `SAP = P x S_value / S_maturity` (P =
   dirty real price strictly); solve the yield from SAP, then the seasonally adjusted BE. Exclude sub-1y issues (priced month by
   month) (BofA, Welcome to the real world, 22 Jul 2025).
5. Consequences for RV: on a non-seasonal spline July-maturity TIPS look rich (final reference value on the high April CPI) and
   April maturities cheap; naive spreads span about -30 to +13bp at the short end vs a few bp once adjusted (Düring, same;
   BofA, UST RV Primer, 2 May 2022). In EUR, French July issues are the most advantaged, German the most disadvantaged.
   Compare linkers only (a) on the same seasonal cycle, or (b) after adjustment. Residual rich/cheap after adjustment may just be
   different seasonal assumptions (participants differ) or the unmodelled floor value of new issues.
6. Implementation: never let a spline absorb seasonality. Composite a seasonal curve (offsetting higher/lower index growth that nets to zero
   over the cycle, or 12 monthly multiplicative factors remarked monthly) onto a smooth index curve that still reprices the calibrators
   (Darbyshire, Coding Interest Rates, c.2024; Deutsche Bank Index Quant, Curve Creation Process, 2 Feb 2023).
7. Seasonality leaks into swaps: integer-year ZC HICP swaps and even the 5y5y show a pattern tracking the inverted linker price
   pattern. Seasonals are a tailwind, not a signal on their own ("not to be blindly followed", BofA, UK Rates Viewpoint: Back to
   school, 5 Sep 2024).

### 5. Linker carry (cash space, then back to real)
Procedure (BofA, Welcome to the real world, 22 Jul 2025); script `linker_carry` implements it.
1. Dirty cash = (real clean + real accrued) x settlement IR.
2. Forward cash = dirty cash x (1 + repo x days/basis), minus each interim coupon's cash (de-annualised coupon x IR on the
   payment date) rolled at repo to the horizon. Repo basis per market (ACT/360 USD/EUR, ACT/365 GBP): state it.
3. Forward real dirty = forward cash / forward IR. Forward real clean = that minus forward real accrued.
4. Solve the forward real yield. RY carry = forward RY - spot RY. Repeat for the nominal comparator; long-BE carry = RY carry - nominal carry.
5. Closed form (no coupons): `P_f = P_0 x (1 + r t) / (1 + i t) ~ P_0 (1 + (r - i) t)`, where `r - i` is the "real short rate":
   repo minus index inflation over the window (Düring, 2021, Ch.23). Agreeing a real forward needs an inflation forecast, a nominal one only repo.
6. Forward reference values: known to the 1st of next month, or the 1st of the month after once the prior CPI is published.
   Beyond, use two paths and show both. Interpretation: positive carry is not positive return. The market is good at pricing the
   predictable part (near-term prints, seasonals); your edge is the gap between its index path and yours. Index carry dominates
   short linkers. Carry-adjust histories of yields and BEs before judging past trade performance.
7. Scenario for "unchanged": state whether carry/roll assumes realised forwards or an unchanged curve; the numbers differ
   (Tuckman & Serrat, 2022). Default here: unchanged real yield curve with the market-implied index path.
8. Signal use: "significantly negative carry of below -9bp" has been a contrarian signal for BE widening over the prior 5 years (JPM,
   13 Aug 2026), because lagged indexation means carry need not reflect medium-term fundamentals. The source does not state its sign
   convention; read it as long-BE carry and verify on your own history before use.

### 6. Relative-value measures
1. **Linker z-spread (preferred)**: project nominal cash flows with reference values from the inflation swap curve (and
   seasonals), discount on the RFR/IBOR curve, solve the parallel spread s.t. PV = dirty cash price. Script `z_spread`
   (continuous compounding; state if you use another). Positive = cheap.
2. **Inflation basis** = swap rate - cash BE (UK 4y: RPI swap 3.38% vs UKTi BE 3.25% = +13bp, BofA, 22 Jul 2025). Mathematical sources: the swap is an exact whole-year average, the BE mixes
   maturity, cash-flow, duration and seasonality mismatches. Behavioural source: structural receive-inflation demand
   (pensions/LDI, structured notes) clears either through swaps rising or linkers cheapening on ASW until buy-linker-ASW-and-pay-inflation
   works (BofA, 22 Jul 2025). Price-formation order: long-term expectations plus short-term carry set bond pricing, bond pricing
   sets swap pricing; the swap market is symmetric, the bond float roughly fixed, so linker carry noise (mostly oil) leaks into
   swaps and long forwards, scaled by arbitrage capital (Düring, same).
3. **IOTA** = linker ASW - nominal ASW (alternative to basis; different because cash flows are misaligned). State the ASW type: US/UK linker
   ASW are proceeds (notional = dirty cash price incl. indexation), euro are par/par; neither captures future accretion (BofA, 22 Jul 2025). On the US desk
   it is TIPS BE vs a matched inflation swap (Citi, US Rates Weekly: Pension plan for 20s?, 9 Oct 2026). Screen: z-score vs the past 3M
   range; regress IOTAs on nominal par spreads vs the benchmark (1M/3M/6M). Small, choppy betas and weak R2 = IOTAs trade on linker
   supply/demand, so a rich IOTA can persist (JPM, 13 Aug 2026).
4. **Real-yield / linker curve RV**: fit one spline per seasonal cycle (US has three issue cycles: Jan/Feb, Apr, Jul), or adjust
   and compare z-spreads. Deduct the deflation-floor option (valued with a standard swaption model, OIS discounting) from the real
   price, apply official monthly multiplicative seasonals interpolated daily, do not exclude on-the-runs, exclude maturities under
   1y (lagged indexation makes them erratic), use few knots (4 benchmark knots plus a 3y midpoint for US) and accept some dispersion
   for smoothness (JPM, The (par) curves they are a-changin', 23 Jul 2024). The floor is worth more for bonds whose accreted
   principal is near par. Do not read scarcity richness (a tiny never-reopened issue) as RV (BofA, 22 Jul 2025).
5. **Comprehensive model** (when a smooth real curve is needed): `I_f = I_t x (s_f/s_t) x exp(iota (f-t))`, then price each cash flow
   with its lag and interpolation; `P = (I/I_0) x sum Rf(t_i) x Cf_i` with `Rf(t) = Df(t) x (s_t/s_0) x exp(iota t)`: a nominal
   spline with an inflation model and seasonality on top. Fit iota (or a time-varying iota_l, tau = 3) to linker prices. Implied long-run
   inflation tracks the HICP 5y5y swap with ~15bp mean absolute deviation, i.e. an arbitrage corridor of ~30bp (about the balance-sheet
   cost of a long-held linker ASW). Valid without a floor or with a far-OTM floor (Düring, 2021, Ch.23).
6. Same-month forward steps: for linkers of one maturity month, compute forward real yields between issues (no seasonal
   adjustment needed) and look for kinks and habitat plateaus ([trade examples](references/trade-examples.md)).

### 7. Fixings and data-release pricing
1. Convert swap fixings (or the ZC curve plus seasonals) into a monthly NSA index path and calendar-year averages. Compare with
   economists' forecasts on the same basis (NSA level, not SA m/m). Decompose the implied m/m into energy using the futures curve
   adjusted for the retail-futures spread; the remainder is implied core. Disclose energy, food and seasonal assumptions:
   two houses imply different cores from identical prices (Citi, US Economics Weekly, 14 Aug 2026; Barclays, Diesel's long haul, 1 Oct 2026).
2. Sanity-check each fixing for the month: a flat NSA fixing when gasoline is up 15% is a flag (July has the smallest NSA/SA
   residual); watch months where the energy futures shape or energy seasonal distorts the implied core (JWS Macro, Global Rates
   Update #7, 19 Jul 2026).
3. Front-end BEs track energy. Either avoid outright front-end exposure, go beyond 1y, or hedge with the energy future (short 2y
   BE hedged with long gasoline futures). A rich/cheap read on fixings is only a view on the gap to economists, so state the economists' source.
4. Use the policy chain for timing: energy future -> inflation fixing for a month -> implied policy rate for that month
   ([trade examples](references/trade-examples.md)). Hand off pass-through and CPI/PCE methodology to
   [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md).

### 8. Fair value and drivers
Published regressions (variables, windows, fit) are in [fair-value-and-screens](references/fair-value-and-screens.md). Defaults:
rolling 1-2y for short forwards (1Yx1Y), 6-12M for 5Yx5Y/10Yx10Y, daily/weekly data; require a modest (not just nonzero) residual
before trading; refit or drop drivers when partial betas swing; keep drivers that add R2 (TTF gas added nothing next to oil). Level regressions on daily data have strongly autocorrelated residuals
and inflated R2: size residuals against their own standard error, use HAC errors, and re-fit on changes before trusting a driver. Use
the regime quadrant on 1y1y real vs 1y1y inflation swaps to read what moved (Barclays, 2 Oct 2026).

## Worked examples
All source numbers are quoted as printed. The script reproduces the index arithmetic exactly (selftest) but not every printed
carry digit; differences are called out.

**A. Index ratio and cash (France, OATei 1.85% 2027, value 22 Jul 2025).** RV = 128.16 + (21/31) x (128.08 - 128.16) = 128.10581
(April 128.16, May 128.08). Base (25 Jul 2010) 93.72591, so IR = 1.36681. Real price 103.141: principal
on EUR 1m = 1.03141 x 1.36681 x 1m = EUR 1,409,741.50; accrued 0.0185 x 362/365 x 1.36681 x 1m = EUR 25,078.15; total EUR
1,434,819.65 (BofA, Welcome to the real world, 22 Jul 2025). US check: April 320.795, May 321.44339 give 321.23423 for 22 Jul 2025 (same source).

**B. ZCIS legs (BofA, same).** US 5y at 2.7040%: start 321.24887, end 372.41548; on 100m pay (1.02704)^5 - 1 = 14,271,201,
receive 15,927,409 (recomputes to 15,927,405), net +1,656,208 to the long. EUR 5y at 1.8438%: HICPxT 128.16 to 148.57; pay 9,565,286,
receive 15,925,406, net +6,360,120. The printed headline quotes do not match the legs; use the leg arithmetic.

**C. TIPS 3m carry (BofA, same).** 0.125% coupon bought 3 Jul 2025 at 97.85938, spot RY 1.34569%, repo 4.4%. Dirty cash (97.85938 +
0.0625% x 79/183) x 1.13891 = 111.48340; horizon IR 324.34323/282.34640 = 1.14874; forward real dirty 98.11752; forward accrued 0.058402;
forward real clean 98.05911; forward RY 1.40896%; **printed RY carry +6.3bp/3m**. Verification note: the printed forward cash (112.71173)
does not tie to its stated formula (111.48340 x 1.044^(3/12) = 112.690), and a street-convention solver gives a spot yield of
1.343%. Recomputing with ACT/360 simple repo gives about +5.1bp (`python scripts/infl_tools.py carry ...`). Treat carry as
"about +5 to +6bp/3m" and the structure (index accrual 3.4% annualised vs repo 4.4%, pull-to-par, forward IR from the market path) as the lesson.

**D. Linker z-spread (BofA, same).** TIPS 2.5% Jan 2029 on 21 Jul 2025: base CPI 214.69971, IR 1.49617, real price 104.390625, real dirty
104.431, cash dirty 156.247; projected IR 1.51769 (Jan-26) to 1.64016 (Jan-29), final cash flow 166.066; PV at flat SOFR 157.893 > 156.247,
so **z-spread +31.2bp (cheap to SOFR)**.

**E. UK forward-step RV (BofA, UK Rates Viewpoint, 5 Sep 2024).** November-maturity forward real yields 2027s-32s 49bp, 2032s-36s 129bp,
2036s-47s 190bp. The +80bp first step is RPI-reform pricing; the +61bp second step is "almost wholly about asset swap cheapening", not in
real swaps. More cases (trade books, IOTA, fixings tables) are in [trade examples](references/trade-examples.md).

## Signals & interpretation
| Signal | Reading | Action / threshold |
|---|---|---|
| Linker z-spread or IOTA 3m z above +2 | linker cheap | candidate long linker vs nominal (long BE); check supply, index exits, scarcity |
| Basis (swap - cash BE) 3m z above +2 | cash BE cheap to swaps | short the basis: long cash BE, pay the inflation swap; confirm receive-inflation demand is not structural |
| Same below -2 | rich (basis: cash BE rich) | candidate short linker / reverse the basis trade; confirm flows are not structural (LDI demand) |
| IOTA beta to nominal spreads small, R2 weak | flow-driven | do not hedge with nominal spreads; size on supply/demand calendar |
| Fixings rich vs economists by 0.4-0.6pp YoY (spring 2027 in a published case) | short-dated inflation priced above forecast | trade only with energy hedge and a catalyst; state the economist source |
| Long-BE carry below about -9bp (sign convention in source unstated) | contrarian BE-widening signal over a 5y window | confirm with seasonal and level; test on own history |
| Model-implied 5y5y vs swap deviates by more than about 30bp | outside the arbitrage corridor | basis/ASW trade, not directional view |
| Sub-1y linker cheap on ASW | index exit, balance-sheet stress | likely technical; trade vs nominal ASW z-scores |
| Regression residual near 0 | no dislocation | wait; residuals shift when directionality flips |
| 5y5y falling | CB credibility or front-loaded inflation, not necessarily weakness | read with policy reaction ([central-bank reaction functions](../macro-central-bank-reaction-functions/SKILL.md)) |
| BE falls with equities (rolling correlation deeply negative) | BE as risk asset | risk of regime shift if real-yield overshoot hits financial conditions |

Confirmation checklist before presenting a trade: (1) same lag, interpolation and seasonal cycle on both legs; (2) carry in
the right sign and with both index paths; (3) energy exposure stated or hedged; (4) liquidity premium regime (stress widens real
yields and compresses BEs); (5) supply/auction/index-inclusion calendar ([bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md));
(6) structural flows ([flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md)). Every trade carries entry, target, stop,
rationale and one named risk.

## Pitfalls
- Never compare raw BEs or z-spreads across linkers with different maturity months or settlement dates without seasonal adjustment.
- BE is not expected inflation: it embeds the inflation risk premium (cost of expressing the view), liquidity, supply/demand and carry. A
  glut of linkers depresses BEs, a scramble for real assets lifts them. There is no natural demand for short linkers.
- Goodhart: with a credible CB, or when policy acts on the instrument, market inflation measures can stop being informative.
- Linkers are duration products. Real yields peak with nominals; TIPS gave back their gains in the 2022 hikes despite high CPI (+2.7% to Mar 2022, +0.1% to Jul 2022, since Jan 2021; Willer & Saunders, 2026, ch.15). For inflation exposure trade the BE.
- A DV01-matched BE trade is not directionally neutral: BEs have positive beta to the nominal curve (JPM, 13 Aug 2026). Size the hedge ratio from a regression of the BE change on the nominal yield change, not DV01 alone.
- Index differences: US CPI vs PCE, UK RPI vs CPI (wedge 0.7-1.0%, beta to the inflation level), French CPI vs euro HICP. Convert with the wedge.
  US BEs and swaps pay CPI while the Fed targets PCE; a PCE-CPI wedge is a signal to examine, not to extrapolate, and the 2026 PCE methodology revision
  (about 20-30bp off core PCE) does not move CPI fixings (Citi, US Economics Weekly, 21 Aug 2026).
- Index rebasing: check how the data feed treats the base index (a chaining factor can make the base appear to change while IR does not).
  EU and US revise past values; Japan rebases every 5 years and publishes one decimal (about 0.1% quantisation noise); published HICP can be about 10bp off its true level.
- Lag/interpolation mismatches break carry and basis. Swaps can use 2m (UK) or 3m non-interpolated (EUR) while bonds interpolate.
- Deflation floors: ZC swaps generally have none, YoY swaps usually do, bonds differ by market (CAD, GBP none; AUD floors coupons too). A near-the-money floor
  raises bond value and distorts BE vs swap; add its option value to model prices.
- Scarcity richness, linker redemptions, bank reinvestment pace and index exits distort short-dated linkers. Use real swaps for macro views.
- Illiquid markets (JGBi): BE is vulnerable to flow-driven declines; use wide stops and small size.
- Seasonal caveats: patterns evolve, houses differ, Easter moves, and the bp effect decays with duration.
- Fixings-implied "core" depends on your energy/food/seasonal assumptions; fixings marks move daily; fixing swaps quote NSA levels while
  surveys and prediction markets quote SA m/m. Precision mismatch (2dp vs 1dp) affects measured errors.
- Driver betas (oil, gas, FX) are regime-dependent; re-check before sizing. A cross-market BE spread can be driven by an omitted factor (oil).
- BE/real-yield macro models break under non-economic buying (QE, official demand) and in stagflation. Model values may be before desk charges.
- Do not read the premia decomposition as data. It is model output.

## Output
Return (and, when a trade follows, hand off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md)):
1. **Provenance block**: index_id, lag, interpolation, floor flag, as-of date and snap, first-release vs revised, seasonal set (`method`, `fit_end_date`), index path used
   for carry (market-implied or economists), repo basis.
2. **Linker table** (one row per bond): `instrument_id`, maturity month, real yield, BE (bp), seasonally adjusted BE, z-spread (bp, positive = cheap), IOTA, basis vs swap,
   RY carry and long-BE carry for 3m/6m/12m, 3m z-score and 1y z-score.
3. **Attribution**: nominal move split into real yield and BE for the window, regime-matrix label.
4. **Fixings view** (if used): implied vs economist monthly NSA/YoY, implied core and assumptions.
5. **Trade idea(s)**: structure (long BE = linker vs DV01-matched nominal, ZCIS, basis, flattener, forward real), entry, target, stop, DV01 weights, carry in bp/3m, the named risk
   and the kill condition.
6. **Caveats**: what is model-dependent (premia, seasonals), what would invalidate.

## Scripts
- [`scripts/infl_tools.py`](scripts/infl_tools.py): reference index (lag, interpolation as parameters), index ratio (floor, 6dp truncation), Fisher/FX breakeven,
  ZC forwards (5y5y), ZCIS legs, real clean price/yield, linker real-yield carry (BofA procedure), seasonal factors (ratio to centred MA), seasonally adjusted price,
  linker z-spread. CLI: `refindex` and `fwdinfl` read canonical `infl_fixings` / `infl_swaps` (CSV or Parquet); `carry` takes explicit inputs.
  `python -I scripts/infl_tools.py --selftest` checks the OATei, US and textbook index examples, ZCIS legs, a carry identity and a coupon-bearing carry hand-calc,
  mid-period price/accrued, a seasonal-recovery case, a z-spread round trip and that missing/short/NaN data raise. Street-convention yields: use for relative carry, not settlement cash.

## Related skills
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): energy pass-through, CPI/PCE methodology, robust cores, which feed fixings views.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): ASW/z-spread mechanics behind IOTA and the nominal comparator.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): general carry/roll framework; this skill adds the index-accrual leg.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market day counts, repo, lag and index conventions.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): spline fitting for the real curve.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-space RV for 1y1y, 5y5y inflation and real forwards.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): general seasonal and month-end index extension tools.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): regression hygiene for BE and real-yield fair values.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): LDI/pension receive-inflation demand behind basis and long-end BEs.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): linker auctions, redemptions and reinvestment.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): policy path used with fixings for forward real rates.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score and ranking conventions for the screens.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used above.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): hand-off format for a finished idea.
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): term-structure models and term premium.
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): fiscal supply and term premium.

## References
- BofA Global Research - Global Rates Viewpoint: Welcome to the real world, global inflation-linked primer, 2nd ed. (Capleton, Swiber, 22 Jul 2025): conventions, carry procedure and TIPS example, SARY, z-spread, basis/IOTA, premia, regime matrix, ZCIS.
- Alexander Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 2021), esp. Ch.23 and Ch.39: index ratio, BE definitions, seasonality, carry formula, comprehensive model, rebasing.
- J H M Darbyshire - Coding Interest Rates (c.2024): index lag/interpolation rules, ZCIS legs and IRR quoting, linker real-space pricing.
- J.P. Morgan - Monthly Inflation Outlook: A mixed bag of inflation market views (13 Aug 2026): FV regressions, IOTA screen, fixings vs forecasts, trade book and hit rates.
- BofA Global Research - UK Rates Viewpoint: Back to school: tough tests this term (Stengeryte, Capleton, 5 Sep 2024): same-month forward steps, UKTi trades, real-swap expression.
- Citi Research - US Rates Weekly: Pension plan for 20s? (9 Oct 2026); All it takes is a little push (4 Oct 2019); Deal or no deal (10 May 2019): IOTA, TIPS ASW screens, BE regression, energy-hedged BE trade.
- Citi Research - European Rates Weekly: A narrative shift looms (17 Mar 2022); Morning Calls (12 and 19 Aug 2026): 5y5y regression, carry tables, linker auction dashboards.
- Citi Research - US Economics Weekly (14 Aug, 21 Aug and 2 Oct 2026) and Inflation Weekly (17 Aug 2026): fixings vs economist path, implied core, CPI vs PCE.
- Barclays Research - Global Rates Weekly: The urgency question (2 Oct 2026): real/inflation quadrant, BE as risk asset, range break, CPI swap seasonality; and US Energy and Inflation: Diesel's long haul to the US consumer (1 Oct 2026): ex-energy implied CPI tracking.
- J.P. Morgan - The (par) curves they are a-changin' (Barry et al., 23 Jul 2024): TIPS par curve with floor and seasonal adjustments.
- BofA Global Research - Monthly rates models (Apr, May, Aug 2025 editions, Braizinha, Craig): 10y BE/RY fair value, global BE PCA, directionality.
- BofA Global Research - UST RV Primer (2 May 2022): three TIPS issue cycles, floor value.
- BofA Global Research - To everything there is a season (23 Jan 2022): real vs BE share of sell-offs, linker returns by curve regime.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026), ch.5, 6, 15: BE behaviour through the Fed cycle, oil/copper conditioning, TIPS in the 2022 hikes.
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets, 4th ed. (Wiley, 2022): BE as expectations plus risk premium; carry/roll scenarios.
- JWS Macro (Substack) - Duration Is Diseased (4 Sep 2025); Global Rates Outlook #4, #5, #6 (Apr-Jun 2026); Global Rates Update #7 (19 Jul 2026); USD & Global Rates Thoughts #2 (13 Nov 2025): who drives the sell-off, fixings decomposition, forward real rates, 5y5y.
- Nordea Markets - EUR rates: Pushing back (17 Jan 2024), and Risk/reward favours receiving ECB meetings (19 Jun 2025): market-implied r*, 2y1y regression.
- Credit Suisse - Basis Points: A Guide to the Front-End and Basis Swap Markets (18 Feb 2010): 5y5y real policy rate.
- J.P. Morgan - Rule-based Fixed Income Monthly (2 Nov 2012): cross-sectional real-yield signal.
- BofA Global Research - Japan Rates Basics (24 Apr 2023): JGBi indexation and floor, supply absorption (dated).
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis, 3rd ed. (McGraw-Hill, 2005), App. F: index-linked gilt 8m/3m lag.
- Morgan Stanley Research - US Rates Strategy: Kalshi Markets as Macro Signals (18 Aug 2026): fixings quote NSA levels, prediction markets SA m/m; compare each with consensus on its own basis.
- Deutsche Bank Index Quant - Interest Rate Curve Creation Process (2 Feb 2023) and tpSEF Rulebook, App. B (2021): inflation-swap valuation inputs and contract terms (dated).
