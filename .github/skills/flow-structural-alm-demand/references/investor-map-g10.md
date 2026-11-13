# G10 structural investor map

This file backs the `flow-structural-alm-demand` skill: who the structural duration holders are in each market, what
they hold, what moves them, and the documented episodes. Every number carries its source. Where the source library is
silent, the entry says so. Treat that as unknown and ask for data. Do not assume zero.

Sign reminders: US swap spread = swap − Treasury. EGB ASW = bond − swap. Receive = long duration.

## Cross-market: natural payers and receivers

| Sector | Payers of fixed | Receivers of fixed |
|---|---|---|
| Intermediate | Banks, sovereigns | Corporates, banks |
| Long end | Banks, asset swappers, mortgage lenders | Pension funds, life insurers, sovereigns |

(Düring, Fixed Income Trading and Risk Management, 2021, Table 29.1.) Other natural payers are spread-product dealers
hedging inventory, hedgers of future issuance (rate locks, forward starters), asset swappers and gap managers with
long assets. Other natural receivers are new-issue swappers (fixed-rate issuers swapping to floating), convexity
hedgers in rallies, and gap managers with long liabilities, i.e. insurers and pensions (Stathakopoulos, The
Interaction Between Repo and Interest Rate Swaps, ICMA workshop, 27 Sep 2021).

US swap positions by sector (CFTC data, Sep 2020; Tuckman & Serrat, Fixed Income Securities, 2022, Table 13.1): pensions
and insurers are likely net long (receive fixed) to hedge long liabilities. Banks are net short. Non-financials pay
fixed to convert floating loans and pre-hedge issuance. The printed "Net" column has an inconsistent sign, so rely on
the text, not the column.

Market structure (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022): the 15y–30y+ section is
"pension funds, longer-term government and corporate funding". It is more stable because long-horizon holders damp
panics and bubbles and only significant events move it. Supply/demand from rules such as the European UFR "can
dominate local markets".

## USD

**Corporate DB pensions.** Liabilities are discounted on an AA corporate curve. Plans follow a glide path from equities
into fixed income as funded ratios rise.
- Funded-ratio mechanics and nowcast: see SKILL.md example A (J.P. Morgan, Issuance, pensions, and long-end spreads,
  14 Sep 2018).
- Instrument choice has shifted from swaps and swaption risk reversals to Treasuries, STRIPS, TRS, reverse THORS and
  OTC bond options. Long-end spread volatility drove the switch. Pension return attribution (monthly plan returns on
  Δ30y UST, Δ30y swap spread, Δlong corporate spread and equity returns, 3y rolling) showed swap-spread exposure falling
  while rate beta held (J.P. Morgan, Pension re-risking and long-end swap spreads, 3 Apr 2020).
- About three-quarters of private-pension fixed income (> ~$500bn) sat in plans with above-median FI allocation as of
  FY18. Re-risking or profit-taking on rate hedges is "effectively secondary market supply of Treasury duration, and
  bearish for long end spreads" (same note).
- Private DB FI allocation rose from 20% to 33–37% over two decades. Funded status rises with rates. A 10y rally of
  ≥ 50bp pushes funded status below 100% (BofA, Basics of UST supply & demand, 24 Jun 2024; BofA, UST supply & demand
  in '25, 26 Nov 2024; BofA, Long UST outflows & dealer holding highs, 10 Mar 2025, with ±25/50/75/100bp grids).
- 2026 state: funded ratio ~115%. Buying steps came at May 2025, May 2026 and ~+3pp later. Equity allocation is ~24%
  (32% at end-2020) against a ~20% terminal, which leaves ~$30–50bn of large-plan UST demand on ~$1.5–2tn of glide-path
  assets. Pension demand was expected back at 5.3–5.5% 30y yields but STRIPS demand stayed weak in Sep 2026, so the
  next trigger is 5.75–6%. Risk: pensions buy long IG (AI-related issuance) instead of USTs (Citi, US Rates Weekly:
  Pension plan for 20s?, 9 Oct 2026). The authors expected 20s/30s auction cuts and positioned in 10s20s spread
  steepeners.
- Rebalancing after the Q4-2018 14% S&P fall drove 30y spreads to −20bp. Worse funded ratios meant pensions would come
  back to buying later. Pension, corporate-supply and stop-out moves in 30y spreads are temporary (Citi, US Rates
  Weekly: The rocky road to a steeper curve, 18 Jan 2019).

**Insurers and variable annuities.**
- VA duration extends when equities fall and/or rates decline, so writers "are forced to receive eventually" (J.P.
  Morgan, 3 Apr 2020). They delivered >$150bn 10y-eq in ~1 month at the March 2020 peak, more than 2× summer 2011
  (J.P. Morgan, What about Bonds?, 2 Apr 2020). VA duration contracted $23bn in one week in Feb 2020 (J.P. Morgan,
  Markets struggle to feed the convexity beast, 28 Feb 2020).
- VA hedgers pay fixed when yields rise and/or risk assets outperform. A rolling 2y regression of VA liability duration
  on 30y yields and equity returns showed rising equity sensitivity and falling rate sensitivity in 2018 (J.P. Morgan,
  14 Sep 2018).
- The VA receiving point is ~20y. Stocks vs the 15y5y/20y10y curve correlation is ~ −23%, but the monthly P&L of a
  delta-hedged flattener is ~uncorrelated with equities because vol rises in that scenario (Citi, US Rates Vol Lab:
  Trading long-dated convexity, 9 May 2019).
- Life insurers hedge long-dated with swaps or bond forwards (hedge accounting) and use futures for short-dated or
  dynamic VA hedges. Under RBC, repo carries a capital charge (CFTC MRAC, The Treasury Cash-Futures Basis Trade, Dec
  2024). 5y20y is a common insurer swaption expression in Schedule DB filings, i.e. buy-and-hold structural demand
  (Morgan Stanley, Investors Are Paying for Protection Against 6% Rates, 2 Jul 2026).
- Taiwanese and Korean lifers buy long-dated USD callables (Formosa). Issuers swap them, which creates long-end
  receiving and vega supply. See `vol-structured-flows-and-vega-supply`.

**Banks.**
- When rates fall, deposits extend and MBS/loan duration contracts. That delivered up to ~$1.5tn of 10y-eq short
  duration (2019–Mar 2020), roughly half each from deposits and mortgage assets. Revolver draws (> $200bn) add
  floating assets. Banks covered less than half and were expected to receive swaps, "a very bearish setup for
  intermediate swap spreads" (J.P. Morgan, Will mortgages bail banks out of their duration short?, 27 Mar 2020). Bank
  duration contracted ~$161bn in one month and $396bn YTD in Feb 2020 (J.P. Morgan, 28 Feb 2020).
- Counter-evidence: bank swap books are mostly market-making and customer facilitation, and banks hedge mainly through
  the deposit franchise (CFTC OCE, Do Banks Hedge Using Interest Rate Swaps?, 2023). Treat the duration-gap estimates as
  an upper bound.
- Securities growth needs deposit growth and tracks the 3m5y slope. Liquidity rules favour cash, short USTs and CMO
  floaters (BofA, 24 Jun 2024).

**Other.**
- UST holders that largely cannot switch to swaps: foreign official, the Fed, insurers, banks and MMFs. Net swap
  receivers: banks, insurers, pensions, VA hedgers and MBS servicers. GSE portfolio shrinkage and Fed MBS QE removed the
  historic mortgage payers, so net receive demand pushes spreads down until toggling investors (hedge funds, banks,
  dealers) take the other side (TBAC, Charge: Swap Spreads, Feb 2021).
- Post-2015 narrowing drivers: reserve managers selling USTs, more swapping of fixed-rate debt, insurers and pensions
  receiving. Constraints do not cause the dislocation but prolong it (Boyarchenko, Gupta, Steele, Yen, Negative Swap
  Spreads, FRBNY Economic Policy Review, Oct 2018).
- A new long-bond (ultra) contract gave LDI a futures substitute for 30y swaps. In 2009 it was expected to stop 30y
  spreads trading as negative as −40bp (late 2008) (Credit Suisse, US Treasuries Futures Focus: New Ultra Long
  Contract, 28 Sep 2009).
- Long SOFR/FF basis stays a few bp wider than overnight fundamentals because of LDI receive-SOFR demand for
  "off-balance sheet long-end duration" (BofA, SOFR/FF term structure post "big bang", 22 Oct 2020).

## EUR

**Dutch pensions.**
- Market-rate discounting with a UFR. The Dutch UFR was 4.2% in 2012, later 3.9%. Funds must buy duration when yields
  fall, a regulatory short-convexity (Düring, 2021).
- 2012 FTK II/DNB discount-curve reforms (market rates beyond 20y) caused diverging 15y5y vs 25y5y PCA residuals:
  structural, not an inefficiency (Credit Suisse, PCA Unleashed, 24 Oct 2012).
- The move to defined contribution (2023–27 at the time of writing) shifts hedging structurally (BNP Paribas, EUR curve
  convexity: Lessons from history, 25 May 2021). Transition size ~€400mn DV01 to pay over ~2 years. Hedge funds held
  ~€100mn DV01 of 10s30s steepeners in advance (JWS Macro, Duration Is Diseased, 4 Sep 2025). Steepeners were "only
  where flows predictable (EUR, Dutch PF 2026/27)" (same author).
- Funds received into prior year-ends to protect coverage ratios. DNB Q2-2025 coverage ratios were high, which limited
  that risk. Hedge ratios were also high, so "a lot of unwinding" was still due for the 1 Jan cohort (Nordea, EUR rates:
  How about that outright receiving, 26 Sep 2025).
- Watch the Eurex–LCH basis for Dutch/German receiving interest. In Feb 2020 the 30y was positive (no receiving) and the
  50y slightly negative (Nordea, EUR Rates Flash, 5 Feb 2020). At Eurex, buy-side funds and insurers paying fixed to
  hedge bonds drive the sign of the basis (Boudiaf, Kretschmann, Scheicher, SUERF Policy Brief 940, Jul 2024).

**EEA insurers (Solvency II).** Formulas are in `regulatory-discount-curves.md`.
- From 30 Jan 2027: FSP 20y for EUR (unchanged), LLFR/UFR extrapolation, α phase-in 0.20 → 0.11 by 2032, VA reform
  favouring bonds, lower risk margin. Long-end EGB ASW has been deeply positive (bonds cheap to swaps) since Q4 2024. The
  reform reinforces the preference for bonds only gradually (Citi, A QT revolution, 17 Sep 2026).
- Room by country: French, Italian and Spanish insurers are already heavily domestic. German and, to a lesser extent,
  Belgian and Dutch insurers have room. The risk margin is ~2.5% of technical provisions on the EMU-11 average
  (Austria 4.9%; Portugal and Italy 1.4%) (same note).
- An Italian lifer with BTP-heavy holdings gains VA through the CSSR, the quality-overshooting adjustment and the Macro
  VA, so govvies, including BTPs, become "considerably more palatable than swaps" (Citi, What to do about OATs?, 1 Oct
  2026).
- Pre-reform risk: life insurers may add duration in response to the Solvency II review (higher capital charges on
  duration gaps). A big 30y rally would reverse the Q1-2021 duration-gap narrowing and could cause "a scramble for
  hedges" (BNP Paribas, 25 May 2021).

**Episodes and curve facts.**
- June 2008: structured-note curve options, pensions and insurers receiving long rates for ALM, and short-convexity
  exotics dealers pushed EUR 30y below 10y. EUR 10y-forward 30y nearly touched 2.0%, below JGB 30y. It reverted once
  positions were squared (Bassman, Forwards are NOT a Prediction, 12 Aug 2013).
- Under stress, pension assets fall while liabilities rise. Funds receive 20–30y, the swap curve flattens sharply and
  30y Bunds underperform 10y. The EUR 10–30 swap-spread curve dived in March 2020 and had recovered ~75% by Dec 2020
  (Quantitative Finance Stack Exchange, Downward Sloping Swap Spread Curve, Dec 2020).
- A paid 20y belly is exposed to ALM receiving at the 20y point in an equity meltdown (Nordea, EUR Rates Flash, 23 May
  2019). The EUR 30/50y slope moves against 1y30y vol, consistent with ALM receiving ultra-long for convexity (Nordea,
  5 Feb 2020).
- Offsets: NGEU paying flows from EU maturity transformation (BNP Paribas, 25 May 2021). EGB/SSA supply WAM is falling
  (Citi, 17 Sep 2026).
- Banks with sticky deposits buy FRNs. Italian CCTs are largely bank-held (Düring, 2021). Danish pensions moved to
  market-rate discounting (Düring, 2021).

## GBP
- The long end is driven mainly by pension funds: "any change in asset allocation by pension funds... tends to have a
  large impact on the UK curve" (Düring, 2021). The UK swap-spread curve slopes down from ~5y (QF Stack Exchange, Dec
  2020).
- GBP 20y richening comes from ALM/pension risk transfer, lower longevity assumptions and pension receiving. It shows
  in the 10s20s30s fly and a steep 15y10y/25y10y. See SKILL.md example C (Citi, Buying vol for less, 25 Sep 2019; Citi,
  US Rates Weekly: Fixing the plumbing, 30 Sep 2019; Citi, In search of cheap vol, 17 Jan 2020).
- Ultra-long: LDI hedging is pro-cyclical and spirals into reverse if yields rise. GBP ultra-long swaps steepened in
  mid-2019 and 30s50s turned upward-sloping (QF Stack Exchange, Why does the ultra long-end of a yield curve invert?,
  2019). A GBP 30y10y–40y10y steepener was among PCA trades in 2012 (Credit Suisse, PCA Unleashed, 24 Oct 2012).
- BPA/buy-out: insurers sell long gilts and linkers, buy USD credit (too little GBP IG) and hedge with long-dated xccy.
  That widens 30y SONIA/SOFR and flattens the basis 10s30s curve (the source's 10s30s is the xccy basis curve, not
  gilts); the 30y widened significantly in 1H23. Long gilts offered ~+70bp
  over SONIA at 30y. Pension "run-on" is reducing buy-outs, so 30y is unlikely to widen much, but BPA keeps the basis
  10s30s flat
  (J.P. Morgan, Cross currency basis 4Q24 Outlook, 26 Sep 2024).
- Sep 2022 LDI: forced selling by levered LDI funds on margin calls, "misunderstood pockets of leverage", more than the
  fiscal news. The BoE bought up to £65bn (28 Sep–14 Oct) (Willer & Saunders, Trading Global Macro Markets, 2026).
  UK insurers and pension funds held ~£277bn of non-UK long-term bonds in Q2 2023, down on LDI collateral calls (BofA,
  FX-SOFR primer, 31 Oct 2023).
- Post-LDI pensions prefer credit over duration: ~£400bn (~£500mn DV01) of structural demand lost, mostly in swaps.
  Linker demand is also down. The author ties the considerable fall in the UK breakeven over the prior 18 months to
  LDI linker demand (JWS Macro, 4 Sep 2025).
  Structural domestic buyers retreating means a larger, more price-sensitive foreign share (Financial Times, Unhedged:
  Who owns government bonds?, Aug 2026).

## JPY
- Life insurers buy long bonds whenever yields exceed their guarantee target, which caps yields. The 10y-vs-30y JGB
  pivot was ~0.75% / ~2% in 2010–15 and creates "linear trading strategies that have an option-like non-linear pay-out"
  near the pivot. BoJ QE changed the dynamics after 2016. The 10y JGB "has no natural investor base, being too long for
  banks and too short for life insurers" (Düring, 2021).
- Seasonality: lifers buy super-longs in Jan–Mar (ALM duration gap, the 2025 economic-value solvency regime, spending
  cash before fiscal year-end) while banks sell to realise profits. 5s30s and 10s30s narrowed in March in 8 of the
  past 10 years (BofA, Bond market seasonality explained, 6 Jun 2022).
- Ownership at end-Dec 2022, ex bills: BoJ 52%, insurance 19%, depository corporations 11%, others 9%, overseas 6%,
  pensions 3% (BofA, Japan Rates Basics, 24 Apr 2023).
- 2026 state: lifers' JGBs fell ¥8.6tn in FY25 (10y+ −¥7.3tn). ESR 215%; +50bp in JPY rates costs about −8pt of ESR.
  Bank IRRBB capacity to add risk up to dEVE thresholds is ~¥90.6tn 10y-eq (major banks ¥52.1tn), realistically less
  than half usable. Market-held JGB supply next year is +¥65tn, concentrated < 10y (J.P. Morgan, Global Fixed Income
  Markets Weekly, Aug 2026).
- Lifers are the expected buyers on heavy selling but give "little resilience" to a rapid rise. Pensions need equity
  gains to buy JGBs (Nikkei > 70,000) (Citi, Japan Rates Weekly: 2% priced in, 14 Aug 2026). Public pensions
  rebalance into JGBs after JGBs underperform other assets (Barclays, Global Rates Weekly: The urgency question, 2 Oct
  2026).
- Some domestic banks were the main super-long buyers in early 2025, partly on ASW. Banks are not natural super-long
  holders, so flatteners may be crowded (J.P. Morgan, Japan Fixed Income Markets Weekly, 21 Feb 2025).
- Foreign alternatives: hedged USD A-and-better 10–20y at 3.15% sat below the 4.03% JGB 30y for lifers in Aug 2026, a
  negative for the foreign bid and a positive for domestic super-longs (Citi, The High-Grade Beat, 19 Aug 2026).
  Lifers cut hedged foreign bonds in 2022 and are waiting for BoJ normalisation to buy super-longs (BofA, FX-SOFR
  primer, 31 Oct 2023).

## AUD
- The super system is ~A$4tn, overweight US equities, with a low FX hedge ratio. Funds receive in long xccy tenors with
  only sporadic pay-side offsets, so the BBSW–SOFR basis is deeply inverted at 20y×5y and beyond (~ −55bp). Offshore
  10y+ issuance by state governments (semis) adds pay-side flow and steepens the basis curve. Higher hedge ratios mean
  sub-1y receive-side FX-OIS (J.P. Morgan, Cross currency basis 2H25 Outlook, 5 Jun 2025).

## CAD, NZD, CHF, SEK, NOK
The source library has no ALM-demand material for these markets. Known regime facts (external): Sweden and Norway apply
Solvency II as EU/EEA members, and SEK has its own extrapolation parameters ("all currencies ex SEK" in Citi, 1 Oct
2026). Switzerland uses the Swiss Solvency Test. Canadian insurers report under OSFI's capital framework. Before using
structural demand in these markets, ask for: the regulator's liability discount-curve rule (last liquid point,
extrapolation), pension and insurer holdings by tenor, hedge ratios, and a long-end flow indicator (CCP basis, SDR
prints).

## Reserve managers (cross-market)
- Prefer short-dated, highly rated USD/EUR/JPY. Purchases at market weight hit captive-holder assets hardest (Düring,
  2021).
- Front-end UST vs OIS follows foreign official demand. Custody holdings rise as the dollar weakens (USD index inverted) (BofA,
  Trade idea: sell 2y spreads, 27 Sep 2017; BofA, 24 Jun 2024). Falling custody holdings may hide offshore custodians
  and rotation into agencies or gold rather than USD exit (Conks, Money Market Update, 15 Sep 2025).
- FX-hedged or asset-swapped buying of JGBs and T-bills via xccy, mostly ≤ 2y (J.P. Morgan, Drivers of cross currency
  basis, 11 Mar 2015). A reserve manager can hedge govvie holdings with IRS instead of selling (Darbyshire, 2022).
- Their long-end footprint is small. Use them for front-end spreads (`stir-bills-and-money-market-spreads`) and the xccy
  basis.

## Bank ALM product flows (cross-market)
Banks pay fixed against fixed-rate mortgages and fixed-APR cards. They receive fixed to hedge current-account
deposits along an actuarial runoff profile, and against fixed-rate savings products. Pension and annuity providers
receive long-dated (Darbyshire, 2022). By CCP: at CME, US banks hedging fixed-rate mortgages give a pay-fixed
preference. At JSCC before 2018, domestic banks received to hedge loan books (SUERF Policy Brief 940, Jul 2024).
