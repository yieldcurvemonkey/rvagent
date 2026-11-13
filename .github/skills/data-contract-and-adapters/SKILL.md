---
name: data-contract-and-adapters
description: "Canonical data contract for the G10 rates RV agent: table schemas (swap/OIS curves, discount factors, bonds and linkers, repo, bond and STIR futures, deliverable baskets, options and swaption vol, swap spreads/ASW, tenor/xccy/CCP basis, FX forwards, inflation fixings/breakevens/seasonals, auctions, CFTC positioning, SDR prints, central-bank meetings, calendars, prediction-market probabilities, CDS, CSA terms, MBS/TBA, order books, backtest signals/positions/trades/P&L), unit and sign conventions, point-in-time and snap rules, the vendor-agnostic adapter interface and a validator. Use when connecting a data source (CSV/Excel export, database, vendor SDK, internal pricer), writing or reviewing an adapter, mapping tickers or fields to canonical ids, checking units (percent vs bp vs decimal, 32nds, 100 minus yield), look-ahead, release lags or vintages, choosing which table a skill reads, or asking for missing data. Triggers: schema, canonical table, adapter, loader, ETL, settle vs close, as-of, validate data."
---

# Data contract and adapters

Every RV skill reads the same canonical tables, so swapping a data vendor, database or pricing library never
touches a skill. This skill fixes the contract: table names and keys, units in column names, explicit signs,
point-in-time rules, one adapter interface, and a validator that rejects data before it can quietly corrupt a signal.
The column-level specification is in [references/schemas.md](references/schemas.md), which is the single source of
truth. The validator parses that file, so the documentation and the checks cannot drift apart.

## When to use
- "Connect my data", "here is a CSV/Excel export", "we have a database/SDK/internal curve library": build an adapter.
- A skill names a canonical table (`curve_par`, `bond_quotes`, ...) and you need its columns, units or key.
- Numbers look 100× or 10,000× off, a book looks flat, spreads have the wrong sign, a universe is empty on some dates.
- Before any backtest: check for look-ahead, release lags, revisions, snap mixing and survivorship.
- A requested analysis needs data that is not in `data/`: produce a precise request.
- A new skill needs a field the contract lacks: propose a contract change here (never read a vendor field directly).

## Inputs (data-agnostic)
This skill defines the inputs for every other skill. The full columns are in [schemas](references/schemas.md).

| Table | Holds (one row per primary key) | Main consumers |
|---|---|---|
| `calendars` | holidays and early closes per settlement or exchange calendar | fixings, schedules, hygiene |
| `cb_meetings` | policy meeting schedule (decisions go to `rate_fixings`) | policy pricing, meeting-dated curves |
| `rate_indices` | RFR, IBOR, policy, repo and CPI index definitions, publication lags, cessations | conventions, compounding |
| `swap_conventions` | fixed/float frequency, day counts, spot and pay lags per `curve_id` (and per tenor band) | curves, risk, carry |
| `bond_static` | govt bond and linker terms, versioned by `valid_from` (taps) | bond, spread, futures, inflation |
| `fut_static` | bond and STIR futures terms: quote type, tick, bp value, delivery and reference dates | futures, STIR |
| `fut_basket` | deliverable bonds and conversion factors per contract | basis, CTD, invoice spreads |
| `opt_static` | listed options on bond and STIR futures | vol |
| `symbol_map` | source symbol → canonical id, unit served, multiplier | adapters |
| `roll_map` | generic (front, CM1, on-the-run) → specific instrument per date, with roll rule | roll, backtests |
| `curve_par` | par swap/OIS rates and govt benchmark par yields by curve, start and tenor | curve, PCA, carry, scans |
| `curve_zero` | discount factors and zero rates by node, interpolation and build id | curves, risk, forwards |
| `rate_fixings` | published fixings and policy rates with publication time and vintage | STIR, compounding, funding |
| `bond_quotes` | clean, accrued, dirty, yield, bid/ask per bond | bond RV, ASW, basis |
| `repo_rates` | GC and special repo by collateral and term; specialness | funding, basis, carry |
| `fut_quotes` / `stir_quotes` | bond futures / STIR futures prices, volume, open interest | futures, STIR |
| `opt_quotes` / `vol_surface` | listed option premia and normal vols / swaption and cap grids by expiry × tenor × strike offset | vol |
| `swap_spreads` | swap spreads, ASW, invoice spreads with explicit sign convention | spreads |
| `basis_swaps` / `ccp_basis` | tenor, index and xccy basis / LCH − CME basis | basis, xccy |
| `fx_rates` | FX spot, outrights and forward points | xccy, hedged returns |
| `infl_fixings` / `infl_swaps` / `infl_seasonals` | CPI prints with vintages / ZC breakevens / monthly seasonal factors | inflation |
| `auctions` | auction calendar and results (stop, WI, tail, cover) | supply, seasonality |
| `positioning` / `flows_trades` | CFTC-style positioning and surveys / trade-repository prints | flows |
| `events_probs` / `macro_series` | event and meeting probabilities / releases, consensus, balance-sheet aggregates, published term premia, market indices and prices, bank ratios (naming and units in schemas) | macro, event risk |
| `cb_texts` | central-bank statements, minutes, speeches and Q&A with release time | macro-central-bank-nlp |
| `cds_quotes` | CDS par spread or upfront by entity, tenor and contract terms (sovereign, counterparty) | CDS basis, XVA |
| `csa_terms` | collateral terms per netting set: threshold, MTA, eligible collateral, remuneration | collateral and XVA |
| `bond_holdings` / `issuance_plan` | central-bank and stripped holdings by line / debt-office gross, net and buyback plans | free float, supply |
| `callable_issuance` | callable and structured-note deal log with status vintages | vega supply |
| `mbs_tba` / `mbs_pool_stats` | agency TBA and specified-pool prices / pool factor, WAC, WALA, CPR, OAS | MBS convexity |
| `dealer_flow` / `book_snapshots` / `bid_offer` | dealer-tagged prints / order-book depth / half-spreads by structure and quote type | flows, costs, execution |
| `signals` → `positions` → `trades` → `pnl`, plus `trial_log` | backtest and live-book I/O, and the log of every run | bt-, port-, rv-trade-monitoring |

Minimum data by task. Ask for exactly this, no more:

| Task | Tables | History |
|---|---|---|
| Swap curve / fly / PCA RV | `curve_par` (+ `swap_conventions`) | daily, ≥ 3y, tenors 1y–30y |
| Forward-space, carry, roll-down | `curve_par` or `curve_zero`, `rate_fixings` | daily, ≥ 1y |
| Bond rich/cheap, switches, ASW | `bond_static`, `bond_quotes`, `curve_par`, `repo_rates` | daily, ≥ 1y, full outstanding universe incl. matured |
| Futures basis / CTD / invoice | `fut_static`, `fut_basket`, `fut_quotes`, `bond_quotes`, `repo_rates` (term to delivery) | ≥ 2 contract cycles |
| STIR / policy pricing | `fut_static`, `stir_quotes`, `rate_fixings`, `cb_meetings` | daily, ≥ 1y |
| Vol RV | `vol_surface` or `opt_static` + `opt_quotes`, plus the underlying curve | daily, ≥ 2y |
| Xccy / FX-hedged | `basis_swaps` (xccy), `fx_rates`, both `curve_par` | daily, ≥ 2y |
| Inflation | `infl_fixings`, `infl_swaps`, `infl_seasonals`, linker `bond_static`/`bond_quotes` | monthly prints ≥ 5y |
| Flows | `positioning`, `flows_trades` (dealer methods add `dealer_flow`) | weekly ≥ 3y / daily ≥ 6m |
| Sovereign CDS basis | `cds_quotes`, `bond_quotes`, `swap_spreads`, `basis_swaps` | daily, ≥ 3y |
| Collateral / XVA | `csa_terms`, `curve_zero` (incl. `<CCY>-CSA-<COLL>`), `basis_swaps`, `cds_quotes` | static + daily |
| Supply, free float | `auctions`, `issuance_plan`, `bond_holdings`, `bond_static` | per release |
| Backtest | the above plus `roll_map`; writes `signals`, `positions`, `trades`, `pnl`, `trial_log` | point-in-time |

If an input is missing, ask for it (template below) or hand off to the `rv-data-engineer` agent. Never invent values.

## Method

### 1. Contract rules
1. **Long (tidy) tables**, one row per primary key, which must be unique. Wide date × tenor matrices are views built
   at read time, never the stored form.
2. **Units in the column name.** Never infer a unit from magnitude: a "|x| < 1 means decimal" rule is a latent 100× or
   10,000× bug. Convert once, at the adapter, using `symbol_map.multiplier`.
3. **Signs travel with the data** (see the sign table). Signed DV01, signed weights and explicit `sign_convention`.
4. **Specific instruments are the primitive.** Generic and constant-maturity series are views through `roll_map`.
   Positions freeze the specific instrument at entry (`SWAP:USD-SOFR:2026-11-12:2036-11-12`, `FUT:ZN:2026-12`).
5. **Point-in-time.** `date` is the observation date; `pub_ts_utc` is when a value became knowable. Static rows are
   versioned (`valid_from`/`valid_to`), and revisions are appended as new vintages, never overwritten.
6. **One snap per series**, recorded on every row.
7. **Store data, not models.** Store quotes, curve nodes (DF + interpolation + `build_id`) and vol grids.
   Calibration and pricing happen in skills, and a rebuilt curve must reprice its inputs.
8. **Quality in-row.** Flag with `data_ok=false` and `dq_reason`; do not delete. Required columns may not be null.
9. **Cash flows are explicit.** Clean, accrued and dirty prices are separate columns. Coupons come from the bond
   schedule, never from the price series. P&L components sum to the total.

### 2. Units and signs
Levels are stored in percent. Differences and vols are stored in bp. **Every analysis, threshold and report is in bp**
(the repo convention): Δbp = 100 × Δpct, and bp = 10,000 × decimal.

| Quantity | Column form | Example |
|---|---|---|
| Rate, yield, coupon, fixing, repo, breakeven level | `*_pct`, 4.25 = 4.25% | `par_rate_pct` 3.8125 |
| Spread, basis, ASW, tail, strike offset | `*_bp` | `value_bp` −38.5 |
| Normal vol | `nvol_bp`, bp per year (daily = annual/√252) | 82.5 |
| Price | `*_px` per 100 face, decimal; STIR `price_px` = 100 − `rate_pct` | 99.8828125; 96.255 |
| Discount factor, probability | 0–1 | 0.6818; 0.32 |
| Share or haircut | `*_frac`, −1..1 (percent is reserved for rates) | 0.02 |
| Money | `*_ccy` in the row's `ccy` | −250 |
| FX | `*_fx` quote per base; `points_fxpts` ÷ `points_scale` (10,000, or 100 for JPY quote) | EURUSD 1.1045 |

| Stored measure | Sign |
|---|---|
| `swap_spreads` `spread_*` | swap − govt (US: negative when swaps are below Treasuries) |
| `swap_spreads` `asw_*` | govt − swap (EGB: positive = bond cheap to swaps) |
| `basis_swaps.spread_bp` | spread on `leg_a` vs `leg_b` flat. EURUSD xccy with `leg_a`=EUR-ESTR: negative = premium paid to borrow USD |
| `ccp_basis.basis_bp` | ccp_a − ccp_b, default LCH − CME |
| `repo_rates.specialness_bp` | GC − specific; positive = bond is special |
| `auctions.tail_bp` | stop − when-issued; positive = tailed |
| `dv01_ccy`, `qty`, `notional_ccy` | positive = long duration: long bond or futures, receive fixed |
| `pnl` | `total = mtm + carry + financing + cost`; cost ≤ 0, financing < 0 is a cost |

Derived curve measures follow the repo conventions: 2s10s = y10 − y2 and 2s5s10s = 2·y5 − y2 − y10, in bp.

### 3. Time, snaps and point-in-time
- `date` is the trading date in the instrument's own market session, not the UTC date. `snap` is one of `settle`,
  `close`, `eod_ny`, `eod_ldn`, `eod_tky`, `eod_syd`, `fix` or `intraday`. `ts_utc` is the exact instant.
- **PIT read rule.** A decision at instant T may use a row only if `date` ≤ T's date, `pub_ts_utc` ≤ T (where
  present), and the row's validity window contains T. For a same-day EOD row, T must also be after the snap. For a
  vintaged table, use the latest vintage at T. `read_asof(table, T, key=...)` enforces the snap condition only
  where `ts_utc` is filled, and blanks auction result columns until `results_ts_utc`. For a decision before the snap without `ts_utc`, pass the previous date (a bare date
  means the end of that day).
- Universe on date d: `issue_date ≤ d < maturity_date` (inclusive on the issue date, so new issues are not dropped on
  their first day). The futures basket on d is `eligible_from ≤ d`; a when-issued bond enters on its issue date.
- Fitted objects are stamped with their fit window and used only afterwards: seasonals carry `fit_end_date`, while
  hedge ratios and PCA loadings use data ≤ t − 1. Signals at t become positions at t + 1.
- Roll maps use only information available on that date (yesterday's open interest, not today's).
- Never let a `settle` fill a `close` gap or vice versa. They differ, usually by a fraction of a bp and by more on
  event days. House end-of-day snaps are local: one index methodology uses 16:00 London for most currencies, 16:00 CET
  for NOK, 16:15 CET for SEK, 15:00 New York, 15:00 Tokyo and 16:30 Sydney and Auckland (Deutsche Bank DBIQ, Interest
  Rate Curve Creation Process, Feb 2023). Cross-market spreads (UST–Bund, gilt–Bund) need one common instant, or the timing gap stated.
- A benchmark fixing is a methodology, not an instant. CME Term SOFR uses VWAPs over 14 half-hour intervals from
  07:00 to 14:00 Chicago, each clipped to a random bid/ask snapshot (Huggins & Schaller, SOFR Futures and Options,
  2022). Store such values as `snap=fix`.

| Data | Observation | Knowable at (`pub_ts_utc`) |
|---|---|---|
| SOFR for day d | `fixing_date` d | about 08:00 New York on the next business day (NY Fed) |
| €STR for day d | d | 08:00 CET on d+1 (ECB) |
| TONA for day d | d | provisional about 17:15 JST on d, final about 10:00 JST on d+1: two vintages (BoJ) |
| CFTC positioning | Tuesday | Friday 15:30 New York, later around holidays (BofA, Technicals Explained, Jan 2025) |
| SDR block trades | execution time | delayed dissemination, notional capped (Clarus, Compression in USD Swaps, Dec 2014) |
| CPI for month m | `ref_month` m | the release instant in m+1; revisions are later vintages |
| Fundamentals indexed by period end | period end | release date, "often by 1.5 months" later (López de Prado, AFML, 2018) |

### 4. Adapter interface
Two methods to implement; point-in-time comes for free. The template is in `scripts/adapter_template.py`.

```python
class DataSource(ABC):
    name: str
    def tables(self) -> set[str]: ...                       # canonical tables this source serves
    def read(self, table, start=None, end=None, where=None) -> pd.DataFrame: ...
        # canonical columns and units; date columns datetime64; *ts_utc tz-aware UTC;
        # raise FileNotFoundError/KeyError if unavailable, so the agent asks instead of guessing
    def read_asof(self, table, as_of, key=None, start=None, end=None, where=None) -> pd.DataFrame:
        return point_in_time(self.read(table, start, end, where), as_of, key)
```

`FileSource(root="data")` serves `data/<table>.parquet`, `data/<table>.csv` or a `data/<table>/` folder of parts.
Skills and their scripts read canonical files, so a pull adapter that implements `read` and an export job that
writes files are equivalent.

### 5. Mapping any source to the contract
1. **Inventory with the user.** Establish the instruments, fields, served units, snap time and zone, history depth,
   revision behaviour, and request limits.
2. **Choose tables and fill `symbol_map`.** For each source symbol record `canonical_id`, `target_table`,
   `target_column`, `unit_in` and `multiplier` (decimal → pct 100, decimal → bp 10,000, pct → bp 100).
3. **Convert at the edge.** 32nds text to decimal (`price_from_32nds`), decimal to pct or bp, yield-quoted futures to
   the `quote_type` rules, and xccy or basis quotes re-oriented so the spread sits on `leg_a`.
4. **Stamp time.** Assign `date` by the market session, plus `snap`, `ts_utc`, and `pub_ts_utc` for anything
   published with a lag or revised.
5. **Version static data.** Use `valid_from`/`valid_to`, and start a new row when a tap changes `amount_out_ccy`.
   Keep matured bonds and expired contracts, since dropping them is survivorship bias.
6. **Write.** One file or folder per table under `data/`, and keep `date` inside each file even when partitioning by
   date. Write per day atomically (temporary file, then rename). Append vintages; never consolidate a partial day.
   Cache static data locally rather than making one request per instrument.
7. **Validate** (section 6), then record what was adjusted in `dq_reason`.

| Source | Typical traps |
|---|---|
| CSV/Excel export | Excel serial dates, decimal commas, `#N/A` text, 32nds strings, different snaps per sheet, silent forward-fill |
| Database | restated history with no vintage columns; joins to static that ignore `valid_from`; local-time dates |
| Vendor SDK / terminal API | settle and close are different requests; codes collide across venues, so test mapped prices on the tick grid and a plausible band and return null rather than "decode"; holiday prints |
| Internal pricer / curve library | export inputs (quotes) and outputs (`curve_zero` nodes, interpolation, `build_id`) as data, never pickled objects; serving curves in decimal |

### 6. Validate
`python scripts/validate_data.py data/curve_par.csv data/bond_quotes.parquet --as-of 2026-11-11`. It checks required
columns, nulls in required columns (present but empty is rejected, never skipped), dtypes (naive timestamps are
rejected), unit ranges (pct in [−100, 100], bp in [−5000, 5000], px in [−100, 1000], prob in [0, 1]; tripwires, not
outlier filters), key uniqueness, no `date`, `ts_utc`, `pub_ts_utc`, `exec_ts_utc` or `results_ts_utc` later than the cutoff
(schedule columns such as `decision_ts_utc` are exempt), and the row identities in
[schemas](references/schemas.md):

- `stir_quotes`: `price_px + rate_pct = 100`
- `bond_quotes`: `dirty_px = clean_px + accrued_px` (negative ex-dividend accrued is legal)
- `ccp_basis`: `basis_bp = 100·(rate_a_pct − rate_b_pct)`
- `repo_rates`: `specialness_bp = 100·(gc_rate_pct − rate_pct)`
- `auctions`: `tail_bp = 100·(stop_yield_pct − wi_yield_pct)`
- `pnl`: components sum to `total_ccy`

Add these adapter conformance tests, each run against a case with a known answer:
1. Settles sit on the tick grid: |price/tick − round(price/tick)| < 1e-6.
2. Price-quoted bond futures fall in 50–300 and STIR prices in 80–110. For `yield_index` and `yield` contracts, test
   the implied yield instead.
3. `curve_zero` has DF = 1 at `date`, and a curve rebuilt from it reprices its own inputs to < 0.1bp.
4. No rows fall on `calendars` holidays unless the venue was open.
5. A term structure identical across all terms on > 90% of days is flagged (`data_ok=false`).
6. Truncation test: rerun the pipeline without the last 60 days. Outputs on the overlapping dates must be identical,
   or there is look-ahead (Chan, Quantitative Trading, 2009).

### 7. When data is missing
Never fill from memory or "typical levels". Check `FileSource("data").tables()`, then ask for exactly what is needed:

```text
To run <analysis> I need the canonical table `curve_par` (data-contract-and-adapters):
  curve_id USD-SOFR and EUR-ESTR, start 0D, tenors 2Y 5Y 10Y 30Y; daily; snap eod_ny (or tell me yours);
  2019-01-01 to today; par_rate_pct in percent (3.81 = 3.81%).
You can (a) drop a CSV/Parquet export in data/, (b) point me to a database table or view, or (c) name the API or
library you use, and I'll write adapters/<source>_adapter.py and validate it.
```

If only part of the data exists, run what it supports and label the output "partial: missing <table/columns>".

## Worked examples
1. **32nds to decimal** (BofA Global Research, U.S. Rates Data: Futures Basis Report, 7 Aug 2025). the Sep-2025 Ultra T-bond future at
   115-17 = 115 + 17/32 = 115.53125. CTD 4.75% Nov-43 at 99-282 = 99 + 28.25/32 = 99.8828125 (the third digit counts
   eighths of a 32nd). Model price 115-19+ = 115.609375. Rich/cheap +0-02+ = 2.5/32 = 0.078125 points, which is
   USD 78.13 per USD 100,000 contract. These are stored as decimals in `fut_quotes.price_px` and
   `bond_quotes.clean_px`, and `price_from_32nds` reproduces all four. The third character is eighths of a 32nd for cash
   bonds, but CME 2y/3y/5y note futures print 2, 5, 7 for 1/4, 1/2, 3/4 (`fut_quarters=True`), so 117-167 is
   117 + 16.75/32 there and 117 + 16.875/32 as a cash quote. Confirm against the tick grid.
2. **ASX bond futures quote 100 − yield** (ASX, Interest Rate Derivatives Price and Valuation Guide, Jul 2025). A
   price of 95.505 means a yield of 4.495%. The contract value is P = 1000·[c(1 − vⁿ)/i + 100vⁿ] with i = 4.495/200 =
   0.022475, v = 1/(1 + i), c = 3 and n = 6 (the 3y contract), giving A$104,180.10; n = 6 reproduces the published
   figure. The tick value therefore varies with the level: `quote_type=yield_index`, `tick_value_ccy` null,
   `settlement_type=cash`, and no basket.
3. **STIR price, rate and P&L.** The 3M SOFR future (SR3) at 96.255 means 3.745%. 1bp = USD 25 and a tick of 0.005 = USD 12.50 (CME SOFR
   futures specifications). A +0.05 move is 5bp × 25 = USD 125 per contract. SR1 settles on the arithmetic average
   (USD 41.67/bp); SO3 is GBP 25/bp, FEU3 EUR 25/bp (tick 0.0025 = EUR 6.25), and CRA CAD 25/bp. Montréal Exchange
   converted BAX into CRA with CDOR = CORRA + 32.138bp (so BAX price = CRA price − 0.32138), stored as
   `rate_indices.fallback_spread_bp`.
4. **Vol units** (RVFi help centre, Bond Futures: Future Global Preferences, Apr 2024). The screen shows an annual
   normal vol of 148.8bp and a daily vol of 9.4bp: 148.8/√252 = 9.37. Store the annual `nvol_bp` only.
5. **Release lag.** CFTC positions dated Tuesday 3-Nov-2026 carry `pub_ts_utc` 2026-11-06T20:30:00Z (Friday 15:30
   New York). A Tuesday-close signal that uses them looks 3 days ahead, and `read_asof` hides them until Friday.
6. **Vintage** (illustrative, the adapter selftest case). An HICP print for 2026-01 is first published as 100.0 on
   11 Feb and revised to 100.3 on 11 Mar 10:00Z. `read_asof` returns 100.0 at 09:59:59Z on 11 Mar and 100.3 on 20 Mar.
7. **Unit tripwire** (illustrative). A `stir_quotes` row with `price_px` 96.40 and `rate_pct` 0.0360 (decimal) fails
   `price_px + rate_pct = 100`. A basis archived as decimal (−0.0020 instead of −20bp) makes a book look flat against
   bp thresholds, and the bp-column W_DECIMAL warning catches it.

## G10 differences the contract must carry
| Market fact | Encoded as |
|---|---|
| ASX 3y/10y bond futures: 100 − yield, cash-settled against the basket's average yield, 6% coupon | `fut_static.quote_type=yield_index`, `settlement_type=cash` |
| Nasdaq SGB futures: quoted as yield (30E/360), 1% coupon, one designated deliverable | `quote_type=yield`, `fut_quotes.yield_pct`, `fut_basket.is_designated` |
| Notional coupons: 6% CBOT, Eurex Schatz/Bobl/Bund/BTP/OAT, MX, JGB; 4% Buxl and Long Gilt; 1% CONF and SGB | `fut_static.notional_coupon_pct` |
| Delivery: Eurex on the 10th calendar day; CBOT and ICE gilt any business day of the month; JGB on the 20th | `first_delivery_date`, `last_delivery_date` |
| AUD IRS: 3M BBSW quarterly to 3y, 6M BBSW semi-annual from 4y, T+1 | two `swap_conventions` rows (`from_tenor` 0D, 4Y) |
| Term IBOR still the IRS standard in AUD, NZD, SEK, NOK (and EUR Euribor); CDOR ceased 28-Jun-2024 | `swap_conventions.index_id`, `rate_indices.status` |
| Day counts: SOFR, €STR, SARON ACT/360; SONIA, TONA ACT/365F; CORRA 365 with no leap adjustment; NOWA ACT/365 vs NIBOR ACT/360 | `rate_indices.day_count` |
| Gilts ex-dividend 7 business days (negative accrued); ACGB ex-interest 7 calendar days | `bond_static.ex_div_rule`; `accrued_px` < 0 allowed |
| T+1 cash settlement: UST, gilts, JGB (since May 2018), Canada (since 27 May 2024) | `bond_static.settle_days` |
| Annual coupons: Bund, OAT, SGB, NGB, Confederation; semi-annual: UST, gilts, JGB, GoC, ACGB, NZGB | `bond_static.coupon_freq` |
| Meetings: SNB quarterly, RBNZ 7 a year (8 from 2027), most others 8; Norges Bank decision 23-Sep-2026 effective 25-Sep | `cb_meetings` rows, `effective_date` |
| Euribor futures named after the period start; SR3 references IMM to IMM | `fut_static.ref_start_date`, `ref_end_date` |
| US rate futures and US Treasury cash keep different holiday calendars | separate `calendar_id` |

Conventions themselves are owned by [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md). The schema
example rows are seeds to verify, not authority.

## Signals & interpretation
Reading the validator output:

| Finding | Usual cause | Action |
|---|---|---|
| `E_RANGE` on `*_pct` | bp or price stored as percent; multiplier applied twice | fix `symbol_map.multiplier`, re-export |
| `W_DECIMAL` | decimal served as pct or bp | confirm with the source; JPY/CHF levels near zero can be genuine |
| `E_DUP_KEY` | two snaps or sources merged; vintages without `pub_ts_utc` | split by snap; add `pub_ts_utc` |
| `E_FUTURE` | UTC date used as trading date; release time missing | fix date assignment; this is a look-ahead leak |
| `E_NULL_REQ` | required column present but empty | reject; a null gating column silently empties universes |
| `E_CHECK` | sign or unit mismatch between related columns | fix at the adapter |
| `E_DTYPE` | Excel serials, 32nds text, naive timestamps | convert at the adapter |
| `W_EXTRA_COL` | vendor fields leaking through | drop, or propose a contract change |

Verdict per requested analysis: **READY** (0 errors), **USABLE WITH CAVEATS** (warnings explained in the report),
**BLOCKED** (errors, or a required table missing).

## Pitfalls
- Option premium is not always paid up front: exchange-listed options on futures can be margined futures-style
  (`opt_static.premium_style`). Read it before treating `premium_px` as cash.
- Free float is not outstanding: take central-bank and stripped amounts from `bond_holdings` as known at the date, not
  from the latest release.
- Size units: a notional-per-bp (DV01) figure read as notional, or the reverse, is a 10,000× error. Keep `dv01_ccy`
  and `notional_ccy` apart, and charge fees on the traded increment, not the whole position.
- Unsigned DV01 or weights lose direction (every leg looks long). Keep them signed.
- Bonds marked at dirty price with coupons also booked as cash double-count the coupon. Use mtm on clean price plus
  carry for accrual and coupons.
- A strict `<` on `issue_date` drops new issues on their first day. Year fractions of days/365.25 instead of the
  instrument's day count can move a bond across a hard maturity cutoff (for example 3.0y).
- Generic series built with different roll rules are not comparable. Record `roll_rule`. Defaults differ by
  currency even inside one tool: USD and CAD roll on the first day of the delivery month, EUR, GBP and JPY on the
  last trade date (RVFi help centre, Future Global Preferences, Apr 2024).
- Whether prices sit on the quoting grid tells you if they are dealer or exchange quotes or matrix prices. Cost
  models need bid/ask or bucketed half-spreads, not one flat bp.
- Some sources print on market holidays (copies of the prior day). Filter against `calendars`.
- Public SDR notionals are capped for blocks, and compression packages carry little price information. Use
  `notional_capped` and `is_compression` before reading volume as flow (Clarus, Dec 2014).
- Fitted weights (PCA or regression flies) are in-sample unless fitted on a rolling window. Never store them as data
  against a date without the fit window.
- Indexing a value by its period end instead of its release date is a look-ahead error (López de Prado, 2018). So is
  using the final revised value at the first-release date, or a universe drawn from today's outstanding list.
- SDR tapes (CFTC Technical Specification, Parts 43 and 45, v3.1, Aug 2022): all-9s placeholders mean unknown, so filter
  them as null. Corrections and error cancels print with a reference to the original, so net them out via
  `action`/`orig_trade_uid`. Allocations, clearing legs and compression legs mostly do not print. Rates may arrive as
  decimals (0.0257 = 2.57%): convert at the adapter.

## Output
1. **Data readiness report**: `| table | rows | date range | snaps | sources | errors | warnings | gaps |` with the
   verdict per requested analysis and the exact missing tables and columns.
2. **Adapter**: `adapters/<source>_adapter.py` (subclass of `DataSource`; all vendor code stays there), its
   `symbol_map` rows, and canonical files in `data/` that pass the validator.
3. **Missing-data request** in the template above, when needed.
4. **Contract change** when a skill needs a new field: edit [schemas](references/schemas.md) (column, dtype, unit,
   req, description, example, Used by), then run `--lint` and `--selftest`. Existing column meanings never change in
   place; add a new column instead. Choose the smallest change: a column or enum value on an existing table, then a
   `macro_series` pattern for one number per period (term premia, indices, prices, bank ratios), and a new table only
   when the primary key differs. Table, column and unit names that skills use must match the schema file exactly.

## Scripts
- [`scripts/validate_data.py`](scripts/validate_data.py): validates CSV/Parquet files or folders against
  `references/schemas.md`. `--as-of` sets the cutoff, `--lint` checks the schema file, `--list` lists tables and keys.
  `--selftest` plants one violation per rule and asserts the exact finding.
- [`scripts/adapter_template.py`](scripts/adapter_template.py): `DataSource`, `FileSource`, `point_in_time`,
  `price_from_32nds`. Its CLI prints or exports a point-in-time read. `--selftest` checks 32nds quotes from the BofA
  report, a revised-CPI vintage, a tap-versioned bond, auction results hidden until release and a missing-table error.

## Related skills
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale data, outliers, holidays, roll stitching after the contract is met
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): authoritative conventions behind `rate_indices`, `swap_conventions`, `bond_static`, `fut_static`
- [fi-curve-construction](../fi-curve-construction/SKILL.md): builds `curve_zero` from `curve_par`, `stir_quotes` and `rate_fixings`
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): builds `roll_map` generics and roll rules
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): consumes `flows_trades` and its caps and exclusions
- [bt-backtest-design](../bt-backtest-design/SKILL.md): consumes `signals` → `positions` → `trades` → `pnl` under the PIT rules
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): leakage, labeling and sample weights on top of PIT data
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): runs the data check first and stops on BLOCKED
- [eng-python-analytics-stack](../eng-python-analytics-stack/SKILL.md): coding conventions for adapters and scripts
- [eng-skill-authoring](../eng-skill-authoring/SKILL.md): how a skill declares inputs against these tables

## References
- Marcos López de Prado - Advances in Financial Machine Learning (Wiley, 2018): point-in-time data, release lags and vintages (Ch.2); look-ahead and survivorship among the backtest sins (Ch.11)
- Ernest P. Chan - Quantitative Trading (Wiley, 2009): truncation test for look-ahead, >4σ bad-data screen, keeping point-in-time snapshots against survivorship
- Giuseppe A. Paleologo - The Elements of Quantitative Investing (Wiley, 2025): data-sourcing checklist (definition and units, provenance, point-in-time vs restated); never use data a production system could not have had
- Igor Tulchinsky et al. - Finding Alphas, Ch.14 "Data and Alpha Design" (Wiley, 2015): a timestamp and delivery time for every point; one bad point can kill a signal
- Doug Huggins & Christian Schaller - SOFR Futures and Options: A Practitioner's Guide (Wiley, 2022): CME Term SOFR input-price methodology, i.e. a fixing as a methodology rather than a snap
- BofA Global Research - U.S. Rates Data: Futures Basis Report (7 Aug 2025): basket and basis column set; 32nds quotes used in the worked example
- RVFi help centre - Bond Futures: Future Global Preferences (Apr 2024): price-source and per-currency roll settings, futures monitor columns, annual vs daily normal vol
- BofA Global Research - Technicals Explained primer, P. Ciana & S. Suttmeier (14 Jan 2025): CFTC Commitments of Traders timing and trader classes
- Clarus Financial Technology - Compression in USD Swaps, C. Barnes (8 Dec 2014): capped block notionals and compression trades in SDR data
- tpSEF Inc. - Rulebook Appendix B: Swap Specifications (effective 8 May 2021): FpML term mapping, ISDA taxonomy, day-count list, adjusted vs unadjusted dates, spot lags
- ISDA - 2021 ISDA Interest Rate Derivatives Definitions FRO Mapping Tables, Version 3 (10/11/2021): G10 floating-rate-option names behind `index_id`
- Deutsche Bank DBIQ - DBIQ Index Guide: Interest Rate Curve Creation Process (2 Feb 2023): local end-of-day snap times by centre; input instrument classes
- CFTC - Technical Specification: Parts 43 and 45 swap data reporting and public dissemination requirements, v3.1 (30 Aug 2022): what the public SDR tape shows and omits
- Alexander Düring - Fixed Income Trading and Risk Management (Wiley, 2021): monthly seasonal factors and seasonal index projection for linkers
- Conks (Monetary Mechanics) - Plumbing Notes: Takeoff Begins (6 Oct 2025): public funding datasets (rate percentiles, repo segments, Fed balance sheet) behind `rate_fixings` and `macro_series`
- J.P. Morgan - Welcome to the machine: NLP of central bank speak, J. Lupton et al. (26 Apr 2023): text-derived daily series with gaps vs trailing averages
- Federal Reserve Bank of New York - Secured Overnight Financing Rate data page (2026) (external): SOFR publication timing
- European Central Bank - Euro short-term rate (€STR) page (2026) (external): T+1 08:00 CET publication
- Bank of Japan - Uncollateralized overnight call rate statistics page (2026) (external): provisional and final TONA
- OpenGamma Strata - FixedOvernightSwapConventions and index reference (external): OIS conventions and index day counts
- CME Group - Calculating U.S. Treasury Futures Conversion Factors (2024) and SOFR futures contract specifications (external)
- ASX - Interest Rate Derivatives Price and Valuation Guide (Jul 2025) and 3 and 10 Year Treasury Bond Futures factsheet (2025) (external)
- Nasdaq - Government Bond Futures Product Sheet (Apr 2024) (external): yield-quoted SGB futures, single deliverable
- Eurex Euro-Bund and CONF futures pages; ICE Futures Europe Long Gilt and Three Month SONIA pages; Montréal Exchange CGB and CRA pages (2026) (external): contract terms in the `fut_static` seeds
- AFMA - Interest Rate Derivative Conventions (Nov 2023) (external): AUD swap frequency switch and T+1 start
- UK Debt Management Office - About gilts (2026) (external): ex-dividend period and negative accrued
