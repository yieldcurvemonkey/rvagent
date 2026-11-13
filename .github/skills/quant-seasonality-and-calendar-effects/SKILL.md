---
name: quant-seasonality-and-calendar-effects
description: 'Find, test and use calendar effects in G10 rates - month-of-year seasonality screens, month-end and quarter-end index extension, quarter/year-end funding turns, auction, refunding, coupon and tax-date cycles, futures delivery and roll calendars, day-of-week and holiday effects, seasonal factors for linkers and macro data, fixed-date calendar trades. Runs the screen-and-test workflow (up-ratio, t and Wilcoxon, event windows, placebo, multiple-testing) and says how to size a hit against sigma and costs. Use when asked "is there seasonality in", "does it cheapen into month-end", "turn premium", "year-end", "quarter-end", "window dressing", "January effect", "January barometer", "first five days", "presidential cycle", "seasonal pattern", "calendar spread seasonal", "seasonally adjusted breakeven", turn-of-year, month-end extension, or when an RV signal might be a calendar artefact. Auction-concession trades: bond-supply-and-cashflow-trading.'
---

# Seasonality and calendar effects

Calendar effects exist where flows, balance-sheet dates or contract mechanics repeat on a known date: index
extensions, funding turns, supply cycles, delivery dates, tax dates, seasonal index prints. This skill is the
workflow for deciding whether such a pattern is real and tradable (mechanism, base rate, significance, placebo,
multiplicity, size against noise and cost) and for the opposite use: stripping calendar effects out of curves, linkers,
spreads and macro data so they do not masquerade as RV signals. Most screens find nothing: the default answer to "is
there seasonality in X" is that a seasonal is at best a tailwind, not a signal on its own (BofA Securities, UK Rates Viewpoint: Back to school, 5 Sep 2024).

## When to use
- "Does the 10y cheapen into month-end / auction week / refunding?", "is Bund asset swap seasonal?", "January effect in rates".
- A screen shows a rich/cheap residual or a spread move that sits on a quarter-end, year-end, roll, coupon or tax date.
- Valuing across a turn: forward-starting swaps, STIR strips or basis spanning 31 Dec; "year-end premium priced in the futures".
- Comparing linkers or inflation swaps with different maturity months (seasonally adjusted breakeven).
- Auction, supply and index-extension timing for a duration or curve trade (the supply and demand mechanics themselves live in the supply skill).
- Validating or killing a research claim of the form "X tends to do Y in month/week Z" (see [rv-research-digest](../rv-research-digest/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Series under test: par swap/OIS or constant-maturity govt yields, curve spreads, flies | `curve_par` | daily close, same `snap`, >= 10y (20y for index-level patterns; JGB and some spread series only about 10y) | test the DV01-neutral spread or fly, not the outright, unless the claim is about duration |
| Swap spreads, asset-swap spreads, invoice spreads | `swap_spreads` | daily, >= 10y | state `sign_convention`; a seasonal "tightening" means opposite things in the two conventions |
| Futures and STIR contracts | `fut_quotes`, `stir_quotes`, `roll_map` | daily settle, roll map | drop or adjust roll days |
| Repo, GC, overnight fixings | `repo_rates`, `rate_fixings` | daily; keep `segment` | turn tests need the ex-turn base level |
| Business-day and exchange calendars | `calendars` | all years incl. future | use the calendar of the instrument: Treasury cash and rate futures differ |
| Auction schedule and results | `auctions` | all auctions, `auction_date`, `settle_date` | results columns are known only at `results_ts_utc` |
| Policy meeting dates | `cb_meetings` | schedule incl. future | event windows around meetings |
| Index price levels and seasonal factors | `infl_fixings`, `infl_seasonals` | monthly; use factors only after `valid_from` | point-in-time sets |
| Macro prints (NSA and SA vintages) | `macro_series` | by `pub_ts_utc` | residual-seasonality checks |

If an input is missing, ask for it or hand off to the data engineering agent. Never invent values; never fill a
holiday with a made-up business day (see [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md)).

## Method

### 0. Order of work (do not reorder)
1. **Mechanism first.** Write down who trades, on what date rule, why, and in what size (DV01 or net cash) before opening the data. Patterns without a mechanism (issuance, redemptions and coupons, fund flows, fiscal year-ends, reporting dates) are not tradable (BofA Securities, Bond market seasonality explained, 6 Jun 2022). Equity-style calendar rules have largely decayed; commodity seasonals tied to real demand persisted (Chan, Quantitative Trading, 2009).
2. **Build event time.** Offsets in business days from an anchor (offset 0 = last business day of the month, auction date, settlement date, expiry, holiday). Never calendar days; take the anchor from the `calendars` table, because a series with missing days shifts "last business day". Assert date alignment (entry before exit, anchor present) and show year-by-year results (Chan, 2009).
3. **Pick the test** (3-6 below), with the defaults in the table.
4. **Multiplicity, placebo, split-sample.** Count how many series x months x windows you scanned before reading any p-value.
5. **Size the hit** against sigma, carry, costs and capacity, then decide: tilt/timing, ignore, or build the adjustment into the model.

**Sign and unit conventions.** Changes are in bp (a `_pct` column x 100). "Up" = change > 0 in the series as quoted: a yield
sell-off (price down), a steeper curve spread (A-B = longer minus shorter, so 2s10s = 10y - 2y), a wider spread in the stored
sign convention (US swap spread = swap minus Treasury yield; EGB asset swap = bond yield minus swap, positive = bond cheap).
State the convention next to every up-ratio: a "tightening" means opposite things in the two spread conventions. For futures
prices and STIR contracts up = price up = rate down.

| Default | Value | Reason |
|---|---|---|
| History | >= 10 yearly observations per month or window | fewer leaves the t and Wilcoxon tests with no power; 6-7 years is anecdote |
| Units | bp for yields, spreads, basis; % for prices; changes, not levels | additive, comparable across months |
| Central tendency | median first, mean second, 10%/25% trimmed means as a check | resists extreme observations (swapsball.net, Testing for seasonality, 19 Nov 2017) |
| Significance | alpha = 10% on both the t-test (mean) and Wilcoxon (median) | source default; require both |
| Up-ratio flag | >= 70% strong, <= 30% weak; report average, median, min, max, counts | (BofA, Bond market seasonality explained, 6 Jun 2022) |
| Futures roll | drop daily changes on days 6-10 of expiry months for a series rolled 2 business days before expiry, or use a roll-adjusted series | roll gaps otherwise land in specific months; the dropped days leave expiry-month sums about 25% short, so compare those months with care (swapsball.net, 19 Nov 2017) |
| Event window | +/-5 business days around the anchor; baseline = mean daily change outside all windows | (RiskVal Highlights newsletter, Bond Futures Delivery, May 2022, uses +/-5 days around 20y auctions over the last 6 cycles vs the 6-month mean) |
| Effect vs noise | candidate only if abs(mean) / sigma_yearly >= 0.5 (house default, not sourced); sigma much larger than mu = no compelling pattern | (swapsball.net, 19 Nov 2017) |
| Multiple testing | expected false flags = alpha x 12 x K (K series); control with Bonferroni or Benjamini-Hochberg across all tests scanned | "green jelly beans" |

### 1. Month-of-year screen (the swapsball procedure)
1. Daily changes in bp (`--diff`), same snap, roll days dropped.
2. Table of summed changes, month x year; discard month-years with fewer than 10 observations.
3. Per month: mean, median, 0/10/25/50% trimmed means, std, up-ratio, count of up months.
4. Tests against all months pooled (H0: the month's move equals the move in all months): two-tailed Student t on the mean, two-tailed Wilcoxon signed-rank on the median, binomial on the up-ratio vs 50%. Assumptions: t needs roughly normal monthly moves, Wilcoxon needs symmetry; check both, neither is guaranteed.
5. Compare the number flagged with alpha x 12 = 1.2 expected by chance per series. A single flagged month in a screen of 12 is what noise delivers.
6. Plot mu +/- 1 sigma per month. If sigma is much larger than mu, the pattern is not compelling.
Vol series: apply the same screen to the month-on-month change in normal vol (bp) and compare 5, 10 and 20 year samples for
stability (one source found gamma outperforming in 4 of the last 5 and 7 of the last 10 Mays; Citi Research, US Rates Vol Lab: Fair
value vs seasonality, 1 May 2017).
`python scripts/seasonality.py screen --csv curve_par.csv --value-col par_rate_pct --where curve_id=<id> --where tenor=10Y --where start=0D --scale 100 --diff --drop-roll`

### 1b. Day-of-week and holiday effects
Evidence in the library is qualitative only (funding firmer into weekends and month-ends, softer on Mondays; position squaring on
Friday afternoons and before holidays), so treat every claim as a hypothesis.
- Weekday: group daily changes by weekday and test each day against the median of the other four days' means (t) and medians
  (Wilcoxon): `weekday_screen` / `python scripts/seasonality.py weekday ...`. Expect alpha x 5 = 0.5 false flags per series; funding
  and repo series (levels of GC, SOFR-FF) are better tested as deviations from the local base level than as daily changes.
- Holiday: events = the holiday dates from `calendars` (`is_business_day = false`) with forward snap. On a series that has no row for the
  holiday, offset -1 is the pre-holiday day and offset 0 the post-holiday day; run `window_study` with `--pre 3 --post 3` and the placebo.
  Use the calendar of the instrument (cash vs futures holidays differ) and require at least 30 events (a handful of holidays per year
  over 10+ years) before reading anything.

### 2. Event-window study (month-end, quarter-end, auction, settlement, holiday)
1. Event dates: period-ends from the series calendar (`period_end_events`), auctions from `auctions.auction_date` (or `settle_date`), holidays from `calendars` (`is_business_day = false`; use the day before and the day after).
2. Matrix of daily changes at offsets -pre..+post for each event. Per-offset mean and t across events (events are the observations; not days).
3. Window total over [lo, hi] minus (window length x baseline), t-stat across events, hit rate (share of events with positive excess).
4. **Placebo**: re-run with event dates shifted by +/-(w+1 .. w+20) business days (w = window length), excluding shifts of about one month for month-end events. Report the share of placebo windows at least as large (floor about 1/41 for 40 shifts; never quote a smaller p). A flat placebo plus a sharp event profile is the signature of a real effect.
5. **Two clocks**: if the tenor's auction cycle is not monthly (10y, 20y, 30y roll quarterly), compare the auction-cycle clock (days since the last auction) with the calendar month/day-of-week clock. A flat auction-cycle profile means it is not an auction effect; also place the same configuration off the auction clock as a placebo.
6. Compare the latest cycle with the average of past cycles (e.g. 5 days before to 10 after) to see whether the effect is still alive (RiskVal, Overview 201: Cash and Futures, 12 Nov 2021).
`python scripts/seasonality.py window --csv <series.csv> --diff --events month_end --lo -3 --hi 1`
(`--events <csv> --event-date-col auction_date` for tables; `--snap backward` for period-end dates that fall on a weekend.)
Window convention: the change at offset k is close(k) - close(k-1), so `--lo a --hi b` is a position entered at the close of day a-1 and
exited at the close of day b. "Enter 3 business days before month-end, exit 1 after" is `--lo -2 --hi 1`. A yield change is the opposite
sign to the P&L of a long-duration position.

### 3. Conditional hit rates (January barometer template)
For any asset: (i) count up and down Januarys with average and median change; (ii) 2x2 table of January up/down against Feb-Mar (and Feb to year-end, and year) up/down, with count, conditional ratio and average changes; (iii) first-five-sessions variant, whose later blocks are the rest of January, the rest of Q1 and the rest of the year (BofA, Technicals Explained: In 2025, 14 Jan 2025). **Always compare with the base rate**: a conditional 70% against an unconditional 61-66% is weak. Choose a later block that does not contain the conditioning block (Feb to year-end, not the whole year; the rest of January, not January): the first-five-day signal largely overlaps the January return it helps form, and the equity barometer's 80% year-hit rate after an up January is partly arithmetic. Barometers decay: the equity January barometer called the year about 90% of the time in the 1950s and 50-60% since 2000 (BofA, Technicals Explained: In 2025, 14 Jan 2025), so use the recent window as the prior. In-window drawdown belongs next to the average: a window that earns +2.3% with an average -8.7% correction is sized on the correction. Full US 10y tables (January, first five days, month-of-year shape, presidential-cycle blocks), the dollar, oil and equity versions, and Fisher p-values: [barometers_and_calendar_tables.md](references/barometers_and_calendar_tables.md). Sub-splits resting on 2-7 observations are anecdotes. Tables are usually presented without significance tests: run Fisher's exact test on the 2x2. Seasonal-momentum variant (Heston and Sadka: buy the month's winners from the same calendar month a year earlier, short the losers; Sharpe = sqrt(12) x mean / std of monthly returns): a survivorship-biased S&P 500 re-test gave an average annual return of -0.9167 and Sharpe -0.1055 (Chan, 2009), so apply the cross-sectional idea to a basket of markets or spreads only with the checks above.

### 4. Fixed-date calendar trades
Buy on a fixed date, close on another. Validate with (a) year-by-year P&L and intra-trade maximum drawdown, (b) varying entry and exit dates by several days each way and checking that profitability holds (if only the exact dates work it is data-snooping), (c) an economic reason (Chan, 2009). Annual trades have one observation per year: 14 years is 14 observations, and large drawdowns appear in winning years (an April gasoline-futures trade made +2,286 USD in 2007 with a -9,816 USD drawdown from entry, in the same book's tables). Trust the printed tables over the prose.

### 5. Seasonal factors and adjustment (use the effect to clean other signals)
- Linkers, inflation swaps, CPI-linked flows: SAP = P x S_v / S_m; breakevens and Z-spreads are not comparable across maturity months without it. Derivations, formulas and the factor estimators: [seasonal_adjustment.md](references/seasonal_adjustment.md). `seasonal_factors()` estimates ratio-to-moving-average factors.
- Macro releases: compare with the same week or month in prior years, use year on year or 3-month annualised, expect residual seasonality, and use point-in-time vintages. Aligning January data with revised January data is look-ahead.
- Curves and funding: strip turns before inferring policy expectations or fitting splines, reinsert after. Jump formulas, sizes, FEDS-style measures and the fed funds year-end decomposition: [period_end_turns.md](references/period_end_turns.md).
- Futures delivery and roll calendars: delivery option value is not seasonality; use the timeline in [calendar_catalogue.md](references/calendar_catalogue.md) and the futures skills below.

### 6. Seasonal RV across markets
Rolling 10-year seasonal medians per market; relative version: overweight markets whose current-month seasonal median is higher, underweight lower, total leverage 100%. Relative added modest value (reward-to-risk 0.66 vs 0.52 long-only on G7 bond futures) while absolute timing added none (Willer and Saunders, Trading Global Macro Markets, 2026). Use only as a tilt.

## Where the effects are (catalogue, details in references)
| Effect | Direction and size (examples) | Mechanism | Detail |
|---|---|---|---|
| Month-end index extension | euro government index +0.05y (equal to its 5y median); gilt -0.02y vs a +0.03y median | tracker duration demand on last trading day | [calendar_catalogue.md](references/calendar_catalogue.md) |
| Quarter-end / year-end funding turns | USD SOFR above reverse-repo by 25-28 bp at Sep and Dec 2024 quarter-ends; German one-day GC minus Eonia, average end-of-month change over 8 years: +138 bp in January, -188 bp in December | balance-sheet snapshots, averaging rules | [period_end_turns.md](references/period_end_turns.md) |
| Auction-cycle drift | 10y: empty week -3.9 bp median, final week -7.4 (86% rallies), first week +2.7 | supply concession then release | [calendar_catalogue.md](references/calendar_catalogue.md) |
| Tax and bill cycles | 12m bill-OIS richens about 7 bp in April-May | paydowns from tax receipts | [calendar_catalogue.md](references/calendar_catalogue.md) |
| Linker and CPI seasonality | seasonal swing same order as trend inflation | NSA index | [seasonal_adjustment.md](references/seasonal_adjustment.md) |
| Cross-currency basis turns | JPY year-end turn about +15 bp in 3m asset-swap decomposition; CAD month-end 40 bp round trip | G-SIB and fiscal year-end, issuance (Samurai May-July) | [period_end_turns.md](references/period_end_turns.md) |
| Day-of-week and holiday | funding up into weekends, month-end; Mondays down | settlement cycles | thin evidence: test |
| January barometer, first five days, presidential cycle | US 10y: Feb-Mar up 70% after an up January vs 66% unconditional; Feb-to-year-end up 61% vs 43% after a down January (Fisher p = 0.20) | none beyond narrative; fiscal and sentiment resets | [barometers_and_calendar_tables.md](references/barometers_and_calendar_tables.md): grade C |

### G10 differences that change the calendar
| Market | What differs |
|---|---|
| USD | 2y/5y/7y issue last business day, 10y/30y and 3y mid-month; quarterly refunding first week of Feb/May/Aug/Nov; mid-month tax and coupon dates; Treasury cash and CME rate futures have different holidays |
| EUR | German auctions on Wednesdays, BKO mid-month maturities; BTP twice monthly with a month-end tranche; year-end turn in EUR GC and the Euribor-linked strip; January issuance and the -3.5 bp January 2y German swap-spread average (BofA, 6 Jun 2022) |
| GBP | gilt remit seasonality (March borrowing historically +18 to +23bn); September 10y up 61% and 2s10s steeper 67% (BofA, Back to school, 5 Sep 2024); SONIA slightly negative the day before quarter-ends |
| JPY | 1 April fiscal year-end turn; central-bank purchase schedule set at month-end and quarter-end; Samurai May-July |
| CAD | Canadian banks cut repo at quarter-ends (Q2 ends in April); month-end FX-OIS turns |
| AUD | Q1 SSA issuance narrows the 5y basis early in the year; Kangaroo swap-backs |
| NZD | tax outflows reduce settlement cash around tax dates, tightening the overnight index vs SOFR |
| CHF, SEK, NOK | no calendar-specific material in the library; run your own screens. SEK term-rate fading turn example in the turns reference |

## Worked examples

**1. A conventional seasonal fails the test.** The folklore said the German 10y bond-futures asset swap (source sign: swap yield minus futures-implied yield, positive = future rich; opposite to the bond-minus-swap convention above) tightens in January and September (government and corporate issuance pick up). Over 2007-2017, monthly average moves ranged about -2 to +4 bp with one-sigma ranges of about +/-10 bp. p-values (t on mean / Wilcoxon on median): January 0.750 / 0.721; September 0.136 / 0.155; nothing significant at 10%, and the sign if anything opposed the folklore. Two other cross-contract boxes did show significant patterns, but scanning boxes without correcting is the "green jelly bean" trap (swapsball.net, Testing for seasonality, 19 Nov 2017).

**2. Which of six published windows survives?** EUR 10y seasonal windows, 2004-2020 (BNP Paribas, EUR curve convexity: Lessons from history, 25 May 2021): bullish 3rd week of June hit rate 94% (average move 10 bp, st dev 14 bp), 3rd week of November 88%, August 77%, January 71%; bearish October 76%, June 65%. Assuming 17 annual observations (hit rates then equal 16/17, 15/17, 13/17, 12/17, 13/17, 11/17) and a 50% null (the rally base rate in each window is not given, so these p-values overstate the bullish windows if yields drifted lower over 2004-2020), one-sided binomial p-values are 0.0001, 0.0012, 0.0245, 0.072, 0.0245, 0.166 (our calculation). If the windows were picked from a weekly grid in both directions (about 104 candidates, an assumption), the Bonferroni-adjusted p is 0.014 for June week 3, 0.12 for November week 3 and 1 for the rest. Only June week 3 is a candidate, with effect/sigma = 10/14 = 0.71, still a 17-observation pattern with no documented mechanism: grade C (below), upgradable to B once a mechanism is found and the out-of-sample years behave.

**3. A January barometer against its base rate.** US 10y yield, 61 Januarys since 1963 (BofA, Technicals Explained: In 2025, 14 Jan 2025): January up then Feb-to-year-end up in 20 of 33 years (61%, average +83 bp after +22 in January); January down then up in 12 of 28 (43%). Unconditional Feb-to-year-end up: 32/61 = 52%. The 18-point gap looks large, yet Fisher's exact test on [[20,13],[12,16]] gives p = 0.20 (our calculation): not significant. A trending yield also makes January and the later months correlated for reasons unrelated to the calendar (the yield rose to 1981 and fell to 2020): year-demean the changes or split at the turn. The headline Feb-Mar version is weaker still: up 70% after an up January (23 of 33) against 61% after a down January (17 of 28) and 66% unconditional, Fisher p = 0.59. The first-five-day rule adds nothing: a rise in the first five days is followed by a rest-of-January fall in 22 of 34 years (65%) against 57% unconditional, p = 0.30, and by a higher rest of year in 18 of 33 (55%) against 63% after a down start, p = 0.60 (our calculations).

**4. Isolating the year-end premium in fed funds futures.** With the December and January meetings effective on 12 Dec and 30 Jan, YE (the average overnight rate 12-31 Dec minus 1-29 Jan; positive = year-end premium) = -(11/20) Nov + (31/20) Dec - (31/29) Jan + (2/29) Feb (futures rates). Scaled to 100K of year-end exposure the weights on the rates are -55K, +155K, -107K, +7K (Nov, Dec, Jan, Feb); read as futures positions (positive = buy) they are the fade below, with no December-step, January-step or parallel exposure: Dec step 155 x 20/31 - 107 + 7 = 0; Jan step -107 x 2/31 + 7 = 0 (our check). Citi's 2019 fade: sell the November contract, buy December, sell January, buy February in that ratio (-55K : 155K : -106K : 7K), package quoted at +4.5 bp (the market-implied technical drop of -4.5 bp after year-end), target +1.5 bp, stop +6 bp; the largest drop in realised history was -2.65 bp (Citi Research, US Rates Weekly: Fixing the plumbing, 30 Sep 2019). Full derivation and day-count caveats: [period_end_turns.md](references/period_end_turns.md).

**5. Hedge ratio across a month boundary.** 1M averaging contracts ($5mm face, daily rate averaged over the month, about $41.67 per bp): N = notional x days in month / ($5mm x 30). Full February on 50mm: 50 x 28 / (5 x 30) = 9.33; 50mm exposed from mid-January to month-end: 50 x 31 / (5 x 30) = 10.33; 50mm exposed for the 10 investment days 4-13 March, with 28 days of the 31-day March contract left: 10 x (31/28) x (10/30) = 3.69 (check: 50mm x 10/360 x 1bp = $138.9 against 41.67 x 28/31 = $37.6 per contract) (Tuckman and Serrat, Fixed Income Securities, 4th ed., 2022).

**6. Illustrative screen on synthetic data (what the script reports).** 20 years of 3 bp/day noise with +1 bp/day injected into January: Jan mean about +19 bp, p_t = 0.0002, flagged; one month elsewhere flagged by chance (expected 1.2). This is the selftest case, not market data.

## Signals & interpretation
- Grade a hit: **A** = mechanism documented + passes both tests at alpha with multiplicity control + placebo flat + holds in both halves of the sample + effect larger than cost and 0.5 sigma. **B** = mechanism and one of the tests; use only as timing tilt. **C** = pattern without mechanism: do not trade. A seasonal is a tailwind, not a signal on its own (BofA, Back to school, 5 Sep 2024).
- Turn trades: size from base tightness and net supply, not from last year's turn. The year-end premium is customarily priced but rarely realised; the overnight rate often collapses on the day (Lehman Brothers, The Short-End of the Curve, 10 Jul 2007). The basis market overprices year-end tightness in advance and then sells off (Conks, Plumbing Notes: Swifter Injections, 4 Dec 2025).
- Seasonal patterns can stall a trend trade for weeks: tighten the stop rather than add. Fly residuals overshoot fair value (5-10 bp within about three months); do not take profit mechanically at zero (BNP, 25 May 2021: rich-fly episodes normalised in 3.1 months on average, with an overshoot in 6 of 7 cases).
- If the screen's residual sits on a date listed in the catalogue, remove the calendar component (turn strip, seasonal factors, roll mask) and re-run the RV signal before calling anything cheap or rich.
- Effect decay: compare the latest cycle with the history of cycles; if the last 3 cycles are flat while the average is strong, downgrade one grade.

## Pitfalls
- **Multiple comparisons**: 12 months x K spreads x two directions at 10% yields a hit by construction. Count the scan, correct, and prefer a prior mechanism-driven list.
- **Small samples**: once-a-year trades and sub-splits (first five days up/down then rest of January, presidential-cycle party x term cells) rest on 2-7 observations. Present hit rates as soft priors and always next to the base rate.
- **Trend in levels**: a month's yield change correlates with the multi-year trend (the Fed hiking path) as much as with the calendar; demean by year or use year-demeaned changes when the sample has a strong trend.
- **Roll, holiday and data-gap alignment**: missing days shift "last business day"; 28/29 Feb and 30-day month-ends make roll inference ambiguous: use an explicit end-of-month flag and never auto-infer IMM rolls; use modified-following where month-end matters (2M from 30 Sep ends Friday 28 Nov, not Monday 1 Dec) (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed., 2022; Coding Interest Rates, c. 2024).
- **Roll-down artefacts**: reusing yesterday's curve inputs misaligns schedules and creates spurious roll-down across the date; use constant-forward methods (Darbyshire, 2022).
- **Look-ahead in seasonal adjustment**: factors fitted on the full sample; revised data. Use point-in-time factors and vintages.
- **Quarter-end data exaggerate swap-spread and basis moves**: measure supply in DV01 and net-cash terms, and exclude the turn days when judging a level (Citi Research, What to do about OATs?, 1 Oct 2026).
- **Regime shifts**: regulation and facilities change turns (the standing repo facility; the June 2019 disclosure change). Split the sample at the break; re-estimate.
- **Gross vs net supply**: gross issuance is not swapping or net duration: check the financial vs non-financial mix and the swapped share (J.P. Morgan, Issuance, pensions, and long-end spreads, 14 Sep 2018).
- **Tests' own assumptions**: the t-test needs normal monthly moves and Wilcoxon symmetry. Fat-tailed rate changes violate both; use the median and trimmed means as a cross-check.
- **Overlapping windows**: weekly auctions with +/-5-day windows overlap, so events share days and are not independent; the across-event t-stat is inflated. Thin the events (one per cycle), shorten the window, or cluster by month.
- **Settlement-day and mid-month effects** outside the period-end windows: coupon settlement on a corporate tax date can produce a squeeze; include them in calendar dummies.
- **Verify the checking tool**: before trusting a new screen, run it on a series with a known injected effect and on pure noise (the `--selftest` does this).

## Output
Return, for each tested effect:
1. A table: `effect | series | window or month | n obs | mean (bp) | median (bp) | sigma (bp) | up-ratio | p_t | p_wilcoxon | p_placebo | multiplicity-adjusted p | mean/sigma | grade A/B/C | mechanism | last-3-cycles`.
2. The number flagged vs alpha x scanned, and the sample split result.
3. A plot per effect: month-by-year heatmap or mean +/- 1 sigma bars; event-profile line (mean per offset with +/-2 s.e. band) with the placebo band shaded.
4. A verdict sentence: *tradable tilt / adjust the model / ignore*, with the carry, cost and stop context.
5. Hand-off: A- or B-graded timing tilts go to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) as a catalyst or entry-timing line, never as the thesis; calendar adjustments go to the relevant curve, linker or spread skill.

## Scripts
- [`scripts/seasonality.py`](scripts/seasonality.py): `monthly_screen` (month x year table, trimmed means, t, Wilcoxon, binomial, expected false flags), `weekday_screen`, `window_study` (event offsets, baseline-adjusted excess, t across events, placebo), `period_end_events`, `roll_window_mask`, `seasonal_factors` (ratio to centred 2x12 moving average), `sa_price`, `ff_year_end_decomp`. Reads the canonical long tables directly (`--where col=value`, `--scale 100` for `_pct` columns, CSV or Parquet; events from `auctions` or `calendars` with `--event-date-col`, `--event-where`). `python scripts/seasonality.py screen|weekday|window --help`. `python -I scripts/seasonality.py --selftest` checks injected effects, a null series, known factors, hand-computed SAP and fed funds algebra.

## Related skills
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): percentile and z-score screens that the calendar filters complement.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): multiple-testing, walk-forward and deflated-Sharpe controls for calendar scans.
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC errors, structural breaks and seasonal ARIMA when the screen needs a model.
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): holidays, roll stitching and snap times behind event-time alignment.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): the canonical tables named above.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): why funding turns occur and which facilities cap them.
- [fi-curve-construction](../fi-curve-construction/SKILL.md): installing turns and meeting-date steps in a curve.
- [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md): linker valuation that consumes the seasonal factors.
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auction concessions, redemptions and coupon reinvestment trades built on these windows.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md), [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md), [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md): delivery and roll calendars.
- [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md): separate turns from meeting steps in the priced path.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md): spreads and basis with quarter-end and year-end effects.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): holiday calendars and conventions per market.
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md), [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): where a seasonal tilt can be combined with other signals.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): G-SIB snapshots and leverage-ratio dates behind period-end turns.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bill-OIS paydown and tax-date cycles.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension, insurer and lifer seasonal buying that a screen may pick up.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event-day vol weighting and election-window templates.
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): pre-mortem when a trade rests on a calendar argument.
- [quant-bayesian-methods](../quant-bayesian-methods/SKILL.md): shrinkage, priors and Bayesian updating.

## References
- swapsball.net - Testing for seasonality (19 Nov 2017): the month x year procedure with trimmed means, t and Wilcoxon, roll-day exclusion, and the failed Bund asset-swap folklore.
- BofA Securities, Global Rates and FX Primer - Bond market seasonality explained (Ciana et al., 6 Jun 2022): up-ratio screens by market, GC and swap-spread seasonals, mechanism attribution.
- BNP Paribas, G10 Interest Rates Focus - EUR curve convexity: Lessons from history (25 May 2021): 2004-2020 seasonal windows and fly overshoot statistics.
- BofA Global Research, Technicals Explained: In 2025 (Ciana, Suttmeier, 14 Jan 2025): January barometer and first-five-day tables for the US 10y, dollar, oil and equity index, US 10y month-of-year and presidential-cycle tables, equity seasonal windows with in-window corrections, and barometer decay by decade.
- Ernest P. Chan - Quantitative Trading (Wiley, 2009): fixed-date seasonal trades, data-snooping remedies, year-by-year drawdown reporting.
- Willer and Saunders - Trading Global Macro Markets (Wiley, 2026): seasonal RV on bond futures, residual seasonality, decay of equity seasonals.
- Düring - Fixed Income Trading and Risk Management (Wiley, 2021): seasonal factors, linker projection, breakeven distortion, turn premium, index rebalancing, auction calendars.
- Federal Reserve Board - What Happens on Quarter-Ends in the Repo Market (FEDS Notes, 6 Jun 2025): quarter-end and month-end measures, event study, settlement-day effect.
- Federal Reserve Bank of New York - Facing Quarter-End Pressures: Understanding the Repo Market and Federal Reserve Tools (Perli, 12 Nov 2024): Sep 2024 quarter-end sizes and cleared-segment pressure.
- Citi Research - US Rates Weekly: Fixing the plumbing (30 Sep 2019): fed funds futures year-end decomposition and trade.
- Ametrano and Bianchetti - Everything You Always Wanted to Know About Multiple Interest Rate Curve Bootstrapping (SSRN, 2013); Ametrano, Bertocchi, Mazzocchi - Advanced Eonia Curve Calibration (SSRN, Dec 2016): turn-of-year jump sizes, jump-size formula, iterative removal.
- Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., 2022) and Coding Interest Rates (c. 2024): turns in curves, business-day modifiers, roll-down artefacts, seasonality curves.
- BofA Global Research - Welcome to the real world: Global inflation-linked primer (22 Jul 2025): seasonally adjusted price, breakeven distortion, toy examples.
- BofA Global Research - US Treasury auction primer (8 Mar 2024): issue and auction calendar, refunding schedule.
- Citi Research - US Rates Weekly: What to expect when you're expecting a turn (20 Apr 2018): auction-week drift in the 10y.
- Citi Research - North America Rates Focus: Corporate supply to bring spreads tighter (3 Jan 2017): January supply seasonality and year-end spread event study.
- Citi Research - European Rates Morning Call (19 Aug 2026): month-end index extension projections.
- Lehman Brothers - The Short-End of the Curve (10 Jul 2007): funding drivers by weekday and period-end; year-turn premium rarely realised.
- BofA Securities - UK Rates Viewpoint: Back to school: tough tests this term (Stengeryte, Capleton, 5 Sep 2024): gilt September seasonals and the "tailwind, not a signal" rule.
- Credit Suisse - Basis Points: A Guide to the Front-End and Basis Swap Markets (18 Feb 2010): fed funds calendar seasonals. Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., 2005): delivery timeline and first-notice calendar-spread pattern.
- RiskVal Highlights newsletter - Bond Futures Delivery (May 2022); RiskVal - Overview 201: Cash and Futures (12 Nov 2021): auction-window default and event normalisation. Citi Research - US Rates Vol Lab: Fair value vs seasonality (1 May 2017): vol seasonality by calendar month. Citi Research - US Rates Weekly: Summer lull (17 Jul 2015); J.P. Morgan - Issuance, pensions, and long-end spreads (14 Sep 2018); Citi Research - What to do about OATs? (1 Oct 2026); Conks - Plumbing Notes: Swifter Injections (4 Dec 2025): summer drift, swapped-share check, quarter-end distortion, year-end basis overpricing.
- Tuckman and Serrat - Fixed Income Securities (4th ed., 2022): averaging-contract hedge ratios, GC spike dates.
- Huggins and Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): pre-standing-facility quarter-end spikes, mid-month sampling; Huggins and Schaller - SOFR Futures and Options (Wiley, 2022): jump dates in the short end.
- Abate (Barclays) - US short interest rate primer (Jan 2025): averaging rules, year-end risk dieting. Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): December contract year-end cheapness.
- Conks (Monetary Mechanics) - The Great Flattening (4 Aug 2024); Plumbing Notes (27 Jun 2024, 10 and 26 Oct 2024, 5 Jan 2025, 15 Sep 2025, 24 Nov 2025); Plumbing Feed: Swaps & Interventions (29 Apr 2026): G-SIB snapshots, quarter-end sequences, settlement-day squeezes.
- Citi Research - Short-End Notes: SOFR/FF to go negative in Q3/Q4 (13 Jun 2025) and SOFR/FF spiking into quarter-end (27 Jun 2025); J.P. Morgan - What does the SRF mean for swap spreads? (12 Jul 2019); BofA Global Research - US Treasury repo primer: 2025 edition (7 Jul 2025) and US repo sensitivity: higher than expected (8 May 2025); Deriscope - Turn-of-the-Month Effect in SOFR Curve built out of 1- & 3-Month Futures (18 Feb 2024): USD funding turns and their curve treatment.
- J.P. Morgan - Drivers of cross currency basis in EUR, GBP, JPY, AUD & CHF (11 Mar 2015), Cross currency basis 4Q24 Outlook (26 Sep 2024) and 2H25 Outlook (5 Jun 2025), There is one market where USD funding stress could reemerge (20 Feb 2020); Citi - STIRT Weekly: Tokyo, we have a problem (week of 7 Aug 2026), You Shall Not Pass (14 Aug 2026), Beam me up, Scotty (21 Aug 2026): basis turns by currency.
- Citi Research - US Rates Weekly: Going nuclear (on the curve) (3 Feb 2017), Swearing in huge expectations (13 Jan 2017), The rocky road to a steeper curve (18 Jan 2019); J.P. Morgan - Markets struggle to feed the convexity beast (28 Feb 2020), Dynamic hedgers are long, banks are short (13 Sep 2019), The return of convexity hedging (31 Jan 2020), For cheap gamma, look to the long end (23 Aug 2019); Citi Research - European Rates Weekly: A narrative shift looms (17 Mar 2022): bill, tax, supply and vol calendars.
- Citi Research - How to trade US midterm elections (14 Aug 2026) and US midterms on the mind (2 Oct 2026); Citi Global Markets - Mid-week musings (19 Aug 2026); J.P. Morgan - Currencies amid long-end UST shenanigans (21 Aug 2026); BofA Global Research - US Vol Primer: A Guide for the Perplexed (Braizinha, 11 Mar 2024): election, September and event-day templates.
- Salomon Brothers - Understanding Treasury Bond Futures: Questions and Answers (Oct 1990); Clarus Financial Technology - What's the Deal with Invoice Spreads (17 Sep 2014); Quantitative Finance Stack Exchange - implied repo and the last delivery date (7 Jul 2018): delivery options and calendar.
- J.P. Morgan - The (par) curves they are a-changin' (23 Jul 2024); Deutsche Bank Index Quant - DBIQ Interest Rate Curve Creation Process (2 Feb 2023); BofA Global Research - UST RV Primer (2 May 2022); J.P. Morgan - US: Jobless claims continue to deliver positive labor signal (13 Aug 2026) and United States weekly (14 Aug 2026); Citi Research - The resilient narrative of US resilience (21 Aug 2026) and Canada Economics Weekly: Data lull comes to an end (13 Aug 2026): seasonal factors in linkers and macro data.
- Murphy - Machine Learning: A Probabilistic Perspective (MIT Press, 2012): seasonal state-space component; Tulchinsky et al. - Finding Alphas (Wiley, 2015): year-on-year changes, point-in-time data; Hasbrouck - Empirical Market Microstructure (2004): intraday seasonality.
- Heston and Sadka, Seasonality in the cross-section of stock returns (Journal of Financial Economics, 2008) (external): seasonal momentum definition.
- Benjamini and Hochberg, Controlling the false discovery rate (Journal of the Royal Statistical Society B, 1995) (external): multiple-testing control used in the screen.
