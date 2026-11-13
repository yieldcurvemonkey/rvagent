---
name: eng-reporting-and-visualization
description: Standard G10 rates RV screens, charts and one-page reports - column sets (level, 1d/1w/1m change, z, percentile, carry and roll, vol, Sharpe, trend, directionality R, Carry/R), normalised-move grids, ranked top/bottom lists, history charts with z-bands, regression and density scatters, heat-maps, sparklines, aged-curve overlays, DV01 positioning panels, funding monitors, trader risk dashboards and backtest tearsheet statistics, with sign legends and colour rules. Use when asked to build, lay out, format or review a screen, dashboard, chart, one-pager, tearsheet, heat-map, "what moved" grid, rich/cheap table or trade-idea exhibit, or to decide what to plot for a spread, fly, forward, basis or swap spread.
---

# Reporting and visualization for RV

An RV screen is a ranked table plus a few charts whose job is to make one decision fast: which rows deserve work, and
in which direction. Every cell must say what it measures, in which unit, and which leg is rich. This skill fixes the
column set, the formulas behind the standard columns, the page layouts and the chart rules, so that every output of
the agent reads the same way and cannot be misread (sign, window, pool, snap).

## When to use
- Building or reviewing a screen: "rank the flies", "what moved most this week", "rich/cheap table for the UST curve".
- Choosing charts for an idea: history with bands, regression scatter, forward-curve overlay, heat-map of z by lookback.
- Laying out a one-pager for a trade (feeds the write-up skill) or a standing dashboard (positioning, funding, risk).
- Reporting a backtest: tearsheet fields, drawdown and concentration statistics, what to disclose.
- Someone asks "what does this column mean / which sign" about a desk report: use the definitions below.

## Inputs (data-agnostic)
Canonical tables from [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md); never read a vendor field.

| Input | Table | Granularity / history | Notes |
|---|---|---|---|
| par swap/OIS or constant-maturity govt rates | `curve_par` | daily, one `snap`, >= 5y for 5y z, >= 1y for ranges | `par_rate_pct` x 100 = bp. Spot-start rows (`start=0D`) for spreads/flies; forward-start rows for forward grids |
| swap spreads, ASW, invoice spreads | `swap_spreads` | daily | read `sign_convention` on every row and print it |
| bond yields/prices, per-bond static | `bond_quotes`, `bond_static` | daily | amount outstanding for liquidity columns |
| futures, STIR, options | `fut_quotes`, `stir_quotes`, `opt_quotes`, `vol_surface` | daily | normal vol in bp |
| repo and funding rates | `repo_rates`, `rate_fixings` | daily | for funding monitors |
| positioning | `positioning` | weekly (`date` = as-of, `pub_ts_utc` = release) | use `net_dv01_ccy`, positive = long duration |
| signals, holdings, P&L, fills | `signals`, `positions`, `pnl`, `trades` | daily | tearsheets and risk dashboards |

If a needed series is missing, say which table and history length is required and ask the user or the data adapter.
Never fill a cell with an invented or interpolated number without marking it.

## Method

### 1. Conventions printed on every page (header or footer)
- **Units and signs.** Rates, spreads, flies, carry in bp. Curve spread A-B = longer minus shorter (2s10s = 10y - 2y).
  Fly 2s5s10s = 2 x 5y - 2y - 10y, positive = belly high (cheap). A fly is a level, not a P&L: say the weights
  (50/50 yield weights as plotted, or DV01-neutral) and that the trade must be rebuilt DV01-neutral before acting.
- **Perspective.** State it once: "carry, z and trend are from the PAYER view" (desk screens) or "from the RECEIVER view".
  A receiver idea needs the opposite signs of every payer-view column (negative carry, positive z, negative trend
  together). Positive DV01 = long duration = receive fixed. Some textbooks use the opposite DV01 sign: convert on input.
- **Spread-vs-govt sign.** US swap spread = swap minus Treasury yield (usually negative). EGB asset-swap spread = bond
  minus swap (positive = bond cheap). Print the convention next to the first number: the table `swap_spreads`
  carries `sign_convention` per row. Likewise print "basis = B - A; positive = CDS cheap" style legends.
- **Snap, window and pool.** One `snap` per series (never mix closes). Print the as-of date, z window, range window and,
  for scores, the pool (currency vs global): scores are rankings that change with the pool and the day.
- **Undefined source columns.** If a column is borrowed from research that does not define it (a "% of spread" column,
  a fitted-curve spread), write the formula in the footer or drop the column.

### 2. Standard screen column set (one row per structure)
Order columns so the eye moves from "where is it" to "is it unusual" to "does it pay":

| Block | Columns | Definition and default |
|---|---|---|
| Level | current level (bp or %), 1d / 1w / 1m change | change over 1, 5, 21 business days, same snap |
| Context | z (3m), z (1y), percentile (1y), 1y min / 25th / 75th / max | z = (level - mean) / sd over the window including today; 3m = 63, 1y = 252, 5y = 1260 business days. Percentile = mid-rank within the window |
| Move | normalised move 1d, 1w, 1m | see section 3 |
| Pay-off | 3m carry & roll (bp), 3m vol (bp), Ex Ante Sharpe, expected return | see below |
| Style | 2w trend, directionality R, Carry/R | see below |
| Liquidity | amount outstanding, free float, futures CTD flag, on/off-the-run | for bond rows |

Desk definitions (payer view, from a G10 best-trade report, GS Global Rates Best Trade Report, 30 Sep 2026):
- **Ex Ante Sharpe** = implied 3m carry & roll / 3m realised vol, annualised. Printed tables fit
  `Sharpe = 2 x carry_3m_bp / printed_vol_bp` on every row checked (reader's arithmetic, not stated by the desk).
- **Entry Z** = (current level - 5y mean) / 5y sd.
- **2w change** = today's 2w-aged yield minus the entry yield 2w ago, in bp: a realised total return including roll.
- **Trend** = 2w realised total return / 3m realised vol, annualised; printed tables fit `13 x 2w_change_bp / printed_vol_bp`.
  Never substitute a plain price or level change: the roll is part of the return.
- **R** = Spearman rank correlation of 3-day changes of the trade level vs 3-day changes of the 10y swap rate, 3m lookback.
- **Carry/R** = Sharpe / (1 + |R|): carry that is disguised duration is penalised.
- **Expected return** (cash RV, RiskVal Overview 201, 12 Nov 2021) = mean-reversion return (bp to the 3m mean, in the
  trade's direction) + 3m carry & roll. Add **MR frequency** = times the level crossed its 3m mean in the last 3m
  and **1-sd MR frequency** = times it went from 1 sd to the mean in 3m. A spread that rarely mean-reverts gets no
  expected-return credit.
- Scale ambiguity: the desk footnote does not say how "printed vol" is scaled. The two fits above are exactly annualised if
  printed vol = daily sd x sqrt(63) (annualised vol / 2). The bundled script takes `vol_bp` as an input and offers that
  scaling as `vol_3m_horizon`; label your own vol column with its scaling.

### 3. Normalised-move grid ("what moved")
`score = change over horizon / sd of changes over that horizon`. Desk practice (GS Market Movers, 30 Sep 2026): 1d and
1w scored on 62 business days of history, 1m on 252. Default here: the sd is ex ante (window ends before the move
starts) so a large move does not dilute its own score; the desk's treatment of the current observation is not stated.
Per cell show: change, score, 1y min/max bar with 25th/75th markers, level at horizon start and now; sparkline for
the biggest mover per category.
Universe template (EUR, GBP, USD, JPY): outrights 2y 5y 10y 30y + 2y3y 5y5y 10y20y; curves 2s5s 2s10s 2s30s 5s10s 5s30s
10s30s and forward curves; flies 2s5s10s 2s10s30s 5s10s30s; other: 10y vs Germany (EUR: Italy - Germany), 10y breakeven,
10y real yield, 10y swap spread or ASW, 2y xccy basis vs USD, plus credit, equity, FX, gold, oil as context rows.
Run it as three grids: daily, weekly, monthly. Default here: flag |score| >= 3 and read the sd window first.

### 4. Ranked lists (the standard screen output)
- Top and bottom N (default 10) by: level z, 1w change, normalised move, Carry/R, carry, trend; split by sector
  or currency when universes differ in size.
- Show the raw bp value next to every ratio. Put a **floor on the denominator** before ranking a ratio column
  (default: |denominator| >= 25 bp for "basis as % of spread"; state the floor). Without it a near-zero I-spread gives
  values like 1,206% (JPM Credit Research, HG CDS Bond Basis Report, 22 Oct 2025).
- Conditional format: red if z < -2, green if z > 2 (GS US Treasury RV Report, 25 Sep 2026). That is a screen flag,
  not a signal: pair it with the direct-spread z and the mean-reversion frequency.
- Show matched-maturity and proceeds ASW side by side for bonds: the gap is large on deep-discount, premium and
  zero-coupon bonds (over 50 bp on a zero-coupon strip, example 5).
- Conflicting signals: when carry, entry and trend disagree the row is excluded from combined lists by construction,
  but keep it in the single-factor list with a "conflict" tag.

### 5. Diagnostic scatters (four per currency and for the global pool)
Colour points by structure type (outright, curve, fly); draw the regression line through the "attractive" quadrants.

| x vs y | Question it answers |
|---|---|
| Carry vs Entry (z) | most attractive combination |
| Trend vs Entry (z) | which reversal is gaining momentum |
| Carry vs Trend | which carry trades are performing |
| Carry vs R | which carry is most correlated to outright rates (quadrants "attractive long/short") |

Attractive set (payer view) = positive carry, negative z, positive trend (pay signals aligned), or the mirror image for
receive. The desk 3-factor score is the distance from the origin of the projection of (carry, entry, trend) onto the
least-squares plane fitted to the attractive trades, refit daily; 2-factor scores project onto a line. Treat it as a
ranking only; for the agent's own ranking use [rv-composite-scoring](../rv-composite-scoring/SKILL.md).

### 6. Chart rules
- **History chart.** Level (one data hue), trailing mean dashed grey, +/-1 and +/-2 sd bands in light grey, last point
  in the accent colour, title carrying last value and z. Business-day x index so holidays do not stretch the axis;
  never interpolate across missing data (the bundled script drops NaN rows, so list data gaps in the footer). Window = the z window of the table (default 1y) and say so.
- **Aged curve / roll chart.** Plot the leading trade plus the same trade "aged" one year (rolled forward on today's
  curve), so carry and roll are visible against history (GS Best Trade Report); for curves, overlay today vs 1m ago.
- **Relative chart.** Plot a ratio or spread against its benchmark as well as the absolute levels: relative tops and
  bottoms often lead absolute ones (BofA Global Research, Technicals Explained, 14 Jan 2025).
- **Regression scatter.** Last point accent, +/-1 residual-sd lines, title with beta, R2, last residual in bp and sd; say which leg is y (y on x) and that residuals of a level-on-level
  fit are autocorrelated, so the residual sd is a display band, not a test; take hedge ratios from regressions on changes.
  Add a **density layer**: one 2-D Gaussian per point (bandwidth from the observed x and y sd), summed on a grid and drawn in
  greyscale behind the dots, so overlapping points are not read as one and outliers are not over-weighted
  (Duering, Fixed Income Trading and Risk Management, 2021; reuse for RV scatters is this skill's extension).
- **Heat-map.** Diverging with a neutral grey midpoint for signed z or Sharpe (z = 0 neutral); single-hue sequential
  for magnitudes; cell text = value, bold at |z| >= 2; rows sorted by the longest window.
- **Colour and axes.** Colour by entity (an instrument keeps its colour when a filter removes others), not by rank.
  One data hue, one accent, grey guides. Never a second y-axis: use stacked panels. Direct labels where contrast is low.
- **Dates.** Windows in business days; a 1y window of 252 obs is not 365 calendar days.

### 7. Page layouts
**Opportunity one-pager** (one trade, one page): (1) title = structure in trader notation, currency, side, pool/date;
(2) sign legend line; (3) key numbers strip: level, 1w change, z 3m/1y/5y, percentile, carry & roll 3m, vol, Sharpe,
R, Carry/R; (4) history chart with bands + aged overlay; (5) regression or forward-curve chart; (6) legs table:
instrument, weight, DV01, notional, yield, liquidity; (7) catalysts and risks line; (8) footer with formulas for every
non-obvious column, windows, snap, data gaps. Hand it to
[rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).

**Report structure** (screen over many structures, GS desk format): Global Summary (tables, then the three
scatters) -> one block per currency: top-30 lists for highest carry, strongest trend, best entry (3m vol-adjusted);
score tables each paired with a chart of the top trade; the four scatters; full outright, curve and fly metric tables.
Global tables are selected from the top 5 per currency. Aggregation for summaries: market -> sector -> tenor bucket ->
rating (credit) or currency -> structure type (rates), each with level and 1d/1w/1m/ytd changes.

Naming: forward outright "1y1y"; forward curve "1y1y/2y1y"; forward-start spread "3y 2s5s"; forward fly "3y 2s5s10s"
(start, then trader notation). Curves and flies are shown in bp (the desk prints % with parentheses for negatives).

**Specialised panels** (layouts, definitions and dated numbers in [references/panels.md](references/panels.md)):
cash-bond RV screen, futures positioning in DV01, money-market stress and funding monitors, trader risk dashboard,
price-format futures spread display, credit basis screen.

### 8. Backtest tearsheet fields (López de Prado, Advances in Financial Machine Learning, 2018, Ch. 14)
- General: time range, average AUM, capacity, leverage = average dollar position / average AUM, maximum dollar position
  (should be close to average AUM), long ratio (about 0.5 for market-neutral), bets per year (a bet ends when the
  position is flattened or flipped; #bets < #trades), average holding period, annualised turnover = average dollar
  traded per year / average annual AUM, correlation to the underlying.
- Performance: P&L including liquidation costs of the terminal position, P&L from longs (bias check), annualised
  time-weighted return, hit ratio, average return from hits, average return from misses.
- Risk: drawdown = largest loss between consecutive high-water marks; time under water = time from a high-water mark until
  the previous maximum is regained (an unrecovered drawdown counts to the end of the sample); report the 95th
  percentile of each.
- Concentration: `h = (sum w^2 - 1/n) / (1 - 1/n)`, `w` = same-sign bet returns / their sum; 0 = uniform, 1 = one
  bet. Report h+ (positive returns), h- (negative returns) and h of bets over time. Target shape: high Sharpe, many
  bets, high hit ratio, low h+ and h- (no fat tails), low h in time (bets not clustered).
- Disclosure: number of trials behind the result; bets, not trades, as independent opportunities. A backtest is for
  discarding bad models, not improving them. Details: [bt-performance-attribution](../bt-performance-attribution/SKILL.md).

## Worked examples
1. **Desk columns reproduced** (GS Global Rates Best Trade Report, 30 Sep 2026, payer view). CHF 1y1y/2y1y: 3m carry 7.7 bp,
   vol 12.3 -> Sharpe = 2 x 7.7 / 12.3 = 1.25 (printed 1.26). JPY 1y1y/2y1y/3y1y: 2 x 4.0 / 6.6 = 1.21 (printed 1.20).
   EUR 1y1y: 2w change 9.1 bp, vol 45.6 -> trend = 13 x 9.1 / 45.6 = 2.59 (printed 2.61). USD 10y5y/15y5y/20y5y:
   Sharpe 1.20, R 0.26 -> Carry/R = 1.20 / 1.26 = 0.95 (printed 0.95). USD outrights have R about 0.85-1.0, so Carry/R is near 0.
2. **Why combined lists drop a row.** CAD 1y1y/2y1y/3y1y has the highest carry (Sharpe 1.47: 3m carry 11.3 bp on vol 15.2, z 0.86,
   trend 8.85) but is excluded from the combined list because entry and trend conflict; the top 3-factor global pick
   is the EUR 5y5y/10y5y/15y5y fly (score 2.69: carry 0.04, entry -0.95, trend 14.10, R -0.05), i.e. a score earned almost
   entirely from entry and trend, with carry near zero (GS Global Rates Best Trade Report, 30 Sep 2026).
3. **Short sd window inflates a mover.** EUR 10y swap spread +4 bp in a week scored 5.7 sd, which implies a 1w-change sd of
   4 / 5.7 = 0.7 bp from a 62-day window; USD 10y20y +32 bp scored 4.6 sd (GS Market Movers, 30 Sep 2026). A reader sees
   both as "significant"; the footer must show the window so the 4 bp is not read as a regime event.
4. **Ratio column without a floor.** Basis 9 bp on an I-spread of 77 bp = 12% (printed 12%), but a near-zero I-spread printed
   1,206% for one issuer and -424% for another; rank on bp or apply the floor first (JPM Credit Research, HG CDS Bond
   Basis Report, 22 Oct 2025). Credit example used only for layout; the same trap hits any "spread / small spread" column.
5. **ASW definition gap.** For one zero-coupon strip (May 2050) matched-maturity swap spread 69.9 bp vs proceeds ASW 122.6 bp; the
   1.25% May 2050 bond showed 69.6 vs 91.6 (GS US Treasury Asset Swap Spreads, 25 Sep 2026). The ASW sign convention is
   undefined in the report: print both measures and the convention, do not pick one silently.
6. **Cash RV flags.** In the same screen the 7y futures CTD showed fitted-curve spread -0.8 bp (z -2.2, flagged rich) and
   the 20y-future CTD +2.1 bp (z 2.9, flagged cheap) with invoice spreads 35.6 and 68.3 bp; red/green at |z| >= 2 sends the
   row to the fitted-curve and direct-spread work, it does not make it a trade (GS, 25 Sep 2026).
7. **Dashboard reading.** Customised-risk summary (Darbyshire, Pricing and Trading Interest Rate Derivatives, 3rd ed.,
   2022, Example 16.9): total P&L 175; 7s8s9s earned 69, i.e. 69 / 175 = 39% of the day from a sub-micro bucket, so a
   candidate to close and bank. Of the VaR-minimising single trades (Example 16.12) only one is valid at a time; trading
   about 50% of each suggestion and re-running cut the book's risk measure c from 259 to 175 (book: 33%; 175 / 259 gives 32% from rounded inputs; the two 175s are unrelated, P&L vs risk).

## Signals & interpretation
- |z| >= 2 on any window = look; |z| >= 2 on 3m AND 1y AND the direct spread (not only a fitted spread) = work on it.
  A z of the 5y window is sensitive to the 5y regime; a best-entry receiver can keep trending against you, so read
  Trend beside Entry.
- Normalised move >= 3 sd = flag; first check the sd window and the quiet-regime effect (example 3).
- Carry/R far below Sharpe = the carry is duration in disguise (many curve trades have R vs 10y of -0.5 to -0.9).
- A row high on entry and trend with carry about 0 is a valid screen result but not a carry trade; label it.
- Fitted or model spreads are not quoted levels: show the direct yield-spread z too.
- Positioning panels: read net DV01 and its 5y percentile, not contract counts; concentration (share of open interest held
  by the 4 and 8 largest traders, 1y window) and changes in 5y-sd units give context. Asset-manager length mirrored by
  leveraged shorts is the basis-trade signature (reader's interpretation, not a claim of the source).
- Funding panels: separate funding-demand gauges (repo-vs-policy-rate spreads) from reserve-scarcity gauges (fed funds vs
  policy floor, reserves/assets); repo can be stressed while fed funds is calm. Details in references.

## Pitfalls
- Carry and roll are static (unchanged curve); 3m vol and the 5y z use different windows, so a high Sharpe with an
  extreme z can still be a regime move. Show the aged chart beside the number.
- Scores compared across pools or dates: the plane is refit daily. Keep the pool label with every score.
- Chart values drawn but not tabulated: a chart without the underlying table cannot be audited; export the rows with the
  PNG (`screen.csv`).
- Mixed snaps or non-synchronous closes inside one fly: a 10y read at a different time from the 2y fakes a move.
- Level charts in a cutting/hiking cycle mislead: plot spreads to the policy rate or to the floor/ceiling, not levels.
- Month-end and quarter-end funding spikes: filter or flag them before z-scoring funding spreads; a quarter-end spike alone is
  not a scarcity signal.
- A Spearman R on 3-day overlapping changes over 63 days has about 20 independent points: treat |R| differences below
  about 0.2 as noise.
- Percentile windows differ by panel (positioning 5y, concentration 1y): print the window in every cell header.
- Past-performance and "desk may hold positions inconsistent with its views" disclaimers belong on anything reproduced
  from desk material; keep source and date on every exhibit.
- PCA displays: eigenvector signs are arbitrary (fix them: PC1 sum > 0, PC2 steepening, PC3 belly up); loadings change
  with sample and instrument set; use changes, not levels, as covariance input.
- A flat parameter heat-map in a backtest (stops, targets) is the overfitting warning, not a result to show as evidence.

## G10 notes
- USD: swap spread = swap - Treasury (negative); funding plumbing monitors, UST cash screen and DV01 positioning panels are
  US-specific. EUR: ASW = bond - swap; Bund ASW and Italy-Germany spread belong in the movers grid. GBP, JPY, CAD, AUD,
  NZD, CHF, SEK, NOK: same column set; forward universes are shorter for SEK and NOK (about out to 1y10y and 5y5y) and vol
  scales differ (printed 3m vol: EUR 1y1y 45.6 vs JPY 1y1y 25.8 vs CHF 1y1y/2y1y 12.3), so compare across currencies
  on Sharpe or normalised move, not on bp. Low-rate markets (JPY, CHF): z and percentile are meaningful, "% of level" is not.
- Positioning panels from US futures reports do not exist for other markets in the canonical `positioning` table
  unless the adapter provides exchange or survey data: say "not available" rather than leaving a blank.

## Output
Return, in this order: (1) the screen table (CSV rows with the column set above, plus pool/date/snap/window columns),
(2) ranked lists, (3) PNG charts named `<kind>_<structure>.png`, (4) a one-pager per shortlisted idea, (5) a footer block
with conventions, formulas, windows and data gaps. For a tearsheet, return the section 8 fields with the number of
trials. State anything not displayed because data was missing.

## Scripts
- [`scripts/rv_charts.py`](scripts/rv_charts.py): numbers and charts for the sections above: structures (`spread`, `fly`,
  `trader_name`), screen columns (`screen`, `rolling_z`, `range_stats`, `normalised_move`, `sparkline`, `z_matrix`),
  desk definitions (`ex_ante_sharpe`, `trend`, `spearman_r`, `carry_over_r`), tearsheet fields (`max_drawdown`,
  `time_under_water`, `hhi_concentration`, `bet_stats`), `pca_loadings`, `density_grid`, and the PNG charts (matplotlib
  optional). CLI: `python scripts/rv_charts.py --curve-par curve_par.csv --curve-id USD-SOFR --legs 2Y,5Y,10Y --out out`
  writes `screen.csv`, `z_matrix.csv` and PNGs. `--selftest` checks known-answer cases (printed desk numbers, planted PCA
  factors, drawdown and concentration arithmetic, canonical panel units) and exits non-zero on failure.

## Related skills
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): produces the ranked universe this skill formats
- [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md): consumes the one-pager and charts
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md): z, percentile and robust-statistic choices
- [rv-composite-scoring](../rv-composite-scoring/SKILL.md): the agent's own ranking score, in place of the desk plane score
- [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md): PCA loadings and residuals shown in the charts
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): tearsheet statistics and P&L explain
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): positioning panel content
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): funding spread meaning behind the monitors
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): matched-maturity vs proceeds ASW definitions
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): regression direction and hedge ratios behind the scatters
- [curve-butterflies](../curve-butterflies/SKILL.md): DV01-neutral fly weights the screen level does not show
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): trial counts and overfitting behind tearsheet numbers
- [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md): standing risk and P&L dashboards for live trades
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): snap times, holidays and stale data
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical input tables

## References
- Goldman Sachs FICC and Equities (IRP Market Strats) - Global Rates Best Trade Report, 30 Sep 2026: scatter, score, column definitions (Sharpe, trend, R, Carry/R), report layout, top picks.
- Goldman Sachs FICC and Equities - GS Market Movers: For Rates and Cross-Asset, 30 Sep 2026: normalised-move grid, horizons, universe.
- Goldman Sachs FICC and Equities (Macro Sales & Trading Strats) - US Treasury Asset Swap Spreads / RV Report, 25 Sep 2026: cash RV columns, z flags, ASW definition gap.
- Goldman Sachs FICC and Equities (Rates Sales and Trading Strats) - UST Futures Positioning Report, 2 Oct 2026: DV01 positioning panels, windows, concentration.
- RiskVal Financial Solutions - RiskVal Overview 201: Cash and Futures, 12 Nov 2021: roll sheet, standard RV column set, expected return and MR frequency.
- Marcos Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018), Ch. 14: backtest statistics, drawdown, time under water, HHI concentration.
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives, 3rd ed. (Aitch & Dee, 2022), Ch. 14-16: trader risk dashboard, VaR and PCA displays.
- Stephen Aikin - STIR Futures: Trading Euribor and Eurodollar Futures, 2nd ed. (Harriman House, 2012): price-format inter-contract spread display.
- Alexander Duering - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): density-augmented scatter.
- J.P. Morgan Credit Research - HG CDS Bond Basis Report (Eric Beinstein), 22 Oct 2025: screen layout, basis sign legend, percent-of-spread pitfall, aggregation hierarchy.
- J.P. Morgan - EM US$ Sovereign Bond-CDS Basis Report (Poojary, Chawla), 22 Oct 2025: country-page layout with current vs 1m overlays.
- BofA Global Research - Technicals Explained: In 2025, get to know technical strategy (Ciana, Suttmeier), 14 Jan 2025: relative-ratio charts lead absolute ones.
- Conks (Monetary Mechanics / Plumbing Notes, Substack), Money Market Updates, Aug 2024 - May 2026: funding monitor definitions and panels (detail in references/panels.md).
