# STIR futures: contract mechanics that change the RV maths

Loaded from [SKILL.md](../SKILL.md). Always confirm a contract's terms in `fut_static` (tick, BPV, reference method,
reference start/end) before trusting anything below: specs change, and several sources here are from the LIBOR era.
Exact per-market conventions live in [fi-g10-market-conventions](../../fi-g10-market-conventions/SKILL.md).

## 1. Price, BPV, P&L
- Price = 100 − rate (rate in %). A future is a cash-settled notional forward deposit; `100 − price` is the forward
  rate over the reference period, not "what 3m Libor/Euribor will be" (Aikin, STIR Futures, 2012).
- BPV = notional × 0.01% × accrual. 3m contracts on a 1m notional pay 25 per bp (USD 1m × 0.0001 × 90/360): SOFR USD 25,
  Euribor EUR 25, Euroswiss/SARON CHF 25, CORRA CAD 25, SONIA GBP 25 (legacy Short Sterling GBP 500k = GBP 12.50/bp).
  1m averaging contracts (SR1, 30-day FF): USD 5m × 0.0001 × 30/360 = USD 41.67/bp. Read `fut_static.bp_value_ccy`.
- P&L (long) = contracts × (exit price − entry price in bp) × BPV. Tick value = BPV × tick in bp.
- Package DV01: every contract is worth BPV per bp of its own rate, so a package with weights w has DV01 = BPV per
  bp of the spread S = Σ w_i r_i regardless of w; contracts traded = Σ|w|; round-trip cost = Σ|w| × 2 × half-spread.
  A (1,−2,1) fly is the cheapest level-neutral fly (4 contracts).
- Hedge with swaps: strip DV01 by bump-and-reprice (bump each future 0.01, reprice swap at original coupon, hedge =
  ΔPV / 25). Hedge counts decline along the strip because of discounting; a receive USD 100mm 2y IMM swap needs
  M5 100, U5 99, Z5 99, H6 98, M6 97, U6 96, Z6 95, H7 95 = 779 contracts (CME Group, Pricing and Hedging USD SOFR
  Interest Rate Swaps with SOFR Futures, 4 Jun 2025).

## 2. Settlement formulas
| Contract | Final price | Notes |
|---|---|---|
| 3m SOFR (SR3) | 100 − R, R = [Π(1 + SOFR_i d_i/360) − 1] × 360/D × 100 | n business days; d_i = calendar days SOFR_i applies (Friday d = 3); D = Σd_i; rounded 0.01bp; reference quarter = 3rd Wed to 3rd Wed (Huggins & Schaller, SOFR Futures and Options, 2022) |
| 1m SOFR (SR1) | 100 − arithmetic average of SOFR over all calendar days of the month | weekends carry prior business-day SOFR; Friday counts 3×; rounded 0.1bp; last trade = last business day of month |
| 30-day FF (ZQ) | 100 − arithmetic average of effective FF over the calendar month | a change effective on day d enters as (d−1)/N old + (N−d+1)/N new; the 31-day compounded-vs-arithmetic gap is about r²(n−1)/720 ≈ 0.67bp at 4%, more than a half-tick, so model it arithmetically |
| 3m SONIA | compounded SONIA over IMM period, ACT/365F | stops trading 08:30 on the last day, before the last fixing is published (Henrard, Overnight Futures: Convexity Adjustment, 2018) |
| 3m Euribor | 100 − 3m Euribor fixing (term rate) | fixes T+2 (Monday before the 3rd Wednesday) and the future EXPIRES then; SOFR/SONIA futures keep trading until the end of the reference period |
| 3m CORRA / SARON / ESTR | compounded overnight rate over the period | same mechanics as SR3; check ACT basis |
| AUD 90d bank bills | value per contract from price = 1/(1 + δR), R = 1 − F, δ = days/365, so BPV varies with the level (about 24, not 25) | expiry 2nd Friday; Henrard (Interest Rate Futures and their Options, 2012) describes physical delivery of 85-95 day bills with a cheapest-to-deliver option; check `fut_static.settlement_type` before assuming either |
| NZD 90d bank bills | cash on 3m BKBM, non-IMM expiry | Clarus, Mechanics and Definitions of Short Term Interest Rate Futures, 2016 |

Legacy IBOR futures (Eurodollar, Short Sterling, Euroyen/TIBOR, BAX, Euroswiss) settle on the 3m IBOR fixing; after
Jun 2023 USD IBOR-linked contracts are SOFR plus a fixed spread, so only the SOFR-FF spreads carry the
secured-unsecured basis. When using histories, mark the LIBOR→SOFR break and the SOFR standing-repo-facility break
(Aug 2021): re-estimate vol, mean reversion and regressions on post-break data.

### In-period front SR3 (do not treat as a normal forward)
Split R into known and unknown fixings:
`R_unknown = [ (1 + R·D/360/100) / Π_known(1 + SOFR_i d_i/360/100) − 1 ] × 360/D_unknown × 100`.
The front contract's volatility decays through its reference quarter and it becomes "sticky"; its hedge ratio is not
25 (e.g. 0.8384 of full sensitivity once part of the quarter is fixed). 6m strip example from 3-Oct-2022 with 95bp
known SOFR in the Sep-22 quarter and prices 99/98.5/98 → 6m annualised strip 1.34% (Huggins & Schaller, 2022).
Roll SR3 exposure from the 2nd into the 3rd listed contract, not front to back: rolling Dec-19 into Mar-20 cost 138bp
at the end of the reference quarter vs 4bp at the start.

## 3. Colour packs, packs/bundles/stacks
| Colour | Quarterly slots | Notes |
|---|---|---|
| Whites | 1-4 | most liquid; meeting idiosyncrasy; margins and vol highest |
| Reds | 5-8 | liquid; futures carry most information up to here |
| Greens | 9-12 | ~40% of Reds' volume (SOFR, Jun 2025); convexity 1.5-12bp |
| Blues | 13-16 | liquidity poor after here; CA trades live here |
| Golds | 17-20 | CA most overvalued but most persistent |
| Purples, Oranges, Pinks, Silvers, Coppers | 21-40 | thin; prices partly implied |
Naming is by slot (Darbyshire, Pricing and Trading Interest Rate Derivatives, 2022); some desks label packs by where
trading concentrates (e.g. "Blues" = SOFR Mar-26..Dec-26 in Feb 2023, Citi, Short Blues convexity via futures/swaps, 21 Feb 2023). State the contracts, not just the colour.

- Pack = 4 consecutive quarterlies, equal weight; bundle = 2-5y (multiples of 4; ED to 10y, Liffe to 5y); stack = n lots
  of one month as a pack proxy.
- Pack yield `[Π_{i=1..4}(1 + 0.25 r_i)] − 1`; N-year bundle yield `[Π_{i=1..4N}(1 + 0.25 r_i)]^(1/N) − 1`. Example:
  H2 97.490, M2 97.310, U2 97.210, Z2 97.160 → 2.735%; adding H3..Z3 97.10/97.00/96.90/96.87 → 2y bundle 2.901% (Aikin, 2012).
  Pack/bundle yields are forward-starting with standardised 0.25y quarters, so they are not comparable with spot bond/swap/deposit yields.
- Quote conventions on net change: Liffe "total change" = sum of leg changes (0.005 steps); CME "annualised" = average of
  leg changes (0.0025 steps). Legs −0.03/−0.03/−0.03/−0.02: Liffe −0.110, CME −0.0275; an average of −0.02875 is not
  tradable on CME. Same pack move looks ~4× as volatile on a Liffe quote. CME pack/bundle min tick 0.25bp, priced as arithmetic average of constituents.
- Strip bootstrap to an IMM swap rate (CME): `DF_i = 1/(1 + R_i d_i/360)`, `CDF_i = Π DF`, `fixed = Σ CDF_i R_i d_i/360 / Σ CDF_i d_i/360`
  (use the fixed leg's own day counts if different). Apr 2025: prices M5 95.895 … H7 96.910 → 2y IMM OIS 3.3304%; dealer
  3.3275/3.3325. Implemented in `strip_swap_rate`.

## 4. Spread matrix, implied pricing, microstructure (Aikin, 2012)
- Spread = P_near − P_far (= far rate − near rate); bid = near bid − far offer. Fly = P1 + P3 − 2P2 = S1 − S2; condor
  B1 + B2 = S1 − S3. Additivity: H2H3 = H2M2 + M2U2 + U2Z2 + Z2H3 = H2U2 + U2H3. Same near leg: H2U3 − H2M3 = M3U3.
  Flip: long M2U2 + short M2Z2 = short U2Z2. Net on paper first; never leg a closing spread.
- Implied-in (outrights imply spreads) and implied-out (spread orders imply outrights) exist at top of book only. Liffe
  implies to calendars; CME also to flies/condors from the strip. Outright orders take precedence over implied. Implieds
  vanish when needed ("lean" on them but do not trade against purely implied prices). Do not autospread the front month.
- Spread widths: from outrights = sum of leg widths; a fly from outrights = 4 leg widths (2 ticks at 0.005), market usually
  trades 1 tick. Packs/bundles/flies usually price tighter than implied; fast markets favour strategy orders not subject to implieds.
- Mid for wide-tick SOFR futures: last trade goes stale; (bid+ask)/2 jumps with small orders; size-weighted mids can be
  spoofed. Prefer an intrinsic-depth mid or a multi-instrument least-squares mid across outrights, spreads and flies:
  `p* = (AᵀWA)⁻¹AᵀW s` with rows [1,0,0], …, [1,−2,1] (Darbyshire, 2022, ch.19; check on SOFR M2/U2/Z2: OLS 98.2114/98.1167/98.0439).
  Do not aggregate order books across venues (double-counts liquidity that one party can pull).
- Liquidity: concentrates in the 2nd-3rd quarterlies not the expiring front; beyond 3-5y mostly implied. SPAN treats spreads at
  ~25% of outright risk but some risk systems count a 100-lot spread as two 100-lot outrights. Many matrix traders live off rebates, so fees and rebate tiers belong in cost.

## 5. Inter-commodity spreads (CME ICS, 2024 listing)
| ICS | Ratio | Quote | Notes |
|---|---|---|---|
| SR1/SR3 | 3 SR1 + 3 SR1 vs 10 SR3 (6 × 41.67 = 250.02 vs 250) | avg(SR1 prices) − SR3 price | no basis: slope/Fed timing + simple-vs-compound; margin offset |
| FF/SR3 | (3+3) FF vs 10 SR3 | avg FF − SR3 | e.g. (94.890 + 94.735)/2 − 94.7775 = 3.5bp |
| SR1/FF | 1:1 | SR1 − FF | pure secured-unsecured basis |
| ESTR/SR3 | 1:1 | ESTR − SR3 | USD vs EUR front-end |
| SR3/T-bill | 1:1 | | bills vs OIS |
The CME ratio differs from the exact contract-weighted spread by <1bp, which matters at low rates. ICS blocks need each
leg to meet the smaller outright threshold. A late 3rd Wednesday leaves more of the SR3 quarter end uncovered by the two SR1s.

## 6. Convexity ordering and what to adjust
forward < term-rate future (Euribor-style) < average-rate future (SR1, FF) < compounded-rate future (SR3). All futures
rates exceed the matching forward; adjust before comparing futures-implied paths with OIS forwards (Tuckman & Serrat,
Fixed Income Securities, 4th ed., 2022). SR1 averaging vs compounding is ≤0.1bp at 2021-22 rates and ~1bp near 5%. Whites
0-0.5bp, Greens 1.5-12bp (Darbyshire, 2022, ch.22). Derivation and modelling: [stir-convexity-adjustment](../../stir-convexity-adjustment/SKILL.md).

## 7. Fixing, expiry and day-count by market (legacy and current)
- T+2 currencies (USD, EUR) fixed on the Monday before the 3rd Wednesday; same-day currencies (GBP, CAD) on the 3rd Wednesday itself (Clarus, 2016).
- Hedge with an expiry within ~2 weeks of the exposure date: futures vs cash basis is "usually ±10bp" in the final month and shrinks in the final week (Aikin, 2012).
- IMM revaluation jumps: DV01 migrates from swaps to futures on roll dates and the overnight curve usually has an implied jump on the IMM date (Clarus, Mechanics of FRA Risks, 2018).
- Tick sizes: CME SOFR 0.5bp (0.25bp front); SONIA futures 0.5bp; Short Sterling ~2010 1bp; IRS CLOBs 0.05-0.01bp. Coarse ticks concentrate volume and make mids noisy.
- Per-market (read the real terms from `fut_static`): USD SR3/SR1/FF; EUR Euribor (term) and ESTR 3m; GBP SONIA (and legacy
  Short Sterling); CHF SARON (legacy Euroswiss); CAD CORRA (legacy BAX); AUD and NZD bank bills (non-IMM expiry; AUD physical);
  JPY TONA/legacy Euroyen/TIBOR (illiquid beyond Reds); SEK/NOK: price policy with meeting-dated OIS (SWESTR, NOWA), not futures.
