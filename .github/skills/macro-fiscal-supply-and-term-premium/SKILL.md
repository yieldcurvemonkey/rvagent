---
name: macro-fiscal-supply-and-term-premium
description: 'Fiscal supply and term-premium analysis for G10 government curves and swap spreads. Splits a long-end move into policy path, term premium and supply or fiscal premium; covers deficit and debt paths, bill share, WAM, coupon sizes, refunding, buybacks, long-end auction cuts, net versus gross duration supply, fiscal convexity, sovereign spread betas, debasement and solvency screens, and election priors. Use when a trader asks whether a 30y or 10y sell-off is term premium or fundamentals, what a deficit, issuance mix or bill share does to 20y and 30y swap spreads, whether a buyback or auction cut is a real signal, fiscal steepener or bear steepener, term premium, TP, fiscal risk premium, supply glut, fiscal dominance, bond vigilantes, the 30y at 5 percent, OAT-Bund or gilt-Bund fiscal beta, debasement trade, gold and breakevens, or a midterm steepener. Auction and buyback event mechanics: bond-supply-and-cashflow-trading; model-based term premium: curve-term-structure-models.'
---

# Macro fiscal supply and term premium

Long yields equal the expected policy path plus a term premium (TP) plus whatever else a given measure carries
(asset-swap, supply or fiscal premium). Deficits, issuance mix and central-bank balance-sheet runoff act mainly on the
premium, not on the policy path. They show up most cleanly in swap spreads and in the 20y and 30y sector, and only
weakly in curve shape. This skill separates a move into those pieces, sizes supply in duration units, and tests
fiscal and debasement narratives against the data they must confirm.

## When to use
- "Is the 30y move term premium or policy path?" / "fundamental or TP?" / "what is the TP doing?"
- Deficit revisions, CBO or budget projections, a fiscal event (budget, tax cut, shutdown) or an election.
- Issuance mix: bill share, WAM, coupon sizes, refunding guidance, buybacks, long-end auction cuts, net cash
  requirement, supply in DV01.
- Fiscal convexity or fiscal fair value for the 10s30s or 5s30s curve; sovereign spread betas (OAT-Bund, BTP-Bund,
  gilt-Bund, JGB free float).
- Debasement, loss-of-confidence or yield-control narratives; "is the Treasury defending the 30y?"
- Not for: fitting a Gauss+ or ACM model (see curve-term-structure-models), TFP construction and the spread-curve
  book (spread-swap-spreads-and-asw), debt-limit and TGA plumbing (stir-bills-and-money-market-spreads), or pension
  and insurer duration demand (flow-structural-alm-demand). Hand off to those and use their outputs here.

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Zero curve nodes (continuous, ACT/365F) | `curve_zero` | daily, ≥ 10y | Forward splits. Government curves use `<CCY>-GOVT-<issuer>` |
| Par OIS / swap and government par rates | `curve_par` | daily, by tenor 1y to 30y | Policy path (1y1y, SOFR/ESTR/SONIA OIS), 5s30s, 10s30s |
| Swap spreads and ASW | `swap_spreads` | daily, by tenor | Sign travels with each row. `spread_*` = swap minus govt (US); `asw_*` = govt minus swap (EGB) |
| Bond yields, outstanding amounts | `bond_quotes`, `bond_static` | daily, ≥ 2y | Amount outstanding for DV01 supply and benchmark duration |
| Auction results | `auctions` | per auction, ≥ 2y | `tail_bp`, bid-to-cover; respect `results_ts_utc` |
| Fiscal, debt, reserves, MMF, breakevens, GDP | `macro_series` | release vintages | Use `unit` and `consensus`; keep vintage for revisions |
| Issuance plan (gross and net by bucket and quarter), buyback calendar, bill share | `issuance_plan` (bill share = `bills` over `all` gross); dated buybacks in `auctions` (`operation=buyback`) | quarterly plans and announcements | If missing, ask the data adapter. Never invent |

Missing data is a stop, not a guess. A TP estimate with no curve history is not an output.

## Conventions (state once, then keep)
- Rates in percent. Spreads, TP and forward premia in bp. Durations in years. DV01 in currency per bp, positive
  for long duration (receive fixed, long bond).
- Curve spreads: 2s10s = 10y minus 2y. Flies: 2s5s10s = 2 x 5y - 2y - 10y.
- **US swap spread** = swap yield minus Treasury yield. Negative means Treasuries yield more than swaps (Treasuries
  cheap to swaps). Restate every move in levels: "Treasuries richen" = the spread rises toward zero; "Treasuries
  cheapen" = it falls more negative. The sources use "widen" in both senses. BofA's UST-OIS convention is the
  opposite sign: negative there = Treasury rich to OIS.
- **EGB asset-swap spread** = govt minus swap; positive = bond cheap to swaps. Some sell-side notes quote the
  opposite sign (swap minus bond). One Citi note describes deeply negative long-end EGB swap spreads as "bonds
  cheap to swaps", which matches the swap-minus-bond convention. Confirm the sign in `swap_spreads` before trading.
- Hedge notation: a receiver of fixed has positive DV01.

## G10 differences
The market-specific detail is in [market-and-event-notes](references/market-and-event-notes.md). The short version:
- **USD:** bill share and WAM are the main levers, and swap spreads are the main fiscal gauge.
- **EUR:** use net cash requirement (NCR) against gross issuance, and read OAT-Bund and BTP-Bund as fiscal gauges.
  Solvency II changes long-end insurer demand.
- **GBP:** DMO long-end cuts and the BoE gilt redesign are one-off repricings. Fiscal risk clusters around the
  Budget. LDI leverage can drive a sell-off more than fiscal news.
- **JPY:** MoF super-long cuts and BoJ holdings matter. Free float is a swap-spread fair-value input.
- **AUD, NZD, CAD, CHF, SEK, NOK:** the sources have little on fiscal supply. Use these only as cross-market context.

## Method

### 1. Split the move into policy path, term premium and residual
For a forward from year n-1 to year n (annual compounding):

    1 + f(n-1,n) = (1 + z_n)^n / (1 + z_(n-1))^(n-1)

Forward = expected short-rate path + duration x lambda - convexity bias, with convexity bias = 0.5 x C x sigma^2
(C in years squared, sigma in decimal). Equivalently, premium = forward - expected path + convexity bias. The expected
excess return of a bond over the short rate is `E[dP/P] - r0 = lambda x D`, so the premium scales with factor
duration (Tuckman and Serrat, 2022, eq. 8.18, App. A8). The first-order split for one tenor over a window is:

    Delta TP ~ Delta yield - Delta expected policy path + Delta convexity

Use one-period forwards, end-of-horizon duration and convexity, and constant-maturity yield changes. The one-period
approximation `f(1,n) - s(n-1) ~ E(Delta s) + BRP_n/(n-1)` is from Ilmanen (Part 2, 1995). The forward-spread premium
FSP = term spread + roll-down (n-1)(s_n - s_(n-1)); for a linear spot curve it is twice the term spread (Ilmanen, Part 2, 1995).

**Identification.** Forwards alone cannot separate an expected short-rate drift from a premium. Every decomposition
rests on an identifying assumption, which you must state:
- expectations hypothesis (lambda = 0) or risk-premium hypothesis (E(dr) = 0). Ilmanen judged the risk-premium
  hypothesis "the more realistic" of the two polar cases (Part 2, 1995);
- a flat expected short rate beyond a long horizon, so forwards beyond it are premium plus convexity (the Gauss+
  identification, using the 14y and 15y forwards, Tuckman and Serrat, 2022);
- a survey of expectations (see step 2).

### 2. Estimate the premium with at least two methods and report the spread between them
1. **Survey-anchored.** `BRP_n ~ (forward-implied change - survey-expected change) x duration at horizon`, annualised.
   Ilmanen's 1981-94 version used about 27 semi-annual surveys (Part 2, 1995).
2. **Return-based.** Average excess returns over a neutral sample: start and end yields similar. Ilmanen used
   1970-94 (about 300 monthly observations) and found no conclusive evidence of rising expected returns beyond two
   years of duration (Part 3, 1995). Use the geometric mean for compounding and the arithmetic mean as the
   expected-return measure. Disinflation samples overstate the premium; very long samples understate it. Plot premia
   against return volatility, not duration, when the vol term structure is inverted.
3. **Regression residual (quick proxy).** `5s30s_t = a + b * y5_t + e_t`, TP_t = e_t, rolling 5-year window. Tells
   you what steepness the level does not explain. The residual is in-sample: the fit includes day t, so it understates
   current deviations. For a signal, fit on a window ending at t-1 (no look-ahead) and treat it as a regime read. Citi reads its rise since the post-Covid fiscal expansion as
   dollar-negative (Citi, Global Macro Strategy, 31 Jul 2026).
4. **Model.** Gauss+ (three-factor cascade, Tuckman and Serrat, 2022). Defaults from that book: 8-year sample with
   annual decay weight 0.8; short rate = fed funds target, not general collateral repo, because repo spikes are
   unrelated to policy expectations; fit the 2y and 10y one-year forwards exactly for daily trading. Worked numbers are
   in [worked-examples](references/worked-examples.md), section 2. Other models in common use include ACM and
   Kim-Wright (external). Keep the model name in every output label.
5. **Cross-check the long-run anchor.** Compare the model's long-run expected short rate with a fundamental anchor
   (real-rate forecasts plus long-run inflation). The gap is a long-run view, not a timing signal.
6. **Does the premium vary?** Regress the realised forward change on the observed forward-minus-short-rate spread,
   `f(n-1,t+1) - y1_t = a + c_n (f(n,t) - y1_t) + e`, H0: c_n = 1, with Newey-West errors because the horizons overlap.
   Rejection means time-varying premia. For the Bund in 1986-98, c_n was 0.95-0.98 (s.e. 0.012-0.029): the pure
   expectations hypothesis was rejected, yet a constant premium was a fair approximation (Cassola and Luis, in Dunis,
   Laws and Naim, 2003).

Long-duration decompositions are imprecise: a few bp of error in the expected yield change, times a 10y or 30y
duration, is larger than the premium itself. Report the premium as a range, not a point.

### 3. Attribute a sell-off (decision ladder)
Run in order, and stop when the answer is clear.
1. **Policy path.** Change in the 1y1y OIS or the policy-meeting pricing over the same window. If it explains most
   of the move, it is not term premium.
2. **TP residual.** Total yield change minus policy-path change, on swap-based yields so the asset-swap leg drops out.
   Cross-check with a second model (step 2).
3. **Cash and supply test.** Asset-swap spread flat means the move is not cash or supply-led. Show ASW as cash minus
   swap in the same tenor. In 2025 the 30y UST ASW was 85 to 85 and gilt ASW went 90 to 88 while the move was
   real-yield-led (JWS Macro, Duration is diseased, 4 Sep 2025).
4. **Inflation test.** Stable breakevens mean the move is real-yield-led. Use 5y5y and 10y breakevens.
5. **Fundamentals check.** Growth against trend, curve against history. Real GDP below trend for three quarters and a
   2s30s that is not abnormally high argue against "fundamentally justified" higher long yields (Citi, US Economics
   Weekly, 21 Aug 2026). A residual approach can give the opposite answer: J.P. Morgan applied a 10y-model
   attribution (2021-25 fit, s.e. 16bp) to the 30y and called a residual within one standard error "fundamentally
   justified" (Global FI Markets Weekly, 21-22 Aug 2026). That is an out-of-sample use of a 10y fit. Run both
   and report the disagreement.
6. **Credit-demand rule.** If long yields rise on credit demand, the policy rate has to rise to hold conditions, even
   when the chair frames higher long yields as tightening (J.P. Morgan, US Weekly, 21 Aug 2026).
7. **Regime.** The worst backdrop for the dollar is a rising term premium with a falling Fed terminal. A term-premium
   rise with a stable terminal is a different case (J.P. Morgan, FX Markets Weekly, 21 Aug 2026).

### 4. Measure supply in duration units, net of central banks
- **Net duration supply.** `S_10y-eq = sum_i N_i x D_i / D_10y`, where `N_i` is net market value sold to the public in
  bucket i = gross issuance minus maturities minus central-bank net purchases (QT runoff adds to supply), and `D_i`
  is that bucket's modified duration. Use DV01, not notional. Net out central-bank holdings as flows, not stocks
  (Citi, European Rates Weekly, 1 Oct 2026).
- **Absorption check.** Net supply ex-Fed (10y-equivalents) less the projected purchases of each buyer group (banks,
  pension and insurance, funds, households, foreign) leaves a residual that price must clear. BofA's 2025 projection:
  net new supply USD 1,610bn + Fed runoff 75bn - large-buyer demand 1,250bn = USD 435bn for other buyers (BofA, 26 Nov
  2024). A buyer base shifting from official (about 50% in 2006 and 2016, 27% in 2026) to price-sensitive private
  holders raises the yield needed to clear (FT Alphaville, 20 Aug 2026).
- **Supply-to-yield rule.** A permanent 1% of GDP increase in 10y-equivalent duration is about 10bp on the 10y
  (Crawley et al., FEDS Note, Jun 2022, as cited in BofA, 2 Jul 2025). Unadjusted supply gives about 7bp (Gagnon et
  al., 2011). Trade direction and rough size, not decimals: estimates vary widely.
- **Financing waterfall.** `borrowing need = deficit + other adjustments + change in TGA`;
  `net coupons = gross coupons - public coupon maturities - buybacks`; `net bills = borrowing need - net coupons`.
  Bill share = bills / marketable debt. Worked FY26 example in [worked-examples](references/worked-examples.md), section 5.
  A TGA rebuild after a debt-limit resolution enters through the TGA term and is financed mostly in bills: bills
  outstanding rose 29% (2017) and 49% (2023) in the six months after resolution, against a projected 2% in 2025 (BofA,
  Funding & debt limit: history lessons, 27 Jun 2025).
- **Bill share bands.** TBAC's guidance was a bill share of about 20% over time, with 15% as the lower bound for
  market functioning. Since 1980 the average has been about 22.5%. BofA's 2025 tolerance was 25% (prior ceiling 22.5%),
  about one standard deviation above the post-2000 average (BofA, 2 Jul 2025). Conks called 30% or more "pushing it" (Conks, Great
  Rebalancing, Jul 2025). Use these as bands for rollover-risk discussion, not as triggers.
- **Bill-OIS uses flow, not stock.** Model bill-OIS on the 3m change in net bill supply. Large net paydowns coincided
  with very rich bills (to about -50bp); large net issuance with bills at about 0 to +15bp. Bill share alone is a
  weak predictor (Barclays, US short interest rate primer, Jan 2025).
- **Private WAM.** Private supply = funding need minus Fed financing. With total WAM fixed, a lower SOMA WAM raises
  private WAM. A 2019 regression of spreads on private WAM had a negative slope: a longer private WAM went with a lower
  10y futures-to-OIS spread (R-squared 0.51) and a poor fit in the 2y (0.09). Citi traded spread-curve flatteners
  on stock-adjusted betas (25% of the regression beta) (Citi, 18 Jan 2019). Treat coefficients as period-specific.

### 5. Fiscal convexity and fiscal fair value
- **Fiscal FV rule of thumb.** 1pp of deficit/GDP is about 20-30bp on long yields (Barclays, Global Rates Weekly, 2 Oct
  2026). A scenario model of 10s30s (Citi, 3 Feb 2017) moved from 28bp too flat with no fiscal expansion to 35bp with
  a 2pp deficit rise. Derived here: about 3.5bp per pp of slope. Scenario-based, not a precise beta.
- **Fiscal convexity.** Higher rates raise debt-service costs, so a rates shock feeds back into supply. A +100bp
  rate path adds more than USD 3trn to borrowing over 10 years (Barclays, 2 Oct 2026). Unlike MBS or futures
  convexity, it does not fade as rates rise. Hedge with long-dated forward vol (e.g. the 10y-forward 5y10y option
  structure), not with a curve trade.
- **Sovereign spread betas.** OAT-Bund moves about 10bp per 1pp of GDP change in one-year-ahead deficit expectations.
  Cross-country spread to OIS against debt/GDP is about 1-3bp per ppt (GS, Reaching Limits, 2 Oct 2026).
- **Implied-move test.** `implied fundamental repricing = observed spread move / beta`. Compare with forecast
  revisions. Excess is risk premium or uncertainty, not fundamentals. Worked example (Sept 2026 OAT-Bund) in
  [worked-examples](references/worked-examples.md), section 8.
- **Free float (JGB).** Free float = debt less central-bank holdings, percent of GDP. Adding about 5pp of free float
  would tighten fair-value 10y spreads by about 3bp (GS, 2 Oct 2026). Use as a fair-value input, not a trade signal.

### 6. Screen debasement, solvency and yield-control narratives
- **Gate for a fiscal-dominance or debasement call.** Require **all** of: breakevens widening; outperformance of the
  fiscal-basket currencies (good-fiscal minus bad-fiscal); and a dovish central bank. A fiscal or term premium rise
  hurts a currency only when policy is too easy (J.P. Morgan, FX Markets Weekly, 21 Aug 2026). In Aug 2026 none was present.
- **Debasement monitor.** Gold, USD, steeper UST curve, breakevens and the S&P. Use it as a monitor, not a trigger.
- **Yield suppression moves the pressure.** Treasury buybacks or other yield-suppression measures tend to shift
  stress into the dollar, gold and bitcoin ("conservation of energy", Citi, Global Macro Strategy, 19 Aug 2026). Trade
  the transmission, not the level.
- **Solvency beliefs and flows.** Stated fear of a debt crisis moves beliefs far more than holdings (Delao and Li,
  NBER WP 35612, Aug 2026). Treat fiscal-news shocks as risk-perception events unless flows confirm.

### 7. Use election priors, then check
- Midterm event study (±125 business days, conditioned on the outcome). 30y swap spreads widened the week after 4
  of 5 midterms, with the median back to 0bp within a month (Citi, Multi-Asset midterm note, 2 Oct 2026; Citi,
  Quantitative Global Macro, 14 Aug 2026). "Widened" here means the long-end spread moved toward zero as the long
  end strengthened and fiscal tail risk was priced out, so Treasuries richened. Use as a prior. Event windows and
  small-sample caveats are in [market-and-event-notes](references/market-and-event-notes.md).
- **Pick analogs by state, not by label.** Match episodes on the variables that drive the response (for a debt-limit
  resolution: the remaining ON RRP buffer and the percentage growth in bill and total marketable supply), then average the
  1, 3 and 6-month changes using a 1-month average over each window. Treat resolutions less than six months apart as one
  episode, and drop episodes with a far larger liquidity buffer (BofA, Funding & debt limit: history lessons, 27 Jun
  2025). Worked case in [worked-examples](references/worked-examples.md), section 13.
- Catalysts stack: a refunding the day after an election, or a cut to long-end sizes in favour of bills, moves
  spreads further toward zero (Treasuries richen) as supply falls.

## Worked examples
These are the anchors. Full ledger in [worked-examples](references/worked-examples.md).

- **Risk-premium identity.** r0 = 1%, D = 5, lambda = 10bp per year of duration: expected return 1.5%; Sharpe 10% at
  sigma 100bp (Tuckman and Serrat, 2022, App. A8).
- **Gauss+ 10y premium.** lambda 0.09 x sigma 1% x D 10 x loading 0.7 = 63bp; convexity about 24bp; a 3% 10y forward
  implies a 2.61% expected 1y rate 9y ahead (Tuckman and Serrat, 2022).
- **TP table, Oct 2026.** 10y total TP 1.35 against a 1.31 average; 30y 1.93 against 1.78. The TP level is near its average
  (2y and 30y are 12-15bp above). That does not say the latest move was not TP: Barclays had the post-FOMC 10y rise at
  about 25bp, of which about 16bp TP, and the SF Fed and ACM models disagreed (Barclays, Global Rates Weekly, 2 Oct 2026).
- **US buyback, Aug 2026.** Operations doubled from USD 2bn to at least USD 4bn each. The 30y gave back most of a 9bp
  fall the next day (30y +6bp to 5.24%). Measured half-life about one day (Financial Times, 20 Aug 2026).
- **OAT-Bund test, Sept 2026.** A 50bp rise in the OAT-Bund spread at 3bp per ppt needs a debt/GDP repricing of about 15-17ppt, against
  deficit revisions of 0.4 and 0.5pp of GDP (about 4-5bp at 10bp per pp). Mostly risk premium (GS, 2 Oct 2026).

## Signals & interpretation
- **TP up with stable breakevens and flat ASW** → real-yield-led TP. Trade real or nominal curve, not supply.
- **Curve twist steepening on fiscal news** → TP-driven, almost fully (Citi, US Rates Weekly, 21 Aug 2026, 2s10s
  residual vs a 10y ACM-style TP). Check that the policy path did not move.
- **30y at a level cited as a trigger** (5.3% and 5.5% appear in Aug 2026 sources) → expect a Treasury response in rungs: larger
  buybacks, then no-coupon-increase guidance, then shorter 20y and 30y issuance, then ending the 20y. Read the rung, not the level alone. The 20y benefits most from a cut
  (Citi, US Rates Weekly, 21 Aug 2026).
- **Buyback announced off-cycle, at double size, after a price high** → a price-level operation, which tends to be
  faded. Plumbing-driven operations (failed auction, forced unwind) are different (WSJ Opinion, 24 Aug 2026).
- **Bill share rising through about 25%** with no coupon increase → rollover and supply-premium risk. Expect the 3-6m
  bill to carry a term-premium-like concession (BofA, 1 Oct 2026).
- **Top-quintile one-month TP rise (more than +10bp)** → equity-negative regime signal (Kim-Wright read in Willer and
  Saunders, 2026; information ratio -0.20 against +0.46 to +0.92 in the other quintiles, much of it from the GFC).
  Use as a risk overlay.
- **Bank breakeven.** With a 15bp Libor-repo gap, a 20% tax rate, a 5% leverage ratio and a 12% return-on-equity
  hurdle, the source's UST-on-ASW carry breaks even only at a swap spread below about -60bp (TBAC, Feb 2021). Check: (60 + 15)bp x (1/0.05) x (1 - 0.20) = 12%. Use as a
  rough floor on how far long-end spreads can go on carry alone.
- **TFP residual back inside one standard error of fair value, or a TFP move that needs an implausible WAM shift** →
  take profits and go neutral on spread-curve trades that rely on TFP mean reversion. J.P. Morgan unwound 5s30s
  spread-curve flatteners at +0.2bp when TFP was within 1 s.e. (IRD Strategy Update, 5 Nov 2025) and took profit on
  10s30s spread-curve steepeners in Aug 2026 (Buying back time, 19 Aug 2026).
- **Spread fair value versus fiscal beta.** A move much larger than beta times the forecast revision is risk premium.
  Keep it out of the fundamental fair-value trade until the premium reverts or the revision arrives.

## Pitfalls
- **Forwards are not expectations.** Low long forwards are not necessarily rich, and high ones not necessarily cheap
  (Ilmanen, Part 1, 1995). Strip convexity and premium before reading a forward.
- **Premia are unobservable and model-dependent.** Run at least two methods and state the identifying assumption. A
  rising model premium can come from a steeper curve in a low-inflation regime, not from bearishness (Tuckman and
  Serrat, 2022).
- **Model premia are revised.** Survey-anchored and affine models are re-estimated, so today's history of the premium
  is not what was visible then. In a backtest use the vintage available at the time, and shift any signal by one bar.
- **Period specificity.** Premium estimates from one sample do not transfer. Check subperiods (Ilmanen and Iwanowski,
  Part 7, 1996).
- **Supply moves swap spreads, not the curve.** Net supply and the 5y5y-minus-2y1y spread show no clear relation
  (Willer and Saunders, 2026). Trade supply in spreads and the 20y-30y sector.
- **Buybacks are small and not QE.** The effect is a short-lived signal. Do not size a buyback trade off notional
  (J.P. Morgan, FX Markets Weekly, 21 Aug 2026).
- **Announcement half-life.** Measure it (about one day in Aug 2026) before trading an announcement.
- **Debt-limit and bill-cut timing.** Bill-supply cuts and resolution rebuilds move bills and repo, not the long end.
  After the 2017-19 resolutions the average 2y and 5y UST-OIS change was under 1bp at 1 and 3 months and about 3bp at 6
  months, against averages of about 2-9bp in SOFR-FF, SOFR-IORB and bill-OIS (BofA, Funding & debt limit: history
  lessons, 27 Jun 2025; table and sign normalisation in [worked-examples](references/worked-examples.md), section 13).
  Use stir-bills-and-money-market-spreads for the front-end trade.
- **Model residuals move with regulation.** Big residuals appeared at regulatory shifts (2015, 2020). Regulation can
  outweigh supply for long periods (TBAC, Feb 2021).
- **Event priors are small-sample.** Five lost trifectas, one to three held. Effects fade within about a month.
- **Stale perishable numbers.** Debt-limit headroom ($1.12tn to $1.24tn across Aug-Oct 2026 notes), 30y levels and
  bill shares all change. Date every number you use.
- **Sign and unit traps.** Mixed US and EGB conventions; "widen" in both senses; percent versus decimal in `macro_series`.
- **Fiscal fear is not always fiscal news.** Leverage events (LDI margin calls in 2022) can drive the move more than the
  fiscal news. Look for forced selling and leverage before attributing the move to deficits (Willer and Saunders, 2026).

## Output
Return one block per market and date, in bp and percent, with dates and sources.

1. **Move decomposition** (table): window, total yield change, policy-path change, TP change (range across two or
   more methods), supply or fiscal residual, unexplained residual. Give the identifying assumption in one line.
2. **Supply in duration units** (table): net 10y-equivalent supply by bucket for the period, bill share against the
   bands, and the supply-to-yield estimate with its range.
3. **Fiscal test** (table): fiscal FV implied move, spread beta used, implied fundamental repricing, forecast revision,
   excess (risk premium), and the verdict (fundamental, premium, or mixed).
4. **Narrative gate** (checklist): breakevens, fiscal-basket FX, Fed tone; pass or fail for each.
5. **Flags**: data gaps, perishable numbers, sign conventions checked, source conflicts.
6. **Hand-off**: a one-line thesis with the instrument and tenor, and the hand-off to `rv-trade-idea-writeup`.

Do not output a trade without a stated premium range, an identifying assumption and a stop condition.

## Scripts
- [`scripts/tp_decomposition.py`](scripts/tp_decomposition.py): forward rates from a `curve_zero` CSV (annual or
  continuous compounding), the expected-return and Sharpe identities, the convexity bias, and term funding premium as
  minus the cross-sectional slope of spreads on duration. `python -I scripts/tp_decomposition.py --selftest` checks
  each against a case with a known answer. CLI: `python -I scripts/tp_decomposition.py <curve_zero.csv> --curve_id
  <id> [--date YYYY-MM-DD] [--compounding cont|annual]`.

## Related skills
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): Gauss+, ACM and Kim-Wright model fits; use for the model step.
- [macro-fair-value-models](../macro-fair-value-models/SKILL.md): macro regression fair values and residuals.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and ASW mechanics, TFP construction and trades.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auction, buyback and issuance-event trading.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill supply, bill-OIS, debt-limit and X-date mechanics.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): QT and reserve-management effects on the front end.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension, insurer (Solvency II) and bank duration demand.
- [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md): the policy path that the decomposition needs.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): event and geopolitical shocks that move fiscal risk premia.
- [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md): scenarios for the debasement and steepening branches.
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): hedging fiscal convexity with long-dated options.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): OAT-Bund, BTP-Bund, gilt-Bund and other fiscal-beta spread trades.
- [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md): sovereign credit premium in EGB spreads and ASW.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): breakeven and real-yield tests in the sell-off ladder.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): SLR and balance-sheet cost behind long-end spread residuals.
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC errors for overlapping-horizon premium regressions.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): swap and govt spread sign conventions per market.
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): write-up of the thesis, sizing and stop.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used in Inputs.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event risk and prediction-market probabilities.

## References
- Bruce Tuckman and Angel Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): forward decomposition (eq. 8.15-8.20), risk-premium identity (App. A8), Gauss+ recipe and worked numbers (App. A9).
- Antti Ilmanen - Understanding the Yield Curve, Parts 1-3 (Salomon Brothers, May to Jul 1995) and Part 6: A Framework for Analyzing Yield Curve Trades (Nov 1995): bond risk premium definition (Part 1), expectations vs premia and survey premia (Part 2), return-based premia over 1970-94 (Part 3), forward-spread premium and roll-down identity (Part 6).
- Antti Ilmanen and Raymond Iwanowski - Understanding the Yield Curve, Part 7 (Salomon Brothers, Feb 1996): time-varying, countercyclical premia and subsample caution.
- Barclays Research - Global Rates Weekly: The urgency question (2 Oct 2026): TP table, model disagreement, fiscal FV and convexity, OAT stress.
- Goldman Sachs - Global Rates Trader: Reaching Limits (2 Oct 2026): fiscal betas for OAT-Bund, debt/GDP sensitivity, JGB free float.
- Citi Research - European Rates Weekly: What to do about OATs? (1 Oct 2026): Solvency II demand, NCR versus gross, fair-value pitfalls.
- Citi Research - US Rates Weekly: Can Secretary Bessent and Chair Warsh save the curve? (21 Aug 2026) and Global Macro Strategy: Our Take on US Treasury Announcement: Buy Gold (19 Aug 2026): supply escalation ladder, 20y and 30y triggers, ACM-based TP read, buyback as price management.
- BofA Global Research - US Rates Viewpoint: Lower UST WAM => backdoor easing (2 Jul 2025): financing waterfall, bill-share bands, supply-to-yield rule.
- Barclays (J. Abate) - US short interest rate primer (Jan 2025): bill share and TBAC guidance, flow-based bill-OIS, debt-ceiling mechanics.
- Treasury Borrowing Advisory Committee - Charge: Swap Spreads (Feb 2021): deficits and long-end swap spreads, bank breakeven, regulatory residuals.
- J.P. Morgan - Buying back time (19 Aug 2026): term funding premium, implied WAM shift test, profit-taking on TFP-driven spread trades.
- Citi Research - US Rates Weekly: Going nuclear (on the curve) (3 Feb 2017): deficit-based 10s30s fair value and scenario sizing.
- Citi Research - Quantitative Global Macro Strategy: How to trade US midterm elections (14 Aug 2026) and Multi-Asset Strategy: US midterms on the mind (2 Oct 2026): election event study, swap spreads as fiscal gauge, refunding catalyst.
- Ricardo Delao and Wenhao Li - Beliefs about Government Debt Valuation and Sustainability (NBER Working Paper 35612, Aug 2026): six-source backing taxonomy, stress capacity, belief-to-action gap.
- Citi Research - US Rates Weekly: The rocky road to a steeper curve (18 Jan 2019): private WAM regression and stock-adjusted beta.
- Dirk Willer and Alex Saunders - Trading Global Macro Markets (Wiley, 2026): Kim-Wright TP signal, supply vs swap spreads, the Truss case, leverage-driven fiscal panics.
- Citi Research - Global Macro Strategy - Views and Trade Ideas: The Messi Theory of Interest Rates (31 Jul 2026): residual 5s30s term-premium proxy and dollar read.
- Citi Research - US Economics Weekly: The resilient narrative of US resilience (21 Aug 2026): real GDP below trend and 2s30s versus history.
- JWS Macro (Substack) - Duration is Diseased: What Can Stop the Rot? (4 Sep 2025): real-yield-led checklist, ASW and breakeven tests, TP components.
- J.P. Morgan - US Weekly Prospects and FX Markets Weekly, Currencies amid long-end UST shenanigans (both 21 Aug 2026): credit-demand rule, regime vs USD, not-QE reading, debasement gate.
- Financial Times - US long-term bonds slide as Treasury secretary Bessent's intervention fails to soothe investors (20 Aug 2026): buyback half-life and 30y reversal.
- Wall Street Journal (Opinion) - Let the Bond Market Speak (Stanley Druckenmiller, 24 Aug 2026): buyback as price management and signal versus plumbing.
- BofA Global Research - US Rates Watch: Funding & debt limit: history lessons (Mark Cabana, Katie Craig, 27 Jun 2025): state-matched analog method, post-resolution changes in funding spreads and 2y-5y UST-OIS, bill-supply growth around debt-limit episodes.
- BofA Global Research - US Rates Watch: Bills: policy and supply uncertainty = cheaper (1 Oct 2026): 3-6m bill term-premium-like concession.
- Conks (Substack) - The Great Rebalancing (16 Jul 2025): bill-share tolerance and the war on long-end supply.
- Christian Dunis, Jason Laws and Patrick Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003), Ch. 3 (Cassola and Luis): forward-regression test of the expectations hypothesis on the Bund curve.
- BofA Global Research - US Rates Viewpoint: UST supply & demand in '25 (26 Nov 2024): net supply against buyer-base absorption.
- J.P. Morgan - IRD Strategy Update: No alarms and no surprises (5 Nov 2025): TFP definition and exit rule.
- J.P. Morgan - Global Fixed Income Markets Weekly (21-22 Aug 2026): 30y attribution with a 10y fair-value model, DMO long-end cut event study, AUD swap-spread models.
- Financial Times Alphaville - The US Treasury is buying long bonds, but not very many (Toby Nangle, 20 Aug 2026) and Treasury demand has become materially more valuation-sensitive (Robin Wigglesworth, 20 Aug 2026): net long-end supply arithmetic and the official-to-private ownership shift.
- Citi Research - Macro Think Tank: Top of Mind (21 Aug 2026); Global Asset Allocation House Views: Bessent And The Back End (21 Aug 2026); European Rates Strategy: Latest views (20 Aug 2026) and European Rates Weekly: A QT revolution (17 Sep 2026): buyback size and signal, JGB supply management, EGB gross versus net supply, BoE QT redesign.
- Nordea Markets - EUR Rates Flash (17 Mar 2020): sovereign credit premium in ultra-long ASW.
- Marko Papic - Geopolitical Alpha (Wiley, 2021): market constraint on fiscal policy and the euro-crisis precedent.
- BofA Global Research - Global Inflation-Linked Primer (2nd ed., 22 Jul 2025): UK linker share of debt and interest bill.
- Gagnon, Raskin, Remache and Sack (2011); Crawley et al., FEDS Note (Jun 2022); Adrian, Crump and Moench (JFE, 2013); Kim and Wright, FEDS working paper (2005) (external): supply-to-yield rules and the ACM and Kim-Wright term-premium models.
