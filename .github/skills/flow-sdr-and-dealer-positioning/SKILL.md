---
name: flow-sdr-and-dealer-positioning
description: Reads public swap trade reporting (CFTC Part 43/45 SDR and DTCC prints) and dealer-tagged flow to infer rates positioning. Covers price-forming cleaning (compression, netting), DV01 sizing, cap and block censoring, package, spreadover, IMM-roll and CCP-basis detection, dealer offsetting (Mean Offsetting Ratio), trade-direction inference from untagged prints, dealer hedge vectors, issuance, callable and structured-note flow, and tail-strike swaption flow. Use when the user asks about SDR or DTCC swap data, the swap tape, volume or liquidity spikes, SEF or venue volume, block trades, flies or curve trades in the tape, spreadover or asset-swap volume, IMM roll volume, CME-LCH basis or CCP switches, dealer offsetting or direction, who is paying or receiving swaps, issuance swapping, callable vega or supply, or 6% strike swaption flow.
---

# Swap trade-reporting flow and dealer positioning

Public swap prints show what traded, when, and at what size. They do not show who traded, which way, or why. This skill turns the tape into flow and positioning estimates: clean to price-forming prints, size in DV01, censor for reporting caps and blocks, detect packages and structures, then infer dealer offsetting and hedge direction. It works because dealers warehouse client risk and hedge it in the interdealer market over minutes to days, and because issuance, callables and structured notes leave footprints in long-dated and tail prints. Every inference is probabilistic. State the confidence and the data gap with each number.

## When to use
- A trader asks what the SDR or DTCC tape says about a tenor, currency or structure ("who is paying 10s30s", "what did the block flow look like").
- Volume or liquidity needs a read that is not notional-based: DV01 volume, print counts, package-adjusted activity, or a spike check.
- Package or structure questions: flies, curves, CCP switches, spreadovers, asset swaps, invoice spreads, IMM rolls.
- Dealer question: is the desk offloading client flow, how long does it take, is the warehouse long or short.
- Supply or convexity question: issuance swapping, callable vega, MBS or structured-note hedge flow reaching the swap market.
- Tail-strike swaption flow (6% strikes), or any "who is buying the protection" question on swaptions.

Not for live order routing, execution quality, or vol-only ideas. Use the execution, vol and CFTC positioning skills for those.

## Inputs (data-agnostic)

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Public swap prints: new, cancel, correct, error; cleared flag; venue; block-cap flag; package and compression flags; dissemination and execution times | `flows_trades` | one row per print, at least 12 months for seasonality, longer for thresholds | `pub_ts_utc` is the knowledge time. A print is visible only after it. Blocks are delayed and capped. |
| Fixed-leg frequency, day count, spot lag per currency and index | `swap_conventions` | per currency and index | Needed for annuity and DV01 sizing. Legacy Libor-era USD swaps pay semi-annual fixed (the 2010-2016 samples); current RFR swaps (SOFR, SONIA, TONA, EUR RFR) pay annual fixed, mostly ACT/360 or ACT/365F. Check the table, not memory. |
| Par swap rates by tenor | `curve_par` | daily snap, at least 3y | Gives DV01 level and forward moneyness for strike tests. State bp or pct. |
| Policy and reference fixings | `rate_fixings` | daily | Used for the moneyness of tail strikes relative to the forward. |
| CCP basis (LCH versus CME mid by tenor) | `ccp_basis` | daily, benchmark tenors | Needed for CCP-basis pairs and switch cost. |
| Holidays and IMM dates | `calendars` | exchange and cash calendars | IMM dates and roll windows. Exchange and cash calendars differ. |
| Auction and issuance calendars and sizes | `auctions` | per auction | Needed for issuance-swap timing and the duration-supply gauge. |
| Dealer-tagged DV01 prints (dealer, direction, venue, timestamp) | `dealer_flow` (`dealer_id`, `exec_ts_utc`, `dv01_ccy`, `is_large`) | per print | Public SDR data carries no counterparty identity. Without this input, skip the dealer-level methods (offsetting, dealer inventory, dealer hedge model) and say so. Never infer a dealer identity from public fields. |

If an input is missing, ask for it or hand off to the data adapter. Never invent prints, dealer identities or sizes.

## Method

### 1. Time and visibility
- Sequence prints by execution time. Use dissemination time only to decide what was knowable.
- In any backtest or live read, a print is visible from its dissemination time, and block prints carry a longer, class-specific delay. Do not use an early-visibility assumption for blocks.
- The execution timestamp of a cleared trade is fixed for the life of the trade identifier. Later amendments do not move it.

### 2. Price-forming cleaning (do this before any volume or direction read)
Apply in this order:
1. **Netting.** A row referenced by a later `correct`, `cancel` or `error` is removed. The `correct` row is kept as the new version. Cancel and error rows are removed. Treat a revision as a new print.
2. **Sentinel values.** All-nines notional or package spread means "unknown", not data. Set to missing.
3. **Remove non-price-forming prints:** compression and portfolio-maintenance (weak price content); fee-less amendments, cancels and novations; clearing legs; allocations; SDR transfers; physically exercised swaptions; prime-brokered and internal trades; manually duplicated prints; FRA switch batches (vendor batch at estimated mid).
4. **Packages.** Count packages, not legs. Strip package legs before reading outright direction (see step 5).
5. **Forward-start.** Choose the threshold and state it. Fleming et al. (NY Fed Staff Report 557, Mar 2012) use effective more than 5 days after trade. Benos et al. (Bank of England Staff WP 580, Jul 2016) keep only spot-starting trades (more than 2 business days is excluded). Use the 2-day spot rule for spot-liquidity work and the 5-day rule when you want the price-forming volume that Fleming et al. report.
6. **Duplicates.** A centrally cleared trade is reported once per clearing-member side, so each cleared trade can appear twice. Keep one per key (execution time, product, currency, effective date, maturity, notional, rate).
7. **Off-market filter.** Benos et al. keep rates within 5% of the same-day end-of-day benchmark for the same currency and maturity. Re-couponing (terminate an off-market swap, replace with a par swap on the same dates) and compression inflate volume. Look for repeated terminations of one long-dated swap.

Sanity check: Fleming et al. found about 167k price-forming against about 319k non-price-forming trades in 2010 (34% of count). Benos et al. retained 628,896 reports (USD 58.17tn) after cleaning. These are 2010-2016 shares (Libor era, pre-cap): use them as an order-of-magnitude sanity check, not a target, because compression and SEF-compression shares have changed (Clarus SEF compression runs were larger than outright counts in 2024).

### 3. Size in DV01, and censoring
- Size in DV01, not notional. Notional across maturities differs by two orders of magnitude; DV01-adjusted median size is roughly constant across maturities at about USD 30k to 50k DV01 for G4 swaps (Fleming et al., NY Fed Staff Report 557, Mar 2012).
- Par fixed-leg DV01 (currency per bp, positive for receive):
  `DV01 = N × 1e-4 × A`, with `A = (1 − (1 + y/f)^(−n)) / y`, `n = tenor × f`, `y` = par rate as a decimal, `f` = fixed-leg frequency per year. Floating-leg DV01 is ignored (a single-curve approximation). For an annual ACT/360 fixed leg multiply by about 365/360 (`dcf_scale` in the script); the 30/360 and ACT/365F cases are about 1.
  Worked check: 10y, USD 100m, 2% with annual payments gives A = 8.9826 and DV01 about 89.8k per bp. McPhail, Schnabl & Tuckman (CFTC OCE Staff Paper 2019-011, Apr 2023) give a receive-2% 10y USD 100m swap NPV of about +9.5m at 1% and about −8.5m at 3%, a DV01 of about 90k per bp. The two agree.
- Tenor buckets for size thresholds: 0-1m, 1-3m, 3-6m, 6-12m, 1-2y, 2-5y, 5-10y, 10-30y, above 30y. Nine buckets explain about 32% of size variance; merging 0-1m and 1-3m drops this to 24%. Keep separate buckets. Use separate G4 and non-G4 thresholds (Fleming et al.).
- "Large" = above the 95th percentile of DV01 within the currency and bucket. Exclude under 2y. Default lookback: trailing 12 months, so thresholds track the regime. The 12-month window is a practitioner default for keeping thresholds current, not a figure from the sources. Fleming et al. used a single 2010 sample, which is a low-rate period.
- **Reporting caps.** Public notionals are capped and rounded, and other fields are scaled to avoid fingerprinting (CFTC Technical Specification, Parts 43 and 45, v3.0 Sep 2021 and v3.1 Aug 2022). In the 2015 Clarus estimate the USD IRS cap was about USD 110k DV01 per trade, smaller at 3y and 4y and larger at longer tenors, and RFQ blocks were about twice the cap (Clarus, Identifying Customer Block Trades, Oct 2015). Cap levels have been revised since, so re-estimate them from the data: the cap shows up as a mass point at the maximum disseminated notional per tenor bucket. Field and dissemination rules are in the CFTC Technical Specification (v3.1, Aug 2022). Treat a capped print as a lower bound: DV01 = cap, flagged as censored. Never compare a capped print to an uncapped one as if both were measured.
- The Fleming et al. thresholds are from 2010, before the caps existed. Do not carry those notional percentiles forward without re-estimating in DV01.

### 4. Customer versus dealer, and venue inference
- Public SDR data has no counterparty identity. Dealers are the largest banks by volume (Benos et al. use the top 16, matching the NY Fed participating dealers). Dealer-to-dealer is about 54% of USD and 61% of EUR volume; dealer-to-client about one third (Benos et al., Jul 2016).
- Rule of thumb from the reporting pattern: capped, non-block prints on the dealer-to-dealer order book are dealer flow; block-flagged prints on request-for-quote venues are customer flow (Clarus, Identifying Customer Block Trades, Oct 2015). The CFTC interpretation behind this rule lapsed on 15 Dec 2015. Re-check the current rules before relying on it.
- Average size by venue = venue volume / trade count for that venue (Clarus, Identifying Customer Block Trades, Oct 2015).
- Venue identifiers (ISO MIC on each record) separate customer-to-dealer, dealer-to-dealer and off-venue. The venue codes and the full field dictionary are in [sdr-fields-and-filters](references/sdr-fields-and-filters.md).

### 5. Structure detection
- **Compression.** Hallmarks: seasoned swaps, packages, identical timestamps, large notional in few trades, fee information. USD compression was about 13% of DTCC SDR trade count and notional in Nov 2014, and 92% of one SEF's volume (Clarus, Compression in USD Swaps, Dec 2014). SDR notionals understate it because blocks are capped.
- **Package anchor.** Package flag true, identical execution timestamp, and identical package spread or price identify a package. Legs cannot otherwise be linked. The Part 43 package flag is a boolean; the type (curve, fly, spreadover) must be inferred from the package price (Clarus, SDR Trading Venues and Packages, Jan 2023).
- **Count packages, not legs.** Legs per package: flies 3, curves 2, CCP switches 2. Clarus (SOFR Swap SEF Volumes, Jun 2024) reports 18,474 fly legs over 6,158 fly packages (3.0 per package), 4,414 curve legs over 2,207 packages (2.0), and 470 CCP-switch legs over 235 switches (2.0). Dividing leg counts by legs per package is the first check.
- **Spreadovers.** A spreadover is a swap-versus-government-bond spread. Buying the bond and paying fixed on the swap is a widener; the opposite is a tightener (Clarus, Mechanics and Definitions of Spreadovers, May 2015). Identify spreadovers from the package fields and price, not from the bond leg, which is not in the print.
- **Invoice spreads.** Match a swap's effective date to a futures delivery date and its maturity to the CTD bond's maturity. Exact matching is a floor on activity: 744 matches in 22,219 analysed prints (about 3%) for August 2014 (Clarus, Invoice Spreads, Sep 2014). A 2014 match count is a floor, not the market size.
- **CCP-basis pairs (USD IRS, CME versus LCH).** (a) Keep spot-starting, cleared, outright prints; exclude curves, flies, spreadovers and compression. (b) Pair prints with identical timestamp, size and maturity. (c) Confirm each leg's clearing house against a same-day venue end-of-day mark. (d) The adjacent leg's price gives the basis. Without the venue cross-reference, false positives equal true positives (24 and 20 suspected pairs in 5y and 10y, cut to 12 and 10 with it; Clarus, Identifying CCP Basis Trades, Mar 2016). Identification is retrospective (T+1).
- **IMM roll.** Naive method: over the first 18 days of March, compare swaps starting on the March IMM date with those on the June IMM date; assume the smaller is rolled and double it, because both legs trade. Trade-by-trade method: identical timestamp and benchmark maturity on March- and June-start legs. The naive method overstates (it assumes all March positions roll); the trade-by-trade method misses rolls executed as separate legs. Report both as a range (Clarus, IMM Roll for Swaps, Mar 2015). Roll timing: the Friday before expiry carried more than 21% of rolled risk, the busiest four sessions over 71%, and rolls were about 15% of the day's volume the day before expiry. Strip roll volume (and compression) before reading liquidity on those otherwise quiet days.

### 6. Dealer offsetting
Two measures. Use both, because they answer different questions.

**(a) Mean Offsetting Ratio (MOR).** After a large customer trade, how much DV01 does the dealer trade in the opposite direction within a window, net of same-direction trading?
`MOR_L = (DV01_opposite − DV01_same) / |DV01_L|` over `(t_L, t_L + W]`, same dealer and currency. The mean is taken over large trades L. Large trades with no later flow count as 0. Fleming et al. count only large trades that add to the dealer's running intraday direction; set the `large` flag that way.
- Reported values (Fleming et al., Mar 2012): USD 0.5, 0.5, 0.7, 0.7 at 30m, 1h, 4h, 8h; EUR 0.7, 0.7, 0.6, 0.5; GBP 0.6, 0.6, 0.5, 0.5; JPY 0.7, 0.6, 0.4, 0.3. About 60% of large-trade DV01 is offset within 30 minutes. This excludes bond and futures hedges, so true offset is higher.
- Reading: MOR near 0.5 at 30m means half of a large trade's risk is passed on inside half an hour, and the rest is warehoused or hedged later. A rising MOR across windows means the desk is still working the risk.

**(b) Offset sign (Riggs et al., JFE 2020).** Per dealer, product and day, take the net on customer-facing venues (D2C) and the net on dealer-to-dealer venues (D2D).
`sign = −1` if opposite, `+1` if same, `0` if one side is zero, dropped if both are zero. "Large D2C" days are those where the dealer's |D2C net| is above its own average.
Result: 34–35% of dealer-days are opposite, and 38–39% on large-D2C days. About a third of D2C trades are offloaded in D2D the same day. D2D prints can therefore be hedges of client flow, not independent views. Riggs et al. use index CDS data. Transfer to rates is an inference that needs testing.

### 6b. Direction inference from public prints (no dealer tags)
Public prints carry no buyer or seller flag, so direction is a model output. Treat it as a probability, not a fact.
- **Sign by price versus an independent mid.** Sign = traded rate versus a contemporaneous mid from a curve built from other quotes (or futures-implied levels). Paying fixed is a trade above mid, receiving below. Quote-midpoint signing beats the tick rule here because OTC prints are sparse and not in a single order book; check accuracy against any labelled sample you have (López de Prado, Advances in Financial Machine Learning, 2018; Hasbrouck, Empirical Market Microstructure notes, 2004). Validate with pseudo-labels from a second, independent mid; a mid reader that silently returns a stale snapshot is no coverage.
- **Decayed signed-DV01 ladder.** `ladder(t) = Σ over prints visible at t of signed_dv01 × (1 − 2·p_flip) × 0.5^(age / half_life)`, where `p_flip` is the probability the sign is wrong. Starting defaults, not validated: half-life 90 minutes (240 for blocks), 5-minute grid inside local trading hours, z-score window 10 days, test at a 60-minute horizon with |z| of at least 1. Visibility is execution time plus the class-specific dissemination delay (section 1). Remove prints unwound by lifecycle events at their unwind time; drop prints suspected to be curve legs.
- **Leakage audit.** Multiply every not-yet-visible print by a huge factor and flip its sign, then rebuild the feature: any change means look-ahead. Test lead-lag with a lagged correlation estimator built for asynchronous data (Hayashi-Yoshida) on increments, not on levels. Use day-clustered inference (day-block bootstrap), because intraday observations inside a day overlap.
- Treat packages as separate: a signed package flow (for example a swap-spread package) tests against the future change in that spread at 1 to 5 days with HAC errors and a placebo (for example the previous session's same-minute mid); report an explicit "uninformative, low power" verdict when the test cannot reject.

### 7. Dealer inventory and hedge model
- Notional is not risk. Long notional is receive-fixed; short is pay-fixed; gross adds offsetting risk; net is long minus short (McPhail et al., Apr 2023). Convert to DV01 (or 5y equivalents) before reading exposure.
- Market value sums NPVs since inception, not rate risk. A zero market value can carry large DV01.
- Dealers carry positive aggregate DV01 and non-dealers negative; the two roughly net to zero (McPhail et al., Apr 2023). Aggregate gross notional was USD 94.7tn against net USD 784bn, with aggregate DV01 of USD 585m (McPhail et al., Apr 2023).
- **Two-tier hedge model** (Mixon & Onur, CFTC OCE Staff Paper 2020-004, Apr 2020). Dealers hedge bespoke exposure with liquid futures and face basis risk `ρ`. With `γ_SD` the dealer risk aversion, `γ_FT` the futures market impact, `Q^S` the bespoke swap exposure and `I` index investment:
  `R = γ_FT / (γ_FT + γ_SD)` (equal to `(1/γ_SD)(1/γ_SD + 1/γ_FT)^(−1)`, in (0,1))
  Equilibrium futures position: `ρ·Q^S·(R − 1) − I·R`.
  Neutral hedge: `−ρ·Q^S`. As risk aversion rises or futures impact falls to zero, `R → 0` and dealers move toward the neutral hedge. Illustration with `γ_SD = γ_FT = 1`, `ρ = 1`, `Q^S = 100`, `I = 0`: `R = 0.5`, futures `−50`, against a neutral `−100` (formula arithmetic, not a dataset). Source equations are partly garbled in extraction; check the coefficients before quoting.
- **Hedge-ratio regressions.** Regress the change in dealer futures on the change in client swap exposure, by tenor bucket (0-3m, 3m-1y, 1-2y, 2-3y, 3y+). Expect negative slopes. Mixon & Onur report an index-swap coefficient of −0.96 (t −6.40) and a single-name coefficient of −0.44. Per-dealer medians are −0.78 and −0.52. A commodity 13-15 month swap hedged in short-dated futures gave 0.5-0.6. These are US commodity results; they do not transfer to G10 rates without testing.
- Net futures against the swap book. Two client types with opposite exposure leave tenor basis even when the book is flat. A hedge ratio below 1 on long-dated exposure hedged in front contracts is expected, and a tighter ratio can reflect tenor migration, not better correlation.
- **Bilateral discounting risk.** Split the book into DV01 by segment and into discounting risk (PV sensitivity to the discount curve). Bilateral trades were about 15% of gross notional but about half of gross market value (J.P. Morgan, Bills, Bonds and Basis, Feb 2020). Falling rates raise the negative PV of paid bilateral positions, so dealers become buyers of long-end FF/Libor basis in a rally (net about USD 80m per bp for dealers in that note).

### 8. Flow-to-level models: convexity, duration and issuance
- **Dynamic-hedger threshold.** Hedgers act on net moves above about 20bp, path-dependently against their last rebalance. A sticky swap spread in a selloff can mean hedgers are not yet covered (J.P. Morgan, Dynamic hedgers are long, Sep 2019).
- **Dynamic-hedger duration.** Hedge duration delivered over large moves (MBS, variable annuities, short gamma from straddle sellers, long-dated callables). In one 21-26bp rise in 10y, about USD 90bn of 10y equivalents came through (J.P. Morgan, Dynamic hedgers are long, Sep 2019). Programmatic short-gamma flow was about USD 500mn/day of 1m×10y ATM straddles held to expiry (J.P. Morgan, Zen and the art of gamma maintenance, Mar 2018). The mechanism is in `flow-mbs-convexity-hedging`.
- **Swap spread beta.** Rolling three-month beta of daily swap-spread change on swap-yield change was positive through 2019, up to about 0.10 to 0.15. Paying in selloffs widens spreads; receiving in rallies narrows them.
- **Issuance swapping.** Match high-grade issues to SDR prints. In the 8 trading days after Labor Day 2018, over USD 85bn of supply came; non-financials were 71% of gross, under 8% swapped (13% in 2016 and 14% in 2017) (J.P. Morgan, Issuance, pensions and long-end spreads, Sep 2018). Gross issuance is not swapping. Check the financial versus non-financial mix and the SDR matches. A receiving model: SSA benchmarks and fixed-rate financials swapped; corporates only when matched; callables as Bermudans struck at par; financial issuance falls in the roughly four-week earnings blackout.
- **Callable vega supply.** Track gross, redeemed and net callable issuance (Formosa versus other; financial versus non-financial). Convert to normal parallel vega, assuming financial and government callables are swapped and non-financial are not. Callable supply cheapens the long-dated surface (Citi, Liquidity, vega and convexity, Mar 2020: 2020 year-to-date gross USD 20.62bn, vega USD 46.8mn).
- **Duration-supply gauge.** Net supply (issuance less central-bank purchases; UST also net of buybacks) in USD mn per bp, quoted as a multiple of a reference average (the Goldman note uses the 2025 average). Desk read, October 2026 (Goldman Sachs, The Week That Was / Will Be, Oct 2026): G4 next week about USD 101mn/bp (1.2x the 2025 average); UST about USD 70mn/bp (1.7x); EGB about USD 9mn/bp (0.3x); JGB about USD 20mn/bp net of the central bank (2x).

### 9. Structured-note and tail-strike flow
- **Structured-note hedge vectors.** Map the note's embedded options to a dealer hedge. Example from a 7% daily-accrual inversion note on 2s30s (Merrill Lynch RateLab, Jun 2008): the buyer is short daily digitals on 2s30s, so the dealer is long them. Per USD/EUR 100m of notes the dealer hedge was: receive 450m 10y against pay 150m 30y, and sell 400m 4y-into-2y straddles against buy 75m 4y-into-30y straddles. Scaled to 15bn of notes (×150): receive about 67bn 10y, pay about 22bn 30y, sell about 60bn 4y-into-2y straddles, buy about 11bn 4y-into-30y straddles.
- A digital is negatively convex once in the money: crossing the strike flips the Greeks and forces rebalancing. Watch the distance from the strike on the convexity-adjusted forward spread.
- **Tail-strike swaption flow.** Keep prints with strike at or above 6% when 10y forwards are about 3.2-4.2%, which is typically 200bp or more out of the money (about 180-280bp across that range). Classify each as investor buy, sell or uncertain. Exclude likely packages. Aggregate DV01 weekly and daily. Tail strikes have few natural end users, so flow there reveals high-rate views, but the motive is "ultimately unknowable from SDR data" (Morgan Stanley, Investors Are Paying for Protection Against 6% Rates, Jul 2026).
- Separate vega-motivated from delta-motivated flow by expiry before reading direction. Long expiries (10y10y, 20y10y) are vega-dominated (vol specialists); intermediate (2y10y, 3y10y) are delta-driven (macro); 5y20y is a buy-and-hold insurer expression (same source).
- High-strike payer demand steepens skew and worsens the street's dV/dr profile (Morgan Stanley, Jul 2026; Goldman Sachs, Oct 2026).

## Worked examples

**A. DV01 sizing (check).** USD 100m, 10y, receive 2%: DV01 about 89.8k per bp (method 3). This matches the McPhail et al. NPV swing of about 90k per bp.

**B. Mean Offsetting Ratio (illustrative arithmetic).** A dealer receives a large USD trade with DV01 +50k. In the next 30 minutes it trades −30k (opposite) and +5k (same). `MOR = (30 − 5) / 50 = 0.5`, the same value Fleming et al. report for USD at 30m. Add a −10k print at 40 minutes: it is outside 30m and inside 1h, so 1h gives `(40 − 5) / 50 = 0.7` (an arithmetic illustration; the reported USD 1h value is 0.5 and 0.7 is the reported 4h and 8h value).

**C. IMM roll (Clarus, IMM Roll for Swaps, Mar 2015).** 5y March-start USD 15.999bn against June-start 13.25bn. Naive roll = 2 × 13.25 = USD 26.5bn. Across tenors the naive estimate is USD 101.1bn, or USD 73.5m DV01. Trade-by-trade DV01 was USD 39.9m. The source describes this as 39% of the naive estimate, but 39.9 / 73.5 is about 54%. The source also says the March contract saw nearly USD 50m of risk, of which the trade-by-trade 19.95m (39.9m divided by 2 legs) is about 40%. Check the denominator and the one-leg versus two-leg basis before quoting either ratio.

**D. CCP switch cost (Clarus, LCH-CME Switch Trades and Margin Management, Jun 2014).** A USD 285m 10y switch (DV01 250k) cut LCH initial margin by USD 38m and CME by USD 10m: total USD 48m, 16% of the USD 305m margin. Net DV01 is unchanged; one-sided DV01 at each CCP shrinks, so margin falls at both.

**E. Basis levels (Clarus, CME-LCH Basis Spread, May 2015; Identifying CCP Basis Trades in the SDR, Mar 2016).** The LCH-CME basis averaged about 0.15bp historically and reached about 2bp in May 2015, with a typical bid-offer of 0.25bp. On 28 Mar 2016 the mid was 0.95bp at 5y and 1.75bp at 10y. Use benchmark tenors only; the term structure is upward-sloping, so the market does not expect reversion.

**F. Record-volume week (Clarus, Swapalypse Now, Apr 2025).** 10y spreads moved 7bp more negative on at least USD 31bn of risk over more than 600 trades (typical about 250); 30y on at least USD 10bn over 425 trades (typical 135). Trade counts rose 2.4x and 3.1x: the activity is real, not one large print.

## Signals & interpretation
- **Volume spike check.** Confirm a notional spike with trade counts and DV01. A notional spike with flat counts is one large print or a re-couponing (method 2).
- **Package-adjusted activity.** Read outright direction only after removing packages and compression. If packages make up a large share of DV01, direction from outright prints is unreliable.
- **Offset reading.** MOR near 0.5 at 30m and rising to 0.7 by 4h-8h means the desk is working risk over the day. Opposite-sign share above about 38% on large-D2C days means dealers are actively offloading. These are reader inferences from the cited studies, not thresholds those studies set.
- **Convexity trigger.** A move beyond about 20bp in 10y raises the chance of hedger-driven flow; watch swap-spread beta for paying or receiving pressure.
- **Duration gauge.** A reading far above its reference average (the gauge is a ratio to the average, for example 1.7x) signals heavy supply that the market must absorb. Use it as a context flag, not an entry rule.
- **Tail-strike net flow.** Net buying of high-strike payers after a rates rally is a view on high rates; net selling of far-out protection is a yield-decline or term-premium-compression signal. Require at least four weeks of net direction before treating it as a trend (reader threshold).
- **Flow shock persistence.** Supply shocks overshoot and recover slowly because of search and capital frictions, so a flow-driven move is a mean-reversion candidate rather than an instant reprice (Duffie, Dark Markets, 2012).
- **Crowding check.** When European government spreads stress, US spreads can tighten through stops (2022 and 2025 episodes, GS cuRated, Oct 2026). Before a regulatory catalyst, crowded positioning becomes the pain trade when vol rises (Clarus, Swapalypse Now, Apr 2025).

## Market differences (G10)
- **USD:** SDR coverage is US-nexus trades. The CME-LCH basis and the CCP switch are USD-specific in the sources. Spreadovers have traded on-venue since the mandate of 15 June 2014. Re-estimate block caps from the data for each currency.
- **EUR:** Desk location, not who trades, drove a fall in the US-to-non-US share of EUR volume from about 20% to 5% after SEF rules (Benos et al., Jul 2016). Use desk location with care. Intraday ECB-day flow peaks in the 16:00-16:15 CET window (Clarus, ECB June Meeting, Jun 2014).
- **GBP:** Gilt maturities in GBP swap prints help identify synthetic floaters (asset-swap structures). Desk gilt supply is small (about USD 2mn/bp in 2026).
- **JPY:** Official FX intervention shows up through custody and repo holdings, not in SDR prints. JGB net supply is central-bank-adjusted.
- **CAD, AUD, NZD, CHF, SEK, NOK:** Sources give no SDR flow analysis. Do not apply the USD or EUR thresholds without testing.
- Detail and per-currency numbers: [market-notes-g10](references/market-notes-g10.md).

## Pitfalls
- Never read gross notional as risk. Net it and convert to DV01 first.
- Public notionals are capped and rounded. Block size is understated by design. A print at the cap is a lower bound.
- Filter all-nines sentinels as missing. Netting must apply corrections, cancels and errors.
- Compression, clearing legs, allocations, transfers and re-couponing are not price-forming and inflate volume.
- Count packages, not legs. Exclude packages before reading outright direction. Package type is not a field.
- Separate vega-motivated from delta-motivated flow by expiry before reading direction.
- D2D prints can be dealer hedges of client flow. Do not read them as independent views.
- The MOR and offset-sign results rest on dealer-tagged data. Without it, do not estimate offsetting from public prints.
- Offset ratios exclude bond and futures hedges. True offset is higher than the ratio shows.
- Gross issuance is not swapping. Check the matches.
- Convexity-hedger flows are threshold-based (about 20bp) and path-dependent.
- Crowding can cause stop-driven spillover across markets. Check the mix of closing and opening trades.
- Naive IMM-roll estimates overstate. Trade-by-trade estimates miss manually legged rolls. Report a range.
- The CFTC block-venue interpretation lapsed on 15 Dec 2015. Re-check the rules.
- The 2010 and 2014 samples are low-rate, pre-cap periods. Do not generalise their notional thresholds.
- Muni, index-CDS and US commodity results do not transfer to G10 swaps without testing. The transfer is an inference.
- Anonymous-tape matching (municipal-bond methods) gives a lower bound on round-trip cost, and chain matching needs dealer identities. Use it as a method for a dataset that has the fields, not as a G10 swap conclusion (Green et al., 2004; Li & Schurhoff).
- FX option sentiment ideas (cumulative put/call, notional-weighted strike) ported from the FX literature rest on one year of data and are weak. Use only as a cross-check.
- A desk skew in quotes is not a view. Check inventory before reading it as one.
- Public SDR data does not tell you who traded or the direction. State the confidence and the gap every time.

## Output
Return:
1. **Flow table** (one row per currency, product and window): price-forming print count, DV01 (capped prints flagged), package and compression share, customer-facing versus dealer-to-dealer share, venue.
2. **Dealer table** (only with dealer-tagged data): window, MOR, opposite-sign share, number of large trades, dealers in sample.
3. **Structure table**: structure, legs per package, package count, DV01, direction, classification confidence (high, medium, low), censoring flag.
4. **Positioning call** (if a direction is inferred): structure, expiry, DV01, direction, confidence, and what would change it.
5. **Data flags**: censoring, forward-start rule used, cleaning rules applied, sentinel counts, rule dates (for example the lapsed CFTC interpretation), and missing dealer data.
6. **Hand-off**: to `rv-trade-idea-writeup` for a trade idea, and to `rv-devils-advocate` for the pre-trade challenge (crowding, what would make the flow read wrong).

## Scripts
- [`scripts/sdr_flow_metrics.py`](scripts/sdr_flow_metrics.py): par fixed-leg DV01 (with `dcf_scale` for ACT/360), horizon and P&L translation, price-forming netting, offset sign, Mean Offsetting Ratio, naive IMM roll, HHI. The CLI takes the canonical `flows_trades` CSV and the canonical `dealer_flow` CSV (columns `dealer_id, exec_ts_utc, ccy, dv01_ccy, is_large`; the script also accepts the short names `ts, dealer, dv01, large`). `python -I scripts/sdr_flow_metrics.py --selftest` checks known cases (for example MOR 0.48 and 0.68, DV01 about 89.8k, 26.5bn IMM roll).

## Related skills
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): futures positioning and surveys, the non-swap view of the same positioning
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension, insurer and bank ALM demand behind long-end receiving
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): MBS and callable convexity hedging that drives threshold flows
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable and structured-note vega supply converted to surface effects
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CME-LCH basis levels, switches and margin costs
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): spreadovers and asset swaps, the swap-versus-bond spread the flow moves
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): how the structures seen in the tape are traded and packaged
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 and key-rate conventions used for sizing
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): liquidity measures and flow-toxicity indicators
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale data, holidays and roll stitching
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical `flows_trades` and related tables
- [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): invoice-spread trade construction behind the matches detected in the tape
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): futures and IMM roll mechanics behind roll volume
- [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md): skew and tail-strike swaption pricing behind high-strike flow
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag tests for flow-to-price claims
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): issuance and auction cycles that feed swapping flow
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-currency fixed-leg frequency and day count for DV01 sizing
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): pre-trade challenge on flow-based ideas

## References
- Fleming, Jackson, Li, Sarkar & Zobel - An Analysis of OTC Interest Rate Derivatives Transactions: Implications for Public Reporting (FRBNY Staff Report 557, Mar 2012, rev. Oct 2012): price-forming filter, DV01 size buckets, Mean Offsetting Ratio, market structure.
- Benos, Payne & Vasios - Centralized trading, transparency and interest rate swap market liquidity (Bank of England Staff Working Paper 580, Jul 2016): cleaning recipe, dealer classification, SEF and mandate effects, desk-location fragmentation.
- McPhail, Schnabl & Tuckman - Do Banks Hedge Using Interest Rate Swaps? (CFTC OCE Staff Paper 2019-011, Apr 2023): notional versus DV01, dealer and non-dealer exposure.
- Mixon & Onur - Risk Appetite and Intermediation by Swap Dealers (CFTC OCE Staff Paper 2020-004, Apr 2020): two-tier dealer hedge model and hedge regressions.
- Riggs, Onur, Reiffen & Zhu - Swap trading after Dodd-Frank: Evidence from index CDS (Journal of Financial Economics 137, 2020): offset-sign method, RFQ evidence (index CDS, transfer to rates untested).
- CFTC - Technical Specification: Parts 43 and 45 swap data reporting and public dissemination requirements (v3.1, Aug 2022; v3.0, Sep 2021): field dictionary, dissemination rules, netting, sentinels, caps.
- Clarus Financial Technology - Identifying Customer Block Trades in the SDR Data (Oct 2015): block-flag venue inference, average size by venue, cap bias.
- Clarus Financial Technology - The IMM Roll for Swaps: What is it and what are the volumes? (Mar 2015): naive and trade-by-trade roll estimators, roll timing.
- Clarus Financial Technology - CCP series: CME-LCH basis and term structure (May 2015), LCH-CME switch mechanics and margin (Jun 2014), CCP-basis pair identification with SEF cross-reference (Mar 2016): basis levels, switch margin saving, false-positive counts, margin reasoning.
- Clarus Financial Technology - Mechanics and Definitions of Spreadovers (May 2015): spreadover sign and venue share.
- Clarus Financial Technology - SDR: Trading Venues and Packages (Jan 2023): Part 43 platform and package fields, venue codes, package taxonomy.
- Clarus Financial Technology - SOFR Swap SEF Volumes (Jun 2024) and Swapalypse Now (Apr 2025): package leg counts, venue shares, record-volume week and trade-count confirmation.
- Clarus Financial Technology - ECB June Meeting: intraday DV01 profile (Jun 2014): intraday timing around policy events.
- Clarus Financial Technology - Invoice Spreads (Sep 2014): invoice-spread detection and match floor.
- J.P. Morgan - Dynamic hedgers are long, banks are short (Sep 2019) and Zen and the art of gamma maintenance (Mar 2018): dynamic-hedger duration, 20bp threshold, swap-spread beta, issuance receiving model, programmatic short-gamma supply.
- J.P. Morgan - Issuance, pensions, and long-end spreads (Sep 2018): issuance-swapping identification and 2018 shares.
- J.P. Morgan - Bills, Bonds, and basis (Feb 2020): dealer DV01 versus discounting risk, bilateral share of gross market value.
- Morgan Stanley - Investors Are Paying for Protection Against 6% Rates (Jul 2026): tail-strike classification, expiry-by-tail heatmap, dealer gamma profile.
- Goldman Sachs - The Week That Was / The Week That Will Be (Oct 2026): duration-supply gauge and desk supply by market.
- Goldman Sachs - GS Macro, cuRated (Oct 2026): crowding check and European-to-US spread spillover.
- Citi Research - Liquidity, vega, and convexity (Mar 2020): callable vega supply and 2020 issuance (partial read; heat maps not used).
- Merrill Lynch - RateLab: "Another Fine Mess" (Jun 2008): structured-note dealer hedge vectors and forced-unwind mechanics.
- Düring - Fixed Income Trading and Risk Management: The Complete Guide (Wiley Finance, 2021): compression, novation, re-couponing, RFQ winner's curse.
- Green, Hollifield & Schurhoff - Financial Intermediation and the Costs of Trading in an Opaque Market (working paper, Jul 2004; municipal bonds, methods only): round-trip matching filters.
- Li & Schurhoff - Dealer Networks (Swiss Finance Institute Research Paper 14-50; Journal of Finance, forthcoming; municipal bonds, methods only): chain matching and dealer-network centrality.
- BofA Global Research - SDR: What do FX options flows tell us? (Feb 2021) and FX Quant Primer (Oct 2018): FX option-flow sentiment method (ported, cross-check only).
- Duffie - Dark Markets: Asset Pricing and Information Transmission in Over-the-Counter Markets (Princeton University Press, 2012): OTC opacity and supply-shock dynamics (partial read; coefficient tables not used).
- Clarus Financial Technology - Compression in USD Swaps (Dec 2014): compression hallmarks, fee-data caveat, block-cap bias, Nov 2014 shares.
- Clarus Financial Technology - The Principals of Swap Trading (Jul 2014), Mechanics of Asset Swaps and Government Bond Swap Spreads (May 2015) and Mechanics and Definitions of Short Term Interest Rate Futures (Jul 2016): desk DV01 by tenor and reporting bias, gilt-maturity matching, volume versus liquidity.
- tpSEF Inc. - Rulebook, Appendix B: Swap Specifications (May 2021): product taxonomy labels, cleared sub-products, CAD and AUD conventions.
- BofA Global Research - FX intervention primer: G10 (Jul 2024): official-flow tracking through custody and foreign repo pool.
- Federal Reserve Bank of New York - Liberty Street Economics, Dealer Trading and Positioning in Floating Rate Notes (Mar 2018): auction-cycle dealer positioning.
- López de Prado - Advances in Financial Machine Learning (Wiley, 2018) and Hasbrouck - Empirical Market Microstructure (teaching notes, NYU Stern, 2004; partial read): trade-signing rules, quote-midpoint signing, inventory and skew.
- O'Hara - Market Microstructure Theory (Blackwell, 1995; partial read, equity-focused): inventory skew versus views, block trades.
- Quantitative Finance Stack Exchange - Downward Sloping Swap Spread Curve (Dec 2020; practitioner discussion, weak source): ALM receiving in the EUR long end.
