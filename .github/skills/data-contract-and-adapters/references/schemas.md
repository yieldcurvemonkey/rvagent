# Canonical data tables

This file is the single source of truth for every table the RV skills read. `scripts/validate_data.py` parses it.
Keep the layout when editing: each table is a `### \`name\`` heading, then a `Primary key:` line, an optional
`Checks:` line, a `Used by:` line, and a column table whose header is exactly
`| column | dtype | unit | req | description | example |`. Any other table under a heading, such as example rows,
is documentation only.

**Examples show format only. They are not market data.** Rows marked "from spec" restate a published contract or
convention term and must still be verified before use (see `fi-g10-market-conventions`).

## Vocabularies

**Dtypes** (CSV text form, then Parquet/pandas form)

| dtype | CSV | Parquet / pandas |
|---|---|---|
| `str` | text | string |
| `date` | `YYYY-MM-DD` | date32 / datetime64 (time ignored) |
| `ts` | ISO-8601 with zone, e.g. `2026-11-10T22:00:00Z` | timestamp[us, tz=UTC]. Naive timestamps are rejected |
| `float` | decimal point `.`; empty = null | float64 |
| `int` | integer; empty = null | int64 (nullable) |
| `bool` | `true` / `false` | bool |

Column-name rules: a `date` column is `date`, `*_date`, `valid_from`, `valid_to`, `eligible_from` or `eligible_to`. A
`ts` column ends in `ts_utc`. The columns `date`, `ts_utc`, `pub_ts_utc`, `exec_ts_utc` and `results_ts_utc` are
observation or knowledge times and may never be later than the as-of cutoff.

**Units.** The unit is in the column name. A generic value column (`value`, `qty`, `price`) is unit `-` and sits next
to an explicit unit column (`unit`, `qty_unit`, `price_unit`).

| unit | name ends in | meaning | validator range (reject outside) |
|---|---|---|---|
| `pct` | `_pct` | percent per annum: 4.25 = 4.25%. Rates, yields, coupons, fixings, breakevens, repo | [-100, 100] |
| `bp` | `_bp` | basis points: spreads, basis, ASW, tails, strike offsets. bp = pct × 100 | [-5000, 5000] |
| `nvol_bp` | `nvol_bp` | normal (Bachelier) vol, bp per year | [0, 2000] |
| `px` | `_px` | price per 100 face, or exchange index points (100 − rate), decimal. Never 32nds text | [-100, 1000] |
| `df` | `discount_factor` | discount factor | [1e-6, 2] |
| `prob` | `prob` | probability 0..1 | [0, 1] |
| `frac` | `_frac` | fraction or share, -1..1 (never percent) | [-1, 1] |
| `ccy` | `_ccy` | amount in the row's currency (`ccy` column) | none |
| `cnt` | `_cnt` | contracts or counts | none |
| `fx` | `_fx` | units of quote currency per 1 unit of base currency | (0, 1e6] |
| `fxpts` | `_fxpts` | forward points in pips (divide by `points_scale`) | none |
| `index` | `index_level` | price-index level (CPI, RPI, HICP) | (0, 1e6] |
| `days` | `_days` | days | [0, 1e5] |
| `years` | `_years` | years | [0, 100] |
| `ratio` | (any) | dimensionless: conversion factor, delta, weight, bid-to-cover | none |
| `-` | (any) | identifier, text, enum, date, or a generic value with a unit column | none |

The validator also warns when every value in a `pct` column is below 0.25 in absolute value (a decimal stored as
percent?) or every value in a `bp` column is below 0.05 (a decimal stored as bp?). JPY and CHF rates can trip the
first warning legitimately. Read it, do not auto-rescale.

**Snaps** (`snap` column): `settle` (exchange official settlement), `close` (venue close or last trade), `eod_ny`,
`eod_ldn`, `eod_tky`, `eod_syd` (house end-of-day snap in that city; exact instant in `ts_utc`), `fix` (official
benchmark fixing), `intraday`. Never mix snaps inside one series.

**Identifiers**

| id | grammar | example |
|---|---|---|
| bond | `BOND:<ISIN>` | `BOND:US91282CXX00` |
| future | `FUT:<exchange product code>:<YYYY-MM>` | `FUT:ZN:2026-12`, `FUT:SR3:2027-03`, `FUT:FGBL:2026-12` |
| listed option | `OPT:<root>:<expiry YYYY-MM-DD>:<C\|P>:<strike>` | `OPT:SR3:2027-03-12:C:96.5` |
| dated swap | `SWAP:<curve_id>:<effective YYYY-MM-DD>:<maturity YYYY-MM-DD>` | `SWAP:USD-SOFR:2026-11-12:2036-11-12` |
| curve / index | `<CCY>-<INDEX>[-<TERM>]`; government curves `<CCY>-GOVT-<issuer>` | `EUR-ESTR`, `EUR-EURIBOR-6M`, `EUR-GOVT-DE` |
| cross-collateral discount curve | `<CCY>-CSA-<COLL>`: cash flows in CCY, collateral posted in COLL; the prefix is the cash-flow currency | `EUR-CSA-USD` |
| generic | `FUT:<root>:<n>` (n-th nearby), `FUT:<root>:CM<n>`, `BOND:<issuer>:OTR<tenor>` | `FUT:ZN:1`, `BOND:US:OTR10Y` |

Tenors: `\d+[DWMY]` (`3M`, `10Y`), `ON`, `TN`, `SN`, `SPOT`. A forward start (`start`) is `0D` for spot-starting,
a tenor (`5Y` for 5y forward), or an ISO date (IMM or meeting-dated). A 5y5y swap is `start=5Y, tenor=5Y`.

## Common optional columns

### `_common`
Optional on every table. A table's own definition of a column overrides this one.

Primary key: `-`
Used by: all

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| ts_utc | ts | - | N | exact instant of the observation or snap | 2026-11-10T22:00:00Z |
| data_ok | bool | - | N | false = row failed an adapter or quality check. Keep the row, do not use it | true |
| dq_reason | str | - | N | why data_ok is false, or what the adapter adjusted | stale: unchanged 5 days |
| ingest_ts_utc | ts | - | N | when the adapter wrote the row | 2026-11-10T22:05:13Z |
| schema_version | int | - | N | contract version the row was written against | 1 |

## Reference and static tables

### `calendars`
Business-day calendars for settlement, fixing and exchange trading. One row per weekday exception (holiday or early
close). Weekends are non-business days implicitly. Keep exchange calendars separate from cash-market calendars: US
rate futures and US Treasury cash do not share holidays.

Primary key: `calendar_id, cal_date`
Used by: fi-g10-market-conventions, fi-curve-construction, stir-rfr-compounding-and-fixing-risk, data-quality-and-timeseries-hygiene, quant-seasonality-and-calendar-effects, bt-backtest-design, bond-supply-and-cashflow-trading, bt-transaction-costs-and-liquidity, eng-python-analytics-stack, flow-positioning-cftc-and-surveys, flow-sdr-and-dealer-positioning, macro-technical-analysis, rv-devils-advocate, rv-execution-and-trade-packaging, spread-tenor-and-index-basis, stir-bills-and-money-market-spreads, stir-central-bank-balance-sheet-and-reserves, stir-futures-rv, vol-gamma-vega-pnl

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| calendar_id | str | - | Y | FpML business-centre code where one exists (USNY, USGS, EUTA, GBLO, JPTO, CATO, AUSY, NZAU, NZWE, CHZU, SEST, NOOS) or an exchange calendar (CME_IR, EUREX, ICE_EU, JPX, MX, ASX, NASDAQ_STO) | GBLO |
| cal_date | date | - | Y | calendar date (may be in the future) | 2026-12-28 |
| is_business_day | bool | - | Y | false = holiday; true rows record an early close | false |
| close_time_local | str | - | N | early-close time, HH:MM local | 14:00 |
| holiday_name | str | - | N | label | Boxing Day (substitute) |
| source | str | - | Y | producing adapter or publisher | exchange_notice |

### `cb_meetings`
Central-bank policy meeting schedule. Outcomes are not stored here: decisions go to `rate_fixings` as a policy-rate
series, so a backtest reading the schedule cannot see the result early.

Primary key: `cb, meeting_date`
Used by: stir-policy-pricing-whats-priced-in, fi-curve-construction, stir-futures-rv, macro-central-bank-reaction-functions, macro-central-bank-nlp, macro-event-risk-and-prediction-markets, quant-seasonality-and-calendar-effects, bt-backtest-design, bt-transaction-costs-and-liquidity, curve-forward-grid-rv, curve-steepeners-flatteners, curve-term-structure-models, fi-g10-market-conventions, macro-geopolitical-risk, macro-regime-and-scenario-analysis, macro-technical-analysis, ml-financial-ml-methodology, ml-models-for-rates, quant-bayesian-methods, quant-cointegration, quant-regime-detection, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-cross-market-govies, spread-tenor-and-index-basis, stir-bills-and-money-market-spreads, stir-central-bank-balance-sheet-and-reserves, stir-options-implied-distributions, stir-repo-and-funding-plumbing, stir-rfr-compounding-and-fixing-risk, vol-rates-options-rv, vol-skew-and-tail-hedging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| cb | str | - | Y | FED, ECB, BOE, BOJ, BOC, RBA, RBNZ, SNB, RIKSBANK, NORGES | NORGES |
| ccy | str | - | Y | ISO-4217 | NOK |
| meeting_date | date | - | Y | decision day, local | 2026-09-23 |
| decision_ts_utc | ts | - | N | scheduled announcement instant (may be in the future; not a knowledge time) | 2026-09-23T08:00:00Z |
| effective_date | date | - | N | first day the new rate applies, when it differs from meeting_date | 2026-09-25 |
| scheduled | bool | - | Y | false = unscheduled or emergency action | true |
| has_projections | bool | - | N | MPR / SEP / MPS published with the decision | true |
| has_press_conf | bool | - | N | press conference held | true |
| valid_from | date | - | Y | date this schedule entry was published | 2025-11-01 |
| valid_to | date | - | N | date it was cancelled or moved (a moved meeting gets a new row) | |
| source | str | - | Y | | cb_website |

### `rate_indices`
Definitions of overnight, term, policy, repo and price indices.

Primary key: `index_id`
Used by: fi-g10-market-conventions, stir-rfr-compounding-and-fixing-risk, spread-tenor-and-index-basis, fi-curve-construction, infl-breakevens-and-linkers, curve-forward-grid-rv, data-quality-and-timeseries-hygiene, fi-risk-dv01-and-transforms, quant-systematic-rates-signals, stir-bills-and-money-market-spreads, stir-central-bank-balance-sheet-and-reserves, stir-repo-and-funding-plumbing

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| index_id | str | - | Y | `<CCY>-<NAME>[-<TERM>]` | EUR-ESTR |
| ccy | str | - | Y | ISO-4217 | EUR |
| family | str | - | Y | RFR, IBOR, POLICY, REPO or CPI | RFR |
| term | str | - | N | ON, 1M, 3M, 6M; null for CPI | ON |
| day_count | str | - | N | ACT/360, ACT/365F, ... | ACT/360 |
| fixing_calendar_id | str | - | N | FK `calendars` | EUTA |
| publication_lag_days | int | days | N | business days from the rate's date to publication | 1 |
| publication_time_local | str | - | N | `HH:MM Area/City` | 08:00 Europe/Berlin |
| status | str | - | Y | active or ceased | active |
| ceased_date | date | - | N | last publication | |
| fallback_index_id | str | - | N | successor index | |
| fallback_spread_bp | float | bp | N | fixed spread adjustment to the successor | |
| source | str | - | Y | | administrator |

Example rows (from spec):

| index_id | family | day_count | publication | note |
|---|---|---|---|---|
| USD-SOFR | RFR | ACT/360 | about 08:00 New York, next business day | NY Fed |
| EUR-ESTR | RFR | ACT/360 | 08:00 CET, next TARGET day | ECB |
| GBP-SONIA | RFR | ACT/365F | next London business day (verify) | BoE |
| JPY-TONA | RFR | ACT/365F | provisional about 17:15 JST same day, final about 10:00 JST next day | BoJ: two vintages |
| CAD-CORRA | RFR | ACT/365F (no leap-year adjustment) | 09:00-11:00 ET, next business day | BoC |
| CHF-SARON | RFR | ACT/360 | reference fixing at 18:00 Zurich | SIX |
| NOK-NOWA / NOK-NIBOR-6M | RFR / IBOR | ACT/365 / ACT/360 | | Norges Bank |
| CAD-CDOR-3M | IBOR | | ceased 28-Jun-2024 | MX converted BAX to CRA at a 32.138bp spread |

### `swap_conventions`
Conventions for every `curve_id` used in `curve_par`, `curve_zero`, `swap_spreads` and `basis_swaps`. Government
fitted or benchmark curves (`curve_type=govt_fit`) get a row too, with the bond market's coupon frequency and day
count. When a market switches convention by tenor, add one row per `from_tenor`. A cross-collateral curve
(`<CCY>-CSA-<COLL>`) gets a row with `curve_type=xccy` and the cash-flow currency's RFR as `index_id`.

Primary key: `curve_id, from_tenor`
Used by: fi-g10-market-conventions, fi-curve-construction, fi-risk-dv01-and-transforms, fi-carry-and-rolldown, spread-swap-spreads-and-asw, rv-execution-and-trade-packaging, curve-forward-grid-rv, eng-python-analytics-stack, fi-collateral-csa-and-xva, flow-sdr-and-dealer-positioning, fut-invoice-spreads, spread-tenor-and-index-basis, stir-rfr-compounding-and-fixing-risk, vol-gamma-vega-pnl

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| curve_id | str | - | Y | curve key | GBP-SONIA |
| from_tenor | str | - | Y | `0D`, or the tenor from which this row applies | 0D |
| ccy | str | - | Y | ISO-4217 | GBP |
| curve_type | str | - | Y | ois, ibor, govt_fit or xccy | ois |
| index_id | str | - | N | FK `rate_indices`; null for govt_fit | GBP-SONIA |
| fixed_freq | str | - | Y | 1Y, 6M, 3M, or `T` (single payment at maturity) | 1Y |
| fixed_day_count | str | - | Y | | ACT/365F |
| float_freq | str | - | N | | 1Y |
| float_day_count | str | - | N | | ACT/365F |
| spot_lag_days | int | days | Y | business days, trade to effective date | 0 |
| pay_lag_days | int | days | N | business days, period end to payment | 0 |
| calendar_id | str | - | Y | FK `calendars` | GBLO |
| bdc | str | - | N | business-day convention | MF |
| clearing_house | str | - | N | LCH, CME, EUREX, JSCC, ASX | LCH |
| source | str | - | Y | | conventions_seed |

Example rows (from spec; verify, and see `fi-g10-market-conventions`):

| curve_id | from_tenor | fixed | float | spot / pay lag |
|---|---|---|---|---|
| USD-SOFR | 0D | 1Y ACT/360 | 1Y ACT/360 | T+2 / 2 |
| EUR-ESTR | 0D | 1Y ACT/360 | 1Y ACT/360 | T+2 / 2 |
| GBP-SONIA | 0D | 1Y ACT/365F | 1Y ACT/365F | T+0 / 0 |
| JPY-TONA | 0D | 1Y ACT/365F | 1Y ACT/365F | T+2 / 2 |
| CHF-SARON | 0D | 1Y ACT/360 | 1Y ACT/360 | T+2 / 2 |
| CAD-CORRA | 0D | 6M ACT/365F | 6M ACT/365F | sources conflict (T+0 vs T+2) / 1 |
| AUD-BBSW | 0D | 3M ACT/365F | 3M BBSW ACT/365F | T+1 |
| AUD-BBSW | 4Y | 6M ACT/365F | 6M BBSW ACT/365F | T+1 (3y-4y negotiated) |
| NZD-BKBM-3M | 0D | 6M ACT/365F | 3M ACT/365F | T+2 |
| SEK-STIBOR-3M | 0D | 1Y 30/360 | 3M ACT/360 | T+2 |
| NOK-NIBOR-6M | 0D | 1Y 30/360 | 6M ACT/360 | T+2 |

### `bond_static`
Government bond reference data, nominal and inflation-linked. Point-in-time through `valid_from`/`valid_to`: a tap
or buyback that changes `amount_out_ccy` closes the old row and opens a new one. A bond is in the universe on date
`d` when `issue_date <= d < maturity_date` (inclusive on the issue date, so new issues are not dropped on their
first day). When-issued trading before `issue_date` is flagged in `bond_quotes.is_wi`.

Primary key: `instrument_id, valid_from`
Used by: bond-rich-cheap-fitted-curve, bond-supply-and-cashflow-trading, spread-swap-spreads-and-asw, spread-cross-market-govies, fut-bond-basis-and-implied-repo, infl-breakevens-and-linkers, fi-carry-and-rolldown, curve-butterflies, curve-steepeners-flatteners, eng-reporting-and-visualization, fi-balance-sheet-and-regulatory-costs, fi-g10-market-conventions, fi-risk-dv01-and-transforms, fut-calendar-roll, fut-ctd-switch-and-delivery-options, fut-invoice-spreads, macro-fiscal-supply-and-term-premium, quant-cointegration, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, spread-sovereign-cds-and-basis, stir-repo-and-funding-plumbing, vol-basis-vs-vol, vol-convexity-and-long-end, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| instrument_id | str | - | Y | `BOND:<ISIN>` | BOND:GB00BXXXXX00 |
| valid_from | date | - | Y | first date this version of the row is true | 2026-03-04 |
| valid_to | date | - | N | first date it is no longer true | |
| isin | str | - | N | | GB00BXXXXX00 |
| issuer | str | - | Y | ISO country code, or EU / supranational code | GB |
| ccy | str | - | Y | ISO-4217 | GBP |
| bond_type | str | - | Y | nominal, linker, frn, bill, strip | nominal |
| coupon_pct | float | pct | Y | annual coupon rate; 0 for bills | 4.25 |
| coupon_freq | int | - | Y | coupons per year; 0 for zero-coupon | 2 |
| day_count | str | - | Y | ACT/ACT ICMA, ACT/365F, ACT/365, 30E/360, 30/360 | ACT/ACT ICMA |
| issue_date | date | - | Y | first settlement of the line | 2026-03-04 |
| first_coupon_date | date | - | N | for short or long first coupons | 2026-07-31 |
| maturity_date | date | - | Y | | 2036-07-31 |
| settle_days | int | days | Y | regular settlement lag | 1 |
| calendar_id | str | - | Y | FK `calendars` | GBLO |
| ex_div_rule | str | - | N | e.g. `7BD` (gilts: 7 business days) or `7CD` (calendar days) | 7BD |
| yield_convention | str | - | N | how `bond_quotes.ytm_pct` is compounded: sa, annual, simple | sa |
| original_term_years | float | years | N | original maturity; drives futures eligibility and on-the-run grouping | 10 |
| amount_out_ccy | float | ccy | N | face outstanding from valid_from | 38000000000 |
| index_id | str | - | N | linkers: FK `rate_indices` (CPI) | GBP-RPI |
| index_lag_months | int | - | N | linkers: indexation lag | 3 |
| base_index_level | float | index | N | linkers: reference index at issue | 380.1 |
| has_deflation_floor | bool | - | N | linkers | false |
| is_green | bool | - | N | green twin of a conventional line | false |
| source | str | - | Y | | debt_office |

### `fut_static`
Bond and STIR futures contract terms, one row per listed contract month. `quote_type` tells consumers what
`fut_quotes.price_px` means: `price` (per 100), `rate_index` (100 − rate), `yield_index` (100 − yield, ASX bond
futures) or `yield` (yield quoted directly, Nasdaq SGB futures).

Primary key: `fut_id`
Used by: fut-bond-basis-and-implied-repo, fut-calendar-roll, fut-ctd-switch-and-delivery-options, fut-invoice-spreads, stir-futures-rv, stir-convexity-adjustment, bt-transaction-costs-and-liquidity, curve-steepeners-flatteners, data-quality-and-timeseries-hygiene, fi-balance-sheet-and-regulatory-costs, fi-carry-and-rolldown, fi-curve-construction, fi-g10-market-conventions, fi-risk-dv01-and-transforms, flow-positioning-cftc-and-surveys, macro-technical-analysis, quant-regression-and-hedge-ratios, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, spread-tenor-and-index-basis, stir-options-implied-distributions, stir-policy-pricing-whats-priced-in, stir-repo-and-funding-plumbing, stir-rfr-compounding-and-fixing-risk, vol-basis-vs-vol, vol-skew-and-tail-hedging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| fut_id | str | - | Y | `FUT:<root>:<YYYY-MM>` | FUT:ZN:2026-12 |
| root | str | - | Y | exchange product code | ZN |
| exchange | str | - | Y | CME, EUREX, ICE_EU, JPX, MX, ASX, NASDAQ_STO | CME |
| ccy | str | - | Y | ISO-4217 | USD |
| product | str | - | Y | bond_fut or stir_fut | bond_fut |
| contract_month | str | - | Y | `YYYY-MM` | 2026-12 |
| quote_type | str | - | Y | price, rate_index, yield_index, yield | price |
| settlement_type | str | - | Y | physical or cash | physical |
| contract_size_ccy | float | ccy | N | face or notional per contract | 100000 |
| notional_coupon_pct | float | pct | N | bond futures notional coupon | 6 |
| tick_size_px | float | px | Y | minimum price increment in quote units | 0.015625 |
| tick_value_ccy | float | ccy | N | value of one tick; null where it varies with the level (ASX bond, bank-bill futures) | 15.625 |
| bp_value_ccy | float | ccy | N | STIR: value of 1bp per contract | |
| first_trade_date | date | - | N | | 2025-09-22 |
| last_trade_date | date | - | Y | | 2026-12-21 |
| first_notice_date | date | - | N | physically delivered contracts | 2026-11-30 |
| first_delivery_date | date | - | N | | 2026-12-01 |
| last_delivery_date | date | - | N | | 2026-12-31 |
| ref_index_id | str | - | N | STIR: FK `rate_indices` | |
| ref_method | str | - | N | STIR: compound, average or ibor_fix | |
| ref_start_date | date | - | N | STIR: start of the reference period (IMM date for SR3) | |
| ref_end_date | date | - | N | STIR: end of the reference period, exclusive | |
| calendar_id | str | - | Y | FK `calendars` | CME_IR |
| source | str | - | Y | | exchange_spec |

Example rows (from spec):

| root (exchange) | quote_type / settlement | size | notional coupon | tick (value) |
|---|---|---|---|---|
| ZT (CME 2y) | price / physical | USD 200,000 | 6% | 1/256 = 0.00390625 (USD 7.8125) |
| ZF (CME 5y) | price / physical | USD 100,000 | 6% | 1/128 = 0.0078125 (USD 7.8125) |
| ZN (CME 10y) | price / physical | USD 100,000 | 6% | 1/64 = 0.015625 (USD 15.625) |
| ZB, UB (CME bond, ultra) | price / physical | USD 100,000 | 6% | 1/32 = 0.03125 (USD 31.25) |
| FGBL (Eurex Bund) | price / physical, delivery 10th calendar day | EUR 100,000 | 6% (Buxl 4%) | 0.01 (EUR 10) |
| R (ICE Long Gilt) | price / physical, any day of delivery month | GBP 100,000 | 4% | 0.01 (GBP 10) |
| CGB (MX 10y) | price / physical | CAD 100,000 | 6% | 0.01 (CAD 10) |
| CONF (Eurex) | price / physical | CHF 100,000 | 1% | 0.01 (CHF 10) |
| XT, YT (ASX 10y, 3y) | yield_index / cash vs basket average yield | AUD 100,000 | 6% | 0.005, value varies |
| SGB10Y (Nasdaq) | yield / one designated bond | SEK 1,000,000 | 1% | 0.001 |
| SR3 (CME) | rate_index / cash, compounded SOFR, IMM to IMM | USD 25 per bp | | 0.005 (USD 12.50); 0.0025 front |
| SR1 (CME) | rate_index / cash, arithmetic average SOFR over the month | USD 41.67 per bp | | |
| SO3 (ICE) | rate_index / cash, compounded SONIA | GBP 25 per bp | | 0.005; 0.0025 front |
| FEU3 (Eurex 3M Euribor) | rate_index / cash, Euribor fix; named after period start | EUR 25 per bp | | 0.0025 (EUR 6.25) |
| CRA (MX 3M CORRA) | rate_index / cash, compounded CORRA | CAD 25 per bp | | 0.005; 0.0025 front |
| FSR3 (Eurex 3M SARON) | rate_index / cash, compounded SARON | CHF 25 per bp | | 0.005 (CHF 12.50) |

### `fut_basket`
Deliverable baskets and conversion factors. The basket on date `d` is the rows with
`eligible_from <= d` and (`eligible_to` null or `d < eligible_to`). A when-issued bond enters on its issue date,
not on its auction announcement. Prefer the exchange-published conversion factor. CME defines it as the price of 1
unit of par at the notional coupon's yield, with remaining term rounded down to the quarter (ZN, TN, ZB, UB) or to
the whole month (ZT, Z3N, ZF).

Primary key: `fut_id, instrument_id`
Used by: fut-bond-basis-and-implied-repo, fut-ctd-switch-and-delivery-options, fut-invoice-spreads, vol-basis-vs-vol, bond-rich-cheap-fitted-curve, fi-balance-sheet-and-regulatory-costs, fi-carry-and-rolldown, fi-g10-market-conventions, fi-risk-dv01-and-transforms, flow-positioning-cftc-and-surveys, fut-calendar-roll, port-scenario-and-stress-testing, quant-cointegration, quant-regression-and-hedge-ratios, rv-devils-advocate, stir-repo-and-funding-plumbing, vol-skew-and-tail-hedging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| fut_id | str | - | Y | FK `fut_static` | FUT:ZN:2026-12 |
| instrument_id | str | - | Y | FK `bond_static` | BOND:US91282CXX00 |
| conversion_factor | float | ratio | N | null for cash-settled or single-deliverable contracts | 0.8123 |
| eligible_from | date | - | Y | first date the bond is deliverable into this contract | 2026-09-30 |
| eligible_to | date | - | N | first date it no longer is | |
| is_designated | bool | - | N | true for a single designated deliverable (Nasdaq SGB) | false |
| source | str | - | Y | | exchange_basket |

### `opt_static`
Listed options on bond and STIR futures. Swaption and cap/floor vols live in `vol_surface`.

Primary key: `opt_id`
Used by: vol-rates-options-rv, vol-skew-and-tail-hedging, vol-gamma-vega-pnl, curve-conditional-trades, stir-policy-pricing-whats-priced-in, data-quality-and-timeseries-hygiene, fut-invoice-spreads, stir-options-implied-distributions, vol-basis-vs-vol, vol-correlation-and-curve-options

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| opt_id | str | - | Y | `OPT:<root>:<expiry>:<C\|P>:<strike>` | OPT:SR3:2027-03-12:C:96.5 |
| underlying_id | str | - | Y | FK `fut_static` | FUT:SR3:2027-03 |
| option_root | str | - | N | exchange option code (quarterly, serial, weekly, midcurve) | SR3 |
| option_right | str | - | Y | C or P | C |
| strike_px | float | px | Y | strike in the underlying's quote units | 96.5 |
| expiry_date | date | - | Y | | 2027-03-12 |
| exercise_style | str | - | Y | AMER or EUR | AMER |
| premium_style | str | - | N | upfront (premium paid at trade) or futures_style (margined daily, no premium cash). Exchange defaults differ: check the exchange rulebook, do not infer from the venue name | upfront |
| is_midcurve | bool | - | N | expiry well before the underlying's reference period | false |
| point_value_ccy | float | ccy | N | value of 1.00 price point per contract | 2500 |
| source | str | - | Y | | exchange_spec |

### `symbol_map`
The adapter's mapping from source symbols to canonical ids, units and columns, stored as data so it can be tested.
Vendor codes collide across products, so check every mapped price against the contract's tick grid and a plausible
band before trusting the map.

Primary key: `source, vendor_symbol, valid_from`
Used by: data-quality-and-timeseries-hygiene

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| source | str | - | Y | adapter or vendor tag | file_export_a |
| vendor_symbol | str | - | Y | the source's own identifier, verbatim | ABC 10Y MID |
| canonical_id | str | - | Y | instrument_id, fut_id, opt_id, or `curve_id\|start\|tenor` | USD-SOFR\|0D\|10Y |
| target_table | str | - | Y | canonical table it feeds | curve_par |
| target_column | str | - | N | canonical column it fills | par_rate_pct |
| unit_in | str | - | N | unit served by the source: dec, pct, bp, 32nds, px, yield | dec |
| multiplier | float | ratio | N | canonical = served × multiplier (dec→pct 100, dec→bp 10000) | 100 |
| valid_from | date | - | Y | | 2020-01-01 |
| valid_to | date | - | N | | |

### `roll_map`
Generic-to-specific mapping per date. Specific instruments are the stored primitive. Generic and constant-maturity
series are views built through this table, and the roll rule must use only information available on that date.

Primary key: `generic_id, date`
Used by: fut-calendar-roll, data-quality-and-timeseries-hygiene, bt-backtest-design, bond-rich-cheap-fitted-curve, macro-technical-analysis, quant-seasonality-and-calendar-effects, quant-systematic-rates-signals, rv-devils-advocate

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| generic_id | str | - | Y | generic series id | FUT:ZN:1 |
| date | date | - | Y | trading date | 2026-11-10 |
| instrument_id | str | - | Y | specific instrument the generic points to on that date | FUT:ZN:2026-12 |
| roll_rule | str | - | Y | first_position_day, first_notice, last_trade, oi_max, volume_max, imm_cutoff, otr_auction, otr_issue | first_position_day |
| source | str | - | Y | | roll_builder |

### `csa_terms`
Credit-support (collateral) terms per netting set: what may be posted, thresholds, margin frequency and the rate paid
on cash collateral. These are inputs only. Exposure profiles, incremental IM and XVA numbers are model outputs and are
not stored here. A netting set with no CSA is a row with `csa_type=none`. The cross-collateral discount curves for a
row are `curve_zero` rows whose `curve_id` follows `<CCY>-CSA-<COLL>`.

Primary key: `netting_set_id, valid_from`
Used by: fi-collateral-csa-and-xva

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| netting_set_id | str | - | Y | internal id of the netting set; no counterparty names in shared data | NS-0042 |
| valid_from | date | - | Y | first date these terms apply | 2024-03-01 |
| valid_to | date | - | N | first date they no longer apply | |
| counterparty_id | str | - | N | counterparty key, FK `cds_quotes.entity` when a CDS curve exists | CP-17 |
| ccy | str | - | Y | currency of the threshold, MTA and independent amount | USD |
| csa_type | str | - | Y | none, bilateral, one_way_receives (only we receive collateral), one_way_posts | bilateral |
| eligible_collateral | str | - | N | semicolon list of cash currencies and bond classes | USD;EUR;UST |
| base_collateral | str | - | N | single cash currency for a one-currency CSA; null for a multi-currency CSA | USD |
| haircut_frac | float | frac | N | haircut on non-cash collateral | 0.02 |
| threshold_ccy | float | ccy | N | exposure the poster may carry uncollateralised | 0 |
| mta_ccy | float | ccy | N | minimum transfer amount | 500000 |
| independent_amount_ccy | float | ccy | N | independent amount or initial margin, signed: positive = we receive | 0 |
| margin_freq | str | - | N | D, W or M | D |
| mpor_days | int | days | N | margin period of risk | 10 |
| remuneration_index_id | str | - | N | FK `rate_indices`: the rate paid on cash collateral | USD-SOFR |
| remuneration_spread_bp | float | bp | N | spread to the remuneration index | 0 |
| has_switch_right | bool | - | N | poster may substitute the collateral currency | true |
| allows_rehypothecation | bool | - | N | collateral taker may reuse it | true |
| source | str | - | Y | | credit_support_annex |

## Market data tables

### `curve_par`
Par swap and OIS rates by curve, forward start and tenor. Constant-maturity government benchmark or fitted par
yields go here too, under a `<CCY>-GOVT-<issuer>` curve_id. Bond-level yields go to `bond_quotes`.

Primary key: `date, snap, curve_id, start, tenor`
Used by: fi-curve-construction, curve-butterflies, curve-steepeners-flatteners, curve-pca-factor-model, curve-forward-grid-rv, curve-term-structure-models, fi-carry-and-rolldown, spread-swap-spreads-and-asw, xccy-basis, rv-opportunity-scan, quant-zscore-and-signal-screening, quant-mean-reversion-ou, bond-rich-cheap-fitted-curve, bond-supply-and-cashflow-trading, bt-backtest-design, bt-performance-attribution, curve-conditional-trades, data-quality-and-timeseries-hygiene, eng-python-analytics-stack, eng-reporting-and-visualization, fi-balance-sheet-and-regulatory-costs, fi-risk-dv01-and-transforms, flow-mbs-convexity-hedging, flow-positioning-cftc-and-surveys, flow-sdr-and-dealer-positioning, flow-structural-alm-demand, fut-bond-basis-and-implied-repo, fut-invoice-spreads, infl-breakevens-and-linkers, macro-central-bank-nlp, macro-event-risk-and-prediction-markets, macro-fair-value-models, macro-fiscal-supply-and-term-premium, macro-geopolitical-risk, macro-inflation-and-energy-drivers, macro-regime-and-scenario-analysis, macro-technical-analysis, ml-financial-ml-methodology, ml-models-for-rates, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-bayesian-methods, quant-cointegration, quant-covariance-estimation, quant-lead-lag, quant-regime-detection, quant-regression-and-hedge-ratios, quant-seasonality-and-calendar-effects, quant-signal-combination-and-decay, quant-systematic-rates-signals, quant-time-series-econometrics, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-ccp-basis, spread-cross-market-govies, spread-sovereign-cds-and-basis, spread-tenor-and-index-basis, stir-bills-and-money-market-spreads, stir-futures-rv, stir-policy-pricing-whats-priced-in, stir-repo-and-funding-plumbing, vol-basis-vs-vol, vol-convexity-and-long-end, vol-correlation-and-curve-options, vol-gamma-vega-pnl, vol-rates-options-rv, vol-skew-and-tail-hedging, vol-structured-flows-and-vega-supply

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | trading date of the snap | 2026-11-10 |
| snap | str | - | Y | snap vocabulary | eod_ny |
| curve_id | str | - | Y | FK `swap_conventions` | USD-SOFR |
| start | str | - | Y | `0D` spot, forward-start tenor, or ISO date | 0D |
| tenor | str | - | Y | swap tenor | 10Y |
| par_rate_pct | float | pct | Y | mid par rate in the curve's own fixed-leg convention | 3.8125 |
| bid_rate_pct | float | pct | N | | 3.8100 |
| ask_rate_pct | float | pct | N | | 3.8150 |
| source | str | - | Y | | file_export_a |

### `curve_zero`
Built curve nodes: discount factors (primary) and zero rates (derived). Store enough to rebuild the curve exactly:
every node, the interpolation, and a `build_id` that identifies the conventions, the input instrument set and the
interpolation. Store data, never serialized pricer objects.

Primary key: `date, snap, curve_id, node_date`
Used by: fi-curve-construction, fi-risk-dv01-and-transforms, fi-carry-and-rolldown, curve-forward-grid-rv, curve-term-structure-models, spread-swap-spreads-and-asw, fi-collateral-csa-and-xva, bt-backtest-design, bt-performance-attribution, curve-steepeners-flatteners, eng-python-analytics-stack, flow-structural-alm-demand, fut-invoice-spreads, infl-breakevens-and-linkers, macro-central-bank-reaction-functions, macro-fiscal-supply-and-term-premium, macro-inflation-and-energy-drivers, macro-technical-analysis, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-bayesian-methods, quant-lead-lag, quant-mean-reversion-ou, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-tenor-and-index-basis, stir-futures-rv, stir-options-implied-distributions, stir-policy-pricing-whats-priced-in, stir-rfr-compounding-and-fixing-risk, vol-convexity-and-long-end, vol-gamma-vega-pnl, vol-skew-and-tail-hedging, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | curve as-of date; DF(date) = 1 | 2026-11-10 |
| snap | str | - | Y | | eod_ny |
| curve_id | str | - | Y | | USD-SOFR |
| node_date | date | - | Y | | 2036-11-12 |
| tenor | str | - | N | label for the node | 10Y |
| discount_factor | float | df | Y | | 0.6818 |
| zero_rate_pct | float | pct | N | continuously compounded, ACT/365F from `date`: z = -100·ln(DF)/τ | 3.83 |
| interpolation | str | - | N | log_linear_df, log_cubic_df, linear_zero, flat_fwd, step_meeting | log_linear_df |
| build_id | str | - | N | hash of conventions, input instruments and interpolation | 7f3a9c |
| collateral | str | - | N | cross-collateral curves (`<CCY>-CSA-<COLL>`): collateral currency, ISO-4217. Null = the curve's own RFR | USD |
| source | str | - | Y | | curve_builder |

### `rate_fixings`
Published fixings for RFR, IBOR, repo and policy-rate indices. `fixing_date` is the date the rate applies to, and
`pub_ts_utc` is when it became public. SOFR for Mon 9-Nov is published about 08:00 New York on the next business day, 10-Nov, so a signal
computed at the 9-Nov close cannot use it. Provisional and final prints (TONA) and republications are separate rows.
Policy decisions are rows here with `fixing_date` = effective date and `pub_ts_utc` = announcement.

Primary key: `index_id, fixing_date, pub_ts_utc`
Used by: stir-rfr-compounding-and-fixing-risk, stir-repo-and-funding-plumbing, stir-policy-pricing-whats-priced-in, stir-futures-rv, stir-bills-and-money-market-spreads, fi-curve-construction, macro-central-bank-reaction-functions, bt-performance-attribution, curve-term-structure-models, data-quality-and-timeseries-hygiene, eng-python-analytics-stack, eng-reporting-and-visualization, fi-balance-sheet-and-regulatory-costs, fi-carry-and-rolldown, fi-g10-market-conventions, flow-sdr-and-dealer-positioning, fut-bond-basis-and-implied-repo, macro-central-bank-nlp, macro-fair-value-models, macro-regime-and-scenario-analysis, quant-seasonality-and-calendar-effects, quant-systematic-rates-signals, rv-research-digest, rv-trade-idea-writeup, spread-cross-market-govies, spread-tenor-and-index-basis, stir-central-bank-balance-sheet-and-reserves, stir-options-implied-distributions, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| index_id | str | - | Y | FK `rate_indices` | USD-SOFR |
| fixing_date | date | - | Y | date the rate applies to | 2026-11-09 |
| rate_pct | float | pct | Y | | 3.92 |
| pub_ts_utc | ts | - | Y | publication instant of this vintage | 2026-11-10T13:00:00Z |
| is_final | bool | - | N | false = provisional print | true |
| volume_ccy | float | ccy | N | underlying volume in the index currency | 2.9e12 |
| p1_pct | float | pct | N | published 1st percentile | 3.85 |
| p25_pct | float | pct | N | 25th percentile | 3.90 |
| p75_pct | float | pct | N | 75th percentile | 3.95 |
| p99_pct | float | pct | N | 99th percentile | 4.05 |
| source | str | - | Y | | administrator |

### `bond_quotes`
Bond prices and yields, one row per bond per snap. Coupons are never folded into the price series: clean price,
accrued and dirty price are separate, and coupon cash comes from the schedule in `bond_static`. Inside a gilt
ex-dividend period `accrued_px` is negative.

Primary key: `date, snap, instrument_id`
Checks: `abs(dirty_px - clean_px - accrued_px) < 1e-4`
Used by: bond-rich-cheap-fitted-curve, spread-cross-market-govies, spread-swap-spreads-and-asw, fut-bond-basis-and-implied-repo, infl-breakevens-and-linkers, bond-supply-and-cashflow-trading, stir-bills-and-money-market-spreads, spread-sovereign-cds-and-basis, bt-backtest-design, bt-performance-attribution, bt-transaction-costs-and-liquidity, curve-butterflies, curve-steepeners-flatteners, data-quality-and-timeseries-hygiene, eng-reporting-and-visualization, fi-balance-sheet-and-regulatory-costs, fi-carry-and-rolldown, fi-risk-dv01-and-transforms, fut-calendar-roll, fut-ctd-switch-and-delivery-options, fut-invoice-spreads, macro-event-risk-and-prediction-markets, macro-fair-value-models, macro-fiscal-supply-and-term-premium, macro-geopolitical-risk, macro-inflation-and-energy-drivers, ml-financial-ml-methodology, ml-models-for-rates, quant-bayesian-methods, quant-cointegration, quant-lead-lag, quant-mean-reversion-ou, quant-regime-detection, quant-regression-and-hedge-ratios, quant-signal-combination-and-decay, quant-time-series-econometrics, quant-zscore-and-signal-screening, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, stir-repo-and-funding-plumbing, vol-basis-vs-vol, vol-convexity-and-long-end, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | trading date | 2026-11-10 |
| snap | str | - | Y | | eod_ldn |
| instrument_id | str | - | Y | FK `bond_static` | BOND:GB00BXXXXX00 |
| clean_px | float | px | Y | mid clean price per 100, decimal | 98.4375 |
| accrued_px | float | px | N | accrued per 100 at `settle_date`; negative ex-dividend | -0.0817 |
| dirty_px | float | px | N | clean + accrued | 98.3558 |
| ytm_pct | float | pct | N | yield in the bond's `yield_convention`; real yield for linkers | 4.4512 |
| bid_px | float | px | N | | 98.42 |
| ask_px | float | px | N | | 98.455 |
| bid_ytm_pct | float | pct | N | | 4.4533 |
| ask_ytm_pct | float | pct | N | | 4.4491 |
| settle_date | date | - | N | settlement date the price and accrued refer to | 2026-11-11 |
| is_wi | bool | - | N | when-issued (before issue_date) | false |
| source | str | - | Y | | file_export_a |

### `bond_holdings`
Face amount of a bond held by a holder class or carved out of the line, with the release time. Free float of a line is
`amount_out_ccy` (from `bond_static` at the date) minus the `central_bank` and `stripped` holdings known at that
instant. Holdings change weekly or monthly and are published late, so they are vintaged here and not folded into
`bond_static` versions.

Primary key: `date, instrument_id, holder, pub_ts_utc`
Used by: bond-rich-cheap-fitted-curve, bond-supply-and-cashflow-trading

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | date the holding is measured at | 2026-11-04 |
| instrument_id | str | - | Y | FK `bond_static` | BOND:US91282CXX00 |
| holder | str | - | Y | central_bank, stripped, official_other, bank, other | central_bank |
| holding_ccy | float | ccy | Y | face held; for `stripped`, face held in stripped form | 4200000000 |
| pub_ts_utc | ts | - | Y | release instant of this figure | 2026-11-05T21:30:00Z |
| source | str | - | Y | | central_bank_statistics |

### `repo_rates`
GC and specific (special) repo by collateral and term. `specialness_bp = (gc_rate_pct - rate_pct) × 100`, positive
when the bond is special. A source whose term structure is identical across all terms on most days is probably
not observing terms. Store it, but set `data_ok=false` with a reason.

Primary key: `date, snap, ccy, collateral, term`
Checks: `abs(specialness_bp - 100*(gc_rate_pct - rate_pct)) < 1e-6`
Used by: stir-repo-and-funding-plumbing, fut-bond-basis-and-implied-repo, fi-carry-and-rolldown, fi-balance-sheet-and-regulatory-costs, spread-swap-spreads-and-asw, bond-rich-cheap-fitted-curve, bond-supply-and-cashflow-trading, bt-backtest-design, bt-performance-attribution, bt-transaction-costs-and-liquidity, eng-reporting-and-visualization, fi-collateral-csa-and-xva, flow-mbs-convexity-hedging, fut-calendar-roll, fut-ctd-switch-and-delivery-options, fut-invoice-spreads, infl-breakevens-and-linkers, ml-financial-ml-methodology, ml-models-for-rates, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-seasonality-and-calendar-effects, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-ccp-basis, spread-sovereign-cds-and-basis, spread-tenor-and-index-basis, stir-bills-and-money-market-spreads, stir-central-bank-balance-sheet-and-reserves, vol-basis-vs-vol, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ny |
| ccy | str | - | Y | | USD |
| collateral | str | - | Y | GC basket (`GC_US`, `GC_DE`, `GC_IT`, ...) or a bond instrument_id | BOND:US91282CXX00 |
| term | str | - | Y | ON, TN, SN, 1W, 2W, 1M, 3M, or ISO end date (term to a delivery date) | ON |
| rate_pct | float | pct | Y | repo rate | 3.70 |
| gc_rate_pct | float | pct | N | matching GC rate, same snap and term | 3.93 |
| specialness_bp | float | bp | N | (GC − rate) × 100 | 23 |
| segment | str | - | N | triparty, dvp, gcf, sponsored, bilateral | dvp |
| haircut_frac | float | frac | N | 0.02 = 2% | 0.02 |
| source | str | - | Y | | file_export_a |

### `cds_quotes`
Credit default swap quotes on sovereign, supranational and counterparty reference entities. The contract terms are in
the key so that several contracts on one entity and tenor (USD and local-currency denomination, physical and cash
settlement, 2003 and 2014 definitions) can coexist; a consumer must pick one. Spreads above 5000bp exceed the bp
tripwire. Distressed names trade on upfront with a fixed 100 or 500bp running coupon, so store `upfront_px` and leave
`par_spread_bp` null. Counterparty default probability and LGD are derived from these quotes and `recovery_frac`.

Primary key: `date, snap, entity, tenor, ccy, settlement, definitions`
Used by: spread-sovereign-cds-and-basis, fi-collateral-csa-and-xva

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | trading date of the snap | 2026-11-10 |
| snap | str | - | Y | | close |
| entity | str | - | Y | reference entity: ISO country code, supranational code or counterparty id | IT |
| tenor | str | - | Y | 6M, 1Y, 3Y, 5Y, 7Y, 10Y, 30Y | 5Y |
| ccy | str | - | Y | contract denomination, ISO-4217 | USD |
| settlement | str | - | Y | physical or cash | physical |
| definitions | str | - | Y | ISDA definitions vintage | 2014 |
| restructuring | str | - | N | restructuring clause: CR, MR, MM, XR | XR |
| coupon_bp | float | bp | Y | fixed running coupon of the contract | 100 |
| par_spread_bp | float | bp | N | mid par spread; null when only an upfront is quoted | 62.5 |
| bid_spread_bp | float | bp | N | | 60.5 |
| ask_spread_bp | float | bp | N | | 64.5 |
| upfront_px | float | px | N | points upfront per 100 on the fixed coupon; positive = protection buyer pays | 0.35 |
| recovery_frac | float | frac | N | recovery used to quote the contract | 0.40 |
| source | str | - | Y | | file_export_a |

### `fut_quotes`
Bond futures prices. `price_px` is in the contract's `quote_type` units: price per 100 for `price`, or
100 − yield for `yield_index` (ASX). Yield-quoted contracts (Nasdaq SGB) fill `yield_pct` and leave `price_px` null.

Primary key: `date, snap, fut_id`
Used by: fut-bond-basis-and-implied-repo, fut-calendar-roll, fut-ctd-switch-and-delivery-options, fut-invoice-spreads, vol-basis-vs-vol, flow-positioning-cftc-and-surveys, bt-backtest-design, bt-performance-attribution, bt-transaction-costs-and-liquidity, curve-steepeners-flatteners, data-quality-and-timeseries-hygiene, eng-reporting-and-visualization, fi-balance-sheet-and-regulatory-costs, fi-carry-and-rolldown, fi-risk-dv01-and-transforms, macro-event-risk-and-prediction-markets, macro-technical-analysis, ml-financial-ml-methodology, ml-models-for-rates, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-cointegration, quant-covariance-estimation, quant-lead-lag, quant-mean-reversion-ou, quant-regression-and-hedge-ratios, quant-seasonality-and-calendar-effects, quant-systematic-rates-signals, quant-time-series-econometrics, quant-zscore-and-signal-screening, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-ccp-basis, stir-repo-and-funding-plumbing, vol-gamma-vega-pnl, vol-rates-options-rv, vol-skew-and-tail-hedging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | settle or close: never mixed | settle |
| fut_id | str | - | Y | FK `fut_static` | FUT:ZN:2026-12 |
| price_px | float | px | N | decimal, never 32nds text | 112.796875 |
| yield_pct | float | pct | N | yield-quoted contracts, or 100 − price_px for yield_index | |
| bid_px | float | px | N | | |
| ask_px | float | px | N | | |
| volume_cnt | float | cnt | N | | 1450000 |
| oi_cnt | float | cnt | N | open interest | 4900000 |
| source | str | - | Y | | exchange_settle |

### `stir_quotes`
STIR futures prices (SOFR, €STR, SONIA, Euribor, CORRA, SARON, TONA, BBSW and BKBM bank bills, STIBOR, NOWA,
NIBOR). Price = 100 − rate for every contract.

Primary key: `date, snap, fut_id`
Checks: `abs(price_px + rate_pct - 100) < 1e-6`
Used by: stir-futures-rv, stir-policy-pricing-whats-priced-in, stir-convexity-adjustment, fut-calendar-roll, fi-curve-construction, bt-performance-attribution, bt-transaction-costs-and-liquidity, curve-butterflies, curve-forward-grid-rv, curve-steepeners-flatteners, data-quality-and-timeseries-hygiene, eng-reporting-and-visualization, fi-carry-and-rolldown, fi-risk-dv01-and-transforms, flow-positioning-cftc-and-surveys, macro-central-bank-reaction-functions, macro-event-risk-and-prediction-markets, macro-geopolitical-risk, macro-technical-analysis, port-position-sizing-and-risk-budget, quant-cointegration, quant-covariance-estimation, quant-lead-lag, quant-mean-reversion-ou, quant-regression-and-hedge-ratios, quant-seasonality-and-calendar-effects, quant-signal-combination-and-decay, quant-time-series-econometrics, quant-zscore-and-signal-screening, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, spread-ccp-basis, spread-tenor-and-index-basis, stir-bills-and-money-market-spreads, stir-options-implied-distributions, stir-repo-and-funding-plumbing, stir-rfr-compounding-and-fixing-risk, vol-gamma-vega-pnl

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | settle |
| fut_id | str | - | Y | FK `fut_static` | FUT:SR3:2027-03 |
| price_px | float | px | Y | | 96.255 |
| rate_pct | float | pct | N | 100 − price_px | 3.745 |
| bid_px | float | px | N | | 96.25 |
| ask_px | float | px | N | | 96.26 |
| volume_cnt | float | cnt | N | | 310000 |
| oi_cnt | float | cnt | N | | 1250000 |
| source | str | - | Y | | exchange_settle |

### `opt_quotes`
Listed option quotes on bond and STIR futures. For STIR options, normal vol of the rate in bp equals the normal vol
of the futures price in points × 100.

Primary key: `date, snap, opt_id`
Used by: vol-rates-options-rv, vol-skew-and-tail-hedging, vol-gamma-vega-pnl, vol-basis-vs-vol, stir-policy-pricing-whats-priced-in, bt-performance-attribution, bt-transaction-costs-and-liquidity, curve-conditional-trades, data-quality-and-timeseries-hygiene, eng-python-analytics-stack, eng-reporting-and-visualization, flow-positioning-cftc-and-surveys, fut-bond-basis-and-implied-repo, fut-ctd-switch-and-delivery-options, fut-invoice-spreads, macro-event-risk-and-prediction-markets, macro-technical-analysis, quant-time-series-econometrics, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, stir-futures-rv, stir-options-implied-distributions, vol-correlation-and-curve-options

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | settle |
| opt_id | str | - | Y | FK `opt_static` | OPT:SR3:2027-03-12:C:96.5 |
| premium_px | float | px | N | premium in underlying price points | 0.0841 |
| bid_px | float | px | N | | 0.0825 |
| ask_px | float | px | N | | 0.085 |
| underlying_px | float | px | N | underlying futures price at the same snap | 96.255 |
| nvol_bp | float | nvol_bp | N | normal vol of the underlying rate or yield, bp per year | 78.4 |
| delta | float | ratio | N | | 0.29 |
| volume_cnt | float | cnt | N | | 12000 |
| oi_cnt | float | cnt | N | | 210000 |
| source | str | - | Y | | exchange_settle |

### `vol_surface`
Swaption, cap/floor, midcurve, constant-maturity listed-option and CMS spread-option normal vols on an expiry × tenor
× strike grid. Strikes are offsets from the ATM forward. If the source gives absolute strikes, store `strike_pct` and
`atm_fwd_pct` and compute the offset, so consumers can re-strike without a curve. For `product=cms_spread` the
`tenor` is `<short>-<long>` (`2Y-10Y`), `atm_fwd_pct` is the convexity-adjusted forward of long minus short CMS rate in
percent, `strike_offset_bp` is from that forward and `nvol_bp` is the normal vol of the spread. FX and equity
implied vols are not rates vols: store them as `macro_series` rows (`unit=pct`).

Primary key: `date, snap, index_id, product, expiry, fwd_start, tenor, strike_offset_bp`
Used by: vol-rates-options-rv, vol-skew-and-tail-hedging, vol-gamma-vega-pnl, vol-convexity-and-long-end, curve-conditional-trades, stir-convexity-adjustment, fi-carry-and-rolldown, bt-performance-attribution, bt-transaction-costs-and-liquidity, curve-butterflies, curve-forward-grid-rv, curve-pca-factor-model, curve-steepeners-flatteners, curve-term-structure-models, data-quality-and-timeseries-hygiene, eng-python-analytics-stack, eng-reporting-and-visualization, flow-mbs-convexity-hedging, flow-positioning-cftc-and-surveys, flow-structural-alm-demand, fut-invoice-spreads, macro-event-risk-and-prediction-markets, macro-fair-value-models, macro-geopolitical-risk, macro-regime-and-scenario-analysis, macro-technical-analysis, ml-financial-ml-methodology, ml-models-for-rates, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-covariance-estimation, quant-mean-reversion-ou, quant-regime-detection, quant-regression-and-hedge-ratios, quant-signal-combination-and-decay, quant-time-series-econometrics, quant-zscore-and-signal-screening, rv-devils-advocate, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, stir-options-implied-distributions, stir-policy-pricing-whats-priced-in, vol-basis-vs-vol, vol-correlation-and-curve-options, vol-structured-flows-and-vega-supply

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ldn |
| ccy | str | - | Y | | EUR |
| index_id | str | - | Y | underlying index | EUR-ESTR |
| product | str | - | Y | swaption, capfloor, midcurve, stir_cm, bond_fut_cm, cms_spread | swaption |
| expiry | str | - | Y | option expiry tenor | 1Y |
| fwd_start | str | - | Y | `0D`; midcurves: gap from expiry to swap start | 0D |
| tenor | str | - | Y | underlying swap tail, or cap maturity; `<short>-<long>` for cms_spread | 10Y |
| strike_offset_bp | float | bp | Y | strike − ATM forward; 0 = ATMF | 0 |
| atm_fwd_pct | float | pct | N | ATM forward at the snap | 2.71 |
| strike_pct | float | pct | N | absolute strike | 2.71 |
| nvol_bp | float | nvol_bp | Y | normal vol, bp per year | 82.5 |
| lnvol_pct | float | pct | N | lognormal vol, or shifted-lognormal with `shift_pct`, if served. Unshifted vols above 100% (low-rate JPY, CHF, EUR) fail the pct tripwire: store them shifted or leave null | 22.2 |
| shift_pct | float | pct | N | shift of a shifted-lognormal quote | 1.0 |
| settlement | str | - | N | physical, cash_par, cash_collat | physical |
| source | str | - | Y | | file_export_a |

### `swap_spreads`
Swap spreads, asset-swap spreads and invoice spreads. The sign convention travels with every row. Defaults: the
`spread_*` measures are stored `swap_minus_govt` (US convention, negative when swaps are below Treasuries). The
`asw_*` measures are stored `govt_minus_swap` (EGB convention: positive = bond cheap to swaps).

Primary key: `date, snap, curve_id, measure, ref`
Used by: spread-swap-spreads-and-asw, fut-invoice-spreads, spread-sovereign-cds-and-basis, fi-balance-sheet-and-regulatory-costs, bond-rich-cheap-fitted-curve, bond-supply-and-cashflow-trading, curve-pca-factor-model, data-quality-and-timeseries-hygiene, eng-reporting-and-visualization, flow-mbs-convexity-hedging, flow-structural-alm-demand, infl-breakevens-and-linkers, macro-fair-value-models, macro-fiscal-supply-and-term-premium, macro-geopolitical-risk, macro-technical-analysis, ml-financial-ml-methodology, ml-models-for-rates, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-bayesian-methods, quant-cointegration, quant-covariance-estimation, quant-lead-lag, quant-mean-reversion-ou, quant-regression-and-hedge-ratios, quant-seasonality-and-calendar-effects, quant-signal-combination-and-decay, quant-time-series-econometrics, quant-zscore-and-signal-screening, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-cross-market-govies, stir-repo-and-funding-plumbing, vol-basis-vs-vol, vol-rates-options-rv, vol-structured-flows-and-vega-supply, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ny |
| ccy | str | - | Y | | USD |
| curve_id | str | - | Y | swap curve, FK `swap_conventions` | USD-SOFR |
| measure | str | - | Y | spread_mm (swap at bond maturity − bond yield), spread_otr (generic swap − on-the-run yield), asw_parpar, asw_proceeds, asw_yy, zspread, invoice | spread_otr |
| ref | str | - | Y | tenor, instrument_id or fut_id the spread refers to | 10Y |
| value_bp | float | bp | Y | | -38.5 |
| sign_convention | str | - | Y | swap_minus_govt or govt_minus_swap | swap_minus_govt |
| source | str | - | Y | | derived |

### `basis_swaps`
Single-currency tenor and index basis, and cross-currency basis. The spread is always on `leg_a` against `leg_b`
flat. If the market quotes it on the other leg, swap the legs and flip the sign in the adapter.

Primary key: `date, snap, basis_type, leg_a, leg_b, start, tenor`
Used by: spread-tenor-and-index-basis, xccy-basis, fi-curve-construction, fi-collateral-csa-and-xva, curve-pca-factor-model, fi-balance-sheet-and-regulatory-costs, flow-structural-alm-demand, macro-fair-value-models, macro-geopolitical-risk, ml-financial-ml-methodology, ml-models-for-rates, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-cointegration, quant-lead-lag, quant-regression-and-hedge-ratios, quant-zscore-and-signal-screening, rv-research-digest, rv-trade-idea-writeup, spread-cross-market-govies, spread-sovereign-cds-and-basis, stir-central-bank-balance-sheet-and-reserves, vol-structured-flows-and-vega-supply

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ldn |
| basis_type | str | - | Y | tenor, index or xccy | xccy |
| ccy | str | - | Y | currency, or pair for xccy | EURUSD |
| leg_a | str | - | Y | index_id of the leg that carries the spread | EUR-ESTR |
| leg_b | str | - | Y | index_id of the flat leg | USD-SOFR |
| start | str | - | Y | | 0D |
| tenor | str | - | Y | | 5Y |
| spread_bp | float | bp | Y | spread added to leg_a for par | -12.0 |
| collateral | str | - | N | xccy: collateral currency (ISO-4217) | USD |
| mtm_reset | bool | - | N | xccy: mark-to-market resetting notional | true |
| source | str | - | Y | | file_export_a |

### `ccp_basis`
Clearing-house basis: the same swap cleared at two CCPs. Default orientation LCH minus CME.

Primary key: `date, snap, index_id, tenor, ccp_a, ccp_b`
Checks: `abs(basis_bp - 100*(rate_a_pct - rate_b_pct)) < 1e-6`
Used by: spread-ccp-basis, fi-collateral-csa-and-xva, fi-curve-construction, flow-positioning-cftc-and-surveys, flow-sdr-and-dealer-positioning, flow-structural-alm-demand, port-scenario-and-stress-testing, quant-cointegration, quant-zscore-and-signal-screening, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ny |
| ccy | str | - | Y | | USD |
| index_id | str | - | Y | | USD-SOFR |
| tenor | str | - | Y | | 10Y |
| ccp_a | str | - | Y | | LCH |
| ccp_b | str | - | Y | | CME |
| rate_a_pct | float | pct | N | par rate cleared at ccp_a | 3.8150 |
| rate_b_pct | float | pct | N | par rate cleared at ccp_b | 3.8100 |
| basis_bp | float | bp | Y | (rate_a − rate_b) × 100 | 0.5 |
| source | str | - | Y | | file_export_a |

### `fx_rates`
FX spot and forwards for cross-currency and FX-hedged analysis. `pair` is base then quote: `EURUSD` = USD per EUR.
For tenors after spot, outright = spot + points / points_scale. ON and TN settle before spot.

Primary key: `date, snap, pair, tenor`
Used by: xccy-basis, spread-cross-market-govies, bt-performance-attribution, port-portfolio-construction, fi-collateral-csa-and-xva, fi-risk-dv01-and-transforms, macro-central-bank-nlp, macro-fair-value-models, macro-geopolitical-risk, macro-regime-and-scenario-analysis, quant-cointegration, quant-lead-lag, rv-research-digest, spread-sovereign-cds-and-basis, vol-correlation-and-curve-options, vol-structured-flows-and-vega-supply

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ldn |
| pair | str | - | Y | BASEQUOTE ISO codes | EURUSD |
| tenor | str | - | Y | SPOT, ON, TN, SN, 1W, 1M, 3M, 6M, 1Y, ... | 3M |
| value_date | date | - | N | settlement date of the tenor | 2027-02-12 |
| outright_fx | float | fx | Y | | 1.1045 |
| points_fxpts | float | fxpts | N | forward points in pips | 45.0 |
| points_scale | float | ratio | N | 10000; 100 when the quote currency is JPY | 10000 |
| source | str | - | Y | | file_export_a |

### `infl_fixings`
Price-index prints (non-seasonally-adjusted) with release vintages. Linkers and zero-coupon inflation swaps usually
reference the first-published value. Revisions are kept as later rows, never overwritten.

Primary key: `index_id, ref_month, pub_ts_utc`
Used by: infl-breakevens-and-linkers, macro-inflation-and-energy-drivers, data-quality-and-timeseries-hygiene, quant-seasonality-and-calendar-effects, rv-research-digest

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| index_id | str | - | Y | FK `rate_indices` (family CPI) | EUR-HICPXT |
| ref_month | str | - | Y | `YYYY-MM` the index measures | 2026-10 |
| index_level | float | index | Y | | 131.42 |
| pub_ts_utc | ts | - | Y | release instant of this vintage | 2026-11-17T10:00:00Z |
| is_first_release | bool | - | N | | true |
| source | str | - | Y | | statistics_office |

### `infl_swaps`
Zero-coupon inflation swap rates (market breakevens). Bond breakevens are derived from linker and nominal yields in
`bond_quotes`.

Primary key: `date, snap, index_id, start, tenor`
Used by: infl-breakevens-and-linkers, macro-inflation-and-energy-drivers, curve-forward-grid-rv, macro-central-bank-reaction-functions, macro-fair-value-models, macro-geopolitical-risk, rv-research-digest, vol-rates-options-rv

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ldn |
| index_id | str | - | Y | | EUR-HICPXT |
| start | str | - | Y | | 0D |
| tenor | str | - | Y | | 5Y |
| zc_rate_pct | float | pct | Y | fixed rate of the ZC inflation swap | 2.03 |
| index_lag_months | int | - | N | indexation lag | 3 |
| base_month | str | - | N | `YYYY-MM` of the base index | 2026-08 |
| source | str | - | Y | | file_export_a |

### `infl_seasonals`
Monthly seasonal factors of a price index, as percent deviation from trend (12 values summing to about 0). Fitted
factors are point-in-time: use a set only after `fit_end_date`'s print was published. Fill `valid_from` so
`read_asof` enforces this; without it nothing stops a backtest from reading a set fitted on later prints.

Primary key: `index_id, month, fit_end_date`
Used by: infl-breakevens-and-linkers, quant-seasonality-and-calendar-effects, macro-inflation-and-energy-drivers

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| index_id | str | - | Y | | EUR-HICPXT |
| month | int | - | Y | 1..12 | 1 |
| seasonal_pct | float | pct | Y | % deviation of the NSA index from trend | -0.7 |
| method | str | - | Y | hp, x13, stl, ratio_to_ma | x13 |
| fit_start_date | date | - | N | first index month used | 2015-01-01 |
| fit_end_date | date | - | Y | last index month used | 2026-09-01 |
| valid_from | date | - | N | first date the set may be used: after the fit_end_date print was published | 2026-10-19 |
| source | str | - | Y | | derived |

### `auctions`
Government bond auction calendar and results. `tail_bp = (stop_yield_pct - wi_yield_pct) × 100`, positive = tailed.
Upcoming auctions are rows with only the schedule columns filled. Result columns (allotment, yields, tail, cover)
become known only at the results release: set `results_ts_utc` to that instant on rows that carry results.
`read_asof` keeps the row (the schedule stays visible) and blanks the result columns before that instant, or always
when `results_ts_utc` is null. Do not use `ts_utc` for this: it hides the whole row.

Primary key: `issuer, auction_date, instrument_id`
Checks: `abs(tail_bp - 100*(stop_yield_pct - wi_yield_pct)) < 1e-6`
Used by: bond-supply-and-cashflow-trading, quant-seasonality-and-calendar-effects, macro-fiscal-supply-and-term-premium, bond-rich-cheap-fitted-curve, bt-backtest-design, data-quality-and-timeseries-hygiene, flow-mbs-convexity-hedging, flow-positioning-cftc-and-surveys, flow-sdr-and-dealer-positioning, flow-structural-alm-demand, macro-event-risk-and-prediction-markets, ml-models-for-rates, rv-devils-advocate, rv-execution-and-trade-packaging, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-cross-market-govies, stir-bills-and-money-market-spreads, stir-central-bank-balance-sheet-and-reserves, stir-repo-and-funding-plumbing

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| issuer | str | - | Y | | US |
| auction_date | date | - | Y | may be in the future | 2026-11-12 |
| instrument_id | str | - | Y | FK `bond_static` | BOND:US91282CXX00 |
| announce_date | date | - | N | when size and line became public | 2026-11-05 |
| settle_date | date | - | N | | 2026-11-17 |
| operation | str | - | N | issue (default when null), buyback or switch. For buybacks and switches `allotted_ccy` is the face accepted and `stop_yield_pct` the highest accepted yield | issue |
| format | str | - | N | single_price, multiple_price, yield_dutch, syndication, tap | single_price |
| is_reopening | bool | - | N | | false |
| offered_ccy | float | ccy | N | | 42000000000 |
| allotted_ccy | float | ccy | N | | 42000000000 |
| stop_yield_pct | float | pct | N | high or stop-out yield | 4.112 |
| avg_yield_pct | float | pct | N | | 4.090 |
| wi_yield_pct | float | pct | N | when-issued yield at the bidding deadline | 4.105 |
| tail_bp | float | bp | N | | 0.7 |
| bid_to_cover | float | ratio | N | | 2.48 |
| results_ts_utc | ts | - | N | results release instant | 2026-11-12T18:00:00Z |
| source | str | - | Y | | debt_office |

### `issuance_plan`
Debt-office issuance and buyback plans by bucket and period, one row per release vintage (a revised plan is a new
row). Realised auctions are in `auctions`. Bill share of gross issuance is derived: the `bills` row over the `all` row.
Dated buyback operations are `auctions` rows with `operation=buyback`.

Primary key: `issuer, plan_period, bucket, pub_ts_utc`
Used by: macro-fiscal-supply-and-term-premium

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| issuer | str | - | Y | ISO country code | US |
| plan_period | str | - | Y | `YYYY-Qn`, `YYYY-MM` or fiscal year `FYYYYY` | 2026-Q4 |
| bucket | str | - | Y | bills, 2y, 5y, 10y, 30y, linkers, frn, short, medium, long or all | all |
| ccy | str | - | Y | | USD |
| pub_ts_utc | ts | - | Y | release instant of this plan | 2026-11-02T13:30:00Z |
| gross_ccy | float | ccy | N | planned gross issuance | 570000000000 |
| net_ccy | float | ccy | N | planned net of redemptions and buybacks | 220000000000 |
| redemptions_ccy | float | ccy | N | maturing debt in the period | 350000000000 |
| buyback_ccy | float | ccy | N | planned buybacks | 0 |
| is_estimate | bool | - | N | true for a projection rather than a committed plan | true |
| source | str | - | Y | | debt_office |

### `callable_issuance`
Callable and structured-note deal log, one row per deal per release vintage. A later call or redemption is a new row
with a later `pub_ts_utc` and a changed `status`; never write an outcome on the announcement row. Notional is the
initial notional in `ccy`. Vega per deal is model output: take it from the user's Bermudan pricer.

Primary key: `deal_id, pub_ts_utc`
Used by: vol-structured-flows-and-vega-supply, flow-mbs-convexity-hedging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| deal_id | str | - | Y | | D-2026-0412 |
| pub_ts_utc | ts | - | Y | instant this vintage became public | 2026-11-03T08:00:00Z |
| announce_date | date | - | Y | announcement date of the deal | 2026-11-03 |
| status | str | - | Y | announced, priced, called, redeemed, matured | announced |
| ccy | str | - | Y | deal currency | USD |
| issuer_type | str | - | Y | financial, government, ssa or non_financial | financial |
| listing | str | - | N | listing channel, such as formosa or other | formosa |
| notional_ccy | float | ccy | Y | initial notional in `ccy` | 100000000 |
| structure | str | - | Y | `<final>NC<lockout>`, e.g. 30NC5, or a name such as PRDC | 30NC5 |
| coupon_type | str | - | N | zero or fixed | zero |
| coupon_pct | float | pct | N | fixed coupon, or accretion rate for a zero | 4.10 |
| call_freq | str | - | N | 1Y, 6M, 3M | 1Y |
| first_call_date | date | - | N | | 2031-11-03 |
| maturity_date | date | - | N | | 2056-11-03 |
| call_date | date | - | N | the call this row reports, for `called` and `redeemed` rows | |
| redeemed_ccy | float | ccy | N | face redeemed at `call_date` | |
| swapped | bool | - | N | true when the issuer hedged into floating; null = infer from `issuer_type` | true |
| vega_per_100mn_ccy | float | ccy | N | model vega in ccy per 1bp of normal vol per 100mn notional | 85000 |
| source | str | - | Y | | deal_database |

### `mbs_tba`
Agency mortgage-backed securities forward (TBA) and specified-pool prices by program, coupon and settlement month.
The generic TBA is `pool_class=tba`. A specified pool is the same key with its pool class, so the pay-up is the pool
price minus the TBA price. The dollar roll (drop) is the front-month minus the next-month TBA price. It is derived,
not stored.

Primary key: `date, snap, program, coupon_pct, settle_month, pool_class`
Used by: flow-mbs-convexity-hedging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ny |
| program | str | - | Y | UMBS30, UMBS15, GNII30 and similar program codes | UMBS30 |
| coupon_pct | float | pct | Y | pass-through coupon | 5.5 |
| settle_month | str | - | Y | `YYYY-MM` of the TBA settlement class | 2026-12 |
| pool_class | str | - | Y | `tba`, or a specified-pool class such as lls85 (low loan balance) | tba |
| price_px | float | px | Y | mid price per 100 face, decimal (not 32nds text) | 99.15625 |
| bid_px | float | px | N | | 99.140625 |
| ask_px | float | px | N | | 99.171875 |
| settle_date | date | - | N | settlement date of the class | 2026-12-14 |
| source | str | - | Y | | dealer_runs |

### `mbs_pool_stats`
Aggregated agency MBS pool statistics by program, coupon and origination cohort, published monthly with the factor
release. OAS and OAD come from a prepayment model, so tag them with `model_id`: a re-run is a new vintage.

Primary key: `date, program, coupon_pct, cohort, pub_ts_utc`
Used by: flow-mbs-convexity-hedging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | as-of date of the statistics | 2026-10-31 |
| program | str | - | Y | as in `mbs_tba` | UMBS30 |
| coupon_pct | float | pct | Y | | 5.5 |
| cohort | str | - | Y | origination year such as 2024, or `all` | all |
| pub_ts_utc | ts | - | Y | release instant | 2026-11-06T21:00:00Z |
| balance_ccy | float | ccy | N | current face outstanding | 310000000000 |
| factor | float | ratio | N | current face over original face, 0..1 | 0.86 |
| wac_pct | float | pct | N | weighted-average coupon of the underlying loans | 6.1 |
| wala_months | float | - | N | weighted-average loan age, months | 14 |
| wam_months | float | - | N | weighted-average remaining maturity, months | 338 |
| cpr_pct | float | pct | N | annualised conditional prepayment rate over `cpr_window` | 7.2 |
| cpr_window | str | - | N | 1M, 3M, 6M or 12M | 3M |
| oas_bp | float | bp | N | option-adjusted spread to the model's curve | 38 |
| oad | float | ratio | N | option-adjusted duration in years; can be negative | 5.9 |
| model_id | str | - | N | prepayment and OAS model that produced `oas_bp` and `oad` | model_v3 |
| source | str | - | Y | | agency_factor_release |

## Flows, positioning, events and macro

### `positioning`
Futures positioning by trader class (CFTC-style reports) and client surveys. `date` is the position date and
`pub_ts_utc` the release: CFTC data are as of Tuesday and released Friday 15:30 New York, later around holidays.

Primary key: `date, report, contract, trader_class`
Used by: flow-positioning-cftc-and-surveys, rv-devils-advocate, stir-convexity-adjustment, bond-supply-and-cashflow-trading, curve-butterflies, data-quality-and-timeseries-hygiene, eng-reporting-and-visualization, flow-mbs-convexity-hedging, flow-structural-alm-demand, fut-bond-basis-and-implied-repo, fut-calendar-roll, macro-geopolitical-risk, macro-regime-and-scenario-analysis, macro-technical-analysis, ml-financial-ml-methodology, ml-models-for-rates, quant-lead-lag, quant-regression-and-hedge-ratios, quant-zscore-and-signal-screening, rv-research-digest, rv-trade-idea-writeup, rv-trade-monitoring, spread-ccp-basis, stir-futures-rv, vol-convexity-and-long-end, vol-skew-and-tail-hedging, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | position as-of date | 2026-11-03 |
| pub_ts_utc | ts | - | Y | release instant | 2026-11-06T20:30:00Z |
| report | str | - | Y | cftc_tff, cftc_legacy, cftc_disagg, exchange, survey | cftc_tff |
| contract | str | - | Y | contract or market covered, all months combined | ZN |
| trader_class | str | - | Y | dealer, asset_manager, leveraged_funds, other_reportables, nonreportable, noncommercial, commercial, total | leveraged_funds |
| long_cnt | float | cnt | N | | 1050000 |
| short_cnt | float | cnt | N | | 1820000 |
| spread_cnt | float | cnt | N | | 310000 |
| oi_cnt | float | cnt | N | total open interest | 4900000 |
| net_dv01_ccy | float | ccy | N | if converted to DV01; positive = long duration | -82000000 |
| long_frac | float | frac | N | survey share long | 0.18 |
| short_frac | float | frac | N | survey share short | 0.22 |
| neutral_frac | float | frac | N | survey share neutral; long + neutral + short = 1 when all three are given | 0.60 |
| source | str | - | Y | | regulator_report |

### `flows_trades`
Public trade-repository (SDR-style) prints and venue trade tapes. Blocks can be disseminated late and with capped
notionals. Cancels and corrections are new rows that reference the original.

Primary key: `trade_uid, pub_ts_utc`
Used by: flow-sdr-and-dealer-positioning, bt-transaction-costs-and-liquidity, rv-execution-and-trade-packaging, bond-supply-and-cashflow-trading, curve-butterflies, flow-mbs-convexity-hedging, flow-positioning-cftc-and-surveys, flow-structural-alm-demand, quant-lead-lag, quant-zscore-and-signal-screening, rv-devils-advocate, rv-research-digest, rv-trade-monitoring, spread-ccp-basis, vol-convexity-and-long-end, vol-skew-and-tail-hedging, vol-structured-flows-and-vega-supply, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| trade_uid | str | - | Y | dissemination id | 9f1c2e |
| pub_ts_utc | ts | - | Y | dissemination instant | 2026-11-10T15:02:11Z |
| exec_ts_utc | ts | - | N | execution instant | 2026-11-10T15:01:58Z |
| action | str | - | Y | new, cancel, correct | new |
| orig_trade_uid | str | - | N | trade a cancel or correction refers to | |
| product | str | - | Y | irs, ois, basis, fra, swaption, capfloor, xccy, infl_swap; tape prints also bond_fut, stir_fut, listed_opt, govt | ois |
| ccy | str | - | Y | | USD |
| index_id | str | - | N | | USD-SOFR |
| effective_date | date | - | N | | 2026-11-12 |
| maturity_date | date | - | N | | 2036-11-12 |
| tenor | str | - | N | derived from dates | 10Y |
| fixed_rate_pct | float | pct | N | | 3.8125 |
| spread_bp | float | bp | N | basis spread | |
| notional_ccy | float | ccy | N | as disseminated | 250000000 |
| notional_capped | bool | - | N | true = shown at the block cap; true size is larger | true |
| is_package | bool | - | N | leg of a package or spread trade | false |
| is_compression | bool | - | N | compression or portfolio-maintenance trade; weak price content | false |
| cleared | bool | - | N | | true |
| clearing_house | str | - | N | | LCH |
| venue | str | - | N | venue name or off_facility | off_facility |
| aggressor_side | str | - | N | initiator, where the tape flags it: pay_fixed or receive_fixed for swaps, buy or sell for futures, bonds and options. Null = unknown, never guessed from price | pay_fixed |
| instrument_id | str | - | N | exchange-listed or cash prints: FK `fut_static`, `opt_static` or `bond_static` | FUT:ZN:2026-12 |
| price_px | float | px | N | exchange-listed or cash prints, decimal | 112.78125 |
| qty_cnt | float | cnt | N | contracts, for exchange-listed prints | 250 |
| option_right | str | - | N | C or P, for swaptions, caps and listed options. Put and call notional are sums of `notional_ccy` by right | C |
| option_strike_pct | float | pct | N | swaptions and caps | |
| option_expiry_date | date | - | N | | |
| premium_ccy | float | ccy | N | | |
| source | str | - | Y | | trade_repository |

### `dealer_flow`
Dealer-tagged prints for dealer-level flow methods (offsetting ratio, dealer inventory, hedge models). Public trade
repositories carry no counterparty identity, so this table comes from a dealer, a venue or a client-flow feed and is
never inferred from `flows_trades`. `dealer_id` is an id assigned by the adapter, not a name.

Primary key: `dealer_id, trade_uid`
Used by: flow-sdr-and-dealer-positioning

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| dealer_id | str | - | Y | adapter-assigned id | D1 |
| trade_uid | str | - | Y | print id, unique within `dealer_id` | 7c21a0 |
| exec_ts_utc | ts | - | Y | execution instant | 2026-11-10T15:01:58Z |
| pub_ts_utc | ts | - | Y | instant the print became available to the user | 2026-11-10T15:02:30Z |
| ccy | str | - | Y | | USD |
| dv01_ccy | float | ccy | Y | signed DV01 per bp of the print, from the dealer's side: positive = the dealer bought duration (received fixed or bought a bond) | 50000 |
| notional_ccy | float | ccy | N | signed, same direction as `dv01_ccy` | 250000000 |
| product | str | - | N | as `flows_trades.product` | ois |
| tenor | str | - | N | | 10Y |
| venue_type | str | - | N | d2c (dealer to client), d2d (dealer to dealer) or other | d2c |
| is_large | bool | - | N | block-size print | true |
| flows_trade_uid | str | - | N | matching `flows_trades.trade_uid` when the print is also public | |
| source | str | - | Y | | client_flow_feed |

### `book_snapshots`
Order-book depth, one row per instrument, instant, side and level, for event-time cost and impact models and for
checking the displayed size behind a quote. `ts_utc` is required here: it is the snapshot instant.

Primary key: `ts_utc, instrument_id, side, level`
Used by: bt-transaction-costs-and-liquidity

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | trading date in the venue's session | 2026-11-10 |
| ts_utc | ts | - | Y | snapshot instant | 2026-11-10T15:00:00Z |
| instrument_id | str | - | Y | FK `fut_static`, `bond_static` or a dated swap id | FUT:ZN:2026-12 |
| venue | str | - | N | | CME |
| side | str | - | Y | bid or ask | bid |
| level | int | - | Y | 1 = best | 1 |
| price_px | float | px | N | futures and bonds | 112.78125 |
| rate_pct | float | pct | N | swaps quoted as a rate | |
| size_cnt | float | cnt | N | contracts displayed | 1450 |
| size_ccy | float | ccy | N | notional displayed, in the row's currency | |
| source | str | - | Y | | venue_feed |

### `bid_offer`
Half-spreads by product, structure and quote type, in bp of the quoted measure, for cost models and execution
planning. A fill-level cost is `trades.slippage_bp`. `half_spread_bp` is one-way: half of the bid-offer width. Convert
futures ticks to bp at the adapter.

Primary key: `date, snap, product, structure, ref, quote_type`
Used by: bt-transaction-costs-and-liquidity, rv-execution-and-trade-packaging

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ldn |
| product | str | - | Y | irs, ois, basis, xccy, swaption, capfloor, infl_swap, govt, bond_fut, stir_fut | ois |
| structure | str | - | Y | outright, curve, fly, switch, basis, box | curve |
| ref | str | - | Y | what the quote is on: `<curve_id>:<tenor or package>` or an instrument id | USD-SOFR:2s10s |
| quote_type | str | - | Y | dealer_indicative, dealer_firm, rfq, screen_clob, broker, matrix | dealer_indicative |
| quote_unit | str | - | Y | the measure the bp refers to: rate, spread, nvol or yield | spread |
| half_spread_bp | float | bp | Y | one-way half-spread | 0.4 |
| size_dv01_ccy | float | ccy | N | DV01 per bp the quote is good for | 50000 |
| source | str | - | Y | | dealer_runs |

### `events_probs`
Event probabilities from prediction markets or derived from market prices. A binary contract priced in dollars per
1-dollar payout is a probability. Do not store the outcome on earlier rows: record settlement as a final row with
`snap=fix` and `prob` 0 or 1 on the resolution date.

Primary key: `date, snap, venue, market_id, outcome`
Used by: macro-event-risk-and-prediction-markets, stir-policy-pricing-whats-priced-in, macro-central-bank-nlp, macro-central-bank-reaction-functions, macro-geopolitical-risk, macro-regime-and-scenario-analysis, ml-financial-ml-methodology, ml-models-for-rates, port-scenario-and-stress-testing, quant-bayesian-methods, rv-devils-advocate, rv-research-digest, rv-trade-idea-writeup, vol-rates-options-rv

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-10 |
| snap | str | - | Y | | eod_ny |
| venue | str | - | Y | prediction venue, or `implied_ois` for curve-implied | implied_ois |
| event_id | str | - | Y | e.g. `FED-2026-12-09`, `US-CPI-2026-11` | FED-2026-12-09 |
| market_id | str | - | Y | venue's market id | FED-2026-12-09-T |
| outcome | str | - | Y | hike_25, hold, cut_25, yes, ... | cut_25 |
| prob | float | prob | Y | mid probability | 0.32 |
| bid_prob | float | prob | N | | 0.31 |
| ask_prob | float | prob | N | | 0.33 |
| volume_cnt | float | cnt | N | | 52000 |
| oi_cnt | float | cnt | N | | 410000 |
| linked_meeting_date | date | - | N | FK `cb_meetings` | 2026-12-09 |
| threshold_pct | float | pct | N | rate threshold for "above X%" markets | 3.75 |
| resolution_date | date | - | N | scheduled resolution | 2026-12-09 |
| is_stale | bool | - | N | no trade since the previous snap; price carried forward | false |
| source | str | - | Y | | file_export_a |

### `cb_texts`
Central-bank documents: statements, minutes, speeches, press conferences, Q&A and testimony. One row per document
and release vintage; `pub_ts_utc` is the knowledge time. Split a Q&A by speaker so only the official's words are
scored, and never merge a questioner's words into an official's row. Scores derived from the text are `macro_series`
rows with `unit=score`.

Primary key: `doc_id, pub_ts_utc`
Used by: macro-central-bank-nlp

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| doc_id | str | - | Y | | FED-STMT-2026-12-09 |
| pub_ts_utc | ts | - | Y | release instant of this vintage | 2026-12-09T19:00:00Z |
| cb | str | - | Y | as `cb_meetings.cb` | FED |
| speaker | str | - | N | official's id or role; null for an institutional document | chair |
| role | str | - | N | chair, governor, member, staff | chair |
| doc_type | str | - | Y | statement, minutes, speech, press_conference, qa, testimony, interview, report | statement |
| lang | str | - | N | ISO-639 code | en |
| ref_meeting_date | date | - | N | FK `cb_meetings`, for statements, minutes and press conferences | 2026-12-09 |
| text | str | - | Y | document text | |
| source | str | - | Y | | cb_website |

### `macro_series`
Economic releases, survey consensus, central-bank balance-sheet and money-market aggregates, text-derived scores, and
other one-number-per-period series that have no table of their own: published term-premium models, market indices
and prices, bank-level regulatory ratios. One row per release vintage. The value's unit is in the `unit` column. For a
market-priced series (index, price, implied vol) `ref_period` is the date `YYYY-MM-DD` and `pub_ts_utc` the snap
instant, so `read_asof` still enforces the snap. Percent levels are stored as percent, like every rate in the
contract (4.25 = 4.25%), and skills convert to bp when they report. Series naming is `<COUNTRY>-<NAME>`; the patterns
are in the table after the columns.

Primary key: `series_id, ref_period, pub_ts_utc`
Used by: macro-inflation-and-energy-drivers, macro-central-bank-reaction-functions, macro-central-bank-nlp, macro-regime-and-scenario-analysis, stir-central-bank-balance-sheet-and-reserves, macro-fiscal-supply-and-term-premium, quant-lead-lag, bt-backtest-design, curve-butterflies, curve-steepeners-flatteners, curve-term-structure-models, data-quality-and-timeseries-hygiene, fi-balance-sheet-and-regulatory-costs, flow-mbs-convexity-hedging, flow-positioning-cftc-and-surveys, flow-structural-alm-demand, infl-breakevens-and-linkers, macro-event-risk-and-prediction-markets, macro-fair-value-models, macro-geopolitical-risk, macro-technical-analysis, ml-financial-ml-methodology, ml-models-for-rates, port-scenario-and-stress-testing, quant-bayesian-methods, quant-regime-detection, quant-regression-and-hedge-ratios, quant-seasonality-and-calendar-effects, quant-systematic-rates-signals, quant-time-series-econometrics, rv-research-digest, spread-ccp-basis, spread-cross-market-govies, spread-tenor-and-index-basis, stir-bills-and-money-market-spreads, stir-repo-and-funding-plumbing, vol-correlation-and-curve-options, vol-structured-flows-and-vega-supply, xccy-basis

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| series_id | str | - | Y | `<COUNTRY>-<NAME>` | US-CPI-CORE-MOM |
| ccy | str | - | Y | currency of the country or market; the currency of a `price` or `ccy_bn` value | USD |
| ref_period | str | - | Y | `YYYY-MM-DD`, `YYYY-MM` or `YYYY-Qn` | 2026-10 |
| pub_ts_utc | ts | - | Y | release instant of this vintage | 2026-11-12T13:30:00Z |
| value | float | - | Y | | 0.3 |
| unit | str | - | Y | pct_mom, pct_yoy, pct (a level in percent), bp, index, price, ccy_bn, k_persons, score, ratio | pct_mom |
| unit_detail | str | - | N | quantity basis of a `price` (per bbl, per MWh, per mmbtu) or the construction of a `ratio` or `score` | per bbl |
| consensus | float | - | N | survey median known before release, same unit | 0.3 |
| is_first_release | bool | - | N | | true |
| source | str | - | Y | | statistics_office |

Series id patterns (documentation only):

| series | `series_id` pattern | `unit` | example |
|---|---|---|---|
| published term premium, one series per model and tenor | `<CC>-TP-<MODEL>-<TENOR>` | pct | `US-TP-ACM-10Y`, `US-TP-KW-10Y` |
| local equity total-return index (net of cash) | `<CC>-EQ-<INDEX>-TR` | index | `US-EQ-BROAD-TR` |
| equity or FX implied vol | `<CC>-EQVOL-<INDEX>-<TENOR>`, `<PAIR>-FXVOL-<TENOR>-<DELTA>` | pct | `EURUSD-FXVOL-3M-ATM` |
| commodity front-month and curve, one series per nearby | `GL-<COMMODITY>-M<n>` | price (currency in `ccy`, quantity basis in `unit_detail`) | `GL-BRENT-M1` |
| trade-weighted FX, terms of trade | `<CC>-FX-TW`, `<CC>-TOT` | index | `AU-TOT` |
| survey-consensus forecast of a series (the forecast itself, not the release consensus) | `<CC>-<NAME>-FCST-<HORIZON>` | pct | `US-CPI-FCST-10Y-AVG` |
| central-bank balance-sheet, fiscal and money-market aggregates | `<CC>-<AGG>` | ccy_bn, pct | `US-TGA`, `US-RESERVES`, `US-ON-RRP` |
| text-derived scores and attention indices | `<CC>-CB-HDS-<DOC>`, `<CC>-CB-TOPIC-<TOPIC>`, `GL-GPR` | score | `US-CB-HDS-STMT` |
| forecast-revision or growth indices | `<CC>-<NAME>` | index or score | `US-GROWTH-REVISIONS` |
| credit and financial-conditions gauges | `<CC>-CREDIT-<GRADE>-OAS`, `<CC>-FCI` | bp, index | `US-CREDIT-IG-OAS` |
| bank-level regulatory ratios | `<CC>-GSIB-<BANK>-SLR`, `-SCORE`, `-SURCHARGE` | pct, score, pct | `US-GSIB-BANKA-SLR` |

## Backtest I/O tables

### `signals`
Signal values per package and decision date. A signal dated `t` uses only data known at `snap` on `t`. Positions
use it from `t+1` (shift by one period).

Primary key: `date, strategy_id, package_id`
Used by: quant-zscore-and-signal-screening, quant-signal-combination-and-decay, rv-composite-scoring, bt-backtest-design, bt-validation-and-overfitting, ml-financial-ml-methodology, bt-performance-attribution, eng-reporting-and-visualization, ml-models-for-rates, port-position-sizing-and-risk-budget, quant-bayesian-methods, quant-lead-lag, quant-mean-reversion-ou, quant-regime-detection, quant-time-series-econometrics, rv-devils-advocate, rv-trade-idea-writeup, curve-term-structure-models

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | decision date | 2026-11-10 |
| snap | str | - | Y | snap of the input data | eod_ny |
| strategy_id | str | - | Y | | fly_mr_v1 |
| package_id | str | - | Y | | USD-SOFR:2Y5Y10Y:fly |
| value | float | - | Y | | 7.4 |
| unit | str | - | Y | bp, z, score, prob | bp |
| zscore | float | ratio | N | | 2.1 |
| horizon_days | float | days | N | intended holding horizon | 60 |
| model_version | str | - | N | code or parameter version | v1.3 |

### `positions`
End-of-day holdings per package leg. Instruments are specific and frozen at entry; a dated swap is
`SWAP:<curve_id>:<effective>:<maturity>`. `dv01_ccy` is signed: positive = long duration (long bond or futures,
receive fixed).

Primary key: `date, strategy_id, package_id, leg`
Used by: bt-backtest-design, port-portfolio-construction, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, rv-trade-monitoring, bt-performance-attribution, bt-transaction-costs-and-liquidity, bt-validation-and-overfitting, curve-pca-factor-model, eng-python-analytics-stack, eng-reporting-and-visualization, fi-risk-dv01-and-transforms, fut-invoice-spreads, quant-covariance-estimation, rv-composite-scoring, rv-devils-advocate, rv-execution-and-trade-packaging, rv-trade-idea-writeup, vol-gamma-vega-pnl

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | holdings after this date's trades | 2026-11-11 |
| strategy_id | str | - | Y | | fly_mr_v1 |
| package_id | str | - | Y | | USD-SOFR:2Y5Y10Y:fly |
| structure | str | - | N | outright, curve, fly, basis, spread, box, option | fly |
| leg | int | - | Y | 1-based leg number | 2 |
| instrument_id | str | - | Y | specific instrument | SWAP:USD-SOFR:2026-11-13:2031-11-13 |
| ccy | str | - | Y | | USD |
| notional_ccy | float | ccy | N | signed: positive = long / receive fixed | 21500000 |
| qty_cnt | float | cnt | N | contracts, signed | |
| dv01_ccy | float | ccy | N | signed DV01 per bp | 10000 |
| weight | float | ratio | N | signed risk weight in the package (receive-belly 50/50 fly: −0.5, +1, −0.5) | 1.0 |

### `trades`
Executions, real or simulated. `qty` is signed: positive = long the instrument (buy bond or futures, receive fixed).

Primary key: `trade_id`
Used by: bt-backtest-design, bt-transaction-costs-and-liquidity, rv-trade-monitoring, bt-performance-attribution, bt-validation-and-overfitting, eng-reporting-and-visualization, quant-mean-reversion-ou, rv-devils-advocate, rv-execution-and-trade-packaging, vol-gamma-vega-pnl

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| trade_id | str | - | Y | | t000187 |
| ts_utc | ts | - | Y | execution or simulated-fill instant | 2026-11-11T14:00:00Z |
| strategy_id | str | - | Y | | fly_mr_v1 |
| package_id | str | - | Y | | USD-SOFR:2Y5Y10Y:fly |
| leg | int | - | Y | | 2 |
| instrument_id | str | - | Y | | SWAP:USD-SOFR:2026-11-13:2031-11-13 |
| ccy | str | - | Y | | USD |
| qty | float | - | Y | signed size in qty_unit | 21500000 |
| qty_unit | str | - | Y | notional_ccy or cnt | notional_ccy |
| price | float | - | Y | fill level in price_unit | 3.6075 |
| price_unit | str | - | Y | px, pct or bp | pct |
| fee_ccy | float | ccy | N | fees, ≤ 0 | -250 |
| slippage_bp | float | bp | N | adverse distance from mid in the quoted level: buy or pay-fixed fill − mid, sell or receive-fixed mid − fill; positive = cost | 0.25 |

### `pnl`
Daily P&L per package with components that sum to the total. `mtm_ccy` is the clean-price or NPV change excluding
accrual, and `carry_ccy` is the change in accrued interest plus coupon cash received (= interest earned; on a coupon
date accrued falls by the coupon and the cash offsets it). A bond's dirty-price change plus coupon cash therefore
equals mtm + carry, with nothing counted twice.

Primary key: `date, strategy_id, package_id`
Checks: `abs(total_ccy - mtm_ccy - carry_ccy - financing_ccy - cost_ccy) < 0.01`
Used by: bt-performance-attribution, bt-backtest-design, bt-validation-and-overfitting, rv-trade-monitoring, eng-reporting-and-visualization, bt-transaction-costs-and-liquidity, curve-pca-factor-model, port-position-sizing-and-risk-budget, port-scenario-and-stress-testing, quant-bayesian-methods, quant-regime-detection, quant-signal-combination-and-decay, rv-devils-advocate, rv-trade-idea-writeup, vol-gamma-vega-pnl

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| date | date | - | Y | | 2026-11-11 |
| strategy_id | str | - | Y | | fly_mr_v1 |
| package_id | str | - | Y | package, or ALL for the strategy total | USD-SOFR:2Y5Y10Y:fly |
| ccy | str | - | Y | reporting currency | USD |
| mtm_ccy | float | ccy | Y | clean or NPV change, excluding accrual | 18250 |
| carry_ccy | float | ccy | Y | change in accrued plus coupon cash received (interest earned) | 410 |
| financing_ccy | float | ccy | Y | repo or funding; negative = cost | -120 |
| cost_ccy | float | ccy | Y | fees and slippage, ≤ 0 | -790 |
| total_ccy | float | ccy | Y | sum of the four components | 17750 |
| dv01_ccy | float | ccy | N | end-of-day signed DV01 | 120 |

### `trial_log`
Append-only log of every backtest run, including controls, aborted runs and categorical choices, so the trial count
`N` behind a deflated Sharpe ratio is the number of distinct `trial_id` and not a memory. Rows are never edited: a
status change is a new row for the same `trial_id` with a later `run_ts_utc`, so relabelling a run never adds a trial.
Per trial, read the latest row.

Primary key: `trial_id, run_ts_utc`
Used by: bt-validation-and-overfitting

| column | dtype | unit | req | description | example |
|---|---|---|---|---|---|
| trial_id | str | - | Y | one id per distinct parameter set and sample window | T0137 |
| run_ts_utc | ts | - | Y | instant this row was written (the run, or a later status change) | 2026-11-11T09:12:00Z |
| strategy_id | str | - | Y | FK `signals.strategy_id` | fly_mr_v1 |
| param_hash | str | - | Y | hash of the full parameter set | 3e9a71 |
| params | str | - | N | parameter set as JSON text | {"lookback": 60} |
| sample_start_date | date | - | Y | first date of the sample | 2019-01-01 |
| sample_end_date | date | - | Y | last date of the sample | 2024-12-31 |
| cost_multiple | float | ratio | N | cost multiplier, 1 = base-case costs | 1.0 |
| is_control | bool | - | N | always-on, random-entry or other null control | false |
| status | str | - | Y | candidate, selected, rejected, aborted | candidate |
| obs_cnt | int | cnt | N | number of return observations | 1510 |
| sharpe_is | float | ratio | N | annualised in-sample Sharpe | 1.8 |
| sharpe_oos | float | ratio | N | annualised out-of-sample Sharpe | 0.6 |
| model_version | str | - | N | code version | v1.3 |
| source | str | - | Y | | backtest_runner |
