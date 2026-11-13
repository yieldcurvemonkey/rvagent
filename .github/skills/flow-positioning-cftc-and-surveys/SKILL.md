---
name: flow-positioning-cftc-and-surveys
description: Reads G10 rates positioning from CFTC TFF/COT futures data, client and sentiment surveys, options put/call flow and real-money flows (pensions and LDI, insurers, convexity hedgers, TIC, CTAs). Turns positions into DV01, point-in-time z-scores and percentiles, roll-pressure and convexity-adjustment residual reads, and tests whether a position is structural or a tradeable view. Use when asked about CFTC positioning, COT or TFF data, asset manager or leveraged fund net longs or shorts, basis trade size, crowded trades, short covering, Treasury futures roll pressure (TU FV TY UXY US WN, first notice), ED or SOFR futures convexity adjustment vs model, client survey net longs or neutrals, bull-bear sentiment, put/call, CTA stops, short squeeze, pension funded ratio, LDI, TIC or foreign official flows, Form PF, or whether a move is flow-driven.
---

# Flow positioning: CFTC, surveys and real-money flows

Positioning tells you who holds a trade and how hard they would have to unwind it. In rates it shows up in three
ways: as calendar-roll pressure (the crowded side must sell the front and buy the back before delivery), as a
residual the fundamental model cannot explain (convexity adjustments, skew, fly cheapness), and as crowding risk that
makes a move fragile (light volume, stop-loss waves, forced sales). Use positioning to explain a dislocation or size
an unwind risk. Do not trade a positioning extreme alone: the same indicator has behaved as contrarian in one market
and as a follower in another, so validate the sign per indicator and per market first.

## When to use
- A question about CFTC TFF/COT positions, asset manager (AM) or leveraged-fund (LF) net positions, open interest
  (OI) by contract, or whether a futures position is a view, a basis trade or a curve/RV leg.
- Treasury futures roll views (TU, FV, TY, UXY, US, WN) and calendar spreads around first notice day (FND).
- ED/SOFR (and other STIR) convexity adjustment (CA) vs model, and whether positioning explains the gap.
- Client surveys (net long share, neutral share), exposure-minus-view sentiment, options put/call flow.
- Real-money flow reads: pension funded status, LDI, insurers, TIC and official holdings, fund flows, CTA positioning.
- Not for: convexity mechanics of MBS and callables ([flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md),
  [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md)); dealer-level trade-repository
  flow ([flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md)); structural ALM demand modelling
  ([flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md)).

## Inputs (data-agnostic)
| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Long and short contracts by trader class, per futures contract (report `cftc_tff`) | `positioning` | weekly, as-of Tuesday; need >= 3y, prefer 5y+ | Use `pub_ts_utc` for timing, never `date` |
| Open interest and DV01 per contract | `positioning` (`oi_cnt`, `net_dv01_ccy`), `fut_static`, `fut_basket` | weekly; daily OI if available | Contract DV01 = CTD (forward) DV01 / conversion factor; ED and SR3 = 25 USD per bp per contract. Contract codes in the text (TU FV TY UXY US WN) map to the canonical `contract` values in the adapter; confirm the mapping |
| Futures settles and volume | `fut_quotes`, `stir_quotes` | daily, one snap per series | Roll-adjusted volume = abs(front volume - back volume) |
| Client survey shares (long, neutral, short) | `positioning` (report `survey`, `long_frac`, `neutral_frac`, `short_frac`) | weekly, >= 1y | if `neutral_frac` is null, neutral = 1 - long - short |
| Options flow (call and put notional, YTD) | `flows_trades` (`option_right`, `notional_ccy`), `opt_quotes` | daily | put and call notional are sums of `notional_ccy` by `option_right`; strip cancels and compression first |
| ED/SOFR CA inputs: futures rate, matched swap rate, cap/floor normal vol | `stir_quotes`, `curve_par`, `vol_surface` | daily, same snap | CA = futures rate - matched swap rate |
| CME-LCH or CCP basis | `ccp_basis` | daily | Check orientation before reading a sign (see Pitfalls) |
| Pension funded status, assets, liabilities; holdings by holder (TIC, Form PF-style) | `macro_series` (unit `ccy_bn`, `pct`) | monthly or quarterly, with release vintages | Quarterly regulatory data lag by months: treat as coarse |
| 5y par yield for valuation adjustment | `curve_par` | daily | Same snap as the holdings series |
| Auction results (tail, bid-to-cover, takedown) | `auctions` | per auction | Results hidden until `results_ts_utc` |
| Release and holiday calendars | `calendars` | daily | Release day moves with US holidays |

If an input is missing, ask the user or hand off to the data adapter. Never invent positions, surveys or flows.

## Method

### 1. Point-in-time indexing (do this first)
- CFTC TFF data are as of Tuesday and published Friday (about 15:30 New York). Release = as-of Tuesday + 3 business
  days. A federal holiday in the release week pushes the release out one business day: Tue 3 Nov 2026 releases Fri 6 Nov 2026;
  Tue 10 Nov 2026 would release Fri 13 Nov, but 11 Nov (Veterans Day) is a holiday, so it releases Mon 16 Nov 2026.
  `release_date` needs the holiday list from `calendars`; without it the result can be a day early.
- A signal at cutoff `t` may use a row only if `pub_ts_utc <= t`. Forward-fill from the release instant, not from the
  as-of date. Using the as-of date for a Friday signal reads three days of future data.
- Survey and fund-flow series follow the same rule with their own publication instants.
- `scripts/flow_positioning.py` implements `release_date`, `pit_daily` and a point-in-time `snapshot`.

### 2. Put positions in risk units
- Net contracts `n = long_cnt - short_cnt` (positive = net long). Gross = long + short.
- Net DV01 (ccy per bp, positive = long duration): `DV01_net = n x DV01_per_contract`. Read DV01, not counts. Contract
  sizes differ by product: 2y (TU) futures carry twice the face of 5y and 10y contracts ($200k vs $100k) but a DV01 no
  larger than FV and well below TY (risk weights below: TU 0.5, FV 0.5, TY 0.75).
  Sources report positions in $mm DV01 per bp or in 10y-equivalents ($bn).
- Aggregate roll-relevant OI in UXY-equivalent units, weights TU 0.5, FV 0.5, TY 0.75, UXY 1, US 1.5, WN 2.5, on the
  3-month moving average of OI (J.P. Morgan, US Bond Futures Rollover Outlook, 12 Aug 2026). Rule: a position matters
  more when aggregate OI is at a high, because more contracts must roll in a short window.
- Concentration = OI held by the 4 (or 8) largest longs or shorts / total OI, percentiled over 1y (Goldman Sachs, UST
  Futures Positioning Report, 2 Oct 2026, partial read). Use it as a squeeze-risk flag, not a direction signal.

### 3. Standardise
- z-score: `z_t = (x_t - mean_W) / sd_W` with sample sd and window `W` ending at `t`. Default `W` = 260 weekly
  observations (5y) for DV01 positions. Use 156 (3y) for contract-level AM net-long roll gauges, as J.P. Morgan does
  (Citi used 1y z for CA snapshots). Require a full window, otherwise report no z. Test robustness at 3y, 5y and 10y:
  Willer and Saunders (Trading Global Macro Markets, 2026) make this check because structural drift changes results.
- Percentile: share of the trailing window at or below `x_t`. Read it with the z-score: TY at the 99th percentile with
  z = 2.0 was called bearish for the roll (J.P. Morgan, Aug 2026).
- Change: 1w or 1m DV01 change divided by the 5y sd of changes of the same length (Goldman Sachs, Oct 2026, "5-year
  standard deviations"). Use it for "is the latest move unusual" questions.
- Survey: z of net long share vs its 1y history, and the neutral share with its 1y percentile (see Worked example D).
- Drift: asset-manager longs trend with fund inflows (BofA, US Rates Watch, Mar 2025), so a raw 5y z flatters recent
  growth. Prefer DV01 or a share of OI (TBAC normalises by coupons outstanding ex-SOMA, Jan 2024), and read the z of the
  normalised series.

### 4. Decide what the position is before reading it
Run these tests in order. A position that passes none of the first three is a candidate for a tradeable view; one
that passes any is structural or RV, and an unwind signal from it is weak.
1. **Mirror test (basis).** AM long and LF short in the same contract mirror each other: AM net longs vs LF net shorts
   have R^2 = 0.92 since 2015 (TBAC, Jan 2024), "nearly one-for-one" (CFTC MRAC, Dec 2024). If the mirror holds, the pair
   is the cash-futures basis trade, not opposing views. Check AM shifts against OI before reading either side.
2. **Fund-duration test.** Regress fund returns on the 10y UST yield, the dollar index and IG spread (TBAC, Jan 2024).
   If AM fund duration is near neutral while AM futures longs are at records, the long is a structural credit overweight
   re-hedged with futures, not a duration call.
3. **RV-leg test.** Regress the contract's position on the curve spread its CTD sits in. J.P. Morgan (Canary in a coal
   mine, Feb 2020) found WN shorts vs the 25s/30s spread at R^2 = 84.4% (1-week moving averages, last 9 months). The WN CTD is a
   25-year bond, so those shorts were a 25s/30s RV leg, not a duration short.
4. **Structural-driver test.** Regress front-end longs on the 2y yield. A tight fit (J.P. Morgan, Canary, Feb 2020:
   R^2 = 0.77, 1-week moving averages, last year) together with a named policy driver marks the position as structural:
   it unwinds slowly, if at all. Tests 3 and 4 regress smoothed levels of two trending series, so R^2 is flattered: also
   fit weekly changes (or test the residual for stationarity) before relying on it.

- **Basis size.** Upper bound on the long-cash / pay-fixed swap trade = hedge-fund long UST exposure minus all short UST
  exposure (BIS Quarterly Review, Dec 2025). Q2 2025, $bn: longs 2,379 - shorts 1,748 = 631, where the 1,748 of shorts splits into 1,060 of futures
  shorts matched to cash (basis) and 688 of other RV. The residual is an upper bound because funds also hold UST for
  margin and liquidity.
- **Gross shorts as a basis gauge.** Gross LF shorts across TU, FV, TY, TN, US, WN peaked near $615bn in Mar 2020; scale
  them to daily futures volume (WN LF shorts about 1.5x daily volume, other contracts about 30%, FV nearer 80%) and to
  government money-fund assets (J.P. Morgan, When market risk meets operational risk, 10 Mar 2020). Compare long cash with
  short futures by maturity bucket: a mismatch means the book is not a textbook basis trade (CFTC OCE Staff Paper 2024-007).
- **Futures to cash.** A futures change overstates cash change. Scale quarterly futures-value changes by about 0.6 to
  0.7 when proxying cash (CFTC OCE Staff Paper 2024-007, Sep 2024: coefficient -0.6 on short futures; futures change sd
  about $100bn vs $75bn for net cash). Part of that correlation is valuation, not quantity.

### 5. Positioning indicators and their sign
The sign is not fixed. Treat the table as the default hypothesis and test it on the market and window you trade.

| Indicator | Hypothesis | Evidence in library | Test before use |
|---|---|---|---|
| AM net long % OI (per contract, 3y z) | high = roll cheapens early, bearish calendar spread | J.P. Morgan (Aug 2026), Citi roll notes (Aug 2026) | Condition on regime: no early cheapening when AM longs were low in 2023 and early 2024 (Citi, Aug 2026) |
| AM and LF net directional futures positions (BofA calls non-commercial ex-LF "a cleaner way to assess" speculative direction, since AM longs mirror LF shorts) | unclear for rates; follower or contrarian depends on market | Willer and Saunders (2026): for bonds, CFTC extremes showed follow-through; reversals were an equity result. BofA (Mar 2025): fund-return regression follower for duration and curve, CFTC non-commercial modest contrarian for duration | Decile test: subsequent 1m to 6m 10y move minus average, by positioning percentile (BofA, Mar 2025). Weekly data with 1m+ horizons overlap: use non-overlapping dates or HAC (Newey-West) errors |
| Dealer net in ED/SOFR | dealer long widens the SOFR CA | Citi (Feb 2017, Sell Blues): record dealer longs pressure risk limits and widen CAs; monthly change in Blues CA minus model on monthly change in CFTC dealer ED positions, 1 Jan 2014 to 3 Jan 2017, R^2 = 0.32, positive slope (Citi, Jan 2017) | Check against the CA residual, not price; R^2 0.32 makes it a filter, not a forecast |
| AM + LF net ED/SOFR shorts (% OI, inverted) vs CA minus model | broadly inverse: when the short base covers, CA tightens toward model (futures richen vs swaps) | Citi (Jun 2021, Feb 2023, Oct 2026); J.P. Morgan (May 2017, "A better way to sell vol": excess CA vs CFTC dealer ED positions, 3y beta positive, strongest 2 to 3y forward) | Chart-based relationship: fit it yourself on monthly changes |
| Survey net long share (z vs 1y) and neutral share | net short with high neutrals = short base not crowded | J.P. Morgan (Canary, Feb 2020): 8% net short, about 1.3 sd below average, neutrals near top of range | Read net and neutral together |
| T-note options put/call, dollar-weighted (sum of OI x settle for puts / for calls), 1y z | rates-native gauge: low z = bullish-leaning options positioning | J.P. Morgan (Canary, Feb 2020): z -0.95 | Indicative; read with survey and CFTC |
| Cumulative options put/call (YTD notional) | above 100% bearish, below 100% bullish | BofA FX options-flow study (Feb 2021): one year of data | Indicative only |
| Trend-follower position (MA-sign model, -4..+4) | limited counter-signal in bonds | Willer and Saunders (2026): bond max-short and max-long buckets differ little | Use for flow timing, not as a contrarian rule |
| Stop-loss exposure of a CTA ensemble | >= 4 of 12 models stopping predicts above-average sigma moves | BofA CTA Monitor (Jun 2025): 9 of 15 largest 1-day sigma declines in S&P futures since 2010 coincided with stop waves; same pattern in TY and Bund | Count stops daily from price data |

### 6. Flow-to-price mechanics (where positioning explains a residual)

**6a. Calendar roll (futures).** Fair value of a calendar spread = cost of carry + CTD rich/cheap vs a fitted curve.
Positioning adds a residual term. Citi's regression (May 2019), in ticks at end of roll on normalised AM % OI from the
CFTC report before FND: FV: y = -17.517x + 2.5885 (R^2 = 0.64); WN: y = -14.666x + 3.039 (R^2 = 0.825; last ten cycles,
excluding the Nov 2016 roll). The gap between the roll and the fitted value is the positioning-adjusted residual.
These coefficients belong to one normalisation and sample: re-estimate them on your own normalisation. Pace matters:
an early roll (percent rolled well above the average of recent rolls) signals heavy net longs or pre-positioning.
J.P. Morgan's four calendar-spread drivers (Aug 2026) are basis convergence, positioning, CTD RV and forward financing;
score each bullish, neutral or bearish, then combine.
For the US bond roll specifically, Citi called the positioning signal "always relatively weak" and "not easy to prove
statistically" (May 2019; Feb 2023). The FV and WN fits above look strong (R^2 0.64 and 0.825), but ten cycles is a small
sample and fits flatter small samples. Exclude extreme-volatility cycles (Nov 2016) and re-test out of sample.

**6b. Convexity adjustment (ED/SOFR).** CA = futures rate - matched swap rate. The model CA is a one-factor Ho-Lee fit to
cap/floor vols, so vol is its main driver. The residual `CA - model` is then a flow term.
- Mechanism: AM and LF are net short futures; dealers take the long side and hedge by paying swaps, so they are
  "structurally short convexity adjustments" (Citi, Sell Blues, Feb 2017). Initial margin favours futures: CME/LCH margin
  on swaps and FRAs uses a 5-day close-out against 1 to 2 days for CME ED futures (Citi, Sell Blues vol lab, Jan 2018).
- Reading: CA above model and rising while model vol falls = positioning, not vol (Citi, Jan 2018; Left-side vols, Jun 2021).
  Short capitulation has historically richened the futures, converging CA down toward model (Citi, Jan 2018: "a short capitulation should richen ED CAs relative to fair value", then CAs "converge closer to fair value").
- Second regressor: the residual of 3y1y implied vol on rates (inverted) moves inversely with CA minus model
  (Citi, Short Blues convexity, Feb 2023). When vol underperforms the rate move, model CA falls while positioning keeps
  observed CA high.

**6c. Skew: flattening and richening risk reversals.** Signal = 3-month change in the 3m10y 25bp-out risk reversal
(payer minus receiver normal vol, bp). Bucket by historical percentile, then read the next 1-month change in the 10y
(Citi, Flatter skew, Jan 2017; monthly, Jan 2006 to Nov 2016):

| 3m change in RR, percentile | Avg next 1m change in 10y (bp) | Median (bp) | Share of rises |
|---|---|---|---|
| < 25th (flattening skew) | -11.5 | -5.0 | 36% |
| 25th to 50th | -2.1 | -1.1 | 48% |
| 50th to 75th | +0.2 | -4.2 | 45% |
| > 75th (richening payer RRs) | +8.8 | +11.1 | 69% |

Read the flattening side as a warning on duration shorts: core shorts hedged with low-strike options richen the low
strikes, so a flattening skew can signal a build-up of duration shorts, and the 10y fell on average in the bucket.
Read the richening side as core longs building: richer risk reversals were a strong predictor of higher rates. An
inverted short-dated skew (receivers over payers) can mean core shorts hedged with OTM receivers. The edge sits in the
tails, not the medians, so use it only with CFTC data.

**6d. Pensions and funded status (long end).** A higher funded ratio means more duration demand. Fully funded plans
defease by adding duration, recently through Treasuries and STRIPS, total-return swaps and bond options rather than
interest rate swaps (J.P. Morgan, Issuance, pensions and long-end spreads, Sep 2018). The channel is Treasury demand:
under the US convention (swap minus Treasury), a higher funded ratio lifts the long-end spread (less negative). STRIPS
issuance is a public proxy for pension duration demand. Nowcast the funded ratio from 1m factor moves. In J.P. Morgan's
regression (Pension re-risking, Apr 2020), partial betas of monthly % returns (bp) on the 30y yield change (bp) are -3.5 for assets and -12.6 for liabilities
(credit spread: -2.0 and -6.4), i.e. effective durations of about 3.5y and 12.6y, so liabilities move more when yields
move and wider credit spreads (a higher liability discount rate) help the funded ratio. Check: 12/29/17 to 8/31/18, assets $1,555bn to $1,547bn, liabilities $1,775bn to
$1,657bn, funded ratio 87.6% to 93.4% (J.P. Morgan, Sep 2018). Pension flows are slow (contributions over months): do not
trade tax-deadline cliffs. Profit-taking on hedges after a credit reversal is secondary supply of Treasury duration and
bearish for long-end spreads (J.P. Morgan, Apr 2020).

**6e. Auction screen.** Strong auction = average z-score of tail (or through), investor takedown and bid-to-cover over
the last two auctions (Citi, Pension plan for 20s, Oct 2026). Two strong 10y auctions in a row were followed by rising
10y yields in that small sample: treat as a contrarian warning, not a signal.

**6f. Official and foreign holdings (TIC).** Valuation-adjusted purchases remove the price effect from the change in
market value:

`purchases_t = (MV_t - MV_{t-1}) + D x MV_{t-1} x dy_t`, with `dy` the 5y yield change in decimal (+10bp = 0.001) and
D = 5 years, the average maturity of foreign holdings from the annual TIC survey used as duration (convexity ignored;
a coupon portfolio's duration is a little lower) (Citi, Trade worries linger, May 2019; the same adjustment appears in Citi, Bessent and Warsh, Aug 2026). A
holding that falls only because yields rose gives zero purchases. Z-score the result over the full sample. Custody moves
distort country data: holdings held through a different custodian can look like selling in one centre and buying in
another. Cayman sales may be hedge funds unwinding basis trades, not official selling. Wait for a string of months before reading a trend.

**6g. CTA positioning.** Trend-follower position = sum over n in {22, 66, 200, 252} of sign(price - SMA_n), range -4 to +4
(Willer and Saunders, 2026). For CTA risk, unwinds matter more than accumulation, and ensemble stops matter more than the
level. The 12-model stop ensemble is a separate construct: 3 lookbacks times 4 stop thresholds (thresholds not published). The sigma move = daily return / prior-day realised vol
(de-annualised), with EWMA lambda 0.97 (BofA CTA Monitor, Jun 2025). A reversal that trips many stops at once is the
large-move case.

**6h. Survey and options sentiment.** Exposure-minus-view: plot the sentiment exposure index minus the view index,
each on a -100 to +100 scale (BofA, UK Rates Viewpoint, Sep 2024). A constructive view without rising exposure means
investors stay cautious. Cumulative put/call: `sum(put notional YTD) / sum(call notional YTD)`. Example: January puts 80
and calls 100 (80%), February puts 110 and calls 100, so (80 + 110) / (100 + 100) = 95%: still below 100% (call-heavy) but
drifting bearish (BofA, Feb 2021, EURUSD, $bn). That study is FX options from a trade repository, not rates: for rates
use the same ratio on listed or repository swaption notional and treat the sign as a hypothesis. Use the
notional-weighted average strike minus spot only as a weak tiebreaker: its direction called next month's average spot
64% of the time in 2020, against 58% for the change in cumulative put/call.

## Worked examples
**A. Roll pressure from AM z-scores (J.P. Morgan, US Bond Futures Rollover Outlook, 12 Aug 2026; 3y lookback).**

| Contract | AM net long (000s) | Percentile | 3y z | Calendar-spread read |
|---|---|---|---|---|
| TY | 2,595 | 99% | 2.0 | bearish, positioning |
| UXY | 713 | 96% | 1.5 | mildly bearish, positioning |
| WN | 1,061 | 83% | 1.6 | neutral (basis convergence vs positioning) |
| US | 552 | 79% | 0.9 | bullish (recent decline in AM longs cited; other drivers dominate) |
| FV | 2,963 | 58% | 0.2 | neutral |
| TU | 1,693 | 28% | -0.5 | neutral |

Lesson: US had a z of 0.9 and still scored bullish, and WN at 1.6 stayed neutral (basis convergence offset positioning).
Positioning is one of four drivers; the z-score is a gauge, not the verdict.

**B. Calendar residual (Citi, Deal or no deal, 10 May 2019).** Using the WN fit in 6a: a roll trading 1 tick rich against
the fitted value is a residual, not a roll view on its own. Citi's 8 May 2019 WN call was 3 ticks cheap to carry but about
1 tick rich vs positioning, with an early roll: bearish.

**C. CA positioning trade (Citi, Sell Blues convexity adjustments, hedged, 9 Feb 2017).** Entry: $200k DV01, bought as
2,000 H0-Z0 ED packs (each pack is four quarterly contracts, so 8,000 contracts x $25 per bp = $200k per bp), against
paying a $2bn matched CME swap at 8.8bp, hedged by paying the 2s5s10s belly (DV01 weights 0.705 / -1 / 0.465). Thesis:
AM and LF had added more than $20.5mn DV01 of ED shorts since the election, so the CA was rich to model. Targets +$600k,
stop -$350k. Closed 6 Jun 2017 at 6.6bp, +$552k. Arithmetic check (own): the CA move from 8.8bp to 6.6bp is 2.2bp x
$200k/bp = $440k; carry and the hedge account for the rest.

**D. Survey, RV and structural tests together (J.P. Morgan, Canary in a coal mine, 25 Feb 2020).** Survey net 8% short,
about 1.3 sd below the 1y average, with neutrals near the top of their 1y range: the short base is not crowded. CFTC net
longs (ED and UST futures) were 1.45 sd below average. Excluding WN, aggregate speculative positioning was near its 1y
average, so the headline short-covering warning overstated the risk. The WN shorts were an RV leg (test 3). Verdict: no
crowded-short squeeze signal.

**E. Pension funded ratio (J.P. Morgan, Pension re-risking and long-end swap spreads, Apr 2020).** Feb 2020: assets
$1,602bn, liabilities $1,949bn, funded ratio 82.2% (check: 1,602 / 1,949 = 82.2%). The March projection was 80.3%; a full credit-spread reversal would take it to about 76%, with the funding gap above $475bn.

## Signals & interpretation
| Condition | Action | Source / basis |
|---|---|---|
| Roll: AM net long z (3y) >= 2 | Bearish calendar spread into FND, unless basis convergence or forward financing outweighs | TY at z 2.0 called bearish (J.P. Morgan, Aug 2026) |
| Roll: AM net long z in [1, 2) | Mild bearish; size small | UXY at z 1.5 called mildly bearish (same) |
| Roll: AM net long z in (-1, 1) | No positioning-based view | FV z 0.2 and TU z -0.5 neutral (same) |
| Roll: early pace well above average with high net longs | Expect early cheapening; pre-positioning possible | Citi (Deal or no deal, May 2019) |
| CA minus model wide while model vol falls | Positioning, not vol, is the driver: consider selling CA with a hedge (own default; examples in worked example C) | Citi (Jan 2018; Jun 2021) pitfall rule |
| CA trades | Citi examples: target 4bp tightening, stop 2.5 to 3bp widening | Citi (Left-side vols, Jun 2021; Short Blues, Feb 2023): records of trades, not rules |
| Skew: 3m change in 3m10y 25bp-out RR below 25th percentile (flattening) | Duration shorts may be building (low-strike hedges); the 10y fell on average next month (-11.5bp) | Citi (Flatter skew, Jan 2017) table, 6c |
| Skew: 3m change above 75th percentile (richening payer RRs) | Core longs may be building; the 10y rose on average next month (+8.8bp), a caution for duration longs (crowded-long risk), not a reason to fade the sell-off | Citi (Flatter skew, Jan 2017) table, 6c |
| Survey net short with neutrals near top of 1y range | Short base not crowded: do not chase a squeeze | J.P. Morgan (Canary, Feb 2020) |
| Cumulative put/call above 100% (YTD) | Bearish for the currency against USD in the FX study (more puts bought); confirm pair orientation | BofA (Feb 2021): one year of data |
| >= 4 of 12 CTA models stopped | Expect above-average sigma moves in that market (shown for S&P futures; same pattern in TY and Bund, 2010 to May 2025) | BofA CTA Monitor (Jun 2025) |
| Two strong auctions in a row | Do not read as bullish; yields rose after in the sample | Citi (Pension plan for 20s, Oct 2026), small sample |
| Funded status near 100% and a 10y rally of 50bp or more | A rally of that size would push funded status below 100%, and pension duration demand falls after large rallies: expect less long-end support, not a sell program | BofA (Jun 2024 and Nov 2024; sensitivity, not an event) |
| Any positioning z beyond 2 with price not yet confirming | Wait for a price break, or flag as devil's-advocate material | Willer and Saunders: bonds follow through |

## Pitfalls
- **Direction from OI is unreliable.** Market open interest is always flat net. Daily OI cannot separate round-trips from
  one-way moves, shorts often hedge cash longs, and OI has roll seasonality (Düring, Fixed Income Trading and Risk
  Management, 2021). Use the OI x rates classification only as a proxy, and only alongside TFF class data.
- **TFF classes cover a minority of OI.** The identified classes covered only 35% to 45% of 10y note OI (Düring, 2021).
  Class moves describe that share of the market only.
- **Dealer classification noise.** US dealers are often marginally net long futures against cash inventory, while EUR and
  JPY dealers are normally net short futures (Düring, 2021). A proprietary-trading firm hedging with futures can be
  reported as an LF short (September 2019 repo stress). LF shorts are not all directional bears.
- **AM long / LF short is not a view.** The mirror is basis, and the AM long is often a structural credit overweight
  re-hedged with futures (TBAC, Jan 2024). AMs use futures because repo counts as interest expense and toward leverage
  limits under the '40 Act, and futures are operationally simpler (CFTC MRAC, Dec 2024).
- **Stale data.** CFTC data were missing during the 2019 shutdown and after 24 Jan 2023 (Citi, Time for moderation, Feb 2023).
  Default rule (own): when the last release is more than 10 calendar days old (one release missed), flag the data stale (`data_ok = false`) and use
  proxies: OI change with yield change, the CME-LCH basis and the CA residual (Citi, Shorts increasing?, Jan 2019).
- **Basis proxies are not pure positioning.** CCP basis includes clearing costs, which differ by client and dealer.
  Policy-driven spikes revert while the structural part persists (SUERF/ECB, Jul 2024; Citi, Shorts increasing?, Jan 2019).
- **Form PF is quarterly, lagged and often read from charts.** Treat magnitudes as approximate. The upper-bound residual
  overstates the swap trade whenever funds hold UST for margin and liquidity.
- **Gross notional means little.** Net and convert to DV01 or 5y-equivalents before comparing books.
- **Fast unwinds, slow builds.** Withdrawals come abruptly and inflows slowly. Crowded trades unwind when a related market
  cracks, not on a change in fundamentals (e.g. a stress in one market forces stops in swap spreads).
- **Light volume is fragile.** A repricing on light volume reverses on a small shift in flow (J.P. Morgan, Formosa note,
  21 Feb 2020: January volumes were 57% and 24% of 2019 and 2018 levels).
- **Priced or not.** Check whether the obvious leg is already priced. If it is, trade the second-order leg.
- **Overlapping returns.** Forward 1m to 6m changes sampled weekly, and 3m changes sampled monthly (the skew table), share
  observations: effective sample size is far smaller than the row count and t-stats are inflated. Use non-overlapping
  windows or HAC errors, and require the sign to hold across sub-periods.
- **Dealer futures hedge swap books.** Dealer net futures roughly offset the dealer swap book (Mixon and Onur, CFTC OCE,
  Apr 2020): net them before reading a dealer position as direction.
- **Sample size.** One-year options-flow hit rates, 20-fund regressions and single-year calendar tables are small. Check
  the same test on 3y and 10y windows before trusting a hit rate.
- **Regime breaks.** Re-estimate roll and CA regressions each year, and drop extreme-volatility cycles (Nov 2016) from fits.
- **Release timing.** Use `pub_ts_utc` for every signal (Method 1). Using as-of dates for timing is a common look-ahead error.
- **CCP basis orientation.** The canonical `ccp_basis` stores LCH minus CME by default, while some notes quote CME-LCH.
  Confirm orientation before reading a sign; a widening CME-LCH basis was read as fresh back-end shorts (Citi, Shorts
  increasing?, Jan 2019).

## Output
Return a positioning snapshot for each contract requested, as a table:

| Field | Content |
|---|---|
| contract, class | e.g. TY, asset_manager |
| as-of / released | as-of Tuesday and release instant (UTC) |
| net contracts; net DV01 ($mm/bp) | signed; positive = long duration |
| z (3y and 5y) and percentile | from the point-in-time snapshot |
| 1w and 1m change in sd units | unusual-move flag at 2 sd |
| concentration (top 4, top 8) | and its 1y percentile |
| AM % OI and roll view | bullish / neutral / bearish, with the z band from the signals table |
| structural tests 1 to 4 | pass / fail, with R^2 for tests 3 and 4 |
| data freshness | days since release; stale flag |
| verdict | roll view, residual (CA or skew), crowding risk, or no positioning signal |

Then hand off: an actionable idea goes to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), a crowding or
unwind question to [rv-devils-advocate](../rv-devils-advocate/SKILL.md), and an ongoing signal to
[rv-trade-monitoring](../rv-trade-monitoring/SKILL.md). State the window, the sign convention (positive = net long; positive
z = above average), the release instant used, and whether any proxy was used.

## Scripts
- [`scripts/flow_positioning.py`](scripts/flow_positioning.py): `release_date`, `rolling_zscore`, `rolling_percentile`,
  `pit_daily` (point-in-time daily view), `valuation_adjusted_flow`, `cumulative_put_call`, `ma_trend_position`,
  `swap_trade_upper_bound`, and a CLI snapshot of net contracts with z and percentile as of a date:
  `python scripts/flow_positioning.py --positioning PATH --as-of 2026-11-12 --window 260`.
  `--selftest` checks each function against a known answer (for example the 95% put/call example and the 631 Form PF residual).

## Related skills
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): trade-repository dealer and client flow; complements CFTC classes
- [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md): convexity-hedger flows that drive swap spreads and vol
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension, insurer and bank ALM demand for long-end duration
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable and structured-note vega supply
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): calendar roll fair value and roll dynamics
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): CTD and delivery effects in the roll
- [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md): futures vs swap convexity adjustment and model dependence
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): CME-LCH basis as a flow gauge
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): cash-futures basis and funding for the basis trade
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap spreads as the price expression of duration flows
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z-score and percentile conventions used here
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): release timing, stale data, holiday calendars
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical tables used as inputs
- [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md): auction results and holder flows behind the auction screen and TIC reads
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR futures relative value where the CA residual is a leg
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): trend and CTA-style technical positioning
- [rv-devils-advocate](../rv-devils-advocate/SKILL.md): crowding and unwind review of any positioning-based idea
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): writing up a trade that rests on positioning
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): testing positioning signals out of sample

Market-by-market differences and proxies for markets without public futures positioning are in
[references/g10-markets-and-proxies.md](references/g10-markets-and-proxies.md). Extra worked numbers (the 2019 roll
calls, the Form PF path, the callable and lifer supply, the FX intervention episodes) are in
[references/worked-examples.md](references/worked-examples.md).
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): rule-based duration and country signals.

## References
- Citi Research - US Rates Weekly, "Deal or no deal: Rates implications" (J. Mathai et al., 10 May 2019): AM % OI roll regressions, roll views.
- Citi Research - Treasury Futures Roll Sep26-Dec26 (R. Datla, J. Williams, A. Vazquez Plata, 18 Aug 2026): roll pace, positioning-regime conditioning.
- J.P. Morgan - US Bond Futures Rollover Outlook (I. Ozil, C. Hayward, E. Alptuna, 12 Aug 2026): AM net-long z-scores, risk-weighted OI, roll calls.
- Citi Research - North America Rates Trade Idea, "Sell Blues convexity adjustments, hedged" (R. Bikbov, J. Williams, 9 Feb 2017): CA mechanism, sizing, trade record.
- Citi Research - US Rates Vol Lab, "Sell Eurodollar convexity in Blues" (R. Bikbov, J. Williams, 8 Jan 2018; partial read): margin reason for futures, capitulation regression, trade record.
- Citi Research - US Rates Weekly, "Swearing in huge expectations" (J. Mathai et al., 13 Jan 2017): dealer-positioning vs CA regression, corporate-issuance seasonality.
- Citi Research - US Rates Vol Lab, "Left-side vols' outperformance" (M. Chang, J. Williams, A. Appeddu, 22 Jun 2021; partial read): CFTC % OI vs Blues CA-minus-model, trade record.
- Citi Research - US Rates Weekly, "Time for moderation" (J. Mathai et al., 17 Feb 2023): roll driver list, futures vs swap positioning, stale CFTC handling.
- Citi Research - Rates Vol Lab, "Short Blues convexity via futures/swaps" (M. Chang, J. Williams, A. Appeddu, 21 Feb 2023): CFTC % OI vs CA-minus-model residual.
- Citi Research - North America Rates Focus, "Flatter skew is a warning signal for duration shorts" (R. Bikbov, 12 Jan 2017): skew-change buckets.
- Citi Research - US Rates Weekly, "Trade worries linger" (J. Mathai et al., 17 May 2019): valuation-adjusted TIC flows with z-scores.
- Citi Research - US Rates Weekly, "Can Secretary Bessent and Chair Warsh save the curve?" (J. Williams et al., 21 Aug 2026): TIC valuation adjustment, pension equity-rotation levels.
- Citi Research - North America Rates Focus, "Shorts increasing? An alternative view of positioning" (J. Williams, 16 Jan 2019): CME-LCH basis and CA as CFTC-free proxies.
- Citi Research - US Rates Weekly, "Pension plan for 20s?" (J. Williams et al., 9 Oct 2026): auction-strength screen, AM SOFR positioning vs CA.
- J.P. Morgan - A better way to sell vol: CME-based convexity adjustments are rich (J. Younger, D. Sarkar, M. Salem, 3 May 2017): excess CA regressed on CFTC dealer ED positioning.
- J.P. Morgan - US Treasury Market Daily, "Canary in a coal mine" (J. Barry et al., 25 Feb 2020): per-contract CFTC decomposition, RV vs structural regressions, survey neutrals.
- J.P. Morgan - Renewed Formosa supply continues to flatten the long end (J. Younger et al., 21 Feb 2020): callable supply and the light-volume reversal caution.
- J.P. Morgan - When market risk meets operational risk (J. Younger, M. Salem, H. St John, 10 Mar 2020): LF gross shorts vs volume, basis unwind arithmetic.
- J.P. Morgan - Pension funded-status papers: "Issuance, pensions, and long-end spreads" (J. Younger, M. Salem, 14 Sep 2018) and "Pension re-risking and long-end swap spreads" (J. Younger, H. St John, 3 Apr 2020): funded-ratio and long-end swap spreads, STRIPS as a proxy, funded-ratio nowcast and attribution betas.
- Treasury Borrowing Advisory Committee - Discussion of Treasury Futures Positions Across Different Investor Types (30 Jan 2024): TFF categories, AM/LF structure, crowding dashboard.
- CFTC Market Risk Advisory Committee - The Treasury Cash-Futures Basis Trade and Effective Risk Management Practices (Dec 2024): AM/LF mirror and why AMs use futures.
- CFTC Office of the Chief Economist - OCE Staff Paper 2024-007, Observations on the Treasury Cash-Futures Basis Trade (S. Mixon, A. Orlov, 23 Sep 2024): basis sizing, futures-to-cash scaling, maturity matching.
- BIS Quarterly Review - Goodbye Libor, hello basis traders (T. Ehlers, K. Todorov, Dec 2025): Form PF upper bound on the swap trade, basis footprint.
- BofA Global Research - US Rates Watch, "Long UST outflows and dealer holding highs" (M. Cabana et al., 10 Mar 2025): positioning dials, OI x price classification, follower and contrarian back-test.
- BofA Global Research - US Rates Viewpoint, "UST supply and demand in '25" (M. Swiber, 26 Nov 2024) and "Basics of UST supply and demand: outlook for 2H '24" (M. Swiber, 24 Jun 2024): buyer-base framework, funded-status sensitivity to a 50bp rally.
- BofA Global Research - US Rates Watch, "Mixed UST positioning picture; China and Japan buy USTs but reduce duration" (M. Swiber, A. Zhang, 22 Apr 2024; partial read): momentum vs contrarian table by positioning percentile.
- CFTC Office of the Chief Economist - Risk Appetite and Intermediation by Swap Dealers (S. Mixon, E. Onur, OCE Staff Paper 2020-004, Apr 2020): dealer futures as swap-book hedges.
- Conks (Monetary Mechanics, Substack) - Plumbing Notes: The Post-QT Era (24 Nov 2025; Form PF chart read, low confidence, used only for the dating caution in the worked-examples file).
- BofA Global Research - UK Rates Viewpoint, "Back to school: tough tests this term" (A. Stengeryte, M. Capleton, 5 Sep 2024): exposure-minus-view sentiment survey.
- BofA Global Research - Systematic Flows Monitor, "More CTA models = better impact estimates" (C. Kotecha et al., 2 Jun 2025): 12-model stop-loss ensemble, sigma-move definition.
- Willer, D. and Saunders, A. - Trading Global Macro Markets (Wiley Finance, 2026): CFTC z-bucket follow-through for bonds, trend-position model, window robustness.
- Düring, A. - Fixed Income Trading and Risk Management (Wiley, 2021): OI and TFF reading caveats, PTF misclassification, dealer positioning by market.
- BofA Global Research - FX Viewpoint, "SDR: What do FX options flows tell us?" (V. Iaralov, H. Du, 1 Feb 2021): cumulative put/call, strike signal, noise filter.
- Goldman Sachs - UST Futures Positioning Report (desk material, 2 Oct 2026, partial read): DV01 positioning, sd and percentile, concentration.
- Commodity Futures Trading Commission - Commitments of Traders explanatory notes (external): report categories, as-of and release timing.
- SUERF Policy Brief No 940, "Back to the basi(c)s: what is the CCP basis" (I. Boudiaf, S. Kretschmann, M. Scheicher, Jul 2024): CCP basis sign and what it measures.
