# Published macro fair-value specifications (templates)

These are the specifications as each source printed them. Use them to pick drivers, windows and plausible beta
magnitudes. **Re-estimate every model on your own point-in-time data.** Coefficients drift, and several of these
proprietary indices (forecast revision indices, growth indices, commodity curve indices) are not in the data
contract. Replace them with an available proxy, such as a PMI, consensus revisions or a commodity future, and say
that you did.

Conventions: y and rate drivers are in % unless marked bp. "SE" is the regression standard error, in bp unless noted.
For a yield, a positive residual means cheap.

## 1. Outright yields and forwards

| Source | Target | Drivers | Window / freq | Fit | Read at the time |
|---|---|---|---|---|---|
| BofA, Introducing a new UST macro framework (15 Oct 2024) | UST 2y/5y/10y/30y via curve PC1, PC2 | 4 DFM factors (broad, growth, inflation, employment) from 19 series, plus fed funds, Fed balance sheet and global yields | 14y weekly | PC R² about 90%+; residual SD about 35bp at 2y/5y and 20-25bp at 10y/30y | FV 2y 4.15, 5y 4.05, 10y 4.15-4.2, 30y 4.35; 2y about 20bp rich (−0.6σ), 10y about 10bp rich (−0.3σ), 30y about 5bp cheap (+0.1σ) |
| BofA, UST RV Primer (2 May 2022); Monthly rates models (4 Aug 2025) | 10y UST via PC1/PC2 of 2s/5s/10s/30s | fed funds; PCs of growth (GDP, capacity utilisation, IP, ISM, retail sales), inflation (CPI, PCE, ECI, import prices) and employment (NFP, claims, unemployment rate); the "adjusted" version adds the Fed balance sheet and global DM rates PC1 | 7-15y | two fair values: US fundamentals only, and adjusted for overseas demand | May 2022: 10y at its cheapest vs fundamentals in the calibration window. Aug 2025: FV 4.25-4.3%, 10y 5-10bp rich (< 1σ) |
| BofA, Monthly rates models (4 Aug 2025) | 10y yields, 16 markets | state-space DFM: `x_t = B·x_{t−1} + w_t`, `y_t = Z·x_t + v_t`, factor count fixed a priori | not stated | z = (resid − mean)/SD | US 10y FV 4.4-4.45 (about 20bp rich); Japan +3.3σ cheap; Switzerland −1.8σ rich |
| JPM, Global Fixed Income Markets Weekly (21 Aug 2026) | 30y UST, using the independent variables of JPM's 10y FV model | const 9.56; 1y1y OIS 0.414 (t 49.5); US FRI −0.04 (t −5.2); 5y5y TIPS BE 0.284 (t 4.6); Fed B/S share of economy −0.127 (t −33.0); tariff dummy 0.144 (t 5.9) | 31 Dec 2020 to 31 Dec 2025 (frequency not stated) | R² 97.9%, SE 16.0bp (14bp in text) | year to date: implied +29bp vs actual +45bp; residual +9bp, inside SE, so justified |
| JPM, same note | 5y5y OIS USD/EUR/GBP | cumulative changes in growth and inflation forecast revision indices | 10y | USD 0.18·infl + 0.16·growth + 2.2 (R² 82%); EUR 0.27/0.12/1.0 (91%); GBP 0.28/0.05/1.1 (93%) | USD cheap, EUR fair, GBP cheap |
| JPM, Japan Fixed Income Markets Weekly (21 Feb 2025) | 10y JGB | 3mx3m JPY OIS, 10y UST, BoJ share of the 3 newest 10y JGBs | rolling 2y | R² 92.3%, SE 7.0bp | +10bp cheap (peak about +15bp mid-2024); not faded |
| JPM, Monthly Inflation Outlook (13 Aug 2026) | 10y real GBP swap | 0.6·2Yx1Y SONIA + 0.55·(1Yx1M/2Yx1M SONIA) + 0.0005·60d MA of APF outstanding − 1.6 | 12M | R² 71%, SE 7bp | modestly cheap |
| Nordea, EUR Rates Flash (5 Feb 2020) | USD 10y swap; EUR 10y swap | global manufacturing PMI; euro-area cyclicals/defensives equity ratio | 2010-2020 | chart cross-check | USD long swap rates "too low" vs PMI |
| Citi, US Rates Weekly: OAT of the blue (2 Oct 2026) | real GDP growth, mapped to 5y5y real rates | quarterly composite PMI (average of services and manufacturing) | not stated | PMI above 55 goes with 3-4% growth | Q3 PMI about 56.8 justifies 5y5y real rates near 2.5% |

## 2. Curves

| Source | Target | Drivers | Window | Fit / read |
|---|---|---|---|---|
| Citi, US Rates Weekly: Going nuclear (on the curve) (3 Feb 2017) | UST 10s30s, long sample | 5y-ahead projected structural deficit/GDP, perceived inflation target, trend GDP growth, 2y rate | long sample (span not stated) | curve 28bp flat to FV with no fiscal expansion; 35bp flat with deficit/GDP +2% |
| Citi, same note | UST 10s30s, post-crisis | global curve factor (average of Bund, JGB, gilt and CAD 10s30s), front STIR futures curve, 10y breakeven | post-crisis (span not stated) | about 30bp flat; a pension funded-ratio index adds little |
| JPM, Global Fixed Income Markets Weekly (21 Aug 2026) | 1y1y/5y5y OIS curve | 1y1y OIS level (bp per %) | past 1y | USD −72.46·x + 319.0 (R² 88%); EUR −70.7·x + 236.3 (91%); GBP −58.6·x + 301.5 (89%); all 10-20bp too steep, which JPM reads as term premium |
| JPM, same note | SONIA 1y1y/5y5y curve | 1y1y SONIA | 12M | R² 89%, SE 7bp; about 12bp too steep but not faded (global drivers); rolling 120d R² fell from about 100% to about 60% |
| JPM, same note | ACGB 3s10s | USD 2s10s, RBA hawk-dove score, RBA labour-topic share, inflation-minus-labour topic share | daily since Jan 2020 | more weight on inflation over labour steepens the curve (see [macro-central-bank-nlp](../../macro-central-bank-nlp/SKILL.md)) |
| BofA, Understanding the yield curve dynamic (23 Jul 2025) | 2s10s, 5s30s via the PCA-macro FV | as in BofA's macro framework | 10-15y | 2s10s −3.8bp (z −0.16); 5s30s +27.0bp (z +0.93), too steep |

## 3. Inflation (breakevens, inflation swaps)

| Source | Target | Specification | Window | Fit / read |
|---|---|---|---|---|
| JPM, Monthly Inflation Outlook (13 Aug 2026) | UK 1Yx1Y RPI | 0.3·1Yx1Y SONIA − 0.0001·front Brent + 0.004·UK NatGas + 1.94 | 12M | R² 87%, SE 8bp; fair |
| JPM, same | UK 5Yx5Y RPI | −0.02·5Yx5Y SONIA + 0.003·front Brent + 0.02·TW-£ − 0.008·GDP FRI + 1.09 | 12M | R² 74%, SE 3bp; about 5bp cheap; oil beta +3bp per $10/bbl |
| JPM, same | EUR 1Yx1Y HICP | 0.85 + 0.465·1Yx1Y €STR + 0.001·Brent | 3M | R² 50%; modestly cheap; TTF dropped (no R² gain, no residual change) |
| JPM, same | US 30y ZC inflation swap | commodity curve index and its square, 3Mx3M/15Mx3M OIS curve, VIX, survey-minus-CPI-implied expectations | 7y daily | R² 87.2%, SE 9.31; more than 1 SD cheap |
| JPM, same | US 5y5y CPI vs Brent | single factor | regime split | R² 0.64 (Jul 2023 to Feb 2026), then 0.08: the relationship broke |
| Citi, US Rates Weekly: Deal or no deal (10 May 2019) | US 5y breakeven | Michigan 1y-ahead expectations, % slope of the oil futures curve (1st vs 12th), USDCAD, a growth index | rolling 2y weekly | actual 1.76 vs FV 1.91 (cheap) |
| BofA, Monthly rates models (4 Aug 2025) | US 10y breakeven, 10y real | inflation expectations, inflation risk premium, liquidity premium | not stated | BE FV 220-225bp (market 5-10bp wide); real FV 1.90-1.95% |

## 4. Swap spreads, funding, bills

| Source | Target | Specification | Window | Fit / read |
|---|---|---|---|---|
| JPM, US Rates: Buying back time (19 Aug 2026) | term funding premium (TFP, the negative slope of swap spreads vs duration) | excess deposits −0.6 (t −23.3); 1Yx10Y vol 0.3 (t 15.8); Treasury WAM 0.1 (t 6.6); net debt ex-SOMA / Fed assets 0.5 (t 18.6); intercept −0.6 | Jun 2020 to Jun 2026 | R² 83%, SE 0.3; actual 4.4 vs FV 4.2; implied WAM shift of −3 months judged implausible |
| JPM, Global Fixed Income Markets Weekly (21 Aug 2026) | 10y gilt swap spread | −1.1·20d MA(3M GC − SONIA) + 0.5·(1Y/1Yx1Y SONIA) − 0.18·10Y SONIA − 0.006·3Mx10Y vol + 0.0004·BoE APF + 0.2 | 12M | R² 78%, SE 2bp; 1bp too narrow |
| Citi, Short-End Notes (21 Aug 2026) | 2y UST swap spread | FV = 3m OIS/GC + 2y SOFR/FF basis (bp) | not stated | slope about 1, R² 0.81 |
| Goldman Sachs, Global Rates Trader: Reaching Limits (2 Oct 2026) | 10y JGB swap spread | free float (JGBs less BoJ holdings, % GDP) and other drivers | not stated | +5pp free float moves FV about 3bp tighter; spreads can stay wide to FV for a long time |
| JPM, Japan Fixed Income Markets Weekly (21 Feb 2025) | JPY 3m T-bill ASW | 3M USD/JPY xccy basis, monthly T-bill net issuance, 3M GC/OIS | 12M | −4bp (bills rich) |

Details: [spread-swap-spreads-and-asw](../../spread-swap-spreads-and-asw/SKILL.md),
[stir-bills-and-money-market-spreads](../../stir-bills-and-money-market-spreads/SKILL.md).

## 5. Cross-asset linkage: FX and cross-currency basis

| Source | Target | Specification | Window | Fit / read |
|---|---|---|---|---|
| Citi, Japan FX: Recent changes in USD/JPY price formation (15 Jun 2026) | USDJPY, two-tier | **Base:** 200d MA of USDJPY on the 200d MAs of the real 10y US-Japan spread, log TOPIX, log commodity index and a broad USD index. **Superstructure:** deviation from the 200d MA on deviations of the nominal 10y spread, TOPIX, commodity terms-of-trade spread and the USD index. FV = fitted deviation + fitted MA | 2017-25 (with a 2022 dummy plus interactions) and 2023-25, daily | base R² 0.994 (smoothed, so inflated), superstructure R² 0.846, SE ¥1.49; FV about ¥159-161 |
| Citi, Macro tapas (7 Aug 2026) | USDJPY | term-premium model vs rate-differential model | not stated | about 162 vs about 160; USDJPY decoupled from the rate-differential level but still tracks its changes |
| JPM, FX Markets Weekly (21 Aug 2026) | G10 USD pairs | 2y OIS spread, relative commodity terms of trade (plus periphery spreads for EUR pairs) | 2y and 1y | EUR/USD 1.1685 vs FV 1.1375 (2y, R² 0.76) and 1.1516 (1y, R² 0.47), z +0.90 rich; currency score = R²-weighted z; wrong-signed models kept but flagged |
| JPM, Drivers of cross currency basis (11 Mar 2015) | 2y EUR/USD xccy basis | 1.90·(Fed B/S − ECB B/S, % GDP) + 20.63·(5th Eurodollar − Euribor futures yield spread) − 9.43 | 2y | R² 71%; 1% of GDP of relative ECB expansion widens the basis by about 2bp |
| JPM, Cross currency basis 4Q24 Outlook (26 Sep 2024) | 1y FX-OIS basis PC1 (EUR, GBP, JPY vs USD) | −0.14·USD money-market slope (1M/2Yx1M OIS) + 0.26·average EUR/GBP/JPY money-market slope + 0.03·S&P equity index level − 0.06·average 3Mx1Y swaption vol − 80.81 (coefficients read off a chart) | since Jan 2017 | R² 73%; basis less negative with a flatter USD curve, steeper non-USD curves, higher equities and lower vol; front-end bases too wide, bias tighter |

Details: [xccy-basis](../../xccy-basis/SKILL.md).

## 6. Money aggregates (P-star)

Source: Hudson Bay Research, A return to monetarism? (Ireland, Miran, Roubini, Jul 2026).
- `P*_t = M_t·V*_t / Y*_t`; price gap = 100·(ln P*_{t−1} − ln P_{t−1}) in pp. V* and Y* are trends from a **one-sided**
  HP filter, which gives real-time estimates and limits data-mining. Run a GDP-deflator version and a PCE version.
- `Δπ_t = α + Σ_{i=1..4} β_i·Δπ_{t−i} + γ·gap_{t−1} + ε_t`, with `π_t = 400·Δln P_t`.
- 1967Q1-2026Q1: γ = 0.10 / 0.08 / 0.09 (GDP basis; M2 / Divisia M2 / Divisia M4) and 0.12 / 0.11 / 0.10 (PCE basis),
  t 3.6-4.0. Lag 1 about −0.35 to −0.38. R² 0.18-0.19.
- Original Hallman-Porter-Small: β = 0.22/yr with constant V* = 1.65 (M2 velocity, 1955-88). It broke right after
  publication when M2 velocity drifted. Never assume constant velocity.
- Divisia weights each component by its liquidity services (forgone interest), so T-bills and money-fund shares get
  small weights. Divisia M4 growing faster than M2 flags frothy financial conditions.
- Steady state: money growth equals potential growth plus target inflation. Higher potential growth raises the
  "speed limit" for money.

## 7. Cross-sectional value across markets

JPM, Global Asset Allocation: Rule-based Fixed Income Monthly (Nov 2012). The panel is currency-hedged 10y swaps in
CAD, CHF, EUR, GBP, JPY, SEK and USD from 2003, in a pooled monthly regression with every variable demeaned across
countries:

| Driver | Coefficient | t |
|---|---|---|
| carry (10y − 1m slope) | 2.6 | 4.1 |
| change in the 10y − 1y slope | 7.4 | 4.2 |
| real yield (10y swap − 10y consensus inflation) | 2.2 | 3.6 |

Adjusted R² is 0.05. A 100bp higher real yield gives about 2.2bp per month of relative yield performance. A long-short
book (top 2 vs bottom 2 real yields) had IR 0.65, or 0.73 without Japan, whose permanently low real yield otherwise
creates a duration bias. The lesson is that cross-sectional macro value can be tradable at a tiny R² when it is
pooled and rebalanced.
