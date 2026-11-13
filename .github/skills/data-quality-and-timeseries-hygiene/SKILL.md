---
name: data-quality-and-timeseries-hygiene
description: 'Cleans and validates the time series that G10 rates relative-value signals are built on. Covers holiday and weekend rows, carry-forward and stale quotes, never forward-filling, snap-time (fixing time) consistency across legs and markets, futures roll stitching and back-adjustment, generic and on-the-run series, benchmark switches and LIBOR/SOFR splices, structural breaks, units and tick-grid checks, outliers and bad prints, and point-in-time (release-date) look-ahead. Use when a z-score, spread, fly, basis or backtest looks too good, jumps on a roll or holiday, mixes closes, or before trusting any history. Triggers - stale quote, holiday, ffill, forward fill, generic, continuous contract, data cleaning, roll gap, back-adjust, on-the-run switch, WI roll, snap time, fixing time, EOD, outlier, bad print, bad tick, spike, look-ahead, point-in-time, vintage, structural break, splice, rebasing, constant maturity. Table schemas and adapters: data-contract-and-adapters.'
---

# Data quality and time-series hygiene

Every RV signal (z-score, PCA residual, fly, basis, backtest P&L) is a function of a cleaned series, and most
"opportunities" that are too good are data artefacts: a carried-forward holiday close, two legs snapped two hours
apart, an unadjusted futures roll, a benchmark switch, a mixed-unit column, or a revised number used before it was
published. This skill is the pre-flight for any history. The rule throughout: **flag, label and explain, never
silently fix, never forward-fill, never delete**. Rows stay in the store with `data_ok=false` and a `dq_reason`
(the `_common` columns of the canonical tables), and consumers choose.

## When to use
- Before computing any z-score, half-life, PCA or regression on a history you did not build yourself.
- A spread/fly/basis series jumps on a roll date, an auction date, a holiday or a quarter-end.
- Two legs of a spread come from different sources, closes, time zones or contract-roll rules.
- Building or auditing generic/continuous series, constant-maturity series, or long histories that cross a benchmark
  change (LIBOR to SOFR, EONIA to ESTR, CDOR to CORRA, rebased CPI).
- A backtest looks suspiciously good: run the look-ahead and known-answer checks in "Verify the checker".

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). Never invent
values; if a calendar, tick size or roll map is missing, ask the user or the data adapter.

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Business-day and early-close calendars (market and exchange kept apart) | `calendars` | per `calendar_id`, past and future | cash and futures holidays differ |
| Any price/rate panel to audit | `curve_par`, `bond_quotes`, `fut_quotes`, `stir_quotes`, `opt_quotes`, `vol_surface`, `swap_spreads` | daily, one `snap` per series | audit per (series, snap), never across snaps |
| Tick size, expiry, delivery dates, quote type | `fut_static`, `opt_static` | one row per contract | read `tick_size_px`; do not hard-code a tick |
| Generic-to-specific mapping and roll rule | `roll_map` | per generic id and date | rule must use only information known that date |
| Source-symbol mapping, unit served, multiplier | `symbol_map` | versioned by `valid_from` | the unit/multiplier test lives here |
| Publication time of anything released | `rate_fixings`, `infl_fixings`, `macro_series`, `positioning`, `auctions` | one row per vintage with `pub_ts_utc` | revisions are rows, never overwrites |
| Index definitions, ceased dates, fallbacks | `rate_indices` | static | builds the break register |

## Method
Run these stages in order. Later stages assume earlier ones; for example outlier detection after stale removal, and
after roll stitching, otherwise roll gaps and post-stale catch-up moves are flagged as "outliers".

### 0. State what the series is
Before any statistic, record: index/leg/collateral (a "repo rate" or "CCBS" label can hide a regime change), `snap`,
unit, price field (mid vs last), curve/contract roll rule, and vendor transformations (imputation, smoothing,
end-of-period convention). Series built with different price fields or roll rules are not comparable. Check what a
benchmark is made of before reading a move: a tri-party benchmark that includes private-collateral trades fell
below the Fed's reverse-repo rate on 18 Jul 2024 while the Treasury-only benchmark stayed in range, a
construction artefact not a signal (Conks, The Repo Market Dislocation Part I, 17 Aug 2024; Conks, Money Market
Update, 12 Aug 2024). Cross-check benchmarks that should co-move before treating any one as "the" rate.

### 1. Units, identifiers and schema
- Units live in column names (`_pct`, `_bp`, `nvol_bp`, `_px`); never guess a unit from magnitude. Decimal vs % vs bp
  errors are 100x-10,000x and still look plausible: a basis archive stored as decimals marked a book 10,000x too
  small so it looked flat; a notional-per-unit field read as per-bp gave 10,000x fees; fly yields in % were compared
  with bp thresholds (Internal research notes, data pitfalls, 2026). Convert only through `symbol_map.multiplier`.
- Reject, do not skip, a required column that is present but entirely null (a NaN time-to-maturity silently emptied
  a universe on most dates).
- Tick-grid and band check on every mapped price: price / `tick_size_px` must be a whole number (`off_grid` in the
  script) and sit inside a plausible band. Vendor codes collide across products, so an on-grid but wrong-product price
  passes the grid test and fails the band test. A listed price off its grid is informative: cash-settled STIR final
  settlements are almost never on the grid while live prints are (18/18 ending contracts off-grid, 32/32 starting
  on-grid) (Internal research handover, 2026). Read the tick from `fut_static` (sources differ for the SOFR front
  contract, 0.0025, vs deferred, 0.005).
- Yields are comparable only after conversion: bond-equivalent yield `BEY = 2(sqrt(1+y) - 1) ~ y - y^2/4` for
  annual-to-semi; discount vs simple-interest bills (`P = 100 - r*DCF` vs `P = 100/(1 + r*DCF)`); do not compare
  annualised rates quoted over different periods (Düring, Fixed Income Trading and Risk Management, 2021).
- Listed vol units differ by product (normal price vol vs lognormal price vol with ratio 1e4/ModDur_ctd, lognormal
  price vol as a decimal). Convert to normal bp before pooling (Internal research handover, 2026). Normal (bp) vol =
  relative (lognormal) yield vol x yield level; do not assume bp vol scales with the rate level (Ilmanen, Understanding the Yield Curve Part 5, Sep 1995). See
  [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md).
- Parsing: UST bond quotes in 32nds, third digit in eighths of a 32nd: `99-24+ = 99-244 = 99.765625`, `99-245 = 99.76953125`; some futures-option feeds use quarters for the third digit instead (there `99-245` is 24.5/32), so confirm the convention per feed; store decimal only. Coupons of fixed-rate issuers
  are mostly multiples of 1/8, so 3.152 is a probable typo (decimal coupons are normal for JGBs and SPGBs). ISINs are
  12 characters with a Luhn check digit; implement the standard Luhn and test it on known ISINs (the printed
  worked example in at least one text has misprints). Taps can carry a temporary ISIN later fungible into the parent
  line, so map issue-level series onto the parent (Düring, 2021).
- Futures month codes differ by family. On legacy IBOR futures the code is the expiry month; on compounded-RFR futures
  it is the start of the reference quarter (the 3M SOFR contract coded V, October, references the October-to-January
  quarter and expires the following January). Mixing families shifts dates by a quarter (FactSet, Interest Rate Future
  white paper, 23 Mar 2023). AUD and NZD bank-bill futures are treated by that source as yield-convention contracts,
  valued through a synthetic bond price, so the value of a tick is not a constant per bp: read the quote type and
  tick value from `fut_static` instead of assuming linear 100 minus rate.

### 2. Calendars, weekends and holidays
1. Build the expected date set from `calendars` for the relevant `calendar_id`, not from "weekdays". Cash and futures
   calendars differ; use the publisher's calendar for a fixing and the exchange's for a futures settle.
2. **Missing business day** (expected, absent): a gap, to be reported. **Row on a weekend/holiday**: a suspect, flag
   `non_business_day_row`.
3. **Carry-forward rows**: a row where every field is unchanged vs the previous row is the vendor carrying the prior
   close over a holiday. Drop from the analysis panel (keep and flag in the store) and log every date. Per-series: see
   stale detection below (Internal research backtest specification v0.4, Oct 2026).
4. **Never forward-fill across a gap.** `ffill`/`bfill` manufacture zero changes (understating vol, creating fake
   mean reversion) or look-ahead (`bfill`). If a model needs a value on a non-business day, use that market's own
   weighting rule instead.
5. Inner-join legs on date only after steps 2-3, then drop weekends. Report the **effective** start (raw start plus
   warm-up of 252 business days for rolling statistics), not the raw start.
6. Observance rules differ and silently shift dates: US, a Saturday holiday is observed on Friday and a Sunday one
   on Monday; UK, a New Year falling on a weekend moves to the following Monday and substitute days appear (Mon 27 and
   Tue 28 Dec 2021, so 25 Dec 2021 + 1 business day following = 29 Dec 2021); in the euro area a weekend holiday is
   simply lost (Darbyshire, Coding Interest Rates, c.2024, Ch.4). Watch one-offs (London closed 8 May 2023 for the
   coronation).
7. Date arithmetic under modified-following is not invertible without the roll day: 28, 29 and 30 Mar 2001 + 6M all land
   on Fri 28 Sep 2001. Keep an explicit end-of-month flag; never auto-infer IMM or roll dates (Darbyshire, 2024).
8. Grade every date rule with an exact identity: `as_of + days_to_expiry == expiry`. A +/-1 day misalignment between
   vol and curve data still matched levels to ~2% in the median but widened dispersion (IQR) 30x. An expiry rule that
   ignored holidays returned Christmas Day for a listed option; the holiday-aware rule matched 263/263 (Internal
   research handover, 2026).
9. Settlement date is the economic date: "for value" means settlement, not trade date. Prices are adjusted for
   non-standard settlement (Düring, 2021, p.117). Futures open interest and volume reach public sources with a
   1-2 day lag (volume close to real time); lag them in backtests.
10. Fixings that accrue over non-business days need day weights: in 3M compounded-RFR futures `d_i` is the number of calendar
    days a fixing applies (Friday's covers Fri-Sun, `d = 3`); arithmetic-average contracts carry the prior business
    day's fixing over weekends and holidays (Huggins & Schaller, SOFR Futures and Options, 2022, Ch.2/4). See
    [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md).
11. Turns and month/year-end jumps are real data, not errors: label them (`turn`) instead of removing them from the
    store; strip them only inside a curve-building step and reinsert (see
    [fi-curve-construction](../fi-curve-construction/SKILL.md) and the TOY numbers in
    [references/worked-examples.md](references/worked-examples.md)). A quarter-end SOFR spike on its own is not a
    scarcity signal; flag reporting dates before reading it (Conks, Money Market Update, 10 Oct 2024).

### 3. Stale data
Run all four tests; they catch different failures.
1. **Panel carry-forward** (above): all columns unchanged vs prior row.
2. **Per-series run length**: flag the repeats inside a run of `>= min_run` identical observations. Choose `min_run`
   from the series, not a constant. For a series quantised at tick `q` with daily s.d. `sigma`,
   `P(unchanged) ~ q / (sigma*sqrt(2*pi))`, and `r` consecutive repeats have probability `p^r`. Take the smallest `r`
   with `p^r < 1e-4`, `min_run = r + 1` (script: `min_run_for`). Worked: `q = 0.01`, `sigma = 0.05` gives `p = 0.080`,
   `r = 4`, `min_run = 5`. A policy-pinned overnight rate or a front STIR contract legitimately repeats for days: raise
   `min_run` or whitelist by meeting calendar, do not drop it.
3. **Stale gate at signal time**: no stale input in the last 3 business days of any series used is a hard entry
   gate (stale inputs manufacture spurious signals) (Internal research backtest specification v0.4, Oct 2026).
4. **Structure checks**: a term structure identical across all terms on most days means the source is not observing
   terms (store it, set `data_ok=false`, reason `flat_term_structure`); off-the-run closes sitting 100% on the 1/32 grid
   are dealer quotes, not matrix prices (Internal research notes, 2026). Wide bid/ask on one pillar of a curve input
   (default: bid/ask above 3x the median of its two neighbours; the cited zig-zag case had 3.0bp against 0.3bp)
   marks a possibly stale quote. Stale quotes hurt most between closely spaced pillars, where discount factors must
   move more to fit and oscillation grows. Inspect forward overnight rates, which are the most sensitive view
   (Deriscope blog, How to build a SOFR Yield Curve in Excel using QuantLib, 18 Feb 2024).
5. **Coverage and match rates**: report per series and provider the share of expected dates present and the share of
   cache/join keys that matched. A "no data" marker may be a failed fetch, not an empty source; a join key whose pattern
   failed across a timezone offset matched only 66% (Internal research handover, 2026). Coverage differs by depth and
   point: front vs deep packs and ATM vs full smile have different availability, and a missing long tenor makes a
   forward such as 10y10y impossible on that source.
6. **Missing is NaN, never 0**: zero is a valid signal that demeaning or decay can turn into a position
   (Tulchinsky et al., Finding Alphas, 2015). Strip NaN/inf before any eigendecomposition.
7. Slow vendor refresh cadence = stale values between updates: record the cadence per source.
8. **Imputation is a model, not data.** If a curve or PCA model needs a complete grid, rebuild a missing tenor from its
   neighbours by PCA reconstruction on stationary, standardised inputs (best of three methods in a yield-curve test: MAE
   1.13 vs 2.45 and 8.02 for one missing month), impute components separately rather than their average, flag the cell
   `imputed`, and never feed an imputed value to a signal or a P&L as an observation (Dunis, Laws & Naim, Applied
   Quantitative Methods for Trading and Investment, 2003, Ch.13).

### 4. Snap time and synchronicity
- **Every leg of a spread, fly or basis must be snapped at the same instant, preferably the official settlement or
  fixing.** A vendor "EOD" bar nearest 17:00 New York against an exchange settle near 15:00 ET injected 1.82bp/day of
  noise into SOFR futures-pack convexity measures, whose true daily moves were ~0.55bp against levels of 1.34-6.81bp: noise
  larger than signal (Internal research handover, 2026). Keep `snap` and the exact `ts_utc` on every row and never
  mix snaps inside a series.
- Non-synchronous closes manufacture mean reversion and variance-ratio effects, so cross-market panels (UST vs Bund vs
  JGB) need one common snap (Dunis, Laws & Naim, Applied Quantitative Methods for Trading and Investment, 2003, Ch.2).
  When a common snap is impossible, use weekly mid-week (Wednesday) closes: they remove the Asia-vs-US T versus T+1
  lag and avoid payroll Fridays (Citi, Decomposing Global Rate Drivers Across EM Asia 5y5y, 13 Aug 2026).
- Non-contemporaneous legs create spikes that cannot be executed: a spiky implied-repo series came from futures and
  CTD prices not being contemporaneous and from comparing overnight SOFR with a term rate (Quantitative Finance Stack
  Exchange, Plotting Treasury Futures implied repo over time). Exclude an input whose value date is out of sync with
  the instruments around it (the spot overnight fixing published the next day was excluded from an OIS bootstrap)
  (Deriscope, 18 Feb 2024).
- Exchange "closes" are exchange-defined (last trade or an average of final minutes) and have limited economic meaning;
  prefer settlement (Düring, 2021). Curve snap times differ by centre and have changed (NOK/DKK/SEK moved to local
  close on 27 Apr 2018): see [references/g10-calendars-snaps-and-rolls.md](references/g10-calendars-snaps-and-rolls.md).
- Mid construction matters in rates because last trade goes stale: use mid of bid/ask; arithmetic first-depth mid is
  unstable on wide-tick contracts, size-weighted mid can be spoofed, and the multi-instrument least-squares mid (stack
  outright, spread and fly books, solve `A p = s`) forces consistency (Darbyshire, Pricing and Trading Interest Rate
  Derivatives, 3rd ed., 2022, Ch.19). Intraday liquidity is session- and event-dependent (Fleming, Mizrach & Nguyen,
  FRBNY Staff Report 381): sample away from 8:30, 10:00, auction times, FOMC and index-pricing times.
- Do not chain sessions: treat each day as its own sample and drop the first change of the day for intraday series
  (Hasbrouck, Empirical Market Microstructure, 2004, Ch.9). Mid-month samples dodge quarter-end funding spikes where
  that is the intent (Huggins & Schaller, Fixed Income Relative Value Analysis, 2024).

### 5. Futures rolls, generic series and benchmark switches
**Store specific instruments; build generics as views.** `roll_map(generic_id, date, instrument_id, roll_rule)` is the
only place a generic resolves to a contract, and the rule may use only information available at that date's close.
A raw generic series jumps by the calendar spread on every roll; z-scores and backtests on it are wrong.

**Choosing the roll rule is a recorded decision.** Sources disagree, so write `roll_rule` into `roll_map` and compare
rules on your data rather than trusting one:
- Treasury futures: rolling on first position day beats rolling on the IMM date (the IMM rule held the expiring contract
  a median 16 business days past the liquidity roll); a "deliverable contract" rule differs from first-position-day
  on 3.6% (10y) to 14.5% (2y) of days (Internal research notes on series construction, 2026). Other practice: first day of
  the delivery month for USD/CAD and last trade date of the 10y contract for EUR/GBP/JPY (vendor preference settings,
  2024); roll 5 days before the delivery month for implied-repo series (Quantitative Finance Stack Exchange).
- Liquidity default when no rule is mandated: roll when back-contract open interest share
  `OI_back / (OI_front + OI_back)` first exceeds 50% (`oi_max`), measured at close t-1, with a calendar fallback.
  Roll timing is partly predictable from history; CBOT contracts roll earlier (delivery any day of the month) while the
  Eurex BTP contract rolls later (Düring, 2021).
- Compounded-RFR 3M STIR futures: roll the second into the third listed contract, before a contract enters its
  reference quarter. Do not roll front to back as with Eurodollars: inside its reference period the front contract is
  sticky with decaying vol, and the Dec-19 to Mar-20 roll cost 138bp at the end of the reference quarter against 4bp at
  the start (Huggins & Schaller, SOFR Futures and Options, 2022, Ch.2). Never treat a front contract inside its
  reference period as a normal forward in a generic series.

**Stitch (back-adjust).** Roll decided at the close of `t-1`, new contract held from `t`:
`gap_t = P_new(t-1) - P_old(t-1)`, same snap, same date. Add `gap_t` to every observation before `t`
(additive; the last segment is untouched, so the series ends at the raw price; forward adjustment would instead match
the start). The roll-day change then equals the new contract's own change. Use `ratio_t = P_new(t-1)/P_old(t-1)` and
multiply history when the series must stay positive and returns must be preserved (additive series can go negative;
the non-negative alternative is `r_t = (rolled P_t - rolled P_{t-1}) / raw P_{t-1}`, `P~ = cumprod(1+r)`)
(López de Prado, Advances in Financial Machine Learning, 2018, Ch.2). Use **rolled** prices for P&L, **raw**
prices for position sizing and capital. Back-adjusted levels carry the cumulative roll gaps (carry), and every new roll
rewrites the whole history: use them for changes and P&L, never for level z-scores, mean reversion on levels or
as-of-`t` comparisons (use fixed-maturity or roll-matched series, and recompute as of each date in a backtest). For rate-like or spread series an additive gap is right (a bp gap is
what the roll costs); multiply only for price-return work. Cheaper alternative for pure seasonality or vol
studies: drop the daily changes inside the roll window (e.g. the 6th-10th of expiry months) instead of adjusting
(swapsball.net, Testing for seasonality, 2017). Failure case: if either contract lacks a price on `t-1`, refuse to
roll (the script raises) instead of interpolating.

**Roll monitoring**: `roll progress = OI_back/(OI_front + OI_back)`; roll-adjusted activity `|vol_front - vol_back|`
removes roll spikes but underestimates activity when both trade outright. Open interest is inflated where principal
clearing lets one account be long and short at once, and has roll seasonality: never infer direction from OI
changes (Düring, 2021).

**On-the-run (OTR) generics.** String on-the-run, old and double-old bond histories by auction and settle date.
Because a new benchmark usually yields slightly more (longer, upward-sloping curve), a raw OTR series jumps with
no price change. Fixes in order of preference: (a) constant-maturity yields from a fitted government curve for
rich/cheap and long-history work (mean reversion on constant-maturity series, not on rolling individual bonds); (b) a
same-bond "clean" series (begin and end of period yields of the same bond; the clean average monthly yield change
was 1bp higher than the OTR series in the Salomon study); (c) a when-issued (WI) roll adjustment (below).
Specifics: new German 5y benchmark OBL178 issued 25 Jul 2018 replaced OBL177 (about half a year longer), so German 2s5s
apparently steepened and 5s10s flattened that day (Düring, 2021). See
[bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md).

**WI roll adjustment** (RiskVal, Generic Time Series Data & Roll Adjustment, 28 Jul 2020): at 3pm New York on auction
day record `WIroll = WI yield - benchmark yield`; apply it to the old benchmark as if the WI had existed before the
auction; decay it linearly to 0 over the prior auction period,
`RollAdj_i = (WIroll/days) * (day_i - beginDay)`, with `beginDay` the day after the previous auction and `days` the
business days in `(beginDay, auction day]`; repeat for all earlier auctions. Prefer decay: the no-decay variant is a flat
shift with sharper jumps and accumulates artificial drift.

**Constant-maturity (CM) series are views, not raw data**, and are not tradeable as listed instruments: 55.9% of US
listed-option observations lay outside a 30-90 day window and the CM series diverged from real contracts by 6.6% at
150-250 days. Aged positions are marked at their live start, not off a CM series (Internal research handover and
backtest specification, 2026). CM par coupon from a discount curve: `C = 100*(1 - Z_T)/A_T`.

### 6. Structural breaks, splices and rebasing
Maintain a **break register** per series (dates in [references/g10-calendars-snaps-and-rolls.md](references/g10-calendars-snaps-and-rolls.md)): index changes, snap
changes, contract-spec changes, methodology changes, rebasing, SRF-style facility changes. Then:
1. **Label, do not splice silently.** A 10y USD swap history mixes LIBOR, SOFR before the standing repo facility
   (announced 28 Jul 2021, capping SOFR at the facility rate) and SOFR after; before it quarter-end SOFR sometimes
   spiked more than 20bp above fed funds. History before and after behaves like swap rates to which a cap is added
   mid-series, invisible at zero rates and binding once rates rise. Re-estimate vol, mean reversion, regressions and
   Sharpe on post-break data only; pre-break spikes and vol overstate the future. No precise splice is known and ad
   hoc LIBOR-SOFR averages are not precise enough (Huggins & Schaller, 2024 and 2022).
2. **Prefer fitted government constant-maturity par yields for long histories** where swap histories are broken; use
   EURIBOR swaps for a cleaner EUR history but not for rich/cheap (Huggins & Schaller, 2024).
3. **If a proxy is unavoidable**, document it and shift for the level difference: SOFR before Aug 2014 proxied by the
   primary-dealer survey GC repo rate shifted by +1bp (SOFR averaged ~1bp above it over the overlap) (BofA, SOFR/FF term
   structure post big bang, 22 Oct 2020). The Fed's backfill regression `SOFR = Survey + 0.38*(GCF - Survey - 0.05)`
   (rates in %, R^2 99.8% over Aug 2014 to end-2017) gives a fitted series back to 2004 (Bowman, FEDS Notes, Historical
   Proxies for the Secured Overnight Financing Rate, 2019). Never pool a proxy-extended sample with the main sample;
   use it for one clearly labelled control study (Internal research backtest specification v0.4, 2026). Mark the
   backfill boundary on any RFR series backfilled before its switch date (Citi, 13 Aug 2026).
4. **Test for a break before using full-period averages.** FF-SOFR (10-day average) was 0.9bp, 9.9bp, -3.2bp and
   0.0bp across four regimes (1.5bp full sample): the mean describes none of them (BofA, 22 Oct 2020). The R^2 of PC1
   on USD was ~0.47 pre-2023 and ~0.76 post-2023 (Citi, 13 Aug 2026). Scatter-plot a regression: a break can show up
   as two lines. See [quant-regime-detection](../quant-regime-detection/SKILL.md) and
   [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md).
5. **Remove pegged or administered series from co-movement statistics.** Dropping a pegged series cut the R^2 of PC1
   on USD from 0.59 to 0.24 (Citi, 13 Aug 2026).
6. **Index and contract changes are jumps**: CBOT bond futures' notional coupon change from 8% to 6% (dated 1998 in the source; the contract change took effect from the Mar 2000 delivery month, so verify the date with the exchange notice); EUR/USD IBOR
   cross-currency curve removed 6 Feb 2023; after Jun 2023 Eurodollar prices are SOFR plus a fixed spread so only
   SOFR-FF spreads carry the secured-unsecured basis (Merrill Lynch RateLab, 7 Oct 2008; Deutsche Bank DBIQ, 2 Feb 2023;
   Huggins & Schaller, 2022).
7. **Inflation indices**: Japan rebases CPI every five years. Chain with `I_old(t) = I_new(t) * <I_old>/<I_new>`, averages
   over the new base year (for Japan `<I_new> = 100`); the ratio is fixed and chains across rebasings. EU and US
   revise past values instead, breaking "past levels are fixed"; store vintages (`infl_fixings`). Seasonally adjust
   before comparing linkers with different maturity months (Düring, 2021; J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024).
   Flag methodology breaks in macro series (a PCE methodology change was expected to lower annual core PCE by
   20-30bp starting with August 2026 data) (Citi, CitiFX Wire Cheatsheet, 24-28 Aug 2026). Seasonal adjustment can also
   flatter a single print (initial claims of 189k, July 2026) (J.P. Morgan, Jobless claims, 13 Aug 2026).
   See [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md).
8. **Node-starved curves**: a curve-derived futures rate is accurate deep and bad at the front when the node grid starts
   late (15.8bp error at pack ranks 1-4 against 0.268bp at ranks 9-12 in 2019). Rule: maximum tenor `>= 3*n_instruments + 6M`,
   else the last instrument is extrapolated and errors bleed backwards (Internal research handover, 2026).

### 7. Outliers and bad prints
1. **Order**: after stale removal and roll stitching, on changes not levels.
2. **Detect**: `scale_t = 1.4826 * trailing MAD(changes, window 60)` computed **excluding** the current change, floored
   (MAD is 0 on tick-quantised series; floor at half the 10th percentile of non-zero |changes|, or half a tick). Flag
   `|d_t| > 6*scale_t`. A flag that reverses at `t+1` (`|d_t + d_{t+1}| <= 0.5|d_t|`) is a **spike**: label only
   date `t` (a one-bad-date defect has two large changes; mark the bad print, not its reversal). A flag that does not
   reverse is a **jump**: a level shift or event, review only, never auto-remove. The spike/jump label for `t` uses
   `t+1` and the default floor uses the full sample, so it is for cleaning history only: at signal time or inside a
   backtest apply just the causal test `|d_t| > 6*scale_t` with a fixed floor, and treat a flag on the latest date as
   unresolved until the next print.
3. **Corroborate**: a genuine extreme should coincide with news or an extreme in related markets; returns beyond 4
   standard deviations with neither are suspect (Chan, Quantitative Trading, 2009, Ch.3). High/low data are noisy and
   errors in them almost always inflate backtest returns; open/close data are more reliable.
4. **Flag, do not delete or silently refit**: an outlier-removing spline fit changes the sample day to day; keep
   tainted data out of the model by flag, not by hoping post-processing removes it (Düring, 2021). Delete only a
   demonstrably erroneous point; an apparent outlier can mean the model is wrong, and a big residual at a high-leverage
   point is the bigger red flag (Shalizi, The Truth about Linear Regression, 2025, Ch.18). If you must estimate through
   outliers use robust loss: L1 or Huber in curve fits and regressions, heavy-tailed covariance estimators (Huggins &
   Schaller, 2024; Palomar, Portfolio Optimization, 2025).
5. **Thin and illiquid prints**: bid-ask bounce (negative lag-1 autocovariance; `c = sqrt(-gamma1)`, spread `= 2c`)
   inflates short-horizon variance and variance ratios; use mids and clean before mean-reversion tests (Hasbrouck,
   2004, Ch.3 and 9). Thin or last-traded strikes can show persistent no-arbitrage violations (Morgan Stanley, Kalshi
   Markets as Macro Signals, 18 Aug 2026). Auction and opening prints reported as one tick can be worth thousands of ticks
   (López de Prado, 2018).
6. **Stale or asynchronous prices bias vol and correlation downward** (stale sectors look diversifying). Use lower
   sampling frequency or overlapping returns with overlap `L`; effective sample size `t_eff ~ 3TL/(2L^2 + 1)`
   (Muller 1993), so `L = 5`, `T = 250` gives ~74. **Do not demean overlapped returns** or vol comes out spuriously
   low (Golub (ed.), BlackRock's Guide to Fixed-Income Risk Management, 2023, Ch.4). Rolling windows create artificial drops when a spike
   leaves the window (March 2009 10y JPY realised vol was 24bp or 45bp by window): use exponentially decaying weights
   (Huggins & Schaller, 2024, Ch.19). Spike handling alone moved an OU-based SOFR futures fair price by ~32bp
   (Huggins & Schaller, 2022).
7. **Trade tapes** (public repositories, venue tapes) need duplicate, compression, cancel/correct and capped-notional
   handling, and ECN matches plus the follow-on workup are one trade timestamped at the end of the workup (Fleming,
   Mizrach & Nguyen, FRBNY Staff Report 381); that recipe lives in [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md).
   Fitted-curve basket hygiene (low free-float bonds, specials, off-the-runs) lives in
   [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md); a rising fit RMSE can be a basket
   artefact (J.P. Morgan, The (par) curves they are a-changin', 23 Jul 2024).

### 8. Point-in-time and look-ahead
- Index anything published by its **release** instant (`pub_ts_utc`): macro data, fixings, positioning, auction
  results. Period-end indexing of a quantity released ~1.5 months later is look-ahead. Keep every vintage; GDP's first
  release plus two monthly revisions were not known at first release, and final vintages at first-release dates is
  "very common" and wrong (López de Prado, 2018). Survey medians become available only ~2 weeks before a release (Morgan
  Stanley, 18 Aug 2026). Use `point_in_time` in the script: latest vintage with `pub_ts <= as_of`.
- A signal at `t` uses data known at the `snap` of `t` and trades from `t+1`; enforce the delay when accessing data
  (Tulchinsky et al., 2015). Statistics are causal: trailing mean/std ending at `t` (or `t-1`), never full-sample.
  Fitted weights (PCA, regression) are in-sample unless estimated on data through `t-1`; run a walk-forward vs full-sample
  comparison, a large gap means you are trading the estimator (Internal research handover, 2026).
- Point-in-time instrument universe: `issue_date <= as_of < maturity_date` (a strict `<` on issue date dropped
  new issues on their issue day); compute time to maturity with Actual/Actual, because `days/365.25` was ~half a day off at
  a hard 3.0y cutoff (Internal research notes, 2026). Lag membership flags by the signal delay.
- **Truncation test** for look-ahead: run on full data and save positions A; drop the most recent N days (N = 10-100;
  60 is a common choice), rerun to get B; drop the last N rows of A; any difference on the overlap is look-ahead
  (Chan, 2009, Ch.3). Lag every input (averages, highs/lows, volume) to the prior close unless entering only at the
  close.
- Adjust-for-returns, as-of-for-features: adjusted prices are for returns only (Paleologo, The Elements of Quantitative
  Investing, 2025, Ch.8). Informative missingness is a leak. See [bt-backtest-design](../bt-backtest-design/SKILL.md).

### 9. Verify the checker before trusting it
- Run each check first on an input whose answer you know (flat strip with zero moves gives 0 curve P&L to 1e-9; a
  zero-move day gives ageing P&L `carry * dDays/365.25`; a date permutation gives Sharpe ~ 0; an injected look-ahead
  must raise Sharpe sharply). Calendar days for carry and theta, trading days (sqrt 252) for vol: mixing the clocks is
  a classic bug (Internal research backtest specification v0.4, Oct 2026).
- Mutation test: break a sign, roll offset or factor and confirm the test fails, then restore.
- Recompute derived fields (carry, roll, specialness) rather than trust opaque vendor fields: a repriced 1y roll matched
  a published carry at correlation +0.991 while a vendor carry-and-roll field gave -0.136 and ranked wrongly (Internal
  research handover, 2026). Tie out to an independent published source at the as-of close date.
- Parity anchors: compare a new pipeline with the prototype on fixed dates; explained differences go to a deviations list
  (spec says / did / why / expected effect), unexplained ones are bugs.

## Worked example
**1. Roll stitching (illustrative numbers).** Held contract A, rolling into B at the close of day `t-1`:
`A(t-1) = 112.500`, `B(t-1) = 112.000`, so `gap = -0.500`. Day `t`: `A = 112.600`, `B = 112.150`.
Raw generic series: 112.500 to 112.150 = **-0.350** (a fake move). Stitched: all history `<= t-1` shifted by `-0.500`
(112.500 becomes 112.000) and day `t` is 112.150, so the change is **+0.150**, equal to B's own change. The series ends
at 112.150, the raw price. Run: `python scripts/ts_clean.py stitch --px px.csv --active roll_map.csv`.

**2. Snap-time noise vs signal.** Mixing a ~17:00 NY vendor bar with ~15:00 ET settle: noise 1.82bp/day; true
convexity-adjustment move 0.55bp/day; levels 1.34-6.81bp. Any z-score of that series measures the snap mismatch
(Internal research handover, 2026). Fix: re-snap every leg at settlement.

**3. Benchmark switch.** 25 Jul 2018: OBL177 to OBL178. Yield jump with no price change: apparent 2s5s steepening and
5s10s flattening. Treat the date as a break or use fitted constant-maturity yields (Düring, 2021).

**4. WI roll adjustment (10y UST, 12 May 2020).** Unadjusted 0.679460% vs roll-adjusted 0.690710%, a roll of about
1.1bp (RiskVal, 28 Jul 2020).

**5. Stale-quote zig-zag.** 0-2y SOFR OIS zeros oscillated between 0.075% and 0.1025% when 7M-18M quotes had 3.0bp bid/ask
vs 0.3bp at 3M-4M; single-strip futures curves were smooth, the mixed 1M+3M curve ranged 0.081%-0.099%
(Deriscope blogs, 18 Feb 2024).

More numbers (least-squares mid, intrinsic depth, Bayesian fill of a closed market, turn-of-year jumps, Roll spread,
seasonality test, basket hygiene) are in [references/worked-examples.md](references/worked-examples.md).

## Signals & interpretation
`dq_reason` vocabulary and the action each implies. The first five codes are written by `scripts/ts_clean.py`; the
last row is for adapters and `symbol_map` checks to write with the same convention:

| `dq_reason` | `data_ok` | Meaning | Action |
|---|---|---|---|
| `non_business_day_row` | false | row dated on weekend/holiday for that calendar | exclude from statistics; keep row |
| `carry_forward_all_unchanged` | false | every series unchanged vs prior row | exclude row from panel; log date |
| `stale:<series>` | false | repeat inside a run of `>= min_run` | exclude that series that day; stale gate for signals |
| `spike:<series>` | false | one-date outlier that reverses next day | exclude that point; check source |
| `review_jump:<series>` | true | large non-reversing move | human review: event, break or roll? |
| `flat_term_structure`, `unit_suspect`, `off_grid` | false | structure/unit/grid failure | fix in adapter or `symbol_map` |

Gates for any signal built on the series: no `stale` in the last 3 business days of an input; effective start after
252 business days of warm-up; all legs same `snap`; roll rule recorded; post-break window only for estimators crossing
a break. If the tests produce no flag on data you expected to be dirty, run the self-test on injected defects before
believing the data are clean.

## Pitfalls
- Forward-filling, interpolating or back-filling to "complete" a panel (look-ahead and zero-change artefacts).
- Rolling on expiry, or measuring the gap on the roll date instead of the prior close (the roll-day change then belongs
  to the old contract, not the one held).
- Calling a one-way level shift a "spike" and deleting it; or calling a bad print a "jump" and keeping it.
- Estimating a mean or vol on a sample that crosses LIBOR/SOFR, a facility change or a rebasing.
- Z-scoring a spliced series, or a CM series, as if it were a traded instrument.
- Detecting outliers before stitching (roll gaps) or before removing stale rows (catch-up moves).
- Using a constant `min_run` for series with different tick/vol (flags a pinned policy rate, misses a liquid swap rate).
- Hard-coding a tick size, a holiday list or a roll rule instead of reading `fut_static`, `calendars`, `roll_map`.
- Trusting a "high-IC" feature that is really a split/roll factor, or a t vs t+1 off-by-one (Paleologo, 2025).
- Multiple-testing on calendar patterns: under no seasonality about `alpha` of tests flag by chance (swapsball.net, 2017;
  see [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md)).
- Scoring a cleaning or fair-value filter against the next print: the last trade looks best and is worst against the truth
  (error 0.020 vs 0.056 against truth in a simulation) (Cotton, Filtering bond and credit default swap markets, 2016).
- Treating spread-to-policy-rate gaps as errors: EUR overnight has sat below the deposit rate under excess liquidity
  (Düring, 2021, p.66). After a policy move compare spreads, not levels (Conks, 10 Oct 2024).

## Output
Return a **data-quality report** before any signal or trade idea uses the history:
1. Table per series: `series_id`, `snap`, unit, first/last/effective-start date, expected dates, missing dates, rows
   flagged by each `dq_reason`, stale-gate status at the as-of date, coverage % and join match rate.
2. Roll table per generic: each roll date, old and new instrument, `roll_rule`, gap (bp or px), additive vs ratio.
3. Break register hits: every break inside the analysis window and whether the estimator window was truncated to
   post-break.
4. Flags file with `date, series, data_ok, dq_reason` (canonical `_common` columns), plus a one-line verdict per series:
   `use`, `use after filtering` or `do not use`, with the reason.
Hand the cleaned panel and the verdicts to the consuming skill (for example
[quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md) or
[bt-backtest-design](../bt-backtest-design/SKILL.md)).

## Scripts
- [`scripts/ts_clean.py`](scripts/ts_clean.py): `calendar_audit`, `stale_rows`, `stale_runs`, `min_run_for`,
  `spike_flags` (spike vs jump, MAD floor, stale-excluded), `off_grid`, `stitch_rolls` (additive or ratio
  back-adjustment, refuses to roll without a prior-date price), `point_in_time`, and `audit` (full panel flags in
  `data_ok`/`dq_reason` form). CLI: `audit --panel panel.csv [--calendar calendars.csv --calendar-id ID]` and
  `stitch --px px.csv --active roll_map.csv [--ratio]`. `python scripts/ts_clean.py --selftest` injects defects at known
  dates into a seeded panel and requires the flagged set to equal the injected set exactly, checks stitching changes
  equal the held contract's changes on every date including roll days, and exits non-zero on any failure.

## Related skills
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables, `snap`, `data_ok`/`dq_reason`
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): per-market indices, day counts, calendars
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): roll fair value and roll-adjusted generics
- [fi-curve-construction](../fi-curve-construction/SKILL.md): turns, jump removal, curve sanity checks
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): fixing day weights, reference periods
- [bt-backtest-design](../bt-backtest-design/SKILL.md): point-in-time data, signal delay, rolling instruments
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): purging, embargo, multiple testing
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): causal z-scores on the cleaned series
- [quant-regime-detection](../quant-regime-detection/SKILL.md): detecting breaks and regimes
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): structural-break and HAC tests
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): overlapping returns, robust estimators
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): constant-maturity series and basket hygiene
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): trade-tape cleaning
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): CPI vintages, seasonals, rebasing
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): calendar effects after cleaning
- [eng-python-analytics-stack](../eng-python-analytics-stack/SKILL.md): pandas conventions for the scripts

## References
- Internal research backtest specification (forward curve vs straddle, v0.4, Oct 2026): panel contract (inner join, holiday-row drop, no forward-fill), stale gate, warm-up, clocks, known-answer tests
- Internal research handover note, convexity RV data pre-flight (2026): snap-time noise, tick-grid roll detection, date-alignment identity, node-starved curves, vol units, cache match rates, vendor carry vs repriced
- Internal research notes on series construction and data pitfalls (2026): roll-rule comparison, unit and null-column bugs, point-in-time universe, Actual/Actual maturity
- Huggins & Schaller - Fixed Income Relative Value Analysis, 2nd ed. (Wiley, 2024): LIBOR/SOFR/SRF breaks, constant-maturity par yields, L1 loss, realised-vol window artefacts
- Huggins & Schaller - SOFR Futures and Options (Wiley, 2022): 3M SOFR futures roll timing, reference-period stickiness, fixing day weights, post-SRF re-estimation
- Düring - Fixed Income Trading and Risk Management (Wiley, 2021): benchmark-switch artefact, CPI rebasing, roll and OI monitoring, conventions, bid-ask bounce, flag-not-delete
- López de Prado - Advances in Financial Machine Learning (Wiley, 2018): roll-gap stitching, non-negative rolled series, vintages and release dates
- RiskVal - Generic Time Series Data & Roll Adjustment (28 Jul 2020): OTR/old/double-old stitching and the decaying WI roll adjustment
- Ametrano & Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN 2219548, 2013): turn-of-year detection and removal
- Ametrano, Bertocchi & Mazzocchi - Advanced Eonia Curve Calibration (SSRN 2881445, Dec 2016): jump-removal algorithm, month-end jumps
- Deutsche Bank DBIQ - Interest Rate Curve Creation Process (2 Feb 2023): G10 curve snap times, snap change 27 Apr 2018, discontinued curves
- Federal Reserve Board - FEDS Notes: Historical Proxies for the Secured Overnight Financing Rate (Bowman, 2019): SOFR backfill regression, benchmark membership
- BofA Securities - SOFR/FF term structure post big bang (Cabana, Axel, Lima, 22 Oct 2020): proxy splice with +1bp shift, regime-dependent spreads
- Salomon Brothers - Understanding the Yield Curve Part 5, Convexity Bias and the Yield Curve (Ilmanen, Sep 1995): clean same-bond series, normal vs relative vol
- J.P. Morgan - The (par) curves they are a-changin' (Barry et al., 23 Jul 2024): fitted-curve basket hygiene and RMSE artefact
- Citi - Decomposing Global Rate Drivers Across EM Asia 5y5y (Goh, Garg, 13 Aug 2026): weekly mid-week sampling, backfilled RFRs, structural-break and pegged-series checks
- Chan - Quantitative Trading (Wiley, 2009): 4-sigma data check, truncation test for look-ahead, multiplicative adjustment, NaN-aware helpers
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): delay convention, NaN vs 0, delay-lagged universe mask, unit mixing
- Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022): mid algorithms, spoofing, least-squares mid, Bayesian fill, curve turns
- Darbyshire - Coding Interest Rates (c.2024): calendar observance rules, non-invertible date arithmetic
- Hasbrouck - Empirical Market Microstructure (NYU Stern teaching notes, 2004): Roll bounce estimator, stale-price models, session chaining
- swapsball.net - Testing for seasonality (19 Nov 2017): roll-window drop, trimmed-mean/median tests, multiple-testing caution
- Golub (ed.) - BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023): asynchronous prices, overlapping returns, effective sample size
- FactSet - Interest Rate Future white paper (McFerrin & Wei, 23 Mar 2023): month-code semantics, yield-quoted AUD/NZD futures
- Deriscope blog - SOFR curve in Excel with QuantLib; Turn-of-the-Month effect in the SOFR curve (Rigopoulos, 18 Feb 2024): stale-quote detection by bid/ask, reprice-to-zero test
- Dunis, Laws & Naim (eds) - Applied Quantitative Methods for Trading and Investment (Wiley, 2003): synchronous closes across markets, PCA imputation of a missing tenor
- Fleming, Mizrach & Nguyen - The Microstructure of a U.S. Treasury ECN: The BrokerTec Platform (Federal Reserve Bank of New York Staff Report 381, 2009, rev. 2017): workup aggregation, intraday liquidity times
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): data-sourcing checklist, adjust-for-returns vs as-of-for-features, leakage
- Palomar - Portfolio Optimization: Theory and Application (Cambridge University Press, 2025): causal statistics, robust estimators
- Shalizi - The Truth about Linear Regression (Carnegie Mellon draft lecture notes, 20 Oct 2025): leverage and outliers
- Cotton - Filtering bond and credit default swap markets (NYU Tandon seminar slides, 27 Apr 2016): scoring filters against truth, not the next print
- Merrill Lynch US Rates Strategy - RateLab: Implied Volatility: A Measurement of Fear (7 Oct 2008): CBOT bond futures coupon-change jump
- Quantitative Finance Stack Exchange - Plotting Treasury Futures implied repo over time: non-contemporaneous prices, roll 5 days before delivery month
- Morgan Stanley - Kalshi Markets as Macro Signals (Carter et al., 18 Aug 2026): survey-median timing, thin-strike prints
- J.P. Morgan - US: Jobless claims continue to deliver positive labor signal (Parrish, 13 Aug 2026): seasonal-adjustment artefact
- Citi - CitiFX Wire Cheatsheet, G10 & EM Week Ahead (24-28 Aug 2026): PCE methodology break
- Conks - Plumbing Notes, Money Market Updates (Aug 2024 to Jun 2025) and The Repo Market Dislocation Part I (17 Aug 2024): benchmark-composition artefact, percentile monitors
