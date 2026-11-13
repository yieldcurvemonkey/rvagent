---
name: stir-futures-rv
description: 'Relative value inside STIR futures strips - calendar spreads, butterflies and micro-flies, condors, packs and bundles (whites/reds/greens/blues/golds), kink and strip-shape fades, roll/carry screens, SR1-SR3 futures spreads, meeting-neutral hedges, term TED. Covers 3m/1m SOFR, SONIA, Euribor, ESTR, CORRA, SARON, bank-bill futures and legacy ED/Short Sterling/Euroswiss across G10. Use when asked whether a futures calendar, fly, pack, gap or colour is rich or cheap, which contract to buy or sell in the strip, how to weight or cost a fly, how to hedge a swap/FRA/loan with futures, or how to trade ICS, SR3 strip vs OIS, microfly roll-down, bundle vs 2y swap, stub/tailing hedges with Eurodollar, Euribor or SONIA futures. SOFR-FF basis: spread-tenor-and-index-basis; pack-vs-swap convexity adjustment: stir-convexity-adjustment.'
---

# STIR futures relative value

A STIR futures strip is a ladder of 3m forward rates (price = 100 - rate) with exchange-fixed conventions, daily margin and
meeting-dated policy steps. RV exists because the contracts are individually noisy, positioning concentrates in particular
months (Decembers, colours, packs), averaging/compounding and meeting dates create calendar artefacts, and futures and swaps
price the same forward differently (convexity, margin, CCP, venue). This skill finds those dislocations, tests that they are
not artefacts, sizes and costs the structure, and states the roll, hedge and exit.

## When to use
- "Is the Sep-27/Dec-27/Mar-28 SOFR fly rich?", "which contract in the strip is cheap to its neighbours", kink or strip-shape fade.
- Spread/fly/condor/pack/bundle construction: weights, DV01, round-trip cost, roll-down (microfly carry).
- Futures vs swaps: strip-implied IMM swap, hedge a swap/FRA/loan with futures, pack convexity (CA) vs model, bundle vs 2y swap.
- Intra-futures spreads: SR1 vs SR3 (ICS 3+3:10), SR1 vs FF (SOFR-FF "SERFF"), FF vs ED-style overlap weighting, meeting gaps.
- Meeting-dated structures expressed in futures (FOMC fly, year-end premium in FF futures).
- Cross-market futures RV (SOFR vs SONIA vs Euribor curve shapes), term TED (bond future vs bundle).
Not here: convexity-adjustment derivation ([stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md)); what is priced in
per meeting ([stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md)); compounding and reset-risk
mechanics ([stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| STIR futures prices (price = 100 - rate) | `stir_quotes` | daily `settle`, >= 1y (3y in calm regimes); bid/ask, volume, OI | never mix `settle` and `close` snaps (they differ by 0.2-0.9bp) |
| Contract terms: BPV, tick, reference method, reference start/end, last trade | `fut_static` | per contract month | `ref_method` compound / average / ibor_fix decides the maths |
| Meeting calendar incl. effective dates | `cb_meetings` | schedule to ~12m | for meeting-neutral hedges and calendar-tilted flies |
| Overnight fixings (known part of in-period front contract, turns) | `rate_fixings` | daily | publication-lag aware |
| Par/zero swap curve on the same CCP as the futures (for pack vs swap, strip-vs-OIS) | `curve_par` / `curve_zero` | daily | state the CCP; margin netting depends on it |
| Futures options (for fly-vs-vol cross-checks) | `opt_quotes` | daily | optional |
| Positioning (OI by month, CFTC categories) | `positioning` | weekly | optional; CA proxy if unavailable |
| Calendars | `calendars` | holidays | exchange calendars, not cash |
Schemas: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If an input is missing, ask for it or hand off to
the `rv-data-engineer` agent. Never invent values. Contract mechanics, per-market terms and settlement formulas:
[references/contract-mechanics.md](references/contract-mechanics.md).

## Method

### 1. Conventions (state them in every output)
- Price = 100 - rate. All structure maths in RATE space, bp. Say "price space" explicitly when quoting exchange spreads.
- Calendar spread (A-B) = rate(far) - rate(near) = P(near) - P(far). Positive = upward sloping; steepening widens it.
- Fly = `2*r_belly - r_front - r_back` (bp) = `P_front + P_back - 2*P_belly`. Positive = belly cheap (high rate).
  Exchange "buy fly" = long wings, short 2 belly = PAY belly. Receive belly (long 2 belly futures) = "sell the fly". Some desks
  quote the microfly as `2*P_belly - wings` (opposite sign): check before comparing with any source.
- Condor (rate space, same sign as the fly: positive = body cheap) `r2 + r3 - r1 - r4` = fly(1,2,3) + fly(2,3,4) = S1 - S3 (price-space exchange condor B1+B2 = P1-P2-P3+P4 equals this); double fly = fly[i] - fly[i+g]; gap g = 1-4 quarters.
- Long futures = receive rate (long duration, gains when rates fall). P&L = contracts x change in price (bp) x BPV.
  BPV: 25 per bp for 3m contracts (USD/EUR/GBP/CHF/CAD), 41.67 for 1m SOFR and 30-day FF (USD). A package with any weights has
  DV01 = one contract BPV per bp of the spread S = sum(w_i r_i); contracts traded = sum|w|.
- "Sell the pack" / "short CA" = buy the pack, pay the matched swap (see 6). State which leg is long the rate.

### 2. Build a clean strip
1. Contracts: first 12-16 quarterlies (Whites, Reds, Greens, Blues; liquidity falls off after the Blues, beyond 3-5y prices are
   partly implied). Add serial/1m contracts only for meeting/month-end structure. Strip length 8 (small markets) or 12 (liquid)
   so the strip always ends just past 2y or 3y; 6, 7, 10, 11, 14 are the worst (roll leverage).
2. Prices: use settles for history. For intraday work, do not use last trade or the plain bid/ask mid on wide-tick SOFR contracts:
   use an intrinsic-depth mid or a multi-instrument least-squares mid that includes spread and fly books ([references/contract-mechanics.md](references/contract-mechanics.md) section 4).
3. Front contract: SOFR/SONIA 3m contracts trade while their reference quarter is under way. Split into known and unknown fixings
   (`R_unknown` formula in the reference file) and treat the in-period contract as sticky, low-vol; exclude it from kink screens.
   Euribor contracts are fixed at start and expire at the fixing; the three families are not interchangeable.
4. Rolling: roll exposure from the 2nd into the 3rd contract before the 2nd enters its reference period; never roll by
   calendar front-to-back for RFR futures (a Dec-19 to Mar-20 roll cost 138bp at quarter-end vs 4bp at the start).
5. Use FIXED-contract structures (e.g. Sep/Dec/Mar) for z-scores. If you must use constant-maturity ranks, back-adjust roll jumps
   (front-rank |change| / median |change| across ranks > 3 = roll day: split into market move and roll artefact).
6. Quote hygiene: exclude stale prints and half-day settles; mark LIBOR-to-SOFR and standing-repo-facility (Aug 2021) breaks and
   re-estimate vol/mean reversion/regressions on post-break data.

### 3. Structure universe and cost
- Universe on N quarterlies: outrights, calendars (gap 1-4), flies (gap 1-4), double flies, condors, packs (4 quarterlies, equal
  weight), bundles (4N), stacks (n lots of one month as pack proxy). Individual ED/FRA-type spreads are noisy: prefer packs and 3m/12m calendars.
- Behaviour: spread vol grows with interval and falls with colour (a white pack spread can be twice as volatile as a red);
  most curvature sits in the first 2 years; 1s2s-type front segments have "a life of their own".
- Cost: round trip = `sum|w| x 2 x half-spread`. Fly (1,-2,1) = 4 contracts = 2bp at 0.25bp half-spread; condor 4 contracts; 2y bundle
  vs swap 8. Starting cost scenarios per fly package: maker 0, tight 1.5bp, taker 2.5bp (of S). Choose the cheapest integer package within tolerance of the
  fitted wing split. Cost in spread-sigmas is scale-invariant: an edge below ~1 cost is not an edge.
- Hedge weights: DV01-neutral first ("make sure your spread is DV01 neutral and then the cash-flow mapping is secondary"). Then, if the fly
  must be direction-neutral, use regression weights (fly on belly) or PCA weights (zero beta to belly); example PCA weights on USD flies
  1.3:2:1.1, 0.9:2:1.1, 0.8:2:1.2. Weights reduce but do not remove level/slope exposure: print the correlation/beta columns.
  Euribor hedges: regress on the 2y government future (PCA of Euribor spreads vs Schatz/Bobl spreads), not on the 10y.
  Weighting detail: [curve-butterflies](../curve-butterflies/SKILL.md), [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md).

### 4. Find kinks and strip-shape dislocations
Run several lenses; require two to agree before sizing.
1. **Fixed-contract fly z + roll.** For each adjacent triple: `fly_bp`, z over 65 trading days (starting default: one quarter,
   tracks regimes; use 252 for slow structures and shorten 3y -> 1y in fast markets), OU half-life, roll, risk-adjusted roll.
   Roll of a long-belly package = `fly[i] - fly[i-1]` (the structure at slot i becomes the one now at slot i-1; static curve).
   Fade direction `d = sign(z)` (z > 0 belly cheap -> buy belly); `fade_roll = d x roll`; risk-adjusted = fade_roll / (annualised 20d vol of the fly).
   `scripts/stir_structures.py` (`screen_flies`) implements this; it skips the in-period front contract by default.
2. **Regression monitor** (curve and fly). Spreads: regress each on its longer leg; negative residual = too flat, positive = too steep.
   Flies: regress on the belly; negative residual = belly rich (low yield), positive = belly cheap. Report 1m/6m/12m z of the residual. Use 1y history; regressions on levels of persistent series are spurious-prone, so treat the residual z as corroboration and check the residual's half-life; PCA flies for
   level/slope-neutral versions. Constant-maturity series are linear interpolations between futures.
3. **Smooth-curve fit residual.** Fit a monotone spline (or short-end meeting-step curve plus spline) through the first ~24 quarterly
   contracts, nodes denser in Whites/Reds, minimise error to settles; signal = futures rate - fitted forward (+ = futures rate too high = contract cheap), with 1y and 3m z.
   Re-run with different node placement: a dislocation that moves with the nodes is a spline artefact. Residuals should be largest in
   Whites and fade outward; a large residual at long expiry is anomalous. RMSE of the strip vs the fit is a regime gauge (it is not directional with Fed expectations).
4. **Calendar-adjusted fly.** Meetings fall unevenly across IMM quarters, so a fly is partly calendar. Compute the effective-meeting-count
   weights `W[i,m]` (share of contract i's reference days after meeting m) and the tilted fly with weights `(-(1-t), 2, -(1+t))`,
   `t = (gap1 - gap2)/(gap1 + gap2)` in meeting counts, |t| <= 0.35. If the tilted fly keeps the signal it is not calendar; if it vanishes it was
   the meeting layout. Smooth-policy-path null: [references/meeting-structures.md](references/meeting-structures.md).
5. **PC1 / PCA residual band** (Euribor, generic 1st-20th contracts): current PC1 residual vs its 1y median and 5th-95th percentile; positive = contract
   cheap (rate too high). Scatter value vs roll-down; prefer PC1-neutral flies, reject the most attractive trade if it is just front-end direction (e.g. a 2-9 flattener).
   See [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md).
6. **Cross-checks.** Compare the 3m-zero from a chained strip with the swap/deposit zero to the same maturity ("stringing") instead of
   forward-by-forward, which is sensitive to interpolation. Compare fly with the fly of option-implied medians (tail rent = -mm_front + 2 mm_belly - mm_back, mm = mean - median of each leg's implied distribution, bp): it retires leg by leg as contracts expire and a persistent gap is a
   risk premium, not an arbitrage; express it with delta-hedged wing options, not an outright fly ([stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md)).
7. **Driver tests before calling it mispricing.** Open-interest concentration (Dec contracts cheapen as their OI rises; R-squared 0.37 in one study),
   year-end/turn premium, FOMC-week premium, recent large single-month trades, convexity (3). "Contract richness follows the specific contract through time"
   (Dec cheap more often than not): judge by z, not by level.

### 5. Futures strip vs swaps (pack convexity RV)
1. Pack rate = average of the four contract rates. Matched swap = forward-starting 1y IMM swap on the CME-cleared curve (quarterly legs, same dates).
   `CA_obs = pack - swap` (bp). "Sell CA" = buy the pack, pay the swap. State the CCP: CA vs LCH looks wider than vs CME; use the CCP whose margin nets with the futures.
2. Model value: one-factor normal Ho-Lee `CA = sigma^2 x T1 x T2 / 2` (sigma normal short-rate vol per year in decimals, T1 start of the reference period = expiry for Euribor, T2 end of reference period; for SOFR/SONIA, which settle at period end, T1 = start is the usual approximation because the exposure builds across the period),
   sigma from caps/floors or listed-option normal vol. Ho-Lee over-corrects beyond ~2y; mean-reverting Hull-White differs most in Reds/Greens/Blues. Whites ~0-0.5bp, Greens 1.5-12bp.
   CA should rise monotonically with expiry. Constant-gamma estimates overstate CA (9.6 vs ~6bp in one example). Details: [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md).
3. Signal is `CA_obs - CA_model` (z over 3m and 1y), not raw CA. Model CA depends only on vol; gaps are positioning, CCP-margin and venue effects, so they can persist
   (Golds more persistent than Blues). Also monitor roll of the position (3m), CA-implied vol vs 3m realised vol, and cap-vol implied/realised.
4. Positioning reading: macro shorts/steepeners concentrate in futures (capital efficient), widening CA; a CA collapse = legacy shorts covered. CA minus model is inversely
   related to net speculative % OI; when positioning data are unavailable infer it from CA and the CME-LCH basis ([flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md), [spread-ccp-basis](../spread-ccp-basis/SKILL.md)).
5. Hedge the short-vol exposure with a weighted curve trade: regress model CA on curve factors (a 2s5s10s swap fly with weights ~(-0.70, 1, -0.46) fitted 10.2 + 21.4 x fly; or a
   futures steepener at DV01 ratio ~1:-1.18 for Greens, 0.74:-1 for Blues). Exclude the ZLB regime when fitting vol-vs-rates regressions. Short CA = short vol: flat-curve, vol-negative regimes support it.
6. Pick the pack that is already normalising, take profit when the gap to model is no longer extreme (even if still rich), respect event risk.
7. Pack/bundle vs swap RV without the CA lens: a 2y swap should sit close to the 2y bundle yield; residual = convexity, tenor basis (3s6s) and forward-start/stub mismatch, plus counterparty/CCP basis. Swaps to ~3y price off futures; after the Reds futures carry little information.

### 6. Intra-futures spreads
- **SR1 vs SR3 (CME ICS: 3 SR1 + 3 SR1 vs 10 SR3, 6 x 41.67 = 250.02 vs 250).** No basis: spread = slope/Fed timing + simple-vs-compound effect (0 at zero rates, ~3bp at constant 5%).
  Fair value `fair_sr1_sr3_bp(level, slope)`; trade only the deviation. Meeting-neutral ratio: `n_late = s_j/((d_post/d_total) x 41.67)`, `n_early = 25/41.67 - n_late` per SR3 ->
  2.9 + 3.1 per 10 for a 4-May meeting in the Mar-22 quarter, not 3 + 3. A meeting after the SR1 months cannot be hedged with them.
- **SR1 vs FF (SERFF) = pure secured/unsecured basis.** Price space basis = -(SOFR - FF): realised +10bp reads -10bp in futures. State the space. After 2023, SR1:FF is the cleanest, cheapest
  instrument for basis exposure; SR3:FF adds period/convention differences. Value with a path model (reserves, bills, month-end), compare month by month, and trade the expiry tied to the catalyst
  (debt limit, tax date, reserve-management pace). Do not read every SOFR spike as stress. Plumbing drivers: [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md),
  [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md). Examples: [references/worked-trades.md](references/worked-trades.md) section C.
- **FF vs 3m (overlap weighting).** FF BPV 41.67; total FF contracts = 3m BPV/41.67 allocated by days each FF month overlaps the 3m period (10/90, 30/90, ...). Backward-looking 3m FF OIS for June covers the same period as forward-looking March ED: trade 1:1.
- **Cross-currency futures spreads** (SOFR vs Euribor vs SONIA) replicate forward-starting FX swaps excluding the cross-currency basis; correlation falls as the basis grows.
  Z-score the slope difference at matched strip slots and compare meeting-implied paths ([xccy-basis](../xccy-basis/SKILL.md)).

### 7. Meeting-dated structures, turns and policy shape
- FOMC/meeting flies: gaps between meetings are tradable (pay/receive meeting spreads across ECB, BoE, RBA, Riksbank, BoJ). When the market prices more than the CB can validate, reaction risk is dovish;
  front-meeting selling pressure filters into later meetings; underweight the paid near leg for less front-meeting delta. Forecast months carry more probability (RBA ~3:1, ECB at worst 1.6:1), so no single
  meeting spread should be flat when the quarter prices hikes. Fair-value formulas and examples: [references/meeting-structures.md](references/meeting-structures.md).
- Year-end/turn: strip it before reading policy; Decembers are structurally cheap; use `ff_decompose` to split monthly FF futures into FOMC steps and a year-end premium (zero-FOMC-exposure weights).
- Size meeting trades by CB01 (sensitivity to that meeting), not DV01. Term-fixing futures (Euribor, legacy IBOR) carry a varying basis to the policy rate and RFR futures embed convexity and turns, so use meeting-dated OIS for probabilities.
- Fed-path ceiling: forwards "will struggle to price more than 70-80% of eventual hikes", so futures shorts have limited upside.

### 8. Futures against cash instruments
- **Strip to swap (hedge or RV):** bootstrap `DF_i = 1/(1 + R_i d_i/360)`, `CDF_i = prod DF`, `fixed = sum(CDF_i R_i d_i/360)/sum(CDF_i d_i/360)`; strip hedge by bump-and-reprice (each future +0.01, hedge = dPV/25).
  Counts decline along the strip. Edge vs a dealer quote is a fraction of a bp (0.1-0.3bp on a 2y). Margin: futures IM USD 570k vs 1.57mm for the swap (~36%); hedge and swap margined separately 2.14mm vs 46k portfolio-margined (~98% lower) (CME example).
  Hedge-error sources: end-date mismatch across a meeting, date mismatches (a Dec contract against a 2-Dec-28-Feb deposit over-hedged >100%), compounding vs simple, payment delay, margin interest.
- **Tailing:** `N_tailed = N/(1 + R0 D/360)` with D = calendar days from today to the future's expiry (daily-settled P&L grows by that factor before the exposure date); imperfect (today's rate), re-adjust; matters at high rates.
- **Strip vs Treasury:** if a Treasury is financed at SOFR, its fair ASW vs SOFR is zero; mismatches are 3m vs 6m pay, ACT/360 vs ACT/ACT, payment delay. Works while ASW is stable ([spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md)).
- **Term TED:** strip yield minus bond-future implied yield (CTD price = F x CF, yield at delivery date); pairs 2y note vs 2y bundle, Schatz vs 2y Euribor bundle, Bobl vs 5y bundle. A credit spread like the swap spread; fill the least liquid leg first; avoid the front month ([fut-invoice-spreads](../fut-invoice-spreads/SKILL.md)).

### 9. Execution and microstructure
- Leg in; never leg a closing spread; "the first cut is always the cheapest". Lean on implieds but do not trade against purely implied prices; they vanish when needed.
  Do not autospread the front month. Netting a spread matrix on paper first finds the cheapest route (same near leg or same far leg).
- Packs, bundles and flies usually quote tighter than implied; Liffe-style quotes add leg changes (4x a CME average): normalise.
- Exchange-rebate tiers change profitability ([bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md)). Sit out FOMC/ECB days and inflation prints for micro-structures; IMM roll jumps in portfolio DV01 are expected.
- Euribor opens 07:00 GMT with no leading indicator; the 2y government future leads the strip; at a crossed Schatz market the Schatz spread can jump a futures tick (0.25-0.5bp vs 0.1bp swap tick): post bids in preferred Euribor contracts.

## Worked example
**Micro-fly roll screen (Euribor, one snapshot).** Prices 1st-12th 96.44, 96.70, 96.94, 97.135, 97.285, 97.39, 97.46, 97.50, 97.525, 97.545, 97.55, 97.56
(Clarus Financial Technology, A Dummies Guide to Trading Interest Rate Swaps, 19 Jun 2024). Rates = 100 - price. Fly (rate space) for belly slot k = `100 x (2 r_k - r_{k-1} - r_{k+1})`:
2nd -2.0, 3rd -4.5, 4th -4.5, 5th -4.5, 6th -3.5, 7th -3.0, 8th -1.5, 9th -0.5, 10th -1.5, 11th +0.5 (the source's price-space microfly has the opposite sign). Long-belly roll over 3m
= `fly_k - fly_{k-1}`: 11th +2.0 (best buy), 8th +1.5, 3rd -2.5 (best sell), 10th -1.0. Buying the 8th earns 1.5bp if the curve is static (`micro_flies` reproduces them). The source buys the 9th and 11th, sells
the 3rd and 10th, so it also weighs level and z; roll alone also flags the 8th. "This is not an arbitrage strategy": edge is a few bp, bid/offer is 2bp round trip, so leg in and size by the fly z.

**Strip to 2y IMM swap, receive USD 100mm.** SR3 prices Apr 2025 (91-day periods): 95.895, 96.290, 96.605, 96.815, 96.940, 96.985, 96.965, 96.910 -> rates 4.105 ... 3.090; discount factors from `1/(1 + R d/360)`;
`sum CDF R d/360 = 0.0647505`, `sum CDF d = 699.926` (annuity x 360) -> swap 3.3304% = 100 x 0.0647505 x 360/699.926 (dealer 3.3275/3.3325; client receives 3.3275, edge 0.29bp; `strip_swap_rate`). Hedge: SELL 779 contracts (100, 99, 99, 98, 97, 96, 95, 95); a -1bp
bump gives dPV 19,480.69 vs 779 x 25 = 19,475. Convexity P&L of receive swap vs 779 short: +253 at -10bp, +1,451 at -25bp, +5,638 at -50bp, +22,292 at -100bp; at -100bp DV01 rises 19,480 -> 19,921, hedge 779 -> 797
(CME Group, Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures, 4 Jun 2025).

**Sell Blues convexity, hedged (Citi, 9 Feb 2017).** Buy 2,000 each of the Mar-20..Dec-20 ED contracts, pay USD 2bn matched CME swap at 8.8bp; hedge: pay belly of the 2s5s10s swap fly (147mm / -85.6mm / 20.89mm at 0.705/-1/0.465
DV01) at -18.2bp. CA was ~4bp (~2 sigma) wide to the model and ~3bp wide to the fly; target +600k, stop -350k, carry +380k/3m, CA roll +1.3bp/3m. Closed 6 Jun 2017 CA 6.6bp, fly -16.5bp: +500k after costs
(Citi Research, North America Rates Trade Idea: Sell Blues convexity adjustments, hedged, 9 Feb 2017; Turning Green from Blue on short convexity, 6 Jun 2017). The SOFR-era rerun (17 Feb 2023) sold the Mar-26..Dec-26 pack at 12.7bp vs model 9.44
(Citi Research, US Rates Weekly: Time for moderation, 17 Feb 2023). More cases (spline table, CA monitor, SERFF, G10 meeting spreads, TED, strip vs UST): [references/worked-trades.md](references/worked-trades.md).

**FOMC-neutral SR1 hedge.** Long 10 Mar-22 SR3, hike effective 5 May 2022 (41 of 91 days post): `s_j = 25 x 41/91 = 11.26`; May SR1 sensitivity `(27/31) x 41.67 = 36.29` -> sell 3.10 May + 2.90 Apr SR1 per 10 SR3 vs the
standard 3 + 3 (Huggins & Schaller, SOFR Futures and Options, 2022; `sr1_hedge_for_sr3`).

## Signals & interpretation
| Lens | Starting threshold (recalibrate per market) | Action / meaning |
|---|---|---|
| Fixed-contract fly z (65d) | `abs(z) >= 2` | candidate fade; belly cheap (z > 0) -> receive belly |
| Risk-adjusted roll | `fade_roll / vol20_ann >= 0.3` | carry must not fight the fade |
| OU half-life of fly (trading days, ~120d window) | <= 90 days | slower than that is not a fade |
| Spline residual z (1y) | `abs(z) >= 3` (e.g. Dec +3.2, Sep -3.1 on one date) | contract rich/cheap to neighbours; confirm with moved nodes |
| Regression residual | sign: spread negative = flat; fly negative = belly rich; z >= 1.5 on 1y (judgement, not sourced) | corroboration only |
| CA - model (pack) | >= ~2 sigma and z(1y) >= 1.5; model gap >= ~2-3bp | sell CA if gap normalising; stop ~2.5bp wider; target 4bp tighter |
| SR1-SR3 vs fair | gap > ~1bp (CME ratio error < 1bp) | Fed-timing / compounding view |
| SERFF forward vs path model | gap > ~1.5-2bp on a catalyst-dated month (judgement; sources quote ~1bp gaps as actionable) | basis view; state price/rate space |
| Blackouts | 5d around FOMC (use CB date), 3d around IMM roll | no new entries; take profit once structure can be priced into expiring legs |
Confirmations before entry: (i) two lenses agree; (ii) not a calendar artefact (tilted fly); (iii) cost < 1/2 of expected move; (iv) a related structure in the swap/FRA
market agrees (crisis rule: only the simplest trades can be implemented); (v) no pending event that can re-price the micro-curve. Exit: target, stop, or time (roll horizon); take profit early when a better
dislocation appears; take profit on flies as expiry approaches and the market can price the policy structure into the contracts. Targets/stops from sources: 4bp / 2.5bp (Blues CA 2023); +600k target / -350k stop on a 2bn Blues position (2017);
fly -8 target / +10 stop (ING 2-6-15, 2020). Fading: "you never fade at fair value; you fade a deep ... value".
Crowding: when consensus structures (Z/Z flatteners, CS-vs-P) are crowded, expect stops; gap/kink trades are short vol (you sell the tail of a sudden stop). Hand composite ranking to
[rv-composite-scoring](../rv-composite-scoring/SKILL.md) and z/half-life details to [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md) and [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md).

## Pitfalls
- Sign: price-space vs rate-space flies and spreads have opposite signs; SERFF futures basis = -(SOFR - FF); "buy fly" = pay belly; condor sign follows the fly (body cheap = positive). State the space.
- Structures are still directional: fly weights, 3m vs 1y curvature, PCA-neutral weights reduce not remove exposure. Always report residual beta to level/slope/belly.
- Flies are partly calendar artefacts (meeting layout vs IMM grid); weekend/holiday fixings carry multi-day weight in compounded periods and can dominate short-dated pricing.
- SOFR contracts fixed in arrears: the front contract's vol decays; 1m SOFR/FF are arithmetic, 3m SOFR compounded (compounded > averaged; r^2(n-1)/720 = 0.67bp for 31d at 4%, larger than a FF half-tick). Do not mix 1m and 3m in one bootstrap.
- Futures are not unbiased forecasts: convexity ordering forward < Euribor-style < average < compounded; convexity-adjust before comparing with OIS forwards; year-end/Japan-April turn stripped before reading policy.
- Strip-vs-swap "arbitrage" is usually 3s6s tenor basis plus forward-start mismatch plus CCP/venue/margin; theoretical forwards depend on curve construction; step-fit residuals are not arbitrage; prefer chained-zero comparisons.
- CA signal is CA minus model, not raw CA; CA - model can persist; pick the normalising pack; Ho-Lee over-corrects beyond ~2y; CME vs LCH reference; margin-funding costs and split clearing can make the bias negative (EUR 2013).
- Short CA is short vol; a 6th/16th-contract steepener hedge of model CA fails at the ZLB; unhedged it loses when futures shorts build further.
- Crowded micro-curve trades gap against you; Dec/Sep contract effects follow the specific contract and OI; spline dislocations should fade with expiry.
- Liquidity: concentrated in 2nd-3rd quarterlies; implied-only prices vanish; ISV systems may count spreads as two outrights while the exchange margins at ~25%; volume is not liquidity; do not aggregate venue books.
- Regime breaks (LIBOR -> SOFR, standing repo facility, ED expiry Jun 2023): re-estimate everything; small samples (event studies of 5 cycles, <25 events of the 6th-minus-1st fed funds future spread) are anecdotes with no costs.
- Meeting-date basis: a hedge whose averaging window spans a meeting needs stacking into the prior month; the standard 3+3:10 is not FOMC-neutral for off-centre meetings.
- Do not trust single-snapshot spot vs forward gaps (stale feed); repeat over several days. Settle and close snaps differ 0.2-0.9bp: never answer a close question with a settle.
- Market-specific: AUD/NZD bank-bill futures have non-IMM expiry, are priced 1/(1+dR) so BPV is rate-dependent (about 24, not the constant 25 of IMM contracts) and older sources describe an AUD deliverable-bill option: read settlement and BPV from `fut_static`; Euribor term futures expire at the fixing; SEK/NOK futures are thin: price policy with meeting-dated OIS (SWESTR, NOWA); JPY futures illiquid beyond Reds; CAD month-end turns can round-trip 40bp (FXOIS +20/-20).

## Output
A table per candidate, ranked by `fade_roll / vol` after confirmations:
`structure | legs (fut_id, weight, contracts) | level (bp, rate space) | z 65d / 1y | residual vs fit and vs regression | calendar-tilted level | roll (bp/3m) | $ roll and carry | risk-adj roll | half-life | package DV01 ($/bp) | cost (round-trip bp) | liquidity (vol, OI, bid/ask) | drivers checked (OI, turn, meeting, CA) | hedge | target / stop | blackout flags | data quality`.
Plus: the strip chart (rates and spline fit), fly/roll heat-map, and for packs a CA-vs-model panel (CA, 1w change, 3m/1y z, vs model, roll, CA-implied vs realised vol). State the
space (rate/price), CCP, snap, window and parameters. Hand off the chosen structure to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) and cost/slippage to
[bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md).

## Scripts
- [`scripts/stir_structures.py`](scripts/stir_structures.py): spreads/flies (condor = adjacent flies summed), micro-fly table with roll, pack/bundle yields, strip-to-IMM-swap rate, SR1 meeting-neutral hedge for an SR3, fair SR1-SR3 spread, Ho-Lee CA,
  meeting weights and calendar-tilted fly, FF futures FOMC/year-end decomposition, regression-residual monitor, package cost, and a fixed-contract fly screen from a `stir_quotes` file.
  `python scripts/stir_structures.py --help`. `--selftest` checks published cases (micro-fly rolls, pack/bundle yields, 3.3304% swap, 2.9/3.1 SR1 hedge, fair SR1-SR3 table, FF decomposition) and exits non-zero on failure.

## Related skills
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): CA models and vol dependence behind pack-vs-swap RV
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): meeting probabilities and paths behind meeting-dated structures
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): compounded/averaged reference periods and fixing-risk ladders
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md), [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): SOFR-FF drivers
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md), [curve-conditional-trades](../curve-conditional-trades/SKILL.md): option cross-checks and conditional versions
- [curve-butterflies](../curve-butterflies/SKILL.md), [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md), [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md): weighting, PCA residuals, directionality
- [fi-curve-construction](../fi-curve-construction/SKILL.md), [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md), [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [fut-calendar-roll](../fut-calendar-roll/SKILL.md): curves, conventions, roll
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md), [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md), [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md), [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): futures vs cash/swap
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md), [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md), [rv-composite-scoring](../rv-composite-scoring/SKILL.md): screening and ranking
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md), [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md), [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-devils-advocate](../rv-devils-advocate/SKILL.md): positioning, costs, write-up, pre-mortem
- [xccy-basis](../xccy-basis/SKILL.md), [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): FX-implied STIR spreads and convexity value
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md), [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md), [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): bills vs OIS legs, turn/seasonal effects, midcurve and option expressions
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md): forward-grid RV, kinks and aged forwards.
- [quant-cointegration](../quant-cointegration/SKILL.md): cointegration tests and level hedge ratios.

## References
- Huggins & Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley Finance, 2022): SR1/SR3 settlement, in-period front, roll timing, SR1-SR3 fair values, FOMC-neutral ratios, jump/diffusion fair value, curve fitting, SR3:ED/SOFR-FF basis, strip vs OIS/Treasury hedges.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012), with Welcome to STIR futures forum posts and blog (2006-2014; "The disappearing convexity bias", 16 Dec 2013): calendars, matrix, flies, packs/bundles, implied pricing, TED, fly-fading practice.
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): colour packs, RFR futures settlement, order-book mids, IMM strip length and knots, FCA sizes, turns, roll-down caveats.
- Darbyshire - Coding Interest Rates (c.2024): step curves on effective dates, regularisation with zero-priced flies, turns, Fed-delay roll scenario.
- CME Group - Pricing and Hedging USD SOFR Interest Rate Swaps with SOFR Futures (Rogerson, 4 Jun 2025): strip bootstrap, hedge ladder, convexity P&L, margin.
- CME Group - Short-Term Interest Rate (STIR) Futures Inter-Commodity Spreads on Globex (Apr 2024): ICS ratios, quote convention, FF/SR3 example.
- Citi Research - US Rates Weekly: Going nuclear (on the curve) (3 Feb 2017): spline kink method, OI regression, per-contract CA.
- Citi Research - US Rates Weekly (2018-2023: What to expect when you're expecting a turn, The rocky road to a steeper curve, All it takes is a little push, Eat, pay, spend, Time for moderation, OAT of the blue): curve/fly monitors, PCA weights, systematic micro-curves, final-hike study.
- Citi Research - North America Rates Trade Ideas and Vol Lab (2017-2018, 2023): Sell Blues convexity adjustments hedged; Turning Green from Blue; Value in Greens convexity; Short Blues convexity via futures/swaps: CA trades, hedge regressions, closes.
- Citi Research - US Rates Weekly: Fixing the plumbing (30 Sep 2019) and Pension plan for 20s? (9 Oct 2026): FF year-end decomposition; SOFR curve trades and Blues CA vs EUR vol.
- Citi Markets (Sales & Trading) - STIRT Weekly (7, 14, 21 Aug 2026) and Short End $waps: Fading the July Premium (23 Jul 2026): G10 meeting-spread views, FOMC fly weighting.
- Citi Research - Short-End Notes: SOFR/FF to go negative in Q3/Q4 (13 Jun 2025) and SOFR/FF spiking into quarter-end (27 Jun 2025); BofA Global Research - US repo sensitivity (8 May 2025): SOFR-FF path models.
- Conks (Monetary Mechanics) - SOFR/FF primer (10 Jun 2026), Plumbing Notes 2024-2026: SERFF construction, sign convention, calendar reading, example views.
- J.P. Morgan - Interest Rate Derivatives (3 Aug 2018, 14 Sep 2018, 12 Jul 2019, 26 Feb 2020, 7 Feb and 6 Mar 2020): pack mean reversion, ED flies, turns from futures spreads, SER vs FF.
- ING Global Markets Research - EUR crisis trades: let's get tactical (3 Mar 2020) and March ECB: taking out the ECB put (12 Mar 2020): PC1 residual bands, PC1-neutral fly, DV01-weighted spreads.
- Clarus Financial Technology - A Dummies Guide to Trading Interest Rate Swaps (19 Jun 2024), Mechanics and Definitions of Carry in Swap Markets (16 Jan 2019), Mechanics of FRA Risks (4 Sep 2018), Mechanics and Definitions of Short Term Interest Rate Futures (6 Jul 2016), CME-LCH Basis: Convexity in Eurodollar Futures (1 Jul 2015): microfly roll, stub hedging, contract facts.
- Heitfield & Park - Inferring Term Rates from SOFR Futures Prices (Federal Reserve Board FEDS 2019-014, Feb 2019): step-function fit, futures vs OIS gaps.
- Henrard - Overnight Futures: Convexity Adjustment (OpenGamma, 2018) and Interest Rate Futures and their Options (2012); Rosen - Averaged Overnight Rate Futures: Convexity Adjustment (FINCAD, 2019): CA sizes and HW closed forms.
- Tuckman & Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): averaging-contract hedge ratios, stacking, tailing, convexity ordering.
- Bocconi Students Investment Club - Understanding Convexity Bias in STIR Futures Markets (29 Mar 2026) and Quantitative Finance Stack Exchange Q&As on STIR convexity adjustment (Jun 2025, Jul 2023): Ho-Lee CA, stringing, futures liquidity beyond Reds.
- Lehman Brothers - The Short-End of the Curve (10 Jul 2007); swapsball.net - Central bank decisions and inflation forecasts (8 Mar 2018): CB01 sizing, forecast-meeting odds.
- Nomura - Conditional Euribor bull flatteners (19 Jun 2014); Goldman Sachs - Global Rates Trader: Reaching Limits (2 Oct 2026); Barclays Research - Global Rates Weekly: The urgency question (2 Oct 2026); JWS Macro (Substack, 2025-2026): option-conditional flattener, AUD flattener, crowded Euribor/SOFR strip trades.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): 6th-minus-1st fed funds future signal and 1s2s independence.
- Ho & Lee - Term structure movements and pricing interest rate contingent claims (Journal of Finance, 1986) (external): Ho-Lee model behind CA = sigma^2 T1 T2 / 2.
- Burghardt, Belton, Lane & Papa - Eurodollar Futures and Options: Controlling Money Market Risk (1991) (external): classic reference on strip pricing and futures-vs-forward mechanics.
