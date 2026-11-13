---
name: flow-structural-alm-demand
description: Structural, regulation-driven duration demand from pensions/LDI, life insurers (Solvency II UFR/FSP, VA, risk margin; Japan ESR), bank ALM and reserve managers. Maps who receives or buys duration, in which tenor and format (swaps, cash, xccy), what triggers it (funded/coverage ratio, equity drawdown, regulatory dates), how big (DV01, 10y-equivalents), and the effect on long-end swap spreads, EGB ASW, 10s30s, the 20y belly (10s20s30s), 30s50s, long forwards (15y10y/25y10y), long-dated vol and long-tenor xccy basis. Script for hedge-rebalancing (short-convexity) flow, UFR-extrapolated liability DV01 split and funded-ratio nowcast. Use when asked why 20y/30y/50y swaps are rich, whether 30y swap spreads or long EGB asset swaps are structurally supported, about Dutch pension reform (Wtp), UK LDI or BPA/buy-out flows, US DB pension glide path/STRIPS, variable-annuity hedging, JGB super-long lifer demand, AUD super-fund basis, or to stress a long-end flattener/payer against forced ALM receiving.
---

# Structural ALM demand: pensions, insurers, banks, reserve managers

Long-end swap rates, long-end swap spreads and the 20y–50y curve are priced partly by holders whose demand comes from
liability accounting and regulation, not expected return. Pensions and insurers are short a very long bond (liability
duration 15–35y). They receive long swaps or buy long bonds to close the gap, and they do it in tenors and formats the
regulator's discount curve dictates. Their flows are predictable in direction and often pro-cyclical: they receive into
rallies and equity sell-offs because regulation "imposes a form of short convexity on pension fund managers" (Düring,
Fixed Income Trading and Risk Management, 2021). Arbitrageurs lean against the kinks only partly, because the other
side keeps trading "for legal rather than economic reasons" (Quantitative Finance Stack Exchange, Why does the ultra
long-end of a yield curve invert?, 2019). This skill identifies the holder, sizes the flow, dates the trigger, and
decides whether an RV signal at the long end should be followed, faded or hedged.

## When to use
- "Why is the EUR/GBP 20y rich in 10s20s30s?", "why is 30s50s inverted?", "is the 15y10y/25y10y forward curve too steep?"
- "Are 30y USD swap spreads too negative?" or "Will Solvency II reform support long EGB asset swaps?"
- Dutch pension transition (Wtp) and EUR 10s30s steepeners, year-end Dutch receiving, Eurex–LCH basis as a flow tell.
- UK LDI after 2022, bulk purchase annuity (BPA/buy-out) flows, gilt linker demand, GBP 30y SONIA/SOFR basis.
- US corporate DB pensions: funded ratio, glide path, STRIPS demand, the yield level at which pensions buy long USTs.
- Variable-annuity (VA) hedging, insurer receiving in equity sell-offs. Use it as a risk check on any long-end payer or
  steepener.
- JGB super-long demand (life insurers' target yields, ESR, fiscal-year-end buying), Japanese bank IRRBB capacity.
- AUD super funds' long-tenor xccy receiving. Reserve-manager demand for front-end govvies.
- An RV screen flags a long-end residual and you must decide: structural (persistent) or a dislocation (fade).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Swap and govt par curves 10y–50y, forwards (15y5y, 20y10y, 25y10y …) | `curve_par` | daily, ≥ 5y | long-end tenors are essential; ≥ 20y history for z-scores where it exists |
| Zero curve for liability discounting | `curve_zero` | as-of date | needed by `regcurve` |
| Swap spreads / ASW at 10y, 20y, 30y | `swap_spreads` | daily, ≥ 5y | `sign_convention` travels with the row |
| Long-tenor xccy and SOFR/FF-type basis | `basis_swaps` | daily, ≥ 3y | AUD/USD, GBP/USD 10y–30y |
| CCP basis 30y/50y (Eurex vs LCH, CME vs LCH) | `ccp_basis` | daily | domestic-client receive/pay tell |
| Long-dated implied vol (1y30y, 5y20y, 10y10y, 20y10y) | `vol_surface` | daily | normal (bp) vol |
| Futures positioning by trader class | `positioning` | weekly | asset-manager longs in long-bond futures |
| Trade-repository prints 20y+ | `flows_trades` | intraday/daily | size and direction of long-end blocks |
| Funded/coverage ratios, plan assets and liabilities, STRIPS outstanding, insurer and pension holdings by sector, hedge ratios, ESR, investor-type flow data, custody holdings | `macro_series` | monthly/quarterly vintages | use `pub_ts_utc`. Funded ratios publish with a lag, so nowcast them |
| Long-end supply calendar and WAM of issuance | `auctions` | event | supply offsets demand |

Liability cash-flow profiles (`t_years, cashflow`) are not a canonical table. Take them from the user or a regulator's
published sector profile, or use a stylized profile and label it. If an input is missing, ask for it or hand off to the
`rv-data-engineer` agent ([data contract](../data-contract-and-adapters/SKILL.md)). Never invent funded ratios, hedge
ratios or flow sizes.

## Conventions
- Rates and spreads in bp. DV01 in currency per bp, positive = gains when rates fall. "Receive" = add duration.
- US swap spread = swap − Treasury (negative when swaps are below Treasuries). Receiving swaps narrows it (more
  negative), and cash buying widens it.
- EGB ASW = bond yield − swap (positive = bond cheap to swaps). Some EUR research quotes "swap spread" = swap − bond:
  "long-end EGB swap spreads deeply negative" means ASW deeply positive. Convert before comparing.
- Fly 10s20s30s = 2·y20 − y10 − y30. A rich 20y gives a low or negative fly. Curve A–B = longer − shorter.
- 10y-equivalent notional = DV01 / DV01 of the 10y per unit notional (the 5y-equivalent analogue: $100mm 10y = $200mm
  5y-eq when DV01s are 0.090 and 0.045; Tuckman & Serrat, Fixed Income Securities, 2022).

## Method
1. **Name the holder and its binding constraint.** The constraint fixes the hedge format, the tenor and the sign of
   the flow. Full per-market detail is in [references/investor-map-g10.md](references/investor-map-g10.md).

   | Holder | Constraint / discount curve | Format | Habitat | Flow and trigger |
   |---|---|---|---|---|
   | Market-value DB pensions (NL, DK, UK LDI) | Liabilities on swap/regulator curve (NL: UFR) or gilt/SONIA curve; target hedge ratio | swaps, long gilts/linkers, futures | 20–50y | receive in rallies to hold the hedge ratio; NL receive into year-end to protect coverage ratios; pay when unwinding hedges (Wtp transition) |
   | US corporate DB | AA-corporate discount curve; glide path to ~20% equity as funded ratio rises | long IG credit, Treasuries/STRIPS, TRS, OTC bond options | 20–30y | buy duration when funded ratio steps up (rates up and/or equities up); sell UST duration when re-risking |
   | EEA life insurers | Solvency II: swap-based RFR to FSP (EUR 20y), then UFR extrapolation; VA/MA | swaps and bond forwards (hedge accounting), long govvies/SSA | 15–30y, more beyond FSP from 2027 | receive at the last liquid point; after the 2027 reform, buy more long bonds relative to swaps |
   | US VA writers | Liability duration rises when equities and rates fall | swaps (receive), futures for dynamic hedges | ~20y | receive in equity sell-offs and rallies |
   | Japanese life insurers | Target yields on guarantees; ESR/economic-value solvency | super-long JGBs | 20–40y | buy whenever yields exceed target, which caps the long end; heavier Jan–Mar |
   | Banks (ALM) | Deposit duration vs loan/MBS duration; IRRBB limits | swaps vs floating loans, FRNs, intermediate govvies | 2–10y | receive when deposits extend or MBS shortens (rallies); pay fixed against fixed-rate mortgages |
   | Reserve managers | Liquidity, USD share, FX | short, high-grade govvies, FX-hedged via xccy | ≤ 5y | buy USTs when the USD weakens; mainly a front-end force |
   | AUD super funds | Low FX hedge ratio on large foreign-equity holdings | xccy, long tenors | 10–30y basis | receive the long-tenor basis, which inverts the basis curve |

2. **Size the hedge need.** For one holder or a sector aggregate:
   - `DV01_L = D_L · PV_L · 1e-4`, `gap = h · DV01_L − DV01_A` (h = target hedge ratio). A positive gap means the
     holder must receive.
   - **Rebalancing (short-convexity) flow** for a parallel shock Δy (bp): `ΔDV01 = −C · PV · 1e-8 · Δy`.
     `flow = h · ΔDV01_L − ΔDV01_A`. A rally (Δy < 0) gives flow > 0, i.e. forced receiving. Liabilities are more convex
     than bullet hedges, so the flow scales with `C_L·PV_L − C_A·PV_A`. Compute it with `scripts/alm_hedge_flow.py rebalance`.
   - **The policy sets the sign.** A fixed-hedge-ratio holder (NL pensions, insurers, VA) receives into rallies, which
     amplifies the move. A glide-path holder (US corporate DB) adds duration when the funded ratio rises, which
     usually happens in sell-offs and equity rallies, and so stabilises the move. Identify which policy dominates the
     market before you sign the flow.
   - Express in 10y-equivalents and compare with net duration supply over the same window, e.g. dealer capacity or
     net coupon issuance in 10y-eq.

3. **Model the regulatory discount curve where it binds** (formulas in
   [references/regulatory-discount-curves.md](references/regulatory-discount-curves.md)).
   - Solvency II from 30 Jan 2027: market curve to the FSP (EUR 20y, unchanged), then
     `f(h) = w(h;α)·LLFR + (1 − w(h;α))·UFR`, with h = years beyond the FSP, `w(0) ≈ 1`, `w(∞) = 0` and UFR 3.30%.
     f(h) is the average continuously compounded forward from the FSP to FSP + h, so the UFR enters as ln(1 + UFR)
     (EIOPA alternative extrapolation method, external). The final α is 0.11 (all currencies ex SEK); with
     supervisory approval it starts at 0.20 and falls linearly to 0.11 by Jan 2032. A lower α puts more liability
     DV01 on market rates beyond 20y. Receiving needs therefore drift longer, but gradually (Citi, European Rates
     Weekly: What to do about OATs?, 1 Oct 2026; Citi, European Rates Weekly: A QT revolution, 17 Sep 2026). Quantify
     with `regcurve`, which splits liability DV01 into market rates ≤ FSP, the LLFR, and the UFR (unhedgeable).
     Then map the LLFR DV01 onto the regulator's LLFR component forwards to see which tenors get the receiving.
   - VA reform (`VA = 0.85·CSSR·RCS`) rewards insurers that match duration with bonds rather than swaps. The authors
     read it as making govvies "considerably more palatable than swaps from an ALM perspective". That supports long
     EGB/SSA ASW (bonds richen vs swaps) more than it supports outright receiving.
   - The risk-margin cost of capital falls from 6% and a time-declining λ is added. The RM becomes less rate-sensitive,
     which "reduce[s] the need to receive long-end swaps". The two Citi notes disagree on the new rate: 4.75%
     (17 Sep 2026) vs 4.5% (1 Oct 2026). Check the Delegated Regulation before using a number.

4. **Track the trigger state.** Nowcast what is published with a lag (`nowcast`).
   - US DB: the funded ratio is a function of equities, rates and AA spreads. Regress monthly % changes of assets
     (rates, spread, equity) and liabilities (rates, spread) over a 3y window, then apply this month's moves (J.P.
     Morgan, Issuance, pensions, and long-end spreads, 14 Sep 2018). Buying was triggered at ~+3pp funded-ratio steps
     (May 2025, May 2026), and the ratio was ~115% by Oct 2026, a post-GFC high (Citi, US Rates Weekly: Pension plan for
     20s?, 9 Oct 2026). A 10y rally of ≥ 50bp pushes funded status below 100% (BofA, UST supply & demand in '25,
     26 Nov 2024). STRIP-ing activity is "a decent public proxy for pension duration demand" (J.P. Morgan, Pension
     re-risking and long-end swap spreads, 3 Apr 2020); track it as the rolling 12m change in STRIPS outstanding (BofA,
     26 Nov 2024).
   - NL: quarterly DNB coverage and interest-rate hedge ratios, transition cohorts dated 1 Jan, Q4 receiving to lock
     in coverage ratios. Use the Eurex − LCH 30y/50y basis (Eurex par rate minus LCH par rate) as a high-frequency
     tell. Domestic receiving pushes Eurex rates below LCH, so a negative basis means Dutch and German clients are
     receiving. A positive 30y basis was read as "no receiving interest" (Nordea, EUR Rates Flash, 5 Feb 2020).
   - Insurers: equity drawdown (VA), ESR sensitivity (Japan lifers: ESR 215%, and +50bp in JPY rates costs about
     −8pt; J.P. Morgan, Global Fixed Income Markets Weekly, Aug 2026), regulatory effective dates and phase-ins.
   - Seasonality: Dutch year-end receiving, and the Japanese fiscal year-end. 5s30s and 10s30s JGB flattened in March
     in 8 of the past 10 years, as lifers bought super-longs while banks took profits (BofA, Bond market seasonality
     explained, 6 Jun 2022). Hand these off to
     [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md).

5. **Build a flow balance sheet.** Tabulate structural buyers and sellers by format (securities vs derivatives) in
   10y-equivalents over a fixed horizon. Buyers in swaps against sellers in cash narrows swap spreads. It says nothing
   about duration or curve direction (J.P. Morgan, What about Bonds? SLR relief, Treasury supply, and long-end
   spreads, 2 Apr 2020). Duration buyers who use swaps include banks, insurers and delevering REITs. Duration sellers
   sit mostly in Treasuries (hedge funds, banks, pensions, real money), so "this mismatch implies spread narrowing".

6. **Translate to the RV metric.**

   | Flow | Metric | Expected sign |
   |---|---|---|
   | Long-end receiving in swaps (LDI, insurers, VA) | US 30y swap spread; EUR/GBP long swap spread curve | more negative; the swap-spread curve slopes down (EUR only at the long end, UK from ~5y, US throughout; Quantitative Finance Stack Exchange, Downward Sloping Swap Spread Curve, Dec 2020) |
   | Receiving concentrated at the LLP/FSP (20y) | 10s20s30s fly; 15y10y/25y10y | fly low (20y rich); 25y10y − 15y10y high (long forward curve steep) |
   | Ultra-long receiving for convexity | 30s50s; 1y30y vol | 30s50s inverted; low 30s50s comes with high long-dated vol demand |
   | Cash buying (US pension STRIPS; EEA insurers' long EGBs under the Solvency II Volatility Adjustment) | 30y spread; EGB ASW | spread less negative; ASW lower (bonds richen) |
   | Hedge unwinds (Wtp transition) | EUR 10s30s; long ASW | steeper; swaps cheapen vs bonds |
   | BPA: UK insurers sell long gilts/linkers, buy USD credit, hedge in long xccy | 30y SONIA/SOFR xccy basis; basis 10s30s | 30y wider; basis curve flatter (J.P. Morgan, Cross currency basis 4Q24 Outlook, 26 Sep 2024; the 10s30s there is the basis curve, not the gilt curve) |
   | AUD super funds receive long-tenor basis | BBSW–SOFR 20y×5y | deeply inverted (≈ −55bp) |

7. **Decide: follow, fade or hedge.**
   - A PCA or fly residual "indicates a dislocation, not necessarily a trade". The diverging 2012 EUR 15y5y vs 25y5y
     residuals came from Dutch FTK/DNB discount-curve reform (Credit Suisse, PCA Unleashed, 24 Oct 2012). If a
     structural flow explains the residual and is still running, do not fade it.
   - Fade only when (a) the driver is ending or saturating (transition complete, funded ratios near terminal
     allocation, regulation changed), (b) positioning is crowded around the flow, or (c) carry pays you to wait. As a
     default, require two of the three.
   - Flows are slow. Contributions take months to work into the market, so do not trade "cliffs" such as tax
     deadlines (J.P. Morgan, 14 Sep 2018). Regulatory phase-ins run over years.
   - Every long-end payer, steepener or short-convexity position carries a left tail: rates fall, ALM managers "wake
     up", and forced receiving sends the long end lower (Nordea, EUR Rates Flash, 24 Jan 2020). Size for it or buy it
     back with receivers. See [rv-devils-advocate](../rv-devils-advocate/SKILL.md).

## Worked examples
**A. US pension funded-ratio nowcast → long-end spreads** (J.P. Morgan, Issuance, pensions, and long-end spreads,
14 Sep 2018). From 29 Dec 2017 to 31 Aug 2018 the 30y swap rose 254 → 295bp, the S&P 500 rose 2674 → 2902 and credit
spreads went 76 → 81bp. Top-100 DB assets went $1,555bn → $1,547bn (nowcast $1,541bn). Liabilities went $1,775bn →
$1,657bn (nowcast $1,641bn). The funded ratio went 87.6% → 93.4% → 93.9% (nowcast). Market factors explained most of the
~6pp rise. Plans held ~36% equities and nearly 30% of plans by assets were fully funded. Fully funded plans defease by
adding duration in Treasuries (record STRIPS), TRS, reverse THORS and OTC bond options rather than swaps. Hence
"higher pension funded ratios are bullish for long-end swap spreads". The authors took profit on 30y matched-maturity
spread narrowers, hedged for 10s30s. The same channel works in reverse: pension rebalancing after the 14% Q4-2018
equity sell-off drove 30y spreads to −20bp (Citi, US Rates Weekly: The rocky road to a steeper curve, 18 Jan 2019).

**B. Why ALM hedgers receive into rallies** (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022, Sec. 4.8).
Liabilities PV $140mm, duration 16.66, convexity 211.37. Matching with a 20y bond (D 15.56, C 141.49) needs
`M = 140 − 140·16.66/15.56 = −9.90`, i.e. borrow $9.90mm and hold $149.90mm. Asset convexity is
(149.90/140)·141.49 = 151.50 < 211.37, so the hedged fund is net short convexity. `rebalance` gives liability DV01
$233.2k/bp. After −100bp liability DV01 rises $29.6k and asset DV01 rises $21.2k, so the fund must receive
**$8.4k/bp more, 3.6% of liability DV01 per 100bp rally**. In the same book, a pension with liabilities of PV $1bn and
DV01 $2mm, holding $1bn of corporates with DV01 $0.5mm, closes the $1.5mm/bp gap by receiving long swaps, spread
across key rates.

**C. GBP 20y richness and the delta-hedged 15y10y/25y10y flattener** (Citi, US Rates Vol Lab: Buying vol for less,
25 Sep 2019). The GBP 20y richened on ALM/pension receiving (pension risk transfer, shorter longevity assumptions)
plus a fiscal/inflation premium, visible in the 10s20s30s fly (Citi calls the fly "high" because it quotes wings −
belly; on this skill's 2·y20 − y10 − y30 convention a rich 20y is a low fly). 15y10y/25y10y was at −3.32bp, an all-time high, with
z-scores 2.10 (1y), 2.35 (3y) and 2.44 (since 2000), 1y carry +0.91bp, daily breakeven 0 and GBP realized vol ~3.93bp/day.
The authors called it "effectively a free long convexity buy". It was initiated on 17 Jan 2020 at −11.2bp, 50k DV01,
re-hedged every 25bp, with z-scores 1.84 (since 2000), 1.15 (3y) and −0.01 (1y) and carry ≈ +0.5bp/yr (Citi, Rates Vol
Lab: In search of cheap vol, 17 Jan 2020). Stated risk: further 20y richening on ALM receiving. The lesson: when the
structural flow inflates the steepness, hold it as positive-carry convexity, not as a mean-reversion bet.

**D. Dutch pension transition and EUR 10s30s** (JWS Macro, Duration Is Diseased, 4 Sep 2025). The transition implied
~€400mn DV01 of paying over ~2 years, against ~€100mn DV01 of hedge-fund 10s30s steepeners already positioned plus
CTAs and bank pre-hedges. The target was 10s30s back toward +50bp. Two checks followed. Nordea saw year-end
receiving risk: funds had received into prior year-ends to protect coverage ratios, and DNB Q2 hedge ratios were
still high, so "a lot of unwinding" remained for the 1 Jan cohort (Nordea, EUR rates: How about that outright
receiving, 26 Sep 2025). Steepeners were consensus, and "any flattening seems to spur fresh interest to put on more
steepeners" (Nordea, EUR rates: The quiet game, 12 Aug 2025). In March 2026 a dramatic 10s30s flattening was partly an
unwind of hedge-fund positions built for the Dutch flow (JWS Macro, #3: Iran & Front End Rates, 8 Mar 2026). The
structural flow was right, but the trade was crowded. Size it as a crowded trade.

**E. Flow balance sheet, Apr–YE 2020, 10y-eq** (J.P. Morgan, What about Bonds?, 2 Apr 2020).

| Buyers | $bn | Format | Sellers | $bn | Format |
|---|---|---|---|---|---|
| Fed | 400 | securities | Treasury | 1,600 | securities |
| Banks | 300–500 | derivatives | Banks | 100 | securities |
| Financial issuers | 250 | derivatives | Foreign CBs | 100 | securities |
| Foreign private | 100 | securities | Pensions | 100 | securities |
| Levered mortgage hedgers | 50 | derivatives | Non-fin rate locks | 30 | derivatives |
| Insurers | 50 | derivatives | | | |

Buyers total ~$1.1–1.3tn and sellers ~$2.0tn. The buyers use swaps and the sellers supply securities, which is a
narrowing (bearish) setup for swap spreads. The table is not a duration view. VA hedgers had delivered >$150bn 10y-eq of
receiving in ~1 month at the March 2020 peak, more than 2× summer 2011.

**F. Regulatory curve, illustrative** (stylized numbers, not market data). Zero curve 2.0% at 1y rising linearly to
3.0% at 20y then flat, a 60y level annuity, FSP 20y, UFR 3.30%, and LLFR = the market 15y→20y forward (3.79%).
`regcurve` gives the LLFR share of liability DV01 at 8.5% for α = 0.20 and 13.1% for α = 0.11. The UFR share (no
market hedge) falls from 24.9% to 20.1%. For the cash flows beyond 20y only, the LLFR share rises from 11.4% to 17.6%.
So over five years the phase-in moves ~5pp of liability DV01 out of the UFR bucket, which has no market hedge, onto
market-linked rates across the LLFR tenors. That is a gradual extension, not a shock.

## Signals & interpretation
- **Structural support for long-end receivers / spread narrowers:** funded or coverage ratios falling toward
  regulatory floors, a sharp equity drawdown (VA receiving; stocks vs 15y5y/20y10y correlation ≈ −23%, lower stocks
  steeper curve; Citi, US Rates Vol Lab: Trading long-dated convexity, 9 May 2019), a negative Eurex − LCH 30y/50y basis,
  and Q4 for Dutch funds.
- **Structural support for long-end cash / wider US 30y spreads:** a US DB funded ratio stepping ≥ 3pp above the last
  buying threshold, a 30y UST above the pension trigger, and rising STRIPS. Citi's 5.3–5.5% 30y trigger brought little
  STRIPS demand in Sep 2026, so they now look for 5.75–6% (Citi, US Rates Weekly: Pension plan for 20s?, 9 Oct 2026).
  Remaining capacity is finite. Equity allocation is ~24% against a ~20% terminal, so only ~$30–50bn of large-plan UST
  demand is left on ~$1.5–2tn of glide-path assets.
- **Long EGB ASW from 2027:** the VA reform favours bonds. German and, to a lesser extent, Belgian and Dutch insurers
  have room to add domestic EGBs. French, Italian and Spanish insurers are already heavily domestic. Shorter EGB and
  SSA issuance WAM (EGBs ~10y and slightly declining; EU 11.6y; other SSAs 7.7y, the lowest since 2015) adds support
  (Citi, A QT revolution, 17 Sep 2026).
- **JGB super-long:** lifers' target-yield buying makes the JGB long end bear-flatten and bull-steepen near pivot
  levels (10y ~0.75% / 30y ~2% in 2010–15; Düring, 2021). Treat linear slope trades there as option-like. Bank buying of
  super-longs is not natural demand given deposit duration, so J.P. Morgan said it may fade long-end flattening if the
  curve keeps hitting local lows (Japan Fixed Income Markets Weekly, 21 Feb 2025).
- **Fade signal:** a long-end residual ≥ 2σ (default screening threshold) that a structural flow does not explain, or one whose flow has been
  pre-traded by fast money (positioning, SDR blocks), or one where the carry pays. Follow signal: a residual explained
  by a running flow with no crowding.
- **Confirmation:** check the flow in at least two of price (fly or spread residual), plumbing (CCP basis, xccy basis,
  vol skew) and quantity (STRIPS, holdings, SDR, regulator data) before attributing a move to ALM.

## Pitfalls
- **Wrong format, wrong spread.** Pensions moving from swaps to Treasuries (US 2018–20) flips the swap-spread sign of the
  same duration demand. Life insurers use swaps or bond forwards for long-dated hedges (hedge accounting) and futures
  for dynamic VA hedges. Pensions use repo and futures opportunistically (CFTC MRAC, The Treasury Cash-Futures Basis
  Trade, Dec 2024). LDI also substitutes between 30y swaps and ultra-bond futures (Credit Suisse, New Ultra Long
  Contract, 28 Sep 2009).
- **Policy sign.** Glide-path and fixed-hedge-ratio holders respond with opposite signs to the same rate move. Do not
  add them without signing each.
- **Bank swap hedging is overstated.** Bank swap books are mostly market-making. Banks hedge assets mainly through the
  deposit franchise (CFTC OCE, Do Banks Hedge Using Interest Rate Swaps?, 2023). Use balance-sheet duration-gap
  estimates only as an upper bound.
- **Leverage reverses the flow.** Levered LDI under margin calls sells gilts into a sell-off. In Sep 2022 gilts fell
  more than 100bp in a week and the BoE bought up to £65bn (Willer & Saunders, Trading Global Macro Markets, 2026).
  Collateral stress turns structural buyers into forced sellers.
- **Demand is shrinking in places.** UK pensions moving to credit and buy-out cost an estimated ~£400bn (~£500mn DV01)
  of structural demand, mostly in swaps (JWS Macro, 4 Sep 2025). STRIPS demand fades as glide paths complete. The
  holder mix shifting toward price-sensitive buyers raises aggregate yield sensitivity even when each group becomes
  less sensitive (FT Alphaville, Treasury demand has become materially more valuation-sensitive, 20 Aug 2026).
- **Lags and vintages.** Funded ratios publish monthly, DNB data quarterly and flow-of-funds quarterly with revisions.
  Use `pub_ts_utc` and nowcast. Never backfill.
- **Regulatory numbers move.** Parameters change by delegated act (the CoC discrepancy above, α phase-in, UFR reset
  annually). Cite the date of every parameter.
- **Correlated risk factors.** VA flows depend on equities as much as rates, and their rate beta drifts. Re-estimate
  rolling betas rather than assuming a static sensitivity.
- **Uncovered markets.** The source library says little on CAD, NZD, CHF, SEK and NOK ALM demand (SEK has its own
  Solvency II extrapolation parameters). Treat structural demand there as unknown, not zero, and ask for regulator
  and holdings data.

## Output
1. **Structural-flow table**: one row per (market, holder, tenor bucket). Columns: holder, constraint, format (swap,
   cash, futures, xccy), tenor, direction (receive/pay or buy/sell), trigger state (value vs threshold, date), size
   (DV01 or 10y-eq, with source and date), timing (seasonal, phase-in, transition date), affected metric and expected
   sign, crowding evidence, and confidence (high, med or low, plus the reason).
2. **Flow balance sheet** (step 5) when swap spreads are in question.
3. **Verdict** on the RV candidate: structural tailwind, headwind or neutral, and follow, fade or hedge, with the left-tail
   scenario (forced receiving or forced selling) in bp on the trade metric.
4. Script output (`rebalance`, `regcurve` or `nowcast`) where sizing matters.
5. Hand-off: the verdict feeds [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (catalysts and risks) and
   [rv-devils-advocate](../rv-devils-advocate/SKILL.md) (crowding and the tail).

## Scripts
- [`scripts/alm_hedge_flow.py`](scripts/alm_hedge_flow.py) has three subcommands. `rebalance` gives the receive DV01
  needed after a parallel shock to hold a hedge ratio (the convexity of ALM hedging), optionally in 10y-eq. `regcurve`
  builds the UFR/LLFR-extrapolated liability curve from `curve_zero` and splits liability DV01 into market ≤ FSP, LLFR
  and UFR for each α. `nowcast` fits the funded-ratio regression on `macro_series` and applies this month's factor
  moves. Run `python scripts/alm_hedge_flow.py --help`. `--selftest` checks the Tuckman pension numbers, a
  zero-coupon repricing, finite-difference DV01s and recovery of known regression betas.

## Related skills
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): the spread that most ALM flows move
- [curve-butterflies](../curve-butterflies/SKILL.md): 10s20s30s and 20y richness
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): 15y10y/25y10y and long forward kinks
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): residuals to classify as structural or dislocation
- [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): 10s30s and 30s50s trades
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): long-end convexity and delta-hedged forward flatteners
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): Formosa/callable insurer demand
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): the other big convexity hedger (servicers, GSEs, banks)
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): crowding around the structural flow
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): long-end block prints and direction
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): Eurex/JSCC/CME vs LCH basis as a domestic-client flow tell
- [xccy-basis](../xccy-basis/SKILL.md): AUD super funds, GBP BPA, Japanese lifer hedging
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): LDI linker demand and inflation basis
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): supply offsetting ALM demand, WAM
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): long-end term premium vs holder mix
- [fi-curve-construction](../fi-curve-construction/SKILL.md): Smith-Wilson/UFR extrapolation mechanics
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): key-rate liability DV01 and 10y-eq mapping
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): LDI collateral, bond CSAs, margin liquidity
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): reserve-manager and front-end demand
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): year-end and fiscal-year-end flows
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md), [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): hand-offs

## References
- Citi Research (Searle, Appeddu et al.) - European Rates Weekly: What to do about OATs? (1 Oct 2026): Solvency II balance sheet, FSP/LLFR/UFR extrapolation, VA/CSSR/RCS, Macro VA, risk-margin formulas
- Citi Research (Searle, Harju et al.) - European Rates Weekly: A QT revolution (17 Sep 2026): Solvency II effective dates, α 0.20→0.11 phase-in, CoC 4.75%, insurer room by country, EGB/SSA WAM
- J.P. Morgan (Younger, Salem) - Interest Rate Derivatives: Issuance, pensions, and long-end spreads (14 Sep 2018): funded-ratio nowcast regression, pensions in Treasuries vs swaps
- J.P. Morgan (Younger, St John) - Pension re-risking and long-end swap spreads (3 Apr 2020): pension return attribution, STRIPS as a proxy, who buys duration in which format
- J.P. Morgan (Younger, St John) - What about Bonds? SLR relief, Treasury supply, and long-end spreads (2 Apr 2020): structural flow balance sheet by format, VA hedging size
- J.P. Morgan (Younger, Salem, St John) - Markets struggle to feed the convexity beast (28 Feb 2020): hedger duration tracking, bank and VA duration changes
- J.P. Morgan (Younger, St John) - Will mortgages bail banks out of their duration short? (27 Mar 2020): bank deposit/MBS duration gap and swap receiving
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): pension duration/convexity matching, swap use by pensions, sector ENNs
- Alexander Düring - Fixed Income Trading and Risk Management (Wiley, 2021): preferred habitat, UFR short convexity, JGB lifer target yields, natural payers/receivers
- Citi Research - US Rates Weekly: Pension plan for 20s? (9 Oct 2026): funded-ratio buying steps, glide-path capacity, pension yield trigger
- Citi Research - US Rates Weekly: The rocky road to a steeper curve (18 Jan 2019): pension rebalancing and 30y spreads
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Buying vol for less (25 Sep 2019) and Rates Vol Lab: In search of cheap vol (17 Jan 2020): GBP 20y ALM richness, 15y10y/25y10y flattener
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Trading long-dated convexity (9 May 2019): VA hedging risk and equity correlation
- JWS Macro - Duration Is Diseased: What Can Stop the Rot? (4 Sep 2025): Dutch transition DV01, UK post-LDI demand loss
- JWS Macro - #3: Iran & Front End Rates (8 Mar 2026): March 2026 10s30s flattening as an unwind of Dutch-flow steepeners
- Nordea Markets (Svendsen) - EUR rates: How about that outright receiving (26 Sep 2025) and The quiet game (12 Aug 2025): Dutch year-end receiving, crowding
- Nordea Markets (Vainikainen) - EUR Rates Flash (24 Jan 2020; 5 Feb 2020): forced ALM receiving risk, Eurex–LCH basis, 30s50s vs vol
- BofA Global Research (Swiber) - UST supply & demand in '25 (26 Nov 2024): funded-status shock mapping, STRIPS
- BofA Global Research - Bond market seasonality explained (6 Jun 2022): March JGB flattening from lifer buying
- J.P. Morgan - Cross currency basis 2H25 Outlook (5 Jun 2025) and 4Q24 Outlook (26 Sep 2024): AUD super long-tenor receiving, GBP BPA flows
- J.P. Morgan - Global Fixed Income Markets Weekly (21-22 Aug 2026) and Japan Fixed Income Markets Weekly (21 Feb 2025): lifer ESR, bank IRRBB capacity, bank super-long buying
- Credit Suisse - PCA Unleashed (24 Oct 2012): Dutch FTK reform as structural residual
- CFTC Office of the Chief Economist (McPhail, Schnabl, Tuckman) - Do Banks Hedge Using Interest Rate Swaps? (2023): limits of bank swap hedging
- CFTC MRAC - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): instrument choice by insurers, pensions and funds
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): 2022 LDI episode
- Credit Suisse Fixed Income Research (Li, Chang) - US Treasuries Futures Focus: New Ultra Long Contract (28 Sep 2009): ultra-bond futures as an LDI substitute for 30y swaps
- Financial Times Alphaville (Wigglesworth) - 'Treasury demand has become materially more valuation-sensitive' (20 Aug 2026): holder mix and yield sensitivity
- Quantitative Finance Stack Exchange - Why does the ultra long-end of a yield curve invert? (2019) and Downward Sloping Swap Spread Curve (Dec 2020): LDI as regulatory-fiat demand, swap-spread curve slope by market
- Klingler & Sundaresan - An Explanation of Negative Swap Spreads: Demand for Duration from Underfunded Pension Plans (Journal of Finance, 2019) (external): pension duration demand and 30y spreads
- Vayanos & Vila - A Preferred-Habitat Model of the Term Structure of Interest Rates (Econometrica, 2021) (external): theory of habitat demand vs arbitrageurs
