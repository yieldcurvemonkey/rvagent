---
name: bt-backtest-design
description: 'How to build an honest backtest of a G10 rates relative-value strategy - the signal -> position -> P&L chain, vectorised panel vs repricing/event-driven engines, execution lag and snap alignment, point-in-time data and publication lags, carry/roll-down accrual, frozen-leg tickets and move-based delta re-hedging, rolling futures and generic series, product P&L recipes, controls and known-answer tests. Bundles a lean vectorised backtester with a look-ahead truncation test. Use when asked to backtest a spread, curve, fly, swap spread, bond/futures basis, STIR or vol trade, build or review a backtester, check look-ahead, lag, point-in-time or survivorship bias, stitch generic or roll-adjusted series, accrue carry, size by DV01 or vol target, or decide what to report (hit rate, Sharpe, cost sweep, trial log). Also covers on-the-run / when-issued roll adjustment, paper-vs-live gaps and always-on / ex-direction controls. Statistical validation (overfit, DSR, CPCV, multiple testing): bt-validation-and-overfitting.'
---

# Backtest design for rates RV

A backtest is a hypothetical simulation. It cannot prove an edge. It discards bad ideas, sizes turnover and cost
sensitivity, and shows how a fully specified rule behaves across regimes (AFML ch.11: "the purpose of a backtest is
to discard bad models, not to improve them"). In rates the usual failure is not the statistics but the engine: a
signal that sees the close it trades on, a constant-maturity series standing in for an aged swap, carry left out,
or a mark built from snaps taken hours apart. This skill fixes the mechanics: what the engine must do, in what
order, in which units, and which tests prove it does. Validation statistics (walk-forward, deflated Sharpe, PBO) live in
[bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md); costs and liquidity in
[bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md); attribution and tearsheets in
[bt-performance-attribution](../bt-performance-attribution/SKILL.md).

## When to use
- "Backtest this 2s5s10s fly / 5s30s swap spread / 10y10y vs 25y10y flattener / SOFR pack / CTD basis / straddle."
- "Is my backtest look-ahead biased?", "what lag should I use?", "why is my equity curve flat/too good?"
- Building or reviewing a backtester: vectorised panel vs full repricing, event-driven loops, roll handling.
- Accruing carry and roll-down, financing (repo, specials), coupon cash, DV01 sizing, re-hedging rules.
- Stitching generic futures or on-the-run series, roll adjustment, point-in-time (PIT) macro or auction data.
- Deciding the minimum a backtest must report before it goes to a trade write-up.

## Inputs (data-agnostic)
Canonical tables are defined in [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md).

| Input | Canonical table | Granularity / history | Notes |
|---|---|---|---|
| Signal values per package and decision date | `signals` | daily; `date` = information date, `snap` stated | A signal dated t uses only data known at that snap on t |
| Par/zero curves, forward grid | `curve_par`, `curve_zero` | daily, same `snap` for every leg; >= 252d warm-up + test span | Never mix snaps inside one series |
| Futures prices, generic-to-specific map | `fut_quotes`, `roll_map` | settle or close, never mixed | Roll rule must be knowable on that date |
| Bonds, repo, specials | `bond_quotes`, `repo_rates` | clean, accrued and dirty kept separate | Own-issue repo, not GC, for the financed leg |
| Calendars, central-bank meetings | `calendars`, `cb_meetings` | per market and exchange | Fri->Mon accrual = 3 calendar days; holiday-aware expiry rules |
| Macro, survey, auction results | `macro_series` (`pub_ts_utc`), `auctions` (`results_ts_utc`) | one row per vintage | Use the vintage known at the decision time |
| Outputs | `positions`, `trades`, `pnl` | daily | `pnl` = mtm + carry + financing + cost = total (checked) |

If an input is missing (e.g. no release timestamps, one snap only, no repo for the financed bond), say so, restrict the
claim, and ask the data adapter for it. Never forward-fill or invent values.

## Method

### 1. Fix the question and the stage
1. **Information analysis first** (Grinold-Kahn ch.12): turn the signal into a portfolio each period, evaluate it
   unfettered (IC, quantile monotonicity, hit rate by signal bucket). **Then** the backtest: add turnover, tradability,
   carry, financing and cost. Match the rebalance period to the signal's information period.
2. Write the full specification (universe, signal, thresholds, sizing, hedge rule, roll rule, costs, sample) **before**
   the first run. A fully specified model is run once; if it fails, change the idea, not the dial ("Don't hunt for settings
   until something passes"). Every run goes in a trial log with its config; the row count is N for the deflated Sharpe.
3. Pre-register the list of cells (parameter grid). Any scored cell not on the list is a trial-count leak.
4. Checklist of the usual sins (Luo et al. via AFML ch.11): survivorship, look-ahead, storytelling, data snooping, costs, outliers (a few extreme days drive the result), shorting/financing.
   For an event or driver study, first trade the realised sign of the driver (perfect foresight, not tradable) to see which variable is worth forecasting, then test the lagged tradable version;
   combine binary sub-signals by "all agree" (higher IR, rarely on) or by summing (lower IR, more often on) (Willer & Saunders).

### 2. Choose the engine and certify it
| Engine | Use for | Weakness |
|---|---|---|
| **Panel / vectorised** (dates x packages matrix; P&L = lagged position x change in spread level) | Parameter grids, signal screens, first look; [`scripts/backtest.py`](scripts/backtest.py) | Constant-maturity series do not age: no true carry/roll, no re-strike, overstated hedged Sharpe |
| **Repricing engine** (tickets marked off the curve every day) | The number you quote: carry, roll, hedge drift, convexity | Slower, more state, more ways to be silently wrong |
| **Event-driven loop** (triggers -> orders -> execute -> freeze instruments -> unwind -> mark) | Path-dependent rules: stops, re-hedging, time exits, basis to delivery | Silent exceptions; needs artifact asserts |

- Rule: **the panel is a signal tool; the engine is the number.** Grid-search on panels, then certify the top 2-3 cells
  through the repricing engine and report that. In one convexity project constant-rank par panels overstated hedged Sharpes
  1.5-6x and understated unhedged dollar P&L 2-3.8x versus repricing aged instruments (Internal convexity RV handover). A tie-out
  of 0.9997 daily-change correlation between panel and engine P&L was achieved; a disagreement is information, not noise.
- **Precompute-and-materialise**: compute the trade calendar in one engine, replay it as dated triggers in the pricing engine.
  Any equity difference is then pricing, not selection.
- **Assert on artifacts** before returning: trades > 0, closed positions > 0, marks non-zero, no equity holes, a sign probe
  passed. A flat equity curve is more often an engine that swallowed exceptions than a market-neutral strategy. Per-step
  `try/except: print; continue` is banned.

### 3. Timing contract (the look-ahead firewall)
```
signal date t  : uses data with knowledge time <= close of t (snap stated)
fill           : at the mark exec_lag marks later (default exec_lag = 1 -> close of t+1)
position h_t   : position held at close t = decision made at close t - exec_lag
P&L(t-1, t]    : h_{t-1} * (S_t - S_{t-1})  + carry + financing  - cost on |h_t - h_{t-1}|
```
Palomar writes it as `R_t = s_{t-1} (z_t - z_{t-1})`. `R_t = w_t' r_t` with `w_t` built on data to t is look-ahead.

| Rule | Default | Reason |
|---|---|---|
| Execution lag | 1 mark after the signal close; ablate 2 and 5 | Same-bar entry on a mark built from asynchronous sources harvests mark noise: measured 0.17-1.13 bp/day noise against true moves of 0.18-0.90 bp/day (Internal convexity RV handover). Lag 0 is a diagnostic only |
| Lag across time zones | 2 days when one leg is timed far from the others (European rate vs USD-timed leg, Asia-Pacific close vs US close) | Willer & Saunders convention; daily-data betas understate cross-market correlation from non-overlap, blend with weekly |
| Rolling stats | z-score, beta, PCA, percentiles use a trailing or expanding window ending at t (or t-1 for betas) | Full-sample z-scores/percentiles are look-ahead in magnitude |
| Warm-up | 252d; z window 60-252; PCA/beta 63-252 | Walk-forward with warm-up t0 of T: the first half of the decisions use on average T/4 + 3t0/4 points (AFML ch.12) |
| Snap alignment | all legs and the signal at one snap | A 17:00 NY vendor snap vs ~15:00 ET futures settle injected 1.82 bp/day of noise on near STIR packs, against true convexity-adjustment moves of ~0.55 bp/day (Internal convexity RV handover) |
| Publication lags | model each series' release timestamp | CFTC positioning: data as of Tuesday, released Friday afternoon (lag 5 days); surveys with discrete updates held constant between updates; IFO/ISM tradable the day after release |
| Parameters | fixed a priori from the spec; never re-fit after seeing OOS | Choose the broad plateau, not the lonely peak |

### 4. Signal -> position rules
- **Z-score** (causal): `z_t = (S_t - mean_L(S)) / std_L(S)` over the L obs ending at t; sign convention `z > 0` = spread rich.
- **Fade state machine** (defaults 60-day window: one quarter): enter `|z| >= 2` (fade: long the spread at `z <= -2`),
  exit at `|z| <= 0.5` or on overshoot, stop at `|z| >= 4`, then stay flat until `|z| < 2` (otherwise the same bar re-enters).
  2.5 gives fewer, higher-conviction trades; 1.5 more and smaller (Brenndoerfer; Chan). Entry/exit levels are fitted
  hyper-parameters: smooth them and test OOS (Palomar ch.15).
- **Linear rule**: `s_t = -clip(z_t / s0, -1, 1)` scales in and out; thresholded is all-in/all-out. Discretise size changes
  (`m* = round(m/d)*d`, d = 0.2) to stop jitter turnover (AFML ch.10).
- **Position size**: the panel engine's unit is `h` = signed ccy per bp of the traded series S (positive = profits when S rises = long the spread).
  For a spread, fly or swap-spread package that is the package DV01. For an outright yield, `h > 0` is a payer (short duration), so the canonical
  `positions.dv01_ccy` (positive = long duration, receive fixed) is `-h`: convert once at the engine boundary and assert the sign on a hand-computed package.
  Fixed target DV01, or vol target
  `DV01_t = target_daily_ccy / std(dS)` over a trailing window through t. Fix the sizing rule a priori and state its
  factor exposure before quoting P&L. Normalise returns by gross notional or DV01, never by the spread level
  (it explodes when the residual crosses zero).
- **Prior-day hedge ratio** in P&L: rolling betas are estimated through t-1.
- **Missing = NaN, never 0**: 0 is a valid position and zero-fill creates spurious positions after demeaning or decay.
- **Overlapping bets**: daily-initiated fixed-horizon trades share returns; effective sample is about `T / holding days`, not T (t-statistics need a Newey-West/block correction, or use non-overlapping bets).
  Report bets, not trades. Drop triggers that fired within the prior window (non-overlapping events).
- **Rebalance day matters**: IR of a 3m-momentum rule ranged 0.3-0.7 with the day of month (JPM, Simple rules to trade
  duration, Oct 2012); a single specification is a noisy estimate. Weekly rebalancing gave no benefit over monthly before costs
  (JPM, Exploiting carry, Jan 2007).

### 5. Position lifecycle: tickets, ageing, hedges
- **Ticket**: store sign, instrument ids with explicit effective and maturity **dates**, strike (fixed rate), notional, open
  date. **Freeze legs at entry.** A relative tenor ("5y") re-resolved at every mark silently prices a fresh at-market package: NPV ~ 0,
  flat equity curve. Never mark an aged position off the constant-maturity series: a 20y5y opened 40 days ago is ~19.89y5y; age
  `a = (t - t0)/365.25`, live start `T = T0 - a`, mark the forward at that start with the same interpolation as the signal
  (Internal backtest spec v0.4, Oct 2026).
- **Carry accrual identity (test it)**: on a zero-move day the ageing P&L equals `carry_per_year * dCalendarDays/365.25` (Fri->Mon = 3x).
  Measure carry by **repricing the aged package**: a repriced 1y roll matched a published 1y carry with correlation +0.991, a running carry-and-roll field
  gave -0.136; translating the curve does not age a struck swap (Internal convexity RV handover).
- **Hedges are new tickets** on the generic forward (never edits to notionals), all on one shared grid; different grids add basis the signal does not see.
- **Move-based re-hedge** (curve gamma `Gamma_c = sum 2*DV01_i*D_i*1e-4`): re-hedge when `|Delta_net| >= |Gamma_c| * 25bp`.
  Without it a convexity trade only earns gamma on the entry-to-exit move. The Sharpe is flat across 15-30 bp thresholds for long-end flatteners; tune over {10,15,25,35}
  and re-optimise when bid/offer changes (Citi, Trading long-dated convexity, 9 May 2019). Roll a long-expiry package once a year.
- **Time of day**: close-to-close realised vol can be inflated by algo flows at the close; hedging around 9am showed the lowest realised
  vols and 5pm the highest (Citi, The art of gamma hedging, 12 Mar 2018). State the hedge time.
- **Roll policy is explicit**: an engine that freezes instruments has no generic roll; rolling is a strategy-level close-and-reopen with its own cost.

### 6. P&L accounting (summary; per-product recipes in [references/pnl-recipes-and-market-notes.md](references/pnl-recipes-and-market-notes.md))
- Components: `total = mtm + carry + financing + cost` (the `pnl` table). `mtm` = clean/NPV change excluding accrual; `carry` = change in accrued plus
  coupon cash; `financing` negative = cost. Dirty-price change plus coupon cash equals mtm + carry, with nothing counted twice. Book coupon
  cash separately, or trades spanning coupon dates dominate.
- Swaps: total P&L is the NPV change of the aged instrument (cash coupons are inside that roll); the carry/mtm split is an attribution (repricing the aged package), not booked cash. Fixings must be in the curve.
- Financing: `financing_ccy = -dir * |MV_dirty| * (1 - haircut) * repo * yearfrac` ACT/360, `dir = +1` long (pays repo, negative = cost), `-1` short (earns the reverse-repo rate);
  repo = GC minus own-issue specialness; fee on the **traded increment**, round trip charged in full.
- Report returns as excess over cash (swap, futures and repo-financed books already are). Do **not** subtract rf again for a self-financing (dollar-neutral, futures, swap) book: excess = R + rf - rf = R. Subtract it only when a
  financing cost is actually incurred (Chan 2009; Willer & Saunders). Sharpe annualised by `sqrt(periods per year)` of the actual trading periods; assumes no autocorrelation.
- Units live in the column name (`_bp`, `_pct`, `_ccy`). A basis stored in decimal made marks 10,000x too small; fly yields in % compared against bp thresholds.
  Assert signs against a hand-computed package each run: a builder that re-signed packages from sign(bpv) entered 15 of 35 flies backwards.
  Quoting a fly as `2b - f - k` vs `b - 0.5(f + k)` changes belly DV01 by 2x.

### 7. Rolling instruments and generic series
- **No position straddles a roll** for futures-based relative series (a constant-rank convexity-adjustment series jumped +0.946 bp/roll, t = 2.7 over 22 rolls). Black out across rolls using
  the **union** of every roll clock in the code (two clocks were one business day apart). Control: with the blackout off, a long book must pick up the artifact.
- **Signal on the constant-rank series, P&L on the dated (spliced) series.** The constant-rank series is stationary because the roll pays back the decay; the spliced series drifted ~20 bp and pushed its 252d z-score to a median of -1.2 so a gate never fired. Splice forward and causally.
- **On-the-run stitching and when-issued (WI) roll adjustment**: at 15:00 on auction day record `WI roll = WI yield - benchmark yield`, apply it to the old benchmark history, and **decay it linearly**:
  `adj_i = WIroll / days * (day_i - beginDay)`, `beginDay` = day after the previous auction, `days` = business days in (beginDay, auction day]. No-decay accumulates artificial drift
  (RiskVal, Generic Time Series Data & Roll Adjustment, 28 Jul 2020). Implication: rebuild the adjusted series **as of each decision date**; the final adjusted history leaks later auction rolls into earlier signals.
- **Multi-leg series ("ETF trick", AFML ch.2)**: model the value `K_t` of $1 invested in the package, never the spread level (time-varying weights make a level series converge with no price move, go negative, ignore cost).
  `h_{i,t} = w_{i,t} K_t / (o_{i,t+1} phi_{i,t} sum|w|)` on rebalance bars `B`, else `h_{i,t-1}`; `delta_{i,t} = p - o` if `(t-1) in B` else `dp`;
  `K_t = K_{t-1} + sum_i h_{i,t-1} phi_{i,t} (delta_{i,t} + d_{i,t})`. Costs go in as a negative dividend, not inside K, or shorting the spread shows fictitious profit.
- Constant-maturity eligibility: `issue_date <= as_of < maturity_date`; compute time to maturity ACT/ACT, not days/365.25 (half a day off at a hard 3.0y cutoff).

### 8. Point-in-time (PIT) data
"Never use data on a date that we could not have used in production on that day" (Paleologo ch.8).
- Release timestamp, not reference period: vendors index macro data by period end, often ~1.5 months before release (AFML ch.2). Revisions: GDP has the first release plus two monthly revisions; using the final value at the first-release date is wrong. Use the `pub_ts_utc` vintage.
- Date identities must hold exactly: `as_of + days_to_expiry == expiry`. A one-day misalignment left median vol ~2% right but widened the dispersion IQR 30x; an expiry rule that returned Christmas Day was fixed to match 263/263.
- Data hygiene before the engine: inner-join inputs, drop weekends, **log** stale rows, never forward-fill; gate: no stale input in the last 3 days. Report cache/match rates (a regex that failed across a timezone offset matched only 66%).
- Curve-derived futures rates need node coverage: error 15.8 bp at ranks 1-4 vs 0.268 bp at 9-12 when the node grid started late. Rule: max tenor >= 3 x n_instruments months + 6 months (quarterly contracts).
- Splices and pre-history proxies (pre-RFR IBOR, 30y proxied by the longest bond > 10y before the mid-1990s) are listed as limitations. Short-gamma and swap-spread studies start where curve quality was acceptable (2004; late 1990s).
- Survivorship: save your own daily snapshots forward. A 'buy the 10 lowest-priced of the 1,000 largest' test returned -42% on true data vs +388% on a survivor-biased database (Chan 2009, equity, but the mechanism applies to bond universes, delisted/matured lines).

### 9. Controls and known-answer tests (details in [references/engine-test-battery.md](references/engine-test-battery.md))
- **Truncation test** (Chan): run on the full data -> positions A; drop the last N = 10-100 days and rerun -> B; if A != B on the overlap there is look-ahead.
- **Lag sweep**: lag 1, 2, 3 (and 5). If delay *improves* results the signal is early, a red flag (Narang: +746% became +870% with a 1-day delay). A rule that works contemporaneously and collapses with a 1-day lag is suspect (Willer & Saunders).
- **Null and mirror controls**: random entry (1,000 draws -> p-value), inverted signal (must lose), always-on side, date permutation (Sharpe ~ 0), look-ahead injection (Sharpe must jump), a null instrument where no relationship should exist.
- **Known-answer tests**: flat strip, zero moves -> P&L 0 to 1e-9; zero-move carry identity; analytic option greeks within 0.1%; simulated hedge with realised = implied vol -> mean ~ 0; unbiased random walk -> no strategy earns (a martingale), so profit there is an engine bug (Chakraborty & Kearns, 2011).
- **Mutation test**: break a sign or factor on purpose, confirm the test fails, restore. A check that cannot fail is not a check.

### 10. Report minimum (every backtest result)
Net and gross P&L; **P&L at 0x / 0.5x / 1x / 2x costs and the break-even one-way cost** per DV01 traded (annualised cost = round-trip cost / holding period in years, Grinold & Kahn ch.14); carry/roll split from mtm; ex-direction (hedged or mean-removed) Sharpe and a
comparison with simply being long/short the outright; bets (not trades) and effective N; hit rate with average win/loss; max drawdown (peak-to-trough of cumulative P&L, or `(1 + HWM)/(1 + cum) - 1` on compounded returns) and time under water; unsmooth autocorrelated return series before comparing Sharpes; turnover; percentage of time on; sample dates;
trial count (N) from the log; list of known limitations (mid marks, no margin/CSA, splices, funding ignored, same-close snapshot); deviations from spec (spec says / did / why / expected effect).

## Worked examples

**A. Mechanics with hand-checkable numbers (script test T1).** Spread level `S = 10, 11, 13, 12, 12` bp; decisions `q = 10, 10, 0, 0, 0` ccy/bp (long 10 DV01 decided at closes 0 and 1, flat decided from close 2). With `exec_lag = 1`
the position held is `h = 0, 10, 10, 0, 0`. mtm: close 2 earns `10 x (13 - 11) = +20`, close 3 earns `10 x (12 - 13) = -10`, total +10. Trades 0->10 and 10->0 = 20 DV01 x 0.5 bp one-way = -10 cost, net 0. The same signal filled at lag 0 earns `10x1 + 10x2 = +30`: same-bar fill flatters by 3x on this path.

**B. Costs flip the sign (Chan, Quantitative Trading, 2009).** A cross-sectional reversal rule on S&P 500 stocks in 2006 showed Sharpe ~0.25 gross and ~-3.19 net of 5 bp one-way; updating at the open instead of the close: 4.43 gross, 0.78 net. An intraday Bollinger mean-reversion rule: ~3 gross, ~-3 net of 1 bp. Equity examples, but the arithmetic is general:
`P&L_net = P&L - sum |dw| x one-way cost`. Always run the 0/0.5/1/2x sweep, and compare break-even cost with the real half bid/offer.

**C. Financed bond holding return (Tuckman & Serrat, Fixed Income Securities, 4th ed., 2022).** 7.625s of 11/15/22 bought at 114.8765, valued at 111.3969 plus a 3.8125 coupon after 6 months, per 1m face:
`(1,113,969 + 38,125 - 1,148,765) / 1,148,765 = 0.2898%`. Funding the full price at 0.05% for 6m costs $287 -> net `0.2648%`. With 98% repo financing ($1,125,790): interest $281, net on $22,975 of capital = `(3,329 - 281)/22,975 = 13.27%` (50x leverage, period return). Even with no explicit repo, charge funding or opportunity cost.

**D. Long basis P&L = basis change + carry (Burghardt et al., The Treasury Bond Basis, 3rd ed., 2005).** Buy $10mm 7.5% 11/16 at 120-20, sell 115 June futures at 103-30, repo 4.5%; unwind 14 days later at 116-21 / 100-16.
Bonds `-$396,875` (127/32 x $3,125), futures `+$395,312.50` (110/32 x 115 x $31.25), coupon `+$29,005.52` (10mm x 0.075/2 x 14/181), repo `-$21,624.23` ($12,356,700 x 4.5% x 14/360): total `+$5,818.80` (components sum to 5,818.79: source rounding) = basis change `-$1,562.50` + carry `+$7,381.29`.
Financing flips basis backtests: a short basis on the bond that went special lost $14,276 while the same trade on the old issue made $14,211 (May-Jun 2000); model own-issue repo, never GC.

**E. Linear roll-adjustment decay (illustrative numbers; formula from RiskVal, 2020).** WI roll `+1.5 bp`, 5 business days between `beginDay` and auction day: `adj = 0, 0.3, 0.6, 0.9, 1.2, 1.5 bp`. It is 0 where the previous stitch sits and equals the full WI roll on auction day, so the stitched history has no jump at either end and no accumulated drift.

**F. A published event-time grid (BofA, US Treasury auction primer, 8 Mar 2024).** Rows = entry day relative to the auction (-9..+7), columns = exit day (-7..+9); per cell: average (bp), SD, hit ratio, "Sharpe" = average/SD, `Score = hit ratio x Sharpe`. Last 12 10y auctions: best 2s10s steepener entry -9 / exit -3 +3.5 bp; holding through the auction lost (entry -3 / exit +5: -5.8 bp). Twelve observations per cell is regime-sensitive: contrast with the last 6 months and require an economic story.

More published rule backtests with their numbers and caveats: [references/published-rule-backtests.md](references/published-rule-backtests.md).

## Signals & interpretation (how to read a backtest)
- **Credibility screens** (Grinold & Kahn; Narang; Chan): IC above ~0.20 usually signals a faulty backtest; IR far above 2 signals mistakes; an out-of-sample R^2 of 0.05 is excellent, above 0.15 suggests a mistake; a profit on an unbiased random walk is a bug.
  At most 5 free parameters and ~252 data points per free parameter. With 20 independent tries the chance of at least one 5%-level fluke is 1 - 0.95^20 = 64% (about 60% for |t| >= 2).
- **Statistical weight**: `t ~ IR x sqrt(years)`, `SE(SR_ann) ~ sqrt((1 + SR_p^2/2)/T) x sqrt(periods/yr)` with `SR_p` the per-period Sharpe and T the number of periods (iid); breadth `BR = (IR/IC)^2` (IR 0.27, IC 0.01 -> ~700 independent bets). Use bets, not rows.
- **Paper vs live**: in one study a rule's recommended trades (+6.9 ticks) became +3.3 net of all costs when traded (Burghardt ch.7), roughly half; treat that as an order of magnitude, not a constant. Many sell-side backtests exclude costs, carry, stops and intraday moves.
- **Direction check**: outright versions often look good only because of the yield trend. Strip direction (hedge vs Bund or the outright) and compare IR with always-long: bond momentum was long ~77-80% of the time in bull samples (JPM, Simple rules to trade duration, Oct 2012).
- **Hit rate on short-option-like structures** (short gamma, short basis) is not evidence of edge: 23 of 25 short-basis trades gained, yet that does not show the options were overpriced (Burghardt ch.6). Stress it and bucket P&L by the size of the underlying move: a convex payoff shows a smile, not a ramp.
- **Time under the rule**: report active IR with `% on`; a conditional rule is credible when both conditions of a two-condition filter improve IR (Willer & Saunders).
- **Plateau, not peak**: Sharpe vs parameter should be a broad plateau; Sharpe vs cost is roughly linear (report intercept and slope).
- **Regime failure**: threshold rules that earned ~5 bp a turn for 21 months lost ~15 bp in five months when the fly trended to +20 bp (Lehman, Macro-awareness in RV trading, Oct 2003). Carry rules fail on vol and crowding, not low carry, and break under yield-curve control.

## Pitfalls
- **Same-bar fills, full-sample statistics, release-vs-period dating** are the three look-ahead families; the truncation, lag and permutation tests catch them.
- **Constant-maturity marks for aged trades**: no carry, wrong convexity, flat or inflated curves. Reprice the aged package.
- **Relative tenors re-resolved every day**; **0 for missing**; **forward-filled stale marks**; **units in decimals**; **sign taken from an unsigned DV01**.
- **A required gating column that is present but null** silently emptied the universe on 284 of 332 dates. Validators must reject present-but-null required columns.
- **Costs embedded in a level series** or charged on the whole position at every resize (charge the traded increment; one round trip = the full charge, not half).
- **Overlapping holds and persistent signals** inflate case counts (297 'cases' were not independent, Burghardt ch.7).
- **Optimisers on history**: calibrating stop/profit-take by history on long-half-life spreads is overfitting; with phi near 1 there is no optimum (AFML ch.13). Prefer synthetic calibration from fitted OU parameters (see [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md)).
- **Fixed-horizon outcomes ignore the path**: positions that would have been stopped out are counted as profits; use volatility-scaled barriers where stops exist.
- **Illiquidity alpha fades** when liquidity normalises (EGB supply concessions 2013-14); best event timing drifts (IT-ES switch T-1 -> T-2); re-test timing periodically.
- **Vol targeting is not a tail fix**: an 11-day EWMA with monthly rebalance raised IRS excess kurtosis 2.4 -> 2.9 (Macrosynergy, IRS returns, 2018 data); trailing vol fails where vol is low just before crises.
- **Small samples**: 12-17 event observations, 15 presidential terms, one structure's result generalised to a strategy. Treat as soft priors.
- **Market quirks**: see the table below.

| Market | Backtest-specific differences |
|---|---|
| USD | UST P&L must include repo with specials and must not roll to the new on-the-run mid-hold; futures settle ~15:00 ET vs 17:00 NY snaps; SOFR curve node-starved before Jul 2019; CBOT notional coupon moved 8% -> 6% in 2000 (CTD behaviour); CFTC data lag 5 days |
| EUR | Futures have small deliverable sets, a fixed delivery day, higher squeeze/fail risk; EGB supply concessions strongest pre-auction (IT, ES, BE, FR); residual-model samples start Jan 2014; expect degradation around QE transitions |
| GBP | Gilt ex-dividend periods give negative accrued; index-linked carry makes quoted real yields and breakevens misstate realised P&L for short linkers (use carry-adjusted series); ex-dividend can remove a CTD mid-month |
| JPY | Time-zone lag (2 days vs USD-timed legs); yield-curve control breaks mechanical carry signals; lowest real yield and vol gave a long-duration bias (excluding Japan cut beta 0.4 -> 0.0); JPY IRS the least correlated DM (0.2-0.3) |
| CAD, AUD, NZD, CHF, SEK, NOK | No market-specific backtest conventions in the sources. Use the same engine with local calendars and snaps; AUD/NZD (Asia-Pacific close) vs North America/Europe legs need the 2-day lag or a same-snap source; CHF has the lowest IRS vol (45 bp monthly SD) so equal-weight cross-market books under-risk it; weight by liquidity |

## Output
Return (and hand to [rv-trade-idea-writeup](../rv-trade-idea-writeup/SKILL.md) when a trade follows):
1. **Spec card**: universe, signal, thresholds, sizing, hedge/roll rules, lag, snap, costs, sample, warm-up, trial count.
2. **Daily tables** in the canonical form: `positions`, `trades`, `pnl` (mtm, carry, financing, cost, total; the identity checked to 0.01).
3. **Result table**: net/gross P&L, annualised Sharpe with SE, t-stat, hit rate, avg win/loss, max DD and time under water, turnover, % on, bets and effective N; cost sweep 0/0.5/1/2x and break-even cost; ex-direction row; always-on and inverted controls.
4. **Test log**: truncation, lag sweep (1/2/3/5), null/mirror controls, known-answer tests, mutation check: pass/fail with numbers.
5. **Limitations and deviations** list, and a one-line verdict: *no edge / edge not distinguishable from costs / edge survives*.

## Scripts
- [`scripts/backtest.py`](scripts/backtest.py): causal z-score, fade state machine with stop lock-out, DV01 or vol-target sizing, lagged P&L split into mtm/carry/financing/cost (calendar-day accrual, Fri->Mon = 3x), cost sweep and break-even cost, Sharpe/SE/drawdown summary, and a look-ahead `truncation_test`.
  `python scripts/backtest.py --series spread.csv --value-col spread_bp --cost-bp 0.3 --target-daily-ccy 10000`; `python -I scripts/backtest.py --selftest` checks hand-computed P&L, the carry identity, the state machine, that the truncation test passes a causal and fails a look-ahead signal,
  no profit on a random walk, profit on a simulated OU spread (inverted loses), and cost monotonicity.
  It is a panel engine: certify the winners with a repricing engine.

## Related skills
- [bt-validation-and-overfitting](../bt-validation-and-overfitting/SKILL.md): walk-forward, purged CV, deflated Sharpe, PBO: run after the engine passes.
- [bt-transaction-costs-and-liquidity](../bt-transaction-costs-and-liquidity/SKILL.md): bid/offer tables, impact and capacity for the cost inputs.
- [bt-performance-attribution](../bt-performance-attribution/SKILL.md): explain the P&L produced here (carry/roll/factors) and build the tearsheet.
- [data-quality-and-timeseries-hygiene](../data-quality-and-timeseries-hygiene/SKILL.md): stale data, snaps, roll stitching, outliers before the engine.
- [data-contract-and-adapters](../data-contract-and-adapters/SKILL.md): canonical `signals`, `positions`, `trades`, `pnl`, `roll_map`.
- [quant-zscore-and-signal-screening](../quant-zscore-and-signal-screening/SKILL.md) and [quant-signal-combination-and-decay](../quant-signal-combination-and-decay/SKILL.md): the signals being tested.
- [quant-mean-reversion-ou](../quant-mean-reversion-ou/SKILL.md): half-life and optimal entry/exit bands.
- [fi-carry-and-rolldown](../fi-carry-and-rolldown/SKILL.md): carry measurement by repricing the aged package.
- [fut-calendar-roll](../fut-calendar-roll/SKILL.md): futures roll mechanics and roll-adjusted generics.
- [port-position-sizing-and-risk-budget](../port-position-sizing-and-risk-budget/SKILL.md): vol targeting, DV01 budgets, stops.
- [ml-financial-ml-methodology](../ml-financial-ml-methodology/SKILL.md): labelling, sample weights and leakage for ML signals.
- [rv-opportunity-scan](../rv-opportunity-scan/SKILL.md): the screen whose rules are backtested here.
- [quant-regression-and-hedge-ratios](../quant-regression-and-hedge-ratios/SKILL.md): rolling betas for the prior-day hedge ratio.
- [curve-forward-grid-rv](../curve-forward-grid-rv/SKILL.md) and [vol-gamma-vega-pnl](../vol-gamma-vega-pnl/SKILL.md): forward-curve vs straddle packages, gamma/theta P&L checks.
- [fut-bond-basis-and-implied-repo](../fut-bond-basis-and-implied-repo/SKILL.md) and [spread-swap-spreads-and-asw](../spread-swap-spreads-and-asw/SKILL.md): basis and swap-spread P&L conventions.
- [fi-risk-dv01-and-transforms](../fi-risk-dv01-and-transforms/SKILL.md): DV01 sign and fly-weight conventions.

## References
- Internal research spec: forward curve vs straddle systematic backtest (v0.4, 23 Oct 2026): ticket marking at live start, carry identity, move-based hedging, controls C1-C5, known-answer tests T1-T12.
- Internal handover note: convexity RV panel/engine split (undated, data to ~Aug 2026): lag rule, repricing carry, snap/date/node-grid traps, cost sweep reporting.
- Internal implementation prompt: forward curve vs straddle backtest (undated): data hygiene, holdout lock, deviations list, mutation tests.
- User's own research-code notes (internal engine and data-port lessons): event-driven loop shape, per-product P&L rules, unit/sign/null-column landmines, fee hook.
- Marcos Lopez de Prado - Advances in Financial Machine Learning (Wiley, 2018), ch.2, 3, 10-14: PIT data, ETF trick, backtest purpose and the seven sins (after Luo et al., 2014), walk-forward, synthetic OTR exits, TWRR, bet sizing (external).
- Ernest P. Chan - Quantitative Trading (Wiley, 2009): lagged-position P&L, truncation look-ahead test, rf rule, drawdown recursion, cost sign flips.
- Burghardt, Belton, Lane, Papa - The Treasury Bond Basis (3rd ed., McGraw-Hill, 2005): long/short basis P&L decomposition, financing, paper vs real trades, overlapping cases.
- Tuckman & Serrat - Fixed Income Securities (4th ed., Wiley, 2022): gross and financed holding-period returns.
- Palomar - Portfolio Optimization: Theory and Application (Cambridge UP, 2025), ch.8, 15: lagged signal formula, rolling z-score, backtest schemes.
- Grinold & Kahn - Active Portfolio Management (2nd ed., McGraw-Hill, 1999): information analysis before backtest, IC/IR/breadth, cost amortisation.
- Paleologo - The Elements of Quantitative Investing (Wiley, 2025), ch.8: PIT rule, data checklist, production parity.
- Tulchinsky et al. - Finding Alphas (Wiley, 2015): position-matrix model, NaN rule, delay/decay/neutralise, null controls, invalid OOS designs.
- Narang - Inside the Black Box (3rd ed., Wiley, 2024): time-decay test, goodness metrics, plateau rule.
- Willer & Saunders - Trading Global Macro Markets (Wiley, 2026): 1/2-day lag convention, publication lags, rolling percentiles, active IR and % on.
- RiskVal Financial Solutions - Generic Time Series Data & Roll Adjustment (28 Jul 2020): on-the-run stitching, linear WI-roll decay.
- Chakraborty & Kearns - Market Making and Mean Reversion (EC'11, 2011): random-walk zero-profit check, OU profit identity.
- Citi Research - US Rates Vol Lab: Trading long-dated convexity (Bikbov, Williams; 9 May 2019): delta-hedged flattener design, hedge-threshold plateau, hedge timing.
- Citi Research - US Rates Vol Lab: The art of gamma hedging (Bikbov, Williams; 12 Mar 2018): short-gamma book construction, hedging variants.
- J.P. Morgan - Do androids dream of electric bonds? (Salem, Younger, Zhao et al.; 22 Nov 2017) and TradeRunner (16 Aug 2018): instrument P&L recipes, quarantine, shuffle-test residual Sharpe.
- J.P. Morgan - Simple rules to trade duration (Mac Gorain; 2 Oct 2012); Exploiting carry with cross-market and curve bond trades (Panigirtzoglou; 11 Jan 2007): rebalance-day sensitivity, per-leg financing, long-bias checks.
- BofA - US Treasury auction primer (Craig et al.; 8 Mar 2024): entry/exit event-time grid with Score = hit ratio x Sharpe.
- J.P. Morgan - Follow the cash flow: trading strategies around supply, redemptions and coupon payments in euro government bond markets (Salford, Chordia; 15 Sep 2015): event-window robustness grid, hedge-type comparison, pre-cost caveat.
- BofA Merrill Lynch - A simple framework for swap spread relative value (Axel et al.; 2 Jun 2016): next-close marking, threshold tables without costs.
- BofA Merrill Lynch - Many EGBs, one simple value tool (Satko; 21 Mar 2018) and BofA - Global inflation-linked primer (22 Jul 2025): expanding-window EGB residual rule; carry-adjusted linker history.
- Lehman Brothers - Macro-Awareness in Relative Value Trading (Tuckman; Oct 2003): threshold rule that worked, then failed in a trend.
- Macrosynergy - Interest rate swap returns: empirical lessons (web print Aug 2025; data to Feb 2018): IRS return construction, vol-targeting kurtosis.
- Salomon Brothers - Understanding the Yield Curve, Part 3 (Ilmanen; Jul 1995) and Part 4: Forecasting U.S. Bond Returns (Aug 1995): neutral sample choice, expanding-window OOS protocol, in-sample vs OOS gap.
- Brenndoerfer - Mean Reversion and Statistical Arbitrage (online handbook chapter, 27 Dec 2025): z-rule defaults, prior-day hedge ratio, gross-notional normalisation.
- Leung & Li - Optimal Mean Reversion Trading (World Scientific, 2016): cost- and stop-dependent entry/exit bands, holding-cost penalty (the printed example is inconsistent).
- Cuturi & d'Aspremont - Mean-Reverting Portfolios: Tradeoffs Between Sparsity and Volatility (arXiv, 2015): Sharpe-versus-cost intercept and slope.
- Nordea Markets - Bonds & bold (Aalund; Nov 2021): delta-hedged swaption straddle backtest, monthly ATMF re-entry, full-grid valuation.
- Citi Research - US Rates Weekly: Deal or no deal (Mathai, Bikbov et al.; 10 May 2019) and EM Strategy Weekly: Can back-end USTs derail EM risk? (Costa et al.; 20 Aug 2026): hedge mechanics and live sizing; hypothetical P&L convention (bid/offer at open and close, mid marks).
- J.P. Morgan - A cross-market bond carry strategy (Investment Strategies No. 15; Panigirtzoglou; 9 Mar 2006); Rule-based Fixed Income Monthly (Mac Gorain; 2 Nov 2012); Update on systematic rule based trading strategies (Gupta, Inkinen, Vijay; 10 Jul 2017); An option by any other name (Younger et al.; 3 Feb 2017); Monthly Inflation Outlook (Diamond et al.; 13 Aug 2026): rule designs, cost assumptions, bucket tests.
- BofA - Technicals Explained primer (Ciana, Suttmeier; 14 Jan 2025); US Rates Watch (Cabana et al.; 10 Mar 2025); FX Quant Primer (Iaralov et al.; 1 Oct 2018); UST RV primer: a hitchhikers guide (Zhang et al.; 2 May 2022): event-study and percentile-bucket designs, hit-ratio definitions, earlier auction grid.
- Quantitative Finance Stack Exchange - "How to adjust butterfly 2s5s10s swaps trade for directionality?" (2018) and "Bergomi: Skew arbitrage" (2020): fly-weight out-of-sample comparison; cost wipe-out of daily unwind and restart.
