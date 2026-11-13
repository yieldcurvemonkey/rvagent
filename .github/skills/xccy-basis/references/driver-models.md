# Cross-currency basis: empirical drivers and fair-value models

Companion to [SKILL.md](../SKILL.md). Every coefficient below is a published, dated, in-sample estimate. Use them
as a map of which variables matter and with what sign and order of magnitude, not as parameters. Re-estimate on
your own data (post-2021 for USD, post-RFR transition for the leg definitions) and check sign stability on a
rolling window before trusting any of them. Sign: basis in bp on the non-USD leg vs USD flat, negative = USD premium.

## 1. Cross-section: net foreign assets (NFA) set the level
- Daily cross-section regression (2012 on) of the 3M basis on the latest banking-sector NFA: about -4 +/- 1bp of
  3M basis per +$100bn NFA. Beta (mean, median, sd) -0.04, -0.04, 0.01 bp per $bn; constant -11.6, -9.55, 11.7;
  R2 30% (28% median). (JPM, FX basis note, 20 Feb 2020)
- Mean residual to the cross-section (bp; positive = basis higher/less negative than NFA implies; % of days
  positive): AUD +14.5 (96%), CAD +29.3 (100%), EUR +9.7 (99%), GBP +5.3 (73%), SEK -12.7 (12%), JPY -9.9 (17%),
  CHF -36.3 (0%). Read: AUD and CAD sit persistently high to NFA, JPY, CHF and SEK low. Use residuals relative to
  each currency's own mean, not the sign. (same source)
- 2Y basis vs 2018 NFA across DM (AU, EA, CH, UK, JP, NO, SE, HK, DK): NFA($bn) = -15.7 x basis(bp) - 12.1,
  R2 0.52. NFA is the dependent variable: do not invert it to forecast the basis (that slope is about R2 / -15.7 =
  -0.033bp per $bn, consistent with the -0.04 above). A small negative basis most of the time means the system is flush
  and offshore entities fund in the currency and swap. (JPM, HKD/USD basis, 18 Sep 2019)
- Mechanism: net foreign asset holders (JPY, EUR, CHF) hedge asset-side USD exposure, which sets a negative basis;
  net foreign liability economies hedge back home.

## 2. Time-series FV per currency (JPM, 20 Feb 2020)
Daily from Jun 2012. Dependent: rolling 1Y FX/OIS basis (bp). Regressors: FRA/OIS (USD, bp), leveraged-fund
positioning ('000s, CFTC), asset-manager positioning, NFA ($bn). Coefficients (t-stat):

| ccy | const | FRA/OIS | lev. funds | asset mgr | NFA | R2 | last resid |
|---|---|---|---|---|---|---|---|
| GBP | 0.06 (0.1) | -0.48 (-19.4) | -0.08 (-7.8) | 0.01 (0.6) | -0.02 (-15.9) | 48% | 7.6 |
| EUR | 35.76 (11.9) | -0.84 (-22.3) | 0.22 (15.1) | -0.09 (-3.9) | -0.06 (-17.7) | 55% | 15.6 |
| JPY | 2.86 (1.4) | -0.86 (-15.5) | 0.08 (3.0) | 0.26 (5.5) | -0.06 (-20.6) | 50% | 18.3 |
| CHF | 14.61 (13.2) | 0.01 (0.3) | -0.06 (-4.8) | -0.56 (-24.1) | -0.04 (-8.1) | 39% | 3.3 |
| CAD | 22.05 (39.9) | -0.46 (-28.9) | -0.03 (-3.4) | 0.10 (7.7) | -0.01 (-3.2) | 36% | -6.7 |
| AUD | none | 0.09 (2.9) | -0.28 (-22.6) | 0.16 (6.9) | -0.04 (-15.9) | 76% | 7.4 |

The AUD constant is suppressed (structurally wide to NFA). Reading: after NFA, USD domestic funding stress
(FRA/OIS) is the most pervasive driver for the funding currencies; AUD follows its own conditions. Positive residual
= basis high (USD premium priced out too far). The average residual across currencies versus 3M GC/OIS is a
funding-RV gauge. (JPM, same note) Light volume weakens every read: January 2020 trade-repository xccy (<1y, USD leg) volume was
57% / 24% of the 2019 / 2018 levels.

## 3. EUR/USD
- **Relative swap spreads.** 10y EUR basis (bp) = 0.64 x (10y US swap spread minus 10y German swap spread, bp)
  + 17.79, R2 0.82. Relative swap spreads explain 80-90% of recent levels at 2y/5y/10y, about 4.5-7.0bp of basis per
  10bp of relative spread. Mechanism: tighter German vs US swap spreads (i) make USD issuance swapped into EUR
  preferable for issuers and (ii) raise the FX-hedged pickup in German assets; both lift demand to borrow EUR through
  the basis, which tightens it. "Room" = beta x year-to-date change in relative spread minus the actual basis change:
  27 Mar 2025, the 10y German spread was about 15bp tighter vs US YTD, implying about 10bp of tightening; the basis
  had widened 1bp, leaving about 11bp of room at 10y, about 8bp at 5y, little at 2y. (BofA, European Rates Watch,
  27 Mar 2025). Forecast mapping, Jun 2025: US-Germany swap spreads 2y -14 to -10, 10y -39 to -29 imply EUR
  about 2bp tighter at 2y and about 5bp tighter at 10y; the US-Japan swap-spread link to JPY is weak, so map EUR
  first and JPY through the strong EUR-JPY 10y basis relation. (BofA, FX-Sofr and xccy: tightening themes, 3 Jun 2025)
  The mapping assumes asset-swap valuations stay fixed; the front end should be judged on reserves/QT instead.
- **2y decomposition.** basis = (USD swap-spread term) + (EUR swap-spread term) + residual, where the terms are
  [(EUR OIS - German yield) - (USD OIS - UST)] built on constant-maturity fitted yields. No-arbitrage would give
  slope 1 and intercept 0; actual slope 0.53, intercept 0.75, R2 0.82 (since Oct 2024). Attribution of a 7bp 2y
  tightening: 10.7bp from EUR spread cheapening, offset by 0.3bp from the USD term and 3.5bp from the residual (10.7 - 0.3
  - 3.5 = 6.9; signs as read from the source text). The EUR leg drives co-movement. 3M changes
  of the basis on 3M changes of the residual: 2y R2 0.27, 10y 0.07, 2s10s 0.01. (Citi, FX Basis Quarterly, 13 Dec 2024)
- **Front end, balance sheets (Libor era).** Each 1% of GDP of relative ECB-vs-Fed balance-sheet growth widens the
  2Y basis about 2bp; the same note's futures-spread (Eurodollar-Euribor) term appears with opposite signs in two
  published versions, so quote only the balance-sheet rule. Policy divergence and balance sheets drive the curve to
  2-3Y; cross-border issuance drives beyond. (JPM, Stretched EUR/USD valuations, 27 Mar 2015; JPM, Drivers of
  cross currency basis, 11 Mar 2015)
- **Issuance.** Yankee (EUR issuer in USD, swapped to EUR: lends USD, borrows EUR) narrows; reverse-Yankee (US issuer
  in EUR: lends EUR, borrows USD) widens. 5Yx5Y: about 7bp wider per EUR1bn/day of reverse-Yankee, about 5bp narrower
  per EUR1bn/day of Yankee (2015 fit, R2 71%). Since Jan 2023 the 1Yx1Y/5Yx5Y curve = -0.23 x (1Yx1Y) - 1.15 x (1M
  MA Yankee issuance) - 8.27, R2 57%; Yankee significant, reverse-Yankee not. (JPM, 11 Mar 2015; JPM, Cross currency
  basis 4Q24 Outlook, 26 Sep 2024)
- **Issuer cost matrix.** Adjusted USD-EUR cost = unadjusted credit-spread gap + xccy basis + 3s/6s basis, by
  maturity and rating. Jun 2025: unadjusted 7/14/21/27bp for 0-3/3-6/6-10/10y+, xccy about -5, adjusted
  3/9/16/23: EUR cheaper everywhere, supporting reverse-Yankee (wider basis). (JPM, 2H25 Outlook, 5 Jun 2025)
  Split by rating and bucket: broad-index metrics mislead (2015 AA favoured USD, BBB EUR).
- **1Yx1Y ESTR/SOFR short-term FV** (6M window): regressors 1Yx1Y ESTR/SOFR yield differential, 10y OAT/Bund,
  3M change in US bill issuance; R2 48%. 10bp relative SOFR underperformance widens the basis about 0.6bp; 10bp wider
  OAT/Bund about 0.8bp. The sign of the policy-differential beta flipped between 2024 and 2025. (JPM, 4Q24, 2H25)
- **Bank-CDS link broke.** 2Y basis = -0.16 x EA-bank CDS + 10.9 (R2 83%, 2011 on); the beta to peripheral spreads
  went from about -20% to +30% from April 2014. (JPM, 11 Mar 2015)

## 4. Cross-currency PCA and PC1 FV (JPM, 2H25 and 4Q24 Outlooks)
- PCA of the 1Y and 5Y bases for EUR, GBP, JPY, AUD (RFR era, since Jan 2024): 1Y PC1 72%, PC2 15%, PC3 10%; 5Y PC1
  93%. The front end is domestically driven; the back end shares a common USD factor. 1Y loadings: PC1 common (EUR 0.6,
  GBP 0.47, JPY 0.6, AUD 0.28); PC2 policy (JPY +0.8; EUR -0.45, GBP -0.2, AUD -0.33); PC3 idiosyncratic (AUD +0.9).
  An earlier 1Y PCA since 2013 reads PC1 as broad USD scarcity (relative policy + risk aversion).
- PC1 of the 1Y basis (5y window) = 0.15 x USD money-market slope - 0.041 x average non-USD MM slope - 0.044 x VIX
  + 1.25 x trade-weighted USD - 132.9, R2 73%. A longer window (since 2017) gives opposite signs on slopes and a
  rates-vol term (R2 73%): the basis is less negative with a flatter USD MM curve, steeper non-USD curves, higher
  equities and lower DM rates vol. Coefficient signs differ by window: treat only as broadly fair/cheap.
- Curve beta: 5Y PC1 = 0.02x^2 + 0.47x - 4.33 on 1Y PC1 (since 2023), R2 95%. Beta below 1: the basis curve
  steepens in widenings and flattens in narrowings; hedge curve trades for front-end beta.

## 5. JPY
- Libor-era (2015): 1Y = f(Fed reserves +0.31bp per $10bn, BoJ current-account reserves -0.25bp per JPY1tn) R2 61%;
  5Y = 0.70 x 1Y - 0.14 x megabank USD CDS - 3.86 x USDJPY 2Y implied vol + 12.6, R2 91%; 1s5s vs 5Y R2 0.46.
- Quarter-end widening comes from the USD side. Samurai/euroyen issuance (peak May-Jul) widens; foreign JGB buying on
  xccy-ASW pickup tightens the intermediate basis; Japanese-investor hedge buying via 10Y+ swaps widens, structured-note
  prepayment tightens. PC1 of the JPY CCBS curve vs 5Y JPY swap realised vol: R2 0.86 (2010-12, weekly): the curve is a
  risk-aversion gauge. (Huggins & Schaller, FIRVA, 2024; JPM, 2H25 Outlook)
- 3m JGB $ASW decomposition: 3m JGB$ASW minus 3m bill = (3m CP - 3m bill) + regulatory/liquidity cost + year-end
  turn (+15bp Oct-Dec). Jun 2025: 9.5 + 9.2 = 18.7 model vs 17.9 actual: fair. (JPM, 2H25 Outlook)
- 3M T-bill ASW (JPY) regressed on 3M USD/JPY basis, monthly T-bill net issuance and 3M GC/OIS: residual about -4bp
  (rich), Feb 2025. A sharp back-end basis tightening can trigger JGB xccy-ASW unwinds that spill into swap spreads.
  (JPM, Japan Weekly, 21 Feb 2025)

## 6. GBP, CHF, AUD
- GBP: 1Yx1Y SONIA/SOFR = -0.1 x BoE reserves (GBP bn) + 71.5, R2 84% (weekly since Oct 2022): GBP10bn fewer reserves
  about +0.9bp. Relative policy not a driver (R2 21% then 0%). Beta to 1Yx1Y EUR 0.41-0.48 (R2 74% then 46%). BoE
  reserve floor caps balance-sheet-driven narrowing. BPA buy-outs (insurers sell gilts, buy USD credit, hedge with long
  xccy) widen the 30Y. (JPM, 2H25 and 4Q24 Outlooks)
- CHF (2015): 1Y CHF vs 1Y EUR beta 1.00 (R2 90%) until the SNB peg change, then 1.86 (R2 74%); driven by SNB sight
  deposits more than front-end yields. (JPM, 11 Mar 2015)
- AUD: positive basis, wide to NFA (section 1). Banks issue about USD 100bn of term funding a year (3-5y) and pay 6m-1y
  basis for money-market issuance. Offshore-funding FV: AUD cost = USD 3M CP - USD 3M OIS + AUD/USD FX-OIS vs AUD 3m
  FRA-OIS. Kangaroo issuance narrows, bank offshore issuance widens; 10Y AUD/USD vs AUD/JPY beta 0.89 (R2 0.68, 2015).
  AUD/NZD quote against term bank bills, so basis comparisons with overnight-RFR currencies need adjustment.

## 7. USD-side liquidity regime (all pairs)
- Reserves differential: if reserves are larger in market A than B, the incentive to raise funding in A weakens and
  the basis moves against A. The 2008-11 widening was a USD liquidity shortage. (JPM, 11 Mar 2015)
- QT divergence: Fed QT slowed/ended while ECB/BoJ continue makes EUR/JPY reserves scarcer than USD, a sustained
  tightening pressure on the front of the EUR basis (BofA, 3 Jun 2025). With RRP depleted a TGA rebuild widens the basis;
  in 2023 it narrowed because RRP fell one for one. T-bill/RRP crowding-out links bills to the basis only when RRP is
  not draining. (JPM, 2H25 and 4Q24 Outlooks) Mechanics belong to
  [stir-central-bank-balance-sheet-and-reserves](../../stir-central-bank-balance-sheet-and-reserves/SKILL.md).
- Structural long-basis checklist (Aug 2026, Citi): no catalyst for the Fed to leave ample reserves; balance-sheet
  shrinkage needs lower bank reserve demand first; basis less hit by bill supply than SOFR/FF; any cut in SOMA WAM
  helps; LCR reform frees $200-600bn of reserve demand; possible central clearing of standing repo; a debt-ceiling
  episode brings RRP back. Conclusion quoted: minimal risks to the basis into 2027. (Citi, STIRT Weekly, 7 Aug 2026)

## 8. Credit/term-premium decomposition (Libor era, still the right way to read legs)
Observed Libor xccy basis = default-free overnight xccy basis + (USD Libor vs USD overnight basis) + (foreign Libor vs
foreign overnight basis). The spread reflects the difference in local term-credit spreads: more credit-risky foreign
Libor gives a negative basis (GBP 2003: GBP 1M Libor +2bp vs USD +0.75bp gave about -1.5bp; CAD CDOR keyed off
bankers' acceptances gave a positive basis of 8-10bp). (Lehman, Interest Rate Parity, Money Market Basis Swaps and
Cross-Currency Basis Swaps, Jun 2003) After the RFR transition a CCBS exchanges an unsecured foreign rate for secured
SOFR (or secured for secured), so the secured-unsecured basis enters once or twice; SOFR vs foreign term rate is more
negative than SOFR vs foreign overnight rate (illustrative: -28 vs -20bp). (Huggins & Schaller, FIRVA, 2024)

## 9. Futures-spread proxy for CCBS moves
Regression of the USD secured-unsecured futures spread (3M SOFR futures minus Eurodollar futures, bp) on the 2Y JPY CCBS
and SOFR, weekly: spread = 4.825 + 2.322 x SOFR(%) - 0.394 x 2Y JPY CCBS, R2 0.67 (spread in bp, SOFR in %, CCBS in bp); single regression -0.5067 x CCBS + 3.77, R2 0.51.
OU fit on the residual: half-life 2.6-3.7 weeks, mean reversion speed 0.19-0.27/week. Use only to trade CCBS moves
cheaply (no principal exchange); not valid where the actual FX cash flows matter (a hedged bond purchase), and the
residual is rarely large enough to trade net of CCBS costs. After the LIBOR cessation use SOFR-FF futures spreads and
re-estimate on post-Aug-2021 data. (Huggins & Schaller, SOFR Futures and Options, 2022)
