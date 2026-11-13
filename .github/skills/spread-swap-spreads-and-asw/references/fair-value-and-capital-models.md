# Fair-value, capital and regression models for swap spreads and ASW

Detail behind `SKILL.md`. Sign tags: **(S-G)** = swap minus govt, **(G-S)** = govt minus swap. Levels are dated snapshots, never
current. Regression coefficients are published in-sample fits: use them to size drivers, not to trade the residual unchecked.

## A. Funding + credit + capital decomposition (what an ASW "should" be)

Source for this whole section: Huggins & Schaller, Fixed Income Relative Value Analysis, 2nd ed., Wiley, 2024 (Ch. 10-12, 17-18) and
Huggins & Schaller, SOFR Futures and Options, Wiley, 2022 (Ch. 4, 9).

A repo-financed bond receives coupon and pays repo; an asset swap pays the coupon and receives the reference rate. So an
asset-swapped bond is **pay repo / receive reference rate**, and the ASW (G-S, "reference + X") is a basis swap plus a credit leg:

| Reference | Fair ASW | Capital basis | Term risk |
|---|---|---|---|
| SOFR (secured) | - expected specialness (discounted) + adjusted CDS (+ haircut cost) | no | no |
| OIS (unsecured, e.g. ESTR, SONIA, TONA) | - specialness - GC-OIS capital basis + adjusted CDS | yes | no |
| IBOR (legacy) | - specialness - GC-OIS - OIS-IBOR term/credit + adjusted CDS | yes | yes |

- **Capital basis (unsecured minus secured O/N) = g x q x d.** g = cost of equity, q = interbank risk weight (min 20%), d = capital
  ratio per 100% RW asset (8%). g = 10% gives 10% x 1.6% = **16bp**. d from 8% to 12% lowers the Bund ASW vs OIS/IBOR by 50% (-20bp to -30bp: the capital basis scales by 1.5x);
  SOFR ASW is unaffected by g, q, d. g and the marginal bank are unobservable, so use it qualitatively.
- **Repo-LIBOR model**: L = R/(1-p(1-c)) + p(1-c)/(1-p(1-c)) + qd(g-b)/(1-p(1-c)). With p = 0, L = b, q = 20%, d = 8%:
  L - R = 1.6% x (g - L), so +5% cost of equity widens LIBOR-repo by 8bp.
- **Adjusted CDS** = 0.45 x market CDS (cash-settled; local-currency CDS trade at 30-60% of USD CDS) or 0.39 x for physical (delivery
  option ~6%). Never use raw CDS as the credit leg: USD Japan CDS 100bp means ~45bp of pure credit, raw CDS overstates fair JGB ASW by
  55bp. Test trades at 30/45/60bp adjusted CDS and prefer those that work across all three.
- **Haircut cost** = haircut x (replacement funding cost - repo). A 2% haircut funded 5% above SOFR = **10bp**. Adding it fits the 5y UST
  SOFR-ASW model (Jan 2021-Sep 2023); the implied marginal haircut cost was 8bp in Sep 2023; early 2022 sat ~10bp above the model
  (flow-driven). Haircuts rise with maturity so they steepen every ASW curve.
- **Specialness** rises with maturity and peaks at deliverable points (German expected specialness approx. 3bp at 5y Bobl deliverable,
  5.9bp at 10y Bund; ABN Amro note via H&S, 17 Apr 2002). It is asymmetric (a call option): regress it out, do not treat as noise.
- **Worked fair value**: 10y Bund ESTR-ASW (G-S) = -16 (capital basis, enters negative) + 15 (adjusted 10y German CDS) - 6 (average specialness, a GC-repo drag) = **-7bp**.
- **Term structure**: credit rises with horizon (upward-sloping ASW curve), specialness pulls long ASW down, capital basis and term
  risk are flat in maturity, haircuts steepen. 17 Oct 2023 SOFR-ASW of basis-swapped govies (G-S, chart reads): Bunds 1y -21, 5y -24,
  10y -22, 20y -3, 25y +3; USTs 1y +1, 5y +25, 10y +29, 20y +64, 25y +65; Gilts 1y -31, 5y -5, 10y +35, 20y +84, 25y +95.
  Long-end Bunds looked excessively rich vs CDS- and haircut-justified levels (idea: sell long Bunds vs buy USTs/gilts, all on SOFR ASW,
  only if the imbalance is judged ephemeral). Pick-up of synthetic EUR USTs over Bunds ~20bp at 1y, ~45bp at 5y.
- **Haircut schedules (Oct 2023, %)**. Fed (notes/bonds): <10y 2.0, 10-30y 2.9; TIPS 2.9/5.7; bills 1.0. BoE coupon/zero: 1-3y 1.5/1.5,
  3-5y 2.0/2.0, 5-10y 3.0/3.5, 10-20y 5.5/6.5, 20-30y 7.0/9.5, >30y 8.5/15.0. ECB DE/FR/ES bullet: 1-3y 1.0, 5-7y 2.0, 7-10y 3.0,
  15-30y 5.0, >30y 6.0; IT bullet: 1-3y 6.0, 7-10y 11.5, 15-30y 13.5. Effect on BTP-Bund ~47bp at 10y and 54bp at 30y (600bp excess
  funding cost). The BoE often lends more against a bullet than the strips replicating it: reconstitute strips before posting.
- **Validity rule**: swap spread = valid rich/cheap only if swap and bond curves coincide. SOFR-ASW (after adjustments) is a usable
  global RV indicator; OIS-ASW and IBOR-ASW embed the unobservable cost of capital. A EUR investor asset- and basis-swaps every bond
  into EUR fixed and fits a curve (see `../../bond-rich-cheap-fitted-curve/SKILL.md`), not spreads to EURIBOR or ESTR.
- **Cleaning SOFR-ASW**: regress on specialness, haircut financing, benchmark status; use yield minus *adjusted* CDS as risk-free yield.
  For US/Germany adjusted CDS is "at times below 10bp" so cleaning may not be worth it, except to compare 2y vs 10y.
- **USD ASW of a foreign bond** = (foreign swap spread - CCBS)/CF, CF = BPV_USD/BPV_foreign. Equilibrium USD ASW = EUR ASW/CF - CCBS/CF;
  CDS >= adjusted CDS ~ USD ASW. Handle in `../../xccy-basis/SKILL.md` and `../../spread-cross-market-govies/SKILL.md`.

## B. Balance-sheet economics (US)

**Why a negative spread is not free money** (Boyarchenko, Gupta, Steele, Yen, Negative Swap Spreads, FRBNY Economic Policy Review, Oct 2018).
Widener = buy matched-maturity Treasury financed in GC repo + pay fixed on the swap (receive float). Earn Treasury coupon + float; pay
swap fixed + repo + funding of haircut + funding of swap initial margin. Equity = SLR x (Treasury notional + haircut + IM + PFE);
Basel add-on PFE factors 0% (<=1y), 0.5% (1-5y), 1.5% (>5y).

$10mm 10y widener, 1-year carry (fall-2015 inputs): IM 3.9% = $390,000 funded at 0.5% = -$1,950; receive 3M LIBOR 0.6% = +$60,000;
repo 0.3% on $9.72mm = -$29,160; haircut 2.8% = $280,000 at 0.5% = -$1,400. Subtotal +$27,490. Spread income = -S(bp) x $1,000 per year
(S = -10bp earns $10,000): net $37,490. Equity at SLR 1..6% = $107.3k / 214.6k / 321.9k / 429.2k / 536.5k / 643.8k, so ROE 35/17/12/9/7/6%.

**Breakeven 10y swap spread (S-G, bp) for target ROE** (rows ROE, columns SLR 1/2/3/4/5/6%): breakeven S = -(ROE x Equity - 27,490)/1,000.

| ROE | 1% | 2% | 3% | 4% | 5% | 6% |
|---|---|---|---|---|---|---|
| 5% | 21 | 16 | 11 | 5 | 0 | -6 |
| 10% | 16 | 5 | -6 | -16 | -27 | -38 |
| 15% | 11 | -6 | -22 | -38 | -54 | -70 |
| 20% | 5 | -16 | -38 | -59 | -81 | -102 |
| 25% | 0 | -27 | -54 | -81 | -107 | -134 |
| 30% | -6 | -38 | -70 | -102 | -134 | -166 |

The 15%/5% cell recomputes to -53bp from the inputs above (published -54); the whole printed grid sits about 1bp more negative than the formula (e.g. 10%/3% formula -4.7 vs printed -6), so use it for ordering, not as a precise level. The equity components listed (notional, haircut, IM, PFE) do not exactly rebuild the published equity: use the published figures. Pre-regulation a 15% ROE was reachable at +11bp.
Carry depends on (float index - repo); the trade loses appeal as that narrows. TBAC version: carry ~ sum[-S + (Libor - repo)]; with
Libor-repo 15bp, 20% tax, 5% leverage ratio and RoE > 12% the spread must be below -60bp (TBAC, Charge: Swap Spreads, Feb 2021).

**SOFR-era decomposition of a 5y spread** (BofA, Taking a look at SOFR spreads, 6 Oct 2020): (1) balance sheet: required ROE 1-2% at 9%
leverage ratio = 10-20bp (about 10bp of the then 15bp 5y spread; smaller at the front, non-linear out the curve); (2) repo vs SOFR:
~1 SD of tri-party minus SOFR since Aug 2014 = ~3bp, 2-3bp of the 5y spread; (3) crisis illiquidity 1-2bp normal, more out the curve
and with implied vol (10y UST +20bp vs SOFR swaps in Mar 2020 before the Fed bought). Total 13-25bp vs then-observed ~10bp 2y, 22bp
10y, 60bp 30y (all as UST minus SOFR swap, i.e. G-S).

**Credit-adjusted convenience premium** (Fleckenstein & Longstaff, Treasury Richness, Journal of Finance, 2023): 30y OIS 4.00%, UST 4.10%
gives -10bp (S-G); with 30bp Treasury CDS the credit-adjusted yield is 3.80%, so the premium is +20bp. 2015-22 averages: 30y spread
-60.47bp vs premium -38.90bp; monthly change correlation 59%. A negative spread does not by itself mean Treasuries are cheap after credit.

**Regulation facts (US, reconcile before quoting)**: SLR = Tier 1 / total leverage exposure; min 3%, GSIB holdco 5%, insured-depository
subsidiary 6%. The 2020 temporary exclusion of Treasuries and reserves applied from 1 Apr 2020 (holdcos) and 15 May 2020 (depository
institutions) until 31 Mar 2021. Capital = max(risk-based, leverage), not the sum: relief only helps a bank for which leverage binds
(Conks, The Fed's Relief Valve Part I, 7 Mar 2025; BofA, Fed's SLR proposal: underwhelming, 25 Jun 2025). The June 2025 eSLR proposal
set the buffer to 50% of the method-1 surcharge (Citi, Short-End Notes, 27 Jun 2025). Clearing-mandate deadlines have been extended
more than once: check current status. Mechanics and GSIB scoring belong to `../../fi-balance-sheet-and-regulatory-costs/SKILL.md`.
Quarter-end: GSIB repo pull-back widens intermediation spreads; ON RRP/sponsored repo rise; size a turn off the ex-month-end base
spread (Federal Reserve Board, FEDS Notes, What Happens on Quarter-Ends in the Repo Market, 6 Jun 2025).

## C. Regression / fair-value models (as published)

| Model (source, date) | Target | Regressors (coef, t) | Fit |
|---|---|---|---|
| 30y MMS, 6M changes, 10y sample (JPM, What about Bonds?, 2 Apr 2020) | 30y MMS (S-G) | const -2.09 (-9.2); 3M GC/OIS -0.25 (-12.4); 10s30s UST curve -0.419 (-47.3); % chg WAM-weighted public debt -0.39 (-10.9); VA hedge demand ($bn 20s) -0.121 (-23.9); Fed custody ($bn) +0.050 (31.1) | R2 71%, SE ~6.4bp |
| TFP, Jun 2020-Jun 2026 (JPM, Buying back time, 19 Aug 2026) | TFP (bp per year of duration) | const -0.6; excess deposits ($tn) -0.6 (-23.3); 1Yx10Y implied vol +0.3 (15.8); Treasury WAM (months) +0.1 (6.6); net debt ex-SOMA / Fed assets +0.5 (18.6) | R2 83%, SE 0.3 |
| 30y spread, 4 factors (JPM, The long and short of it, 3 Aug 2018) | 30y MMS | 5s30s UST curve, 1y-ahead deficit expectations, VA hedging flows, WAM of marketable debt | curve beta "more than doubled" over rolling 5y |
| 10y spread (JPM, The return of convexity hedging, 31 Jan 2020) | 10y MMS | bank convexity (duration gap), 3M GC/OIS | fair value used for 3-5bp-wide call |
| 2y UST/OIS (BofA/TBAC; Citi) | 2y spread | 3M GC/OIS (dominant anchor); IG spreads; excess reserves; also 3m FF/term GC, dealer UST inventory, FX reserves | R2 39% (TBAC 2010-20); supply insignificant there |
| 2y spread FV (Citi, Short-End Notes, 21 Aug 2026) | 2y spread | FV = 3m OIS/GC + 2y SOFR/FF (bp): y = 1.0x, R2 0.81 | |
| Front-end vs private supply (Citi, All it takes is a little push, 4 Oct 2019) | 2y OIS/UST; 2y swap spread | 12m rolling private (ex-Fed) supply, coupon-only vs coupon+bill; Jan 2016-Sep 2019 | OIS/2yUST R2 0.69/0.64; 2y swap spread 0.61 coupon-only vs 0.21 with bills |
| Cross-tenor (Citi, 3 Jan 2017) | 10y spread | = 0.41 x 30y spread + 6.71 | R2 0.65 (2016-17) |
| GBP 10y gilt SS, past 12M (JPM, Global FI Markets Weekly, 21-22 Aug 2026) | 10y SS | -1.1 x 20d MA(3M GC-SONIA) + 0.5 x (1Y/1Yx1Y SONIA) - 0.18 x 10Y SONIA - 0.006 x 3Mx10Y vol + 0.0004 x BoE APF + 0.2 | R2 78%, SE 2bp |
| AUD 10y SS (same) | 10y SS | swap-curve RMSE, YM/XM curve, OIS shape, 5Y corporate credit index, USD swap spread, govt debt / private credit; semis-ACGB beta 0.6 | |
| EURUSD xccy from relative spreads (BofA, 27 Mar 2025) | 10y EUR/USD basis | 0.64 x (US vs German swap spread) + 17.79 | R2 0.82 |

Rules: (i) **implied-expectations inversion**: divide an observed spread move by a driver's coefficient to see the driver shift that would
justify it; a -0.3 TFP move would need WAM expectations ~3 months shorter, so the move was judged outsized (JPM, 19 Aug 2026). (ii) Haircut
historical WAM betas (Citi used 25%). (iii) Large residuals coincide with regime shifts (2015 Basel III, 2020 SLR exemption): refit,
do not extrapolate. (iv) Do not trade a "too steep" residual when a global driver dominates and R2 is decaying (JPM, 21-22 Aug 2026).
(v) Supply views belong in swap spreads, not curve shape: 30y spreads track the 10y-ahead deficit/GDP projection; 1% less deficit/GDP
widens spreads ~3bp (Willer & Saunders, Trading Global Macro Markets, Wiley, 2026; Citi, Learning on the job, 2 Aug 2019).

## D. Cross-section and PCA model detail

- **TFP/ZDS**: daily OLS of MMS on modified duration across 2/3/5/7/10/20/30y: spread_m = ZDS - TFP x ModDur_m. Units: TFP in bp per
  year of duration (one JPM note labels it bp/day, the companion IRD note bp/year; the regression slope is bp per unit of duration, i.e.
  per year). Sample 21 Aug 2026 (JPM): MMS (S-G) 2y -15.2, 3y -20.4, 5y -27.7, 7y -34.8, 10y -40.0, 20y -66.8, 30y -70.9; published TFP 4.4,
  ZDS -8.0. Re-running with par-bond durations at 4.2% gives TFP 3.8, ZDS -10.0 (`scripts/asw.py` `tfp_zds`): the fit is sensitive to the
  duration inputs, so use the same benchmark set and duration convention every day and compare against your own history, not a published
  level. A large one-day drop in ZDS (whole term structure shifts down) is "a telltale sign of de-leveraging" (JPM, Near, far, wherever
  yields are, 2 Oct 2026; levels there: ZDS -8.2 to -10.4, TFP 4.2).
- **Exit rule**: when the TFP residual vs model is inside one standard error (SE 0.3), go neutral and unwind spread-curve trades
  positioned for the TFP correction; keep curve trades with little TFP exposure (2s/3s, 3s/5s) (JPM, No alarms and no surprises, 5 Nov 2025).
- **PCA fair value** (BofA, A simple framework for swap spread relative value, 2 Jun 2016): per country, 2y/5y/10y/30y swap spreads,
  rolling 250d PCA (2 PCs explain "high 90s" % of variance), residual = actual - fitted (bp), z-score residual over 250d, DI = 10d moving
  average of RMS of the four z (`dislocation_index`). Residuals AR(1), half-life ~20 days. Back-test: each day buy cheapest/sell richest by
  z while DI > threshold, legs 1:1 in bp, no costs/carry/stops.

| DI threshold | US cum bp / Sharpe / days / avg hold | Germany cum bp / Sharpe / days / avg hold |
|---|---|---|
| 1.0 | 267 / 1.2 / 1750 / 32 | 869 / 2.4 / 2278 / 43 |
| 1.2 | 221 / 1.2 / 1359 / 26 | 803 / 2.5 / 1906 / 37 |
| 1.6 | 111 / 0.8 / 879 / 28 | 675 / 2.7 / 1352 / 30 |
| 2.0 | 51 / 0.4 / 676 / 38 | 554 / 2.8 / 967 / 21 |

  Readings at publication: Germany DI 1.13 (2y wide vs 10y), UK and Japan ~0.6, US ~0.3. Citi's OIS/UST version: 1y sample, residual to the
  first 2 PCs, colour by 3m z; 20 Aug 2026 residuals within +-0.5bp at every tenor (nothing to trade) (Citi, Short-End Notes, 21 Aug 2026).
- **Carry/vol hurdle (post-SLR reform)** (Barclays, Swap spreads: The Bright Spot in US rates, 30 Sep 2026): banks optimise carry per unit
  of risk; hurdle C/V = 0.25; solve the spread at which C/V falls to the hurdle; widening potential = implied - current. Table (spread /
  carry / 1y vol / C/V / implied spread / widening, bp; carry horizon as printed, not restated): 2y -14/11/10/1.15/-1/13; 3y -20/10/10/1.00/-4/17;
  5y -27/7/10/0.76/-8/20; 7y -34/6/12/0.52/-15/19; 10y -38/5/13/0.40/-23/15; 20y -63/5/19/0.26/-62/1; 30y -66/4/17/0.24/none. Read: long
  belly (7y) wideners; 30y is already at the hurdle. Assumes IORB = SOFR - 2bp.
- **Directionality beta**: rolling 3M beta of weekly (or daily) spread changes on yield changes per tenor, vs 10y median and 5th/95th
  percentiles; positive = convexity hedgers paying (JPM, Is bank convexity hedging lying in wait?, 31 May 2019; Dynamic hedgers are long,
  banks are short, 13 Sep 2019: ~+0.10 to +0.15, strongest out the curve). Older evidence: SSDir ~ -0.1 in 1998 (Golub & Tilman, 2000).
  Hedgers act only on net moves above ~20bp. MBS arithmetic: see `../../flow-mbs-convexity-hedging/SKILL.md`.
