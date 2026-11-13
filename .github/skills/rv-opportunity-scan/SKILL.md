---
name: rv-opportunity-scan
description: End-to-end G10 rates relative-value (RV) opportunity scan, a workflow that orchestrates the method skills. Takes markets, instruments, horizon and constraints; checks the data; routes each question type (curve spreads and flies, PCA residuals, forward grid, bond rich/cheap, swap spreads/ASW, cross-market govies and EGB spreads, futures basis/CTD/roll, STIR and policy pricing, xccy basis, vol, inflation, flows) to the right skill or script; computes one standard metric set per candidate (level, z at 3m/1y/3y, percentile, half-life, 3m carry+roll, carry/vol, PCA residual, hit-rate, expected gain); filters on liquidity, half-life vs horizon and costs; ranks, stresses and vets down to a shortlist. Bundles scripts/scan.py, a curve spread and fly scanner. Use when asked to find RV trades or opportunities, "what looks rich/cheap", scan or screen the curve, trade radar, best trades, scorecard, RV monitor, dislocations, or any broad request across USD EUR GBP JPY CAD AUD NZD CHF SEK NOK without a named structure.
argument-hint: "<markets / instruments / horizon / constraints>"
---

# RV opportunity scan

A scan is a funnel, not a model: universe -> data check -> screens -> one standard metric set -> filters -> composite rank
-> stress -> devil's advocate -> write-up. Research desks run the same funnel as a trade radar (Citi), a best-trade scorecard
(Goldman Sachs), an anomaly grid (Goldman Sachs Market Movers) or an RV monitor (Nordea, RiskVal); see
[desk-screens](references/desk-screens.md). This skill fixes the order of the steps, the common metric definitions that make
screens comparable, and which method skill owns each detail. It never invents data and never promotes a screen hit to a
trade: the most attractive rows on a desk chart are "not necessarily trades that we would recommend" (Citi, Rates Vol Lab, 12 Jun 2023).

## When to use
- "Find me RV in USD and EUR", "what is cheap on the curve", "scan 2s5s10s-type flies", "best trades", "trade radar", "screen G10".
- A broad request with no named structure, or several markets and instruments at once.
- Refreshing a standing watch list, or checking whether an idea from a note still screens.
Not for: pricing one named structure (go to its method skill), or monitoring an open trade ([rv-trade-monitoring](../rv-trade-monitoring/SKILL.md)).

## Inputs (data-agnostic)
Argument: `<markets / instruments / horizon / constraints>`, e.g. `USD EUR curves+flies, 3m, DV01 >= 50k, no options`.
Parse into a scope card and state it back before computing:

| Field | Default if absent | Note |
|---|---|---|
| Markets | the user's named currencies; else USD EUR GBP | add JPY CAD AUD NZD CHF SEK NOK only on request (smaller, thinner universes) |
| Instruments | curve spreads and flies first | then add what the question needs (decision table below) |
| Horizon h | 3 months = 63 trading days | carry, vol, hit-rate and expected gain all use the SAME h |
| Lookbacks | z at 63d, 252d, 756d; primary 252d | desks use 1y/3y/since 2000 (Citi), 5y (GS), 50d/200d (Nordea), 250d (BofA) |
| Constraints | min liquidity, max structures, no options, no illiquid legs, risk limit | carried into the filters |

Canonical tables ([data-contract-and-adapters](../data-contract-and-adapters/SKILL.md)): `curve_par` (swap/OIS and fitted govt
benchmark curves), `bond_quotes`, `swap_spreads`, `fut_quotes`, `stir_quotes`, `vol_surface`, `basis_swaps`, `fx_rates`,
`infl_swaps`, `positioning`. History: at least 3y of daily data on one snap time for z/half-life (hard minimum 100 observations).
Missing table: ask the user or the data adapter for it; say which screens were skipped. Never fill a gap with a guess.

## Conventions (state in every output)
- bp throughout. Curve A-B = longer - shorter (2s10s = 10y - 2y). Fly 2s5s10s = 2 x 5y - 2y - 10y (high = belly cheap/high yield).
- **side = +1 receive-type**: P&L rises when the structure level FALLS (receive fixed, long bond, receive the belly, flattener = receive
  long/pay short). Default side = sign(z): fade the deviation. A momentum idea sets side explicitly. These are the conventions of
  [rv-composite-scoring](../rv-composite-scoring/SKILL.md), so scan output feeds it unchanged.
- z > 0 = level high vs its own window = receive-type cheap. Some desks sign z by trade direction (Nordea) or quote carry from the payer's
  view (Goldman: "Receive" quadrant = carry < 0, z > 0); convert before mixing.
- `carry_bp` is the 3m carry + roll of the side = +1 position, positive = earns. A side = -1 trade earns minus that.
- Swap-spread sign: US swap minus Treasury; EGB ASW bond minus swap (positive = bond cheap). Vol in normal (bp) terms.

## Method

### Step 0. Scope
Write the scope card (table above). Pick the universe from the grid in step 2. A standard daily grid (Goldman Sachs, Market Movers,
30 Sep 2026): outrights 2y 5y 10y 30y; forwards 2y3y 5y5y 10y20y; curves 2s5s 2s10s 2s30s 5s10s 5s30s 10s30s; forward spreads; flies
2s5s10s 2s10s30s 5s10s30s; 10y vs Germany; 10y breakeven; 10y real yield; 10y swap spread / ASW; 2y xccy basis. Do not enumerate
unquoted forward cross-products: they swamp the ranking by count.

### Step 1. Data check (stop here if it fails)
Run [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) validation and
[data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md) checks. Pass criteria:

| Check | Pass | Else |
|---|---|---|
| Same snap time on all legs of a structure | yes | do not mix snaps; re-snap or drop |
| Last date | within 1 business day of the as-of date | flag `stale`; never forward-fill |
| History | >= 756 obs for z_756, >= 252 for z_252, >= 100 minimum | flag `thin_history`, compute only the lookbacks that fit |
| Regime | ZLB years (USD fed funds <= 50bp) and pre-2016 EUR excluded from vol-vs-rates fits | shorten the window, say so |
| Constant maturity | half-life, PCA and carry use constant-maturity series (par curve or fitted curve), not rolling bonds | build via [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md) |
| Outliers | none > 5 robust sd in one day without a news reason | check the price source first: data errors look like opportunities |

### Step 2. Screens: route the question to the right skill
Run every row the scope needs; each returns candidates in the SAME metric set (step 3). Script names are the ones in each skill's
`Scripts` section.

| Question type | Screen | Skill (script) |
|---|---|---|
| Curve spreads and flies, spot | all pairs and triples of a tenor set | this skill (`scripts/scan.py`); weights in [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md) (`curve_beta.py`), [curve-butterflies](../curve-butterflies/SKILL.md) (`fly_weights.py`) |
| Is it curve RV or factor exposure? | PCA residual of spread/fly vs level-slope-curvature | [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md) (`pca_curve.py screen`) |
| Forward space: 1y1y ... 5y5y, 10y10y/15y15y, kinks | forward grid, forward-minus-spot, forward-curve pairs, BE/RV | [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md) (`forward_grid.py`), [vol-convexity-and-long-end](../vol-convexity-and-long-end/SKILL.md) (`convexity_screen.py`) |
| Which bond is rich/cheap; switches | residual to a fitted curve, z of residual | [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md) (`fit_curve.py`) |
| Govies vs swaps | swap-spread / ASW level z, spread-curve, fitted ASW spline | [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md) (`asw.py`); drivers in [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md) (`balance_sheet_hurdles.py`) |
| UST vs Bund, EGB vs Bund, gilts, JGB, ACGB, NZGB | cross-market spread z, beta-weighted, FX-hedged carry | [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md) (`cross_market_spreads.py`); credit read in [spread-sovereign-cds-and-basis](../spread-sovereign-cds-and-basis/SKILL.md) (`sov_cds_basis.py`) |
| Futures basis, CTD, delivery options, roll, invoice spread | net basis/implied repo, CTD scenarios, calendar-roll fair value, invoice spread | [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md) (`basis.py`), [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md) (`ctd_scenarios.py`), [fut-calendar-roll](../fut-calendar-roll/SKILL.md) (`roll_fv.py`), [fut-invoice-spreads](../fut-invoice-spreads/SKILL.md) (`invoice_spread.py`) |
| STIR strip shape, packs, kinks | spreads, flies, strip fit residual, roll | [stir-futures-rv](../stir-futures-rv/SKILL.md) (`stir_structures.py`), [stir-convexity-adjustment](../stir-convexity-adjustment/SKILL.md) (`convexity_adj.py`) |
| Policy pricing vs view | meeting-by-meeting path, probabilities, cuts/hikes priced | [stir-policy-pricing-whats-priced-in](../stir-policy-pricing-whats-priced-in/SKILL.md) (`meeting_path.py`); reaction function in [macro-central-bank-reaction-functions](../macro-central-bank-reaction-functions/SKILL.md) (`reaction_rules.py`) |
| Bills, repo, funding | bill-OIS, SOFR-FF, specialness, reserves | [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md) (`bill_yields.py`), [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md) (`repo_funding_math.py`), [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md) (`reserve_monitor.py`) |
| Tenor/index/CCP basis | basis z, basis DV01 | [spread-tenor-and-index-basis](../spread-tenor-and-index-basis/SKILL.md) (`basis_tools.py`), [spread-ccp-basis](../spread-ccp-basis/SKILL.md) (`ccp_basis.py`) |
| Cross-currency | FX-implied rate vs OIS, hedged-return comparison | [xccy-basis](../xccy-basis/SKILL.md) (`xccy_basis.py`) |
| Vol | implied vs realised, grid and surface PCA residuals, skew, correlation, supply-driven vega, conditional curve trades | [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md) (`bachelier.py`), [vol-skew-and-tail-hedging](../vol-skew-and-tail-hedging/SKILL.md) (`skew_tools.py`), [vol-correlation-and-curve-options](../vol-correlation-and-curve-options/SKILL.md) (`implied_corr.py`), [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md) (`vega_supply.py`), [curve-conditional-trades](../curve-conditional-trades/SKILL.md) (`conditional_curve.py`) |
| Inflation | breakeven and real-yield z, 5y5y, seasonality, linker carry | [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md) (`infl_tools.py`) |
| Is the move fundamental? | macro-factor fair value residual | [macro-fair-value-models](../macro-fair-value-models/SKILL.md) (`fair_value.py`) |
| Flows, positioning, supply | CFTC/survey z, structural ALM demand, auctions, MBS convexity | [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md) (`flow_positioning.py`), [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md) (`alm_hedge_flow.py`), [flow-mbs-convexity-hedging](../flow-mbs-convexity-hedging/SKILL.md), [bond-supply-and-cashflow-trading](../bond-supply-and-cashflow-trading/SKILL.md) (`supply_event_grid.py`) |

Flows and positioning are overlays, not screens: they decide whether to act on a screen hit (step 6). The division of labour from the practitioner
literature: statistical models find rich/cheap, financial models explain why and judge whether it corrects, and statistical models again set
the hedge ratio and holding horizon (Huggins and Schaller, 2024).

### Step 3. Standard metric set (every candidate, every screen, same horizon h)
`scripts/scan.py` computes all of this for curves and flies; other screens must return the same columns. Formulas, h in trading days,
h_y = h/252, L = structure level in bp:

| Metric | Definition | Default and reason |
|---|---|---|
| `level_bp` | L = sum(rho_i x y_i); curve (-1, +1), fly (-1, +2, -1) in DV01 terms | 50/50 DV01 fly is exactly 2b - f - k in yield space; per-leg notionals of the trade to execute come out as `legs_trade` (+ receive fixed, - pay fixed, already multiplied by `side`; belly = 2, wings sized by the annuity ratio, approximate) |
| `z_63`, `z_252`, `z_756` | (L - mean) / std over the trailing window incl. today, ddof 1 | 3m, 1y, 3y. State the lookback; report the one that disagrees. A z with no reversion speed "tells us almost nothing" (Huggins and Schaller, 2024) |
| `pctile` | share of the last 756 obs <= L | rank-based, robust to fat tails; high correlation with z, never add both to a score |
| `halflife_days`, `df_t` | AR(1) on the 756 obs ending YESTERDAY (a fresh jump must not set its own reversion speed): L_t = a + phi L_{t-1}; hl = ln2 / -ln(phi), 0 < phi < 1, else NaN. `df_t` = Dickey-Fuller t of (phi - 1); null = unit root | NaN or > 180d = `no_reversion`; `df_t` > -2.86 (5% DF value) = `unit_root` flag: a random walk cannot be rejected. Simulated on 756 obs, a pure random walk shows hl <= 90d 36% of the time (<= 180d 67%), so half-life alone is weak evidence; the DF flag removes about 90% of such false passes but has low power at hl 60-90d (25-50%), hence a flag, not a gate. BofA swap-spread PCA residuals: about 20 days |
| `carry_bp` | 3m carry + roll of the receive-type position, in rate-equivalent bp | per receiver leg: (y - r) x h_y / A + (y - y(T - h_y)); A annuity proxy; sum with DV01 weights. Screening approximation: exact numbers come from [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md) |
| `vol_bp` | std of daily change of L over 252 obs x sqrt(h) | same horizon as carry; use the h-day vol, not annual |
| `carry_vol`, `carry_vol_ann` | side x carry_bp / vol_bp; annual = that / sqrt(h_y) (x2 for 3m) | GS "ex-ante Sharpe" = 3m carry/vol annualised: USD 10y5y/15y5y/20y5y 1.8bp on 3.0 gives 2 x 1.8/3.0 = 1.2 |
| `pca_resid_bp`, `pca_z` | actual - rank-3 reconstruction of the demeaned level panel, summed with the weights; z over the same panel | positive = high vs factors = receive-type cheap. RV only, never a level view. Needs >= 5 tenors |
| `er_bp`, `er_vol` | OU gain over h: side x (L - mean)(1 - e^{-k h}) + side x carry; k = ln2/hl per obs | no half-life = no reversion credit; constant-vol OU overstates the gain at extreme entries, so distrust er at |z| > 3 (Huggins and Schaller). er/vol is the cross-instrument expected Sharpe (Huggins and Schaller; Citi, Holistic approach to convexity, Jun 2022) |
| `hit_frac` | share of h-day windows in the last 756 obs where -side x (L_{t+h} - L_t) + side x carry > 0 | windows overlap: effective n about 756/63 = 12. Compare Nordea's "probability in the money after 1y" |

Extra vetting columns when available: R = correlation of dL with the outright rate change (Carry/R = carry-vol / (1 + |R|), Goldman),
breakeven/realised-vol for convexity trades (step 4), liquidity (DV01 executable), cost.

### Step 4. Filters (reject, do not downweight)
`scan.py` gates only items 1-3 (`--min-abs-z`, `--max-hl`, `--cost-bp`) and FLAGS what else it can compute (`carry_against`, `z_disagree`,
`unit_root`, `z>4`, `thin_history`, `stale`); items 4-9 are vetting steps for you. A row that is flagged but still `passed` needs a stated reason:
1. **Entry**: |z_252| >= 1.5 (the 3m z flag is +/-2 in Goldman's UST screen; 1.5 keeps the funnel wide before costs). A candidate where
   z_63, z_252, z_756 do not share a sign is a lookback artefact: keep only if you can say why (scan.py does not gate on this: read the three columns).
2. **Reversion fits the horizon**: half-life <= 90d (one quarter); > 180d = a macro view, not RV. A `unit_root` flag means the half-life is not
   statistically distinguishable from a random walk: keep only with an economic anchor (an arbitrage- or hedging-linked spread), else watch-list.
3. **Costs**: er_bp >= 2 x round-trip cost (default cost 0.5bp of level per structure, overridden by
   [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md)). Over-estimate costs (Narang).
4. **Liquidity and size**: executable DV01 >= 100k in DM rates (40k EM) and risk/reward >= 1.5:1 to the stop (Citi Radar criteria);
   thin legs (illiquid forwards, odd tenors, off-the-run bonds) are watch-list only: Citi left USD 15y5y/20y10y on a watch list at 1y z 4.2 for illiquidity (Liquidity, vega and convexity, Mar 2020).
5. **Carry sign test by convexity**: delta-hedged long-convexity packages (flatteners in forwards) tolerate negative carry if
   BE/RV < 1 (BE = the daily move whose convexity gain offsets the daily carry bleed, Citi 5 Dec 2019; second-order form s* = sqrt(2|carry_yr|/(252|gamma|)) with carry_yr the ANNUAL carry in bp (multiply the 3m `carry_bp` by 4) and gamma in bp per bp^2; RV = realised daily vol); short-convexity packages
   (forward steepeners) want BE/RV "meaningfully above 1". The sign of the rule flips with the position (Citi, 5 Dec 2019 and 12 Jun 2023).
6. **Directionality**: Goldman's Carry/R = Sharpe/(1 + |R|) is a mild penalty (|R| = 1 only halves a Sharpe), so also filter on |R| itself: USD outright
   forwards sit at R 0.85-1.0 (a rates view: hedge it or drop it), USD 10y5y/15y5y/20y5y at 0.26. Flag |R| > 0.5 (judgement threshold, not from a source).
7. **Factor test**: pca_z and z of opposite signs = `z_disagree`: the factors explain the move, probably a directional view in disguise. Likewise a
   plain z and value relative to rates can point opposite ways (Citi, Trading long-dated convexity, May 2019): check both.
8. **De-duplicate**: structures that share legs are one bet. Keep the best per belly tenor (flies) and per long leg (curves); with N
   tenors there are only N - 1 independent spreads, whatever the structure count (Grinold and Kahn: dependent signals masquerade as breadth).
9. **Multiple testing**: for iid z a screen of 84 structures at |z| >= 1.5 yields about 84 x 0.134 = 11 hits by chance (|z| >= 2: 4). Curve levels
   are persistent, so the real floor is higher: for a random walk the trailing-252d z exceeds 1.5 on about 33% of days and 2 on about 15% (simulation).
   20 tries give a 64% chance of at least one t >= 2 fluke (Grinold and Kahn). Require a reason or a second, independent screen, not just a z, and
   test the screen itself on random data (finding predictability there is the failure; Grinold and Kahn).

### Step 5. Rank
Hand the passed table to [rv-composite-scoring](../rv-composite-scoring/SKILL.md): `python scripts/scan.py ... --passed-only --out ranked.csv` then
`python ../rv-composite-scoring/scripts/score.py ranked.csv --mode composite` (columns `z`, `carry_bp`, `vol_bp`, `pctile`, `halflife_days`,
`hit_frac`, `side` match; the scorer's default weight on `hit_frac` is 0, use `--weights hit=...` to count it). `--passed-only` matters: without it the failed rows are scored too. The scorer writes its own `flags` column; the
scan's reasons stay in `scan_flags`, so keep both in the radar table. scan.py's own `j = carry_vol_ann + |z|` is the
Nordea J-score in the chosen direction, only a provisional sort key. Scores are refit rankings: never compare them across screens, dates or
currencies (Goldman: EUR 10y2y/12y3y/15y5y scores 2.64 in the EUR screen, 1.99 in the global one).
Check the weights against the naive alternatives (pure |z|, equal-weight) with [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md).

### Step 6. Vet the top 5-10 (the part a screen cannot do)
For each: (a) **why is it cheap?** supply, ALM, balance sheet, policy path, index/seasonal, position squeeze: run the relevant row of the
decision table and the flow skills ([flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md), [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md));
(b) **regime**: [quant-regime-detection](../quant-regime-detection/SKILL.md) gate; a 10y10y vol-rate beta flipped in 2025 (Citi, 5 Oct 2026);
(c) **timing**: wait for the event (Citi: wait for FOMC before entering a long-end steepener; hawkish outcomes cause knee-jerk bear flattening);
(d) **crowding**: steepeners were consensus (Nordea, Aug 2025); positioning can override valuation; (e) **decomposition**: a carry fly with positive
10s30s beta earns mostly curvature or vol decline (Nordea, Aug 2025): attribute before believing the thesis; (f) **hedge ratio and
weights**: DV01-neutral is directional if the legs have different betas, rebuild with [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md)
or PCA weights ("hedge against all factors of lower order than the one to which exposure is wanted", Huggins and Schaller).

### Step 7. Stress
[port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md) with the seven-shock curve template (Citi, Agency MBS Weekly,
21 Aug 2026) plus historical replays and PCA shocks:

Shock set: (1) forwards realised (the curve rolls to its forwards), then the four twists and two parallels:

| Shock | 2y and shorter | 5y | 10y and longer |
|---|---|---|---|
| Parallel +/-50bp | +/-50 | +/-50 | +/-50 |
| Bull steepener | -50 | -25 | 0 |
| Bull flattener | 0 | -25 | -50 |
| Bear steepener | 0 | +25 | +50 |
| Bear flattener | +50 | +25 | 0 |

Record P&L per shock and the loss at the stop. Read the twists in pairs: a curve RV should earn (or lose) on both flatteners or both steepeners, so a
sign flip between bull and bear flattener (same shape, opposite direction) is residual duration. A fly with its belly at 5y is exactly unchanged by
every shock in this set (2s5s10s under the bull steepener: 2 x (-25) - (-50) - 0 = 0), so add a curvature shock (belly +/-10bp, wings 0) or the PCA-3 shocks.
Size to the stop with [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md); portfolio overlap with
[port-portfolio-construction](../port-portfolio-construction/SKILL.md).

### Step 8. Devil's advocate, write-up, handoff
Each survivor goes through [rv-devils-advocate](../rv-devils-advocate/SKILL.md) (pre-mortem, kill criteria, closed-trade lessons) and then
[rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) (thesis, structure, weights, entry/target/stop, carry/roll, scenarios).
Execution: [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md). After entry: [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md).
To turn a research note into a screen row first: [rv-research-digest](../rv-research-digest/SKILL.md).

## Worked examples

### A. Synthetic run of `scripts/scan.py --demo` (illustrative, not market data)
Synthetic 1,000-day par curve (2y 3y 5y 7y 10y plus a 3M short rate), 7y bumped +12bp on the last date, 3m horizon:
```
python scripts/scan.py --demo --top 6
# asof 2026-11-10  horizon 63d  z_ref 252d  structures 20  passed 12
rank structure level_bp  z_63    z  z_756 pca_z pctile halflife  df_t carry_bp vol_bp  er_bp hit_frac side scan_flags
   1   5Y7Y10Y    26.26  5.91 4.79   5.14  5.77   1.00    25.49 -3.20     4.65  14.89  26.04     0.77    1 z>4
   2   3Y7Y10Y    39.38  5.43 5.05   4.47  5.88   1.00    30.42 -2.89     2.41  16.67  27.09     0.67    1 z>4
   3   2Y7Y10Y    50.69  4.16 3.95   3.76  5.73   1.00    32.21 -2.76    -1.41  19.53  26.94     0.51    1 unit_root carry_against
   4     7Y10Y    -7.45 -6.05 -2.66  -3.13 -5.87   0.00    31.42 -2.91    -4.11   9.32  13.07     0.79   -1
   5    2Y3Y7Y   -20.61 -4.05 -2.59  -1.93 -3.41   0.05    33.15 -2.88    -2.11  11.87  12.84     0.63   -1
   6      5Y7Y    18.82  4.63  2.66   2.53  5.55   1.00    50.04 -2.29     0.54   8.59   8.78     0.56    1 unit_root
```
Reading: the planted 7y shows up in every structure that contains it: as the belly of the flies (side +1: receive the belly), and as the
short leg of the 7y10y curve (level low, side -1: receive 7y, pay 10y; `legs_trade` 7Y:+1.37, 10Y:-1.00). The scan cannot tell a real dislocation from a
data error, so step 1 matters first. All the 7y-belly flies carry `pca_z` > 5 with the same sign as z: the factors do not explain it. Row 3 has negative
carry (-1.41bp) but expected gain 26.9bp from reversion; `carry_against` is a reason to look, not to drop, whereas its `unit_root` flag (df_t -2.76 > -2.86)
says the reversion speed itself is not proven. Row 1 is cleanest: carry +4.65bp, hit 0.77, df_t -3.20. Rows 1-6 ALL contain the 7y, so they are ONE bet:
keep row 1, then step 6 asks why the 7y moved. 10 of the 20 structures contain the 7y, which is why 12 of 20 pass: the shared-leg effect of step 4
item 8, not 12 ideas. (With all seven synthetic tenors 2Y-30Y the same demo has 56 structures and 20 pass; a real 8-tenor grid has 84.)

### B. Long-convexity flattener screen (Citi, North America Rates Trade Idea, 5 Dec 2019; USD, close 4 Dec 2019)
Columns: curve bp | 1y z | 3y z | z since 2000 | 1y carry | daily BE | BE/RV.
| Pair | Curve | 1y z | 3y z | z2000 | Carry | BE | BE/RV |
|---|---|---|---|---|---|---|---|
| 10y10y/15y15y | -6.77 | 0.55 | 1.38 | 1.08 | -3.19 | 4.14 | 0.98 |
| 15y5y/20y10y | -12.54 | -0.91 | 0.70 | 0.64 | -2.09 | 3.33 | 0.80 |
| 15y10y/25y10y | -15.65 | -0.54 | 0.58 | 0.25 | -0.86 | 1.84 | 0.45 |
| 20y5y/25y5y | -7.02 | -2.22 | 0.02 | -0.33 | 0.43 | 0.00 | 0.00 |
Realised 1y vol about 4.2bp/day, so BE/RV = 3.33/4.15 = 0.80 for 15y5y/20y10y (matches). The trade ($50k DV01 15y5y/20y10y entered at -11.8bp,
delta-hedged every 20bp) booked about +$155k net of costs by 5 Dec 2019 (curve -12.5bp). The note's exit rule is on the screen metric, not on
the thesis: close when carry deteriorates and BE/RV rises toward 1 even if the curve view holds (here carry -2.09bp/yr, BE/RV 0.80). A row with
positive carry (20y5y/25y5y: +0.43) has BE 0: no breakeven is needed because there is no carry bleed to pay for.
Same date, GBP 15y10y/25y10y: carry +0.47, z since 2000 2.05, BE 0: better value and better carry than USD, put on the watch list.

### C. Forward steepener frontier (Citi, Rates Vol Lab, 12 Jun 2023; USD, close 8-9 Jun 2023): the sign flips
| Steepener | Curve | 3y z | z2000 | 1y carry | BE | RV | BE/RV |
|---|---|---|---|---|---|---|---|
| 10y10y/20y5y | -62.4 | -0.91 | -1.47 | 10.31 | 7.22 | 5.24 | 1.38 |
| 10y10y/15y15y | -51.5 | -0.91 | -2.07 | 6.89 | 6.18 | 5.30 | 1.17 |
| 10y10y/25y10y | -105.6 | -1.04 | -2.56 | 6.04 | 3.97 | 4.66 | 0.85 |
| 15y5y/25y10y | -94.1 | -1.11 | -2.58 | 1.66 | 2.29 | 4.66 | 0.49 |
Short-convexity steepeners are paid carry, so the filter is BE/RV above 1 (carry more than covers realised moves). The deepest z rows
(25y10y legs, z2000 -2.6) have the lowest BE/RV: best entry, worst carry, the note's own warning that "the steepeners with the most attractive carry usually have the worst entry point".
The note picked the efficient frontier with BE/RV above 1: 10y10y/15y15y and 10y10y/20y5y (the latter preferred on 3y z), and said to wait for
FOMC. Applying the flattener rule (low BE/RV good) here would invert the ranking: do not reuse a filter across position types.

### D. Nordea EUR monitor (EUR Rates Flash, 23 May 2019): J-score reading
| Point | Rate % | 1y C&R bp | Cvx bp | C&R/vol | Z | J = c + z | ITM 1y/3y/5y/10y % |
|---|---|---|---|---|---|---|---|
| 1y1y | -0.228 | 3.4 | 0.1 | 0.18 | -1.13 | -0.95 | 74/59/35/18 |
| 4y1y | 0.303 | 20.9 | 1.4 | 0.43 | -0.76 | -0.33 | 26/33/28/14 |
| 15y5y | 1.532 | -2.6 | 4.9 | 0.04 | -0.62 | -0.58 | 1/15/16/8 |
All twelve points have J < 0 (receivers unattractive: carry/vol 0.03-0.43 does not offset z of -0.6 to -1.1), the PCA residuals are at most
+1.1bp ("very moderate"), so the monitor says do not receive; the published idea was to pay 10/20/30y belly. The ITM column makes the same point:
on the 1y window only 1% of history had receivers on 15y5y in the money (15% on the 3y window). Note value of convexity grows with tenor (0.1bp at 1y1y to 7.6bp at 30y10y),
so a carry/vol screen that leaves it out understates long forwards.

### E. Bond-level Treasury screen (Goldman Sachs, US Treasury Relative Value, 25 Sep 2026) and an ASW definition trap
Sign: here ASW = bond yield minus swap rate (positive = bond cheap), the opposite sign to the US swap-spread convention (swap minus Treasury) in the
conventions above. Flag rule |3m z| >= 2 on matched-maturity SOFR ASW and on the residual to a fitted curve. 7y CTD 4.5% Aug-2033: MMS 33.8bp, fitted -0.8bp (z -2.2, rich);
20y CTD 4.875% Aug-2045: fitted +2.1bp (z 2.9, cheap). Same note: P-STRIP May-2050 ASW 69.9bp matched-maturity vs 122.6bp proceeds: state the ASW
flavour or the number is meaningless for low-price bonds. Confirm a fitted residual with the quoted spread z (RiskVal: fitted-curve spread 2.7 SD cheap,
direct yield spread 1.8 SD cheap, so the note trades the yield spread because the fitted spread is theoretical).

### F. Anomaly grid trap (Goldman Sachs, Market Movers, 30 Sep 2026)
Normalised move = change / std of same-horizon changes; 1w uses 62 days, 1m 252. EUR 10y swap spread +4bp printed 5.7 sd, because the 62-day window was
quiet; USD 10y20y +32bp was 4.6 sd. Always show the bp move beside the sd move and the window, and re-run on a longer window before calling it an anomaly.

More desk templates, the Grinold-Kahn calibration table and the dislocation-indicator back-test: [desk-screens](references/desk-screens.md).
Per-market universes, vol scales and regime exclusions: [g10-screen-notes](references/g10-screen-notes.md).

## Signals & interpretation
- Strong candidate = |z| >= 1.5 on at least two lookbacks AND PCA residual of the same sign AND half-life <= 90d with no `unit_root` flag AND er_bp >= 2 x cost AND an
  identified reason it should revert. Four of five is a watch-list item.
- High z + positive carry-vol + short half-life + low directionality: classic RV. High z with no half-life: trend or regime change, not RV.
- Carry-vol above about 1.0 annualised is a good screen row (GS best rows 1.2-1.5); above 2 on small carry and tiny vol is usually a
  low-vol long-end spread: check bp carry (1.8bp) and cost before believing it.
- Expected-return decomposition (Salomon Brothers, Ilmanen, Nov 1995): carry + roll + convexity + view + local rich/cheap + financing; judge
  a price chart only after splitting delta, carry and convexity ("historical charts are MISLEADING, especially when there is a structural convexity bias", Citi, Jun 2022).
- Conflict between signals is information: the Goldman screen drops CAD 1y1y/2y1y/3y1y (top carry, rich entry, adverse trend) by construction.
- A screen that flags a lot is a weak screen: expect at least 13% of structures at |z| >= 1.5 by chance alone (iid floor; about 33% for random-walk-like levels).

## Pitfalls
- **Window artefacts**: 62-day windows inflate sd scores in low-vol regimes; a 5y window across a hiking cycle measures the cycle. Report two lookbacks.
- **PCA and fitted-curve RV is relative only**, never a level view; PCA in-sample residuals look better than they trade (the fit sees today).
  Re-run walk-forward in [bt-backtest-design](../bt-backtest-design/SKILL.md) before sizing on residual z.
- **Pure mean reversion is crowded and not arbitrage**: "a small dislocation might be a harbinger of bigger things" (Düring, 2021); repo squeezes
  can intensify before reverting. Ask why it is rich/cheap first.
- **Back-test hygiene**: BofA's dislocation back-tests exclude costs, carry and stops; at low thresholds the hit rates are inflated and expanding windows adapt slowly.
- **Static carry assumes an unchanged curve**; a high score can come from entry and trend with tiny carry (Goldman).
- **Largest signals come late or at dislocations** (adverse selection): cap or winsorise extreme signals (Narang); this skill flags |z| > 4 for review rather than capping. IC above 0.20 or IR far above 2 means an error (Grinold and Kahn).
- **Illiquid structure on a good screen** (USD 15y5y/20y10y, Mar 2020, VA hedging concentrated in the 20y): watch-list, not a trade.
- **Convexity or vol model dependence**: convexity adjustments and forward-vol numbers depend on implied vol; forward-vol screens use realised correlation as a
  proxy for implied (an approximation, Citi). A Sharpe of 4.17 on a forward-vol screen was flagged as an outlier to verify.
- **Do not mix conventions**: payer vs receiver sign, ASW flavour, swap index (OIS-based spreads sit 4-6bp above SOFR-based), repo definition across markets.
- **Stop breach is an exit** (Citi Radar: 33bp flattening vs a 30bp stop): do not re-underwrite after the fact.
- **Scores do not carry across screens**; per-currency and global rankings differ; re-run the whole table when the universe changes.
- **Rebuild the weights**: desk tables do not disclose them; DV01-neutral is not beta-neutral.

## Output
1. **Scope card** (markets, instruments, horizon h, lookbacks, constraints, data used, screens skipped and why).
2. **Radar table** from the ranked CSV (one row per candidate; `signals`-compatible via rv-composite-scoring):

| rank | package_id | structure | side (receive/pay) | level_bp | z_63 / z_252 / z_756 | pctile | half-life d / df_t | carry_bp (3m) | vol_bp | carry/vol ann | pca_z | er_bp | hit_frac | liquidity (DV01) | scan_flags / flags | passed |

3. **Shortlist of at most 5** (post step 6-7), each: one-line thesis, why it is cheap/rich, weights and legs (`legs_trade`), entry/target/stop and
   risk/reward (>= 1.5), 3m carry+roll, z at two lookbacks, stress P&L under the seven shocks, kill criteria. Hand off to
   [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md).
4. **Rejected** with reason codes (`no_reversion`, `unit_root`, `cost_fail`, `z_disagree`, `thin_history`, `stale`, `dup_leg`, `illiquid`).
5. Footer: universe size, number of structures tested, expected chance hits (at least N x 0.134), data as-of, scan parameters. Say plainly that these
   are screen outputs, backward-looking, and that the shortlist has not been traded or priced for execution.

## Scripts
- [`scripts/scan.py`](scripts/scan.py): `scan` (all curves and flies on a tenor set -> metric table), `synth_curves`, `last_z`, `halflife`,
  `df_tstat`, `ou_er`, `hit_frac`, `pca_resid`, `annuity`. CLI reads a canonical `curve_par` CSV/Parquet:
  `python scripts/scan.py --curve-par curve_par.csv --curve-id USD-SOFR --snap eod_ny --tenors 2Y,3Y,5Y,7Y,10Y,20Y,30Y --h-days 63 --out ranked.csv`;
  `--kind curves|flies`, `--z-ref`, `--min-abs-z`, `--max-hl`, `--cost-bp`, `--passed-only` (write passing rows only), `--top`. Spot curves only (start = 0D); one curve and one snap per run.
  `python scripts/scan.py --demo` reproduces example A. Requires a short tenor (<= 1Y) for financing carry, else carry is roll-only
  (`cr_basis = roll_only`). `python -I scripts/scan.py --selftest` checks: linear-curve levels and hand-computed carry+roll, a flat curve
  (zero carry), column-order invariance, z of 1..252 against the closed form, exact AR(1) half-life, a simulated AR(1), Dickey-Fuller rejection rates on random walks and AR(1), a kinked curve with hand-computed roll and carry, row definitions of carry/vol, its annualisation, reversion credit and h-day vol on a mixed-side table, the OU expected gain, the cost hurdle (nothing passes at 1000bp), hit-fraction
  limits, the PCA residual of a planted bump against the true projector, and an end-to-end planted-dislocation ranking. Exits non-zero on failure.

## Related skills
- Data and conventions: [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md), [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md),
  [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md), [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md)
- Metrics: [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md), [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md),
  [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md), [curve-pca-factor-model](../curve-pca-factor-model/SKILL.md), [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md),
  [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md) (unit-root and half-life tests), [quant-cointegration](../quant-cointegration/SKILL.md)
- Structures: [curve-steepeners-flatteners](../curve-steepeners-flatteners/SKILL.md), [curve-butterflies](../curve-butterflies/SKILL.md), [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md),
  [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md), [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md), [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md),
  [stir-futures-rv](../stir-futures-rv/SKILL.md), [vol-rates-options-rv](../vol-rates-options-rv/SKILL.md), [infl-breakevens-and-linkers](../infl-breakevens-and-linkers/SKILL.md), [xccy-basis](../xccy-basis/SKILL.md)
- Downstream: [rv-composite-scoring](../rv-composite-scoring/SKILL.md), [port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md), [rv-devils-advocate](../rv-devils-advocate/SKILL.md),
  [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md), [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md), [rv-trade-monitoring](../rv-trade-monitoring/SKILL.md)
- Vetting context: [macro-regime-and-scenario-analysis](../macro-regime-and-scenario-analysis/SKILL.md), [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md),
  [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md)
- Upstream and context: [rv-research-digest](../rv-research-digest/SKILL.md), [macro-fair-value-models](../macro-fair-value-models/SKILL.md), [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md)
- [curve-term-structure-models](../curve-term-structure-models/SKILL.md): term-structure models and term premium.
- [vol-basis-vs-vol](../vol-basis-vs-vol/SKILL.md): basis as embedded vol vs options.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): gamma, vega and theta P&L.
- [stir-options-implied-distributions](../stir-options-implied-distributions/SKILL.md): option-implied policy-rate distributions.
- [stir-rfr-compounding-and-fixing-risk](../stir-rfr-compounding-and-fixing-risk/SKILL.md): RFR compounding and fixing risk.
- [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md): event risk and prediction-market probabilities.
- [macro-inflation-and-energy-drivers](../macro-inflation-and-energy-drivers/SKILL.md): energy-to-inflation pass-through and CPI nowcasts.
- [macro-geopolitical-risk](../macro-geopolitical-risk/SKILL.md): geopolitical channels and fade/follow rules.
- [macro-central-bank-nlp](../macro-central-bank-nlp/SKILL.md): central-bank text scoring.
- [macro-technical-analysis](../macro-technical-analysis/SKILL.md): trend, momentum and technical timing.
- [quant-lead-lag](../quant-lead-lag/SKILL.md): lead-lag and transmission between markets.
- [quant-covariance-estimation](../quant-covariance-estimation/SKILL.md): covariance and correlation estimation.
- [quant-systematic-rates-signals](../quant-systematic-rates-signals/SKILL.md): rule-based duration and country signals.
- [fi-curve-construction](../fi-curve-construction/SKILL.md): OIS/RFR curve building and diagnostics.
- [fi-collateral-csa-and-xva](../fi-collateral-csa-and-xva/SKILL.md): CSA discounting and xVA wedges.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): P&L attribution and performance metrics.
- [eng-reporting-and-visualization](../eng-reporting-and-visualization/SKILL.md): screens, charts and one-page reports.

## References
- Citi Research - North America Rates Trade Idea Alert: Taking profits on delta-hedged 15y5y/20y10y flatteners (R. Bikbov, 5 Dec 2019): convexity-flattener screen, BE/RV, exit rule, full USD table
- Citi Research - Rates Vol Lab: Forward steepener and vol divergence (M. Chang, J. Williams, A. Appeddu, 12 Jun 2023): steepener screen with the flipped BE/RV rule, carry-entry frontier, forward-vol frontier
- Goldman Sachs FICC and Equities (IRP Market Strats) - Global Rates Best Trade Report (desk material, 30 Sep 2026): carry/entry/trend metrics, quadrants, projected composite, Carry/R, per-currency scores
- Goldman Sachs FICC and Equities (IRP Market Strats) - Market Movers for Rates and Cross-Asset (30 Sep 2026): standard screen grid, normalised-move score, 62/252-day windows, low-vol window trap
- Goldman Sachs FICC and Equities (Macro Sales & Trading Strats) - US Treasury Relative Value Report / US Treasury Asset Swap Spreads (25 Sep 2026): bond-level layout, |3m z| >= 2 flags, MMS vs proceeds ASW, fitted-curve spread
- Nordea Markets - EUR Rates Flash (J. Vainikainen, 23 May 2019): RV monitor, J-score, in-the-money probabilities, value of convexity, PCA residuals
- Nordea Markets - EUR rates: Pushing back (A. Svendsen, 17 Jan 2024) and EUR rates: The quiet game (12 Aug 2025): dashboard columns, trade boxes with target/stop, carry-fly and crowding warnings
- Citi Research - Global Macro Trade Ideas Radar (L. Costa et al., 13 Aug 2026): radar inclusion criteria (DV01, 1.5:1), HVaR/IVaR normalisation, closed-trade lessons, stop discipline
- Citi Research - Rates Vol Lab: In search of cheap vol (R. Bikbov, J. Williams, 17 Jan 2020): cross-market BE/RV ranges, hedge frequency, regime exclusions
- Citi Research - Rates Vol Lab: Left-side vols' outperformance (M. Chang, J. Williams, A. Appeddu, 22 Jun 2021): gamma-neutral forward-vol frontier ranked by ex-ante Sharpe
- Citi Research - Rates Vol Lab: Liquidity, vega, and convexity (30 Mar 2020): watch-list rule for illiquid structures, forward-vol Sharpe outlier
- Citi Research - US Rates Vol Lab: Trading long-dated convexity (9 May 2019) and Long Live Formosa (9 Jan 2017): ZLB exclusion, z vs value, conditional pick-up arithmetic, vol-surface PCA residual
- Citi Research - Rates Vol Lab: Fading vega dislocations (5 Oct 2026): 2026 frontier, callable-supply vega, vol-rate beta flip
- Citi - Interest Rate Volatility Trading: A Holistic Approach to Convexity Across Fixed Income (M. Parolari, Jun 2022): P&L decomposition, expected Sharpe across instruments
- Citi Research - Agency MBS Weekly: The Summer Lull (21 Aug 2026): seven curve-shock stress template, duration-hedged carry
- BofA Merrill Lynch - Liquid Insight: A simple framework for swap spread relative value (R. Axel, E. Satko, S. Cross, 2 Jun 2016): PCA dislocation indicator, back-test, half-life
- BofA Merrill Lynch Global Research - European Rates Viewpoint: Many EGBs, one simple value tool (E. Satko, 21 Mar 2018): EGB PCA residual screen, threshold grid, cheap-leg effect
- RiskVal Financial Solutions - RiskVal Overview 201: Cash and Futures (12 Nov 2021): bond roll sheet, RV screener, mean-reversion frequency, fitted vs direct spread
- Doug Huggins and Christian Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): statistical vs financial model workflow, OU/PCA, fitted-curve residuals, ASW adjustments
- Salomon Brothers - Understanding the Yield Curve, Part 6 (A. Ilmanen, Nov 1995): expected-return decomposition for curve trades
- Richard Grinold and Ronald Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): IC/IR/breadth, multiple-testing and cost rules
- Rishi Narang - Inside the Black Box (3rd ed., Wiley, 2024): implementation dimensions of a screen, adverse selection of extreme signals, cost over-estimation
- Alexander During - Fixed Income Trading and Risk Management (Wiley, 2021): critique of pure statistical-arbitrage mean reversion
- JWS Macro (Substack) - #3: Iran & Front End Rates (8 Mar 2026): energy-beta screen, positioning residuals
- Deriscope blog - Yield Curve Building in Excel with Central Bank Meeting Dates and STIR OIS Trading Arbitrage Opportunities: The GBP Sonia case (I. Rigopoulos, 18 Feb 2024): meeting-date step curve, spot-vs-forward check
- Citi Research - The High-Grade Beat: The path forward for hyperscalers (D. Sorid, M. Jacob, 19 Aug 2026): 120-day 2-sigma issuer-curve screen, fixed-sample rules (credit template)
