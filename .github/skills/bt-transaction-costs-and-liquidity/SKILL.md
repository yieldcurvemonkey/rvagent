---
name: bt-transaction-costs-and-liquidity
description: 'Prices transaction costs, market impact and liquidity for G10 rates RV trades and backtests: one-way bid/offer per leg and per DV01, package and hedge/roll cost tiers, cost-multiplier sweep and break-even, square-root and inventory-aware impact, capacity vs ADV, liquidity-regime monitors (depth, price impact, intraday vs close vol, curve dispersion, effective vs indicative spread), flow toxicity (VPIN, imbalance) and RFQ execution. Use when asked about bid/offer, bid-ask, slippage, transaction costs, "do costs kill this trade", break-even holding period, hedge frequency, market impact, liquidity, depth, capacity, crowding, toxic flow, or whether a swap, bond, futures, STIR, swaption or fly/curve/basis trade is tradeable in size. Package, venue and protocol choice: rv-execution-and-trade-packaging.'
---

# Transaction costs, impact and liquidity for rates RV

Most small RV edges in rates (a fly 1-2bp from fair, a 0.5bp basis, a mean-reverting spread with a 1-day half-life) are the
same size as the cost of getting in and out. A backtest without realistic, time-varying costs is not a result. This skill
turns quotes, trade tapes and position paths into: a one-way cost per leg, a round-trip cost per package, a break-even
holding period, a cost-multiplier sweep, an impact and capacity estimate, and a liquidity-regime flag that tells the agent
when to widen costs or refuse to initiate. Costs enter every headline number, not an appendix.

## When to use
- "Do costs kill this trade?", "what is the break-even?", "what bid/offer should I assume for a 2s5s10s / swap spread / basis / STIR fly?"
- Costing any backtest: charging per leg, per DV01 traded, with initiation vs hedge/roll tiers and a 0x/0.5x/1x/2x sweep.
- How often to hedge or rebalance, and how wide a no-trade band should be.
- Size questions: market impact of a block, size vs ADV or median trade size, capacity, crowding, exit cost in stress.
- Is the market liquid right now? Depth, price impact, curve dispersion, effective vs indicative spread, VPIN, spoofing.
- Which venue and how many dealers to call; how a dealer will price and skew a request.

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md). If an input is missing, ask
the user or the data engineer for it. Never invent a spread or a depth.

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Bid and ask for bonds, futures, STIR, listed options | `bond_quotes` (`bid_px`, `ask_px`, `bid_ytm_pct`, `ask_ytm_pct`), `fut_quotes`, `stir_quotes`, `opt_quotes` (`bid_px`, `ask_px`) | daily snap, 2y+, same snap as the signal | one-way half-spread = (ask - bid)/2 in price; in yield (bid_ytm_pct - ask_ytm_pct)/2 x 100 bp (the bid yield is the higher one). Indicative and settlement-time spreads understate size cost |
| Holdings path (signed DV01 per leg) | `positions` (`dv01_ccy`) | daily, from the backtest | traded DV01 = day-over-day change, first day = full entry, last day liquidated. Include zero-DV01 rows for flat days; DV01 also drifts on a constant-notional hold (see Pitfalls) |
| Executions, simulated or real | `trades` (`qty`, `price`, `slippage_bp` positive = cost, `fee_ccy` <= 0) | per fill | measures realised cost vs mid |
| Public trade prints | `flows_trades` (`notional_ccy`, `notional_capped`, `is_package`, `is_compression`) | intraday | strip compression, packages, cancels before any volume or cost read |
| P&L ledger | `pnl` (`cost_ccy` <= 0) | daily | the output of this skill lands in `cost_ccy` |
| Volume and open interest | `fut_quotes`, `stir_quotes`, `opt_quotes` (`volume_cnt`, `oi_cnt`) | daily | volume is not liquidity: compare with open-interest change |
| Vol surface and vol history | `vol_surface` (`nvol_bp`) | daily | for vol-regime links and option b/o in normal vol |
| Repo specialness | `repo_rates` (`specialness_bp`) | daily | on-the-run premium contains specialness |
| Event calendar | `cb_meetings`, `calendars` | forward-looking | for event-window depth and hedge timing |
| Swap and swaption half-spreads | `bid_offer` (`half_spread_bp`, `quote_unit`) | by tenor, structure, period | if empty, user-supplied dealer quotes, or the priors in [cost-benchmarks](references/cost-benchmarks.md) |
| Order-book depth and aggressor-flagged tape | `book_snapshots`; `flows_trades` (`aggressor_side`, `instrument_id`, `price_px`) | top-3 levels, event time | if absent, use quote-based and daily-bar methods only |

## Method

### 1. Units and sign conventions (get these right first)
- **One-way half-spread** h = mid-to-bid or mid-to-offer, in bp of rate (or yield bp). A round trip is 2h on each leg. Full
  width = 2h. Sources quote both: label every number, and halve a full width before charging.
- **Cost in currency** = |DV01 traded| x h x cost_mult, DV01 in currency per bp. Charge the **traded increment**
  (day-over-day change in DV01), never the position; include entry and terminal liquidation. Writing `pnl.cost_ccy` = -cost
  (<= 0); `trades.slippage_bp` = fill minus mid in the adverse direction (positive = cost).
- **Price to yield bp**: `bp = pts / (ModDur x Price / 10000)`. A 1/256 tick on a 10y (ModDur 8, price 100) is 0.049bp. Half a
  32nd on a contract with ModDur 8 is 0.195bp. Treasury futures have no bp value until a deliverable's DV01 maps them.
- **STIR**: price = 100 - rate, tick 0.005 = 0.5bp for 3M contracts (about 25 per bp per 1mm 3M contract); listed calendars,
  flies and condors quote directly in bp, not index points.
- **Options**: charge b/o in normal-vol bp x vega, or (ask - bid)/2 in price points; keep the premium and vol bases separate.

### 2. Choose the cost source (best first)
1. **Measured**: half-spread from the same-snap `bid_*`/`ask_*` columns, by instrument and date, time-varying.
2. **Dealer quote** supplied by the user for the exact structure and size (ask: size, tenor, structure, time of day).
3. **Bucketed table** by instrument class and tenor from [cost-benchmarks](references/cost-benchmarks.md), scaled by the
   period (b/o fell from 1.2-2.0bp in 1995-2004 to 0.3bp in 2017-18 for USD 2y-10y swaps; Citi Research, The art of gamma
   hedging, 12 Mar 2018). Never apply today's cost to 1998 or 2020.
4. **Placeholder** flagged as such in the output. Cost model shape: flat is crude, piecewise-linear in size is the usual
   compromise (Narang, Inside the Black Box, 3rd ed., 2024). If in doubt overestimate (underestimating bleeds from overtrading,
   overestimating only over-holds), and refresh from your own fills.
Per-instrument or bucketed spreads, never one flat bp: a flat number charges the wrong legs.

### 3. Package cost, initiation vs hedge/roll
- Package one-way cost = sum over legs of |DV01_i| x h_i. Report it per gross DV01 and per unit of the package's own risk
  (the package bp must match the fly convention: for belly minus average wings it is the belly DV01, for 2x5y-2y-10y it is half
  the belly DV01). `scripts/costs.py package_cost` does this.
- **Initiation costs more than hedge or roll**: long-dated USD forward-curve packages 0.75-1.0bp to initiate, 0.3-0.4bp per
  delta-hedge or roll (hedges are smaller and carry less dealer risk; Citi Research, US Rates Vol Lab: Trading long-dated
  convexity, 9 May 2019). Use separate parameters for entry/exit and for rebalances.
- **Quoted package vs legging**: a package priced as one structure is cheaper than the sum of its legs, and a dealer's spread
  margin must be strictly below the sum of its component spreads (2s10s < 2s5s + 5s10s; Darbyshire, Pricing and Trading
  Interest Rate Derivatives, 3rd ed., 2022, Ch.19). Legging a STIR fly (+1, -2, +1 = 4 contracts) and crossing half a tick on each (0.25bp on a 0.5bp-tick contract) costs 4 x 0.25 = 1.0bp one way, 2.0bp round trip, illustrative; a listed fly pays its own quoted spread once, and legging adds legging risk (Aikin, STIR Futures, 2nd ed., 2012).
- **Futures vs swaps** as the hedge: futures are cheaper to trade but add CTD/basis risk; margin and balance-sheet costs
  belong in the carry/financing line, see [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md).

### 4. Amortise, break even, sweep
- **Annualised cost = round-trip cost / holding years.** Grinold-Kahn: a 1.5% round trip (0.75% each way) on a repeating
  6-month 2% gainer is 3%/yr of cost against 4%/yr of alpha, net 1%; the same 8% gainer held 24 months pays 0.75%/yr, net
  3.25% (Grinold and Kahn, Active Portfolio Management, 2nd ed., 1999).
- **Break-even holding days** = round-trip cost (bp) / carry+roll (bp/day). If net carry is zero or negative, carry never repays
  cost: return "never", do not return a positive number. Carry sign and units come from
  [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md).
- **Net edge** = gross expected move + carry x days - round-trip cost.
- **Cost sweep**: run cost_mult in {0, 0.5, 1, 2}. Tune at 1x, test robustness at 2x, report P&L at every multiple and the
  **break-even cost multiple** (cost at which net edge is zero). Costs must be on in every headline result. A negative result
  is acceptable. Always state the known limitations: mid marks, no margin/CSA/balance-sheet charge, funding ignored.
- **Return on execution costs** = dollar performance / total execution costs "should be a large multiple" (Lopez de Prado,
  Advances in Financial Machine Learning, 2018, Ch.14). Include liquidation cost of the terminal position.
- **Cost erosion of the information ratio**: 200 stocks rebalanced semiannually with IC 0.0577 give a formula IR of 1.154; at about 100%/yr turnover and a 0.80% round trip the net IR is 0.70 (1.21% alpha on 1.729% risk); a top-quartile manager (IR 0.5) can lose about half her return to costs (Grinold and Kahn, 1999). IR = IC x sqrt(BR) logic: [port-portfolio-construction](../port-portfolio-construction/SKILL.md).
- **Turnover logic**: value added is concave in turnover; at least 75% of incremental value is kept at 50% of the turnover,
  so slow down before cutting alpha ([execution-and-capacity](references/execution-and-capacity.md) section 1).

### 5. Trading frequency and bands
- Costs set the hedge or rebalance frequency: at 0.5bp swap b/o the best delta-hedge threshold for short 1m10y straddles was
  about 3-7% of delta; at 0.3bp it was 0% (daily). Move-based hedging of convex flatteners plateaus at 15-30bp bands. Re-fit
  when b/o changes (Citi, The art of gamma hedging, 12 Mar 2018; Trading long-dated convexity, 9 May 2019). Detail and
  mean-reversion entry/exit bands with costs: [execution-and-capacity](references/execution-and-capacity.md).
- Hedge when realised vol between hedges is lowest and liquidity is deepest (the best hour drifts between windows; re-estimate).

### 6. Impact and size
- **Square-root impact**: cost per unit about sigma x sqrt(V_trade / V_daily); total cost grows as size^1.5 ("it costs roughly one
  day's volatility to trade one day's volume"; Grinold and Kahn, 1999). Swap-book add-on in DV01 terms: impact (bp) =
  alpha x sqrt(|x|), alpha default 1/1000 (1bp for 1mm DV01); total (2/3) alpha |x|^1.5; inventory-aware
  (2/3) alpha (|I+x|^1.5 - |I|^1.5) with negative add-ons floored (Darbyshire, 2022, Ch.19.4). `scripts/costs.py`
  `impact_addon_ccy`/`quote_cost_ccy`.
- **Splitting does not beat an inventory-aware dealer**: two 50k DV01 requests cost 0.65bp then 0.77bp, average 0.71bp = the
  single 100k price (Darbyshire, 2022, Ex 19.10). Splitting helps against a CLOB and when trading across time with recovery.
- **Aggregate across accounts before costing**: impact is nonlinear, summing per-account impact underestimates cost.
- **Calibrate to live fills**, use the same cost and impact model in backtest and production, include financing (Paleologo, The
  Elements of Quantitative Investing, 2025).
- **Size gates** (house defaults, tune to the desk): each order at most 1% of ADV (Chan, Quantitative Trading, 2009); compare
  the trade with the median and 95th percentile trade size by currency and tenor, in the same unit (G4 IRS/OIS/FRA 5-10y: median
  about USD 51mm notional, 95th $257mm; median DV01 per trade roughly $30-50k across tenors; FRBNY Staff Reports No. 557, 2012); above the
  95th percentile treat the trade as a block and quote conditionally.

### 7. Liquidity regime and cost multiplier
Build trailing rolling z-scores (1y-2y, signed so higher = less liquid; never full-sample mean/std, and the multiplier applied to a trade is the one known at the decision snap) of the indicators in
[microstructure-metrics](references/microstructure-metrics.md) section D and map them to a multiplier.

| Regime | Trigger (house default, anchored on the J.P. Morgan composite: 0.95 a month before, 2.44 and 5.32 in Mar 2020) | Cost multiplier | Action |
|---|---|---|---|
| Normal | composite < 1, depth z > -1, intraday/close vol ratio z < 1 | 1x | trade |
| Elevated | composite 1-2, or any two monitors beyond 2 sigma | 2x (10y USD swap b/o went from about 0.3bp in 2018, width convention unstated, to 0.6bp mid-to-b/o in Mar 2020: 2x or more) | smaller size, widen hedge bands, avoid releases |
| Stress | composite > 2, or effective spreads wide of the minimum tick while depth looks normal | 3-10x (small UST trades about 10x in Mar 2020) | do not initiate multi-leg or off-benchmark size |

- **Core monitors**: top-3 depth, price impact per $100mn, fast-participant share of depth, intraday vs close-to-close realised
  vol, curve dispersion (RMSE or spline form, thresholds differ), effective vs indicative spread, futures-vs-cash richness. Use
  several and read divergences: bid/offer looked normal in 2015-16 while curve dispersion rose (Duering, Fixed Income Trading and
  Risk Management, 2021).
- **Optical vs effective depth**: on 9 Mar 2020 about two-thirds of 30y interdealer volume filled wider than the minimum
  increment while displayed depth looked ordinary (J.P. Morgan, When market risk meets operational risk, 10 Mar 2020). Measure
  fills against the tick.
- **Vol-liquidity loop**: higher implied vol leads to fast-participant withdrawal, more impact, more realised vol (J.P. Morgan,
  Impossible to walk in this muck, 6 Mar 2020). But microstructure can improve while vol rises, so do not assume deterioration.
- **Flash events**: volume surges while depth collapses (10y UST yield fell 16bp and rose 16bp in 12 minutes on 15 Oct 2014 against a daily sd of 4-5bp); small electronic trades still clear while large trades stay hard (Tuckman and Serrat, 2022).
- **Calendar**: depth thins into 08:30 releases, auctions and central-bank decisions and takes 15-60 minutes to rebuild; Tokyo
  hours are thinnest, NY deepest; year-end is a seasonal low. Link event windows to
  [macro-event-risk-and-prediction-markets](../macro-event-risk-and-prediction-markets/SKILL.md) and
  [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md).
- **Liquidity hierarchy**: news hits the most liquid instrument first (on-the-run UST in the US; bond futures in Germany and
  Japan, so little on-the-run premium there) and the rest reprice through it. Swaps lag in a rally; futures cheapen first in a sell-off
  (Duering, 2021; J.P. Morgan, 10 Mar 2020). Liquidity conditions are correlated across markets: diversification does not diversify them.

### 8. Low-data estimators
Where there are no quotes (linkers, small govies, history before quotes were stored): Roll from the lag-1 autocovariance
(`roll_half_spread`), Corwin-Schultz from highs and lows, Amihud (`amihud`) from daily bars, dispersion from prints. Formulas,
caveats and thresholds: [microstructure-metrics](references/microstructure-metrics.md) section B.

### 9. Flow toxicity and fills
- Treat a fill as information: conditional on being filled, is the trade still attractive? An easy fill on a hard-to-value
  package should prompt re-underwriting (Jane Street, Probability and Markets primer).
- VPIN = E[|2 v_buy - 1|] on volume bars; persistent imbalance is necessary but not sufficient (it must also be unpredictable).
  Futures show among the lowest VPIN false-positive rates (Lopez de Prado, 2018). Displayed depth in futures can be spoofed.
- Fast-participant depth falls 5-25 minutes ahead of slower participants in stress: use it as an early warning.
- Execution: show fewer dealers for informative size; go to the point of least liquidity first; never leg a closing spread
  ([execution-and-capacity](references/execution-and-capacity.md) section 2; hand-off to
  [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md)).

## Worked examples

**A. Costing a fly, illustrative inputs.** Receive-belly 2s5s10s fly measured as 5y - (2y + 10y)/2 (a 1bp move is worth the belly
DV01), DV01-neutral: 2y -5,000, 5y +10,000, 10y -5,000 currency per bp. Half-spreads 0.4 / 0.5 / 0.5bp (illustrative outright values
in the range of the dealer-margin template in Darbyshire, 2022, Ch.19; replace with quotes). One-way = 5,000 x 0.4 + 10,000 x 0.5 +
5,000 x 0.5 = 9,500; round trip 19,000, which is **1.9bp of the fly** (19,000 / belly DV01 10,000) or 0.95bp per gross DV01 (20,000).
In the 2x5y-2y-10y convention (twice this fly, 5,000 per bp) the same cost is 3.8bp and the edge below 6.0bp: compare cost and edge in
one convention. Expected convergence 3.0bp gross: net 1.1bp at 1x, 2.05bp at 0.5x, -0.8bp at 2x, break-even multiple 3.0 / 1.9 = 1.58x.
Net carry+roll 0.01bp/day repays the cost only after 190 days. Verdict: fails the 2x test, so treat as marginal; ask for a package quote
before dropping it. (`package_cost` and `breakeven --round-trip-bp 1.9 --carry-bp-day 0.01` in `scripts/costs.py` reproduce these.)

**B. Cost neutralises a statistical edge** (d'Aspremont, Identifying Small Mean Reverting Portfolios, 2008). Optimal sparse
mean-reverting USD swap baskets (e.g. short local flies) estimated on 100 days of 1y-30y swaps and traded 50 days out of sample looked promising frictionless, but "even
minuscule transaction costs (a bid-ask spread of 1bp) are sufficient to completely neutralize" them. Rule: compare the out-of-sample
price range of any automated fly or basket screen in bp with the round-trip cost before ranking it.

**C. Hedge band vs cost** (Citi, The art of gamma hedging, 12 Mar 2018): 1994-2017 short 1m10y straddles, hedge at the close only if
|delta| exceeds a threshold. At 0.5bp swap b/o the Sharpe peaks at a 3-7% threshold; at 0.3bp daily hedging (0%) is best. Use
the current b/o to choose the band; the same 0.3bp-vs-0.6bp swing between 2018 and Mar 2020 changes the answer.

**D. Impact add-on** (Darbyshire, 2022, Ex 19.10): 100,000 DV01 in 10Y with core 0.5bp: 50,000 + add-on 21,081 = 71,081, i.e.
0.71bp. As two 50k requests: 25,000 + 7,454 = 32,453 (0.65bp), then the second add-on is (2/3)(0.001)(100,000^1.5 - 50,000^1.5) =
13,628 so 0.77bp; the average is 0.71bp.

**E. A "free" spread that is not** (Clarus Financial Technology, Pricing and Arbitraging the CME/LCH Basis, 22 Jun 2015): $100mm 5Y,
quoted basis 1.25bp = $12,500 a year, PV about $60,447. After SEF fees, clearing and FCM fees, net cash flow about +$45,042; IM
funding costs about -$181,571 over the life (day-1 IM about $3.87mm). Break-even basis 3.932bp, about three times the quote, and
IM add-ons grow super-linearly with size. Full stack: [spread-ccp-basis](../spread-ccp-basis/SKILL.md).

**F. Indicative vs effective spread** (Federal Reserve Board, FEDS 2025-049, 7 Jul 2025; off-the-run USTs, dealer-to-client, 2018-24):
median effective (full-spread scale) 0.37bp vs indicative 0.68bp, so screens overstate typical cost. But above $50mm the 95th percentile
is 12.41bp vs 4.15bp indicative. A just-off-the-run bond's 1bp indicative is about 0.73bp effective; the factor rises when the on-the-run
benchmark is itself illiquid. Charge size-conditional costs, not the screen.

**G. Illiquidity that is only visible at exit** (Citi, North America Rates Trade Idea Alert, 15 Jun 2020): a USD 10y10y/20y10y/30y10y fly entered
at 16bp in late Feb 2020 peaked in March but could only be unwound when costs returned to about 3bp, at 10bp on 15 Jun 2020 for $360k.
Peak marks in a dislocation are not tradeable.

## Signals & interpretation
- **Tradeable** (house defaults): break-even cost multiple (gross edge / round-trip cost) of at least 2, i.e. positive net edge at 2x costs.
  Robust: multiple of at least 3, i.e. net edge at 1x of at least 2x the round-trip cost (return on execution costs a large multiple).
  Below 2, state that the trade is cost-limited.
- Carry that repays cost in less than the signal half-life is good; negative net carry means the trade needs the move, not time.
- **Prefer the tighter market** among near-identical screens (Citi chose 15y5y/20y10y over 15y5y/20y15y for a tighter market).
- Fast mean reversion with tiny price range is a cost trap: require range / round-trip cost of at least 3 (house default).
- Regime flag Elevated or Stress: apply the multiplier, shrink size, widen bands; do not start illiquid multi-leg packages even when
  z-scores are extreme (Citi, Liquidity, vega, and convexity, 30 Mar 2020: a 4-sigma flattener was "effectively a free convexity buy" and was not started).
- Effective cost above the screen spread, or fills systematically worse than mid by more than the assumed half-spread, means the cost
  table is too low: update it before trusting any P&L.
- Alpha that exists only because of illiquidity fades when liquidity returns (EGB auction cycle 2013-14); judge such strategies net of a
  time-varying bid/offer.

## Pitfalls
- **Units**: full vs half spread, price vs yield bp, index points vs bp, notional-per-unit read as per-bp (10,000x error), decimals stored as bp.
  Put the unit in every column name.
- **DV01 drift read as trading**: DV01 of a constant-notional hold changes every day (rates, pull to par), so differencing DV01 charges phantom
  trades. Use `--drift-tol` (e.g. 0.02 = ignore daily DV01 changes under 2% of the position) or difference notional or contracts and multiply by
  DV01 per unit. A roll between instruments with unchanged DV01 also shows zero traded DV01: book each contract as its own leg to charge the roll.
- **Charging the position instead of the increment** (fee at every resize) or only at unwind, or an immediate fill with no slippage.
  Assert marks are non-zero, closed-trade count positive and no equity gaps, so silent failures cannot hide cost gaps.
- **Mid marks with mid fills.** Mark at mid but enter and exit at bid/offer; add slippage for larger than standard size (Citi Research,
  Emerging Markets Strategy Weekly, 20 Aug 2026).
- **Snap-time mismatch** between a data snap and a settlement or fixing time adds noise that can exceed the signal; use one snap per series
  ([data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md)).
- **Indicative quotes are advertising**; executed-trade spreads are biased low for hard-to-trade issues (only executed trades are observed);
  stress samples keep only the bonds that still trade.
- **Cost keyed on the wrong axis**: off-the-run Treasury cost depends on issue age and size as well as maturity; do not charge both legs of a
  switch the same.
- **Admin flow in volume**: compression, IMM-roll packages, CCP-basis packages and cancels distort volume and price content; strip them. Capped
  block notionals understate size.
- **Volume is not liquidity** where risk recycling inflates turnover; use DV01-weighted volume and open-interest change.
- **Hedges get their worst friction when needed**: assume wider b/o and impaired repo in the scenario the trade protects against
  ([port-scenario-and-stress-testing](../port-scenario-and-stress-testing/SKILL.md)).
- **Stale or asynchronous prices** understate vol and correlation and overallocate to illiquid sectors.
- **Missing G10 data**: sources give no cost numbers for CAD, AUD, NZD, CHF and little for SEK and NOK. Measure from bid/ask or ask for
  quotes; say so in the output.
- **Placeholders left in place**: replace them with dealer quotes and mark them in the report.
- **Short-horizon backtests on last prices** overstate profits; use bid, ask and, if needed, book data.

## Output
Return, per trade or strategy:
1. **Cost assumptions table**: leg or structure, source (measured / dealer / bucketed prior / placeholder), one-way half-spread bp,
   unit, period, regime multiplier.
2. **Package economics**: one-way and round-trip cost (ccy and bp of package risk), break-even holding days vs carry+roll (or "never"),
   net edge, and the **0x / 0.5x / 1x / 2x sweep** with the break-even multiple.
3. **Liquidity regime card**: monitors with current z-scores, regime (Normal / Elevated / Stress), multiplier applied, event windows ahead.
4. **Size and capacity**: DV01 vs median and 95th percentile trade size, vs ADV or depth, impact add-on in bp, execution advice
   (venue, dealers to call, leg order, timing).
5. **Caveats**: limitations (mid marks, no margin or balance-sheet cost, funding), missing G10 data, placeholders.
6. **Hand-off**: write `pnl.cost_ccy` (<= 0) and `trades.slippage_bp` for [bt-backtest-design](../bt-backtest-design/SKILL.md); pass the
   cost line and regime flag to [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md).

## Scripts
- [`scripts/costs.py`](scripts/costs.py): per-leg and package cost, increment-based cost path from a canonical `positions` table with a
  cost-multiplier sweep, break-even holding days vs carry, annualised cost, price-to-yield-bp conversion, square-root and inventory-aware
  impact add-on, Roll half-spread, Amihud, expected round turns of a moving-average rule.
  `python scripts/costs.py cost-path --positions positions.csv --half-spread-bp 0.4 --sweep 0,0.5,1,2 [--drift-tol 0.02]`;
  `python scripts/costs.py breakeven --round-trip-bp 1.9 --carry-bp-day 0.01`. `--selftest` checks known cases (worked example A, the add-on
  numbers above, Grinold-Kahn annualisation, increment-vs-position charging, negative carry returns "never", Roll recovery from a simulation).

## Related skills
- [bt-backtest-design](../bt-backtest-design/SKILL.md): where costs are charged (fills, marks, rolls); this skill supplies the numbers.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): shows `cost_ccy` as its own P&L component.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): tune at 1x costs, validate at 2x; cost choices are a degree of freedom.
- [rv-execution-and-trade-packaging](../rv-execution-and-trade-packaging/SKILL.md): turns the cost and liquidity read into legs, order and venue.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 per leg that cost is charged on.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): balance-sheet and margin cost that bid/offer omits.
- [spread-ccp-basis](../spread-ccp-basis/SKILL.md): the full fee, IM and break-even stack for CCP basis trades.
- [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): delta-hedge cost against gamma P&L.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): entry and exit bands with costs.
- [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): turnover vs signal half-life.
- [flow-sdr-and-dealer-positioning](../flow-sdr-and-dealer-positioning/SKILL.md): trade-repository hygiene and dealer flow.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): size against liquidity and DV01 budgets.
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): snaps, stale quotes, outliers.
- [stir-futures-rv](../stir-futures-rv/SKILL.md): STIR calendar, fly and bundle trading where fees and legging dominate.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): roll trades are a recurring cost line (charge each contract as its own leg).
- [port-portfolio-construction](../port-portfolio-construction/SKILL.md): netting trades across packages before costing; IR = IC x sqrt(BR) with costs.

## References
Detail files: [cost-benchmarks](references/cost-benchmarks.md), [microstructure-metrics](references/microstructure-metrics.md), [execution-and-capacity](references/execution-and-capacity.md).
- Citi Research - US Rates Vol Lab: The art of gamma hedging (Bikbov, Williams, 12 Mar 2018): swap and swaption b/o history, hedge threshold vs cost, time-of-day hedging.
- Citi Research - US Rates Vol Lab: Trading long-dated convexity (Bikbov, Williams, 9 May 2019): initiation vs hedge/roll cost tiers, hedge-band plateau, tighter-market tie-break.
- Citi Research - Rates Vol Lab: Liquidity, vega, and convexity (Bikbov, Williams, 30 Mar 2020): intraday vs close-to-close vol diagnostic, do not initiate when illiquid.
- Citi Research - North America Rates Trade Idea Alert: Taking profits on long end butterfly trade (Mathai, Williams, 15 Jun 2020): exit-cost example.
- J.P. Morgan - When market risk meets operational risk (Younger, Salem, St John, 10 Mar 2020): effective-cost metric, optical vs effective depth, liquidity ladder.
- J.P. Morgan - Are we there yet? An update on fixed income market liquidity (Younger, St John, 1 Apr 2020): six-component composite liquidity index.
- J.P. Morgan - Drivers of price impact and the role of hidden liquidity (Younger, Sarkar, Salem, 13 Jan 2017): imbalance-bucket impact, square-root fits by session.
- J.P. Morgan - Far from the shallow now? Liquidity provision by high frequency participants in US rates (Salem, Barry, Younger, St John, 12 Apr 2019): depth definition, reaction-speed classes.
- J.P. Morgan - Fast and furious: the link between rapid trading and volatility in U.S. rates markets (Salem, Younger, St John, 20 Nov 2018): fast-fraction to impact to vol mapping.
- J.P. Morgan - When the going gets tough, the tough get going: rates market liquidity through data releases (Salem, Younger, St John, 5 Nov 2019): event-day depth, recovery time.
- J.P. Morgan - U.S. Rates Strategy: Times like these (Barry, Sun, White, 10 Feb 2016): fitted-curve RMSE liquidity proxy, off-the-run premia.
- J.P. Morgan - European Rates Strategy: Follow the cash flow (Salford, Chordia, 15 Sep 2015): liquidity-dependent alpha tracks bid/offer.
- Federal Reserve Board - FEDS 2025-049, Trading Costs v. Indicative Liquidity in the Off-the-Run Treasury Market (Sokolinskiy, 7 Jul 2025): duration-normalised effective spread.
- Federal Reserve Bank of New York - Staff Reports No. 381, The Microstructure of a U.S. Treasury ECN: The BrokerTec Platform (Fleming, Mizrach, Nguyen, 2009, rev. 2017): spread, depth, impact by tenor.
- Federal Reserve Bank of New York - Staff Reports No. 557, An Analysis of OTC Interest Rate Derivatives Transactions (Fleming, Jackson, Li, Sarkar, Zobel, 2012): trade-size tables, dealer offset ratios.
- Darbyshire - Pricing and Trading Interest Rate Derivatives: A Practical Guide to Swaps (3rd ed., Aitch & Dee, 2022): margin LP, impact and inventory add-ons, mid algorithms, quoting examples.
- Duering - Fixed Income Trading and Risk Management: The Complete Guide (Wiley, 2021): liquidity taxonomy, spline dispersion, RFQ leakage, market structure.
- Tuckman, Serrat - Fixed Income Securities: Tools for Today's Markets (4th ed., Wiley, 2022): liquidity metrics, market structure, size vs ADV, frictions on arbitrage.
- Grinold, Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): cost components, square-root impact, amortisation, turnover frontier.
- Hasbrouck - Empirical Market Microstructure (teaching notes, NYU Stern, 2004): Roll models, impact estimation, no-trade band.
- Aikin - STIR Futures: Trading Euribor and Eurodollar Futures (2nd ed., Harriman House, 2012): exchange fees, implied liquidity, legging, execution order.
- Leung, Li - Optimal Mean Reversion Trading (World Scientific, 2016): cost-dependent entry and exit bands.
- Riggs, Onur, Reiffen, Zhu - Swap trading after Dodd-Frank: Evidence from index CDS (Journal of Financial Economics 137, 2020): RFQ competition and round-trip cost (analogue for rates).
- Hendershott, Madhavan - Click or Call? Auction versus Search in the Over-the-Counter Market (Journal of Finance, Feb 2015): venue choice and dealer-count effects (corporate-bond analogue).
- Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018): implementation shortfall, Roll, Corwin-Schultz, VPIN, imbalance bars.
- Clarus Financial Technology blog - Pricing and Arbitraging the CME/LCH Basis (Skarecky, 22 Jun 2015): full fee and IM cost stack, 3.932bp break-even.
- d'Aspremont - Identifying Small Mean Reverting Portfolios (arXiv, 2008): 1bp bid-ask neutralises swap-fly mean reversion.
- Bank of England - Staff Working Paper No. 580, Centralized trading, transparency and interest rate swap market liquidity (Benos, Payne, Vasios, Jul 2016): dispersion and Amihud measures on swaps.
- Yadav, Younger - Central Clearing the U.S. Treasury Market (University of Chicago Law Review 92, 2025): March 2020 small-trade cost multiple.
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025): impact model, capacity, calibration to live fills.
- Chan - Quantitative Trading: How to Build Your Own Algorithmic Trading Business (Wiley, 2009): cost taxonomy, 1% of ADV cap, capacity and crowding.
- Narang - Inside the Black Box (3rd ed., Wiley, 2024): cost components and model shapes (partial).
- Citi Research - Emerging Markets Strategy Weekly: Can back-end USTs derail EM risk? (Costa et al., 20 Aug 2026): backtest marking at bid/offer and mid.
- Jane Street - Probability and Markets (trading primer, undated): fill as information, adverse selection.
- Also cited in the detail files: Dunis, Laws, Naim, Applied Quantitative Methods for Trading and Investment (Wiley, 2003); Tulchinsky et al., Finding Alphas (Wiley, 2015); O'Hara, Market Microstructure Theory (Blackwell, 1995); Gueant, Lehalle, Fernandez-Tapia, Dealing with the Inventory Risk (arXiv, 2012); Duffie, Garleanu, Pedersen, Over-the-Counter Markets (Econometrica, 2005) and Duffie, Dark Markets (Princeton, 2012); Cotton, Who Ya Gonna Call? (Quant Summit NY, 2019) and Cotton, Papanicolaou, Trading Illiquid Goods (2017); Cuturi, d'Aspremont, Mean-Reverting Portfolios (arXiv, 2015); Golub (ed.), BlackRock's Guide to Fixed-Income Risk Management (Wiley, 2023); Golub, Tilman, Risk Management: Approaches for Fixed Income Markets (Wiley, 2000); Clarus Financial Technology blog posts on SDR block trades (7 Oct 2015), compression (8 Dec 2014), the IMM roll (31 Mar 2015), EUR swap liquidity around the ECB (18 Jun 2014), swap trading (1 Jul 2014) and STIR futures (6 Jul 2016); FT Alphaville, Another reminder that dealers can spoof, too (20 Jan 2017); Conks (Substack), The Rise of the Secured Standard (25 Aug 2023); J.P. Morgan, Investment Strategies No. 74 (2 Oct 2012), TradeRunner (16 Aug 2018) and For cheap gamma, look to the long end (23 Aug 2019); Quantitative Finance Stack Exchange, Bergomi: Skew arbitrage; MIT OpenCourseWare 18.642 Lecture 7 (2024).
- Roll (1984), A simple implicit measure of the effective bid-ask spread in an efficient market, Journal of Finance (external).
- Kyle (1985), Continuous auctions and insider trading, Econometrica (external).
- Amihud (2002), Illiquidity and stock returns: cross-section and time-series effects, Journal of Financial Markets (external).
- Almgren, Chriss (2000), Optimal execution of portfolio transactions, Journal of Risk (external).
- Corwin, Schultz (2012), A simple way to estimate bid-ask spreads from daily high and low prices, Journal of Finance (external).
