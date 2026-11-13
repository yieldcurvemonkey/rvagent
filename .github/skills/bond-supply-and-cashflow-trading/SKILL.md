---
name: bond-supply-and-cashflow-trading
description: 'Trades and reads government-bond supply and cash-flow events in G10 - auction concessions and auction-cycle trades, auction scoring (tail/through, bid-to-cover, takedown), issuance calendars and net cash requirement (NCR, DV01 supply), redemption/coupon reinvestment, buybacks and issuance cuts, QT and central-bank purchase/sale supply, on/off-the-run and new-issue cycles, low-coupon scarcity, month-end index extension. Use when asked about auction concession, pre-auction cheapening, WI, tail/stop-through, takedown, bid-to-cover, refunding/QRA, DMO remit, net supply, NCR, redemptions, coupon reinvestment, buyback, QT, rinban, SOMA/Fed runoff, OTR vs old, specialness, new issue premium, syndication, supply calendar, or "is supply priced". Bills, TGA and debt limit: stir-bills-and-money-market-spreads; term-premium decomposition: macro-fiscal-supply-and-term-premium.'
---

# Bond supply and cash-flow trading

Governments, central banks and index managers move bonds on a known schedule. Dealers cheapen a bond into its
auction to make balance-sheet room, then it richens as inventory is distributed; coupons and redemptions put cash back into
the same market; buybacks, QT and issuance cuts change the free float of duration. The RV edge is small per trade (a few bp)
and regime-dependent, so the skill is mostly **arithmetic (how much duration must the market absorb, and when)**,
**event-study discipline (windows, hedges, costs, sample size)** and **knowing what is already priced**.

Conventions used throughout: yields, spreads, tails and P&L in bp; a trade on a yield or spread level is `pnl = direction x
(x_exit - x_entry)` with direction +1 for a short bond / pay-the-spread position (profits when yield or spread rises) and -1
for a long. EGB asset-swap spread = bond yield minus swap rate (positive = bond cheap to swaps, `govt_minus_swap`); US swap
spread = swap minus Treasury (`swap_minus_govt`), so supply that cheapens Treasuries makes the US spread **more negative**
(`swap_spreads.sign_convention` travels with every row). Treasury-vs-OIS: use `UST yield - OIS`, positive = Treasuries cheap;
source notes quote it both ways, so normalise before reusing any level. DV01 in currency per bp, positive = long duration.

## When to use
- "Is the 10y cheap into the auction?", "what is the concession in BTPs/OATs/gilts/JGBs/Treasuries?", "post-auction rally".
- "How much supply is coming, in DV01 / net of QT / net of redemptions?", "NCR", "remit", "QRA", "completion rate".
- Redemption or coupon reinvestment windows; month-end and quarter-end index-extension windows.
- Buyback announcements, issuance-cut speculation (20y/30y, DMO mix, MoF super-long), QT redesign, BoJ/BoE/ECB/Fed purchases or sales.
- Bill supply, TGA rebuild, debt ceiling, bills vs OIS, front-end Treasury vs OIS and swap spreads as supply trades.
- On-the-run vs old, reopening cycles, specialness, new-issue premium, low-coupon (tax) scarcity, new bonds entering a futures basket.

## Inputs (data-agnostic)
Canonical tables from [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md) (`references/schemas.md`).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Auction calendar and results (size, WI, stop, tail, cover) | `auctions` | per auction, >= 5y (>= 30 events per issuer/tenor for a signal) | `tail_bp` positive = tailed. Results only after `results_ts_utc`; schedule rows are knowable ahead |
| Bond reference, amount outstanding, coupons, maturity | `bond_static` | point in time (`valid_from`) | Redemptions = `amount_out_ccy` at `maturity_date`; coupon cash from `coupon_pct`, `coupon_freq`; aggregate tap ISINs by line |
| Bond yields/prices, bid/ask, WI flag | `bond_quotes` | daily close, single `snap` | Use close-of-business levels, never auction-time levels; bid/ask for costs |
| Par curve, swap spreads / ASW | `curve_par`, `swap_spreads` | daily | Hedge legs and the "adjusted vs benchmark" spread; state sign convention |
| Repo / specialness | `repo_rates` | daily, own-issue and GC | `specialness_bp = (GC - rate) x 100`; model own-issue repo, not GC |
| Holiday and settlement calendars | `calendars` | forward-looking | Windows count trading days; trade-date vs settlement-date for cash flows |
| Positioning, trade tape | `positioning`, `flows_trades` | weekly / intraday | Optional confirmation (basis shorts, block hedges near pricing) |

Canonical: central-bank and stripped holdings by line (`bond_holdings`, free-float coupons), debt-office issuance and
buyback plans (`issuance_plan`), and buyback operations (`auctions` with `operation=buyback`). Not canonical, ask the
user or the data adapter: financing tables (QRA/remit/completion rates), dealer takedown and allotment by investor
class, buyback offers, TGA and bill forecasts. If an input is missing, ask for it or hand off to the `rv-data-engineer` agent.
Never invent values.

## Method

### 1. Size the supply (what the market must absorb)
1. **Gross to net.** `NCR = gross supply - redemptions - free-float coupons - net change in central-bank holdings`
   (QT = negative change, so it raises NCR one-for-one). Report with and without QT to isolate it, by issuer and month, and
   completion vs the 3y average. Redemptions and coupon cash come from `bond_static`; the central-bank share is user-supplied.
2. **Duration, not notional.** `DV01_supply = notional x modified duration x 1e-4` (currency per bp); convert to 10y-equivalents with
   the DV01 ratio. The same notional with the same DV01 means no extra duration to absorb. Net long-end supply = gross - buybacks.
3. **US waterfall.** `net coupon = gross coupons - (coupons maturing - Fed rollover) - buybacks`; `net bills = borrowing need -
   net coupon`; net supply to the public adds Fed runoff. Bills are absorbed with cash, coupons add duration risk.
4. **UK remit.** `funding need = CGNCR(ex) + redemptions + carry-forward`, funded by bills, NS&I, gilts. Forecast monthly CGNCR
   with historical seasonal averages (they beat the official monthly profile) and stress a range.
5. **Forward supply percentile.** Rolling 6-week forward DV01 of coupon supply, bucketed into terciles against history. Low
   forward supply was followed by 10y rallies over 1-2 weeks; the market prices supply 4-6 weeks ahead, so 2 weeks beats 4. Point
   in time: use only sizes announced by the as-of date and expanding-window terciles (full-sample terciles look ahead).
6. **Cross-market duration gauge.** Weekly duration supply net of central-bank purchases and buybacks (USD mn/bp) against the prior-year weekly
   average, by market (week of 5 Oct 2026: UST ~1.7x, EGB 0.3x, gilts 0.4x, JGB ~2x; Goldman Sachs, 2 Oct 2026): ranks where supply is heavy.
7. **Buyer-side balance.** Net coupon supply ex-central bank in 10y-equivalents against projected buyer absorption (foreign,
   pensions/insurers, banks, funds, households); the residual must clear on price. Use direction, not point estimates.

`scripts/supply_arithmetic.py` implements 1-3 and the rollover-cap mechanics; detail in
[references/ust-supply-and-buybacks.md](references/ust-supply-and-buybacks.md) and
[references/g10-issuance-and-cb-operations.md](references/g10-issuance-and-cb-operations.md).

### 2. Auction-concession event trade
1. **Event list** from `auctions`: tapped bond or, for a new line, the closest shorter maturity. Exclude syndications, exchanges,
   private placements, linkers (unless testing linkers) and aid-programme issuers. T = auction date, close-of-business levels.
2. **Default windows (EGB).** Pre-auction: short at T-5 close, exit T-1 close (longer is better: T-4 and T-3 cut P&L from 3.4bp to 2.3 and
   1.3). Post-auction: long at T-1, exit T+4. Cash-flow reinvestment: T-1 to T+3 on a trade-date basis.
3. **Measure and hedge.** Trade the **curve-adjusted spread vs Germany**, not the outright: `S = (ASW_c - ASW_DE) - beta x
   EA_mm_spread`, `beta = bond spread to the maturity-matched German par yield / weighted EA maturity-matched spread` (a ratio,
   fixed at entry, not a regression beta). Outright concession P&L mostly reflects the yield trend (EMU yield fell ~3.75% to 1.30% over
   the sample). In the US use curve/fly packages (2s10s, 2s5s10s) or swap/OIS spreads, which are "cleaner exposures to supply" than outrights.
4. **Grid, not a point.** For entry in -10..0 and exit in -5..+10 compute n, mean, hit, Sharpe, `score = hit x Sharpe`
   (`scripts/supply_event_grid.py`). The best of ~100 correlated cells is biased up (selection): prefer a neighbourhood of cells that agree, a score ranking and a regime check (compare the full
   sample with the last 6 months and with the prevailing curve regime). Minimum 30 events for a signal; 12 events (the usual US
   10y sample) is colour. Events of different countries/tenors in the same week share the market move: cluster standard errors by
   week (pooled n overstates independence) and hold out the last period.
5. **Costs.** Round trip = half the quoted bid/ask spread in bp on each leg, twice (use `bond_quotes` bid/ask yields), plus repo
   cost if the short is special (a bid/ask yield gap in bp is `(bid_ytm_pct - ask_ytm_pct) x 100`, positive; one round trip pays it once
   per leg, weighted by the leg's DV01 ratio). Net P&L must still be positive in at least two sub-periods; the published concession is pre-cost and
   shrank to 0.5-1.3bp in 2013-15 when liquidity normalised.
6. **Do not scale with size.** Auction size (% outstanding) and payment size had R2 of 6% and 10% on P&L: no size signal.

### 3. Reading an auction result (after the fact, and as a preview)
| Metric | Rule |
|---|---|
| Tail / through | `tail_bp = (stop - WI) x 100`; > 0 weak, < 0 strong. Duration-adjust across tenors; ignore when non-competitive bids are large. Other "tails" differ (MoF: gap between the pro-rata and average accepted yield, always >= 0): do not mix definitions |
| Bid-to-cover | vs the tenor's 3- and 6-auction average; inflated by dealer bids and self-bids |
| Takedown | high PD share = weak; high direct/end-user = strong; indirect proxies foreign demand for coupons, **not for bills** |
| Strength score | mean z of (-tail, cover, takedown) vs the previous 12; two strong auctions in a row are not bullish on their own (`scripts/supply_arithmetic.py strength`) |
| Preview | yield change since last auction, richness vs wings adjusted for rate level and slope, WI roll vs carry erosion |

For EGB RV dashboards z-score (3m) the yield, spread to the fitted curve, fly vs surrounding bonds, spread vs the closest-rated
bond and CAS to swaps; buckets below -2 rich, above +2 cheap, linkers on real yield and BEI. German auctions are not readable
(retention, anonymous taps, no primary dealers); JGB tails use the MoF definition, while BoJ rinban semantics of cover flip.

### 4. Redemption and coupon reinvestment
Cash received on date T is reinvested in the same market, so buy the 5y bond vs Germany on the curve-adjusted spread (direction -1: profits as the spread tightens) at T-1 close, exit T+3 close
(T on a trade-date basis: the date whose trades settle on the payment date). Evidence is weak (0.4bp, 51% hit) and positive mainly in BE, NL,
ES and FR; in IT it is swamped by the auction cycle. Treat as a tilt that adds to a concession view, not a standalone trade. Larger
cash flows do not help. For Formosa-style callables, forecast redemptions as `sum over bonds of P(call at current yields) x notional`.
Quasi-passive reinvestment towards a ~10y WAM underlies the German March/May 2s10s flattening. Realised return equals the
yield only if coupons reinvest at that yield: `realized_yield()` in the arithmetic script (2.375% 30y bought at 100.6875 returns 1.778% at 0%
reinvestment and 3.207% at 5%, Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022).

### 5. Supply to spread regressions
1. Regress the spread, not the outright: 2y Treasury-OIS / 2y swap spread on **12m rolling private (ex-Fed) coupon supply**, back end on
   private WAM. Coupon-only supply fits the front end better than coupon+bill (R2 0.61 vs 0.21). Both sides are persistent levels:
   the R2 is an in-sample level fit, so use HAC standard errors, test changes or out-of-sample, and expect a spurious-fit risk.
2. Bill supply matters only contemporaneously and only vs OIS at the front end; model the 3m **flow**, not the stock (paydowns take
   bills to about -50bp vs OIS, issuance about 0 to +15bp).
3. **Haircut historical betas to 25%** (stock effects) before sizing a view. Exit when the term-funding-premium residual is within one standard
   error of fair value (SE 0.3 in the JPM model).
4. Check what is priced: once the supply thesis is consensus, flip the trade on an unpriced catalyst (early end of QT, TGA path, coupon-size change).

### 6. Buybacks, issuance cuts and QT
1. **Classify the operation**: liquidity support (off-the-runs; plumbing) vs cash management vs price management (off-cycle,
   double-size, after a yield high). Price management gets faded; the market infers the threshold (e.g. a 30y level) and treats announced
   floors as minimums.
2. **Net it**: gross - buyback = net long-end supply; a doubling from $2bn to $4bn per operation is a few $bn in a $100bn quarter ("does
   not move the needle"); size is secondary to the signal. Add the funding leg: bill-funded buybacks cheapen 3m/6m and flatten the curve.
3. **Read execution**: offers/max (record offers concentrated in 2 CUSIPs = holders de-risking, bearish even if the size is full), price paid
   vs mid, RMSE of the spline fit by sector. Buybacks show in RV (compressed spline errors, wider 30y swap spreads), not outright yields.
4. **Escalation ladder** (Treasury): bigger buybacks; no coupon increases; cut 20y/30y sizes; end the 20y. The 20y trades poorly vs 10s/30s, so
   10s20s steepeners/long-20y are the cleanest expression. DMO/MoF cuts have short half-lives and smaller repeated effects.
5. **CTD effect**: buybacks and issuance surprises are nonsystematic spread shocks that raise switch-option value: re-run the basket after
   any announcement (see [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md)).
6. **QT**: track DV01 sold vs total, auction clearing spread vs mid (positive = concession), which bonds are sold (low coupons?), passive
   run-off of short issues (removes collateral, long gilts vulnerable to specialness). Pro-rata purchases or sales hit hardest where captive
   holders are concentrated: check free float, not outstanding (`free_float_after_purchase`). Structural QT changes are one-off repricings.
7. **Purchase sizing**: operations too large vs dealer supply can sell off instead of rally (BoJ April 2013).

### 7. On/off-the-run, specialness and new issues
- Specialness (US 10y) is low after the auction, peaks the day before the first reopening (avg 156bp) and falls below 20bp before the next new
  issue: short demand vanishes after the reopening. Use own-issue repo in carry; a special new issue can flip short-basis P&L sign.
- OTR premium is pronounced in US/IT/ES, small in FR, absent in DE/JP; benchmark switches fake slope/fly jumps (use spline or
  constant-maturity series).
- 5y futures template: buy the OTR 5y basis early in the cycle, sell it late (OTR cheapens ~5bp vs old in the 1.5 months before the next auction;
  four cycles, 2000-02; selling is negative carry while the OTR is special). Cash version, reopening RV: long OTR vs short old financed in repo
  for ~1 week; cost = repo minus reverse-repo spread (20bp in the example) (Conks, Demystifying the Repo Market Part III, 28 May 2024). A high
  new-issue premium (yield above the fair value from surrounding issues) signals indigestion and invites flipping (Düring, 2021).
- Do not short the "obvious" rich bond into a refunding without stops: crowded, squeezable, special rates have no floor.
- New issues in a futures basket: if the new bond will be CTD, back out its implied price from the future; unissued cheap CTD in the back month:
  buy the calendar; a bond leaving the basket loses its CTD premium (buy the second CTD's basis or sell the calendar).

### 8. Known-demand calendar windows (candidate set, test before use)
Month-end duration extension (long duration from 3 business days before month-end to 1 day after; receive 10y swap around quarter-end),
pre-auction concession (T-2 to T+1 as the short-window alternative to T-5..T-1), coupon reinvestment (5y, T-1 to T+1), quarter-end
repo/balance-sheet (2y, T-2 to T), corporate issuance rate-lock (hedge from settlement-1 to settlement in the tenor bucket 0-3Y: 2Y,
3-7Y: 5Y, 7-12Y: 10Y, 12-20Y: 15Y, 20Y+: 30Y). These are hypotheses from known flows, not validated edges: run them through the grid and
[quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md). January corporate supply (13% of annual
financial issuance, ~8.4y average maturity) historically tightened long swap spreads. Callable/structured supply is handled in
[vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md).

## Worked examples
1. **EGB pre-auction short** (J.P. Morgan, Follow the cash flow, 15 Sep 2015): 1330 trades, avg 3.4bp, 67% success, IR 2.5, before costs; by country ES 5.1bp, IT 4.3, BE
   4.0, FR 2.3, AT 2.1, NL 0.9, FI 0.3. Adjusted hedge IR 2.5 vs non-adjusted 1.2 vs outright 1.1. With an illustrative 1.5bp round-trip cost the net edge is ~1.9bp:
   viable on ES/IT/BE, marginal on FR/AT, not on FI/NL. Italy-Spain switch exit T-2: 2.0bp per trade, IR 3.0 vs T-1 0.7bp, IR 1.1. Beta check (script): bond 80bp over German m/m, EA average 50bp, beta
   1.6; if the EA spread widens 10bp and the bond 16bp, P&L is 0; the bond alone +20bp gives +4bp.
2. **UST auction-window grid** (BofA, US Treasury auction primer, 8 Mar 2024): last 12 10y auctions, 2s10s steepener best at entry -9 / exit -3 = +3.5bp; exiting after the auction
   lost (-3/+5 = -5.8bp); hit 55-58% and Score <= 23%. 2s10s flattener entry -3 / exit -1: +2.9bp, Score 52%. In the 2022 edition the sign was opposite (BofA, UST RV Primer, 2 May 2022): 12
   events are a regime snapshot, not an edge.
3. **US financing waterfall** (BofA, Lower UST WAM => backdoor easing, 2 Jul 2025): FY26 borrowing need $2,100bn, net coupon $1,275bn so net bills = $825bn; FY27 $1,033bn coupon,
   $1,067bn bills, bill share 24.3% vs a 20-25% tolerance. Stable vs growing coupons = $1,003bn less 10y-equivalent issuance, ~30bp lower 10y.
4. **SOMA rollover** (BofA primer): $80bn maturing, $60bn cap: $20bn reinvested; 75% maturing mid-month gives $15bn there; a 3y that is half the mid-month offering gets $7.5bn. Add-ons
   do not change gross auction size.
5. **Long-end buyback, Aug 2026** (Financial Times Alphaville, 20 Aug 2026; Citi, Top of Mind, 21 Aug 2026): $2bn to >= $4bn per operation, gross 20y+30y $111bn, net $97bn vs $103bn; 30y -8bp
   on the day to 5.21%, round-tripped to 5.24% next day (half-life ~1 day), bills cheapened. Read: signal and bill-funded flattening, not duration relief. Late-Sep 10-20y operation took the
   full $6bn on $46.4bn offered in 2 CUSIPs (Goldman Sachs, 2 Oct 2026): de-risking, bearish.
6. **Front-end supply trade** (BofA, Trade idea: sell 2y spreads, 27 Sep 2017; buy 2y vs OIS, 30 May 2018): sell 2y Treasury vs OIS at -3.5bp, target +5, stop -8, on 2y coupon $26bn to $35bn and
   record foreign-official custody; it reached ~16bp cheap. Flipped to buy at 18bp cheap, target 0, stop 25 once supply was priced and an early QT stop looked likely.
7. **Gilt low-coupon scarcity** (BofA, 5 Aug 2024): sell 4.125% 2027 / buy 0.125% 2028 on ASW, entry +1.8bp (Nov 2022), target -25, closed -25.4bp (Aug 2024); QT sales fed the scarcity; risk was a new benchmark.
8. **Term funding premium** (J.P. Morgan, Buying back time, 19 Aug 2026): fair value 4.2 vs actual 4.7 (bp per year of duration) then 4.4 after the buyback upsizing; the -0.3 move implied WAM expectations ~3 months
   shorter, judged outsized, so 10s/30s spread-curve steepeners were closed at +1.4bp.

## Signals & interpretation
- **Pre-auction short**: spread-vs-Germany or curve-adjusted level has not cheapened > 1 SD of 5-day change into T-5 (otherwise it is priced), instrument liquid, own-issue repo
  not special, a NCR or DV01 supply percentile in the top tercile. Cut when the concession already exceeds the historical 3-4bp mean.
- **Post-auction long**: tail <= 0 and strength score >= 0 add to the case; a large tail with weak takedown argues for T+4 exit or skipping it.
- **Supply percentile** top tercile (heavy forward DV01) favours bear steepeners and swap-spread tighteners (in US sign: swap spread more negative); bottom tercile favours 1-2 week
  rallies. Seasonality is a tailwind, not a signal: it often does not line up with direction (US Aug, Canada May/Aug rally despite issuance), use it for curves and spreads.
- **Bills**: net bill supply falling (paydowns, debt-limit) means bills richen vs OIS; the post-resolution rebuild cheapens funding and bills (a few bp, up to 6bp in 2025; 5-12bp on SOFR-IORB).
  Strip non-TGA cash injections and quarter-end prints.
- **Buyback/cut announcement**: fade if it responds to a price level, hold if it responds to plumbing; take profit when the implied WAM or supply change looks implausible vs deficits.
  A large fair-value residual into heavy supply is not a timing signal (catching a falling knife).
- **Exit rule**: close concession trades at the planned exit date regardless of P&L; close supply-regression trades within one SE of fair value or when the catalyst is priced.

## Pitfalls
- Macro swamps supply: deficits rise in slowdowns when duration gets a bid; local auction effects are real but often overwhelmed. Do not attribute every long-end sell-off to supply.
- Small samples and sign flips (12 US events); optimum windows drift (IT-ES T-1 to T-2): re-test periodically.
- Using auction-time levels or settlement-date closes inflates edge; use close-of-business on trade dates, and `results_ts_utc` to avoid look-ahead on tails and takedown.
- Outright concession P&L embeds the yield trend; strip it (curve-adjusted spread vs benchmark).
- Bid-to-cover and indirects are weak proxies; calendar pre-announcement (NL) spreads the concession; German auctions are unreadable.
- Crowded shorts into refundings squeeze; model own-issue repo; fails penalty makes specials unbounded; haircuts can jump at stress (3% to 80%).
- Supply is endogenous in credit (+0.22 return correlation with 1m-lagged supply, Willer & Saunders 2026): do not mechanically fade credit supply; for govvies supply effects are stronger.
  Rule of thumb for a large supply overhang (QT, sales): about half removed is often enough for the price to bottom (same source).
- A supply shock overshoots then partly reverts when capital is slow (Duffie, Dark Markets, 2012): a pure cost reprices at once, so a gradual fade is the tradable signature.
- "ASW" is not one number: the same bond was 40bp yield-yield and 37.6bp par-par (Darbyshire, 3rd ed., 2022); a DMO or issuer hedging with swaps leaves that ASW risk.
- Buybacks funded by bills are not WAM-neutral; unscheduled support signals stress and damages "regular and predictable" issuance, which raises term premium.
- Debt-limit analogs: condition on the ON RRP buffer (2021 and 2023 are not comparable); normalise sign conventions between exhibits (FF - SOFR vs SOFR - FF; OIS - UST vs UST - OIS).
- Quarter- and year-end distort repo, RRP and swap spreads; supply-driven RV is not an arbitrage once repo, borrow costs and bid/ask are included.
- Do not extrapolate from one-off structural events (BoE QT redesign) or from stale mechanics (April 2023 BoJ YCC operations); treat dated 2026 figures as examples, verify live.

## Output
Return (1) a **supply table**: issuer, window (week/month), gross, redemptions, coupons, CB change, NCR, DV01 supply and 10y-equivalents, vs 3y or prior-year average, completion %, with/without QT;
(2) an **event-study grid** (n, mean bp, median, hit, Sharpe, score, IR, costs) with the chosen cell, regime split and the ones next to it; (3) an **auction scorecard** (tail, cover,
takedown, strength z) when a result exists; (4) a **trade card**: instrument and hedge ratio, DV01 per leg, entry/exit dates (T-offsets), target, stop, expected net edge after costs,
what is priced, catalyst, invalidation; (5) data caveats (missing inputs, sign convention used). Hand off to `rv-trade-idea-writeup`; sizing to
[port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md); costs to [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md).

## Scripts
- [`scripts/supply_event_grid.py`](scripts/supply_event_grid.py): entry/exit grid for any event list (auctions, redemptions, coupons, buybacks) on a bp series; n, mean, median, hit, Sharpe,
  score = hit x Sharpe, annualised IR; handles non-trading-day events and drops windows beyond the sample. `python scripts/supply_event_grid.py --help`; `--selftest` checks a constructed concession with known mean, hit and Sharpe.
- [`scripts/supply_arithmetic.py`](scripts/supply_arithmetic.py): NCR, US net coupon/bill waterfall, rollover-cap add-ons, single-price award, free float after pro-rata purchases, DV01 supply, realised
  horizon yield, hedge beta and curve-adjusted spread, auction strength z-scores (`strength` CLI on the canonical `auctions` table). `--selftest` checks published worked examples.

Detail: [EGB backtest tables](references/egb-follow-the-cash-backtest.md) | [UST supply, buybacks, bills, debt limit](references/ust-supply-and-buybacks.md) |
[G10 calendars, QT and central-bank operations](references/g10-issuance-and-cb-operations.md).

## Related skills
- [macro-fiscal-supply-and-term-premium](../macro-fiscal-supply-and-term-premium/SKILL.md): deficits, issuance mix and term premium behind the supply path.
- [stir-bills-and-money-market-spreads](../stir-bills-and-money-market-spreads/SKILL.md): bills vs OIS, bill supply, MMF demand, debt-limit dynamics.
- [stir-central-bank-balance-sheet-and-reserves](../stir-central-bank-balance-sheet-and-reserves/SKILL.md): QE/QT mechanics, reserves, RRP/TGA funding spreads.
- [stir-repo-and-funding-plumbing](../stir-repo-and-funding-plumbing/SKILL.md): specialness, issuance-day repo, quarter-end effects.
- [bond-rich-cheap-fitted-curve](../bond-rich-cheap-fitted-curve/SKILL.md): fitted-curve residuals, supply/age/deliverability regressors, OTR premia.
- [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): swap-spread and ASW supply effects, sign conventions.
- [spread-cross-market-govies](../spread-cross-market-govies/SKILL.md): EGB spreads vs Bund, cross-market hedges.
- [fut-ctd-switch-and-delivery-options](../fut-ctd-switch-and-delivery-options/SKILL.md): buybacks and new issues changing the CTD.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md): OTR basis and specialness in basis trades.
- [flow-structural-alm-demand](../flow-structural-alm-demand/SKILL.md): pension, insurer, bank and reserve-manager demand against supply.
- [vol-structured-flows-and-vega-supply](../vol-structured-flows-and-vega-supply/SKILL.md): callable (Formosa) issuance as vega and receive-fixed supply.
- [quant-seasonality-and-calendar-effects](../quant-seasonality-and-calendar-effects/SKILL.md): month-end, quarter-end and refunding seasonals.
- [fi-g10-market-conventions](../fi-g10-market-conventions/SKILL.md): settlement, day-count and issuance conventions per market.
- [bt-backtest-design](../bt-backtest-design/SKILL.md) and [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): event-study design and cost haircuts.
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): multiple testing across grid cells, walk-forward on tiny samples.
- [quant-time-series-econometrics](../quant-time-series-econometrics/SKILL.md): HAC errors for rolling-supply regressions.
- [fi-balance-sheet-and-regulatory-costs](../fi-balance-sheet-and-regulatory-costs/SKILL.md): dealer balance-sheet limits behind the concession and quarter-end repo.
- [flow-positioning-cftc-and-surveys](../flow-positioning-cftc-and-surveys/SKILL.md): CFTC, survey and real-money positioning.

## References
- J.P. Morgan, European Rates Strategy - Follow the cash flow: trading strategies around supply, redemptions and coupon payments in euro government bond markets (Salford, Chordia, 15 Sep 2015): core EGB concession and reinvestment backtests.
- BofA Global Research - US Treasury auction primer (Craig, Cabana et al., 8 Mar 2024): QRA/calendar, auction scoring, Score = hit x Sharpe grids, SOMA add-ons, buyback design.
- BofA Global Research - UST RV Primer: a hitchhikers guide to RV on the UST curve (Zhang, Braizinha, Axel, 2 May 2022): dealer balance-sheet concession mechanism, opposite-sign 2022 grids.
- Citi Research - US Rates Weekly: What to expect when you're expecting a turn (20 Apr 2018): auction-week seasonality and forward DV01 supply terciles.
- Citi Research - US Rates Weekly: The rocky road to a steeper curve (18 Jan 2019) and All it takes is a little push (4 Oct 2019): supply regressions, bill-supply and WAM betas.
- Citi Research - US Rates Weekly: Eat, pay, spend (27 Mar 2020) and Can Secretary Bessent and Chair Warsh save the curve? (21 Aug 2026): TU/OIS bill-supply trade, buyback escalation ladder.
- Citi Research - US Rates Weekly: Learning on the job (2 Aug 2019); Pension plan for 20s? (9 Oct 2026); OAT of the blue (2 Oct 2026): refunding tail model, auction-strength screen, supply-cut steepener.
- Citi Research - European Rates Weekly: What to do about OATs? (1 Oct 2026); European Rates Strategy: Latest views (20 Aug 2026); A QT revolution (17 Sep 2026); A narrative shift looms (17 Mar 2022): NCR, completion, BoE QT redesign, remit arithmetic.
- BofA Global Research - Lower UST WAM => backdoor easing (Swiber, Cabana, Craig, 2 Jul 2025); UST supply & demand in '25 (26 Nov 2024); Basics of UST supply & demand (24 Jun 2024): financing waterfall, bill share, buyer absorption.
- BofA Global Research - Funding & debt limit: history lessons (27 Jun 2025) and X-date shift (7 Feb 2025): debt-limit analog event study and bill-supply path.
- BofA Merrill Lynch - US Rates Alpha: Trade idea: sell 2y spreads (Axel, Cabana et al., 27 Sep 2017) and Trade idea: buy 2y Treasury vs OIS (Cabana, Axel, 30 May 2018): front-end supply trade and its flip once priced.
- BofA Global Research - US Rates Watch: Fed QT Beyond Taper & Funding Impact (Cabana, Craig, 22 Oct 2021): funding-spread regressions on reserves and debt ex Fed.
- J.P. Morgan - Buying back time (19 Aug 2026); Global Fixed Income Markets Weekly (21-22 Aug 2026): term funding premium model, TBAC buyback score, DMO/MoF event studies.
- Citi Research / Financial Times / Wall Street Journal / Goldman Sachs - Aug-Oct 2026 UST buyback coverage (Buy Gold, 19 Aug; Top of Mind, 21 Aug; Alphaville, 20 Aug; Druckenmiller, 24 Aug; The Week That Was, 2 Oct): size vs signal, netting, execution read.
- Barclays - Interest Rate Derivatives: Swap spreads: The Bright Spot in US rates (Mok, Nashikkar, 30 Sep 2026): buyback effect through RV metrics.
- Barclays - US short interest rate primer (Abate, Jan 2025): QT design, debt-ceiling rules, bill share, bill-OIS vs supply flow; Barclays Global Rates Weekly (2 Oct 2026): AFT buybacks, BoE QT sales.
- BofA Global Research - Low coupon/high coupon Gilt spread trade hits target (5 Aug 2024); Will retail discover Gilts? (10 Nov 2022): tax-driven low-coupon scarcity.
- BofA Global Research - Japan Rates Basics (Yamashita, Yamada, 24 Apr 2023): MoF auction and BoJ rinban reading, FY plan; Citi Japan Rates Weekly (21 Aug, 2 Oct 2026): JGB supply tables and FY plan.
- BofA Securities - Bond market seasonality explained (Ciana et al., 6 Jun 2022): market-by-market issuance and reinvestment seasonals.
- J.P. Morgan - Times like these: structural changes in off-the-run Treasury pricing (10 Feb 2016); Renewed Formosa supply continues to flatten the long end (21 Feb 2020): OTR roll cycle, callable supply.
- Citi Research - Corporate supply to bring spreads tighter (3 Jan 2017): January corporate supply seasonality.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): OTR/new-issue basis cycle, buyback CTD switch, European calendars.
- Alexander Düring - Fixed Income Trading and Risk Management (Wiley, 2021): auction metrics, NIC, Finanzagentur, free float, BoJ 2013, per-country conventions.
- Tuckman & Serrat - Fixed Income Securities (4th ed., Wiley, 2022): specialness cycle, reinvestment, issuance calendar, ECB QE constraints.
- Huggins & Schaller - Fixed Income Relative Value Analysis (2nd ed., Wiley, 2024): supply regressors in fitted curves, specialness option value, new-issue basket pricing.
- Conks (Substack) - Demystifying the Repo Market Part III (28 May 2024); The Great Rebalancing (16 Jul 2025); The Stealth Liquidity Squeeze (14 Aug 2023): reopening trade, bill share, TQT.
- Dirk Willer & Alex Saunders - Trading Global Macro Markets (Wiley, 2026): credit supply endogeneity, supply-overhang rule of thumb.
- J H M Darbyshire - Pricing and Trading Interest Rate Derivatives (3rd ed., Aitch & Dee, 2022): DMO rate locking, issuance swaps, ASW definitions.
- Darrell Duffie - Dark Markets (Princeton University Press, 2012): slow-moving capital and post-supply reversion.
- Federal Reserve Bank of New York, Liberty Street Economics - Dealer Trading and Positioning in Floating Rate Notes (Fleming, Wahlers, 26 Mar 2018): auction-cycle dealer event study.
- J.P. Morgan - Cross currency basis 4Q24 Outlook (26 Sep 2024) and Drivers of cross currency basis (11 Mar 2015): issuance-adjusted basis models.
