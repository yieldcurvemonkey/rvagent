---
name: vol-structured-flows-and-vega-supply
description: 'Turns long-dated callable and structured-note issuance into bucketed vega supply and dealer hedge vectors, then tests whether the swaption surface and long-end curve already price it. Covers Formosa / Taiwan-lifer callable zero-coupon accreters (30NC1, 30NC5, 40NC5), cancellable swaps and Bermudan-vs-European (B/E) hedging, swapped-vs-unswapped issuer rules, empirical call and redemption haircuts, 10y10y straddle equivalents, dVega/dRate rebalancing, and structured notes (CMS spread range accruals, inversion notes, CMS caps, PRDC, Uridashi). Use when asked why bottom-right or long-expiry swaption vol (10y10y, 10y20y, 20y10y, 5y30y, 2y30y) is cheap or rich, how much vega callable supply delivers and where, what a lockout or regulatory change does to the vol surface, what dealers must trade after a big rally or selloff, or why 30y swap spreads, 10s30s and 30s50s flatten on issuance-related receiving. Also vega supply, callable supply. Pension and insurer duration demand: flow-structural-alm-demand.'
---

# Structured flows and vega supply

When investors buy long-dated callables or structured notes, they sell an embedded option to earn a higher coupon.
Once the issuer swaps the bond, the option sits on dealer books. For callables the dealer is long a Bermudan
receiver. For range accruals the dealer is long digital or spread options. Dealers hedge by selling liquid European
swaptions and by trading the curve. The result is price-insensitive vega supply in specific expiry × tail buckets
(USD: 5y-20y expiries into 10y-30y tails), receive-fixed flow at the long end, and rebalancing flows that depend on
the rate path (dVega/dRate, Greeks flipping at a strike).

This skill sizes that supply, maps it to hedge points and checks whether the surface already prices it. It pays in
two cases:
- Supply shifts before the surface adjusts: a lockout rule, a migration from 30NC5 to 40NC5, a seasonal lull or a
  redemption wave.
- A forced unwind overshoots: a strike cross, or a 50bp+ rally or selloff.

## When to use
- "Why is USD 10y10y / 10y20y / bottom-right vol so cheap? Is it cheap for a reason?"
- "How much vega did callable (Formosa) issuance supply this month or quarter, and in which buckets?"
- "Taiwan changed the minimum lockout or the cap. What happens to 2y30y vs 2y10y and to 10y expiries?"
- "Redemptions are coming. How much gets reinvested, and when?"
- "What do Bermudan books do in a 50bp rally or selloff?"
- A structured-note wave (CMS range accruals, inversion notes, CMS caps) is near its strike and someone asks
  whether hedgers will be forced to trade.
- Long-end flattening blamed on "issuance-related receiving": 30y swap spreads, 10s30s, 30s50s, or 30y10y vs
  10y10y forward.

## Who holds what, and which way the flows go
Conventions:
- Vol is normal (bp/yr).
- Vega is in currency per 1bp normal vol ("$mn/abp" in some notes).
- Zero-coupon accreter notional is the initial (issue) notional.
- Curve spreads are longer minus shorter (10s30s = 30y − 10y, 30s50s = 50y − 30y), so long-end receiving makes them
  lower (flatter). The US swap spread is swap rate − Treasury yield (`swap_spreads`, `swap_minus_govt`), so
  long-end receiving makes it lower (more negative). Receive fixed = long duration.
- Vega supply means vega that dealers sell into European swaptions. A positive number means downward pressure on
  that bucket's implied vol.
- Our framing follows J.P. Morgan and Citi: after the issuer swaps, the dealer holds the option. BofA calls the
  "issuing entities" long Bermudan vol. Both describe the same economics, and for FIG self-placed deals the
  issuer's own desk holds it.

| Flow | Who ends up long the option | Hedge at issue | Big rally | Big selloff |
|---|---|---|---|---|
| Long-dated callable (Formosa 30NC5, 40NC5 zero-coupon accreter), swapped | Dealer. The issuer receives fixed on a cancellable swap; the dealer pays fixed and holds the cancel right, which makes it long a Bermudan receiver | Receive fixed in long-end swaps (flattens 10s30s and 30s50s, tightens 30y swap spreads). Sell European swaptions along the coterminal diagonal (vega supply) | Long gamma, so the dealer pays fixed and resists the rally. Bermudan vega collapses faster than European vega, so the dealer buys European vega back | The dealer receives fixed. Net vega is delivered long, so the dealer sells long-dated vega |
| Callable that is not swapped (non-financial issuer, by default) | Issuer keeps the call | none | none | none |
| CMS spread range accrual or inversion note | Dealer is long the digitals the investor sold through the coupon | Curve trades plus vanilla vol, for example receive 10y vs pay 30y and sell 4y2y vs buy 4y30y straddles | — | At a strike cross the Greeks flip. Hedgers must sell the curve and buy short-tail vol, gamma first and then vega |
| CMS caps sold to investors | Dealer is short the caps | Buy a strip of OTM payers from the strike out to 20%+. There is no natural seller, so payer skew gets bid | — | — |
| Notes with embedded curve options (USD 2006) | Dealer is long spread vol | Sell curve vol | — | — |
| JPY PRDC / long FX-linked notes | Dealers' PRDC hedging books (option detail not in the sources) | Long-end USD/JPY cross-currency basis, linked to the FX level | — | — |

Sources for the table: J.P. Morgan (29 Mar 2019; 21 Feb 2020), Citi (9 Jan 2017; 3 Jan 2017), BofA (11 Mar 2024),
Merrill Lynch RateLab (11 Jun 2008; 27 Oct 2009; Dec 2006), Huggins & Schaller (2024).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Callable / structured issuance deal log | `callable_issuance` | deal level, ≥ 3y (call history needs ≥ 5y) | announce_date, ccy, issuer_type (financial / government / ssa / non_financial), listing (formosa / other), notional_ccy (initial), structure (`30NC5`), coupon_type (zero / fixed), call_freq, `status` vintages with `call_date` and `redeemed_ccy` (supply uses the first row per `deal_id`; the CLI does this); optional `swapped` and `vega_per_100mn_ccy` |
| Swaption normal vols | `vol_surface` (product = swaption, strike_offset_bp = 0) | daily, ≥ 3y | expiries 1y-20y, tails 2y-30y, for ratios, regressions and z-scores |
| Par swap curve | `curve_par` | daily, ≥ 3y | annuities for straddle equivalents; 10s30s, 30s50s and 10y10y-vs-30y10y forwards |
| Swap and swaption prints | `flows_trades` | daily | long-expiry swaption prints and long-end receive prints around deal dates (confirms hedging) |
| 30y swap spreads | `swap_spreads` (measure spread_otr or spread_mm, ref 30Y) | daily, ≥ 3y | delta channel; check `sign_convention` |
| Long-end cross-currency basis | `basis_swaps` (basis_type = xccy) | daily | JPY/AUD structured-note channels (PRDC, Uridashi) |
| FX spot and forward points | `fx_rates` | daily | investor FX-hedge cost (e.g. 3M forward carry) and pick-up after hedging, a driver of demand |
| Investor balance sheets | `macro_series` | monthly / quarterly | e.g. Taiwan lifer total and foreign assets, regulatory caps |

If the deal log is missing, ask the user or the data adapter for it. Never invent issuance or vega numbers. The
per-deal vega needs a Bermudan pricer (model each deal as a par cancellable swap or accreter callable struck at the
announcement-date par rate). The two anchors below are only for order-of-magnitude work.

## Method
1. **Classify each deal**:
   - Swapped (vol reaches the street): financial, government and SSA issuers swap; non-financial issuers do not.
     This is Citi's "simplistic" rule. J.P. Morgan counts a corporate as swapped only if an SDR print matches the
     deal.
   - FIG self-placed deals keep the hedge on the issuer's own vol desk, so they reach the street only partly.
2. **Vega per deal**: `vega_i = notional_i / 100mn × v(structure, curve, vols) × swapped_i`.
   - Anchors at early-2017 rates: 30NC1 ≈ $145K and 30NC6 ≈ $270K per $100mn initial notional, per 1bp normal vol
     (Citi, Long Live Formosa, Jan 2017).
   - Vega rises with lockout and with final maturity (40NC5 > 30NC5).
   - A flatter curve pushes risk into longer expiries for any structure (J.P. Morgan, 10 Jan 2020).
3. **Redemptions and net supply**:
   - Expected redemptions: `E[R] = Σ_i p_call,i × N_i`.
   - Raw Bermudan call probabilities overstate actual calls. Observed call efficiency among bonds with very high
     model call odds since Jun 2019 was about 0.5 (notional-weighted). By segment: about 0.7 for issues ≥ $300mn,
     0.2-0.4 for smaller issues, > 0.7 for non-financial corporates, lowest for FIG self-placed (J.P. Morgan,
     10 Jan 2020). That 0.5 is for the high-odds bonds only. For a whole book, whose probabilities include lower
     odds, use the book-level ratio below (about 0.4) unless you fit the classifier.
   - Better still, fit a call classifier on model probability, log size and issuer type
     ([ml-models-for-rates](../ml-models-for-rates/SKILL.md)).
   - The haircut is not a constant: for 2020 as a whole J.P. Morgan's empirical/raw ratio was 30/78 ≈ 0.38, and
     0.24-0.47 by quarter. Project redemptions at current rates and at ±50bp (Citi, In search of cheap vol,
     Jan 2020), because call odds move with rates. `expected_redemptions(..., efficiency=0.4)` in the script.
   - Reinvestment: freed regulatory room is reinvested quickly, despite a 6-month grace period. Default: 1/3 of
     returned principal goes back into callables, split 50/50 between 30NC5 and 40NC5 (J.P. Morgan, 10 Jan 2020).
     In Q1 2020 new deals (~$14.5bn) roughly matched cash returned (~$14bn) (J.P. Morgan, 21 Feb 2020), so treat
     1/3 as a floor and calibrate it to the latest quarter.
   - New money from investor growth: Citi (Jan 2017) found Taiwan lifers' foreign non-exempt assets went from about
     37% to about 42% of assets against a 45% cap. Total assets grew about 9% a year and foreign holdings about 25%
     a year. On that basis Citi projected about $35bn a year of net Formosa supply (2016 was about $30bn).
4. **Bucket the vega**:
   - A Bermudan with annual calls from lockout L to final M has vega along the coterminal diagonal
     L×(M−L), (L+1)×(M−L−1), and so on.
   - Map each bucket to liquid hedge points. Defaults:
     - NC1-NC2: 50/50 1y30y and 10y20y (Citi: "some combination 1y30y and 10y20y (or even 10y10y for liquidity
       reasons)").
     - Lockout ≥ 3y: 5y25y 35% / 10y20y 35% / 20y10y 30% (Citi's Mar 2019 bucketing of the outstanding stock).
     - 6y expiries are illiquid, so Citi expected that vega to be hedged in 10y expiries (10y10y, 10y20y).
     - 40NC5 adds 20y-expiry risk: about $5.5mn of J.P. Morgan's ~$20mn/abp in Q1 2020. The defaults above are
       30y-coterminal, so supply your own hedge map for 40y finals (the script refuses to default any final maturity other than 30y).
5. **Convert to straddle equivalents** so supply can be compared with market size:
   - `straddle_vega(e, t) = 2 · N · A(e, t) · √e · φ(0) · 1e-4`, where φ(0) = 0.3989, A is the forward annuity
     (years) and the vega is per 1bp normal vol.
   - `straddle_eq_notional = bucket_vega / straddle_vega(e, t, N = 1)`.
   - Compute this yourself. Do not reuse a ratio from a note (see Worked example A).
6. **Measure the dealer stock and dVega/dRate**:
   - Dealer short European vega = `stock_vega × (1 − hedge-fund share) × hedge ratio`. Defaults: hedge-fund share
     0.15 and hedge ratio 0.85 (Citi, Mar 2019). J.P. Morgan (2019) estimates about 40% of the risk (vega-weighted)
     is placed with end users via B/E switches. Treat that as a cross-check.
   - Reprice the dealer book (long Bermudan stock, short European hedges) under parallel shocks of ±25, ±50 and
     ±100bp, in vega terms (V = vega in ccy per 1bp, both legs positive numbers):
     `ΔV(s) = [V_Berm(s) − V_Berm(0)] − [V_Euro(s) − V_Euro(0)]`, the change in the dealer's net long vega. Repricing only the Bermudans overstates
     the rebalancing, because the European hedges lose vega too. A negative ΔV in a rally means dealers must buy
     European vega. A positive ΔV in a selloff means they sell it.
   - Snapshot from J.P. Morgan (Mar 2019): callable convexity would stay at 80-90% of its then level in a further
     rally and fall meaningfully only after a 50bp+ rally. Recompute for today's stock; do not reuse as a rule.
7. **Is it priced?** Test the bucket the supply hits, and its neighbours:
   - (a) tail or expiry ratio z-score, 3m window (Citi's switch tables);
   - (b) level regression of the bucket (y) on a less-affected bucket (x) over 1-3y, with the residual's z-score
     (examples in Worked example A). Fit on data ending before the signal date. Check that the residual is
     stationary with an Engle-Granger cointegration test (an ADF on estimated residuals needs Engle-Granger critical
     values, not the plain ADF ones; see [quant-cointegration](../quant-cointegration/SKILL.md)). Level-on-level
     residuals are highly autocorrelated, so read the z as a ranking, not a p-value;
   - (c) macro-vol residual: vol regressed on the first 3 rate PCs, so the rates level does not contaminate the
     signal;
   - (d) roll-up along the expiry axis (e.g. 1y30y vs 5y30y).
   - Use [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md) for the statistics.
8. **Delta channel**:
   - Express issuance-related receiving in 10y-equivalents and as 30-40y partial DV01.
   - Compare it with natural payers at that maturity. For the ultra-long end J.P. Morgan (2020) found "no natural
     payer", so there is no floor under flattening while supply lasts.
9. **Structured notes**:
   - Track strike proximity on the **convexity-adjusted forward** spread, not the spot spread:
     `z_strike = (F_adj − K) / (σ_spread · √τ)`, with `σ_spread = √(σ_A² + σ_B² − 2ρσ_Aσ_B)`. F_adj and K in bp,
     σ in bp per √year (normal vols of the two CMS rates), ρ their correlation, τ in years to the observation.
   - Scale the per-100mm hedge vector to the estimated outstanding. Check whether customers already hold the same
     trade as the hedgers.
   - Notes that cannot be called keep their switch risk for their whole life.

## Worked examples
**A. Lockout proposal, viewed as a vega-bucket shift** (Citi, Long Live Formosa, 9 Jan 2017; full grid in
[references](references/supply-history-and-hedge-vectors.md)).
- The rule: Taiwan *proposed* a 6y minimum non-call for the exemption from lifers' 45% foreign-investment cap. A
  later draft set it at 5y (Citi, 17 Jan 2017). Recent issuance had been mostly NC1-NC2, and about 70% of 2014
  NC1/NC2 bonds were already called.
- Supply: about $38bn gross Formosa over Q2 2017-Q2 2018.
- Bucket shift, 30NC6 minus 30NC1, $K per $100mn: 1y30y −13.5, 2y30y −8.7, 4y25y −9.2, 6y25y +24.6, 7y25y +31.2,
  10y10y +30.1, 10y20y +30.4, 10y25y +19.8.
- The grid sums to +129K, close to the 270 − 145 = +125K headline. Vega leaves 1y-2y expiries in 30y tails and
  arrives in 10y expiries and 10y-20y tails.
- Citi's sizing: total vega +$31mn (≈ $20bn 10y10y straddle equivalents) and 10y-expiry vega +$46mn (≈ $25bn).
  Those numbers depend on an unpublished lockout mix, so they cannot be reproduced. Their two conversions imply
  $1.55mn and $1.84mn of vega per $1bn of straddles.
- Our conversion at a flat 2.6% gives $1.70mn per $1bn, so $31mn ≈ $18bn and $46mn ≈ $27bn.
- Priced check:
  - The first-order effect was already priced. 10y30y was about 5 normals (about 1.6σ) cheap to 2y30y. The fit
    10y30y = 0.51 × 2y30y + 25.99 (R² 0.80) also showed it cheap (Citi, Buy long expiries, 17 Jan 2017).
  - The second-order effect was not priced. The 2y-expiry 10y/30y tail vol ratio was 1.09, a 3m z-score of +2.4.
- Trade: buy 2y30y vs sell 2y10y straddles, beta-weighted at 1 : 0.8 vega. That is $53mn of 2y30y per $100mn of
  2y10y. The script reproduces $52.7mn from flat-2.6% annuities; the Citi Weekly's "$63mn" does not reconcile.
- Risk: the rule is delayed or diluted.

**B. Dealer stock** (Citi, Vol cycle, steepeners, and SOFR, 25 Mar 2019).
- Stock: about $175bn of financial long-dated callables outstanding, 95% zero-coupon accreters, with the average
  structure printed as "4NC30". That is about $366mn of normal vega swapped to dealers.
- Dealer hedges: 366 × 0.85 × 0.85 ≈ **$265mn short European vega**. Split 35/35/30 that is about $93mn 5y25y,
  $93mn 10y20y and $79mn 20y10y.
- Event (ex-ante estimate): Citi estimated that the move of swaps to SOFR discounting would reprice dealer
  positions down by about $100mn at unchanged vols (a value transfer, assuming delta hedges are offset by valuation
  adjustments at the CCP), or by up to about $260mn at January 2019 FF/SOFR basis, and that dealers could mark
  European vols lower against Bermudans.
- Read-across: the B/E vol differential is a supply-driven RV axis. J.P. Morgan's B/E switches trade it directly,
  e.g. sell a 3Yx27Y 4.5%-strike Bermudan receiver at 3585bp of notional vs buy the European at 3523bp
  (J.P. Morgan, 29 Mar 2019).

**C. Empirical haircut and the 40NC5 migration** (J.P. Morgan, 10 Jan and 21 Feb 2020).
- Redemptions: $85bn was up for call in 2020. The raw Bermudan model said $78bn would be redeemed, the empirical
  model about $30bn. Quarterly empirical/raw ratios were 47%, ~32%, ~32% and 24%, so supply was front-loaded.
- Vega supply: Q1 2020 was about **$20mn/abp**, against $40mn/abp from the raw pricer. It was the most since early
  2018, with about $5.5mn/abp in 20y+ expiries. Buyers took 40NC5 for about 15-20bp of pick-up over 30NC5.
- Vol trade: buy 10y10y vs sell 20y10y ATMF straddles, vega-neutral: long $58.4mn 10Yx10Y (1185c) vs short $50mn
  20Yx10Y (1230c). It was first put on in Dec 2019 and still open in the 21 Feb 2020 note. At about 2% flat
  annuities the two legs' vegas match to within 1%, which checks the sizing.
- Delta: about $9bn of 10y-equivalents in Q1, on course for a record $14bn+. Trade: receive $185mn 30Yx10Y (1.70%)
  vs pay $125mn 10Yx10Y (2.09%) at −39bp, slide −4bp/1y.

**D. EUR inversion notes, a forced unwind** (Merrill Lynch RateLab, 11 Jun 2008).
- The note: 10y, 7% coupon accruing on each day that EUR 30y CMS − 2y CMS ≥ 0. With 7 inverted days out of 91 the
  coupon is 7% × 84/91 = 6.46%.
- Hedge per 100mm of notes (700mm of digitals): receive 450mm 10y vs pay 150mm 30y; sell 400mm 4y2y straddles vs
  buy 75mm 4y30y. Scaled to EUR 15bn of notes (issued range 13-20bn): about 60bn short 4y2y, 11bn long 4y30y,
  67bn received 10y and 22bn paid 30y.
- What happened: spot 2s30s inverted after hawkish ECB comments, and the Greeks flipped. Dealers had to sell the
  curve with no counterparty, because customers were already in steepeners. They then bought back the 4y2y
  straddles and went net long, buying gamma first and then vega. EUR 3m2y and 3y2y normal vols spiked. The note
  prints a 32bp one-day move in the "USD 2yr versus USD 30yr swap spread" as a theoretical "nine standard
  deviation" event; it sits in a note about EUR, so check the currency before reusing it.

## Signals & interpretation
- **Supply regime**: compare the monthly swapped vega with its median over the prior 12 complete months
  (exclude the current month; never compare a month-to-date figure with full months).
  - Default thresholds: ≥ 1.5× is heavy and ≤ 0.5× is light. The series is lumpy and seasonal, so a median ratio
    is more robust than a z-score.
  - Heavy supply leads to cheapening in the mapped hedge points and a positive vol roll-up for long bottom-right
    vega. BofA (Feb 2024) quotes 5y30y at about 85bp vs 1y30y at about 97bp, about +3bp/yr.
  - Light supply is a "tailwind for long-dated vol" (Citi, Feb 2023, Sep 2026 and Oct 2026; Morgan Stanley,
    Jul 2026).
  - Supply is endogenous: it restarts when vol falls and credit spreads stabilise (Citi, Mar 2020) and slows
    when yields are less attractive after a rally (Citi, May 2017). Do not treat it as independent of vol.
- **Seasonality**:
  - January is heavy. At least 50% of Q1 typically prints in January, and Jan 2017 set the record at $9.5bn.
  - February is lighter around Lunar New Year.
  - Financial issuance drops during the roughly 4-week earnings blackout (J.P. Morgan, Sep 2019), e.g. Mar 2018
    $3.6bn → Apr ~$0.3bn (Citi, Convexity Meets Steepeners, Apr 2018).
  - June is subdued.
  - Trade the supply lull after a heavy month, e.g. Citi bought 10y-expiry vol after January 2020.
  - See [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md).
- **Bucket shifts beat level calls.** A structure-mix change (lockout rule, NC5 → 40NC5, a flatter curve) moves vega
  across expiries.
  - Trade the bucket that is not yet priced when |z| ≥ 1.5 in the direction the supply implies.
  - If the first-order point is already ≥ 1.5σ cheap, look one step away (Worked example A).
- **Vega intensity** = vega per $bn of swapped gross issuance.
  - From Citi's monitor (our ratio): about 2.0-2.2 per financial $bn in 2016-17; 2.2-2.9 per gross $bn in
    2018-2022 (no financial split, so a lower bound per swapped $bn); 1.07 in H1 2023; about 0.9-1.0 in 2025-26
    (all financial). The step-down began in 2023, not 2025.
  - A step change signals a structure or issuer-mix change, or a methodology change. Ask before extrapolating.
- **Cheap for a reason.** Citi (Sep 2019) saw forward vols at −1.5σ to −2.4σ but did not buy, because of
  lower-bound risk plus callable supply. Do not fade supply-driven cheapness while supply continues. Citi
  (Parolari, Jun 2022) calls trades distorted by persistent forces, such as Taiwanese-insurer vol selling via
  callables, *structural*: their ex-post charts trend rather than revert, so size them as carry trades, not
  mean-reversion trades.
- **dVega/dRate**:
  - After a large selloff, expect extra long-dated vol selling. 10y10y and 10y30y cheapened post-election in 2016
    partly from dVega/dRate flows (Citi, Jan 2017). In 2013 structured-note dealers cut long-expiry, long-tail vega as rates rose.
  - After a large rally, Bermudan books buy vega back, which gives the slightly positive-convex 5y30y
    vol-vs-forward profile BofA describes.
  - Supply does not always cheapen vol: after the 2019 rally and long-end flattening dealers were net short via
    dVega/dRate (a steeper Bermudan diagonal), and new Q1 2020 supply went into covering that short (J.P. Morgan,
    21 Feb 2020). Net the stock repricing (step 6) against new supply before calling direction.
  - Fading a flow-driven overshoot is a timing trade. Size it for further stop-outs (Citi, Mar 2020).
- **Delta.** Issuance-related receiving lines up with a flatter 10s30s/30s50s and tighter 30y spreads. Dealers'
  callable gamma pays into rallies and offsets mortgage receivers (net hedger flow = negative-convexity hedgers −
  callable offset). See [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md).
- **Structured notes near the strike.** With |z_strike| < 1 (our default threshold) on the convexity-adjusted forward, and dealers and
  customers positioned the same way, expect gap risk in the curve and short-tail vol. Own short-tail gamma or stay
  out. Do not sell it.

## G10 market differences
| Market | Documented channel | What to watch |
|---|---|---|
| USD | Formosa and other long-dated callables, mostly 30NC5/40NC5 zero-coupon accreters from financial issuers; Korean-lifer callables are also mentioned (J.P. Morgan, Sep 2019) | Since 2025 most supply is non-Formosa (2026 YTD Formosa $1.28bn of $18.14bn gross). Our inference: Taiwan regulation is no longer the main driver. Watch Taiwan FX-hedge cost and the lifer caps |
| EUR | CMS-spread range accruals and inversion notes (2007-08, EUR 13-20bn); structured-note digital hedging plus pension/insurer ALM receiving pushed EUR 30y below 10y in Jun 2008 (Credit Suisse, Aug 2013). Danish callable mortgage bonds load EUR vol mainly in 5y and 10y expiries, with 5y20y as proxy (Nordea, Nov 2021) | Short-tail vol (2y tails) and 2s30s near note strikes; see [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md) and [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md) |
| JPY | PRDC hedging ties 20y-30y USD/JPY basis to FX; prepayments of structured notes linked to equity or FX unwind super-long receivers | [xccy-basis](../xccy-basis/SKILL.md) |
| AUD | Reverse dual-currency hedging desks receive long-end AUD/USD basis when AUD/JPY falls and pay when it rallies (J.P. Morgan, Mar 2015). Linking this to Uridashi issuance is our inference | AUD/JPY level vs 10y basis |
| GBP, CAD, NZD, CHF, SEK, NOK | No structured vega-supply channel is documented in the reference library | The method transfers, but you need local issuance data. Do not assume USD-sized effects |

## Pitfalls
- **Raw model call probabilities.** They saturate near 100% after rallies, but issuers do not call purely on
  economics. Without the empirical haircut, J.P. Morgan's 2020 redemptions were overstated about 2.6× ($78bn vs
  $30bn) and Q1 vega supply 2× ($40mn vs $20mn/abp).
- **The swapped rule is crude.** A higher non-financial share means less vol sold. FIG self-placed deals keep the
  hedge in-house.
- **Not every Bermudan is hedged with Europeans.** J.P. Morgan puts about 40% (vega-weighted) into B/E switches;
  Citi puts about 15% with hedge funds plus a 0.85 hedge ratio. These are rival estimates from two houses, not
  haircuts to stack. Street supply is less than the gross vega either way.
- **New-issuance models ignore dVega/dRate.** J.P. Morgan's own Exhibit 11 says so. Add the stock repricing (step 6)
  before calling direction after a big move.
- **Regulatory analysis is about drafts.** The 6y minimum was a proposal and the later draft said 5y. Size scenarios
  and label which version you used.
- **Mixed units.** Do not combine initial notional with accreted notional, $mn/abp vega with notional-equivalent
  straddles, or normal vol with lognormal vol.
- **Strike proximity measured on spot.** Measure it on the convexity-adjusted forward spread. In 2008 the forwards
  inverted after spot.
- **Persistence.** Technically driven cheapening (supply, long-vega liquidations) can run further before it reverts.
  Pre-define stops.
- **Directional contamination.** Normal vol co-moves with rate levels. Regress on rate PCs before calling a bucket
  cheap ([vol-rates-options-rv](../vol-rates-options-rv/SKILL.md)).
- **Discounting or CSA changes.** These move the value of long-dated European hedges (Citi estimated ex ante that the SOFR
  transition would reprice dealer positions down by about $100mn-$260mn) and can shift the B/E marks.

## Output
Return the following, then hand off to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and challenge
the result with [rv-devils-advocate](../rv-devils-advocate/SKILL.md).
1. **Supply table** by month or quarter: gross, redeemed, net, swapped share, vega (ccy per bp normal), vega per
   $bn swapped, versus the trailing-12m median and versus forecast.
2. **Bucket table** for each hedge point (e.g. 1y30y, 5y25y, 10y10y, 10y20y, 20y10y): vega supplied, straddle
   notional equivalent, current normal vol, 3m tail/expiry ratio z-score, regression residual z, and roll-up.
3. **Stock and scenario block**: dealer short European vega, and ΔV of the stock at ±25, ±50 and ±100bp (who
   buys or sells vega where).
4. **Delta block**: 10y-equivalent receiving, 30-40y partial DV01, and the long-end curve and spread levels
   affected.
5. **Verdict**: priced or not priced, the expression (e.g. tail switch, expiry flattener, B/E switch, long-end
   forward flattener), sizing basis (vega-neutral or beta-weighted), catalysts (issuance calendar, call dates,
   regulation) and kill criteria (supply surprise vs forecast, selloff beyond 50bp).

## Scripts
- [`scripts/vega_supply.py`](scripts/vega_supply.py): applies the swapped rule, computes per-deal vega from an input
  vega table (with 30NC1/30NC6 anchors as a fallback), monthly supply and vega intensity, hedge-point allocation,
  ATMF straddle equivalents, expected redemptions and the dealer short-European chain.
  - Run `python scripts/vega_supply.py --deals deals.csv --vega-table vt.csv --hedge-map hm.csv --rate-pct 4.0`.
  - `--selftest` checks the flat annuity and the Bachelier straddle vega against closed forms and a finite difference, reproduces
    Citi's $53mn switch notional and the 366 → 265 dealer chain, and checks the aggregation on a toy deal log.
  - It contains no Bermudan pricer. Feed it model vegas.

## Related skills
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): surface rich/cheap, macro-vol residuals, tail and expiry switches
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): long-end convexity value and curve-implied vol vs swaption vol
- [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md): CMS spread options, digitals and spread vol
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): payer skew bid from CMS-cap hedging
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): P&L of the resulting vega and gamma trades
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): the negative-convexity flows that callables offset
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): confirming hedge prints and the swapped flag
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension and insurer long-end receiving
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): 30y swap spreads under issuance-related receiving
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): 30y10y vs 10y10y forward flatteners
- [xccy-basis](../xccy-basis/SKILL.md): PRDC, Uridashi and investor FX-hedge cost
- [ml-models-for-rates](../ml-models-for-rates/SKILL.md): empirical call-probability classifier
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): level regressions and beta-weighted vol switches
- [quant-cointegration](../quant-cointegration/SKILL.md): Engle-Granger test of the bucket-on-bucket residual
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md) and [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md)
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): the `callable_issuance` table

## References
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Long Live Formosa (9 Jan 2017): lockout rule → vega profile → hedge points, the 30NC1/30NC6 vega anchors, and the 2y30y/2y10y trade
- Citi Research (Mathai, Bikbov, Kang, Williams) - US Rates Weekly: Swearing in huge expectations (13 Jan 2017): the full 30NC6−30NC1 bucketed-vega grid and the 10y10y straddle trade with target/stop
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Buy long expiries (17 Jan 2017): the 5y draft rule, lockout mix, and the 10y30y-on-2y30y regression
- Citi Research (Mathai, Bikbov, Kang, Williams) - US Rates Weekly: Going nuclear (on the curve) (3 Feb 2017): record January supply and the 3y30y-on-3y10y regression
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Vol cycle, steepeners, and SOFR (25 Mar 2019): dealer Bermudan stock, the hedge mix and the SOFR-discounting value transfer
- J.P. Morgan (Younger, Beinstein, Salem, St John) - Taiwanese demand for US fixed income in 2020 (10 Jan 2020): empirical call model, reinvestment, 40NC5 migration and 20y-expiry supply
- J.P. Morgan (Younger, Salem, St John) - Interest Rate Derivatives: Renewed Formosa supply continues to flatten the long end (21 Feb 2020): duration supply, dVega/dRate saturation and long-end flatteners
- J.P. Morgan (Younger, Salem, St John) - Interest Rate Derivatives: A comprehensive look at convexity hedging in interest rates (29 Mar 2019): dealers long convexity, the B/E placement share and callable offset flows
- J.P. Morgan (Younger, Salem, St John) - Interest Rate Derivatives: Dynamic hedgers are long, banks are short, and both are buyers of spreads (13 Sep 2019): swapped-issuance rules, Korean-lifer callables and the earnings blackout
- BofA Global Research (Braizinha) - US Vol Primer: A Guide for the Perplexed (11 Mar 2024): Bermudan hedging → vol roll-up and the dVega/dRate profile
- Citi Research (Bikbov, Williams) - Rates Vol Lab: In search of cheap vol (17 Jan 2020): Q1 front-loading, 40NC5 vega and the supply-lull switch trade
- Citi Research (Bikbov, Williams) - Rates Vol Lab: Liquidity, vega, and convexity (30 Mar 2020): technical cheapening and USD vs EUR 10y10y
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Buying vol for less (25 Sep 2019): cheap forward vol that is cheap for a reason
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Fair value vs seasonality (1 May 2017): monitor methodology and 2016-17 supply/vega
- Citi Research (Chang, Williams, Appeddu, Vazquez Plata) - Rates Vol Lab: Fading vega dislocations (5 Oct 2026): 2025-26 supply, mostly non-Formosa
- Citi Research (Chang, Williams, Appeddu) - Rates Vol Lab: Forward steepener and vol divergence (12 Jun 2023): 2022-23 supply collapse
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Gamma and Vega RV (14 Jan 2019): 2018 supply and structural shifts in fair vol levels
- Merrill Lynch RateLab - "Well, here's another nice mess you've gotten me into" (11 Jun 2008): the EUR inversion-note hedge vector and the Greeks-flip unwind
- BAS/ML RateLab (Bassman) - No Bad Bonds, Just Bad Prices (27 Oct 2009): CMS-cap hedging as a source of payer skew
- Merrill Lynch RateLab (Bassman) - [Yield Curve Options] (8 Dec 2006; title inferred): structured notes leaving dealers long spread vol
- Credit Suisse (Bassman, Convexity Maven) - Forwards are NOT a Prediction (12 Aug 2013): structured-note dVega/dRate in 2013 and EUR 30y below 10y in 2008
- Morgan Stanley (Zhou, Hornbach, Tobias, Singh, Carter) - Investors Are Paying for Protection Against 6% Rates (2 Jul 2026): callable issuance monitor by issuer type and low supply as vol support
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Convexity Meets Steepeners (19 Apr 2018): callable supply seasonality (earnings blackout) and FX-hedge-cost drag
- Citi Research (Chang, Williams, Appeddu) - Rates Vol Lab: Short Blues convexity via futures/swaps (21 Feb 2023): low vega supply as a tailwind for bottom-right vol
- Morgan Stanley (Zhou, Carter, Hornbach, Tobias, Singh) - Buy Higher Rates Protection at a 30% Discount (27 Aug 2026): EUR vs USD 5y5y vol switch citing callable issuance
- Doug Huggins, Christian Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): PRDC hedging and the long-end cross-currency basis
- J.P. Morgan (Bassi et al.) - Drivers of cross currency basis in EUR, GBP, JPY, AUD & CHF (11 Mar 2015): structured-note prepayments and reverse dual-currency hedging flows
- Citi Research (Mathai, Bikbov, Kang, Williams, Li) - US Rates Weekly: The rocky road to a steeper curve (18 Jan 2019): short 10y10y straddles on callable supply
- Citi Research (Bikbov, Williams) - US Rates Vol Lab: Trading long-dated convexity (9 May 2019): April 2019 callable supply and the 2019 supply outlook
- Citi Research (Chang, Williams, Appeddu) - Rates Vol Lab: Left-side vols' outperformance (22 Jun 2021): muted callable supply and 10y10y vs 5y10y
- Citi Research (Chang, Williams, Appeddu, Vazquez Plata) - Rates Vol Lab: Slow and steady wins the short gamma race (14 Sep 2026): low callable issuance as a tailwind for long-dated vol
- Citi Interest Rate Volatility Trading (Parolari) - A Holistic Approach to Convexity Across Fixed Income (Jun 2022): structural vs idiosyncratic RV, with Taiwanese-insurer vol selling as the structural example
- Nordea Markets (Aalund) - Bonds & bold: The one you don't like to read but need to read! (5 Nov 2021): vol exposure of Danish callable mortgage bonds by expiry
- Citi Research (Bikbov) - North America Rates Focus: Corporate supply to bring spreads tighter (3 Jan 2017): dealers receive 30y to hedge long-dated callables, which tightens 30y spreads, plus Formosa yield-pick-up economics
