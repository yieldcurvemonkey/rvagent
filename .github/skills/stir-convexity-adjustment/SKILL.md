---
name: stir-convexity-adjustment
description: Size and trade the futures-vs-forward convexity adjustment (CA, convexity bias) in STIR - the gap between futures-implied rates (SOFR SR3/SR1, SONIA, Euribor, CORRA, SARON, TONA, bank-bill futures) and matched FRA/OIS forwards. Covers Ho-Lee and Hull-White fair CA, CA-implied vol vs realised, the pack CA monitor (Reds/Greens/Blues/Golds vs forward CME swaps), gamma/option replication, CME vs LCH and margin effects, positioning drivers, and short/long-convexity RV trades with vol hedges. Use when asked about convexity bias or adjustment, futures/FRA or futures/swap basis, "is Blues CA rich to model", CA-implied vol, sell or buy convexity, ED/SOFR pack vs matched swap, CME-based CA, or whether a futures strip can be compared with swaps or bootstrapped without adjustment.
---

# STIR futures convexity adjustment (CA)

Futures settle every day at a constant value per bp; FRAs and swaps are discounted, so their value per bp changes with the
rate level. Receiving a swap against short futures is long gamma and makes money when rates move either way. The market
pays for that with a futures rate above the matched forward. That gap is the CA. It has a model fair value that depends
on rate vol and time to expiry only (so it is a vol quantity), plus a market residual driven by positioning, margin and
clearing frictions. This skill measures the CA correctly, compares it with fair value, and decides whether the residual is
a trade. Measure first: most "CA signals" are convention errors (annual swap leg, wrong snap, wrong CCP curve).

## When to use
- Comparing a futures strip with swap/FRA forwards, or bootstrapping a curve from futures (adjust first, see Method 7).
- "Is the Blues/Golds CA rich or cheap to model?", CA-implied vol vs realised vol, CA roll-down, CA z-scores.
- Structuring a sell-convexity (buy pack, pay matched swap) or buy-convexity trade, sizing, hedging its vol exposure.
- Interpreting why futures cheapened to swaps (positioning vs vol vs CCP basis).
- Not for: bond futures delivery options (`fut-*`), SR3 vs SR1 reference-period mechanics beyond CA
  ([stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md)), pure strip spread/fly RV
  ([stir-futures-rv](../stir-futures-rv/SKILL.md)).

## Conventions (state them in every output)
| Item | Convention |
|---|---|
| CA | futures rate minus matched forward rate, in bp, positive. FRA/forward rate = futures rate - CA. Futures price = 100 - rate, so futures price is below the forward price |
| Pack | 4 consecutive quarterly contracts; pack rate = arithmetic mean of the 4 rates (100 - price); DV01 = 4 x contract bp value (USD 25/bp per SR3 contract, so 100/bp per pack) |
| Pack CA | pack rate minus the matched forward swap par rate, same CCP, quarterly fixed and quarterly floating legs, start = first contract's reference start, end = 12 months later |
| "Sell / short convexity" | buy futures (pack) + pay fixed on the matched swap. Profits if CA tightens. Short vol. "Buy / long convexity" = sell futures + receive the swap |
| Vol | normal (Bachelier) vol in bp per year. Never lognormal |
| Time | years ACT/365 to the contract's reference start (T1); T2 = T1 + 0.25 |
| Colours (USD) | Reds/Greens/Blues/Golds = years 2-5 of the strip. Blues = pack starting about 3.1y out (rank 13), Golds about 4.1y (rank 17). Name the pack by its contracts (e.g. H6-Z6) |
| Curve | always name the CCP of the swap leg (CME or LCH). CA vs LCH is wider than vs CME |

## Inputs (data-agnostic)
Canonical tables: see [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) and its `schemas.md`.
- `stir_quotes` (snap = `settle` only, never an end-of-day snap: the futures settle about 15:00 New York, and a 17:00 snap
  against a settlement-time curve injects about 1.8bp/day of noise on near packs) and `fut_static` (`ref_start_date`,
  `ref_end_date`, `ref_method`, `bp_value_ccy`). The SR3 month code is the START of the reference quarter but the contract
  expires at its end, a quarter later (legacy ED expired in its code month); mixing the two shifts dates by a quarter. Use
  `ref_start_date`, not the code (FactSet, Interest Rate Future white paper, 2023).
- `curve_zero` (discount factors) for the matched swap. Do not read the matched swap from `curve_par` when the stored
  USD fixed leg is annual: an annual leg raises the swap rate by about 3q^2/8 (3.4bp at q = 3%, 9.4bp at 5%; Citi quote 4-12bp), which
  understates CA and is not convexity (Citi, NA Rates Trade Idea: Turning Green from Blue on short convexity, 6 Jun 2017). Use
  `par_from_dfs` in [scripts/convexity_adj.py](scripts/convexity_adj.py).
- `vol_surface` (product `capfloor`, ATM normal vol at the pack's mean expiry) or `opt_quotes` (listed STIR option
  `nvol_bp` where liquid, through early Greens; cap/floor vol beyond) (J.P. Morgan, A better way to sell vol, 3 May 2017).
  State the vol source: option-implied and cap-implied vols give different fair CAs.
- `positioning` (CFTC-style, lag to `pub_ts_utc`: Tuesday data are public Friday 15:30 New York), `ccp_basis`, `rate_fixings`.
- History: 1y of daily pack CA for 1y z-scores (3m = 63 trading days, 1y = 252), 3m realised pack vol.
- If any input is missing, ask the data adapter / user. Never invent a vol or a swap curve.

## Method

### 1. Fair CA: choose the model and the form
Ho-Lee (dr = theta dt + sigma dz): futures - forward = `sigma^2 * T1 * T2 / 2` for the continuously compounded forward
rate (Hull). With sigma = 120bp, T1 = 8, T2 = 8.25: 0.5 x 0.012^2 x 8 x 8.25 = 47.52bp (Hull textbook check).
Three forms are in use; they differ by 8-17% at Blues, so state which one:

| form (`form=`) | CA per contract | reproduces |
|---|---|---|
| `T1sq` | sigma^2 T1^2 / 2 | the sell-side pack screens (zero-accrual limit of Citi's formula) |
| `T1T2` | sigma^2 T1 T2 / 2 | Hull, Tuckman-Serrat Table 12.12 (term-rate row), BSIC, J.P. Morgan |
| `simple` | sigma^2 (T2^2 - tau^2/3) / 2 | exact Gaussian for compounded-in-arrears SR3-style payoff (tau = 0.25) |

Citi's full form is `CA = (Fwd + 1/D) * [exp(sigma^2 T D (D + T/2)) - 1]`, D = 0.25, whose D -> 0 limit is
`sigma^2 T^2 / 2` (Citi, Rates Vol Lab: Left-side vols' outperformance, 22 Jun 2021). It ignores skew and
forward-rate correlation ("small in practice").
Default for a pack screen: `T1sq` with the sigma from cap/floor (or option) vol at the pack's mean expiry, because it
is what published monitors use and lets you check your numbers against them. Use `simple` or Hull-White for absolute
fair value in a curve build. Table (Ho-Lee `T1sq`, per contract, bp):

| sigma \ T1 (y) | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 80bp | 0.3 | 1.3 | 2.9 | 5.1 | 8.0 |
| 100bp | 0.5 | 2.0 | 4.5 | 8.0 | 12.5 |
| 150bp | 1.1 | 4.5 | 10.1 | 18.0 | 28.1 |

Properties to test any implementation against: CA = 0 if sigma = 0; scales with sigma^2 (double the vol, 4x the CA)
and about T1^2 (log-log slope of CA on T1 near 2); monotonically rising with expiry; whites 0-0.5bp, greens 1.5-12bp
(Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022). Work in decimals internally: 100x unit
errors are the classic CA bug.

Hull-White (mean reversion a): `CA(T1,T2) = [B(T1,T2)/(T2-T1)] * [B(T1,T2)(1-exp(-2aT1)) + 2a B(0,T1)^2] * sigma^2/(4a)`,
B(s,t) = (1-exp(-a(t-s)))/a; a -> 0 gives Ho-Lee. HW < Ho-Lee for any a > 0, similar at the front, diverging in
reds-greens: "using the simpler Ho-Lee beyond two years will systematically over-correct" (BSIC, Understanding Convexity
Bias in STIR Futures Markets, 29 Mar 2026). Calibrate (a, sigma) by least squares to ATM normal caplet vols,
sigma_HW(T) = sigma B(0,T)/T as printed by BSIC (close to the exact sigma sqrt((1 - exp(-2aT))/(2aT)) for aT below about 0.3).
If the minimum is unstable, fix a (3% is a common choice) and solve for sigma (West,
Interest Rate Derivatives lecture notes, 2010). One factor is enough for a screen; a strict treatment needs
intra-curve correlation (two factors) and one-factor "will slightly overestimate" (Quantitative Finance Stack Exchange,
SOFR futures options, 2023). Derivations, Tuckman/Henrard variants and the overnight-futures forms are in
[references/models.md](references/models.md).

Ordering of futures rates over the same forward (Jensen): compounded-rate futures (SR3) > average-rate (SR1, Fed funds)
> term-rate (Euribor-type) > forward (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022). The average-vs-compounded gap is at most about 1/3bp even at 5y (Rosen, 2019).

### 2. Mechanism, so you know what moves it
- Gamma view (preferred). The swap has gamma, the future has none. CA = upfront value of the gamma P&L of the
  delta-hedged package until both expire. Expected P&L ~ `0.5 * (sigma*sqrt(T))^2 * Gamma`, divide by futures DV01
  for bp. It is not about reinvesting margin: a collateralised FRA has the same reinvestment pattern (Quantitative Finance
  Stack Exchange, "Why are FRA/futures convexity adjustments necessary?", 2019-2025).
- Most FRA convexity comes from the OIS-discounting sensitivity, not discounting over the accrual period (same source).
- Short CA = short a delta-hedged straddle: positive roll (theta) against hedge losses. Held to maturity,
  `E[P&L] = E[ integral (T - t)(sigma_implied^2 - sigma_realised^2) dt ]` (Citi, Left-side vols' outperformance, 22 Jun 2021).
- Financing-bias view (Huggins and Schaller, SOFR Futures and Options, 2022): the sign of the futures-forward gap depends
  on the correlation of futures price with the margin rate; whether it matters depends on whether the price-setter
  actually earns margin interest. Treat the size as empirical.

### 3. Measure the pack CA (the only daily series worth monitoring)
1. Pack rate = mean of the 4 settle rates (100 - price) of consecutive quarterly contracts.
2. Matched swap par from `curve_zero`: `par = (DF(T0) - DF(T4)) / sum_i d_i DF(T_i)`, quarterly ACT/360, T0 = first
   contract's reference start. `CA_bp = 100 * (pack_rate_pct - par_pct)`.
3. Same CCP curve for the whole history; CME for a trade done against CME futures (margin netting).
4. Controls before trusting a series (run on every date):
   - Zero-convexity control: recompute with the swap curve's own IMM forwards instead of futures. Result must be about
     0 on a flat curve; on a sloped curve the equal-weighted mean of forwards exceeds the DF-weighted par by the
     slope tilt (0.38bp for forwards rising 3.0 to 4.0% over the year, `scripts/convexity_adj.py`). Compare against that
     tilt, not against zero, because CA levels are 1-5bp.
   - No-arbitrage sign: CA >= 0. A negative value is usually a stale deferred settle. Passing is not enough: a k-day-stale
     quote books zero P&L for k days then a jump, which manufactures a low-vol, fat-jump series. Detect staleness on the
     raw price panel.
   - Shape: log-log slope on T1 about 2, correlation of CA with T1^2 near 1 across packs.
   - Curve resolution: if the discount curve has no node inside the window, interpolated forwards are identical and the
     control passes trivially. Skip such dates. A curve-derived futures rate is poor at the front (error 15.8bp on ranks
     1-4 in an internal test) and fine deep.
   - Gate the swap leg as well as the futures leg: a junk swap leg gave CA < 0 on 93% of days in one internal test.

### 4. CA-implied vol and the monitor columns
Invert: `sigma_impl = sqrt(2 * CA / mean_i(T1_i^2))` (bp, CA in 1e-4 units; `implied_vol_bp`). Compare with:
3m realised pack vol (bp/day x sqrt(252)), and cap/floor implied vs realised. Per 1y pack the standard screen
(Citi, Rates Vol Lab: Short Blues convexity via futures/swaps, 21 Feb 2023) reports:
CA (bp), 1w change, 3m z, 1y z | model CA | CA - model, 3m z, 1y z | 3m roll for short convexity (bp) | CA-implied vol |
realised vol | implied/realised | cap vol implied/realised. Use packs from the Reds out: front packs divide by a tiny T1^2
and invert to 700bp+; `d sigma / d CA = sigma / (2 CA)` sets the minimum usable rank given the CA noise.
Per-contract version: theory says CA rises monotonically, so a contract with CA (or CA - model) above its longer
neighbour is cheap to the interpolated neighbours. Persistent by contract (December cheap, September rich), so judge by
z-score and treat it as RV only (Citi, US Rates Weekly: Going nuclear (on the curve), 3 Feb 2017).

### 5. Decompose the residual (vol vs positioning vs funding)
`CA - model` is what the vol-driven model cannot explain. Attribute it before trading:
1. Vol: CA moves with model CA. Part of any widening is justified by higher vol. The signal is the divergence, not the level.
   "CA rose while vols fell" points to a technical, not a vol, driver (Citi, Left-side vols' outperformance, 22 Jun 2021).
2. Positioning: asset managers and leveraged funds express rate views short in listed futures, dealers take the other
   side and hedge by paying swaps, so dealers are structurally short convexity; record dealer ED longs widened CA.
   Monthly change in Blues CA-vs-model on change in dealer net ED positioning, 2014-2017: R^2 = 0.32, positive slope
   (Citi, US Rates Weekly: Swearing in huge expectations, 13 Jan 2017). A 3y beta of excess CA on dealer net position peaks
   at 2-3y forward (beta about 0.85, correlation 80%+) (J.P. Morgan, 3 May 2017). In the SOFR era the CA-vs-model spread was inversely
   related to asset-manager net futures position (% of open interest); the link broke in Oct 2026 (Citi, US Rates Weekly:
   Pension plan for 20s?, 9 Oct 2026). Early-January corporate issuance (swap receiving) also widens CA seasonally (Citi, Swearing in huge expectations, 13 Jan 2017). Positioning data lag: when absent, read the CA itself as a gauge (a collapse to
   model after 2018 = legacy shorts covered) (Citi, Rates Focus: Shorts increasing?, 16 Jan 2019).
3. Vol lagging yields: the residual of 3y1y implied vol regressed on the rate level is inversely related to CA - model
   (Citi, US Rates Weekly: Time for moderation, 17 Feb 2023).
4. Funding/CCP: excess CA is compensation for initial margin on otherwise riskless legs, worse when legs sit at different
   CCPs. Implied funding spread = excess CA / IM; at a fixed spread, excess CA scales linearly with IM
   (J.P. Morgan, 3 May 2017). Convexity is tradable between CME futures and FRAs only if the swap is cleared at CME with
   portfolio margining (Clarus Financial Technology, CME-LCH Basis: Convexity in Eurodollar Futures, 1 Jul 2015). Futures
   margin period is 1 day versus 5 for swaps, and portfolio margining cut initial margin by about 98% in CME's example
   (CME Group, Pricing and Hedging USD SOFR IRS with SOFR Futures, 4 Jun 2025). See
   [spread-ccp-basis](../spread-ccp-basis/SKILL.md).

### 6. Trade construction and sizing
Short convexity (sell CA), the standard package:
1. Buy N packs (each of the 4 contracts N times); pay a matched forward swap on the same CCP, quarterly/quarterly, notional
   `= DV01_target / (1e-4 * forward annuity)`. USD 100k DV01: 1,000 packs and about USD 1.0-1.2bn swap (forward annuity
   about 0.85-0.99 for 1y swaps starting 1-3y out; Citi traded 1.17bn at about 3.2y out).
2. P&L ~ `(CA_entry - CA_exit) x DV01`, plus running carry = 3m roll of the CA (0.7-1.7bp per 3m in Citi's trades).
3. Vol hedge (optional). Fair CA is directional with implied vol and front-end vol correlates with curve shape, so an
   unhedged short CA is short vol. Hedge by regressing model CA on curve factors, e.g. Blues CA on a 2s5s10s swap fly:
   `CA = 9.7 + 20.6 (-0.705 y2 + y5 - 0.465 y10)` (CA in bp, swap yields in %, belly-positive fly; Citi, NA Rates Trade Idea: Sell Blues convexity adjustments, hedged,
   9 Feb 2017); hedge = pay the belly, residual CA - fitted fly is the convergence signal. Greens: ED5/ED9 steepener with
   DV01 weights 1 / -1.18 (Citi, Turning Green from Blue, 6 Jun 2017). The curve hedge fails at the zero bound and
   carries a market bias (front-end vol is directional with rates). Caution: an internal SOFR 2020-24 replication found the
   fly hedge did not reduce risk (hedge R^2 0.00-0.01, sign-flipping beta, variance reduction positive in 15.8% of
   1,890 fly-hedge combinations), so validate the hedge on your own data before sizing it.
4. Alternative hedge: sell a cap/floor or straddle of matching expiry (Blues CA ~ 3y1y). Carry is lower
   (USD 65k vs 206k per 3m on 100k DV01 in Jan 2017).
5. Costs: breakeven was 1.2-1.6bp per leg versus 0.25bp assumed in an internal backtest; a round-trip cost of 1bp halved
   the P&L and 2bp removed it. Execute as a package at the CCP's settle.
Long convexity (buy CA): sell packs + receive the swap. Rationale: CA is the option premium and the swap's convexity the
gamma; it pays only if realised moves exceed the breakeven embedded in CA (Citi, Pension plan for 20s?, 9 Oct 2026).

### 7. Using CA in curve building
Adjust futures forwards before comparing with swaps or bootstrapping: `forward = futures rate - CA`. The 1m average
contract and OIS payment-lag effects are negligible (below 0.1bp and about 1/400bp); the 3m compounded CA is not (Rosen,
Averaged Overnight Rate Futures: Convexity Adjustment, 2019; Henrard, Overnight Indexed Swaps ..., 2004). Workflow:
(1) bootstrap a pre-curve ignoring CA, (2) calibrate Ho-Lee/HW to cap or option vol, (3) compute CA by contract,
(4) re-bootstrap with `forward = futures - CA` (Quantitative Finance Stack Exchange, SOFR futures options, 2023). Do not
mix 1m and 3m futures in one bootstrap without correcting the 1m: the 1m-implied zero sits 1/6 to 1/2bp above the
3m-implied (Deriscope blog, Turn-of-the-Month Effect in SOFR Curve, 2024). Strip turns (December premium) before
comparing futures with forwards (Aikin, STIR Futures, 2nd ed., 2012). CME's own SOFR discounting curve uses 3m futures for 3M-2Y "with a convexity adjustment applied to futures to reflect the OTC vs
exchange risk differential" (CME Group, SOFR Discounting Transition Process for Cleared Swaps, 2 Jun 2020). A practitioner alternative is to imply the CA from
the market: fit a smooth parametric convexity curve to the liquid short swaps, composite curve = futures proxy +
convexity curve (Quantitative Finance Stack Exchange, STIR Futures convexity adjustment, 2025). See
[fi-curve-construction](../fi-curve-construction/SKILL.md).

## Worked examples
1. CA-implied vol inversion, Blues H6-Z6, 16 Feb 2023 (Citi, Short Blues convexity via futures/swaps, 21 Feb 2023). Contract
   starts 18 Mar/17 Jun/16 Sep/16 Dec 2026, T1 = 3.08/3.33/3.58/3.83y, mean T1^2 = 12.04. Observed CA 13.09bp:
   `sigma = sqrt(2 x 13.09 / 12.04 / 1e-4) = 147.4bp` (published 147.6). Model CA from cap vol 9.44bp (implies
   sigma_cap = 147.4 x sqrt(9.44/13.09) = 125bp). CA - model = +3.65bp, implied/realised 1.1, cap vol impl/rlzd 0.9. Golds
   H7-Z7: CA 21.24, model 13.87, +7.37, 3m z 1.48. Script check: `scripts/convexity_adj.py --selftest` reproduces both.
2. Trade, 17 Feb 2023: sell 1,000 H6-Z6 packs, pay USD 1.17bn CME 18-Mar-26 to 16-Mar-27 swap, entry CA 12.7bp (pack rate minus swap rate), USD 100k DV01.
   Carry +1.5bp per 3m (USD 150k), target 4bp tightening (+USD 400k), stop 2.5bp widening (-USD 250k): reward/risk 1.6,
   carry covers 60% of the stop in 3m. Sizing check: 100,000 / (1e-4 x 1.17bn) = 0.855 annuity, consistent with a 1y
   swap starting 3.1y out. Why Blues not Golds: Golds had the highest CA but looked more persistent, and Blues CA had
   already begun normalising. Primary risk: more short duration built in futures rather than OTC (Citi, Short Blues
   convexity via futures/swaps, 21 Feb 2023; US Rates Weekly: Time for moderation, 17 Feb 2023).
3. Outcomes (Citi, US Rates Weekly: All it takes is a little push, 4 Oct 2019; Turning Green from Blue, 6 Jun 2017; Time for
   moderation, 17 Feb 2023 for the 2021 trade): Blues
   sold 9 Feb 2017 at 8.8bp with a fly hedge, closed 6 Jun 2017 at 6.6bp, about +USD 0.5-0.55mm vs +0.6mm target, closed
   early for a better trade. Greens sold 6 Jun 2017 at 4.3bp (USD 300k DV01, hedge removed 13 Jul for +USD 70.5k), closed
   8 Aug 2017 at 2.65bp for +USD 475.5k: exit because the dislocation was no longer extreme and hawkish Fed risk loomed
   (Citi, Alert: Target achieved on short Greens convexity, 8 Aug 2017). Sell Blues 11 Jun 2021 at 7.9bp, closed 3 Dec 2021 at 3.4bp,
   +USD 389k.
4. Gamma sizing (Quantitative Finance Stack Exchange, 2019-2025; 27 Jul 2023): receive Jun-25 IMM 3m swap, delta USD 25k/bp,
   hedged with 1,000 short futures, swap gamma USD 12.2/bp per bp, option-implied normal vol 139-140bp, horizon 2y.
   Constant gamma: 0.5 x (140 x sqrt(2))^2 x 12.2 = USD 239k = 9.6bp. With gamma decaying to about 7.0 after 1y: about 6bp,
   "closer to market" (`gamma_ca_bp` with linear decay to zero at 2.35y gives 5.5bp). Ignoring gamma decay overstates by roughly 60%. `gamma_ca_bp` in the script.
5. Convexity P&L, receive USD 100mm 2y vs 779 short SR3 (CME, Pricing and Hedging USD SOFR IRS with SOFR Futures, 4 Jun 2025):
   net P&L -100bp +USD 22,292, +100bp +USD 21,226, +/-10bp about +USD 250/+180. Approximation
   `0.5 x 18 (contracts of re-hedge per 100bp) x 100bp x USD 25 = USD 22,500`. A payoff that is convex shows a smile when
   P&L is bucketed by size of move, not a ramp.
6. Regime flip (sign of the signal is not structural): Feb 2023 Blues CA +3.65bp rich to model (short CA favoured); Sep-Oct
   2026 Golds about -5bp and Blues -3 to -5bp cheap to model, 3m z -2.6 to -3.3 (first and last rows of the 2 Oct screen),
   while implied/realised 1.2-1.3 (Citi,
   Rates Vol Lab: Fading vega dislocations, 5 Oct 2026; Slow and steady wins the short gamma race, 14 Sep 2026). Long CA vs short EUR
   vol: sell 1,000 Blue pack, receive USD 1.19bn CME fwd swap at 5bp vs sell EUR 300mm 6m1y ATMF straddles, vega -EUR 16k,
   target +USD 300k, stop -USD 200k; USD 100k per bp of CA was matched to about EUR 16k of 6m1y vega by recent realised beta (Citi, Pension plan for 20s?, 9 Oct 2026). More
   trades and screen snapshots: [references/trades-and-screens.md](references/trades-and-screens.md).

## Signals & interpretation
| Reading | Interpretation / action |
|---|---|
| CA - model about +4bp (2 sigma), also about +3bp (2 sigma) wide to the hedging fly, roll >= +1.3bp/3m, implied/realised about 1.3, dealers net long futures at highs | Short convexity entry (Citi's five published conditions, 2017; the Feb 2023 trade was looser: 3m z 1.3, implied/realised 1.1). Size to a USD target of about 3-4bp and stop about 60-75% of target |
| CA - model between -2 and +2bp, z within +/-1 | No trade. Do not trade the CA level, trade the divergence from model |
| CA - model <= -3bp, z <= -2, asset managers not net short, vol not falling | Long convexity candidate (Oct 2026 pattern). Pair with short vol of a matching expiry and disclose the expiry mismatch |
| CA up, model flat/down (vol falling) | Technical (positioning) widening: likely persistent until shorts capitulate; prefer the pack that has started normalising |
| CA and model both up (vol up) | Vol-driven, not a mispricing; short CA is losing short-vol |
| CA < 0 or CA much below model on one pack only | Data first (stale settle, swap-leg junk), then positioning (short covering) |
| 3m change in 3m10y 25bp-out risk reversal in its lowest quartile (flat skew) | Shorts capitulating, CA likely to tighten; extremes only (Citi, Sell Blues convexity adjustments, hedged, 9 Feb 2017) |
| Per-contract CA above longer neighbour | Cheap to neighbours; RV only, persistent by contract |
Exit: target reached, or the dislocation stops being extreme even if CA is still rich (Citi, 8 Aug 2017), or edge shrinks
and a better trade exists; respect event risk (hawkish Fed repricing, SOMA/QT talk).

## G10 market notes
| Market | Notes |
|---|---|
| USD | SR3 compounded SOFR, IMM to IMM, USD 25/bp, listed 5y+ out; SR1 arithmetic average, USD 41.67/bp. SR3 pack vs forward CME swaps is the standard CA. Customers clear at CME (futures netting), dealers at LCH. CME portfolio-margining client savings went from about USD 2bn (2018) to above USD 9bn (early 2025) (CME, 4 Jun 2025). Legacy ED CA collapsed after 2011 on CME cross-margining |
| EUR | Euribor 3m futures (term rate fixed in advance): Ho-Lee `T1T2` form. 2y ATM normal cap vol 105.86bp gave CA about 0 at ER1 to 5-6bp at ER12 (Mar 2026) (BSIC, 29 Mar 2026). HW 1F (a 3%, sigma 35bp) gave about 1.4bp at 5y in Dec 2012 (Ametrano and Bianchetti, 2013). In 2013 split clearing (LIFFE futures vs SwapClear FRA margin not nettable) turned the bias slightly negative (Aikin, The disappearing convexity bias, 16 Dec 2013): check where each leg clears. Market FRAs carry below 1bp convexity |
| GBP | SONIA 3m futures compounded ACT/365F, HW sigma 65bp (valued end-2017) gives about 1bp for contracts starting early 2020, 2bp (2021), 3.3bp (2022), 5bp (2023), 7.3bp (early 2024, the 6y contract) (Henrard, Overnight Futures: Convexity Adjustment, 2018). Sterling futures vs IMM-FRA CA may not be fully priced (Poskitt via West, 2010). Positioning, futures venue and swap-CCP basis can dominate theory |
| JPY | Short strips need only a small adjustment (Duering, 2021). Sources give no pack-level levels |
| CAD | CORRA compounded futures use a 365-day year in settlement; no CA levels in the sources |
| AUD, NZD | Bank-bill futures are quoted in yield (term rate fixed in advance: use `T1T2`). Henrard (2012) describes AUD bills as physically settled, adding a cheapest-to-deliver option on top of any CA; check the current contract specification and, if it applies, separate the two before reading a gap |
| CHF | SARON compounded 3m futures; legacy 3m futures existed. No levels in sources |
| SEK, NOK | No source material. Apply the same Ho-Lee `T1sq` form with the local cap vol, and treat results as unverified |
All markets: size grows with sigma^2 T^2, so it matters for deferred contracts of long-strip markets (USD, EUR, GBP, CAD)
and little for short strips. Market CA follows supply and demand: "the much higher liquidity of futures compared to IMM
IRSs can create distortions ... far from the theoretical no arbitrage price" (Darbyshire, 2022).

## Pitfalls
- Annual swap leg vs quarterly futures: a 4-12bp bias that scales with the rate squared. Check legs first.
- Mixing Ho-Lee forms (`T1sq` vs `T1T2`) changes implied vol by up to about 7%; a `T1T2` build cannot reproduce published
  Citi tables. Check before comparing with a sell-side screen.
- CA vs the wrong CCP or wrong snap: CME vs LCH level differences (excess CA vs CME was about 80% of that vs LCH in 2017, ranging 30% at Z7 to 85% at Z8/H9)
  and 15:00 vs 17:00 snaps will each swamp a 1-2bp dislocation.
- Treating CA as vol only: excess CA also reflects margin, balance-sheet cost and positioning. Check positioning before
  calling it vol mispricing (J.P. Morgan, 3 May 2017).
- A vol-calibrated model "assumes unchanged vol". Short CA is short vol: hawkish shocks and reaction-function shifts hurt.
  Main risk is further short build-up in futures. The signal can persist for months (Golds more than Blues).
- Realised vol is backward-looking: implied/realised is a cushion gauge, not a forecast.
- Ho-Lee overstates CA beyond about 2y (no mean reversion); smile and curve correlation are ignored (one-factor
  overestimates slightly).
- Constant-gamma estimates overstate CA (gamma decay), by about 60% in the SOFR example.
- An implied CA (residual vs a curve) contains the true CA plus futures/cash basis (FactSet, Interest Rate Future white
  paper, 2023). A constant-CA scenario assumption understates futures risk in large moves.
- Do not read every futures/OIS gap as convexity: the risk premium grows with horizon (federal funds futures minus realised
  compounded rate averaged 4.4bp at 3m and 10.5bp at 6m over 2000-2019) (Heitfield and Park, Federal Reserve Board FEDS
  2019-014). Strip-vs-swap "arbitrage" is usually 3s6s tenor basis plus forward-start mismatch (Aikin, 2012).
- Daily convexity is unidentified: read convexity at trade level, daily P&L only through linear factors.
- Screen "best trades" are "not necessarily trades that we would recommend": backward-looking and illustrative.
- Check each colour separately: short covering can be confined to Blues and beyond while Reds/Greens open interest still rises.
- SR1 averaging vs compounding adds at most 0.1bp at 2021-22 rates and about 1bp near 5% (Huggins and Schaller, 2022).
- Tail futures hedges: `N_tailed = N / (1 + R0 D / 360)`, re-set as rates and days change (Tuckman and Serrat, Table 12.8).

## Output
A CA note per pack/currency with: (1) conventions used (form, vol source and tenor, CCP, snap, curve build id);
(2) table: pack, CA (bp), model, CA - model, 3m/1y z, 3m roll, CA-implied vol, realised vol, implied/realised, cap-vol impl/rlzd;
(3) data-control results (sign, staleness, swap-leg gate); (4) attribution of the residual: vol vs positioning (lagged
data) vs CCP/funding; (5) trade if any: instruments, packs, swap notional and CCP, DV01, entry CA, target, stop, 3m carry,
hedge and its measured effectiveness, key risk; (6) what would invalidate it. Hand to
[rv-devils-advocate](../rv-devils-advocate/SKILL.md) and [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

## Scripts
[scripts/convexity_adj.py](scripts/convexity_adj.py): `ho_lee_ca_bp`, `hull_white_ca_bp`, `pack_model_ca_bp`,
`implied_vol_bp`, `pack_ca_bp`, `par_from_dfs`, `par_from_forwards`, `gamma_ca_bp`, `tail_factor`, `screen`. CLI:
`python -I scripts/convexity_adj.py --selftest` (checks Hull 47.52bp, Tuckman Table 12.12, HW vs published EUR 2012 values,
published Citi implied vols, gamma example, a numerical Gaussian covariance check) and
`--screen packs.csv [--form T1sq] [--window 63]` (columns `date, pack_id, t1_first_years, ca_bp, sigma_cap_bp`).

## Related skills
- [stir-futures-rv](../stir-futures-rv/SKILL.md): strip spreads, flies, packs/bundles; adjust for CA before comparing with swaps
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): SR3 vs SR1 reference periods
- [fi-curve-construction](../fi-curve-construction/SKILL.md): futures inputs to the curve, CA-adjusted bootstrapping
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CME-LCH basis that shifts the measured CA
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): margin, initial-margin funding cost, portfolio margining
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): dealer/asset-manager positioning as the CA driver
- [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md): cap/floor and futures-option vols, implied vs realised
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): short CA as a delta-hedged straddle; gamma vs theta P&L
- [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md): long-end convexity value and synthetic vol packages, the cash-curve cousin of CA
- [curve-butterflies](../curve-butterflies/SKILL.md): 2s5s10s fly weights used as the vol hedge
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): day counts, futures and swap conventions per market
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): cost per leg vs the CA edge
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): option-implied policy-rate distributions.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): the implied policy path.

## References
- Citi Research - Rates Vol Lab: Short Blues convexity via futures/swaps (Chang, Williams, Appeddu, 21 Feb 2023): CA as short-vol proxy, Ho-Lee fair value, implied-vol inversion, full screen and trade
- Citi Research - US Rates Weekly: Time for moderation (17 Feb 2023): CA definition, positioning and vol-lag drivers, CME vs LCH choice, trade target/stop
- Citi Research - NA Rates Trade Idea: Sell Blues convexity adjustments, hedged (Bikbov, Williams, 9 Feb 2017): original Blues trade, fly regression, skew signal
- Citi Research - US Rates Weekly: Swearing in huge expectations (13 Jan 2017): CA screen definition, positioning regression R^2 0.32, fly-hedge fit
- Citi Research - NA Rates Trade Idea: Turning Green from Blue on short convexity (6 Jun 2017): Blues close, Greens trade, annual-leg bias, hedge fits
- Citi Research - US Rates Vol Lab: Value in Greens convexity (15 May 2017): Greens trade, ED5/ED9 hedge rationale
- Citi Research - Rates Vol Lab: Left-side vols' outperformance (22 Jun 2021): Ho-Lee formula, short CA = short straddle, E[P&L]
- Citi Research - Rates Vol Lab: Forward steepener and vol divergence (12 Jun 2023); Liquidity, vega, and convexity (30 Mar 2020); In search of cheap vol (17 Jan 2020): monitor snapshots
- Citi Research - Rates Vol Lab: Fading vega dislocations (5 Oct 2026); Slow and steady wins the short gamma race (14 Sep 2026): 2026 regime where CA is cheap to model
- Citi Research - US Rates Weekly: Pension plan for 20s? (9 Oct 2026): long CA vs short EUR vol, positioning link broken
- Citi Research - NA Rates Trade Idea: Alert: Take off the hedge on short Greens convexity (13 Jul 2017); Target achieved on short Greens convexity (8 Aug 2017): hedge unwind, exit rule
- Citi Research - US Rates Vol Lab: Convexity Meets Steepeners (19 Apr 2018); US Rates Weekly: What to expect when you're expecting a turn (20 Apr 2018): ED6/ED16 hedge, ZLB failure
- Citi Research - NA Rates Focus: Shorts increasing? An alternative view of positioning (Williams, 16 Jan 2019): CA as positioning gauge
- Citi Research - US Rates Weekly: Going nuclear (on the curve) (3 Feb 2017): per-contract rich/cheap; All it takes is a little push (4 Oct 2019): closed-trade outcomes
- J.P. Morgan - A better way to sell vol: CME-based convexity adjustments are rich (Younger, Sarkar, Salem, 3 May 2017): excess CA vs positioning, implied funding spread, CME vs LCH
- CME Group - Pricing and Hedging USD SOFR IRS with SOFR Futures (Rogerson, 4 Jun 2025): strip-to-swap, hedge ratios, convexity P&L table, margin
- Clarus Financial Technology - CME-LCH Basis: Convexity in Eurodollar Futures (Barnes, 1 Jul 2015): margin funding, portfolio-margining requirement
- BSIC - Understanding Convexity Bias in STIR Futures Markets (29 Mar 2026): Ho-Lee and Hull-White derivation, calibration, EUR example
- Quantitative Finance Stack Exchange - "Why are FRA/futures convexity adjustments necessary?" (2019-2025), "STIR Futures convexity adjustment" (2025), "SOFR futures options" (2023): gamma view, SOFR sizing example, market-implied CA, pre-curve workflow
- Tuckman and Serrat - Fixed Income Securities, 4th ed. (Wiley, 2022): CA formulas, Table 12.12, ordering of futures rates, tailing
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): futures convexity adjustment (FCA) as hedged-package P&L, whites vs greens size
- Huggins and Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): financing bias vs nonlinearity, SR3 vs SR1
- Henrard (OpenGamma) - Overnight Futures: Convexity Adjustment (Feb 2018); Interest Rate Futures and their Options: Some Pricing Approaches (Feb 2012); My Future Is Not Convex (May 2012); Overnight Indexed Swaps and Floored Compounded Instrument in HJM One-Factor Model (BIS working paper, Feb 2004): HW closed forms, GBP levels, negligible OIS payment-lag effect
- Garcia-Lorite and Merino - Convexity adjustments a la Malliavin (arXiv, 2023); Rosen (FINCAD) - Averaged Overnight Rate Futures: Convexity Adjustment (2019): overnight-futures CA, SOFR levels
- Ametrano and Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN, Apr 2013): EUR CA, FRA convexity below 1bp
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed. (Harriman House, 2012) and blog "The disappearing convexity bias" (16 Dec 2013): P&L tables, post-2011 collapse, EUR split clearing
- Heitfield and Park - Inferring Term Rates from SOFR Futures Prices (Federal Reserve Board FEDS 2019-014, Feb 2019): futures-OIS risk premium by horizon
- West - Interest Rate Derivatives lecture notes (Financial Modelling Agency, 2010); Duering - Fixed Income Trading and Risk Management (Wiley, 2021); FactSet - Interest Rate Future white paper (2023): Ho-Lee/HW formulas, strip building, implied-CA caveat
- Deriscope blog - Turn-of-the-Month Effect in SOFR Curve built out of 1- and 3-Month Futures (Rigopoulos, 18 Feb 2024): 1m vs 3m implied-zero gap
- CME Group - SOFR Discounting Transition Process for Cleared Swaps (Dayon, Bawadhankar, 2 Jun 2020): CCP curve built with convexity-adjusted 3m futures
- Hull - Options, Futures, and Other Derivatives (Pearson), convexity adjustment and short-rate model chapters (external): Ho-Lee T1 T2 sigma^2/2 anchor
- Burghardt and Hoskins - "A Question of Bias", Risk, March 1995 (external): origin of the Eurodollar convexity bias
